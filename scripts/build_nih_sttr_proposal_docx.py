# DEPRECATED 2026-09-03: generates LIVER/Collicott-era content. DO NOT RE-RUN for submission.
# Active Research Plan is Park intestinal: drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_PURDUE_Park_2026-09-03.docx
#!/usr/bin/env python3
"""NIH STTR (PA-27-102) Phase I proposal write-up — actual research-plan narrative,
aligned to NIH SBIR/STTR forms (Specific Aims 1pg, Research Strategy 6pg:
Significance/Innovation/Approach, Abstract 30 lines, Narrative 3 sentences).

Team (finalized 2026-08-26): Exos Aerospace = SBC (>=40%) - BLK3 suborbital platform;
Univ. of Washington / Dr. Edward Kelly = Research Institution of record (>=30%) - kidney MPS science;
Purdue (Collicott/Park) = subaward (<=30%) - suborbital experiment methods.
"""
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = "drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_DRAFT_2026-08-26.docx"
NAVY = RGBColor(0x0A, 0x3D, 0x7C)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x55, 0x55, 0x55)

d = Document()
for s in d.sections:
    s.top_margin = s.bottom_margin = Pt(54)
    s.left_margin = s.right_margin = Pt(60)


def para(text="", *, bold=False, italic=False, size=10.5, color=DARK,
         align=WD_ALIGN_PARAGRAPH.LEFT, after=6, before=0):
    p = d.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    if text:
        r = p.add_run(text)
        r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
        r.font.color.rgb = color; r.font.name = "Calibri"
    return p


def h1(text):
    return para(text, bold=True, size=13.5, color=NAVY, before=14, after=5)


def h2(text):
    return para(text, bold=True, size=11.5, color=NAVY, before=9, after=3)


def runline(pairs, after=6, size=10.5):
    """pairs = list of (text, bold) rendered inline in one paragraph."""
    p = d.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    for text, bold in pairs:
        r = p.add_run(text)
        r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = DARK; r.font.name = "Calibri"
    return p


def bullet(text, lead=None):
    p = d.add_paragraph()
    p.paragraph_format.left_indent = Pt(16)
    p.paragraph_format.space_after = Pt(3)
    if lead:
        r = p.add_run("•  " + lead + " ")
        r.font.size = Pt(10.5); r.font.bold = True; r.font.color.rgb = DARK; r.font.name = "Calibri"
        r2 = p.add_run(text)
        r2.font.size = Pt(10.5); r2.font.color.rgb = DARK; r2.font.name = "Calibri"
    else:
        r = p.add_run("•  " + text)
        r.font.size = Pt(10.5); r.font.color.rgb = DARK; r.font.name = "Calibri"
    return p


def rule():
    para("—" * 46, size=8, color=GREY, after=6, before=2)


# ============================================================ COVER / META
para("EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC.", bold=True, size=13, color=NAVY, after=1)
para("NIH STTR Phase I — Research Plan Narrative (DRAFT for internal review)", bold=True, size=12, after=1)
para("A Reusable Suborbital Microgravity Platform for Onset-Kinetics Screening of Kidney "
     "Microphysiological Systems Before ISS Commitment", italic=True, size=11, color=DARK, after=6)
runline([("Funding opportunity: ", True), ("PA-27-102 (Omnibus STTR, R41/R42) — due September 8, 2026.   ", False),
         ("Awarding component (proposed): ", True), ("NIBIB primary / NIA secondary.", False)], after=2)
runline([("Small Business Concern (PD/PI or co-PI): ", True),
         ("Exos Aerospace, Greenville, TX.   ", False),
         ("Research Institution of record: ", True),
         ("University of Washington (Dr. Edward J. Kelly).   ", False)], after=2)
runline([("Subaward institution: ", True),
         ("Purdue University (Prof. Steven Collicott / Weldon BME).   ", False),
         ("Prepared: ", True), ("2026-08-26.   ", False),
         ("Status: ", True), ("DRAFT — not for external release.", False)], after=4)
para("This document is the actual NIH research-plan narrative (Aims + Research Strategy), written to the "
     "NIH SBIR/STTR forms structure and page limits — it is the proposal itself, distinct from the "
     "outreach/intro correspondence already sent to the partners.", italic=True, size=9.5, color=GREY, after=4)
rule()

# ============================================================ 40/30/30 SNAPSHOT
h2("STTR compliance snapshot (statutory work split)")
bullet("Exos Aerospace (SBC) — platform, payload module, integration, flight operations, recovery.", lead="≥40%:")
bullet("University of Washington / Kelly lab (single partnering Research Institution of record) — kidney "
       "MPS science, assay design, onset-kinetics analysis.", lead="≥30%:")
bullet("Purdue University subaward (Collicott, AAE) — suborbital experiment design / reduced-gravity fluid "
       "methods; optional Weldon BME organ-chip co-investigator (Park).", lead="≤30% (subaward):")
para("PD/PI to be confirmed (STTR permits the PI at either the SBC or the RI). Kelly's NIH/ISS record supports "
     "either an RI-based PI with an Exos co-PI, or an Exos-based PI with Kelly as co-PI. Multi-PI (MPI) leadership "
     "plan recommended.", size=9.5, color=GREY, after=6)
rule()

# ============================================================ PROJECT NARRATIVE
h1("Project Narrative (public relevance — three sentences)")
para("Microphysiological systems (“organ chips”) that model the human kidney are increasingly used to predict "
     "drug toxicity and disease, and evidence shows microgravity alters their transport and barrier function in ways "
     "relevant to both spaceflight health and ground disease modeling. Sending these chips to the International Space "
     "Station is slow and costly, and late hardware failures waste scarce research dollars. This project develops and "
     "validates a low-cost, reusable suborbital flight platform that lets investigators screen and de-risk kidney chip "
     "experiments — capturing the first seconds-to-minutes of the microgravity response — before committing to an "
     "orbital campaign.")

# ============================================================ ABSTRACT
h1("Project Summary / Abstract (≤30 lines)")
para("Microphysiological systems (MPS), or organ-on-chip devices, are now central to NIH's mission to improve the "
     "predictivity of preclinical models. The NCATS/NIBIB Tissue Chips in Space program demonstrated that microgravity "
     "meaningfully perturbs MPS behavior — including renal transporter expression and epithelial barrier function — "
     "yet access to microgravity remains dominated by the International Space Station (ISS), where multi-year timelines, "
     "high cost, and launch/transit delays make it impractical to screen hardware or to isolate the earliest phase of "
     "the microgravity response. There is no rapid, recoverable, low-cost platform to de-risk an MPS payload before an "
     "ISS commitment. This STTR pairs Exos Aerospace — operator of BLK3, one of only three FAA-licensed reusable "
     "suborbital launch vehicles in the United States and a platform with peer-reviewed suborbital life-science heritage "
     "(living human glioblastoma stem cells; npj Microgravity 2023;9:92) — with the kidney-MPS laboratory of Dr. Edward "
     "Kelly at the University of Washington, an ISS Tissue Chips veteran and NCATS TraCe MPS kidney-center investigator, "
     "with a Purdue University subaward for suborbital experiment methods. We will (Aim 1) design and flight-qualify a "
     "standardized, environmentally controlled, recoverable BLK3 payload module for perfused kidney MPS with automated "
     "fixation at defined timepoints; (Aim 2) characterize the onset kinetics of the proximal-tubule MPS response across "
     "the first ~3–4 minutes of microgravity — drug-transporter function, barrier integrity, and mechanotransduction "
     "markers — producing a dataset not obtainable on ISS; and (Aim 3) validate the end-to-end suborbital screening "
     "pipeline and define a quantitative go/no-go framework for de-risking a subsequent ISS flight. The deliverable is a "
     "validated, reusable screening platform and a first onset-kinetics dataset that lower the cost and risk of orbital "
     "MPS science. Phase II expands to a multi-flight campaign and a standing screening service for NIH-funded MPS "
     "investigators, with a clear commercialization path in Exos's payload-services business.")

# ============================================================ SPECIFIC AIMS
h1("Specific Aims (1 page)")
para("Microphysiological systems now underpin NIH efforts to replace poorly predictive animal models, and the "
     "NCATS/NIBIB Tissue Chips in Space program established that microgravity alters kidney-MPS transport and barrier "
     "function. But the only routinely used microgravity environment for this work is the ISS: a platform whose cost, "
     "multi-year cadence, and launch/transit lag make it impossible to cheaply screen hardware, and impossible to isolate "
     "the earliest seconds-to-minutes of the microgravity (µg) response — the onset window where gravisensing and "
     "fluid-shift signaling initiate. Investigators therefore fly expensive orbital payloads with un-screened hardware and "
     "no onset-kinetics baseline, and absorb late-stage failures.")
para("We propose to close this gap with a reusable suborbital screening platform. Exos Aerospace operates BLK3, an "
     "FAA-licensed reusable suborbital vehicle that delivers ~3–4 minutes of recoverable microgravity with full payload "
     "return and rapid turnaround — at a fraction of ISS cost and lead time. Teamed with the UW kidney-MPS laboratory of "
     "Dr. Edward Kelly (ISS Tissue Chips veteran; NCATS TraCe MPS kidney center) and a Purdue suborbital-methods subaward, "
     "we will build and validate the platform and generate the first quantitative kidney-MPS onset-kinetics dataset. "
     "Our central hypothesis is that suborbital µg reproducibly and measurably perturbs proximal-tubule MPS transport "
     "and barrier function within the flight window, and that these early responses predict outcomes relevant to a "
     "subsequent ISS campaign — making suborbital flight a valid, low-cost screen. We will pursue three aims:")
h2("Aim 1 — Design and flight-qualify a recoverable kidney-MPS payload module for BLK3. (Exos lead)")
para("Develop a standardized payload module providing perfusion, thermal control, and gas exchange for a perfused "
     "proximal-tubule MPS, with automated chemical fixation/quench at defined timepoints and intact recovery. "
     "Milestone: module passes vibration, thermal, and recovery qualification; interface control document (ICD) frozen; "
     "cell viability in a flight-representative ground profile ≥ that of static 1g controls.", after=4)
h2("Aim 2 — Characterize onset kinetics of the proximal-tubule MPS response to microgravity. (UW/Kelly lead)")
para("Fly the Kelly-lab kidney MPS on BLK3 and quench at staged µg timepoints (e.g., ~0, 60, 240 s) plus ground and "
     "1g-in-flight (centrifuge or matched-hardware) controls. Endpoints: drug-transporter function (e.g., OAT1/OAT3 uptake, "
     "P-gp/efflux), tight-junction/barrier integrity, cytoskeletal and mechanotransduction markers, and viability. "
     "Milestone: a statistically powered onset-kinetics dataset distinguishing µg-onset from 1g, unobtainable on ISS.", after=4)
h2("Aim 3 — Validate the end-to-end screening pipeline and a de-risk-for-ISS decision framework. (Joint; Purdue methods)")
para("Establish and document the prep → integrate → fly → recover → assay pipeline with defined turnaround, and derive "
     "a quantitative go/no-go framework that maps suborbital onset metrics to ISS-campaign readiness. Purdue (Collicott) "
     "provides suborbital experiment design and reduced-gravity fluid-mechanics validation. Milestone: reproducible "
     "pipeline across ≥2 flights and a validated scoring rubric adopted into the Phase II service concept.", after=4)
para("Impact: a validated, reusable, low-cost microgravity screen and a first kidney-MPS onset-kinetics dataset that "
     "reduce the cost and risk of NIH orbital MPS science and seed a self-sustaining suborbital screening service.",
     italic=True, size=10, color=GREY)

# ============================================================ RESEARCH STRATEGY
h1("Research Strategy (≤6 pages)")

h2("A. Significance")
para("The problem. NIH has invested heavily in microphysiological systems to improve preclinical predictivity, and the "
     "NCATS/NIBIB Tissue Chips in Space program (a NCATS + NIBIB partnership) showed that microgravity is a uniquely "
     "revealing stressor for these systems — renal MPS flown to ISS displayed altered transporter expression and "
     "epithelial phenotype relevant both to astronaut health and to ground disease and aging models. That program also "
     "exposed the bottleneck: microgravity access for MPS is effectively synonymous with the ISS. An ISS MPS experiment "
     "carries multi-year lead times, six- to seven-figure cost, constrained crew time, and launch/transit delays that both "
     "gate throughput and blur the earliest phase of the biological response. Two consequences follow. First, investigators "
     "fly un-screened hardware: a fluidic seal, bubble-management, or viability failure discovered on orbit is enormously "
     "expensive. Second, the onset window — the first seconds to minutes in which gravisensing, cytoskeletal remodeling, "
     "and fluid-shift signaling initiate — is essentially unobservable on ISS, because payloads reach microgravity hours "
     "of handling and a launch profile removed from the cells' first exposure.")
para("Why suborbital, and why now. A reusable suborbital vehicle delivers a clean ~3–4 minute microgravity plateau with "
     "the payload in the investigator's hands within hours — recovered intact for immediate assay. This is the natural "
     "instrument for two things ISS cannot cheaply provide: (1) low-cost, rapid-turnaround screening to de-risk hardware "
     "and protocols before an orbital commitment, and (2) direct capture of onset kinetics. Suborbital flight does not "
     "replace sustained-µg ISS science; it screens and de-risks before it, and it interrogates a time window ISS obscures. "
     "The NIH SBIR/STTR program was reauthorized in April 2026; microgravity is investigator-initiated (not a named topic), "
     "and a device/platform framing fits NIBIB, which co-funded the Tissue Chips in Space program and already holds "
     "microgravity MPS in its portfolio (NIA secondary for µg-accelerated-aging angles).")
para("Significance of success. A validated suborbital screen would let every NIH-funded MPS group test hardware and "
     "protocol before spending orbital dollars — “screen on BLK3, fly the winners to ISS” — and would create the first "
     "systematic onset-kinetics datasets for renal (and, in Phase II, other) MPS. Kidney MPS is the right beachhead: renal "
     "proximal-tubule transport is central to drug clearance and nephrotoxicity, it is one of the most mature MPS domains, "
     "and the UW Kelly laboratory has already flown kidney chips to ISS and runs an NCATS TraCe MPS kidney center — the "
     "science, the assays, and the ISS reference points already exist.")

h2("B. Innovation")
bullet("A purpose-built, recoverable suborbital MPS platform. We convert a reusable launch vehicle into a standardized, "
       "environmentally controlled, quick-turn research instrument for perfused organ chips — not a one-off payload.",
       lead="Platform:")
bullet("Onset-kinetics as a first-class measurement. Automated in-flight fixation at staged µg timepoints isolates the "
       "0–240 s response window that ISS cannot resolve, turning a limitation of short-duration flight into the core "
       "scientific product.", lead="Measurement:")
bullet("A screen-before-ISS decision framework. We define quantitative go/no-go metrics linking cheap suborbital data to "
       "orbital-campaign readiness — a reusable methodology, not just a dataset.", lead="Method:")
bullet("A commercial reuse model. Because BLK3 is reusable with rapid turnaround, the same qualified module supports a "
       "recurring, low-cost screening service for the broader NIH MPS community, giving the platform a self-sustaining "
       "commercialization path beyond the award.", lead="Economics:")
para("Distinct from prior art: existing microgravity-MPS work is ISS/orbital and captures chronic exposure; parabolic "
     "flight offers only ~20–second, non-recoverable, repeated transients. Neither delivers a single clean multi-minute "
     "µg plateau with intact recovery and staged fixation. That combination is the novelty. Notably, the Kelly lab's own "
     "sustained-µg PT-MPS flights to ISS (Lidberg et al., npj Microgravity 2024) found no significant alteration in "
     "proximal-tubule vitamin-D metabolism or a unique response to human serum under chronic exposure — leaving the acute "
     "onset window (the first seconds to minutes, obscured by ISS transit time) as an open question their own published "
     "ISS dataset cannot answer and this proposal is purpose-built to test.")

h2("C. Approach")
para("Team and roles. Exos Aerospace (SBC, ≥40%) owns the vehicle, the payload module, integration, flight operations, "
     "and recovery, and contributes peer-reviewed suborbital life-science heritage. The University of Washington Kelly "
     "laboratory (Research Institution of record, ≥30%) owns the kidney-MPS biology, assays, controls, and onset-kinetics "
     "analysis; Dr. Kelly's ISS Tissue Chips flights and NCATS TraCe MPS kidney center supply validated hardware and "
     "orbital reference data. A Purdue University subaward (≤30%; Prof. Collicott, AAE) contributes suborbital experiment "
     "design and reduced-gravity fluid-mechanics methods, with an optional Weldon BME organ-chip co-investigator (Park) to "
     "deepen the bio bench. All µg durations, g-levels, and viability claims below are design targets to be verified in "
     "Aim 1, not demonstrated results.")

para("Aim 1 — Payload module design and flight qualification (Exos lead; months 1–6).", bold=True, after=2)
bullet("Design a self-contained module providing closed-loop perfusion, thermal control (37°C), and gas exchange sized to "
       "the Kelly-lab MPS cartridge, with automated reagent actuation for fixation/quench at commanded timepoints and a "
       "sealed, recoverable containment consistent with FAA payload safety and biosafety handling.")
bullet("Freeze an interface control document (ICD) with UW (fluidics, power, data, thermal, biosafety) and define the "
       "recovery-to-assay chain (target payload-in-hand within hours of landing).")
bullet("Qualify against a flight-representative environment — boost/ascent loads and transient shock, thermal, and "
       "recovery — using Exos ground facilities (Greenville: manufacturing, test, and tethered-hover only; no launch on "
       "site). Verify cell viability in a ground flight-profile run relative to static 1g controls before committing cells "
       "to flight.")
runline([("Milestone / go-no-go (M6): ", True),
         ("qualified module + frozen ICD + viability parity in ground profile. Failure here re-scopes Aim 2 timepoints "
          "or module before any flight cell use.", False)], after=6, size=10)

para("Aim 2 — Onset-kinetics characterization (UW/Kelly lead; months 4–11).", bold=True, after=2)
bullet("Fly the perfused proximal-tubule MPS on BLK3 and command fixation at staged µg timepoints (e.g., ~0, 60, 240 s), "
       "with matched ground controls and an in-flight/hardware-matched 1g reference to separate µg effects from launch, "
       "vibration, and handling.")
bullet("Assay panel (Kelly lab): active drug-transporter function (e.g., OAT1/OAT3-mediated uptake; P-gp/efflux), "
       "tight-junction and barrier integrity, cytoskeletal / mechanotransduction and gravisensing markers, proteinuria, "
       "and vitamin-D bioactivation (25(OH)D3 → 1,25(OH)2D3), directly benchmarked against the lab's own two ISS PT-MPS "
       "flights (CRS-17: vitamin D metabolism / proteinuric response; CRS-22: calcium-oxalate microcrystal nephrolithiasis "
       "model) and their published sustained-exposure result set.")
bullet("Power/replication: define n per timepoint from the Kelly lab's ISS/ground effect-size history for the primary "
       "transporter and vitamin-D endpoints (their CRS-17/CRS-22 datasets provide the baseline variance estimates) to "
       "detect a pre-specified change across ≥2 flights; pre-register endpoints and analysis.")
runline([("Milestone (M11): ", True),
         ("a statistically powered onset-kinetics dataset that distinguishes µg-onset responses from 1g controls and "
          "resolves dynamics ISS cannot capture.", False)], after=6, size=10)

para("Aim 3 — Pipeline validation and de-risk-for-ISS framework (joint; Purdue methods; months 6–12).", bold=True, after=2)
bullet("Document the full prep → integrate → fly → recover → assay pipeline with measured turnaround and reproducibility "
       "across the flights; Purdue (Collicott) leads suborbital experiment-design and reduced-gravity fluid-mechanics "
       "validation of the perfusion/quench behavior.")
bullet("Derive a quantitative go/no-go rubric mapping suborbital onset metrics to ISS-campaign readiness (which failure "
       "modes suborbital screening catches; which endpoints predict orbital outcomes).")
runline([("Milestone (M12): ", True),
         ("reproducible pipeline across ≥2 flights + validated scoring rubric carried into the Phase II service concept.",
          False)], after=6, size=10)

h2("Compliance, risk, and feasibility")
bullet("BLK3 is FAA-licensed but has not yet flown commercially; the March 2027 flight provides a concrete near-term "
       "target, and Aim 1 qualification precedes any cell flight. Schedule risk is mitigated by decoupling module "
       "qualification (Aim 1) from the specific flight date and by planning ≥2 flights.", lead="Vehicle:")
bullet("Human specimens / cell lines only (established human and iPSC-derived renal cells); no vertebrate animals and no "
       "human-subjects interaction anticipated — documented under the appropriate exemptions with authentication of key "
       "biological resources.", lead="Bio:")
bullet("Sealed, recoverable containment; standard MPS biosafety; no select agents.", lead="Safety:")
bullet("If µg-onset signals are small, the powered multi-flight design and pre-registered primary endpoint preserve "
       "interpretability; a null onset result is itself a fundable screening finding (defines what suborbital can and "
       "cannot resolve).", lead="Scientific:")

h2("Phase I deliverables and path to Phase II / commercialization")
bullet("Flight-qualified, recoverable kidney-MPS payload module + frozen ICD (reusable across investigators).")
bullet("First quantitative kidney-MPS onset-kinetics dataset and a validated de-risk-for-ISS scoring framework.")
bullet("Phase II: multi-flight campaign; extend the module to additional MPS (cardiac, hepatic, barrier tissues); stand up "
       "a recurring suborbital screening service for NCATS TraCe MPS / Tissue-Chips and NASA-funded groups. Commercialization "
       "rides Exos's existing payload-services business (recoverable capacity, published per-flight pricing), giving a "
       "credible non-dilutive-to-revenue transition.")

h2("Budget and period (Phase I)")
para("~12 months. Total costs consistent with the NIH SBIR/STTR Phase I guideline, allocated to the statutory STTR split: "
     "Exos (SBC) ≥40%, UW (RI of record) ≥30%, Purdue subaward ≤30%. Detailed budget and justification to be built to the "
     "final guideline amount during routing; UW OSP (~5–7 business days) and Purdue SPS (~5 business days) internal routing "
     "govern the true submission-ready date ahead of the September 8 deadline.", size=10)

rule()
h2("What still must be locked before submission (not part of the narrative, but gates it)")
bullet("Confirm PD/PI vs. co-PI (MPI leadership plan) and NIBIB program-officer pre-submission concurrence (SEED office).")
bullet("Kelly to open UW OSP routing and Collicott to open Purdue subaward routing now; the later office governs.")
bullet("Exos org-level eRA Commons registration APPROVAL (submitted 2026-08-26, pending NIH) — the last plumbing gate.")
bullet("Kelly-lab MPS specifics (cell source, exact transporter/barrier assays, effect sizes) drop into Aim 2 to finalize "
       "power and endpoints.")

para("Prepared by Exo for John Quinn, Exos Aerospace. DRAFT — internal review only; not for external release. "
     "Sources: capture/NIH_Microgravity_pursuit.md; NIH SBIR/STTR forms (Specific Aims 1 pg / Research Strategy 6 pg; "
     "Abstract 30 lines; Narrative 3 sentences); npj Microgravity 2023;9:92.",
     italic=True, size=8.5, color=GREY, before=8)

d.save(OUT)
print("WROTE", OUT)
