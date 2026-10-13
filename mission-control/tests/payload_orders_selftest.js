// exo3 eval for lib/payload-orders.js governed steps (Jon 2026-10-11): FAA cross-waiver HYBRID confirmation,
// ExoSign-default (outside LSA needs a reason), in-kind payment path ($1 INK documentation invoice).
// Runs against a sandbox copy of the module + store. Run: node mission-control/tests/payload_orders_selftest.js
const assert = require('assert'); const fs = require('fs'); const os = require('os'); const path = require('path');
const { Readable } = require('stream');
process.env.PAYLOAD_NO_DECISIONS = '1';
const SB = fs.mkdtempSync(path.join(os.tmpdir(), 'po-st-'));
fs.mkdirSync(path.join(SB, 'lib')); fs.mkdirSync(path.join(SB, 'data'));
fs.copyFileSync(path.join(__dirname, '..', 'lib', 'payload-orders.js'), path.join(SB, 'lib', 'payload-orders.js'));
const day = n => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
const base = { questionnaire_received: true, export: { status: 'not_controlled' }, csl: [{ name: 'X', clear: true }], milestones: {}, history: [] };
fs.writeFileSync(path.join(SB, 'data', 'payload-orders.json'), JSON.stringify({ seq: 3, orders: [
  { ...base, id: 'P1', customer: 'Cash Co', contract_value: 8000, flight_date: day(140), lsa_signed_at: day(-1) },          // executed -> prompt
  { ...base, id: 'P2', customer: 'Far Co', contract_value: 8000, flight_date: day(400) },                                   // not executed, > L-150 -> no prompt
  { ...base, id: 'P3', customer: 'InKind Co', contract_value: 8000, flight_date: day(140), lsa_signed_at: day(-1), in_kind: { description: '20 watches', value: 8000 } },
] }));
const p = require(path.join(SB, 'lib', 'payload-orders.js'));
let n = 0; const ok = (c, m) => { assert.ok(c, 'FAIL: ' + m); n++; };
const get = id => p.load().orders.find(o => o.id === id);
const req = (url, body) => Object.assign(Readable.from([JSON.stringify(body)]), { url, method: 'POST' });
const call = (url, body, role = 'admin') => new Promise(res => {
  const r = { writeHead(c) { this.c = c; }, end(b) { res({ code: this.c, body: JSON.parse(b) }); } };
  p.handle(req(url, body), r, { getSession: () => ({ role, email: 'jquinn@exosaero.com', name: 'John Quinn' }), loadEnvelopes: () => [], glog() {}, createEnvelope: async () => ({}) });
});
(async () => {
  // waiver hybrid step
  ok(await p.waiverPrompts([]) === 2, 'prompt filed for executed orders only (P1, P3), not P2 (>L-150, unsigned)');
  ok(await p.waiverPrompts([]) === 0, 'one open card per order (no duplicate prompts)');
  p.onDecision({ id: 'D-TOK', dedupeKey: 'payload-waiver:P1', answer: 'Yes — original on file' });
  ok(!get('P1').waiver_wet_signed_at, 'token/agent answer (no human) never records the waiver');
  p.onDecision({ id: 'D-NY', dedupeKey: 'payload-waiver:P1', answer: 'Not yet', answeredBy: 'Lizi Quinn', answeredByEmail: 'lquinn@exosaero.com' });
  ok(get('P1').waiver_reprompt_after === day(14), "'Not yet' re-asks in 14 days");
  p.onDecision({ id: 'D-Y', dedupeKey: 'payload-waiver:P1', answer: 'Yes — original on file', note: 'signed 2026-10-09, front-office binder', answeredBy: 'Lizi Quinn', answeredByEmail: 'lquinn@exosaero.com' });
  ok(get('P1').waiver_wet_signed_at === '2026-10-09' && /Lizi Quinn \(D-Y\)/.test(get('P1').waiver_confirmed_by), 'human Yes records signature date + who confirmed');
  // ExoSign default: outside-MC LSA needs a reason
  let r = await call('/api/payload-orders/lsa-outside', { id: 'P2', signed_at: day(0), signed_copy: 'SharePoint/x.pdf' });
  ok(r.code === 400 && /ExoSign is the default/.test(r.body.error), 'outside LSA without a reason is refused');
  r = await call('/api/payload-orders/lsa-outside', { id: 'P2', signed_at: day(0), signed_copy: 'SharePoint/x.pdf', reason: 'ExoSign down' });
  ok(r.code === 200 && get('P2').lsa_outside_reason === 'ExoSign down', 'outside LSA with reason is recorded');
  // in-kind path
  let v = p.view(get('P3'), []);
  ok(v.milestones_view.length === 1 && v.milestones_view[0].key === 'INK' && v.milestones_view[0].amount === 1, 'in-kind: single $1 INK milestone replaces M1-M3');
  ok(/\$1 in-kind documentation invoice/.test(v.next_action), 'in-kind next action = issue the $1 invoice');
  r = await call('/api/payload-orders/milestone', { id: 'P3', key: 'M1', action: 'invoiced', invoice_no: '1' });
  ok(r.code === 400, 'cash milestone refused on an in-kind order');
  await call('/api/payload-orders/milestone', { id: 'P3', key: 'INK', action: 'invoiced', invoice_no: '0076' });
  await call('/api/payload-orders/milestone', { id: 'P3', key: 'INK', action: 'paid', amount: 1, date: day(0) });
  ok(/Record the in-kind payment received/.test(p.view(get('P3'), []).next_action), 'after $1 paid -> record goods received');
  await call('/api/payload-orders/in-kind', { id: 'P3', action: 'received', date: day(0), note: '20 watches in safe' });
  ok(/close the order/.test(p.view(get('P3'), []).next_action) && get('P3').in_kind.received_by === 'John Quinn', 'goods received (by a named person) -> ready to close');
  ok(/Issue the M1 invoice/.test(p.view(get('P1'), []).next_action), 'cash orders unchanged');
  console.log(`payload-orders selftest: ${n}/${n} pass`);
  fs.rmSync(SB, { recursive: true, force: true });
})().catch(e => { console.error(e.message); process.exit(1); });
