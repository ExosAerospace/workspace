#!/usr/bin/env node
// BLK3 (Phil Eaton 2026-10-22, MC #3824): GSE = Ground Support Equipment — NOT an FRU, not required
// for flight; includes ground telemetry and on-board telemetry components. FRUs run in parallel:
// no links between FRUs. Audited ERP writes via the DAL. Idempotent. Usage: node blk3_gse_parallel.js [--apply]
const path = require('path');
const { openErp } = require(path.join(__dirname, '..', 'erp-foundation', 'dal'));
const APPLY = process.argv.includes('--apply');
const erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: 'exo (for peaton@exosaero.com)', agent: 'blk3-gse-parallel' });
const PID = 'tw-902146', GSE_LIST = 'tw-tl-2606284';
const load = () => { const t = erp.getProjectSchedule(PID).tasks; t.forEach(x => x.p = JSON.parse(x.predecessors_json || '[]')); return t; };
let T = load();
const get = n => { const t = T.find(x => x.title === n); if (!t) throw new Error('missing: ' + n); return t; };
const day = (s, n) => { const d = new Date(String(s).slice(0, 10) + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10) + 'T00:00:00'; };
const log = [];
function unlink(from, to) { const a = get(from), b = get(to); if (b.p.includes(a.id)) { b.p = b.p.filter(x => x !== a.id); log.push(`unlink "${to}" no longer waits on "${from}"`); if (APPLY) erp.updateScheduleTask(b.id, { predecessors: b.p }); } }
function link(from, to) { const a = get(from), b = get(to); if (!b.p.includes(a.id)) { b.p.push(a.id); log.push(`link   "${to}" now waits on "${from}"`); if (APPLY) erp.updateScheduleTask(b.id, { predecessors: b.p }); } }

// 1) Telemetry / GPS out of the Recovery FRU
unlink('Mount GPS antenna', 'FRU ready for integration: Recovery Section');
unlink('Add serial port for servo control', 'Mount GPS antenna');
unlink('Engage FCC license preparation', 'Get quote for ground telemetry support');   // licensing stays its own track
// 2) FRUs in parallel: remove links between the Payload and Computer FRUs
unlink('Fabricate Wiring Harness', 'Power Supply Design');
unlink('Power Supply Design', 'Mount upper ACS');
// 3) Launch-stool parts feed the scale refurbish
link('Order launch-stool scale / load-cell parts', 'Repair or refurbish launch stool scale system');
// 4) Move telemetry/GPS + payload ground handling into the GSE section (task list)
const toGse = ['Determine components for on-board telemetry', 'BOM & materials list — telemetry / GPS', 'Order GPS antenna', 'Mount GPS antenna',
  'Get quote for ground telemetry support', 'Find suitable lifting device(s) for payload', 'Find suitable portable payload processing enclosure'];
for (const n of toGse) { const t = get(n); if (t.task_list_id !== GSE_LIST) { log.push(`move   "${n}" → GSE section`);
  if (APPLY) { const raw = JSON.parse(require('child_process').execFileSync('sqlite3', [path.join(__dirname, '..', 'erp-foundation', 'mc.db'), `SELECT raw_json FROM task WHERE id='${t.id}'`]).toString());
    // raw_json can hold stale owner/state (the DAL updates those columns only) → carry current column values.
    erp.upsertTask({ ...raw, owner: t.owner, state: t.state, due_date: t.due_date, startDate: t.start_date, phase: t.phase, task_list_id: GSE_LIST, predecessors: t.p }); } } }
// 5) GSE roll-up line (not an FRU; not linked to vehicle integration)
const feeds = ['Repair or refurbish launch stool scale system', 'Mount GPS antenna', 'Get quote for ground telemetry support', 'Find suitable portable payload processing enclosure'];
if (!T.some(x => x.id === 'mc-gse')) {
  const pre = feeds.map(get), last = pre.map(t => t.due_date).sort().pop(), st = day(last, 1), du = day(st, 4);
  log.push(`create "GSE ready (ground support — not required for flight)" ${st.slice(0, 10)} → ${du.slice(0, 10)} · waits on ${pre.length} GSE tasks`);
  if (APPLY) erp.upsertTask({ id: 'mc-gse', project_id: PID, task_list_id: GSE_LIST, title: 'GSE ready (ground support — not required for flight)', state: 'Open', owner: null,
    due_date: du, priority: null, category: 'schedule', description: 'Ground Support Equipment (launch stool, ground + on-board telemetry, payload handling). Not an FRU; nice to have, not required for flight.',
    source: 'mc', startDate: st, progress: 0, parentTaskId: null, predecessors: pre.map(t => t.id), seq: Math.max(...T.map(t => Number(t.seq) || 0)) + 1,
    phase: 'Integration & Test (FRUs)', created_by: 'peaton@exosaero.com (via Exo)' });
}
erp.close();
console.log((APPLY ? 'APPLIED' : 'DRY RUN') + ': ' + log.length + ' changes'); log.forEach(l => console.log('  ' + l));
