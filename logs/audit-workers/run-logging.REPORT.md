# run-logging worker report (2026-09-28)

## What changed
1. **scripts/run_logged.py** (commit f6030e2) is a wrapper: `run_logged.py <label> -- <original command>`. It runs the command exactly as before (same argv, env, cwd, stdin and stdout). Stderr is passed through live to the job's normal stderr log. After each run it appends one JSON line to `logs/runs/YYYY-MM-DD.jsonl` with label, start, end, duration, exit code or signal, and the last 50 stderr lines. The job's exit code is passed through unchanged. A signal death is re-raised, so launchd sees the same status. SIGTERM and similar signals are forwarded to the job. If logging itself fails, the job's result is not affected. It runs under /usr/bin/python3, so it doesn't depend on mise or PATH.
2. **scripts/run_failures_report.py** and the launchd job **com.exos.run-failures-report**, daily at 06:30 (commit db1edaf).
   - It writes `reports/run-failures/YYYY-MM-DD.md`. The report lists failed runs with their stderr tail, plus wrapped jobs whose schedule should have fired in the last 24h but logged no run.
   - Only when there are failures or missed runs, it creates or updates one open MC task (owner Exo, source `run-failures-report`, framed as "proposed review"). It never sends email or Discord.
   - To pass exo3-gate, the job is registered in `agent-registry.json` and added to `config/agent-evals.json` for liveness checks. Plist source: the run-failures-report template in `config/launchd/`.
3. **scripts/convert_job_to_logged.py** (commit 7fdb631, later fixes in a710e79 and b2037ff).
   - Before changing a plist it backs up the original to `~/Library/LaunchAgents/.pre-runlog-backup/`. The first backup is never overwritten.
   - It is idempotent. The new plist is checked with `plutil -lint` before it replaces the old one.
   - Supports `--dry-run`, `--all --limit N`, `--reload` and `--restore <label>`.
   - With `--reload` it only reloads jobs that are loaded, not running right now and not RunAtLoad. If a reload fails it restores the original plist.
4. **Converted 143 jobs in 8 batches** (commits a710e79, 6c4fa06, b4362b1, 7b2b40f, b239630, b2037ff, bf97477, 8e25dcc). The manifest is `logs/runs/conversion-manifest.json` and the log is `logs/runs/conversion.log`.
   - 116 of them are reloaded and live. The other 27 are the RunAtLoad jobs listed below. run-failures-report was wrapped when it was created, so 144 jobs are wrapped in total and 117 are live.
   - After every batch `launchctl list | grep -c com.exos` stayed at 149, never dropping. It rose from 148 because run-failures-report was added and another session added mc-recycle-purge.
5. **scripts/agent_eval.py** (commit d810221): its liveness check now looks past the wrapper to find a job's real script name. Without this, every wrapped job would resolve to "run_logged".
6. **.gitignore**: ignores `logs/runs/*.jsonl`. The manifest and conversion log stay tracked. This change is uncommitted; it goes in with this report.

## Converted, takes effect on next load (RunAtLoad=true, NOT reloaded)
capability-gap-scan, capstone-capture, capstone-queue-refresh, capture-action-dispatch, claude-auth-keepalive, completion-watchdog, cron-watchdog, decision-note-router, decision-send-watcher, delivery-sweeper, expense-workflow, fleet-status, mc-email-command, mc-md-export, mc-snapshot-export, mission-score, outreach-autoclose, payload-intake, piee-login-reminder, priority-inbox-watcher, program-state, quote-close-stamp, sent-loop-closer, task-ledger-snapshot, task-note-command, util-metrics, warm-ollama (all com.exos.*). Their plists on disk are wrapped. The running launchd definition is still the original until the next login or reboot, or a deliberate reload.

## Skipped (not touched)
com.exos.missioncontrol, com.exos.series-a-worklist (still unloaded/disabled, never bootstrapped), com.exos.mc-tunnel (cloudflared), com.exos.vaultwarden-backup (vault), com.exos.capital-bridge-funds and com.exos.capital-bridge-nudge (their names contain "bridge", so I skipped them to be safe). Mission Control was not restarted.

## Verified
- Wrapper tests: exit codes 7, 0, 127 and 143, SIGTERM forwarding, env and cwd passthrough, stdin, stderr tail capped at 50 lines, and a backgrounded grandchild doesn't hang it.
- Report tested on synthetic data: failures listed and a missed daily job detected.
- Under real launchd, run-failures-report, receiving-capture, guild-channel-watchdog, inventory-capture and assignment-notifier all logged runs with exit 0. `launchctl print` shows the wrapped arguments.
- All 150 com.exos plists pass `plutil -lint`.
- The three non-zero `launchctl list` statuses (mc-email-command, outreach-autoclose, payload-intake, all exit 1) are RunAtLoad jobs still running their original unwrapped command, so those failures predate this work. Worth a human look.

## Left undone / watch items
- **mc-recycle-purge** was added by another session during this run and got wrapped and reloaded in batch 4. If that session re-copies its plist from a template, the wrap is lost. Re-run `convert_job_to_logged.py --reload com.exos.mc-recycle-purge` in that case. The same applies to **dataroom-bd-refresh**, which has an untracked template in config/launchd/ from another session.
- Future new jobs aren't wrapped automatically. To catch them, run `python3 scripts/convert_job_to_logged.py --all --reload` periodically or at install time.
- The "expected but never ran" check only covers jobs that have been wrapped for the full 24h window, so the first useful 06:30 report is 2026-09-30.
- The committed templates in config/launchd/ (capital-bridge-nudge, opfinance-alerts, opfinance-pulse, supplier-dd-exo3) are still unwrapped. If someone re-installs opfinance-* from those templates, the wrap is undone.
