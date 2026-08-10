'use strict';
/* blk3_seed_dependencies.js — seed finish-to-start dependencies on the BLK3 schedule from the
 * current sequence + logical grouping. Within each work package (task-list), each task's
 * predecessor is the previous task in Teamwork import order (rowid). Also stamps a stable global
 * seq number per task. Audited via dal.updateScheduleTask. Dry-run by default; --apply to write.
 */
const { DatabaseSync } = require('node:sqlite');
const { openErp } = require('../erp-foundation/dal');
const APPLY = process.argv.includes('--apply');
const PROJECT = 'tw-902146';

const db = new DatabaseSync('erp-foundation/mc.db');
const rows = db.prepare(`SELECT rowid, id, task_list_id, title FROM task WHERE project_id=? ORDER BY rowid`).all(PROJECT);
db.close();

// stable global seq by import order
rows.forEach((r, i) => { r.seq = i + 1; });

// chain within each task-list (logical group), in sequence
const prevInList = {};
const plan = rows.map(r => {
  const prev = prevInList[r.task_list_id];
  prevInList[r.task_list_id] = r.id;
  return { id: r.id, seq: r.seq, title: r.title, predecessors: prev ? [prev] : [] };
});

const byId = {}; rows.forEach(r => byId[r.id] = r);
console.log(`BLK3 dependency seed — ${plan.length} tasks, ${new Set(rows.map(r=>r.task_list_id)).size} work packages`);
plan.forEach(p => {
  const predTitle = p.predecessors.length ? '#' + byId[p.predecessors[0]].seq + ' ' + (byId[p.predecessors[0]].title || '').slice(0, 28) : '(start — no predecessor)';
  console.log(`  #${String(p.seq).padStart(2)} ${(p.title || '').slice(0, 40).padEnd(40)} ⟸ ${predTitle}`);
});

if (!APPLY) { console.log('\nDRY-RUN. Re-run with --apply to write (audited).'); process.exit(0); }
const erp = openErp('erp-foundation/mc.db', { actor: 'blk3-seed-deps', agent: 'blk3-deps' });
let w = 0;
for (const p of plan) { erp.updateScheduleTask(p.id, { predecessors: p.predecessors, seq: p.seq }); w++; }
erp.close();
console.log(`\nSeeded predecessors + seq on ${w} tasks (audited ERP).`);
