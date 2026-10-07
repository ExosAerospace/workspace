#!/usr/bin/env python3
"""Build Exos RDRE Flight Demo Requirements Spec for MSFC / Teasley.
Run: PYTHONNOUSERSITE=1 python3.12 scripts/build_rdre_requirements_spec.py
Output: drafts/Exos_RDRE_Flight_Demo_Requirements_to_MSFC_DRAFT_2026-10-07.docx
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

LH  = "assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT = "drafts/Exos_RDRE_Flight_Demo_Requirements_to_MSFC_DRAFT_2026-10-07.docx"
NAVY = RGBColor(0x0A, 0x3D, 0x7C)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x55, 0x55, 0x55)
RED  = RGBColor(0xCC, 0x00, 0x00)
GOLD = RGBColor(0xB8, 0x86, 0x00)

doc = Document(LH)

def _set(run, size, color=DARK, bold=False, italic=False):
    run.font.size = Pt(size); run.font.color.rgb = color
    run.font.bold = bold; run.font.italic = italic; run.font.name = "Calibri"

def h1(t):
    p = doc.add_paragraph(); p.space_before = Pt(14); p.space_after = Pt(4)
    r = p.add_run(t); _set(r, 13, NAVY, bold=True); return p

def h2(t):
    p = doc.add_paragraph(); p.space_before = Pt(8); p.space_after = Pt(2)
    r = p.add_run(t); _set(r, 11, NAVY, bold=True); return p

def body(t, size=10.5):
    p = doc.add_paragraph(); p.space_after = Pt(5)
    r = p.add_run(t); _set(r, size, DARK)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; return p

def bullet(t, size=10.5, indent=0.25):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(indent); p.space_after = Pt(3)
    r = p.add_run("•  " + t); _set(r, size, DARK); return p

def tbd(label, desc, size=10.5, indent=0.25):
    """Item with [TBD-Phil] tag in GOLD."""
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(indent); p.space_after = Pt(3)
    r1 = p.add_run("•  "); _set(r1, size, DARK)
    r2 = p.add_run("[TBD-Phil] "); _set(r2, size, GOLD, bold=True)
    r3 = p.add_run(f"{label}: {desc}"); _set(r3, size, DARK)
    return p

def req(num, text, tbd_flag=False, size=10.5):
    p = doc.add_paragraph(); p.space_after = Pt(4)
    r1 = p.add_run(f"REQ-{num:03d}  "); _set(r1, size, NAVY, bold=True)
    if tbd_flag:
        r_tbd = p.add_run("[TBD-Phil] "); _set(r_tbd, size, GOLD, bold=True)
    r2 = p.add_run(text); _set(r2, size, DARK)
    return p

def note(t):
    p = doc.add_paragraph(); p.space_after = Pt(3)
    p.paragraph_format.left_indent = Inches(0.35)
    r = p.add_run("Note: " + t); _set(r, 9.5, GREY, italic=True); return p

def rule():
    p = doc.add_paragraph(); pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr'); bot = OxmlElement('w:bottom')
    bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'4')
    bot.set(qn('w:space'),'1'); bot.set(qn('w:color'),'0A3D7C')
    pbdr.append(bot); pPr.append(pbdr); return p

def warn_header():
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.space_after = Pt(2)
    r = p.add_run("⚠  DRAFT — NOT FOR RELEASE — Pending Jon Quinn Approval  ⚠")
    _set(r, 11, RED, bold=True); return p

# ─── HEADER ──────────────────────────────────────────────────────────────────
doc.add_paragraph()
warn_header()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("RDRE FLIGHT DEMONSTRATION — DRAFT REQUIREMENTS SPECIFICATION")
_set(r, 16, NAVY, bold=True); p.space_after = Pt(2)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Submitted by Exos Aerospace to NASA MSFC / Thomas Teasley")
_set(r, 11, GREY, italic=True); p.space_after = Pt(1)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Draft Date: October 7, 2026  |  Version: DRAFT v0.1")
_set(r, 10.5, DARK); p.space_after = Pt(1)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("POC: John Quinn, Cofounder & CEO  |  jquinn@exosaero.com")
_set(r, 10.5, DARK); p.space_after = Pt(4)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Proprietary — Unclassified. Items marked [TBD-Phil] require confirmation from Phil Gard / Neil before release.")
_set(r, 9, GREY, italic=True)

rule()

# ─── 1. OBJECTIVE ────────────────────────────────────────────────────────────
h1("1. Objective")
body("Exos Aerospace seeks to perform an in-flight demonstration of an RDRE engine on a BLK3-class "
     "suborbital rocket. The primary objectives are: (a) generate the first in-flight RDRE performance "
     "data set (ISP, combustion stability, heat signature) under real flight conditions; (b) characterize "
     "in-flight loads and vibration environment at the engine–vehicle interface to define isolation and "
     "damping requirements for future flight systems; and (c) operate the engine exclusively within the "
     "test-stand-demonstrated performance envelope established by NASA MSFC's INROADS program.")
body("The vehicle profile is: ground-level hover, then flight. Exos does not seek to operate the engine "
     "outside any regime previously demonstrated on the MSFC test stand. All flight data gathered would "
     "be made available to NASA under the agreed Space Act Agreement.")
rule()

# ─── 2. PROPELLANT ───────────────────────────────────────────────────────────
h1("2. Propellant")
tbd("Propellant selection", "LOX/CH4 or LOX/Ethanol — TBD. Tank sizing is approximately 1:1 between these two propellants, so either is viable from a vehicle standpoint. Exos requests Teasley's recommendation on which is better suited to the existing INROADS hardware.")
note("LOX/ethanol and LOX/methane show near-equivalent performance on the INROADS thrust chamber per Teasley 10/6 discussion.")
rule()

# ─── 3. PERFORMANCE ──────────────────────────────────────────────────────────
h1("3. Performance Requirements")

h2("3.1 Thrust")
req(1, "Minimum required sea-level thrust: 5,000 lbf at the engine / vehicle interface.", False)
req(2, "Target sea-level thrust: ~6,000 lbf. Higher thrust is acceptable if achievable within the "
       "inlet-pressure constraints in Section 4.", False)
tbd("Thrust confirmation", "confirm minimum acceptable thrust for the BLK3-class vehicle mission profile (hover then flight to target altitude).", size=10.5)

h2("3.2 Mass Flow")
req(3, "Target mass flow: approximately 20–25 lb/s.", True)
tbd("Mass flow", "confirm design point mass flow (lb/s total, oxidizer-to-fuel ratio) and acceptable range.", size=10.5)

h2("3.3 Burn Duration")
req(4, "Required burn duration: minimum 85 seconds (continuous), encompassing hover phase and flight ascent. "
       "Engine must survive the full duration without performance excursions outside tested ranges.")

h2("3.4 Throttle")
req(5, "Throttle range: 50–100% of rated thrust minimum. Exos would use throttle during hover phase.")
note("MSFC baseline supports 50% throttle; possibly 40% — not yet confirmed below 50%.")
tbd("Minimum throttle", "confirm whether 40% throttle is available for hover-phase control authority.", size=10.5)

h2("3.5 Specific Impulse")
req(6, "Target Isp: ≥250 s sea level (vacuum Isp not required for this demonstration).", True)
tbd("Isp confirmation", "verify Isp at the agreed design-point Pc and mass flow.", size=10.5)

h2("3.6 Efficiency")
req(7, "Combustion efficiency: ≥90% acceptable; ≥98% preferred (achievable per MSFC data at ≥700 psi Pc).")
rule()

# ─── 4. INLET PRESSURE ───────────────────────────────────────────────────────
h1("4. Inlet Pressure Envelope")
body("Exos manufactures its own carbon fiber propellant tanks and can accommodate the following "
     "inlet-pressure options. Exos requests Teasley's guidance on which option best matches the "
     "available INROADS hardware or a proposed retrofit:")

h2("Option A — 750 psi inlet")
bullet("Exos preferred from a vehicle-weight standpoint.")
bullet("Requires outer-body redesign and remanufacture per Teasley's assessment; reduces Pc to ~300+ psi.")
bullet("Exos accepts this trade if MSFC can perform the outer-body retrofit within the program schedule.")

h2("Option B — 1,000 psi inlet")
bullet("MSFC baseline inlet condition for existing INROADS hardware (no outer-body change needed).")
bullet("Exos can manufacture tanks to 1,000 psi; weight penalty is manageable.")
bullet("Exos preferred if Option A retrofit adds schedule risk.")

h2("Option C — 1,200 psi inlet")
bullet("Supports ~25 lb/s mass flow for ~6,000 lbf SL thrust.")
bullet("Exos can manufacture tanks to 1,200 psi.")
bullet("Likely approaches pump augmentation territory; Exos will evaluate electric pump addition.")

note("Exos is exploring electric pump augmentation to bridge the 750 psi supply to a higher inlet pressure "
     "if required. Exos is NOT currently planning a turbopump system for this vehicle size.")
tbd("Inlet pressure selection", "confirm final option (A/B/C) with Phil and Neil after reviewing vehicle mass budget.", size=10.5)
rule()

# ─── 5. HARDWARE OPTIONS ─────────────────────────────────────────────────────
h1("5. Hardware Options (for Teasley / MSFC Consideration)")
body("Exos proposes discussion of the following hardware paths. MSFC and Teasley to advise on feasibility "
     "and relative schedule/cost confidence:")

h2("Option A — Existing As-Is Hardware")
bullet("Use currently available non-flight-weight MSFC hardware.")
bullet("No performance or duration guarantee. Best for early hover data; not baselined for 85 s burn.")
bullet("Fastest to vehicle integration; acceptable if Exos accepts data uncertainty.")

h2("Option B — Outer-Body Retrofit")
bullet("Retain existing inner body/injectors; redesign and remanufacture outer body to match "
       "Exos 750 psi inlet condition.")
bullet("Reduces chamber pressure; requires MSFC engineering effort.")
tbd("Option B schedule", "Teasley to provide estimate after seeing firm requirements.", size=10.5)

h2("Option C — Post-1B/1C Series Hardware")
bullet("Higher-confidence hardware available after INROADS 1B (≈Mar–May 2027) and 1C test series.")
bullet("Estimated availability: end of 2027.")
bullet("Preferred path for an 85 s burn if timeline allows.")

h2("Option D — License Current Design + Exos Build")
bullet("Exos licenses the INROADS design from NASA Tech Transfer; builds hardware in-house with DNC machining and contracted additive printing.")
bullet("Teasley coaches Exos engineering through manufacturing and post-processing.")
bullet("Estimated timeline: ~2 years to first test article (Exos-owned design).")
bullet("Exos to initiate NASA Tech Transfer contact separately from the Space Act Agreement.")
note("Options A and B are near-term; C is preferred for flight confidence; D is the long-term Exos IP path.")
rule()

# ─── 6. DATA RETURN ───────────────────────────────────────────────────────────
h1("6. Data Exos Will Return to NASA")
body("Exos proposes to share the following in-flight data with NASA MSFC as part of the Space Act Agreement, "
     "adding to the INROADS data set in ways not achievable from ground testing:")
bullet("In-flight loads and vibration profile at engine–vehicle interface (accelerometry, multiple axes, full burn duration).")
bullet("In-flight ISP data package: thrust vs. time, oxidizer + fuel mass flow vs. time, mixture ratio, chamber pressure, throat and expansion ratio, ambient P/T, burn duration.")
bullet("Hover-phase stability data: throttle response, engine behavior during vertical profile.")
bullet("Post-flight hardware inspection and any anomaly report.")
note("Data return specifics to be defined in the SAA. Exos will make all in-flight data available to MSFC.")
rule()

# ─── 7. INTERFACES ────────────────────────────────────────────────────────────
h1("7. Vehicle Interface Requirements")
tbd("Engine mass (dry)", "provide with hardware option selected.", size=10.5)
tbd("Engine envelope (diameter × length)", "provide with hardware option selected.", size=10.5)
bullet("Mounting: Exos provides structural interface; requires MSFC bolt-pattern and load spec.")
tbd("Propellant inlet fittings / port sizes", "confirm with hardware option selected.", size=10.5)
bullet("Ignition system: Exos to confirm ignition power/pyro requirements.")
bullet("Electrical/harness: Exos provides power and signal harness to engine; requires connector/pinout spec.")
tbd("Heat load / thermal interface", "confirm max engine surface temperature during 85 s burn.", size=10.5)
note("Exos has flown an active NASA vibration damper previously and has experience routing vibration-isolation hardware. Exos expects to design an isolator system once loads data book is available.")
rule()

# ─── 8. SCHEDULE & BUDGET ─────────────────────────────────────────────────────
h1("8. Schedule & Budget (Indicative — TBD)")
tbd("Program budget", "Exos is targeting a ~$10M program envelope for BLK3-class RDRE demo. Breakdown TBD pending hardware option selection and SAA scope.", size=10.5)
tbd("Target flight date", "depends on hardware option (A/B: potentially 2026–2027; C: end-2027; D: ~2028). Phil and Neil to advise.", size=10.5)
bullet("Exos manufactures vehicle hardware (CF tanks, structure, GNC, flight systems) in-house; key long-lead is engine hardware.")
bullet("Exos has CNC machining in-house; will contract additive manufacturing for RDRE components if Option D selected.")
rule()

# ─── 9. AGREEMENT STRUCTURE ───────────────────────────────────────────────────
h1("9. Proposed Agreement Structure")
body("Exos proposes the following phased Space Act Agreement structure based on the 10/6 discussion:")
bullet("Umbrella Reimbursable Space Act Agreement — master vehicle with annexes for each phase.")
bullet("Annex 1: Paid Consultation — Exos reimburses NASA MSFC for Teasley's time to: review and refine "
       "this requirements document; advise on hardware options; support design reviews.")
bullet("Annex 2 (pending): Hardware delivery / retrofit scope — defined after requirements are finalized and "
       "Chris Hill approves.")
bullet("Annex 3 (pending): Data sharing / publication rights — in-flight data made available to MSFC; "
       "any publications co-credited per NASA policy.")
note("Exos must separately contact NASA Tech Transfer for any IP license under Option D. This SAA does not "
     "confer an IP license — that is a parallel process.")
rule()

# ─── SIGNATURE BLOCK ──────────────────────────────────────────────────────────
h1("Submitted by")
doc.add_paragraph()
for line, bold in [
    ("John Quinn", True),
    ("Cofounder & CEO, Exos Aerospace Systems & Technologies, Inc.", False),
    ("299 FM 1903, Greenville, TX 75402", False),
    ("jquinn@exosaero.com  |  (430) 966-4005  |  www.exosaero.com", False),
]:
    p = doc.add_paragraph()
    r = p.add_run(line); _set(r, 10.5, DARK, bold=bold); p.space_after = Pt(1)

doc.add_paragraph()
warn_header()

doc.save(OUT)
print(f"Saved: {OUT}")
