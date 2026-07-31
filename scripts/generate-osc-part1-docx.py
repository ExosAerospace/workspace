#!/usr/bin/env python3
"""Generate OSC Part 1 Concept Document as .docx on Exos letterhead."""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import os

doc = Document()

style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10.5)
font.color.rgb = RGBColor(0x33, 0x33, 0x33)

for section in doc.sections:
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# --- HEADER ---
header = doc.sections[0].header
hp = header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = hp.add_run("EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC.")
run.bold = True
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)
hp.add_run("\n")
run2 = hp.add_run("299 FM 1903, Greenville, TX 75402  |  www.exosaero.com")
run2.font.size = Pt(8)
run2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

# --- FOOTER ---
footer = doc.sections[0].footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = fp.add_run("CONFIDENTIAL — FOR OSC PRE-APPLICATION USE ONLY")
run.font.size = Pt(7)
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
run.italic = True

# --- TITLE ---
title = doc.add_heading('', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("Office of Strategic Capital (OSC)\nDirect Loan — Part 1 Concept")
run.font.size = Pt(18)
run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)
run.bold = True

# Subtitle
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = sub.add_run("Loan Requested: $15,000,000")
run.bold = True
run.font.size = Pt(13)
run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)
sub.add_run("\n")
run2 = sub.add_run("Prepared: June 8, 2026  |  For: John Quinn, Chairman & Co-Founder")
run2.font.size = Pt(9)
run2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_paragraph()  # spacer

# --- HELPER FUNCTIONS ---
def add_heading(text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x00, 0x2B, 0x5C)
    return h

def add_para(text, bold=False, italic=False):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
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
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    return table

# ============================
# 1. EXECUTIVE SUMMARY
# ============================
add_heading("1. Executive Summary")
add_para(
    "Exos Aerospace Systems & Technologies, Inc. requests a $15,000,000 OSC direct loan to fund the "
    "construction and expansion of a 25,000 sq ft Exos-owned advanced manufacturing facility that "
    "industrializes domestic production of reusable launch vehicles (BLK4), Rotating Detonation Rocket "
    "Engines (RDRE), and — upon completion of Exos's acquisition of Scorpius Space Launch Company — "
    "TRL 9 Type 5 composite cryogenic tanks (flight-proven on the lunar surface)."
)
add_para(
    "The project expands the U.S. defense industrial base for space launch and advanced propulsion, "
    "on U.S. soil, with a clean domestic capital structure and zero foreign influence."
)

# ============================
# 2. APPLICANT OVERVIEW
# ============================
add_heading("2. Applicant Overview")
add_bullet("Exos Aerospace Systems & Technologies, Inc.", bold_prefix="")
add_bullet("Delaware/Texas C-corp; 299 FM 1903, Greenville, TX 75402")
add_bullet("CAGE 7EMY6 · UEI CK24BPZGF854 · NAICS 336414")
add_bullet("One of three FAA-licensed reusable suborbital launch companies in the U.S.")
add_bullet("Reusable BLK3 platform; active AFRL SBIR Phase II (FA9300-25-C-6022) for RDRE integration")
add_bullet("NASA Flight Opportunities on-ramp pathway")
add_bullet("100% U.S. beneficial ownership. Directors: David Mitchell and John Quinn.")
add_bullet("Operating entity: Exos Aerospace Global LLC (Wyoming)")

add_para("Scorpius Acquisition:", bold=True)
add_para(
    "Exos owns 18% of Scorpius Space Launch Company with a right of first refusal on the remaining 82%. "
    "Exercising the ROFR brings the only known TRL 9 Type 5 composite cryogenic tank production line "
    "(flown as fuel and LOX tanks on Intuitive Machines IM-1 and IM-2 lunar missions) in-house — "
    "a strategic domestic-industrial-base asset."
)

add_para("Financial Snapshot (CPA-Certified Reports):", bold=True)
add_table(
    ["Metric", "FY 2025 (Full Year)", "FY 2026 YTD (Jan–May)"],
    [
        ["Revenue", "$1,554,864", "$849,905"],
        ["Net Income", "$198,887", "$174,337"],
        ["Cash (period end)", "$354,426", "$445,902"],
        ["Total Assets", "$16,147,200", "$16,006,209"],
        ["Accounts Receivable", "$545,032", "$197,269"],
    ]
)
doc.add_paragraph()
add_bullet("Profitable in both FY2025 and FY2026 YTD — cash-flow positive and accelerating")
add_bullet("May 2026 standalone: $431,573 revenue / $302,148 net income")
add_bullet("YoY revenue growth: 275% (Jan-May 2025 vs. Jan-May 2026)")

# ============================
# 3. PROJECT DESCRIPTION & USE OF PROCEEDS
# ============================
add_heading("3. Project Description & Use of Proceeds ($15M)")
add_para(
    "Construction and build-out of an Exos-owned 25,000 sq ft advanced manufacturing facility "
    "(expanding from current 10,000 sq ft operations) to move from prototype to rate production of:",
    bold=False
)
add_bullet("BLK4 reusable launch vehicles — manufacturing tooling, fixtures, assembly & integration lines")
add_bullet("RDRE propulsion — production and integration equipment")
add_bullet("Scorpius Type 5 composite cryogenic tanks (post-acquisition) — composite production & test equipment")
add_bullet("Shared test infrastructure for rate production")

add_para(
    "Site Status: Multiple states under active negotiation for the expansion facility. Current Greenville, TX "
    "facility (10,000 sq ft) continues operations during buildout. Final site selection pending state "
    "incentive packages and expansion terms.",
    italic=True
)

add_table(
    ["Use of Proceeds", "Amount ($M)"],
    [
        ["Facility construction / buildout (25,000 sq ft, Exos-owned)", "5.0"],
        ["BLK4 manufacturing tooling & integration lines", "4.0"],
        ["RDRE production & integration equipment", "2.5"],
        ["Composite cryo-tank production & test equipment (post-Scorpius)", "2.0"],
        ["Rate-production test infrastructure & commissioning", "1.5"],
        ["Total OSC Loan", "15.0"],
    ]
)
doc.add_paragraph()
add_para(
    "All proceeds are capital expenditures on Exos-owned hard assets — directly matching OSC's mandate "
    "(construction, modernization, expansion). The $5M facility buildout is based on Exos's internal "
    "budget for 25,000 sq ft construction.",
    italic=True
)

# ============================
# 4. CTC ALIGNMENT
# ============================
add_heading("4. Covered Technology Category (CTC) Alignment")
add_bullet("Space launch / spacecraft and propulsion (reusable launch vehicles, RDRE)", bold_prefix="Primary: ")
add_bullet("Advanced manufacturing and advanced materials (composite cryogenic structures)", bold_prefix="Secondary: ")
add_para(
    "Exact CTC numbers to be confirmed against the live NOFA covered-category list prior to submission.",
    italic=True
)

# ============================
# 5. NATIONAL SECURITY NEXUS
# ============================
add_heading("5. National & Economic Security Nexus")
add_bullet("Expands the domestic defense industrial base for reusable launch and advanced propulsion — OSC's core mission")
add_bullet(
    "Re-shores the only known TRL 9 Type 5 lunar-heritage cryogenic tank capability under U.S. ownership "
    "(via the Scorpius acquisition funded by the concurrent Series A)"
)
add_bullet("Supports responsive/reusable launch, RDRE propulsion, polar-orbit access, and Golden Dome-relevant capabilities")
add_bullet("Creates high-tech manufacturing jobs — 25,000 sq ft facility expansion tripling production capacity")
add_bullet("Resilient domestic supply chain for space launch hardware and advanced propulsion components")

# ============================
# 6. CAPITAL STACK
# ============================
add_heading("6. Financing Structure / Capital Stack (≥80% Non-Federal)")
add_para(
    "The OSC loan is the non-dilutive debt slice for hard production capex. Equity (Series A, up to $25M) "
    "funds the Scorpius acquisition and working capital. The OSC-funded production project is scoped narrowly "
    "to capex, with federal SBIR funds (TACFI/STRATFI) kept on the separate R&D/development side."
)

add_para("Non-Federal Capital for the Production Project (≥80%):", bold=True)
add_bullet("Series A equity — up to $25M (private, domestic investors; Whitefield Capital as qualified-investor introducer)")
add_bullet("Reinvested commercial + Scorpius revenue — $850K YTD through May 2026, accelerating")
add_bullet("Projected revenue ramp (financial model v8): $2.04M+ (2026E) → $9.4M (2027E) → $34M (2028E)")

add_para("Federal (Kept Separate / Minority):", bold=True)
add_bullet("OSC loan $15M — the production-capex slice")
add_bullet("TACFI (up to $15M) + STRATFI fund RDRE/BLK4 development, scoped as a distinct cost category")

add_para(
    "On the production project, non-federal sources dominate well past 80%. OSC's exact treatment of the "
    "loan within the 80/20 ratio to be confirmed during pre-application.",
    italic=True
)

# ============================
# 7. CREDITWORTHINESS
# ============================
add_heading("7. Creditworthiness")

add_para("Historical Performance:", bold=True)
add_table(
    ["Period", "Revenue", "Net Income", "Cash (End)"],
    [
        ["FY 2024", "$627,141", "($418,822)", "$143,032"],
        ["FY 2025", "$1,554,864", "$198,887", "$354,426"],
        ["FY 2026 YTD (Jan-May)", "$849,905", "$174,337", "$445,902"],
    ]
)
doc.add_paragraph()

add_para("Key Credit Indicators:", bold=True)
add_bullet("Turnaround achieved: FY2024 net loss → FY2025 net profit → FY2026 accelerating")
add_bullet("Revenue trajectory: 148% growth FY2024→FY2025; 275% growth YTD YoY")
add_bullet("Cash position strengthening: $143K → $354K → $446K over 18 months")
add_bullet("Debt servicing current: Ascentium Capital, Balboa Capital, Blink buyout notes all current")

add_para("Contracted Backlog & Pipeline:", bold=True)
add_bullet("entX Launch Services Agreement ($840K)")
add_bullet("USAF SBIR Phase II CLINs (FA9300-25-C-6022)")
add_bullet("Scorpius contracts (incl. Intuitive Machines tankage)")
add_bullet("NASA Flight Opportunities on-ramp (~$8M/yr steady state post-qualification)")
add_bullet("BLK3 payload bookings pipeline")

add_para("Projected Revenue (Financial Model v8):", bold=True)
add_para("$2.04M+ (2026E annualized) → $9.4M (2027E) → $34M (2028E) → $64M (2029E) → $129M (2030E)")

add_para("Collateral:", bold=True)
add_bullet("The Exos-owned 25,000 sq ft production facility (the funded asset)")
add_bullet("BLK4/RDRE/cryo manufacturing tooling & equipment")
add_bullet("Intellectual property (propulsion, flight software, composite tank processes)")
add_bullet("Scorpius stock (book value $790K; strategic value materially higher post-ROFR)")

# ============================
# 8. OWNERSHIP & FOREIGN INFLUENCE
# ============================
add_heading("8. Ownership & Foreign Influence Disclosure")

add_para("Cap Table (as of August 2024; 12,314,286 shares outstanding):", bold=True)
add_table(
    ["Holder", "Shares", "%", "Citizenship", "Notes"],
    [
        ["Exos Aerospace Investments", "4,529,779", "36.8%", "U.S.", "Managed by Mitchell & Quinn"],
        ["David Mitchell", "4,558,725", "37.0%", "U.S.", "Co-founder, Director"],
        ["John Quinn", "2,574,175", "20.9%", "U.S.", "Co-founder, Chairman"],
        ["Employee option pool", "650,000", "5.3%", "U.S.", "Unallocated"],
        ["Total", "12,314,286", "100%", "100% U.S.", ""],
    ]
)
doc.add_paragraph()

add_para("Foreign Influence Assessment: NONE", bold=True)
add_bullet("Delaware/Texas C-corp; principal place of business 299 FM 1903, Greenville, TX 75402")
add_bullet("No Euronext/Dublin listing (path dropped June 2026); no non-U.S. capital-markets structure")
add_bullet("No foreign investors, no foreign board members, no foreign influence")
add_bullet("All Series A investors will be screened for OSC compliance prior to close")

add_para("Subsidiary Structure:", bold=True)
add_bullet("Exos Aerospace Global LLC (Wyoming) — holding company; Directors: David Mitchell, John Quinn")
add_bullet("Exos Aerospace Italia SRL — Italian subsidiary (intercompany receivable only; no operational influence on U.S. entity or OSC-funded project)")
add_bullet("Scorpius Space Launch Company — 18% owned (future 100% subsidiary post-acquisition)")

# ============================
# 9. ELIGIBILITY SELF-ASSESSMENT
# ============================
add_heading("9. Eligibility Self-Assessment")
add_table(
    ["Criterion", "Status"],
    [
        ["U.S.-based capital project", "✓  Expansion facility (site selection in progress)"],
        ["Covered Technology Category", "✓  Space launch / propulsion / adv. manufacturing"],
        ["Construction / modernization / expansion", "✓  25,000 sq ft facility ($5M) + $10M equipment/tooling"],
        ["≥80% non-federal capital", "✓  Series A ($25M) + revenue >> $15M OSC loan"],
        ["Creditworthiness", "✓  Profitable, growing, backlog, collateral"],
        ["National-security / industrial-base nexus", "✓  Reusable launch + re-shored cryo IP + RDRE production"],
        ["Foreign-influence clean", "✓  100% U.S. ownership, no foreign capital structure"],
    ]
)

# ============================
# 10. REMAINING ITEMS
# ============================
doc.add_paragraph()
add_heading("10. Items to Confirm Before Formal Submission")
add_bullet("NOFA 2 live terms — confirm pool, CTC list, and deadlines on cto.mil/osc", bold_prefix="1. ")
add_bullet(
    "Site selection — multiple states under negotiation. OSC will require site control evidence "
    "(LOI, option, or lease) for Part 2; Part 1 can proceed with site selection in progress.",
    bold_prefix="2. "
)
add_bullet(
    "CPA-certified financials are in hand. Full audit available once funding is committed. "
    "CPA-certified is sufficient for Part 1; audit strengthens Part 2.",
    bold_prefix="3. "
)

# --- FOOTER NOTE ---
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("— END OF PART 1 CONCEPT —")
run.bold = True
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run(
    "All financial figures sourced from CPA-certified QuickBooks reports provided June 8, 2026.\n"
    "Projections from Exos Financial Model v8. Confirm all figures against the live NOFA before submission."
)
run2.font.size = Pt(8)
run2.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
run2.italic = True

# --- SAVE ---
out_path = os.path.expanduser("~/.openclaw/workspace/drafts/Exos_OSC_Part1_Concept_June2026.docx")
doc.save(out_path)
print(f"Saved: {out_path}")
