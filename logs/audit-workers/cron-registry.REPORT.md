# cron-registry worker report (2026-09-29)

Closes exo3 audit THEME 3 residual: the OpenClaw cron jobs were not in the registry and emitted no telemetry. Jon approved this 2026-09-29 08:28 CDT. No cron was created, edited, disabled, run or removed. The gateway and Mission Control were not restarted. No emails or Discord messages were sent.

## What changed
| Commit | Step |
|---|---|
| ad96733 | **Inventory.** `logs/audit-workers/cron-registry.inventory.json`, built by `cron-registry.build_inventory.py`. It is read-only: `openclaw cron list --all --json` plus the run-history table, with the SQLite DB opened read-only. Prompt text is left out on purpose because several prompts contain credentials. |
| 8f820da | **Registry.** All 57 crons were added to `agent-registry.json` as `kind: openclaw-cron` with the label `cron:<slug of name>`. Each one has the full spec with no blank or TBD fields, plus `enabled`, `cron_id`, `model` and `ai_in_critical_path`. Five entries also carry a `human_confirm_gap` field. `com.exos.cron-telemetry` is registered here too. The diff is 1,367 added lines and 0 removed, formatting unchanged. |
| 76368b8 | **Telemetry script.** `scripts/cron_telemetry.py` emits one fleet_log event per new finished cron run. It keeps a per-job high-water mark in `state/cron-telemetry-state.json`. Selftest passes 17/17. |
| d62312e | **Eval.** `agent_eval.py` change: cron registry drift (matched on cron_id, one deduped alert, same path as launchd). Liveness: WARN when there's no run within 2.5× the schedule interval, FAIL when there are 2 or more consecutive errors. Disabled crons are skipped. `config/agent-evals.json` gains 57 cron entries plus com.exos.cron-telemetry. Additions only. Selftest now passes 15/15: the 7 existing cases plus 8 cron cases. |
| e4ef0b1 | **Launchd job.** `com.exos.cron-telemetry` runs every 15 minutes, wrapped by `run_logged.py`, under `/usr/bin/python3`. Template is in `config/launchd/`. It's installed and bootstrapped. |

## Counts (57 registered: 33 enabled, 24 disabled)
The "33 crons" in the audit is the enabled count. The 24 disabled ones are registered too, marked `enabled:false`.
- **By layer (all / enabled):** SENSE 16/10 · INTERPRET 11/7 · ORCHESTRATE 18/10 · DECIDE 4/2 · LEARN 3/2 · GOVERN 5/2
- **By risk (all / enabled):** HIGH 15/10 · MED 15/9 · LOW 27/14
  - HIGH means it sends email, acts outside Exos, or changes a system of record.
  - MED means it writes internal files.
  - LOW means it only reads and reports.
- **Payload types:** 50 agentTurn, 6 systemEvent, 1 command. An AI model sits in the critical path of 56 of the 57.
- **Owners:** Lizi Quinn owns 3 (Trending Content, Industry Signal Posts, the disabled LQuinn CRM report). John Quinn owns the rest.

## Verified
- `cron_telemetry.py --selftest` passes 17/17 under both /usr/bin/python3 (3.9) and mise python 3.12. `agent_eval.py --selftest` passes 15/15. `exo3_gate.py --selftest` passes. Everything compiles with py_compile, and both plists pass `plutil -lint`.
- **First real telemetry pass,** started under launchd:
  - It emitted **16 cron run events** covering the last 24h, plus 1 pass event. `logs/fleet-events.jsonl` went from 19,491 to 19,508 lines.
  - The run exited 0, and `logs/runs/` recorded it.
  - A second pass emitted **0**, so dedupe works.
  - The high-water mark covers 107 job ids in the run history.
- **agent_eval dry run:** 176 agents scored, including the 33 enabled crons. All 33 crons are OK and cron registry drift is 0. The cadences check out on real schedules: daily = 24h, weekday = 72h, bi-weekly = 336h, month-end = 28d.
  - There are 2 FAILs, both from before this work: `series-a-worklist` is intentionally unloaded, and `missioncontrol` shows LastExitStatus=15 from the cutover restart.
- Dry-run mode still writes eval events to fleet_log (that's how agent_eval already worked). My 3 dry runs added a few extra `agent_eval` lines.

## Human-confirm gaps: REPORT ONLY (nothing was modified; Jon decides)
1. **R-017: `Decisions Matrix Daily Update (R-017)`**. ENABLED, runs daily at 06:05, Sonnet 5.
   - What it does: an LLM closes open MC decisions on its own judgement.
   - Evidence, STEP 3b: *"If a message FROM John … shows the action was done after that date … close the decision (STEP 4) with answer 'Closed (already done): …'"*
   - Evidence, STEP 4: *"For any open decision whose related task is clearly Done/closed … PATCH it closed … '{"answer":"Auto-closed: underlying item resolved"}'"*
   - The server only checks that the answer starts with "Closed" or "Auto-closed". Nobody confirms.
   - **Proposed fix:** token-originated closes land as `pending_close`, and a human confirms or rejects them on MC. This mirrors the Capital Bridge `pending_confirmation` gate. Alternatively, the job lists "proposed closes" in its digest and Jon replies to confirm, like the backlog-grind cron already does. Add a decision-trace per proposed close.
2. **`Agent Self-Improvement Implementer (Weekly)`**. ENABLED, Sundays 06:00.
   - What it does: an LLM rewrites other agents' prompts and schedules and can retire a job.
   - Evidence: *"IMPLEMENT NOW: prompt edits, search-query tweaks, schedule changes, retiring a clear duplicate"* and *"Cron prompt changes: use cron tool (action=get then action=update)"*.
   - This conflicts with the exo3 rule that a behavior change to a registered agent must ship with an eval and a registry update.
   - **Proposed fix:** make it propose-only. It writes proposed diffs plus one Decisions card, and a human applies them.
3. **`APAC deal-flow weekly scan`**. ENABLED, Sundays 18:00, main-session system event.
   - What it does: an LLM appends records to MC data and restarts production Mission Control.
   - Evidence: *"AUTO-APPEND each new one to that JSON … then restart MC (launchctl kickstart -k gui/$(id -u)/com.exos.missioncontrol)"*.
   - The entries are Watch/$0, but the restart happens every time.
   - **Proposed fix:** write candidates to a staging list for Toshi to vet, and drop the MC restart from the prompt.
4. **`Overnight Resolver`**. DISABLED.
   - Evidence: *"EXECUTE IT YOURSELF … updating a task's status/owner/priority/tags in Supabase … deduping/merging duplicates"*.
   - **Proposed fix:** keep it disabled. If it's re-enabled, switch to a proposed batch that Jon confirms.
   - Memory says the resolver moved to launchd. That version is outside this task, and the same decision boundary probably applies to it. Worth checking.
5. **`Overnight Resolver — Opus Escalation`**. DISABLED.
   - Evidence: *"EXECUTE it directly in Mission Control"* and *"(b) execute or stage that action immediately"*.
   - **Proposed fix:** same as #4.
- **Secondary:** `VFW Tundra AMP PowerStep — RFQ follow-up` is a disabled one-shot from the past. Its prompt says *"resubmit the car-part.com RFQ"*, which is an external send with no confirm. Recommend removing it.
- **Watch item, not a gap:** `Exos Capital Bridge Agent ($1M)` updates stages, statuses and dollars in the markdown pursuit tracker. That tracker is advisory. The real money ledger already has its human sign-off gate.

## Other findings for Jon
- **The SAM.gov key renewal reminder failed and never reached Jon.** On 9/11, the model `anthropic/claude-haiku-4-5-20251001` was rejected by the model allowlist. The key was last entered 2026-06-18 with an 89-day life, so it has **probably been expired since about 9/15**. The cron's next run is 12/05. Please check the SAM key. The SAM watchers may be failing quietly.
- **Credentials are embedded in 6 cron prompts** (names only, values not copied anywhere):
  - Monthly Investor Report (ENABLED): mail-bridge SMTP password.
  - Self-Improvement Implementer (ENABLED): hard-coded decisions token. Memory says that token rotates, so its Decisions posts may already be failing.
  - Overnight Resolver and Opus Escalation (disabled): the same token plus a Supabase publishable key.
  - Solar Report (disabled): Home Assistant token.
  - Daily Email Opportunity Scanner (disabled): mail password.
  - Proposed fix: read these from `secrets.json` the way R-017 already does. Rotating them is Jon's call.
- **Tool access is broader than the prompts suggest.** 35 crons have no `toolsAllow`, so they run with the main agent's `tools.profile=full`, which includes shell. Only the prompt text holds them back. The structural fix is a narrower `toolsAllow` per cron.
- **Transient crons escape the registry.** 28 self-deleting one-shot crons ran in the last 30 days, for example last night's Studio cutover reminder. They exist for only hours, so the hourly drift check rarely sees them. Telemetry does capture their runs, tagged `registered:false`. Proposed fix: a class-level registry entry for agent-created reminders, plus an agent_eval WARN on `registered:false` run events.
- **Three Research Team prompts contradict themselves:** Tech & IP, Policy, and Competitive. Their header says "no file writes", but their footer requires a run-log line in `opportunities-tracker.md`.

## Left undone / notes
- I didn't run the CLAUDE.md startup auto-restore (CronList, RemoteTrigger check, status message). This worker's rules forbid Discord messages and cron changes.
- I didn't change the registry's header counters (`total`, `standing`). They were already stale at 150 vs 154 entries. A `cron_backfill` summary block was added instead.
- `state/cron-telemetry-state.json` is runtime state and stays untracked, like the other state files.
- Drift alerts for crons go through the existing `agent_eval` path to the system channel. As of now, zero crons are unregistered and zero are FAIL, so the next hourly run should send nothing new for crons.
