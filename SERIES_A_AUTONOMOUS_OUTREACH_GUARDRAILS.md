# SERIES A — AUTONOMOUS OUTREACH: GUARDRAILS & ACTION PLAN
**Prepared for:** John Quinn, Cofounder & CEO, Exos Aerospace
**Date:** June 26, 2026
**Purpose:** Define the controls under which Exo may send Series A investor outreach **directly** once Jon approves the messaging — and the phased plan to turn it on safely.

---

## The model — a "two-key" release system
Nothing sends until **both keys** are present:
- **KEY 1 — Approved Message.** A locked, version-stamped template (body + subject + disclaimer). Any edit voids approval and requires re-approval.
- **KEY 2 — Approved Audience.** A specific recipient list (or explicit selection criteria) pulled from the scored CRM, deduped and screened.

Both keys → Exo may send *that message* to *that audience*, within the operating limits below. Change either key → new approval. This is the core of "you approve, then I commence."

## The non-negotiable: securities-law compliance (do this FIRST)
Series A is a private securities offering. Before any send, **Marion Keyes confirms the Reg D exemption**, because it dictates what outreach is even legal:
- **If Rule 506(b)** — *no general solicitation allowed.* Outreach is limited to investors with a **pre-existing, substantive relationship.** The agent may only contact CRM records flagged as such.
- **If Rule 506(c)** — *general solicitation is allowed*, but you must take **reasonable steps to verify accredited status** before anyone invests. Broader outreach is fine; accreditation gates at the commitment stage.

Every message also carries an approved **disclaimer block** (not an offer to sell; offers made only via the PPM to accredited investors; forward-looking-statements caveat; no guarantees of return) and a **CAN-SPAM footer** (physical address 299 FM 1903, Greenville, TX 75402; working unsubscribe). No performance promises, no overstated traction, framing consistent with the PPM / financial model (projections only).

## Content controls
- **Locked approved templates only** — no improvised claims. Personalization limited to bounded fields (name, firm, one thesis hook); the agent never invents facts.
- Honors all standing Exos rules: one-of-three identity, no-overstate-traction, no unprovable absolutes, SEC-grade hedging.

## Recipient controls
- Send only from the **approved target list** (scored CRM), deduped.
- **MANDATORY DD GATE (hard block, no exceptions):** before any draft is prepared or any message is sent, the recipient MUST pass `scripts/dd_screen.py`. Call `dd_screen.is_blocked(firm=, email=, domain=)` — if it returns True (firm failed the CRM DD engine **or** is on the do-not-engage blocklist), the firm is **dropped and never contacted**. Firms returning `caution` require Jon's explicit human review before they enter a send batch. This gate is the same one the daily worklist uses, so the two can never diverge.
- **Hard-exclude list** enforced (competitors; Jon's named excludes — e.g., Dan Quayle per the Cerberus rule; anyone Jon flags).
- **Suppression list** honored permanently (opt-outs, bounces, "do not contact").
- **Daily cap** (recommend 25–40/day) and **business-hours CT, weekday** send windows — human-paced, protects deliverability/domain reputation.

## Send identity & cadence
- From **jquinn@exosaero.com**, correct signature/letterhead, proper reply-to.
- **One initial touch + an approved follow-up cadence** (e.g., +5 and +12 days), **max 2–3 touches**, then stop. No badgering.

## Human-in-the-loop tiers
- **Tier 1 (autonomous after two-key approval):** initial templated outreach + approved follow-ups to the approved list.
- **Tier 2 (Jon approves each):** anything personalized beyond bounded fields; high-value/strategic targets; **sending the PPM or granting data-room access**; any non-standard ask.
- **Tier 3 (Jon only — agent never):** negotiating terms, valuation talk, commitments, signatures.

## Reply handling
- **All replies route to Jon immediately** and are logged to CRM. The agent may *draft* a suggested response but **does not send replies autonomously** in v1 — replies are where the nuance and risk live.

## Audit, reporting & kill switch
- **Every send logged to CRM**: timestamp, template version, recipient, status. Immutable trail; nothing deleted.
- **Daily digest to Jon:** sent / opens / replies / warm leads / anything paused.
- **Auto-pause triggers:** bounce rate over threshold, any spam complaint, a reply signaling a legal/regulatory concern, or abnormal reply volume → halt + alert.
- **Kill switch:** "pause Series A outreach" halts instantly. Standing circuit-breaker: **stop and re-confirm after the first batch (e.g., 50 sends).**

---

## Action plan (phased rollout)
**Step 1 — Authorize (this week).**
- Keyes confirms exemption (506(b) vs 506(c)) + permissible outreach + disclaimer language.
- Jon approves the master template(s) + disclaimer (Exo will provide 1–2 ready options).
- Lock the target list / criteria from `SERIES_A_SCORED_CRM`; set daily cap + suppression list.

**Step 2 — Pilot.**
- Agent sends a **small approved batch (10–20 targets)**, logs to CRM, reports. Jon reviews results before scaling.

**Step 3 — Scale within caps.**
- Roll to the full approved list within daily caps; run the approved follow-up cadence; reply-routing to Jon; weekly pipeline report.
- Stand up a **Series A Outreach Agent** (scheduled, like the NASA Capture Agent) + a **Series A pursuit tracker**, with the two-key send capability wired in.

**Step 4 — Iterate.**
- Tune templates by response data; expand the list; surface warm leads to Jon for Tier-2/3 handling.

---

## What Exo needs from Jon to switch it on
1. **Exemption confirmed** (Keyes): 506(b) or 506(c) — gates everything.
2. **Approve the master message + disclaimer** (Exo will send 1–2 options).
3. **Approve the target list / criteria** + hard-excludes.
4. **Set the daily cap** and confirm send-from = jquinn@exosaero.com, replies route to you only.
5. **OK the pilot-first** (10–20) rollout.

*Recommendation: pilot-first, 506-exemption confirmed by Keyes before any send, replies always to Jon. Once 1–5 are set, Exo can commence outreach inside these guardrails and report daily.*
