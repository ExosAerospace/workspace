# r2-confirm-gaps — exo3 round 2 report (2026-09-30, resumed run)

Scope: five "human-confirm gap" crons. The rule is: AI proposes, a human confirms.

## Decisions filed for Jon (all open, none answered by me)
| ID | Card | Recommended |
|---|---|---|
| D-7281852 | EXO3: Decisions Daily Update can only PROPOSE closing a decision | Keep it |
| D-7281853 | EXO3: Weekly Self-Improvement agent now proposes instead of rewriting other agents | Keep it |
| D-7281854 | EXO3: Weekly APAC scan now stages candidates for Toshi instead of adding them | Keep it |
| D-7281855 | EXO3: Old Overnight Resolver crons made propose-only, pasted keys removed (still off) — HIGH | Keep it |
| D-7281856 | EXO3: Delete the old car-part RFQ follow-up job (already deleted — please confirm) | Keep it deleted |

Each card's context includes the rollback command. The dedupeKeys are `exo3-r2:r2-confirm-gaps:<slug>`.

## What changed
- **(a) R-017 Decisions Daily (77ee570f).** The server gate was already committed in e13a807 and has been live since the MC restart at 12:37. The prompt was already propose-only ("PROPOSE closes", token read from `.decisions-token`), and toolsAllow is absent. I made no further edits and filed the decision card.
- **(b) Self-Improvement weekly (ed638bd8).** The prompt was already PROPOSE-ONLY before this run: it writes to reports/self-improvement/, files Decision cards and has no cron edit/retire wording. toolsAllow is absent. No edit was needed.
- **(c) APAC weekly scan (28a46633).** I rewrote the prompt so the scan appends candidates to the new `mission-control/data/apac-candidates-staging.json` (status Proposed). It now treats `apac-opportunities.json` as read-only and no longer restarts MC. The email digest to Toshi stays. Commit **5086ef1**.
- **(d) Both Overnight Resolvers (f2ec7aca, 1f60acb4).** Both prompts are now PROPOSE-ONLY: board changes go into a proposals file plus one consolidated Decision card, and the Supabase connection is GET-only. I removed the pasted MC token and Supabase key; the prompts now read them by name from `.decisions-token` and `~/.openclaw/secrets.json` (`supabase_service_role_key`). I ran `--clear-tools` on both and confirmed toolsAllow is absent. Both are still **DISABLED**.
- **(e) Car-part RFQ one-shot (3299389d).** Exo's main session had already deleted it at about 13:01 on Jon's "Delete the sixth", before I got to it (memory/2026-09-30.md:50). I did not delete it. I updated D-7281856 to ask Jon to confirm, and marked its registry entry as retired (**b38932f**).
- **Guard (deterministic, in code).** `scripts/cron_prompt_guard.py` (a7e78d6, extended in 5086ef1):
  - It now catches pasted Supabase keys.
  - It FAILs if any new `source:'auto-scan'` record shows up in the live APAC file. APAC-010..013 are grandfathered.
  - agent_eval runs it every hour. That wiring reached HEAD through the cron-hygiene worker's 5bdf974 (a shared-tree race), and I added its selftest to agent_eval's selftest in **8ed06aa**.
- **Registry.** agent-registry.json updates for all six entries: permission_envelope, escalation, eval_suite, telemetry, human_confirm_gap, and change_log (approver John Quinn, "pending Jon approval — D-xxxx"). Commits **da35b97** and **b38932f**. config/agent-evals.json already had liveness entries for the enabled crons, so it needed no change.

## Verified
- `cron_prompt_guard.py`: selftest 18/18. A live pass shows all 5 crons OK, and it exits 0.
- `agent_eval.py --selftest`: 18/18, with cron_hygiene 22/22, mail_bridge_guard 11/11 and cron_prompt_guard 18/18.
- `decision_answer_selftest.js`: 7/7. `cron_hygiene`: 0 FAIL.
- No MC restart and no gateway restart. No `cron run`. No emails or Discord messages sent. No data deleted.

## Left undone / notes
- **Credential rotation.** The MC decisions token and the Supabase publishable key sat in plain text in the old resolver prompts. Rotating them is irreversible, so I left it to Jon and flagged it in D-7281855. The cron-hygiene worker owns rotation decisions.
- **Remaining gap.** The APAC scan runs in the main session with full tools, so the prompt alone can't stop a live-file write. The guard detects one within the hour, but it can't prevent it.
- **Backups.** Cron backups are in logs/audit-workers/cron-backups/ (gitignored, not committed).
