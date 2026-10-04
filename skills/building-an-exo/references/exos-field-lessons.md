# Exos ExO 3.0 Field Lessons

Real implementation failures and anti-patterns from Exos Aerospace's ExO 3.0 build (2026). Each lesson maps to a framework concept and proposes a structural countermeasure. Source: `mission-control/data/exo3-field-failures.json`. Maintained weekly by `scripts/exo3_field_report.py`.

---

## L-001 · Registry + liveness eval ≠ Trusted Eval

**What happened:** 155 of 238 registered agents (65%) have only liveness/exit-code evals. An agent that exits 0 but produces wrong output — duplicate Discord posts, missed deliveries, stale responses — scores PASS on every liveness check. The decisions-discord-feed triple-post (F-003) and the capstone answerer false self-post (F-007) are direct evidence.

**Anti-pattern:** "We registered the agent and gave it a cadence check — that's the eval."

**Countermeasure:** Any agent with side effects (sends, external writes, POSTs, UI-visible output) must have an output eval:
- What is the expected observable outcome per run?
- What signal confirms it landed (DB row, delivered event, ack from recipient system)?
- Define a dup_sends, delivery_exhausted, or outcome_count check in `config/agent-evals.json`.

**Framework recommendation:** Add `output_eval` as a required field in `AGENT_SPEC_SCHEMA` for `risk_tier >= MED` or any agent with a non-null permission_envelope external send. Gate registration blocks if absent.

---

## L-002 · Commit gate ≠ runtime drift gate — two separate controls needed

**What happened:** 9 live agents ran for an indeterminate period outside the registry. The pre-commit gate only sees staged git additions. Agents loaded via `launchctl load` outside a git commit are invisible to it. (F-001)

**Anti-pattern:** "The commit gate ensures all agents are registered."

**Countermeasure:** A second control at the runtime layer: hourly comparison of `~/Library/LaunchAgents/com.exos.*` + `launchctl list` against `agent-registry.json`. Any unregistered label → deduped alert. Implemented as `_registry_drift` check in `scripts/agent_eval.py`.

**Framework recommendation:** The Fiduciary Wedge requires two controls: a commit-time gate (PREVENT) and a runtime-drift check (DETECT). Documenting only one as "the enforcement" is a single point of failure.

---

## L-003 · Shared-library blast radius — one regression, fleet-wide impact

**What happened:** A change to `deliver.py` (used by 50+ agents) propagated a duplicate-send failure across the fleet simultaneously. No dependency map existed; no eval monitored the shared library's fleet-wide output; the exo3 gate did not flag deliver.py changes as DECIDE/GOVERN-level. (F-003, F-008)

**Anti-pattern:** "Each agent is independently evaluated — shared libraries are implementation details."

**Countermeasure:**
1. Add high-blast-radius shared libraries (`deliver.py`, `durable_send_shim.py`, `run_logged.py`) to `DECIDE_GOVERN_FILES` in `exo3_gate.py` so any change triggers a Four-Pillars WARN.
2. Give the delivery infrastructure its own output eval (fleet-level dup_send rate monitored by `agent_eval.py`).
3. Before any shared-library change, enumerate all downstream agents and their eval coverage.

**Framework recommendation:** AGENT_SPEC_SCHEMA should include a `shared_deps` field listing shared libraries an agent depends on. The eval runner can then produce a blast-radius impact map before a library change is committed.

---

## L-004 · Agentic Fidelity Paradox — self-reported status ≠ external outcome

**What happened:** The UTD capstone answerer (F-007) returned ANSWERED status from its model step, but had no posting tools in its execution context and never actually delivered to Discord. The DB row showed ANSWERED; students saw nothing. The agent's self-report was the only evidence of completion — and it was wrong.

**Anti-pattern:** "The agent reports success — mark it done."

**Countermeasure:** For any agent whose output is externally visible (Discord post, email sent, DB row created), the completion signal must come from the external system, not the agent's own return value:
- Verify the DB row exists AND has the expected state AFTER the agent writes it.
- For Discord posts: check deliver.py returned `outcome: sent` (not just `spooled`), or poll the channel's message history.
- Model self-assessment is evidence; external system confirmation is the ground truth.

**Framework recommendation:** Add a `completion_signal` field to AGENT_SPEC_SCHEMA: the external signal that constitutes verified completion (e.g., `"delivered event in fleet-events.jsonl"`, `"DB row state = Done"`, `"ack from MC API"`). Evals check this signal, not the agent's return value.

---

## L-005 · Quiet Drift via runtime-injection side effects — the toolsAllow trap

**What happened:** The OpenClaw cron tool auto-injects `toolsAllow` from the calling session when a cron is created or edited from a `claude-cli` session. The `claude-cli` backend cannot enforce runtime toolsAllow and errors in ~170ms. The cron appears loaded, launchctl shows exit 0 (the fast-fail is clean), but produces zero output. Affected 7+ crons across the fleet; recurred after a model-bump re-injected. (F-006)

**Anti-pattern:** "The cron is loaded and the last exit status is 0 — it's healthy."

**Countermeasure:**
1. After ANY cron create/edit from a claude-cli session: immediately run `openclaw cron edit <id> --clear-tools`.
2. Staleness eval: a cron that completes in <500ms and writes no output is a Quiet Drift signal, not a health signal. Add a min-runtime-or-output check to the eval.
3. After any model-bump on `anthropic/*` crons: sweep all affected crons with `--clear-tools`.

**Framework recommendation:** Runtime-injection side effects (where a tooling operation modifies agent configuration as a by-product) are a structural gap in the Granular Rollback pillar. Tooling should expose these mutations visibly and require explicit confirmation.

---

## L-006 · ETA promises break the Trust Loop without a feedback measurement

**What happened:** Exo's promised ETAs ran 7-11x longer than actual, across all session types, for months. There was no measurement, no logging, no weekly correction. The Trust Loop (one of the Three Compounding Loops) was structurally open: agents claim capability they cannot verify in their own output. (F-004)

**Anti-pattern:** "The agent estimates how long it takes — that's good enough."

**Countermeasure:** Log every promised-vs-actual pair (`scripts/eta_log.py`). Weekly RSI §14 reviews drift and proposes recalibrated defaults. Calibrated defaults are published in `AGENTS.md` and enforced as standing rules. The Trust Loop closes when self-estimates are grounded in measured performance.

**Framework recommendation:** AGENT_SPEC_SCHEMA should include `latency_sla_s` (expected max turnaround). The LEARN layer tracks actual vs. SLA weekly and flags drift. This converts agent self-estimates from model intuition into calibrated operational data.

---

## L-007 · Fiduciary Wedge requires a re-verification gate, not just a routing rule

**What happened:** Capture agents escalated stale conditions to Jon — alerts about issues that had already been resolved or changed. The Fiduciary Wedge rule existed (only route to Jon what requires his decision), but no operational check verified that the condition was still current before filing a Decision card. (F-005)

**Anti-pattern:** "The agent detected an issue and routed it — the wedge is working."

**Countermeasure:** Any escalation to Jon must include a re-verification step: re-read the live state of the triggering condition at the moment of escalation (not from cache or prior-session memory). If the condition is resolved, suppress the escalation and log it as a false positive.

**Framework recommendation:** The Fiduciary Wedge should be operationalized as a two-phase check: (1) detect condition, (2) re-verify condition is still active immediately before routing. Phase 2 is the gate. Single-phase implementations are vulnerable to stale-carry-forward.

---

*Source: `mission-control/data/exo3-field-failures.json` · Updated weekly by `scripts/exo3_field_report.py`*
