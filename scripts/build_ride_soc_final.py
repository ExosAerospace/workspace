#!/usr/bin/env python3
"""Build the Exos RIDE Statement of Capability (SOC), submission version.

Spec-compliant per SAM RIDE RFI (opp f00d704b47bf44feb24cfa2112c8101c): <=15 pages,
11-pt Times New Roman, 1-inch margins, references "RIDE", unclassified, non-proprietary.
Incorporates the Government's answered CRM (Perales, 2026-10-05). MC task #2848.
Run: /usr/bin/python3 scripts/build_ride_soc_final.py  (then soffice --convert-to pdf)
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml.ns import qn

OUT = "drafts/Exos_RIDE_Statement_of_Capability_2026-10-09.docx"
FONT = "Times New Roman"

doc = Document()
for s in doc.sections:
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
st = doc.styles["Normal"]
st.font.name = FONT; st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(4)

hdr = doc.sections[0].header.paragraphs[0]
hdr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hdr.add_run("RIDE — Statement of Capability — Exos Aerospace Systems & Technologies, Inc. — UNCLASSIFIED")
r.font.name = FONT; r.font.size = Pt(11)

def run(p, t, bold=False, italic=False, hl=False):
    r = p.add_run(t); r.font.name = FONT; r.font.size = Pt(11)
    r.bold = bold; r.italic = italic
    if hl: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return r

def center(t, bold=False):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; run(p, t, bold); p.paragraph_format.space_after = Pt(1)

def h1(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10); run(p, t, bold=True)

def h2(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(4); run(p, t, bold=True, italic=True)

def body(*parts):
    """parts: str, or (str, 'hl') for a yellow-highlighted confirm item."""
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for x in parts:
        if isinstance(x, tuple): run(p, x[0], hl=True)
        else: run(p, x)
    return p

def bullet(t):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.15); p.paragraph_format.space_after = Pt(2)
    run(p, "•  " + t)

# ---------------- COVER BLOCK ----------------
center("UNCLASSIFIED", True)
center("RIDE — Statement of Capability (SOC)", True)
center("Rocket Systems Launch Program (RSLP) Innovative Delivery of Effects (RIDE)")
center("Dedicated Reusable Suborbital Launch Services — Exos BLK3")
center("")
center("Submitted to: SSC/AAK-KT (Contract Specialist Tristan Perales; PCO Robert Robson) for SSC/SYD 80/AMX")
center("In response to: RIDE Request for Information, SAM.gov notice f00d704b47bf44feb24cfa2112c8101c")
center("Due: 9 October 2026, 17:00 MDT")
center("")
center("Exos Aerospace Systems & Technologies, Inc.", True)
center("CAGE 7EMY6  |  UEI CK24BPZGF854  |  Small Business")
center("299 FM 1903, Greenville, TX 75402")
center("POC: John Quinn, Cofounder & CEO — jquinn@exosaero.com — +1 (972) 740-8355")
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run(p, "This RIDE SOC contains no classified, CUI, or proprietary information and is provided for Government "
    "market-research purposes. Technical figures are current best estimates.", italic=True)

# ---------------- 1 ----------------
h1("1. Summary")
body("Exos Aerospace Systems & Technologies, Inc. (Exos) submits this Statement of Capability in response to the RIDE "
     "RFI. Exos is a small-business launch provider that designs, manufactures, and operates its own reusable "
     "suborbital launch vehicle, the BLK3 Precision Suborbital Reusable Launch Vehicle (PSRLV), and controls its "
     "technical baseline and launch operations. Exos offers dedicated and multi-manifest suborbital launch for "
     "developmental, responsive, demonstration, and operational payloads, with intact recovery of the vehicle and "
     "payload. Exos intends to compete for on-ramp to the RIDE Commercial IDIQ, and to the Non-Commercial IDIQ once "
     "its cost-accounting system meets the stated criterion (Section 3.4).")

# ---------------- 2 ----------------
h1("2. Company Information")
bullet("Legal name: Exos Aerospace Systems & Technologies, Inc.; CAGE 7EMY6; UEI CK24BPZGF854; Greenville, Texas.")
bullet("NAICS and size (per Government CRM response #4): Exos is a small business under both contemplated NAICS "
       "codes — 336414 (Guided Missiles and Space Vehicle Manufacturing) and 481212 (Nonscheduled Chartered Freight "
       "Air Transportation). Exos identifies 336414 as the best-applicable code.")
bullet("Licensing: FAA commercial launch license for the SARGE/BLK3 reusable suborbital vehicle family, renewed "
       "March 2026; transition to 14 CFR Part 450 in progress.")
bullet("DoD program experience: AFRL SBIR Phase II contract FA9300-25-C-6022, under which Exos provides the flight "
       "vehicle to integrate and fly a Government-selected rotating-detonation rocket engine to free flight; a "
       "follow-on AFRL contract extension (Project Hermes) was executed in September 2026. Exos previously completed "
       "design, fabrication, and hot-fire test of a reusable hypersonic launch-vehicle prototype under a USAF/AFWERX "
       "Phase II SBIR.")

# ---------------- 3 ----------------
h1("3. Response to the RIDE On-Ramp Criteria")
h2("3.1  Ownership and control of the launch-vehicle technical baseline")
body("Exos designs and manufactures BLK3 and holds full authority to make technical changes in response to "
     "requirements. Exos conducts its own launch and recovery operations. Exos does not resell or broker another "
     "provider's vehicle. This meets the Government's stated intent (CRM #7, #26).")
h2("3.2  Previous successful liftoff")
body("Per CRM #5, a successful liftoff of a predecessor or heritage vehicle owned and operated by the proposing "
     "vendor satisfies this criterion. Exos's SARGE vehicle, the direct predecessor of BLK3 and owned and operated "
     "by Exos, has flown four times from Spaceport America, New Mexico. Each flight began with the initial, "
     "non-reversible propulsive event that RIDE uses to define liftoff. BLK3's first flight campaign is planned "
     "for early 2027 and will add liftoff evidence for the current configuration before the anticipated Q3 FY2027 "
     "solicitation.")
h2("3.3  Mass-to-objective: 50 kg to 100 km (direct suborbital, per CRM #25)")
body("BLK3 has a 135 kg payload bay (25 in × 36 in). In response to CRM #6, which asks what data supports the "
     "threshold, Exos maintains a 6-degree-of-freedom nominal-mission trajectory model of BLK3 (TAOS; site winds and "
     "1-sigma dispersions). ",
     ("[CONFIRM BEFORE SUBMIT: the BLK3 6-DOF nominal predicts apogee of ___ km with a 50 kg payload (≥100 km required)]"),
     " Exos will provide the trajectory analysis to RSLP on request, and will provide flight-measured apogee "
     "data from the 2027 BLK3 campaign once available.")
h2("3.4  Cost accounting system (Non-Commercial IDIQ only)")
body("Exos does not yet have an approved accounting system under R-DFARS 242.7502. A DCAA-compliant timekeeping and "
     "project cost-accounting capability is in implementation. Exos will seek on-ramp to the Commercial IDIQ first, "
     "and to the Non-Commercial IDIQ once that criterion is met. Exos supports the Government's intent (CRM #2) to "
     "allow a single proposal to on-ramp to both IDIQs where criteria are met.")

# ---------------- 4 ----------------
h1("4. Launch Service Offering")
bullet("Mission types: developmental, responsive, demonstration, and operational payloads; hosted experiments; "
       "flight test and qualification of sensors and subsystems; suborbital technology demonstrations (CRM #9).")
bullet("Manifest: dedicated or multi-manifest within the 135 kg bay, set mission by mission at the task-order level "
       "(CRM #14).")
bullet("Recovery and reuse: the vehicle and payload are recovered intact. The vehicle is designed for rapid reuse; "
       "Exos's catalog offering is approximately three days between flights in campaign mode at a commercial range.")
bullet("Launch site: Exos proposes its FAA-licensed operations at Spaceport America, New Mexico, consistent with "
       "CRM #11. Exos needs minimal launch infrastructure (a pad with power and communications), which supports "
       "other ranges when a task order requires it.")
bullet("Range safety: Exos operates under its FAA license. Where a task order requires range-specific approval "
       "(e.g., RCC 319), Exos will pursue it for that mission (CRM #12).")
bullet("Pricing: Exos's published commercial rate for a dedicated BLK3 flight is about $1 million. Firm-fixed-price "
       "pricing will be offered at the task-order level (CRM #14).")

# ---------------- 5 ----------------
h1("5. Alignment to RIDE Mission Pillars")
bullet("Responsive & Reliable Launch: a reusable vehicle with minimal infrastructure needs and campaign-mode "
       "turnaround supports schedule-resilient, responsive access.")
bullet("Servicing, Mobility & Logistics: Exos affiliate Scorpius Space Launch Company, in which Exos holds an 18% "
       "interest, built the composite cryogenic propellant tanks flown on the Intuitive Machines IM-1 (Odysseus) and "
       "IM-2 (Athena) lunar missions. This domestic capability is relevant to in-space propellant storage and "
       "mobility.")

# ---------------- 6 ----------------
h1("6. Orbital Roadmap (requested in CRM #10)")
body("Exos offers suborbital launch under RIDE today. Exos's planned orbital path is the BLK4 Heavy configuration. "
     "It depends on future funding, has not flown, and is not offered under this SOC. Exos will update RSLP as BLK4 "
     "Heavy matures. Exos supports the Government's position that suborbital-only providers may on-ramp, and "
     "recommends separate suborbital and orbital lanes or CLINs so that task orders are competed among providers "
     "suited to each regime.")

# ---------------- 7 ----------------
h1("7. Mission Assurance Approach and Feedback (requested in CRM #15)")
body("Exos recommends mission assurance (MA) tailored per task order to the Government-assessed acceptable risk. "
     "For developmental and demonstration missions where most of the risk sits with the payload, Exos recommends a "
     "Category-2-style tailored posture. This keeps cost and schedule low while meeting Government risk "
     "thresholds. Exos's baseline MA content draws on its FAA licensing work: system safety analysis, flight-safety "
     "analysis, reliability analysis, FMECA, configuration management, and pre-flight readiness reviews. Exos is "
     "prepared to deliver the notional minimum-award data products: MA process walk-through, rocket design risks, "
     "Program Management Plan, System Safety Program Plan, Cybersecurity Implementation Plan (aligned to "
     "NIST SP 800-171 / CMMC 2.0), Reliability Analysis Report, and FMECA.")

# ---------------- 8 ----------------
h1("8. Feedback on the Draft On-Ramp Criteria (invited in CRM #19 and #26)")
bullet("Liftoff criterion: Exos supports requiring a successful liftoff by proposal submission and accepting "
       "heritage vehicles owned and operated by the offeror (CRM #5, #19).")
bullet("MTO evidence: Exos recommends accepting either flight data or a documented 6-DOF trajectory analysis on the "
       "offeror's controlled baseline, confirmed by flight data before the first launch task order (CRM #6).")
bullet("Reusability: Exos supports the Government's plan to consider cost at task-order competition (CRM #8). "
       "Exos recommends that reusable providers be allowed to price multi-flight and campaign task orders, so the "
       "Government gets the full per-flight cost benefit of reuse.")
bullet("Suborbital manifest: Exos would value the updated manifest that separates orbital and suborbital "
       "missions (CRM #1, #13) to size suborbital cadence and capacity.")

# ---------------- 9 ----------------
h1("9. Point of Contact")
body("John Quinn, Cofounder & CEO, Exos Aerospace Systems & Technologies, Inc. — jquinn@exosaero.com — "
     "+1 (972) 740-8355 — 299 FM 1903, Greenville, TX 75402. Exos welcomes a one-on-one session with the RSLP team "
     "on BLK3 capability, mission assurance, and on-ramp planning.")
center("UNCLASSIFIED", True)

doc.save(OUT)
print("WROTE", OUT)
