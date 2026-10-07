#!/usr/bin/env python3
"""Add 'With vs Without Exos Capital' sheet to EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx.
Compares SSLC standalone (status-quo) vs SSLC with Exos offer (v12 trajectory → $54.7M Y5).
Jon instructions 2026-10-07: show funding gap, doubling stat, CAGR comparison, cumulative gap.
"""
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os

XLSX = "/Users/exomac/.openclaw/workspace/drafts/EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx"

# ── palette ─────────────────────────────────────────────────────────────────
DARK_BLUE   = "1F3864"
MID_BLUE    = "2E75B6"
LIGHT_BLUE  = "D6E4F0"
GREEN_DARK  = "375623"
GREEN       = "E2EFDA"
GREEN_MID   = "70AD47"
RED_DARK    = "9B1C1C"
RED_LIGHT   = "FFE0E0"
ORANGE      = "FCE4D6"
YELLOW      = "FFF2CC"
YELLOW_DARK = "BF8F00"
GREY        = "F2F2F2"
WHITE       = "FFFFFF"
BLACK       = "000000"

def fill(hex_):   return PatternFill("solid", fgColor=hex_)
def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)
def thick_bottom():
    t = Side(style="medium", color="888888")
    return Border(bottom=t)


def cell(ws, row, col, val=None, bold=False, italic=False, size=10,
         fg=None, bg=None, fmt=None, align_h="left", wrap=False, merge_to=None, color=None):
    c = ws.cell(row=row, column=col, value=val)
    c.font = Font(bold=bold, italic=italic, size=size,
                  color=(color or (WHITE if bg in (DARK_BLUE, MID_BLUE, GREEN_DARK, RED_DARK) else BLACK)))
    if bg:    c.fill = fill(bg)
    if fmt:   c.number_format = fmt
    c.alignment = Alignment(horizontal=align_h, vertical="center", wrap_text=wrap)
    c.border = thin_border()
    if merge_to:
        ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=merge_to)
    return c


wb = openpyxl.load_workbook(XLSX)

# Remove existing sheet if re-running
if "With vs Without Exos Capital" in wb.sheetnames:
    del wb["With vs Without Exos Capital"]

ws = wb.create_sheet("With vs Without Exos Capital")

# ── column widths ────────────────────────────────────────────────────────────
ws.column_dimensions["A"].width = 42
for col in ["B","C","D","E","F"]:
    ws.column_dimensions[col].width = 14
ws.column_dimensions["G"].width = 2   # spacer
for col in ["H","I","J","K","L"]:
    ws.column_dimensions[col].width = 14

# ── title ────────────────────────────────────────────────────────────────────
ws.merge_cells("A1:L1")
ws["A1"].value = "SSLC: WITH vs WITHOUT EXOS CAPITAL — 5-Year Growth Comparison"
ws["A1"].font = Font(bold=True, size=14, color=WHITE)
ws["A1"].fill = fill(DARK_BLUE)
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 28

ws.merge_cells("A2:L2")
ws["A2"].value = ("Prepared 2026-10-07  |  DRAFT — MANAGEMENT ASSUMPTIONS  |  INTERNAL — Exo/CEO only  |  "
                  "Without-Exos trajectory derived from FY27 Q1 actual $713K run-rate; With-Exos uses v12 SSLC revenue drivers. "
                  "All figures management assumptions unless labeled 'Actual'.")
ws["A2"].font = Font(italic=True, size=9, color="555555")
ws["A2"].alignment = Alignment(horizontal="center", wrap_text=True)
ws.row_dimensions[2].height = 28

# ── KEY FACT callout ─────────────────────────────────────────────────────────
ws.merge_cells("A4:L6")
ws["A4"].value = (
    "KEY FACT:  Reaching $5M in FY27 requires averaging $1.43M/quarter for Q2–Q4  "
    "($5,000K − $713K Q1 actual ÷ 3 quarters = $1,429K/qtr)  —  "
    "exactly 2.0× the most recent quarter's $713K  —  starting immediately.  "
    "Without Exos capital to fund working capital and IM ramp, that doubling is not achievable on SSLC's $198K cash position."
)
ws["A4"].font = Font(bold=True, size=11, color=BLACK)
ws["A4"].fill = fill(YELLOW)
ws["A4"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
ws["A4"].border = Border(
    left=Side(style="medium", color=YELLOW_DARK),
    right=Side(style="medium", color=YELLOW_DARK),
    top=Side(style="medium", color=YELLOW_DARK),
    bottom=Side(style="medium", color=YELLOW_DARK)
)
ws.row_dimensions[4].height = 22
ws.row_dimensions[5].height = 22
ws.row_dimensions[6].height = 22

# ────────────────────────────────────────────────────────────────────────────
# SECTION A: WITHOUT EXOS CAPITAL (status-quo standalone)
# ────────────────────────────────────────────────────────────────────────────
R = 8

ws.merge_cells(f"A{R}:F{R}")
ws[f"A{R}"].value = "WITHOUT EXOS CAPITAL — Status-Quo Standalone Trajectory"
ws[f"A{R}"].font = Font(bold=True, size=11, color=WHITE)
ws[f"A{R}"].fill = fill(RED_DARK)
ws[f"A{R}"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[R].height = 22

# sub-header: constraints
R += 1
ws.merge_cells(f"A{R}:F{R}")
ws[f"A{R}"].value = ("Constraints: Cash $198K | $984K prepaid work needs $300–700K to complete | FY26 op loss −$416K | "
                     "He-tank rework unresolved | No capex | No IM ramp capital → growth capped by self-funded working capital")
ws[f"A{R}"].font = Font(italic=True, size=9, color=RED_DARK)
ws[f"A{R}"].alignment = Alignment(horizontal="left", wrap_text=True)
ws.row_dimensions[R].height = 22
R += 1

# column headers
hdrs = ["", "FY27", "FY28", "FY29", "FY30", "FY31"]
for ci, h in enumerate(hdrs, 1):
    c_obj = ws.cell(row=R, column=ci, value=h)
    c_obj.font = Font(bold=True, size=10, color=WHITE)
    c_obj.fill = fill(MID_BLUE)
    c_obj.alignment = Alignment(horizontal="center")
    c_obj.border = thin_border()
ws.row_dimensions[R].height = 18
R += 1

# Without-Exos data
# Basis: Q1 FY27 actual $713K → annual run-rate $2.85M
# No capital → growth capped; model 10% CAGR organic from FY28 (survivorship)
wo_rev = [2850_000, 3_136_000, 3_449_000, 3_794_000, 4_174_000]
wo_gr  = [None, 0.10, 0.10, 0.10, 0.10]
wo_ebitda = [-416_000, -200_000, 50_000, 200_000, 350_000]  # derived: FY26 actual + slow improvement
wo_notes = [
    "Run-rate from Q1 actual $713K × 4  (Actual anchor)",
    "+10% CAGR — organic only; WC-constrained; stall risk if prepaid-work gap not funded",
    "+10%",
    "+10%",
    "+10%",
]

rows_wo = [
    ("SSLC Revenue (standalone)",        wo_rev,    "$#,##0", False, wo_notes),
    ("  YoY Revenue Growth",             wo_gr,     "0.0%",   False, None),
    ("SSLC Est. EBITDA (standalone)",     wo_ebitda, "$#,##0", False, None),
    ("Cumulative Revenue (FY27–year)",   None,      "$#,##0", True,  None),
]

cum_wo = [sum(wo_rev[:i+1]) for i in range(5)]

for lbl, vals, fmt, is_cum, notes in rows_wo:
    if is_cum:
        vals = cum_wo
    for ci in range(1, 7):
        if ci == 1:
            c_obj = ws.cell(row=R, column=ci, value=lbl)
            c_obj.font = Font(bold=False, size=10, color=BLACK)
            c_obj.alignment = Alignment(horizontal="left")
            c_obj.border = thin_border()
        else:
            yr_idx = ci - 2
            if vals is not None and yr_idx < len(vals):
                v = vals[yr_idx]
            else:
                v = None
            c_obj = ws.cell(row=R, column=ci, value=v)
            c_obj.number_format = fmt
            c_obj.font = Font(size=10, color=(RED_DARK if v is not None and isinstance(v, (int,float)) and v < 0 else BLACK))
            c_obj.alignment = Alignment(horizontal="right")
            c_obj.border = thin_border()
            c_obj.fill = fill(RED_LIGHT) if lbl.startswith("SSLC Revenue") else fill(GREY if ci % 2 == 0 else WHITE)
    R += 1

# stall-risk note
ws.merge_cells(f"A{R}:F{R}")
ws[f"A{R}"].value = ("⚠  Stall Risk: SSLC needs $300–700K to deliver $984K prepaid/deposited work already billed. "
                     "On $198K cash, a working-capital crunch could interrupt deliveries in Q2–Q3 FY27, "
                     "reducing FY27 below the $2.85M run-rate. The 10% CAGR assumes the crunch is survived.")
ws[f"A{R}"].font = Font(italic=True, size=9, color=RED_DARK)
ws[f"A{R}"].alignment = Alignment(horizontal="left", wrap_text=True)
ws[f"A{R}"].fill = fill(RED_LIGHT)
ws.row_dimensions[R].height = 30
R += 2

# ────────────────────────────────────────────────────────────────────────────
# SECTION B: WITH EXOS CAPITAL (v12 trajectory)
# ────────────────────────────────────────────────────────────────────────────
ws.merge_cells(f"A{R}:F{R}")
ws[f"A{R}"].value = "WITH EXOS CAPITAL — v12 SSLC Revenue Trajectory (→ $54.7M by FY31)"
ws[f"A{R}"].font = Font(bold=True, size=11, color=WHITE)
ws[f"A{R}"].fill = fill(GREEN_DARK)
ws[f"A{R}"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[R].height = 22
R += 1

ws.merge_cells(f"A{R}:F{R}")
ws[f"A{R}"].value = ("Exos offer provides: Cash at close $2.51M | Debts paid at face | "
                     "$984K prepaid-work funded (cost $500K) | WC bridge | Exos channel + IM ramp capex | "
                     "v12 tank-unit/ASP ramp model. Figures: v12 Annual P&L, recalculated 2026-10-07.")
ws[f"A{R}"].font = Font(italic=True, size=9, color=GREEN_DARK)
ws[f"A{R}"].alignment = Alignment(horizontal="left", wrap_text=True)
ws.row_dimensions[R].height = 22
R += 1

hdrs2 = ["", "FY27", "FY28", "FY29", "FY30", "FY31"]
for ci, h in enumerate(hdrs2, 1):
    c_obj = ws.cell(row=R, column=ci, value=h)
    c_obj.font = Font(bold=True, size=10, color=WHITE)
    c_obj.fill = fill(MID_BLUE)
    c_obj.alignment = Alignment(horizontal="center")
    c_obj.border = thin_border()
ws.row_dimensions[R].height = 18
R += 1

# v12 SSLC revenue (from Assumptions sheet)
wi_rev    = [4_120_000, 8_680_000, 19_220_000, 33_880_000, 54_690_000]
wi_gr     = [None, 1.108, 1.214, 0.763, 0.614]   # YoY
wi_ebitda_sslc = [
    round(4_120_000 * 0.65 - 1_400_000),   # ~1.28M
    round(8_680_000 * 0.65 - 1_512_000),   # ~4.13M
    round(19_220_000 * 0.70 - 1_633_000),  # ~11.82M
    round(33_880_000 * 0.70 - 1_763_000),  # ~21.95M
    round(54_690_000 * 0.70 - 1_904_000),  # ~36.38M
]
cum_wi = [sum(wi_rev[:i+1]) for i in range(5)]

rows_wi = [
    ("SSLC Revenue (with Exos, v12)",     wi_rev,       "$#,##0", False),
    ("  YoY Revenue Growth",              wi_gr,        "0.0%",   False),
    ("SSLC Est. EBITDA (v12 drivers)",    wi_ebitda_sslc,"$#,##0",False),
    ("Cumulative Revenue (FY27–year)",    None,         "$#,##0", True ),
]

for lbl, vals, fmt, is_cum in rows_wi:
    if is_cum:
        vals = cum_wi
    for ci in range(1, 7):
        if ci == 1:
            c_obj = ws.cell(row=R, column=ci, value=lbl)
            c_obj.font = Font(bold=False, size=10, color=BLACK)
            c_obj.alignment = Alignment(horizontal="left")
            c_obj.border = thin_border()
        else:
            yr_idx = ci - 2
            v = vals[yr_idx] if (vals is not None and yr_idx < len(vals)) else None
            c_obj = ws.cell(row=R, column=ci, value=v)
            c_obj.number_format = fmt
            c_obj.font = Font(size=10, bold=(lbl.startswith("SSLC Revenue")), color=BLACK)
            c_obj.alignment = Alignment(horizontal="right")
            c_obj.border = thin_border()
            c_obj.fill = fill(GREEN) if lbl.startswith("SSLC Revenue") else fill(GREY if ci % 2 == 0 else WHITE)
    R += 1

R += 1

# ────────────────────────────────────────────────────────────────────────────
# SECTION C: GROWTH-RATE COMPARISON
# ────────────────────────────────────────────────────────────────────────────
ws.merge_cells(f"A{R}:F{R}")
ws[f"A{R}"].value = "GROWTH-RATE (CAGR) AND CUMULATIVE-GAP COMPARISON — FY27 to FY31"
ws[f"A{R}"].font = Font(bold=True, size=11, color=WHITE)
ws[f"A{R}"].fill = fill(DARK_BLUE)
ws[f"A{R}"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[R].height = 22
R += 1

# CAGR calculations (hard-coded; labeled management assumptions)
# Without: 2.85M → 4.174M over 4 yrs = (4.174/2.85)^0.25 - 1 = 1.0100 - 1 ≈ 10.0%
# With:    4.12M → 54.69M over 4 yrs = (54.69/4.12)^0.25 - 1 ≈ 90.8%
cagr_wo = (4_174_000 / 2_850_000) ** 0.25 - 1
cagr_wi = (54_690_000 / 4_120_000) ** 0.25 - 1
cum5_wo = sum(wo_rev)
cum5_wi = sum(wi_rev)
gap_y5  = wi_rev[-1] - wo_rev[-1]
gap_cum = cum5_wi - cum5_wo

cmp_rows = [
    ("FY27 SSLC Revenue",                 wo_rev[0],  wi_rev[0],  "$#,##0",  "$#,##0"),
    ("FY31 SSLC Revenue",                 wo_rev[-1], wi_rev[-1], "$#,##0",  "$#,##0"),
    ("FY27–FY31 CAGR (SSLC Revenue)",     cagr_wo,    cagr_wi,    "0.0%",    "0.0%"),
    ("Cumulative 5-yr SSLC Revenue",      cum5_wo,    cum5_wi,    "$#,##0",  "$#,##0"),
    ("Y5 Annual Revenue Gap (With − W/O)",None,        gap_y5,     None,      "$#,##0"),
    ("Cumulative 5-yr Gap (With − W/O)",  None,        gap_cum,    None,      "$#,##0"),
]

hdr_r = [("Metric", MID_BLUE), ("Without Exos Capital", RED_DARK), ("With Exos Capital", GREEN_DARK),
         ("Without Exos Capital", RED_DARK), ("With Exos Capital", GREEN_DARK)]
for ci, (h, bg) in enumerate(hdr_r, 1):
    c_obj = ws.cell(row=R, column=ci, value=h)
    c_obj.font = Font(bold=True, size=10, color=WHITE)
    c_obj.fill = fill(bg)
    c_obj.alignment = Alignment(horizontal="center")
    c_obj.border = thin_border()
ws.row_dimensions[R].height = 18
R += 1

for (lbl, v_wo, v_wi, fmt_wo, fmt_wi) in cmp_rows:
    ws.cell(row=R, column=1, value=lbl).font = Font(bold=True, size=10)
    ws.cell(row=R, column=1).border = thin_border()
    c2 = ws.cell(row=R, column=2, value=v_wo)
    c2.number_format = fmt_wo or "General"
    c2.fill = fill(RED_LIGHT)
    c2.border = thin_border()
    c2.alignment = Alignment(horizontal="right")
    c3 = ws.cell(row=R, column=3, value=v_wi)
    c3.number_format = fmt_wi or "General"
    c3.fill = fill(GREEN)
    c3.border = thin_border()
    c3.alignment = Alignment(horizontal="right")
    c3.font = Font(bold=True, size=10)
    R += 1

# ────────────────────────────────────────────────────────────────────────────
# SECTION D: NARRATIVE SUMMARY (right side of sheet for print flow)
# ────────────────────────────────────────────────────────────────────────────
# Re-anchor to row 8, columns H–L (the right-side companion)
SR = 8

ws.merge_cells(f"H{SR}:L{SR}")
ws[f"H{SR}"].value = "NARRATIVE — The Capital Gap Story"
ws[f"H{SR}"].font = Font(bold=True, size=11, color=WHITE)
ws[f"H{SR}"].fill = fill(DARK_BLUE)
ws[f"H{SR}"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[SR].height = 22
SR += 1

narrative_blocks = [
    ("Without Exos: Status-Quo Constraints", RED_DARK, [
        "Cash on hand (10/2/26):  $198K",
        "Prepaid work to deliver:  $984K face",
        "Cost to complete that work:  $300K–$700K",
        "FY26 operating loss:  −$416K",
        "He-tank rework unresolved — no resolution path without new owner",
        "No capex capacity → headcount/equipment frozen",
        "Growth capped by self-funded working capital",
        "FY27 achievable at run-rate:  ~$2.85M",
        "FY31 best-case (10% CAGR, no stall):  ~$4.2M",
        f"5-yr CAGR (status quo):  ~{cagr_wo*100:.1f}%",
    ]),
    ("With Exos: What Capital Unlocks", GREEN_DARK, [
        "Cash at close:  $2.51M",
        "SSLC debts paid at face (est. ~$500K TBV)",
        "Prepaid-work delivery funded (cost $500K)",
        "WC bridge removes Q2–Q3 stall risk",
        "Exos procurement channel:  immediate BLK3 tank POs",
        "Intuitive Machines ramp:  14–16 tanks firm FY27",
        "Capex for production scale-up enabled",
        "FY27 target (IM firm + ramp):  $4.1M–$5.5M",
        "FY31 (v12 trajectory):  $54.7M",
        f"5-yr CAGR (with Exos, v12):  ~{cagr_wi*100:.1f}%",
    ]),
    ("The Doubling Requirement", YELLOW_DARK, [
        "FY27 $5M target − Q1 $713K actual = $4,287K remaining",
        "Over 3 quarters (Q2–Q4) = $1,429K/qtr required",
        "vs. Q1 $713K actual = 2.0× immediate ramp",
        "Only funded if Exos capital bridges the working-capital gap",
        "Without capital → Q2–Q4 stays ≈ $713K/qtr = $2.85M FY27",
    ]),
]

for (title, title_bg, lines) in narrative_blocks:
    ws.merge_cells(f"H{SR}:L{SR}")
    ws[f"H{SR}"].value = title
    ws[f"H{SR}"].font = Font(bold=True, size=10, color=WHITE)
    ws[f"H{SR}"].fill = fill(title_bg)
    ws[f"H{SR}"].alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[SR].height = 20
    SR += 1
    for line in lines:
        ws.merge_cells(f"H{SR}:L{SR}")
        ws[f"H{SR}"].value = f"  {line}"
        ws[f"H{SR}"].font = Font(size=9.5)
        ws[f"H{SR}"].alignment = Alignment(horizontal="left", vertical="center")
        ws[f"H{SR}"].border = thin_border()
        ws.row_dimensions[SR].height = 16
        SR += 1
    SR += 1

# management-assumptions footer
last_row = max(R, SR) + 1
ws.merge_cells(f"A{last_row}:L{last_row}")
ws[f"A{last_row}"].value = ("Management Assumptions — all projections forward of FY27 Q1 actual ($713K) are management estimates, "
                             "not independently audited. Without-Exos CAGR assumes no working-capital stall; stall scenarios produce lower figures. "
                             "With-Exos CAGR uses v12 SSLC tank-unit/ASP/COGS drivers, not independently audited. DRAFT, 2026-10-07.")
ws[f"A{last_row}"].font = Font(italic=True, size=9, color="666666")
ws[f"A{last_row}"].alignment = Alignment(horizontal="left", wrap_text=True)
ws.row_dimensions[last_row].height = 28

# ── freeze pane, save ────────────────────────────────────────────────────────
ws.freeze_panes = "B11"
wb.save(XLSX)

# Quick LibreOffice recalc check (open + re-save as xlsx to catch formula errors)
import subprocess, tempfile, shutil
tmp = XLSX.replace(".xlsx", "_recalc.xlsx")
res = subprocess.run(
    ["soffice", "--headless", "--convert-to", "xlsx", "--outdir",
     os.path.dirname(XLSX), XLSX],
    capture_output=True, text=True
)
print("LibreOffice recalc:", res.returncode, res.stderr[:200] if res.stderr else "OK")
if res.returncode == 0:
    recalc_out = XLSX.replace(".xlsx", "_recalc.xlsx")  # soffice names it this way
    # soffice converts foo.xlsx → foo.xlsx in outdir (same name)
    # actually it produces EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx (same name, same dir)
    pass

print(f"DONE: {XLSX}")
print(f"Without CAGR:  {cagr_wo*100:.1f}%")
print(f"With CAGR:     {cagr_wi*100:.1f}%")
print(f"FY27 without:  ${wo_rev[0]:,.0f}")
print(f"FY27 with(v12):${wi_rev[0]:,.0f}")
print(f"FY31 without:  ${wo_rev[-1]:,.0f}")
print(f"FY31 with(v12):${wi_rev[-1]:,.0f}")
print(f"Y5 gap:        ${gap_y5:,.0f}")
print(f"Cumulative gap:${gap_cum:,.0f}")
print(f"Doubling req:  ${(5_000_000 - 713_000) / 3:,.0f}/qtr vs $713K = {(5_000_000 - 713_000)/3/713_000:.2f}×")
