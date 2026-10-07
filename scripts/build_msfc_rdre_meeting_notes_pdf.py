#!/usr/bin/env python3
"""Build letterhead-matched PDF for MSFC RDRE meeting notes 2026-10-06.
Run: python3 scripts/build_msfc_rdre_meeting_notes_pdf.py
Uses reportlab + extracted letterhead banners (see exos-letterhead-proposal-doc skill).
"""
import os, subprocess, sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
                                 KeepTogether)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus.flowables import PageBreak

LH   = "assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT  = "drafts/Exos_MSFC_RDRE_Meeting_Notes_2026-10-06.pdf"
TMPD = "/tmp/lh_banner_notes"

# ── extract letterhead banners ──────────────────────────────────────────────
os.makedirs(TMPD, exist_ok=True)
subprocess.run(["unzip","-o",LH,"word/media/*","-d",TMPD], capture_output=True)
HEADER_IMG = os.path.join(TMPD,"word","media","image1.png")
FOOTER_IMG = os.path.join(TMPD,"word","media","image2.png")
if not os.path.exists(HEADER_IMG):
    print("ERROR: could not extract header image from letterhead"); sys.exit(1)

# ── page callbacks ──────────────────────────────────────────────────────────
def on_page(canvas, doc):
    W, H = letter
    from reportlab.lib.utils import ImageReader
    if os.path.exists(HEADER_IMG):
        canvas.drawImage(ImageReader(HEADER_IMG), 0, H-1.65*inch, W, 1.65*inch,
                         preserveAspectRatio=False)
    if os.path.exists(FOOTER_IMG):
        canvas.drawImage(ImageReader(FOOTER_IMG), 0, 0, W, 1.25*inch,
                         preserveAspectRatio=False)

# ── colors ─────────────────────────────────────────────────────────────────
NAVY = HexColor("#0A3D7C"); DARK = HexColor("#1A1A1A"); GREY = HexColor("#555555")
RED  = HexColor("#CC0000")

# ── styles ──────────────────────────────────────────────────────────────────
def S(name,**kw):
    defaults = dict(fontName="Helvetica",fontSize=10.5,textColor=DARK,
                    leading=14,spaceAfter=4,spaceBefore=0,leftIndent=0,
                    alignment=TA_JUSTIFY)
    defaults.update(kw)
    return ParagraphStyle(name,**defaults)

ST = {
    "title": S("title",fontName="Helvetica-Bold",fontSize=16,textColor=NAVY,
               alignment=TA_CENTER,spaceAfter=2),
    "sub":   S("sub",  fontName="Helvetica-Oblique",fontSize=11,textColor=GREY,
               alignment=TA_CENTER,spaceAfter=4),
    "warn":  S("warn", fontName="Helvetica-Bold",fontSize=9.5,textColor=RED,
               leftIndent=14,spaceAfter=4),
    "h1":    S("h1",   fontName="Helvetica-Bold",fontSize=13,textColor=NAVY,
               spaceBefore=12,spaceAfter=4),
    "h2":    S("h2",   fontName="Helvetica-Bold",fontSize=11,textColor=NAVY,
               spaceBefore=8,spaceAfter=2),
    "body":  S("body"),
    "note":  S("note", fontName="Helvetica-Oblique",fontSize=9.5,textColor=GREY,
               leftIndent=25,spaceAfter=3),
    "kv":    S("kv",   spaceAfter=3),
    "bul":   S("bul",  leftIndent=18,spaceAfter=2),
    "bul2":  S("bul2", leftIndent=36,spaceAfter=2),
}

def h1(t):  return Paragraph(t, ST["h1"])
def h2(t):  return Paragraph(t, ST["h2"])
def body(t): return Paragraph(t, ST["body"])
def note(t): return Paragraph(t, ST["note"])
def bul(t):  return Paragraph("•  " + t, ST["bul"])
def bul2(t): return Paragraph("–  " + t, ST["bul2"])
def warn(t): return Paragraph("⚠ INTERNAL ONLY — " + t, ST["warn"])
def hr():    return HRFlowable(width="100%",thickness=0.75,color=NAVY,spaceAfter=6,spaceBefore=2)
def sp(n=4): return Spacer(1, n)
def kv(label, val):
    return Paragraph(f"<b>{label}:</b> {val}", ST["kv"])

# ── document ────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(OUT, pagesize=letter,
    topMargin=1.75*inch, bottomMargin=1.35*inch,
    leftMargin=0.85*inch, rightMargin=0.85*inch,
    title="Exos MSFC RDRE Meeting Notes 2026-10-06")

story = []
story += [
    sp(6),
    Paragraph("MEETING NOTES — NASA MSFC RDRE TECHNICAL DISCUSSION", ST["title"]),
    Paragraph("October 6, 2026  |  1:00 PM CDT  |  Virtual", ST["sub"]),
    warn("For Exos internal use only. Do not distribute outside Exos without Jon Quinn approval."),
    hr(),

    h1("1. Attendees"),
    h2("NASA MSFC"),
    bul("Tom Teasley — RDRE Technical Lead, INROADS program, ER13 (combustion devices)"),
    bul("Seth Bell — Industry & Commercial Partnerships Manager (also covers OGA / Other Government Agencies)"),
    bul("Mike — Partnerships (surname unknown; Seth's colleague)"),
    bul("Chris Hill — Project Manager / Approver for INROADS (not on call; must approve any SAA)"),
    h2("Exos Aerospace"),
    bul("Jon Quinn — Cofounder & CEO"),
    bul("Phil Gard — Chief Engineer (joined late, via phone)"),
    hr(),

    h1("2. Background & Purpose"),
    body("This was the first substantive technical-plus-business meeting between Exos Aerospace and NASA MSFC's "
         "RDRE team. Exos is conducting a trade-study down-select between (a) licensing the NASA MSFC INROADS "
         "RDRE design and (b) the GTL fully-machined RDRE path, for potential integration on a BLK3-class vehicle "
         "flight demonstration. This meeting opened both the technical and agreement-structure discussions."),
    note("Transcription note: 'INROADS' (or 'in roads') appears to be the NASA MSFC RDRE development program name. "
         "'9,000–12,000 kilohertz' in transcript is almost certainly 9–12 kHz."),
    hr(),

    h1("3. Technical Facts  (per Teasley, verbal — 2026-10-06)"),

    h2("3.1  Engine Performance & Tested Hardware"),
    bul("Maximum tested thrust: 5,800 lbf (sea level, pressure-fed to date).  (per Teasley, verbal)"),
    bul("Baseline design: ~20 lb/s mass flow → ~5,000–6,000 lbf at sea level.  (per Teasley, verbal)"),
    bul2("At altitude (~10,000 ft) same conditions yield ~8,000 lbf+.  (per Teasley, verbal)"),
    bul("Baseline operating conditions: ~1,000 psi chamber pressure / ~1,700 psi inlet pressure.  (per Teasley, verbal)"),
    bul("Throttle: baselined 50%; possibly 40% (thrust chamber only; other components may limit further).  (per Teasley, verbal)"),
    bul("Cooling: all regenerative — no film cooling used.  (per Teasley, verbal)"),
    bul("Notional 10,000-lbf engine system: baselined for turbo-pump-fed methane-rich gas generator cycle "
        "(50–100% = ~5,000–10,000 lbf).  (per Teasley, verbal)"),

    h2("3.2  Efficiency"),
    bul("≥98% combustion efficiency at ≥700 psi chamber pressure.  (per Teasley, verbal)"),
    bul("≥90% combustion efficiency above ~300 psi chamber pressure.  (per Teasley, verbal)"),
    bul("ISP ~250 s at ~300 psi Pc / 20 lb/s / ~5,000 lbf (LOX-methane or LOX-ethanol near-equivalent).  (per Teasley, verbal)"),

    h2("3.3  Loads Environment"),
    bul("Measured loads: up to ~1,000+ g in some test configurations.  (per Teasley, verbal)"),
    bul("Dominant frequency range: ~9–12 kHz.  (per Teasley, verbal)"),
    note("Transcript reads '9,000–12,000 kilohertz' — almost certainly 9–12 kHz."),
    bul("Loads data book: not yet released — data scattershot, not yet interpretable.  (per Teasley, verbal)"),
    bul("Early: metal C-rings shattered; pushing frequency higher → smaller items (instrumentation ports) failing.  (per Teasley, verbal)"),
    bul("No chamber wall erosion observed in any test.  (per Teasley, verbal)"),
    bul("Detonations localized within ~0.25 inch of injector face.  (per Teasley, verbal)"),
    bul("Resonator cavity testing successfully mitigated targeted frequencies.  (per Teasley, verbal)"),

    h2("3.4  Inlet Pressure / Exos Interface Compatibility"),
    bul("750 psi inlet: requires outer-body redesign + remanufacture to open throat, reducing Pc/inlet P.  (per Teasley, verbal)"),
    bul("~25 lb/s for ~6,000 lbf SL → ~1,200 psi inlet required — pushes toward pump augmentation.  (per Teasley, verbal)"),
    bul("LOX/CH4 turbo-pump <10,000 lbf: none found in NASA repository.  (per Teasley, verbal)"),
    bul("Ursa Major Hadley: ~5,000 lbf LOX/kerosene oxy-rich — turbo-pump possibly adaptable with RDRE chamber.  (per Teasley, verbal)"),

    h2("3.5  Hardware Availability & Timeline"),
    bul("Existing non-flight-weight hardware: available now; no performance or duration guarantee.  (per Teasley, verbal)"),
    bul("Higher-confidence hardware: post-1B (≈Mar–May 2027) / post-1C series — likely end-2027 at earliest.  (per Teasley, verbal)"),
    bul("New thrust chamber (license current design): ~12–18 months.  (per Teasley, verbal)"),
    bul("Exos-owned design with Teasley coaching: approximately 2 years.  (per Teasley, verbal)"),
    bul("Turbomachinery: several years.  (per Teasley, verbal)"),
    bul("Additive timeline: ~10 days print + ~3 wks depowder + optional CT scan + HIP ≤2 wks + flow test ≤2 wks.  (per Teasley, verbal)"),
    bul("GRCop powder supply: easing — primary suppliers reportedly restoring quotas.  (per Teasley, verbal)"),
    bul("Fastest path: license current INROADS design.  (per Teasley, verbal)"),

    h2("3.6  Vacuum / In-Space Operation"),
    bul("Restart in vacuum: possible — MSFC work done, details not releasable.  (per Teasley, verbal)"),
    bul("No funded flight demo in INROADS program; any flight demo 5–10+ years under NASA's plan.  (per Teasley, verbal)"),
    note("Jon stated Exos could potentially do this in ≤2 years — noted as Exos aspiration, not a NASA commitment."),

    h2("3.7  INROADS Program IP / Publications"),
    bul("Heat-transfer correlation paper: in journal review (JNF/JANNAF) — one equation predicts convective "
        "heat transfer coefficient for LOX/CH4 RDE hot wall.  (per Teasley, verbal)"),
    bul("JPP paper: design and prediction of wave count and speed — validated vs. ~300 hot fires.  (per Teasley, verbal)"),
    hr(),

    h1("4. Proposed Agreement Path  (per Teasley / Mike / Seth, verbal)"),
    bul("Step 1: Exos provides firm written requirements document."),
    bul("Step 2: Teasley socializes with PM Chris Hill → Hill must approve."),
    bul("Step 3: Umbrella Reimbursable Space Act Agreement (SAA) with annexes."),
    bul2("Annex 1: paid consultation (Exos pays for Teasley's time; Seth/Mike overhead / no direct cost)."),
    bul2("Subsequent annexes added as scope evolves."),
    bul("Licensing path: Exos has NOT engaged NASA Tech Transfer — must do so separately for an IP license."),
    note("All SAAs are public documents — searchable on NASA.gov. Exos has 1–2 existing SAAs."),
    hr(),

    h1("5. Exos-Stated Intents  (Jon / Phil, on call — pre-decisional)"),
    body("The following reflects what Jon and Phil stated on the call. Pre-decisional; subject to board "
         "approval and trade-study completion."),
    bul("Objective: hover then fly — generate in-flight data on isolation/damping requirements."),
    bul("Burn duration: ~85 seconds."),
    bul("Propellant: LOX/CH4 or LOX/ethanol (tank sizing ~1:1)."),
    bul("Thrust target: ~6,000 lbf sea level."),
    bul("Tank inlet options Exos can supply: 750 / 1,000 / 1,200 psi (CF tanks manufactured in-house)."),
    bul("Approximate program budget mentioned: ~$10M for a BLK3-class flight demo."),
    bul("Exos previously flew a NASA active vibration damper — familiar with isolator/damper hardware."),
    warn("Do NOT describe Exos as an 'RDRE propulsion provider' or as offering propulsion packages. "
         "RDRE is a trade-study down-select (MSFC license vs. GTL machined). Exos does not own MSFC RDRE technology."),
    hr(),

    h1("6. Open Questions"),
    bul("Exact Exos inlet pressure requirement — drives outer-body redesign decision."),
    bul("Propellant selection: LOX/CH4 vs. LOX/ethanol."),
    bul("Phil to confirm mass flow and thrust precision vs. Teasley's 20 lb/s baseline."),
    bul("Can ~6,000 lbf be achieved at 750 psi inlet without outer-body redesign?"),
    bul("Electric pump vs. clean-sheet design path at 5,000–6,000 lbf — cost/schedule?"),
    bul("NASA Tech Transfer contact / license path — who initiates and timeline?"),
    bul("'RCG' data meaning — confirm with Dankanich."),
    hr(),

    h1("7. Actions"),
    kv("A-1 [Jon]",  "Draft and finalize firm written RDRE requirements; send to Teasley for Chris Hill review. [Decision posted 2026-10-07]"),
    kv("A-2 [Phil]", "Confirm precise mass flow, inlet pressure, and thrust requirement vs. Teasley's 20 lb/s baseline."),
    kv("A-3 [Jon]",  "Initiate NASA Tech Transfer contact for INROADS license path."),
    kv("A-4 [Jon]",  "Update Dankanich on 10/6 meeting outcome; advance GRCop/PSI thread."),
    kv("A-5 [Seth Bell — MSFC]", "Prepare umbrella SAA framework for when requirements are ready."),
    hr(),
    sp(4),
    Paragraph("Exos Aerospace Systems & Technologies, Inc.  |  299 FM 1903, Greenville, TX 75402  |  jquinn@exosaero.com",
              S("ft",fontName="Helvetica-Oblique",fontSize=8.5,textColor=GREY,alignment=TA_CENTER,spaceAfter=1)),
    Paragraph("INTERNAL — Do not distribute. Proprietary — Unclassified.",
              S("ft2",fontName="Helvetica-Oblique",fontSize=8.5,textColor=GREY,alignment=TA_CENTER)),
]

doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"Saved: {OUT}")
