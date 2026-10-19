#!/usr/bin/env node
// Seed SSLC MC demo container with realistic demo data.
// Run: node scripts/seed_sslc_demo.js [--db /path/to/sslc.db]
'use strict';

const path = require('path');
const dbPath = (() => {
  const idx = process.argv.indexOf('--db');
  return idx >= 0 ? process.argv[idx + 1] : (process.env.ERP_DB_PATH || path.join(__dirname, '../erp-foundation/mc.db'));
})();

const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync(dbPath);

db.exec('PRAGMA foreign_keys = ON;');
db.exec('PRAGMA journal_mode = WAL;');

const now = new Date().toISOString();

function ins(table, row) {
  const keys = Object.keys(row);
  const vals = keys.map(k => row[k]);
  const ph = keys.map(() => '?').join(', ');
  try {
    db.prepare(`INSERT OR IGNORE INTO ${table} (${keys.join(', ')}) VALUES (${ph})`).run(...vals);
  } catch (e) {
    if (!e.message.includes('UNIQUE') && !e.message.includes('FOREIGN KEY')) {
      console.error(`Insert ${table} [${row.id}]:`, e.message.slice(0, 80));
    }
  }
}

// ── Roles ─────────────────────────────────────────────────────────────────────
['admin', 'manager', 'member', 'finance'].forEach(id => ins('role', { id, label: id.charAt(0).toUpperCase() + id.slice(1), description: '' }));

// ── Vendors / Suppliers ───────────────────────────────────────────────────────
const vendors = [
  { id: 'VND-001', name: 'Luxfer Gas Cylinders', active: 1, category: 'hardware', raw_json: JSON.stringify({ email: 'sales@luxfer.com', phone: '800-764-0366', city: 'Riverside', state: 'CA' }) },
  { id: 'VND-002', name: 'Chart Industries', active: 1, category: 'hardware', raw_json: JSON.stringify({ email: 'info@chartind.com', phone: '440-753-1490' }) },
  { id: 'VND-003', name: 'Parker Hannifin', active: 1, category: 'hardware', raw_json: JSON.stringify({ email: 'orders@parker.com' }) },
  { id: 'VND-004', name: 'Airgas', active: 1, category: 'consumables', raw_json: JSON.stringify({ email: 'orders@airgas.com' }) },
  { id: 'VND-005', name: 'Swagelok Texas', active: 1, category: 'hardware', raw_json: JSON.stringify({ email: 'houston@swagelok.com' }) },
  { id: 'VND-006', name: 'McMaster-Carr', active: 1, category: 'hardware', raw_json: '{}' },
  { id: 'VND-007', name: 'Orbital Sciences Corp', active: 1, category: 'services', raw_json: '{}' },
];
vendors.forEach(v => ins('vendor', v));

// ── Parts / Inventory Items ───────────────────────────────────────────────────
const parts = [
  { id: 'PART-HE-001', part_number: 'HE-3L-6K', description: 'He Pressurant Tank 6000 psi 3L — Helium pressurant sphere, 3 liter, 6000 psi MEOP', unit: 'EA', unit_cost: 8500.00, lead_time_days: 90, make_buy: 'buy', active: 1 },
  { id: 'PART-HE-002', part_number: 'HE-6L-6K', description: 'He Pressurant Tank 6000 psi 6L — 6 liter, 6000 psi MEOP', unit: 'EA', unit_cost: 14200.00, lead_time_days: 120, make_buy: 'buy', active: 1 },
  { id: 'PART-HE-003', part_number: 'HE-3L-10K', description: 'He Pressurant Tank 10000 psi 3L — 3 liter, 10000 psi MEOP', unit: 'EA', unit_cost: 19800.00, lead_time_days: 150, make_buy: 'buy', active: 1 },
  { id: 'PART-AL-001', part_number: 'AL-6061-4IN', description: 'Aluminum 6061-T6 Round Bar 4" dia', unit: 'FT', unit_cost: 45.00, lead_time_days: 14, make_buy: 'buy', active: 1 },
  { id: 'PART-CF-001', part_number: 'CF-IM7-12K', description: 'Carbon Fiber Tow IM7 12K', unit: 'LB', unit_cost: 32.00, lead_time_days: 21, make_buy: 'buy', active: 1 },
  { id: 'PART-EP-001', part_number: 'EP-9394-CRYO', description: 'Epoxy Resin Hysol EA 9394 (cryogenic grade)', unit: 'KG', unit_cost: 85.00, lead_time_days: 30, make_buy: 'buy', active: 1 },
  { id: 'PART-VLV-001', part_number: 'VLV-1/4-HP-SS', description: 'Fill/Drain Valve 1/4" HP Stainless, 15000 psi', unit: 'EA', unit_cost: 385.00, lead_time_days: 45, make_buy: 'buy', active: 1 },
  { id: 'PART-PRV-001', part_number: 'PRV-6100', description: 'Pressure Relief Valve 6100 psi, 1/4" NPT', unit: 'EA', unit_cost: 520.00, lead_time_days: 60, make_buy: 'buy', active: 1 },
  { id: 'PART-PTR-001', part_number: 'PTR-10K-KULITE', description: 'Pressure Transducer 0-10000 psi, Kulite XTM-190', unit: 'EA', unit_cost: 680.00, lead_time_days: 45, make_buy: 'buy', active: 1 },
];
parts.forEach(p => ins('part', p));

// ── Inventory transactions (current on-hand) ──────────────────────────────────
const inv_txns = [
  { id: 'IT-001', part_id: 'PART-HE-001', kind: 'count', qty: 4, source: 'seed', occurred_at: now },
  { id: 'IT-002', part_id: 'PART-HE-002', kind: 'count', qty: 2, source: 'seed', occurred_at: now },
  { id: 'IT-003', part_id: 'PART-HE-003', kind: 'count', qty: 1, source: 'seed', occurred_at: now },
  { id: 'IT-004', part_id: 'PART-AL-001', kind: 'count', qty: 24, source: 'seed', occurred_at: now },
  { id: 'IT-005', part_id: 'PART-CF-001', kind: 'count', qty: 150, source: 'seed', occurred_at: now },
  { id: 'IT-006', part_id: 'PART-EP-001', kind: 'count', qty: 12, source: 'seed', occurred_at: now },
  { id: 'IT-007', part_id: 'PART-VLV-001', kind: 'count', qty: 8, source: 'seed', occurred_at: now },
  { id: 'IT-008', part_id: 'PART-PRV-001', kind: 'count', qty: 6, source: 'seed', occurred_at: now },
  { id: 'IT-009', part_id: 'PART-PTR-001', kind: 'count', qty: 5, source: 'seed', occurred_at: now },
];
inv_txns.forEach(t => ins('inventory_txn', t));

// ── Bills of Materials (bom_line: assembly, section, item_no, part_id, qty_per) ──
const boms = [
  { id: 'BOM-HE001-001', assembly: 'HE-3L-6K', section: 'Pressure Vessel', item_no: '001', part_id: 'PART-AL-001', qty_per: 2.5 },
  { id: 'BOM-HE001-002', assembly: 'HE-3L-6K', section: 'Composite Shell', item_no: '002', part_id: 'PART-CF-001', qty_per: 3.2 },
  { id: 'BOM-HE001-003', assembly: 'HE-3L-6K', section: 'Composite Shell', item_no: '003', part_id: 'PART-EP-001', qty_per: 0.8 },
  { id: 'BOM-HE001-004', assembly: 'HE-3L-6K', section: 'Plumbing', item_no: '004', part_id: 'PART-VLV-001', qty_per: 1 },
  { id: 'BOM-HE001-005', assembly: 'HE-3L-6K', section: 'Plumbing', item_no: '005', part_id: 'PART-PRV-001', qty_per: 1 },
  { id: 'BOM-HE001-006', assembly: 'HE-3L-6K', section: 'Instrumentation', item_no: '006', part_id: 'PART-PTR-001', qty_per: 1 },
  { id: 'BOM-HE002-001', assembly: 'HE-6L-6K', section: 'Pressure Vessel', item_no: '001', part_id: 'PART-AL-001', qty_per: 4.0 },
  { id: 'BOM-HE002-002', assembly: 'HE-6L-6K', section: 'Composite Shell', item_no: '002', part_id: 'PART-CF-001', qty_per: 6.1 },
  { id: 'BOM-HE002-003', assembly: 'HE-6L-6K', section: 'Composite Shell', item_no: '003', part_id: 'PART-EP-001', qty_per: 1.5 },
  { id: 'BOM-HE002-004', assembly: 'HE-6L-6K', section: 'Plumbing', item_no: '004', part_id: 'PART-VLV-001', qty_per: 2 },
  { id: 'BOM-HE002-005', assembly: 'HE-6L-6K', section: 'Plumbing', item_no: '005', part_id: 'PART-PRV-001', qty_per: 1 },
  { id: 'BOM-HE002-006', assembly: 'HE-6L-6K', section: 'Instrumentation', item_no: '006', part_id: 'PART-PTR-001', qty_per: 2 },
];
boms.forEach(b => ins('bom_line', b));

// ── Purchase Orders ────────────────────────────────────────────────────────────
const pos = [
  { id: 'PO-001', vendor_id: 'VND-001', status: 'open', total: 34000.00, issued_at: '2026-09-15T00:00:00Z', raw_json: JSON.stringify({ notes: 'FY2026 He tank procurement, 4x HE-3L-6K', need_by: '2026-12-01' }) },
  { id: 'PO-002', vendor_id: 'VND-003', status: 'open', total: 4620.00, issued_at: '2026-10-01T00:00:00Z', raw_json: JSON.stringify({ notes: 'Parker valves — 12x VLV-1/4-HP-SS', need_by: '2026-11-15' }) },
  { id: 'PO-003', vendor_id: 'VND-005', status: 'pending', total: 8160.00, issued_at: '2026-10-18T00:00:00Z', raw_json: JSON.stringify({ notes: 'Swagelok HP fittings and tubing', need_by: '2026-11-30' }) },
  { id: 'PO-004', vendor_id: 'VND-002', status: 'open', total: 28400.00, issued_at: '2026-08-20T00:00:00Z', raw_json: JSON.stringify({ notes: 'Chart Industries LN2 cryogenic vessel 1000L', need_by: '2027-02-28' }) },
];
pos.forEach(p => ins('purchase_order', p));

const po_lines = [
  { id: 'POL-001', po_id: 'PO-001', description: 'He Pressurant Tank 3L 6000 psi (HE-3L-6K)', qty: 4, unit_price: 8500.00, amount: 34000.00 },
  { id: 'POL-002', po_id: 'PO-002', description: 'Fill/Drain Valve 1/4" HP (VLV-1/4-HP-SS)', qty: 12, unit_price: 385.00, amount: 4620.00 },
  { id: 'POL-003', po_id: 'PO-003', description: 'Swagelok HP fittings assorted', qty: 1, unit_price: 8160.00, amount: 8160.00 },
  { id: 'POL-004', po_id: 'PO-004', description: 'LN2 Cryogenic Vessel 1000L custom', qty: 1, unit_price: 28400.00, amount: 28400.00 },
];
po_lines.forEach(l => ins('po_line', l));

// ── MRP Run ────────────────────────────────────────────────────────────────────
ins('mrp_run', { id: 'MRP-001', run_at: now, actor: 'seed', scope: 'Q4-2026', summary_json: JSON.stringify({ notes: 'Q4 2026 MRP run — open tank orders and customer commitments' }) });
const mrp_lines = [
  { id: 'MRPL-001', run_id: 'MRP-001', part_id: 'PART-CF-001', assembly: 'HE-3L-6K,HE-6L-6K', gross: 25.0, on_hand: 150, on_order: 0, net: 125, unit_cost: 32.00, ext_cost: 4000.00, vendor: 'McMaster-Carr' },
  { id: 'MRPL-002', run_id: 'MRP-001', part_id: 'PART-AL-001', assembly: 'HE-3L-6K,HE-6L-6K', gross: 18.0, on_hand: 24, on_order: 0, net: 6, unit_cost: 45.00, ext_cost: 270.00, vendor: 'McMaster-Carr', demand_ref: 'WO-001,WO-002 — recommend PO 20 ft' },
  { id: 'MRPL-003', run_id: 'MRP-001', part_id: 'PART-EP-001', assembly: 'HE-3L-6K,HE-6L-6K', gross: 4.8, on_hand: 12, on_order: 0, net: 7.2, unit_cost: 85.00, ext_cost: 408.00, vendor: 'Airgas' },
  { id: 'MRPL-004', run_id: 'MRP-001', part_id: 'PART-PTR-001', assembly: 'HE-3L-6K,HE-6L-6K', gross: 6, on_hand: 5, on_order: 0, net: -1, unit_cost: 680.00, ext_cost: 4080.00, vendor: 'Swagelok Texas', demand_ref: 'WO-001,WO-002 — SHORT 1 unit, recommend PO' },
];
mrp_lines.forEach(l => ins('mrp_line', l));

// ── Companies / CRM ────────────────────────────────────────────────────────────
const companies = [
  { id: 'CO-001', name: 'Rocket Lab USA', category: 'Customer', raw_json: JSON.stringify({ website: 'https://rocketlabusa.com', industry: 'Launch Vehicle', status: 'active' }) },
  { id: 'CO-002', name: 'ABL Space Systems', category: 'Customer', raw_json: JSON.stringify({ website: 'https://ablspacesystems.com', industry: 'Launch Vehicle', status: 'active' }) },
  { id: 'CO-003', name: 'Relativity Space', category: 'Prospect', raw_json: JSON.stringify({ industry: 'Launch Vehicle', status: 'active' }) },
  { id: 'CO-004', name: 'Exos Aerospace', category: 'Partner', raw_json: JSON.stringify({ website: 'https://exosaero.com', industry: 'Launch Vehicle', status: 'active' }) },
];
companies.forEach(c => ins('company', c));

const contacts = [
  { id: 'CON-001', company_id: 'CO-001', name: 'Peter Beck', title: 'CEO', email: 'pbeck@rocketlabusa.com' },
  { id: 'CON-002', company_id: 'CO-002', name: 'Harry O\'Donoghue', title: 'VP Engineering', email: 'hodonoghue@ablspace.com' },
  { id: 'CON-003', company_id: 'CO-004', name: 'John Quinn', title: 'CEO', email: 'jquinn@exosaero.com' },
];
contacts.forEach(c => ins('contact', c));

// ── Invoices (AR/AP) ──────────────────────────────────────────────────────────
const invoices = [
  { id: 'INV-001', number: 'SSLC-2026-0034', amount: 17000.00, status: 'paid', issued_at: '2026-09-01T00:00:00Z', raw_json: JSON.stringify({ description: 'He Tank 3L 6000psi x2 — PO RL-20260834', customer: 'Rocket Lab USA', type: 'receivable' }) },
  { id: 'INV-002', number: 'SSLC-2026-0041', amount: 28400.00, status: 'open', issued_at: '2026-10-10T00:00:00Z', raw_json: JSON.stringify({ description: 'He Tank 6L 6000psi x2 — PO RL-20261012', customer: 'Rocket Lab USA', type: 'receivable', due_date: '2026-11-09' }) },
  { id: 'INV-003', number: 'SSLC-AP-2026-012', amount: 8500.00, status: 'open', issued_at: '2026-10-15T00:00:00Z', raw_json: JSON.stringify({ description: 'Exos subcontract — pressure vessel inspection services', vendor: 'Exos Aerospace', type: 'payable', due_date: '2026-11-14' }) },
];
invoices.forEach(i => ins('invoice', i));

// ── Work Orders ────────────────────────────────────────────────────────────────
const wos = [
  { id: 'WO-001', wo_number: 'WO-2026-001', item: 'He Pressurant Tank 3L 6000 psi (HE-3L-6K)', qty: 2, status: 'in_progress', due: '2026-11-15', raw_json: JSON.stringify({ notes: 'Rocket Lab PO RL-20261012 — 2x 3L He tanks', customer: 'Rocket Lab USA' }) },
  { id: 'WO-002', wo_number: 'WO-2026-002', item: 'He Pressurant Tank 6L 6000 psi (HE-6L-6K)', qty: 1, status: 'planned', due: '2026-12-15', raw_json: JSON.stringify({ notes: 'ABL Space test article — 1x 6L He tank', customer: 'ABL Space Systems' }) },
];
wos.forEach(w => ins('work_order', w));

// ── Org Units ─────────────────────────────────────────────────────────────────
['Engineering', 'Finance & Admin', 'Operations'].forEach((name, i) => {
  ins('org_unit', { id: `OU-00${i+1}`, name });
});

console.log('✓ SSLC demo data seeded');
db.close();
