#!/usr/bin/env python3
"""Build the Exos RIDE Statement of Capability (SOC) v2: restructured to the RIDE RFI's required SOC posture
areas (A)-(F) and its five encouraged topics, with PUG figures and flight photos. MC task #3442 (from D-7281957).

RFI spec (SAM notice f00d704b47bf44feb24cfa2112c8101c, Sec. 6): <=15 pages, 11-pt Times New Roman, 1-inch margins,
reference "RIDE", unclassified/non-proprietary, include NAICS 336414 + 481212 size status.
Figures come from the public Exos Payload User Guide (July 2026, "Approved for public release") and Exos flight media.
Run: /usr/bin/python3 scripts/build_ride_soc_v2.py  (then soffice --headless --convert-to pdf)
"""
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from PIL import Image
MAXH = 2.6  # max figure-row image height, inches

OUT = "drafts/Exos_RIDE_Statement_of_Capability_2026-10-09_v2.docx"
A = "drafts/ride_soc_assets/"
M = "media/blk3-footage/"
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

# page numbers in footer
fp = doc.sections[0].footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
def _fld(p, code):
    r = p.add_run(); r.font.name = FONT; r.font.size = Pt(11)
    for tag, txt in (("begin", None), (None, code), ("end", None)):
        if tag:
            e = r._r.makeelement(qn("w:fldChar"), {qn("w:fldCharType"): tag}); r._r.append(e)
        else:
            e = r._r.makeelement(qn("w:instrText"), {qn("xml:space"): "preserve"}); e.text = txt; r._r.append(e)
rr = fp.add_run("RIDE — UNCLASSIFIED — Page "); rr.font.name = FONT; rr.font.size = Pt(11)
_fld(fp, "PAGE")

def run(p, t, bold=False, italic=False):
    r = p.add_run(t); r.font.name = FONT; r.font.size = Pt(11); r.bold = bold; r.italic = italic
    return r

def center(t, bold=False):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; run(p, t, bold)
    p.paragraph_format.space_after = Pt(1)

def h1(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10); p.paragraph_format.keep_with_next = True
    run(p, t, bold=True)

def h2(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(4); p.paragraph_format.keep_with_next = True
    run(p, t, bold=True, italic=True)

def body(*parts):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for x in parts:
        if isinstance(x, tuple): run(p, x[0], bold=True)
        else: run(p, x)
    return p

def bullet(t, lead=None):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.first_line_indent = Inches(-0.15); p.paragraph_format.space_after = Pt(2)
    run(p, "•  ")
    if lead: run(p, lead + " ", bold=True)
    run(p, t)

FIG = [0]
def figure(path, cap, width=6.0):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(path, width=Inches(width))
    FIG[0] += 1
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER; c.paragraph_format.space_after = Pt(6)
    run(c, f"Figure {FIG[0]}. ", bold=True); run(c, cap, italic=True)

def figure_row(items, width):
    """items: [(path, caption)] side by side in a borderless table."""
    t = doc.add_table(rows=2, cols=len(items)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (path, cap) in enumerate(items):
        c0 = t.cell(0, i).paragraphs[0]; c0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c0.paragraph_format.keep_with_next = True
        iw, ih = Image.open(path).size
        if ih / iw * width > MAXH: c0.add_run().add_picture(path, height=Inches(MAXH))
        else: c0.add_run().add_picture(path, width=Inches(width))
        FIG[0] += 1
        c1 = t.cell(1, i).paragraphs[0]; c1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(c1, f"Figure {FIG[0]}. ", bold=True); run(c1, cap, italic=True)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr(); trPr.append(trPr.makeelement(qn("w:cantSplit"), {}))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

def table(rows, widths, header=True):
    t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, w in enumerate(widths): t.columns[j].width = Inches(w)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = t.cell(i, j); cell.width = Inches(widths[j])
            p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = i < len(rows) - 1
            run(p, v, bold=(header and i == 0))
        trPr = t.rows[i]._tr.get_or_add_trPr(); trPr.append(trPr.makeelement(qn("w:cantSplit"), {}))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

# ================= COVER BLOCK =================
center("UNCLASSIFIED", True)
center("RIDE — Statement of Capability (SOC)", True)
center("Rocket Systems Launch Program (RSLP) Innovative Delivery of Effects (RIDE) — Supplemental RFI (RIDE2026)")
center("Dedicated Reusable Suborbital Launch Services — Exos BLK3")
center("")
center("Submitted to: Robert Robson (PCO) and Tristan Perales (Contract Specialist), SSC/SYD 80/AMX")
center("In response to: RIDE Supplemental RFI, SAM.gov notice f00d704b47bf44feb24cfa2112c8101c — due 9 October 2026, 17:00 MDT")
center("")
center("Exos Aerospace Systems & Technologies, Inc.", True)
center("CAGE 7EMY6  |  UEI CK24BPZGF854  |  Small Business  |  299 FM 1903, Greenville, TX 75402")
center("POC: John Quinn, Cofounder & CEO — jquinn@exosaero.com — +1 (972) 740-8355")
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run(p, "This RIDE SOC contains no classified, CUI, or proprietary information and is provided for Government market-"
       "research purposes. Figures and vehicle data are drawn from the Exos BLK3 Payload User Guide (July 2026, approved "
       "for public release). Technical figures are current best estimates.", italic=True)

figure_row([(M + "SARGE_ascent.jpg", "SARGE liftoff and boost, Spaceport America, NM."),
            (A + "canopy_crop.jpg", "SARGE returning under its guided ram-air parachute for intact recovery.")], 3.0)

# ================= 1 =================
h1("1. Summary")
body("Exos Aerospace Systems & Technologies, Inc. (Exos) is a U.S. small business that designs, builds, licenses, and "
     "operates its own reusable suborbital launch vehicles. Its current vehicle, the BLK3 Suborbital Reusable Launch "
     "Vehicle (SRLV), is a single-stage, pressure-fed LOX/ethanol rocket. Its design reference mission is ",
     ("135 kg to 100 km"), " from Spaceport America, New Mexico, and it returns the vehicle and payload intact under a "
     "guided parafoil. BLK3 meets the RIDE gating criteria: Exos owns and controls the technical baseline (Section 2); "
     "Exos's heritage vehicle SARGE, owned and operated by Exos, has lifted off four times (Section 3); and BLK3 can "
     "carry 50 kg well above 100 km (Section 4). Exos intends to propose to the ",
     ("RIDE Commercial IDIQ"), " and to the ", ("Non-Commercial IDIQ"), " once its accounting system meets the stated "
     "criterion (Section 5).")

table([["RIDE gating criterion (CRM #26)", "Exos position", "Evidence"],
       ["Own/control LV technical baseline", "Meets", "Exos designs, builds, and operates BLK3 (Sec. 2)"],
       ["Successful liftoff by proposal", "Meets (heritage vehicle, CRM #5)", "SARGE: 4 liftoffs, Spaceport America, 2018–2019 (Sec. 3)"],
       ["50 kg to ≥100 km (direct suborbital, CRM #25)", "Meets by analysis; flight data 2027",
        "~134 km unconstrained at 50 kg; engine cutoff commanded at 110 km (Sec. 4)"],
       ["Approved accounting system (Non-Commercial only)", "In implementation", "Sec. 5"]],
      [2.1, 1.6, 2.8])

# ================= 2 =================
h1("2. Company, Production Process, and Control of the Technical Baseline")
bullet("Exos Aerospace Systems & Technologies, Inc.; CAGE 7EMY6; UEI CK24BPZGF854; headquarters, engineering, and "
       "manufacturing in Greenville, Texas, with an engine and vehicle test site at Caddo Mills Municipal Airport, Texas.",
       "Company.")
bullet("Exos is a small business under both NAICS codes named in the RFI: 336414 (Guided Missiles and Space Vehicle "
       "Manufacturing) and 481212 (Nonscheduled Chartered Freight Air Transportation — Space Transportation). Exos "
       "considers 336414 the best-applicable code.", "NAICS and size.")
bullet("FAA reusable launch vehicle mission license for the SARGE/BLK3 family, first issued 14 February 2018 and "
       "most recently renewed March 2026; transition to 14 CFR Part 450 in progress.", "Licensing.")
bullet("Exos designs the airframe, propulsion, avionics, guidance software, and recovery system and builds the "
       "vehicle in Greenville, using extensive carbon-fiber composite structures to cut dry mass. BLK3 has nearly "
       "the dry mass of SARGE but carries about 50% more propellant, because its diameter grew from 508 mm (20 in) "
       "to 635 mm (25 in). Exos holds full authority to make technical changes in response to Government "
       "requirements and does not resell another provider's vehicle (CRM #7, #26).",
       "Production process and baseline control (RFI topic 1).")
bullet("AFRL SBIR Phase II contract FA9300-25-C-6022, under which Exos provides the flight vehicle to integrate and "
       "fly a Government-selected rotating-detonation rocket engine to free flight; a follow-on AFRL extension "
       "(Project Hermes) was executed in September 2026. Exos earlier completed design, fabrication, and hot-fire "
       "test of a reusable hypersonic launch-vehicle prototype under a USAF/AFWERX Phase II SBIR. That effort is "
       "the origin of BLK3.", "DoD program experience.")
figure_row([(A + "pug-004-002.png", "BLK3 stack: 10.82 m, modular sections (PUG §2.2)."),
            ("assets/blk3_hover.png", "BLK3 vertical integrated test with tethered hover at Exos's Texas test site.")], 3.0)

# ================= 3 =================
h1("3. (A) Commercial Missions and (C) Flight Heritage")
h2("3.1  Current commercial involvement and intent")
body("Exos sells dedicated and shared suborbital flights to commercial, academic, and Government payload customers. "
     "Its published Payload User Guide gives payload providers the vehicle capability, environments, interfaces, "
     "integration flow, and launch operations, and its online Payload Questionnaire opens a payload review. SARGE "
     "flights have carried research payloads for paying customers. ", ("Exos intends to propose to the RIDE "
     "Commercial IDIQ"), " for Space Transportation Services: developmental, responsive, demonstration, and "
     "operational payloads; hosted experiments; and flight test and qualification of sensors and subsystems (CRM #9).")
h2("3.2  Previous liftoffs (vehicle, date, location)")
body("Under the RFI definition (the initial, non-reversible propulsive event), Exos's heritage vehicle SARGE, owned and "
     "operated by Exos, has lifted off four times. All four flights launched from Spaceport America, New Mexico, under "
     "Exos's FAA license. Per CRM #5, a liftoff of a heritage vehicle owned and operated by the offeror satisfies "
     "the criterion.")
table([["Flight", "Date", "Location", "Outcome (public record)"],
       ["SARGE Pathfinder", "25 Aug 2018", "Spaceport America, NM", "Liftoff; ~28 km; nine payloads; vehicle recovered and reflown"],
       ["SARGE Mission 1 (first reuse)", "2 Mar 2019", "Spaceport America, NM", "Liftoff; ~20 km (winds); research payloads; recovered"],
       ["SARGE flight 3", "29 Jun 2019", "Spaceport America, NM", "Liftoff; loss of control early in boost; recovered intact"],
       ["SARGE flight 4", "26 Oct 2019", "Spaceport America, NM", "Liftoff; structural failure; vehicle lost"]],
      [1.5, 0.9, 1.5, 2.6])
h2("3.3  Planned liftoff in the next 12 months")
body("BLK3's first flight campaign is planned for ", ("early 2027 from Spaceport America, New Mexico"), ", under "
     "Exos's FAA license. This is within twelve months of SOC submission and ahead of the anticipated Q3 FY2027 "
     "solicitation. It will add liftoff and flight-measured apogee evidence for the current configuration.")
h2("3.4  How the heritage supports design maturity")
body("SARGE flew the same airframe four times in fourteen months. Those flights demonstrated licensed launch "
     "operations, autonomous guidance, and recovery, refurbishment, and reflight of a single vehicle. None of the "
     "SARGE flights reached its planned altitude. Exos used the flight data to redesign the vehicle: BLK3 replaces "
     "SARGE's aluminum structure with carbon-fiber composite and carries about 50% more propellant. BLK3's maturity "
     "rests on SARGE flight data, ground and hover testing of the integrated vehicle, the FAA license and its "
     "flight-safety analysis, and a 6-degree-of-freedom trajectory model. The 2027 BLK3 flight campaign will close "
     "the remaining gap with flight data.")
figure_row([(M + "SARGE_earth_limb.jpg", "Onboard SARGE camera view of the Earth's limb during flight."),
            (M + "SARGE_recovery_ops.jpg", "Exos launch crew during SARGE flight operations.")], 3.0)

# ================= 4 =================
h1("4. Mass-to-Objective: 50 kg to 100 km (CRM #6, #25)")
body("BLK3's design reference mission is 135 kg to 100 km from Spaceport America (1,400 m MSL). BLK3 can also carry "
     "200 kg to about 80 km, the payload range used for NASA Flight Opportunities. Figure 7 plots maximum "
     "altitude against payload mass from the Payload User Guide. With a ", ("50 kg payload, BLK3's unconstrained "
     "capability is about 134 km"), ", well above the 100 km threshold.")
body("Altitude is limited in operation, not by performance. ", ("Exos's FAA license and recovery system are designed "
     "and programmed to command engine cutoff when the calculated maximum altitude reaches 110 km."), " The onboard "
     "apogee prediction is based on TRICK simulation software repurposed from the Space Shuttle program. A 50 kg "
     "mission therefore flies to a nominal 110 km apogee. This leaves a 10 km margin above the RIDE threshold "
     "while keeping the vehicle inside its licensed and recovery-qualified envelope. In answer to CRM #6, Exos will "
     "provide its 6-DOF nominal-mission trajectory analysis for a 50 kg payload (site winds and 1-sigma "
     "dispersions) to RSLP on request, and will provide flight-measured apogee data from the 2027 BLK3 campaign.")
figure(A + "fig_alt_vs_payload.png", "BLK3 maximum altitude vs. payload mass. Data points from the Exos Payload "
       "User Guide (July 2026); the 110 km line is the commanded engine-cutoff altitude.", 6.0)
figure(A + "pug-005-004.png", "Nominal BLK3 mission profile at the 135 kg design reference: altitude (blue) and "
       "velocity (green) vs. time (PUG §2.3).", 6.0)
body("Payload-relevant timeline (design reference): engine ignition T+0; main engine cutoff (MECO) about T+90 s at "
     "3.8 g peak boost load; about 150 s of microgravity from T+130 s; ballute deployment at the onset of milli-g, "
     "about T+285 s (4.3 g peak); main parachute about T+520 s (6.8 g shock); landing about T+1,500 s near the pad. "
     "Total mission time is typically 20–25 minutes. Boost loads are gentle compared with solid boosters, under 4 g.")
figure(A + "pug-006-005.png", "Nominal BLK3 g-load profile (PUG §2.3).", 6.0)

# ================= 5 =================
h1("5. (B) Non-Commercial Missions")
body("Exos's non-commercial work to date has been for DoD under SBIR contracts. In each case the vehicle or its CONOPS "
     "was modified for a Government need. BLK3 itself began as a USAF concept for a ground-launched hypersonic test "
     "vehicle. Under AFRL contract FA9300-25-C-6022, Exos is adapting its vehicle to carry and fly a "
     "Government-selected rotating-detonation rocket engine to free flight. This is military-unique integration "
     "and qualification work that the commercial market did not plan for.")
body(("Exos intends to propose to the RIDE Non-Commercial IDIQ"), " once it meets the accounting-system criterion. "
     "Readiness today:")
bullet("Exos does not yet have an approved accounting system under R-DFARS 242.7502, and has no MMAS determination. "
       "A DCAA-compliant timekeeping and project cost-accounting capability is being implemented. Exos will on-ramp "
       "to the Commercial IDIQ first and supports the Government's intent to allow a single proposal to on-ramp to "
       "both IDIQs where criteria are met (CRM #2).", "Business systems.")
bullet("Exos controls its own design, so Government requirement changes go straight to the engineering team that "
       "owns the baseline. Changes are managed through configuration management, interface control documents (ICDs), "
       "and combined systems tests of the integrated vehicle.", "Evolving requirements.")
bullet("For non-commercial work, BLK3's first flight in early 2027 from Spaceport America, New Mexico, is the "
       "planned liftoff within 12 months. The AFRL engine-integration effort sets the pattern for modified-vehicle "
       "missions.", "Planned liftoff.")

# ================= 6 =================
h1("6. Launch Service Offering, Rapid Launch, and Payload Capabilities (RFI topics 2–5)")
h2("6.1  Service offering")
bullet("Dedicated or multi-manifest flights in a standard 636 mm (25.04 in) ID × 1,219 mm (48 in) payload bay, with "
       "payload swap up to integration (CRM #14). Payloads can be installed the day before launch.", "Manifest.")
bullet("The vehicle and payload are recovered intact near the pad. Payloads go back to their owners on launch day.",
       "Recovery.")
bullet("Exos proposes its FAA-licensed operations at Spaceport America (CRM #11). Exos needs only a pad with power "
       "and communications, so other ranges are workable when a task order requires them. Where a task order "
       "requires range-specific approval (e.g., RCC 319), Exos will pursue it for that mission (CRM #12).",
       "Launch site.")
bullet("Exos's published commercial rate for a dedicated BLK3 flight is about $1 million. Firm-fixed-price pricing "
       "will be offered at the task-order level.", "Pricing.")
figure_row([(A + "pug-007-007.png", "Spaceport America Vertical Launch Area: Exos pad, launch control, viewing area (PUG §2.4)."),
            (A + "pug-009-008.png", "BLK3 standard payload bay and adapter plates (PUG §3).")], 3.0)
h2("6.2  Rapid launch (RIDE responsive-launch requirement)")
body("Exos defines rapid launch as a short call-up from a flight-ready, reusable vehicle with minimal ground "
     "infrastructure. Today the vehicle can fly again two days after a mission, using a spare recovery system and "
     "pre-charged high-pressure helium so that a full post-flight inspection still fits in the turnaround. The "
     "mobile launch kit (launch control trailer, crane truck, propellants) deploys from Greenville to the pad in "
     "four days. The limiting factor is range scheduling: Exos's current agreement with the New Mexico Spaceport "
     "Authority, White Sands Missile Range, and the FAA requires 30 days' notice of a launch. To work toward the "
     "RIDE goal of launch within 24 hours, Exos proposes:")
bullet("standing, pre-coordinated airspace and launch windows for RIDE campaigns;")
bullet("classes of payloads pre-approved by the FAA, which Exos is already developing with FAA/AST (PUG §4.2), so "
       "payload review does not hold up launch;")
bullet("a vehicle held flight-ready on alert at the range with late payload installation, and a funded "
       "responsive-launch demonstration task order to prove the timeline.")
h2("6.3  Payload manufacturing and integration capabilities")
body("Standard service includes a mounting plate, an EMI and interference check during the combined systems test, "
     "and the FAA payload review, which Exos manages. Optional services include custom adapter plates, multiple "
     "payloads, payload power (5/12/24 V DC), telemetry-based trigger signals (e.g., at microgravity onset or "
     "apogee), real-time downlink, external antennas and cameras, viewports, payload-bay vacuum modification, "
     "pointing, payload ejection, and special (biological or radiological) payloads. Exos's in-house composite "
     "and machining capability can build custom payload structures and enclosures.")
figure(A + "pug-009-009.png", "BLK3 payload customer connections: triggers A/B (0–24 V DC) and switched payload "
       "power (PUG §3.4).", 4.6)

# ================= 7 =================
h1("7. (D) Mission Assurance")
bullet("Exos supports MA tailored to each customer's risk tolerance. ", "Viewpoint.")
bullet("Yes. If the Government requires its own independent MA for a RIDE mission, regardless of commerciality, "
       "Exos will still propose. The cost and schedule of that MA should be priced into the task order.",
       "Independent Government MA.")
bullet("Exos has not flown under an RSLP SRP-4/OSP-4 MA category. Its MA experience comes from FAA licensing (system "
       "safety, flight-safety and hazard analyses, payload review, readiness reviews with FAA/AST) and from its DoD "
       "SBIR deliverables.", "History.")
bullet("Exos is willing to provide the Attachment 2 analyses that apply to a liquid, single-stage, recoverable "
       "vehicle. Two limits apply. (1) Detailed engine and injector design data and high-resolution telemetry are "
       "export-controlled (ITAR). Exos will provide them to the Government under appropriate controls, but asks that "
       "they not be released to support contractors without an export-compliant NDA. (2) Ordnance and "
       "ordnance-FTS items (A1-2.1) do not apply as written: BLK3 uses autonomous thrust termination, not an ordnance "
       "flight-termination system.", "Data limits.")
bullet("Reliability and statistical deliverables that depend on BLK3 flight history cannot be complete until the "
       "2027 flight campaign. Until then Exos will provide analysis-based versions and update them with flight data.",
       "Barriers.")
bullet("The GNC software terminates thrust if the vehicle would leave the 6.5 km flight hazard area during boost. "
       "Engine cutoff at a predicted 110 km apogee keeps every flight inside the licensed envelope. Each payload gets a "
       "combined systems test, physical fit-up, dry run and abort practice, and a mandatory Mission Readiness Review. "
       "Flight rules include a 10 m/s ground-wind limit. Because the vehicle is reusable, Exos inspects the actual "
       "flown hardware after every flight and feeds the results into the next flight. An expendable vehicle cannot "
       "provide this.", "Reducing launch risk without full MA.")
bullet("Accept FAA license analyses and readiness reviews as MA evidence. Let MA data carry over between missions "
       "on the same vehicle. Use a Category R-style tailored package as the default for developmental and "
       "demonstration missions where the risk sits mostly with the payload.", "Streamlining ideas.")

# ================= 8 =================
h1("8. (E) Feedback on the IDIQ Minimum Guarantee")
bullet("Fund one dedicated suborbital demonstration flight carrying a Government pathfinder or instrumentation "
       "payload. It returns real flight-environment data and validates each awardee's integration process, rather "
       "than producing documents. Launch service user guides already exist, and Exos's Payload User Guide is public.",
       "Non-duplicative deliverable.")
bullet("Studies with immediate value: measuring the payload environment on recoverable suborbital vehicles; a "
       "responsive-launch CONOPS study (range coordination, alert posture, timelines); and range-compatibility "
       "studies (e.g., RCC 319 tailoring for reusable vehicles).", "Technical studies and analyses.")
bullet("Payload-integration training for Government payload teams, plus an MA process walk-through on the "
       "contractor's real data.", "Alternate high-value efforts.")
bullet("Size the minimum so small businesses can carry it on fixed price, and let the minimum be met by a flight "
       "task order, not only by studies.", "Other considerations.")

# ================= 9 =================
h1("9. (F) Additional Feedback and Plans for Future Capability")
bullet("Exos supports requiring a successful liftoff by proposal submission, accepting heritage vehicles owned and "
       "operated by the offeror, and removing the 12-month orbital-pathway language (CRM #5, #19).", "Liftoff criterion.")
bullet("Accept either flight data or a documented 6-DOF analysis on the offeror's controlled baseline, confirmed "
       "by flight data before the first launch task order (CRM #6).", "Mass-to-objective evidence.")
bullet("Exos supports the Government's plan to consider cost at task-order competition (CRM #8). Reusable providers "
       "should be allowed to price multi-flight and campaign task orders, so the Government gets the full per-flight "
       "cost benefit of reuse.", "Reusability.")
bullet("Exos recommends separate suborbital and orbital lanes or CLINs, and would value the updated manifest that "
       "separates them (CRM #1, #10, #13).", "Suborbital lane.")
bullet("Exos offers suborbital launch under RIDE today. Its planned orbital path is the BLK4 Heavy configuration. "
       "BLK4 Heavy depends on future funding, has not flown, and is not offered under this SOC. Exos affiliate "
       "Scorpius Space Launch Company, in which Exos holds an 18% interest, built the composite cryogenic propellant "
       "tanks flown on the Intuitive Machines IM-1 and IM-2 lunar missions. That domestic capability is relevant to "
       "in-space propellant storage and mobility. (RFI topic 3; CRM #10)", "Future capability.")

h1("10. Point of Contact")
body("John Quinn, Cofounder & CEO, Exos Aerospace Systems & Technologies, Inc. — jquinn@exosaero.com — "
     "+1 (972) 740-8355 — 299 FM 1903, Greenville, TX 75402. Exos welcomes a one-on-one session with RSLP on BLK3 "
     "capability, mission assurance, and on-ramp planning.")

doc.save(OUT)
print("WROTE", OUT)
