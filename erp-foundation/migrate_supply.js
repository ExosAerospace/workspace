#!/usr/bin/env node
'use strict';
/**
 * migrate_supply.js — Phase 5 Supply Chain (supplier master/ASL, purchase orders, receiving inspection).
 * Idempotent: adds columns to the Phase-0 stub tables (vendor / purchase_order / po_line / receipt) on an
 * existing mc.db. schema.sql carries the same columns for fresh builds. Rich fields live in raw_json.
 * Run: node erp-foundation/migrate_supply.js
 */
const path = require('path');
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync(path.join(__dirname, 'mc.db'));

const COLS = {
  vendor: ['qb_id TEXT', 'asl_status TEXT', 'category TEXT', 'country TEXT', 'flight_critical INTEGER',
           'dd_tier TEXT', 'review_due TEXT', 'active INTEGER', 'updated_at TEXT'],
  purchase_order: ['po_number TEXT', 'source TEXT', 'qb_id TEXT', 'requested_by TEXT', 'approved_by TEXT',
                   'approved_at TEXT', 'need_by TEXT', 'promised_date TEXT', 'contract_id TEXT', 'decision_id TEXT',
                   'flight_critical INTEGER', 'updated_at TEXT'],
  po_line: ['line_no INTEGER', 'part_number TEXT', 'account TEXT', 'amount REAL', 'qty_received REAL'],
  receipt: ['po_line_id TEXT', 'qty_received REAL', 'qty_accepted REAL', 'qty_rejected REAL', 'result TEXT',
            'coc_received INTEGER', 'received_by TEXT', 'ncr_id TEXT'],
};
let added = 0;
for (const [t, cols] of Object.entries(COLS)) {
  const have = new Set(db.prepare(`PRAGMA table_info(${t})`).all().map(r => r.name));
  for (const c of cols) {
    const name = c.split(' ')[0];
    if (!have.has(name)) { db.exec(`ALTER TABLE ${t} ADD COLUMN ${c}`); added++; console.log(`+ ${t}.${name}`); }
  }
}
db.exec(`CREATE INDEX IF NOT EXISTS idx_po_vendor ON purchase_order(vendor_id);
CREATE INDEX IF NOT EXISTS idx_po_line_po ON po_line(po_id);
CREATE INDEX IF NOT EXISTS idx_receipt_po ON receipt(po_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_vendor_qb ON vendor(qb_id) WHERE qb_id IS NOT NULL;`);
console.log(`supply-chain migration: ${added} column(s) added`);
db.close();
