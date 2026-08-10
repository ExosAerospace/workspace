'use strict';
/* blk3_assign_owners.js — assign owners to the BLK3 ERP schedule tasks (tw-902146) by
 * expertise, matched to real BambooHR titles. Audited via dal.updateScheduleTask.
 * Dry-run by default; pass --apply to write.
 *
 * Title-based expertise map:
 *   Kyle Ballard      (CFO)                         -> budget / quote / price / cost
 *   Neil Milburn      (COO/XSO)                     -> regulatory (FCC/FAA) + R&D/sim/redesign (Russ Blink's tech -> Neil)
 *   Steven Norsworthy (Avionics Test Technician)    -> FSW/telemetry/GPS/ITOS/ACS/avionics/recovery electronics
 *   Phillip Eaton     (Aerospace Operations Manager)-> payload/ejector/enclosure/design + default disposition
 *   Mike Talley / Victor Castilleja (Machinist/AIT) -> fabrication / machining / structures (load-balanced)
 */
const { openErp } = require('../erp-foundation/dal');
const APPLY = process.argv.includes('--apply');

const KYLE = 'Kyle Ballard', NEIL = 'Neil Milburn', STEVE = 'Steven Norsworthy',
      PHIL = 'Phillip Eaton', MIKE = 'Mike Talley', VIC = 'Victor Castilleja';

let fab = 0;
function ownerFor(title) {
  const t = (title || '').toLowerCase();
  if (/budget|quote|price|cost|invoice/.test(t)) return KYLE;                                   // CFO
  if (/fcc|licen|faa|regulat|waiver|part 450/.test(t)) return NEIL;                              // COO/XSO regulatory
  if (/\bsim\b|trick|simulation|r&d|\br and d\b|redesign|design model|noise solution|model\b/.test(t)) return NEIL; // Russ tech -> Neil
  if (/fsw|flight software|telemetry|serial|\bgps\b|itos|\bacs\b|deadband|variable|power supply|avionics|spark detect|software/.test(t)) return STEVE; // avionics
  if (/recovery|servo|release|parachute|canopy|drogue/.test(t)) return STEVE;                    // recovery electronics
  if (/payload|ejector|ejection|lifting|enclosure|processing/.test(t)) return PHIL;              // ops/payload
  if (/design|harness design|airframe section design/.test(t)) return PHIL;                      // design coordination
  if (/fabricat|bulkhead|harness|launch stool|fincan|\bfin\b|fins|\btank\b|pressure section|reinforcement|mount|support|refurbish|rebuild|\bbuild\b|section|machin|weld|composite/.test(t))
    return (fab++ % 2) ? VIC : MIKE;                                                             // machinists, load-balanced
  return PHIL;                                                                                   // default: Ops Manager dispositions
}

const erp = openErp('erp-foundation/mc.db', { actor: 'blk3-assign-owners', agent: 'blk3-assign' });
const s = erp.getProjectSchedule('tw-902146');
const dist = {};
const plan = s.tasks.map(t => { const o = ownerFor(t.title); dist[o] = (dist[o] || 0) + 1; return { id: t.id, title: t.title, owner: o, cur: t.owner }; });

console.log(`BLK3 owner assignment — ${plan.length} tasks (by title/expertise)`);
Object.entries(dist).sort((a, b) => b[1] - a[1]).forEach(([o, c]) => console.log(`  ${o.padEnd(20)} ${c}`));
console.log('');
plan.forEach(p => console.log(`  ${p.owner.padEnd(18)} ${(p.title || '').slice(0, 52)}`));

if (!APPLY) { console.log('\nDRY-RUN. Re-run with --apply to write (audited).'); erp.close(); process.exit(0); }
let w = 0;
for (const p of plan) { erp.updateScheduleTask(p.id, { owner: p.owner }); w++; }
erp.close();
console.log(`\nAssigned owners on ${w} schedule tasks (audited ERP).`);
