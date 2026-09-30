# r2-launchd-residuals worker report (2026-09-30, resumed run)

## Decisions filed for Jon (all open; none answered or closed by me)
| ID | What | Priority |
|---|---|---|
| D-7281860 | Keep/roll back: 25 login-start jobs reloaded onto run logging (f60a3e7, a067f0a) | med |
| D-7281861 | Keep/roll back: email-bridge password drift + login-storm alarm (a93b78b) | high |
| D-7281862 | Keep/roll back: 4 chained jobs no longer hide a failed step (5727c21, 6486f82) | med |
| D-7281863 | Held: may I reload mc-email-command (it replies to non-Exos MC users)? | high |
| D-7281864 | Held: PIEE reminder is due now but launchd won't fire it until ~10/19 (lockout ~10/4) | high |
| D-7281865 | Decision only (money): gate qb_deposit_sync so deposit matches are proposed, then human-confirmed | high |

## What changed (commits)
- **f60a3e7** (9/29, earlier run): 14 harmless RunAtLoad jobs reloaded onto run_logged.
- **a93b78b** (+ **ad41142**, which restored the file mode): `scripts/mail_bridge_guard.py`, wired into the hourly agent_eval.
  - Root cause of the IMAP "no such user" errors: `secrets.json` `protonmail_bridge_smtp_password` still held the Mini's value after the cutover, while the Studio Bridge uses `~/.config/exos/bridge-studio.pw`.
  - The flood of failed logins then tripped Bridge's lockout, which caused the "too many login attempts" errors.
  - Another session synced the password at about 07:40 CDT on 9/29. The last error in the run logs is 07:36, and nothing has errored since.
  - Parallel polling amplified the problem but didn't cause it: the schedules didn't change and the errors still stopped.
  - The guard compares hashes only and never logs in. It FAILs on password drift, and on 3 or more auth-error runs across 2 or more jobs within 2 hours.
  - Checks: selftest 11/11. Replaying the real 9/29 log flags 37 runs across 4 jobs. Live status is OK.
  - Not fixed (not needed now): 27 scripts each call imaplib directly. A shared IMAP back-off would need changes to all 27. I'd only suggest it if this recurs.
- **a067f0a**: 9 more RunAtLoad jobs reloaded:
  - capstone-capture, capture-action-dispatch, claude-auth-keepalive, completion-watchdog, cron-watchdog, decision-send-watcher, delivery-sweeper, payload-intake, priority-inbox-watcher.
  - Each shows the wrapper in `launchctl print` and logged a run with exit 0 at 13:05.
  - Also recorded here: outreach-autoclose and sent-loop-closer, which the killed run reloaded at 22:47 on 9/29.
  - Held: mc-email-command (D-7281863) and piee-login-reminder (D-7281864).
- **5727c21**: `scripts/run_chain.py`, the wrapper template for chained jobs. It keeps `;` semantics but exits with the first failing step's status, names that step on stderr and logs a fleet_log `chain_step_failed` event. Selftest 9/9.
- **6486f82**: `scripts/convert_chain_job.py`. It backs up to `~/Library/LaunchAgents/.pre-runchain-backup/`, lints the plist and supports `--restore`.
  - Converted and reloaded: dashboard-data-refresh, doc-manager, sent-followup-tracker (nested under task_ledger) and sent-loop-closer. Each shows run_chain live in launchd.
  - sent-loop-closer then ran with exit 0.
  - I left the `&&` chains alone because they already fail fast.
- **5b6a97e**: agent-registry.json change_log, eval, telemetry and escalation updates for everything above. Approver is John Quinn, status "pending Jon approval — D-xxxx".

## Verified
- `launchctl list | grep -c com.exos` = 151 throughout.
- All the new or changed scripts pass `py_compile` and their own selftests. `agent_eval --selftest` passes, and a dry-run of agent_eval completed (rc 0).
- All 4 converted plists pass `plutil -lint`.
- Mission Control and the OpenClaw gateway were NOT restarted. No crons were edited.

## Notes / left undone
- **Shared-tree races:**
  - r2-cron-hygiene's commit b7d2dae briefly dropped my agent_eval hook. They restored it in 5a51294, and HEAD now has both.
  - My first 4b commit swept in another session's staged shop-inventory files. I soft-reset that one local, unpushed commit right away and recommitted only my file through a private index. Their files are staged again as they were.
  - All my later commits used a private index.
- I deleted one test line (`fixture-chain-test`) from `logs/runs/2026-09-30.jsonl` so it wouldn't show up in tomorrow's failure report. The rewrite took milliseconds; a run finishing in that window could in theory have lost its log line.
- Not done:
  - Unwrapped templates in `config/launchd/` (capital-bridge-nudge, opfinance-*, supplier-dd-exo3). A re-install from those templates would undo the wrap.
  - The qb_deposit_sync gate itself (waits on D-7281865).
  - PIEE long-term fix: move it to a fixed calendar date (StartCalendarInterval), mentioned in D-7281864.
