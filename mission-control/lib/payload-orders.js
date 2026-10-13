// Payload order-to-cash — one tracked path from questionnaire to final payment for every BLK3 payload.
// Jon 2026-10-01: "Kordel France is ready to sign and pay ... no clear process direction or status."
//
// Stages (computed, never hand-set):
//   1 Questionnaire → 2 Export screen → 3 LSA ready → 4 Out for signature → 5 Executed
//   → 6 M1 invoiced → 7 Slot reserved (M1 paid) → 8 M2 (L-120) → 9 M3 (post-flight data) → Closed
// Money: standard terms (Addendum A, Jon 9/9 delegation) = 50% at reservation / 40% at L-120 / 10% at
// post-flight data. The signed LSA governs — contract_value can be set to the LSA figure.
//
// EXPORT CONTROL (Jon 2026-10-01): ITAR/EAR payloads are the off-normal case. MC never holds the
// controlled data. For a controlled order MC stores ONLY: the jurisdiction + classification number,
// the SharePoint (GCC High) storage path, the trained handler, and the SEC-CUI-STOR confirmation.
//   - Trained handler = signed BOTH the CUI Policies (sec-cui) and CUI NDA (sec-cui-nda) in Required Reading.
//   - Controlled orders: notes are disabled, nothing but the commercial LSA can be uploaded, and the
//     LSA text is run through scripts/itar_ear_screen.py before it can be sent.
//   - Every order: export screen + CSL denied-party screen must be done before the LSA goes out or
//     any invoice is recorded.
//
// FAA CROSS-WAIVER (Jon 2026-10-08): every executed order also needs the customer's WET-SIGNED reciprocal
// waiver of claims (14 CFR 440.17) physically at Exos by L-90 (90 days before the scheduled launch), so Exos can
// submit all waivers to the FAA for payload approval. Tracked as a required gate parallel to the money stages:
// shown in next_action from execution onward, overdue after L-90, and the order cannot close without it.
// HYBRID STEP (Jon 2026-10-11): Exo can't see paper, so a HUMAN confirms the wet-signed original is physically on
// file. Exo files a Decision (dedupeKey payload-waiver:<id>) once the order is executed or within L-150; the human
// click (server.js -> onDecision) records waiver_wet_signed_at + waiver_confirmed_by. 'Not yet' re-prompts in 14 days.
// Store: data/payload-orders.json (MC is the system of record for this; no generator touches it).
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const { promisify } = require('util');
const execFileP = promisify(execFile);

const MC_DIR = path.join(__dirname, '..');
const WS = path.join(MC_DIR, '..');
const STORE = path.join(MC_DIR, 'data', 'payload-orders.json');
const RR_FILE = path.join(MC_DIR, 'data', 'required-reading.json');
const LSA_DIR = path.join(MC_DIR, 'uploads', 'payload-orders');
const DOCX2HTML = path.join(WS, 'scripts', 'docx2html.py');
// Customer copy = Exos letterhead + the LSA's own page layout (Jon 2026-10-01). The e-sign envelope shows these
// page images, never the re-flowed mammoth HTML (that is only used for the export screen's text).
const LSA_RENDER = path.join(WS, 'scripts', 'lsa_esign_render.py');
async function renderLsa(docxAbs) {
  const { stdout } = await execFileP(PY, [LSA_RENDER, docxAbs], { timeout: 300000 });
  return JSON.parse(String(stdout).trim().split('\n').pop());
}
const ITAR_SCREEN = path.join(WS, 'scripts', 'itar_ear_screen.py');
const CSL_SCREEN = path.join(WS, 'scripts', 'csl_screen.py');
const PAYLOAD_CUSTOMER = path.join(WS, 'scripts', 'payload_customer.py');
const PY = '/usr/bin/python3';

const MISSIONS_FILE = path.join(MC_DIR, 'data', 'missions.json');
// Mission numbers (M5, M6, ...): Jon 2026-10-01 — every payload order, invoice and payload-customer record carries one.
function missions() { try { return JSON.parse(fs.readFileSync(MISSIONS_FILE, 'utf8')).missions || []; } catch { return []; } }
function missionLabel(id) { const m = missions().find(x => x.id === id); return m ? m.label : (id || ''); }
const RATE_PER_KG = 7500;          // published rate card
const INTEGRATION_FEE = 500;       // flat, standard terms
const TRAINING_DOCS = ['sec-cui', 'sec-cui-nda'];
const PROCEDURE = 'SEC-CUI-STOR';
const MILESTONES = [
  { key: 'M1', pct: 50, trigger: 'At slot reservation (LSA executed)' },
  { key: 'M2', pct: 40, trigger: 'L-120 days before flight' },
  { key: 'M3', pct: 10, trigger: 'Post-flight data delivered to customer' },
];
// IN-KIND PAYMENT (Jon 2026-10-11): a customer may pay with goods/services instead of cash. The in-kind value is
// defined to match the standard price (rate card + integration fee, e.g. $7,500 + $500 = $8,000), and a single $1
// documentation invoice (milestone INK) replaces M1/M2/M3, so every payload keeps the same QB invoice trail.
// The order completes when the $1 is paid AND a person records the in-kind consideration received.
const INK = { key: 'INK', pct: null, trigger: '$1 documentation invoice for an in-kind payment (at LSA execution)' };
const EXPORT_STATUSES = ['unscreened', 'not_controlled', 'ear', 'itar'];
const CONTROLLED = s => s === 'ear' || s === 'itar';

// ── store ──
function load() {
  try { const d = JSON.parse(fs.readFileSync(STORE, 'utf8')); return { seq: d.seq || 0, orders: d.orders || [] }; }
  catch { return { seq: 0, orders: [] }; }
}
function save(d) {
  const tmp = STORE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(d, null, 1));
  fs.renameSync(tmp, STORE);
}
const now = () => new Date().toISOString();
const who = s => (s && (s.name || s.email)) || 'MC user';
function log(o, s, action, detail) {
  (o.history = o.history || []).push({ at: now(), by: who(s), email: s && s.email, action, detail: detail || '' });
}
// exo3 telemetry (same schema as scripts/fleet_log.py) for the governed steps: waiver confirm, in-kind, outside LSA.
const FLEET_LOG = path.join(MC_DIR, '..', 'logs', 'fleet-events.jsonl');
function fleet(action, detail, kind = 'govern') {
  if (process.env.PAYLOAD_NO_DECISIONS) return;   // selftest
  try {
    fs.appendFileSync(FLEET_LOG, JSON.stringify({ ts: new Date().toISOString(), corr: Math.random().toString(16).slice(2, 18),
      agent: 'payload-orders-exo3', kind, action, owner: 'John Quinn', outcome: null, level: 'info', detail: detail || {} }) + '\n');
  } catch {}
}

// ── trained handlers: signed both CUI docs in Required Reading (current version) ──
function trainedHandlers() {
  let rr; try { rr = JSON.parse(fs.readFileSync(RR_FILE, 'utf8')); } catch { return []; }
  const cur = {}; for (const d of rr.docs || []) cur[d.id] = d.version;
  const per = {};
  for (const c of rr.completions || []) {
    if (!TRAINING_DOCS.includes(c.doc_id) || !c.valid || !c.acknowledged_at) continue;
    if (cur[c.doc_id] && c.doc_version && c.doc_version !== cur[c.doc_id]) continue;
    const e = (c.user_email || '').toLowerCase();
    (per[e] = per[e] || { email: e, name: c.user_name, docs: {} }).docs[c.doc_id] = c.acknowledged_at;
  }
  return Object.values(per).filter(p => TRAINING_DOCS.every(d => p.docs[d]))
    .map(p => ({ email: p.email, name: p.name, trained: p.docs }));
}

// ── SharePoint path: GCC High (*.sharepoint.us) URL, or a library path inside the exosaero tenant ──
function validSharePoint(p) {
  p = String(p || '').trim();
  if (!p || p.length > 600) return 'Enter the SharePoint location (max 600 characters).';
  if (/^https?:\/\//i.test(p)) {
    let u; try { u = new URL(p); } catch { return 'Not a valid URL.'; }
    if (u.protocol !== 'https:') return 'SharePoint link must be https.';
    if (/\.sharepoint\.com$/i.test(u.hostname)) return 'That is commercial SharePoint (.sharepoint.com). Controlled data must be in GCC High (.sharepoint.us).';
    if (!/\.sharepoint\.us$/i.test(u.hostname)) return 'Link must be on Exos GCC High SharePoint (*.sharepoint.us).';
    return null;
  }
  if (/^exosaero\s*[\\/]/i.test(p)) return null;  // e.g. "exosaero \ Exos US-Payloads \ Scentience"
  return 'Use the GCC High SharePoint link (https://…sharepoint.us/…) or the library path starting "exosaero \\ …".';
}

// ── screens (async; never block the event loop) ──
async function itarScreen(text) {
  try {
    const p = execFile(PY, [ITAR_SCREEN], { timeout: 30000, maxBuffer: 4 << 20 }, () => {});
    const out = await new Promise((resolve, reject) => {
      let buf = ''; p.stdout.on('data', c => buf += c); p.on('close', () => resolve(buf)); p.on('error', reject);
      p.stdin.end(String(text || ''));
    });
    const s = out.trim();
    return (!s || s === '[]') ? [] : [s.slice(0, 400)];
  } catch (e) { return ['export screen could not run (' + e.message + ') — treated as a hold']; }
}
async function cslScreen(name) {
  if (!name) return null;
  try {
    const { stdout } = await execFileP(PY, [CSL_SCREEN, '--name', name], { timeout: 120000, maxBuffer: 4 << 20 });
    const s = stdout.trim();
    return { name, clear: s.startsWith('🟢'), result: s.slice(0, 500), at: now() };
  } catch (e) { return { name, clear: false, result: 'screen failed: ' + e.message, at: now() }; }
}

// ── money + stage ──
function contractValue(o) {
  if (o.contract_value != null && o.contract_value !== '') return Number(o.contract_value);
  const kg = Number(o.mass_kg || 0);
  return kg ? Math.round(kg * RATE_PER_KG + INTEGRATION_FEE) : null;
}
function addDays(d, n) { const t = Date.parse(d); return isNaN(t) ? null : new Date(t + n * 864e5).toISOString().slice(0, 10); }

function view(o, envelopes) {
  const cv = contractValue(o);
  const env = o.envelope_id ? (envelopes || []).find(e => e.id === o.envelope_id) : null;
  const envStatus = env ? env.status : null;
  const executed = !!(o.lsa_signed_at || envStatus === 'completed');
  const ik = o.in_kind || null;
  const ms = ik ? [{ ...INK, amount: 1, ...((o.milestones || {}).INK || {}) }] : MILESTONES.map(m => {
    const r = (o.milestones || {})[m.key] || {};
    return { ...m, amount: cv != null ? Math.round(cv * m.pct / 100) : null, ...r };
  });
  if (o.flight_date && !ik) ms[1].due = addDays(o.flight_date, -120);
  const x = o.export || { status: 'unscreened' };
  const cslOk = (o.csl || []).length > 0 && (o.csl || []).every(c => c.clear || c.cleared_by);
  const exportOk = x.status === 'not_controlled' || (CONTROLLED(x.status) && x.sharepoint_path && x.handler_email && x.procedure_ack);
  const screened = exportOk && cslOk;
  let stage, next;
  if (o.closed) { stage = 10; next = 'Closed'; }
  else if (!o.questionnaire_received) { stage = 1; next = 'Get the payload questionnaire (Addendum D) back from the customer'; }
  else if (!screened) { stage = 2; next = !cslOk ? 'Run / clear the denied-party (CSL) screen' : 'Complete the export screen (jurisdiction + SharePoint path if controlled)'; }
  else if (!executed && !o.lsa_file && !o.lsa_sent_outside_at) { stage = 3; next = 'Upload the LSA (Word) for this customer'; }
  else if (!executed && !envStatus && !o.lsa_sent_outside_at) { stage = 3; next = 'Send the LSA for e-signature'; }
  else if (!executed) { stage = 4; next = 'Waiting on customer signature, then John countersigns'; }
  else if (ik && !ms[0].invoiced_at) { stage = 5; next = 'Issue the $1 in-kind documentation invoice'; }
  else if (ik && !ms[0].paid_at) { stage = 6; next = 'Collect the $1 documentation payment'; }
  else if (ik && !ik.received_at) { stage = 8; next = `Record the in-kind payment received (${ik.description || 'goods'}, value $${Number(ik.value || cv || 0).toLocaleString()})`; }
  else if (ik) { stage = 9; next = 'In-kind payment received + $1 documented — close the order'; }
  else if (!ms[0].invoiced_at) { stage = 5; next = 'Issue the M1 invoice (50%)'; }
  else if (!ms[0].paid_at) { stage = 6; next = 'Collect M1 payment'; }
  else if (!ms[1].paid_at) { stage = 7; next = ms[1].invoiced_at ? 'Collect M2 payment (40%)' : 'Invoice M2 (40%) at L-120' + (ms[1].due ? ' — ' + ms[1].due : ''); }
  else if (!ms[2].paid_at) { stage = 8; next = ms[2].invoiced_at ? 'Collect M3 payment (10%)' : 'Invoice M3 (10%) after post-flight data delivery'; }
  else { stage = 9; next = 'All payments received — close the order'; }
  const today = new Date().toISOString().slice(0, 10);
  // FAA cross-waiver gate (parallel to the money stages once the LSA is executed)
  const waiverDue = o.flight_date ? addDays(o.flight_date, -90) : null;
  const waiverOk = !!(o.waiver_wet_signed_at && o.waiver_faa_submitted_at);
  if (executed && !o.closed && !waiverOk) {
    next += ' · ' + (!o.waiver_wet_signed_at
      ? `Get the customer's WET-SIGNED cross-waiver of claims at Exos${waiverDue ? ' by ' + waiverDue + ' (L-90)' : ' (L-90; set the flight date)'}`
      : 'Submit the waiver package to the FAA for payload approval');
  }
  const waiverOverdue = executed && !o.closed && !o.waiver_wet_signed_at && waiverDue && waiverDue <= today;
  const overdue = waiverOverdue || (o.next_due && o.next_due < today) || (!ik && stage === 7 && !ms[1].invoiced_at && ms[1].due && ms[1].due <= today);
  const received = ms.reduce((a, m) => a + (Number(m.amount_received) || 0), 0);
  return {
    ...o, flight: o.mission ? missionLabel(o.mission) : o.flight, contract_value_effective: cv, milestones_view: ms, stage, next_action: next, overdue: !!overdue,
    controlled: CONTROLLED(x.status), export_ok: !!exportOk, csl_ok: cslOk, screened: !!screened,
    executed, envelope_status: envStatus, amount_received_total: received,
    waiver_due: waiverDue, waiver_ok: waiverOk, waiver_overdue: !!waiverOverdue,
  };
}

// ── field rules ──
const EDITABLE = ['customer', 'contact_name', 'contact_email', 'contact_phone', 'billing_address', 'payload_name', 'mission', 'flight', 'flight_date', 'mass_kg',
  'contract_value', 'owner', 'task_ids', 'opp_id', 'questionnaire_received', 'next_due', 'notes',
  'waiver_wet_signed_at', 'waiver_faa_submitted_at', 'waiver_confirmed_by', 'waiver_original_location'];
function clean(fields, o) {
  const out = {};
  for (const k of EDITABLE) if (k in fields) out[k] = fields[k];
  if ('mass_kg' in out) out.mass_kg = out.mass_kg === '' ? null : Number(out.mass_kg);
  if ('contract_value' in out) out.contract_value = (out.contract_value === '' || out.contract_value == null) ? null : Number(out.contract_value);
  if ('questionnaire_received' in out) out.questionnaire_received = !!out.questionnaire_received;
  if ('payload_name' in out) out.payload_name = String(out.payload_name || '').slice(0, 80);
  // phone + billing address come from the website questionnaire (scripts/payload_questionnaire.py); qb_invoice.py
  // needs both on every invoice (#3418). Address format: 'street; city, ST zip'.
  for (const k of ['contact_phone', 'billing_address']) if (k in out) out[k] = String(out[k] || '').trim().slice(0, 200) || null;
  if ('mission' in out) { out.mission = String(out.mission || '').trim().toUpperCase(); if (out.mission && !missions().some(m => m.id === out.mission)) return { error: 'Unknown mission ' + out.mission + ' (add it to data/missions.json first).' }; if (out.mission) out.flight = missionLabel(out.mission); }
  if (o && CONTROLLED((o.export || {}).status) && 'notes' in out && String(out.notes || '').trim() && out.notes !== o.notes) {
    return { error: 'Notes are disabled on a controlled (ITAR/EAR) payload. Keep technical detail in the SharePoint location only.' };
  }
  return { out };
}

function send(res, code, obj) { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); }
function readBody(req, limit) {
  return new Promise((resolve, reject) => {
    let b = '', n = 0;
    req.on('data', c => { n += c.length; if (n > limit) { reject(new Error('too large')); req.destroy(); } else b += c; });
    req.on('end', () => { try { resolve(b ? JSON.parse(b) : {}); } catch (e) { reject(e); } });
  });
}

// ctx: { getSession, loadEnvelopes, createEnvelope(req, {title, html, subject, message, signers}), glog }
async function handle(req, res, ctx) {
  const fp = req.url.split('?')[0];
  const s = ctx.getSession(req);
  if (!s) return send(res, 401, { error: 'Unauthorized' });
  if (!['admin', 'manager'].includes(s.role)) return send(res, 403, { error: 'Payload orders are limited to admins and managers.' });
  const isAdmin = s.role === 'admin';
  const me = (s.email || '').toLowerCase();

  if (fp === '/api/payload-orders' && req.method === 'GET') {
    const d = load(); const envs = ctx.loadEnvelopes();
    return send(res, 200, { orders: d.orders.map(o => view(o, envs)), handlers: trainedHandlers(), missions: missions(),
      terms: { rate_per_kg: RATE_PER_KG, integration_fee: INTEGRATION_FEE, milestones: MILESTONES, procedure: PROCEDURE, training_docs: TRAINING_DOCS } });
  }
  if (req.method !== 'POST') return send(res, 404, { error: 'Not found' });

  let body; try { body = await readBody(req, fp.endsWith('/lsa-upload') ? 36 << 20 : 1 << 20); }
  catch (e) { return send(res, 400, { error: 'Bad request: ' + e.message }); }
  const d = load();
  const o = body.id ? d.orders.find(x => x.id === body.id) : null;
  if (fp !== '/api/payload-orders/save' && !o) return send(res, 404, { error: 'Order not found' });
  const audit = (action, detail) => { try { ctx.glog('payload-orders', action, 'info', o ? o.id : '', { by: me, detail }); } catch {} };

  // create / update
  if (fp === '/api/payload-orders/save') {
    const r = clean(body.fields || {}, o);
    if (r.error) return send(res, 422, { error: r.error });
    const textToScreen = [r.out.payload_name, r.out.notes].filter(Boolean).join('\n');
    if (textToScreen) {
      const hits = await itarScreen(textToScreen);
      if (hits.length) return send(res, 422, { error: 'Blocked: this text looks like export-controlled technical data. Keep it in SharePoint, not MC. (' + hits[0] + ')' });
    }
    let rec = o;
    if (!rec) {
      if (!r.out.customer) return send(res, 400, { error: 'Customer is required' });
      d.seq += 1;
      rec = { id: 'PO2C-' + new Date().getFullYear() + '-' + String(d.seq).padStart(3, '0'), created_at: now(), created_by: who(s),
        export: { status: 'unscreened' }, milestones: {}, csl: [], history: [] };
      d.orders.push(rec);
      log(rec, s, 'created', r.out.customer);
    }
    const changed = Object.keys(r.out).filter(k => JSON.stringify(rec[k]) !== JSON.stringify(r.out[k]));
    Object.assign(rec, r.out); rec.updated_at = now();
    if (changed.length && o) log(rec, s, 'updated', changed.join(', '));
    save(d); audit('save', changed.join(','));
    return send(res, 200, { ok: true, order: view(rec, ctx.loadEnvelopes()) });
  }

  // denied-party screen: customer company + contact
  if (fp === '/api/payload-orders/csl') {
    if (body.clear_index != null) {   // human clears a name-collision hit (admin only, needs a reason)
      if (!isAdmin) return send(res, 403, { error: 'Only an admin can clear a CSL hit.' });
      const c = (o.csl || [])[Number(body.clear_index)];
      if (!c || !String(body.reason || '').trim()) return send(res, 400, { error: 'Give a reason for clearing.' });
      c.cleared_by = who(s); c.cleared_at = now(); c.clear_reason = String(body.reason).slice(0, 300);
      log(o, s, 'csl cleared', c.name + ': ' + c.clear_reason);
    } else {
      const names = [o.customer, o.contact_name].filter(Boolean);
      o.csl = [];
      for (const n of names) o.csl.push(await cslScreen(n));
      log(o, s, 'csl screened', o.csl.map(c => c.name + (c.clear ? ' clear' : ' HIT')).join('; '));
    }
    save(d); audit('csl', '');
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  // export screen
  if (fp === '/api/payload-orders/export') {
    const status = String(body.status || '');
    if (!EXPORT_STATUSES.includes(status)) return send(res, 400, { error: 'status must be one of ' + EXPORT_STATUSES.join(', ') });
    const x = { status, classification: String(body.classification || '').trim().slice(0, 40),
      source: String(body.source || '').slice(0, 40), screened_by: who(s), screened_at: now() };
    if (x.classification && !/^[A-Za-z0-9 .\-\/()]+$/.test(x.classification)) return send(res, 400, { error: 'Classification is just the number (e.g. EAR99, 9A515.x, USML Cat XV(e)).' });
    if (CONTROLLED(status)) {
      if (!x.classification) return send(res, 400, { error: status === 'itar' ? 'Enter the USML category.' : 'Enter the ECCN.' });
      const spErr = validSharePoint(body.sharepoint_path);
      if (spErr) return send(res, 400, { error: spErr });
      const h = trainedHandlers().find(t => t.email === String(body.handler_email || '').toLowerCase());
      if (!h) return send(res, 400, { error: 'Handler must have signed both the CUI Policies and the CUI NDA in Required Reading.' });
      x.sharepoint_path = String(body.sharepoint_path).trim();
      x.handler_email = h.email; x.handler_name = h.name;
      // Only the handler (or an admin) can confirm the SEC-CUI-STOR procedure was done.
      if (body.procedure_ack) {
        if (me !== h.email && !isAdmin) return send(res, 403, { error: 'Only the named handler (or an admin) can confirm ' + PROCEDURE + '.' });
        x.procedure_ack = { by: who(s), email: me, at: now() };
      } else if (o.export && o.export.procedure_ack && o.export.handler_email === h.email && o.export.sharepoint_path === x.sharepoint_path) {
        x.procedure_ack = o.export.procedure_ack;
      }
    }
    o.export = x;
    log(o, s, 'export screen', status + (x.classification ? ' ' + x.classification : '') + (x.procedure_ack ? ' · ' + PROCEDURE + ' confirmed' : ''));
    save(d); audit('export', status);
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  // LSA upload (Word only, commercial contract — screened before it is kept)
  if (fp === '/api/payload-orders/lsa-upload') {
    const name = String(body.filename || '');
    if (!/\.docx$/i.test(name)) return send(res, 400, { error: 'Upload the LSA as a Word (.docx) file.' });
    const buf = Buffer.from(String(body.data_b64 || ''), 'base64');
    if (!buf.length || buf.length > 25 << 20) return send(res, 400, { error: 'File missing or over 25 MB.' });
    const dir = path.join(LSA_DIR, o.id); fs.mkdirSync(dir, { recursive: true });
    const stamp = Date.now();
    const docx = path.join(dir, stamp + '_' + name.replace(/[^\w.\-]+/g, '_'));
    const html = docx.replace(/\.docx$/i, '.html');
    fs.writeFileSync(docx, buf);
    try { await execFileP(PY, [DOCX2HTML, docx, html], { timeout: 60000 }); }
    catch (e) { try { fs.unlinkSync(docx); } catch {} return send(res, 500, { error: 'Could not read the Word file: ' + e.message }); }
    const text = fs.readFileSync(html, 'utf8').replace(/<img[^>]*>/g, ' ').replace(/<[^>]+>/g, ' ');
    const hits = await itarScreen(text);
    if (hits.length) {
      for (const f of [docx, html]) { try { fs.unlinkSync(f); } catch {} }
      log(o, s, 'LSA upload BLOCKED by export screen', name);
      save(d);
      return send(res, 422, { error: 'Blocked: the LSA contains what looks like export-controlled technical data. Keep technical detail in SharePoint and send a commercial-only LSA. (' + hits[0] + ')' });
    }
    let rend;
    try { rend = await renderLsa(docx); }
    catch (e) { return send(res, 500, { error: 'Could not put the LSA on Exos letterhead / render its pages: ' + String(e.stderr || e.message).slice(0, 300) }); }
    o.lsa_file = path.relative(MC_DIR, docx); o.lsa_html = path.relative(MC_DIR, html); o.lsa_uploaded_at = now();
    o.lsa_letterhead_docx = path.relative(MC_DIR, rend.letterhead_docx); o.lsa_pdf = path.relative(MC_DIR, rend.pdf);
    o.lsa_pages_html = path.relative(MC_DIR, rend.pages_html);
    log(o, s, 'LSA uploaded', name + ' → on Exos letterhead, ' + rend.pages + ' pages');
    save(d); audit('lsa-upload', name);
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  // send LSA for e-signature (customer signs first, John countersigns last)
  if (fp === '/api/payload-orders/send-lsa') {
    const v = view(o, ctx.loadEnvelopes());
    if (!v.screened) return send(res, 409, { error: 'Finish the export screen and CSL screen first.' });
    if (!o.lsa_html) return send(res, 409, { error: 'Upload the LSA first.' });
    if (v.envelope_status && v.envelope_status !== 'expired') return send(res, 409, { error: 'An e-sign envelope is already out (' + v.envelope_status + ').' });
    const email = String(body.signer_email || o.contact_email || '').trim();
    const name = String(body.signer_name || o.contact_name || '').trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return send(res, 400, { error: 'Customer signer email required.' });
    // Format-true copy only: letterhead + original page layout. Render now if this LSA predates the rule.
    if (!o.lsa_pages_html || !fs.existsSync(path.join(MC_DIR, o.lsa_pages_html))) {
      try { const rend = await renderLsa(path.join(MC_DIR, o.lsa_file));
        o.lsa_letterhead_docx = path.relative(MC_DIR, rend.letterhead_docx); o.lsa_pdf = path.relative(MC_DIR, rend.pdf); o.lsa_pages_html = path.relative(MC_DIR, rend.pages_html); }
      catch (e) { return send(res, 500, { error: 'LSA not sent: could not render it on Exos letterhead (' + String(e.stderr || e.message).slice(0, 200) + ').' }); }
    }
    const html = fs.readFileSync(path.join(MC_DIR, o.lsa_pages_html), 'utf8');
    const title = 'BLK3 Launch Services Agreement — ' + o.customer;
    const r = await ctx.createEnvelope(req, {
      title, html, subject: 'Signature requested: ' + title,
      message: 'Please review and sign the Launch Services Agreement for your payload on ' + ((o.mission ? missionLabel(o.mission) : o.flight) || 'BLK3') + '. Exos countersigns after you.',
      signers: [{ name: name || 'Customer', email, role: 'Customer' }, { name: 'John Quinn', email: 'jquinn@exosaero.com', role: 'Exos Aerospace — CEO' }],
    });
    if (!r || !r.id) return send(res, 500, { error: 'E-sign envelope was not created.' });
    o.envelope_id = r.id; o.lsa_sent_at = now();
    log(o, s, 'LSA sent for e-signature', email + ' → John countersigns (envelope ' + r.id + ')');
    save(d); audit('send-lsa', r.id);
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  // LSA handled outside MC (e.g. emailed Word copy) — record it so status stays true.
  // ExoSign (send-lsa) is the default path; outside is an exception, so a reason is required (Jon 2026-10-11).
  if (fp === '/api/payload-orders/lsa-outside') {
    const why = String(body.reason || '').trim();
    if ((body.sent_at || body.signed_at) && !why) return send(res, 400, { error: 'ExoSign is the default. Say why this LSA was handled outside MC (e.g. ExoSign was down).' });
    if (why) o.lsa_outside_reason = why.slice(0, 300);
    if (body.sent_at) { o.lsa_sent_outside_at = String(body.sent_at).slice(0, 10); log(o, s, 'LSA sent outside MC', o.lsa_sent_outside_at + ' · reason: ' + why); }
    if (body.signed_at) {
      if (!String(body.signed_copy || '').trim()) return send(res, 400, { error: 'Say where the fully signed copy is filed.' });
      o.lsa_signed_at = String(body.signed_at).slice(0, 10); o.lsa_signed_copy = String(body.signed_copy).slice(0, 400);
      log(o, s, 'LSA executed outside MC', o.lsa_signed_at + ' · ' + o.lsa_signed_copy + ' · reason: ' + why);
    }
    save(d); audit('lsa-outside', ''); fleet('lsa_outside', { order: o.id, by: me, reason: why });
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  // milestone: invoiced / paid
  if (fp === '/api/payload-orders/milestone') {
    const key = String(body.key || ''); const act = String(body.action || '');
    const okKey = o.in_kind ? key === 'INK' : MILESTONES.some(m => m.key === key);
    if (!okKey || !['invoiced', 'paid', 'undo'].includes(act)) return send(res, 400, { error: o.in_kind ? 'In-kind order: only the $1 INK documentation milestone applies.' : 'Bad milestone/action' });
    const v = view(o, ctx.loadEnvelopes());
    if (!v.screened) return send(res, 409, { error: 'Export + CSL screen must be complete before any invoice or payment is recorded.' });
    if (!v.executed && act !== 'undo') return send(res, 409, { error: 'The LSA is not executed yet.' });
    o.milestones = o.milestones || {}; const m = o.milestones[key] = o.milestones[key] || {};
    if (act === 'undo') {
      if (!isAdmin) return send(res, 403, { error: 'Only an admin can undo a milestone.' });
      o.milestones[key] = {}; log(o, s, key + ' reset', String(body.reason || '').slice(0, 200));
    } else if (act === 'invoiced') {
      m.invoice_no = String(body.invoice_no || '').slice(0, 40); m.invoiced_at = String(body.date || now()).slice(0, 10);
      m.invoiced_by = who(s);
      log(o, s, key + ' invoiced', (m.invoice_no || 'no #') + ' · ' + m.invoiced_at);
    } else {
      const amt = Number(body.amount);
      if (!(amt > 0)) return send(res, 400, { error: 'Enter the amount received.' });
      if (!m.invoiced_at) m.invoiced_at = String(body.date || now()).slice(0, 10);
      m.paid_at = String(body.date || now()).slice(0, 10); m.amount_received = amt; m.recorded_by = who(s);
      log(o, s, key + ' paid', '$' + amt.toLocaleString() + ' · ' + m.paid_at);
      if (key === 'M1' || key === 'INK') {   // first money in → payload-customer registry (green badge + metrics)
        const args = [PAYLOAD_CUSTOMER, 'add', '--company', o.customer, '--payload-name', o.payload_name || o.customer + ' payload',
          '--mission', (o.mission ? missionLabel(o.mission) : o.flight) || 'BLK3', '--flight-no', o.mission || '', '--contract-id', o.id, '--amount-paid', String(amt), '--paid-date', m.paid_at,
          '--notes', (key === 'INK' ? `In-kind payment (${(o.in_kind || {}).description || 'goods'}, value $${Number((o.in_kind || {}).value || 0).toLocaleString()}); $1 documentation invoice` : 'M1 deposit') + ' via MC payload order ' + o.id];
        if (o.mass_kg) args.push('--mass-kg', String(o.mass_kg));
        if (o.flight_date) args.push('--flight-date', o.flight_date);
        if (v.contract_value_effective) args.push('--contract-value', String(v.contract_value_effective));
        if (o.lsa_signed_copy) args.push('--signed-contract', o.lsa_signed_copy);
        execFile(PY, args, { timeout: 30000 }, (e) => { if (e) console.error('[payload-orders] registry add failed', e.message); });
      }
    }
    save(d); audit('milestone', key + ' ' + act);
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  // in-kind payment: set terms (description + value), or record the consideration received
  if (fp === '/api/payload-orders/in-kind') {
    if (body.action === 'set') {
      const desc = String(body.description || '').trim();
      const val = Number(body.value || contractValue(o) || 0);
      if (!desc || !(val > 0)) return send(res, 400, { error: 'Describe the in-kind payment and its value.' });
      if (Object.keys(o.milestones || {}).some(k => k !== 'INK' && (o.milestones[k] || {}).invoiced_at)) return send(res, 409, { error: 'Cash milestones already invoiced — undo them first.' });
      o.in_kind = { ...(o.in_kind || {}), description: desc.slice(0, 200), value: val, set_by: who(s), set_at: now() };
      log(o, s, 'in-kind payment set', `${o.in_kind.description} · value $${val.toLocaleString()} · $1 documentation invoice replaces M1/M2/M3`);
    } else if (body.action === 'received') {
      if (!o.in_kind) return send(res, 409, { error: 'Not an in-kind order.' });
      const dt = String(body.date || now()).slice(0, 10);
      o.in_kind.received_at = dt; o.in_kind.received_by = who(s); o.in_kind.received_note = String(body.note || '').slice(0, 200);
      log(o, s, 'in-kind payment received', `${o.in_kind.description} · ${dt}${o.in_kind.received_note ? ' · ' + o.in_kind.received_note : ''}`);
    } else if (body.action === 'clear') {
      if (!isAdmin) return send(res, 403, { error: 'Only an admin can remove the in-kind terms.' });
      log(o, s, 'in-kind payment removed', String(body.reason || '').slice(0, 200)); delete o.in_kind;
    } else return send(res, 400, { error: 'Bad action' });
    save(d); audit('in-kind', body.action); fleet('in_kind_' + body.action, { order: o.id, by: me, value: (o.in_kind || {}).value });
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  if (fp === '/api/payload-orders/close') {
    const vw = view(o, ctx.loadEnvelopes());
    if (!body.reopen && vw.executed && !vw.waiver_ok && !String(body.reason || '').match(/cancel/i)) {
      return send(res, 409, { error: 'Cannot close: the wet-signed cross-waiver of claims (and its FAA submission) is not recorded. Record it, or close with a reason mentioning "cancelled".' });
    }
    o.closed = !body.reopen; o.closed_at = o.closed ? now() : null;
    log(o, s, o.closed ? 'closed' : 'reopened', String(body.reason || '').slice(0, 200));
    save(d); audit('close', '');
    return send(res, 200, { ok: true, order: view(o, ctx.loadEnvelopes()) });
  }

  return send(res, 404, { error: 'Not found' });
}

// ── FAA cross-waiver hybrid step: Exo prompts, a human confirms the wet-signed original is on file ──
const DECISIONS_TOKEN = path.join(MC_DIR, 'data', '.decisions-token');
function fileDecision(body) {
  if (process.env.PAYLOAD_NO_DECISIONS) return Promise.resolve({ id: 'D-TEST' });   // tests only
  return new Promise((ok, bad) => {
    const http = require('http');
    const data = JSON.stringify(body);
    const rq = http.request({ host: '127.0.0.1', port: 8080, path: '/api/decisions/ingest', method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Exo-Token': fs.readFileSync(DECISIONS_TOKEN, 'utf8').trim(), 'Content-Length': Buffer.byteLength(data) } }, rs => {
      let b = ''; rs.on('data', c => b += c); rs.on('end', () => { try { ok(JSON.parse(b)); } catch (e) { bad(e); } });
    });
    rq.on('error', bad); rq.end(data);
  });
}
// Called on a timer by server.js. Files at most one open waiver card per order.
async function waiverPrompts(envelopes) {
  const d = load(); const today = new Date().toISOString().slice(0, 10); let filed = 0;
  for (const o of d.orders) {
    const v = view(o, envelopes || []);
    if (o.closed || o.waiver_wet_signed_at || !o.flight_date) continue;
    if (!(v.executed || today >= addDays(o.flight_date, -150))) continue;
    if (o.waiver_decision_id && !(o.waiver_reprompt_after && today >= o.waiver_reprompt_after)) continue;
    const r = await fileDecision({
      title: `FAA cross-waiver on file? ${o.customer} (${v.flight || o.mission || ''})`,
      question: `Is ${o.customer}'s WET-SIGNED cross-waiver of claims physically on file at Exos?`,
      context: `Order ${o.id}. FAA reciprocal waiver of claims (14 CFR 440.17) must be wet-signed and at Exos by ${v.waiver_due} (L-90 for the ${o.flight_date} flight) so Exos can submit all waivers to the FAA for payload approval. Exo can't verify paper. Confirm only if you have seen the original. Put where it is filed in the note (and the signature date as YYYY-MM-DD if it differs from today). 'Not yet' re-asks in 14 days.`,
      proposedAction: 'Exo records the waiver as on file (date + who confirmed) on the payload order',
      type: 'yesno', options: ['Yes — original on file', 'Not yet'], priority: v.waiver_overdue ? 'high' : 'med',
      approver: 'lquinn@exosaero.com', relatedItem: o.id, source: 'Payload order-to-cash (exo3)', dedupeKey: `payload-waiver:${o.id}`,
    });
    o.waiver_decision_id = r && r.id; o.waiver_reprompt_after = null;
    log(o, { name: 'Exo' }, 'waiver_prompt', `Decision ${o.waiver_decision_id} filed: confirm wet-signed waiver on file`); filed++;
    fleet('waiver_prompt', { order: o.id, decision: o.waiver_decision_id, due: v.waiver_due }, 'decide');
  }
  if (filed) save(d);
  return filed;
}
// Called by server.js right after a human answers a payload-waiver decision.
function onDecision(dec) {
  if (!dec || !/^payload-waiver:/.test(dec.dedupeKey || '')) return;
  const by = String(dec.answeredBy || ''), email = String(dec.answeredByEmail || '');
  if (!by && !email) return;   // token/proposed answers never count
  const d = load(); const o = d.orders.find(x => x.id === dec.dedupeKey.slice('payload-waiver:'.length)); if (!o) return;
  const ans = String(dec.answer || '').toLowerCase(), note = String(dec.note || '');
  const today = new Date().toISOString().slice(0, 10);
  if (ans.startsWith('yes')) {
    const m = note.match(/\b(20\d\d-\d\d-\d\d)\b/);
    o.waiver_wet_signed_at = (m && m[1] <= today) ? m[1] : today;
    o.waiver_confirmed_by = `${by || email} (${dec.id})`;
    if (note) o.waiver_original_location = note.slice(0, 200);
    fleet('waiver_confirmed', { order: o.id, decision: dec.id, by: by || email });
    log(o, { name: by, email }, 'waiver_confirmed', `Wet-signed original on file, confirmed by ${by || email} via ${dec.id}${note ? ': ' + note.slice(0, 120) : ''}`);
  } else {
    o.waiver_reprompt_after = addDays(today, 14);
    fleet('waiver_not_yet', { order: o.id, decision: dec.id, by: by || email, reprompt: o.waiver_reprompt_after });
    log(o, { name: by, email }, 'waiver_not_yet', `${by || email}: not yet on file (${dec.id}); re-ask ${o.waiver_reprompt_after}`);
  }
  save(d);
}

module.exports = { handle, view, load, trainedHandlers, validSharePoint, contractValue, waiverPrompts, onDecision };
