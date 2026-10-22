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
    /** HR directory (read-through from the Bamboo mirror). Directory-level fields ONLY —
     *  no comp_band / emergency_contact / PII. Bamboo remains authoritative. */
    getEmployees() {
      return db.all(
        `SELECT e.id, e.full_name, e.employment_status,
                p.title AS position_title,
                o.name  AS department,
                e.org_unit_id, e.manager_id,
                m.full_name AS manager_name,
                json_extract(e.raw_json,'$.email')      AS work_email,
                json_extract(e.raw_json,'$.bamboo_id')  AS bamboo_id
           FROM employee e
           LEFT JOIN position  p ON p.id = e.position_id
           LEFT JOIN org_unit  o ON o.id = e.org_unit_id
           LEFT JOIN employee  m ON m.id = e.manager_id
          ORDER BY o.name IS NULL, o.name, e.full_name`);
    },
    getOrgUnits() {
      return db.all('SELECT id, name, parent_id FROM org_unit ORDER BY name');
    },
    /** Resolve an employee (and their manager's email) by work email — for approval routing. */
    getEmployeeByEmail(email) {
      return db.get(
        "SELECT e.id, e.full_name, json_extract(e.raw_json,'$.email') AS work_email, e.manager_id, " +
        "m.full_name AS manager_name, json_extract(m.raw_json,'$.email') AS manager_email " +
        "FROM employee e LEFT JOIN employee m ON m.id = e.manager_id " +
        "WHERE lower(json_extract(e.raw_json,'$.email')) = lower(?)", String(email || ''));
    },
    getPositions() {
      return db.all('SELECT id, title, org_unit_id FROM position ORDER BY title');
    },

    // ---- HR reconcile deletes (audited) — used by bamboo_sync to keep the mirror == Bamboo ----
    deleteEmployee(id) {
      id = String(id);
      const before = db.get('SELECT * FROM employee WHERE id = ?', id);
      if (!before) return false;
      // A departing manager can no longer be referenced — null out reports' manager_id first (FK-safe).
      db.run('UPDATE employee SET manager_id = NULL WHERE manager_id = ?', id);
      writeAudited('employee', id, 'delete', before, null, () => db.run('DELETE FROM employee WHERE id = ?', id));
      return true;
    },
    deletePosition(id) {
      id = String(id);
      const before = db.get('SELECT * FROM position WHERE id = ?', id);
      if (!before) return false;
      writeAudited('position', id, 'delete', before, null, () => db.run('DELETE FROM position WHERE id = ?', id));
      return true;
    },
    deleteOrgUnit(id) {
      id = String(id);
      const before = db.get('SELECT * FROM org_unit WHERE id = ?', id);
      if (!before) return false;
      writeAudited('org_unit', id, 'delete', before, null, () => db.run('DELETE FROM org_unit WHERE id = ?', id));
      return true;
    },

    // ---- P5: Asset register (serialized flight hardware) — reads + audited writes ----
    listAssets() {
      return db.all(
        `SELECT a.id, a.serial, a.name, a.config, a.location,
                (SELECT COUNT(*) FROM asset_event e WHERE e.asset_id = a.id) AS events
           FROM asset a ORDER BY a.name`);
    },
    listAssetEvents(asset_id) {
      return db.all('SELECT id, asset_id, kind, occurred_at, notes FROM asset_event WHERE asset_id = ? ORDER BY occurred_at DESC, id DESC', String(asset_id));
    },
    upsertAsset(a) {
      if (!a || !a.id) throw new Error('upsertAsset requires id');
      const id = String(a.id);
      const before = db.get('SELECT * FROM asset WHERE id = ?', id) || null;
      writeAudited('asset', id, before ? 'update' : 'insert', before, a, () => {
        db.run('INSERT INTO asset (id,serial,name,config,location,raw_json) VALUES (?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET serial=excluded.serial, name=excluded.name, config=excluded.config, location=excluded.location, raw_json=excluded.raw_json',
          id, a.serial ?? null, a.name ?? null, a.config ?? null, a.location ?? null, JSON.stringify(a));
      });
      return db.get('SELECT * FROM asset WHERE id = ?', id);
    },
    addAssetEvent(ev) {
      if (!ev || !ev.id || !ev.asset_id) throw new Error('addAssetEvent requires id + asset_id');
      const id = String(ev.id);
      writeAudited('asset_event', id, 'insert', null, ev, () => {
        db.run('INSERT INTO asset_event (id,asset_id,kind,occurred_at,notes,raw_json) VALUES (?,?,?,?,?,?)',
          id, String(ev.asset_id), ev.kind ?? null, ev.occurred_at ?? null, ev.notes ?? null, JSON.stringify(ev));
      });
      return db.get('SELECT * FROM asset_event WHERE id = ?', id);
    },

    // ---- P5: Supply chain — supplier master/ASL, purchase orders, receiving inspection (audited) ----
    listContracts() { return db.all('SELECT id, number, title, customer, status FROM contract ORDER BY title'); },
    listWBS() { return db.all('SELECT id, contract_id, code, name FROM wbs_element ORDER BY contract_id, code'); },
    listVendors() {
      return db.all(`SELECT id, name, qb_id, asl_status, category, country, flight_critical, dd_tier, review_due,
                            active, updated_at, raw_json FROM vendor ORDER BY name COLLATE NOCASE`);
    },
    getVendor(id) { return db.get('SELECT * FROM vendor WHERE id = ?', String(id)); },
    getVendorByQb(qbId) { return db.get('SELECT * FROM vendor WHERE qb_id = ?', String(qbId)); },
    upsertVendor(v) {
      if (!v || !v.id) throw new Error('upsertVendor requires id');
      const id = String(v.id);
      const before = db.get('SELECT * FROM vendor WHERE id = ?', id) || null;
      const prev = before && before.raw_json ? JSON.parse(before.raw_json) : {};
      const rec = { ...prev, ...v, updated_at: new Date().toISOString() };
      writeAudited('vendor', id, before ? 'update' : 'insert', before, rec, () => {
        db.run(`INSERT INTO vendor (id,name,raw_json,qb_id,asl_status,category,country,flight_critical,dd_tier,review_due,active,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, raw_json=excluded.raw_json, qb_id=excluded.qb_id,
                  asl_status=excluded.asl_status, category=excluded.category, country=excluded.country,
                  flight_critical=excluded.flight_critical, dd_tier=excluded.dd_tier, review_due=excluded.review_due,
                  active=excluded.active, updated_at=excluded.updated_at`,
          id, rec.name ?? null, JSON.stringify(rec), rec.qb_id ?? null, rec.asl_status ?? null, rec.category ?? null,
          rec.country ?? null, rec.flight_critical ? 1 : 0, rec.dd_tier ?? null, rec.review_due ?? null,
          rec.active === false ? 0 : 1, rec.updated_at);
      });
      return db.get('SELECT * FROM vendor WHERE id = ?', id);
    },
    listPOs({ vendor_id, since, limit = 2000 } = {}) {
      const where = [], args = [];
      if (vendor_id) { where.push('p.vendor_id = ?'); args.push(String(vendor_id)); }
      if (since) { where.push('p.issued_at >= ?'); args.push(String(since)); }
      return db.all(`SELECT p.id, p.po_number, p.source, p.qb_id, p.vendor_id, v.name AS vendor_name, p.status, p.total,
                            p.issued_at, p.need_by, p.promised_date, p.requested_by, p.approved_by, p.approved_at,
                            p.project_id, p.wbs_id, p.contract_id, p.decision_id, p.flight_critical, p.updated_at,
                            (SELECT COUNT(*) FROM receipt r WHERE r.po_id = p.id) AS receipts
                       FROM purchase_order p LEFT JOIN vendor v ON v.id = p.vendor_id`
        + (where.length ? ' WHERE ' + where.join(' AND ') : '')
        + ' ORDER BY p.issued_at DESC, p.id DESC LIMIT ?', ...args, limit);
    },
    getPO(id) {
      const po = db.get('SELECT p.*, v.name AS vendor_name FROM purchase_order p LEFT JOIN vendor v ON v.id = p.vendor_id WHERE p.id = ?', String(id));
      if (!po) return null;
      po.lines = db.all('SELECT * FROM po_line WHERE po_id = ? ORDER BY line_no, id', po.id);
      po.receipt_list = db.all('SELECT * FROM receipt WHERE po_id = ? ORDER BY received_at DESC, id DESC', po.id);
      return po;
    },
    /** Upsert a PO; if `lines` is given, the PO's lines are replaced (each line write audited). */
    upsertPO(po, lines) {
      if (!po || !po.id) throw new Error('upsertPO requires id');
      const id = String(po.id);
      const before = db.get('SELECT * FROM purchase_order WHERE id = ?', id) || null;
      const prev = before && before.raw_json ? JSON.parse(before.raw_json) : {};
      const rec = { ...prev, ...po, updated_at: new Date().toISOString() };
      const F = ['vendor_id', 'project_id', 'wbs_id', 'status', 'total', 'issued_at', 'po_number', 'source', 'qb_id',
                 'requested_by', 'approved_by', 'approved_at', 'need_by', 'promised_date', 'contract_id', 'decision_id', 'flight_critical', 'updated_at'];
      writeAudited('purchase_order', id, before ? 'update' : 'insert', before, rec, () => {
        db.run(`INSERT INTO purchase_order (id,raw_json,${F.join(',')}) VALUES (?,?,${F.map(() => '?').join(',')})
                ON CONFLICT(id) DO UPDATE SET raw_json=excluded.raw_json, ${F.map(f => `${f}=excluded.${f}`).join(', ')}`,
          id, JSON.stringify(rec), ...F.map(f => f === 'flight_critical' ? (rec[f] ? 1 : 0) : (rec[f] ?? null)));
      });
      if (Array.isArray(lines)) {
        const old = db.all('SELECT * FROM po_line WHERE po_id = ?', id);
        const keep = new Set(lines.map((l, i) => String(l.id || `${id}-L${i + 1}`)));
        for (const o of old) if (!keep.has(o.id)) writeAudited('po_line', o.id, 'delete', o, null, () => db.run('DELETE FROM po_line WHERE id = ?', o.id));
        lines.forEach((l, i) => {
          const lid = String(l.id || `${id}-L${i + 1}`);
          const b = db.get('SELECT * FROM po_line WHERE id = ?', lid) || null;
          const lr = { ...l, id: lid, po_id: id, line_no: l.line_no ?? i + 1 };
          writeAudited('po_line', lid, b ? 'update' : 'insert', b, lr, () => {
            db.run(`INSERT INTO po_line (id,po_id,description,qty,unit_price,raw_json,line_no,part_number,account,amount,qty_received)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET description=excluded.description, qty=excluded.qty, unit_price=excluded.unit_price,
                      raw_json=excluded.raw_json, line_no=excluded.line_no, part_number=excluded.part_number, account=excluded.account,
                      amount=excluded.amount, qty_received=COALESCE(po_line.qty_received, excluded.qty_received)`,
              lid, id, lr.description ?? null, lr.qty ?? null, lr.unit_price ?? null, JSON.stringify(lr), lr.line_no,
              lr.part_number ?? null, lr.account ?? null, lr.amount ?? null, lr.qty_received ?? null);
          });
        });
      }
      return this.getPO(id);
    },
    /** Record a receipt + receiving inspection against a PO line; rolls qty_received onto the line. */
    addReceipt(r) {
      if (!r || !r.id || !r.po_id) throw new Error('addReceipt requires id + po_id');
      const id = String(r.id);
      writeAudited('receipt', id, 'insert', null, r, () => {
        db.run(`INSERT INTO receipt (id,po_id,received_at,raw_json,po_line_id,qty_received,qty_accepted,qty_rejected,result,coc_received,received_by,ncr_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)`,
          id, String(r.po_id), r.received_at ?? new Date().toISOString(), JSON.stringify(r), r.po_line_id ?? null,
          r.qty_received ?? null, r.qty_accepted ?? null, r.qty_rejected ?? null, r.result ?? null,
          r.coc_received ? 1 : 0, r.received_by ?? null, r.ncr_id ?? null);
        if (r.po_line_id) db.run('UPDATE po_line SET qty_received = COALESCE(qty_received,0) + ? WHERE id = ?', Number(r.qty_received) || 0, String(r.po_line_id));
      });
      return db.get('SELECT * FROM receipt WHERE id = ?', id);
    },
    /** Supplier scorecard inputs: spend (12 mo), on-time and quality from MC receiving inspections. */
    vendorScorecards(sinceIso) {
      return db.all(`SELECT v.id AS vendor_id,
          (SELECT COALESCE(SUM(p.total),0) FROM purchase_order p WHERE p.vendor_id = v.id AND p.issued_at >= ?) AS spend_12mo,
          (SELECT COUNT(*) FROM purchase_order p WHERE p.vendor_id = v.id AND p.issued_at >= ?) AS pos_12mo,
          (SELECT MAX(p.issued_at) FROM purchase_order p WHERE p.vendor_id = v.id) AS last_po,
          (SELECT COUNT(*) FROM receipt r JOIN purchase_order p ON p.id = r.po_id WHERE p.vendor_id = v.id) AS receipts,
          (SELECT COUNT(*) FROM receipt r JOIN purchase_order p ON p.id = r.po_id WHERE p.vendor_id = v.id
              AND COALESCE(p.promised_date, p.need_by) IS NOT NULL AND substr(r.received_at,1,10) <= COALESCE(p.promised_date, p.need_by)) AS on_time,
          (SELECT COUNT(*) FROM receipt r JOIN purchase_order p ON p.id = r.po_id WHERE p.vendor_id = v.id
              AND COALESCE(p.promised_date, p.need_by) IS NOT NULL) AS dated_receipts,
          (SELECT COALESCE(SUM(r.qty_received),0) FROM receipt r JOIN purchase_order p ON p.id = r.po_id WHERE p.vendor_id = v.id) AS qty_in,
          (SELECT COALESCE(SUM(r.qty_accepted),0) FROM receipt r JOIN purchase_order p ON p.id = r.po_id WHERE p.vendor_id = v.id) AS qty_ok,
          (SELECT COUNT(*) FROM receipt r JOIN purchase_order p ON p.id = r.po_id WHERE p.vendor_id = v.id AND COALESCE(r.qty_rejected,0) > 0) AS rejects
        FROM vendor v`, sinceIso, sinceIso);
    },

    deleteAsset(id) {
      id = String(id);
      const b = db.get('SELECT * FROM asset WHERE id = ?', id); if (!b) return false;
      for (const e of db.all('SELECT * FROM asset_event WHERE asset_id = ?', id))
        writeAudited('asset_event', e.id, 'delete', e, null, () => db.run('DELETE FROM asset_event WHERE id = ?', e.id));
      writeAudited('asset', id, 'delete', b, null, () => db.run('DELETE FROM asset WHERE id = ?', id));
      return true;
    },

    // ---- P5B: Production control (work orders + routing/WIP + quality; closes MQ-1) ----
    listWorkOrders() {
      return db.all(
        `SELECT w.id, w.wo_number, w.item, w.qty, w.status, w.due, w.project_id, w.wbs_id,
                (SELECT COUNT(*) FROM work_order_op o WHERE o.work_order_id=w.id) AS ops,
                (SELECT COUNT(*) FROM work_order_op o WHERE o.work_order_id=w.id AND o.status='complete') AS ops_done,
                (SELECT COUNT(*) FROM ncr n WHERE n.work_order_id=w.id AND n.status!='closed') AS open_ncr
           FROM work_order w ORDER BY w.due IS NULL, w.due, w.wo_number`);
    },
    listWorkOrderOps(work_order_id) {
      return db.all('SELECT id, work_order_id, seq, operation, work_center, status FROM work_order_op WHERE work_order_id = ? ORDER BY seq', String(work_order_id));
    },
    listNCRs() {
      return db.all('SELECT id, ncr_number, work_order_id, kind, description, status, disposition FROM ncr ORDER BY status, ncr_number');
    },
    upsertWorkOrder(w) {
      if (!w || !w.id) throw new Error('upsertWorkOrder requires id');
      const id = String(w.id);
      const before = db.get('SELECT * FROM work_order WHERE id = ?', id) || null;
      writeAudited('work_order', id, before ? 'update' : 'insert', before, w, () => {
        db.run('INSERT INTO work_order (id,wo_number,item,project_id,wbs_id,qty,status,due,raw_json) VALUES (?,?,?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET wo_number=excluded.wo_number, item=excluded.item, project_id=excluded.project_id, wbs_id=excluded.wbs_id, qty=excluded.qty, status=excluded.status, due=excluded.due, raw_json=excluded.raw_json',
          id, w.wo_number ?? null, w.item ?? null, w.project_id ?? null, w.wbs_id ?? null, w.qty ?? null, w.status ?? 'planned', w.due ?? null, JSON.stringify(w));
      });
      return db.get('SELECT * FROM work_order WHERE id = ?', id);
    },
    upsertWorkOrderOp(o) {
      if (!o || !o.id || !o.work_order_id) throw new Error('upsertWorkOrderOp requires id + work_order_id');
      const id = String(o.id);
      const before = db.get('SELECT * FROM work_order_op WHERE id = ?', id) || null;
      writeAudited('work_order_op', id, before ? 'update' : 'insert', before, o, () => {
        db.run('INSERT INTO work_order_op (id,work_order_id,seq,operation,work_center,status,raw_json) VALUES (?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET seq=excluded.seq, operation=excluded.operation, work_center=excluded.work_center, status=excluded.status, raw_json=excluded.raw_json',
          id, String(o.work_order_id), o.seq ?? null, o.operation ?? null, o.work_center ?? null, o.status ?? 'pending', JSON.stringify(o));
      });
      return db.get('SELECT * FROM work_order_op WHERE id = ?', id);
    },
    upsertNCR(n) {
      if (!n || !n.id) throw new Error('upsertNCR requires id');
      const id = String(n.id);
      const before = db.get('SELECT * FROM ncr WHERE id = ?', id) || null;
      writeAudited('ncr', id, before ? 'update' : 'insert', before, n, () => {
        db.run('INSERT INTO ncr (id,ncr_number,work_order_id,kind,description,status,disposition,raw_json) VALUES (?,?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET ncr_number=excluded.ncr_number, work_order_id=excluded.work_order_id, kind=excluded.kind, description=excluded.description, status=excluded.status, disposition=excluded.disposition, raw_json=excluded.raw_json',
          id, n.ncr_number ?? null, n.work_order_id ?? null, n.kind ?? 'NCR', n.description ?? null, n.status ?? 'open', n.disposition ?? null, JSON.stringify(n));
      });
      return db.get('SELECT * FROM ncr WHERE id = ?', id);
    },

    // ---- Timekeeping interface (BambooHR DCAA time -> ERP time_entry, read-through, audited) ----
    upsertTimeEntry(t) {
      if (!t || !t.id) throw new Error('upsertTimeEntry requires id');
      const id = String(t.id);
      const before = db.get('SELECT * FROM time_entry WHERE id = ?', id) || null;
      writeAudited('time_entry', id, before ? 'update' : 'insert', before, t, () => {
        db.run('INSERT INTO time_entry (id,user_id,task_id,project_id,wbs_id,work_date,hours,labor_class,notes,approved_by,approved_at,locked,raw_json) ' +
          'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET user_id=excluded.user_id, task_id=excluded.task_id, project_id=excluded.project_id, wbs_id=excluded.wbs_id, work_date=excluded.work_date, hours=excluded.hours, labor_class=excluded.labor_class, notes=excluded.notes, approved_by=excluded.approved_by, approved_at=excluded.approved_at, locked=excluded.locked, raw_json=excluded.raw_json',
          id, t.user_id ?? null, t.task_id ?? null, t.project_id ?? null, t.wbs_id ?? null, t.work_date ?? null, t.hours ?? null, t.labor_class ?? null, t.notes ?? null, t.approved_by ?? null, t.approved_at ?? null, t.locked ? 1 : 0, JSON.stringify(t));
      });
      return db.get('SELECT * FROM time_entry WHERE id = ?', id);
    },

    // ---- Schedule integration (Teamwork -> ERP: project / task_list / task) ----
    upsertProject(p) {
      if (!p || !p.id) throw new Error('upsertProject requires id');
      const id = String(p.id); const before = db.get('SELECT * FROM project WHERE id = ?', id) || null;
      writeAudited('project', id, before ? 'update' : 'insert', before, p, () => {
        db.run('INSERT INTO project (id,name,contract_id,status,raw_json) VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, contract_id=excluded.contract_id, status=excluded.status, raw_json=excluded.raw_json',
          id, p.name ?? null, p.contract_id ?? null, p.status ?? null, JSON.stringify(p));
      });
      return db.get('SELECT * FROM project WHERE id = ?', id);
    },
    upsertTaskList(tl) {
      if (!tl || !tl.id) throw new Error('upsertTaskList requires id');
      const id = String(tl.id); const before = db.get('SELECT * FROM task_list WHERE id = ?', id) || null;
      writeAudited('task_list', id, before ? 'update' : 'insert', before, tl, () => {
        db.run('INSERT INTO task_list (id,project_id,name,raw_json) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id, name=excluded.name, raw_json=excluded.raw_json',
          id, tl.project_id ?? null, tl.name ?? null, JSON.stringify(tl));
      });
      return db.get('SELECT * FROM task_list WHERE id = ?', id);
    },
    upsertTask(t) {
      if (!t || !t.id) throw new Error('upsertTask requires id');
      const id = String(t.id); const before = db.get('SELECT * FROM task WHERE id = ?', id) || null;
      writeAudited('task', id, before ? 'update' : 'insert', before, t, () => {
        db.run('INSERT INTO task (id,task_list_id,project_id,title,state,owner,due_date,priority,category,description,source,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET task_list_id=excluded.task_list_id, project_id=excluded.project_id, title=excluded.title, state=excluded.state, owner=excluded.owner, due_date=excluded.due_date, priority=excluded.priority, category=excluded.category, description=excluded.description, source=excluded.source, raw_json=excluded.raw_json',
          id, t.task_list_id ?? null, t.project_id ?? null, t.title ?? null, t.state ?? null, t.owner ?? null, t.due_date ?? null, t.priority ?? null, t.category ?? null, t.description ?? null, t.source ?? null, JSON.stringify(t));
      });
      return db.get('SELECT * FROM task WHERE id = ?', id);
    },
    listProjects() { return db.all('SELECT id, name, status, contract_id FROM project ORDER BY name'); },
    listTasksBySource(source) { return db.all('SELECT id FROM task WHERE source = ?', String(source)); },
    getProjectSchedule(pid) {
      pid = String(pid);
      const project = db.get('SELECT id, name, status FROM project WHERE id = ?', pid);
      const lists = db.all('SELECT id, name FROM task_list WHERE project_id = ? ORDER BY name', pid);
      const tasks = db.all(
        "SELECT id, task_list_id, title, state, owner, due_date, " +
        "json_extract(raw_json,'$.startDate') AS start_date, json_extract(raw_json,'$.progress') AS progress, " +
        "json_extract(raw_json,'$.predecessors') AS predecessors_json, json_extract(raw_json,'$.seq') AS seq, json_extract(raw_json,'$.phase') AS phase " +
        "FROM task WHERE project_id = ? ORDER BY due_date IS NULL, due_date", pid);
      return { project, lists, tasks };
    },
    /** Audited edit of a single schedule task's start/due/owner/state; preserves all other raw_json. */
    updateScheduleTask(id, p) {
      id = String(id); p = p || {};
      const before = db.get('SELECT * FROM task WHERE id = ?', id);
      if (!before) return null;
      const after = { ...before, ...p };
      writeAudited('task', id, 'update', before, after, () => {
        db.run(
          "UPDATE task SET " +
          "due_date = CASE WHEN ? THEN ? ELSE due_date END, " +
          "owner = CASE WHEN ? THEN ? ELSE owner END, " +
          "state = CASE WHEN ? THEN ? ELSE state END, " +
          "raw_json = json_set(json_set(raw_json,'$.startDate',COALESCE(?,json_extract(raw_json,'$.startDate'))),'$.due_date',COALESCE(?,json_extract(raw_json,'$.due_date'))) " +
          "WHERE id = ?",
          p.due_date !== undefined ? 1 : 0, p.due_date ?? null,
          p.owner !== undefined ? 1 : 0, p.owner ?? null,
          p.state !== undefined ? 1 : 0, p.state ?? null,
          p.start_date !== undefined ? (p.start_date ?? null) : null,
          p.due_date !== undefined ? (p.due_date ?? null) : null,
          id);
        if (p.predecessors !== undefined)
          db.run("UPDATE task SET raw_json = json_set(raw_json,'$.predecessors',json(?)) WHERE id = ?", JSON.stringify(p.predecessors || []), id);
        if (p.seq !== undefined)
          db.run("UPDATE task SET raw_json = json_set(raw_json,'$.seq',?) WHERE id = ?", p.seq, id);
        if (p.phase !== undefined)
          db.run("UPDATE task SET raw_json = json_set(raw_json,'$.phase',?) WHERE id = ?", p.phase || null, id);
      });
      return db.get('SELECT * FROM task WHERE id = ?', id);
    },
    deleteTask(id) { id = String(id); const b = db.get('SELECT * FROM task WHERE id = ?', id); if (!b) return false; writeAudited('task', id, 'delete', b, null, () => db.run('DELETE FROM task WHERE id = ?', id)); return true; },
    deleteTaskList(id) { id = String(id); const b = db.get('SELECT * FROM task_list WHERE id = ?', id); if (!b) return false; writeAudited('task_list', id, 'delete', b, null, () => db.run('DELETE FROM task_list WHERE id = ?', id)); return true; },
    deleteProject(id) { id = String(id); const b = db.get('SELECT * FROM project WHERE id = ?', id); if (!b) return false; writeAudited('project', id, 'delete', b, null, () => db.run('DELETE FROM project WHERE id = ?', id)); return true; },

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

    // ---- Contracts & CDRL (Phase 4): federal awards → WBS → deliverables, all audited ----
    upsertContract(c) {
      if (!c || !c.id) throw new Error('upsertContract requires id');
      const id = String(c.id);
      const before = db.get('SELECT * FROM contract WHERE id = ?', id) || null;
      writeAudited('contract', id, before ? 'update' : 'insert', before, c, () => {
        db.run('INSERT INTO contract (id,number,title,customer,status,funded_value,start_date,end_date,raw_json) ' +
          'VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET number=excluded.number, title=excluded.title, ' +
          'customer=excluded.customer, status=excluded.status, funded_value=excluded.funded_value, ' +
          'start_date=excluded.start_date, end_date=excluded.end_date, raw_json=excluded.raw_json',
          id, c.number ?? null, c.title ?? null, c.customer ?? null, c.status ?? null,
          c.funded_value ?? null, c.start_date ?? null, c.end_date ?? null, JSON.stringify(c));
      });
      return db.get('SELECT * FROM contract WHERE id = ?', id);
    },
    upsertWbs(w) {
      if (!w || !w.id) throw new Error('upsertWbs requires id');
      const id = String(w.id);
      const before = db.get('SELECT * FROM wbs_element WHERE id = ?', id) || null;
      writeAudited('wbs_element', id, before ? 'update' : 'insert', before, w, () => {
        db.run('INSERT INTO wbs_element (id,contract_id,parent_id,code,name,budget,raw_json) VALUES (?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET contract_id=excluded.contract_id, parent_id=excluded.parent_id, ' +
          'code=excluded.code, name=excluded.name, budget=excluded.budget, raw_json=excluded.raw_json',
          id, w.contract_id ?? null, w.parent_id ?? null, w.code ?? null, w.name ?? null, w.budget ?? null, JSON.stringify(w));
      });
      return db.get('SELECT * FROM wbs_element WHERE id = ?', id);
    },
    upsertDeliverable(d) {   // CDRL
      if (!d || !d.id) throw new Error('upsertDeliverable requires id');
      const id = String(d.id);
      const before = db.get('SELECT * FROM deliverable WHERE id = ?', id) || null;
      writeAudited('deliverable', id, before ? 'update' : 'insert', before, d, () => {
        db.run('INSERT INTO deliverable (id,contract_id,cdrl_number,title,due_date,status,raw_json) VALUES (?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET contract_id=excluded.contract_id, cdrl_number=excluded.cdrl_number, ' +
          'title=excluded.title, due_date=excluded.due_date, status=excluded.status, raw_json=excluded.raw_json',
          id, d.contract_id ?? null, d.cdrl_number ?? null, d.title ?? null, d.due_date ?? null, d.status ?? null, JSON.stringify(d));
      });
      return db.get('SELECT * FROM deliverable WHERE id = ?', id);
    },
    upsertContractMilestone(m) {
      if (!m || !m.id) throw new Error('upsertContractMilestone requires id');
      const id = String(m.id);
      const before = db.get('SELECT * FROM contract_milestone WHERE id = ?', id) || null;
      writeAudited('contract_milestone', id, before ? 'update' : 'insert', before, m, () => {
        db.run('INSERT INTO contract_milestone (id,contract_id,name,due_date,amount,status,raw_json) VALUES (?,?,?,?,?,?,?) ' +
          'ON CONFLICT(id) DO UPDATE SET contract_id=excluded.contract_id, name=excluded.name, due_date=excluded.due_date, ' +
          'amount=excluded.amount, status=excluded.status, raw_json=excluded.raw_json',
          id, m.contract_id ?? null, m.name ?? null, m.due_date ?? null, m.amount ?? null, m.status ?? null, JSON.stringify(m));
      });
      return db.get('SELECT * FROM contract_milestone WHERE id = ?', id);
    },
    listContracts() {
      return db.all('SELECT id,number,title,customer,status,funded_value,start_date,end_date FROM contract ORDER BY start_date DESC');
    },
    listCdrls(contractId) {
      return db.all('SELECT id,cdrl_number,title,due_date,status FROM deliverable WHERE contract_id = ? ORDER BY due_date', String(contractId));
    },
    listWbs(contractId) {
      return contractId
        ? db.all('SELECT id,contract_id,parent_id,code,name,budget FROM wbs_element WHERE contract_id = ? ORDER BY code', String(contractId))
        : db.all('SELECT id,contract_id,parent_id,code,name,budget FROM wbs_element ORDER BY contract_id, code');
    },
    /** Budget-vs-actual cost rollup per WBS: budget (contract), labor HOURS booked (Bamboo/DCAA
     *  time_entry), and material $ committed (po_line → purchase_order.wbs_id). Labor→$ needs the
     *  Bamboo labor rate (joined later); hours are shown until then. Returns rows + totals. */
    contractRollup(contractId) {
      const rows = db.all(
        'SELECT w.id, w.code, w.name, w.budget, ' +
        '(SELECT COALESCE(SUM(t.hours),0) FROM time_entry t WHERE t.wbs_id = w.id) AS labor_hours, ' +
        '(SELECT COALESCE(SUM(pl.qty*pl.unit_price),0) FROM po_line pl JOIN purchase_order po ON po.id = pl.po_id WHERE po.wbs_id = w.id) AS material_cost ' +
        'FROM wbs_element w WHERE w.contract_id = ? ORDER BY w.code', String(contractId));
      const totals = rows.reduce((a, r) => ({
        budget: a.budget + (r.budget || 0), labor_hours: a.labor_hours + (r.labor_hours || 0),
        material_cost: a.material_cost + (r.material_cost || 0),
      }), { budget: 0, labor_hours: 0, material_cost: 0 });
      return { rows, totals };
    },

    // ---- Sales-agent commissions: contract → who initiated → payout, all audited ----
    upsertSalesAgent(a) {
      if (!a || !a.id) throw new Error('upsertSalesAgent requires id');
      const id = String(a.id);
      const before = db.get('SELECT * FROM sales_agent WHERE id = ?', id) || null;
      writeAudited('sales_agent', id, before ? 'update' : 'insert', before, a, () => {
        db.run('INSERT INTO sales_agent (id,name,email,base_rate,bonus_rate,bonus_condition,equity_shares,equity_vesting,agreement_doc,status,raw_json) ' +
          'VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, email=excluded.email, ' +
          'base_rate=excluded.base_rate, bonus_rate=excluded.bonus_rate, bonus_condition=excluded.bonus_condition, ' +
          'equity_shares=excluded.equity_shares, equity_vesting=excluded.equity_vesting, agreement_doc=excluded.agreement_doc, ' +
          'status=excluded.status, raw_json=excluded.raw_json',
          id, a.name ?? null, a.email ?? null, a.base_rate ?? null, a.bonus_rate ?? 0, a.bonus_condition ?? null,
          a.equity_shares ?? null, a.equity_vesting ?? null, a.agreement_doc ?? null, a.status ?? 'Active', JSON.stringify(a));
      });
      return db.get('SELECT * FROM sales_agent WHERE id = ?', id);
    },
    /** Record WHO initiated/supported a contract — this is what drives commission routing. */
    upsertAttribution(x) {
      if (!x || !x.id) throw new Error('upsertAttribution requires id');
      const id = String(x.id);
      const before = db.get('SELECT * FROM contract_attribution WHERE id = ?', id) || null;
      writeAudited('contract_attribution', id, before ? 'update' : 'insert', before, x, () => {
        db.run('INSERT INTO contract_attribution (id,contract_id,agent_id,role,rate,effective_date,note,raw_json) ' +
          'VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET contract_id=excluded.contract_id, agent_id=excluded.agent_id, ' +
          'role=excluded.role, rate=excluded.rate, effective_date=excluded.effective_date, note=excluded.note, raw_json=excluded.raw_json',
          id, x.contract_id, x.agent_id, x.role ?? 'initiated', x.rate ?? null, x.effective_date ?? null, x.note ?? null, JSON.stringify(x));
      });
      return db.get('SELECT * FROM contract_attribution WHERE id = ?', id);
    },
    /** THE TRIGGER: Exos received a customer payment on a contract → accrue a commission (status
     *  'due', due 30 days out per the agreement) for every attributed agent. Idempotent per
     *  (contract, payment_date, agent).
     *
     *  Bonus rule (Jon 2026-07-31): base rate applies to the WHOLE payment. The +bonus rate
     *  applies ONLY to the revenue for the mass booked in the TOP 25% of the payload bay — i.e.
     *  the booked mass above the 75%-of-capacity line. bonus_mass = max(0, booked_kg − 0.75*capacity).
     *  bonus revenue = amount * (bonus_mass / booked_kg). So a full bay earns base on all + bonus on
     *  just its top-25% slice; a ≤75% booking earns no bonus. Non-payload payments: omit booked_kg → no bonus.
     */
    recordContractPayment(contractId, { amount, date, customer = null, booked_kg = 0, capacity_kg = 135 } = {}) {
      if (!contractId || amount == null || !date) throw new Error('recordContractPayment requires contractId, amount, date');
      const attrs = db.all('SELECT * FROM contract_attribution WHERE contract_id = ?', String(contractId));
      const due = new Date(new Date(date).getTime() + 30 * 86400000).toISOString().slice(0, 10);
      const amt = Number(amount);
      const bk = Number(booked_kg) || 0;
      const cap = Number(capacity_kg) || 135;
      const bonusMass = bk > 0 ? Math.max(0, Math.min(bk, cap) - 0.75 * cap) : 0;
      const bonusFraction = bk > 0 ? bonusMass / bk : 0;      // share of THIS booking's revenue in the top 25%
      const bonusApplies = bonusMass > 0 ? 1 : 0;
      const out = [];
      for (const a of attrs) {
        const agent = db.get('SELECT * FROM sales_agent WHERE id = ?', a.agent_id);
        if (!agent) continue;
        const rate = a.rate != null ? a.rate : (agent.base_rate || 0);
        const bonusRate = bonusApplies ? (agent.bonus_rate || 0) : 0;
        const bonusBase = Math.round(bonusFraction * amt * 100) / 100;   // revenue the bonus rate applies to
        const commissionAmount = Math.round((rate * amt + bonusRate * bonusBase) * 100) / 100;
        const cid = `comm-${contractId}-${String(date).slice(0,10)}-${a.agent_id}`;
        const before = db.get('SELECT * FROM commission WHERE id = ?', cid) || null;
        const row = { id: cid, contract_id: String(contractId), agent_id: a.agent_id, customer,
          payment_amount: amt, payment_date: date, rate, bonus_applies: bonusApplies, bonus_rate: bonusRate,
          booked_kg: bk, capacity_kg: cap, bonus_mass: Math.round(bonusMass * 100) / 100, bonus_base_amount: bonusBase,
          commission_amount: commissionAmount, status: (before ? before.status : 'due'), due_date: due };
        writeAudited('commission', cid, before ? 'update' : 'insert', before, row, () => {
          db.run('INSERT INTO commission (id,contract_id,agent_id,customer,payment_amount,payment_date,rate,bonus_applies,bonus_rate,booked_kg,capacity_kg,bonus_mass,bonus_base_amount,commission_amount,status,due_date,raw_json) ' +
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payment_amount=excluded.payment_amount, ' +
            'rate=excluded.rate, bonus_applies=excluded.bonus_applies, bonus_rate=excluded.bonus_rate, booked_kg=excluded.booked_kg, ' +
            'capacity_kg=excluded.capacity_kg, bonus_mass=excluded.bonus_mass, bonus_base_amount=excluded.bonus_base_amount, ' +
            'commission_amount=excluded.commission_amount, due_date=excluded.due_date, customer=excluded.customer, raw_json=excluded.raw_json',
            cid, row.contract_id, row.agent_id, customer, amt, date, rate, bonusApplies, bonusRate, bk, cap,
            row.bonus_mass, bonusBase, commissionAmount, row.status, due, JSON.stringify(row));
        });
        out.push({ ...db.get('SELECT * FROM commission WHERE id = ?', cid), agent_name: agent.name, agent_email: agent.email });
      }
      return out;
    },
    markCommissionPaid(id, { paid_date, qb_ref } = {}) {
      const cid = String(id);
      const before = db.get('SELECT * FROM commission WHERE id = ?', cid);
      if (!before) throw new Error(`commission ${id} not found`);
      const after = { ...before, status: 'paid', paid_date: paid_date || new Date().toISOString().slice(0,10), qb_ref: qb_ref ?? before.qb_ref };
      writeAudited('commission', cid, 'update', before, after, () => {
        db.run('UPDATE commission SET status=?, paid_date=?, qb_ref=COALESCE(?,qb_ref) WHERE id=?',
          'paid', after.paid_date, qb_ref ?? null, cid);
      });
      return after;
    },
    listCommissions({ status, agent_id, limit = 200 } = {}) {
      const where = [], args = [];
      if (status) { where.push('c.status = ?'); args.push(status); }
      if (agent_id) { where.push('c.agent_id = ?'); args.push(agent_id); }
      return db.all('SELECT c.*, a.name AS agent_name, a.email AS agent_email FROM commission c ' +
        'LEFT JOIN sales_agent a ON a.id = c.agent_id' +
        (where.length ? ' WHERE ' + where.join(' AND ') : '') +
        ' ORDER BY c.due_date LIMIT ?', ...args, limit);
    },
    getAgentByEmail(email) {
      if (!email) return null;
      return db.get('SELECT * FROM sales_agent WHERE lower(email) = lower(?)', String(email)) || null;
    },
    listAttributions(contractId) {
      return db.all('SELECT x.*, a.name AS agent_name FROM contract_attribution x LEFT JOIN sales_agent a ON a.id=x.agent_id WHERE x.contract_id = ?', String(contractId));
    },

    // ---- P5C: MRP — part master, BOM, inventory ledger, missions, MRP runs, purchase requests ----
    // Audited upserts that only write (and only log) when a column actually changed, so the nightly
    // sync does not flood audit_log with no-op rows.
    mrpUpsert(table, rec) {
      const COLS = {
        part: ['part_number', 'description', 'vendor', 'vendor_id', 'unit', 'unit_cost', 'cost_basis', 'lead_time_days', 'make_buy', 'active', 'raw_json'],
        bom_line: ['assembly', 'section', 'item_no', 'part_id', 'qty_per', 'raw_json'],
        mission: ['label', 'customer', 'vehicle', 'asset_id', 'status', 'need_date', 'raw_json'],
        purchase_request: ['run_id', 'vendor', 'vendor_id', 'status', 'est_total', 'need_by', 'routes_to_jon', 'po_id', 'raw_json'],
      }[table];
      if (!COLS) throw new Error('mrpUpsert: unsupported table ' + table);
      if (!rec || !rec.id) throw new Error('mrpUpsert requires id');
      const id = String(rec.id);
      const before = db.get(`SELECT * FROM ${table} WHERE id = ?`, id) || null;
      const row = {};
      for (const c of COLS) row[c] = rec[c] === undefined ? (before ? before[c] : null) : (rec[c] === null ? null : (typeof rec[c] === 'object' ? JSON.stringify(rec[c]) : rec[c]));
      if (before && COLS.every(c => String(before[c] ?? '') === String(row[c] ?? ''))) return { id, changed: false };
      const ts = new Date().toISOString();
      const stamp = table === 'purchase_request' && !before ? ['created_at', 'updated_at'] : ['updated_at'];
      const cols = ['id', ...COLS, ...stamp];
      const vals = [id, ...COLS.map(c => row[c]), ...stamp.map(() => ts)];
      writeAudited(table, id, before ? 'update' : 'insert', before, { id, ...row }, () => {
        db.run(`INSERT INTO ${table} (${cols.join(',')}) VALUES (${cols.map(() => '?').join(',')}) ` +
          `ON CONFLICT(id) DO UPDATE SET ${cols.slice(1).filter(c => c !== 'created_at').map(c => `${c}=excluded.${c}`).join(', ')}`, ...vals);
      });
      return { id, changed: true };
    },
    addInventoryTxn(t) {
      if (!t || !t.id || !t.part_id || !t.kind) throw new Error('addInventoryTxn requires id, part_id, kind');
      if (t.kind === 'receipt' && t.ref && db.get("SELECT 1 FROM inventory_txn WHERE kind='receipt' AND ref = ?", String(t.ref))) return null;
      writeAudited('inventory_txn', t.id, 'insert', null, t, () => {
        db.run('INSERT INTO inventory_txn (id,part_id,kind,qty,location,source,ref,occurred_at) VALUES (?,?,?,?,?,?,?,?)',
          String(t.id), String(t.part_id), t.kind, Number(t.qty) || 0, t.location ?? null, t.source ?? null, t.ref ?? null, t.occurred_at || new Date().toISOString());
      });
      return t.id;
    },
    /** On-hand per part = latest physical count + receipts/adjustments after that count. */
    onHandByPart() {
      const out = {};
      const counts = db.all(`SELECT t.part_id, t.qty, t.occurred_at FROM inventory_txn t
        JOIN (SELECT part_id, MAX(occurred_at) m FROM inventory_txn WHERE kind='count' GROUP BY part_id) x
          ON x.part_id = t.part_id AND x.m = t.occurred_at WHERE t.kind='count'`);
      const since = {};
      for (const c of counts) { out[c.part_id] = Number(c.qty) || 0; since[c.part_id] = c.occurred_at; }
      for (const d of db.all("SELECT part_id, qty, occurred_at FROM inventory_txn WHERE kind IN ('receipt','adjust')")) {
        if (!since[d.part_id] || d.occurred_at > since[d.part_id]) out[d.part_id] = (out[d.part_id] || 0) + (Number(d.qty) || 0);
      }
      return out;
    },
    lastCountByPart() {
      const m = {};
      for (const r of db.all(`SELECT part_id, qty FROM inventory_txn t WHERE kind='count' AND occurred_at =
          (SELECT MAX(occurred_at) FROM inventory_txn x WHERE x.part_id=t.part_id AND x.kind='count')`)) m[r.part_id] = Number(r.qty) || 0;
      return m;
    },
    listParts() { return db.all('SELECT * FROM part ORDER BY part_number'); },
    listBom(assembly) { return db.all('SELECT * FROM bom_line WHERE assembly = ? ORDER BY section, CAST(item_no AS REAL)', String(assembly)); },
    listMissions() { return db.all('SELECT * FROM mission ORDER BY id'); },
    /** Open supply: open/issued PO lines not yet fully received (QB + MC POs). */
    listOpenPoLines() {
      return db.all(`SELECT l.id, l.po_id, l.part_number, l.description, l.qty, COALESCE(l.qty_received,0) qty_received,
          p.po_number, p.status, p.vendor_id, p.need_by, p.promised_date, p.issued_at
        FROM po_line l JOIN purchase_order p ON p.id = l.po_id
        WHERE p.status IN ('open','issued','partially_received') AND COALESCE(l.qty,0) > COALESCE(l.qty_received,0)`);
    },
    listAcceptedReceipts() {
      return db.all(`SELECT r.id, r.po_id, r.po_line_id, r.received_at, COALESCE(r.qty_accepted, r.qty_received, 0) qty,
          l.part_number, l.description FROM receipt r LEFT JOIN po_line l ON l.id = r.po_line_id`);
    },
    saveMrpRun(run, lines) {
      if (!run || !run.id) throw new Error('saveMrpRun requires id');
      writeAudited('mrp_run', run.id, 'insert', null, { ...run, lines: (lines || []).length }, () => {
        db.run('INSERT INTO mrp_run (id,run_at,actor,scope,summary_json) VALUES (?,?,?,?,?)',
          run.id, run.run_at, run.actor || actor, run.scope || '', JSON.stringify(run.summary || {}));
        for (const l of lines || []) {
          db.run(`INSERT INTO mrp_line (id,run_id,part_id,assembly,demand_ref,gross,on_hand,on_order,net,unit_cost,ext_cost,vendor,vendor_id,make_buy,need_by,action)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`,
            l.id, run.id, l.part_id, l.assembly, l.demand_ref, l.gross, l.on_hand, l.on_order, l.net, l.unit_cost, l.ext_cost,
            l.vendor, l.vendor_id, l.make_buy, l.need_by, l.action);
        }
      });
      return run.id;
    },
    latestMrpRun() { return db.get('SELECT * FROM mrp_run ORDER BY run_at DESC LIMIT 1') || null; },
    /** Manual on-hand edit from the MRP page: refresh one planned line in place (audited). */
    mrpLineSetOnHand(lineId, f) {
      const before = db.get('SELECT * FROM mrp_line WHERE id = ?', String(lineId));
      if (!before) return null;
      const after = { ...before, on_hand: f.on_hand, net: f.net, ext_cost: f.ext_cost, action: f.action };
      writeAudited('mrp_line', String(lineId), 'update', before, after, () => {
        db.run('UPDATE mrp_line SET on_hand=?, net=?, ext_cost=?, action=? WHERE id=?',
          f.on_hand, f.net, f.ext_cost, f.action, String(lineId));
      });
      return after;
    },
    listMrpLines(runId) {
      return db.all(`SELECT m.*, p.part_number, p.description FROM mrp_line m LEFT JOIN part p ON p.id = m.part_id
        WHERE m.run_id = ? ORDER BY (m.action = 'none'), m.ext_cost DESC`, String(runId));
    },
    listPurchaseRequests({ status } = {}) {
      return status ? db.all('SELECT * FROM purchase_request WHERE status = ? ORDER BY est_total DESC', String(status))
                    : db.all('SELECT * FROM purchase_request ORDER BY created_at DESC, est_total DESC');
    },
    getPurchaseRequest(id) { return db.get('SELECT * FROM purchase_request WHERE id = ?', String(id)) || null; },

    // ---- audit inspection ----
    recentAudit({ limit = 10 } = {}) {
      return db.all('SELECT id,actor,ts,entity,entity_id,action FROM audit_log ORDER BY id DESC LIMIT ?', limit);
    },

    close() { db.close(); },
  };
}

module.exports = { openErp };
