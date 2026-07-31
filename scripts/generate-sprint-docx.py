#!/usr/bin/env python3
"""Generate SPRINT BAA White Paper .docx with Exos letterhead styling."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os

ASSETS = '/Users/exomac/.openclaw/workspace/assets'
OUT = '/Users/exomac/.openclaw/workspace/drafts/SPRINT-BAA-RDRE-White-Paper.docx'

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
para('WHITE PAPER SUBMISSION', bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para('SPRINT Broad Agency Announcement', bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para('BAA-RQR-2019-0001 / FA9300-19-S001', size=11, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para('Space Propulsion Research and Innovation\nfor Neutralizing Satellite Threats', size=11, align=WD_ALIGN_PARAGRAPH.CENTER, after=16)

para('Title: Rotating Detonation Rocket Engine (RDRE) Flight Demonstration\nand Operational Propulsion System Development on a Reusable Suborbital Platform', bold=True, size=11, after=8)

# Cover details table
details = [
    ('Submitting Organization:', 'Exos Aerospace Systems & Technologies, Inc.\n299 FM 1903, Greenville, TX 75402\nwww.exosaero.com'),
    ('CAGE Code:', '7EMY6'),
    ('UEI:', 'CK24BPZGF854'),
    ('Business Size:', 'Small Business (NAICS 336414)'),
    ('Primary Contact:', 'John Quinn, CEO\njquinn@exosaero.com | +1-972-740-8355'),
    ('Technical Contact:', 'Russell Blink, CTO & Principal Investigator\nrblink@exosaero.com'),
    ('Estimated Cost:', '$10,000,000'),
    ('Period of Performance:', '36 months'),
    ('Classification:', 'Unclassified'),
]
for label, val in details:
    p = doc.add_paragraph()
    r = p.add_run(label + ' ')
    r.bold = True; r.font.color.rgb = DARK; r.font.size = Pt(10)
    r2 = p.add_run(val)
    r2.font.color.rgb = DARK; r2.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# --- SECTION 1 ---
h1('1. TECHNICAL CONCEPT')
h2('1.1 Objective')
para('Exos Aerospace proposes a 36-month program to flight-demonstrate a Rotating Detonation Rocket Engine (RDRE) on a reusable suborbital launch vehicle, then scale the resulting propulsion system toward an operational upper stage / orbital transfer vehicle configuration. This program transitions RDRE technology from ground test and hover demonstration (current SBIR Phase II baseline) through iterative flight test to an operationally relevant propulsion system for space resiliency applications.')

h2('1.2 Background and Problem Statement')
para('Rotating detonation engines represent the most significant advance in chemical propulsion efficiency in decades, offering 25%+ specific impulse improvement over conventional deflagration-based combustion at equivalent thrust levels. AFRL, NASA, and industry have invested heavily in RDRE ground test \u2014 but no flight demonstration pathway currently exists that provides the iterative, reusable test cadence needed to mature this technology to operational readiness.')
para('The SPRINT BAA seeks innovative research in chemical propulsion systems and their interactions with spacecraft systems. RDRE technology directly addresses this need: detonation-based propulsion offers higher thrust density, reduced combustor size, and improved fuel economy \u2014 all critical attributes for spacecraft propulsion systems that must operate within tight mass and volume constraints for resiliency applications.')
para('The gap: RDRE has been extensively ground-tested but never flight-demonstrated on a reusable platform that enables rapid hardware iteration. Without iterative flight data, RDRE cannot mature from laboratory demonstration to operational spacecraft propulsion.', bold=True, after=8)

h2('1.3 Technical Approach')

para('Phase A \u2014 RDRE Flight Integration and Demonstration (Months 1\u201318)', bold=True, after=4)
para('Integrate the RDRE from the current SBIR Phase II hover test configuration into the Exos BLK3 Precision Suborbital Reusable Launch Vehicle (PSRLV) for suborbital flight. BLK3 provides:')
bullet('50\u2013135 kg payload capacity to 100+ km altitude')
bullet('Mach 3\u20135+ reentry environment')
bullet('Full vehicle recovery enabling post-flight hardware inspection')
bullet('Flight cadence of weeks between flights (not months)')
bullet('FAA-licensed operations from Greenville, TX')

para('The Phase A flight campaign will execute a minimum of 5 instrumented RDRE suborbital flights, collecting data on:')
bullet('Detonation wave stability under flight dynamic loads (vibration, acceleration, attitude changes)')
bullet('Thermal performance in altitude thermal environments')
bullet('Propellant feed system behavior under flight g-loading profiles')
bullet('RDRE/vehicle system interactions (thrust vectoring, vehicle dynamics, structural loads)')
bullet('Start/restart reliability in flight conditions')

para('Each flight provides recovered hardware for post-flight inspection \u2014 a capability unique to reusable platforms and critical for understanding RDRE degradation, thermal cycling effects, and component wear patterns that cannot be captured from telemetry alone.')

para('Deliverables:', bold=True, after=2)
bullet('RDRE flight-qualified configuration and integration package')
bullet('5+ instrumented suborbital flights with comprehensive data sets')
bullet('Flight performance database for AFRL propulsion community')
bullet('Post-flight hardware condition reports with metallurgical analysis')
bullet('RDRE flight operations manual')

para('Phase B \u2014 RDRE Scaling for Upper Stage / OTV Application (Months 12\u201330)', bold=True, after=4)
para('Using flight data from Phase A, scale the RDRE propulsion system from BLK3-class thrust to the BLK4 multi-purpose hypersonic vehicle configuration:')
bullet('BLK4 specifications: 48 in diameter, ~48 ft length, 27,300 lb GLOW')
bullet('Lofted trajectory: ~2,200 km range, ~1,100 km apogee, up to Mach 20')
bullet('Depressed trajectory: ~1,200 km range, ~110 km apogee, up to Mach 15')
bullet('Single vehicle architecture covering SRBM through IRBM-class profiles')

para('Scaling activities include:')
bullet('RDRE combustor scaling analysis informed by BLK3 flight data')
bullet('Propellant management system design for cryogenic upper stage operations')
bullet('Thermal management and vehicle integration for sustained RDRE operation')
bullet('Performance modeling validated against BLK3 flight truth data')
bullet('Preliminary Design Review for RDRE-powered upper stage configuration')

para('Deliverables:', bold=True, after=2)
bullet('RDRE scaling analysis report with BLK3 flight data correlation')
bullet('BLK4/upper stage RDRE integration concept design')
bullet('Propellant management system design for cryogenic operations')
bullet('Preliminary Design Review package')
bullet('Technology transition plan for operational RDRE upper stage')

para('Phase C \u2014 Mission Utility Analysis and Transition (Months 24\u201336)', bold=True, after=4)
para('Conduct mission utility analysis for RDRE-powered propulsion in USSF space resiliency applications:')
bullet('On-orbit maneuvering / orbital transfer with RDRE propulsion')
bullet('Rapid-response space access using RDRE upper stage')
bullet('Space domain awareness mission profiles enabled by RDRE performance improvements')
bullet('Spacecraft bus integration considerations for RDRE propulsion')
bullet('Cost-performance trade studies versus conventional chemical propulsion')

para('Deliverables:', bold=True, after=2)
bullet('Mission utility analysis report for RDRE in space resiliency applications')
bullet('Cost-performance comparison with conventional propulsion alternatives')
bullet('RDRE spacecraft integration guide')
bullet('Technology Readiness Assessment (TRA) documenting TRL advancement')
bullet('Final technical report with all flight data, analysis, and transition recommendations')

h2('1.4 Key Technical Risks and Mitigations')
add_table(
    ['Risk', 'Mitigation'],
    [
        ['RDRE stability in flight dynamic environment', 'Hover test data (Phase II) establishes ground-truth baseline; BLK3 instrumentation captures all relevant environments; iterative flights enable rapid design-test-learn cycles'],
        ['Thermal management at sustained operation', 'Reusable platform enables post-flight thermal inspection of actual hardware; Phase A flights incrementally extend burn duration'],
        ['Propellant feed under flight g-loads', 'BLK3 heritage propellant systems provide validated feed architecture; RDRE-specific modifications tested incrementally'],
        ['BLK4 scaling assumptions', 'Phase B scaling analysis anchored to actual BLK3 flight data, not computational models alone'],
    ]
)

doc.add_page_break()

# --- SECTION 2 ---
h1('2. RELEVANCE TO SPRINT OBJECTIVES')
para('This proposal directly addresses multiple SPRINT technology areas:')
bold_bullet('Chemical propulsion systems: ', 'RDRE is a chemical (LOX/fuel) propulsion system offering revolutionary performance improvement over conventional engines')
bold_bullet('Complete propulsion systems and spacecraft interactions: ', 'Flight demonstration captures RDRE/vehicle system interactions that ground test cannot replicate')
bold_bullet('Mission utility of propulsion research concepts: ', 'Phase C explicitly addresses operational constructs and architectures for RDRE in space resiliency missions')
para('RDRE technology is uniquely relevant to the SPRINT mission of improving spacecraft propulsion for resiliency. Higher Isp means more delta-V per kilogram of propellant \u2014 directly enabling more responsive maneuvering, longer on-orbit life, and greater mission flexibility for resilient space architectures.')

# --- SECTION 3 ---
h1('3. OFFEROR QUALIFICATIONS')
h2('3.1 Relevant Experience')
bold_bullet('USAF SBIR Phase II (FA9300-25-C-6022) \u2014 $1.9M, Active: ', 'Hybrid Vehicle Rocket with Government-Furnished RDRE. Hover test demonstration. Direct technical baseline for this proposal.')
bold_bullet('USAF SBIR Phase I (FA9300-24-P-6006) \u2014 $189K, Completed: ', 'Hypersonic vehicle development concept. BLK4 vehicle architecture.')
bold_bullet('NASA MSFC Data Usage Agreement \u2014 Active: ', 'RDRE technology development collaboration with Marshall Space Flight Center.')
bold_bullet('FAA Reusable PSRLV License \u2014 Active: ', 'One of only three in the United States. Operational readiness for repeated flight campaigns.')
bold_bullet('Scorpius Space Launch Company (Affiliate): ', 'Type 5 linerless cryogenic tank technology at TRL 9 \u2014 flight-proven on Intuitive Machines Odysseus and Athena lunar landers.')

h2('3.2 Personnel')
add_table(
    ['Name', 'Role', 'Qualifications'],
    [
        ['John Quinn', 'Program Manager / CEO', 'Executive leadership of reusable launch programs; government contract management; SBIR Phase II PI'],
        ['Russell Blink', 'Principal Investigator / CTO', 'PI for MACH-XL and SBIR programs; lead systems engineer for BLK3/BLK4; Armadillo Aerospace veteran; GNC, propulsion, flight software'],
        ['Neil Milburn', 'Deputy PM / COO', 'Decades of aerospace engineering and program management; NASA Morpheus PM; technical authority for BLK3, BLK4, and RDRE programs'],
    ]
)

h2('3.3 Facilities')
add_table(
    ['Facility', 'Location', 'Capabilities'],
    [
        ['HQ & Vehicle Integration', 'Greenville, TX', 'Assembly, payload integration, avionics, propulsion test'],
        ['FAA-Licensed Launch Site', 'Spaceport America, NM', 'Launch operations, propellant handling, range safety'],
        ['Scorpius Manufacturing', 'Torrance, CA', 'Cryogenic tank fabrication, COPV production'],
    ]
)

doc.add_page_break()

# --- SECTION 4 ---
h1('4. COST ESTIMATE')
para('Total Proposed Cost: $10,000,000 (36-month period of performance)', bold=True, after=8)

add_table(
    ['Phase', 'Budget', '%', 'Period'],
    [
        ['Phase A: RDRE Flight Demonstration', '$4,500,000', '45%', 'Months 1\u201318'],
        ['Phase B: RDRE Scaling to Upper Stage', '$3,500,000', '35%', 'Months 12\u201330'],
        ['Phase C: Mission Utility & Transition', '$2,000,000', '20%', 'Months 24\u201336'],
    ]
)

para('', after=4)
para('Phase A breakdown:', bold=True, after=2)
bullet('RDRE flight integration engineering: $1,200,000')
bullet('BLK3 vehicle modifications and instrumentation: $800,000')
bullet('5+ suborbital flights (operations, propellant, recovery): $1,500,000')
bullet('Data analysis, reporting, program management: $1,000,000')

para('Phase B breakdown:', bold=True, after=2)
bullet('RDRE combustor scaling analysis and design: $1,500,000')
bullet('Propellant management system design: $800,000')
bullet('Vehicle integration engineering: $700,000')
bullet('Preliminary Design Review and documentation: $500,000')

para('Phase C breakdown:', bold=True, after=2)
bullet('Mission utility analysis: $800,000')
bullet('Cost-performance trade studies: $400,000')
bullet('Technology transition planning and final reporting: $800,000')

para('Cost leverage: Exos\u2019s existing SBIR Phase II ($1.9M) provides the hover test baseline at no additional cost to the SPRINT program. The BLK3 vehicle, launch infrastructure, and FAA licensing represent existing capital investment that does not require SPRINT funding to develop \u2014 only to operate.', after=8)

# --- SECTION 5 ---
h1('5. SECURITY')
para('This white paper is submitted at the UNCLASSIFIED level. Exos Aerospace is a U.S.-owned and U.S.-controlled entity with no Foreign Ownership, Control, or Influence (FOCI). ITAR/EAR compliance programs are in place. Exos does not currently hold a facility clearance but can initiate the process if required by specific classified elements of the program.')

# --- FOOTER ---
para('', after=12)
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run('Exos Aerospace Systems & Technologies, Inc.')
r.bold = True; r.font.color.rgb = NAVY; r.font.size = Pt(10)
para('299 FM 1903, Greenville, TX 75402', size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para('CAGE: 7EMY6 | UEI: CK24BPZGF854', size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=1)
para('John Quinn, CEO \u2014 jquinn@exosaero.com \u2014 +1-972-740-8355', size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=8)

# Footer
footer = os.path.join(ASSETS, 'exos-letterhead-footer.png')
if os.path.exists(footer):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(footer, width=Inches(5.5))

doc.save(OUT)
print(f'Saved: {OUT}')
