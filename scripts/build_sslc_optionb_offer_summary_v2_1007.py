#!/usr/bin/env python3
"""Rebuild Exos_SSLC_OptionB_Offer_Summary_2026-10-07.docx  — 2-page max.
John rules 2026-10-07 15:22-15:28 + 2026-10-09 update (14:12):
  - Section 1: offer value TABLE (Component | Low | Base | High | Trigger/Timing)
  - 10/9 UPDATE: 1.0% EAI units at close (~$1.697M at 409A $169.7M); subtotal at close ~$6.06M
  - 10/9 UPDATE: described as "EAI units issued as part of Exos's Rule 504 offering, at the 409A value"
  - Stock earn-out: 0.0/0.25/0.5% (unchanged); total equity: 1.0%/1.25%/1.5%
  - Expected totals: ~$7.0M / $8.58M / $10.16M (HIGH case back above $10M)
  - Framing line in John's voice after the table
  - No SSLC year-by-year revenue tables or growth projections
  - Keep 'negotiating terms', no Counsel gates, keep Eqvista wording
  - Name: John Quinn (not Jon Quinn); lockup: same as Exos principals
  - Model note: Rule 504 $10M cap; Rule 504 is U.S.-only (distinct from Japan Reg S round)
"""
import os, shutil, subprocess
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

WS   = "/Users/exomac/.openclaw/workspace"
TMPL = os.path.join(WS, "assets", "EXOS_Letterhead_Greenville_TX_PRIMARY.docx")
RAW  = os.path.join(WS, "drafts", "_sslc_optionb_v2_raw.docx")
OUT  = os.path.join(WS, "drafts", "Exos_SSLC_OptionB_Offer_Summary_2026-10-07.docx")
PDF  = os.path.join(WS, "drafts", "Exos_SSLC_OptionB_Offer_Summary_2026-10-07.pdf")

NAVY  = RGBColor(0x1F, 0x3A, 0x68)
BLUE  = RGBColor(0x2E, 0x75, 0xB6)
BLACK = RGBColor(0x00, 0x00, 0x00)
RED   = RGBColor(0xC0, 0x00, 0x00)
GREEN = RGBColor(0x37, 0x56, 0x23)
GREY  = RGBColor(0x60, 0x60, 0x60)

shutil.copy(TMPL, RAW)
doc = Document(RAW)
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(10)

# ── helpers ──────────────────────────────────────────────────────────────────
def P(text="", bold=False, size=None, color=None, italic=False,
      sa=3, sb=0, indent=None, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after  = Pt(sa)
    p.paragraph_format.space_before = Pt(sb)
    if indent: p.paragraph_format.left_indent = Inches(indent)
    if align:  p.alignment = align
    if text:
        r = p.add_run(text)
        r.bold=bold; r.italic=italic
        if size:  r.font.size=Pt(size)
        if color: r.font.color.rgb=color
    return p

def H1(text, sb=6):
    p = P(text, bold=True, size=12, color=NAVY, sa=3, sb=sb)
    p.paragraph_format.keep_with_next = True
    return p

def H2(text):
    p = P(text, bold=True, size=10.5, color=BLUE, sa=2, sb=3)
    p.paragraph_format.keep_with_next = True
    return p

def body(text):
    P(text, size=10, sa=3)

def B(lead, rest=""):
    p = P(sa=2, indent=0.2)
    p.add_run("•  ")
    if lead:
        r = p.add_run(lead); r.bold=True
    if rest:
        p.add_run(rest)

def note(text):
    P(text, size=8.5, italic=True, color=GREY, sa=2)

def shaded_cell(cell_obj, hex_fill):
    tc = cell_obj._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)

def add_table(rows_data, col_widths, hdr_fill="1F3A68"):
    t = doc.add_table(rows=len(rows_data), cols=len(rows_data[0]))
    try:    t.style = "Table Grid"
    except: pass
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), col_widths):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for i, row_vals in enumerate(rows_data):
        for j, val in enumerate(row_vals):
            cell = t.cell(i, j)
            cell.width = Inches(col_widths[j])
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(str(val) if val is not None else "")
            r.font.size = Pt(9)
            if i == 0:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                shaded_cell(cell, hdr_fill)
            elif j == 0:
                r.bold = True
    P(sa=3)
    return t

def add_offer_table():
    """Offer value table: Component | Low | Base | High | When/Notes.
    Subtotal = gray+bold; Total = green+bold; Milestone group = light blue-gray;
    Memo = amber+italic. Earn-outs labeled as negotiating terms / mgmt assumptions."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH as WDA

    DARK  = "1F3A68"
    GRAY  = "F3F4F6"
    GREEN = "D1FAE5"
    AMBER = "FEF3C7"
    MSTN  = "EFF6FF"   # milestone rows — very light blue

    col_w = [2.25, 0.80, 0.80, 0.80, 1.85]   # inches; total ~6.5"

    # (Component, Low, Base, High, Notes, kind)
    rows = [
        ("Component",                                 "Low",     "Base",    "High",    "When / Notes",                                              "header"),
        # ── Close items ───────────────────────────────────────────────────────────
        ("Cash at close",                             "$2,510K", "$2,510K", "$2,510K", "Close ~Q1 FY27",                                            "data"),
        ("SSLC transaction costs",                    "$60K",    "$60K",    "$60K",    "Close; seller-side",                                        "data"),
        ("Credit for Exos's existing stake",          "$790K",   "$790K",   "$790K",   "Close (non-cash credit)",                                   "data"),
        ("SSLC debts paid at face",                   "$500K",   "$500K",   "$500K",   "Close; ~$500K TBV in QB",                                   "data"),
        ("Working-capital bridge",                    "$500K",   "$500K",   "$500K",   "Close",                                                     "data"),
        ("Exos equity — 1.0% EAI units\n(Rule 504, at 409A ~$170M)",
                                                      "$1,697K", "$1,697K", "$1,697K", "EAI units issued as part of Exos's\nRule 504 offering, at the 409A value;\nissued at financing close",  "data"),
        ("Subtotal: funding at close",                "$6,057K", "$6,057K", "$6,057K", "",                                                          "subtotal"),
        # ── Earn-outs (negotiating terms — mgmt assumptions) ─────────────────────
        ("Tank earn-out (5 yrs, 5%/yr,\ncap $300K/yr)",
                                                      "$750K",   "$1,250K", "$1,500K", "FY27–FY31; low 3%/base 5%/high\n7% × IM rev; $300K/yr cap","data"),
        ("Milestone M1: SSLC FY2026-27 rev\n≥$5.1M",
                                                      "$200K",   "$200K",   "$200K",   "Pays FY28 Q1 if verified\n(all scenarios: mgmt base case)", "mstn"),
        ("Milestone M2: Nebula/OTV production\ncontract signed",
                                                      "—",       "$200K",   "$200K",   "Pays at contract execution\n(any year FY27–FY30)",          "mstn"),
        ("Milestone M3: SSLC annual rev ≥$10M",       "—",       "$250K",   "$250K",   "Pays first year threshold hit\n(est. FY29 at base/high)",   "mstn"),
        ("Milestone M4: SSLC annual rev ≥$20M",       "—",       "—",       "$250K",   "Pays first year threshold hit\n(est. FY31 at high)",        "mstn"),
        ("Milestone M5: BLK3 tank qualification\ncomplete",
                                                      "—",       "—",       "$200K",   "Pays at Exos BLK3 tank cert\n(est. FY27–FY28)",             "mstn"),
        ("Exos stock earn-out at listing\n(on top of 1.0% EAI up-front)",
                                                      "$0",      "$424K",   "$848K",   "Post-RTO ~FY28; earn-out 0.0%/0.25%/0.5% FD; lockup same as Exos principals.\nAt 409A ($170M): $0/$424K/$848K. Total Exos equity: 1.0%/1.25%/1.5%.", "data"),
        ("TOTAL OFFER VALUE (5-yr)",                  "$7,007K", "$8,582K", "$10,157K","FY27–FY31",                                                 "total"),
        ("Memo: Exos stock if held to FY31\n(not additive to total above)",
                                                      "$5.7M",   "$8.5M",   "$11.4M",  "16× EV/EBITDA; ~30% dilution;\ntotal stake 1.0/1.25/1.5% (EAI+earn-out);\nmgmt assumption", "memo"),
    ]

    note_text = ("Earn-out rows: negotiating terms — management assumptions. "
                 "Each milestone is independently verifiable; none pay unless the trigger is met.")
    P(note_text, size=7.5, italic=True, color=GREY, sa=2)

    t = doc.add_table(rows=len(rows), cols=5)
    try:    t.style = "Table Grid"
    except: pass
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), col_w):
        gc.set(qn("w:w"), str(int(w * 1440)))

    GREY_COLOR = RGBColor(0x6B, 0x72, 0x80)

    for i, (comp, lo, ba, hi, notes, kind) in enumerate(rows):
        vals = [comp, lo, ba, hi, notes]
        for j, val in enumerate(vals):
            cell = t.cell(i, j)
            cell.width = Inches(col_w[j])
            cell.text = ""
            p = cell.paragraphs[0]
            if j in (1, 2, 3):
                p.alignment = WDA.RIGHT

            if   kind == "header":   shaded_cell(cell, DARK)
            elif kind == "subtotal": shaded_cell(cell, GRAY)
            elif kind == "total":    shaded_cell(cell, GREEN)
            elif kind == "memo":     shaded_cell(cell, AMBER)
            elif kind == "mstn":     shaded_cell(cell, MSTN)

            for line in val.split("\n"):
                r = p.add_run(line)
                r.font.size = Pt(8)
                if kind == "header":
                    r.bold = True
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                elif kind in ("subtotal", "total"):
                    r.bold = True
                elif kind == "memo":
                    r.italic = True
                    r.font.color.rgb = GREY_COLOR
                if line != val.split("\n")[-1]:
                    p.add_run().add_break()

    P(sa=3)
    return t

# ────────────────────────────────────────────────────────────────────────────
# DOCUMENT HEADER
# ────────────────────────────────────────────────────────────────────────────
P("INTERNAL  ·  DRAFT  ·  NEGOTIATING TERMS  ·  CEO / Board Eyes Only",
  bold=True, size=9, color=RED, align=WD_ALIGN_PARAGRAPH.CENTER, sa=2)

P("EXOS AEROSPACE — SSLC OPTION B: ACQUISITION OFFER SUMMARY",
  bold=True, size=14, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER, sa=2, sb=0)

P("October 9, 2026  ·  Exos Aerospace Systems & Technologies, Inc.",
  size=9.5, italic=True, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, sa=5)

# ────────────────────────────────────────────────────────────────────────────
# SECTION 1 — WHAT SSLC HOLDERS RECEIVE
# ────────────────────────────────────────────────────────────────────────────
H1("1.  What SSLC Holders Receive")


P("Up-front price reflects today's numbers; earn-outs let SSLC holders share directly "
  "in tank deliveries, revenue milestones, and the Exos listing.",
  italic=True, size=9.5, color=BLUE, sa=3)

add_offer_table()

# Why this structure — compact callout
note("Why this structure: SSLC holders receive real Exos equity at close (1.0% EAI units, 409A-valued ~$1.7M, "
     "issued as part of Exos's Rule 504 offering) — not only contingent upside. "
     "It aligns them with Exos immediately. The earn-out stock stays 0.0–0.5%, so total equity is 1.0–1.5%.")

note("Chart: SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png  ·  "
     "Full model: EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx → 'Total Compensation' sheet  ·  "
     "IM program continuity: Exos-SSLC continues the Intuitive Machines contract with no delivery interruption.")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 4 — TERMS (SHORT BOX)
# ────────────────────────────────────────────────────────────────────────────
H1("3.  Key Terms", sb=3)

terms_rows = [
    ["Term",                         "Detail"],
    ["Agreement basis",              "May 2025 Asset Acquisition Agreement, §3 exclusivity trigger"],
    ["Total commitment",             "$5,057,000 base at close ($2.51M cash + $60K costs + $790K Exos stake credit + ~$1.70M EAI equity at 409A, Rule 504)"],
    ["Exclusivity period",           "90 days from SSLC confirmation; extension not unreasonably withheld (§3)"],
    ["Holdback (§7)",                "5% escrow, released at 12-month anniversary"],
    ["SSLC debts assumed",           "Paid at face at close (est. ~$500K; verify QuickBooks)"],
    ["Status",                       "DRAFT — NEGOTIATING TERMS — not a final or binding offer"],
]
add_table(terms_rows, [1.9, 4.1])

SEC_504_URL  = ("https://www.sec.gov/resources-small-businesses/exempt-offerings/"
                "exemption-limited-offerings-not-exceeding-10-million-rule-504-regulation-d")
RULE144_URL  = "https://www.ecfr.gov/current/title-17/chapter-II/part-230/section-230.144"
RULE10B5_URL = "https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.10b-5"

note(f"504 cap: ~$1.7M counts toward the Rule 504 $10M rolling 12-month cap; confirm remaining capacity. "
     f"Rule 504 is U.S.-only; EAI units in the Japan round are Reg S — the two must remain distinct. "
     f"See model → 'EAI Lockup & Liquidity' sheet for full detail.")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 5 — EAI UNIT LOCKUP & LIQUIDITY
# ────────────────────────────────────────────────────────────────────────────
H1("4.  EAI Unit Lockup & Liquidity", sb=3)

note(f"Restricted securities — Rule 504 Reg D, restrictive legend; not freely tradeable at issuance. "
     f"Same lockup as Exos principals. Rule 504 ref: {SEC_504_URL}")

lockup_bullets = [
    ("Rule 144 resale.  ",
     f"Holding period 6 months (reporting issuer) or 1 year (non-reporting). "
     f"Exos is currently non-reporting; 6-month path opens only after RTO. "
     f"17 CFR 230.144(d): {RULE144_URL}"),
    ("RTO structure — preferred at close.  ",
     "At RTO close, founders/legacy holders receive unregistered non-voting non-convertible preferred "
     "(avoids NASDAQ Rule 5635). Converts to common + becomes liquid only after: (i) shareholder vote "
     "(proxy ~30 days post-close) and (ii) effective resale registration (S-1/S-3). "
     "EAI units follow this same path. "
     "[Board Brief 2026-09-04:16; Board Questions 2026-09-08:36,44]"),
]
for lead, rest in lockup_bullets:
    B(lead, rest)

# Lockup timeline table
timeline_rows = [
    ["Milestone",                                "Target / Status"],
    ["Board acceptance",                         "D+0 — units committed; not yet issued"],
    ["Financing close — units issued",           "Targeted Q1 FY27; 1-yr Rule 144 clock starts"],
    ["Targeted RTO close",                       "~6 months post-financing (targeted, not assured)"],
    ["Conversion vote + resale reg. effective",  "~30–90 days post-RTO; preferred → common"],
    ["Rule 144 eligibility",                     "6-mo (after reporting); 1-yr if non-reporting at issuance"],
    ["ALL DATES",                                "Targeted, not assured. RTO may not close."],
]
add_table(timeline_rows, [2.6, 3.9], hdr_fill="375623")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 6 — PROJECTED POST-RTO VALUE
# ────────────────────────────────────────────────────────────────────────────
H1("5.  Projected Post-RTO Value  (Projection — Not a Promise)", sb=3)

note(f"Forward-looking projection — management assumptions (RTO completion, listing valuation, ~30% dilution). "
     f"Not a guarantee; actual results may differ. RTO may not close. "
     f"SEC Rule 10b-5, 17 CFR 240.10b-5 ({RULE10B5_URL}) antifraud rules apply. "
     f"409A issuance value: ~$1.70M. Up-front 1.0% EAI only; earn-out column is additional at listing.")

proj_rows = [
    ["Scenario",  "RTO MEV",  "1.0% pre-dil",  "1.0% post-dil\n(~30% dil)",  "+ earn-out at listing"],
    ["Low",       "$200M",    "$2.00M",         "$1.40M",                      "$0 (0.0%)"],
    ["Base",      "$250M",    "$2.50M",         "$1.75M",                      "+$424K (0.25%)"],
    ["High",      "$300M",    "$3.00M",         "$2.10M",                      "+$848K (0.50%)"],
]
add_table(proj_rows, [0.85, 0.85, 1.10, 1.30, 1.40])

# ────────────────────────────────────────────────────────────────────────────
# FOOTER
# ────────────────────────────────────────────────────────────────────────────
note("Detail in model: drafts/EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx  ·  "
     "With-vs-Without comparison: sheet 'With vs Without Exos Capital'  ·  "
     "Exclusivity rescue options: SSLC_Exclusivity_Rescue_Options_and_Draft_Message_2026-10-07_DRAFT_v2.docx")

P("DRAFT — INTERNAL — NEGOTIATING TERMS — John Quinn, CEO, Exos Aerospace — 2026-10-09",
  bold=True, size=8.5, color=RED, align=WD_ALIGN_PARAGRAPH.CENTER, sa=0, sb=4)

# ── save raw, apply letterhead, convert to PDF ───────────────────────────────
doc.save(RAW)
subprocess.run(
    ["/usr/bin/python3",
     os.path.join(WS, "scripts/apply_exos_letterhead.py"), RAW, OUT],
    check=True
)
os.remove(RAW)
print(f"DOCX: {OUT}")

result = subprocess.run(
    ["soffice", "--headless", "--convert-to", "pdf", "--outdir",
     os.path.join(WS, "drafts"), OUT],
    capture_output=True, text=True
)
print(f"PDF:  {PDF}  (soffice rc={result.returncode})")
if result.stderr: print("soffice stderr:", result.stderr[:300])

print("Done.")
