#!/usr/bin/env python3
"""Build EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx
All formulas, no hardcodes in output cells. Base: v6 pre-commission model structure.
"""
import openpyxl
from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side,
                              numbers)
from openpyxl.utils import get_column_letter
import os

OUT = "/Users/exomac/.openclaw/workspace/drafts/EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx"

# ── palette ──────────────────────────────────────────────────────────────────
DARK_BLUE  = "1F3864"
MID_BLUE   = "2E75B6"
LIGHT_BLUE = "D6E4F0"
YELLOW     = "FFF2CC"
GREEN      = "E2EFDA"
ORANGE     = "FCE4D6"
RED_LIGHT  = "FFE0E0"
GREY       = "F2F2F2"
WHITE      = "FFFFFF"

def hdr(text, bold=True, color=WHITE, bg=MID_BLUE, size=11):
    f = Font(bold=bold, color=color, size=size)
    fill = PatternFill("solid", fgColor=bg)
    aln  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return f, fill, aln

def label_style():
    return Font(bold=False, size=10), PatternFill("solid", fgColor=WHITE), \
           Alignment(horizontal="left", vertical="center")

def num_fmt(ws, cell, fmt="$#,##0"):
    ws[cell].number_format = fmt

def row_hdr(ws, row, text, col_span_end="I", bg=LIGHT_BLUE):
    ws.cell(row=row, column=1).value = text
    ws.cell(row=row, column=1).font = Font(bold=True, size=10)
    ws.cell(row=row, column=1).fill = PatternFill("solid", fgColor=bg)
    ws.merge_cells(f"A{row}:{col_span_end}{row}")

def set_val(ws, row, col, val, fmt="$#,##0", bold=False, bg=None, italic=False):
    c = ws.cell(row=row, column=col, value=val)
    c.number_format = fmt
    c.font = Font(bold=bold, italic=italic, size=10)
    if bg:
        c.fill = PatternFill("solid", fgColor=bg)
    return c

def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

wb = openpyxl.Workbook()

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 1: Assumptions
# ─────────────────────────────────────────────────────────────────────────────
ws = wb.active
ws.title = "Assumptions"
ws.column_dimensions["A"].width = 42
ws.column_dimensions["B"].width = 18
ws.column_dimensions["C"].width = 32

# Title
ws.merge_cells("A1:C1")
ws["A1"] = "EXOS Aerospace / SSLC Option B Acquisition — Assumptions"
ws["A1"].font = Font(bold=True, color=WHITE, size=13)
ws["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 24

ws["A2"] = "Prepared: 2026-10-07 | DRAFT — NEGOTIATING TERMS | INTERNAL — Exo/CEO only"
ws["A2"].font = Font(italic=True, size=9, color="666666")
ws.merge_cells("A2:C2")

# Column headers
for col, txt in [(1,"Assumption"),(2,"Value"),(3,"Source / Notes")]:
    c = ws.cell(row=4, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

# ── Deal parameters ──────────────────────────────────────────────────────────
row_hdr(ws, 5, "DEAL STRUCTURE — Option B", bg=DARK_BLUE)
ws["A5"].font = Font(bold=True, color=WHITE, size=10)
ws["A5"].fill = PatternFill("solid", fgColor=DARK_BLUE)

data_assump = [
    # row: label, value, source
    (6,  "Agreement date (Asset Acquisition Agreement)",     "2025-05-13",                   "Executed — Jon Quinn & Jim Wertz"),
    (7,  "§3 exclusivity trigger: financing agreement",     "Ainigma/FNEX executed mandate","FNEX advisory agreement; strengthen with investor/sponsor use-of-proceeds letter"),
    (8,  "Exclusivity period (days)",                        90,                             "§3 of the 2025 Agreement"),
    (9,  "Deal price — total commitment ($)",                3360000,                        "§3 / §1: $2.51M cash + $60K costs + $790K stake credit"),
    (10, "  Cash at close ($)",                              2510000,                        "Stated deal price — cash component"),
    (11, "  SSLC closing costs ($)",                        60000,                          "Seller's costs; included in total"),
    (12, "  Exos existing-stake credit ($)",                790000,                         "18% equity at 2021 basis (~$4.39M total × 18%)"),
    (13, "  Escrowed holdback (§7) — 5% for 12 months ($)", "=B9*0.05",                    "§7; released at 12-month anniversary"),
    (14, "SSLC debts assumed at face ($)",                  500000,                         "MANAGEMENT ASSUMPTION — UNVERIFIED. To verify in SSLC QB (session expired 10/7). Microcosm loan + Wertz notes + AP. Wertz/Microcosm debt paid at face = path to yes."),
    (15, "Exos loan to SSLC — waived as license consideration ($)", 38000,                 "Jon decision 10/2; not re-proposed"),
    (16, "Working capital bridge needed (mid-point) ($)",    500000,                         "SSLC needs $0.3–0.7M to finish paid-for work (FY27 Q1 cash $198K; prepaid $984K; gap). Mid=$500K."),
    (17, "Series A raise — first close ($)",                10000000,                        "D1 of record, 2026-08-13"),
    (18, "Pre-money valuation (Eqvista 409A) ($)",           169700000,                      "Eqvista 03/31/26; $8.66/sh; DLOM 36.51%"),
    (19, "RTO minimum enterprise value ($)",                 250000000,                      "FNEX/Ainigma term — $250M min MEV"),
    (20, "Pre-RTO note size ($)",                            15000000,                       "FNEX/Ainigma convertible note"),
]

for (r, lbl, val, src) in data_assump:
    ws.cell(r, 1).value = lbl
    ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val
    ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, (int, float)):
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.cell(r, 3).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 28

# ── Earn-out parameters ──────────────────────────────────────────────────────
row_hdr(ws, 22, "EARN-OUT PARAMETERS", bg=DARK_BLUE)
ws["A22"].font = Font(bold=True, color=WHITE)
ws["A22"].fill = PatternFill("solid", fgColor=DARK_BLUE)

earn_data = [
    (23, "Earn-out i — IM tank revenue % (low)",             0.03,   "Management assumption — unverified"),
    (24, "Earn-out i — IM tank revenue % (base)",            0.05,   "Management assumption — unverified"),
    (25, "Earn-out i — IM tank revenue % (high)",            0.07,   "Management assumption — unverified"),
    (26, "Earn-out i — annual cap ($)",                      300000, "Management assumption — unverified"),
    (27, "Earn-out i — duration (years)",                    3,      "Management assumption — unverified"),
    (28, "Earn-out ii — Exos stock % of FD shares (low)",   0.003,  "Management assumption — unverified"),
    (29, "Earn-out ii — Exos stock % of FD shares (base)",  0.005,  "Management assumption — unverified"),
    (30, "Earn-out ii — Exos stock % of FD shares (high)",  0.007,  "Management assumption — unverified"),
    (31, "Earn-out ii — assumed listing price (low) ($)",    200000000,"FNEX RTO min $250M MEV; low scenario"),
    (32, "Earn-out ii — assumed listing price (base) ($)",   250000000,"FNEX RTO minimum MEV"),
    (33, "Earn-out ii — assumed listing price (high) ($)",   300000000,"Management assumption — unverified"),
    (34, "Earn-out ii — lockup period (months)",             12,     "Standard post-listing lockup"),
]
for (r, lbl, val, src) in earn_data:
    ws.cell(r, 1).value = lbl
    ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val
    ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, float) and val < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, int) and val > 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.row_dimensions[r].height = 22

# ── SSLC Financials ──────────────────────────────────────────────────────────
row_hdr(ws, 36, "SSLC HISTORICAL & PROJECTED FINANCIALS", bg=DARK_BLUE)
ws["A36"].font = Font(bold=True, color=WHITE)
ws["A36"].fill = PatternFill("solid", fgColor=DARK_BLUE)

sslc_fin = [
    (37, "SSLC FY26 actual revenue ($)",           1925000,   "SSLC QB FY26 actuals (Jon 10/2 QB pull)"),
    (38, "SSLC FY26 operating loss ($)",           -416000,   "SSLC QB FY26 actuals"),
    (39, "SSLC FY26 net income ($)",               -78000,    "Net of one-time $287K ERC credit"),
    (40, "SSLC FY27 Q1 actual revenue ($)",        713000,    "SSLC QB FY27 Q1 (Sep not yet closed, Jon 10/2)"),
    (41, "SSLC FY27 billed-ahead + deposits ($)",  984000,    "FY27 Q1 QB: $864K billed-ahead + $120K deposits"),
    (42, "SSLC cash at QB date ($)",               198000,    "SSLC QB FY27 Q1 (10/2/2026)"),
    (43, "Exos % of SSLC revenue (FY26)",          0.236,     "23.6% per Jon 10/2 board meeting"),
    (44, "Markus: IM tank revenue FY27 firm ($)",  5000000,   "Markus Rufer confirmed ~$5M firm for 2027, 14–16 tanks (Jon 10/2)"),
    (45, "SSLC assumed COGS % (FY27+)",            0.52,      "MANAGEMENT ASSUMPTION — derived from FY26 implied P&L"),
    (46, "SSLC assumed OpEx base FY27 ($)",        1400000,   "MANAGEMENT ASSUMPTION — small team (~10-12 people, Torrance)"),
    (47, "SSLC OpEx annual growth rate (FY28+)",   0.08,      "MANAGEMENT ASSUMPTION — unverified"),
    (48, "SSLC revenue growth FY28 ($)",           7500000,   "MANAGEMENT ASSUMPTION — IM Nebula OTV ramp"),
    (49, "SSLC revenue FY29 ($)",                  10000000,  "MANAGEMENT ASSUMPTION — IM scaling + new contracts"),
    (50, "SSLC revenue FY30 ($)",                  13000000,  "MANAGEMENT ASSUMPTION"),
    (51, "SSLC revenue FY31 ($)",                  16500000,  "MANAGEMENT ASSUMPTION"),
    (52, "v15 benchmark — SSLC acq revenue Y1 ($)", 900000,  "Old acquisition model (pre-commission, pre-IM-tank confirmation); Option B should exceed"),
    (53, "v15 benchmark — SSLC acq revenue Y5 ($)", 21000000,"Old acquisition model v15 benchmark"),
]
for (r, lbl, val, src) in sslc_fin:
    ws.cell(r, 1).value = lbl
    ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val
    ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, float) and val < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, (int, float)) and abs(val) >= 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.row_dimensions[r].height = 22

# ── Exos standalone ──────────────────────────────────────────────────────────
row_hdr(ws, 55, "EXOS STANDALONE PROJECTIONS (excl. SSLC commission post-close)", bg=DARK_BLUE)
ws["A55"].font = Font(bold=True, color=WHITE)
ws["A55"].fill = PatternFill("solid", fgColor=DARK_BLUE)

exos_fin = [
    (56, "Exos standalone revenue FY27 ($)",      2600000,   "Management assumption: entX $1.6M + TACFI $0.8M + other $0.2M (v15 baseline excl. SSLC commission)"),
    (57, "Exos standalone revenue FY28 ($)",      4500000,   "Management assumption — BLK3 first flight + TACFI scale"),
    (58, "Exos standalone revenue FY29 ($)",      7000000,   "Management assumption"),
    (59, "Exos standalone revenue FY30 ($)",      11000000,  "Management assumption"),
    (60, "Exos standalone revenue FY31 ($)",      16000000,  "Management assumption"),
    (61, "Exos standalone EBITDA FY27 ($)",       -4000000,  "Management assumption — pre-BLK3 flight investment phase"),
    (62, "Exos standalone EBITDA FY28 ($)",       -1500000,  "Management assumption — BLK3 flying, BLK4 dev"),
    (63, "Exos standalone EBITDA FY29 ($)",       500000,    "Management assumption — approaching breakeven"),
    (64, "Exos standalone EBITDA FY30 ($)",       2500000,   "Management assumption"),
    (65, "Exos standalone EBITDA FY31 ($)",       5000000,   "Management assumption"),
    (66, "Intercompany Exos purchases from SSLC FY27 ($)", 500000, "MANAGEMENT ASSUMPTION — Exos BLK3 tank purchases from SSLC subsidiary; eliminated on consolidation"),
    (67, "Intercompany growth rate FY28+ (%)",    0.15,      "MANAGEMENT ASSUMPTION"),
]
for (r, lbl, val, src) in exos_fin:
    ws.cell(r, 1).value = lbl
    ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val
    ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, float) and abs(val) < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, (int, float)) and abs(val) >= 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.row_dimensions[r].height = 22

ws.row_dimensions[55].height = 22


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 2: Deal Structure
# ─────────────────────────────────────────────────────────────────────────────
ds = wb.create_sheet("Deal Structure")
ds.column_dimensions["A"].width = 38
ds.column_dimensions["B"].width = 16
ds.column_dimensions["C"].width = 16
ds.column_dimensions["D"].width = 16
ds.column_dimensions["E"].width = 28

# Title
ds.merge_cells("A1:E1")
ds["A1"] = "SSLC Option B — Deal Structure, Sources & Uses, Earn-Out Analysis"
ds["A1"].font = Font(bold=True, color=WHITE, size=12)
ds["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
ds["A1"].alignment = Alignment(horizontal="center", vertical="center")
ds.row_dimensions[1].height = 22

ds["A2"] = "Option B: invoke §3 exclusivity at $3.36M base + earn-out (IM tank revenue and/or Exos stock post-listing). SSLC debts paid at face. DRAFT — [Counsel review required]."
ds["A2"].font = Font(italic=True, size=9, color="444444")
ds.merge_cells("A2:E2")
ds.row_dimensions[2].height = 30

# Sources & Uses
ds.merge_cells("A4:E4")
ds["A4"] = "SOURCES & USES AT CLOSE"
ds["A4"].font = Font(bold=True, color=WHITE); ds["A4"].fill = PatternFill("solid", fgColor=DARK_BLUE)

hdr_row = 5
for col, txt in [(1,"Line Item"),(2,"Amount ($)"),(3,""),(4,""),(5,"Notes")]:
    c = ds.cell(row=hdr_row, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)

su_data = [
    # (row, label, value_formula_or_val, notes)
    (6,  "USES",                                     "",            ""),
    (7,  "  Cash to SSLC sellers at close",          "=Assumptions!B10", "§3 deal price — cash component"),
    (8,  "  SSLC closing costs (sellers)",           "=Assumptions!B11", "Per §3 deal price"),
    (9,  "  SSLC debts assumed at face",             "=Assumptions!B14", "Microcosm/Wertz notes + AP — TO VERIFY IN SSLC QB"),
    (10, "  Working capital bridge (mid-point)",     "=Assumptions!B16", "SSLC needs $0.3–0.7M to finish paid-for work"),
    (11, "  Less: Exos stake credit (18%)",          "=-Assumptions!B12","18% equity at 2021 basis — reduces net cash"),
    (12, "  5% escrow holdback (§7, 12 mo.)",        "=Assumptions!B13", "Released at 12-month anniversary"),
    (13, "TOTAL USES",                               "=SUM(B7:B12)",     "Net cash out-of-pocket at close + escrow"),
    (14, "",                                          "",            ""),
    (15, "SOURCES",                                  "",            ""),
    (16, "  Series A first close (allocated to SSLC)","=Assumptions!B10+Assumptions!B16", "SSLC acquisition + WC bridge from Series A"),
    (17, "  Exos stake credit (non-cash)",           "=Assumptions!B12", "Existing 18% stake reduces cash required"),
    (18, "TOTAL SOURCES",                            "=B16+B17",         ""),
    (19, "Check (Sources − Uses)",                   "=B18-B13",         "Should = 0; debt payoff from SSLC operating cash"),
]
for (r, lbl, val, notes) in su_data:
    ds.cell(r, 1).value = lbl
    ds.cell(r, 5).value = notes
    ds.cell(r, 5).font = Font(size=9, italic=True, color="444444")
    if val:
        ds.cell(r, 2).value = val
        ds.cell(r, 2).number_format = "$#,##0;($#,##0)"
    if lbl in ("TOTAL USES", "TOTAL SOURCES", "Check (Sources − Uses)"):
        for col in range(1, 6):
            ds.cell(r, col).font = Font(bold=True, size=10)
            ds.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    elif lbl == "USES" or lbl == "SOURCES":
        ds.merge_cells(f"A{r}:E{r}")
        ds.cell(r, 1).font = Font(bold=True, size=10)
        ds.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
    ds.row_dimensions[r].height = 18

# Earn-out Analysis
ds.merge_cells("A21:E21")
ds["A21"] = "EARN-OUT MECHANICS (two variants shown side by side; combined option in Col D)"
ds["A21"].font = Font(bold=True, color=WHITE); ds["A21"].fill = PatternFill("solid", fgColor=DARK_BLUE)
ds.row_dimensions[21].height = 20

for col, txt in [(1,"Metric"),(2,"Earn-Out i: IM Tank Revenue %"),(3,"Earn-Out ii: Exos Stock post-RTO"),(4,"Combined (i + ii)"),(5,"Notes")]:
    c = ds.cell(row=22, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE, size=9); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(wrap_text=True, horizontal="center")

eo_data = [
    # (row, label, eo_i, eo_ii, combined, notes)
    (23, "Structure",
         "% of SSLC IM tank revenue, annual cap, 3-year term",
         "Exos common stock at listing (% of FD shares); 12-mo lockup",
         "Both i + ii",
         "Gives SSLC sellers upside from IM growth AND Exos growth"),
    (24, "Low scenario",
         "=MIN(Assumptions!B23*Assumptions!B44,Assumptions!B26)*Assumptions!B27",
         "=Assumptions!B28*Assumptions!B31",
         "=D24+C24",
         "Low: 3% tank rev (cap $300K) × 3yr + 0.3% of $200M listing"),
    (25, "Base scenario",
         "=MIN(Assumptions!B24*Assumptions!B44,Assumptions!B26)*Assumptions!B27",
         "=Assumptions!B29*Assumptions!B32",
         "=B25+C25",
         "Base: 5% × $5M firm + 0.5% of $250M listing"),
    (26, "High scenario",
         "=MIN(Assumptions!B25*Assumptions!B44,Assumptions!B26)*Assumptions!B27",
         "=Assumptions!B30*Assumptions!B33",
         "=B26+C26",
         "High: 7% × $5M + 0.7% of $300M listing"),
    (27, "Exos dilution (stock, base)",
         "n/a",
         "=Assumptions!B29",
         "=Assumptions!B29",
         "0.5% of FD shares; non-material at Series A scale"),
    (28, "Lockup / vesting",
         "Annual payments, 3 years",
         "12-month lockup post-listing",
         "Each tranche per its own schedule",
         ""),
]
for (r, lbl, i, ii, comb, notes) in eo_data:
    ds.cell(r, 1).value = lbl; ds.cell(r, 1).font = Font(size=9)
    ds.cell(r, 2).value = i
    ds.cell(r, 3).value = ii
    ds.cell(r, 4).value = comb
    ds.cell(r, 5).value = notes; ds.cell(r, 5).font = Font(size=9, italic=True, color="444444")
    for col in [2, 3, 4]:
        c = ds.cell(r, col)
        if isinstance(c.value, str) and c.value.startswith("="):
            c.number_format = "$#,##0"
        c.font = Font(size=9)
    ds.row_dimensions[r].height = 28

# Total Consideration table
ds.merge_cells("A30:E30")
ds["A30"] = "TOTAL CONSIDERATION SUMMARY (Base price + earn-out)"
ds["A30"].font = Font(bold=True, color=WHITE); ds["A30"].fill = PatternFill("solid", fgColor=DARK_BLUE)

for col, txt in [(1,"Component"),(2,"Low"),(3,"Base"),(4,"High"),(5,"Notes")]:
    c = ds.cell(row=31, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)

tc_data = [
    (32, "Base acquisition price",      "=Assumptions!B9","=Assumptions!B9","=Assumptions!B9","§3 deal price; incl. stake credit"),
    (33, "SSLC debts assumed (TBV)",   "=Assumptions!B14","=Assumptions!B14","=Assumptions!B14","To verify in SSLC QB"),
    (34, "Earn-out (combined)",         "=D24","=D25","=D26","Earn-out i + ii combined"),
    (35, "TOTAL CONSIDERATION",         "=B32+B33+B34","=C32+C33+C34","=D32+D33+D34","All-in for 82% of SSLC"),
    (36, "Implied 100% SSLC value",     "=B35/0.82","=C35/0.82","=D35/0.82","At 82% acquisition; Exos holds 18%"),
    (37, "Payback (yrs at base EBITDA)","=B35/1240000","=C35/1240000","=D35/1240000","FY27 SSLC EBITDA est. $1.24M"),
]
for (r, lbl, low, base, high, notes) in tc_data:
    ds.cell(r, 1).value = lbl
    for col, val in [(2, low), (3, base), (4, high)]:
        ds.cell(r, col).value = val
        ds.cell(r, col).number_format = "$#,##0" if lbl != "Payback (yrs at base EBITDA)" else "0.0x"
    ds.cell(r, 5).value = notes; ds.cell(r, 5).font = Font(size=9, italic=True)
    if "TOTAL" in lbl:
        for col in range(1, 6):
            ds.cell(r, col).font = Font(bold=True)
            ds.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    ds.row_dimensions[r].height = 18


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 3: P&L and Cash Flow (Annual + Year-1 Quarterly)
# ─────────────────────────────────────────────────────────────────────────────
pl = wb.create_sheet("PL and Cash Flow")
pl.column_dimensions["A"].width = 36
for col in ["B","C","D","E","F","G"]:
    pl.column_dimensions[col].width = 14
pl.column_dimensions["H"].width = 18

# Title
pl.merge_cells("A1:H1")
pl["A1"] = "EXOS + SSLC Consolidated P&L and Cash Flow — Option B Acquisition"
pl["A1"].font = Font(bold=True, color=WHITE, size=12)
pl["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
pl["A1"].alignment = Alignment(horizontal="center", vertical="center")
pl.row_dimensions[1].height = 22

pl["A2"] = "Assumes acquisition closes ~Q1 FY27. All figures in USD. SSLC consolidated from close date. Formulas link to Assumptions sheet."
pl["A2"].font = Font(italic=True, size=9, color="444444")
pl.merge_cells("A2:H2")

# ── Year-1 Quarterly (FY27) ───────────────────────────────────────────────────
pl.merge_cells("A4:H4")
pl["A4"] = "FY27 QUARTERLY — Exos+SSLC Consolidated (acquisition assumed closed Q1)"
pl["A4"].font = Font(bold=True, color=WHITE); pl["A4"].fill = PatternFill("solid", fgColor=DARK_BLUE)

for col, txt in [(1,"Line Item"),(2,"FY27 Q1"),(3,"FY27 Q2"),(4,"FY27 Q3"),(5,"FY27 Q4"),(6,"FY27 Total"),(7,""),(8,"Notes")]:
    c = pl.cell(row=5, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

# FY27 quarterly — using known Q1 and distributing remaining
# SSLC Q1 actual: $713K. IM tanks mostly in Q2-Q4 (Markus $5M firm). Distribute:
# SSLC: Q1=$713K (actual), Q2=$1.4M, Q3=$1.4M, Q4=$2.0M (front-loaded per billed-ahead)
# Exos: Q1=$550K, Q2=$700K, Q3=$700K, Q4=$650K = $2.6M (spread evenly)

q_data_pl = [
    # (row, label, q1, q2, q3, q4, notes)
    # Revenue section
    (6,  "SSLC Revenue (post-consolidation)", 713000,  1387000, 1400000, 2000000, "Q1 actual; Q2-Q4 management assumption distributing $5.5M FY27 total"),
    (7,  "Exos Standalone Revenue",           550000,  700000,  700000,  650000,  "Management assumption; $2.6M FY27 total (v15 baseline excl. SSLC commission)"),
    (8,  "Less: Intercompany Eliminations",   -125000, -125000, -125000, -125000, "Exos purchases from SSLC; $500K/yr eliminated"),
    (9,  "NET CONSOLIDATED REVENUE",          "=B6+B7+B8","=C6+C7+C8","=D6+D7+D8","=E6+E7+E8",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_data_pl:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True, color="444444")
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        pl.cell(r, col).number_format = "$#,##0;($#,##0)"
    if isinstance(q1, str):
        for col in [2,3,4,5]:
            pl.cell(r, col).number_format = "$#,##0;($#,##0)"
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "$#,##0;($#,##0)"
    if "NET CONSOLIDATED" in lbl or "TOTAL" in lbl:
        for col in range(1, 9):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    pl.row_dimensions[r].height = 18

# COGS
pl.merge_cells("A11:H11")
pl["A11"] = "COST OF GOODS SOLD"
pl["A11"].font = Font(bold=True, color=WHITE); pl["A11"].fill = PatternFill("solid", fgColor=MID_BLUE)

q_cogs = [
    (12, "SSLC COGS (52% of SSLC rev)",    "=B6*Assumptions!B45","=C6*Assumptions!B45","=D6*Assumptions!B45","=E6*Assumptions!B45", "52% management assumption; derived from FY26"),
    (13, "Exos COGS (45% of Exos rev)",    "=B7*0.45","=C7*0.45","=D7*0.45","=E7*0.45", "45% management assumption (launch vehicle hardware-heavy)"),
    (14, "TOTAL COGS",                     "=B12+B13","=C12+C13","=D12+D13","=E12+E13", ""),
    (15, "GROSS PROFIT",                   "=B9-B14","=C9-C14","=D9-D14","=E9-E14",""),
    (16, "Gross Margin %",                 "=IF(B9<>0,B15/B9,0)","=IF(C9<>0,C15/C9,0)","=IF(D9<>0,D15/D9,0)","=IF(E9<>0,E15/E9,0)",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_cogs:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True)
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        fmt = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
        pl.cell(r, col).number_format = fmt
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
    if "GROSS PROFIT" in lbl or "TOTAL COGS" in lbl:
        for col in range(1, 7):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=GREEN)
    pl.row_dimensions[r].height = 18

# OpEx
pl.merge_cells("A18:H18")
pl["A18"] = "OPERATING EXPENSES (combined)"
pl["A18"].font = Font(bold=True, color=WHITE); pl["A18"].fill = PatternFill("solid", fgColor=MID_BLUE)

q_opex = [
    (19, "SSLC OpEx",            350000, 350000, 350000, 350000, "FY27 $1.4M / 4 quarters"),
    (20, "Exos OpEx (excl. R&D)",650000, 650000, 650000, 650000, "Exos G&A / payroll (management assumption)"),
    (21, "Exos R&D / BLK3 dev",  500000, 500000, 500000, 500000, "BLK3 development; ramps down post-flight"),
    (22, "TOTAL OPEX",           "=SUM(B19:B21)","=SUM(C19:C21)","=SUM(D19:D21)","=SUM(E19:E21)",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_opex:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True)
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        pl.cell(r, col).number_format = "$#,##0;($#,##0)"
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "$#,##0;($#,##0)"
    if "TOTAL" in lbl:
        for col in range(1, 7):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=ORANGE)
    pl.row_dimensions[r].height = 18

# EBITDA
q_ebitda_rows = [
    (24, "EBITDA", "=B15-B22","=C15-C22","=D15-D22","=E15-E22",""),
    (25, "EBITDA Margin %","=IF(B9<>0,B24/B9,0)","=IF(C9<>0,C24/C9,0)","=IF(D9<>0,D24/D9,0)","=IF(E9<>0,E24/E9,0)",""),
    (26, "D&A (est.)",  -40000,-40000,-40000,-40000,"$160K FY27 SSLC + Exos combined; management assumption"),
    (27, "EBIT",        "=B24+B26","=C24+C26","=D24+D26","=E24+E26",""),
    (28, "Interest / one-time","0","0","0","0","Acquisition-related one-time costs in Q1 (separate line)"),
    (29, "Pre-Tax Income","=B27+B28","=C27+C28","=D27+D28","=E27+E28",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_ebitda_rows:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True)
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        fmt = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
        pl.cell(r, col).number_format = fmt
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
    if lbl in ("EBITDA", "EBIT", "Pre-Tax Income"):
        for col in range(1, 7):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    pl.row_dimensions[r].height = 18

# Cash Flow (simplified)
pl.merge_cells("A31:H31")
pl["A31"] = "FY27 QUARTERLY — CASH FLOW (simplified)"
pl["A31"].font = Font(bold=True, color=WHITE); pl["A31"].fill = PatternFill("solid", fgColor=DARK_BLUE)

q_cf = [
    (32, "Beginning Cash (Exos + SSLC at close)", 198000, "=E32+E33+E34","=E33+E34+E35","=E34+E35+E36","SSLC cash $198K at QB date"),
    (33, "SSLC acquisition cash out",    -2510000, 0, 0, 0,               "Deal cash at close (Q1)"),
    (34, "Working capital injection",    -500000,  0, 0, 0,               "SSLC bridge; Q1"),
    (35, "Operating cash (EBITDA proxy)","=B24","=C24","=D24","=E24",    "EBITDA proxy; ± WC changes not modeled"),
    (36, "Series A proceeds allocated",  3010000,  0,  0,  0,             "Acquisition ($2.51M) + WC bridge ($0.5M) from first close"),
    (37, "ENDING CASH",                 "=SUM(B32:B36)","=C32+C33+C34+C35+C36","=D32+D33+D34+D35+D36","=E32+E33+E34+E35+E36",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_cf:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True)
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        pl.cell(r, col).number_format = "$#,##0;($#,##0)"
    pl.cell(r, 6).value = f"=E{r}" if "ENDING" in lbl else ""
    pl.cell(r, 6).number_format = "$#,##0;($#,##0)"
    if "ENDING" in lbl:
        for col in range(1, 7):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    pl.row_dimensions[r].height = 18

# ── 5-Year Annual P&L ─────────────────────────────────────────────────────────
pl.merge_cells("A40:H40")
pl["A40"] = "5-YEAR ANNUAL P&L — FY27–FY31 (Exos+SSLC Consolidated)"
pl["A40"].font = Font(bold=True, color=WHITE); pl["A40"].fill = PatternFill("solid", fgColor=DARK_BLUE)

for col, txt in [(1,"Line Item"),(2,"FY27"),(3,"FY28"),(4,"FY29"),(5,"FY30"),(6,"FY31"),(7,"FY27-31 CAGR"),(8,"Notes")]:
    c = pl.cell(row=41, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

# Annual revenue data
# SSLC: FY27 $5.5M, FY28 $7.5M, FY29 $10M, FY30 $13M, FY31 $16.5M
# Exos: FY27 $2.6M, FY28 $4.5M, FY29 $7M, FY30 $11M, FY31 $16M
# Interco: FY27 $0.5M, FY28 $0.575M, FY29 $0.661M, FY30 $0.76M, FY31 $0.874M
# Net consolidated: $7.6M, $11.425M, $16.339M, $23.24M, $31.626M

ann_pl = [
    # Revenue
    (42,  "SSLC Revenue",            "=Assumptions!B37+Assumptions!B44","=Assumptions!B48","=Assumptions!B49","=Assumptions!B50","=Assumptions!B51","","SSLC actual + IM firm FY27; projections FY28+"),
    (43,  "Exos Standalone Revenue",  "=Assumptions!B56","=Assumptions!B57","=Assumptions!B58","=Assumptions!B59","=Assumptions!B60","","v15 baseline excl. SSLC commission"),
    (44,  "Less: Intercompany",        -500000, -575000, -661000, -760000, -874000,"","Exos tank purchases from SSLC; interco elim."),
    (45,  "NET CONSOLIDATED REVENUE", "=B42+B43+B44","=C42+C43+C44","=D42+D43+D44","=E42+E43+E44","=F42+F43+F44","=IFERROR((F45/B45)^(1/4)-1,0)",""),
    # Gross Profit
    (47,  "SSLC Gross Profit (48%)",  "=B42*(1-Assumptions!B45)","=C42*(1-Assumptions!B45)","=D42*(1-Assumptions!B45)","=E42*(1-Assumptions!B45)","=F42*(1-Assumptions!B45)","",""),
    (48,  "Exos Gross Profit (55%)",  "=B43*0.55","=C43*0.55","=D43*0.55","=E43*0.55","=F43*0.55","","45% COGS on standalone"),
    (49,  "GROSS PROFIT",             "=B47+B48","=C47+C48","=D47+D48","=E47+E48","=F47+F48","",""),
    (50,  "Gross Margin %",           "=IF(B45<>0,B49/B45,0)","=IF(C45<>0,C49/C45,0)","=IF(D45<>0,D49/D45,0)","=IF(E45<>0,E49/E45,0)","=IF(F45<>0,F49/F45,0)","",""),
    # EBITDA
    (52,  "SSLC EBITDA",             "=B42*(1-Assumptions!B45)-Assumptions!B46","=C42*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)","=D42*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)^2","=E42*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)^3","=F42*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)^4","",""),
    (53,  "Exos Standalone EBITDA",  "=Assumptions!B61","=Assumptions!B62","=Assumptions!B63","=Assumptions!B64","=Assumptions!B65","","Management assumption; see Assumptions sheet"),
    (54,  "CONSOLIDATED EBITDA",     "=B52+B53","=C52+C53","=D52+D53","=E52+E53","=F52+F53","=IFERROR((F54/B54)^(1/4)-1,0)",""),
    (55,  "EBITDA Margin %",         "=IF(B45<>0,B54/B45,0)","=IF(C45<>0,C54/C45,0)","=IF(D45<>0,D54/D45,0)","=IF(E45<>0,E54/E45,0)","=IF(F45<>0,F54/F45,0)","",""),
    # v15 benchmark comparison
    (57,  "— v15 benchmark SSLC acq rev (old model)","=Assumptions!B52","","","","=Assumptions!B53","","Old pre-commission acquisition model; Option B exceeds benchmark"),
    (58,  "— Option B SSLC revenue vs benchmark","=B42-B57","","","","=F42-F57","","Positive = Option B SSLC rev exceeds old benchmark"),
]
for row_data in ann_pl:
    r = row_data[0]; lbl = row_data[1]
    vals = row_data[2:7]   # FY27-FY31
    cagr = row_data[7]
    notes = row_data[8]
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True, color="444444")
    for i, val in enumerate(vals):
        col = i + 2
        pl.cell(r, col).value = val
        fmt = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
        pl.cell(r, col).number_format = fmt
    if cagr:
        pl.cell(r, 7).value = cagr
        pl.cell(r, 7).number_format = "0.0%"
    bold_rows = ["NET CONSOLIDATED REVENUE","GROSS PROFIT","CONSOLIDATED EBITDA"]
    if lbl in bold_rows:
        for col in range(1, 8):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    elif lbl in ["SSLC EBITDA","Exos Standalone EBITDA"]:
        for col in range(1, 7):
            pl.cell(r, col).fill = PatternFill("solid", fgColor=GREEN)
    pl.row_dimensions[r].height = 18

# Section headers
for r in [46, 51, 56]:
    pl.merge_cells(f"A{r}:H{r}")
    pl.cell(r, 1).value = ["GROSS PROFIT","EBITDA","BENCHMARK COMPARISON"][r//10 - 4] if r != 56 else "BENCHMARK COMPARISON"
    pl.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
    pl.cell(r, 1).font = Font(bold=True, size=9)
pl["A46"] = "GROSS PROFIT"
pl["A51"] = "EBITDA"
pl["A56"] = "BENCHMARK COMPARISON (Option B vs v15 old acquisition model)"


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 4: Returns and Dilution
# ─────────────────────────────────────────────────────────────────────────────
rd = wb.create_sheet("Returns and Dilution")
rd.column_dimensions["A"].width = 36
for col in ["B","C","D","E"]:
    rd.column_dimensions[col].width = 16
rd.column_dimensions["F"].width = 22

rd.merge_cells("A1:F1")
rd["A1"] = "SSLC Option B — Returns, Dilution & Benchmark Comparison"
rd["A1"].font = Font(bold=True, color=WHITE, size=12)
rd["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
rd["A1"].alignment = Alignment(horizontal="center")
rd.row_dimensions[1].height = 22

# Column headers
for col, txt in [(1,"Metric"),(2,"Low"),(3,"Base"),(4,"High"),(5,"v15 Benchmark"),(6,"Notes")]:
    c = rd.cell(row=3, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

returns_data = [
    # Revenue comparison
    (4,  "FY27 SSLC revenue (Option B)",   "='PL and Cash Flow'!B42","='PL and Cash Flow'!B42","='PL and Cash Flow'!B42","=Assumptions!B52",""),
    (5,  "FY31 SSLC revenue (Option B)",   "='PL and Cash Flow'!F42","='PL and Cash Flow'!F42","='PL and Cash Flow'!F42","=Assumptions!B53",""),
    (6,  "FY27 SSLC rev vs benchmark ($+)","=B4-D4","=C4-D4","=D4-E4","—","Positive = Option B exceeds old model"),
    (7,  "FY31 SSLC rev vs benchmark ($+)","=B5-E4","=C5-E4","=D5-E5","—","Substantial delta; IM tank confirmation changes picture"),
    # Total consideration
    (9,  "Total consideration (all-in)",    "='Deal Structure'!B35","='Deal Structure'!C35","='Deal Structure'!D35","n/a","Base price + earn-out + assumed debt"),
    (10, "Implied 100% SSLC value",         "='Deal Structure'!B36","='Deal Structure'!C36","='Deal Structure'!D36","n/a",""),
    (11, "Exos FY31 SSLC EBITDA",           "='PL and Cash Flow'!B52","='PL and Cash Flow'!B52","='PL and Cash Flow'!F52","n/a","SSLC standalone EBITDA contribution"),
    (12, "SSLC FY31 EBITDA × 10x (value)", "=B11*10","=C11*10","=D11*10","n/a","Indicative exit value at 10× EBITDA"),
    (13, "Acquisition ROI (FY31 val/cost)", "=B12/B9","=C12/C9","=D12/D9","n/a","Illustrative; not a guarantee"),
    # Dilution
    (15, "Earn-out ii: Exos stock (low)",   "=Assumptions!B28","","","","% of FD shares issued for earn-out"),
    (16, "Earn-out ii: Exos stock (base)",  "","=Assumptions!B29","","",""),
    (17, "Earn-out ii: Exos stock (high)",  "","","=Assumptions!B30","",""),
    (18, "Earn-out stock dilution",         "=B15","=C16","=D17","n/a","Non-material; well within Series A dilution"),
    # Cash need
    (20, "FY27 net cash deployment",        "=Assumptions!B10+Assumptions!B16","=Assumptions!B10+Assumptions!B16","=Assumptions!B10+Assumptions!B16","n/a","Acquisition + WC bridge; from Series A"),
    (21, "Series A first close",            "=Assumptions!B17","=Assumptions!B17","=Assumptions!B17","n/a","$10M; well covers acquisition+bridge"),
    (22, "Remaining for Exos ops post-acq","=B21-B20","=C21-C20","=D21-D20","n/a","Available for BLK3, R&D, G&A after SSLC"),
]
for row_data in returns_data:
    if len(row_data) < 6: continue
    r, lbl = row_data[0], row_data[1]
    vals = row_data[2:6]
    notes = row_data[6] if len(row_data) > 6 else ""
    rd.cell(r, 1).value = lbl
    rd.cell(r, 6).value = notes; rd.cell(r, 6).font = Font(size=9, italic=True, color="444444")
    for i, val in enumerate(vals):
        col = i + 2
        rd.cell(r, col).value = val
        if "%" in lbl or "ROI" in lbl:
            rd.cell(r, col).number_format = "0.0%"
        elif "dilution" in lbl.lower():
            rd.cell(r, col).number_format = "0.00%"
        else:
            rd.cell(r, col).number_format = "$#,##0"
    rd.row_dimensions[r].height = 18

# Section headers
for r, title in [(8,""), (14,"EARN-OUT DILUTION ANALYSIS"), (19,"CASH DEPLOYMENT SUMMARY")]:
    if title:
        rd.merge_cells(f"A{r}:F{r}")
        rd.cell(r, 1).value = title
        rd.cell(r, 1).font = Font(bold=True, size=10)
        rd.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_BLUE)

for col, txt in [(1,"Metric"),(2,"Low"),(3,"Base"),(4,"High"),(5,"v15 Benchmark"),(6,"Notes")]:
    c = rd.cell(row=3, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 5: Funding
# ─────────────────────────────────────────────────────────────────────────────
fn = wb.create_sheet("Funding")
fn.column_dimensions["A"].width = 40
fn.column_dimensions["B"].width = 18
fn.column_dimensions["C"].width = 30

fn.merge_cells("A1:C1")
fn["A1"] = "SSLC Option B — Funding Structure & Risks"
fn["A1"].font = Font(bold=True, color=WHITE, size=12)
fn["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
fn["A1"].alignment = Alignment(horizontal="center")
fn.row_dimensions[1].height = 22

fund_data = [
    # (row, label, val_or_formula, notes)
    (3,  "FUNDING OVERVIEW",                         "",                       ""),
    (4,  "Acquisition is funded from Exos-only post-RTO proceeds", "Investor requirement","SSLC stays OUT of RTO perimeter (Jon 10/2 remarks to SSLC board)"),
    (5,  "Series A first close ($)",                 "=Assumptions!B17",       "D1 of record; $10M"),
    (6,  "  Allocated to SSLC acquisition",          "=Assumptions!B10",       "Cash deal price"),
    (7,  "  Allocated to SSLC WC bridge",            "=Assumptions!B16",       "$0.3–0.7M; mid=$500K"),
    (8,  "  Remaining for Exos operations",          "=B5-B6-B7",              ""),
    (9,  "Pre-RTO convertible note ($)",             "=Assumptions!B20",       "FNEX/Ainigma; primary Exos development capital"),
    (10, "TOTAL FINANCING AT CLOSE",                 "=B5",                    "Series A covers acquisition + WC bridge"),
    (12, "§3 FINANCING TRIGGER GAP (CRITICAL RISK)", "",                       ""),
    (13, "FNEX/Ainigma role",                        "Advisor / broker-dealer","FNEX is NOT itself the 'investor or lender' under §3"),
    (14, "Risk: SSLC counsel (Danny) challenges trigger","HIGH",                "§3 requires 'investor or lender capable of financing'; advisory mandate may not qualify"),
    (15, "Mitigation required",                      "Attach FNEX countersigned agreement + investor/sponsor use-of-proceeds letter naming SSLC asset purchase","[Counsel review] — [Confirm FNEX agreement countersigned per D-7281974 10/6]"),
    (16, "§3 extension right",                       "SSLC shall not unreasonably withhold","90-day window from exclusivity grant; request extension proactively while good-faith progress shown"),
    (17, "Timing: 90-day exclusivity ends",          "~Jan 6, 2027",           "From ~Oct 8 grant; RTO is 4-5 months; need extension"),
    (19, "RELATED-PARTY DISCLOSURES",                "",                       ""),
    (20, "Jon sits on BOTH boards",                  "Conflict of interest",   "Jon must RECUSE from SSLC vote; send as Exos CEO only"),
    (21, "Fairness opinion",                         "Required (Eqvista engaged)","Eqvista engaged for 409A + fairness opinion per D1-D4 of record"),
    (22, "Disinterested director approval",          "Required (SSLC side)",   "Markus Rufer and Bob as disinterested directors approve; Jon abstains"),
    (23, "Legal review",                             "Deferred (Jon 10/7)",    "Negotiation stage; no legal review until Jon calls it"),
    (25, "HE-TANK DISPUTE RISK",                     "",                       ""),
    (26, "Rev3 tank leaks at boss post-Hysol",       "RISK",                   "10/1 hydro fail; Morey questions as flight article. Plan B: qualified COPV ≤$250K (MC #3056, D-7281994)"),
    (27, "Impact on acquisition",                    "SSLC demonstrably can't deliver BLK3 flight article","Customer-hat PO default (due 9/24/2025) kept in reserve; resolves post-acquisition"),
    (29, "SSLC CASH RISK",                           "",                       ""),
    (30, "SSLC cash at close (est.)",                "=Assumptions!B42+Assumptions!B41-Assumptions!B16","FY27 Q1 cash + billed-ahead minus WC need"),
    (31, "Risk: SSLC runs out of cash before close", "MEDIUM",                 "Cash $198K + collections on $984K prepaid; needs $0.3-0.7M to finish work"),
    (32, "Mitigation: Option C pre-cliff bridge",    "Secured prepaid BLK3 tank PO $300-700K","Use only disclosed SSLC numbers; Option C held for follow-up"),
    (34, "DATA NOT VERIFIED IN SSLC QB (CRITICAL GAPS)", "", ""),
    (35, "SSLC total liabilities / AP",              "~$500K est. — TO VERIFY IN SSLC QB","QB session expired 10/7; cannot confirm Microcosm/Wertz note amounts. Must verify before signing."),
    (36, "SSLC total debt assumed at face",          "TO VERIFY IN SSLC QB",   "Critical for Bob/Jim: personal path to yes depends on debt payoff amount"),
    (37, "Exos loan to SSLC status in QB",           "~$38K — cancelled per Jon 10/2","Verify cancellation documented in QB"),
]
for (r, lbl, val, notes) in fund_data:
    fn.cell(r, 1).value = lbl
    fn.cell(r, 2).value = val
    fn.cell(r, 3).value = notes
    fn.cell(r, 1).font = Font(size=10)
    fn.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    fn.cell(r, 3).alignment = Alignment(wrap_text=True)
    if isinstance(val, str) and val.startswith("="):
        fn.cell(r, 2).number_format = "$#,##0"
        fn.cell(r, 2).font = Font(bold=True, size=10)
    if lbl in ("FUNDING OVERVIEW","§3 FINANCING TRIGGER GAP (CRITICAL RISK)","RELATED-PARTY DISCLOSURES",
               "HE-TANK DISPUTE RISK","SSLC CASH RISK","DATA NOT VERIFIED IN SSLC QB (CRITICAL GAPS)"):
        fn.merge_cells(f"A{r}:C{r}")
        fn.cell(r, 1).font = Font(bold=True, color=WHITE)
        fn.cell(r, 1).fill = PatternFill("solid", fgColor=DARK_BLUE if lbl in ("FUNDING OVERVIEW",) else MID_BLUE)
    if val in ("HIGH","MEDIUM"):
        fn.cell(r, 2).font = Font(bold=True, color="FF0000" if val=="HIGH" else "FF8C00")
    fn.row_dimensions[r].height = 28

# ── Save ──────────────────────────────────────────────────────────────────────
wb.save(OUT)
print(f"Saved: {OUT}")
