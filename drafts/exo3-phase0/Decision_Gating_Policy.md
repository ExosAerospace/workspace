# Decision Gating Policy — when the fleet may interrupt the CEO

**Standing rule, set by Jon 2026-08-26** ("reduce the decision steps to things where you clearly need me to make a choice"). Applies to every agent/engine that can create a Decisions-matrix card.

## The one test
A decision reaches Jon **only** when one of these is true:

1. **Genuine CHOICE (input).** He must pick between real options or supply information only he has (a strategic call, a routing pick, a meeting readout that gates a downstream move). Type = `choice`/`open`, not a rubber-stamp.
2. **External SEND he must authorize.** An email/message leaving the company. Jon explicitly keeps these ("continue to request approval before sending"). Type = `yesno` Send/Edit/Hold.
3. **Consequential / regulated.** gov/.mil/.gov, investor/capital/ROFR/409A, contracts/LOI/NDA, ITAR/export/DDTC, wires, Scorpius/RDRE strategic. These route to Jon (or the designated approver) by policy.

## What must NOT become a decision
- **Meta-wrappers** — "email/route/deliver/brief X *to Jon* for approval." That's Exo asking permission to do the delivery he already directed. **Do the delivery; don't gate it.** (If it produces an external send, surface *that* send — rule 2 — not the wrapper.)
- **Already-directed internal work** — anything Jon told the fleet to do. Execute and log it; don't re-ask.
- **Info-capture** — "get Jon's debrief/readout." That's a request for input, not a choice — make it a lightweight task/nudge, not a governance gate.
- **Speculative "does a warm path exist?"** — parked to the research feed (existing rule, Jon 2026-07-31).
- **Low-consequence outreach send-approvals** — delegated per standing rule (payload → UTD capstone; BLK3 → Lizi).

## Guardrail (never over-suppress)
Suppression rules are **guarded**: if the item carries a true-consequence signal (gov/investor/ITAR/NDA/contract/RDRE/Scorpius) or is an external send, it is **kept** with Jon regardless of phrasing. Suppression is **reversible** — items are superseded/filed, never deleted.

## Where it's enforced
- `opportunity_processor.py` — source-level (the 41% biggest generator).
- `decision_triage.py` — fleet-wide backstop (30-min cron).
- *(Optional, needs MC restart)* server-level ingest classifier — enforces the same test across **all** sources at creation time. Awaiting Jon's nod.

## The metric this serves
Fewer asks × low override on what remains. Baseline (2026-08-26): **ask rate ~86% avoidable**, **override rate 14.1%**. Both must trend down (see Wave 0 baseline).
