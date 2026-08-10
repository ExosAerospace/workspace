'use strict';
/**
 * teamwork_sync.js — Teamwork -> ERP schedule INTERFACE (read-through).
 * Replicates a Teamwork project's schedule (task-lists + tasks with start/due/owner/status)
 * into the ERP project/task_list/task tables, tagged source='teamwork' so it never mixes
 * with the MC board tasks (source='mission-control-md'). Teamwork stays authoritative; this
 * never writes back to Teamwork. Idempotent + self-healing (prunes teamwork rows no longer
 * in the pull), same pattern as bamboo_sync.js.
 *
 * Creds (secrets.json or env): TEAMWORK_TOKEN / teamwork_token, TEAMWORK_BASE / teamwork_base.
 * Run:  node erp-foundation/teamwork_sync.js [projectId]           # dry-run (default 902146 = BLK3 Flight)
 *       node erp-foundation/teamwork_sync.js [projectId] --apply   # write the mirror (audited)
 */
const fs = require('fs');
const path = require('path');
const os = require('os');
const { openErp } = require('./dal');

const DB = path.join(__dirname, 'mc.db');
const APPLY = process.argv.includes('--apply');
const PROJECT_ID = String((process.argv.find(a => /^\d+$/.test(a))) || '902146'); // 902146 = Blk3 Flight

function creds() {
  let s = {};
  try { s = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.openclaw', 'secrets.json'), 'utf8')); } catch {}
  return {
    token: process.env.TEAMWORK_TOKEN || s.teamwork_token,
    base: (process.env.TEAMWORK_BASE || s.teamwork_base || 'https://exosaerospace.teamwork.com').replace(/\/$/, ''),
  };
}

async function twFetch(base, token, urlPath) {
  const auth = Buffer.from(`${token}:x`).toString('base64');
  const r = await fetch(base + urlPath, { headers: { Authorization: `Basic ${auth}`, Accept: 'application/json' } });
  if (!r.ok) throw new Error(`Teamwork ${urlPath} -> HTTP ${r.status}`);
  return r.json();
}

// page through a v3 collection endpoint
async function twAll(base, token, pathBase, key) {
  let page = 1, out = [];
  for (;;) {
    const sep = pathBase.includes('?') ? '&' : '?';
    const d = await twFetch(base, token, `${pathBase}${sep}page=${page}&pageSize=250`);
    const rows = d[key] || [];
    out = out.concat(rows);
    const pg = (d.meta && d.meta.page) || {};
    if (!pg.hasMore && !(pg.pageCount && page < pg.pageCount)) break;
    if (rows.length === 0) break;
    page++;
    if (page > 40) break; // safety
  }
  return out;
}

const mapState = s => (String(s || '').toLowerCase() === 'completed') ? 'Done' : 'Open';
function ownerOf(t) {
  const u = (t.assigneeUsers && t.assigneeUsers[0]) || null;
  if (u) return [u.firstName, u.lastName].filter(Boolean).join(' ') || null;
  return null;
}

async function main() {
  const { token, base } = creds();
  if (!token) { console.log('Missing Teamwork token (secrets.json teamwork_token or TEAMWORK_TOKEN).'); process.exit(1); }

  const proj = (await twFetch(base, token, `/projects/${PROJECT_ID}.json`)).project || {};
  console.log(`Teamwork project ${PROJECT_ID}: "${proj.name || '?'}"`);
  const lists = await twAll(base, token, `/projects/api/v3/projects/${PROJECT_ID}/tasklists.json`, 'tasklists');
  const tasks = await twAll(base, token, `/projects/api/v3/projects/${PROJECT_ID}/tasks.json`, 'tasks');
  console.log(`  ${lists.length} task-lists, ${tasks.length} tasks in the Teamwork schedule.`);

  if (!APPLY) {
    console.log('\nDRY-RUN (no writes). Would mirror into the ERP:');
    console.log(`  project tw-${PROJECT_ID} + ${lists.length} task_lists + ${tasks.length} tasks (source=teamwork).`);
    tasks.slice(0, 6).forEach(t => console.log(`   - ${(t.name || '').slice(0, 46)}  [${t.status}]  ${t.startDate || '?'} -> ${t.dueDate || '?'}`));
    console.log('   Re-run with --apply to write (audited).');
    return;
  }

  const erp = openErp(DB, { actor: 'teamwork-sync@exosaero.com', agent: 'teamwork-sync' });
  const projId = 'tw-' + PROJECT_ID;
  erp.upsertProject({ id: projId, name: proj.name || `Teamwork ${PROJECT_ID}`, status: proj.status || 'active', source: 'teamwork', teamwork_id: PROJECT_ID });
  for (const l of lists) erp.upsertTaskList({ id: 'tw-tl-' + l.id, project_id: projId, name: l.name, source: 'teamwork', teamwork_id: l.id });
  for (const t of tasks) {
    erp.upsertTask({
      id: 'tw-task-' + t.id, project_id: projId,
      task_list_id: t.tasklistId ? 'tw-tl-' + t.tasklistId : null,
      title: t.name, state: mapState(t.status), owner: ownerOf(t),
      due_date: t.dueDate || null, priority: t.priority || null, category: 'schedule',
      description: t.description || null, source: 'teamwork',
      startDate: t.startDate || null, progress: t.progress ?? null,
      parentTaskId: t.parentTaskId || null, tw_status: t.status, teamwork_id: t.id,
    });
  }

  // ── RECONCILE: prune teamwork rows no longer in the pull (mirror == Teamwork) ──
  const keepTask = new Set(tasks.map(t => 'tw-task-' + t.id));
  const keepList = new Set(lists.map(l => 'tw-tl-' + l.id));
  let pruned = { task: 0, list: 0 };
  for (const row of erp.listTasksBySource('teamwork')) if (!keepTask.has(row.id) && erp.deleteTask(row.id)) pruned.task++;
  for (const row of erp.getProjectSchedule(projId).lists) if (!keepList.has(row.id) && erp.deleteTaskList(row.id)) pruned.list++;

  console.log(`\n✓ Mirrored Teamwork -> ERP: project ${projId}, ${lists.length} task-lists, ${tasks.length} tasks (audited; Teamwork authoritative).`);
  if (pruned.task || pruned.list) console.log(`  Reconciled (pruned stale): ${pruned.task} tasks, ${pruned.list} task-lists.`);
  erp.close();
}

main().catch(e => { console.error('teamwork_sync failed:', e.message); process.exit(1); });
