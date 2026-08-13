---
name: "consortium-play"
description: "Evaluate any opportunity as an Exos prime-integrator consortium play (EIC): partners, FFP scopes, backups, vehicle."
---

# Consortium Play — evaluate opportunities as an Exos prime-integrator bid

**When to use:** any BD opportunity, RFP/RFI/BAA/SBIR, or partner conversation. Run this lens *in addition to* the single-company angle — Exos's differentiator is being the integrator that knits 3–4 firms into a virtual prime.

## The model (EIC — Exos Integrated Consortium)
Exos = **prime integrator**: holds the contract, systems-engineering/PM integration, the compliance boundary (ITAR/CUI on GCC High via Atomus, CMMC), and the **single-point-of-failure backup bench**. Each partner **quotes and owns its own scope Firm-Fixed-Price** and keeps autonomy/IP/other customers. Full model: `drafts/Exos_Integrated_Consortium_Model.md`. Live tracker: `mission-control/consortium.html` + `mission-control/data/consortium.json`.

## Procedure
1. **Decompose** the opportunity into clean, ownable scopes (the WBS a prime would sub out).
2. **Map partners to scopes** from the bench (`data/consortium.json` + relationship dossiers): Scorpius (propulsion/tanks), MATECH/Super Carbon (CMC + carbon-carbon), Hybron (fast composites), CDT (composites mfg), Starfighters (flight test / underutilized-company sub-consortium), Atomus (compliance), CertBuddyAI (regulatory), Albers (hub). Ask: **"which 2–4 partners + Exos = a winning prime bid here?"**
3. **Assign a 2-deep backup** for every critical scope (the contingency bench = Exos's value-add and margin basis).
4. **Pick the vehicle** (light→heavy): Teaming Agreement→FFP subcontract · standing Consortium MOU · JV (only for a big set-aside) · License (embedded IP).
5. **Protections:** 2-page master per partner (MNDA + background/foreground IP split + non-circumvention + scope-bounded FFP + exclusivity window + exit) + 1-page per-pursuit work order (scope, price, backup). RDRE/controlled subject → MNDA before technical exchange.
6. **Log it:** add/append the pursuit + members to `data/consortium.json` (partner, scope, backup) so the team is tracked.
7. **Surface to Jon:** name the consortium, not just the single-company angle, and flag the strongest 2–3 plays.

## Output
A short "consortium framing" for the opportunity: WBS scopes → partner per scope (FFP) → backup per scope → vehicle → protections needed → next step. Update the Consortium track.

## Guardrails
- Each partner prices its OWN scope FFP; no forced cost-share; risk bounded to scope.
- Never expose one partner's confidential data to another without NDAs in place.
- Controlled tech (RDRE, hypersonics) → ITAR posture + MNDA first.
