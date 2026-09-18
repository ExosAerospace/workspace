'use strict';
/**
 * migrate_commissions.js — Sales-agent commission module (additive, idempotent).
 *
 * Adds three tables to mc.db so commissions ride the same audited ERP spine as
 * contracts (not the CRM Supabase): they link contract → who initiated → payout.
 *
 *   sales_agent          — the agent + their agreement terms (rate, bonus, equity)
 *   contract_attribution — WHO initiated/supported a contract (drives who gets paid)
 *   commission           — the ledger: one row per customer payment → commission due → paid
 *
 * Run:  node erp-foundation/migrate_commissions.js
 */
const path = require('path');
const { openRawFallback } = (() => {
  // reuse the DAL's driver selection without exporting it
  try { require('better-sqlite3'); } catch (_) {}
  return {};
})();

const DB = path.join(__dirname, 'mc.db');

function open(file) {
  try {
    const Database = require('better-sqlite3');
    const db = new Database(file);
    return { run: (s) => db.exec(s), close: () => db.close() };
  } catch (_) {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(file);
    return { run: (s) => db.exec(s), close: () => db.close() };
  }
}

const db = open(DB);
// Reopen with query support for the additive column check.
const q = (() => {
  try { const D = require('better-sqlite3'); const d = new D(DB); return { all:(s)=>d.prepare(s).all(), run:(s)=>d.exec(s), close:()=>d.close() }; }
  catch (_) { const { DatabaseSync } = require('node:sqlite'); const d = new DatabaseSync(DB); return { all:(s)=>d.prepare(s).all(), run:(s)=>d.exec(s), close:()=>d.close() }; }
})();
db.run(`
CREATE TABLE IF NOT EXISTS sales_agent (
  id            TEXT PRIMARY KEY,
  name          TEXT,
  email         TEXT,
  base_rate     REAL,            -- e.g. 0.05 = 5% of each customer payment
  bonus_rate    REAL,            -- additional rate when bonus_condition is met
  bonus_condition TEXT,          -- human description of when the bonus applies
  equity_shares INTEGER,
  equity_vesting TEXT,
  agreement_doc TEXT,            -- path to the signed agreement
  status        TEXT DEFAULT 'Active',
  raw_json      TEXT
);

CREATE TABLE IF NOT EXISTS contract_attribution (
  id            TEXT PRIMARY KEY,
  contract_id   TEXT NOT NULL REFERENCES contract(id),
  agent_id      TEXT NOT NULL REFERENCES sales_agent(id),
  role          TEXT DEFAULT 'initiated',  -- 'initiated' | 'supported'
  rate          REAL,                      -- override; NULL = use agent.base_rate
  effective_date TEXT,
  note          TEXT,
  raw_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_attr_contract ON contract_attribution(contract_id);
CREATE INDEX IF NOT EXISTS idx_attr_agent    ON contract_attribution(agent_id);

CREATE TABLE IF NOT EXISTS commission (
  id              TEXT PRIMARY KEY,
  contract_id     TEXT REFERENCES contract(id),
  agent_id        TEXT REFERENCES sales_agent(id),
  customer        TEXT,
  payment_amount  REAL,          -- the customer payment Exos received
  payment_date    TEXT,          -- date Exos was paid
  rate            REAL,          -- base rate applied
  bonus_applies   INTEGER DEFAULT 0,
  bonus_rate      REAL DEFAULT 0,
  commission_amount REAL,        -- (rate + bonus) * payment_amount
  status          TEXT DEFAULT 'due',   -- 'due' | 'paid' | 'void'
  due_date        TEXT,          -- payment_date + 30 days (per agreement)
  paid_date       TEXT,
  qb_ref          TEXT,          -- QuickBooks bill/payment reference
  note            TEXT,
  raw_json        TEXT
);
CREATE INDEX IF NOT EXISTS idx_comm_status ON commission(status);
CREATE INDEX IF NOT EXISTS idx_comm_agent  ON commission(agent_id);
CREATE INDEX IF NOT EXISTS idx_comm_contract ON commission(contract_id);
`);
db.close();

// Additive columns for the mass-aware bonus (safe to re-run).
const cols = q.all("PRAGMA table_info(commission)").map(c => c.name);
for (const [name, type] of [['booked_kg','REAL'],['capacity_kg','REAL'],['bonus_mass','REAL'],['bonus_base_amount','REAL']]) {
  if (!cols.includes(name)) { q.run(`ALTER TABLE commission ADD COLUMN ${name} ${type}`); console.log('  + column commission.' + name); }
}
q.close();
console.log('✓ commission tables ready (sales_agent, contract_attribution, commission)');
