'use strict';
/**
 * seed_hr.js — Phase 1 HR core: populate the People domain with the real Exos org.
 *
 * NON-PII ONLY: departments, positions, employees, titles, and (inferred) reporting lines.
 * No comp bands, SSNs, emergency contacts, or benefits — those wait for the CUI-scoped Azure
 * Government host (plan §5A). Structural org data is non-PII and safe on ExoMac.
 *
 * Reporting lines marked source:"inferred" are best-guess from the capability matrix + org
 * structure — correct them in the HR UI; every change is audited. Idempotent (upserts).
 *
 * Run:  node erp-foundation/seed_hr.js
 */
const path = require('path');
const { openErp } = require('./dal');

const DB = path.join(__dirname, 'mc.db');
const erp = openErp(DB, { actor: 'jquinn@exosaero.com', agent: 'erp-seed-hr' });

// ── Departments (org_unit) ──
const ROOT = { id: 'org-exos', name: 'Exos Aerospace' };
const UNITS = [
  ROOT,
  { id: 'org-exec', name: 'Executive', parent_id: 'org-exos' },
  { id: 'org-eng', name: 'Engineering', parent_id: 'org-exos' },
  { id: 'org-tflops', name: 'Test & Flight Operations', parent_id: 'org-exos' },
  { id: 'org-mfg', name: 'Manufacturing', parent_id: 'org-exos' },
  { id: 'org-bd', name: 'Business Development', parent_id: 'org-exos' },
];

// ── Positions ──
const POSITIONS = [
  { id: 'pos-ceo', title: 'Cofounder & CEO', org_unit_id: 'org-exec' },
  { id: 'pos-coo', title: 'Cofounder & COO', org_unit_id: 'org-exec' },
  { id: 'pos-blk3-eng', title: 'BLK3 Vehicle Engineering & Flight Test', org_unit_id: 'org-eng' },
  { id: 'pos-eng-test', title: 'Engineering / Test', org_unit_id: 'org-tflops' },
  { id: 'pos-machinist', title: 'Machinist / Manufacturing', org_unit_id: 'org-mfg' },
  { id: 'pos-bd', title: 'Business Development', org_unit_id: 'org-bd' },
  { id: 'pos-eng', title: 'Engineering', org_unit_id: 'org-eng' },
];

// ── Employees (non-PII). manager lines flagged inferred where not certain. ──
const EMP = [
  { id: 'emp-jquinn', full_name: 'John Quinn', email: 'jquinn@exosaero.com', position_id: 'pos-ceo', org_unit_id: 'org-exec', manager_id: null },
  { id: 'emp-nmilburn', full_name: 'Neil Milburn', email: 'nmilburn@exosaero.com', position_id: 'pos-coo', org_unit_id: 'org-exec', manager_id: 'emp-jquinn', note: 'Retiring ~2027-05 (Part 450); training successors.' },
  { id: 'emp-peaton', full_name: 'Phil Eaton', email: 'peaton@exosaero.com', position_id: 'pos-blk3-eng', org_unit_id: 'org-eng', manager_id: 'emp-nmilburn', mgr_source: 'inferred' },
  { id: 'emp-snorsworthy', full_name: 'Steve Norsworthy', email: 'snorsworthy@exosaero.com', position_id: 'pos-eng-test', org_unit_id: 'org-tflops', manager_id: 'emp-nmilburn', mgr_source: 'inferred', note: 'Succession to Victor Castilleja ~Sep/Oct 2026.' },
  { id: 'emp-mtalley', full_name: 'Mike Talley', email: 'mtalley@exosaero.com', position_id: 'pos-machinist', org_unit_id: 'org-mfg', manager_id: 'emp-nmilburn', mgr_source: 'inferred' },
  { id: 'emp-lquinn', full_name: 'Lizi Quinn', email: 'lquinn@exosaero.com', position_id: 'pos-bd', org_unit_id: 'org-bd', manager_id: 'emp-jquinn', mgr_source: 'inferred' },
  { id: 'emp-rblink', full_name: 'Russ Blink', email: 'rblink@exosaero.com', position_id: 'pos-eng', org_unit_id: 'org-eng', manager_id: 'emp-nmilburn', mgr_source: 'inferred', note: 'Role/title to confirm (survey pending).' },
  { id: 'emp-kballard', full_name: 'Kyle Ballard', email: 'kballard@exosaero.com', position_id: 'pos-eng', org_unit_id: 'org-eng', manager_id: 'emp-nmilburn', mgr_source: 'inferred', note: 'Role/title to confirm (survey pending).' },
  { id: 'emp-vcastilleja', full_name: 'Victor Castilleja', email: null, position_id: 'pos-eng-test', org_unit_id: 'org-tflops', manager_id: 'emp-nmilburn', employment_status: 'Incoming', mgr_source: 'inferred', note: 'Incoming — Steve Norsworthy succession (~Sep/Oct 2026).' },
];

let n = 0;
for (const u of UNITS) { erp.upsertOrgUnit(u); n++; }
for (const p of POSITIONS) { erp.upsertPosition(p); n++; }
for (const e of EMP) { erp.upsertEmployee(e); n++; }

console.log(`Seeded People domain via audited DAL (${n} records, actor=jquinn@exosaero.com, driver=${erp.driver}).\n`);
console.log('Org chart:');
for (const e of erp.listEmployees()) {
  console.log(`  ${(e.org_unit || '—').padEnd(26)} ${(e.full_name || '').padEnd(20)} ${e.title || ''}${e.employment_status !== 'Active' ? '  [' + e.employment_status + ']' : ''}`);
}
console.log('\nLast 6 audit rows (proof every write is logged):');
for (const a of erp.recentAudit({ limit: 6 })) console.log(`  #${a.id} ${a.action} ${a.entity}/${a.entity_id} by ${a.actor} @ ${a.ts.slice(0, 19)}`);
erp.close();
