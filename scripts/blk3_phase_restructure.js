#!/usr/bin/env node
// BLK3 schedule → phase structure (Phil Eaton 2026-10-22, MC #3824):
// Design → BOM & materials list → Purchasing → Fabrication. Design is a predecessor of every
// purchase it drives. Adds one unassigned BOM task per design area (Phil assigns owners).
// Audited writes through the ERP DAL. Idempotent. Usage: node blk3_phase_restructure.js [--apply]
const path = require('path');
const { openErp } = require(path.join(__dirname, '..', 'erp-foundation', 'dal'));
const APPLY = process.argv.includes('--apply');
const erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: 'exo (for peaton@exosaero.com)', agent: 'blk3-phase-restructure' });
const PID = 'tw-902146';
const sched = () => erp.getProjectSchedule(PID).tasks.map(t => ({ ...t, preds: JSON.parse(t.predecessors_json || '[]') }));
let T = sched();
const byTitle = n => { const t = T.find(x => x.title.toLowerCase() === n.toLowerCase()); if (!t) throw new Error('missing task: ' + n); return t; };
const day = (s, n) => { const d = new Date(String(s).slice(0, 10) + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10) + 'T00:00:00'; };
const log = [];

// 1) Phases
const PHASE = {
  'Design & Analysis': ['Airframe Section Design', 'Design wiring harnesses', 'Power Supply Design', 'Payload Ejector', 'Modify design model with large GHe pressurant tank',
    'Redesign Nosecone Bulkhead', 'Determine components for on-board telemetry', 'Redesign Fins', 'Flight simulations using Trick', 'R&D Fincan / Engine Bay Noise Solution', 'Assign ACS deadband and rate review'],
  'Purchasing': ['Order launch-stool scale / load-cell parts', 'Order bulkhead raw stock', 'Order wire & connectors — main harness', 'Order power-supply components',
    'Order payload airframe reinforcement stock', 'Order large GHe pressurant tank (LONG-LEAD)', 'Order GHe tank support stock', 'Order pressure-section material',
    'Order recovery-section material', 'Order wire & connectors — recovery harness', 'Order GPS antenna', 'Purchase larger release servo',
    'Get quote for ground telemetry support', 'Find suitable lifting device(s) for payload', 'Find suitable portable payload processing enclosure'],
  'Fabrication & Assembly': ['Modify launch stool', 'Repair or refurbish launch stool scale system', 'Fabricate Bulkheads', 'Fabricate Wiring Harness', 'Mount upper ACS',
    'Payload Airframe Reinforcements', 'Payload Ejection Mechanism', 'Rebuild with large GHe tank', 'Fabricate new GHe tank supports',
    'Build a complete upgraded pressure section for back 2 back flights', 'Complete fabrication of recovery section', 'Machine the Nosecone Bulkhead',
    'Fabricate wiring harnesses for recovery section', 'Mount GPS antenna'],
  'Software Development & Verification': ['Add serial control of recovery servo', 'Add spark detect to fsw and ITOS', 'Remove unused variables', 'Speed up telemetry where possible', 'Add serial port for servo control'],
  'Integration & Test (FRUs)': ['Test Recovery methodology for BLK3 system'],
  'Licensing & Regulatory': ['Engage FCC license preparation'],
};

// 2) Design → BOM → purchases → fabrication chains
const CHAINS = [
  { design: 'Airframe Section Design', bom: 'BOM & materials list — airframe / bulkheads', orders: ['Order bulkhead raw stock'], fab: { 'Fabricate Bulkheads': 'Order bulkhead raw stock' } },
  { design: 'Design wiring harnesses', bom: 'BOM & materials list — main wiring harness', orders: ['Order wire & connectors — main harness'], fab: { 'Fabricate Wiring Harness': 'Order wire & connectors — main harness' } },
  { design: 'Power Supply Design', bom: 'BOM & materials list — power supply', orders: ['Order power-supply components'], fab: {} },
  { design: 'Payload Ejector', bom: 'BOM & materials list — payload ejector & airframe reinforcements', orders: ['Order payload airframe reinforcement stock'], fab: { 'Payload Airframe Reinforcements': 'Order payload airframe reinforcement stock' } },
  { design: 'Modify design model with large GHe pressurant tank', bom: 'BOM & materials list — pressurization section',
    orders: ['Order large GHe pressurant tank (LONG-LEAD)', 'Order GHe tank support stock', 'Order pressure-section material'],
    fab: { 'Rebuild with large GHe tank': 'Order large GHe pressurant tank (LONG-LEAD)', 'Fabricate new GHe tank supports': 'Order GHe tank support stock',
           'Build a complete upgraded pressure section for back 2 back flights': 'Order pressure-section material' } },
  { design: 'Redesign Nosecone Bulkhead', bom: 'BOM & materials list — recovery section',
    orders: ['Order recovery-section material', 'Order wire & connectors — recovery harness'],
    fab: { 'Complete fabrication of recovery section': 'Order recovery-section material', 'Machine the Nosecone Bulkhead': 'Order recovery-section material',
           'Fabricate wiring harnesses for recovery section': 'Order wire & connectors — recovery harness' } },
  { design: 'Determine components for on-board telemetry', bom: 'BOM & materials list — telemetry / GPS', orders: ['Order GPS antenna'], fab: { 'Mount GPS antenna': 'Order GPS antenna' } },
];

function setPhase(t, ph) { if (t.phase !== ph) { log.push(`phase  ${t.title} → ${ph}`); if (APPLY) erp.updateScheduleTask(t.id, { phase: ph }); } }
function addPred(t, p) { if (!t.preds.includes(p.id)) { log.push(`link   "${t.title}" now waits on "${p.title}"`); t.preds.push(p.id); if (APPLY) erp.updateScheduleTask(t.id, { predecessors: t.preds }); } }

for (const [ph, names] of Object.entries(PHASE)) names.forEach(n => setPhase(byTitle(n), ph));

let seq = Math.max(...T.map(t => Number(t.seq) || 0));
for (const c of CHAINS) {
  const d = byTitle(c.design);
  let bom = T.find(x => x.title === c.bom);
  if (!bom) {
    const id = 'mc-bom-' + d.id.replace(/^(tw|mc)-task-/, '');
    bom = { id, title: c.bom, preds: [d.id], phase: 'BOM & Materials', task_list_id: d.task_list_id, start_date: day(d.due_date, 1), due_date: day(d.due_date, 3) };
    log.push(`create "${c.bom}" (unassigned) ${bom.start_date.slice(0, 10)} → ${bom.due_date.slice(0, 10)}, waits on "${d.title}"`);
    if (APPLY) erp.upsertTask({ id, project_id: PID, task_list_id: d.task_list_id, title: c.bom, state: 'Open', owner: null, due_date: bom.due_date, priority: null,
      category: 'schedule', description: 'BOM and materials list pulled from the design, released to purchasing.', source: 'mc', startDate: bom.start_date, progress: 0,
      parentTaskId: null, predecessors: [d.id], seq: ++seq, phase: 'BOM & Materials', created_by: 'peaton@exosaero.com (via Exo)' });
    T = APPLY ? sched() : T.concat([bom]);
    bom = T.find(x => x.title === c.bom);
  }
  c.orders.forEach(o => addPred(byTitle(o), bom));
  Object.entries(c.fab).forEach(([f, o]) => addPred(byTitle(f), byTitle(o)));
}
erp.close();
console.log((APPLY ? 'APPLIED' : 'DRY RUN') + ': ' + log.length + ' changes'); log.forEach(l => console.log('  ' + l));
