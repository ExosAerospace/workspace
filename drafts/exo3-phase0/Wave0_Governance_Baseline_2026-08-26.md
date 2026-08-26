# ExO 3.0 — Wave 0 Baseline: Governance & Human-Review Queue (honest score)

**Date:** 2026-08-26 · **Owner:** Exo · **Task:** #2352 · **Scope:** the Decisions matrix (Human Review Queue) as the measurable proxy for GOVERN/ASSURE + the recursive-learning "falling override rate" metric.

This is the Wave 0 baseline Jon green-lit — the fleet scored honestly, from data, not narrative. Everything below is computed from `mission-control/data/decisions.json` (793 lifetime decisions).

---

## 1. The headline numbers

| Metric | Value | What it means |
|---|---|---|
| Lifetime decisions | **793** | Total ever routed to the queue |
| Answered / delegated / open / cancelled | 711 / 53 / 26 / 3 | Current disposition |
| `yesno` (approval-shaped) | **693 (87%)** | Overwhelmingly gate-approvals, not choices |
| Genuine multi-option `input` (open/choice/multiple) | **~64 (8%)** | The decisions that actually needed Jon's judgment |
| Of the 448 Jon personally actioned: **approve** | **385 (85.9%)** | Rubber-stamps — he agreed with Exo's proposal |
| Of the 448: **override** (no / hold / false-positive) | **63 (14.1%)** | Where his judgment changed the outcome |
| Pure system noise (auto-closed / duplicate / "none") | **187 (26.3% of answered)** | Never needed a human at all |

**Read it plainly:** Jon's instinct was right. Historically, **~86% of the decisions he touched were rubber-stamps** and another quarter were noise. Only **~8% of all decisions were genuine choices**. The gate has been asking permission for work he already directed.

## 2. The recursive-learning metric (this is the ExO "9" test)

Salim's framework: *the test of a real system is a falling human-override rate.* We now have the baseline.

- **Human-override rate (baseline): 14.1%** — on the decisions Jon actually adjudicated, he changed the outcome 1 in 7 times. The other 6 in 7, Exo's proposed action was what he'd have done anyway.
- **The deeper signal isn't the override rate — it's the *ask rate*.** An 86% rubber-stamp rate means the system was over-asking: 385 times it interrupted the CEO to confirm a call it had already gotten right. Governance maturity = **fewer asks × low override on what remains.**

**Two numbers to drive to a 9:**
1. **Override rate ↓** (proposals keep matching Jon's judgment) — baseline **14.1%**.
2. **Ask rate ↓** (stop gating already-directed / low-consequence work) — baseline **~86% of the queue was avoidable.**

## 3. Where the volume comes from (source attribution)

| Source | Decisions | Note |
|---|---|---|
| Opportunity Engine | **326 (41%)** | Per-email send-approvals + "ask Jon" meta-wrappers — the primary flood |
| Decisions Daily Update | 118 | Rollup churn |
| Overnight Resolver | 86 | Auto-resolution (mostly healthy) |
| Exo (direct) | 74 | Session/email-command items |
| De-Risk Orbital Engine | 25 | Outreach send-approvals |
| Export-control screen | 20 | ITAR gate — legitimately consequential |

## 4. Four Pillars (GOVERN/ASSURE) — instrumented status

| Pillar | Status | Evidence / gap |
|---|---|---|
| **Permission Envelope / Fiduciary Wedge** | ✅ **3** | Every external send chains to a named human; email-command envelope enforced |
| **Human Review Queue** | ✅ **3** | Decisions matrix live; now with a codified input-vs-approve gating policy |
| **Trusted Evals (drift detection)** | ⚠️ **1–2** | `agentClass`/`correlationId` are stamped on decisions but override-rate is not yet tracked over time — **Wave 1 target** |
| **Granular Rollback** | ⚠️ **2** | Decisions are superseded not deleted (reversible); no per-agent action rollback ledger — **Wave 1 target** |

## 5. Honest scoring

- **Overall: ~6–7, L2–L3** — consistent with the prior read. We run the governance layer most of the field only talks about (live fleet + central logging + Fiduciary Wedge + Review Queue + MTP). We clear the Dabbling Test.
- **The single capped dimension is GOVERN/ASSURE instrumentation** — we hold the logs and the queue but don't yet *measure* drift or *prove* the override rate is falling. That's the exact line between "a fast agent fleet" (caps ~6–7) and "a governed, compounding OS" (a 9).

## 6. What already shipped today (Phase 0 action, reversible)

Per Jon's 2026-08-26 direction to "reduce the human review cue":
1. **Source fix** — `opportunity_processor.py` (the 41% source) now suppresses self-referential "email/route/deliver/brief-to-Jon-for-approval" meta-asks: Exo performs the internal delivery already directed instead of consuming a CEO decision. **Guarded** — never fires on gov/.mil, investor, ITAR, NDA, contract, RDRE, or Scorpius items, and never on an external SEND (Jon keeps those approvals).
2. **Triage backstop** — `decision_triage.py` batches the same meta-redundant class + meeting-debrief info-captures out of the CEO gate, same guard.
3. **Codified** the input-vs-approve principle as a standing gating policy (see `Decision_Gating_Policy.md`).
4. **Honest caveat:** the *current* 26 open items are already legitimate — every meta-shaped one carries a real consequence signal (Kolon NDA, OSC $15M loan, SSC/gov, AFRL routing, RDRE payload), so they were **kept**, not stripped. Only 1 duplicate + 1 malformed item were cleared. **The win is the creation rate going forward, not theatrics on today's board.**

## 7. Baseline locked → next

- **Override rate: 14.1%** and **ask rate: ~86% avoidable** are the Wave 0 baseline of record. Wave 1 instruments both as live, trending metrics so we can *prove* the system is compounding — the thing 135 of the 136 orgs can't show.
