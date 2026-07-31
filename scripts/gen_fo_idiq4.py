#!/usr/bin/env python3
"""Generate the clean FO IDIQ 4 on-ramp submission docx with Jon's pricing revision
(full-bay floor $1,012,500, 3-day turnaround standardized) plus the review fixes."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
NAVY=RGBColor(0x0B,0x1F,0x3A); ACCENT=RGBColor(0x1F,0x4E,0x79); GRAY=RGBColor(0x44,0x44,0x44)
OUT="/Users/exomac/.openclaw/workspace/drafts/Exos_FO_IDIQ4_OnRamp_Formal_Submission.docx"

HEADER_IMG="/Users/exomac/.openclaw/workspace/mission-control/brand-assets/exos-letterhead-header.png"
FOOTER_IMG="/Users/exomac/.openclaw/workspace/mission-control/brand-assets/exos-letterhead-footer.png"

d=Document()
for s in d.sections:
    s.left_margin=Inches(0.8); s.right_margin=Inches(0.8)
    s.top_margin=Inches(1.5); s.header_distance=Inches(0.4)
    s.bottom_margin=Inches(1.2); s.footer_distance=Inches(0.35)
    # Exos brand header (wordmark, left) and footer ("Aerospace Systems & Technologies", right)
    hp=s.header.paragraphs[0]; hp.alignment=WD_ALIGN_PARAGRAPH.LEFT
    hp.add_run().add_picture(HEADER_IMG, width=Inches(5.0))
    fp=s.footer.paragraphs[0]; fp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    fp.add_run().add_picture(FOOTER_IMG, width=Inches(5.0))
d.styles["Normal"].font.name="Calibri"; d.styles["Normal"].font.size=Pt(10.5)

def p(t,size=10.5,bold=False,color=None,after=5,before=0,italic=False,align=None):
    x=d.add_paragraph();x.paragraph_format.space_after=Pt(after);x.paragraph_format.space_before=Pt(before)
    if align:x.alignment=align
    r=x.add_run(t);r.bold=bold;r.italic=italic;r.font.size=Pt(size)
    if color:r.font.color.rgb=color
    return x
def h1(t): p(t,size=13,bold=True,color=NAVY,before=10,after=4)
def h2(t): p(t,size=11,bold=True,color=ACCENT,before=6,after=3)
def bullet(t):
    x=d.add_paragraph(style="List Bullet");x.paragraph_format.space_after=Pt(2)
    x.add_run(t).font.size=Pt(10.5)
def table(rows,header=True,widths=None):
    t=d.add_table(rows=0,cols=len(rows[0]));t.style="Light Grid Accent 1"
    for i,row in enumerate(rows):
        cells=t.add_row().cells
        for j,val in enumerate(row):
            cells[j].text=""
            par=cells[j].paragraphs[0];par.paragraph_format.space_after=Pt(1)
            run=par.add_run(str(val));run.font.size=Pt(9.5)
            if header and i==0: run.bold=True
    return t

# ---- Title ----
p("NASA Flight Opportunities IDIQ 4 — On-Ramp Submission",size=15,bold=True,color=NAVY,after=1)
p("Suborbital Payload Flight and Integration Services — Exos Aerospace BLK3",size=11,bold=True,color=GRAY,after=8)
for line in [
 "Solicitation Reference: 80AFRC23R0001 (NASA Armstrong Flight Research Center)",
 "Contract Vehicle: Suborbital/Hosted Orbital Flight and Payload Integration Services 4 (FO IDIQ 4)",
 "NAICS: 481212 — Nonscheduled Chartered Freight Air Transportation",
 "Offeror: Exos Aerospace Systems & Technologies, Inc., 299 FM 1903, Greenville, TX 75402",
 "Point of Contact: John Quinn, Cofounder and CEO — +1-972-740-8355 — www.exosaero.com",
 "Date: July 21, 2026"]:
    p(line,size=9.5,color=GRAY,after=1)
p("Exos Aerospace offers its BLK3 reusable suborbital rocket as a qualified vehicle under FO IDIQ 4. Exos is "
  "one of only three FAA-licensed reusable rocket launch providers in the United States, with commercial "
  "suborbital operating heritage dating to 2018. BLK3 provides payload access to the space environment above "
  "100 km with intact hardware return and short vehicle turnaround, directly matching the Flight Opportunities "
  "Program objective of advancing technology readiness through repeated access to high-altitude, reduced-gravity, "
  "and vacuum environments. Sections 2 through 5 below constitute Exos's formal on-ramp response.",before=6,after=4)

# ---- Section 2 ----
h1("Section 2: Vehicle Qualification — BLK3")
h2("2.1 Regulatory Compliance")
bullet("FAA launch license: Reusable launch vehicle license under 14 CFR §431, renewed March 13, 2026, authorizing launch operations from Spaceport America, NM. Greenville, TX is the manufacturing, integration, and hover-test facility. Transition to a 14 CFR Part 450 license is in progress.")
bullet("Reusable launch vehicle: Vehicle designed and operated for reuse (VTVL — vertical takeoff, vertical landing).")
bullet("US-incorporated commercial launch provider: Exos Aerospace Systems & Technologies, Inc., Greenville, TX.")
h2("2.2 Flight Profile")
table([["Parameter","Value"],
 ["Vehicle designation","BLK3 (Block 3 PSRLV)"],
 ["Apogee","greater than or equal to 100 km (Kármán line — space environment)"],
 ["Boost-phase acceleration","less than 4 g"],
 ["Peak transient shock","approximately 7 g (brief)"],
 ["Microgravity duration","approximately 90+ seconds (coast phase above 50 km)"],
 ["Payload return","Yes — intact hardware recovery"],
 ["Vehicle turnaround","3-day (target)"],
 ["Operating heritage","Commercial suborbital operations since 2018 (SARGE platform)"],
 ["BLK3 next commercial flight","Targeted Q1 2027, Spaceport America, NM"]])
h2("2.3 Payload Accommodation")
table([["Parameter","Value"],
 ["Maximum payload mass","135 kg"],
 ["Payload bay dimensions","25 in (dia) x 36 in (length), cylindrical"],
 ["Payload environments","Microgravity, vacuum, high altitude, suborbital thermal"],
 ["Integration lead time","90 days (target)"],
 ["Electrical interface","28 VDC, MIL-SPEC connectors (confirmed per payload)"],
 ["Data / telemetry","Downlink available; onboard computer stack collects sensor data"],
 ["Customer access","Pre-launch encapsulation support"]])
h2("2.4 Relevant Environments Provided")
for b in ["Microgravity: approximately 90+ seconds above the effective gravity floor.",
 "Vacuum / low atmospheric density: at 100 km altitude.",
 "High altitude: payload rides the full ground-to-apogee flight profile.",
 "Thermal cycling: ascent heating followed by coast-phase cold soak.",
 "Vibration and shock: characterized per flight; data provided to payload customers."]: bullet(b)
h2("2.5 Vehicle Heritage")
for b in ["Commercial suborbital operating lineage since 2018 (SARGE, Exos's predecessor VTVL platform).",
 "BLK3 developed under a USAF/AFWERX Phase II SBIR (August 2022) as a reusable prototype.",
 "Active USAF contract: Phase II FA9300-25-C-6022 (propulsion and reusable launch technology).",
 "Exos is the commercial successor to Armadillo Aerospace, carrying that VTVL lineage forward."]: bullet(b)

# ---- Section 3 ----
h1("Section 3: Management Proposal")
h2("3.1 Company Overview")
p("Exos Aerospace Systems & Technologies, Inc. is a privately held US aerospace company based in Greenville, "
  "Texas, with launch operations at Spaceport America, New Mexico. Founded as the commercial successor to "
  "Armadillo Aerospace, Exos has operated reusable suborbital launch vehicles commercially since 2018. Exos "
  "holds an 18% ownership stake in Scorpius Space Launch Company, with a right of first refusal on remaining "
  "ownership, providing access to Type 5 cryogenic tank technology with flight heritage from the Intuitive "
  "Machines Odysseus and Athena lunar missions.")
h2("3.2 Key Personnel")
table([["Name","Role","Relevance"],
 ["John Quinn","Cofounder and CEO","Prime customer interface, program oversight"],
 ["Neil Milburn","VP Operations","Flight operations, FAA interface, safety"],
 ["Phil Eaton","Engineering lead","Vehicle integration, payload accommodation"]])
h2("3.3 Facilities")
for b in ["Primary site: 299 FM 1903, Greenville, TX 75402 — final manufacturing, assembly, integration, and acceptance testing.",
 "Composite structures: raw composite fabrication via Scorpius (Torrance, CA); final build and test in Greenville, TX.",
 "Launch site: Spaceport America, Truth or Consequences, NM — licensed launch pad.",
 "Mobile command module: self-contained; no fixed infrastructure required at the launch site beyond pad, power, and communications.",
 "International presence: Exos Aerospace Italia, Srl (Torino, Italy); HOSPO / Space Cotan engagement (Japan)."]: bullet(b)
h2("3.4 Insurance and Bonding")
bullet("Exos maintains launch liability insurance consistent with FAA licensing requirements.")
bullet("Government third-party indemnification is addressed per current Launch Services Purchase Act authorities.")

# ---- Section 4 ----
h1("Section 4: Past Performance")
table([["Contract / Program","Customer","Relevance","Status"],
 ["SARGE suborbital flights (2018–present)","Commercial","Operational VTVL reusable launch and payload hosting","Operating heritage"],
 ["USAF AFWERX Phase II SBIR","US Air Force (AFWERX)","BLK3 development as reusable prototype","Complete"],
 ["Phase II FA9300-25-C-6022","USAF (AFRL)","Active propulsion and reusable launch technology contract","Active"],
 ["Scorpius Type 5 cryo tanks","Intuitive Machines / NASA","Exos-enabled fuel and LOX tanks on Odysseus and Athena lunar missions","Complete (TRL 9)"],
 ["FAA §431 reusable launch license (renewed 3/13/26)","FAA / AST","Active reusable launch vehicle license; Part 450 transition in progress","Active"]])

# ---- Section 5 ----
h1("Section 5: Rough Order of Magnitude (ROM) Pricing")
p("Rates below are illustrative ROM for FO IDIQ 4 proposal purposes and are subject to confirmation of the "
  "final pricing tier. A full multi-year price-volume schedule will be provided at formal submission. Exos "
  "maintains a live pricing reference at www.exosaero.com/pricing.",italic=True,after=4)
h2("5.1 Payload Slot Pricing (by the slot)")
table([["Configuration","ROM Price","Notes"],
 ["Full bay (135 kg, 25x36)","$1,012,500 – $1,200,000","Includes integration support, flight, recovery"],
 ["Half bay (~65 kg)","$506,250 – $650,000","Shared manifest"],
 ["Dedicated small experiment","$75,000 – $250,000","Mass under 10 kg, standard interfaces"],
 ["Re-flight (same experiment)","Discount scales linearly with the fraction of the payload bay reflown: 10% at 75% of the bay, up to 15% for a full-bay re-flight","Vehicle reuse amortization"]])
h2("5.2 Integration Services (NRE)")
table([["Service","ROM Price"],
 ["Payload accommodation study","$15,000 – $35,000"],
 ["Integration support (customer team at Greenville)","$5,000 – $10,000 per week"],
 ["Telemetry data package","See www.exosaero.com/pricing"],
 ["ITAR-controlled payload handling","Case-by-case"]])
h2("5.3 Optional Enhancements")
table([["Option","Notes"],
 ["Dedicated flight (single customer)","10% below the full-bay slot price"],
 ["Accelerated booking (60–90 days pre-flight, inside the standard 90-day integration window)","Plus 20%"],
 ["On-site mission integration support","Included, standard"]])

# ---- Appendix A ----
h1("Appendix A: Requirements Compliance Matrix (supplementary)")
table([["FO IDIQ 4 Requirement","Exos BLK3 Response","Status"],
 ["FAA-licensed US commercial launch vehicle","§431 license active (renewed 3/13/26); Part 450 transition in progress","Compliant"],
 ["Access to space environment (over 50 km altitude)","100 km apogee","Compliant"],
 ["Payload hosting by the slot","135 kg / 25x36 bay","Compliant"],
 ["Payload integration services","Full integration support available","Compliant"],
 ["Suborbital vehicle for high-altitude environment","Suborbital VTVL","Compliant"],
 ["Vehicle reusability (multi-flight cadence)","VTVL reusable; 3-day turnaround target","Compliant"],
 ["Researcher seats (by the seat)","Not available on BLK3 (cargo only; no human rating)","N/A"],
 ["Orbital capability","Not offered under this suborbital vehicle; Exos BLK4H orbital vehicle is a future roadmap item (targeted 2031)","N/A — not required for suborbital slot"],
 ["NAICS 481212 eligibility","Yes (under 1,500 employees)","Compliant"],
 ["Mission assurance and systems engineering support","Available","Compliant"],
 ["Government property / GFE compatibility","Case-by-case","TBD"],
 ["Data rights / SBIR data-rights protections","FAR Part 12 commercial baseline","Compliant"]])
p("Net assessment: BLK3 meets all mandatory suborbital payload-hosting requirements for FO IDIQ 4. Exos does "
  "not offer researcher seats (no human-spaceflight rating) or orbital capability, neither of which is required "
  "to qualify as a suborbital payload provider.",before=6)

d.save(OUT); print("wrote",OUT)
