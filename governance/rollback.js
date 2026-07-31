'use strict';
/**
 * rollback.js -- Granular Rollback pillar for the ERP / systems-of-record class.
 *
 * The audit_log already stores before_json on every mutation, so a revert is a
 * replay of the prior state. This gives the ERP agent class a *defined,
 * tested* rollback path (Four Pillars requirement), addressable two ways:
 *
 *   - by audit id:        node rollback.js --id 3858
 *   - by correlation id:  node rollback.js --run 9f2a...   (reverts the whole
 *                         agent run, newest-first, atomically)
 *
 * Safety: dry-run by default. Pass --apply to actually write. Every rollback is
 * itself audited (action='rollback') under a new correlation id, so the revert
 * is as traceable as the original action. Never deletes audit history.
 *
 * Supported entities mirror dal.js (deal, task). Extend the REVERTERS map as the
 * DAL grows; an unsupported entity aborts rather than guessing.
 */
const path = require('path');
const { DatabaseSync } = require('node:sqlite');

const DB = process.env.MC_DB || path.join(__dirname, '..', 'erp-foundation', 'mc.db');

let govlog = null;
try { govlog = require('./govlog'); } catch (_) {}

// entity -> how to restore a `before` snapshot (and how to undo an insert)
const REVERTERS = {
  deal: {
    restore: (db, before) => db.prepare(
      'UPDATE deal SET stage=?, status=?, owner=?, next_action=? WHERE id=?'
    ).run(before.stage ?? null, before.status ?? null, before.owner ?? null, before.next_action ?? null, String(before.id)),
    undoInsert: (db, id) => db.prepare('DELETE FROM deal WHERE id=?').run(String(id)),
  },
  task: {
    restore: (db, before) => db.prepare(
      'UPDATE task SET state=?, owner=? WHERE id=?'
    ).run(before.state ?? null, before.owner ?? null, String(before.id)),
    undoInsert: (db, id) => db.prepare('DELETE FROM task WHERE id=?').run(String(id)),
  },
};

function loadRows(db, { id, run }) {
  if (id) return db.prepare('SELECT * FROM audit_log WHERE id=?').all(Number(id));
  if (run) return db.prepare('SELECT * FROM audit_log WHERE correlation_id=? ORDER BY id DESC').all(run);
  throw new Error('specify --id <auditId> or --run <correlationId>');
}

function revertRow(db, row, apply) {
  const rev = REVERTERS[row.entity];
  if (!rev) throw new Error(`no reverter for entity '${row.entity}' (audit id ${row.id})`);
  const before = row.before_json ? JSON.parse(row.before_json) : null;
  const plan = before
    ? `restore ${row.entity} ${row.entity_id} to pre-'${row.action}' state`
    : `undo insert of ${row.entity} ${row.entity_id} (delete row)`;
  if (!apply) return { audit_id: row.id, action: 'would ' + plan };
  if (before) rev.restore(db, before); else rev.undoInsert(db, row.entity_id);
  return { audit_id: row.id, action: plan };
}

function main() {
  const args = process.argv.slice(2);
  const get = (f) => { const i = args.indexOf(f); return i >= 0 ? args[i + 1] : null; };
  const apply = args.includes('--apply');
  const sel = { id: get('--id'), run: get('--run') };

  const db = new DatabaseSync(DB);
  db.exec('PRAGMA foreign_keys = ON;');
  const rows = loadRows(db, sel);
  if (!rows.length) { console.log('no matching audit rows'); return; }

  const trace = govlog ? govlog.newRun('rollback') : { run_id: 'rb-' + Date.now().toString(36) };
  const results = [];
  db.exec('BEGIN');
  try {
    for (const row of rows) {
      const r = revertRow(db, row, apply);
      results.push(r);
      if (apply) {
        db.prepare('INSERT INTO audit_log (actor, ts, entity, entity_id, action, before_json, after_json, correlation_id) VALUES (?,?,?,?,?,?,?,?)')
          .run('rollback', new Date().toISOString(), row.entity, String(row.entity_id), 'rollback',
               row.after_json, row.before_json, trace.run_id);
      }
    }
    db.exec(apply ? 'COMMIT' : 'ROLLBACK');
  } catch (e) { db.exec('ROLLBACK'); throw e; }

  if (govlog && apply) { try { govlog.event(trace, 'rollback', 'ok', '', { reverted: results.length }); } catch (_) {} }
  console.log(JSON.stringify({ mode: apply ? 'APPLIED' : 'DRY-RUN', reverted: results.length, results }, null, 2));
}

if (require.main === module) main();
module.exports = { revertRow, REVERTERS };
