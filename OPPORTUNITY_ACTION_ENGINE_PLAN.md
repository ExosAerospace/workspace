# Opportunity Action Engine — Plan
**Goal:** Assign an agent to every open opportunity and grind it down to ONE ready-to-send next step — owner named, deliverable drafted, staged for Jon's one-click approval.
**Drafted:** 2026-06-22 · Owner: Exo · Status: AWAITING JON'S GO

---

## 1. The problem this solves
124 opportunities in the tracker; 98 carry a `next_action`, but those actions are vague ("Manual review required", "Research Global Secure Shipping"). Nothing converts them into a *sent* artifact. Intel piles up; outreach doesn't go out. This engine closes the gap: opportunity → single concrete step → drafted deliverable → Jon approves → sent.

## 2. What "one actionable step" means (the agent contract)
Each agent takes exactly ONE opportunity and returns a strict object:
- **next_step** — one sentence, verb + object + recipient ("Email Giovanni Rosanova at NASA SRPO the BLK3 sounding-rocket capability one-pager")
- **owner** — `Exos (Jon)` or a named Team member (Lizi, Lquinn, counsel, etc.)
- **deliverable** — the actual artifact, fully drafted and staged in `drafts/`: email with To/Cc/Subject/body, or a doc. No placeholders, no "[POC TBD]".
- **route** — one of: `SEND` (email ready, needs Jon's approve), `TASK` (internal work, assign owner+due), `DECISION` (needs Jon's go/no-go or a missing input), `CLOSE` (dead — propose archiving with reason)
- **confidence / blockers** — if blocked, the single thing needed to unblock

If a contact is missing, the agent researches it first (standing rule) — never punts a placeholder.

## 3. Scope & filtering (cost control)
- **Exclude** CLOSED / SCAM / DEAD / DROPPED / PASS → ~30 drop out, leaving ~90 live.
- **Rank** by `value × urgency × stage-heat` (reuse the MC composite score already in server.js).
- **Process in waves of ~15** per run, hottest first. Two runs/day ⇒ the full live book cycles every ~3 days; hot items every run.
- Model tiering: **Sonnet** workers for the per-opportunity grind (cheap); **Opus** only for top-tier deals (ROFR, Series A lead, >$10M gov) and blocked-item escalation.

## 4. Routing the output (nothing leaves without Jon)
- `SEND` → email staged in `drafts/` **+** a Decision card in MC: *"Send to <recipient>? [Send / Edit / Hold]"*. Respects the no-external-email rule — Jon is the gate.
- `TASK` → MC task (owner, due, priority) via `/api/tasks`.
- `DECISION` → Decisions inbox via `/api/decisions/ingest` (yes/no or pick-an-input).
- `CLOSE` → Decision: *"Archive <opp>? reason: …"*.
Every run also writes the chosen `next_action` back into `opportunities-tracker.md` so the dashboard reflects reality.

## 5. Where it runs — LOCAL, by design
The 6 cloud research agents **cannot reach Mission Control** (MC is LAN-only at 192.168.143.216:8080; no public ingress). So this engine runs **locally** (launchd), where it can both read `opportunities.json` and POST to `localhost:8080`. Local model (Ollama/Qwen) for the cheap pass, with a Claude fallback for top-tier. This also fixes the broader wiring gap (see §7).

## 6. Mechanism
`scripts/opportunity_processor.py` (new):
1. Load `opportunities.json`, filter to live, rank, take next N (default 15) not processed in the last 24h (state in `data/opportunity-processor-state.json`).
2. For each, spawn a worker (sessions_spawn / local model) with the agent contract above + full Exos positioning context.
3. Validate each result against a schema; stage deliverables; POST the route to MC; write `next_action` back to the tracker.
4. Log a run summary to Discord #rd-team and the Research feed.
Scheduled via launchd `com.exos.opportunity-engine` — proposed 06:15 & 18:15 (after the 05:45/17:45 data refresh).

## 7. Bonus: this also bridges the cloud agents
While we're here, the same local pattern fixes the cloud→MC gap: a small `research_bridge` step reads the research Discord channels where the 6 cloud agents post and POSTs new briefs to `/api/research/ingest`. Folds the cloud intel into MC without a public ingress.

## 8. Build order (once approved)
1. `opportunity_processor.py` + state file + schema validation
2. Wire the 4 routes to MC endpoints (SEND/TASK/DECISION/CLOSE)
3. Tracker write-back
4. launchd schedule + Discord run-summary
5. Dry-run on top 15 (report only, no sends) → review with Jon → enable write-back + decision cards
6. (Optional) research_bridge for cloud agents

## 9. Decisions needed from Jon
- **Cadence/batch:** 15 per run × 2/day (full book ~3 days) — OK, or go bigger/faster?
- **Send gate:** keep every external email behind a Decision card (recommended), or auto-stage only?
- **Execution:** local Qwen for the grind + Claude for top-tier (recommended), or all-Claude?
