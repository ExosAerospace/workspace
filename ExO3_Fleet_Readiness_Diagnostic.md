# ExO 3.0 Readiness Diagnostic — Exos Agent Fleet

**Prepared for:** John Quinn, Cofounder & CEO · **Date:** 2026-07-27 · **Method:** ExO 3.0 (OS Outline v25) Appendix A diagnostics — DRIVE + SHAPE scoring, Four Pillars of GOVERN/ASSURE, Miura-Ko L0–L5 ladder. **Deployment mode:** Direct Mode (≤50 — the company IS the edge).

## Verdict

**Miura-Ko level: L3 (Organizational Infrastructure), low end.** The fleet has crossed from "personal productivity" into real infrastructure — a scheduler, a central correlation-ID log, an agent registry, a failure watchdog, a human review queue, and a working Quiet-Drift eval. Most firms score 1s on the Four Pillars; Exos scores 3s and 4s. That is genuinely ahead. **It is not yet L4 (compounding)** because the governance backstop covers only 5 of ~40 live agents, so the fleet cannot yet compound — and the gaps are exactly where it is visibly failing.

**Composite: DRIVE 14/25 · SHAPE 13/25 = 27/50 — Foundational, crossing toward Ready on the governance axis.**

## Scores

**DRIVE (the intelligence engine)**
- **Decision Architecture — 3/5.** A decision-boundary map (two-way-door = agent executes; one-way-door = escalate to Jon) is drafted in the governance registry as the explicit fix for founder congestion. But it is flagged "pending Jon's confirmation," so today ~85% of tasks still pool on you. **Congestion is the fingerprint.**
- **Recursive Learning — 3/5.** An Agent Self-Improvement + Agent Meta-Evaluator loop already runs weekly. Rare and correct; not yet propagating versioned workflow gains.
- **Intelligence Stack — 3/5.** MVIS is real and running (event log, registry, watchdog). Capped at the lowest Four Pillar (3).
- **Value Moat — 2/5.** Decision traces + proprietary CRM/pipeline data are accumulating but not yet a moat.
- **Elastic Agency — 3/5.** 28 OpenClaw crons + 45 launchd jobs under one documented Permission Envelope.

**SHAPE (the organizational form)**
- **Safe Autonomy — 4/5.** Strongest characteristic. The Fiduciary Wedge is real: every external send chains to a named human owner (Jon for outreach/gov; David Mitchell + counsel for securities). Watchdog + cron-disable = working kill switch.
- **Human Architecture — 2/5.** Founder-as-bottleneck: the fleet routes almost everything to one person. The decision-boundary map is the designed relief valve — unconfirmed.
- **Adaptive Architecture — 3/5.** Modular, model-swappable agents.
- **Purpose Control — 2/5.** The MTP exists as prose ("De-risk the impossible…") but is **not** encoded as the machine-readable three-layer protocol agents actually read. Consequence below.
- **Ecosystem Trust — 2/5.** Early.

## Four Pillars of GOVERN/ASSURE (the control plane)
| Pillar | Evidence | Score |
|---|---|---|
| Trusted Evals | `run_evals.py` computes per-class human-override rate vs. registry ceiling, RED/AMBER/GREEN, exit-2 to gate | 3 |
| Searchable Logs (correlation IDs) | `events.jsonl` — 2,275 correlation-ID events, live today | 3 |
| Granular Rollback | `rollback.js` + per-class rollback path in registry | 3 |
| Human Review Queue | Decisions board — 464 items, the queue evals read from | 4 |

**No new agent class should deploy until every pillar ≥ 3 for that class. The scaffolding clears that bar; coverage does not.**

## The live wound — Exhibit A of Quiet Drift
The **BLK3 Payload Sales Engine** (local model `qwen3.6:35b`) has posted failure narration to #blk3-payload for three straight days — "browser can't read local files," "file_fetch needs a node," and, on 2026-07-27, it refused its own campaign doc as if it were a prompt injection. The cron exited **"ok"** each time. This is textbook **Quiet Drift**: no crash, green status, degradation discovered in the channel instead of on a dashboard. Root cause: (1) the engine is **not in the governance registry**, so `run_evals.py` never scored it; (2) the local model is under-powered for the file-read + tool-orchestration task and its Constraint layer is mis-tuned (the **Agentic Fidelity Paradox** — over-adherence to a "reject injections" rule, misfiring on legitimate content). The fix loop already exists; it just isn't wired to this agent.

## Recommended next actions (ranked)
1. **Wire the failing engine into governance + take model out of the critical path.** Register it (Autonomy Tier, envelope, eval ceiling, rollback), and make the enrichment deterministic (`payload_pipeline_to_opps.py`) with the model used only for drafting. Stops the channel bleed and proves the loop. *I can do this now.*
2. **Confirm the decision-boundary defaults.** One review of the registry's two-way-door / one-way-door map unlocks the founder-congestion relief valve — the single highest-leverage SHAPE move.
3. **Encode the MTP as the three-layer machine-readable protocol** (Constraint / Decision / Identity). This is what prevents the over-refusal failure from recurring across the fleet.
4. **Extend Four-Pillar coverage from 5 → all ~40 agents.** Instrument each with govlog + an eval ceiling. This is what moves Exos from L3 to L4 (compounding).
5. **Build the Mission Control fleet panel** — one screen: every agent, last run, status, override rate, $ in pipeline, awaiting-Jon items.

**Bottom line:** Exos is further along the AI-native path than almost any firm its size — the architecture is bought and partly deployed. The gap is coverage and confirmation, not construction. Two decisions from you (items 1–2) close the visible failures this week.
