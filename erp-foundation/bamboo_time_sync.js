'use strict';
/**
 * bamboo_time_sync.js — Phase 2 timekeeping INTERFACE (Jon 2026-07-30: timekeeping lives in
 * BambooHR; MC only READS actuals for cost rollup). Pulls approved/clock time-tracking entries
 * from the Bamboo Time Tracking API and mirrors them into MC's audited `time_entry` table,
 * mapping each entry's Bamboo project/task to the ERP contract + WBS element. Never writes Bamboo.
 *
 * Bamboo stays the DCAA system of record (daily entry, supervisor approval, object-lock). This
 * interface is read-only + idempotent (stable ids, upsert) so re-runs reconcile, not duplicate.
 *
 * NOTE: until a Bamboo admin sets up Projects (= contracts) and Tasks (= DCAA cost codes / WBS),
 * `projectInfo` on entries is null and rows land UNMAPPED (project_id/wbs_id null). The pipeline
 * still works today; mapping lights up automatically once the Bamboo structure exists.
 *
 * Run:  node erp-foundation/bamboo_time_sync.js                       # dry-run, last 30d
 *       node erp-foundation/bamboo_time_sync.js --start 2026-09-01 --end 2026-09-30
 *       node erp-foundation/bamboo_time_sync.js --apply               # write into MC (audited)
 */
const fs = require('fs');
const path = require('path');
const os = require('os');
const { openErp } = require('./dal');

const APPLY = process.argv.includes('--apply');
function arg(name, def) { const i = process.argv.indexOf(name); return i > -1 ? process.argv[i + 1] : def; }

function creds() {
  let s = {};
  try { s = JSON.parse(fs.readFileSync(path.join(os.homedir(), '.openclaw', 'secrets.json'), 'utf8')); } catch {}
  return { sub: process.env.BAMBOO_SUBDOMAIN || s.bamboo_subdomain, key: process.env.BAMBOO_API_KEY || s.bamboo_api_key };
}
async function bambooGet(sub, key, endpoint) {
  const url = `https://api.bamboohr.com/api/gateway.php/${sub}/v1/${endpoint}`;
  const auth = Buffer.from(`${key}:x`).toString('base64');
  const r = await fetch(url, { headers: { Authorization: `Basic ${auth}`, Accept: 'application/json' } });
  if (!r.ok) throw new Error(`Bamboo ${endpoint} → HTTP ${r.status} ${await r.text().catch(() => '')}`);
  return r.json();
}

const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();

// Build a matcher from the ERP contracts + WBS so a Bamboo project/task name maps to (contract, wbs).
function buildMap(erp) {
  const contracts = erp.listContracts();
  const wbsByContract = {};
  for (const c of contracts) {
    wbsByContract[c.id] = erp.listWbs(c.id) || [];
  }
  return function map(projectInfo) {
    if (!projectInfo) return { project_id: null, wbs_id: null };
    const pName = norm(projectInfo.project && (projectInfo.project.name || projectInfo.project));
    const tName = norm(projectInfo.task && (projectInfo.task.name || projectInfo.task));
    const c = contracts.find(x => pName && (norm(x.number) === pName || norm(x.title).includes(pName) || pName.includes(norm(x.number))));
    if (!c) return { project_id: null, wbs_id: null };
    const wbsList = wbsByContract[c.id] || [];
    const w = wbsList.find(x => tName && (norm(x.name) === tName || norm(x.code) === tName || tName.includes(norm(x.code)) || tName.includes(norm(x.name))));
    return { project_id: c.id, wbs_id: w ? w.id : null };
  };
}

function ymd(d) { return d.toISOString().slice(0, 10); }

async function main() {
  const { sub, key } = creds();
  if (!sub || !key) { console.log('BambooHR not configured (bamboo_subdomain / bamboo_api_key).'); return; }
  const end = arg('--end', ymd(new Date()));
  const start = arg('--start', ymd(new Date(Date.now() - 30 * 864e5)));
  console.log(`Bamboo time sync ${start} → ${end} (${APPLY ? 'APPLY' : 'dry-run'})`);

  const entries = await bambooGet(sub, key, `time_tracking/timesheet_entries?start=${start}&end=${end}`);
  console.log(`  ${entries.length} timesheet entr${entries.length === 1 ? 'y' : 'ies'} returned.`);

  const erp = openErp(path.join(__dirname, 'mc.db'), { actor: 'bamboo-time-sync@exosaero.com', agent: 'bamboo-time-sync' });
  const map = buildMap(erp);
  let mapped = 0, unmapped = 0, approved = 0, total = 0;
  const rows = [];
  for (const e of entries) {
    const { project_id, wbs_id } = map(e.projectInfo);
    if (project_id) mapped++; else unmapped++;
    const isApproved = !!(e.approved === true || e.approved === 'approved' || e.approvedAt);
    if (isApproved) approved++;
    total += Number(e.hours) || 0;
    const row = {
      id: `bhr-time-${e.id}`,
      user_id: `bamboo-${e.employeeId}`,
      task_id: null,
      project_id, wbs_id,
      work_date: e.date,
      hours: Number(e.hours) || 0,
      labor_class: e.type || 'clock',
      notes: e.note || null,
      approved_by: isApproved ? (e.approvedByUserId ? `bamboo-user-${e.approvedByUserId}` : 'bamboo') : null,
      approved_at: e.approvedAt || null,
      locked: isApproved ? 1 : 0,   // object-lock: approved Bamboo time is immutable
      raw_json: e,
    };
    rows.push(row);
    if (APPLY) erp.upsertTimeEntry(row);
  }
  console.log(`  hours=${total.toFixed(1)} · mapped→WBS=${mapped} · unmapped=${unmapped} · approved/locked=${approved}`);
  if (unmapped && !mapped) {
    console.log('  NOTE: 0 entries mapped — Bamboo Projects/Tasks (contracts + WBS cost codes) not configured yet.');
    console.log('        Configure them in Bamboo admin, tag time to them, and mapping lights up automatically.');
  }
  if (!APPLY) { console.log('  DRY-RUN — re-run with --apply to write into MC time_entry (audited).'); return rows; }
  console.log(`  APPLIED: ${rows.length} time_entry row(s) upserted (audited). Feeds the WBS cost rollup.`);
}

main().catch(e => { console.error(e.message); process.exit(1); });
