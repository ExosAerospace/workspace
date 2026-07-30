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
// Governance: correlation-id event log (Four Pillars -- Searchable Logs).
// Soft dependency: never let logging break a data write.
let govlog = null;
try { govlog = require('../governance/govlog'); } catch (_) { /* governance optional */ }

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
  // Correlation id: one logical agent run threads through every audit row it
  // writes, and into governance/events.jsonl. Caller passes opts.correlationId
  // (or opts.run from govlog.newRun); otherwise a per-session id is minted.
  const run = opts.run
    || (govlog ? govlog.newRun(opts.agent || 'erp-dal') : { agent: opts.agent || 'erp-dal', run_id: 'erp-' + Date.now().toString(36) });
  const correlationId = opts.correlationId || run.run_id;

  function audit(entity, id, action, before, after) {
    db.run(
      'INSERT INTO audit_log (actor, ts, entity, entity_id, action, before_json, after_json, correlation_id) VALUES (?,?,?,?,?,?,?,?)',
      actor, new Date().toISOString(), entity, String(id), action,
      before == null ? null : JSON.stringify(before),
      after == null ? null : JSON.stringify(after),
      correlationId
    );
  }

  /** Run a mutation + its audit row atomically, then emit a correlated event. */
  function writeAudited(entity, id, action, before, after, mutate) {
    const v = db.tx(() => { mutate(); audit(entity, id, action, before, after); });
    if (govlog) { try { govlog.event(run, action, 'ok', '', { entity, id: String(id), correlation_id: correlationId }); } catch (_) {} }
    return v;
  }

  return {
    driver: db.driver,
    correlationId,   // the trace id for everything this handle writes

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

    // ---- HR core (Phase 1): People domain, all mutations audited ----
    // NOTE: PII columns (comp_band, emergency_contact) are intentionally NOT written here —
    // they stay null until the CUI-scoped Azure Government host is live (plan §5A). Structural
    // org data (name, title, department, reporting line, status) is non-PII and safe on ExoMac.
    upsertOrgUnit(o) {
      if (!o || !o.id) throw new Error('upsertOrgUnit requires id');
      const id = String(o.id);
      const before = db.get('SELECT * FROM org_unit WHERE id = ?', id) || null;
      writeAudited('org_unit', id, before ? 'update' : 'insert', before, o, () => {
        db.run('INSERT INTO org_unit (id,name,parent_id,raw_json) VALUES (?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET name=excluded.name, parent_id=excluded.parent_id, raw_json=excluded.raw_json',
          id, o.name ?? null, o.parent_id ?? null, JSON.stringify(o));
      });
      return db.get('SELECT * FROM org_unit WHERE id = ?', id);
    },
    upsertPosition(p) {
      if (!p || !p.id) throw new Error('upsertPosition requires id');
      const id = String(p.id);
      const before = db.get('SELECT * FROM position WHERE id = ?', id) || null;
      writeAudited('position', id, before ? 'update' : 'insert', before, p, () => {
        db.run('INSERT INTO position (id,title,org_unit_id,raw_json) VALUES (?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET title=excluded.title, org_unit_id=excluded.org_unit_id, raw_json=excluded.raw_json',
          id, p.title ?? null, p.org_unit_id ?? null, JSON.stringify(p));
      });
      return db.get('SELECT * FROM position WHERE id = ?', id);
    },
    upsertEmployee(e) {
      if (!e || !e.id) throw new Error('upsertEmployee requires id');
      const id = String(e.id);
      const before = db.get('SELECT * FROM employee WHERE id = ?', id) || null;
      writeAudited('employee', id, before ? 'update' : 'insert', before, e, () => {
        db.run('INSERT INTO employee (id,user_id,org_unit_id,position_id,manager_id,full_name,employment_status,start_date,raw_json) ' +
          'VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id, org_unit_id=excluded.org_unit_id, ' +
          'position_id=excluded.position_id, manager_id=excluded.manager_id, full_name=excluded.full_name, ' +
          'employment_status=excluded.employment_status, start_date=excluded.start_date, raw_json=excluded.raw_json',
          id, e.user_id ?? null, e.org_unit_id ?? null, e.position_id ?? null, e.manager_id ?? null,
          e.full_name ?? null, e.employment_status ?? 'Active', e.start_date ?? null, JSON.stringify(e));
      });
      return db.get('SELECT * FROM employee WHERE id = ?', id);
    },
    listEmployees() {
      return db.all('SELECT e.id,e.full_name,e.employment_status,p.title,o.name AS org_unit,e.manager_id ' +
        'FROM employee e LEFT JOIN position p ON p.id=e.position_id LEFT JOIN org_unit o ON o.id=e.org_unit_id ' +
        'ORDER BY o.name, e.full_name');
    },
    orgUnits() { return db.all('SELECT id,name,parent_id FROM org_unit ORDER BY name'); },

    // ---- audit inspection ----
    recentAudit({ limit = 10 } = {}) {
      return db.all('SELECT id,actor,ts,entity,entity_id,action FROM audit_log ORDER BY id DESC LIMIT ?', limit);
    },

    close() { db.close(); },
  };
}

module.exports = { openErp };
