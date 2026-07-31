#!/usr/bin/env python3
"""Generate Montana One-Pager for Congressional/Mayor presentation."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import os

ASSETS = '/Users/exomac/.openclaw/workspace/assets'
OUT = '/Users/exomac/.openclaw/workspace/drafts/Exos_Montana_Program_OnePager.docx'

doc = Document()

# Tight margins for one-pager
for section in doc.sections:
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    section.header_distance = Inches(0.01)
    section.footer_distance = Inches(0.01)

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10)
style.paragraph_format.space_after = Pt(2)
style.paragraph_format.space_before = Pt(0)

NAVY = RGBColor(0x1B, 0x3A, 0x5C)
DARK = RGBColor(0x2D, 0x2D, 0x2D)
GRAY = RGBColor(0x55, 0x55, 0x55)
BLUE = RGBColor(0x1E, 0x73, 0xBE)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF0, 0xF4, 0xF8)

def add_shading(cell, color_hex):
    """Add shading to a table cell."""
    shading = cell._element.get_or_add_tcPr()
    shd = shading.makeelement(qn('w:shd'), {
        qn('w:fill'): color_hex,
        qn('w:val'): 'clear',
    })
    shading.append(shd)

def para(text, bold=False, size=None, align=None, after=None, before=None, color=None, italic=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.color.rgb = color or DARK
    run.font.name = 'Calibri'
    if italic: run.italic = True
    if size: run.font.size = Pt(size)
    if align: p.alignment = align
    if after is not None: p.paragraph_format.space_after = Pt(after)
    if before is not None: p.paragraph_format.space_before = Pt(before)
    return p

def add_run(p, text, bold=False, size=None, color=None, italic=False):
    run = p.add_run(text)
    run.bold = bold
    run.font.name = 'Calibri'
    run.font.color.rgb = color or DARK
    if italic: run.italic = True
    if size: run.font.size = Pt(size)
    return run

# ================================================================
# LOGO
# ================================================================
logo = os.path.join(ASSETS, 'exos-letterhead-logo.png')
if os.path.exists(logo):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(logo, width=Inches(1.4))
    p.paragraph_format.space_after = Pt(2)

# ================================================================
# TITLE
# ================================================================
p = para('MONTANA AEROSPACE ECONOMIC DEVELOPMENT PROGRAM', bold=True, size=13,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=0, color=NAVY)
p = para('Precision Suborbital Launch \u2022 Workforce Development \u2022 Pathway to Polar Orbit',
         size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=1, color=GRAY, italic=True)

# ================================================================
# THE OPPORTUNITY
# ================================================================
p = para('THE OPPORTUNITY', bold=True, size=11, after=3, color=NAVY)
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(4)
add_run(p, 'Oklahoma recently invested $17 million in a single horizontal-launch spaceplane carrying just 11 lbs of payload to catalyze their spaceport program. ', size=10)
add_run(p, 'Exos Aerospace', bold=True, size=10)
add_run(p, ' proposes a far more compelling package: a ', size=10)
add_run(p, '$6 million program', bold=True, size=10, color=BLUE)
add_run(p, ' deploying ', size=10)
add_run(p, 'two Precision Suborbital Reusable Launch Vehicles (PSRLVs)', bold=True, size=10)
add_run(p, ' \u2014 the only commercially available, FAA-licensed reusable suborbital rockets in the U.S. \u2014 '
        'each carrying 135 kg of payload to 100+ km altitude. '
        'At one-third the cost and orders of magnitude more capability, Montana gets not just a spaceport catalyst but a clear pathway to polar orbit launch capability '
        'and direct alignment with national security priorities including the Golden Dome initiative. '
        'If Oklahoma\u2019s investment made strategic sense for a horizontal spaceplane, Montana\u2019s opportunity with Exos is exceptional.', size=10)

# FAA licensing advantage bullets
p = para('Why a launch vehicle is critical to spaceport licensing:', bold=True, size=9, after=2, before=4, color=NAVY)
faa_points = [
    'FAA launch site licensing requires a specific launch vehicle for flight safety analysis \u2014 without one, the application cannot proceed.',
    'Exos\u2019s FAA-licensed BLK3 provides the vehicle data (trajectory, IIP, Ec modeling) needed to complete the licensing process.',
    'Having the vehicle on Day 1 compresses the licensing timeline by years compared to states that must find a vehicle operator after the fact.',
    'Montana moves to the front of the line \u2014 an operational vehicle with flight heritage means the FAA has real data, not projections.',
]
for pt in faa_points:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.space_before = Pt(0)
    add_run(p, '\u2022 ', bold=True, size=8.5, color=NAVY)
    add_run(p, pt, size=8.5, color=DARK)

# ================================================================
# THREE PILLARS TABLE
# ================================================================
p = para('PROGRAM PILLARS', bold=True, size=11, after=3, before=6, color=NAVY)

table = doc.add_table(rows=2, cols=3)
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# Header row
headers = ['LAUNCH OPERATIONS', 'EDUCATION & WORKFORCE', 'ORBITAL PATHWAY']
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(h)
    run.bold = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = WHITE
    run.font.name = 'Calibri'
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_shading(cell, '1B3A5C')

# Content row
contents = [
    '\u2022 Deploy 2 BLK3 PSRLVs for DoD, NASA, and commercial flight test campaigns\n'
    '\u2022 Suborbital flights to 100+ km from Montana ranges\n'
    '\u2022 30-day launch turnaround \u2014 rapid, repeatable access\n'
    '\u2022 FAA launch site licensing for Montana operations\n'
    '\u2022 Montana\u2019s 45\u201348\u00b0N latitude ideal for future polar orbit launch corridor',

    '\u2022 STEM pipeline: MSU, Montana Tech, and commercial/private educator partnerships\n'
    '\u2022 Hands-on student integration into flight ops teams\n'
    '\u2022 Biomedical space science program (international collaboration with Space Port Australia)\n'
    '\u2022 Aerospace technician certification + veteran transition pathways\n'
    '\u2022 School engagement: K-12 through graduate-level aerospace and biomedical curricula',

    '\u2022 Suborbital ops prove range safety, airspace, and infrastructure \u2014 de-risking the path to orbital\n'
    '\u2022 Proven spaceport operations attract orbital launch startups to base in Montana\n'
    '\u2022 Revenue model: ~$1M/flight (current NASA pricing) generates sustainable spaceport income\n'
    '\u2022 Positions Montana alongside Kodiak, AK and Vandenberg, CA as a polar launch destination'
]

for i, c in enumerate(contents):
    cell = table.rows[1].cells[i]
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(c)
    run.font.size = Pt(8)
    run.font.color.rgb = DARK
    run.font.name = 'Calibri'
    add_shading(cell, 'F0F4F8')

# Set column widths
for row in table.rows:
    for i, cell in enumerate(row.cells):
        cell.width = Inches(2.3)

# ================================================================
# ECONOMIC IMPACT
# ================================================================
p = para('ECONOMIC IMPACT', bold=True, size=10, after=2, before=5, color=NAVY)

impact_table = doc.add_table(rows=1, cols=4)
impact_table.alignment = WD_TABLE_ALIGNMENT.CENTER

impacts = [
    ('50\u201375+', 'Direct Jobs\nby Year 3'),
    ('$6M', 'Initial\nInvestment'),
    ('$50M+', 'Follow-on Federal\nContract Potential'),
    ('3\u20135x', 'Economic\nMultiplier'),
]

for i, (num, label) in enumerate(impacts):
    cell = impact_table.rows[0].cells[i]
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(num + '\n')
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = BLUE
    run.font.name = 'Calibri'
    run2 = p.add_run(label)
    run2.font.size = Pt(8)
    run2.font.color.rgb = GRAY
    run2.font.name = 'Calibri'
    add_shading(cell, 'F0F4F8')

# ================================================================
# WHY MONTANA
# ================================================================
p = para('WHY MONTANA', bold=True, size=10, after=2, before=6, color=NAVY)
points = [
    ('Geographic advantage:', ' 45\u201348\u00b0N latitude \u2014 only CONUS polar/SSO launch option between Kodiak, AK and Vandenberg, CA. Townsend site strategically located near military base; Billings under evaluation (population density being assessed).'),
    ('National security:', ' supports Golden Dome initiative; polar orbit access strengthens domestic space industrial base.'),
    ('Clear airspace & low density:', ' ideal for FAA range safety. IIP/Ec Monte Carlo analysis underway with MT-specific wind data.'),
    ('Infrastructure:', ' AeroTec/MADA test facilities, MSU top-3 small satellite program, no state sales tax, Governor\u2019s 406 JOBS Initiative.'),
    ('International:', ' Space Port Australia (Dr. Gabrielle Caswell) partnership \u2014 biomedical space science + international payload customers.'),
]
for label, detail in points:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(1)
    add_run(p, '\u2022 ' + label, bold=True, size=8.5, color=DARK)
    add_run(p, detail, size=8.5, color=DARK)

# ================================================================
# PROGRAM PHASES (compact)
# ================================================================
p = para('$6M PROGRAM STRUCTURE ENABLES', bold=True, size=10, after=2, before=5, color=NAVY)

phase_table = doc.add_table(rows=4, cols=4)
phase_table.alignment = WD_TABLE_ALIGNMENT.CENTER

# Header
phase_headers = ['Phase', 'Timeline', 'Investment', 'Milestones']
for i, h in enumerate(phase_headers):
    cell = phase_table.rows[0].cells[i]
    cell.text = ''
    p = cell.paragraphs[0]
    run = p.add_run(h)
    run.bold = True
    run.font.size = Pt(8)
    run.font.color.rgb = WHITE
    run.font.name = 'Calibri'
    add_shading(cell, '1B3A5C')

phases = [
    ('1: Foundation', 'Months 1\u201311', '$2.5M',
     'FAA site licensing initiated; ground test ops at AeroTec; MSU/Tech student cohort onboarded; 10\u201315 jobs created to support'),
    ('2: Flight Ops', 'Months 12\u201318', '$2.5M',
     '2 BLK3 PSRLVs operational; first suborbital flights from NM (transition to MT as license granted & spaceport ready with infrastructure and staffing); DoD/NASA flight test campaigns; international payload integration; 25\u201340 jobs to support'),
    ('3: Operations Turnover', 'Months 19\u201336', '$1.0M',
     'Operations turnover to Montana Spaceport Team as 100% revenue recipients for payload sales (~$1M/flight, current NASA pricing); polar launch corridor qualification; 50\u201375+ jobs required; $50M+ federal pipeline established'),
]

for row_idx, (phase, timeline, invest, milestones) in enumerate(phases, 1):
    data = [phase, timeline, invest, milestones]
    for col_idx, val in enumerate(data):
        cell = phase_table.rows[row_idx].cells[col_idx]
        cell.text = ''
        p = cell.paragraphs[0]
        run = p.add_run(val)
        run.font.size = Pt(7.5)
        run.font.color.rgb = DARK
        run.font.name = 'Calibri'
        if col_idx == 0:
            run.bold = True
        add_shading(cell, 'F8FAFC' if row_idx % 2 == 0 else 'FFFFFF')

# Set widths
widths = [Inches(1.1), Inches(0.9), Inches(0.7), Inches(4.1)]
for row in phase_table.rows:
    for i, cell in enumerate(row.cells):
        cell.width = widths[i]

# ================================================================
# ABOUT EXOS (compact footer)
# ================================================================
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(4)
p.paragraph_format.space_after = Pt(0)
add_run(p, 'EXOS AEROSPACE ', bold=True, size=7, color=NAVY)
add_run(p, '| FAA-licensed reusable suborbital launch | Active USAF SBIR Phase II & NASA contracts | Profitable since Dec 2025 | ', size=7, color=GRAY)
add_run(p, 'www.exosaero.com', size=7, color=BLUE)
add_run(p, ' | John Quinn, CEO | jquinn@exosaero.com | +1-972-740-8355', size=7, color=GRAY)

# ================================================================
# PAGE 2 — ANTICIPATED Q&A
# ================================================================
doc.add_page_break()

# Logo on page 2
if os.path.exists(logo):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(logo, width=Inches(1.5))
    p.paragraph_format.space_after = Pt(4)

p = para('ANTICIPATED QUESTIONS & ANSWERS', bold=True, size=14,
         align=WD_ALIGN_PARAGRAPH.CENTER, after=2, color=NAVY)
p = para('Montana Aerospace Economic Development Program',
         size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=6, color=GRAY, italic=True)

# Divider
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(6)
run = p.add_run('\u2500' * 95)
run.font.size = Pt(6)
run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

qas = [
    ('How can Congress help make this happen?',
     '\u2022 FAA launch site licensing: Congressional endorsement accelerates FAA review for Billings and Townsend sites.\n'
     '\u2022 Federal funding: Direct DoD/NASA contracts to Montana \u2014 $50M+ already in Exos\u2019s STRATFI/SBIR/OTA pipeline.\n'
     '\u2022 Golden Dome: Advocate for Montana polar launch as a strategic asset for space-based missile defense.\n'
     '\u2022 Workforce grants: Support NSF, NASA Space Grant, and DOL funding for aerospace workforce programs.'),

    ('How does suborbital launch de-risk the path to orbital and attract orbital companies?',
     'Suborbital test vehicles are the key enabler for orbital development. They provide rapid, low-cost flight testing of orbital technologies '
     'on FAA-licensed vehicles \u2014 avionics, GNC, propulsion subsystems, and thermal protection can be validated in real flight environments without '
     'the cost or risk of an orbital mission. Critically, suborbital vehicles also enable deployment and testing of orbital recovery systems \u2014 '
     'reentry, parachute, and landing technologies that orbital companies must prove before they can fly. '
     'An active suborbital spaceport with flight heritage, established FAA relationships, and trained staff is exactly what orbital startups need. '
     'Montana becomes a destination where orbital companies co-locate, share infrastructure, and leverage an existing ecosystem.'),

    ('Why does Montana need this? We already have aerospace companies.',
     'Montana has aerospace manufacturing (GE, Lattice Materials) but no launch capability. Launch operations create a fundamentally different '
     'economic anchor \u2014 they attract payload integrators, propulsion companies, range services, and federal testing programs that don\u2019t exist '
     'without an active launch site. This program transforms Montana from a supplier state to a destination state for aerospace operations.'),

    ('Is $6M enough to establish a real launch program?',
     'Yes. Exos already has FAA-licensed vehicles, flight heritage, and active government contracts. The $6M funds Montana-specific infrastructure, '
     'vehicle deployment, and workforce development \u2014 not vehicle R&D. Additionally, this $6M catalyzes over $50M in follow-on federal funding '
     'through existing DoD contract vehicles (STRATFI, SBIR Phase III, OTA) that require a demonstrated operational site.'),

    ('What about safety and environmental concerns?',
     'Exos operates under FAA reusable launch vehicle licenses with comprehensive safety protocols. Montana\u2019s low population density and clear '
     'airspace are precisely why the FAA favors locations like this. Suborbital vehicles are recovered and reused \u2014 no debris fields. '
     'Environmental impact is minimal compared to traditional industrial development, and all operations undergo FAA environmental review.'),

    ('How does this lead to polar orbit launch capability?',
     'Montana\u2019s 45\u201348\u00b0N latitude is geometrically ideal for polar and sun-synchronous orbits (SSO) \u2014 the fastest-growing orbital segment, '
     'serving Earth observation, weather, and national security satellites. Today, the only U.S. polar launch sites are Kodiak, Alaska and '
     'Vandenberg, California. Montana offers a mid-latitude alternative with lower logistics costs and year-round operations. Suborbital operations '
     'establish the regulatory, infrastructure, and safety track record the FAA requires for an orbital launch license.'),

    ('What federal funding does this attract?',
     'Exos holds an active USAF SBIR Phase II contract ($1.9M) and is pursuing STRATFI ($15M) and SPRINT BAA ($10M) awards. These programs require '
     'demonstrated operational sites and private investment matches. Montana\u2019s $6M commitment directly enables $50M+ in federal contract potential. '
     'Every dollar Montana invests is leveraged 8\u201310x through federal matching programs designed for exactly this type of technology transition.'),

    ('How does this support the Golden Dome initiative and national security?',
     'The Golden Dome initiative requires rapid, responsive space access for missile defense and persistent space domain awareness. Montana launch '
     'capability provides a geographically diverse, high-latitude launch site for polar orbit missions critical to national security constellations. '
     'The Townsend site\u2019s proximity to a military installation further strengthens the national security case for Montana as a strategic launch location.'),

    ('What international partnerships are involved?',
     'Space Port Australia (Moree, NSW) is actively partnering on this initiative, with a focus on biomedical space science programs and school engagement. '
     'Exos also has signed launch services agreements with Australian aerospace companies developing hardware for NASA\u2019s lunar program. '
     'Montana becomes a destination for international payload customers and biomedical research \u2014 creating a global draw that extends the state\u2019s '
     'economic impact beyond domestic aerospace.'),

    ('How many jobs, and what kind?',
     'Phase 1 (Months 1\u201311): 10\u201315 positions \u2014 engineers, technicians, operations staff. '
     'Phase 2 (Months 12\u201318): 25\u201340 positions \u2014 launch operations, payload integration, range safety. '
     'Phase 3 (Months 19\u201336): 50\u201375+ positions as operations transfer to Montana Spaceport Team. '
     'These are high-skill, high-wage jobs averaging $75\u2013120K, with a direct university-to-employment pipeline through MSU and Montana Tech.'),

    ('What\u2019s the educational component?',
     'Exos is establishing hands-on student integration programs with Montana State University and Montana Tech. Students work directly on flight '
     'campaigns \u2014 payload integration, avionics, ground support, and flight analysis. The first student cohort is being onboarded for a Q1 2027 '
     'payload campaign. Additionally, the Space Port Australia partnership brings a biomedical space science program focused on engaging Montana '
     'schools in biomedical research payloads \u2014 connecting healthcare, STEM education, and aerospace in a way that broadens the program\u2019s appeal '
     'beyond traditional engineering. We also plan aerospace technician certification programs and veteran transition pathways.'),

    ('What makes Exos different from other launch companies promising economic development?',
     'Two things: (1) Exos is already operational \u2014 FAA-licensed, flight-proven, profitable, with active DoD and NASA contracts. This isn\u2019t a '
     'startup seeking development funding. (2) Our vehicles are reusable and can fly repeatedly from Montana, generating sustained operations '
     'and ~$1M per flight in revenue at current NASA pricing \u2014 revenue that transfers to the Montana Spaceport Team in Phase 3.'),
]

for i, (q, a) in enumerate(qas):
    # Question
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5 if i > 0 else 0)
    p.paragraph_format.space_after = Pt(2)
    add_run(p, f'Q: {q}', bold=True, size=9.5, color=NAVY)

    # Answer
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    add_run(p, a, size=9, color=DARK)

# Footer
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(8)
run = p.add_run('\u2500' * 95)
run.font.size = Pt(6)
run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(0)
add_run(p, 'Prepared by Exos Aerospace Systems & Technologies, Inc. | May 2026 | ', size=7.5, color=GRAY)
add_run(p, 'www.exosaero.com', size=7.5, color=BLUE)

# Footer image
footer_img = os.path.join(ASSETS, 'exos-letterhead-footer.png')
if os.path.exists(footer_img):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(footer_img, width=Inches(5.0))

doc.save(OUT)
print(f'Saved: {OUT}')
print(f'Size: {os.path.getsize(OUT) / 1024:.0f} KB')
