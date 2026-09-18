'use strict';
/**
 * bamboo_sync.js — BambooHR read-through INTERFACE (Jon 2026-07-30: HR is strictly an interface
 * to BambooHR; Bamboo stays the system of record). This pulls the employee directory + org from
 * the Bamboo REST API and mirrors it into MC's local cache (employee/org_unit/position) via the
 * audited DAL, so MC can show a directory / org chart and link tasks to people — WITHOUT owning
 * HR data. Bamboo remains authoritative; this never writes back to Bamboo, and never stores PII
 * (comp/benefits/SSN) — only directory-level fields (name, title, department, manager, work email).
 *
 * Credentials (secrets.json or env): BAMBOO_SUBDOMAIN, BAMBOO_API_KEY.
 * Run:  node erp-foundation/bamboo_sync.js            # dry-run (fetch + show, no writes)
 *       node erp-foundation/bamboo_sync.js --apply    # mirror into the local cache (audited)
 */
const fs = require('fs');
const path = require('path');
const os = require('os');
const { openErp } = require('./dal');

const DB = path.join(__dirname, 'mc.db');
const APPLY = process.argv.includes('--apply');

function creds() {
  let s = {};
  try { s = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.openclaw', 'secrets.json'), 'utf8')); } catch {}
  const sub = process.env.BAMBOO_SUBDOMAIN || s.bamboo_subdomain;
  const key = process.env.BAMBOO_API_KEY || s.bamboo_api_key;
  return { sub, key };
}

async function bambooGet(sub, key, endpoint) {
  const url = `https://api.bamboohr.com/api/gateway.php/${sub}/v1/${endpoint}`;
  const auth = Buffer.from(`${key}:x`).toString('base64');
  const r = await fetch(url, { headers: { Authorization: `Basic ${auth}`, Accept: 'application/json' } });
  if (!r.ok) throw new Error(`Bamboo ${endpoint} → HTTP ${r.status} ${await r.text().catch(() => '')}`);
  return r.json();
}

const slug = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'na';

async function main() {
  const { sub, key } = creds();
  if (!sub || !key) {
    console.log('BambooHR interface not configured. To enable, add to ~/.openclaw/secrets.json:');
    console.log('   "bamboo_subdomain": "<your-subdomain>",   "bamboo_api_key": "<api-key>"');
    console.log('(or set BAMBOO_SUBDOMAIN / BAMBOO_API_KEY env vars), then re-run.');
    return;
  }
  console.log(`Fetching BambooHR directory for "${sub}"…`);
  const dir = await bambooGet(sub, key, 'employees/directory');
  const emps = dir.employees || [];
  console.log(`  ${emps.length} employees in the Bamboo directory.`);

  // Bamboo's directory endpoint omits supervisor — pull it per employee for the manager mapping.
  // (No local override layer: BambooHR is the single system of record; make corrections there.)
  const supByName = {};                 // "Last, First" -> that person's bamboo id
  for (const e of emps) supByName[`${e.lastName}, ${e.firstName}`] = 'bamboo-' + e.id;
  for (const e of emps) {
    try { e._supervisor = (await bambooGet(sub, key, `employees/${e.id}?fields=supervisor`)).supervisor || null; }
    catch { e._supervisor = null; }
    e._dept = e.department || null;
    e._email = e.workEmail || null;
  }

  const depts = [...new Set(emps.map(e => e._dept).filter(Boolean))];
  const titles = [...new Set(emps.map(e => e.jobTitle).filter(Boolean))];

  if (!APPLY) {
    console.log(`\nDRY-RUN (no writes). Would mirror: ${depts.length} departments, ${titles.length} positions, ${emps.length} employees (+overrides, +managers).`);
    emps.slice(0, 12).forEach(e => console.log(`   ${e.displayName}  ·  ${e.jobTitle || '—'}  ·  ${e._dept || '—'}  ·  mgr ${e._supervisor || '—'}`));
    console.log('   Re-run with --apply to write the read-through cache (audited).');
    return;
  }

  const erp = openErp(DB, { actor: 'bamboo-sync@exosaero.com', agent: 'bamboo-sync' });
  erp.upsertOrgUnit({ id: 'org-exos', name: 'Exos Aerospace' });
  for (const d of depts) erp.upsertOrgUnit({ id: 'org-' + slug(d), name: d, parent_id: 'org-exos', source: 'bamboo' });
  for (const t of titles) erp.upsertPosition({ id: 'pos-' + slug(t), title: t, source: 'bamboo' });
  for (const e of emps) {
    erp.upsertEmployee({
      id: 'bamboo-' + e.id, full_name: e.displayName, email: e._email,
      org_unit_id: e._dept ? 'org-' + slug(e._dept) : null,
      position_id: e.jobTitle ? 'pos-' + slug(e.jobTitle) : null,
      manager_id: e._supervisor && supByName[e._supervisor] ? supByName[e._supervisor] : null,
      employment_status: 'Active', source: 'bamboo', bamboo_id: e.id,
    });
  }
  // ── RECONCILE: prune anything not in this Bamboo pull, so the mirror == Bamboo (read-through, self-healing) ──
  const keepEmp = new Set(emps.map(e => 'bamboo-' + e.id));
  const keepOrg = new Set(['org-exos', ...depts.map(d => 'org-' + slug(d))]);
  const keepPos = new Set(titles.map(t => 'pos-' + slug(t)));
  const pruned = { employee: 0, position: 0, org_unit: 0 };
  for (const row of erp.getEmployees()) if (!keepEmp.has(row.id) && erp.deleteEmployee(row.id)) pruned.employee++;
  for (const row of erp.getPositions()) if (!keepPos.has(row.id) && erp.deletePosition(row.id)) pruned.position++;
  for (const row of erp.getOrgUnits()) if (!keepOrg.has(row.id) && erp.deleteOrgUnit(row.id)) pruned.org_unit++;

  console.log(`\n✓ Mirrored from Bamboo: ${depts.length} departments, ${titles.length} positions, ${emps.length} employees (audited; Bamboo remains authoritative).`);
  if (pruned.employee || pruned.position || pruned.org_unit)
    console.log(`  Reconciled (pruned stale non-Bamboo rows): ${pruned.employee} employees, ${pruned.position} positions, ${pruned.org_unit} org units.`);
  erp.close();
}

main().catch(e => { console.error('bamboo_sync failed:', e.message); process.exit(1); });
