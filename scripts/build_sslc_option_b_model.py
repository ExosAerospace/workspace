#!/usr/bin/env python3
"""Build EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx
Two cases: Actuals-Anchored and Old-Model (v12 drivers).
Fixes FY27 SSLC inconsistency ($5.5M quarterly vs $6.925M 5-yr).
Adds reconciliation table and v15 understatement note.
"""
import openpyxl
from openpyxl.styles import (PatternFill, Font, Alignment, Border, Side)
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
PURPLE     = "7030A0"
LIGHT_PURPLE = "EAD8F7"

def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def sec_hdr(ws, row, text, bg=DARK_BLUE, col_end="I"):
    ws.merge_cells(f"A{row}:{col_end}{row}")
    ws.cell(row, 1).value = text
    ws.cell(row, 1).font = Font(bold=True, color=WHITE, size=10)
    ws.cell(row, 1).fill = PatternFill("solid", fgColor=bg)
    ws.row_dimensions[row].height = 20

def set_val(ws, row, col, val, fmt="$#,##0", bold=False, bg=None, italic=False):
    c = ws.cell(row=row, column=col, value=val)
    c.number_format = fmt
    c.font = Font(bold=bold, italic=italic, size=10)
    if bg:
        c.fill = PatternFill("solid", fgColor=bg)
    return c

wb = openpyxl.Workbook()

# ─────────────────────────────────────────────────────────────────────────────
# SHEET 1: Assumptions
# ─────────────────────────────────────────────────────────────────────────────
ws = wb.active
ws.title = "Assumptions"
ws.column_dimensions["A"].width = 46
ws.column_dimensions["B"].width = 18
ws.column_dimensions["C"].width = 36

# Title
ws.merge_cells("A1:C1")
ws["A1"] = "EXOS Aerospace / SSLC Option B Acquisition — Assumptions"
ws["A1"].font = Font(bold=True, color=WHITE, size=13)
ws["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 24

ws["A2"] = "Prepared: 2026-10-07 | DRAFT — NEGOTIATING TERMS | INTERNAL — Exo/CEO only | Two cases: Actuals-Anchored and Old-Model (v12 drivers)"
ws["A2"].font = Font(italic=True, size=9, color="666666")
ws.merge_cells("A2:C2")

for col, txt in [(1,"Assumption"),(2,"Value"),(3,"Source / Notes")]:
    c = ws.cell(row=4, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

# ── Deal parameters ──────────────────────────────────────────────────────────
sec_hdr(ws, 5, "DEAL STRUCTURE — Option B", bg=DARK_BLUE, col_end="C")

data_assump = [
    (6,  "Agreement date (Asset Acquisition Agreement)",     "2025-05-13",                   "Executed — Jon Quinn & Jim Wertz"),
    (7,  "§3 exclusivity trigger: financing agreement",     "Ainigma/FNEX executed mandate","FNEX advisory agreement; strengthen with investor/sponsor use-of-proceeds letter"),
    (8,  "Exclusivity period (days)",                        90,                             "§3 of the 2025 Agreement"),
    (9,  "Deal price — total commitment ($)",                3360000,                        "§3 / §1: $2.51M cash + $60K costs + $790K stake credit"),
    (10, "  Cash at close ($)",                              2510000,                        "Stated deal price — cash component"),
    (11, "  SSLC closing costs ($)",                        60000,                          "Seller's costs; included in total"),
    (12, "  Exos existing-stake credit ($)",                790000,                         "18% equity at 2021 basis (~$4.39M total × 18%)"),
    (13, "  Escrowed holdback (§7) — 5% for 12 months ($)", "=B9*0.05",                    "§7; released at 12-month anniversary"),
    (14, "SSLC debts assumed at face ($)",                  500000,                         "MANAGEMENT ASSUMPTION — UNVERIFIED. QB session expired 10/7. Microcosm loan + Wertz notes + AP."),
    (15, "Exos loan to SSLC — waived as license consideration ($)", 38000,                 "Jon decision 10/2; not re-proposed"),
    (16, "Working capital bridge needed (mid-point) ($)",    500000,                         "SSLC needs $0.3–0.7M to finish paid-for work. Mid=$500K."),
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
sec_hdr(ws, 22, "EARN-OUT PARAMETERS", bg=DARK_BLUE, col_end="C")
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
    ws.cell(r, 1).value = lbl; ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val; ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, float) and val < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, int) and val > 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.row_dimensions[r].height = 22

# ── ACTUALS-ANCHORED CASE: SSLC Financials ───────────────────────────────────
sec_hdr(ws, 36, "ACTUALS-ANCHORED CASE — SSLC HISTORICAL & PROJECTED FINANCIALS", bg=MID_BLUE, col_end="C")
sslc_fin = [
    (37, "SSLC FY26 actual revenue ($)",           1925000,   "SSLC QB FY26 actuals (Jon 10/2 QB pull)"),
    (38, "SSLC FY26 operating loss ($)",           -416000,   "SSLC QB FY26 actuals"),
    (39, "SSLC FY26 net income ($)",               -78000,    "Net of one-time $287K ERC credit"),
    (40, "SSLC FY27 Q1 actual revenue ($)",        713000,    "SSLC QB FY27 Q1 (Sep not yet closed, Jon 10/2)"),
    (41, "SSLC FY27 billed-ahead + deposits ($)",  984000,    "FY27 Q1 QB: $864K billed-ahead + $120K deposits"),
    (42, "SSLC cash at QB date ($)",               198000,    "SSLC QB FY27 Q1 (10/2/2026)"),
    (43, "Exos % of SSLC revenue (FY26)",          0.236,     "23.6% per Jon 10/2 board meeting"),
    (44, "Markus: IM tank revenue FY27 firm ($)",  5000000,   "Markus Rufer confirmed ~$5M firm for 2027, 14–16 tanks (Jon 10/2)"),
    (45, "SSLC assumed COGS % (FY27+, actuals-anchored)",    0.52,  "Derived from FY26 implied P&L"),
    (46, "SSLC assumed OpEx base FY27 ($)",        1400000,   "Small team (~10-12 people, Torrance)"),
    (47, "SSLC OpEx annual growth rate (FY28+)",   0.08,      "Management assumption"),
    # FIX: separate FY27 projected annual from the broken FY26+IM formula
    (48, "SSLC FY27 projected annual revenue, actuals-anchored ($)", 5500000,
         "FIX 10/7: quarterly total = Q1 $713K + Q2-Q4 $4,787K = $5.5M. "
         "Prior annual formula used FY26 actual ($1.925M) + IM tanks ($5M) = $6.925M — inconsistent. "
         "Correct basis is Q1 actuals + Q2-Q4 distribution of $5M firm IM ramp."),
    (49, "SSLC revenue FY28 ($)",                  7500000,   "IM Nebula OTV ramp"),
    (50, "SSLC revenue FY29 ($)",                  10000000,  "IM scaling + new contracts"),
    (51, "SSLC revenue FY30 ($)",                  13000000,  "Management assumption"),
    (52, "SSLC revenue FY31 ($)",                  16500000,  "Management assumption"),
    (53, "v15 benchmark — SSLC acq revenue Y1 ($)", 900000,  "Old acquisition model (pre-commission, pre-IM-tank); Option B exceeds"),
    (54, "v15 benchmark — SSLC acq revenue Y5 ($)", 21000000,"Old acquisition model v15 benchmark"),
]
for (r, lbl, val, src) in sslc_fin:
    ws.cell(r, 1).value = lbl; ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val; ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, float) and val < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, (int, float)) and abs(val) >= 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.cell(r, 3).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 22

# ── ACTUALS-ANCHORED CASE: Exos standalone ───────────────────────────────────
sec_hdr(ws, 56, "ACTUALS-ANCHORED CASE — EXOS STANDALONE (excl. SSLC commission post-close)", bg=MID_BLUE, col_end="C")
exos_fin = [
    (57, "Exos standalone revenue FY27 ($)",      2600000,   "entX $1.6M + TACFI $0.8M + other $0.2M (v15 baseline excl. SSLC commission)"),
    (58, "Exos standalone revenue FY28 ($)",      4500000,   "BLK3 first flight + TACFI scale"),
    (59, "Exos standalone revenue FY29 ($)",      7000000,   "Management assumption"),
    (60, "Exos standalone revenue FY30 ($)",      11000000,  "Management assumption"),
    (61, "Exos standalone revenue FY31 ($)",      16000000,  "Management assumption"),
    (62, "Exos standalone EBITDA FY27 ($)",       -4000000,  "Pre-BLK3 flight investment phase"),
    (63, "Exos standalone EBITDA FY28 ($)",       -1500000,  "BLK3 flying, BLK4 dev"),
    (64, "Exos standalone EBITDA FY29 ($)",       500000,    "Approaching breakeven"),
    (65, "Exos standalone EBITDA FY30 ($)",       2500000,   "Management assumption"),
    (66, "Exos standalone EBITDA FY31 ($)",       5000000,   "Management assumption"),
    (67, "Intercompany Exos purchases from SSLC FY27 ($)", 500000, "Exos BLK3 tank purchases from SSLC; eliminated on consolidation"),
    (68, "Intercompany growth rate FY28+ (%)",    0.15,      "Management assumption"),
]
for (r, lbl, val, src) in exos_fin:
    ws.cell(r, 1).value = lbl; ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val; ws.cell(r, 2).font = Font(size=10, bold=True)
    if isinstance(val, float) and abs(val) < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, (int, float)) and abs(val) >= 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.row_dimensions[r].height = 22

# ── OLD-MODEL CASE (v12 DRIVERS) — input block ───────────────────────────────
sec_hdr(ws, 70, "OLD-MODEL CASE (v12 DRIVERS) — source: v12 Annual P&L, recalculated 10/7", bg=PURPLE, col_end="C")
ws.cell(70, 1).fill = PatternFill("solid", fgColor=PURPLE)

v12_note = (71, "NOTE: v12 Month 1 = July 2026; Y1=FY27, Y2=FY28, …Y5=FY31. "
                "Scorpius tank drivers: units 1.5→9/month ramp; ASP $183K Y1 +50% Y2 +25%/yr Y3-Y5 → ~$536K Y5; "
                "COGS 35% Y1-Y2, 30% Y3-Y5. "
                "Exos standalone derived = total − Scorpius tanks.", None, None)
ws.cell(71, 1).value = v12_note[1]
ws.cell(71, 1).font = Font(size=9, italic=True, color="444444")
ws.merge_cells("A71:C71")
ws.row_dimensions[71].height = 40
ws.cell(71, 1).alignment = Alignment(wrap_text=True)

v12_data = [
    # (row, label, value, source)
    (72, "— v12 Scorpius tank ASP Y1 ($)",          183000,     "Controls!B31 — confirmed in model"),
    (73, "— v12 Scorpius tank ASP Y5 ($, approx)",  536000,     "$183K × 1.50 × 1.25 × 1.25 × 1.25 ≈ $536K"),
    (74, "— v12 Scorpius COGS Y1-Y2 (%)",           0.35,       "Controls!B54 = 35%"),
    (75, "— v12 Scorpius COGS Y3-Y5 (%)",           0.30,       "Controls!E54 = 30%"),
    (76, "— v12 SSLC/Scorpius revenue Y1 FY27 ($)", 4120000,    "v12 Annual P&L 'Revenue from Scorpius Space Tank Sales' Y1, recalculated 10/7"),
    (77, "— v12 SSLC/Scorpius revenue Y2 FY28 ($)", 8680000,    "v12 Annual P&L Y2"),
    (78, "— v12 SSLC/Scorpius revenue Y3 FY29 ($)", 19220000,   "v12 Annual P&L Y3"),
    (79, "— v12 SSLC/Scorpius revenue Y4 FY30 ($)", 33880000,   "v12 Annual P&L Y4"),
    (80, "— v12 SSLC/Scorpius revenue Y5 FY31 ($)", 54690000,   "v12 Annual P&L Y5"),
    (81, "— v12 Total consolidated revenue Y1 ($)", 8880000,    "v12 Annual P&L 'Total Revenue' Y1"),
    (82, "— v12 Total consolidated revenue Y2 ($)", 21350000,   "v12 Annual P&L Y2"),
    (83, "— v12 Total consolidated revenue Y3 ($)", 48590000,   "v12 Annual P&L Y3"),
    (84, "— v12 Total consolidated revenue Y4 ($)", 95920000,   "v12 Annual P&L Y4"),
    (85, "— v12 Total consolidated revenue Y5 ($)", 179190000,  "v12 Annual P&L Y5"),
    (86, "— v12 Exos standalone revenue Y1 ($)",    "=B81-B76", "Derived: v12 total − Scorpius"),
    (87, "— v12 Exos standalone revenue Y2 ($)",    "=B82-B77", "Derived"),
    (88, "— v12 Exos standalone revenue Y3 ($)",    "=B83-B78", "Derived"),
    (89, "— v12 Exos standalone revenue Y4 ($)",    "=B84-B79", "Derived"),
    (90, "— v12 Exos standalone revenue Y5 ($)",    "=B85-B80", "Derived"),
    (91, "— v12 Total EBITDA Y1 ($)",               1120000,    "v12 Annual P&L 'EBITDA' Y1, recalculated 10/7"),
    (92, "— v12 Total EBITDA Y2 ($)",               4120000,    "v12 Annual P&L Y2"),
    (93, "— v12 Total EBITDA Y3 ($)",               17240000,   "v12 Annual P&L Y3"),
    (94, "— v12 Total EBITDA Y4 ($)",               42160000,   "v12 Annual P&L Y4"),
    (95, "— v12 Total EBITDA Y5 ($)",               101610000,  "v12 Annual P&L Y5"),
]
for (r, lbl, val, src) in v12_data:
    ws.cell(r, 1).value = lbl
    ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
    ws.cell(r, 2).value = val
    ws.cell(r, 2).font = Font(size=10, bold=True)
    ws.cell(r, 2).fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
    if isinstance(val, float) and abs(val) < 1:
        ws.cell(r, 2).number_format = '0.0%'
    elif isinstance(val, (int, float)) and abs(val) >= 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    elif isinstance(val, str) and val.startswith("="):
        ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src
    ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.cell(r, 3).fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
    ws.row_dimensions[r].height = 22

# v15 note
ws.cell(97, 1).value = (
    "⚠  v15 UNDERSTATEMENT NOTE: The v15 'Scorpius acquisition benchmark' shows "
    "$0.9M→$21M over 5 years. v12's own Scorpius line is $4.1M→$54.7M — 13× larger at Y5. "
    "The actuals-anchored case ($5.5M→$16.5M SSLC line) also substantially exceeds v15. "
    "Do NOT edit v15; this note records the discrepancy for the board summary."
)
ws.merge_cells("A97:C97")
ws.cell(97, 1).font = Font(size=9, bold=True, color="C00000")
ws.cell(97, 1).fill = PatternFill("solid", fgColor=RED_LIGHT)
ws.cell(97, 1).alignment = Alignment(wrap_text=True)
ws.row_dimensions[97].height = 52

# ── PREPAID-WORK DELIVERY OBLIGATION (Jon 10/7) ──────────────────────────────
sec_hdr(ws, 99, "PREPAID-WORK DELIVERY OBLIGATION (Jon 10/7)", bg=DARK_BLUE, col_end="C")
prepaid_data = [
    (100, "SSLC prepaid-work face value — billed-ahead + deposits ($)", 984000,
          "per 10/2 SSLC QB pull; verify. $864K billed-ahead + $120K deposits."),
    (101, "  of which: billed-ahead ($)", 864000,  "per 10/2 SSLC QB pull; verify"),
    (102, "  of which: deposits ($)",     120000,  "per 10/2 SSLC QB pull; verify"),
    (103, "Cost to Exos to fund completion (mid = WC bridge) ($)", 500000,
          "Same as B16 — $0.3–$0.7M to finish paid-for IM work; mid=$500K"),
]
for (r, lbl, val, src) in prepaid_data:
    ws.cell(r, 1).value = lbl; ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val; ws.cell(r, 2).font = Font(size=10, bold=True)
    ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src; ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.cell(r, 3).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 22

# ── BENEFITS TO SSLC INVESTORS (Jon 10/7) ────────────────────────────────────
sec_hdr(ws, 105, "BENEFITS TO SSLC INVESTORS (Jon 10/7)", bg=DARK_BLUE, col_end="C")
benefits = [
    (106, "1. Debt relief at face",                          "~$500K TBV",      "Microcosm/Wertz notes + AP paid; personal path for Jim"),
    (107, "2. Delivery obligations assumed & funded",        "$984K face/$500K cost", "Exos funds completion; per 10/2 QB pull; verify"),
    (108, "3. No further capital calls",                     "Structural",       "Investors stop funding a cash-negative entity"),
    (109, "4. Cash at close",                                "$2,510,000",       "Section 3 deal price cash component"),
    (110, "5. Earn-out upside — IM tank revenue (3 yrs)",   "Up to $900K",      "5%/yr x $5M IM firm; $300K cap"),
    (111, "6. Earn-out upside — Exos stock post-RTO",       "$0.6M–$2.1M",     "0.3–0.7% FD at listing ($200M–$300M MEV)"),
    (112, "7. Liquidity via listed Exos stock",              "Post-RTO ~FY28",   "12-mo lockup; publicly tradeable thereafter"),
    (113, "8. IM program continuity",                        "Operational",      "No customer disruption; Exos-SSLC entity delivers"),
]
for (r, lbl, val, src) in benefits:
    ws.cell(r, 1).value = lbl; ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 2).value = val; ws.cell(r, 2).font = Font(size=10)
    ws.cell(r, 3).value = src; ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.cell(r, 3).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 20

# ── HOLD TO YEAR 5 — ASSUMPTIONS (Jon 10/7) ──────────────────────────────────
sec_hdr(ws, 115, "HOLD TO YEAR 5 — ASSUMPTIONS (Jon 10/7)", bg=PURPLE, col_end="C")

y5_data = [
    (116, "EV/EBITDA multiple (Market Approach, Eqvista 409A 3/31/2026)", 16,
          "EV/EBITDA 16x — Eqvista 409A; Market Approach"),
    (117, "Old-Model (v12) FY31 EBITDA ($)",    101610000,
          "v12 Annual P&L Y5 total EBITDA; recalculated 10/7"),
    (118, "Old-Model FY31 implied EV ($)",       "=B117*B116",
          "FY31 EBITDA x 16x = ~$1.626B"),
    (119, "Actuals-Anchored FY31 EBITDA (est.) ($)", 11000000,
          "AA consolidated FY31 (SSLC ~$6.0M + Exos $5.0M); derived from PL sheet"),
    (120, "Actuals-Anchored FY31 implied EV ($)", "=B119*B116",
          "~$176M — BELOW $250M RTO listing value; see warning row 136"),
    (121, "SSLC earn-out stock stake at listing (base)", 0.005,
          "Base earn-out grant = 0.5% FD shares at listing"),
    (122, "Post-listing dilution assumption (flat, mgmt)", 0.30,
          "MANAGEMENT ASSUMPTION: Series A $25M staged (D1-D4, ~13%) + RTO issuance (~12%) + option pool (~5%) = ~30% dilution total"),
    (123, "Dilution factor (1 minus dilution)",  "=1-B122",   "0.70"),
    (124, "SSLC stake FY31 — base post-dilution", "=B121*B123",   "0.5% x 0.70 = 0.35%"),
    (125, "SSLC stake FY31 — low post-dilution",  "=Assumptions!B28*(1-B122)", "0.3% x 0.70 = 0.21%"),
    (126, "SSLC stake FY31 — high post-dilution", "=Assumptions!B30*(1-B122)", "0.7% x 0.70 = 0.49%"),
    (127, "Old-Model FY31 share value — low ($)",  "=B118*B125",   "~$3.41M"),
    (128, "Old-Model FY31 share value — base ($)", "=B118*B124",   "~$5.69M"),
    (129, "Old-Model FY31 share value — high ($)", "=B118*B126",   "~$7.97M"),
    (130, "AA FY31 share value — low ($)",         "=B120*B125",   "~$370K"),
    (131, "AA FY31 share value — base ($)",        "=B120*B124",   "~$616K"),
    (132, "AA FY31 share value — high ($)",        "=B120*B126",   "~$862K"),
    (133, "Multiple v at-listing — Old-Model base", "=B128/(Assumptions!B29*Assumptions!B32)",
          "~4.5x the at-listing stock earn-out value ($1.25M)"),
    (134, "Multiple v at-listing — AA base",        "=B131/(Assumptions!B29*Assumptions!B32)",
          "~0.49x — AA FY31 EV BELOW listing; stock worth less by FY31 in AA case"),
]
for (r, lbl, val, src) in y5_data:
    ws.cell(r, 1).value = lbl; ws.cell(r, 1).font = Font(size=10)
    ws.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
    ws.cell(r, 2).value = val; ws.cell(r, 2).font = Font(size=10, bold=True)
    ws.cell(r, 2).fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
    if isinstance(val, float) and 0 < abs(val) <= 1:
        ws.cell(r, 2).number_format = '0.00%'
    elif isinstance(val, (int, float)) and abs(val) >= 1000:
        ws.cell(r, 2).number_format = '$#,##0'
    elif isinstance(val, str) and val.startswith("="):
        if any(x in val for x in ["B122","B123","B124","B125","B126","B28","B29","B30"]):
            ws.cell(r, 2).number_format = '0.00%'
        else:
            ws.cell(r, 2).number_format = '$#,##0'
    ws.cell(r, 3).value = src; ws.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    ws.cell(r, 3).fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
    ws.cell(r, 3).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r].height = 28

ws.cell(136, 1).value = (
    "WARNING: AA CASE Y5 HOLD — Actuals-Anchored FY31 EV (~$176M) is BELOW the $250M RTO "
    "listing value. In the AA case, holding to FY31 yields LESS than the at-listing earn-out. "
    "This reflects conservative actuals-based projections, not a flaw in the deal. "
    "Old-Model (v12) FY31 EV ~$1.63B yields ~4.5x the at-listing stock value."
)
ws.merge_cells("A136:C136")
ws.cell(136, 1).font = Font(size=9, bold=True, color="C00000")
ws.cell(136, 1).fill = PatternFill("solid", fgColor=RED_LIGHT)
ws.cell(136, 1).alignment = Alignment(wrap_text=True)
ws.row_dimensions[136].height = 42


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 2: Deal Structure (unchanged from prior version)
# ─────────────────────────────────────────────────────────────────────────────
ds = wb.create_sheet("Deal Structure")
ds.column_dimensions["A"].width = 38
ds.column_dimensions["B"].width = 16
ds.column_dimensions["C"].width = 16
ds.column_dimensions["D"].width = 16
ds.column_dimensions["E"].width = 28

ds.merge_cells("A1:E1")
ds["A1"] = "SSLC Option B — Deal Structure, Sources & Uses, Earn-Out Analysis"
ds["A1"].font = Font(bold=True, color=WHITE, size=12)
ds["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
ds["A1"].alignment = Alignment(horizontal="center", vertical="center")
ds.row_dimensions[1].height = 22

ds["A2"] = "Option B: invoke §3 exclusivity at $3.36M base + earn-out (IM tank revenue and/or Exos stock post-listing). SSLC debts paid at face. DRAFT — negotiation-stage terms."
ds["A2"].font = Font(italic=True, size=9, color="444444")
ds.merge_cells("A2:E2")
ds.row_dimensions[2].height = 30

ds.merge_cells("A4:E4")
ds["A4"] = "SOURCES & USES AT CLOSE"
ds["A4"].font = Font(bold=True, color=WHITE); ds["A4"].fill = PatternFill("solid", fgColor=DARK_BLUE)

for col, txt in [(1,"Line Item"),(2,"Amount ($)"),(3,""),(4,""),(5,"Notes")]:
    c = ds.cell(row=5, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)

su_data = [
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
    elif lbl in ("USES", "SOURCES"):
        ds.merge_cells(f"A{r}:E{r}")
        ds.cell(r, 1).font = Font(bold=True, size=10)
        ds.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
    ds.row_dimensions[r].height = 18

ds.merge_cells("A21:E21")
ds["A21"] = "EARN-OUT MECHANICS (two variants shown side by side; combined option in Col D)"
ds["A21"].font = Font(bold=True, color=WHITE); ds["A21"].fill = PatternFill("solid", fgColor=DARK_BLUE)
ds.row_dimensions[21].height = 20

for col, txt in [(1,"Metric"),(2,"Earn-Out i: IM Tank Revenue %"),(3,"Earn-Out ii: Exos Stock post-RTO"),(4,"Combined (i + ii)"),(5,"Notes")]:
    c = ds.cell(row=22, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE, size=9); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(wrap_text=True, horizontal="center")

eo_data = [
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
    ds.cell(r, 2).value = i; ds.cell(r, 3).value = ii
    ds.cell(r, 4).value = comb
    ds.cell(r, 5).value = notes; ds.cell(r, 5).font = Font(size=9, italic=True, color="444444")
    for col in [2, 3, 4]:
        c = ds.cell(r, col)
        if isinstance(c.value, str) and c.value.startswith("="):
            c.number_format = "$#,##0"
        c.font = Font(size=9)
    ds.row_dimensions[r].height = 28

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
        ds.cell(r, col).number_format = "$#,##0" if "Payback" not in lbl else "0.0x"
    ds.cell(r, 5).value = notes; ds.cell(r, 5).font = Font(size=9, italic=True)
    if "TOTAL" in lbl:
        for col in range(1, 6):
            ds.cell(r, col).font = Font(bold=True)
            ds.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    ds.row_dimensions[r].height = 18


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 3: P&L and Cash Flow — TWO CASES
# ─────────────────────────────────────────────────────────────────────────────
pl = wb.create_sheet("PL and Cash Flow")
pl.column_dimensions["A"].width = 36
for col in ["B","C","D","E","F","G"]:
    pl.column_dimensions[col].width = 14
pl.column_dimensions["H"].width = 18

pl.merge_cells("A1:H1")
pl["A1"] = "EXOS + SSLC Consolidated P&L — Option B Acquisition | TWO CASES"
pl["A1"].font = Font(bold=True, color=WHITE, size=12)
pl["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
pl["A1"].alignment = Alignment(horizontal="center", vertical="center")
pl.row_dimensions[1].height = 22

pl["A2"] = ("Actuals-Anchored Case: uses Q1 FY27 actuals and actuals-derived projections. "
            "Old-Model Case (v12 drivers): uses v12 Scorpius unit/ASP/COGS ramp + v12 Exos standalone. "
            "FY27 SSLC fixed: $5.5M (quarterly basis) — prior annual formula ($6.925M) was inconsistent.")
pl["A2"].font = Font(italic=True, size=9, color="444444")
pl.merge_cells("A2:H2")
pl.row_dimensions[2].height = 28

# ── FY27 Quarterly (unchanged; clearly labelled Actuals-Anchored) ─────────────
pl.merge_cells("A4:H4")
pl["A4"] = "FY27 QUARTERLY — Actuals-Anchored Case — Exos+SSLC Consolidated (acquisition assumed closed Q1)"
pl["A4"].font = Font(bold=True, color=WHITE)
pl["A4"].fill = PatternFill("solid", fgColor=MID_BLUE)

for col, txt in [(1,"Line Item"),(2,"FY27 Q1"),(3,"FY27 Q2"),(4,"FY27 Q3"),(5,"FY27 Q4"),(6,"FY27 Total"),(7,""),(8,"Notes")]:
    c = pl.cell(row=5, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

q_data_pl = [
    (6,  "SSLC Revenue (post-consolidation)", 713000,  1387000, 1400000, 2000000, "Q1 actual $713K; Q2-Q4 distributes $5M IM firm ramp → FY27 total $5.5M"),
    (7,  "Exos Standalone Revenue",           550000,  700000,  700000,  650000,  "v15 baseline; $2.6M FY27 total excl. SSLC commission"),
    (8,  "Less: Intercompany Eliminations",   -125000, -125000, -125000, -125000, "Exos purchases from SSLC; $500K/yr eliminated"),
    (9,  "NET CONSOLIDATED REVENUE",          "=B6+B7+B8","=C6+C7+C8","=D6+D7+D8","=E6+E7+E8",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_data_pl:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True, color="444444")
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        pl.cell(r, col).number_format = "$#,##0;($#,##0)"
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "$#,##0;($#,##0)"
    if "NET CONSOLIDATED" in lbl:
        for col in range(1, 9):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    pl.row_dimensions[r].height = 18

pl.merge_cells("A11:H11")
pl["A11"] = "COST OF GOODS SOLD"
pl["A11"].font = Font(bold=True, color=WHITE); pl["A11"].fill = PatternFill("solid", fgColor=MID_BLUE)

q_cogs = [
    (12, "SSLC COGS (52%)",   "=B6*Assumptions!B45","=C6*Assumptions!B45","=D6*Assumptions!B45","=E6*Assumptions!B45","52%; derived from FY26"),
    (13, "Exos COGS (45%)",   "=B7*0.45","=C7*0.45","=D7*0.45","=E7*0.45","45% COGS"),
    (14, "TOTAL COGS",        "=B12+B13","=C12+C13","=D12+D13","=E12+E13",""),
    (15, "GROSS PROFIT",      "=B9-B14","=C9-C14","=D9-D14","=E9-E14",""),
    (16, "Gross Margin %",    "=IF(B9<>0,B15/B9,0)","=IF(C9<>0,C15/C9,0)","=IF(D9<>0,D15/D9,0)","=IF(E9<>0,E15/E9,0)",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_cogs:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True)
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        pl.cell(r, col).number_format = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
    if "GROSS PROFIT" in lbl or "TOTAL COGS" in lbl:
        for col in range(1, 7):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=GREEN)
    pl.row_dimensions[r].height = 18

pl.merge_cells("A18:H18")
pl["A18"] = "OPERATING EXPENSES"
pl["A18"].font = Font(bold=True, color=WHITE); pl["A18"].fill = PatternFill("solid", fgColor=MID_BLUE)

q_opex = [
    (19, "SSLC OpEx",           350000, 350000, 350000, 350000, "FY27 $1.4M / 4Q"),
    (20, "Exos OpEx (excl. R&D)",650000, 650000, 650000, 650000, "Exos G&A / payroll"),
    (21, "Exos R&D / BLK3 dev", 500000, 500000, 500000, 500000, "BLK3 development"),
    (22, "TOTAL OPEX",          "=SUM(B19:B21)","=SUM(C19:C21)","=SUM(D19:D21)","=SUM(E19:E21)",""),
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

q_ebitda_rows = [
    (24, "EBITDA", "=B15-B22","=C15-C22","=D15-D22","=E15-E22",""),
    (25, "EBITDA Margin %","=IF(B9<>0,B24/B9,0)","=IF(C9<>0,C24/C9,0)","=IF(D9<>0,D24/D9,0)","=IF(E9<>0,E24/E9,0)",""),
    (26, "D&A (est.)", -40000,-40000,-40000,-40000,"$160K FY27 combined"),
    (27, "EBIT",      "=B24+B26","=C24+C26","=D24+D26","=E24+E26",""),
    (28, "Interest / one-time","0","0","0","0",""),
    (29, "Pre-Tax Income","=B27+B28","=C27+C28","=D27+D28","=E27+E28",""),
]
for (r, lbl, q1, q2, q3, q4, notes) in q_ebitda_rows:
    pl.cell(r, 1).value = lbl
    pl.cell(r, 8).value = notes; pl.cell(r, 8).font = Font(size=9, italic=True)
    for col, val in [(2,q1),(3,q2),(4,q3),(5,q4)]:
        pl.cell(r, col).value = val
        pl.cell(r, col).number_format = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
    pl.cell(r, 6).value = f"=SUM(B{r}:E{r})"
    pl.cell(r, 6).number_format = "0.0%" if "%" in lbl else "$#,##0;($#,##0)"
    if lbl in ("EBITDA", "EBIT", "Pre-Tax Income"):
        for col in range(1, 7):
            pl.cell(r, col).font = Font(bold=True)
            pl.cell(r, col).fill = PatternFill("solid", fgColor=YELLOW)
    pl.row_dimensions[r].height = 18

# ── 5-Year Annual P&L — TWO CASES SIDE BY SIDE ────────────────────────────────
# Actuals-Anchored: cols B-G | Old-Model: cols I-N
pl.column_dimensions["H"].width = 3   # spacer
pl.column_dimensions["I"].width = 4   # case label
for col_letter in ["J","K","L","M","N","O"]:
    pl.column_dimensions[col_letter].width = 14
pl.column_dimensions["P"].width = 22

# Merged header across both cases
pl.merge_cells("A32:P32")
pl["A32"] = "5-YEAR ANNUAL P&L — FY27–FY31 | LEFT: Actuals-Anchored Case | RIGHT: Old-Model Case (v12 Drivers)"
pl["A32"].font = Font(bold=True, color=WHITE, size=11)
pl["A32"].fill = PatternFill("solid", fgColor=DARK_BLUE)
pl["A32"].alignment = Alignment(horizontal="center")
pl.row_dimensions[32].height = 22

# Actuals-Anchored sub-header
pl.merge_cells("A33:G33")
pl["A33"] = "ACTUALS-ANCHORED CASE"
pl["A33"].font = Font(bold=True, color=WHITE, size=10)
pl["A33"].fill = PatternFill("solid", fgColor=MID_BLUE)
pl["A33"].alignment = Alignment(horizontal="center")

# Old-Model sub-header
pl.merge_cells("J33:P33")
pl["J33"] = "OLD-MODEL CASE (v12 DRIVERS) — source: v12 Annual P&L, recalculated 10/7"
pl["J33"].font = Font(bold=True, color=WHITE, size=10)
pl["J33"].fill = PatternFill("solid", fgColor=PURPLE)
pl["J33"].alignment = Alignment(horizontal="center")

# Column headers row 34
for col, txt in [(1,"Line Item"),(2,"FY27"),(3,"FY28"),(4,"FY29"),(5,"FY30"),(6,"FY31"),(7,"CAGR")]:
    c = pl.cell(row=34, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=MID_BLUE)
    c.alignment = Alignment(horizontal="center")

for col, txt in [(10,"FY27"),(11,"FY28"),(12,"FY29"),(13,"FY30"),(14,"FY31"),(15,"CAGR"),(16,"Notes")]:
    c = pl.cell(row=34, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE); c.fill = PatternFill("solid", fgColor=PURPLE)
    c.alignment = Alignment(horizontal="center")

pl.cell(34, 1).value = "Line Item"
pl.row_dimensions[34].height = 18

# helper: bold highlight row both sides
def ann_row(r, lbl, aa_vals, v12_vals, notes, bold=False, aa_bg=None, v12_bg=None, pct=False):
    pl.cell(r, 1).value = lbl
    pl.cell(r, 1).font = Font(bold=bold, size=10)
    pl.cell(r, 16).value = notes
    pl.cell(r, 16).font = Font(size=9, italic=True, color="444444")
    pl.cell(r, 16).alignment = Alignment(wrap_text=True)
    fmt = "0.0%" if pct else "$#,##0;($#,##0)"
    for i, val in enumerate(aa_vals):
        col = i + 2
        c = pl.cell(r, col, value=val)
        c.number_format = fmt
        if bold: c.font = Font(bold=True, size=10)
        if aa_bg: c.fill = PatternFill("solid", fgColor=aa_bg)
    for i, val in enumerate(v12_vals):
        col = i + 10
        c = pl.cell(r, col, value=val)
        c.number_format = fmt
        if bold: c.font = Font(bold=True, size=10)
        if v12_bg: c.fill = PatternFill("solid", fgColor=v12_bg)
    # CAGR col 7 (AA) and 15 (v12)
    aa_cagr_f = f"=IFERROR((F{r}/B{r})^(1/4)-1,0)"
    v12_cagr_f = f"=IFERROR((N{r}/J{r})^(1/4)-1,0)"
    pl.cell(r, 7).value = aa_cagr_f; pl.cell(r, 7).number_format = "0.0%"
    pl.cell(r, 15).value = v12_cagr_f; pl.cell(r, 15).number_format = "0.0%"
    pl.row_dimensions[r].height = 18

# Revenue section header
pl.merge_cells("A36:G36")
pl["A36"] = "REVENUE"
pl["A36"].fill = PatternFill("solid", fgColor=LIGHT_BLUE)
pl["A36"].font = Font(bold=True, size=9)
pl.merge_cells("J36:P36")
pl["J36"] = "REVENUE"
pl["J36"].fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
pl["J36"].font = Font(bold=True, size=9)
pl.row_dimensions[36].height = 16

# Actuals-Anchored values (note: FY27 fixed at $5.5M per B48)
aa_sslc  = ["=Assumptions!B48","=Assumptions!B49","=Assumptions!B50","=Assumptions!B51","=Assumptions!B52"]
aa_exos  = ["=Assumptions!B57","=Assumptions!B58","=Assumptions!B59","=Assumptions!B60","=Assumptions!B61"]
aa_inter = [-500000,-575000,-661000,-760000,-874000]
aa_net   = [f"=B{37}+B{38}+B{39}",f"=C{37}+C{38}+C{39}",f"=D{37}+D{38}+D{39}",f"=E{37}+E{38}+E{39}",f"=F{37}+F{38}+F{39}"]

# Old-Model (v12) values from Assumptions block
v12_sslc  = ["=Assumptions!B76","=Assumptions!B77","=Assumptions!B78","=Assumptions!B79","=Assumptions!B80"]
v12_exos  = ["=Assumptions!B86","=Assumptions!B87","=Assumptions!B88","=Assumptions!B89","=Assumptions!B90"]
v12_inter = [-500000,-575000,-661000,-760000,-874000]  # same interco assumption
v12_net   = ["=Assumptions!B81","=Assumptions!B82","=Assumptions!B83","=Assumptions!B84","=Assumptions!B85"]

ann_row(37, "SSLC Revenue", aa_sslc, v12_sslc,
        "AA: $5.5M (fixed, quarterly basis); v12: tank unit/ASP ramp model")
ann_row(38, "Exos Standalone Revenue", aa_exos, v12_exos,
        "AA: v15 commission-only basis; v12: includes BLK4/propulsion/wet-lease ramp")
ann_row(39, "Less: Intercompany", aa_inter, v12_inter, "Same in both cases")
ann_row(40, "NET CONSOLIDATED REVENUE",
        [f"=B{37}+B{38}+B{39}",f"=C{37}+C{38}+C{39}",f"=D{37}+D{38}+D{39}",f"=E{37}+E{38}+E{39}",f"=F{37}+F{38}+F{39}"],
        v12_net,
        "", bold=True, aa_bg=YELLOW, v12_bg=YELLOW)

# EBITDA section header
pl.merge_cells("A42:G42")
pl["A42"] = "EBITDA"
pl["A42"].fill = PatternFill("solid", fgColor=LIGHT_BLUE)
pl["A42"].font = Font(bold=True, size=9)
pl.merge_cells("J42:P42")
pl["J42"] = "EBITDA"
pl["J42"].fill = PatternFill("solid", fgColor=LIGHT_PURPLE)
pl["J42"].font = Font(bold=True, size=9)
pl.row_dimensions[42].height = 16

# Actuals-anchored SSLC EBITDA = SSLC_rev × (1-COGS%) - OpEx
aa_sslc_ebitda = [
    "=Assumptions!B48*(1-Assumptions!B45)-Assumptions!B46",
    "=Assumptions!B49*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)",
    "=Assumptions!B50*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)^2",
    "=Assumptions!B51*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)^3",
    "=Assumptions!B52*(1-Assumptions!B45)-Assumptions!B46*(1+Assumptions!B47)^4",
]
aa_exos_ebitda = ["=Assumptions!B62","=Assumptions!B63","=Assumptions!B64","=Assumptions!B65","=Assumptions!B66"]

# v12 EBITDA — total consolidated from model; SSLC portion derived
# SSLC EBITDA v12: rev × (1 - COGS Y1-Y2=35%, Y3-Y5=30%) minus SSLC opex (use same $1.4M base / 8% growth)
v12_sslc_ebitda = [
    "=Assumptions!B76*(1-Assumptions!B74)-Assumptions!B46",
    "=Assumptions!B77*(1-Assumptions!B74)-Assumptions!B46*(1+Assumptions!B47)",
    "=Assumptions!B78*(1-Assumptions!B75)-Assumptions!B46*(1+Assumptions!B47)^2",
    "=Assumptions!B79*(1-Assumptions!B75)-Assumptions!B46*(1+Assumptions!B47)^3",
    "=Assumptions!B80*(1-Assumptions!B75)-Assumptions!B46*(1+Assumptions!B47)^4",
]
# v12 Exos standalone EBITDA = v12 total EBITDA - v12 SSLC EBITDA
v12_exos_ebitda = [
    f"=Assumptions!B91-J{43}",
    f"=Assumptions!B92-K{43}",
    f"=Assumptions!B93-L{43}",
    f"=Assumptions!B94-M{43}",
    f"=Assumptions!B95-N{43}",
]

ann_row(43, "SSLC EBITDA", aa_sslc_ebitda, v12_sslc_ebitda,
        "AA: 48% gross margin − OpEx; v12: 65%/70% GM − OpEx (35%/30% COGS)")
ann_row(44, "Exos Standalone EBITDA", aa_exos_ebitda, v12_exos_ebitda,
        "AA: v15 management assumption; v12: derived from v12 total EBITDA − v12 SSLC EBITDA")
ann_row(45, "CONSOLIDATED EBITDA",
        [f"=B{43}+B{44}",f"=C{43}+C{44}",f"=D{43}+D{44}",f"=E{43}+E{44}",f"=F{43}+F{44}"],
        ["=Assumptions!B91","=Assumptions!B92","=Assumptions!B93","=Assumptions!B94","=Assumptions!B95"],
        "v12 total EBITDA taken directly from v12 Annual P&L", bold=True, aa_bg=YELLOW, v12_bg=YELLOW)
ann_row(46, "EBITDA Margin %",
        [f"=IF(B40<>0,B45/B40,0)",f"=IF(C40<>0,C45/C40,0)",f"=IF(D40<>0,D45/D40,0)",f"=IF(E40<>0,E45/E40,0)",f"=IF(F40<>0,F45/F40,0)"],
        [f"=IF(J40<>0,J45/J40,0)",f"=IF(K40<>0,K45/K40,0)",f"=IF(L40<>0,L45/L40,0)",f"=IF(M40<>0,M45/M40,0)",f"=IF(N40<>0,N45/N40,0)"],
        "", pct=True)

# v15 benchmark comparison
pl.merge_cells("A48:G48")
pl["A48"] = "BENCHMARK COMPARISON (Option B / both cases vs v15 old acquisition model)"
pl["A48"].fill = PatternFill("solid", fgColor=LIGHT_BLUE)
pl["A48"].font = Font(bold=True, size=9)
pl.row_dimensions[48].height = 16

pl.cell(49, 1).value = "v15 benchmark SSLC acq rev Y1"
pl.cell(49, 1).font = Font(size=9, italic=True)
pl.cell(49, 2).value = "=Assumptions!B53"; pl.cell(49, 2).number_format = "$#,##0"
pl.cell(49, 6).value = "=Assumptions!B54"; pl.cell(49, 6).number_format = "$#,##0"
pl.cell(49, 16).value = "v15 Y1=$0.9M, Y5=$21M — understates both cases"
pl.cell(49, 16).font = Font(size=9, italic=True, color="C00000")
pl.row_dimensions[49].height = 18

pl.cell(50, 1).value = "AA Case SSLC rev vs v15 benchmark"
pl.cell(50, 2).value = "=B37-B49"; pl.cell(50, 2).number_format = "$#,##0"
pl.cell(50, 6).value = "=F37-F49"; pl.cell(50, 6).number_format = "$#,##0"
pl.cell(50, 10).value = "v12 SSLC rev vs v15 benchmark"
pl.cell(50, 10).font = Font(size=9, italic=True)
pl.cell(50, 11).value = "=J37-B49"; pl.cell(50, 11).number_format = "$#,##0"
pl.cell(50, 14).value = "=N37-F49"; pl.cell(50, 14).number_format = "$#,##0"
pl.cell(50, 16).value = "Positive = exceeds v15; v12 exceeds v15 by 4.6x at Y1 and 2.6x at Y5"
pl.cell(50, 16).font = Font(size=9, italic=True, color="C00000")
pl.row_dimensions[50].height = 18

pl.cell(51, 1).value = "⚠ v15 'Scorpius acquisition benchmark' ($0.9M→$21M) understates v12's own Scorpius line ($4.1M→$54.7M) by 13× at Y5. See Assumptions!A97 for full note."
pl.merge_cells("A51:P51")
pl.cell(51, 1).font = Font(bold=True, size=9, color="C00000")
pl.cell(51, 1).fill = PatternFill("solid", fgColor=RED_LIGHT)
pl.row_dimensions[51].height = 22


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 4: Returns and Dilution — both cases
# ─────────────────────────────────────────────────────────────────────────────
rd = wb.create_sheet("Returns and Dilution")
rd.column_dimensions["A"].width = 36
for col in ["B","C","D","E","F","G"]:
    rd.column_dimensions[col].width = 15
rd.column_dimensions["H"].width = 22

rd.merge_cells("A1:H1")
rd["A1"] = "SSLC Option B — Returns, Dilution & Benchmark Comparison | TWO CASES"
rd["A1"].font = Font(bold=True, color=WHITE, size=12)
rd["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
rd["A1"].alignment = Alignment(horizontal="center")
rd.row_dimensions[1].height = 22

for col, txt in [(1,"Metric"),(2,"AA — Low"),(3,"AA — Base"),(4,"AA — High"),(5,"v12 Old-Model"),(6,"v15 Benchmark"),(7,""),(8,"Notes")]:
    c = rd.cell(row=3, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=MID_BLUE if col <= 4 else (PURPLE if col == 5 else DARK_BLUE))
    c.alignment = Alignment(horizontal="center", wrap_text=True)
rd.row_dimensions[3].height = 22

returns_data = [
    (4,  "FY27 (Y1) SSLC revenue",
         "='PL and Cash Flow'!B37","='PL and Cash Flow'!B37","='PL and Cash Flow'!B37",
         "='PL and Cash Flow'!J37","=Assumptions!B53",""),
    (5,  "FY31 (Y5) SSLC revenue",
         "='PL and Cash Flow'!F37","='PL and Cash Flow'!F37","='PL and Cash Flow'!F37",
         "='PL and Cash Flow'!N37","=Assumptions!B54",""),
    (6,  "FY27 total revenue",
         "='PL and Cash Flow'!B40","='PL and Cash Flow'!B40","='PL and Cash Flow'!B40",
         "='PL and Cash Flow'!J40","n/a",""),
    (7,  "FY31 total revenue",
         "='PL and Cash Flow'!F40","='PL and Cash Flow'!F40","='PL and Cash Flow'!F40",
         "='PL and Cash Flow'!N40","n/a",""),
    (8,  "FY27 EBITDA",
         "='PL and Cash Flow'!B45","='PL and Cash Flow'!B45","='PL and Cash Flow'!B45",
         "='PL and Cash Flow'!J45","n/a",""),
    (9,  "FY31 EBITDA",
         "='PL and Cash Flow'!F45","='PL and Cash Flow'!F45","='PL and Cash Flow'!F45",
         "='PL and Cash Flow'!N45","n/a",""),
    (11, "Total consideration (all-in)",
         "='Deal Structure'!B35","='Deal Structure'!C35","='Deal Structure'!D35","same","n/a",""),
    (12, "FY31 SSLC EBITDA × 10x (exit value)",
         "='PL and Cash Flow'!F43*10","='PL and Cash Flow'!F43*10","='PL and Cash Flow'!F43*10",
         "='PL and Cash Flow'!N43*10","n/a","Indicative only"),
    (13, "Acquisition ROI (FY31 val / cost)",
         "=B12/B11","=C12/C11","=D12/D11","='PL and Cash Flow'!N43*10/'Deal Structure'!C35","n/a",
         ""),
    (15, "Earn-out ii stock dilution (low/base/high)",
         "=Assumptions!B28","=Assumptions!B29","=Assumptions!B30","same","n/a","% FD shares"),
    (17, "FY27 net cash deployment",
         "=Assumptions!B10+Assumptions!B16","=Assumptions!B10+Assumptions!B16","=Assumptions!B10+Assumptions!B16",
         "same","n/a","Acq + WC from Series A"),
    (18, "Series A first close",
         "=Assumptions!B17","=Assumptions!B17","=Assumptions!B17","same","n/a",""),
    (19, "Remaining for Exos ops post-acq",
         "=B18-B17","=C18-C17","=D18-D17","same","n/a",""),
]
for row_data in returns_data:
    if len(row_data) < 7: continue
    r = row_data[0]; lbl = row_data[1]
    vals = list(row_data[2:7])
    notes = row_data[7] if len(row_data) > 7 else ""
    rd.cell(r, 1).value = lbl
    rd.cell(r, 8).value = notes; rd.cell(r, 8).font = Font(size=9, italic=True, color="444444")
    for i, val in enumerate(vals):
        col = i + 2
        rd.cell(r, col).value = val
        if "ROI" in lbl or "dilution" in lbl.lower():
            rd.cell(r, col).number_format = "0.0x" if "ROI" in lbl else "0.00%"
        else:
            rd.cell(r, col).number_format = "$#,##0"
    rd.row_dimensions[r].height = 18

for r, title in [(10,"RETURNS ANALYSIS"),(14,"DILUTION"),(16,"CASH DEPLOYMENT")]:
    rd.merge_cells(f"A{r}:H{r}")
    rd.cell(r, 1).value = title
    rd.cell(r, 1).font = Font(bold=True, size=10)
    rd.cell(r, 1).fill = PatternFill("solid", fgColor=LIGHT_BLUE)
    rd.row_dimensions[r].height = 18


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 5: Funding (unchanged)
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
    (3,  "FUNDING OVERVIEW",                         "",                       ""),
    (4,  "Acquisition is funded from Exos-only post-RTO proceeds","Investor requirement","SSLC stays OUT of RTO perimeter (Jon 10/2)"),
    (5,  "Series A first close ($)",                 "=Assumptions!B17",       "D1 of record; $10M"),
    (6,  "  Allocated to SSLC acquisition",          "=Assumptions!B10",       "Cash deal price"),
    (7,  "  Allocated to SSLC WC bridge",            "=Assumptions!B16",       "$0.3–0.7M; mid=$500K"),
    (8,  "  Remaining for Exos operations",          "=B5-B6-B7",              ""),
    (9,  "Pre-RTO convertible note ($)",             "=Assumptions!B20",       "FNEX/Ainigma; primary Exos development capital"),
    (10, "TOTAL FINANCING AT CLOSE",                 "=B5",                    "Series A covers acquisition + WC bridge"),
    (12, "§3 FINANCING TRIGGER GAP (CRITICAL RISK)", "",                       ""),
    (13, "FNEX/Ainigma role",                        "Advisor / broker-dealer","FNEX is NOT itself the 'investor or lender' under §3"),
    (14, "Risk: SSLC counsel challenges trigger",    "HIGH",                   "§3 requires 'investor or lender capable of financing'; advisory mandate may not qualify"),
    (15, "Mitigation required",                      "FNEX countersigned + investor/sponsor use-of-proceeds letter naming SSLC asset purchase","[Confirm FNEX agreement countersigned per D-7281974 10/6]"),
    (16, "§3 extension right",                       "SSLC shall not unreasonably withhold","90-day window; request extension proactively"),
    (17, "Timing: 90-day exclusivity ends",          "~Jan 6, 2027",           "From ~Oct 8 grant; RTO is 4-5 months; need extension"),
    (19, "RELATED-PARTY DISCLOSURES",                "",                       ""),
    (20, "Jon sits on BOTH boards",                  "Conflict of interest",   "Jon must RECUSE from SSLC vote; send as Exos CEO only"),
    (21, "Fairness opinion",                         "Required (Eqvista 8/14/2026)","Agreement still unsigned (held ~1 month)"),
    (22, "Disinterested director approval",          "Required (SSLC side)",   "Markus Rufer and Bob; Jon abstains"),
    (23, "Legal review",                             "Deferred (Jon 10/7)",    "Negotiation stage; no legal review until Jon calls it"),
    (25, "HE-TANK DISPUTE RISK",                     "",                       ""),
    (26, "Rev3 tank leaks at boss post-Hysol",       "RISK",                   "10/1 hydro fail; Plan B: qualified COPV ≤$250K (MC #3056)"),
    (27, "Impact on acquisition",                    "SSLC demonstrably can't deliver BLK3 flight article","Customer-hat PO default kept in reserve"),
    (29, "SSLC CASH RISK",                           "",                       ""),
    (30, "SSLC cash at close (est.)",                "=Assumptions!B42+Assumptions!B41-Assumptions!B16","FY27 Q1 cash + billed-ahead minus WC need"),
    (31, "Risk: SSLC runs out before close",         "MEDIUM",                 "Cash $198K + collections on $984K prepaid"),
    (32, "Mitigation: Option C pre-cliff bridge",    "Secured prepaid BLK3 tank PO $300-700K","Option C held for follow-up"),
    (34, "DATA NOT VERIFIED IN SSLC QB (CRITICAL)",  "",                       ""),
    (35, "SSLC total liabilities / AP",              "~$500K est. — TO VERIFY","QB session expired 10/7; cannot confirm Microcosm/Wertz amounts"),
    (36, "SSLC total debt assumed at face",          "TO VERIFY IN SSLC QB",   "Critical for Bob/Jim: personal path depends on debt payoff"),
    (37, "Exos loan to SSLC status in QB",           "~$38K — cancelled 10/2", "Verify cancellation documented in QB"),
]
for (r, lbl, val, notes) in fund_data:
    fn.cell(r, 1).value = lbl; fn.cell(r, 2).value = val; fn.cell(r, 3).value = notes
    fn.cell(r, 1).font = Font(size=10)
    fn.cell(r, 3).font = Font(size=9, italic=True, color="444444")
    fn.cell(r, 3).alignment = Alignment(wrap_text=True)
    if isinstance(val, str) and val.startswith("="):
        fn.cell(r, 2).number_format = "$#,##0"
        fn.cell(r, 2).font = Font(bold=True, size=10)
    if lbl in ("FUNDING OVERVIEW","§3 FINANCING TRIGGER GAP (CRITICAL RISK)","RELATED-PARTY DISCLOSURES",
               "HE-TANK DISPUTE RISK","SSLC CASH RISK","DATA NOT VERIFIED IN SSLC QB (CRITICAL)"):
        fn.merge_cells(f"A{r}:C{r}")
        fn.cell(r, 1).font = Font(bold=True, color=WHITE)
        fn.cell(r, 1).fill = PatternFill("solid", fgColor=DARK_BLUE)
    if val in ("HIGH","MEDIUM"):
        fn.cell(r, 2).font = Font(bold=True, color="FF0000" if val=="HIGH" else "FF8C00")
    fn.row_dimensions[r].height = 28


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 6: Total Compensation — both cases
# ─────────────────────────────────────────────────────────────────────────────
tcomp = wb.create_sheet("Total Compensation")
tcomp.column_dimensions["A"].width = 40
for col in ["B","C","D","E","F","G","H"]:
    tcomp.column_dimensions[col].width = 13

tcomp.merge_cells("A1:H1")
tcomp["A1"] = "SSLC Option B — Total Compensation to SSLC Shareholders/Stakeholders | TWO CASES"
tcomp["A1"].font = Font(bold=True, color=WHITE, size=12)
tcomp["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
tcomp["A1"].alignment = Alignment(horizontal="center", vertical="center")
tcomp.row_dimensions[1].height = 22

tcomp["A2"] = ("BASE = Old-Model Case (v12 drivers), as requested. Actuals-Anchored shown as sensitivity. "
               "Funding at close identical in both; chart shows Old-Model base.")
tcomp["A2"].font = Font(italic=True, size=9, color="C00000")
tcomp.merge_cells("A2:H2")

for col, txt in [(1,"Component"),(2,"FY27 (Close)"),(3,"FY28"),(4,"FY29"),(5,"FY30"),(6,"FY31"),(7,"5-Yr Total"),(8,"Notes")]:
    c = tcomp.cell(row=4, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=DARK_BLUE)
    c.alignment = Alignment(horizontal="center", wrap_text=True)

# Funding at close
tcomp.merge_cells("A5:H5")
tcomp["A5"] = "FUNDING DELIVERED AT CLOSE (FY27) — identical in both cases"
tcomp["A5"].font = Font(bold=True, size=10, color=WHITE)
tcomp["A5"].fill = PatternFill("solid", fgColor="444444")

fund_rows = [
    (6,  "Cash at close",                               "=Assumptions!B10", 0,0,0,0,"§3 deal price"),
    (7,  "SSLC closing costs",                          "=Assumptions!B11", 0,0,0,0,"Seller's costs"),
    (8,  "Exos stake credit (non-cash)",                "=Assumptions!B12", 0,0,0,0,"18% equity at 2021 basis"),
    (9,  "SSLC debts assumed at face (TBV)",            "=Assumptions!B14", 0,0,0,0,"per 10/2 SSLC QB pull; verify"),
    (10, "Prepaid-work delivery obligations assumed",   "=Assumptions!B100",0,0,0,0,"$984K face (billed-ahead $864K + deposits $120K); per 10/2 SSLC QB pull; verify"),
    (11, "Working-capital bridge (completion cost)",    "=Assumptions!B16", 0,0,0,0,"Mid=$500K; funds completion of prepaid IM work"),
    (12, "TOTAL FUNDING DELIVERED",
         "=SUM(B6:B11)","=SUM(C6:C11)","=SUM(D6:D11)","=SUM(E6:E11)","=SUM(F6:F11)",
         "All at close in FY27"),
]
for r, lbl, fy27, fy28, fy29, fy30, fy31, notes in fund_rows:
    tcomp.cell(r, 1).value = lbl
    tcomp.cell(r, 8).value = notes
    tcomp.cell(r, 8).font = Font(size=9, italic=True, color="444444")
    for col, val in [(2,fy27),(3,fy28),(4,fy29),(5,fy30),(6,fy31)]:
        tcomp.cell(r, col).value = val
        tcomp.cell(r, col).number_format = "$#,##0"
    tcomp.cell(r, 7).value = f"=SUM(B{r}:F{r})"
    tcomp.cell(r, 7).number_format = "$#,##0"
    if "TOTAL" in lbl:
        for col in range(1, 8):
            tcomp.cell(r, col).font = Font(bold=True, size=10)
            tcomp.cell(r, col).fill = PatternFill("solid", fgColor="666666")
            if col > 1:
                tcomp.cell(r, col).font = Font(bold=True, size=10, color=WHITE)
    else:
        tcomp.cell(r, 1).font = Font(size=10)
        tcomp.cell(r, 1).fill = PatternFill("solid", fgColor=GREY)
    tcomp.row_dimensions[r].height = 18

# Earn-outs
tcomp.merge_cells("A13:H13")
tcomp["A13"] = "FORWARD POTENTIAL — EARN-OUTS (same in both cases; driven by IM firm revenue)"
tcomp["A13"].font = Font(bold=True, size=10, color=WHITE)
tcomp["A13"].fill = PatternFill("solid", fgColor="E26A21")

fwd_rows = [
    (14, "Tank earn-out base (i): 5%/yr, $300K cap",
         "=MIN(Assumptions!B24*Assumptions!B44,Assumptions!B26)",
         "=MIN(Assumptions!B24*Assumptions!B44,Assumptions!B26)",
         "=MIN(Assumptions!B24*Assumptions!B44,Assumptions!B26)",
         0, 0, "5% × $5M firm IM ramp × 3 years; $300K/yr cap"),
    (15, "Tank earn-out low (i): 3%/yr",
         "=MIN(Assumptions!B23*Assumptions!B44,Assumptions!B26)",
         "=MIN(Assumptions!B23*Assumptions!B44,Assumptions!B26)",
         "=MIN(Assumptions!B23*Assumptions!B44,Assumptions!B26)",
         0, 0, "Low scenario"),
    (16, "Tank earn-out high (i): 7%/yr",
         "=MIN(Assumptions!B25*Assumptions!B44,Assumptions!B26)",
         "=MIN(Assumptions!B25*Assumptions!B44,Assumptions!B26)",
         "=MIN(Assumptions!B25*Assumptions!B44,Assumptions!B26)",
         0, 0, "High — capped at $300K"),
    (17, "Stock earn-out base (ii): 0.5% FD @ listing",
         0, 0, "=Assumptions!B29*Assumptions!B32", 0, 0,
         "At $250M listing; realized FY29 post lockup"),
    (18, "Stock earn-out low (ii): 0.3% @ $200M",
         0, 0, "=Assumptions!B28*Assumptions!B31", 0, 0, "Low RTO"),
    (19, "Stock earn-out high (ii): 0.7% @ $300M",
         0, 0, "=Assumptions!B30*Assumptions!B33", 0, 0, "High RTO"),
]
for r, lbl, fy27, fy28, fy29, fy30, fy31, notes in fwd_rows:
    tcomp.cell(r, 1).value = lbl
    tcomp.cell(r, 1).font = Font(size=10)
    tcomp.cell(r, 1).fill = PatternFill("solid", fgColor=GREY)
    tcomp.cell(r, 8).value = notes
    tcomp.cell(r, 8).font = Font(size=9, italic=True, color="444444")
    for col, val in [(2,fy27),(3,fy28),(4,fy29),(5,fy30),(6,fy31)]:
        tcomp.cell(r, col).value = val
        tcomp.cell(r, col).number_format = "$#,##0"
    tcomp.cell(r, 7).value = f"=SUM(B{r}:F{r})"
    tcomp.cell(r, 7).number_format = "$#,##0"
    tcomp.row_dimensions[r].height = 18

# TOTAL CONSIDERATION — OLD MODEL (base) + ACTUALS-ANCHORED (sensitivity)
tcomp.merge_cells("A21:H21")
tcomp["A21"] = "TOTAL CONSIDERATION — OLD-MODEL CASE (v12) BASE | Actuals-Anchored as Sensitivity"
tcomp["A21"].font = Font(bold=True, size=10, color=WHITE)
tcomp["A21"].fill = PatternFill("solid", fgColor=PURPLE)

tot_rows = [
    (22, "OLD-MODEL BASE: funding + tank base + stock base",
         "=B12+B14+B17","=C12+C14+C17","=D12+D14+D17","=E12+E14+E17","=F12+F14+F17"),
    (23, "OLD-MODEL LOW:  funding + tank low + stock low",
         "=B12+B15+B18","=C12+C15+C18","=D12+D15+D18","=E12+E15+E18","=F12+F15+F18"),
    (24, "OLD-MODEL HIGH: funding + tank high + stock high",
         "=B12+B16+B19","=C12+C16+C19","=D12+D16+D19","=E12+E16+E19","=F12+F16+F19"),
    (25, "AA SENSITIVITY BASE: funding + tank base + stock base",
         "=B12+B14+B17","=C12+C14+C17","=D12+D14+D17","=E12+E14+E17","=F12+F14+F17"),
]
row_bgs = [YELLOW, GREEN, ORANGE, LIGHT_BLUE]
for (r, lbl, fy27, fy28, fy29, fy30, fy31), rbg in zip(tot_rows, row_bgs):
    tcomp.cell(r, 1).value = lbl
    tcomp.cell(r, 1).font = Font(bold=True, size=10)
    tcomp.cell(r, 1).fill = PatternFill("solid", fgColor=rbg)
    for col, val in [(2,fy27),(3,fy28),(4,fy29),(5,fy30),(6,fy31)]:
        tcomp.cell(r, col).value = val
        tcomp.cell(r, col).number_format = "$#,##0"
        tcomp.cell(r, col).font = Font(bold=True, size=10)
        tcomp.cell(r, col).fill = PatternFill("solid", fgColor=rbg)
    tcomp.cell(r, 7).value = f"=SUM(B{r}:F{r})"
    tcomp.cell(r, 7).number_format = "$#,##0"
    tcomp.cell(r, 7).font = Font(bold=True, size=10)
    tcomp.cell(r, 7).fill = PatternFill("solid", fgColor=rbg)
    tcomp.row_dimensions[r].height = 20

tcomp["A27"] = "Chart: see drafts/SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png (incl prepaid-work + Y5 hold annotation)"

# ── HOLD TO YEAR 5 — Total Compensation perspective ──────────────────────────
tcomp.merge_cells("A29:H29")
tcomp["A29"] = "HOLD TO YEAR 5 — Forward Potential if SSLC Investors Hold Exos Shares to FY31 (Jon 10/7)"
tcomp["A29"].font = Font(bold=True, size=10, color=WHITE)
tcomp["A29"].fill = PatternFill("solid", fgColor=PURPLE)

tcomp["A30"] = ("Base = Old-Model (v12). Dilution: Series A $25M staged (D1-D4, ~13%) + RTO (~12%) + "
                "option pool (~5%) = ~30% flat (MANAGEMENT ASSUMPTION). "
                "0.5% stake at listing → 0.35% post-dilution. "
                "AA case EV ~$176M = BELOW $250M listing — stock worth less in AA case by FY31.")
tcomp["A30"].font = Font(size=8, italic=True, color="C00000")
tcomp.merge_cells("A30:H30")
tcomp.row_dimensions[30].height = 32
tcomp["A30"].alignment = Alignment(wrap_text=True)

for col, txt in [(1,"Scenario"),(2,"FY31 EV"),(3,"Post-dil stake"),(4,"FY31 share value"),(5,"At-listing value"),(6,"Multiple vs listing"),(7,""),(8,"Notes")]:
    c = tcomp.cell(row=31, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE, size=9)
    c.fill = PatternFill("solid", fgColor=PURPLE)
    c.alignment = Alignment(horizontal="center", wrap_text=True)
tcomp.row_dimensions[31].height = 22

y5_hold_rows = [
    (32, "Old-Model — Low",   "=Assumptions!B118", "=Assumptions!B125",
         "=B32*C32", "=Assumptions!B28*Assumptions!B31", "=D32/E32",
         "0.3% grant x 0.70 = 0.21%; EV $1.626B"),
    (33, "Old-Model — Base",  "=Assumptions!B118", "=Assumptions!B124",
         "=B33*C33", "=Assumptions!B29*Assumptions!B32", "=D33/E33",
         "0.5% grant x 0.70 = 0.35%; EV $1.626B (~4.5x listing)"),
    (34, "Old-Model — High",  "=Assumptions!B118", "=Assumptions!B126",
         "=B34*C34", "=Assumptions!B30*Assumptions!B33", "=D34/E34",
         "0.7% grant x 0.70 = 0.49%; EV $1.626B"),
    (35, "AA — Low",          "=Assumptions!B120", "=Assumptions!B125",
         "=B35*C35", "=Assumptions!B28*Assumptions!B31", "=D35/E35",
         "BELOW listing value — AA FY31 EV ~$176M < $250M MEV"),
    (36, "AA — Base",         "=Assumptions!B120", "=Assumptions!B124",
         "=B36*C36", "=Assumptions!B29*Assumptions!B32", "=D36/E36",
         "BELOW listing — ~$616K vs $1.25M at listing (~0.49x)"),
    (37, "AA — High",         "=Assumptions!B120", "=Assumptions!B126",
         "=B37*C37", "=Assumptions!B30*Assumptions!B33", "=D37/E37",
         "BELOW listing — ~$862K vs $2.1M at listing (~0.41x)"),
]
for r, label, ev, stake, val, at_list, mult, notes in y5_hold_rows:
    tcomp.cell(r, 1).value = label; tcomp.cell(r, 1).font = Font(size=9)
    tcomp.cell(r, 2).value = ev;    tcomp.cell(r, 2).number_format = "$#,##0"
    tcomp.cell(r, 3).value = stake; tcomp.cell(r, 3).number_format = "0.00%"
    tcomp.cell(r, 4).value = val;   tcomp.cell(r, 4).number_format = "$#,##0"
    tcomp.cell(r, 5).value = at_list; tcomp.cell(r, 5).number_format = "$#,##0"
    tcomp.cell(r, 6).value = mult;  tcomp.cell(r, 6).number_format = "0.00x"
    tcomp.cell(r, 8).value = notes; tcomp.cell(r, 8).font = Font(size=8, italic=True, color="444444")
    bg = LIGHT_PURPLE if "Old" in label else YELLOW
    if "AA" in label:
        tcomp.cell(r, 1).fill = PatternFill("solid", fgColor=RED_LIGHT)
    tcomp.row_dimensions[r].height = 18

tcomp.cell(39, 1).value = ("NOTE: Y5 hold values are NOT additive to at-listing earn-out. "
                            "Investors choose to hold OR sell at listing. "
                            "Old-Model base: hold to FY31 = ~$5.69M vs sell at listing = $1.25M (4.5x). "
                            "AA base: hold to FY31 = ~$0.62M vs sell at listing = $1.25M (0.49x) — AA case penalizes holding.")
tcomp.merge_cells("A39:H39")
tcomp.cell(39, 1).font = Font(size=8, bold=True, color="C00000")
tcomp.cell(39, 1).fill = PatternFill("solid", fgColor=RED_LIGHT)
tcomp.cell(39, 1).alignment = Alignment(wrap_text=True)
tcomp.row_dimensions[39].height = 42
tcomp["A27"].font = Font(italic=True, size=9, color="444444")
tcomp.merge_cells("A27:H27")


# ─────────────────────────────────────────────────────────────────────────────
# SHEET 7: Reconciliation — v12 vs Actuals-Anchored
# ─────────────────────────────────────────────────────────────────────────────
rec = wb.create_sheet("Reconciliation")
rec.column_dimensions["A"].width = 36
for col in ["B","C","D","E","F"]:
    rec.column_dimensions[col].width = 14
rec.column_dimensions["G"].width = 44

rec.merge_cells("A1:G1")
rec["A1"] = "RECONCILIATION: v12 Old-Model vs Actuals-Anchored Case"
rec["A1"].font = Font(bold=True, color=WHITE, size=12)
rec["A1"].fill = PatternFill("solid", fgColor=DARK_BLUE)
rec["A1"].alignment = Alignment(horizontal="center")
rec.row_dimensions[1].height = 22

rec["A2"] = ("Explains why Old-Model (v12) projections are higher than the Actuals-Anchored case. "
             "Primary drivers: (1) SSLC FY26 actual $1.925M and FY27 Q1 $713K far below v12 Y1 $4.12M; "
             "(2) unit ramp and ASP escalation not in actuals-anchored; "
             "(3) Exos standalone in actuals-anchored used commission-only v15 baseline, not v12 BLK4/propulsion ramp.")
rec["A2"].font = Font(italic=True, size=9, color="444444")
rec.merge_cells("A2:G2")
rec.row_dimensions[2].height = 52
rec["A2"].alignment = Alignment(wrap_text=True)

for col, txt in [(1,"Line Item"),(2,"FY27 (Y1)"),(3,"FY28 (Y2)"),(4,"FY29 (Y3)"),(5,"FY30 (Y4)"),(6,"FY31 (Y5)"),(7,"Reconciliation Reason")]:
    c = rec.cell(row=4, column=col, value=txt)
    c.font = Font(bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=DARK_BLUE)
    c.alignment = Alignment(horizontal="center", wrap_text=True)
rec.row_dimensions[4].height = 22

# SSLC Revenue section
rec.merge_cells("A5:G5")
rec["A5"] = "SSLC REVENUE"
rec["A5"].fill = PatternFill("solid", fgColor=LIGHT_BLUE)
rec["A5"].font = Font(bold=True, size=9)
rec.row_dimensions[5].height = 16

sslc_recon = [
    (6,  "v12 SSLC/Scorpius revenue",
         4120000, 8680000, 19220000, 33880000, 54690000,
         "v12 uses tank unit ramp (1.5→9/month) × ASP ($183K Y1, +50% Y2, +25%/yr Y3-5). "
         "14 tanks/month × $536K Y5 ASP drives $54.7M."),
    (7,  "Actuals-Anchored SSLC revenue",
         5500000, 7500000, 10000000, 13000000, 16500000,
         "Anchored to Q1 actual $713K + distribution of Markus-confirmed $5M IM ramp. "
         "FY28+ is conservative management assumption without unit-ramp escalation."),
    (8,  "Δ (v12 − AA)",
         "=B6-B7","=C6-C7","=D6-D7","=E6-E7","=F6-F7",
         "v12 exceeds AA by $8.7M at Y5 → driven entirely by ASP escalation + unit ramp not reflected in actuals."),
    (9,  "v12 Scorpius Y1 vs FY26 actual ($1.925M)",
         "gap", None, None, None, None,
         "SSLC FY26 actual revenue was only $1.925M (all programs) vs v12 Y1 SSLC-only $4.12M. "
         "FY27 Q1 was $713K ($2.85M annualized) vs v12 Y1 $4.12M. "
         "Gap = unit ramp hadn't started at model build date."),
]
for r, lbl, y1, y2, y3, y4, y5, reason in sslc_recon:
    rec.cell(r, 1).value = lbl
    rec.cell(r, 1).font = Font(size=10)
    rec.cell(r, 7).value = reason
    rec.cell(r, 7).font = Font(size=9, italic=True, color="444444")
    rec.cell(r, 7).alignment = Alignment(wrap_text=True)
    for col, val in [(2,y1),(3,y2),(4,y3),(5,y4),(6,y5)]:
        if val is None or val == "gap":
            rec.cell(r, col).value = val
            rec.cell(r, col).font = Font(size=9, italic=True)
        else:
            rec.cell(r, col).value = val
            rec.cell(r, col).number_format = "$#,##0;($#,##0)"
    if lbl.startswith("Δ"):
        for col in range(1, 8):
            rec.cell(r, col).fill = PatternFill("solid", fgColor=ORANGE)
    rec.row_dimensions[r].height = 28

# Total Revenue section
rec.merge_cells("A11:G11")
rec["A11"] = "TOTAL CONSOLIDATED REVENUE"
rec["A11"].fill = PatternFill("solid", fgColor=LIGHT_BLUE)
rec["A11"].font = Font(bold=True, size=9)
rec.row_dimensions[11].height = 16

total_recon = [
    (12, "v12 total revenue",       8880000, 21350000, 48590000, 95920000, 179190000,
         "v12 consolidates all revenue lines: BLK4, propulsion/wet-lease, Scorpius tanks, Sarge."),
    (13, "AA total revenue",
         "='PL and Cash Flow'!B40","='PL and Cash Flow'!C40","='PL and Cash Flow'!D40",
         "='PL and Cash Flow'!E40","='PL and Cash Flow'!F40",
         "AA: Exos v15 standalone ($2.6M→$16M) + SSLC actuals-anchored ($5.5M→$16.5M) − interco."),
    (14, "Δ (v12 − AA)",
         "=B12-B13","=C12-C13","=D12-D13","=E12-E13","=F12-F13",
         "Two main drivers: (a) v12 Exos standalone includes BLK4 revenue ramp absent from v15; "
         "(b) v12 Scorpius ASP/unit escalation vs actuals-anchored flat-ish growth."),
    (15, "Exos standalone v12 vs v15",
         "=Assumptions!B86-Assumptions!B57",
         "=Assumptions!B87-Assumptions!B58",
         "=Assumptions!B88-Assumptions!B59",
         "=Assumptions!B89-Assumptions!B60",
         "=Assumptions!B90-Assumptions!B61",
         "v12 Exos standalone uses BLK4 launch/wet-lease/propulsion ramp. "
         "v15 (commission-only) = entX + TACFI + other only; no BLK4 commercial revenue."),
]
for r, lbl, y1, y2, y3, y4, y5, reason in total_recon:
    rec.cell(r, 1).value = lbl; rec.cell(r, 1).font = Font(size=10)
    rec.cell(r, 7).value = reason
    rec.cell(r, 7).font = Font(size=9, italic=True, color="444444")
    rec.cell(r, 7).alignment = Alignment(wrap_text=True)
    for col, val in [(2,y1),(3,y2),(4,y3),(5,y4),(6,y5)]:
        rec.cell(r, col).value = val
        rec.cell(r, col).number_format = "$#,##0;($#,##0)"
    if lbl.startswith("Δ"):
        for col in range(1, 7):
            rec.cell(r, col).fill = PatternFill("solid", fgColor=ORANGE)
    rec.row_dimensions[r].height = 28

# EBITDA section
rec.merge_cells("A17:G17")
rec["A17"] = "EBITDA"
rec["A17"].fill = PatternFill("solid", fgColor=LIGHT_BLUE)
rec["A17"].font = Font(bold=True, size=9)
rec.row_dimensions[17].height = 16

ebitda_recon = [
    (18, "v12 total EBITDA",         1120000, 4120000, 17240000, 42160000, 101610000,
         "v12 Y1 EBITDA positive ($1.12M) despite ramp — Scorpius tanks are high-margin at 65% GP. "
         "Y5 $101.6M driven by Scorpius scale + BLK4 operational leverage."),
    (19, "AA total EBITDA",
         "='PL and Cash Flow'!B45","='PL and Cash Flow'!C45","='PL and Cash Flow'!D45",
         "='PL and Cash Flow'!E45","='PL and Cash Flow'!F45",
         "AA Y1 negative: Exos standalone EBITDA −$4M (pre-BLK3 investment) offsets SSLC $1.24M. "
         "AA Y5 lower: no BLK4 commercial ramp, lower Scorpius scale."),
    (20, "Δ (v12 − AA)",
         "=B18-B19","=C18-C19","=D18-D19","=E18-E19","=F18-F19",
         "Divergence widened by Y5 because v12 Exos standalone (BLK4/propulsion) vastly exceeds v15 baseline "
         "AND v12 Scorpius COGS drops to 30% vs AA constant 52%."),
]
for r, lbl, y1, y2, y3, y4, y5, reason in ebitda_recon:
    rec.cell(r, 1).value = lbl; rec.cell(r, 1).font = Font(size=10)
    rec.cell(r, 7).value = reason
    rec.cell(r, 7).font = Font(size=9, italic=True, color="444444")
    rec.cell(r, 7).alignment = Alignment(wrap_text=True)
    for col, val in [(2,y1),(3,y2),(4,y3),(5,y4),(6,y5)]:
        rec.cell(r, col).value = val
        rec.cell(r, col).number_format = "$#,##0;($#,##0)"
    if lbl.startswith("Δ"):
        for col in range(1, 7):
            rec.cell(r, col).fill = PatternFill("solid", fgColor=ORANGE)
    rec.row_dimensions[r].height = 36

# SSLC FY27 inconsistency fix note
rec.merge_cells("A22:G22")
rec["A22"] = ("FY27 SSLC INCONSISTENCY FIX (10/7): "
              "Prior annual P&L formula = FY26 actual ($1.925M) + IM tanks ($5M) = $6.925M. "
              "Corrected to $5.5M (quarterly total: Q1 actual $713K + Q2-Q4 distributing $5M firm IM ramp). "
              "The formula mixed a completed-year revenue figure with a forward booking — not additive.")
rec["A22"].font = Font(bold=True, size=9, color="C00000")
rec["A22"].fill = PatternFill("solid", fgColor=RED_LIGHT)
rec["A22"].alignment = Alignment(wrap_text=True)
rec.row_dimensions[22].height = 52

# v15 understatement box
rec.merge_cells("A24:G24")
rec["A24"] = ("v15 BENCHMARK UNDERSTATEMENT: v15 'Scorpius acquisition benchmark' $0.9M→$21M over 5 years. "
              "v12's own Scorpius/SSLC line is $4.1M Y1→$54.7M Y5 (13× v15 at Y5). "
              "Actuals-Anchored SSLC is $5.5M Y1→$16.5M Y5 (also exceeds v15 by 6×-8×). "
              "Do NOT edit v15 — it is a pre-IM-tank confirmation legacy model.")
rec["A24"].font = Font(bold=True, size=9, color="C00000")
rec["A24"].fill = PatternFill("solid", fgColor=RED_LIGHT)
rec["A24"].alignment = Alignment(wrap_text=True)
rec.row_dimensions[24].height = 52


# ── Save ──────────────────────────────────────────────────────────────────────
wb.save(OUT)
print(f"Saved: {OUT}")
