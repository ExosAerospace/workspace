#!/usr/bin/env python3
"""Convert EPIC RFI response markdown to a formatted .docx"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import re

doc = Document()

# Page margins
for section in doc.sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)

# Helper functions
def add_heading_styled(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)
    return h

def add_para(text, bold=False, italic=False, size=None, align=None, space_after=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    if align:
        p.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        for paragraph in hdr_cells[i].paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(10)
    for row_data in rows:
        row_cells = table.add_row().cells
        for i, val in enumerate(row_data):
            row_cells[i].text = val
            for paragraph in row_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)
    return table

def add_separator():
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)

# === COVER PAGE INFO ===
add_para('ENTERPRISE PROTOTYPE INITIATIVE CONSORTIUM (EPIC)', bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
add_para('RFI Response — RFI-RFZF-B001', bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)

add_para('Submitted to:', bold=True, size=11, space_after=2)
add_para('Air Force Research Laboratory (AFRL)\nFA8750 AFRL RIK, Rome, NY 13441', size=11, space_after=6)

add_para('Points of Contact:', bold=True, size=11, space_after=2)
add_para('Catherine Hulser, Agreements Officer — catherine.hulser@us.af.mil\nErica Ogundadegbe, Agreements Officer — erica.ogundadegbe@us.af.mil\nMatthew Shaver, Agreement Officer Representative — matthew.shaver@us.af.mil', size=10, space_after=12)

add_para('Submitted by:', bold=True, size=11, space_after=2)
add_para('Exos Aerospace Systems & Technologies, Inc.\n299 FM 1903, Greenville, TX 75402\nwww.exosaero.com\nCAGE Code: 7EMY6  |  UEI: CK24BPZGF854', size=11, space_after=6)

add_para('Point of Contact:', bold=True, size=11, space_after=2)
add_para('John Quinn, Chief Executive Officer\njquinn@exosaero.com  |  +1-972-740-8355', size=11, space_after=6)

add_para('Date: May 12, 2026', bold=True, size=11, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=12)

doc.add_page_break()

# === 1. EXECUTIVE SUMMARY ===
add_heading_styled('1. Executive Summary', level=1)

add_para('Exos Aerospace Systems & Technologies, Inc. (Exos) respectfully submits this response to RFI-RFZF-B001 in support of the Air Force Research Laboratory\'s Enterprise Prototype Initiative Consortium (EPIC). Exos is a nontraditional defense contractor and small business that designs, builds, tests, and operates reusable suborbital launch vehicles and advanced propulsion systems. We are interested in participating as a Project-Level Performer within the EPIC consortium framework, providing rapid-cycle hardware prototyping, flight test, and technology demonstration services aligned with AFRL mission areas.', space_after=6)

add_para('Exos is one of only three U.S. companies holding an active FAA license for reusable suborbital launch operations, and we maintain an active USAF SBIR Phase II contract (FA9300-25-C-6022) with the Air Force Test Center for Rotating Detonation Rocket Engine (RDRE) development. Our affiliate, Scorpius Space Launch Company, holds the only known TRL 9 Type 5 cryogenic tank technology with demonstrated lunar operational heritage.', space_after=6)

add_para('As a nontraditional defense contractor and small business, Exos satisfies the participation requirements under 10 U.S.C. §4022 for Other Transaction for Prototype authority and brings hardware-first, flight-test-driven capabilities to the EPIC consortium structure.', space_after=12)

# === 2. ORGANIZATIONAL CAPABILITIES ===
add_heading_styled('2. Organizational Capabilities', level=1)

add_heading_styled('2.1 Core Competencies', level=2)

add_para('Reusable Suborbital Launch Platform (BLK3 PSRLV)', bold=True, space_after=2)
add_bullet('Reusable launch vehicle capable of delivering 50–135 kg payloads above the Kármán line (100+ km)')
add_bullet('FAA-licensed launch operations from Spaceport America, NM (14 CFR §431, transitioning to Part 450); Greenville, TX is the manufacturing and hover-test facility')
add_bullet('Rapid turnaround capability: weeks between flights, multiple flights per month')
add_bullet('3–4 minutes microgravity; Mach 3–5+ reentry; full vehicle recovery and reuse')
add_bullet('Proven as a rapid-cycle testbed for technology maturation and flight qualification')

add_para('Rotating Detonation Rocket Engine (RDRE) Development', bold=True, space_after=2)
add_bullet('Active USAF SBIR Phase II (FA9300-25-C-6022, $1.9M) for Hybrid Vehicle Rocket with Government-Furnished RDRE')
add_bullet('NASA Marshall Space Flight Center Data Usage Agreement for RDRE development')
add_bullet('Targeting 25%+ Isp improvement over conventional combustion')
add_bullet('Pathfinder flight demonstration planned Q1–Q2 2027')

add_para('Cryogenic Systems (via Scorpius Space Launch Company)', bold=True, space_after=2)
add_bullet('Type 5 cryogenic tank technology at TRL 9 — flight-proven on Intuitive Machines Odysseus (IM-1) and Athena lunar landers')
add_bullet('Composite Overwrapped Pressure Vessel (COPV) manufacturing')
add_bullet('Applications: long-duration zero-boiloff cryo storage, in-space refueling depot architecture, reusable launch vehicle tankage')

add_heading_styled('2.2 Prototype Delivery Capabilities', level=2)
add_para('Exos maintains end-to-end prototype delivery capability across:', space_after=2)
add_bullet('Hardware: ', bold_prefix='Hardware: ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Hardware: ')
run.bold = True
p.add_run('Propulsion systems, launch vehicle structures, cryogenic tanks, payload integration hardware, avionics, recovery systems')

add_bullet('', bold_prefix='Software: ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Software: ')
run.bold = True
p.add_run('Flight control software, mission planning tools, telemetry and data acquisition systems')

add_bullet('', bold_prefix='Technical Data: ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Technical Data: ')
run.bold = True
p.add_run('Flight test reports, performance analyses, design documentation, safety analyses')

add_bullet('', bold_prefix='Test Services: ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Test Services: ')
run.bold = True
p.add_run('Static fire testing, flight testing, environmental testing, TRL advancement campaigns')

add_heading_styled('2.3 Facilities', level=2)
add_table(
    ['Facility', 'Location', 'Capabilities'],
    [
        ['HQ & Integration', 'Greenville, TX', 'Vehicle assembly, payload integration, avionics lab'],
        ['Licensed Launch Site', 'Spaceport America, NM', 'FAA-licensed launch operations, propellant handling (14 CFR §431)'],
        ['Scorpius Manufacturing', 'Torrance, CA', 'Cryogenic tank fabrication, COPV production'],
    ]
)

# === 3. OTA EXPERIENCE ===
add_heading_styled('3. Other Transaction Authority Experience', level=1)
add_para('Exos has direct experience operating under government prototype and technology development agreements:', space_after=4)

add_bullet('', bold_prefix='USAF SBIR Phase II (FA9300-25-C-6022): ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('USAF SBIR Phase II (FA9300-25-C-6022): ')
run.bold = True
p.add_run('Active $1.9M contract with Air Force Test Center (AFTC) for RDRE hardware development and flight test integration. Milestone-based performance with hardware deliverables.')

add_bullet('', bold_prefix='USAF SBIR Phase I (FA9300-24-P-6006): ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('USAF SBIR Phase I (FA9300-24-P-6006): ')
run.bold = True
p.add_run('Completed $189K contract for hypersonic vehicle development concept.')

add_bullet('', bold_prefix='NASA MSFC Data Usage Agreement: ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('NASA MSFC Data Usage Agreement: ')
run.bold = True
p.add_run('Active collaboration for RDRE technology development with Marshall Space Flight Center.')

add_bullet('', bold_prefix='NASA REDDI/Flight Opportunities Programs: ')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('NASA REDDI/Flight Opportunities Programs: ')
run.bold = True
p.add_run('Prior suborbital flight services under NASA commercial programs.')

add_para('While Exos has not served as an OT Consortium Manager, our experience as a performer under milestone-based government agreements with hardware deliverables directly maps to the Project-Level Performer role envisioned under EPIC. We are experienced in operating within structured reporting frameworks (monthly technical status reports, quarterly financial reports, milestone reviews).', space_after=12)

# === 4. QUALITY CONTROL ===
add_heading_styled('4. Quality Control & Risk Management', level=1)

add_heading_styled('4.1 Quality Assurance', level=2)
add_para('Exos maintains quality control practices consistent with aerospace flight hardware production:', space_after=2)
add_bullet('Configuration management and change control processes for flight hardware')
add_bullet('Inspection and acceptance protocols for propulsion, structural, and avionics subsystems')
add_bullet('Traceability of materials and components through the supply chain')
add_bullet('Post-flight analysis and anomaly resolution processes')
add_bullet('Documentation and lessons-learned integration across flight campaigns')

add_heading_styled('4.2 Risk Management', level=2)
add_para('Exos employs a structured risk management approach for all prototype and flight programs:', space_after=2)

add_bullet('')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Risk Identification: ')
run.bold = True
p.add_run('Technical, schedule, cost, and safety risks catalogued at program initiation')

add_bullet('')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Risk Mitigation: ')
run.bold = True
p.add_run('Active mitigation plans with quantified residual risk acceptance')

add_bullet('')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Schedule Management: ')
run.bold = True
p.add_run('Milestone-based execution with regular progress reviews')

add_bullet('')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Safety: ')
run.bold = True
p.add_run('FAA-compliant safety protocols for launch operations, propellant handling, and personnel protection')

add_bullet('')
p = doc.paragraphs[-1]
p.clear()
run = p.add_run('Reusability Advantage: ')
run.bold = True
p.add_run('Vehicle recovery and reuse reduces per-iteration cost and schedule risk for prototype campaigns, enabling faster design-test-learn cycles')

# === 5. SECURITY ===
add_heading_styled('5. Security Practices', level=1)
add_para('Exos Aerospace is registered and active in SAM.gov. The company operates under the following security framework:', space_after=4)

for label, desc in [
    ('ITAR/EAR Compliance: ', 'Exos and Scorpius technologies are subject to ITAR controls. The company maintains Technology Control Plans (TCPs) and compliance programs for export-controlled articles and technical data.'),
    ('Cybersecurity: ', 'Information systems and communications are managed in accordance with NIST SP 800-171 requirements for controlled unclassified information (CUI).'),
    ('Physical Security: ', 'Controlled access to manufacturing, integration, and launch facilities.'),
    ('Foreign Ownership: ', 'Exos Aerospace is a U.S.-owned and U.S.-controlled entity with no Foreign Ownership, Control, or Influence (FOCI). The company maintains a European subsidiary (Exos Aerospace Italia, Srl) for allied-nation commercial operations, structured to maintain ITAR compliance.'),
    ('Personnel Security: ', 'Key personnel are U.S. persons. Exos does not currently hold a facility clearance; however, facility and individual clearance applications can be initiated as required by specific Project-Level Orders under the EPIC consortium framework.'),
]:
    add_bullet('')
    p = doc.paragraphs[-1]
    p.clear()
    run = p.add_run(label)
    run.bold = True
    p.add_run(desc)

# === 6. PERSONNEL ===
add_heading_styled('6. Personnel Qualifications', level=1)
add_table(
    ['Name', 'Title', 'Qualifications'],
    [
        ['John Quinn', 'CEO & Cofounder', 'Executive leadership of reusable launch programs; government contract management; investor and partner relations'],
        ['Neil Milburn', 'COO & Technical Lead', 'Decades of aerospace engineering experience; technical authority for BLK3 PSRLV and RDRE programs; government program execution'],
    ]
)
add_para('')
add_para('Exos maintains a lean technical team with deep expertise in propulsion, structures, avionics, and flight operations. No personnel currently hold active security clearances. For PLO efforts requiring cleared personnel, Exos has established teaming relationships and can augment accordingly. Clearance applications will be processed in coordination with the Consortium Manager and cognizant security authority as specific PLO requirements dictate.', space_after=12)

# === 7. PAST PERFORMANCE ===
add_heading_styled('7. Relevant Past Performance', level=1)
add_table(
    ['Program', 'Customer', 'Value', 'Status', 'Relevance'],
    [
        ['SBIR Phase II — RDRE', 'USAF AFTC (FA9300-25-C-6022)', '$1.9M', 'Active', 'Hardware prototyping under milestone-based govt. agreement'],
        ['SBIR Phase I — Hypersonic', 'USAF AFTC (FA9300-24-P-6006)', '$189K', 'Complete', 'Concept development & feasibility'],
        ['RDRE Development', 'NASA MSFC (DUA)', 'N/A', 'Active', 'Joint technology development with government lab'],
        ['Cryo Tanks — IM-1 Odysseus', 'Intuitive Machines', 'Commercial', 'Complete', 'TRL 9 cryo tanks on lunar surface'],
        ['Cryo Tanks — Athena', 'Intuitive Machines', 'Commercial', 'Complete', 'Second lunar mission, flight-proven'],
        ['Launch Services Agreement', 'entX Pty Ltd (Australia)', 'Commercial', 'Active', 'International commercial payload customer'],
        ['BLK3 Wet Lease', 'Space COTAN / HOSPO (Japan)', 'Commercial', 'Active', 'International launch capability partnership'],
    ]
)

# === 8. FEEDBACK ===
add_heading_styled('8. Feedback on EPIC Structure', level=1)
add_para('In response to AFRL\'s request for feedback on how the Government can best satisfy its needs:', space_after=4)

feedback = [
    ('1. Nontraditional Contractor Access: ', 'The EPIC consortium should actively lower barriers for nontraditional defense contractors and small businesses to participate as Project-Level Performers. Many innovative hardware-focused companies (propulsion, launch systems, advanced materials) lack the administrative infrastructure to navigate complex consortium onboarding. Streamlined onboarding and simplified proposal formats for PLOs would increase the diversity and quality of prototype solutions available to AFRL.'),
    ('2. Hardware Prototype Emphasis: ', 'We encourage AFRL to ensure the EPIC structure accommodates hardware-intensive prototyping (propulsion, flight vehicles, cryogenic systems) alongside software and IT-centric projects. Milestone-based payments and appropriate cost structures for hardware builds and flight tests will attract the companies best positioned to deliver physical prototypes.'),
    ('3. Flight Test as TRL Advancement: ', 'Exos recommends that the EPIC framework recognize commercial reusable launch platforms as TRL advancement tools. Rapid-cycle suborbital flight testing can mature technologies from TRL 4–5 to TRL 6–7 in months rather than years, directly supporting AFRL\'s goal of timely capability delivery.'),
    ('4. Security Tiering: ', 'For PLOs that do not require classified work, we recommend a tiered security approach that does not impose TS/SCI overhead on unclassified prototyping efforts, which would unnecessarily exclude innovative small businesses and nontraditional contractors.'),
]
for label, desc in feedback:
    p = doc.add_paragraph()
    run = p.add_run(label)
    run.bold = True
    p.add_run(desc)
    p.paragraph_format.space_after = Pt(8)

# === 9. CONCLUSION ===
add_heading_styled('9. Conclusion', level=1)
add_para('Exos Aerospace is a qualified nontraditional defense contractor and small business with active USAF contracts, flight-proven hardware, and demonstrated prototype delivery capability. We are interested in participating as a Project-Level Performer within the EPIC consortium and welcome the opportunity to contribute rapid-cycle hardware prototyping and flight test services to AFRL\'s technology pipeline.', space_after=6)
add_para('We look forward to continued engagement as the EPIC program develops.', space_after=12)

add_separator()

add_para('Exos Aerospace Systems & Technologies, Inc.', bold=True, size=11, space_after=2)
add_para('299 FM 1903, Greenville, TX 75402', size=11, space_after=2)
add_para('John Quinn, CEO — jquinn@exosaero.com — +1-972-740-8355', size=11, space_after=8)
add_para('This response is submitted for informational purposes only in response to RFI-RFZF-B001 and does not constitute an offer or commitment.', italic=True, size=9, space_after=0)

# Save
output = '/Users/exomac/.openclaw/workspace/drafts/EPIC-RFI-RFZF-B001-Exos-Aerospace-Response.docx'
doc.save(output)
print(f'Saved: {output}')
