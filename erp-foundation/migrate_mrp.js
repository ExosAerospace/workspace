#!/usr/bin/env node
'use strict';
/**
 * migrate_mrp.js — ERP Phase 5C (MRP): part master, BOM, inventory ledger, missions, MRP runs, purchase requests.
 * Idempotent and ADDITIVE ONLY (CREATE TABLE/INDEX IF NOT EXISTS) — safe on the live mc.db.
 * Never run migrate.js on a live db (it rebuilds from JSON and wipes ASL/supply data).
 * schema.sql carries the same DDL for fresh builds.
 * Run: node erp-foundation/migrate_mrp.js
 */
const path = require('path');
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync(process.env.MRP_DB || path.join(__dirname, 'mc.db'));

const DDL = `
CREATE TABLE IF NOT EXISTS part (
  id             TEXT PRIMARY KEY,          -- pt-<normalized part number>
  part_number    TEXT,
  description    TEXT,
  vendor         TEXT,                      -- normalized vendor name from the BOM
  vendor_id      TEXT REFERENCES vendor(id),
  unit           TEXT,
  unit_cost      REAL,
  cost_basis     TEXT,                      -- paid | found | bom-sheet | none
  lead_time_days INTEGER,
  make_buy       TEXT,                      -- make | buy
  active         INTEGER DEFAULT 1,
  raw_json       TEXT,
  updated_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_part_pn ON part(part_number);
CREATE TABLE IF NOT EXISTS bom_line (
  id          TEXT PRIMARY KEY,             -- <assembly>:<section>#<item>
  assembly    TEXT,                         -- BLK3
  section     TEXT,
  item_no     TEXT,
  part_id     TEXT REFERENCES part(id),
  qty_per     REAL,                         -- per vehicle; NULL = not quantified on the BOM
  raw_json    TEXT,
  updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_bom_assembly ON bom_line(assembly);
CREATE INDEX IF NOT EXISTS idx_bom_part ON bom_line(part_id);
CREATE TABLE IF NOT EXISTS inventory_txn (
  id          TEXT PRIMARY KEY,
  part_id     TEXT REFERENCES part(id),
  kind        TEXT,                         -- count (physical snapshot) | receipt (ERP receiving) | adjust
  qty         REAL,                         -- count: absolute on-hand; receipt/adjust: delta
  location    TEXT,
  source      TEXT,
  ref         TEXT,
  occurred_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_invtxn_part ON inventory_txn(part_id, occurred_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invtxn_ref ON inventory_txn(kind, ref) WHERE ref IS NOT NULL AND kind = 'receipt';
CREATE TABLE IF NOT EXISTS mission (
  id          TEXT PRIMARY KEY,             -- M5, M6
  label       TEXT,
  customer    TEXT,
  vehicle     TEXT,                         -- BLK3 (= BOM assembly)
  asset_id    TEXT REFERENCES asset(id),
  status      TEXT,
  need_date   TEXT,                         -- vehicle build-complete need date (drives MRP need-by)
  raw_json    TEXT,
  updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS mrp_run (
  id           TEXT PRIMARY KEY,
  run_at       TEXT,
  actor        TEXT,
  scope        TEXT,
  summary_json TEXT
);
CREATE TABLE IF NOT EXISTS mrp_line (
  id          TEXT PRIMARY KEY,
  run_id      TEXT REFERENCES mrp_run(id) ON DELETE CASCADE,
  part_id     TEXT REFERENCES part(id),
  assembly    TEXT,
  demand_ref  TEXT,                         -- asset serial + missions, e.g. "S0 (M5, M6)"
  gross       REAL,
  on_hand     REAL,
  on_order    REAL,
  net         REAL,
  unit_cost   REAL,
  ext_cost    REAL,
  vendor      TEXT,
  vendor_id   TEXT,
  make_buy    TEXT,
  need_by     TEXT,
  action      TEXT                          -- none | buy | make | quantify (BOM qty missing)
);
CREATE INDEX IF NOT EXISTS idx_mrp_line_run ON mrp_line(run_id);
CREATE TABLE IF NOT EXISTS purchase_request (
  id            TEXT PRIMARY KEY,           -- pr-<run>-<n>
  run_id        TEXT REFERENCES mrp_run(id),
  vendor        TEXT,
  vendor_id     TEXT,
  status        TEXT,                       -- open | converted | cancelled | superseded
  est_total     REAL,
  need_by       TEXT,
  routes_to_jon INTEGER,                    -- est_total >= supply-config approval threshold
  po_id         TEXT REFERENCES purchase_order(id),
  raw_json      TEXT,                       -- lines [{part_id, part_number, description, qty, unit_cost}]
  created_at    TEXT,
  updated_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_pr_status ON purchase_request(status);
`;
db.exec(DDL);
const n = db.prepare("SELECT COUNT(*) c FROM sqlite_master WHERE type='table' AND name IN ('part','bom_line','inventory_txn','mission','mrp_run','mrp_line','purchase_request')").get().c;
console.log(`mrp migration: ${n}/7 Phase 5C tables present`);
db.close();
module.exports = { DDL };
