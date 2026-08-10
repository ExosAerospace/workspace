'use strict';
/* blk3_schedule_dates.js — populate start/due dates on the BLK3 Flight ERP schedule mirror.
 * The Teamwork project (tw-902146) has no real dates; this spreads the 35 tasks sequentially
 * across the program window (Day 1 = 2026-08-10, end = 2027-03-15) in Teamwork order (rowid),
 * setting the due_date column and raw_json.startDate while preserving all other raw_json fields.
 * Dry-run by default; pass --apply to write. The sync guard preserves these where Teamwork is blank.
 */
const { DatabaseSync } = require('node:sqlite');
const DB = 'erp-foundation/mc.db';
const PROJECT = 'tw-902146';
const START = Date.parse('2026-08-10T00:00:00Z');
const END = Date.parse('2027-03-15T00:00:00Z');
const APPLY = process.argv.includes('--apply');

const db = new DatabaseSync(DB);
const rows = db.prepare(`SELECT rowid, id, title, raw_json FROM task WHERE project_id=? ORDER BY rowid`).all(PROJECT);
const n = rows.length;
const span = END - START;
const iso = ms => new Date(ms).toISOString().slice(0, 10);

const plan = rows.map((r, i) => {
  const s = START + Math.round((i / n) * span);
  const d = START + Math.round(((i + 1) / n) * span);   // due = next task's start; last = END
  return { id: r.id, rowid: r.rowid, title: r.title, start: iso(s), due: iso(d), raw: r.raw_json };
});

console.log(`BLK3 schedule dates — ${n} tasks, ${iso(START)} -> ${iso(END)} (Teamwork order)`);
plan.slice(0, 6).forEach(p => console.log(`  ${p.start} -> ${p.due}  ${(p.title || '').slice(0, 44)}`));
console.log(`  … (${n - 6} more)`);

if (!APPLY) { console.log('\nDRY-RUN. Re-run with --apply to write.'); db.close(); process.exit(0); }

const upd = db.prepare(`UPDATE task SET due_date=?, raw_json=json_set(json_set(raw_json,'$.startDate',?),'$.due_date',?) WHERE id=?`);
let w = 0;
for (const p of plan) { upd.run(p.due, p.start, p.due, p.id); w++; }
db.close();
console.log(`\nWrote start/due to ${w} tasks. (due_date column + raw_json.startDate/​due_date)`);
