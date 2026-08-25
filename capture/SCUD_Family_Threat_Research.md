# SCUD Family — Threat Research Brief (supports the MDA reusable-liquid-target thesis)

**Prepared for:** John Quinn, Exos Aerospace · **Date:** 2026-08-24 · **Classification:** Proprietary / Unclassified — open-source only
**Purpose:** Ground the reusable liquid-signature target pitch (`MDA_Reusable_Liquid_Target_Capture.md`, `drafts/MDA_TC_Target_RFI_Response_DRAFT.md`) in real SCUD-family data.

---

## 1. What the SCUD is

- **Origin:** Soviet. R-11 (Scud-A, IOC 1957, DIA SS-1b) → **R-17 / R-300 Elbrus (Scud-B, IOC ~1962–64, SS-1c)** — the definitive, most-produced version. Designer Makeyev / SKB-385; Isaev engine.
- **Single-stage, liquid-fuel, road-mobile SRBM.** Inertial guidance. Max speed ~Mach 5.
- **The most-launched ballistic missile in war except the German V-2** (Iran–Iraq "War of the Cities," Gulf War 1991, and many others).

## 2. Propulsion & propellant — the signature-relevant part

- **Storable liquid bipropellant** (deliberately, to avoid cryogenic LOX and enable field storage/mobility):
  - **Fuel:** kerosene-based **TM-185**.
  - **Oxidizer:** **inhibited red fuming nitric acid (IRFNA / AK-27I)** — nitric-acid-based.
  - **Igniter:** **TG-02** (triethylamine/xylidine), hypergolic with the acid.
- **Load (Scud-B):** ~3,500 kg IRFNA oxidizer + ~1,000 kg fuel.
- **Why it matters for us:** this is a **nitric-acid/kerosene** combustion plume — a **liquid-class signature, chemically distinct from solid-motor** targets (no aluminum-oxide) *and* distinct from cryogenic LOX engines. **This is the honest fidelity anchor:** BLK3 today is **LOX/ethanol (cryogenic)** → correct *liquid class*, but a different oxidizer chemistry than a SCUD's nitric-acid plume. **Closing that gap is exactly what our storable-propellant pursuit does** — it moves the signature toward true SCUD chemistry. So "SCUD-class, tunable via storables" is the accurate claim, and this research is *why* the storable roadmap has program value.

## 3. Variants (the SRBM ladder — maps to BLK3)

| Variant | DIA | Range | Payload | Notes |
|---|---|---|---|---|
| Scud-A (R-11) | SS-1b | 180 km | 950 kg | Original |
| **Scud-B (R-17)** | SS-1c | **300 km** | 985 kg | Core; CEP ~450 m; ~11.25 m × 0.88 m, ~5,900 kg |
| Scud-C | SS-1d | 550–600 km | 600 kg | Extended range, less payload |
| Scud-D | SS-1e | 700 km | 985 kg | 1989; terminal guidance / **separating warhead** |

## 4. The proliferation family (why this is a *large, recurring* threat set — maps BLK3→BLK4)

The SCUD is the **taproot of the world's liquid ballistic-missile threat.** Its descendants are the systems MDA and allies actually test against:

- **North Korea:** Hwasong-5 (Scud-B copy) → Hwasong-6 (Scud-C) → Hwasong-7 / **No-Dong (Rodong)** — a scaled-up Scud, **MRBM ~1,000–1,300 km**, larger airframe/engine, heavy warhead.
- **Iran:** **Shahab-1** (Scud-B / Hwasong-5) → **Shahab-2** (Scud-C / Hwasong-6, separating **Qiam-1** variant) → **Shahab-3** (No-Dong-derived **MRBM/IRBM, ~800–2,000 km**, single liquid engine, AK-27 oxidizer). Iran's liquid-missile program has near-total North Korean "DNA"; ODNI (Mar 2025) notes Iran holds the **largest missile stockpile in the region**; NASIC catalogued **14+ Iranian ballistic-missile variants**.
- **Also fielded/derived:** Syria, Egypt, Libya, Pakistan lineage.

**The mapping to our vehicles is exact:**
- **BLK3 = SCUD-class SRBM** (Scud-B/C, Shahab-1/2, Hwasong-5/6) — the short-range liquid threat, **now**.
- **BLK4 = SCUD-derivative IRBM** (No-Dong / Shahab-3 class, ~1,000–2,000 km) — same liquid family scaled up, **COTS Firefly Reaver**, the MDA TC RFI's IRBM tier.

## 5. Why this makes the Exos pitch stronger

1. **The threat is real, dominant, and liquid.** The most-proliferated ballistic threat set in the world — across the actual adversaries missile defense is sized against — is **liquid-fueled SCUD lineage**, SRBM through IRBM.
2. **Solid targets misrepresent it.** A solid-motor target cannot present a nitric-acid/kerosene (or any liquid) plume. The fidelity gap is structural.
3. **Our roadmap is the answer, and now it's evidence-backed.** Liquid airframe today (right class) + **storable-propellant pursuit** (toward SCUD nitric-acid chemistry) + **range progression** (BLK3 SRBM → BLK4 IRBM/Reaver) = a **SCUD-family threat-representation line** matched to the real threat ladder.
4. **Honest framing holds:** "SCUD-class liquid signature, tunable toward specific variants via storables" — never "identical," never "ICBM today."

---
*Open-source sources: CSIS Missile Threat (missilethreat.csis.org — Scud, Shahab-3); Missile Defense Advocacy Alliance; Astronautix / RussianSpaceWeb (R-17); U.S. Army ODIN WEG; CRS "Iran's Ballistic Missile Capabilities" (everycrsreport.com); IISS Iran missile open-source analysis; Atlantic Council Iran missile inventory; 19FortyFive (Iran–NK missile DNA, 2026). All UNCLASSIFIED open-source; no CUI. Figures are open-source estimates and vary by source.*
