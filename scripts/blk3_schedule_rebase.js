'use strict';
/* blk3_schedule_rebase.js — rebase the BLK3 Teamwork schedule into a new window and assign owners.
 * Day one = 2026-08-10, end = 2027-03-15. Preserves Teamwork task ORDER (separation/sequence),
 * spreads due dates across the window, assigns each task to the right owner by domain
 * (Russ's technical/design tasks -> Neil to disposition). Creates MC board tasks.
 * Dry-run by default; --apply to create.  */
const { openErp } = require('../erp-foundation/dal');
const https = require('https');

const START = new Date('2026-08-10T00:00:00Z');
const END = new Date('2027-03-15T00:00:00Z');
const APPLY = process.argv.includes('--apply');
const SUPA = 'pcrgpuoljylqcumijvnw.supabase.co';
const KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp';

// Domain -> owner email. Russ Blink's technical/design/sim work is redirected to Neil to disposition.
const NEIL = 'nmilburn@exosaero.com', STEVE = 'snorsworthy@exosaero.com', PHIL = 'peaton@exosaero.com',
      MIKE = 'mtalley@exosaero.com', VIC = 'vcastilleja@exosaero.com', KYLE = 'kballard@exosaero.com';
const NAME = { [NEIL]: 'Neil Milburn', [STEVE]: 'Steven Norsworthy', [PHIL]: 'Phillip Eaton',
               [MIKE]: 'Mike Talley', [VIC]: 'Victor Castilleja', [KYLE]: 'Kyle Ballard' };
let fabToggle = 0;
function ownerFor(title) {
  const t = (title || '').toLowerCase();
  if (/budget|quote|price|cost/.test(t)) return KYLE;
  if (/fcc|licen|faa|regulat/.test(t)) return NEIL;
  if (/sim|trick|r&d|\br and d\b|redesign|design model|noise solution/.test(t)) return NEIL; // Russ -> Neil
  if (/fsw|flight software|telemetry|serial|gps|itos|\bacs\b|deadband|variable|power supply|avionics|spark detect/.test(t)) return STEVE;
  if (/recovery|servo|release|parachute|canopy/.test(t)) return STEVE;
  if (/payload|ejector|ejection|lifting|enclosure|processing/.test(t)) return PHIL;
  if (/design|harness design|airframe section design/.test(t)) return PHIL;
  if (/fabricat|bulkhead|harness|launch stool|fincan|\bfin\b|fins|tank|pressure section|reinforcement|mount|support|refurbish|rebuild|\bbuild\b|section for/.test(t)) {
    return (fabToggle++ % 2) ? VIC : MIKE; // load-balance fabrication across the two machinists
  }
  return PHIL; // default: Ops Manager dispositions
}

function post(path, body) {
  return new Promise((res, rej) => {
    const data = JSON.stringify(body);
    const req = https.request({ hostname: SUPA, path: '/rest/v1/' + path, method: 'POST',
      headers: { apikey: KEY, Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json',
                 Prefer: 'return=representation', 'Content-Length': Buffer.byteLength(data) } },
      r => { let b = ''; r.on('data', c => b += c); r.on('end', () => res(JSON.parse(b || '[]'))); });
    req.on('error', rej); req.write(data); req.end();
  });
}

async function main() {
  const erp = openErp('erp-foundation/mc.db', { actor: 'blk3-rebase' });
  const s = erp.getProjectSchedule('tw-902146');
  // order by Teamwork displayOrder if present, else keep mirror order
  const rows = s.tasks.map(t => {
    let ord = 0; try { ord = JSON.parse(erp.getEmployees ? '{}' : '{}'); } catch (e) {}
    return t;
  });
  const tasks = s.tasks.slice(); // mirror already ordered
  erp.close();
  const n = tasks.length;
  const span = END - START;
  const byOwner = {};
  const plan = tasks.map((t, i) => {
    const due = new Date(START.getTime() + Math.round((i / (n - 1)) * span));
    const owner = ownerFor(t.title);
    byOwner[owner] = (byOwner[owner] || 0) + 1;
    return { seq: i + 1, title: t.title, due: due.toISOString().slice(0, 10), owner, email: owner };
  });
  console.log(`BLK3 flight schedule — ${n} tasks, ${START.toISOString().slice(0,10)} -> ${END.toISOString().slice(0,10)}`);
  console.log('Assignment distribution:');
  Object.entries(byOwner).sort((a,b)=>b[1]-a[1]).forEach(([e,c]) => console.log(`  ${NAME[e]||e}: ${c}`));
  console.log('\nPlan:');
  plan.forEach(p => console.log(`  #${String(p.seq).padStart(2)} ${p.due}  ${(NAME[p.owner]||p.owner).padEnd(18)} ${p.title.slice(0,48)}`));

  if (!APPLY) { console.log('\nDRY-RUN. Re-run with --apply to create the board tasks.'); return; }

  const now = new Date().toISOString();
  const fs = require('fs');
  const STATE = 'logs/assignment-notify-state.json';
  let notifyState = {}; try { notifyState = JSON.parse(fs.readFileSync(STATE, 'utf8')); } catch (e) {}
  let made = 0;
  for (const p of plan) {
    const r = await post('tasks', {
      title: p.title, owner: NAME[p.email] || p.email, assigned_email: p.email, assigned_to: NAME[p.email] || p.email,
      assigned_at: now, state: 'To Do', priority: 70, due_date: p.due, category: 'BLK3 to Flight',
      source: 'blk3-schedule', tags: ['blk3', 'flight-schedule'],
      description: `BLK3 flight schedule task (rebased: Day 1 = 2026-08-10, program end 2027-03-15). Sequence #${p.seq} of ${n}. From the Teamwork "Blk3 Flight" schedule. Initial assignment — disposition/adjust as needed.`,
    });
    if (Array.isArray(r) && r[0]) { made++; notifyState[String(r[0].id)] = p.email; }  // pre-seed -> no email blast
  }
  fs.writeFileSync(STATE, JSON.stringify(notifyState));
  console.log(`\nCreated ${made} BLK3 board tasks. Assignment-notifier pre-seeded (no email blast).`);
}
main();
