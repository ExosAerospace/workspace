'use strict';
/**
 * seed_contracts.js — Phase 4: Contracts & CDRL. Models Exos's CONFIRMED federal awards as
 * contract → WBS → CDRL deliverables via the audited DAL, then prints the budget-vs-actual cost
 * rollup (labor hours from Bamboo/DCAA time_entry + material $ from POs, against WBS budget).
 *
 * ONLY awarded contracts are seeded here. Pursuits (TACFI, NASA Phase III conversion) stay in the
 * pipeline/opportunities until awarded — never modeled as contracts (no overstating traction).
 * Dollar values / CDRL dates left null where not verified (do not fabricate). WBS is DCAA-aligned
 * so it maps 1:1 to the Bamboo project/cost-code structure that books the labor.
 *
 * Run:  node erp-foundation/seed_contracts.js
 */
const path = require('path');
const { openErp } = require('./dal');
const erp = openErp(path.join(__dirname, 'mc.db'), { actor: 'jquinn@exosaero.com', agent: 'erp-seed-contracts' });

// ── Confirmed awards ──
const CONTRACTS = [
  { id: 'ctr-fa9300-25-c-6022', number: 'FA9300-25-C-6022', title: 'HVRR-RDRE SBIR Phase II (Project Hermes)',
    customer: 'USAF / AFRL', status: 'Active', funded_value: null, start_date: '2025-07',
    note: 'Basis for TACFI eligibility + sole-source Phase III (no $ ceiling). Funded value to load.' },
  { id: 'ctr-karmen-d2p2', number: 'Karmen D2P2', title: 'Karmen — BLK3 2-flight / 48-hr reusability demo',
    customer: 'USAF', status: 'Active', funded_value: 300000, start_date: null,
    note: 'USAF-funded $300K (vs ~$3M full scope).' },
];

// DCAA-aligned WBS (maps to Bamboo project cost codes). Budgets null until loaded.
const WBS = {
  'ctr-fa9300-25-c-6022': [
    { code: '1.0', name: 'Program Management' },
    { code: '2.0', name: 'RDRE Development' },
    { code: '3.0', name: 'HVRR Integration' },
    { code: '4.0', name: 'Test & Flight Demonstration' },
  ],
  'ctr-karmen-d2p2': [
    { code: '1.0', name: 'Program Management' },
    { code: '2.0', name: 'BLK3 Demo Preparation' },
    { code: '3.0', name: 'Flight Operations (2 flights / 48 hr)' },
  ],
};

// Standard SBIR CDRLs (format-standard, not fabricated specifics — due dates null until loaded).
const CDRLS = {
  'ctr-fa9300-25-c-6022': [
    { cdrl: 'A001', title: 'Monthly Progress / Status Reports', status: 'Open' },
    { cdrl: 'A002', title: 'Final Technical Report', status: 'Open' },
  ],
  'ctr-karmen-d2p2': [
    { cdrl: 'A001', title: 'Flight Demonstration Report', status: 'Open' },
  ],
};

let n = 0;
for (const c of CONTRACTS) {
  erp.upsertContract(c); n++;
  for (const w of (WBS[c.id] || [])) {
    erp.upsertWbs({ id: `${c.id}-wbs-${w.code}`, contract_id: c.id, code: w.code, name: w.name, budget: null }); n++;
  }
  for (const d of (CDRLS[c.id] || [])) {
    erp.upsertDeliverable({ id: `${c.id}-cdrl-${d.cdrl}`, contract_id: c.id, cdrl_number: d.cdrl, title: d.title, due_date: null, status: d.status }); n++;
  }
}

const fmt = v => v == null ? '—' : '$' + Number(v).toLocaleString();
console.log(`Seeded Contracts domain via audited DAL (${n} records, driver=${erp.driver}).\n`);
for (const c of erp.listContracts()) {
  console.log(`▸ ${c.number} — ${c.title}`);
  console.log(`    ${c.customer} · ${c.status} · funded ${fmt(c.funded_value)} · start ${c.start_date || '—'}`);
  const cdrls = erp.listCdrls(c.id);
  if (cdrls.length) console.log('    CDRLs: ' + cdrls.map(d => `${d.cdrl_number} (${d.status})`).join(', '));
  const { rows, totals } = erp.contractRollup(c.id);
  console.log('    Cost rollup (budget-vs-actual per WBS):');
  for (const r of rows) console.log(`      ${r.code} ${r.name.padEnd(34)} budget ${fmt(r.budget).padStart(10)} | labor ${r.labor_hours}h | material ${fmt(r.material_cost)}`);
  console.log(`      TOTAL${' '.repeat(33)} budget ${fmt(totals.budget).padStart(10)} | labor ${totals.labor_hours}h | material ${fmt(totals.material_cost)}`);
  console.log('');
}
console.log('Actuals are 0 until Bamboo/DCAA time + POs flow in — the rollup populates automatically as they do.');
erp.close();
