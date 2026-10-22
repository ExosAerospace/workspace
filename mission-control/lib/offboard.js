'use strict';
// ── OFFBOARD / HAND OFF A PERSON (Jon 2026-10-22) ────────────────────────────────────────────
// One admin action removes someone's access and hands their open work to a successor:
//   1. MC account deactivated + every session killed (immediately)
//   2. open tasks (not Done/Cancelled) they own or are assigned → successor; multi-owner "A+B" keeps
//      the other names; a timeline note on each task records the hand-off
//   3. open Decision cards assigned to / awaiting them → successor
//   4. secure access: entity cells — scripts/mc_cell_onboard_exo3.py access-sync removes the email
//      within 5 min; Exos MC — the response lists the Cloudflare step (Guard/CLI does the revoke)
// dry_run returns the exact list without changing anything. Works on Supabase tasks (Exos MC) and the
// file-backed task store (DB-less entity cells).
const fs = require('fs');
const path = require('path');

const OPEN = t => !['Done', 'Cancelled', 'Canceled', 'Archived'].includes(t.state);

function matches(t, v) {
  const em = String(v.email || '').toLowerCase();
  if (em && String(t.assigned_email || '').toLowerCase().split(/[,+\s]+/).includes(em)) return true;
  return String(t.owner || '').split('+').map(s => s.trim()).some(p => p && (p === v.name || p.toLowerCase() === em));
}

function handOff(t, v, s) {
  const parts = String(t.owner || '').split('+').map(x => x.trim()).filter(Boolean)
    .filter(p => p !== v.name && p.toLowerCase() !== String(v.email || '').toLowerCase());
  if (!parts.includes(s.name)) parts.push(s.name);
  const owner = parts.join('+');
  const emails = String(t.assigned_email || '').toLowerCase().split(/[,+\s]+/).filter(e => e && e !== String(v.email).toLowerCase());
  if (!emails.includes(String(s.email).toLowerCase())) emails.push(String(s.email).toLowerCase());
  return { owner, assigned_to: owner, assigned_email: emails.join(',') };
}

async function run(o) {
  const { victim: v, successor: s, dryRun, who, users, saveUsers, sessions, saveSessions, supabaseEnabled, supabaseRequest, supabaseGetAll,
    dataDir, loadDecisions, saveDecisions } = o;
  const out = { person: { id: v.id, name: v.name, email: v.email }, successor: { id: s.id, name: s.name, email: s.email }, dry_run: !!dryRun,
    tasks: [], decisions: [], access: '' };
  const note = `[Update] owner: ${v.name} → ${s.name} (hand-off: ${v.name} offboarded by ${who})`;

  // tasks
  if (supabaseEnabled) {
    const all = (await supabaseGetAll('tasks?select=id,title,owner,assigned_to,assigned_email,state')).data;
    for (const t of (all || []).filter(t => OPEN(t) && matches(t, v))) {
      out.tasks.push({ id: t.id, title: t.title });
      if (dryRun) continue;
      await supabaseRequest('PATCH', `tasks?id=eq.${encodeURIComponent(t.id)}`, { ...handOff(t, v, s), updated_at: new Date().toISOString() });
      await supabaseRequest('POST', 'activities', { type: 'task_update', subject: `task:${t.id}`, body: note, owner: who, status: 'completed' });
    }
  } else {
    const tf = path.join(dataDir, 'tasks.json'), nf = path.join(dataDir, 'task-notes.json');
    let d; try { d = JSON.parse(fs.readFileSync(tf, 'utf8')); } catch { d = { tasks: [] }; }
    const list = Array.isArray(d) ? d : d.tasks || [];
    let notes; try { notes = JSON.parse(fs.readFileSync(nf, 'utf8')); } catch { notes = []; }
    for (const t of list.filter(t => OPEN(t) && matches(t, v))) {
      out.tasks.push({ id: t.id, title: t.title });
      if (dryRun) continue;
      Object.assign(t, handOff(t, v, s), { updated_at: new Date().toISOString() });
      notes.push({ id: 'N-' + Date.now().toString(36) + out.tasks.length, type: 'task_update', subject: 'task:' + t.id, body: note, owner: who, created_at: new Date().toISOString() });
    }
    if (!dryRun && out.tasks.length) {
      const w = (f, val) => { fs.writeFileSync(f + '.tmp', JSON.stringify(val, null, 1)); fs.renameSync(f + '.tmp', f); };
      w(tf, d); w(nf, notes);
    }
  }

  // open decision cards
  if (loadDecisions) {
    const decs = loadDecisions(); const em = String(v.email).toLowerCase(); let changed = false;
    for (const dc of decs) {
      const st = dc.status || 'open';
      if (!['open', 'pending', 'delegated', 'reassigning'].includes(st)) continue;
      const hit = ['assignedTo', 'approver'].filter(k => String(dc[k] || '').toLowerCase() === em);
      if (!hit.length) continue;
      out.decisions.push({ id: dc.id, title: dc.title });
      if (dryRun) continue;
      for (const k of hit) dc[k] = s.email;
      dc.reassignedFrom = v.email; dc.updated = new Date().toISOString(); changed = true;
    }
    if (changed) saveDecisions(decs);
  }

  // account + sessions last, so a failure above leaves the person's work intact and visible
  if (!dryRun) {
    const u = users.find(x => x.id === v.id);
    if (u) { u.active = false; u.offboarded_at = new Date().toISOString(); u.offboarded_by = who; u.successor_id = s.id; saveUsers(users); }
    for (const [tok, sess] of sessions.entries()) if (sess.userId === v.id) sessions.delete(tok);
    saveSessions();
  }
  const ent = process.env.ENTITY && process.env.ENTITY !== 'exos';
  out.access = ent ? 'Secure access removed automatically within 5 minutes.'
    : 'Exos MC: run python3 scripts/mc_cell_onboard_exo3.py access-sync --entity exos --remove-only --apply (runs every 5 min) to drop them from Cloudflare.';
  return out;
}

module.exports = { run, matches, handOff };
