#!/usr/bin/env python3
"""Rebuild Exos_SSLC_OptionB_Offer_Summary_2026-10-07.docx  — 2-page max.
John rules 2026-10-07 15:22-15:28 + 2026-10-09 update (17:35):
  - Section 1: offer value TABLE (Component | Low | Base | High | Trigger/Timing)
  - 10/9 UPDATE: FIXED $1.0M EAI equity (not 1.0%); ~0.589% of $169.7M 409A; Rule 504 at financing close
  - ① $4,360K | ② $5,360K | ③ $6,310K / $7,885K / $9,460K (HIGH < $10M — not rebalanced)
  - Earn-out stock row shows LISTING values ($0/$625K/$1,500K); 409A in notes
  - Stock earn-out: 0.0/0.25/0.5% (unchanged); total equity: ~0.59%/~0.84%/~1.09%
  - Framing line in John's voice after the table
  - No SSLC year-by-year revenue tables or growth projections
  - Keep 'negotiating terms', no Counsel gates, keep Eqvista wording
  - Name: John Quinn (not Jon Quinn); EAI up-front units: float, no lockup at listing (John 10/9 option 2)
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
    hold_tint = light orange+dark-bold (IF HELD row); hold = solid orange+white-bold (④ row)."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH as WDA

    DARK        = "1F3A68"
    GRAY        = "F3F4F6"
    GREEN       = "D1FAE5"
    AMBER       = "FEF3C7"
    MSTN        = "EFF6FF"   # milestone rows — very light blue
    ORANGE      = "F26A21"   # Exos brand orange — solid fill for ④ row
    ORANGE_TINT = "FBD2BC"   # ~30% tint of #F26A21 — light fill for IF HELD row

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
        ("① Cash & debt relief at close",             "$4,360K", "$4,360K", "$4,360K", "Cash + costs + stake credit + debts + WC bridge",           "subtotal"),
        ("+ Exos equity — $1.0M fixed EAI units\n(Rule 504, ~0.59% at 409A ~$170M)",
                                                      "$1,000K", "$1,000K", "$1,000K", "EAI units issued as part of Exos's\nRule 504 offering, at the 409A value;\n$1.0M counts toward Rule 504 $10M cap;\nissued at financing close",  "data"),
        ("② Total at financing close (① + equity)",   "$5,360K", "$5,360K", "$5,360K", "",                                                          "subtotal"),
        # ── Earn-outs (negotiating terms — mgmt assumptions) ─────────────────────
        ("Tank earn-out: 5% of SSLC's IM tank\nrevenue/yr, cap $300K/yr, FY27–FY31",
                                                      "$750K",   "$1,250K", "$1,500K", "Single 5% rate; scenario = revenue\nSSLC achieves: Low $3M/yr → $150K/yr;\nBase $5M/yr → $250K/yr;\nHigh $6M+/yr → $300K/yr (cap)","data"),
        ("Milestone M1: SSLC FY2026-27 rev\n≥$5.1M",
                                                      "$200K",   "$200K",   "$200K",   "Pays FY28 Q1 if verified\n(all scenarios: mgmt base case)", "mstn"),
        ("Milestone M2: Nebula/OTV production\ncontract signed",
                                                      "—",       "$200K",   "$200K",   "Pays at contract execution\n(any year FY27–FY30)",          "mstn"),
        ("Milestone M3: SSLC annual rev ≥$10M",       "—",       "$250K",   "$250K",   "Pays first year threshold hit\n(est. FY29 at base/high)",   "mstn"),
        ("Milestone M4: SSLC annual rev ≥$20M",       "—",       "—",       "$250K",   "Pays first year threshold hit\n(est. FY31 at high)",        "mstn"),
        ("Milestone M5: BLK3 tank qualification\ncomplete",
                                                      "—",       "—",       "$200K",   "Pays at Exos BLK3 tank cert\n(est. FY27–FY28)",             "mstn"),
        ("Exos stock earn-out at listing\n(on top of ~0.59% EAI up-front)",
                                                      "$0",      "$625K",   "$1,500K", "Post-RTO ~FY29; earn-out 0.0%/0.25%/0.5% FD; lockup same as Exos principals.\nAt 409A: $0/$424K/$848K. Total Exos equity: ~0.59%/~0.84%/~1.09%.", "data"),
        ("③ TOTAL OFFER VALUE, 5-yr\n(② + earn-outs; earn-out stock at listing)",
                                                      "$6,310K", "$7,885K", "$9,460K", "FY27–FY31. HIGH < $10M target — not rebalanced.",           "total"),
        ("IF HELD: all Exos stock projected\nin FY2031 (replaces listing earn-out)",
                                                      "$6.7M",   "$9.6M",   "$12.4M",  "Total stake ~0.59/0.84/1.09% → ~0.41/0.59/0.76% after\n~30% dilution × ~$1.63B FY31 EV (16× v12 EBITDA).\nProjection only; on SSLC-actuals case ~$0.7–1.3M.", "hold_tint"),
        ("④ TOTAL IF STOCK HELD TO 2031\n(① + tank + milestones + 2031 stock)",
                                                      "$12.0M",  "$15.8M",  "$19.4M",  "Alternative to ③, NOT added to it. Forward-looking\nprojection, not a promise; RTO may not close.", "hold"),
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

            if   kind == "header":    shaded_cell(cell, DARK)
            elif kind == "subtotal":  shaded_cell(cell, GRAY)
            elif kind == "total":     shaded_cell(cell, GREEN)
            elif kind == "memo":      shaded_cell(cell, AMBER)
            elif kind == "mstn":      shaded_cell(cell, MSTN)
            elif kind == "hold_tint": shaded_cell(cell, ORANGE_TINT)
            elif kind == "hold":      shaded_cell(cell, ORANGE)

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
                elif kind == "hold_tint":
                    r.bold = True
                    r.font.color.rgb = RGBColor(0x1F, 0x3A, 0x68)  # navy, readable on light orange
                elif kind == "hold":
                    r.bold = True
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)  # white on solid orange
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

# ── Earn-Out Targets Table ───────────────────────────────────────────────────
H2("Earn-Out Targets: FY27–FY31")

def add_targets_table():
    from docx.enum.text import WD_ALIGN_PARAGRAPH as WDA
    DARK   = "1F3A68"
    MSTN   = "EFF6FF"
    TOTAL  = "D1FAE5"
    GREY_C = RGBColor(0x6B, 0x72, 0x80)
    col_w  = [1.85, 1.55, 0.85, 0.85, 0.85, 0.85]  # total ~6.8"
    rows = [
        # (Earn-out, Target, Low, Base, High, Pays, kind)
        ("Earn-out", "Target SSLC must hit", "Low", "Base", "High", "Pays", "header"),
        ("Tank earn-out\n5% of IM tank revenue/yr,\ncap $300K/yr, FY27–FY31",
         "Revenue SSLC achieves\neach year FY27–FY31",
         "$3.0M/yr\n→ $150K/yr\n→ $750K total",
         "$5.0M/yr\n→ $250K/yr\n→ $1.25M total",
         "$6.0M+/yr\n→ $300K/yr (cap)\n→ $1.5M total",
         "Annual,\nFY27–FY31", "data"),
        ("M1: SSLC FY2026-27 rev ≥ $5.1M → $200K",
         "SSLC FY27 annual revenue ≥ $5.1M",
         "✓", "✓", "✓", "FY28 Q1\n(if verified)", "mstn"),
        ("M2: Nebula/OTV production contract → $200K",
         "Nebula/OTV production\ncontract signed",
         "—", "✓", "✓", "At contract\nexecution", "mstn"),
        ("M3: SSLC annual rev ≥ $10M → $250K",
         "SSLC annual revenue ≥ $10M",
         "—", "✓", "✓", "First yr hit\n(est. FY29)", "mstn"),
        ("M4: SSLC annual rev ≥ $20M → $250K",
         "SSLC annual revenue ≥ $20M",
         "—", "—", "✓", "First yr hit\n(est. FY31)", "mstn"),
        ("M5: BLK3 tank qualification → $200K",
         "Exos BLK3 tank\nqualification complete",
         "—", "—", "✓", "At BLK3 cert\n(est. FY27–28)", "mstn"),
        ("Exos stock earn-out at RTO listing\n(additional to ~0.59% EAI up-front)",
         "Issued at RTO listing",
         "$0\n(0.0%)", "$625K\n(0.25%)", "$1,500K\n(0.50%)", "Post-RTO\n~FY29", "data"),
        ("TOTAL EARN-OUTS (5-yr, ③ minus ②)",
         "",
         "$950K", "$2,525K", "$4,100K", "", "total"),
    ]
    t = doc.add_table(rows=len(rows), cols=6)
    try:    t.style = "Table Grid"
    except: pass
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), col_w):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for i, (c0, c1, c2, c3, c4, c5, kind) in enumerate(rows):
        vals = [c0, c1, c2, c3, c4, c5]
        for j, val in enumerate(vals):
            cell = t.cell(i, j)
            cell.width = Inches(col_w[j])
            cell.text = ""
            p = cell.paragraphs[0]
            if j >= 2:
                p.alignment = WDA.CENTER
            if   kind == "header": shaded_cell(cell, DARK)
            elif kind == "mstn":   shaded_cell(cell, MSTN)
            elif kind == "total":  shaded_cell(cell, TOTAL)
            for line in val.split("\n"):
                r = p.add_run(line)
                r.font.size = Pt(8)
                if kind == "header":
                    r.bold = True
                    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                elif kind == "total":
                    r.bold = True
                elif kind == "mstn" and j >= 2:
                    r.font.color.rgb = GREY_C if val == "—" else RGBColor(0x00, 0x00, 0x00)
                if line != val.split("\n")[-1]:
                    p.add_run().add_break()
    P(sa=2)

add_targets_table()
note("Earn-out totals verified: Low $750K+$200K+$0=$950K ✓  Base $1,250K+$650K+$625K=$2,525K ✓  High $1,500K+$1,100K+$1,500K=$4,100K ✓  (each = ③ minus ② = ③ minus $5,360K)")

note("EAI units: $1.0M fixed (~0.59% FD) issued as part of Rule 504 offering at close; part of RTO public float; "
     "freely tradeable at listing (no lockup). Earn-out stock (0.0–0.5% additional) at RTO listing. "
     "Full model: EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx → 'EAI Lockup & Liquidity' and 'Total Compensation' sheets.")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 4 — TERMS (SHORT BOX)
# ────────────────────────────────────────────────────────────────────────────
H1("3.  Key Terms", sb=3)

terms_rows = [
    ["Term",                         "Detail"],
    ["Agreement basis",              "May 2025 Asset Acquisition Agreement, §3 exclusivity trigger"],
    ["Total commitment",             "$5,360,000 base at close ($2.51M cash + $60K costs + $790K Exos stake credit + $500K WC + $1.0M EAI equity at 409A, Rule 504)"],
    ["Exclusivity period",           "90 days from SSLC confirmation; extension not unreasonably withheld (§3)"],
    ["Holdback (§7)",                "5% escrow, released at 12-month anniversary"],
    ["SSLC debts assumed",           "Paid at face at close (est. ~$500K; verify QuickBooks)"],
    ["SSLC employees",               "Exos offers employment to SSLC employees on terms no less favorable than current (incl. comp & benefits), subject to Exos hiring policies + confirmatory diligence; key-employee option pool set in the Definitive Agreement"],
    ["Status",                       "DRAFT — NEGOTIATING TERMS — not a final or binding offer"],
]
add_table(terms_rows, [1.9, 4.1])

SEC_504_URL  = ("https://www.sec.gov/resources-small-businesses/exempt-offerings/"
                "exemption-limited-offerings-not-exceeding-10-million-rule-504-regulation-d")
RULE144_URL  = "https://www.ecfr.gov/current/title-17/chapter-II/part-230/section-230.144"
RULE10B5_URL = "https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.10b-5"

note("Rule 504: $1.0M toward $10M rolling 12-month cap; U.S.-only (Japan round is Reg S — keep distinct). "
     "EAI timeline: committed at board acceptance → issued at financing close (Q1 FY27 targeted) → "
     "freely tradeable at RTO listing (targeted ~6 mo post-close; not assured). "
     "Full detail: model → 'EAI Lockup & Liquidity' sheet.")

# ────────────────────────────────────────────────────────────────────────────
# FOOTER
# ────────────────────────────────────────────────────────────────────────────
note("Full model: EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx  ·  "
     "With-vs-Without: sheet 'With vs Without Exos Capital'  ·  "
     "Eqvista fairness opinion: engaged 8/14/2026; agreement still unsigned (held ~1 month). Projections are forward-looking (SEC Rule 10b-5 applies); RTO stock projection (mgmt assumption, not a guarantee): see model 'Total Compensation' / 'Returns and Dilution'  ·  "
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
