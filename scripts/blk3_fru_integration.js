#!/usr/bin/env node
// BLK3 FRU readiness → full vehicle integration & test (Phil Eaton 2026-10-22, MC #3824).
// One "FRU ready for integration" task per Field Replaceable Unit (bottom → top), each waiting on
// the build work that feeds it; one "Full vehicle integration & test" task waiting on all FRUs.
// New tasks are UNASSIGNED (no cards/notifications until Phil assigns). Existing dates untouched.
// Audited ERP writes via the DAL. Idempotent. Usage: node blk3_fru_integration.js [--apply]
const path = require('path');
const { openErp } = require(path.join(__dirname, '..', 'erp-foundation', 'dal'));
const APPLY = process.argv.includes('--apply');
const erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: 'exo (for peaton@exosaero.com)', agent: 'blk3-fru-integration' });
const PID = 'tw-902146', PH = 'Integration & Test';
let T = erp.getProjectSchedule(PID).tasks;
const get = n => { const t = T.find(x => x.title === n); if (!t) throw new Error('missing: ' + n); return t; };
const day = (s, n) => { const d = new Date(String(s).slice(0, 10) + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10) + 'T00:00:00'; };
const FRUS = [  // bottom of vehicle → top
  ['Engine Section', []],
  ['Fin Can', ['Redesign Fins', 'R&D Fincan / Engine Bay Noise Solution']],
  ['Propellant Tanks', []],
  ['Pressurization Section', ['Rebuild with large GHe tank', 'Fabricate new GHe tank supports', 'Build a complete upgraded pressure section for back 2 back flights']],
  ['Computer Section', ['Power Supply Design', 'Add spark detect to fsw and ITOS', 'Remove unused variables', 'Speed up telemetry where possible']],
  ['Payload Section', ['Fabricate Bulkheads', 'Fabricate Wiring Harness', 'Mount upper ACS', 'Payload Airframe Reinforcements', 'Payload Ejection Mechanism']],
  ['Recovery Section', ['Complete fabrication of recovery section', 'Machine the Nosecone Bulkhead', 'Fabricate wiring harnesses for recovery section', 'Add serial port for servo control', 'Mount GPS antenna']],
];
const log = []; let seq = Math.max(...T.map(t => Number(t.seq) || 0));
const lastDue = ts => ts.map(t => t.due_date).sort().pop();
const listFor = ts => (ts[0] && ts[0].task_list_id) || T[0].task_list_id;
// FRUs with build work: ready 1 day after its last feeding task, 5-day readiness/acceptance window.
const withWork = FRUS.filter(f => f[1].length).map(f => lastDue(f[1].map(get)));
const latest = withWork.sort().pop();
const fruIds = [];
FRUS.forEach(([name, feeds], i) => {
  const title = `FRU ready for integration: ${name}`;
  const pre = feeds.map(get);
  const st = pre.length ? day(lastDue(pre), 1) : day(latest, -4);   // no build tasks yet → align with the others
  const du = day(st, 4);
  const id = 'mc-fru-' + (i + 1);
  fruIds.push(id);
  if (T.some(x => x.id === id)) return;
  log.push(`create "${title}" ${st.slice(0, 10)} → ${du.slice(0, 10)}` + (pre.length ? ` · waits on ${pre.length} build task(s)` : ' · ⚠ no build tasks on the schedule yet'));
  if (APPLY) erp.upsertTask({ id, project_id: PID, task_list_id: listFor(pre), title, state: 'Open', owner: null, due_date: du, priority: null, category: 'schedule',
    description: `${name} FRU (field replaceable unit) built, inspected and acceptance-checked; ready for full vehicle integration.` + (pre.length ? '' : ' No build tasks for this FRU are on the schedule yet.'),
    source: 'mc', startDate: st, progress: 0, parentTaskId: null, predecessors: pre.map(t => t.id), seq: ++seq, phase: PH, fru: name, fru_order: i + 1, created_by: 'peaton@exosaero.com (via Exo)' });
});
const intId = 'mc-fru-integration';
if (!T.some(x => x.id === intId)) {
  const fruDue = APPLY ? lastDue(erp.getProjectSchedule(PID).tasks.filter(t => fruIds.includes(t.id))) : day(latest, 5);
  const st = day(fruDue, 1), du = day(st, 13);
  log.push(`create "Full vehicle integration & test (all 7 FRUs)" ${st.slice(0, 10)} → ${du.slice(0, 10)} · waits on all 7 FRU-ready tasks`);
  if (APPLY) erp.upsertTask({ id: intId, project_id: PID, task_list_id: T[0].task_list_id, title: 'Full vehicle integration & test (all 7 FRUs)', state: 'Open', owner: null,
    due_date: du, priority: null, category: 'schedule', description: 'Stack and integrate all 7 FRUs (Engine Section, Fin Can, Propellant Tanks, Pressurization, Computer, Payload, Recovery); integrated vehicle test.',
    source: 'mc', startDate: st, progress: 0, parentTaskId: null, predecessors: fruIds, seq: ++seq, phase: PH, created_by: 'peaton@exosaero.com (via Exo)' });
}
erp.close();
console.log((APPLY ? 'APPLIED' : 'DRY RUN') + ': ' + log.length + ' changes'); log.forEach(l => console.log('  ' + l));
