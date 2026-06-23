'use strict';
/**
 * dal.js -- thin data-access layer (Phase 0 stub).
 *
 * Purpose: demonstrate the audit pattern, NOT full coverage. Every mutation
 * goes through writeAudited(), which captures a before/after snapshot and
 * appends an immutable audit_log row in the SAME transaction as the data write.
 * This is the chokepoint the §5A RBAC/audit design requires; the eventual
 * server.js audit middleware should call into helpers shaped like these.
 *
 * Usage:
 *   const { openErp } = require('./dal');
 *   const erp = openErp('./mc.db', { actor: 'jquinn@exosaero.com' });
 *   erp.getCompanies({ limit: 5 });
 *   erp.upsertDeal({ id: 'EXOS-0001', stage: 'Engaged' });
 *   erp.listTasks({ state: 'In Progress' });
 *   erp.close();
 *
 * Driver: prefers better-sqlite3, falls back to node:sqlite (same adapter
 * shape as migrate.js).
 */
const fs = require('fs');

function openRaw(file) {
  try {
    const Database = require('better-sqlite3');
    const db = new Database(file);
    return {
      driver: 'better-sqlite3',
      all: (sql, ...a) => db.prepare(sql).all(...a),
      get: (sql, ...a) => db.prepare(sql).get(...a),
      run: (sql, ...a) => db.prepare(sql).run(...a),
      tx: (fn) => db.transaction(fn)(),
      close: () => db.close(),
    };
  } catch (_) { /* fall through */ }
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(file);
  return {
    driver: 'node:sqlite',
    all: (sql, ...a) => db.prepare(sql).all(...a),
    get: (sql, ...a) => db.prepare(sql).get(...a),
    run: (sql, ...a) => db.prepare(sql).run(...a),
    // node:sqlite has no transaction() helper; emulate with explicit BEGIN/COMMIT.
    tx: (fn) => {
      db.exec('BEGIN');
      try { const v = fn(); db.exec('COMMIT'); return v; }
      catch (e) { db.exec('ROLLBACK'); throw e; }
    },
    close: () => db.close(),
  };
}

function openErp(file, opts = {}) {
  if (!fs.existsSync(file)) throw new Error(`mc.db not found at ${file} -- run migrate.js first`);
  const db = openRaw(file);
  db.run('PRAGMA foreign_keys = ON;');
  const actor = opts.actor || 'system';

  function audit(entity, id, action, before, after) {
    db.run(
      'INSERT INTO audit_log (actor, ts, entity, entity_id, action, before_json, after_json) VALUES (?,?,?,?,?,?,?)',
      actor, new Date().toISOString(), entity, String(id), action,
      before == null ? null : JSON.stringify(before),
      after == null ? null : JSON.stringify(after)
    );
  }

  /** Run a mutation + its audit row atomically. */
  function writeAudited(entity, id, action, before, after, mutate) {
    return db.tx(() => { mutate(); audit(entity, id, action, before, after); });
  }

  return {
    driver: db.driver,

    // ---- reads (no audit) ----
    getCompanies({ limit = 50 } = {}) {
      return db.all('SELECT id,name,category,tier FROM company ORDER BY name LIMIT ?', limit);
    },
    getDeal(id) { return db.get('SELECT * FROM deal WHERE id = ?', id); },
    listTasks({ state, owner, limit = 100 } = {}) {
      const where = [], args = [];
      if (state) { where.push('state = ?'); args.push(state); }
      if (owner) { where.push('owner = ?'); args.push(owner); }
      const sql = 'SELECT id,title,state,owner,priority FROM task'
        + (where.length ? ' WHERE ' + where.join(' AND ') : '')
        + ' ORDER BY priority DESC LIMIT ?';
      return db.all(sql, ...args, limit);
    },

    // ---- writes (audited) ----
    /** Insert or update a deal; audits before/after. */
    upsertDeal(deal) {
      if (!deal || deal.id == null) throw new Error('upsertDeal requires deal.id');
      const id = String(deal.id);
      const before = db.get('SELECT * FROM deal WHERE id = ?', id) || null;
      const action = before ? 'update' : 'insert';
      writeAudited('deal', id, action, before, deal, () => {
        if (before) {
          db.run('UPDATE deal SET stage = COALESCE(?,stage), status = COALESCE(?,status), owner = COALESCE(?,owner), next_action = COALESCE(?,next_action) WHERE id = ?',
            deal.stage ?? null, deal.status ?? null, deal.owner ?? null, deal.next_action ?? null, id);
        } else {
          db.run('INSERT INTO deal (id,company_id,contact_id,owner,stage,status,raw_json) VALUES (?,?,?,?,?,?,?)',
            id, deal.company_id ?? null, deal.contact_id ?? null, deal.owner ?? null,
            deal.stage ?? null, deal.status ?? null, JSON.stringify(deal));
        }
      });
      return db.get('SELECT * FROM deal WHERE id = ?', id);
    },

    /** Update a task's state; audits before/after. */
    setTaskState(id, state, newOwner) {
      const before = db.get('SELECT * FROM task WHERE id = ?', String(id));
      if (!before) throw new Error(`task ${id} not found`);
      const after = { ...before, state, owner: newOwner ?? before.owner };
      writeAudited('task', id, 'update', before, after, () => {
        db.run('UPDATE task SET state = ?, owner = COALESCE(?,owner) WHERE id = ?', state, newOwner ?? null, String(id));
      });
      return after;
    },

    // ---- audit inspection ----
    recentAudit({ limit = 10 } = {}) {
      return db.all('SELECT id,actor,ts,entity,entity_id,action FROM audit_log ORDER BY id DESC LIMIT ?', limit);
    },

    close() { db.close(); },
  };
}

module.exports = { openErp };
