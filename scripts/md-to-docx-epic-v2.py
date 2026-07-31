#!/usr/bin/env python3
"""Generate expanded 10-page EPIC RFI response with images and history."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import os

IMG = '/Users/exomac/.openclaw/workspace/assets/epic-images'

doc = Document()

for section in doc.sections:
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
style.paragraph_format.space_after = Pt(4)

# Colors
NAVY = RGBColor(0x1B, 0x3A, 0x5C)
DARK = RGBColor(0x33, 0x33, 0x33)

def h1(text):
    h = doc.add_heading(text, level=1)
    for r in h.runs:
        r.font.color.rgb = NAVY
        r.font.size = Pt(14)
    h.paragraph_format.space_before = Pt(12)
    h.paragraph_format.space_after = Pt(6)
    return h

def h2(text):
    h = doc.add_heading(text, level=2)
    for r in h.runs:
        r.font.color.rgb = NAVY
        r.font.size = Pt(12)
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(4)
    return h

def para(text, bold=False, italic=False, size=None, align=None, after=None, before=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = DARK
    if size: run.font.size = Pt(size)
    if align: p.alignment = align
    if after is not None: p.paragraph_format.space_after = Pt(after)
    if before is not None: p.paragraph_format.space_before = Pt(before)
    return p

def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        r.font.color.rgb = DARK
        r2 = p.add_run(text)
        r2.font.color.rgb = DARK
    else:
        r = p.add_run(text)
        r.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(2)
    return p

def bold_bullet(label, desc):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(label)
    r.bold = True
    r.font.color.rgb = DARK
    r2 = p.add_run(desc)
    r2.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(2)
    return p

def add_img(filename, width_inches=5.5, caption=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    path = os.path.join(IMG, filename)
    if os.path.exists(path):
        run.add_picture(path, width=Inches(width_inches))
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cr = cp.add_run(caption)
        cr.italic = True
        cr.font.size = Pt(9)
        cr.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        cp.paragraph_format.space_after = Pt(8)

def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for paragraph in hdr[i].paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(9)
    for row_data in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row_data):
            cells[i].text = val
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)
    return table

# ============================================================
# COVER PAGE
# ============================================================
# Logo
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run()
logo_path = os.path.join(IMG, 'MDA_BLK4_White_Paper_image1.jpg')
if os.path.exists(logo_path):
    run.add_picture(logo_path, width=Inches(3.5))

para('', after=6)

para('ENTERPRISE PROTOTYPE INITIATIVE CONSORTIUM (EPIC)', bold=True, size=18, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para('RFI Response \u2014 RFI-RFZF-B001', bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, after=24)

# Cover details
para('Submitted to:', bold=True, size=11, after=2)
para('Air Force Research Laboratory (AFRL)\nFA8750 AFRL RIK, Rome, NY 13441', size=11, after=8)

para('Points of Contact:', bold=True, size=11, after=2)
para('Catherine Hulser, Agreements Officer \u2014 catherine.hulser@us.af.mil\n'
     'Erica Ogundadegbe, Agreements Officer \u2014 erica.ogundadegbe@us.af.mil\n'
     'Matthew Shaver, Agreement Officer Representative \u2014 matthew.shaver@us.af.mil', size=10, after=12)

para('Submitted by:', bold=True, size=11, after=2)
para('Exos Aerospace Systems & Technologies, Inc.\n'
     '299 FM 1903, Greenville, TX 75402\n'
     'www.exosaero.com\n'
     'CAGE Code: 7EMY6  |  UEI: CK24BPZGF854', size=11, after=8)

para('Point of Contact:', bold=True, size=11, after=2)
para('John Quinn, Chief Executive Officer\n'
     'jquinn@exosaero.com  |  +1-972-740-8355', size=11, after=8)

para('Date: May 12, 2026', bold=True, size=11, after=4)

doc.add_page_break()

# ============================================================
# 1. EXECUTIVE SUMMARY
# ============================================================
h1('1. Executive Summary')

para('Exos Aerospace Systems & Technologies, Inc. (Exos) respectfully submits this response to '
     'RFI-RFZF-B001 in support of the Air Force Research Laboratory\u2019s Enterprise Prototype '
     'Initiative Consortium (EPIC). Exos is a nontraditional defense contractor and small business '
     'that designs, builds, tests, and operates reusable suborbital launch vehicles and advanced '
     'propulsion systems. We are interested in participating as a Project-Level Performer within the '
     'EPIC consortium framework, providing rapid-cycle hardware prototyping, flight test, and '
     'technology demonstration services aligned with AFRL mission areas.', after=6)

para('Exos is one of only three U.S. companies holding an active FAA license for reusable suborbital '
     'launch operations, and we maintain an active USAF SBIR Phase II contract (FA9300-25-C-6022) with '
     'the Air Force Test Center for Rotating Detonation Rocket Engine (RDRE) development. Our affiliate, '
     'Scorpius Space Launch Company, holds the only known TRL 9 Type 5 cryogenic tank technology with '
     'demonstrated lunar operational heritage.', after=6)

para('As a nontraditional defense contractor and small business, Exos satisfies the participation '
     'requirements under 10 U.S.C. \u00a74022 for Other Transaction for Prototype authority and brings '
     'hardware-first, flight-test-driven capabilities to the EPIC consortium structure.', after=6)

add_img('EXOS_WHITE_PAPER_MACH-XL_26_REV_1_260123_image1.jpeg', 5.0,
        'Figure 1. Exos Aerospace BLK3 Precision Reusable Suborbital Launch Vehicle (PSRLV)')

# ============================================================
# 2. COMPANY HISTORY & HERITAGE
# ============================================================
h1('2. Company History & Technical Heritage')

para('Exos Aerospace was founded in 2014 by the engineering team formerly of Armadillo Aerospace, '
     'bringing over two decades of liquid rocket vehicle design, build, and flight test experience. '
     'The team\u2019s heritage spans from early reusable rocket experimentation through NASA contract '
     'performance and current USAF programs, representing one of the deepest institutional knowledge '
     'bases in reusable liquid rocket vehicles in the United States.', after=6)

h2('2.1 Armadillo Aerospace Heritage (2000\u20132013)')

para('The Exos engineering and management team designed, built, and flight-tested multiple families '
     'of vertical-takeoff, vertical-landing (VTVL) liquid rocket vehicles at Armadillo Aerospace:', after=4)

bold_bullet('QUAD Vehicle Family: ', 'The Texel, Pixel, and Morpheus vehicles\u2014spherical-tank '
            'VTVL platforms using LOX/ethanol propulsion. These vehicles pioneered the hanging-tether '
            'hover test methodology that was later adopted as standard practice. The team assisted FAA AST '
            'in drafting the safety legislation governing this test protocol.')

bold_bullet('MOD Vehicle Family: ', 'The MOD, SuperMOD, and Scorpius Level II vehicles\u2014modular '
            'lander architectures demonstrating precision landing, autonomous GNC, and in-flight restart.')

bold_bullet('NASA Northrop Grumman Lunar Lander Challenge: ', 'The team won the competition with Pixel, '
            'demonstrating autonomous point-to-point powered landing\u2014a capability that directly '
            'informed NASA\u2019s subsequent lunar lander programs.')

add_img('VOLUME_II_Technical_231005_RB_004_image1.png', 3.5,
        'Figure 2. Armadillo Aerospace QUAD vehicle (Pixel/Texel) \u2014 predecessor to Exos platforms')

h2('2.2 NASA Morpheus Lunar Lander (NASA JSC Contract)')

para('Following the team\u2019s success in the Lunar Lander Challenge, NASA Johnson Space Center awarded '
     'a contract to build Morpheus\u2014a scaled-up QUAD-derived lander. Morpheus served dual purposes:', after=4)

bullet('Integration and flight testing of JPL\u2019s Autonomous Landing and Hazard Avoidance Technology '
       '(ALHAT), including lidar-based Hazard Detection Systems, Doppler velocimeters, and laser altimeters')
bullet('Integration of a NASA JSC Propulsion Department LOX/LCH4 engine, first test-stand tested at the '
       'Exos team\u2019s Caddo Mills facility')

para('Morpheus was subsequently flown at a custom-built test range at Kennedy Space Center and '
     'successfully landed autonomously on a simulated lunar surface, demonstrating the team\u2019s '
     'ability to deliver flight-ready hardware under government contract with stringent safety and '
     'performance requirements.', after=6)

add_img('VOLUME_II_Technical_231005_RB_004_image2.png', 3.5,
        'Figure 3. NASA Morpheus autonomous landing at Kennedy Space Center simulated lunar terrain')

h2('2.3 BLK3 PSRLV Development (2014\u2013Present)')

para('Exos Aerospace developed the BLK3 Precision Reusable Suborbital Launch Vehicle under a '
     'USAF/AFWERX Phase II SBIR contract. The BLK3 validated Exos\u2019s proprietary Type V linerless '
     'composite integral tank technology (manufactured by sister company Scorpius Space Launch Company), '
     'flight avionics, GNC software derived from NASA Morpheus heritage, and the Automated Flight Safety '
     'System (AFS).', after=4)

para('Key BLK3 technical achievements:', after=2)
bullet('Successful hanging-tether hover tests validating propulsion, avionics, and GNC integration')
bullet('Type V linerless composite tanks at TRL 9 \u2014 later selected for Intuitive Machines lunar missions')
bullet('Automated Flight Safety System (AFS) with independent navigation, CPU, and power source')
bullet('Legacy NASA-licensed flight software customized for suborbital and RDRE integration missions')
bullet('FAA-licensed reusable launch operations from Spaceport America, NM (Greenville, TX is the manufacturing and hover-test facility)')

add_img('VOLUME_II_Technical_231005_RB_004_image3.png', 5.0,
        'Figure 4. BLK3 PSRLV hover test, static fire, and tether operations at Greenville, TX')

# ============================================================
# 3. ORGANIZATIONAL CAPABILITIES
# ============================================================
h1('3. Organizational Capabilities')

h2('3.1 Core Competencies')

para('Reusable Suborbital Launch Platform (BLK3 PSRLV)', bold=True, after=2)
bullet('Reusable launch vehicle: 50\u2013135 kg payloads above the K\u00e1rm\u00e1n line (100+ km)')
bullet('FAA-licensed launch operations from Spaceport America, NM (14 CFR \u00a7431, transitioning to Part 450); Greenville, TX is the manufacturing and hover-test facility')
bullet('Rapid turnaround: weeks between flights, multiple flights per month')
bullet('3\u20134 minutes microgravity; Mach 3\u20135+ reentry; full vehicle recovery and reuse')
bullet('Ruggedized COTS single-board flight computer; JAVAD high-dynamic GPS; EMCORE/Systron-Donner IMU')
bullet('Redundant navigation sensors for higher reliability mission profiles')

para('Rotating Detonation Rocket Engine (RDRE) Development', bold=True, after=2)
bullet('Active USAF SBIR Phase II (FA9300-25-C-6022, $1.9M) for Hybrid Vehicle Rocket with Government-Furnished RDRE')
bullet('NASA Marshall Space Flight Center Data Usage Agreement for RDRE development')
bullet('EXOS-HVVR demonstrator design: carbon composite vehicle with GFE RDRE integration')
bullet('Targeting 25%+ Isp improvement over conventional combustion')
bullet('Pathfinder flight demonstration planned Q1\u2013Q2 2027')

add_img('VOLUME_II_Technical_231005_RB_004_image6.png', 2.5,
        'Figure 5. EXOS-HVVR RDRE Demonstrator \u2014 conceptual design for SBIR Phase II')

para('Cryogenic Systems (via Scorpius Space Launch Company)', bold=True, after=2)
bullet('Type 5 linerless composite cryogenic tank technology at TRL 9')
bullet('Flight-proven on Intuitive Machines Odysseus (IM-1) and Athena lunar landers')
bullet('Composite Overwrapped Pressure Vessel (COPV) manufacturing')
bullet('Applications: long-duration zero-boiloff cryo storage, in-space refueling, reusable launch tankage')

para('BLK4 Multi-Purpose Hypersonic Vehicle', bold=True, after=2)
bullet('Upsized BLK3 derivative: 48 in diameter, ~48 ft length, 27,300 lb GLOW')
bullet('Lofted trajectory: ~2,200 km range, ~1,100 km apogee, up to Mach 20')
bullet('Depressed trajectory: ~1,200 km range, ~110 km apogee, up to Mach 15')
bullet('Single vehicle architecture covering SRBM through IRBM-class profiles')
bullet('Designed under MACH-XL aligned prototype OTA framework')

h2('3.2 Prototype Delivery Capabilities')
para('Exos maintains end-to-end prototype delivery capability across:', after=2)
bold_bullet('Hardware: ', 'Propulsion systems, launch vehicle structures, cryogenic tanks, payload integration, avionics, recovery systems, hypersonic target vehicles')
bold_bullet('Software: ', 'Flight control (NASA Morpheus heritage), mission planning, telemetry and data acquisition, automated flight safety')
bold_bullet('Technical Data: ', 'Flight test reports, trajectory analyses, thermal environment analyses, design documentation, safety analyses')
bold_bullet('Test Services: ', 'Static fire, hanging-tether hover, free-flight, suborbital launch, environmental testing, TRL advancement campaigns')

h2('3.3 Facilities')
add_table(
    ['Facility', 'Location', 'Capabilities'],
    [
        ['HQ & Integration', 'Greenville, TX', 'Vehicle assembly, payload integration, avionics lab, propellant handling'],
        ['Licensed Launch Site', 'Spaceport America, NM', 'FAA-licensed launch operations (14 CFR §431)'],
        ['Scorpius Manufacturing', 'Torrance, CA', 'Cryogenic tank fabrication, COPV production, composite tooling'],
    ]
)

para('Exos maintains active engagement with the University Consortium for Applied Hypersonics (UCAH) at '
     'Texas A\u0026M University, providing access to hypersonic test infrastructure and academic collaboration.', after=8, before=6)

# ============================================================
# 4. OTA EXPERIENCE
# ============================================================
h1('4. Other Transaction Authority Experience')

para('Exos has direct experience operating under government prototype and technology development agreements:', after=4)

bold_bullet('USAF SBIR Phase II (FA9300-25-C-6022): ', 'Active $1.9M contract with Air Force Test Center (AFTC) for RDRE hardware development and flight test integration. Milestone-based performance with hardware deliverables.')
bold_bullet('USAF SBIR Phase I (FA9300-24-P-6006): ', 'Completed $189K contract for hypersonic vehicle development concept.')
bold_bullet('NASA JSC Morpheus Contract: ', 'Full vehicle design, manufacture, integration, and autonomous flight test at KSC under NASA contract. Demonstrated government hardware delivery with flight safety compliance.')
bold_bullet('NASA MSFC Data Usage Agreement: ', 'Active collaboration for RDRE technology development with Marshall Space Flight Center.')
bold_bullet('NASA REDDI/Flight Opportunities Programs: ', 'Prior suborbital flight services under NASA commercial programs.')
bold_bullet('MACH-XL White Paper: ', 'BLK4 hypersonic target vehicle proposed under prototype OTA framework for MDA, structured as fixed-price, milestone-aligned execution.')

para('While Exos has not served as an OT Consortium Manager, our experience as a performer under '
     'milestone-based government agreements with hardware deliverables directly maps to the Project-Level '
     'Performer role envisioned under EPIC. We are experienced in operating within structured reporting '
     'frameworks (monthly technical status reports, quarterly financial reports, milestone reviews).', after=8)

add_img('VOLUME_II_Technical_231005_RB_004_image5.png', 4.5,
        'Figure 6. BLK3 PSRLV hanging-tether hover test under USAF/AFWERX SBIR Phase II')

# ============================================================
# 5. QUALITY CONTROL
# ============================================================
h1('5. Quality Control & Risk Management')

h2('5.1 Quality Assurance')
para('Exos maintains quality control practices consistent with aerospace flight hardware production:', after=2)
bullet('Configuration management and change control processes for flight hardware')
bullet('Inspection and acceptance protocols for propulsion, structural, and avionics subsystems')
bullet('Traceability of materials and components through the supply chain')
bullet('Post-flight analysis and anomaly resolution processes')
bullet('Documentation and lessons-learned integration across 20+ years of flight campaigns')
bullet('Type V composite tank quality processes validated through lunar mission acceptance (Intuitive Machines)')

h2('5.2 Risk Management')
para('Exos employs a structured risk management approach for all prototype and flight programs:', after=2)
bold_bullet('Risk Identification: ', 'Technical, schedule, cost, and safety risks catalogued at program initiation')
bold_bullet('Risk Mitigation: ', 'Active mitigation plans with quantified residual risk acceptance')
bold_bullet('Schedule Management: ', 'Milestone-based execution with regular progress reviews')
bold_bullet('Safety: ', 'FAA-compliant safety protocols for launch operations, propellant handling, and personnel protection. Automated Flight Safety System (AFS) provides independent flight termination capability.')
bold_bullet('Reusability Advantage: ', 'Vehicle recovery and reuse reduces per-iteration cost and schedule risk for prototype campaigns, enabling faster design-test-learn cycles than expendable approaches')
bold_bullet('Flight Heritage De-Risk: ', 'Over two decades of liquid rocket vehicle operations have produced a mature anomaly resolution database and institutional knowledge base that reduces risk on new prototype efforts')

# ============================================================
# 6. SECURITY
# ============================================================
h1('6. Security Practices')

para('Exos Aerospace is registered and active in SAM.gov (CAGE: 7EMY6, UEI: CK24BPZGF854). '
     'The company operates under the following security framework:', after=4)

bold_bullet('ITAR/EAR Compliance: ', 'Exos and Scorpius technologies are subject to ITAR controls. The company maintains Technology Control Plans (TCPs) and compliance programs for export-controlled articles and technical data.')
bold_bullet('Cybersecurity: ', 'Information systems and communications are managed in accordance with NIST SP 800-171 requirements for controlled unclassified information (CUI).')
bold_bullet('Physical Security: ', 'Controlled access to manufacturing, integration, and launch facilities at Greenville, TX and Torrance, CA.')
bold_bullet('Foreign Ownership: ', 'Exos Aerospace is a U.S.-owned and U.S.-controlled entity with no Foreign Ownership, Control, or Influence (FOCI). The company maintains a European subsidiary (Exos Aerospace Italia, Srl) for allied-nation commercial operations, structured to maintain ITAR compliance.')
bold_bullet('Personnel Security: ', 'Key personnel are U.S. persons. Exos does not currently hold a facility clearance; however, facility and individual clearance applications can be initiated as required by specific Project-Level Orders under the EPIC consortium framework.')

# ============================================================
# 7. PERSONNEL
# ============================================================
h1('7. Personnel Qualifications')

add_table(
    ['Name', 'Title', 'Qualifications'],
    [
        ['John Quinn', 'CEO & Cofounder', 'Executive leadership of reusable launch programs; government contract management; Series A capital raise; international business development'],
        ['Neil Milburn', 'COO & Program Manager', 'Decades of aerospace engineering and program management; technical authority for BLK3, BLK4, and RDRE programs; NASA Morpheus PM; Armadillo Aerospace veteran'],
        ['Russell Blink', 'CTO & Principal Investigator', 'Principal Investigator for MACH-XL and SBIR programs; lead systems engineer for BLK3/BLK4 vehicle architecture; Armadillo Aerospace veteran; deep expertise in GNC, propulsion, and flight software'],
    ]
)

para('', after=4)
para('Exos maintains a lean technical team with deep expertise in propulsion, structures, avionics, and '
     'flight operations spanning over 20 years of continuous liquid rocket vehicle development. The team '
     'has collectively designed, built, and flown more than a dozen unique liquid rocket vehicle '
     'configurations across the QUAD, MOD, SARGE, and BLK vehicle families.', after=4)

para('No personnel currently hold active security clearances. For PLO efforts requiring cleared '
     'personnel, Exos has established teaming relationships and can augment accordingly. Clearance '
     'applications will be processed in coordination with the Consortium Manager and cognizant '
     'security authority as specific PLO requirements dictate.', after=8)

# ============================================================
# 8. PAST PERFORMANCE
# ============================================================
h1('8. Relevant Past Performance')

add_table(
    ['Program', 'Customer', 'Value', 'Status', 'Relevance'],
    [
        ['SBIR Phase II \u2014 RDRE', 'USAF AFTC\n(FA9300-25-C-6022)', '$1.9M', 'Active', 'Hardware prototyping under milestone-based govt. agreement'],
        ['SBIR Phase I \u2014 Hypersonic', 'USAF AFTC\n(FA9300-24-P-6006)', '$189K', 'Complete', 'Concept development & feasibility'],
        ['Morpheus Lunar Lander', 'NASA JSC', 'Contract', 'Complete', 'Full vehicle design/build/fly under govt. contract at KSC'],
        ['RDRE Development', 'NASA MSFC (DUA)', 'N/A', 'Active', 'Joint technology development with government lab'],
        ['Cryo Tanks \u2014 Odysseus', 'Intuitive Machines', 'Commercial', 'Complete', 'TRL 9 cryo tanks on lunar surface'],
        ['Cryo Tanks \u2014 Athena', 'Intuitive Machines', 'Commercial', 'Complete', 'Second lunar mission, flight-proven'],
        ['Launch Services', 'entX Pty Ltd (Australia)', 'Commercial', 'Active', 'International payload customer'],
        ['BLK3 Wet Lease', 'Space COTAN / HOSPO (Japan)', 'Commercial', 'Active', 'International launch partnership'],
    ]
)

h2('8.1 Technology Readiness Summary')
add_table(
    ['Subsystem', 'TRL', 'Heritage'],
    [
        ['Type V Linerless Composite Tanks', '9', 'Lunar surface operations (IM-1 Odysseus, Athena)'],
        ['Flight Avionics & GNC', '9', '20+ years, multiple vehicle families, NASA Morpheus'],
        ['Automated Flight Safety System', '7', 'BLK3 flight-qualified'],
        ['COPV Pressurization (PRESSURMAX)', '9', 'Multiple vehicle flights'],
        ['Liquid Rocket Propulsion', '9', 'QUAD, MOD, BLK3 flight heritage'],
        ['RDRE Integration (HVVR)', '4', 'Design complete, SBIR Phase II active'],
        ['BLK4 Hypersonic Vehicle', '5\u20136', 'Derived from TRL 9 subsystems, new integration'],
    ]
)

# ============================================================
# 9. FEEDBACK
# ============================================================
h1('9. Feedback on EPIC Structure')

para('In response to AFRL\u2019s request for feedback on how the Government can best satisfy its needs:', after=6)

p = doc.add_paragraph()
r = p.add_run('1. Nontraditional Contractor Access: ')
r.bold = True; r.font.color.rgb = DARK
r2 = p.add_run('The EPIC consortium should actively lower barriers for nontraditional defense contractors and small businesses to participate as Project-Level Performers. Many innovative hardware-focused companies (propulsion, launch systems, advanced materials) lack the administrative infrastructure to navigate complex consortium onboarding. Streamlined onboarding and simplified proposal formats for PLOs would increase the diversity and quality of prototype solutions available to AFRL.')
r2.font.color.rgb = DARK
p.paragraph_format.space_after = Pt(6)

p = doc.add_paragraph()
r = p.add_run('2. Hardware Prototype Emphasis: ')
r.bold = True; r.font.color.rgb = DARK
r2 = p.add_run('We encourage AFRL to ensure the EPIC structure accommodates hardware-intensive prototyping (propulsion, flight vehicles, cryogenic systems) alongside software and IT-centric projects. Milestone-based payments and appropriate cost structures for hardware builds and flight tests will attract the companies best positioned to deliver physical prototypes.')
r2.font.color.rgb = DARK
p.paragraph_format.space_after = Pt(6)

p = doc.add_paragraph()
r = p.add_run('3. Flight Test as TRL Advancement: ')
r.bold = True; r.font.color.rgb = DARK
r2 = p.add_run('Exos recommends that the EPIC framework recognize commercial reusable launch platforms as TRL advancement tools. Rapid-cycle suborbital flight testing can mature technologies from TRL 4\u20135 to TRL 6\u20137 in months rather than years, directly supporting AFRL\u2019s goal of timely capability delivery to the warfighter.')
r2.font.color.rgb = DARK
p.paragraph_format.space_after = Pt(6)

p = doc.add_paragraph()
r = p.add_run('4. Security Tiering: ')
r.bold = True; r.font.color.rgb = DARK
r2 = p.add_run('For PLOs that do not require classified work, we recommend a tiered security approach that does not impose TS/SCI overhead on unclassified prototyping efforts, which would unnecessarily exclude innovative small businesses and nontraditional contractors from the consortium.')
r2.font.color.rgb = DARK
p.paragraph_format.space_after = Pt(6)

p = doc.add_paragraph()
r = p.add_run('5. Production Pathway Integration: ')
r.bold = True; r.font.color.rgb = DARK
r2 = p.add_run('EPIC should provide a clear pathway from prototype PLO to follow-on production contracts. Companies like Exos that can demonstrate prototype-to-production scalability (as detailed in our BLK4/MACH-XL concept) are best positioned to deliver enduring capability, but only if the consortium structure bridges the prototype-production gap.')
r2.font.color.rgb = DARK
p.paragraph_format.space_after = Pt(8)

# ============================================================
# 10. CONCLUSION
# ============================================================
h1('10. Conclusion')

para('Exos Aerospace is a qualified nontraditional defense contractor and small business with active USAF '
     'contracts, over two decades of liquid rocket vehicle flight heritage, flight-proven hardware including '
     'lunar-qualified cryogenic systems, and demonstrated prototype delivery capability under government contract. '
     'Our team\u2019s heritage\u2014from Armadillo Aerospace through NASA Morpheus to current USAF SBIR and RDRE '
     'programs\u2014represents one of the most experienced reusable liquid rocket vehicle teams in the country.', after=6)

para('We are interested in participating as a Project-Level Performer within the EPIC consortium and welcome '
     'the opportunity to contribute rapid-cycle hardware prototyping, flight test, and technology demonstration '
     'services to AFRL\u2019s technology pipeline.', after=6)

para('We look forward to continued engagement as the EPIC program develops.', after=16)

# Signature block
para('\u2500' * 60, after=8)

# Footer with logo
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.LEFT
run = p.add_run()
footer_logo = os.path.join(IMG, 'VOLUME_II_Technical_231005_RB_004_image12.png')
if os.path.exists(footer_logo):
    run.add_picture(footer_logo, width=Inches(4.0))

para('', after=2)
para('Exos Aerospace Systems & Technologies, Inc.', bold=True, size=11, after=2)
para('299 FM 1903, Greenville, TX 75402', size=11, after=2)
para('John Quinn, CEO \u2014 jquinn@exosaero.com \u2014 +1-972-740-8355', size=11, after=2)
para('CAGE: 7EMY6  |  UEI: CK24BPZGF854', size=11, after=8)
para('This response is submitted for informational purposes only in response to RFI-RFZF-B001 '
     'and does not constitute an offer or commitment.', italic=True, size=9, after=0)

# Save
output = '/Users/exomac/.openclaw/workspace/drafts/EPIC-RFI-RFZF-B001-Exos-Aerospace-Response.docx'
doc.save(output)
print(f'Saved: {output}')
