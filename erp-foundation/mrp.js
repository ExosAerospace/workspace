#!/usr/bin/env node
'use strict';
/**
 * mrp.js — ERP Phase 5C: Material Requirements Planning on the audited ERP db.
 *
 *   sync  Load the MC materials files into the ERP (part master, every vehicle BOM in mrp-assemblies.json — BLK3, HVRR —,
 *         physical counts, missions) and
 *         post ERP receiving (accepted receipts) into the inventory ledger. Idempotent; only changed rows
 *         are written/audited. Mission Control pages keep reading their JSON files unchanged.
 *   run   Demand = flight vehicles with missions booked (asset serial → BOM assembly; M5 + M6 on BLK3 S0 =
 *         ONE BLK3 build set) + non-mission builds from mrp-assemblies.json (HVRR-1). Parts shared across vehicles
 *         are netted once against the common stock pool. Net = gross − on hand − on order (open PO lines). Shortages become per-vendor
 *         PURCHASE REQUESTS (proposals only). A request becomes a PO only when a person converts it into a
 *         PO draft and submits it through the existing Suppliers & POs approval flow (≥ $5K / flight-critical
 *         → Jon's Decision card). This engine never creates, approves, or sends a PO and never touches QB.
 *   all   sync + run (default).
 *
 * Usage: node erp-foundation/mrp.js [sync|run|all] [--actor email] [--json]
 */
const fs = require('fs');
const path = require('path');
const { openErp } = require('./dal');

const WS = path.join(__dirname, '..');
const DATA = path.join(WS, 'mission-control', 'data');
const DB = process.env.MRP_DB || path.join(__dirname, 'mc.db');
const readJSON = (f, d) => { try { return JSON.parse(fs.readFileSync(path.join(DATA, f), 'utf8')); } catch { return d; } };
const num = v => { const n = parseFloat(String(v == null ? '' : v).replace(/[$,]/g, '')); return isNaN(n) ? null : n; };
const r3 = n => Math.round((Number(n) || 0) * 1000) / 1000;
const r2 = n => Math.round((Number(n) || 0) * 100) / 100;
const normPN = s => String(s || '').trim().toUpperCase().replace(/\s+/g, '');
// Vehicle BOMs + non-mission builds (BLK3, HVRR, ...). BLK3 is the default if the file is missing.
const assemblyConfig = () => readJSON('mrp-assemblies.json', { assemblies: [{ id: 'BLK3', bom_index: 'bom-index.json', overlays: true }], builds: [] });
// A part number specific enough to find inside free-text PO lines: >= 5 chars, has a digit, not a <ASSEMBLY>-<section>-<item> placeholder.
const matchablePN = pn => pn.length >= 5 && /\d/.test(pn) && !pn.startsWith('BLK3-') && !pn.startsWith('HVRR-');

// BOM vendor spellings → one canonical name ("Digikey"/"DigiKey"/"Digi-Key" → Digi-Key).
const VENDOR_ALIASES = [
  [/^digi-?key/i, 'Digi-Key'], [/^mouser/i, 'Mouser'], [/^mc ?master/i, 'McMaster-Carr'], [/^aircraft spruce/i, 'Aircraft Spruce'],
  [/^pasterna?c?k/i, 'Pasternack'], [/^morga?n? newton/i, 'Morgan Newton'], [/^hobby ?town/i, 'HobbyTown'], [/^pei[- ]gene?s/i, 'PEI-Genesis'],
  [/^radwell/i, 'Radwell'], [/^exos\b/i, 'Exos'], [/^allied/i, 'Allied Electronics & Automation'],
];
const canonVendor = v => {
  const s = String(v || '').trim().replace(/[`]+$/, '');
  if (!s || /^\?+$/.test(s)) return '';
  for (const [re, name] of VENDOR_ALIASES) if (re.test(s)) return name;
  return s;
};
const vkey = s => String(s || '').toLowerCase().replace(/\b(inc|llc|co|corp|company|electronics|specialty|ltd)\b/g, '').replace(/[^a-z0-9]/g, '');

function vendorIndex(erp) {
  const idx = {};
  for (const v of erp.listVendors()) {
    const k = vkey(v.name); if (!k) continue;
    if (!idx[k] || (v.qb_id && !idx[k].qb_id)) idx[k] = v;
  }
  return name => {
    const k = vkey(name); if (!k) return null;
    if (idx[k]) return idx[k];
    const hit = Object.keys(idx).filter(x => x.startsWith(k) || k.startsWith(x)).sort((a, b) => b.length - a.length)[0];
    return hit && hit.length >= 5 ? idx[hit] : null;
  };
}

// ── sync ────────────────────────────────────────────────────────────────────
function sync(erp) {
  const stats = { parts: 0, parts_changed: 0, bom_lines: 0, bom_changed: 0, counts_posted: 0, receipts_posted: 0, missions: 0 };
  const blk3Edits = readJSON('bom-edits.json', {});
  const blk3Costs = (readJSON('bom-costs.json', { costs: {} }).costs) || {};
  const inv = readJSON('inventory.json', { records: [] });
  const shop = readJSON('shop-inventory.json', { items: [] });
  const findVendor = vendorIndex(erp);

  // Physical stock sources (same matching rules as /api/inventory so the ERP and the page agree).
  const shopBy = {};
  for (const it of shop.items || []) for (const k of [it.exos_sku, it.source_sku]) {
    const kk = normPN(k); if (kk.length >= 5) shopBy[kk] = (shopBy[kk] || 0) + (parseFloat(it.qty) || 0);
  }
  const recBy = {};
  for (const r of inv.records || []) {
    for (const k of [r.vendor_pn, r.mfg_pn, r.key]) if (k) recBy[normPN(k)] = r;
    if (r.section && r.item) recBy[`${String(r.section).toUpperCase()}#${r.item}`] = r;
  }

  const parts = {};      // part_id → part rec
  const onHand = {};     // part_id → counted qty (max across the BOM lines that share the part)
  const locs = {};
  const bomLines = [];   // written after the parts they reference (FK)
  const seen = {};
  stats.assemblies = {};
  for (const asm of assemblyConfig().assemblies) {
  const A = asm.id;
  const bom = readJSON(asm.bom_index, { rows: [] });
  // bom-edits / bom-costs / ledger section#item matches are keyed to the BLK3 BOM rows only.
  const edits = asm.overlays ? blk3Edits : {};
  const costs = asm.overlays ? blk3Costs : {};
  stats.assemblies[A] = (bom.rows || []).length;
  for (const row of bom.rows || []) {
    const sec = row.section || '', item = String(row.item || '');
    const key = `${sec}#${item}`;
    const pn = row.vendor_pn || row.mfg_pn || '';
    // No part number → assembly-scoped placeholder (BLK3 ids unchanged from the first load).
    const pid = pn ? 'pt-' + normPN(pn) : `pt-${A}-${sec.replace(/\W+/g, '')}-${item}`;
    const ed = edits[key] || {};
    const c = costs[key];
    const sheet = num(row.cost);
    const unit_cost = c && num(c.unit_cost) > 0 ? num(c.unit_cost) : (sheet > 0 ? sheet : 0);
    const cost_basis = c && num(c.unit_cost) > 0 ? (c.basis || 'found') : (sheet > 0 ? 'bom-sheet' : 'none');
    const vendor = canonVendor(row.vendor);
    const v = vendor && vendor !== 'Exos' ? findVendor(vendor) : null;
    const p = parts[pid] || (parts[pid] = {
      id: pid, part_number: pn || `${A}-${sec}-${item}`, description: ed.description || row.description || '',
      vendor, vendor_id: v ? v.id : null, unit: 'ea', unit_cost: r2(unit_cost) || null, cost_basis,
      make_buy: /^exos/i.test(String(row.vendor || '')) ? 'make' : 'buy', active: 1,
      raw_json: { mfg_pn: row.mfg_pn || '', vendor_pn: row.vendor_pn || '', bom_vendor: row.vendor || '', cost_source: c ? (c.source || '') : '', cost_ref: c ? (c.ref || '') : '' },
    });
    if (!p.unit_cost && unit_cost) { p.unit_cost = r2(unit_cost); p.cost_basis = cost_basis; }

    const qtyPer = num(ed.req !== undefined && ed.req !== '' ? ed.req : row.qty);
    // The BOM sheet repeats a few section#item keys (blank or reused item numbers) — keep each row distinct.
    const sk = `${A}:${key}`;
    seen[sk] = (seen[sk] || 0) + 1;
    bomLines.push({ id: sk + (seen[sk] > 1 ? `~${seen[sk]}` : ''), assembly: A, section: sec, item_no: item, part_id: pid, qty_per: qtyPer,
      raw_json: { description: ed.description || row.description || '', source: bom.source || '', edited_by: ed._by || '' } });

    let rec = null;
    for (const k of [row.vendor_pn, row.mfg_pn]) if (k && recBy[normPN(k)]) { rec = recBy[normPN(k)]; break; }
    if (!rec && item && asm.overlays) rec = recBy[`${sec.toUpperCase()}#${item}`];
    let shopOh = 0;
    for (const k of [row.vendor_pn, row.mfg_pn]) { const kk = normPN(k); if (kk.length >= 5 && shopBy[kk] != null) { shopOh = shopBy[kk]; break; } }
    let oh = (rec ? Number(rec.qty_on_hand) || 0 : 0) + shopOh;
    if (ed.on_hand !== undefined && ed.on_hand !== '') oh = Number(ed.on_hand) || 0;
    onHand[pid] = Math.max(onHand[pid] || 0, oh);
    if (rec && (rec.locations || []).length) locs[pid] = rec.locations.join(', ');
  }
  }
  for (const p of Object.values(parts)) { const r = erp.mrpUpsert('part', p); stats.parts++; if (r.changed) stats.parts_changed++; }
  for (const b of bomLines) { const r = erp.mrpUpsert('bom_line', b); stats.bom_lines++; if (r.changed) stats.bom_changed++; }

  // Physical counts → ledger, only when the count differs from the last one posted.
  const last = erp.lastCountByPart();
  const at = new Date().toISOString();
  let n = 0;
  for (const [pid, qty] of Object.entries(onHand)) {
    if (last[pid] !== undefined && r3(last[pid]) === r3(qty)) continue;
    if (last[pid] === undefined && !qty) continue;
    erp.addInventoryTxn({ id: `cnt-${Date.now().toString(36)}-${n++}`, part_id: pid, kind: 'count', qty: r3(qty), location: locs[pid] || null,
      source: 'mc-inventory (BOM ledger + shop inventory of record)', ref: null, occurred_at: at });
    stats.counts_posted++;
  }

  // ERP receiving (Suppliers & POs → receiving inspection) → ledger, matched to a part by part number.
  const pnIndex = Object.values(parts).map(p => [normPN(p.part_number), p.id]).filter(([pn]) => matchablePN(pn));
  for (const rc of erp.listAcceptedReceipts()) {
    if (!(Number(rc.qty) > 0)) continue;
    const hay = normPN((rc.part_number || '') + ' ' + (rc.description || ''));
    const m = rc.part_number && parts['pt-' + normPN(rc.part_number)] ? ['', 'pt-' + normPN(rc.part_number)] : pnIndex.find(([pn]) => hay.includes(pn));
    if (!m) continue;
    if (erp.addInventoryTxn({ id: `rcp-${rc.id}`, part_id: m[1], kind: 'receipt', qty: Number(rc.qty), location: null,
      source: 'erp receiving', ref: rc.id, occurred_at: rc.received_at || at })) stats.receipts_posted++;
  }

  // Missions (demand drivers) — linked to the flight-vehicle asset by serial.
  const assets = erp.listAssets();
  for (const m of (readJSON('missions.json', { missions: [] }).missions || [])) {
    const a = assets.find(x => m.vehicle_serial && x.serial === m.vehicle_serial);
    erp.mrpUpsert('mission', { id: m.id, label: m.label, customer: m.customer || '', vehicle: m.vehicle || '', asset_id: a ? a.id : null,
      status: m.status || '', need_date: m.need_date || null, raw_json: m });
    stats.missions++;
  }
  return stats;
}

// ── run ─────────────────────────────────────────────────────────────────────
function run(erp, actor) {
  const cfg = (() => { try { return JSON.parse(fs.readFileSync(path.join(DATA, 'supply-config.json'), 'utf8')); } catch { return {}; } })();
  const threshold = Number(cfg.approval && cfg.approval.jon_threshold) || 5000;
  const parts = Object.fromEntries(erp.listParts().map(p => [p.id, p]));
  const assets = Object.fromEntries(erp.listAssets().map(a => [a.id, a]));
  const missions = erp.listMissions().filter(m => !['flown', 'cancelled', 'closed'].includes(String(m.status || '').toLowerCase()));

  // Demand per flight vehicle: every booked mission on the same serial shares ONE build set.
  const builds = {};
  for (const m of missions) {
    const key = m.asset_id || `unassigned:${m.id}`;
    const b = builds[key] || (builds[key] = { asset_id: m.asset_id, serial: m.asset_id && assets[m.asset_id] ? assets[m.asset_id].serial : '', assembly: m.vehicle, missions: [], need_by: null });
    b.missions.push(m.id);
    if (m.need_date && (!b.need_by || m.need_date < b.need_by)) b.need_by = m.need_date;
  }
  // Non-mission builds (e.g. the HVRR contract vehicle) from mrp-assemblies.json.
  for (const cb of assemblyConfig().builds || []) {
    if (!cb.assembly || ['complete', 'cancelled', 'paused'].includes(String(cb.status || '').toLowerCase())) continue;
    const a = cb.asset_serial ? Object.values(assets).find(x => x.serial === cb.asset_serial) : null;
    if (a && builds[a.id]) continue;   // already planned through its missions
    builds[a ? a.id : `build:${cb.id}`] = { asset_id: a ? a.id : null, serial: cb.asset_serial || '', assembly: cb.assembly, missions: [cb.id], qty: Number(cb.qty) || 1, need_by: cb.need_by || null, ref: cb.ref || '' };
  }
  const gross = {}, unquantified = new Set(), demandRef = {}, needBy = {}, byAsm = {}, blk3Set = {};
  for (const b of Object.values(builds)) {
    if (!b.assembly) continue;
    const ref = `${b.assembly} ${b.serial || ''}`.trim() + ` (${b.missions.join(', ')})`;
    const q = b.qty || 1;
    for (const l of erp.listBom(b.assembly)) {
      (byAsm[l.part_id] = byAsm[l.part_id] || new Set()).add(b.assembly);
      if (l.qty_per == null) { unquantified.add(l.part_id); }
      else {
        gross[l.part_id] = (gross[l.part_id] || 0) + Number(l.qty_per) * q;
        if (b.assembly === 'BLK3') blk3Set[l.part_id] = (blk3Set[l.part_id] || 0) + Number(l.qty_per);
      }
      demandRef[l.part_id] = demandRef[l.part_id] ? (demandRef[l.part_id].includes(ref) ? demandRef[l.part_id] : demandRef[l.part_id] + '; ' + ref) : ref;
      if (b.need_by && (!needBy[l.part_id] || b.need_by < needBy[l.part_id])) needBy[l.part_id] = b.need_by;
    }
  }

  // Supply: on hand (ledger) + on order (open PO lines matched by part number in the line PN/description).
  const onHand = erp.onHandByPart();
  const pnList = Object.values(parts).map(p => [normPN(p.part_number), p.id]).filter(([pn]) => matchablePN(pn));
  const onOrder = {}, orderRefs = {};
  for (const l of erp.listOpenPoLines()) {
    const hay = normPN((l.part_number || '') + ' ' + (l.description || ''));
    const hit = pnList.find(([pn]) => hay.includes(pn));
    if (!hit) continue;
    onOrder[hit[1]] = (onOrder[hit[1]] || 0) + (Number(l.qty) - Number(l.qty_received));
    (orderRefs[hit[1]] = orderRefs[hit[1]] || []).push(l.po_number || l.po_id);
  }

  const runAt = new Date();
  const runId = 'mrp-' + runAt.toISOString().replace(/[-:]/g, '').replace('T', '-').slice(0, 15);
  const lines = [];
  const ids = new Set([...Object.keys(gross), ...unquantified]);
  let i = 0;
  for (const pid of ids) {
    const p = parts[pid] || {};
    const g = r3(gross[pid] || 0), oh = r3(onHand[pid] || 0), oo = r3(onOrder[pid] || 0);
    let net = unquantified.has(pid) && !gross[pid] ? 0 : r3(Math.max(0, g - oh - oo));
    // 'verify': paid in QuickBooks (for BLK3 S0) but no physical count — almost certainly received or built into S0.
    // Only the BLK3 set is held back for a count; any demand beyond it (e.g. HVRR's set) is still a real buy.
    let ref = demandRef[pid] || '';
    let action = unquantified.has(pid) && !gross[pid] ? 'quantify' : (net > 0 ? (p.make_buy === 'make' ? 'make' : 'buy') : 'none');
    if (net > 0 && p.cost_basis === 'paid') {
      const held = Math.min(net, blk3Set[pid] || 0);
      if (held >= net) action = 'verify';
      else if (held > 0) { net = r3(net - held); ref += ` · ${held} more paid for BLK3 S0, not counted — verify`; }
    }
    lines.push({ id: `${runId}-${++i}`, part_id: pid, assembly: [...(byAsm[pid] || [])].sort().join(', '), demand_ref: ref, gross: g, on_hand: oh, on_order: oo, net,
      unit_cost: p.unit_cost || 0, ext_cost: r2(net * (p.unit_cost || 0)), vendor: p.vendor || '', vendor_id: p.vendor_id || null,
      make_buy: p.make_buy || 'buy', need_by: needBy[pid] || null, action });
  }

  // Purchase requests: one per vendor for the 'buy' shortages. Proposals only.
  const groups = {};
  for (const l of lines.filter(x => x.action === 'buy')) {
    const k = l.vendor_id || ('name:' + (l.vendor || 'Vendor TBD'));
    const g = groups[k] || (groups[k] = { vendor: l.vendor || 'Vendor TBD', vendor_id: l.vendor_id, lines: [], est_total: 0, need_by: null });
    const p = parts[l.part_id] || {};
    g.lines.push({ part_id: l.part_id, part_number: p.part_number, description: p.description, qty: l.net, unit_cost: l.unit_cost,
      cost_basis: p.cost_basis, ext_cost: l.ext_cost, on_order_pos: orderRefs[l.part_id] || [] });
    g.est_total = r2(g.est_total + l.ext_cost);
    if (l.need_by && (!g.need_by || l.need_by < g.need_by)) g.need_by = l.need_by;
  }

  const summary = {
    builds: Object.values(builds).map(b => ({ serial: b.serial, assembly: b.assembly, missions: b.missions, need_by: b.need_by })),
    parts_planned: lines.length,
    short_buy: lines.filter(l => l.action === 'buy').length,
    short_make: lines.filter(l => l.action === 'make').length,
    needs_qty: lines.filter(l => l.action === 'quantify').length,
    verify_paid_not_counted: lines.filter(l => l.action === 'verify').length,
    verify_value: r2(lines.filter(l => l.action === 'verify').reduce((a, l) => a + l.ext_cost, 0)),
    covered: lines.filter(l => l.action === 'none').length,
    est_buy_cost: r2(lines.filter(l => l.action === 'buy').reduce((a, l) => a + l.ext_cost, 0)),
    unpriced_buy_lines: lines.filter(l => l.action === 'buy' && !(l.unit_cost > 0)).length,
    on_order_matched_parts: Object.keys(onOrder).length,
    purchase_requests: Object.keys(groups).length,
    pr_to_jon: Object.values(groups).filter(g => g.est_total >= threshold).length,
    threshold,
  };
  erp.saveMrpRun({ id: runId, run_at: runAt.toISOString(), actor, scope: 'flight vehicles with booked missions', summary }, lines);

  // Supersede the previous run's still-open requests; converted ones stay linked to their PO.
  for (const pr of erp.listPurchaseRequests({ status: 'open' })) erp.mrpUpsert('purchase_request', { id: pr.id, status: 'superseded' });
  let k = 0;
  for (const g of Object.values(groups).sort((a, b) => b.est_total - a.est_total)) {
    erp.mrpUpsert('purchase_request', { id: `pr-${runId.slice(4)}-${String(++k).padStart(2, '0')}`, run_id: runId, vendor: g.vendor, vendor_id: g.vendor_id || null,
      status: 'open', est_total: g.est_total, need_by: g.need_by, routes_to_jon: g.est_total >= threshold ? 1 : 0, po_id: null, raw_json: { lines: g.lines } });
  }
  return { run_id: runId, summary };
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const cmd = ['sync', 'run', 'all'].includes(args[0]) ? args[0] : 'all';
  const ai = args.indexOf('--actor');
  const actor = ai >= 0 ? args[ai + 1] : 'mrp-planner';
  const erp = openErp(DB, { actor, agent: 'mrp-planner' });
  try {
    const out = {};
    if (cmd !== 'run') out.sync = sync(erp);
    if (cmd !== 'sync') out.run = run(erp, actor);
    console.log(args.includes('--json') ? JSON.stringify(out) : JSON.stringify(out, null, 2));
  } finally { erp.close(); }
}

module.exports = { sync, run };
