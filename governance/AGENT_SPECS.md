# Exos Agent Permission Envelopes (AGENT_SPEC_SCHEMA)
Session 2c · 2026-06-24 · Human Owner (all classes): **Jon** · Machine source: `governance/registry.json`

Eight-property specs for the 8 autonomous agent classes. The headline is the
**Decision Boundary** — what each class may now *execute* without routing to Jon
vs. what it must *escalate*. This is the founder-congestion fix from the readiness
baseline, and it is only safe **because** the governance gate (logs + rollback +
evals) was closed first: every autonomous action is now correlation-logged and
rollback-able, so delegating reversible work no longer means flying blind.

## Global constraints (apply to every class — MTP Constraint Layer)
No external sends without approval · no capability/traction overstatement · no
ITAR/CUI outside the boundary · no financial/legal commitment without CEO sign-off ·
no hard-delete (soft-delete + approval). These are hard floors; the boundaries below
only ever loosen *reversible, in-scope* actions.

## The Decision Boundary — where the congestion goes away

The three "Recommend" classes are where volume currently piles onto you. Today they
push nearly everything to the Decisions inbox. With the backstop in place they can
clear the reversible ~80% themselves and surface only genuine one-way doors:

- **resolver** — EXECUTE: status/owner/priority/tag updates on reversible MC items, reschedule/snooze, dedupe/merge, draft-and-stage follow-ups. ESCALATE: external sends, new commitments, capability claims, closing/abandoning a high-priority deal.
- **opportunity-engine** — EXECUTE: file/tag/score, auto-archive clear non-fits, dedupe pipeline. ESCALATE: pursue/no-pursue above the relevance floor, anything needing outreach or a bid.
- **research** — EXECUTE: ingest/tag/dedupe, auto-discard low-relevance, cluster. ESCALATE: items flagged actionable (a grant to pursue, an investor to contact).
- **sam-watch** — EXECUTE: detect/log/alert amendments. ESCALATE: amendments that change eligibility, scope, or deadline.
- **email-router** — EXECUTE: classify/route inbound, extract attachments. ESCALATE: unclassifiable or sensitive-pattern mail (legal/investor/ITAR).
- **crm** — EXECUTE: internal reminders + pipeline reports, flag stale deals. ESCALATE: any external contact.
- **dashboard-data / erp-dal** — EXECUTE: regenerate derived artifacts / audited in-schema upserts. ESCALATE: writes to source of truth, schema/DDL changes, bulk deletes.
- **payload-sales** (added 2026-07-27) — EXECUTE: enrich prospects, bridge them into priced MC opportunities, stage drafts, post the deterministic daily summary to #blk3-payload. ESCALATE: any external send/outreach, any price quoted externally, capability claims, closing/abandoning a high-value prospect. *Substrate note:* the critical path (pipeline→opportunities→summary→delivery) runs as a deterministic launchd script (`scripts/payload_sales_engine.py`) with govlog correlation IDs; the weak local model is out of the critical path (best-effort drafting only). Replaced the old single-agentTurn engine that had no local file-read tool and posted Quiet-Drift failures to the channel for three days.

**Projected effect:** the inbox stops carrying reversible bookkeeping (status flips,
dedupes, low-relevance triage) and carries only real decisions — pursue/no-pursue,
external sends, commitments. The eval runner watches each loosened class; if a
class's override rate climbs past its ceiling, that's the Quiet-Drift signal to tighten
its boundary back. Self-correcting.

## Eight properties (per class)
All eight are populated in machine-readable form in `governance/registry.json`:
1. **Purpose** · 2. **Autonomy Tier** · 3. **Permission Envelope** (`write_scope` + global constraints + `decision_boundary`) · 4. **Memory Boundary** · 5. **Escalation Rules** (`decision_boundary.escalate` → `escalation_owner`) · 6. **Eval Suite** (`override_rate_ceiling` + `min_runs_for_eval`, run by `run_evals.py`) · 7. **Telemetry/Audit** (govlog correlation_id → `events.jsonl` + `audit_log`) · 8. **Reusability Scope** (registry class id = Capability Registry tag).

## Scope-isolation status (honest)
- ✅ Correlation-ID telemetry on every class · ✅ Read/write scopes declared · ✅ Rollback path defined per class · ✅ Escalation owner named (Jon).
- ⚠️ Pending: scoped *workload* credentials per agent (several still run under shared local creds) and a tested kill-switch per class. Recommend as the next hardening pass before loosening any boundary to `fully_autonomous`.

## What needs your sign-off to go live
The boundaries above are **proposed defaults**. Turning a delegation on = letting that
class act without the inbox round-trip. Lowest-risk first to switch on: **research**
and **opportunity-engine** auto-triage (ingest/tag/dedupe/archive) — pure reversible
bookkeeping, fully logged, trivially rolled back. Highest-value: **resolver**
reversible MC updates. Say which to enable and I wire the execute-path + the escalate
filter into those scripts.
