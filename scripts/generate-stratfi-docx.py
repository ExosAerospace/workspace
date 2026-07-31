#!/usr/bin/env python3
"""Generate STRATFI PY26.1 Maximum Funding Proposal .docx with Exos letterhead styling."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os

ASSETS = '/Users/exomac/.openclaw/workspace/assets'
OUT = '/Users/exomac/.openclaw/workspace/drafts/STRATFI-PY26-1-Exos-RDRE-15M.docx'

doc = Document()

for section in doc.sections:
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.01)
    section.footer_distance = Inches(0.01)

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
style.paragraph_format.space_after = Pt(4)

NAVY = RGBColor(0x1B, 0x3A, 0x5C)
DARK = RGBColor(0x33, 0x33, 0x33)

def h1(text):
    h = doc.add_heading(text, level=1)
    for r in h.runs:
        r.font.color.rgb = NAVY; r.font.size = Pt(14)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(6)

def h2(text):
    h = doc.add_heading(text, level=2)
    for r in h.runs:
        r.font.color.rgb = NAVY; r.font.size = Pt(12)
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(4)

def para(text, bold=False, size=None, align=None, after=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.color.rgb = DARK
    if size: run.font.size = Pt(size)
    if align: p.alignment = align
    if after is not None: p.paragraph_format.space_after = Pt(after)
    return p

def bullet(text):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(text)
    r.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(2)

def bold_bullet(label, desc):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(label)
    r.bold = True; r.font.color.rgb = DARK
    r2 = p.add_run(desc)
    r2.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(2)

def add_table(headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for paragraph in hdr[i].paragraphs:
            for run in paragraph.runs:
                run.bold = True; run.font.size = Pt(9)
    for row_data in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row_data):
            cells[i].text = val
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)

# --- LOGO ---
logo = os.path.join(ASSETS, 'exos-letterhead-logo.png')
if os.path.exists(logo):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(logo, width=Inches(2.5))
    para('', after=4)

# --- COVER ---
para('SpaceWERX PY26.1 STRATFI', bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para('NOTICE OF OPPORTUNITY \u2014 PROPOSAL SUBMISSION', bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)

para('BLK3/BLK4 RDRE-Powered Reusable Vehicle Program', bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para('From Hover Test to Operational DoD Hypersonic\nFlight Test and Space Propulsion Transition', size=11, align=WD_ALIGN_PARAGRAPH.CENTER, after=16)

details = [
    ('Company:', 'Exos Aerospace Systems & Technologies, Inc.'),
    ('Address:', '299 FM 1903, Greenville, TX 75402'),
    ('Eligible Phase II:', 'FA9300-25-C-6022 ($1,897,824)'),
    ('CAGE Code:', '7EMY6'),
    ('UEI:', 'CK24BPZGF854'),
    ('STRATFI Request:', '$15,000,000'),
    ('Period of Performance:', '36 months'),
    ('CEO / Primary Contact:', 'John Quinn \u2014 jquinn@exosaero.com \u2014 +1-972-740-8355'),
    ('CTO / Technical Contact:', 'Russell Blink \u2014 rblink@exosaero.com'),
    ('Classification:', 'Unclassified'),
    ('Date:', 'May 2026'),
]
for label, val in details:
    p = doc.add_paragraph()
    r = p.add_run(label + ' ')
    r.bold = True; r.font.color.rgb = DARK; r.font.size = Pt(10)
    r2 = p.add_run(val)
    r2.font.color.rgb = DARK; r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# --- EXECUTIVE SUMMARY ---
h1('1. Executive Summary')
para('Exos Aerospace proposes a $15M STRATFI investment to transition the RDRE technology developed under SBIR Phase II (FA9300-25-C-6022) from hover test demonstration through full suborbital flight qualification on BLK3, then scale to the BLK4 multi-purpose hypersonic vehicle \u2014 delivering both operational flight test services and an RDRE-powered hypersonic platform to the DoD.')

para('This is a two-vehicle, full-spectrum transition program:', bold=True, after=4)
bold_bullet('BLK3 (Near-Term): ', 'Flight-qualify RDRE on the Precision Suborbital Reusable Launch Vehicle. Establish BLK3 as an on-demand DoD flight test service. Demonstrate rapid-turnaround reusable operations.')
bold_bullet('BLK4 (Mid-Term): ', 'Scale RDRE propulsion to the BLK4 hypersonic vehicle (48 in dia, ~48 ft length, 27,300 lb GLOW). Demonstrate RDRE-powered flight across SRBM through IRBM-class profiles at speeds up to Mach 20. Deliver a prototype operational hypersonic vehicle with RDRE propulsion.')

para('Combined, these two vehicles transition RDRE from laboratory demonstration to flight-demonstrated operational capability \u2014 spanning suborbital test services (BLK3) and hypersonic weapon/test vehicle applications (BLK4).', after=8)

# --- PROBLEM STATEMENT ---
h1('2. Problem Statement')
bold_bullet('RDRE Has No Flight Demonstration Pathway: ', 'Despite extensive ground testing by AFRL, NASA, and industry, no RDRE has been flight-demonstrated on a reusable platform that enables iterative testing. Without flight data, RDRE cannot transition to operational spacecraft or weapon system propulsion.')
bold_bullet('DoD Lacks Affordable Flight Test Access: ', 'Current options: orbital launches ($50M+, non-recoverable), sounding rockets (single-use), or government range-dependent flights (18\u201324 month scheduling). No rapid-turnaround reusable flight test service exists.')
bold_bullet('Hypersonic Vehicle Propulsion Needs a Step Change: ', 'Current hypersonic vehicle propulsion is constrained by conventional combustion efficiency limits. RDRE offers 25%+ Isp improvement \u2014 enabling longer range, higher speed, and greater payload fraction.')

doc.add_page_break()

# --- TECHNICAL APPROACH ---
h1('3. Technical Approach \u2014 Four-Task Program ($15M / 36 Months)')

h2('Task 1: RDRE Suborbital Flight Demonstration on BLK3')
para('Budget: $4,500,000 (30%) | Period: Months 1\u201318', bold=True, after=4)
para('Integrate RDRE from Phase II hover test configuration into BLK3 PSRLV. Execute minimum 5 instrumented RDRE suborbital flights to 100+ km altitude.')
para('Data collection:', bold=True, after=2)
bullet('Detonation wave stability under flight dynamic loads')
bullet('Thermal performance in altitude environments')
bullet('Propellant feed behavior under flight g-loading')
bullet('RDRE/vehicle system interactions')
bullet('Start/restart reliability in flight conditions')
para('Deliverables:', bold=True, after=2)
bullet('RDRE flight-qualified configuration')
bullet('5+ instrumented suborbital flights with full data packages')
bullet('Flight performance database for AFRL/NASA')
bullet('Post-flight hardware inspection reports')
bullet('RDRE flight operations manual')

h2('Task 2: BLK3 DoD Flight Test Service Qualification')
para('Budget: $3,000,000 (20%) | Period: Months 6\u201324', bold=True, after=4)
para('Establish BLK3 as a qualified DoD flight test service:')
bullet('Standardized DoD payload interface specification')
bullet('Security and classification handling for DoD payloads')
bullet('Flight environment characterization dataset')
bullet('Demonstration of 4-week turnaround between flights')
bullet('4+ demonstration flights with representative DoD payloads')
para('Deliverables:', bold=True, after=2)
bullet('DoD Flight Test Service qualification package')
bullet('Payload integration guide for DoD customers')
bullet('4+ demonstration flights')
bullet('Turnaround time demonstration (30-day target)')
bullet('Phase III SBIR transition plan')

h2('Task 3: BLK4 RDRE-Powered Hypersonic Vehicle Development')
para('Budget: $5,500,000 (37%) | Period: Months 6\u201333', bold=True, after=4)
para('Scale RDRE propulsion to BLK4 hypersonic vehicle:', after=4)

add_table(
    ['Parameter', 'Specification'],
    [
        ['Diameter', '48 inches'],
        ['Length', '~48 ft'],
        ['GLOW', '27,300 lb'],
        ['Lofted Trajectory', '~2,200 km range, ~1,100 km apogee, Mach 20'],
        ['Depressed Trajectory', '~1,200 km range, ~110 km apogee, Mach 15'],
        ['Profile Coverage', 'SRBM through IRBM-class'],
    ]
)

para('', after=4)
para('Activities:', bold=True, after=2)
bullet('RDRE combustor scaling informed by BLK3 flight data')
bullet('BLK4 detailed design with RDRE propulsion integration')
bullet('Scorpius Type 5 cryogenic tank integration (TRL 9 heritage)')
bullet('Structural and thermal analysis for hypersonic flight envelope')
bullet('Critical Design Review for RDRE-powered BLK4')
bullet('Ground test of integrated RDRE/BLK4 propulsion system')
para('Deliverables:', bold=True, after=2)
bullet('BLK4 RDRE integration design package')
bullet('RDRE scaling analysis correlated to BLK3 flight data')
bullet('Critical Design Review package')
bullet('Ground test results')
bullet('Flight test plan for BLK4 RDRE prototype')

h2('Task 4: HVRR Operational Prototype and Transition')
para('Budget: $2,000,000 (13%) | Period: Months 18\u201336', bold=True, after=4)
bullet('HVRR operational prototype design and fabrication')
bullet('RDRE propulsion integration for orbital transfer / upper stage')
bullet('Suborbital flight test of HVRR prototype on BLK3')
bullet('Mission utility analysis for USSF resiliency applications')
bullet('Phase III transition plan and final technical report')

doc.add_page_break()

# --- STRATEGIC ALIGNMENT ---
h1('4. Alignment with USSF / DAF Strategic Priorities')
bold_bullet('National Defense Strategy: ', 'Strengthening the defense industrial base through small business innovation in launch, propulsion, and hypersonic technology.')
bold_bullet('Tactically Responsive Space: ', 'BLK3 demonstrates rapid-turnaround launch operations directly relevant to TacRS architecture.')
bold_bullet('Resilient Space Architecture: ', 'Reusable flight test enables rapid iteration; RDRE propulsion enables more maneuverable space assets.')
bold_bullet('Hypersonic Weapon Systems: ', 'BLK4 with RDRE addresses DAF requirements for hypersonic strike and test vehicle capabilities.')
bold_bullet('DAF S&T Strategy: ', 'RDRE flight demonstration and BLK4 integration directly address goals for next-generation propulsion and hypersonic capabilities.')

# --- TRANSITION ---
h1('5. Transition and Commercialization')
h2('5.1 Government Transition Pathways')
bold_bullet('Phase III SBIR: ', 'Sole-source authority (15 U.S.C. \u00a7638) for any DoD component.')
bold_bullet('Space Enterprise Consortium OTA: ', 'Prototype projects for USSF customers.')
bold_bullet('AEDC Velocity Alliance: ', 'Contracting vehicle for AFTC/AEDC customers (application pending).')
bold_bullet('EPIC Consortium: ', 'RFI response submitted May 12, 2026 (RFI-RFZF-B001).')
bold_bullet('MDA / MACH-XL: ', 'BLK4 proposed under prototype OTA framework for Missile Defense Agency.')

h2('5.2 Commercial Customers')
bold_bullet('entX Pty Ltd (Australia): ', 'Radioisotope heater unit suborbital flight demonstration (signed).')
bold_bullet('Space COTAN / HOSPO (Japan): ', 'BLK3 wet lease for international operations (active).')

h2('5.3 Revenue')
para('FY2025 (Actual): $1.55M revenue | $0.26M EBITDA (17% margin)\nFY2026 (Projected): $9.1M | FY2027: $21.1M | FY2028: $37.5M')
para('Exos is EBITDA-positive and not a pre-revenue startup.', bold=True)

# --- COST SHARE ---
h1('6. Investment and Cost-Share Structure')
para('STRATFI 1:1:1 Matching Model:', bold=True, after=4)

add_table(
    ['Source', 'Amount', 'Status'],
    [
        ['SBIR Phase II', '$1,897,824', 'Awarded (FA9300-25-C-6022)'],
        ['STRATFI Request', '$15,000,000', 'This proposal'],
        ['Series A Equity', '$10,000,000', 'Closing Q2 2026'],
        ['Euronext Dublin Listing', '$12,500,000', 'Q3 2026 target'],
        ['Scorpius Acquisition', '$6,000,000', 'ROFR exercise Q2 2026'],
        ['Commercial Revenue', '$1.55M actual / $9.1M projected', 'Ongoing'],
        ['Total Private Match', '>$15,000,000', 'Satisfies requirement'],
    ]
)

para('', after=4)
para('STRATFI Budget Allocation ($15,000,000):', bold=True, after=4)
add_table(
    ['Task', 'Budget', '%'],
    [
        ['Task 1 \u2014 RDRE BLK3 Flight Demo', '$4,500,000', '30%'],
        ['Task 2 \u2014 DoD Flight Test Service', '$3,000,000', '20%'],
        ['Task 3 \u2014 BLK4 RDRE Hypersonic Vehicle', '$5,500,000', '37%'],
        ['Task 4 \u2014 HVRR Prototype & Transition', '$2,000,000', '13%'],
    ]
)

doc.add_page_break()

# --- TEAM ---
h1('7. Team and Partnerships')
add_table(
    ['Entity', 'Role', 'Contribution'],
    [
        ['Exos Aerospace (Prime)', 'Vehicle Design & Operations', 'BLK3/BLK4 design, manufacturing, launch ops, RDRE integration, FAA licensing'],
        ['Scorpius Space Launch Co.', 'Cryogenic Systems', 'Type 5 tanks (TRL 9, lunar heritage), propellant engineering, COPV production'],
        ['NASA MSFC', 'Research Partner', 'RDRE Data Usage Agreement, propulsion data, computational support'],
        ['USAF AFRL/AFTC', 'Government Champion', 'Phase II contracting office, RDRE GFE, test oversight, transition pathway'],
    ]
)

para('', after=8)
para('Key Personnel:', bold=True, after=4)
add_table(
    ['Name', 'Role', 'Qualifications'],
    [
        ['John Quinn', 'CEO & PM', 'Executive leadership, govt contract management, SBIR Phase II PI'],
        ['Russell Blink', 'CTO & PI', 'PI for MACH-XL/SBIR; BLK3/BLK4 systems engineer; GNC/propulsion; Armadillo veteran'],
        ['Neil Milburn', 'COO & Deputy PM', 'Decades aerospace engineering; NASA Morpheus PM; Armadillo veteran'],
    ]
)

# --- PAST PERFORMANCE ---
h1('8. Past Performance')
add_table(
    ['Program', 'Customer', 'Value', 'Status'],
    [
        ['SBIR Phase II \u2014 RDRE', 'USAF AFTC', '$1.9M', 'Active'],
        ['SBIR Phase I \u2014 Hypersonic', 'USAF AFTC', '$189K', 'Complete'],
        ['RDRE Development (DUA)', 'NASA MSFC', 'N/A', 'Active'],
        ['FAA Reusable Launch License', 'FAA', 'N/A', 'Active'],
        ['Cryo Tanks \u2014 Odysseus', 'Intuitive Machines', 'Commercial', 'Delivered'],
        ['Cryo Tanks \u2014 Athena', 'Intuitive Machines', 'Commercial', 'Delivered'],
        ['Launch Services', 'entX (Australia)', 'Commercial', 'Active'],
        ['BLK3 Wet Lease', 'Space COTAN (Japan)', 'Commercial', 'Active'],
        ['Morpheus Vehicle', 'NASA JSC', 'Govt Contract', 'Complete'],
    ]
)

# --- TRL ---
h1('9. Technology Readiness Levels')
add_table(
    ['Technology', 'Current TRL', 'Post-STRATFI TRL'],
    [
        ['BLK3 PSRLV (Vehicle)', '8', '9'],
        ['LOX/Ethanol Propulsion', '9', '9'],
        ['Type 5 Cryogenic Tanks', '9', '9'],
        ['RDRE Integration (HVRR)', '4', '6\u20137'],
        ['BLK4 Hypersonic Vehicle', '5\u20136', '7'],
        ['RDRE Flight Operations', '3', '6'],
        ['DoD Flight Test Service', '6', '8'],
    ]
)

# --- FOOTER ---
para('', after=12)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Exos Aerospace Systems & Technologies, Inc.')
r.bold = True; r.font.color.rgb = NAVY; r.font.size = Pt(10)
para('299 FM 1903, Greenville, TX 75402', size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para('CAGE: 7EMY6 | UEI: CK24BPZGF854', size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para('John Quinn, CEO \u2014 jquinn@exosaero.com \u2014 +1-972-740-8355', size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

footer = os.path.join(ASSETS, 'exos-letterhead-footer.png')
if os.path.exists(footer):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(footer, width=Inches(5.5))

doc.save(OUT)
print(f'Saved: {OUT}')
