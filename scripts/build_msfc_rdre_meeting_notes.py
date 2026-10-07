#!/usr/bin/env python3
"""Build internal meeting notes for NASA MSFC RDRE meeting 2026-10-06.
Run: PYTHONNOUSERSITE=1 python3.12 scripts/build_msfc_rdre_meeting_notes.py
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

LH  = "assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT = "drafts/Exos_MSFC_RDRE_Meeting_Notes_2026-10-06.docx"
NAVY = RGBColor(0x0A, 0x3D, 0x7C)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
GREY = RGBColor(0x55, 0x55, 0x55)
RED  = RGBColor(0xCC, 0x00, 0x00)

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

def body(t, size=10.5, color=DARK):
    p = doc.add_paragraph(); p.space_after = Pt(4)
    r = p.add_run(t); _set(r, size, color)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY; return p

def bullet(t, size=10.5, indent=0.25, color=DARK):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(indent); p.space_after = Pt(2)
    r = p.add_run("•  " + t); _set(r, size, color); return p

def note(t):
    p = doc.add_paragraph(); p.space_after = Pt(3)
    p.paragraph_format.left_indent = Inches(0.35)
    r = p.add_run(t); _set(r, 9.5, GREY, italic=True); return p

def kv(label, val, size=10.5):
    p = doc.add_paragraph(); p.space_after = Pt(2)
    r1 = p.add_run(label + ": "); _set(r1, size, DARK, bold=True)
    r2 = p.add_run(val);          _set(r2, size, DARK); return p

def rule():
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    p = doc.add_paragraph(); pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement('w:pBdr'); bot = OxmlElement('w:bottom')
    bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'4')
    bot.set(qn('w:space'),'1'); bot.set(qn('w:color'),'0A3D7C')
    pbdr.append(bot); pPr.append(pbdr); return p

def warn(t):
    p = doc.add_paragraph(); p.space_after = Pt(4)
    p.paragraph_format.left_indent = Inches(0.2)
    r = p.add_run("⚠ INTERNAL ONLY — " + t); _set(r, 9.5, RED, bold=True); return p

# ── HEADER ─────────────────────────────────────────────────────────────────
doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("MEETING NOTES — NASA MSFC RDRE TECHNICAL DISCUSSION")
_set(r, 16, NAVY, bold=True); p.space_after = Pt(2)

p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("October 6, 2026  |  1:00 PM CDT  |  Virtual")
_set(r, 11, GREY, italic=True); p.space_after = Pt(2)

warn("For Exos internal use only. Do not distribute outside Exos without Jon Quinn approval.")
rule()

# ── ATTENDEES ───────────────────────────────────────────────────────────────
h1("1. Attendees")

h2("NASA MSFC")
bullet("Tom Teasley — RDRE Technical Lead, INROADS program, ER13 (combustion devices)")
bullet("Seth Bell — Industry & Commercial Partnerships Manager (also covers OGA / Other Government Agencies)")
bullet("Mike — Partnerships (surname unknown; Seth's colleague in the partnerships office)")
bullet("Chris Hill — Project Manager / Approver for INROADS (not on the call; must approve any SAA)")

h2("Exos Aerospace")
bullet("Jon Quinn — Cofounder & CEO")
bullet("Phil Gard — Chief Engineer (joined call late, via phone)")

rule()

# ── BACKGROUND ──────────────────────────────────────────────────────────────
h1("2. Background & Purpose")
body("This was the first substantive technical-plus-business meeting between Exos Aerospace and NASA MSFC's "
     "RDRE team. Exos is conducting a trade-study down-select between (a) licensing the NASA MSFC INROADS "
     "RDRE design and (b) the GTL fully-machined RDRE path, for potential integration on a BLK3-class vehicle "
     "flight demonstration. This meeting opened both the technical and agreement-structure discussions.")
note("Transcription note: 'INROADS' (or 'in roads') appears to be the NASA MSFC RDRE development program name. "
     "'9,000–12,000 kilohertz' is almost certainly 9–12 kHz (kilohertz) not megahertz.")

rule()

# ── TECHNICAL FACTS ─────────────────────────────────────────────────────────
h1("3. Technical Facts (per Teasley, verbal — 2026-10-06)")

h2("3.1 Engine Performance & Tested Hardware")
bullet("Maximum tested thrust: 5,800 lbf (sea level, pressure-fed to date).  (per Teasley, verbal)")
bullet("Baseline design: ~20 lb/s mass flow → ~5,000–6,000 lbf at sea level (sea-level atmosphere).  (per Teasley, verbal)")
bullet("  At altitude (e.g., 10,000 ft) same conditions yield ~8,000 lbf+.  (per Teasley, verbal)", indent=0.5)
bullet("Baseline operating conditions: ~1,000 psi chamber pressure / ~1,700 psi inlet pressure.  (per Teasley, verbal)")
bullet("Throttle capability: baselined at 50%; possibly 40%, unconfirmed — thrust chamber only, other components may limit further.  (per Teasley, verbal)")
bullet("Cooling: all regenerative — no film cooling used.  (per Teasley, verbal)")
bullet("A notional 10,000-lbf engine system is baselined for a turbo-pump-fed methane-rich gas generator cycle "
       "(thrust chamber same design, 50–100% = ~5,000–10,000 lbf).  (per Teasley, verbal)")

h2("3.2 Efficiency")
bullet("≥98% combustion efficiency at ≥700 psi chamber pressure.  (per Teasley, verbal)")
bullet("≥90% combustion efficiency above ~300 psi chamber pressure.  (per Teasley, verbal)")
bullet("ISP ~250 s at ~300 psi Pc / 20 lb/s / ~5,000 lbf (LOX-methane or LOX-ethanol close to same).  (per Teasley, verbal)")

h2("3.3 Loads Environment")
bullet("Measured loads: up to ~1,000+ g in some test configurations.  (per Teasley, verbal)")
bullet("Dominant frequency range: ~9–12 kHz.  (per Teasley, verbal)")
note("Transcription artifact: transcript reads '9,000–12,000 kilohertz' which is almost certainly 9–12 kHz.")
bullet("Loads environment data book: not yet released — team is still correlating scattershot data from different test-article locations; data not yet interpretable enough to publish.  (per Teasley, verbal)")
bullet("Structural damage observed: early testing saw metal C-rings shattering; pushing operating frequency higher shifted to smaller instrumentation ports failing.  (per Teasley, verbal)")
bullet("No wall erosion of the combustion chamber surface has been observed in any MSFC test.  (per Teasley, verbal)")
bullet("Detonations appear localized within the first ~0.25 inch from the injector face.  (per Teasley, verbal)")
bullet("Resonator cavity testing showed it did mitigate targeted frequencies.  (per Teasley, verbal)")

h2("3.4 Inlet Pressure / Exos Interface Compatibility")
bullet("750 psi inlet would require a redesign and remanufacture of the outer body to open the throat area "
       "(reduce chamber pressure and inlet pressure to match Exos supply capability).  (per Teasley, verbal)")
bullet("Running at ~25 lb/s for ~6,000 lbf SL requires ~1,200 psi inlet — pushes toward pump augmentation.  (per Teasley, verbal)")
bullet("Options for Exos tank pressure: 750 / 1,000 / 1,200 psi — Exos can manufacture CF tanks to any of these ratings.  (discussed on call)")
bullet("MSFC did look for LOX/CH4 turbo-pump designs below 10,000 lbf in the NASA repository — none found.  (per Teasley, verbal)")
bullet("Alternative noted: Ursa Major Hadley engine (~5,000 lbf, LOX/kerosene, oxidizer-rich) — turbo-pump could potentially be adapted with an RDRE thrust chamber.  (per Teasley, verbal)")

h2("3.5 Hardware Availability & Timeline")
bullet("Existing non-flight-weight hardware: available now; no performance guarantee, no duration guarantee.  (per Teasley, verbal)")
bullet("Higher-confidence hardware: post-1B test series (≈ March–May 2027) and post-1C series — likely available end-2027 at earliest.  (per Teasley, verbal)")
bullet("New thrust chamber (license & adapt current design): ~12–18 months to do correctly.  (per Teasley, verbal)")
bullet("Exos-owned design with Teasley coaching: approximately 2 years.  (per Teasley, verbal)")
bullet("Turbomachinery: several years; even the INROADS program was baselined 4–5 years and it was considered aggressive.  (per Teasley, verbal)")
bullet("Manufacturing steps (additive path): ~10 days print + ~3 weeks depowder + optional CT scan + HIP up to ~2 weeks + flow test up to ~2 weeks.  (per Teasley, verbal)")
bullet("GRCop powder supply easing: primary suppliers bringing additional nozzles online; several large shipments reportedly landed ~2 months ago.  (per Teasley, verbal)")
bullet("Fastest path overall: license the current INROADS design (adapts to Exos operating conditions, not flight-weight but extensible).  (per Teasley, verbal)")

h2("3.6 Vacuum / In-Space Operation")
bullet("Vacuum restart is possible — some MSFC work done, details not releasable.  (per Teasley, verbal)")
bullet("No flight demonstration is funded or planned in the current INROADS program; any flight demo is 5–10+ years out under NASA's current program.  (per Teasley, verbal)")
bullet("Ground-based vacuum chamber demo discussion exists, but is not funded.  (per Teasley, verbal)")
note("Jon commented Exos could potentially do a vacuum/in-space flight demo in 2 years or less — noted as an Exos aspiration, not a NASA commitment.")

h2("3.7 INROADS Program Papers / IP")
bullet("Heat-transfer correlation paper in journal review (JNF / JANNAF); single equation predicts convective heat transfer coefficient for LOX/CH4 RDE hot wall.  (per Teasley, verbal)")
bullet("Paper in Journal of Propulsion & Power: design and prediction of wave count and wave speed for any given geometry — validated against ~300 hot fires.  (per Teasley, verbal)")

rule()

# ── AGREEMENT PATH ──────────────────────────────────────────────────────────
h1("4. Proposed Agreement Path (per MSFC — Teasley / Mike / Seth, verbal)")
bullet("Step 1: Exos provides firm written requirements document — what they want, operating conditions, expectations, schedule/budget context.")
bullet("Step 2: Teasley socializes requirements with PM Chris Hill. Hill must approve before any agreement is executed.")
bullet("Step 3: Umbrella Reimbursable Space Act Agreement (SAA), structured with annexes allowing phased scope additions.")
bullet("  Annex 1 starts with paid consultation — Exos pays for Teasley's time; Seth and Mike are overhead / no direct cost.  (per Mike/Seth, verbal)", indent=0.5)
bullet("  Subsequent annexes added as scope / needs evolve.  (per Seth, verbal)", indent=0.5)
bullet("Licensing path: Exos has NOT yet engaged NASA Tech Transfer. Teasley confirmed this is the separate, necessary step for an IP license.")
note("All Space Act Agreements are public documents — searchable on NASA.gov. Exos has 1–2 existing SAAs.")

rule()

# ── EXOS STATED INTENTS ─────────────────────────────────────────────────────
h1("5. Exos-Stated Intents (on call — Jon / Phil)")
body("The following reflects what Jon and Phil stated on the call as Exos's intent/goals. These are "
     "pre-decisional and subject to board approval and trade-study completion.")
bullet("Flight objective: hover, then fly — generate in-flight data on isolation/damping requirements and "
       "in-flight RDRE behavior not available from ground testing.")
bullet("Target burn duration: ~85 seconds.")
bullet("Propellant: LOX/CH4 or LOX/ethanol (tank sizing is ~1:1 between the two).")
bullet("Thrust target: ~6,000 lbf sea level.")
bullet("Inlet pressure options Exos can supply: 750 / 1,000 / 1,200 psi (CF tank manufacturing in-house).")
bullet("Approximate program budget mentioned: ~$10M for a BLK3-class flight demo.")
bullet("Noted existing Exos advantage: previously flew a NASA active vibration damper — aware of what an isolator/damper looks like.")
warn("Do NOT describe Exos as an 'RDRE propulsion provider' or as offering propulsion packages. "
     "RDRE remains a trade-study down-select (MSFC license vs. GTL machined). "
     "Exos does not own the MSFC RDRE technology.")

rule()

# ── OPEN QUESTIONS ──────────────────────────────────────────────────────────
h1("6. Open Questions")
bullet("Exact Exos inlet pressure requirement (750 / 1,000 / 1,200 psi) — drives whether outer-body redesign is needed.")
bullet("Propellant selection: LOX/CH4 vs. LOX/ethanol — to be confirmed in requirements.")
bullet("Mass flow and thrust precision: Phil to confirm numbers vs. Teasley's 20 lb/s baseline.")
bullet("Is ~6,000 lbf achievable at 750 psi inlet without outer-body redesign? — Teasley to confirm after seeing firm requirements.")
bullet("Hadley engine turbo-pump adaptation: path/cost/timeline vs. clean-sheet electric pump at 5,000–6,000 lbf?")
bullet("'RCG' data — confirm exact meaning per Dankanich context.")
bullet("Has Exos had contact with NASA Tech Transfer? (Teasley confirmed they have not — needs to be initiated for licensing path.)")

rule()

# ── ACTIONS ─────────────────────────────────────────────────────────────────
h1("7. Actions")
kv("A-1", "Jon / Phil — Draft and finalize firm written RDRE requirements document; send to Teasley for Chris Hill review. [OWNER: Jon — Decision posted 2026-10-07]")
kv("A-2", "Phil — Confirm precise mass flow, inlet pressure envelope, and thrust requirement; validate against Teasley's 20 lb/s baseline. [OWNER: Phil]")
kv("A-3", "Jon — Initiate contact with NASA Tech Transfer office re: INROADS license path (separate from SAA / Teasley). [OWNER: Jon]")
kv("A-4", "Jon — Loop in Dankanich on 10/6 meeting outcome; update on GRCop supply and PSI connection (pending). [OWNER: Jon]")
kv("A-5", "Seth Bell (MSFC) — Prepare umbrella SAA framework for when requirements are ready; Exos to confirm schedule/timeline. [OWNER: Seth]")

rule()

doc.add_paragraph()
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Exos Aerospace Systems & Technologies, Inc.  |  299 FM 1903, Greenville, TX 75402  |  jquinn@exosaero.com")
_set(r, 8.5, GREY, italic=True)
p2 = doc.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
r2 = p2.add_run("INTERNAL — Do not distribute. Proprietary — Unclassified.")
_set(r2, 8.5, GREY, italic=True)

doc.save(OUT)
print(f"Saved: {OUT}")
