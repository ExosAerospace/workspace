# dr-failover — REPORT (2026-10-02, Jon 10:10 "go ahead 2-4" + item 1)

## Status
All 4 items are built, deployed and verified. Automatic failover runs in **DRY-RUN**: it watches and logs, but takes no action. Going live is Jon's decision D-7281894, after the drill.
Nothing was sent (no email or Discord). Mission Control and the OpenClaw gateway were not restarted. No data was deleted. Nothing needed admin/sudo on the Mini.

## What changed
1. **Nightly/hourly DR (item 1).** I continued the other session's work: the 09:53 backup had finished OK (rc=23, a few snapshot files vanished mid-copy), and that session had already loaded `com.exos.dr-backup` + `com.exos.backup-watchdog` at 10:08.
   - **Schedule:** I kept its **hourly** schedule instead of 02:00, because a delta run measures **60 s**. The staged plist now matches the live one.
   - **Backup now also copies:** `~/.cloudflared` (both tunnels: exos-mc creds and the lan-tunnel token, which was missing before), `~/.config/exos`, and the Studio's current com.exos launchd set plus a `_loaded.txt` list of loaded jobs.
   - **Lock:** a single-flight lock means the hourly run and the Sunday drill can't overlap.
   - **Checksum verify:** new `dr_verify.py` checks 6 critical files by sha256 on the Mini after every run. A mismatch counts as a failed backup, so no sentinel is written.
   - **Watchdog:** now also alerts on **checksum FAIL** and **"Mini link down"** (two probes, e.g. the Mini is FileVault-locked after a reboot). Each condition is deduped separately. Added fleet_log telemetry, `--dry-run`, and `--selftest` (7/7).
   - **Sentinel:** verified fresh (backup at 10:27, checksum verify OK).
2. **Hot-state sync (item 2).** New `scripts/dr_hot_sync.py`, launchd `com.exos.dr-hot-sync`, every 300 s, under run_logged. It copies:
   - sessions.json, users.json, .public-url;
   - mission-control/data/*.json(l), excluding the 13.9k snapshot files and .bak files (127 files, 42 MB on the first pass);
   - mc.db, via `sqlite3 .backup` (the db is in WAL mode);
   - the uploads delta.

   It never deletes, writes `.hot-sync-stamp.json`, and does nothing while the Studio is fenced. **Measured 1.5–2.4 s and ~190 KB per run**, so it isn't heavy. The mirrored mc.db passes `integrity_check`. MC logins survive a failover because sessions.json comes across, so no MC restart was needed.
3. **Automatic failover at 6 min (item 3).** Settings are in `config/failover.json` (mode=dry-run).
   - **Lease location:** Supabase **Storage**, private bucket `exos-control` (created; additive), object `control-lease.json`. It isn't a table because the service_role REST key can't run DDL and the only tables are the 8 CRM tables. Read-after-write consistency was verified.
   - **`control_lease.py`:** pure decision logic. The holder moves studio → mini-pending (a claim) → mini (a promote).
   - **`lease_renew.py`** (`com.exos.lease-renew`, Studio, 60 s): renews the lease, re-reads to verify, and pushes a heartbeat to the Mini over exos-mini. It fences the Studio when the lease is held by the Mini, or when there's been no Supabase AND no internet for ≥240 s.
     - In live mode, fencing writes `~/.openclaw/state/server-fenced.flag` and boots out the exos-mc and lan-tunnel connectors (plus the gateway if the lease is lost).
     - Unfencing happens only after a successful read shows the Studio still holds the lease.
     - In dry-run it only records `server-fence-dryrun.json`.
   - **`run_logged.py` fence gate:** while the flag exists, every non-exempt com.exos job skips with exit 0 and a `skipped: fenced` run record. The flag is only ever written in live mode, and any error in the gate falls back to running the job as before. Tested under a fake HOME.
   - **`failover_monitor.py`** (failover-monitor-exo3, `com.exos.failover-monitor`, **user LaunchAgent on the Mini**, runs from `~/dr-mirror/workspace/scripts` with /usr/bin/python3 3.9). It promotes only if ALL of these hold:
     - the lease is ≥360 s stale, via a mini-pending claim at least 60 s old;
     - the Studio is dark on both paths: (1) heartbeat over the exos-mini link, (2) MC https `/sign` over exos-mc (Access-bypassed, served by MC);
     - no maintenance hold is set.

     It then writes holder=mini and re-reads after 60 s before promoting. Promote means: restore from the mirror, start MC (waiting for :8080), start both tunnels, start the Studio's loaded jobs, and DM Jon + post in #exomac-system. Expect MC back **about 7–8 min after the Studio's last renewal**. Failback is manual.
   - **`failover_hold.py`:**
     - `--minutes N --reason ...` sets the hold, as a separate object `failover-hold.json` beside the lease, so the renewer can't overwrite it;
     - `--clear` and `--status`;
     - `--failback --confirm NAME` (Studio only).
   - **Selftest 7/7** on both boxes: 3-min blip → no promote; Studio dead → promote at 6–8 min; alive-but-partitioned → the Studio fences (at 5.0 min) before the Mini promotes (8.5 min), never both active, and it stays fenced after the partition heals; hold → no promote; Supabase outage from the Studio only → nothing; Studio back mid-claim → it reclaims; tunnel dead but Studio alive → no promote.
4. **Drill (item 4).** `failover_validate.py` now also checks: lease freshness, Studio not fenced, hot-sync age <15 min, Mini monitor alive, dry-run promote plan on the Mini (`--plan`, every input present), selftest on the Mini, and mirrored mc.db integrity. The degradation register is updated. **`--print` run: PASS 15/15**, RTO 60 s, hot RPO 11 s. It never runs a live promote.

## exo3
- **Registry:** new entries for com.exos.dr-hot-sync, com.exos.lease-renew (lease-renew-exo3) and com.exos.failover-monitor (failover-monitor-exo3). Updated entries for dr-backup, backup-watchdog and failover-validate (envelope, eval_suite, telemetry, escalation, change_log with approver John Quinn and status "pending Jon approval — D-…").
- **agent-evals:** liveness for dr-backup (3600), backup-watchdog (3600), dr-hot-sync (300), lease-renew (60), failover-monitor (60, host mini).
- **Telemetry:** fleet_log agents backup-watchdog, dr-hot-sync, lease-renew, failover-monitor, failover-hold.

## Commits (branch erp-phase0, not pushed)
- 91591d6 checkpoint: config/dr-backup.json (other session: dest → mini-dr)
- a8cf105 backup hardening + watchdog link/checksum alerts
- f69082c checkpoint: agent-registry.json dr-backup/backup-watchdog entries (other session; re-serialized at indent=1, content unchanged)
- dabb2f0 hot-state sync + registry/evals
- c18963e backup carries ~/.config/exos + launchd set
- 6b597b3 lease + fencing + failover monitor + hold (dry-run) + registry/evals
- b1a258c drill checks
- e879096 registry decision ids
- 8aea9d9 this report + retroactive registry entry for com.exos.mini-dr-link (the exo3 gate flagged it: the other session created it unregistered)

## Decisions filed (none answered or closed by me)
- **D-7281892** (med): keep the hourly verified backup + 5-min hot sync. Roll back: `launchctl bootout gui/$(id -u)/com.exos.dr-hot-sync`; `git revert a8cf105 c18963e`.
- **D-7281893** (high): keep the failover machinery in dry-run. Roll back: `launchctl bootout gui/$(id -u)/com.exos.lease-renew` on the Studio and `.../com.exos.failover-monitor` on the Mini.
- **D-7281894** (high): live failover drill **Sun 10/4 06:00 CT** (~15 min MC outage), then switch to live.
- **D-7281895** (med): staff note "use https://mc.exosaero.space only". The draft paragraph is in the card. **Not sent.**

## Left undone / needs Jon or admin
- **Mini → Studio SSH:** `ssh.exosaero.space` is behind interactive Cloudflare Access, so the Mini can't SSH to the Studio unattended. It needs a CF Access **service token** (Jon's CF account). The monitor doesn't depend on it: its two paths are the heartbeat over exos-mini and MC https.
- **OpenClaw gateway crons / Studio Exobot** are NOT auto-started on promote (one bot token = one gateway, and the Mini will run its own Exo (Mini) bot). This is manual after a failover. Decide this before going live.
- **Failback step 2** (sync Mini → Studio after a promote) has no script yet. It's a runbook step in the `failover_hold.py` docstring.
- **Promote overwrites the Mini's workstation files:** it rsyncs the mirror workspace over the Mini's `~/.openclaw/workspace` (no delete; secrets and tunnel files keep `.pre-promote-*` copies). That overwrites any Mini-local workstation edits. Review this at the drill against the Mini's workstation role.
- **FileVault on the Mini (kept per Jon):** after a power-loss reboot nothing runs until someone unlocks it, including the link, the backup, the hot sync and the failover monitor. The watchdog now alerts on this. A UPS for the Mini is recommended. `com.exos.mini-dr-link` is a user agent, so it only runs while exomac is logged in.
- **Supabase dependency:** if Supabase is down, the Mini never promotes (fail-safe).
- **Wasted space in the backup:** the `~/.openclaw` pass also copies `~/.openclaw/workspace`, so the workspace is mirrored twice (mirror is 26 GB). Excluding it from that pass would save time and space. Not changed, because it's outside this scope.
- **Superseded prototype:** `scripts/active_lease.py` (the 9/13 local-file prototype, untracked, never wired) is superseded by `control_lease.py` and left in place.
- **Untracked dependency:** `scripts/fleet_log.py` is still untracked in git (another session's file) but committed code imports it.
- Nothing needed sudo; all Mini jobs are user LaunchAgents.
