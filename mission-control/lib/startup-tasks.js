'use strict';
// ── ENTITY STARTUP BOARD (containerized MC cells only; Jon 2026-10-22) ─────────────────────
// A new organization's task board is its Mission Control bring-up plan: the base tasks plus one
// detailed setup task per feature switched on in Settings > Features. sync() re-runs at startup
// and after every Settings save:
//   - feature turned on  → its setup task is added (To Do)
//   - feature turned off → its task is removed if nobody touched it, else set Cancelled with a note
//   - old SAMPLE tasks (source 'sample') are removed
// Cells without a database also get a file-backed task store (handle()), so users can work the
// board: change state/owner/due date, add tasks and notes. Exos MC never loads this module.
const fs = require('fs');
const path = require('path');

function create(entity, dataDir, playbookFile) {
  if (!entity || entity === 'exos') return null;
  const tasksFile = path.join(dataDir, 'tasks.json');
  const notesFile = path.join(dataDir, 'task-notes.json');
  const selFile = path.join(dataDir, 'mc-feature-selections.json');
  const catFile = path.join(dataDir, 'mc-feature-catalog.json');
  const readJson = (f, d) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return d; } };
  const writeJson = (f, v) => { const tmp = f + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(v, null, 1)); fs.renameSync(tmp, f); };
  const now = () => new Date().toISOString();
  const loadTasks = () => { const d = readJson(tasksFile, { tasks: [] }); return Array.isArray(d) ? { tasks: d } : (d.tasks ? d : { tasks: [] }); };
  const saveTasks = d => { d.generated_display = 'Startup board'; d.updated_at = now(); writeJson(tasksFile, d); };

  function featureNames() {
    const cat = readJson(catFile, {}); const m = {};
    for (const s of ['native', 'integrations']) for (const g of (cat[s] || [])) for (const it of g.items) m[it.id] = it.name;
    return m;
  }

  function describe(p, names, pb) {
    const L = [`Phase ${p.phase}: ${(pb.phases || {})[p.phase] || ''}`, '', p.why, ''];
    if (p.owner_role) L.push('Suggested owner: ' + p.owner_role, '');
    if (p.prereq && p.prereq.length) L.push('Do first: ' + p.prereq.map(id => names[id] || id).join(', '), '');
    L.push('Steps:'); p.steps.forEach((s, i) => L.push(`${i + 1}. ${s}`));
    L.push('', 'Done when: ' + p.done, '', 'Help: ' + p.rep, '', 'Questions: add a note on this task and ' + pb.rep_label + ' answers here.');
    return L.join('\n');
  }

  function sync(who) {
    const pb = readJson(playbookFile, null);
    if (!pb) return { ok: false, error: 'playbook missing' };
    const t = ((readJson(selFile, {}).tenants || {})[entity]) || {};
    const enabled = new Set(Array.isArray(t.enabled) ? t.enabled : []);
    const names = featureNames();
    const notes = readJson(notesFile, []);
    const touched = id => notes.some(n => n.subject === 'task:' + id);
    const d = loadTasks();
    const byId = new Map(d.tasks.map(x => [String(x.id), x]));
    const want = new Map();
    const label = p => `Startup ${p.phase} · ${p.title}`;
    // Phase first, then rank inside the phase: plan → people & roles → platform → … → go-live.
    const prio = p => 1000 - p.phase * 100 - (p.rank ?? 5);
    for (const [k, p] of Object.entries(pb.base)) want.set('SU-' + k, { p, title: label(p) });
    for (const id of enabled) { const p = pb.features[id]; if (p) want.set('SU-' + id, { p, title: label(p), feature: id }); }
    let added = 0, removed = 0, cancelled = 0, revived = 0, refreshed = 0;
    d.tasks = d.tasks.filter(x => { if (x.source === 'sample') { removed++; return false; } return true; });
    for (const [id, w] of want) {
      const cur = byId.get(id);
      if (!cur) {
        d.tasks.push({ id, title: w.title, state: 'To Do', owner: 'Team', category: 'Startup', priority: prio(w.p), suggested_owner: w.p.owner_role || null,
          due_date: null, description: describe(w.p, names, pb), source: 'startup', tags: ['startup', 'group'].concat(w.feature ? ['feature:' + w.feature] : []),
          created_at: now(), updated_at: now() });
        added++;
      } else if (cur.source === 'startup' && cur.state === 'Cancelled' && cur.cancel_reason === 'feature-off') {
        cur.state = 'To Do'; delete cur.cancel_reason; cur.updated_at = now(); revived++;
      }
      // Playbook updates reach tasks nobody has started yet (wording, order, suggested owner).
      if (cur && cur.source === 'startup' && cur.state === 'To Do' && !touched(id)) {
        const desc = describe(w.p, names, pb);
        if (cur.title !== w.title || cur.description !== desc || cur.priority !== prio(w.p)) {
          Object.assign(cur, { title: w.title, description: desc, priority: prio(w.p), suggested_owner: w.p.owner_role || null, updated_at: now() }); refreshed++;
        }
      }
    }
    d.tasks = d.tasks.filter(x => {
      if (x.source !== 'startup' || want.has(String(x.id))) return true;
      const untouched = x.state === 'To Do' && !touched(x.id);
      if (untouched) { removed++; return false; }
      if (x.state !== 'Cancelled' && x.state !== 'Done') { x.state = 'Cancelled'; x.cancel_reason = 'feature-off'; x.updated_at = now(); cancelled++; }
      return true;
    });
    d.tasks.sort((a, b) => (b.priority || 0) - (a.priority || 0) || String(a.title).localeCompare(String(b.title), undefined, { numeric: true }));
    saveTasks(d);
    return { ok: true, added, removed, cancelled, revived, refreshed, total: d.tasks.length, by: who || 'system' };
  }

  // ── File-backed task API (only when the cell has no database) ──
  function handle(req, res, session) {
    const p = req.url.split('?')[0];
    const send = (code, v) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(v)); };
    const body = fn => { let b = ''; req.on('data', c => b += c); req.on('end', () => { let j; try { j = JSON.parse(b || '{}'); } catch { return send(400, { error: 'bad json' }); } fn(j); }); };
    const visible = t => !session || session.role !== 'member' || t.owner === 'Team' || (t.tags || []).includes('group')
      || (t.assigned_email || '').toLowerCase() === (session.email || '').toLowerCase() || t.owner === session.name || t.owner === session.email;
    const who = (session && (session.name || session.email)) || 'user';
    if (p === '/api/tasks' && req.method === 'GET') { send(200, loadTasks().tasks.filter(visible).map(({ description, ...r }) => r)); return true; }
    if (p === '/api/task-desc' && req.method === 'GET') {
      const id = new URLSearchParams(req.url.split('?')[1] || '').get('id');
      const t = loadTasks().tasks.find(x => String(x.id) === String(id));
      send(200, { id, description: t && visible(t) ? (t.description || '') : '' }); return true;
    }
    if (p === '/api/tasks' && req.method === 'POST') {
      body(j => { const d = loadTasks(); const t = { ...j, id: 'T-' + Date.now().toString(36), state: j.state || 'To Do', priority: j.priority ?? 50, source: 'user', created_at: now(), updated_at: now() };
        d.tasks.push(t); saveTasks(d); send(201, t); }); return true;
    }
    if (p === '/api/tasks' && req.method === 'PATCH') {
      body(({ id, ...f }) => { const d = loadTasks(); const t = d.tasks.find(x => String(x.id) === String(id));
        if (!t || !visible(t)) return send(404, { error: 'not found' });
        const ch = [];
        for (const k of ['state', 'owner', 'title', 'due_date', 'priority', 'category']) if (k in f && f[k] !== t[k]) ch.push(`${k}: ${t[k] ?? '—'} → ${f[k] ?? '—'}`);
        delete f.id; delete f.source; Object.assign(t, f, { updated_at: now() });
        if (f.state === 'Done') t.completed_at = now(); else if (f.state) t.completed_at = null;
        if (f.state && f.state !== 'Cancelled') delete t.cancel_reason;
        saveTasks(d);
        if (ch.length) { const n = readJson(notesFile, []); n.push({ id: 'N-' + Date.now().toString(36), type: 'task_update', subject: 'task:' + id, body: '[Update] ' + ch.join(' | '), owner: who, created_at: now() }); writeJson(notesFile, n); }
        send(200, t); }); return true;
    }
    if (p.startsWith('/api/tasks/delete') && req.method === 'POST') {
      if (!session || !['admin', 'manager'].includes(session.role)) { send(403, { error: 'Only an admin or manager can delete tasks' }); return true; }
      body(j => { const ids = new Set([].concat(j.id || j.ids || []).map(String)); const d = loadTasks(); d.tasks = d.tasks.filter(x => !ids.has(String(x.id))); saveTasks(d); send(200, { success: true }); }); return true;
    }
    if (p === '/api/tasks/updates' && req.method === 'GET') {
      const id = new URLSearchParams(req.url.split('?')[1] || '').get('task_id');
      const t = loadTasks().tasks.find(x => String(x.id) === String(id));
      send(200, t && visible(t) ? readJson(notesFile, []).filter(n => n.subject === 'task:' + id) : []); return true;
    }
    if (p === '/api/tasks/updates' && req.method === 'POST') {
      body(j => { const n = readJson(notesFile, []); const row = { id: 'N-' + Date.now().toString(36), type: 'task_note', subject: 'task:' + j.task_id, body: String(j.body || '').slice(0, 20000), owner: who, created_at: now() };
        n.push(row); writeJson(notesFile, n); send(201, row); }); return true;
    }
    return false;
  }

  return { sync, handle };
}

module.exports = { create };
