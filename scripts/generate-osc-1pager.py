#!/usr/bin/env python3
"""Generate OSC Part 1 — 1-Page Concept Summary."""

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os

doc = Document()

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(8.5)
font.color.rgb = RGBColor(0x33, 0x33, 0x33)

pf = style.paragraph_format
pf.space_before = Pt(1)
pf.space_after = Pt(1)
pf.line_spacing = 1.0

for section in doc.sections:
    section.top_margin = Cm(1.2)
    section.bottom_margin = Cm(1.0)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)

# --- HEADER ---
header = doc.sections[0].header
hp = header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = hp.add_run("EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC.")
run.bold = True
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)
hp.add_run("\n")
run2 = hp.add_run("299 FM 1903, Greenville, TX 75402  |  www.exosaero.com  |  CAGE 7EMY6  |  UEI CK24BPZGF854")
run2.font.size = Pt(7)
run2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

# --- TITLE ---
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
title.paragraph_format.space_before = Pt(2)
title.paragraph_format.space_after = Pt(4)
run = title.add_run("OSC Direct Loan — Part 1 Concept Summary  |  $15,000,000 Request")
run.bold = True
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)

# --- HELPERS ---
def section_head(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(1)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)
    return p

def body(text):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(1)
    for r in p.runs:
        r.font.size = Pt(8.5)
    return p

def small_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(7.5)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(7.5)
    return table

# ============================
# CONTENT
# ============================

section_head("THE ASK")
body(
    "Exos Aerospace requests a $15M OSC direct loan to construct a 25,000 sq ft advanced manufacturing "
    "facility (expanding from 10,000 sq ft) for rate production of BLK4 reusable launch vehicles, RDRE "
    "propulsion systems, and — post-acquisition of Scorpius Space Launch Company — TRL 9 Type 5 composite "
    "cryogenic tanks (flight-proven on the lunar surface via Intuitive Machines IM-1/IM-2)."
)

section_head("USE OF PROCEEDS (ALL CAPEX)")
small_table(
    ["Use of Proceeds", "$M"],
    [
        ["Facility construction / buildout (25,000 sq ft)", "5.0"],
        ["BLK4 manufacturing tooling & integration lines", "4.0"],
        ["RDRE production & integration equipment", "2.5"],
        ["Composite cryo-tank production (post-Scorpius)", "2.0"],
        ["Test infrastructure & commissioning", "1.5"],
        ["TOTAL", "15.0"],
    ]
)

section_head("APPLICANT")
body(
    "Exos Aerospace Systems & Technologies, Inc. — Delaware/Texas C-corp, Greenville TX. "
    "One of three FAA-licensed reusable suborbital launch companies in the U.S. Active AFRL SBIR "
    "Phase II (FA9300-25-C-6022). NAICS 336414. 100% U.S. owned — zero foreign influence."
)

section_head("FINANCIAL PERFORMANCE (CPA-CERTIFIED)")
small_table(
    ["", "FY 2024", "FY 2025", "FY 2026 YTD (Jan-May)"],
    [
        ["Revenue", "$627K", "$1,555K", "$850K"],
        ["Net Income", "($419K)", "$199K", "$174K"],
        ["Cash (end)", "$143K", "$354K", "$446K"],
    ]
)
body("Turnaround FY24→FY25. Revenue growth 275% YoY. Profitable and accelerating. All debt current.")

section_head("PROJECTED REVENUE (MODEL v8)")
body("$2.0M (2026E) → $9.4M (2027E) → $34M (2028E) → $64M (2029E) → $129M (2030E)")

section_head("CAPITAL STACK (≥80% NON-FEDERAL)")
body(
    "OSC $15M = non-dilutive debt for production capex. Series A equity (up to $25M, private domestic) "
    "funds the Scorpius acquisition + working capital. TACFI/STRATFI fund R&D separately. "
    "Non-federal sources dominate well past 80% on the production project."
)

section_head("OWNERSHIP (12.3M SHARES — 100% U.S.)")
small_table(
    ["Holder", "%", "Notes"],
    [
        ["Exos Aerospace Investments", "36.8%", "Managed by Mitchell & Quinn"],
        ["David Mitchell", "37.0%", "Co-founder, Director"],
        ["John Quinn", "20.9%", "Co-founder, Chairman"],
        ["Employee option pool", "5.3%", "Unallocated"],
    ]
)
body("No Euronext/Dublin listing. No foreign investors. No foreign board members. Clean domestic structure.")

section_head("CTC ALIGNMENT")
body(
    "Primary: space launch / spacecraft & propulsion. Secondary: advanced manufacturing, advanced materials. "
    "National-security nexus: reusable launch, RDRE propulsion, re-shored lunar-heritage cryo-tank IP, "
    "Golden Dome-relevant capabilities, domestic industrial base expansion."
)

section_head("COLLATERAL & BACKLOG")
body(
    "Collateral: funded facility, tooling/equipment, IP, Scorpius stock ($790K book). "
    "Backlog: entX LSA ($840K), USAF SBIR Phase II CLINs, Scorpius/IM contracts. "
    "Pipeline: NASA Flight Opportunities (~$8M/yr), BLK3 payload bookings."
)

# --- FOOTER ---
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("CONFIDENTIAL — Prepared June 8, 2026 for OSC pre-application use")
run.font.size = Pt(7)
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
run.italic = True

out_path = os.path.expanduser("~/.openclaw/workspace/drafts/Exos_OSC_Part1_OnePager_June2026.docx")
doc.save(out_path)
print(f"Saved: {out_path}")
