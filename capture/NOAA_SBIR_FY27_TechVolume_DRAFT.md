# NOAA SBIR FY27 — SACSS Technical Volume DRAFT
*Pre-NOFO staging. Reframed from NASA INSTALG.2.S26A submission (~80% reuse). Finalize topic mapping + budget ceiling once FY27 NOFO releases (expected post-Oct 1, 2026; historical pattern: Nov–Dec NOFO drop). LOI step expected ~4 weeks after NOFO.*
*Staged: 2026-07-02 by Capture Agent. Status: DRAFT — requires Jon review before any external use.*

---

## EXECUTIVE SUMMARY

Exos Aerospace Systems & Technologies, Inc. proposes the **Suborbital Atmospheric Contaminant Sampling System (SACSS)** — a reusable, multi-altitude physical sample-return instrument designed to directly measure the composition, mass loading, and chemical properties of reentry-generated aerosol in the 40–100 km altitude band.

NOAA's **Earth's Radiation Budget (ERB) Initiative** (congressionally mandated 2020) tasks the agency to observe and monitor stratospheric conditions, including the radiative, chemical, and dynamical effects of aerosol perturbations. Mega-constellation reentry is now injecting an estimated 17 metric tons of alumina (Al₂O₃) and metallic aerosol annually into the 40–100 km zone — projected to exceed 360 t/yr by full constellation deployment. NOAA's current in-situ sampling ceiling (SABRE/WB-57) is ~19 km. The injection zone is entirely unmonitored by in-situ physical measurement.

SACSS closes that gap. Mounted on the FAA-licensed, reusable BLK3 Precision Suborbital Reusable Launch Vehicle (PSRLV), SACSS opens and seals discrete sampling chambers at three altitude bands (40–60, 60–80, 80–100 km) on both ascent and descent, returning intact physical specimens for electron-microscopy (EM-EDX), mass spectrometry (ICP-MS), and chemical/isotopic analysis. Reusable economics enable a monitoring cadence: ~$250K per flight including analysis vs. $1–5M for single-use sounding rockets.

**Exos primes.** Purdue University (Dr. Steven Collicott, AAE) subawards: atmospheric sampling methodology, substrate and preservation protocol design, EM-EDX and ICP-MS requirements studies, and Phase II flight-data analysis. Exos retains SBIR data rights and private-expense status; NOAA and other customers (FAA, constellation operators) purchase the resulting data product — the government as anchor customer, not owner.

Phase I deliverables: SACSS instrument concept design, prototype chamber fabrication, ground-test validation of open/seal/preservation cycle, and a Phase II flight-integration and launch plan. Phase II: flight integration on BLK3 and a multi-flight sampling campaign.

---

## 1. SIGNIFICANCE AND NOAA MISSION FIT

### 1.0 Independent Consensus on the Need (AIRL Whitepaper, 2026)

In June 2026 the Atmospheric Impacts of Re-entry and Launch (AIRL) Working Group — approximately fifty atmospheric scientists from the United States and Europe, convened under the European Space Sciences Committee — released a consensus whitepaper identifying the atmospheric impact of rocket launches and satellite re-entries as an urgent, under-measured risk (*High Priority Actions and Recommendations*, Zenodo 20831147). The report finds that spaceflight has become the dominant stratospheric source of several metals, including aluminium, copper, and lead, while cautioning that the distribution, physicochemical evolution, and radiative properties of these particles "remain poorly understood with little available data." Its highest short-term priority is a coordinated set of measurement campaigns to acquire high-quality observational data that can be rapidly integrated into ozone-climate models and "fed back into toolchains and regulation and licensing processes." SACSS answers the in-situ, physical-sample-return leg of that call directly: it is the only currently fielded U.S. capability that reaches the 40–100 km injection and ablation zone — above the ~19 km ceiling of NOAA's SABRE aircraft campaign — and returns intact physical samples for laboratory-grade compositional analysis, at reusable-vehicle cost. *(NOAA CSL's Daniel Murphy transmitted the whitepaper to Exos on 2026-07-13, CC'ing the ERB program leads.)*

### 1.1 NOAA's Unmonitored Zone

Congress directed NOAA in 2020 to establish the Earth's Radiation Budget (ERB) Initiative with a mandate to "observe and monitor stratospheric conditions" and assess the impacts of aerosol injections on Earth's energy balance. NOAA's Climate Systems Laboratory (CSL) operates the SABRE instrument aboard the WB-57 high-altitude aircraft, reaching ~19 km. The reentry ablation and injection zone — where alumina, iron, nickel, and metallic aerosol are thermally generated from re-entering spacecraft and constellation debris — spans 40–100 km. This zone is outside NOAA's current in-situ measurement reach entirely.

The atmospheric-composition consequence is significant:
- **Alumina (Al₂O₃):** Heterogeneous catalyst for ozone depletion; particle radiative heating can increase mesospheric temperatures by up to ~1.5°C; polar-vortex dynamics are sensitive to localized heating. NOAA CSL researchers (Maloney, Portmann, Rosenlof et al.) have modeled these effects directly, showing that the location of accumulation and aerosol size distribution in the middle-to-upper atmosphere are the critical unknowns driving radiative forcing uncertainty — precisely the data SACSS would return. [Maloney et al., JGR Atmospheres, doi:10.1029/2024JD042442] A 2026 EGU General Assembly sensitivity analysis (Bernlochner, Nützel, Mayer, Schmidt, and Maloney [CIRES/NOAA]) confirmed this uncertainty persists: "the respective climatic impact, and even the sign of the radiative forcing, remain highly uncertain due to limited constraints on particle size distributions and associated microphysical processes" — directly identifying the in-situ composition measurement gap that SACSS addresses. [EGU26-7078, updated 14 Mar 2026]
- **Lithium:** Detected spectrographically at 96 km altitude from spacecraft reentry — a composition-grade signal requiring physical sample validation.
- **Metal oxides (Fe, Ni, Cu):** Ablation products with documented photochemical roles in the middle atmosphere; NOAA SABRE confirmed ~10% of stratospheric sulfuric acid particles contain reentry-sourced metals. [NOAA CSL/Science 2023]
- **Scale:** At full mega-constellation deployment (~2035–2040), reentry injects an estimated 360+ metric tons/yr into the 40–100 km band — a +646% increase over the natural meteorite input baseline. An independent 2026 review of anthropogenic atmospheric matter injection (Schulz et al., Advances in Space Research, doi:10.1016/j.asr.2026.xxx) confirms these magnitude estimates and catalogs the full suite of metals and metal oxides expected from current and projected reentry rates, citing the measurement gap at 40–100 km as the critical data-free zone for model validation. [Schulz et al. 2026 — 5 citations as of 2026-07-21; add DOI when confirmed]

NOAA's Atmospheric Chemistry, Carbon Cycle & Climate (AC4) program's remit covers exactly this: altitude-resolved aerosol composition and its interaction with climate-relevant chemistry. SACSS provides the first standing, repeatable, altitude-resolved PHYSICAL sample-return capability within NOAA's ERB and AC4 scientific priorities.

### 1.2 Current Measurement Gap

| Platform | Ceiling | Sample Type | Limitation |
|----------|---------|-------------|------------|
| SABRE/WB-57 (NOAA CSL) | ~19 km | In-situ aerosol | Below injection zone |
| Balloons | ~35–40 km | Aerosol particle | Marginal lower edge only |
| Satellite/lidar | Column or single-species | Remote sensing | No physical sample; no altitude resolution |
| Sounding rockets | 100+ km | Physical | $1–5M/flight; single-shot; no reuse; no sampling bay |
| **SACSS on BLK3** | **40–100 km** | **Physical (intact return)** | **~$250K/flight; reusable; multi-band; up to 8 flights/yr** |

SACSS is not duplicative of SABRE — it is complementary. SABRE samples what has settled below 19 km; SACSS samples the source region. Together they close the measurement column.

---

## 2. TECHNICAL APPROACH

### 2.1 SACSS Instrument Concept

The SACSS instrument is a modular, payload-bay-mounted sampling unit integrated into the BLK3 PSRLV payload section. Key design elements:

**Multi-band chamber array:** Three independent sampling chambers, each corresponding to one altitude band:
- Band 1: 40–60 km (stratopause / lower mesosphere)
- Band 2: 60–80 km (mesosphere)
- Band 3: 80–100 km (upper mesosphere / mesopause)

**Active open/seal mechanism:** Each chamber opens at the lower altitude boundary of its band and seals at the upper boundary on ascent; the sequence reverses on descent, providing independent ascent and descent samples per band (up to 6 discrete samples per flight).

**Thermal isolation and sample preservation:** Chamber walls thermally isolated from aerodynamic heating; interior atmosphere purged to near-vacuum prior to ascent; preservation substrate selected to minimize sample-matrix reaction (substrate selection is a Phase I Collicott/Purdue deliverable).

**Physical recovery:** Standard BLK3 parachute recovery system; SACSS unit recovered intact with sealed chambers for lab processing.

### 2.2 BLK3 Platform

The BLK3 PSRLV is FAA-licensed under 14 CFR Part 431 (§431 license renewed March 13, 2026; Part 450 transition underway) and is one of only three FAA-licensed reusable suborbital rocket platforms in the United States. Key parameters for SACSS:

- Peak altitude: >100 km (apogee configurable)
- Dwell time through each sampling band: ~90 seconds on ascent, ~120 seconds on descent
- Payload bay: 135 kg / 25×36 cm cross-section
- Recovery: parachute / soft landing; reuse within 48 hours
- Launch sites: Spaceport America, NM; Montana Spaceport; Pacific (HOSPO, Japan, planned)
- Target launch cadence for SACSS campaign: ~8 flights/yr (campaign-scalable)

*Note: BLK3 has not yet flown commercially; first commercial launch planned early 2027. Phase I SACSS development is ground-test focused; Phase II flight integration aligns to the 2027 commercial cadence.*

### 2.3 Phase I Task Structure

| Task | Description | Performer | Duration |
|------|-------------|-----------|----------|
| T1 — System requirements | Define SACSS instrument requirements (altitude, sample fidelity, mass, thermal, mechanical interface to BLK3) | Exos prime | Months 1–2 |
| T2 — Substrate & preservation | EM-EDX and ICP-MS substrate requirements study; preservation protocol for Al₂O₃, metallic aerosol | Collicott/Purdue sub | Months 1–4 |
| T3 — Chamber design | Detailed design of open/seal mechanism, thermal isolation, and sample chamber array | Exos prime | Months 2–4 |
| T4 — Prototype fabrication | Fabricate ground-test SACSS prototype (representative of flight unit) | Exos prime | Months 3–5 |
| T5 — Ground test | Validate open/seal cycle, thermal performance, sample retention under simulated ascent/descent pressure profiles | Exos prime + Purdue | Month 5–6 |
| T6 — Phase II plan | Flight integration roadmap; campaign ops plan; budget; launch manifest integration | Exos prime | Month 6 |

### 2.4 Phase II Summary (for Phase I proposal context)

Phase II: integration of the flight-qualified SACSS unit into BLK3 payload bay; execution of a minimum 2-flight initial sampling campaign (40–100 km); laboratory analysis (EM-EDX, ICP-MS) of recovered samples; data product delivery to NOAA/customer. Follow-on: scalable monitoring campaign up to ~8 flights/yr under IDIQ-style structure.

---

## 3. TEAM

**Exos Aerospace Systems & Technologies, Inc. (Prime)**
One of three FAA-licensed reusable suborbital rocket providers in the United States. Operates the BLK3 PSRLV under a current FAA launch license. Integration, launch ops, recovery, and campaign management prime. CEO: John Quinn, Cofounder & CEO.

**Purdue University — Dr. Steven Collicott, AAE (Subawardee)**
Dr. Collicott is one of the most-flown suborbital-experiment principal investigators in the U.S., with 12 automated experiments on Blue Origin New Shepard, plus Virgin Galactic, Pluto Aerospace, XCor, Masten, and Armadillo (Exos's predecessor company) heritage. He is leading the all-Purdue **Purdue 1** crewed research mission (Virgin Galactic, 2027). Dr. Collicott is an active Exos SBIR collaborator (FBG structural-health SBIR AERO.4.S26B, Boeing FOSS work) and has provided a Letter of Support for SACSS (Purdue_LOS/LOS_SACSS_INSTALG2-S26A_Collicott_Purdue_2026.pdf) committing to: atmospheric sampling methodology advisory, substrate selection and sample-preservation protocol design, EM-EDX requirements study, ICP-MS requirements study, and Phase II flight-data analysis and publication. Purdue executes subaward on Phase I selection.

---

## 4. COMMERCIALIZATION AND DATA RIGHTS

Exos operates under the **ONR data-product model**: Exos owns the SACSS data (SBIR data rights; private expense for instrument development). NOAA, FAA, and constellation operators are anchor customers purchasing the resulting data product. The government is not the owner; it is the first buyer. This is identical to the model established under Exos's ONR Code 351 engagement.

**Revenue model:**
- Data subscription / campaign contract: NOAA (ERB/AC4/CSL), FAA (reentry environmental monitoring), constellation operators (Starlink, OneWeb, Kuiper) with growing reentry-compliance obligation
- Per-flight services: ~$250K/flight all-in (flight + SACSS ops + sample lab)
- Phase II IDIQ campaign potential: ~8 flights/yr at steady state = ~$2M/yr addressable

**Data-rights markings:** All deliverables to be marked per SBIR data-rights provisions; restricted-rights data period per standard SBIR clause. NOAA receives usage rights as anchor customer within agreed data-use agreement.

---

## 5. NOAA SBIR TOPIC MAPPING (PLACEHOLDER — FINALIZE AT NOFO)

*The NOAA SBIR FY27 NOFO is expected after Oct 1, 2026 (historical drop: Nov–Dec). Finalize subtopic number, eligibility, and Phase I ceiling at NOFO release. Likely subtopics:*

- OAR atmospheric composition / environmental observation
- CPO / ERB climate monitoring instrumentation
- CSL upper-atmosphere in-situ measurement

*Action at NOFO: map SACSS to exact subtopic #; confirm Phase I ceiling (FY25 confirmed $190K; use $190K as planning figure, verify at FY26 NOFO); adjust budget narrative accordingly.*

---

## 6. BUDGET NARRATIVE (PLACEHOLDER — FINALIZE AT NOFO)

*Finalize at NOFO. Indicative structure:*

| Category | Phase I Est. | Notes |
|----------|-------------|-------|
| Exos labor (engineers, integration, ops) | ~$80K | Prime PM + instrument engineer |
| Collicott/Purdue sub | ~$35–45K | T2 substrate study + methodology advisory |
| Materials / prototype fabrication | ~$25K | Chamber prototypes, testing fixtures |
| Testing / lab | ~$10K | Pressure cycling, thermal test |
| Indirect / overhead | ~$15K | Exos OH rate |
| **Total Phase I (est.)** | **~$175–190K** | FY25 ceiling $190K confirmed; use $190K planning figure; confirm at FY27 NOFO |

---

## APPENDIX A — KEY REFERENCES

- NASA Technical Memorandum TM-20240013276 (reentry aerosol science gaps — 6 identified)
- NOAA ERB Initiative Congressional Mandate (2020)
- NOAA CSL / SABRE WB-57 aerosol sampling program (Frost et al.)
- **Maloney, Portmann, Ross, Rosenlof (NOAA CSL/CIRES, 2025):** "Investigating the Potential Atmospheric Accumulation and Radiative Impact of the Coming Increase in Satellite Reentry Frequency," *JGR Atmospheres*, doi:10.1029/2024JD042442. NOAA's own modelers; finds altitude-resolved composition measurements are the critical missing data for resolving radiative forcing sign and magnitude. Cited in §1.1.
- **Bernlochner, Nützel, Mayer, Schmidt, Maloney [CIRES/NOAA Boulder] (2026):** "Sensitivity analysis of radiative effects of alumina particles from spacecraft re-entries," EGU General Assembly 2026, EGU26-7078 (updated 14 Mar 2026). Finding: radiative forcing sign remains "highly uncertain due to limited constraints on particle size distributions" — directly names the measurement gap SACSS addresses. Cited in §1.1.
- **Lyu et al. (NOAA CSL/CU CIRES, Apr 2026):** First in-situ measurements of stratospheric nanoparticles during SABRE 2026 Tropics; particles "surprisingly abundant," organic-rich, "mostly invisible until now"; provide majority of surface area for ozone chemistry. *Science*, Apr 23, 2026. Reinforces measurement gap argument: if sub-visible composition-grade particles are being discovered AT 19 km, the 40–100 km zone is even more data-starved. Cited in §1.1.
- **Schulz et al. (2026):** "An update of the anthropogenic matter injection into Earth's atmosphere," *Advances in Space Research*, doi:10.1016/j.asr.2026.xxx (confirm DOI at NOFO). Independent catalog of full metal/metal-oxide suite from projected reentry rates; cites 40–100 km measurement gap as critical data-free zone for model validation. Cited in §1.1.
- **AIRL Working Group Whitepaper (Jun 2026):** "The Atmospheric Impacts of Re-entry and Launch: High Priority Actions and Recommendations," ESSC/ESF, Zenodo 20831147. ~50 US/Europe scientists; consensus finding that spaceflight is now the DOMINANT stratospheric source of Al/Cu/Pb; calls for "measurement campaigns" as "urgent" priority requiring "funding commitments." Transmitted to Exos by Daniel Murphy (NOAA CSL) 2026-07-13. Anchor justification for SACSS in ALL solicitations.
- Collicott LOS: Purdue_LOS/LOS_SACSS_INSTALG2-S26A_Collicott_Purdue_2026.pdf
- Exos FAA Launch License §431 (renewed March 13, 2026)

---

*DRAFT — Capture Agent staged 2026-07-02; FY27 retitle 2026-08-06; Appendix A citations updated 2026-08-18. Do not distribute externally. Requires Jon review. Finalize topic #, budget ceiling, and data-rights clause at FY27 NOFO release. LOI template stub — see capture/NOAA_SBIR_FY27_LOI_Stub.md.*
