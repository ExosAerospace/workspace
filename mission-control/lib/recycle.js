'use strict';
// ── MC RECYCLE BIN (exo3 remedy 2026-09-28, recoverable deletes) ─────────────────────────
// Every Mission Control delete writes the FULL record + metadata here BEFORE the delete runs.
// Store: mission-control/data/recycle-bin/YYYY-MM-DD.jsonl (one JSON entry per line, per day).
// Deleted upload binaries are MOVED to recycle-bin/files/<recycle_id>__<stored_name> instead of
// being unlinked. Retention 90 days: purge() only removes recycle-bin day files / parked binaries.
// Restore: python3 scripts/mc_restore.py --list | --restore <recycle_id> [--force]
//
// Entry shape:
//   { recycle_id, deleted_at, type, id, who, route, source, record, extra }
//   source = { kind:'supabase', table, key }                     (row snapshot, upsert on restore)
//          | { kind:'json', file, path:[...], key }               (file relative to mission-control/;
//                                                                  path = keys to the array, [] = top level)
// Fail-closed: if the snapshot cannot be written, record() throws and the caller MUST NOT delete.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MC_DIR = path.join(__dirname, '..');
const RECYCLE_DIR = path.join(MC_DIR, 'data', 'recycle-bin');
const FILES_DIR = path.join(RECYCLE_DIR, 'files');
const RETENTION_DAYS = 90;

function _ensureDir(d) { fs.mkdirSync(d, { recursive: true, mode: 0o700 }); }

function whoOf(session) {
  if (!session) return 'system';
  return session.email || session.name || session.userId || 'unknown-session';
}

// Append one entry synchronously (durable before the caller deletes). Returns recycle_id.
function newId(now) {
  return 'rb_' + (now || new Date()).toISOString().replace(/[-:.TZ]/g, '').slice(0, 14) + '_' + crypto.randomBytes(4).toString('hex');
}

function record({ recycle_id: rid, type, id, record: rec, source, who, route, extra }) {
  if (!source || !source.kind) throw new Error('recycle: source required');
  _ensureDir(RECYCLE_DIR);
  const now = new Date();
  const recycle_id = rid || newId(now);
  const entry = {
    recycle_id, deleted_at: now.toISOString(), type: type || source.table || 'record',
    id: id == null ? null : String(id), who: who || 'system', route: route || null,
    source, record: rec === undefined ? null : rec, extra: extra || null,
  };
  const fp = path.join(RECYCLE_DIR, now.toISOString().slice(0, 10) + '.jsonl');
  const fd = fs.openSync(fp, 'a', 0o600);
  try { fs.writeSync(fd, JSON.stringify(entry) + '\n'); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  return recycle_id;
}

// Snapshot Supabase rows matching `filter` (e.g. "id=eq.123") and record each one.
// Throws if the snapshot read fails, so the caller refuses the delete. Returns recycle_ids.
async function snapshotSupabase(sbRequest, { table, filter, key, type, who, route, extra }) {
  const r = await sbRequest('GET', `${table}?${filter}`);
  if (!r || r.status >= 400 || !Array.isArray(r.data)) {
    throw new Error(`recycle: snapshot of ${table}?${filter} failed (status ${r && r.status})`);
  }
  const k = key || 'id';
  return r.data.map(row => record({
    type: type || table, id: row[k], record: row, who, route, extra,
    source: { kind: 'supabase', table, key: k },
  }));
}

// Snapshot then DELETE. Resolves the supabaseRequest result plus recycle_ids.
async function recycleThenDelete(sbRequest, opts) {
  const recycle_ids = await snapshotSupabase(sbRequest, opts);
  const res = await sbRequest('DELETE', `${opts.table}?${opts.filter}`);
  return Object.assign({}, res, { recycle_ids });
}

// Where parkFile() will put a file for a given recycle_id (relative to MC_DIR) — record this first.
function parkedPath(absPath, recycleId) { return path.relative(MC_DIR, path.join(FILES_DIR, recycleId + '__' + path.basename(absPath))); }

// Move a file into the recycle bin (instead of unlinking). Returns the parked path relative to MC_DIR.
function parkFile(absPath, recycleId) {
  if (!absPath || !fs.existsSync(absPath)) return null;
  _ensureDir(FILES_DIR);
  const dest = path.join(MC_DIR, parkedPath(absPath, recycleId));
  try { fs.renameSync(absPath, dest); }
  catch (e) { fs.copyFileSync(absPath, dest); fs.unlinkSync(absPath); }
  return path.relative(MC_DIR, dest);
}

// Remove recycle entries older than RETENTION_DAYS. Touches ONLY recycle-bin day files and
// parked binaries under recycle-bin/files. Returns { removedDays, removedFiles }.
function purge(days) {
  const keep = (days || RETENTION_DAYS) * 86400000;
  const cutoff = Date.now() - keep;
  const out = { removedDays: [], removedFiles: [] };
  if (!fs.existsSync(RECYCLE_DIR)) return out;
  for (const f of fs.readdirSync(RECYCLE_DIR)) {
    const m = /^(\d{4}-\d{2}-\d{2})\.jsonl$/.exec(f);
    if (m && Date.parse(m[1] + 'T23:59:59Z') < cutoff) { fs.unlinkSync(path.join(RECYCLE_DIR, f)); out.removedDays.push(f); }
  }
  if (fs.existsSync(FILES_DIR)) {
    for (const f of fs.readdirSync(FILES_DIR)) {
      const m = /^rb_(\d{8})/.exec(f);
      if (!m) continue;
      const d = Date.parse(`${m[1].slice(0, 4)}-${m[1].slice(4, 6)}-${m[1].slice(6, 8)}T23:59:59Z`);
      if (d < cutoff) { fs.unlinkSync(path.join(FILES_DIR, f)); out.removedFiles.push(f); }
    }
  }
  return out;
}

module.exports = { RECYCLE_DIR, FILES_DIR, RETENTION_DAYS, whoOf, newId, record, parkedPath, snapshotSupabase, recycleThenDelete, parkFile, purge };
