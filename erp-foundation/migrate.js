#!/usr/bin/env node
/**
 * Phase 0 ERP migration: JSON flat-files -> SQLite (mc.db)
 *
 * - Reads the COPIES in erp-foundation/sample-data/ (never the live files).
 * - Builds mc.db fresh from schema.sql (idempotent: drops mc.db* and recreates).
 * - Loads each dataset into the matching tables.
 * - Writes an audit_log row per inserted record (actor = 'migrate.js').
 * - Prints a reconciliation report: JSON count vs rows inserted, with skips.
 *
 * DB driver: prefers better-sqlite3 (production target). Falls back to the
 * built-in node:sqlite (Node >=22, experimental) so this runs without an npm
 * install. A tiny adapter normalizes the two APIs.
 *
 * Run:  node erp-foundation/migrate.js
 */

'use strict';
const fs = require('fs');
const path = require('path');

const DIR = __dirname;
const SAMPLE = path.join(DIR, 'sample-data');
const DB_PATH = path.join(DIR, 'mc.db');
const SCHEMA_PATH = path.join(DIR, 'schema.sql');

// ---------------------------------------------------------------------------
// DB adapter: expose .exec(sql), .prepare(sql).run(...args), .close()
// ---------------------------------------------------------------------------
function openDb(file) {
  // Try better-sqlite3 first (the production dependency).
  try {
    const Database = require('better-sqlite3');
    const db = new Database(file);
    return {
      driver: 'better-sqlite3',
      exec: (sql) => db.exec(sql),
      prepare: (sql) => {
        const st = db.prepare(sql);
        return { run: (...a) => st.run(...a) };
      },
      pragma: (p) => db.pragma(p),
      close: () => db.close(),
    };
  } catch (_) { /* fall through */ }

  // Fall back to built-in node:sqlite (experimental).
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(file);
  return {
    driver: 'node:sqlite',
    exec: (sql) => db.exec(sql),
    prepare: (sql) => {
      const st = db.prepare(sql);
      return { run: (...a) => st.run(...a) };
    },
    pragma: (p) => db.exec('PRAGMA ' + p + ';'),
    close: () => db.close(),
  };
}

const nowIso = () => new Date().toISOString();
const j = (v) => (v === undefined ? null : JSON.stringify(v));
function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(SAMPLE, name), 'utf8'));
}

// ---------------------------------------------------------------------------
// Idempotency: remove the DB + WAL/SHM sidecars so each run is a clean rebuild.
// ---------------------------------------------------------------------------
for (const f of [DB_PATH, DB_PATH + '-wal', DB_PATH + '-shm', DB_PATH + '-journal']) {
  if (fs.existsSync(f)) fs.unlinkSync(f);
}

const db = openDb(DB_PATH);
db.exec(fs.readFileSync(SCHEMA_PATH, 'utf8'));
db.exec('PRAGMA foreign_keys = ON;');

// Audit helper -- every insert records an append-only audit row.
const auditStmt = db.prepare(
  'INSERT INTO audit_log (actor, ts, entity, entity_id, action, before_json, after_json) VALUES (?,?,?,?,?,?,?)'
);
function audit(entity, id, after) {
  auditStmt.run('migrate.js', nowIso(), entity, String(id), 'insert', null, j(after));
}

const report = []; // {source, jsonCount, inserted, skipped:[{id,reason}], tables:{}}

// ---------------------------------------------------------------------------
// 1) users.json -> role, user
// ---------------------------------------------------------------------------
(function loadUsers() {
  const rows = readJson('users.json');
  const r = { source: 'users.json', jsonCount: rows.length, inserted: 0, skipped: [], tables: { user: 0, role: 0 } };

  // Seed the role + clearance reference tables (from §5A RBAC matrix).
  const roleStmt = db.prepare('INSERT OR IGNORE INTO role (id,label,description) VALUES (?,?,?)');
  for (const [id, label] of [
    ['admin', 'Administrator'], ['manager', 'Manager'], ['member', 'Member'],
    ['hr', 'Human Resources'], ['finance', 'Finance'], ['contracts', 'Contracts'],
  ]) { roleStmt.run(id, label, 'seeded by migrate.js'); r.tables.role++; }

  const clrStmt = db.prepare('INSERT OR IGNORE INTO clearance (id,label,description) VALUES (?,?,?)');
  for (const [id, label] of [
    ['hr-pii', 'HR PII'], ['itar-controlled', 'ITAR Controlled'], ['financial', 'Financial'],
  ]) clrStmt.run(id, label, 'seeded by migrate.js');

  const ins = db.prepare(
    'INSERT INTO user (id,email,name,role_id,password_hash,password_salt,active,created_at,raw_json) VALUES (?,?,?,?,?,?,?,?,?)'
  );
  for (const u of rows) {
    if (u.email == null) { r.skipped.push({ id: u.id, reason: 'missing email (unique key)' }); continue; }
    const id = String(u.id);
    ins.run(id, u.email, u.name ?? null, u.role ?? 'member',
      u.password_hash ?? null, u.password_salt ?? null,
      u.active ? 1 : 0, u.created_at ?? null, j(u));
    audit('user', id, u);
    r.inserted++; r.tables.user++;
  }
  report.push(r);
})();

// ---------------------------------------------------------------------------
// 2) crm-data.json -> company, contact, deal  (normalize the flat row)
// ---------------------------------------------------------------------------
(function loadCrm() {
  const rows = readJson('crm-data.json');
  const r = { source: 'crm-data.json', jsonCount: rows.length, inserted: 0, skipped: [],
    tables: { company: 0, contact: 0, deal: 0 } };

  const insCo = db.prepare('INSERT INTO company (id,name,category,fit_thesis,tier,source,raw_json) VALUES (?,?,?,?,?,?,?)');
  const insCt = db.prepare('INSERT INTO contact (id,company_id,name,title,email,emails_alt,phone,linkedin,raw_json) VALUES (?,?,?,?,?,?,?,?,?)');
  const insDeal = db.prepare(
    'INSERT INTO deal (id,company_id,contact_id,owner,stage,status,meeting_status,warm_intro,offer,priority_score,cadence,first_outreach,last_touch,next_touch,due,next_action,notes,source,raw_json) ' +
    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
  );

  const seen = new Set();
  for (const row of rows) {
    if (row.id == null) { r.skipped.push({ id: '(null)', reason: 'missing id (deal PK)' }); continue; }
    const did = String(row.id);
    if (seen.has(did)) { r.skipped.push({ id: did, reason: 'duplicate id in source (first-wins)' }); continue; }
    seen.add(did);
    const coId = did + '-co';
    const ctId = did + '-ct';

    insCo.run(coId, row.company ?? null, row.category ?? null, row.fit_thesis ?? null, row.tier ?? null, row.source ?? null,
      j({ id: coId, name: row.company, category: row.category, fit_thesis: row.fit_thesis, tier: row.tier }));
    audit('company', coId, { id: coId, name: row.company });
    r.tables.company++;

    insCt.run(ctId, coId, row.contact ?? null, row.title ?? null, row.email ?? null,
      row.emails_alt ?? null, row.phone ?? null, row.linkedin ?? null,
      j({ id: ctId, name: row.contact, title: row.title, email: row.email }));
    audit('contact', ctId, { id: ctId, name: row.contact });
    r.tables.contact++;

    insDeal.run(did, coId, ctId, row.owner ?? null, row.stage ?? null, row.status ?? null,
      row.meeting_status ?? null, row.warm_intro ?? null, row.offer ?? null,
      row.priority_score ?? null, row.cadence ?? null, row.first_outreach ?? null,
      row.last_touch ?? null, row.next_touch ?? null, row.due ?? null, row.next_action ?? null,
      row.notes ?? null, row.source ?? null, j(row));
    audit('deal', did, row);
    r.inserted++; r.tables.deal++;
  }
  report.push(r);
})();

// ---------------------------------------------------------------------------
// 3) tasks.json -> task  (wrapper object {generated_at,...,tasks:[]})
// ---------------------------------------------------------------------------
(function loadTasks() {
  const wrap = readJson('tasks.json');
  const rows = Array.isArray(wrap) ? wrap : (wrap.tasks || []);
  const r = { source: 'tasks.json', jsonCount: rows.length, inserted: 0, skipped: [], tables: { task: 0 } };
  const ins = db.prepare(
    'INSERT INTO task (id,title,state,owner,due_date,priority,category,description,source,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?)'
  );
  const seen = new Set();
  for (const t of rows) {
    if (t.id == null) { r.skipped.push({ id: '(null)', reason: 'missing id (task PK)' }); continue; }
    const id = String(t.id);
    if (seen.has(id)) { r.skipped.push({ id, reason: 'duplicate id in source (first-wins)' }); continue; }
    seen.add(id);
    ins.run(id, t.title ?? null, t.state ?? null, t.owner ?? null, t.due_date ?? null,
      typeof t.priority === 'number' ? t.priority : null, t.category ?? null, t.description ?? null, t.source ?? null, j(t));
    audit('task', id, t);
    r.inserted++; r.tables.task++;
  }
  report.push(r);
})();

// ---------------------------------------------------------------------------
// 4) opportunities.json -> opportunity (wrapper {..., opportunities:[]})
// ---------------------------------------------------------------------------
(function loadOpportunities() {
  const wrap = readJson('opportunities.json');
  const rows = Array.isArray(wrap) ? wrap : (wrap.opportunities || []);
  const r = { source: 'opportunities.json', jsonCount: rows.length, inserted: 0, skipped: [], tables: { opportunity: 0 } };
  const ins = db.prepare(
    'INSERT INTO opportunity (id,title,status,type,category,value,due,next_action,priority,description,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)'
  );
  const seen = new Set();
  for (const o of rows) {
    if (o.id == null) { r.skipped.push({ id: '(null)', reason: 'missing id' }); continue; }
    const id = String(o.id);
    if (seen.has(id)) { r.skipped.push({ id, reason: 'duplicate id in source (first-wins)' }); continue; }
    seen.add(id);
    ins.run(id, o.title ?? null, o.status ?? null, o.type ?? null, o.category ?? null,
      o.value ?? null, o.due ?? null, o.next_action ?? null,
      typeof o.priority === 'number' ? o.priority : null, o.description ?? null, j(o));
    audit('opportunity', id, o);
    r.inserted++; r.tables.opportunity++;
  }
  report.push(r);
})();

// ---------------------------------------------------------------------------
// 5) decisions.json -> decision (top-level array)
// ---------------------------------------------------------------------------
(function loadDecisions() {
  const rows = readJson('decisions.json');
  const r = { source: 'decisions.json', jsonCount: rows.length, inserted: 0, skipped: [], tables: { decision: 0 } };
  const ins = db.prepare(
    'INSERT INTO decision (id,source,related_item,title,question,context,proposed_action,type,options_json,priority,dedupe_key,status,answer,note,answered_at,answered_by,created,updated,raw_json) ' +
    'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
  );
  const seen = new Set();
  for (const d of rows) {
    if (d.id == null) { r.skipped.push({ id: '(null)', reason: 'missing id' }); continue; }
    const id = String(d.id);
    if (seen.has(id)) { r.skipped.push({ id, reason: 'duplicate id in source (first-wins)' }); continue; }
    seen.add(id);
    ins.run(id, d.source ?? null, d.relatedItem ?? null, d.title ?? null, d.question ?? null,
      d.context ?? null, d.proposedAction ?? null, d.type ?? null, j(d.options), d.priority ?? null,
      d.dedupeKey ?? null, d.status ?? null, d.answer ?? null, d.note ?? null,
      d.answeredAt ?? null, d.answeredBy ?? null, d.created ?? null, d.updated ?? null, j(d));
    audit('decision', id, d);
    r.inserted++; r.tables.decision++;
  }
  report.push(r);
})();

// ---------------------------------------------------------------------------
// 6) envelopes.json -> document (doc_type='envelope') + document_signer
// ---------------------------------------------------------------------------
(function loadEnvelopes() {
  const rows = readJson('envelopes.json');
  const r = { source: 'envelopes.json', jsonCount: rows.length, inserted: 0, skipped: [],
    tables: { document: 0, document_signer: 0 } };
  const insDoc = db.prepare(
    'INSERT INTO document (id,title,doc_type,status,version,body_html,created_at,raw_json) VALUES (?,?,?,?,?,?,?,?)'
  );
  const insSign = db.prepare(
    'INSERT INTO document_signer (document_id,name,email,role,token,signed,signed_at,ip,signature_type,raw_json) VALUES (?,?,?,?,?,?,?,?,?,?)'
  );
  for (const e of rows) {
    if (e.id == null) { r.skipped.push({ id: '(null)', reason: 'missing id' }); continue; }
    const id = String(e.id);
    // strip signatureData (huge base64 images) from raw_json to keep DB lean; preserved fidelity for all other fields
    const lean = { ...e, signers: (e.signers || []).map((s) => ({ ...s, signatureData: s.signatureData ? '[omitted]' : null })) };
    insDoc.run(id, e.title ?? null, 'envelope', e.status ?? null, 1, e.html ?? null, e.createdAt ?? null, j(lean));
    audit('document', id, { id, title: e.title, doc_type: 'envelope' });
    r.inserted++; r.tables.document++;
    for (const s of (e.signers || [])) {
      insSign.run(id, s.name ?? null, s.email ?? null, s.role ?? null, s.token ?? null,
        s.signed ? 1 : 0, s.signedAt ?? null, s.ip ?? null, s.signatureType ?? null,
        j({ ...s, signatureData: s.signatureData ? '[omitted]' : null }));
      r.tables.document_signer++;
    }
  }
  report.push(r);
})();

// ---------------------------------------------------------------------------
// Reconciliation report
// ---------------------------------------------------------------------------
const auditCount = (() => {
  // crude count via a fresh prepared select using exec is awkward across drivers;
  // recompute from report instead (every insert audited 1:1 for primary entities).
  return null;
})();

console.log('\n========== RECONCILIATION REPORT ==========');
console.log('driver:', db.driver, '| db:', DB_PATH, '\n');
const pad = (s, n) => String(s).padEnd(n);
console.log(pad('SOURCE', 24), pad('JSON', 6), pad('INSERTED', 9), 'TABLES (rows)');
console.log('-'.repeat(78));
let totalJson = 0, totalIns = 0, totalSkip = 0;
for (const r of report) {
  const tbls = Object.entries(r.tables).map(([k, v]) => `${k}=${v}`).join(' ');
  console.log(pad(r.source, 24), pad(r.jsonCount, 6), pad(r.inserted, 9), tbls);
  totalJson += r.jsonCount; totalIns += r.inserted; totalSkip += r.skipped.length;
  for (const s of r.skipped) console.log('    SKIP', s.id, '->', s.reason);
}
console.log('-'.repeat(78));
console.log(pad('TOTAL', 24), pad(totalJson, 6), pad(totalIns, 9), `skipped=${totalSkip}`);
console.log('\nNote: crm-data.json fans out 1 JSON row -> 3 tables (company+contact+deal).');
console.log('      envelopes fan out -> document + document_signer (per signer).');
console.log('      "INSERTED" counts the PRIMARY entity per source (deal, task, etc.).');
console.log('==========================================\n');

db.close();
console.log('mc.db created OK.');
