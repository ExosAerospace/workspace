// Supply Chain (ERP Phase 5): supplier master + Approved Supplier List, purchase orders, receiving inspection,
// supplier scorecards. Data lives in the audited ERP db (erp-foundation/mc.db) via the DAL — every write is an
// audit_log row. QuickBooks stays the books: an MC PO is pushed to QB as a (non-posting) PurchaseOrder only
// after it is approved; QB-entered POs and vendors sync in every 30 min (erp-foundation/qb_supply_sync.js).
//
// PO lifecycle: draft → pending_approval → issued (approved + in QB) → partially_received → received → closed
//               (or rejected / cancelled). Gates on submit:
//   • supplier DD status "failed" (human-confirmed exclusion/OFAC) → hard block
//   • flight-critical PO to a supplier not on the ASL (Approved/Conditional) → blocked unless an admin gives an
//     override reason (one-time buy; FAI + CoC still required) — the override forces Jon's approval
//   • Jon approves by Decision card when: total ≥ threshold, flight-critical, DD not cleared on a DEFENSE-contract PO
//     (Jon 2026-10-22: DD applies only to defense buys; contract customer USAF/AFRL/Navy/DARPA/... or raw defense:true), or an
//     ASL override. Otherwise any admin other than the requester approves in the page (segregation of duties).
// Flowdowns (FAR/DFARS + Exos quality clauses) are selected from the PO's flags, incorporated by reference.
'use strict';
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');

const MC_DIR = path.join(__dirname, '..');
const WS = path.join(MC_DIR, '..');
const DB = process.env.SUPPLY_DB || path.join(WS, 'erp-foundation', 'mc.db');   // env override = tests only
const CONFIG = process.env.SUPPLY_CONFIG || path.join(MC_DIR, 'data', 'supply-config.json');
const ACCTS = path.join(MC_DIR, 'data', 'qb-accounts-cache.json');
const DECISIONS = path.join(MC_DIR, 'data', 'decisions.json');
const TOKEN = path.join(MC_DIR, 'data', '.decisions-token');
const QB_SUPPLY = path.join(WS, 'scripts', 'qb_supply.py');
const PY = '/usr/bin/python3';
const ASL_OK = ['Approved', 'Conditional'];
const ASL_STATES = ['Not evaluated', 'Pending qualification', 'Approved', 'Conditional', 'Disapproved', 'Inactive'];

const send = (res, code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };
const now = () => new Date().toISOString();
const today = () => now().slice(0, 10);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const money = n => '$' + (Number(n) || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const parse = s => { try { return s ? JSON.parse(s) : {}; } catch { return {}; } };

function config() {
  try { return JSON.parse(fs.readFileSync(CONFIG, 'utf8')); } catch (e) { throw new Error('supply-config.json unreadable: ' + e.message); }
}
function openErp(actor, agent) {
  const { openErp: o } = require(path.join(WS, 'erp-foundation', 'dal'));
  return o(DB, { actor: actor || 'mc-server', agent: agent || 'mc-supply-chain' });
}
function readBody(req) {
  return new Promise((ok, bad) => { let b = ''; req.on('data', c => { b += c; if (b.length > 2e6) bad(new Error('body too large')); }); req.on('end', () => { try { ok(b ? JSON.parse(b) : {}); } catch (e) { bad(e); } }); });
}
function py(args, stdin) {
  return new Promise((ok, bad) => {
    const p = execFile(PY, [QB_SUPPLY, ...args], { timeout: 90000, maxBuffer: 8 * 1024 * 1024 }, (err, out) => {
      let j = {}; try { j = JSON.parse(out || '{}'); } catch {}
      if (err || j.error) return bad(new Error(j.error || String(err)));
      ok(j);
    });
    if (stdin !== undefined) { p.stdin.write(JSON.stringify(stdin)); p.stdin.end(); }
  });
}

// ── views ───────────────────────────────────────────────────────────────────
function vendorView(v, sc, cfg) {
  const r = parse(v.raw_json);
  const s = sc || {};
  const reviewDue = r.review_due || v.review_due || null;
  return {
    id: v.id, name: v.name, qb_id: v.qb_id, active: v.active !== 0, asl_status: v.asl_status || 'Not evaluated',
    category: v.category || r.category || '', country: v.country || '', flight_critical: !!v.flight_critical,
    scope: r.scope || '', qualification: r.qualification || '', certs: r.certs || [], cage: r.cage || '', uei: r.uei || '',
    email: r.email || '', phone: r.phone || '', notes: r.notes || '', source: r.source || '',
    dd_tier: v.dd_tier || null, dd_status: r.dd_status || null, dd_flags: r.dd_flags || [], cui_exposure: !!r.cui_exposure,
    review_due: reviewDue, review_overdue: !!(reviewDue && reviewDue < today() && ASL_OK.includes(v.asl_status)),
    asl_history: (r.asl_history || []).slice(-10),
    spend_12mo: Math.round(s.spend_12mo || 0), pos_12mo: s.pos_12mo || 0, last_po: s.last_po || null, receipts: s.receipts || 0,
    on_time_pct: s.dated_receipts ? Math.round(100 * s.on_time / s.dated_receipts) : null,
    quality_pct: s.qty_in ? Math.round(100 * s.qty_ok / s.qty_in) : null, rejects: s.rejects || 0,
  };
}
function flowdowns(po, cfg) {
  const f = { always: true, gov: !!po.contract_id, cui: !!po.cui, export: !!po.export_controlled, electronic: !!po.electronic_parts,
              metals: !!po.specialty_metals, flight_critical: !!po.flight_critical, over_10k: (Number(po.total) || 0) > 10000 };
  return (cfg.flowdowns || []).filter(c => (c.when || ['always']).some(w => f[w]) && (!c.and || c.and.every(w => f[w])));
}
function poView(po, cfg) {
  const r = parse(po.raw_json);
  const out = { ...r, ...po, raw_json: undefined, flight_critical: !!po.flight_critical };
  out.lines = (po.lines || []).map(l => ({ ...parse(l.raw_json), ...l, raw_json: undefined }));
  out.receipt_list = (po.receipt_list || []).map(x => ({ ...parse(x.raw_json), ...x, raw_json: undefined }));
  if (po.source === 'mc') out.flowdowns = flowdowns(out, cfg);
  return out;
}
const DEFENSE_RE = /\b(USAF|AFRL|Air Force|Army|Navy|ONR|NAVAIR|NAVSEA|DARPA|DoD|DoW|Department of (Defense|War)|Space Force|USSF|SSC|MDA|Missile Defense|DLA|AEDC|SOCOM|DTRA|DIU)\b/i;
function isDefenseContract(erp, contractId) {
  if (!contractId) return false;
  const c = (erp.listContracts() || []).find(x => x.id === contractId || x.number === contractId);
  if (!c) return false;
  const r = parse(c.raw_json);
  return r.defense === true || (r.defense !== false && DEFENSE_RE.test(`${c.customer || ''} ${c.title || ''}`));
}
function routeReasons(po, vendor, cfg) {
  const rs = [];
  const thr = Number(cfg.approval.jon_threshold) || 5000;
  if ((Number(po.total) || 0) >= thr) rs.push(`total ≥ ${money(thr)}`);
  if (po.flight_critical) rs.push('flight-critical');
  // Supplier DD applies only to defense-contract buys (Jon 2026-10-22); the Decision card raised here is the DD sign-off.
  if (po.defense && !vendor.dd_tier) rs.push('supplier not DD-screened (defense contract) — Exo screens before approval');
  else if (po.defense && vendor.dd_tier !== 'GREEN' && vendor.dd_status !== 'cleared') rs.push(`supplier DD ${vendor.dd_tier} not cleared (defense contract)`);
  if (po.asl_override) rs.push('ASL override');
  if (po.contract_id && cfg.approval.gov_funded_to_jon) rs.push('charged to a government contract');
  return rs;
}

// ── Decisions ───────────────────────────────────────────────────────────────
function fileDecision(body) {
  if (process.env.SUPPLY_NO_DECISIONS) return Promise.resolve({ id: 'D-TEST' });   // tests only
  return new Promise((ok, bad) => {
    const http = require('http');
    const tok = fs.readFileSync(TOKEN, 'utf8').trim();
    const data = JSON.stringify(body);
    const rq = http.request({ host: '127.0.0.1', port: 8080, path: '/api/decisions/ingest', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Exo-Token': tok, 'Content-Length': Buffer.byteLength(data) } }, rs => {
      let b = ''; rs.on('data', c => b += c); rs.on('end', () => { try { ok(JSON.parse(b)); } catch (e) { bad(e); } });
    });
    rq.on('error', bad); rq.end(data);
  });
}

// Approve → vendor in QB (create if missing) → push PO to QB → status issued.
async function finalizeApproval(poId, approverLabel, actor) {
  const cfg = config();
  let erp = openErp(actor, 'mc-supply-approve');
  let po, vendor;
  try {
    po = erp.getPO(poId);
    if (!po) throw new Error('PO not found');
    if (po.status !== 'pending_approval') return { skipped: true, status: po.status };
    vendor = erp.getVendor(po.vendor_id);
  } finally { erp.close(); }
  const vr = parse(vendor.raw_json);
  const r = parse(po.raw_json);
  let vendorQb = vendor.qb_id;
  const result = { qb: null };
  if (cfg.qb_push !== false) {
    if (!vendorQb) vendorQb = (await py(['create-vendor'], { name: vendor.name, email: vr.email, phone: vr.phone })).qb_id;
    const lines = po.lines.map(l => ({ ...parse(l.raw_json), ...l }));
    const pushed = await py(['push-po'], {
      vendor_qb_id: vendorQb, txn_date: today(), due_date: po.need_by || null,
      memo: `MC ${po.id}${po.need_by ? ' · need by ' + po.need_by : ''}${r.ship_to ? ' · ship to ' + r.ship_to : ''}`,
      private_note: `Issued from Mission Control ${po.id}; approved by ${approverLabel}. Requested by ${po.requested_by}.`,
      lines: lines.map(l => ({ description: [l.part_number, l.description].filter(Boolean).join(' — '), qty: l.qty, unit_price: l.unit_price, account_id: l.account_id })),
    });
    result.qb = pushed;
  }
  erp = openErp(actor, 'mc-supply-approve');
  try {
    if (vendorQb && !vendor.qb_id) erp.upsertVendor({ id: vendor.id, qb_id: String(vendorQb) });
    const hist = (r.history || []).concat([{ at: now(), by: approverLabel, action: 'approved', detail: result.qb ? `QB PO #${result.qb.doc_number}` : 'QB push off' }]);
    erp.upsertPO({ id: po.id, status: 'issued', approved_by: approverLabel, approved_at: now(), issued_at: today(),
                   qb_id: result.qb ? String(result.qb.qb_id) : null, po_number: result.qb ? result.qb.doc_number : po.id, history: hist });
  } finally { erp.close(); }
  return result;
}
function rejectPO(poId, who, reason, actor) {
  const erp = openErp(actor, 'mc-supply-approve');
  try {
    const po = erp.getPO(poId); if (!po || po.status !== 'pending_approval') return false;
    const r = parse(po.raw_json);
    erp.upsertPO({ id: po.id, status: 'rejected', history: (r.history || []).concat([{ at: now(), by: who, action: 'rejected', detail: reason || '' }]) });
    return true;
  } finally { erp.close(); }
}

// Called by server.js right after a human answers a decision (event-driven; no polling lag).
async function onDecision(d) {
  if (!d || !/^po-approve:/.test(d.dedupeKey || '')) return;
  const by = String(d.answeredBy || ''), email = String(d.answeredByEmail || '');
  if (!by && !email) return;
  const poId = d.dedupeKey.slice('po-approve:'.length);
  const ans = String(d.answer || '').toLowerCase();
  if (ans.startsWith('approve')) await finalizeApproval(poId, `${by || email} (${d.id})`, email || by);
  else if (ans.startsWith('reject')) rejectPO(poId, `${by || email} (${d.id})`, d.note || '', email || by);
}

// ── printable PO ────────────────────────────────────────────────────────────
function printHTML(po, cfg) {
  const co = cfg.company || {};
  // Entity cells never fall back to Exos letterhead/identifiers (Jon 2026-10-22).
  const isEx = !process.env.ENTITY || process.env.ENTITY === 'exos';
  const FB = isEx ? { name: 'Exos Aerospace Systems & Technologies, Inc.', address: '299 FM 1903, Greenville, TX 75402', cage: '7EMY6', uei: 'CK24BPZGF854' }
                  : { name: '(set company name in Suppliers > Settings)', address: '', cage: '—', uei: '—' };
  const lines = po.lines.map((l, i) => `<tr><td>${i + 1}</td><td>${esc(l.part_number || '')}</td><td>${esc(l.description)}</td><td class=r>${esc(l.qty)}</td><td class=r>${money(l.unit_price)}</td><td class=r>${money((l.qty || 0) * (l.unit_price || 0))}</td></tr>`).join('');
  const fd = (po.flowdowns || []).map(c => `<li><b>${esc(c.ref)}</b> — ${esc(c.title)}${c.note ? ` <i>(${esc(c.note)})</i>` : ''}</li>`).join('');
  const draft = po.status !== 'issued' && po.status !== 'partially_received' && po.status !== 'received' && po.status !== 'closed';
  return `<!doctype html><html><head><meta charset=utf-8><title>PO ${esc(po.po_number || po.id)}</title><style>
body{font:12px/1.4 -apple-system,Helvetica,Arial;color:#111;margin:32px;max-width:850px}h1{font-size:22px;margin:0}table{border-collapse:collapse;width:100%;margin:12px 0}
td,th{border:1px solid #bbb;padding:5px;text-align:left;vertical-align:top}th{background:#f1f3f6}.r{text-align:right}.hdr{display:flex;justify-content:space-between}
.wm{color:#c00;font-weight:700;font-size:16px}ol,ul{margin:4px 0 4px 18px;padding:0}.small{font-size:10.5px;color:#444}@media print{.noprint{display:none}}</style></head><body>
<div class=hdr><div><h1>${esc(co.name || FB.name)}</h1><div>${esc(co.address || FB.address)}</div><div>CAGE ${esc(co.cage || FB.cage)} · UEI ${esc(co.uei || FB.uei)}</div></div>
<div style="text-align:right"><h1>PURCHASE ORDER</h1><div style="font-size:16px"><b>${esc(po.po_number || po.id)}</b></div><div>Date: ${esc(po.issued_at || today())}</div>${draft ? '<div class=wm>DRAFT — NOT AN ORDER UNTIL APPROVED</div>' : ''}</div></div>
<table><tr><th style="width:50%">Supplier</th><th>Ship to</th></tr><tr><td>${esc(po.vendor_name)}${po.vendor_email ? '<br>' + esc(po.vendor_email) : ''}</td><td>${esc(po.ship_to || co.ship_to || co.address || FB.address)}<br>Attn: ${esc(po.requested_by_name || po.requested_by || '')}</td></tr></table>
<table><tr><th>Need-by date</th><th>Terms</th><th>Charge to</th><th>Flight-critical</th></tr><tr><td>${esc(po.need_by || '—')}</td><td>${esc(po.terms || cfg.default_terms || 'Net 30')}</td><td>${esc(po.charge_label || po.contract_id || po.project_id || 'Overhead')}</td><td>${po.flight_critical ? 'YES — quality clauses apply' : 'No'}</td></tr></table>
<table><tr><th>#</th><th>Part no.</th><th>Description</th><th class=r>Qty</th><th class=r>Unit</th><th class=r>Extended</th></tr>${lines}
<tr><td colspan=5 class=r><b>Total</b></td><td class=r><b>${money(po.total)}</b></td></tr></table>
${po.notes ? `<p><b>Notes:</b> ${esc(po.notes)}</p>` : ''}
<h3>Terms, conditions and flowdown requirements</h3>
<p class=small>This order is subject to Exos standard purchase order terms and conditions. The following clauses and requirements are incorporated by reference with the same force and effect as if given in full text (FAR/DFARS full text: acquisition.gov). Supplier shall flow applicable requirements to its sub-tier suppliers.</p>
<ul class=small>${fd}</ul>
<p class=small>Acceptance of this order, by acknowledgment or by performance, constitutes acceptance of these terms.</p>
<table style="margin-top:28px"><tr><td style="height:46px;width:50%">Authorized by Exos: ${esc(po.approved_by || '')}<br>${esc(po.approved_at ? po.approved_at.slice(0, 10) : '')}</td><td>Supplier acknowledgment (name / date):</td></tr></table>
<p class="noprint small"><button onclick="print()">Print / Save as PDF</button></p></body></html>`;
}

// ── handler ─────────────────────────────────────────────────────────────────
async function handle(req, res, ctx) {
  const u = new URL(req.url, 'http://x');
  const fp = u.pathname;
  const s = ctx.getSession(req);
  if (!s) return send(res, 401, { error: 'auth required' });
  if (['member', 'early_adopter'].includes(s.role)) return send(res, 403, { error: 'Supply chain is limited to Exos staff with purchasing access.' });
  const isAdmin = s.role === 'admin';
  const me = s.email || s.name || 'unknown';
  const label = s.name || s.email;
  const cfg = config();
  const glog = (a, d) => { try { ctx.glog('supply-chain', a, 'info', '', { by: me, detail: d }); } catch {} };

  if (fp === '/api/supply' && req.method === 'GET') {
    const erp = openErp(me);
    try {
      const since = new Date(Date.now() - 365 * 864e5).toISOString().slice(0, 10);
      const sc = new Map(erp.vendorScorecards(since).map(x => [x.vendor_id, x]));
      const vendors = erp.listVendors().map(v => vendorView(v, sc.get(v.id), cfg));
      const cutoff = new Date(Date.now() - 730 * 864e5).toISOString().slice(0, 10);
      const pos = erp.listPOs({ limit: 5000 }).filter(p => p.source === 'mc' || p.status !== 'closed' || (p.issued_at || '') >= cutoff);
      let accounts = []; try { accounts = JSON.parse(fs.readFileSync(ACCTS, 'utf8')).accounts; } catch {}
      return send(res, 200, { vendors, pos, accounts, projects: erp.listProjects(), asl_states: ASL_STATES,
        contracts: erp.listContracts(), wbs: erp.listWBS(), approval: cfg.approval, me: { email: s.email, name: s.name, admin: isAdmin } });
    } finally { erp.close(); }
  }

  if (fp === '/api/supply/po' && req.method === 'GET') {
    const erp = openErp(me);
    try { const po = erp.getPO(u.searchParams.get('id')); return po ? send(res, 200, poView(po, cfg)) : send(res, 404, { error: 'not found' }); }
    finally { erp.close(); }
  }

  if (fp === '/api/supply/po/print' && req.method === 'GET') {
    const erp = openErp(me);
    try {
      const raw = erp.getPO(u.searchParams.get('id'));
      if (!raw) return send(res, 404, { error: 'not found' });
      const po = poView(raw, cfg);
      const v = erp.getVendor(po.vendor_id); po.vendor_email = v ? parse(v.raw_json).email : '';
      if (po.source !== 'mc') po.flowdowns = [];
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); return res.end(printHTML(po, cfg));
    } finally { erp.close(); }
  }

  if (req.method !== 'POST') return send(res, 404, { error: 'unknown supply route' });
  const body = await readBody(req);

  // Supplier master / ASL edit (ASL status changes: admin only — Quality decision).
  if (fp === '/api/supply/vendor') {
    const erp = openErp(me);
    try {
      let v = body.id ? erp.getVendor(body.id) : null;
      if (!v) {
        if (!body.name) return send(res, 400, { error: 'name required' });
        const id = 'v-mc-' + String(body.name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
        if (erp.getVendor(id)) return send(res, 409, { error: 'supplier already exists' });
        erp.upsertVendor({ id, name: String(body.name).slice(0, 120), email: body.email || '', phone: body.phone || '', country: body.country || '',
                           asl_status: 'Not evaluated', source: 'mc', created_by: me });
        glog('vendor_created', id);
        v = erp.getVendor(id);
        if (!body.asl_status && !body.category) return send(res, 200, { ok: true, vendor: vendorView(v, null, cfg) });
      }
      const r = parse(v.raw_json);
      const upd = { id: v.id };
      for (const k of ['category', 'scope', 'qualification', 'cage', 'uei', 'email', 'phone', 'country', 'notes']) if (body[k] !== undefined) upd[k] = String(body[k]).slice(0, 2000);
      if (body.certs !== undefined) upd.certs = (Array.isArray(body.certs) ? body.certs : []).slice(0, 20).map(c => ({ name: String(c.name || '').slice(0, 80), number: String(c.number || '').slice(0, 80), expires: String(c.expires || '').slice(0, 10) }));
      if (body.flight_critical !== undefined) upd.flight_critical = !!body.flight_critical;
      if (body.asl_status !== undefined && body.asl_status !== v.asl_status) {
        if (!isAdmin) return send(res, 403, { error: 'Only Quality/admin can change ASL status.' });
        if (!ASL_STATES.includes(body.asl_status)) return send(res, 400, { error: 'bad ASL status' });
        if (ASL_OK.includes(body.asl_status) && !(body.qualification || r.qualification)) return send(res, 400, { error: 'Record the qualification basis (doc review / FAI / survey / heritage) before approving.' });
        if (ASL_OK.includes(body.asl_status) && r.dd_status === 'failed') return send(res, 409, { error: 'Supplier failed due diligence — cannot be placed on the ASL.' });
        upd.asl_status = body.asl_status;
        upd.asl_history = (r.asl_history || []).concat([{ at: now(), by: label, from: v.asl_status, to: body.asl_status, reason: String(body.reason || '').slice(0, 300) }]);
        if (ASL_OK.includes(body.asl_status)) {
          const d = new Date(); d.setMonth(d.getMonth() + (Number(cfg.asl_review_months) || 12));
          upd.review_due = body.review_due || d.toISOString().slice(0, 10);
        }
      } else if (body.review_due !== undefined) upd.review_due = String(body.review_due).slice(0, 10);
      erp.upsertVendor(upd);
      glog('vendor_updated', v.id + (upd.asl_status ? ' ASL→' + upd.asl_status : ''));
      return send(res, 200, { ok: true, vendor: vendorView(erp.getVendor(v.id), null, cfg) });
    } finally { erp.close(); }
  }

  // Create / edit a PO draft.
  if (fp === '/api/supply/po/save') {
    const erp = openErp(me);
    try {
      let po = body.id ? erp.getPO(body.id) : null;
      if (po && po.source !== 'mc') return send(res, 409, { error: 'QuickBooks-entered POs are read-only here.' });
      if (po && !['draft', 'rejected'].includes(po.status)) return send(res, 409, { error: `PO is ${po.status}; only drafts can be edited.` });
      if (po && po.requested_by !== me && !isAdmin) return send(res, 403, { error: 'Only the requester (or an admin) can edit this draft.' });
      const vendor = erp.getVendor(body.vendor_id);
      if (!vendor) return send(res, 400, { error: 'Pick a supplier.' });
      const lines = (body.lines || []).filter(l => l && (l.description || l.part_number)).slice(0, 100).map((l, i) => ({
        line_no: i + 1, part_number: String(l.part_number || '').slice(0, 80), description: String(l.description || '').slice(0, 1000),
        qty: Number(l.qty) || 0, unit_price: Math.round((Number(l.unit_price) || 0) * 10000) / 10000, account_id: String(l.account_id || ''),
        account: String(l.account || '').slice(0, 200), amount: Math.round((Number(l.qty) || 0) * (Number(l.unit_price) || 0) * 100) / 100,
      }));
      if (!lines.length) return send(res, 400, { error: 'Add at least one line.' });
      if (lines.some(l => !(l.qty > 0) || !(l.unit_price >= 0))) return send(res, 400, { error: 'Every line needs qty > 0 and a unit price.' });
      if (cfg.qb_push !== false && lines.some(l => !l.account_id)) return send(res, 400, { error: 'Every line needs a QuickBooks expense account.' });
      let id = po ? po.id : null;
      if (!id) {
        const yr = today().slice(0, 4);
        const n = erp.listPOs({ limit: 100000 }).filter(p => p.source === 'mc' && String(p.id).startsWith(`po-mc-${yr}-`)).length + 1;
        id = `po-mc-${yr}-${String(n).padStart(3, '0')}`;
      }
      const prev = po ? parse(po.raw_json) : {};
      const total = Math.round(lines.reduce((a, l) => a + l.amount, 0) * 100) / 100;
      const rec = {
        id, source: 'mc', status: 'draft', vendor_id: vendor.id, total, need_by: body.need_by || null, promised_date: body.promised_date || null,
        project_id: body.project_id || null, wbs_id: body.wbs_id || null, contract_id: body.contract_id || null,
        charge_label: body.charge_label || '', flight_critical: !!body.flight_critical, cui: !!body.cui, export_controlled: !!body.export_controlled,
        electronic_parts: !!body.electronic_parts, specialty_metals: !!body.specialty_metals, ship_to: String(body.ship_to || '').slice(0, 300),
        notes: String(body.notes || '').slice(0, 2000), terms: String(body.terms || cfg.default_terms || 'Net 30').slice(0, 40),
        requested_by: po ? po.requested_by : me, requested_by_name: po ? prev.requested_by_name : label, asl_override: null, decision_id: null,
        history: (prev.history || []).concat([{ at: now(), by: label, action: po ? 'edited' : 'created', detail: `${lines.length} line(s) · ${money(total)}` }]),
      };
      erp.upsertPO(rec, lines);
      glog('po_saved', id);
      return send(res, 200, { ok: true, po: poView(erp.getPO(id), cfg) });
    } finally { erp.close(); }
  }

  // Submit for approval: gates + routing.
  if (fp === '/api/supply/po/submit') {
    const erp = openErp(me);
    let po, vendor, reasons, decision = null;
    try {
      po = erp.getPO(body.id);
      if (!po || po.source !== 'mc') return send(res, 404, { error: 'not found' });
      if (!['draft', 'rejected'].includes(po.status)) return send(res, 409, { error: `PO is ${po.status}` });
      vendor = vendorView(erp.getVendor(po.vendor_id), null, cfg);
      const r = parse(po.raw_json);
      if (vendor.dd_status === 'failed') return send(res, 409, { error: `${vendor.name} failed supplier due diligence — no POs. (${(vendor.dd_flags || []).join('; ')})` });
      let override = null;
      if (po.flight_critical && !ASL_OK.includes(vendor.asl_status)) {
        if (!body.asl_override_reason) return send(res, 409, { error: `${vendor.name} is not on the Approved Supplier List (status: ${vendor.asl_status}). Flight-critical buys need an ASL supplier — qualify them first, or an admin can give a one-time override reason.`, needs_override: true });
        if (!isAdmin) return send(res, 403, { error: 'Only an admin can override the ASL gate.' });
        override = { by: label, at: now(), reason: String(body.asl_override_reason).slice(0, 500) };
      }
      const view = { ...r, ...po, asl_override: override, defense: isDefenseContract(erp, po.contract_id) };
      reasons = routeReasons(view, vendor, cfg);
      const hist = (r.history || []).concat([{ at: now(), by: label, action: 'submitted', detail: reasons.length ? 'to Jon: ' + reasons.join(', ') : 'admin approval' }]);
      erp.upsertPO({ id: po.id, status: 'pending_approval', asl_override: override, approval_route: reasons.length ? 'jon' : 'admin', route_reasons: reasons, history: hist });
      po = erp.getPO(po.id);
    } finally { erp.close(); }
    if (reasons.length) {
      const pv = poView(po, cfg);
      const base = cfg.public_base || 'https://mc.exosaero.space';
      const ctxt = [
        `Supplier: ${vendor.name} — ASL: ${vendor.asl_status}; DD: ${vendor.dd_tier || 'not screened'}${vendor.dd_status ? ' (' + vendor.dd_status + ')' : ''}${(vendor.dd_flags || []).length ? ' — ' + vendor.dd_flags.join('; ') : ''}`,
        `Requested by: ${pv.requested_by_name || pv.requested_by} · Need by: ${pv.need_by || '—'} · Charge to: ${pv.charge_label || pv.contract_id || pv.project_id || 'Overhead'}`,
        `Lines: ` + pv.lines.map(l => `${l.qty} × ${l.part_number ? l.part_number + ' ' : ''}${l.description} @ ${money(l.unit_price)}`).join(' | '),
        `Why this needs you: ${reasons.join(', ')}${pv.asl_override ? ` — override reason: "${pv.asl_override.reason}"` : ''}`,
        `Flowdowns attached: ${pv.flowdowns.map(c => c.ref).join(', ')}`,
        `PO preview: ${base}/api/supply/po/print?id=${encodeURIComponent(po.id)}`,
        `On Approve: the PO is created in QuickBooks (non-posting, next PO #) and marked issued; the requester sends the PO PDF to the supplier.`,
      ].join('\n');
      try {
        decision = await fileDecision({ source: 'Supply Chain (exo3)', title: `EXO3: Approve PO — ${vendor.name} ${money(po.total)}`,
          question: `Approve purchase order ${po.id} to ${vendor.name} for ${money(po.total)}?`, context: ctxt,
          proposedAction: 'Approve — PO goes into QuickBooks and is issued to the supplier.', type: 'choice', options: ['Approve', 'Reject'],
          priority: po.flight_critical ? 'high' : 'med', relatedItem: po.id, dedupeKey: `po-approve:${po.id}`,
          approver: cfg.approval.jon_email, assignedTo: cfg.approval.jon_email, agentClass: 'supply-chain' });
        const erp2 = openErp(me); try { erp2.upsertPO({ id: po.id, decision_id: decision.id }); } finally { erp2.close(); }
      } catch (e) { glog('decision_file_failed', po.id + ' ' + e.message); }
    }
    glog('po_submitted', po.id);
    const erp3 = openErp(me); try { return send(res, 200, { ok: true, routed_to: reasons.length ? 'Jon (Decision ' + (decision && decision.id || 'pending') + ')' : 'any admin except the requester', po: poView(erp3.getPO(po.id), cfg) }); } finally { erp3.close(); }
  }

  // In-page approval (admin route), or Jon approving directly.
  if (fp === '/api/supply/po/approve') {
    if (!isAdmin) return send(res, 403, { error: 'Only an admin can approve POs.' });
    const erp = openErp(me);
    let po;
    try { po = erp.getPO(body.id); } finally { erp.close(); }
    if (!po || po.status !== 'pending_approval') return send(res, 409, { error: 'PO is not awaiting approval.' });
    const r = parse(po.raw_json);
    const isJon = String(s.email || '').toLowerCase() === String(cfg.approval.jon_email).toLowerCase();
    if (po.requested_by === me && !isJon) return send(res, 403, { error: 'You can\'t approve your own PO — another admin has to.' });
    if (r.approval_route === 'jon' && !isJon) return send(res, 403, { error: `This PO needs Jon's approval (${(r.route_reasons || []).join(', ')}). It's on his Decisions board.` });
    if (body.decision === 'reject') { rejectPO(po.id, label, body.reason, me); glog('po_rejected', po.id); return send(res, 200, { ok: true }); }
    try {
      const out = await finalizeApproval(po.id, label, me);
      glog('po_approved', po.id);
      const erp2 = openErp(me); try { return send(res, 200, { ok: true, ...out, po: poView(erp2.getPO(po.id), cfg) }); } finally { erp2.close(); }
    } catch (e) { return send(res, 502, { error: 'Approved, but the QuickBooks push failed: ' + e.message + ' — the PO is still pending; try again.' }); }
  }

  if (fp === '/api/supply/po/cancel') {
    const erp = openErp(me);
    try {
      const po = erp.getPO(body.id);
      if (!po || po.source !== 'mc') return send(res, 404, { error: 'not found' });
      if (['received', 'closed', 'cancelled'].includes(po.status)) return send(res, 409, { error: `PO is ${po.status}` });
      if (po.status === 'issued' || po.status === 'partially_received') { if (!isAdmin) return send(res, 403, { error: 'Only an admin can cancel an issued PO.' }); }
      else if (po.requested_by !== me && !isAdmin) return send(res, 403, { error: 'Only the requester or an admin can cancel.' });
      const r = parse(po.raw_json);
      let qbNote = '';
      if (po.qb_id) {
        try { await py(['close-po'], { qb_id: po.qb_id }); qbNote = ` — QB PO #${po.po_number} closed`; }
        catch (e) { qbNote = ` — QB PO #${po.po_number} could NOT be closed (${e.message.slice(0, 120)}); close it in QB`; }
      }
      erp.upsertPO({ id: po.id, status: 'cancelled', history: (r.history || []).concat([{ at: now(), by: label, action: 'cancelled', detail: String(body.reason || '').slice(0, 300) + qbNote }]) });
      glog('po_cancelled', po.id);
      return send(res, 200, { ok: true, note: 'Cancelled' + qbNote + '.' });
    } finally { erp.close(); }
  }

  // Receive + receiving inspection (any PO — MC or QB). Rejects auto-open an NCR (Production → Quality).
  if (fp === '/api/supply/receive') {
    const erp = openErp(me);
    try {
      const po = erp.getPO(body.po_id);
      if (!po) return send(res, 404, { error: 'PO not found' });
      if (['draft', 'pending_approval', 'rejected', 'cancelled'].includes(po.status)) return send(res, 409, { error: `Can't receive against a ${po.status} PO.` });
      const rows = (body.lines || []).filter(l => Number(l.qty_received) > 0);
      if (!rows.length) return send(res, 400, { error: 'Enter a received quantity on at least one line.' });
      const r = parse(po.raw_json);
      if (po.flight_critical && !body.coc_received && !body.coc_waiver) return send(res, 400, { error: 'Flight-critical PO: Certificate of Conformance is required (or record why it is waived).' });
      const at = body.received_at || now();
      const made = [];
      let ncrId = null;
      const rejected = rows.filter(l => Number(l.qty_rejected) > 0);
      if (rejected.length) {
        const yr = today().slice(0, 4);
        const n = erp.listNCRs().filter(x => String(x.id).startsWith(`ncr-${yr}-`)).length + 1;
        ncrId = `ncr-${yr}-${String(n).padStart(3, '0')}`;
        erp.upsertNCR({ id: ncrId, ncr_number: `RI-${yr}-${String(n).padStart(3, '0')}`, kind: 'NCR', status: 'open', disposition: null,
          description: `Receiving inspection reject — ${po.vendor_name || ''} PO ${po.po_number || po.id}: ` + rejected.map(l => {
            const pl = po.lines.find(x => x.id === l.po_line_id) || {}; return `${l.qty_rejected} × ${pl.description || 'item'} (${l.reason || 'no reason given'})`; }).join('; '),
          po_id: po.id, vendor_id: po.vendor_id, opened_by: label });
      }
      rows.forEach((l, i) => {
        const pl = po.lines.find(x => x.id === l.po_line_id);
        const qr = Number(l.qty_received) || 0, qj = Math.min(qr, Number(l.qty_rejected) || 0);
        const rec = erp.addReceipt({ id: `rcv-${Date.now().toString(36)}-${i}`, po_id: po.id, po_line_id: pl ? pl.id : null, received_at: at,
          qty_received: qr, qty_accepted: qr - qj, qty_rejected: qj, result: qj ? (qj === qr ? 'reject' : 'partial') : 'accept',
          coc_received: !!body.coc_received, coc_waiver: body.coc_waiver || '', received_by: label, ncr_id: qj ? ncrId : null,
          packing_slip: String(body.packing_slip || '').slice(0, 80), reason: String(l.reason || '').slice(0, 300), notes: String(body.notes || '').slice(0, 1000),
          description: pl ? pl.description : '' });
        made.push(rec.id);
      });
      const fresh = erp.getPO(po.id);
      const allIn = fresh.lines.length && fresh.lines.every(l => (Number(l.qty_received) || 0) >= (Number(l.qty) || 0));
      const status = po.status === 'closed' ? 'closed' : (allIn ? 'received' : 'partially_received');
      erp.upsertPO({ id: po.id, status, history: (r.history || []).concat([{ at: now(), by: label, action: 'received', detail: `${made.length} line(s)${ncrId ? ' · NCR ' + ncrId : ''}` }]) });
      glog('po_received', po.id + (ncrId ? ' ncr ' + ncrId : ''));
      return send(res, 200, { ok: true, receipts: made, ncr: ncrId, status });
    } finally { erp.close(); }
  }

  return send(res, 404, { error: 'unknown supply route' });
}

module.exports = { handle, onDecision, flowdowns };
