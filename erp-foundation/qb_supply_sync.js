#!/usr/bin/env node
'use strict';
/**
 * qb_supply_sync.js — QuickBooks vendors + purchase orders → ERP supplier master / PO tables (audited DAL).
 * Also folds in the Supplier-Diligence-exo3 registry (DD tier/status) and BOM-only suppliers not yet in QB.
 *
 * MC owns: ASL status, qualification, certs, flight-critical scope, review dates, receiving inspections,
 * and every PO raised in MC. QB owns: vendor identity/contact and POs created directly in QB. A sync never
 * overwrites an MC-owned field; unchanged QB records are skipped (no audit noise).
 *
 * Run: node erp-foundation/qb_supply_sync.js [--json /tmp/qbsupply.json]   (launchd com.exos.qb-supply-sync, 30 min)
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');
const { openErp } = require('./dal');

const WS = path.join(__dirname, '..');
const DD = path.join(WS, 'mission-control', 'data', 'supplier-dd-registry.json');
const ACCTS = path.join(WS, 'mission-control', 'data', 'qb-accounts-cache.json');
const norm = s => String(s || '').toLowerCase().replace(/[,.]|\b(inc|llc|corp|corporation|co|ltd|company)\b/g, '').replace(/\s+/g, ' ').trim();
const hash = o => crypto.createHash('sha1').update(JSON.stringify(o)).digest('hex').slice(0, 16);
const slug = s => norm(s).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60);

function loadQB() {
  const i = process.argv.indexOf('--json');
  const raw = i > 0 ? fs.readFileSync(process.argv[i + 1], 'utf8')
    : execFileSync('/usr/bin/python3', [path.join(WS, 'scripts', 'qb_supply.py'), 'pull'], { timeout: 240000, maxBuffer: 64 * 1024 * 1024 }).toString();
  const d = JSON.parse(raw);
  if (d.error) throw new Error('QB pull failed: ' + d.error);
  return d;
}

function main() {
  const qb = loadQB();
  let dd = { suppliers: [] };
  try { dd = JSON.parse(fs.readFileSync(DD, 'utf8')); } catch (e) {}
  const ddList = Array.isArray(dd.suppliers) ? dd.suppliers : Object.values(dd.suppliers || {});
  const ddByName = new Map(ddList.map(s => [norm(s.name), s]));

  const erp = openErp(path.join(__dirname, 'mc.db'), { actor: 'qb-supply-sync', agent: 'qb-supply-sync' });
  const stats = { vendors_new: 0, vendors_upd: 0, pos_new: 0, pos_upd: 0, dd_only: 0, skipped: 0 };
  try {
    const existing = new Map(erp.listVendors().map(v => [v.id, v]));
    const qbToVid = new Map();
    const seenDD = new Set();
    for (const v of qb.vendors) {
      const id = 'v-qb-' + v.qb_id;
      qbToVid.set(String(v.qb_id), id);
      const d = ddByName.get(norm(v.name)) || ddByName.get(norm(v.company));
      if (d) seenDD.add(norm(d.name));
      const qbPart = { name: v.name, qb_id: String(v.qb_id), company: v.company, email: v.email, phone: v.phone,
                       country: v.country || (d && d.country) || '', city: v.city, state: v.state, active: v.active, is_1099: v.is_1099 };
      const ddPart = d ? { dd_tier: d.tier || null, dd_status: d.status || null, dd_flags: d.flags || [], dd_updated: d.updated || null, cui_exposure: !!d.cui_exposure } : {};
      const h = hash({ qbPart, ddPart });
      const cur = existing.get(id);
      const prev = cur && cur.raw_json ? JSON.parse(cur.raw_json) : null;
      if (prev && prev.qb_hash === h) { stats.skipped++; continue; }
      const rec = { id, ...qbPart, ...ddPart, qb_hash: h, source: 'qb' };
      if (!prev) rec.asl_status = 'Not evaluated';
      erp.upsertVendor(rec);
      prev ? stats.vendors_upd++ : stats.vendors_new++;
    }
    // BOM / DD-registry suppliers that don't exist in QB yet (no PO history) — still part of the supplier master.
    for (const d of ddList) {
      if (seenDD.has(norm(d.name))) continue;
      const id = 'v-dd-' + slug(d.name);
      const ddPart = { name: d.name, country: d.country || '', dd_tier: d.tier || null, dd_status: d.status || null,
                       dd_flags: d.flags || [], dd_updated: d.updated || null, cui_exposure: !!d.cui_exposure, source: d.source || 'dd' };
      const h = hash(ddPart);
      const cur = existing.get(id);
      const prev = cur && cur.raw_json ? JSON.parse(cur.raw_json) : null;
      if (prev && prev.qb_hash === h) { stats.skipped++; continue; }
      erp.upsertVendor({ id, ...ddPart, qb_hash: h, ...(prev ? {} : { asl_status: 'Not evaluated' }) });
      stats.dd_only++;
    }

    // Purchase orders. A PO raised in MC and pushed to QB comes back here with its qb_id → update status only.
    const byQb = new Map(erp.listPOs({ limit: 100000 }).filter(p => p.qb_id).map(p => [String(p.qb_id), p]));
    for (const p of qb.pos) {
      const mine = byQb.get(String(p.qb_id));
      const vendor_id = qbToVid.get(String(p.vendor_qb_id)) || null;
      const qbPart = { po_number: p.doc_number, qb_id: String(p.qb_id), vendor_id, total: p.total, issued_at: p.txn_date,
                       qb_status: p.status, qb_due_date: p.due_date, memo: p.memo, private_note: p.private_note };
      const lines = p.lines.map((l, i) => ({ description: l.description, qty: l.qty, unit_price: l.unit_price, amount: l.amount, account: l.category, line_no: i + 1, qb_line_id: l.qb_line_id }));
      const h = hash({ qbPart, lines });
      const prev = mine ? JSON.parse(erp.getPO(mine.id).raw_json || '{}') : null;
      if (prev && prev.qb_hash === h) { stats.skipped++; continue; }
      if (mine && mine.source === 'mc') {
        // MC-originated: QB is downstream. Only reflect QB closing it (billed/received in QB).
        const upd = { id: mine.id, qb_status: p.status, qb_hash: h };
        if (p.status === 'Closed' && !['received', 'closed', 'cancelled'].includes(mine.status)) upd.status = 'closed';
        erp.upsertPO(upd);
        stats.pos_upd++; continue;
      }
      const id = mine ? mine.id : 'po-qb-' + p.qb_id;
      const status = p.status === 'Closed' ? 'closed' : (prev && ['partially_received', 'received'].includes(prev.status) ? prev.status : 'open');
      erp.upsertPO({ id, source: 'qb', ...qbPart, status, qb_hash: h }, mine ? undefined : lines);
      mine ? stats.pos_upd++ : stats.pos_new++;
    }
    fs.writeFileSync(ACCTS + '.tmp', JSON.stringify({ generated_at: new Date().toISOString(), accounts: qb.accounts }));
    fs.renameSync(ACCTS + '.tmp', ACCTS);
  } finally { erp.close(); }
  console.log(JSON.stringify({ ok: true, at: new Date().toISOString(), ...stats }));
}

try { main(); } catch (e) { console.error('qb-supply-sync failed:', e.message); process.exit(1); }
