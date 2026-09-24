'use strict';
// outbox.js — durable write queue for Mission Control.
//
// When Supabase is unreachable, MC writes (POST/PATCH/DELETE) can't persist and would be
// lost. This append-only journal captures those mutations locally and replays them once the
// DB is back, so no edit is dropped during an outage. Healthy-path writes never touch this —
// entries are only enqueued when a write actually fails.
//
// Storage: one JSON object per line (JSONL) at data/outbox.jsonl. Single-threaded MC, so no
// locking; writes go temp+rename for whole-file rewrites, appendFileSync for enqueue.

const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'data', 'outbox.jsonl');
const MAX_TRIES = 25; // after this many failed replays, park as 'dead' so we never loop forever

function _ensureDir() {
  try { fs.mkdirSync(path.dirname(FILE), { recursive: true }); } catch (_) {}
}

function _readAll() {
  try {
    return fs.readFileSync(FILE, 'utf8').split('\n').filter(Boolean).map(l => {
      try { return JSON.parse(l); } catch (_) { return null; }
    }).filter(Boolean);
  } catch (_) { return []; }
}

function _writeAll(rows) {
  _ensureDir();
  const tmp = FILE + '.tmp';
  fs.writeFileSync(tmp, rows.map(r => JSON.stringify(r)).join('\n') + (rows.length ? '\n' : ''));
  fs.renameSync(tmp, FILE);
}

// Record a failed mutation for later replay. Only non-GET methods belong here.
function enqueue(method, pathAndQuery, body) {
  if (!method || method === 'GET') return null;
  _ensureDir();
  const rec = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    ts: new Date().toISOString(),
    method, path: pathAndQuery, body: body || null,
    tries: 0, status: 'pending',
  };
  try { fs.appendFileSync(FILE, JSON.stringify(rec) + '\n'); } catch (_) {}
  return rec.id;
}

function pendingCount() {
  return _readAll().filter(r => r.status === 'pending').length;
}

function stats() {
  const rows = _readAll();
  return {
    pending: rows.filter(r => r.status === 'pending').length,
    dead: rows.filter(r => r.status === 'dead').length,
    total: rows.length,
  };
}

// Replay every pending mutation through `sender(method, path, body) -> {status}` (a raw
// Supabase call that must NOT re-enqueue on failure). Returns {applied, stillPending, dead}.
// Idempotent by construction for PATCH/DELETE-by-id; POST re-creates the row on recovery.
async function replay(sender) {
  const rows = _readAll();
  const pending = rows.filter(r => r.status === 'pending');
  if (!pending.length) return { applied: 0, stillPending: 0, dead: 0 };
  let applied = 0, dead = 0;
  for (const r of pending) {
    let ok = false;
    try {
      const res = await sender(r.method, r.path, r.body);
      ok = res && res.status >= 200 && res.status < 300;
    } catch (_) { ok = false; }
    if (ok) { r.status = 'done'; r.done_ts = new Date().toISOString(); applied++; }
    else {
      r.tries = (r.tries || 0) + 1;
      if (r.tries >= MAX_TRIES) { r.status = 'dead'; dead++; }
    }
  }
  // Keep only still-actionable rows: drop 'done', retain 'pending'/'dead' (dead kept for audit).
  const survivors = rows.filter(r => r.status !== 'done');
  _writeAll(survivors);
  return { applied, stillPending: survivors.filter(r => r.status === 'pending').length, dead };
}

module.exports = { enqueue, replay, pendingCount, stats, FILE };
