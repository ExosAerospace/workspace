#!/usr/bin/env python3
"""Rebuild Exos_SSLC_OptionB_Offer_Summary_2026-10-07.docx  — 2-page max.
John rules 2026-10-07 15:22-15:28:
  - Section 1: offer value TABLE (Component | Low | Base | High | Trigger/Timing)
  - Framing line in John's voice after the table
  - HIGH total 5-yr value ≈ $10M; tank earn-out extended to 5yr; milestone earn-outs added
  - Doubling stat updated to $5.1M target
  - No SSLC year-by-year revenue tables or growth projections
  - Keep 'negotiating terms', no Counsel gates, keep Eqvista wording
  - Name: John Quinn (not Jon Quinn); lockup: same as Exos principals
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
        ("Subtotal: funding at close",                "$4,360K", "$4,360K", "$4,360K", "",                                                          "subtotal"),
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
        ("Exos stock earn-out at listing",            "$1,000K", "$1,875K", "$3,000K", "Post-RTO ~FY28; 0.5% / 0.75%\n/ 1.0% FD; principals' lockup", "data"),
        ("TOTAL OFFER VALUE (5-yr)",                  "$6,310K", "$8,135K", "$9,960K", "FY27–FY31",                                                 "total"),
        ("Memo: Exos stock if held to FY31\n(not additive to total above)",
                                                      "$5.7M",   "$8.5M",   "$11.4M",  "16× EV/EBITDA; ~30% dilution;\nmgmt assumption",            "memo"),
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

P("October 7, 2026  ·  Exos Aerospace Systems & Technologies, Inc.",
  size=9.5, italic=True, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, sa=5)

# ────────────────────────────────────────────────────────────────────────────
# SECTION 1 — WHAT SSLC HOLDERS RECEIVE
# ────────────────────────────────────────────────────────────────────────────
H1("1.  What SSLC Holders Receive")

body("The Exos offer delivers liquidity, debt relief, and equity upside — "
     "without requiring any additional capital call from current SSLC shareholders.")

P("The up-front price reflects what the numbers support today. "
  "The earn-outs are how that value grows: as goals are met — IM tank deliveries, "
  "revenue milestones and the Exos listing — SSLC holders share directly in the upside.",
  italic=True, size=9.5, color=BLUE, sa=4)

add_offer_table()

B("No additional capital calls  ",
  "Once closed, SSLC's standalone cash burn stops entirely.")
B("IM program continuity  ",
  "Exos-SSLC continues the Intuitive Machines contract with no delivery interruption.")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 2 — WHY GROWTH REQUIRES EXOS CAPITAL
# ────────────────────────────────────────────────────────────────────────────
H1("2.  Why the Growth Trajectory Requires Exos Capital")

body("The bottleneck is not the technology or the IM demand — it is working capital.  "
     "SSLC's most recent quarter (FY27 Q1) came in at $713K in revenue.  "
     "Hitting $5.1M for FY27 requires averaging $1.46M per quarter in Q2–Q4 — "
     "approximately 2.05× that pace — starting immediately.  "
     "That doubling is not achievable on SSLC's current $198K cash balance.")

P("Standalone constraints (SSLC's own numbers):",
  bold=True, size=10, sa=2, sb=3)

B("Cash position  ", "$198K at October 2, 2026 — roughly one month of operating burn.")
B("Working capital gap  ",
  "$300K–$700K needed to maintain delivery commitments and service new IM orders — "
  "before SSLC can ramp to the $5.1M/year target run rate.")
B("Operating history  ", "FY26 operating loss: −$416K. No self-funding path to production scale.")
B("He-tank rework  ",
  "Rev3 GHe tank 4,400 psi proof issue unresolved (MC #3056). "
  "Remediation cost ~$175K to COPV ($300K gap). Resolves cleanly as intercompany under Exos.")
B("No capex capacity  ",
  "Production-scale equipment and headcount additions are not fundable from SSLC's cash position. "
  "Growth is capped at current run-rate without outside capital.")

note("The With-vs-Without comparison, year-by-year CAGR figures, and cumulative revenue gap "
     "are in the model spreadsheet: EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx, "
     "sheet 'With vs Without Exos Capital'.")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 3 — TOTAL COMPENSATION CHART
# ────────────────────────────────────────────────────────────────────────────
H1("3.  Total Compensation — 5-Year View (FY27–FY31)", sb=4)

note("Stacked chart below: funding delivered at close + earn-out forward potential. "
     "Base scenario shown; earn-out range (low/high) is in the model.")

# Compensation summary table — updated for 5-yr earn-out structure
comp_rows = [
    ["Component",                        "Timing",          "Low / Base / High"],
    ["Cash at close",                    "Close ~Q1 FY27",  "$2,510K"],
    ["SSLC closing costs (Seller)",      "Close",           "$60K"],
    ["Exos stake credit (non-cash)",     "Close (credit)",  "$790K"],
    ["Debt relief (est., TBV)",          "Close",           "~$500K"],
    ["WC bridge",                        "Close",           "$500K / $500K / $500K"],
    ["Subtotal: funding at close",       "Close",           "$4,360K / $4,360K / $4,360K"],
    ["Tank earn-out (5 yr, 5%/yr)",      "FY27–FY31",       "$750K / $1,250K / $1,500K"],
    ["Milestone earn-outs (5 triggers)", "FY27–FY31",       "$200K / $650K / $1,100K"],
    ["Exos stock earn-out",              "Post-RTO ~FY28",  "$1,000K / $1,875K / $3,000K"],
    ["TOTAL OFFER VALUE (5-yr)",         "FY27–FY31",       "$6.3M / $8.1M / $10.0M"],
]
add_table(comp_rows, [2.3, 1.4, 1.8])

# embed chart image if it exists
chart_path = os.path.join(WS, "drafts", "SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png")
if os.path.exists(chart_path):
    doc.add_picture(chart_path, width=Inches(5.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    note("Chart: SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png  |  "
         "Full model: EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx")
else:
    note("Chart file not found at expected path — see model xlsx → 'Total Compensation' sheet.")

# ────────────────────────────────────────────────────────────────────────────
# SECTION 4 — TERMS (SHORT BOX)
# ────────────────────────────────────────────────────────────────────────────
H1("4.  Key Terms", sb=4)

terms_rows = [
    ["Term",                         "Detail"],
    ["Agreement basis",              "May 2025 Asset Acquisition Agreement, §3 exclusivity trigger "
                                     "(non-exclusive → exclusive upon Exos financing agreement)"],
    ["Total commitment",             "$3,360,000 ($2.51M cash + $60K costs + $790K Exos stake credit)"],
    ["Exclusivity period",           "90 days from SSLC confirmation; extension not unreasonably withheld "
                                     "while financing works in good faith (§3)"],
    ["Holdback (§7)",                "5% escrow, released at 12-month anniversary"],
    ["SSLC debts assumed",           "Paid at face at close (est. ~$500K; verify QuickBooks)"],
    ["Disinterested directors",      "John Quinn abstains from SSLC board vote; sends as Exos CEO "
                                     "(Cal. Corp. Code §310)"],
    ["Fairness opinion",             "Eqvista engaged 8/14/2026; agreement still unsigned "
                                     "(held ~1 month)"],
    ["Status",                       "DRAFT — NEGOTIATING TERMS — not a final or binding offer"],
]
add_table(terms_rows, [1.9, 4.1])

# ────────────────────────────────────────────────────────────────────────────
# FOOTER
# ────────────────────────────────────────────────────────────────────────────
note("Detail in model: drafts/EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx  ·  "
     "With-vs-Without comparison: sheet 'With vs Without Exos Capital'  ·  "
     "Exclusivity rescue options: SSLC_Exclusivity_Rescue_Options_and_Draft_Message_2026-10-07_DRAFT_v2.docx")

P("DRAFT — INTERNAL — NEGOTIATING TERMS — John Quinn, CEO, Exos Aerospace — 2026-10-07",
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
