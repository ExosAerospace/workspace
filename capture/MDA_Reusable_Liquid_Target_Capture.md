# MDA — Reusable Liquid-Signature Threat-Representative Target (Exos as PRIME)

**Prepared for:** John Quinn, Cofounder & CEO, Exos Aerospace · **Date:** 2026-08-24
**Classification:** Proprietary / Unclassified · **Status:** Capture thesis for pursuit decision
**Relationship to prior work:** This is the **lead play**. The kill-vehicle sub-tier analysis (`MDA_LowCost_KillVehicle_Capture.md`) becomes the **fallback/secondary** — there, Exos is a minor sub under a weapons prime. Here, **Exos is the prime of a capability MDA structurally needs and largely cannot buy.**

---

## Bottom line up front

Exos should go **directly to MDA** as the **prime** of a **reusable, liquid-fueled, threat-representative target vehicle** — not as a sub on someone's kill vehicle. The wedge is a real, widening test-fidelity gap: **the threat is going liquid and reusable, while MDA's target fleet is overwhelmingly solid-motor.** A solid target cannot faithfully present a liquid threat's signature. Exos's liquid propulsion — normally just an architecture choice — becomes a **signature moat**, and the in-program **RDRE + storable-propellant** roadmap extends it into a **threat-signature library**.

- **Non-dilutive entry:** ~**$2M** direct-to-MDA to modify BLK3's flight trajectory to threat-representative kinematics + characterize the liquid signature.
- **Recurring line:** **$1.5M/vehicle**, reusable **20–25 flights** (non-lethal test phases leave the target intact) → **multi-$M per vehicle over life**; a small fleet = a **tens-of-$M recurring** program.
- **Primes (LM / Elbit America / Firefly) become customers/teammates, not gatekeepers.**

---

## 1. The threat thesis (the "why now" for MDA)

1. **The threat is going liquid and reusable.** A generation of adversary and emerging-power systems runs on **reusable, liquid-fueled** propulsion — China's reusable liquid boosters, Iran's expanding liquid launch/missile program, North Korea's liquid ICBMs. Key logic: **any nation with orbital launch capability inherently has ICBM-range energy** — and increasingly those systems are **liquid, not solid-motor.**
2. **Liquid signatures break the solid-target assumption.** Solid motors and liquid engines present **fundamentally different plume signatures** — spectral content, intensity, temperature, particulates (solids carry aluminum-oxide; liquids do not). Sensors and seekers validated against **solid** targets are **not proven against the liquid threats actually proliferating.** A live test-fidelity gap.
3. **The target inventory hasn't caught up.** MDA's target fleet is overwhelmingly **solid-motor** (cheap, storable). There is a **structural shortage of liquid-signature, threat-representative targets** — precisely as the threat set turns liquid.
4. **Reusability cuts both ways.** Adversary reusable-liquid vehicles mean higher launch cadence to defend against; a **reusable liquid target** lets MDA test at matching **cadence and cost**.

**Net:** MDA needs liquid-signature, threat-representative, high-cadence targets — a need that grows as the threat proliferates, and one the current solid fleet cannot meet.

---

## 2. Why Exos, uniquely — liquid propulsion as a signature moat

- **BLK3 is liquid-fueled and reusable.** Categorically the right signature class, at **20–25 flights per vehicle** — not the one-and-done economics of an expendable target.
- **The propulsion roadmap IS a threat-signature library.** This is the part unique to Exos:
  - **Today (LOX/ethanol):** liquid-class boost/ascent signature — far closer to a liquid threat than any solid target.
  - **Storable propellants (in-program pursuit):** moves the signature toward actual threat chemistry (SCUD/Shahab/No-Dong use storable hypergolics), improving fidelity.
  - **RDRE (in-program pursuit):** a novel **detonation-cycle** signature representing *next-generation* propulsion threats.
  - → The RDRE + storable work already funded in the program **doubles as a threat-representation roadmap**, not a separate R&D line.
- **Minimal-infrastructure / mobile** ops → distributed, responsive test cadence; **TX-local**; **non-dilutive** $2M dev.

---

## 3. Honest capability tiering (so MDA's signature people trust the pitch)

**Range-class progression (per JQ, 2026-08-24):** BLK3 is honestly an **extremely short-range** vehicle in MDA's book — the **short-range (SRBM-class) test target** that proves the reusable liquid-signature model **now**. **BLK4 is the intermediate-range (IRBM-class) growth tier** — previously proposed around the **flight-proven Firefly Reaver engine (COTS)** — which reaches the **IRBM tier of MDA's own target RFI** (§5). ICBM-class is roadmap/beyond.

| Tier | What it represents | Status |
|---|---|---|
| **Liquid boost/ascent signature** | Liquid-plume IR/optical signature vs. solid | **Now** — BLK3's core differentiator |
| **Short-range (SRBM, "SCUD-class") target** | SCUD short-range liquid threat — kinematics + liquid signature | **Now (BLK3)**, with the $2M trajectory mod |
| **Signature tuned to a specific threat set** | Exact spectral match to a SCUD variant (propellant/additive/plume seeding) | **Tunable** — storable-propellant path improves this |
| **Intermediate-range (IRBM, SCUD-derivative / No-Dong / Shahab-class) target** | IRBM kinematics/energy — the MDA TC RFI's tier | **Growth (BLK4)** — COTS design around Firefly Reaver engine |
| **ICBM-class reentry / RV separation / penaids** | Intercontinental terminal energy, complex threats | **Roadmap/beyond** — do not claim today |

**The claim to make:** *"A reusable, liquid-signature target family — short-range today (BLK3), intermediate-range (IRBM) next (BLK4, COTS/Reaver), built entirely from commercial off-the-shelf components — tunable to the threat set."* **Not** "identical to a SCUD," **not** "ICBM today." That honesty is what makes it credible to MDA's signature analysts.

**COTS is the low-cost/low-risk story:** the entire design — including BLK4's flight-proven **Firefly Reaver** engine — is **commercial off-the-shelf.** No bespoke propulsion development on the target's critical path (RDRE stays a separate propulsion-signature roadmap element, not the target's engine). COTS = affordable, fast, low technical risk, domestic supply — exactly MDA's low-cost mandate.

---

## 4. The reusability economics (why the unit price works)

Most interceptor/sensor test events **do not destroy the target**: seeker characterization, track/discrimination, guidance, and **fly-by / "turn-away"** geometries all leave it intact. Only **terminal hit-to-kill lethality shots** expend a target. So a reusable target survives the non-lethal campaign and is spent only at end-of-life (~20–25 flights) or on a deliberate lethality event.

**First-vehicle revenue model** (revenue side is firm from Jon's framing; cost inputs flagged for Exos to confirm — not invented here):

| Line | Value | Note |
|---|---|---|
| Non-recurring dev (MDA-funded) | **~$2.0M** | Trajectory mod + liquid-signature characterization; **non-dilutive** |
| Vehicle unit price | **$1.5M / vehicle** | Reusable |
| Flights per vehicle life | **20–25** | Non-lethal test phases |
| Per-sortie service (range ops + refurb + margin) | **[Exos to set]** | Illustrative $150–300K → **$3–7.5M / vehicle over life** |
| **Lifecycle revenue / vehicle** | **$1.5M + (20–25 × sortie)** | Recurring |
| Small fleet (e.g., 3–5 vehicles) | **tens of $M, recurring** | Program-scale |
| **Margin** | **[needs BLK3 unit build cost + per-sortie refurb cost]** | *Jon/Neil to plug real numbers* |

**Customer value pitch:** *"20+ threat presentations for the cost of a couple of expendable targets — and they're liquid-signature, which expendable solids can't give you."*

---

## 4A. Program framing — a **$75M, BLK3 → BLK4** target program

Present to MDA as a **~$75M, ~3-year program** that stands up a **reusable SCUD-family target line**, progressing from the short-range **SCUD-class (BLK3)** to the intermediate-range **No-Dong / Shahab-class (BLK4, COTS Reaver)**. Notional allocation to the $75M topline (WBS to firm with Exos cost inputs):

**Phase 1 — BLK3 SCUD-class SRBM target — $18M**
- Threat-representative trajectory mod + liquid-signature characterization — $4M
- Storable-propellant signature-fidelity development (closes the SCUD nitric-acid gap) — $4M
- Reusable target vehicles (4 + spares) — $7M
- Mobile range-ops kit + integration — $3M

**Phase 2 — BLK4 No-Dong/Shahab IRBM-class target — $34M**
- BLK4 vehicle development (airframe / structures / avionics) — $14M
- COTS **Firefly Reaver** engine integration + procurement — $6M
- IRBM trajectory / kinematics + higher-fidelity signature — $5M
- BLK4 fleet build + tooling — $9M

**Cross-program — operations, signature, PM, reserve — $23M**
- Signature-augmentation / seeker-representation partner scopes — $5M
- Manufacturing tooling + domestic second-source bench — $4M
- Multi-year range operations & sustainment — $6M
- Systems engineering / PM / ITAR-CMMC compliance — $4M
- Program reserve / integrator contingency — $4M

**Total: $75M.**

**Recovery is a funded R&D sub-phase — honest attrition (per JQ):** recovering a vehicle **on a ballistic reentry trajectory** is genuine, unsolved-in-this-class development. Plan for **3–5 vehicles expended before the first successful recovery** (grounded: LandSpace Zhuque-3 failed its Dec-2025 recovery before succeeding Aug-2026; the US had no recoverable ballistic/hypersonic vehicle between the X-15 and Stratolaunch). This is fundable — MDA understands flight-test attrition — and the expended early units **still deliver value as expendable threat targets** during the recovery campaign. **US uniqueness:** no other US provider flies a **ballistic, liquid-signature threat profile *and* has a path to recover on that trajectory** — Stratolaunch recovers but flies a winged hypersonic *glide* (wrong regime); Rocket Lab HASTE flies ballistic but is *expendable*; Blue Origin recovers a *fixed vertical hop* (not threat-representative). Full analysis: `RD_Liquid_Threat_Landscape_and_Recovery.md`.

**The strategic kicker — a non-dilutive path to BLK4.** This program **pays Exos to build BLK4** — the exact next-gen vehicle behind the Series A / STRATFI narrative. MDA target dollars fund a vehicle Exos intends to build anyway, and the reusable-target line then throws off recurring revenue on top. The $2M trajectory-mod and $1.5M/vehicle unit economics (§4) sit **inside** this program as line items, not the whole story. *(Allocations illustrative to Jon's $75M topline; firm with real BLK3/BLK4 build cost.)*

---

## 5. Path to capture (Exos as prime, direct)

1. **IS&T / Advanced Capability Concepts white paper** (fastest touch): *"Reusable liquid-signature threat-representative target for MDS sensor/interceptor test."* Anchor on the threat thesis (§1). *(Exo drafts; .mil submission needs Jon.)*
2. **NOBLE registration** (HQ0860-25-S-0001) — get on the low-cost target / test distribution. *(Jon go, .mil.)*
3. **MDA SBIR** — target-vehicle / signature-representation topic in the FY26 cycle: the lane where Exos primes a small scope and earns credentialing + non-dilutive dev.
4. **Primes as customers/teammates, not gatekeepers:** LM MFC (Grand Prairie), Elbit America (Fort Worth — seeker/signature partner), Firefly (responsive launch) — offer them the target service; don't wait to sub under them.

---

## 6. What needs Jon (async — decide when back)

1. **Go/no-go on the pursuit** as framed (Exos prime, direct-to-MDA reusable liquid target).
2. **Plug real cost inputs** (BLK3 unit build cost, per-sortie refurb) so the P&L shows margin, not just revenue.
3. **The "[stud]-like vehicle" reference** from the 8/24 thread didn't transcribe cleanly — confirm the vehicle/designation you wanted this modeled on and it goes in.
4. **On approval:** Exo drafts the IS&T white paper + NOBLE capability snapshot (both .mil-ready for Jon's send) and the one-page threat-thesis leave-behind.

---
*Sources: this capture synthesizes the 2026-08-24 strategy thread (JQ); MDA_LowCost_KillVehicle_Capture.md; MDA_Opportunity_Capture_Brief.md (NOBLE HQ0860-25-S-0001, IS&T BAA, MDA SBIR). Threat characterization (liquid vs. solid plume signatures; liquid-fueled threat proliferation; orbital=ICBM-range energy) per open-source missile-defense literature. Revenue framing per JQ; cost/margin inputs pending Exos internals. Proprietary / Unclassified — no CUI.*
