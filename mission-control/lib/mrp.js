// MRP (ERP Phase 5C): material requirements planning on the audited ERP db (erp-foundation/mrp.js).
// Demand = flight vehicles with booked missions (M5 + M6 on BLK3 S0 = one BLK3 build set). Net = gross − on hand
// − on order. Shortages become per-vendor purchase REQUESTS (proposals). Converting a request creates a PO DRAFT
// in Suppliers & POs; the requester completes it (QB account, flags) and submits it through the existing approval
// flow (≥ $5K / flight-critical / DD not cleared → Jon's Decision card). Nothing here approves, issues, or spends.
'use strict';
const path = require('path');
const { execFile } = require('child_process');

const WS = path.join(__dirname, '..', '..');
const DB = process.env.MRP_DB || path.join(WS, 'erp-foundation', 'mc.db');
const ENGINE = path.join(WS, 'erp-foundation', 'mrp.js');

const send = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };
const parse = s => { try { return s ? JSON.parse(s) : {}; } catch { return {}; } };
const now = () => new Date().toISOString();
function openErp(actor) {
  const { openErp: o } = require(path.join(WS, 'erp-foundation', 'dal'));
  return o(DB, { actor: actor || 'mc-server', agent: 'mc-mrp' });
}
function readBody(req) {
  return new Promise((ok, bad) => { let b = ''; req.on('data', c => { b += c; if (b.length > 1e5) bad(new Error('body too large')); }); req.on('end', () => { try { ok(b ? JSON.parse(b) : {}); } catch (e) { bad(e); } }); });
}
let running = null;

async function handle(req, res, ctx) {
  const fp = new URL(req.url, 'http://x').pathname;
  const s = ctx.getSession(req);
  if (!s) return send(res, 401, { error: 'auth required' });
  if (['member', 'early_adopter'].includes(s.role)) return send(res, 403, { error: 'MRP is limited to Exos staff with purchasing access.' });
  const canAct = ['admin', 'manager'].includes(s.role);
  const me = s.email || s.name || 'unknown';
  const glog = (a, d) => { try { ctx.glog('mrp', a, 'info', '', { by: me, detail: d }); } catch {} };

  if (fp === '/api/mrp' && req.method === 'GET') {
    const erp = openErp(me);
    try {
      const run = erp.latestMrpRun();
      const parts = Object.fromEntries(erp.listParts().map(p => [p.id, p]));
      const vendors = Object.fromEntries(erp.listVendors().map(v => [v.id, v]));
      return send(res, 200, {
        run: run ? { ...run, summary: parse(run.summary_json), summary_json: undefined } : null,
        lines: run ? erp.listMrpLines(run.id) : [],
        missions: erp.listMissions().map(m => ({ ...m, raw_json: undefined })),
        requests: erp.listPurchaseRequests().filter(p => ['open', 'converted'].includes(p.status)).map(p => ({
          ...p, lines: parse(p.raw_json).lines || [], raw_json: undefined,
          asl_status: p.vendor_id && vendors[p.vendor_id] ? vendors[p.vendor_id].asl_status : null })),
        part_count: Object.keys(parts).length, can_act: canAct, running: !!running,
      });
    } finally { erp.close(); }
  }

  if (fp === '/api/mrp/run' && req.method === 'POST') {
    if (!canAct) return send(res, 403, { error: 'Only an admin or manager can re-run MRP.' });
    if (running) return send(res, 409, { error: 'An MRP run is already in progress.' });
    running = new Promise(done => execFile(process.execPath, [ENGINE, 'all', '--actor', me, '--json'], { timeout: 120000, maxBuffer: 4 * 1024 * 1024 },
      (err, out, errout) => done({ err, out, errout })));
    const r = await running; running = null;
    if (r.err) return send(res, 500, { error: 'MRP run failed: ' + String(r.errout || r.err.message).split('\n').filter(l => !/ExperimentalWarning|trace-warnings/.test(l)).join(' ').slice(0, 400) });
    let j = {}; try { j = JSON.parse(r.out); } catch {}
    glog('mrp_run', j.run && j.run.run_id);
    return send(res, 200, { ok: true, ...j });
  }

  // Purchase request → PO draft in Suppliers & POs (requester completes + submits; approval rules unchanged).
  if (fp === '/api/mrp/request/convert' && req.method === 'POST') {
    if (!canAct) return send(res, 403, { error: 'Only an admin or manager can turn a request into a PO draft.' });
    const body = await readBody(req);
    const erp = openErp(me);
    try {
      const pr = erp.getPurchaseRequest(body.id);
      if (!pr) return send(res, 404, { error: 'request not found' });
      if (pr.status !== 'open') return send(res, 409, { error: `Request is ${pr.status}.` });
      const vendorId = body.vendor_id || pr.vendor_id;
      const vendor = vendorId ? erp.getVendor(vendorId) : null;
      if (!vendor) return send(res, 400, { error: `No supplier on file matches "${pr.vendor}". Pick the supplier first.`, needs_vendor: true });
      const lines = (parse(pr.raw_json).lines || []).slice(0, 100).map((l, i) => ({
        line_no: i + 1, part_number: String(l.part_number || '').slice(0, 80), description: String(l.description || '').slice(0, 1000),
        qty: Number(l.qty) || 0, unit_price: Math.round((Number(l.unit_cost) || 0) * 10000) / 10000, account_id: '', account: '',
        amount: Math.round((Number(l.qty) || 0) * (Number(l.unit_cost) || 0) * 100) / 100,
      }));
      if (!lines.length) return send(res, 400, { error: 'Request has no lines.' });
      const yr = now().slice(0, 4);
      const n = erp.listPOs({ limit: 100000 }).filter(p => p.source === 'mc' && String(p.id).startsWith(`po-mc-${yr}-`)).length + 1;
      const id = `po-mc-${yr}-${String(n).padStart(3, '0')}`;
      const total = Math.round(lines.reduce((a, l) => a + l.amount, 0) * 100) / 100;
      erp.upsertPO({
        id, source: 'mc', status: 'draft', vendor_id: vendor.id, total, need_by: pr.need_by || null, charge_label: 'BLK3 S0 build',
        notes: `From MRP purchase request ${pr.id} (run ${pr.run_id}). Unit prices are planning estimates — confirm the quote, add QuickBooks accounts, and set flight-critical before submitting.`,
        terms: 'Net 30', requested_by: me, requested_by_name: s.name || me, mrp_request: pr.id,
        history: [{ at: now(), by: s.name || me, action: 'created', detail: `from MRP ${pr.id} · ${lines.length} line(s)` }],
      }, lines);
      erp.mrpUpsert('purchase_request', { id: pr.id, status: 'converted', po_id: id, vendor_id: vendor.id });
      glog('mrp_request_converted', `${pr.id} -> ${id}`);
      return send(res, 200, { ok: true, po_id: id, open: `suppliers.html#po=${encodeURIComponent(id)}` });
    } finally { erp.close(); }
  }

  if (fp === '/api/mrp/request/cancel' && req.method === 'POST') {
    if (!canAct) return send(res, 403, { error: 'Only an admin or manager can dismiss a request.' });
    const body = await readBody(req);
    const erp = openErp(me);
    try {
      const pr = erp.getPurchaseRequest(body.id);
      if (!pr || pr.status !== 'open') return send(res, 409, { error: 'Request is not open.' });
      const raw = parse(pr.raw_json);
      erp.mrpUpsert('purchase_request', { id: pr.id, status: 'cancelled', raw_json: { ...raw, cancelled: { by: s.name || me, at: now(), reason: String(body.reason || '').slice(0, 300) } } });
      glog('mrp_request_cancelled', pr.id);
      return send(res, 200, { ok: true });
    } finally { erp.close(); }
  }

  // Manual on-hand edit (Jon 10/3). Posts an audited physical count to the ERP ledger, records an override the
  // nightly sync honours until the inventory sources report a recount, and refreshes this line's net in place.
  // Purchase requests are NOT rewritten — re-run MRP to regenerate them.
  if (fp === '/api/mrp/onhand' && req.method === 'POST') {
    if (!canAct) return send(res, 403, { error: 'Only an admin or manager can edit on-hand quantities.' });
    const body = await readBody(req);
    const qty = Number(body.qty);
    if (!body.part_id || !Number.isFinite(qty) || qty < 0 || qty > 1e6) return send(res, 400, { error: 'Enter an on-hand quantity of 0 or more.' });
    const r3 = n => Math.round((Number(n) || 0) * 1000) / 1000;
    const reason = String(body.reason || '').slice(0, 300);
    const erp = openErp(me);
    try {
      const run = erp.latestMrpRun();
      const line = run && erp.listMrpLines(run.id).find(l => l.id === body.line_id && l.part_id === body.part_id);
      if (!line) return send(res, 404, { error: 'That line is not in the current MRP run. Reload the page.' });
      const at = now();
      erp.addInventoryTxn({ id: `cnt-mrp-${Date.now().toString(36)}`, part_id: line.part_id, kind: 'count', qty: r3(qty), location: null,
        source: `mrp manual count by ${s.name || me}${reason ? ' — ' + reason : ''}`, ref: line.id, occurred_at: at });
      const fs = require('fs');
      const OVR = path.join(WS, 'mission-control', 'data', 'mrp-onhand-overrides.json');
      let ovr = {}; try { ovr = JSON.parse(fs.readFileSync(OVR, 'utf8')); } catch {}
      ovr[line.part_id] = { qty: r3(qty), src_qty: null, by: s.name || me, at, reason, previous: line.on_hand };
      fs.writeFileSync(OVR + '.tmp', JSON.stringify(ovr, null, 1)); fs.renameSync(OVR + '.tmp', OVR);
      let { action, net } = line;
      if (action !== 'quantify') {
        net = Math.max(0, r3(Number(line.gross) - qty - (Number(line.on_order) || 0)));
        if (net === 0) action = 'none';
        else if (action === 'none') action = line.make_buy === 'make' ? 'make' : 'buy';
      }
      const upd = erp.mrpLineSetOnHand(line.id, { on_hand: r3(qty), net, ext_cost: Math.round(net * (Number(line.unit_cost) || 0) * 100) / 100, action });
      glog('mrp_onhand_edit', `${line.part_number || line.part_id}: ${line.on_hand} -> ${r3(qty)}${reason ? ' (' + reason + ')' : ''}`);
      return send(res, 200, { ok: true, line: { ...line, ...upd } });
    } finally { erp.close(); }
  }

  return send(res, 404, { error: 'unknown mrp route' });
}

module.exports = { handle };
