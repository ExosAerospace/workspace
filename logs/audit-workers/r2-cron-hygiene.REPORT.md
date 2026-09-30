# r2-cron-hygiene — exo3 round 2 report (2026-09-30, resumed run)

Jon's directive: 2026-09-29 22:38 CDT, #exomac-system. The first run was killed at 22:47 on 9/29 after committing the guards (13c8022, c1afc77) and editing some crons. It filed no decisions. This run finished the scope, filed every decision, and wrote this report. Nothing was sent externally, no cron was run or removed, and neither MC nor the gateway was restarted.

## cron_hygiene.py: before vs after
- Audit baseline (9/29, first run): **6 FAIL / 2 WARN**.
- At the start of this run: **2 FAIL / 1 WARN**. The FAILs were the 2 overnight-resolver crons, which belong to r2-confirm-gaps and which they have since fixed. The WARN was the SAM reminder carrying toolsAllow.
- Once the new conflicting-instructions guard went in (be28aec): 0 FAIL / 6 WARN (the 3 Research Team crons × 2 contradictions).
- **After: 0 FAIL / 0 WARN.** Selftests: agent_eval 18/18, cron_hygiene 28/28, cron_telemetry 17/17, mail_bridge_guard 11/11, cron_prompt_guard 18/18. R-NONEWS coverage: none missing. Registry drift: 0 launchd, 0 cron (it had been flagging diu-hycat every hour since 09:05).

## What changed, by scope item
**(a) Secrets out of prompts.** The first run already did this on 9/29 22:46 and 9/30. I verified it against the backups:
- Solar Report: the HA token now comes from `~/.config/exos/home-assistant.token`.
- Daily Email Scanner: the bridge password now comes from `bridge-studio.pw`, and mail goes through `send_email.py`.
- Monthly Investor Report: now uses `send_email.py`.

No literal credential is left in any cron. I checked by name which exposed values are still live, without printing any values:
- The HA token is **still live** and should be rotated.
- The pasted bridge password is not the current Studio one; it is most likely the old Mini's.
- The embedded decisions token is stale.
- The Supabase key is the publishable (public) one.

I did not rotate anything; that is for Jon. Registry specs are updated.

**(b) SAM.gov reminder cron 2f914ea5.**
- Model: `anthropic/claude-haiku-4-5` (on the allowlist).
- Ran `--clear-tools`; `openclaw cron get` confirms toolsAllow is gone.
- The reminder no longer asks Jon to "send me the new key" in Discord.

**Finding:** the key is **not** expired. A live read-only SAM search returned HTTP 200 today, and the watchers swept normally on 9/28. So the HIGH decision asks Jon to check the real expiry date rather than claiming the key has lapsed. The next reminder is scheduled for 12/5.

**(c) Research Team: Competitive Intelligence, Technology & IP, Policy & Regulatory.**
- Removed the "RUN LOG (REQUIRED) append to opportunities-tracker.md" sections. They contradicted the no-filesystem header, and isolated runs can't write files; cron_telemetry already logs each run.
- Removed the empty-run posts (the 2-line Pulse/Posture, "✅ RLV still 3", "no roster change"), which contradicted R-NONEWS. Empty runs now reply exactly NO_REPLY.
- Ran `--clear-tools` (none had been set).
- New deterministic guard: `cron_hygiene.conflict_findings()` WARNs hourly via agent_eval.

**(d) Transient class + HyCAT.**
- agent_eval `cron_drift` now exempts a cron only if it is schedule `at` + delete_after_run + due within 31 days, **and** the registry entry `cron-class:transient-agent-reminder` exists with a complete spec. If that entry is missing or incomplete, the check fails closed (every one-shot counts as drift again).
- Registered `com.exos.diu-hycat-cso-watch`: owner John Quinn, envelope, eval, and a liveness entry in agent-evals (cadence 50400s).

**(e) Full-tool-access plan.** Decision only; nothing changed. Live count: 24 enabled + 6 disabled full-tool AI jobs. Proposal: 14 keep full access; 10 web-only watchers move to a restricted agent profile, piloted on one job first.

## Commits (all mine, not pushed)
- 13c8022, c1afc77: guards (first run)
- b7d2dae: transient class (code)
- 5a51294 + 5bdf974: merge fixes (see incident below)
- 938faee: agent-evals HyCAT
- be28aec: conflicting-instructions guard
- 983a969: registry specs for the 7 crons changed this round
- 12ed2ab: registry wording fix

My two registry entries (transient class + HyCAT) were swept into r2-confirm-gaps' commit **da35b97**. That happened because we edited the same file at the same time; the content is correct.

## Decisions filed (all open, assigned to jquinn@exosaero.com)
- **D-7281857** (med): keep the transient reminder-cron class + HyCAT registration?
- **D-7281858** (HIGH): the SAM.gov key still works today; check its real expiry at sam.gov.
- **D-7281859** (med): keep the SAM reminder cron fixes?
- **D-7281866** (med): keep the cleaned Research Team prompts?
- **D-7281867** (HIGH): keep credentials out of prompts (read by name)?
- **D-7281868** (HIGH, Jon-only): rotate the HA token; confirm the old Mini's Proton Bridge is signed out.
- **D-7281869** (HIGH, plan only): which of the 24 full-tool AI jobs keep full access.

## Incident: shared-tree commit race (fixed)
While building b7d2dae from HEAD, r2-launchd-residuals committed a93b78b, and b7d2dae dropped their `check_mail_bridge`. My fix (5a51294) then dropped r2-confirm-gaps' `check_cron_prompt_guard`, which ad41142 had just carried in. 5bdf974 restored the full union. HEAD now contains all three workers' functions, and the selftests pass.

Lessons:
- Don't build commits off a HEAD snapshot on this tree. Use `git commit --only <paths>` from the working tree.
- Temp-index commits leave stale blobs in the shared index. I reset my paths afterwards.

## Left undone / for follow-up
- Rotation (D-7281868) and the tool-tier rollout (D-7281869) wait on Jon.
- The SAM reminder schedule should be re-anchored once Jon reports the real expiry date (D-7281858).
- Watch tonight's 18:00 Monthly Investor Report. It is the first month-end run since mail moved to `send_email.py`. It ran OK on 9/28 and 9/29.
- Cron backups (these contain secrets and are gitignored, not committed): `logs/audit-workers/cron-backups/*.20260930T1306*.json` and `*.20260930T1308*.json`.
- CLAUDE.md startup restore (CronList / RemoteTrigger / status message) was skipped: this is a scoped worker session, and the hard rules forbid Discord messages.
