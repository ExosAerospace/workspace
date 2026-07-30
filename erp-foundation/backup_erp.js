'use strict';
/**
 * backup_erp.js — Phase 0 deliverable: automated, restore-tested ERP database backup.
 *
 * Uses SQLite's `VACUUM INTO` to write a CONSISTENT snapshot of mc.db even while the DB is live
 * (WAL-safe — no torn reads). Then RESTORE-VERIFIES the snapshot by opening it and comparing row
 * counts of key tables against the source; a snapshot that doesn't reconcile is deleted, not kept.
 * Retention prunes old snapshots. This is the local (on-ExoMac) leg of the plan's 3-2-1:
 *   1) here on ExoMac  2) [copy to exobot-backup node]  3) [encrypted offsite in GCC High]
 * The two remote legs are wired separately (they need the node / GCC High target).
 *
 * Run:  node erp-foundation/backup_erp.js         (scheduled nightly via launchd com.exos.erp-backup)
 */
const fs = require('fs');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');

const DIR = __dirname;
const SRC = path.join(DIR, 'mc.db');
const OUT = path.join(DIR, 'backups');
const KEEP = 30;                       // retain last 30 nightly snapshots
const VERIFY_TABLES = ['company', 'contact', 'deal', 'employee', 'org_unit', 'audit_log', 'task'];

function ts() {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
function counts(dbFile) {
  const db = new DatabaseSync(dbFile, { readOnly: true });
  const out = {};
  for (const t of VERIFY_TABLES) {
    try { out[t] = db.prepare(`SELECT count(*) c FROM ${t}`).get().c; } catch { out[t] = null; }
  }
  db.close();
  return out;
}

function main() {
  if (!fs.existsSync(SRC)) { console.error('mc.db not found — run migrate.js first'); process.exit(1); }
  fs.mkdirSync(OUT, { recursive: true });
  const snap = path.join(OUT, `mc-${ts()}.db`);

  // consistent online snapshot
  const src = new DatabaseSync(SRC);
  src.exec(`VACUUM INTO '${snap.replace(/'/g, "''")}'`);
  src.close();

  // restore-verify: row counts must reconcile with the source
  const a = counts(SRC), b = counts(snap);
  const mismatch = VERIFY_TABLES.filter(t => a[t] !== b[t]);
  if (mismatch.length) {
    fs.unlinkSync(snap);
    console.error(`✗ backup FAILED verify (mismatch: ${mismatch.join(', ')}) — snapshot discarded`);
    process.exit(2);
  }
  const sizeMB = (fs.statSync(snap).size / 1048576).toFixed(1);

  // retention
  const snaps = fs.readdirSync(OUT).filter(f => /^mc-\d{8}-\d{6}\.db$/.test(f)).sort();
  const pruned = snaps.slice(0, Math.max(0, snaps.length - KEEP));
  for (const f of pruned) fs.unlinkSync(path.join(OUT, f));

  console.log(`✓ backup verified: ${path.basename(snap)} (${sizeMB} MB) — rows reconcile across ${VERIFY_TABLES.length} tables`);
  console.log(`  counts: ${VERIFY_TABLES.map(t => `${t}=${b[t]}`).join('  ')}`);
  console.log(`  retained ${Math.min(snaps.length, KEEP)} snapshot(s)${pruned.length ? `, pruned ${pruned.length}` : ''}`);
  console.log(`  NEXT (remote legs of 3-2-1): copy ${path.basename(snap)} to the exobot-backup node + encrypted GCC High offsite.`);
}
main();
