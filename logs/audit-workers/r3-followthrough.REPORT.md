# r3-followthrough: REPORT (exo3 round 3, 2026-10-02)

Jon answered the 4 EXO3 cards on 2026-10-01 (around 06:10 CDT). Before acting, I checked that each one was answered by a human: status "answered" and answeredBy "John Quinn". All four are now carried out.

What this run did not do:
- No emails or Discord messages.
- No MC or gateway restart, no `openclaw cron run`.
- No QuickBooks writes, and no money moved.
- Nothing pushed.

## Decisions filed (both open; I answered or closed none)
| id | priority | what |
|---|---|---|
| **D-7281890** | high | Keep or roll back the web-only pilot on the Grant & Contract Scanner (item 3) |
| **D-7281891** | high | GFE copies are deleted, but the Time Machine backups still hold them. How should those be handled? (item 4) |

Items 1 and 2 got no new cards. Jon had already approved those exact changes (D-7281865, D-7281863), and their change_log entries cite those decisions.

## Commits (in order)
| hash | what |
|---|---|
| c97effc | Item 2: conversion manifest records the mc-email-command reload |
| 76e961b | Item 1: `qb_deposit_sync.py` now proposes; a human books |
| 214e8fb | Item 1: registry and evals for qb-deposit-sync |
| e3a40b7 | Item 3: cron guards read the OpenClaw 2026.9.7 store again, plus the restricted-tier guard |
| ba6dc0d | Item 3 and item 2: registry and evals (pilot cron entry, mc-email-command change_log) |
| be07f31 | Checkpoint: another session's uncommitted edits in `compliance/cui-remediation-log.md`, committed as-is |
| 169f5d3 | Item 4: GFE deletion logged (paths and sha256 only) |

## 1. D-7281865: qb_deposit_sync is now propose-only
How it works now:
- A confident match no longer credits a lane. It becomes a ledger proposal.
- Each run's new proposals go on ONE consolidated high-priority EXO3 card (dedupeKey `qb-deposit:<digest>`).
- Lanes and the tracker are credited only when THAT card is answered by a human with "Book …".
- These never book:
  - token or agent answers (since e13a807 they leave the card open with a proposedAnswer)
  - an answeredBy that names an agent
  - a blank answeredBy
  - "Hold"
  - an answer on a different card
- "Don't book" moves the lines to pending review.
- The 17 existing matches are grandfathered, with the count recorded in `gate.grandfathered_matched` on the first live run.
- If filing the card fails, the proposals stay unbooked and are retried on the next run.
- Telemetry: fleet_log `deposit_sync_run`, `deposit_proposals_filed`, `deposit_booked`, `deposit_rejected` and `deposit_card_failed`.

Checks:
- `--selftest` passes 18/18 on both python 3.9 (launchd) and 3.14. It replays "auto-booked without click".
- Live `--dry` run: QuickBooks read-only, 20 lines, 0 new, ledger byte-identical afterwards.

Registry: autonomy is now Propose-only, with the envelope, eval_suite, telemetry, escalation and risk MED updated. The change_log cites approver John Quinn on D-7281865. agent-evals has the selftest command.

## 2. D-7281863: mc-email-command reloaded onto run_logged
- Reloaded at 07:24:55 CDT with bootout + bootstrap, the same method as a067f0a.
- `launchctl print` shows `run_logged.py com.exos.mc-email-command -- …` as the arguments.
- The RunAtLoad run logged exit 0 (1.3 s) in `logs/runs/2026-10-02.jsonl`.
- I triggered no replies manually.

## 3. D-7281869: web-only pilot (one job)
Pilot job: **Research Team: Grant & Contract Scanner** (cron `f4ea413e`). Jon's approved plan named this job.

The new OpenClaw agent `research-web` (added with `openclaw config set`, which hot-applies with no restart):
- **Allows only:** group:web, group:memory, session_status, message, tavily_search and tavily_extract.
- **Denies:** runtime, fs, automation, nodes, ui, agents, media, sessions_spawn/send, subagents and conversations_send/turn.
- Claude models can't enforce a per-job toolsAllow, but they do enforce this agent-level policy (gateway hook; checked in the OpenClaw 2026.9.7 docs).

Cron change:
- `openclaw cron edit --agent research-web`, then `--clear-tools`.
- In 2026.9.7, `--clear-tools` writes `toolsAllow: ["*"]` (explicit unrestricted) instead of removing the key. Every agentTurn job now gets that value by default. It is not the claude-cli "cannot enforce" trap, and the guard was updated to match.
- `openclaw cron get` shows agentId research-web. Prompt, model, schedule and delivery are unchanged.
- First run on the new agent: Wed 10/7 12:00.

Issues I hit and fixed while doing this:
- **Heartbeat.** The new agent inherited the 3-hour heartbeat to Jon's DM, so it would have messaged him once active hours began at 08:00.
  - I set `research-web.heartbeat.every = "0m"`.
  - I added `main.heartbeat = {}` and `coding.heartbeat = {}`. Once any agent has its own heartbeat block, only agents with a block run heartbeats, so these empty blocks keep main and coding on the defaults.
  - `openclaw status` shows 3h (main), 3h (coding), disabled (research-web).
- **Memory.** research-web's memory index was empty. I ran `openclaw memory index --agent research-web` and now have 434/434 files, the same as main. A test search returned results.
- **System job.** Creating the agent makes OpenClaw add a weekly `skill-collection-review-research-web` job. It delivers nothing. Its toolsAllow lists write/exec, but the agent policy denies those. main and coding already have the same job from the upgrade. I left it alone.

**Pre-existing outage found and fixed (e3a40b7):**
- Since the OpenClaw 2026.9.7 upgrade (~11:00 CDT on 10/1), `cron_jobs` keeps its fields in job_json/state_json, and `cron_run_logs` was replaced by `cron_run_receipts`.
- As a result, cron_telemetry exited 1 every 15 minutes. cron_hygiene, cron_prompt_guard, agent_eval's cron scoring and the registry drift check were all skipped (84 skips in agent-eval.log), so nothing watched the crons for about 20 hours.
- Fix: an adapter in `cron_telemetry.py` (`job_rows`, `run_rows`, `load_cron_jobs_full`) that reads either schema. The other scripts now use it.
- Also in the same commit:
  - Heartbeat rows are not counted as drift.
  - **New guard:** `cron_hygiene.restricted_tier_findings()` FAILs if a restricted-tier job leaves research-web, or if that agent's tool policy widens or disappears. It WARNs if the heartbeat is re-enabled.
- Selftests: cron_telemetry 22/22, cron_hygiene 37/37, cron_prompt_guard 18/18, agent_eval 18/18, all on both pythons.
- Live results:
  - cron_hygiene: 0 FAIL / 0 WARN.
  - Prompt guard: 5/5 OK.
  - cron-telemetry launchd: exit 1 at 07:24, then exit 0 at 07:39.

**Expect one drift alert from the next hourly agent_eval.** It will list 4 unregistered system-declared AI jobs that the upgrade created:
- skill-collection-review-main
- skill-collection-review-coding
- skill-collection-review-research-web
- Memory Dreaming Promotion

These are real (weekly, with write/exec tool lists) and need registering or disabling. I did neither; that is the guard working as designed.

Registry: the pilot cron's envelope, memory boundary, eval_suite, telemetry and change_log entry are updated. The change_log has approver John Quinn, status "pending Jon approval — D-7281890" and the rollback command.

**Next wave (not touched; each gets its own card after the 10/7 pilot run):**
- Research Team: Competitive Intelligence (60aed194)
- Research Team: Technology & IP Monitor (1cf93736)
- Research Team: Policy & Regulatory Watch (5f3b0529)
- Research Team: Investor & Capital Markets (29aab815)
- Industry Signal Posts (e6d339d7)
- Trending Content Scanner (bcff8330)
- NASA SBIR cryo Phase I appendix watch (bfe8d388)
- SBIR/SpaceWERX topic-fit watch (b942779c)
- SAM.gov API key renewal reminder (2f914ea5)

Pilot rollback: `openclaw cron edit f4ea413e-c591-41ee-8933-7a927ed60c67 --agent main`, then remove the id from `RESTRICTED_TIER` in `scripts/cron_hygiene.py`. Optionally also run `openclaw config unset agents.entries.research-web`.

## 4. D-7281874: GFE deletion (sha-matched only)
- I swept the whole home folder by sha256: every file whose size matched either document was hashed (about 255k files walked).
- Only 3 copies existed, all in `~/.openclaw/media/inbound` (dated 3/25/2026):
  - 2× AAS paper `dbd21394…`
  - 1× Teasley DUA `7aa7c50e…`
- No copies were in ~/exos-asset-backups, ~/dr-selftest-mirror, drafts/, uploads, Desktop, Documents, Downloads, iCloud or /tmp.
- I re-hashed each file immediately before deleting it with `rm`. The sweep afterwards found 0.
- Path, sha256, size and mtime are logged in `compliance/cui-remediation-log.md` (169f5d3), with no content.

**Not done, and why:** Time Machine is not excluded for ~/.openclaw. The external "My Book" Time Machine disk and the hourly local snapshots almost certainly still hold the files. The local snapshots expire on their own within about 24 hours. Time Machine can't delete single files, and this session has no Full Disk Access, so I couldn't inspect or purge them. Erasing whole backups would be irreversible and broad, so that is filed to Jon as **D-7281891**.

**Trajectory / 6DOF / Monte Carlo files were NOT deleted.** Another session logged on 10/2 that Jon released these as not CUI. The inventory:
| path | size | files | newest |
|---|---|---|---|
| ~/.openclaw/workspace/project-lazarus | 2.5 MB | 17 | 2026-10-02 (active) |
| ~/.openclaw/workspace/lazarus_taos | 2.4 MB | 7 | 2026-07-22 |
| ~/.openclaw/workspace/blk3_polar | 0.7 MB | 6 | 2026-07-20 |
| ~/.openclaw/workspace/memory/channels/project-lazarus | <0.1 MB | 1 | 2026-09-13 |
| drafts/BLK3_Part450_MonteCarlo_Dispersion_Framework.md | 8 KB | | 2026-09-02 |
| drafts/Part450_117_MonteCarlo_Dispersion_Framework_2026-09-07.{md,docx} | 8 KB / 41 KB | | 2026-09-07 |
| mission-control/uploads/1788386596547_BLK3_Part450_MonteCarlo_Dispersion_Framework.docx | 40 KB | | 2026-09-02 |
| mission-control/uploads/1788804300774_Part450_117_MonteCarlo_Dispersion_Framework_2026-09-07.docx | 41 KB | | 2026-09-07 |
| ~/.openclaw/tmp/tmp1zzqmzoa/, tmpfxx8piws/ (same two .docx) | 40 / 41 KB | | 9/02, 9/07 |
| ~/exos-asset-backups/2026-09-29…10-02 (both uploads .docx in each of 4 nightly sets) | 8 × ~40 KB | | |
| scripts/mc_montecarlo_envelope.py | 9 KB | | 2026-09-22 |

## Other notes
- **Shared tree.** `compliance/` was entirely untracked, and the log had another session's finished 10/2 entry (Sandia TAOS restriction and the trajectory release). I committed that as its own checkpoint (be07f31) before appending mine.
- **Commit method.** I used only explicit paths with `git commit --only`. Every registry/evals edit was a single fresh load → modify → save, and each diff contained only my entries.
- **Backups (gitignored, not committed).**
  - `logs/audit-workers/cron-backups/f4ea413e-c591-41ee-8933-7a927ed60c67.20261002T072843.json`: the original pilot cron.
  - `logs/audit-workers/cron-backups/openclaw.json.20261002T072927.bak`: openclaw.json before the agent and heartbeat edits.
- **Skipped:** the CLAUDE.md session-startup routine (CronList / RemoteTrigger / status message). This is a scoped worker, and the hard rules forbid Discord messages.
