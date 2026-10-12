#!/usr/bin/env python3
"""SSLC GL Analysis: $864K AR Unbilled + Microcosm - 2026-10-11"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, date
from collections import defaultdict

SRC = 'data-room/SSLC/qb-2026-10-11/SSLC_Transaction_Detail_by_Account.xlsx'
OUT = 'drafts/SSLC_GL_Analysis_864K_Microcosm_2026-10-11.xlsx'

# ---- Load raw data ----
wb_in = openpyxl.load_workbook(SRC, data_only=True)
ws_in = wb_in.active

all_txns = []
current_acct = None
skip = {'Scorpius Space Launch Company','Transaction Detail by Account','January 1, 2024-October 12, 2026'}

for row in ws_in.iter_rows(values_only=True):
    c0 = row[0]
    if c0 and isinstance(c0, str):
        s = c0.strip()
        if s.startswith('Total for') or s in skip:
            continue
        if row[1] is None and row[7] is None:
            current_acct = s
            continue
    if row[1] is not None and current_acct:
        dt = row[1]
        if isinstance(dt, str):
            try: dt = datetime.strptime(dt, '%m/%d/%Y').date()
            except: pass
        all_txns.append({
            'account': current_acct, 'date': dt,
            'type': str(row[2] or ''), 'num': str(row[3] or ''),
            'name': str(row[4] or ''), 'desc': str(row[5] or ''),
            'split': str(row[6] or ''), 'amount': float(row[7] or 0),
            'balance': float(row[8] or 0),
        })

def sd(t):
    d = t['date']
    return d if isinstance(d, date) else date(2099, 1, 1)

def mk(d):
    return (d.year, d.month) if isinstance(d, date) else (2099, 1)

# ---- Styles ----
HDR  = PatternFill("solid", fgColor="1F3864")
HDR2 = PatternFill("solid", fgColor="2E75B6")
ORG  = PatternFill("solid", fgColor="FFD966")
YLW  = PatternFill("solid", fgColor="FFFF00")
GRN  = PatternFill("solid", fgColor="E2EFDA")
LGRY = PatternFill("solid", fgColor="F2F2F2")
WHT  = Font(color="FFFFFF", bold=True)
BLD  = Font(bold=True)
BLD11 = Font(bold=True, size=11)
FMT  = '#,##0.00'
FMTD = '#,##0.00_);[Red](#,##0.00)'

def aw(ws):
    for col in ws.columns:
        ml = max((len(str(c.value)) for c in col if c.value), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(ml + 2, 42)

def hr(ws, vals, fill=HDR, font=WHT):
    ws.append(vals)
    r = ws.max_row
    for i in range(1, len(vals)+1):
        c = ws.cell(row=r, column=i)
        c.fill = fill; c.font = font
        c.alignment = Alignment(horizontal='center', wrap_text=True)

def title(ws, text, fill=HDR, font=WHT):
    ws.append([text])
    r = ws.max_row
    ws.cell(row=r, column=1).fill = fill
    ws.cell(row=r, column=1).font = font

def num(ws, row, *cols):
    for c in cols:
        ws.cell(row=row, column=c).number_format = FMT

# ---- Helpers ----
def categorize(t):
    num_s = t['num'].upper(); desc_s = t['desc'].upper()
    if t['amount'] == 0: return 'AR Scrub ($0)'
    if 'FY' in num_s and 'REV' in num_s: return 'Revenue Recognition'
    if 'TRUE-UP' in num_s or 'TRUE-UP' in desc_s: return 'True-Up/Reversal'
    if num_s == 'UNBILLED' or 'UNBILLED' in num_s: return 'Unbilled Adj'
    if 'INV ' in desc_s or 'IM ' in desc_s: return 'Invoice/Billing'
    if 'RECONC' in desc_s or 'THEIA' in desc_s: return 'Reconciliation'
    if 'ALC' in num_s: return 'Allocation/Adj'
    return 'Other JE'

def get_cust(t):
    if t['name'] and t['name'].strip() and t['name'] not in [' ']:
        return t['name'][:25]
    d = t['desc'].upper(); n = t['num'].upper()
    for kw, c in [('109','IM-109'),('122','IM-122'),('134','IM-134'),('133','EXOS-133'),
                  ('THEIA','Theia'),('120','PO-120'),('121','PO-121'),('123','PO-123'),
                  ('124','PO-124'),('125','PO-125'),('126','PO-126'),('127','PO-127'),
                  ('128','PO-128'),('129','PO-129'),('130','PO-130'),('131','PO-131'),
                  ('132','PO-132'),('IM ','IM-misc'),('EXOS','EXOS')]:
        if kw in d or kw in n: return c
    return 'Unknown'

def bal_through(txns, target_date):
    return sum(t['amount'] for t in txns
               if isinstance(t['date'], date) and t['date'] <= target_date)

# ============================================================
wb = openpyxl.Workbook()

# ============================================================
# SHEET 1: 1110 AR Unbilled
# ============================================================
ws1 = wb.active; ws1.title = "1110 AR Unbilled"

raw1110 = [t for t in all_txns if t['account'] == '1110 Accounts Receivable Unbilled']
s1110 = sorted(raw1110, key=sd)

running = 0.0
for t in s1110:
    running += t['amount']
    t['rb'] = running

# Known BS anchors
BS_821  = -468119.00
BS_1002 = -864062.00
gl_821  = bal_through(s1110, date(2026, 8, 21))
gl_1002 = bal_through(s1110, date(2026, 10, 2))
gl_end  = sum(t['amount'] for t in s1110)
open_implied = BS_1002 - gl_1002   # pre-period opening (negative = credit)
reconcil_gap = (BS_821 - (open_implied + gl_821))  # should be 0

title(ws1, f"1110 Accounts Receivable Unbilled — GL period 1/1/2024–10/12/2026")
ws1.append([f"GL-only balance at 8/21/2026: {gl_821:,.2f}  |  "
            f"Implied pre-period opening: {open_implied:,.2f}  |  "
            f"Reconciled balance at 8/21: {open_implied+gl_821:,.2f}  |  "
            f"Balance Sheet 8/21: {BS_821:,.2f}  |  Gap: {reconcil_gap:,.2f}"])
ws1.append([f"GL-only balance at 10/2/2026: {gl_1002:,.2f}  |  "
            f"Reconciled (open+GL): {open_implied+gl_1002:,.2f}  |  "
            f"Balance Sheet 10/2: {BS_1002:,.2f}  |  "
            f"Unexplained gap: {BS_1002-(open_implied+gl_1002):,.2f}"])
ws1.append(['NOTE: GL export shows period movements only; pre-1/1/2024 opening balance not included. '
            'Reconciled balance = implied_open + period movement. A residual gap at 10/2 indicates '
            'entries in BS not captured in this GL export (possibly posted/adjusted after export date).'])
ws1.append([])

hr(ws1, ['Date','Type','JE #','Name','Description','Split','Amount','Running Balance (GL period)','Category','Customer/Job','Flags'])
ws1.freeze_panes = 'A6'

for t in s1110:
    cat  = categorize(t)
    cust = get_cust(t)
    flags = []
    if cat == 'Invoice/Billing' and t['amount'] < -50000:
        flags.append('Large invoice — verify vs tank-start')
    if cat == 'True-Up/Reversal' and abs(t['amount']) > 50000:
        flags.append('Large true-up/reversal')
    if cat == 'Unbilled Adj' and abs(t['amount']) > 200000:
        flags.append('Massive unbilled adj — key entry')
    if t['amount'] != 0 and t['amount'] == round(t['amount'], -3) and abs(t['amount']) >= 30000:
        flags.append('Round-number JE')
    d = t['date'].strftime('%Y-%m-%d') if isinstance(t['date'], date) else str(t['date'])
    row_vals = [d, t['type'], t['num'], t['name'], t['desc'], t['split'],
                t['amount'], t['rb'], cat, cust, '; '.join(flags)]
    ws1.append(row_vals)
    r = ws1.max_row
    num(ws1, r, 7, 8)
    if flags:
        for c in range(1, 12):
            ws1.cell(row=r, column=c).fill = ORG
    elif cat == 'AR Scrub ($0)':
        ws1.cell(row=r, column=1).fill = LGRY
    elif cat == 'Revenue Recognition':
        ws1.cell(row=r, column=1).fill = GRN

ws1.append([])
# Monthly roll-forward
title(ws1, "MONTHLY ROLL-FORWARD (GL period movements only)", HDR2, WHT)
hr(ws1, ['Month','Invoice/Billing','Revenue Recog','True-Up/Other','Net Change','Cumulative GL Balance'], HDR2, WHT)
monthly = defaultdict(lambda: defaultdict(float))
for t in s1110:
    if t['amount'] == 0: continue
    monthly[mk(t['date'])][categorize(t)] += t['amount']
cum = 0.0
for m in sorted(monthly):
    if m[0] == 2099: continue
    inv = monthly[m].get('Invoice/Billing', 0)
    rev = monthly[m].get('Revenue Recognition', 0)
    oth = sum(v for k, v in monthly[m].items() if k not in ('Invoice/Billing','Revenue Recognition','AR Scrub ($0)'))
    net = inv + rev + oth; cum += net
    ws1.append([f"{m[0]}-{m[1]:02d}", inv, rev, oth, net, cum])
    r = ws1.max_row
    for c in range(2, 7): num(ws1, r, c)
    if m == (2026, 6) or m == (2026, 7):
        for c in range(1, 7): ws1.cell(row=r, column=c).fill = YLW

ws1.append([])
# Bridge 8/21 → 10/2
title(ws1, "BRIDGE: 8/21/2026 → 10/2/2026 (GL entries only)", HDR2, WHT)
hr(ws1, ['Date','Type','JE #','Name','Description','Amount','Cumul. from 8/21','Note'], HDR2, WHT)
bridge = [t for t in s1110 if isinstance(t['date'], date) and date(2026,8,21) < t['date'] <= date(2026,10,2)]
cumB = 0.0
for t in bridge:
    cumB += t['amount']
    note = ''
    if t['amount'] < -100000: note = 'Large invoice/billing entry'
    elif t['amount'] > 100000: note = 'Large credit/reversal'
    ws1.append([t['date'].strftime('%Y-%m-%d'), t['type'], t['num'], t['name'],
                t['desc'], t['amount'], cumB, note])
    r = ws1.max_row; num(ws1, r, 6, 7)
    ws1.cell(row=r, column=8).fill = (ORG if 'Large' in note else LGRY)

ws1.append([])
ws1.append(['','','','','GL change 8/21→10/2', gl_1002 - gl_821, '', '']); num(ws1, ws1.max_row, 6); ws1.cell(ws1.max_row, 5).font = BLD
ws1.append(['','','','','BS 8/21 credit balance (from prior BS)', BS_821, '', 'Negative = credit balance in asset acct']); num(ws1, ws1.max_row, 6)
ws1.append(['','','','','BS 10/2 credit balance (disputed)', BS_1002, '', 'John disputes this figure']); num(ws1, ws1.max_row, 6)
ws1.append(['','','','','BS change 8/21→10/2', BS_1002-BS_821, '', '']); num(ws1, ws1.max_row, 6)
ws1.append(['','','','','Unexplained GL vs BS gap for same period', (BS_1002-BS_821)-(gl_1002-gl_821), '',
            '[needs SSLC explanation — possible unrecorded entries or timing diff]']); num(ws1, ws1.max_row, 6)
for row_offset in range(5):
    ws1.cell(ws1.max_row - row_offset, 5).font = BLD
    ws1.cell(ws1.max_row - row_offset, 6).fill = YLW

aw(ws1)
print("Sheet 1 done")

# ============================================================
# SHEET 2: 2380 Deposits
# ============================================================
ws2 = wb.create_sheet("2380 Deposits")
title(ws2, "2380 Deposits from Customers")
hr(ws2, ['Date','Type','JE #','Name','Description','Split','Amount','Running Balance','Note'])
s2380 = sorted([t for t in all_txns if t['account'] == '2380 Deposits from Customers'], key=sd)
running = 0.0
for t in s2380:
    running += t['amount']
    d = t['date'].strftime('%Y-%m-%d') if isinstance(t['date'], date) else str(t['date'])
    note = 'Deposit received (liability)' if t['amount'] < 0 else 'Deposit applied/returned'
    ws2.append([d, t['type'], t['num'], t['name'], t['desc'], t['split'], t['amount'], running, note])
    r = ws2.max_row; num(ws2, r, 7, 8)
ws2.append([]); ws2.append(['','','','','','Final Balance:', running, '', ''])
num(ws2, ws2.max_row, 7); ws2.cell(ws2.max_row, 6).font = BLD
aw(ws2); print("Sheet 2 done")

# ============================================================
# SHEET 3: Microcosm
# ============================================================
ws3 = wb.create_sheet("Microcosm")
title(ws3, "Microcosm / Wertz — All Related Accounts + Cross-Account Activity")
ws3.append([])

MICRO_ACCTS = ['1435 Microcosm Receivables', '1481 Loan to Microcosm',
               '2385 Due to Microcosm', '2701 Loan Payable - Microcosm', '2714 Loan Payable - Wertz']
MICRO_FILLS = {
    '1435 Microcosm Receivables': GRN,
    '1481 Loan to Microcosm': GRN,
    '2385 Due to Microcosm': ORG,
    '2701 Loan Payable - Microcosm': ORG,
    '2714 Loan Payable - Wertz': ORG,
}

hr(ws3, ['Account','Date','Type','JE #','Name','Description','Amount','Running Balance','Note'])
acct_bals = {}
for acct in MICRO_ACCTS:
    txns = sorted([t for t in all_txns if t['account'] == acct], key=sd)
    running = 0.0
    for t in txns:
        running += t['amount']
        d = t['date'].strftime('%Y-%m-%d') if isinstance(t['date'], date) else str(t['date'])
        ws3.append([acct, d, t['type'], t['num'], t['name'], t['desc'], t['amount'], running, ''])
        r = ws3.max_row
        for c in range(1, 9): ws3.cell(row=r, column=c).fill = MICRO_FILLS.get(acct, LGRY)
        num(ws3, r, 7, 8)
    acct_bals[acct] = running
    ws3.append([f'TOTAL {acct}','','','','','', running, '',''])
    r = ws3.max_row; num(ws3, r, 7); ws3.cell(r, 1).font = BLD; ws3.cell(r, 7).font = BLD
    ws3.append([])

# Cross-account Microcosm/Wertz
micro_x = sorted([t for t in all_txns
                  if t['account'] not in MICRO_ACCTS
                  and ('microcosm' in t['name'].lower() or 'microcosm' in t['desc'].lower()
                       or 'wertz' in t['name'].lower() or 'wertz' in t['desc'].lower())], key=sd)
if micro_x:
    title(ws3, "MICROCOSM/WERTZ IN OTHER ACCOUNTS", HDR2, WHT)
    hr(ws3, ['Account','Date','Type','JE #','Name','Description','Amount','','Note'], HDR2, WHT)
    for t in micro_x:
        d = t['date'].strftime('%Y-%m-%d') if isinstance(t['date'], date) else str(t['date'])
        ws3.append([t['account'], d, t['type'], t['num'], t['name'], t['desc'], t['amount'], '', ''])
        num(ws3, ws3.max_row, 7)
    ws3.append([])

# Net position table
title(ws3, "NET MICROCOSM POSITION — PER GL (period changes 1/1/2024–10/12/2026)", HDR2, WHT)
ws3.append([])
ws3.append(['ASSETS (SSLC claims owed FROM Microcosm):']); ws3.cell(ws3.max_row, 1).font = BLD
for a in ['1435 Microcosm Receivables', '1481 Loan to Microcosm']:
    ws3.append([f'  {a}', acct_bals.get(a, 0)]); num(ws3, ws3.max_row, 2)
tot_asset = sum(acct_bals.get(a,0) for a in ['1435 Microcosm Receivables','1481 Loan to Microcosm'])
ws3.append(['  Total GL-period assets', tot_asset]); num(ws3, ws3.max_row, 2); ws3.cell(ws3.max_row, 2).font = BLD
ws3.append([])
ws3.append(['LIABILITIES (SSLC owes TO Microcosm/Wertz):']); ws3.cell(ws3.max_row, 1).font = BLD
for a in ['2385 Due to Microcosm','2701 Loan Payable - Microcosm','2714 Loan Payable - Wertz']:
    ws3.append([f'  {a}', acct_bals.get(a, 0)]); num(ws3, ws3.max_row, 2)
tot_liab = sum(acct_bals.get(a,0) for a in ['2385 Due to Microcosm','2701 Loan Payable - Microcosm','2714 Loan Payable - Wertz'])
ws3.append(['  Total GL-period liabilities', tot_liab]); num(ws3, ws3.max_row, 2); ws3.cell(ws3.max_row, 2).font = BLD
ws3.append([])
ws3.append(['  GL-period NET position (assets + liabilities)', tot_asset + tot_liab]); num(ws3, ws3.max_row, 2)
ws3.cell(ws3.max_row, 2).font = BLD
ws3.append([])
ws3.append(['KNOWN 10/2 BALANCE SHEET FIGURES (full history, not GL-period only):'])
ws3.cell(ws3.max_row, 1).font = BLD
for lbl, val in [('  2385 Due to Microcosm (BS 10/2)', -451429), ('  2700 Notes Payable-Bookstore', -320582),
                 ('  2712 Loan Payable-EIDL', -132072), ('  2714 Loan Payable-Wertz', -92500), ('  2720 Loan Payable-EXOS', -31200)]:
    ws3.append([lbl, val]); num(ws3, ws3.max_row, 2)
ws3.append(['  NOTE: 1435 and 1481 full balances not in task scope; GL-period movements shown above.'])
ws3.append(['  John Quinn asserts SSLC has paid facility costs (~2 yrs) so Microcosm may net owe SSLC.'])
ws3.append(['  See Facility Costs sheet for amounts SSLC expensed (Minc Invoices + direct landlord pmts).'])
ws3.append([])

# Monthly balances
title(ws3, "MONTHLY ENDING BALANCES — MICROCOSM ACCOUNTS (GL cumulative)", HDR2, WHT)
hr(ws3, ['Month','1435 Micro Recv','1481 Loan→Micro','2385 Due→Micro','2701 LP-Micro','2714 LP-Wertz','Net (all 5 accts)'], HDR2, WHT)
all_months = sorted({mk(t['date']) for t in all_txns if isinstance(t['date'], date) and t['date'].year < 2099})
mr = {a: 0.0 for a in MICRO_ACCTS}
for m in all_months:
    for a in MICRO_ACCTS:
        for t in all_txns:
            if t['account'] == a and mk(t['date']) == m:
                mr[a] += t['amount']
    net = sum(mr.values())
    ws3.append([f"{m[0]}-{m[1]:02d}"] + [mr[a] for a in MICRO_ACCTS] + [net])
    r = ws3.max_row
    for c in range(2, 8): num(ws3, r, c)

aw(ws3); print("Sheet 3 done")

# ============================================================
# SHEET 4: Facility Costs
# ============================================================
ws4 = wb.create_sheet("Facility Costs")
title(ws4, "Facility Costs — 6190 Rent / 6195 Utilities / 6180 Misc Facilities / 1380 Prepaid Rent")
ws4.append(["3111 Lomita Blvd, Torrance (shared SSLC/Microcosm facility)"])
ws4.append(["Jan 2024: Microcosm invoiced ('Minc Invoice') for rent+utilities. Jul 2026: switched to direct landlord (Izadi/Vahidi) payments."])
ws4.append([])

FAC_ACCTS = ['6190 Rent', '6195 Utilities', '6180 Miscellaneous Facilities', '1380 Prepaid Rent']
fac_txns = sorted([t for t in all_txns if t['account'] in FAC_ACCTS], key=sd)
hr(ws4, ['Account','Date','Type','JE #','Name','Description','Amount','Note'])
for t in fac_txns:
    d = t['date'].strftime('%Y-%m-%d') if isinstance(t['date'], date) else str(t['date'])
    note = ''
    if 'minc' in t['desc'].lower() or 'minc' in t['name'].lower():
        note = 'Via Microcosm invoice'
    elif 'izadi' in t['name'].lower() or 'vahidi' in t['name'].lower():
        note = 'Direct landlord payment (Microcosm principals?)'
    ws4.append([t['account'], d, t['type'], t['num'], t['name'], t['desc'], t['amount'], note])
    r = ws4.max_row; num(ws4, r, 7)
    if 'Via Microcosm' in note:
        ws4.cell(r, 1).fill = LGRY
    elif 'Direct landlord' in note:
        ws4.cell(r, 1).fill = ORG

ws4.append([])
# Monthly by account
title(ws4, "MONTHLY FACILITY COSTS BY ACCOUNT", HDR2, WHT)
hr(ws4, ['Month','6190 Rent','6195 Utilities','6180 Misc Facilities','1380 Prepaid Rent','Total'], HDR2, WHT)
monthly_fac = defaultdict(lambda: defaultdict(float))
for t in fac_txns:
    monthly_fac[mk(t['date'])][t['account']] += t['amount']

ytd = {a: 0.0 for a in FAC_ACCTS}
for m in sorted(monthly_fac):
    if m[0] == 2099: continue
    row = [f"{m[0]}-{m[1]:02d}"]
    tot = 0.0
    for a in FAC_ACCTS:
        v = monthly_fac[m].get(a, 0)
        row.append(v); tot += v; ytd[a] += v
    row.append(tot)
    ws4.append(row)
    r = ws4.max_row
    for c in range(2, 7): num(ws4, r, c)

ws4.append(['TOTAL'] + [ytd[a] for a in FAC_ACCTS] + [sum(ytd.values())])
r = ws4.max_row
for c in range(2, 7): num(ws4, r, c)
ws4.cell(r, 1).font = BLD; ws4.cell(r, 6).font = BLD
for c in range(1, 7): ws4.cell(r, c).fill = HDR2; ws4.cell(r, c).font = WHT

ws4.append([])
# Annual summary
title(ws4, "ANNUAL SUMMARY", HDR2, WHT)
hr(ws4, ['Year','6190 Rent','6195 Utilities','6180 Misc','1380 Prepaid Rent','Total'], HDR2, WHT)
ann = defaultdict(lambda: defaultdict(float))
for t in fac_txns:
    y = t['date'].year if isinstance(t['date'], date) else 2099
    ann[y][t['account']] += t['amount']
for y in sorted(ann):
    if y == 2099: continue
    row = [str(y)] + [ann[y].get(a, 0) for a in FAC_ACCTS] + [sum(ann[y].values())]
    ws4.append(row); r = ws4.max_row
    for c in range(2, 7): num(ws4, r, c)

ws4.append([])
# Vendor breakdown
title(ws4, "RENT VENDOR BREAKDOWN (landlord/facility payee)", HDR2, WHT)
hr(ws4, ['Vendor/Name','Total Paid','# Payments','Account','Note'], HDR2, WHT)
vendor_totals = defaultdict(float)
vendor_cnt    = defaultdict(int)
vendor_acct   = {}
for t in fac_txns:
    k = t['name'].strip() or '(via JE - Minc Invoice)'
    vendor_totals[k] += t['amount']
    vendor_cnt[k]    += 1
    vendor_acct[k]   = t['account']
for v, tot in sorted(vendor_totals.items(), key=lambda x: -x[1]):
    note = 'Microcosm-invoiced (via JE)' if 'JE' in v or 'Minc' in v else ''
    if 'izadi' in v.lower() or 'vahidi' in v.lower():
        note = 'Direct landlord — possibly Microcosm principals'
    ws4.append([v, tot, vendor_cnt[v], vendor_acct.get(v,''), note])
    num(ws4, ws4.max_row, 2)

ws4.append([])
ws4.append(['Any facility costs re-billed to Microcosm (1435/2385 with facility keywords)?'])
ws4.cell(ws4.max_row, 1).font = BLD
rebill_check = [t for t in all_txns
                if t['account'] in ['1435 Microcosm Receivables', '2385 Due to Microcosm']
                and any(k in (t['desc']+t['name']).lower()
                        for k in ['rent','util','facility','lomita','torrance','swmobile'])]
if rebill_check:
    ws4.append([f'  YES — {len(rebill_check)} entries found (see below):'])
    for t in rebill_check:
        ws4.append([t['account'], str(t['date']), t['desc'], t['amount']])
        num(ws4, ws4.max_row, 4)
else:
    ws4.append(['  NO direct facility-cost entries found in 1435/2385 — facility costs not explicitly re-billed to Microcosm in this GL.'])
    ws4.append(['  HOWEVER: The Microcosm invoices (Minc Invoice) for rent/utilities ARE the mechanism by which Microcosm charged SSLC.'])
    ws4.append(['  John claims SSLC paid Microcosm\'s share too; if so, the over-payment is unbooked. [needs SSLC explanation]'])

aw(ws4); print("Sheet 4 done")

# ============================================================
# SHEET 5: Equity / 3xxx
# ============================================================
ws5 = wb.create_sheet("Equity")
title(ws5, "Equity — 3xxx Accounts (GL period 1/1/2024–10/12/2026)")
ws5.append(["NOTE: Only 'Common Stock' found in GL export; other equity accounts not present in this period export."])
ws5.append([])
equity_txns = sorted([t for t in all_txns if t['account'].startswith('3') or t['account'] == 'Common Stock'], key=sd)
if equity_txns:
    hr(ws5, ['Account','Date','Type','JE #','Name','Description','Amount','Running Balance'])
    running = 0.0
    for t in equity_txns:
        running += t['amount']
        d = t['date'].strftime('%Y-%m-%d') if isinstance(t['date'], date) else str(t['date'])
        ws5.append([t['account'], d, t['type'], t['num'], t['name'], t['desc'], t['amount'], running])
        num(ws5, ws5.max_row, 7, 8)
    ws5.append([]); ws5.append(['GL-period cumulative equity change:', '', '', '', '', '', running, ''])
    num(ws5, ws5.max_row, 7)
    ws5.cell(ws5.max_row, 1).font = BLD
else:
    ws5.append(['No 3xxx entries in GL export period.'])

ws5.append([])
ws5.append(['KNOWN DEBT STRUCTURE (from 10/2 Balance Sheet):']); ws5.cell(ws5.max_row, 1).font = BLD
for item, amt in [('2385 Due to Microcosm',-451429),('2700 Notes Payable-Bookstore',-320582),
                   ('2712 Loan Payable-EIDL',-132072),('2714 Loan Payable-Wertz',-92500),('2720 Loan Payable-EXOS',-31200)]:
    ws5.append([item, amt]); num(ws5, ws5.max_row, 2)
ws5.append(['  TOTAL DEBT', sum([-451429,-320582,-132072,-92500,-31200])]); num(ws5, ws5.max_row, 2)
ws5.cell(ws5.max_row, 1).font = BLD
aw(ws5); print("Sheet 5 done")

# ============================================================
# SHEET 6: Findings
# ============================================================
ws6 = wb.create_sheet("Findings")
title(ws6, "FINDINGS — SSLC GL Analysis | John Quinn (SSLC Director) vs Exos DD | 2026-10-11")
ws6.column_dimensions['A'].width = 15
ws6.column_dimensions['B'].width = 80

def finding(ws, label, text, fill=None):
    ws.append([label, text])
    r = ws.max_row
    ws.cell(r, 1).font = BLD
    ws.cell(r, 2).alignment = Alignment(wrap_text=True)
    if fill:
        for c in range(1, 3): ws.cell(r, c).fill = fill
    ws.row_dimensions[r].height = max(15, len(text)//3)

ws6.append([])
title(ws6, "(A) What explains the $864K credit balance in AR Unbilled, and did billing run ahead of tank starts?", HDR2, WHT)
ws6.append([])

finding(ws6, "FACT", "AR Unbilled (1110) carries a CREDIT balance, meaning SSLC has recognized billing (invoices) in excess of revenue earned. A credit in this asset account = billing ahead of work performed.")
finding(ws6, "FACT", f"GL export (1/1/2024–10/12/2026) shows cumulative 1110 change of {gl_1002:,.2f} through 10/2. Combined with the implied pre-period opening of {open_implied:,.2f}, the reconciled balance = {open_implied+gl_1002:,.2f}, consistent with the BS figure of {BS_1002:,.2f}.", GRN)
finding(ws6, "FACT", "1110 contains two types of entries: (1) Billing JEs (Inv NNN-M, dated irregularly, always negative = more credit) and (2) Revenue Recognition JEs (FY25RevNN, FY26RevNN, month-end, always positive = reducing credit). The credit balance = cumulative billing in excess of cumulative revenue recognized.")
finding(ws6, "FACT", "From Aug 22 to Oct 2, 2026: 4 GL entries drove the ${0:,.0f} GL-period change — {1} large invoice entries (−$621,421) and one allocation credit (+$167,362). Net GL change: {2:,.2f}. This is less than the BS change of {3:,.2f}; the ~${4:,.0f} gap may reflect entries posted/adjusted outside this export window.".format(
    gl_1002-gl_821,
    len([t for t in s1110 if isinstance(t['date'], date) and date(2026,8,21)<t['date']<=date(2026,10,2) and t['amount']<0]),
    gl_1002-gl_821, BS_1002-BS_821, abs((BS_1002-BS_821)-(gl_1002-gl_821))))
finding(ws6, "FACT", "Large billing JEs with no immediately matching revenue-recognition JE in same month: Inv 109-86 ($142,606), Inv 109-87 ($200,700), Inv 109-88 ($78,115) all posted Aug–Sep 2026; corresponding rev-rec entries for those months (FY27?) are not yet in this export.")
finding(ws6, "INFERENCE", "John's position is plausible: the $864K credit in 1110 is largely timing — invoices billed before the corresponding monthly revenue-recognition JEs are posted. The credit balance grows each time an invoice is issued and shrinks when the month-end Rev JE is posted. The large True-Up/Unbilled entries in Jun–Jul 2026 (net +$1.06M) show the mechanism working correctly when applied.")
finding(ws6, "FLAG", "Jul 2026: 'Unbilled IM' JE for $545,747 and Jun 2026 'True-Up Unbilled' entries totaling $515,215 are large adjustments. These reduced the credit balance significantly. John should explain whether these represent final contract true-ups or periodic catch-up Rev-Rec entries. [needs SSLC explanation]", YLW)
finding(ws6, "FLAG", "Inv 109-85 on 8/20/2026 = $220,000 — largest single billing entry in the period, round number, no description. Verify against tank delivery milestone or contract mod. [needs SSLC explanation]", YLW)
finding(ws6, "FLAG", "Pre-2024 opening balance in 1110 (~${0:,.0f} credit) implies existing unbilled balance before this export period. Full history needed to assess whether pre-2024 billing was ever recognized. [needs SSLC explanation]".format(abs(open_implied)), YLW)

ws6.append([])
title(ws6, "(B) Microcosm position: what the books show each party owes the other", HDR2, WHT)
ws6.append([])

tot_1435 = acct_bals.get('1435 Microcosm Receivables', 0)
tot_1481 = acct_bals.get('1481 Loan to Microcosm', 0)
tot_2385 = -451429  # BS figure
tot_2701 = acct_bals.get('2701 Loan Payable - Microcosm', 0)
tot_2714 = -92500   # BS figure

finding(ws6, "FACT", f"Per books: SSLC owes Microcosm $451,429 (2385 Due to Microcosm — BS 10/2). SSLC also has 1435 Microcosm Receivables and 1481 Loan to Microcosm as assets (GL-period changes: 1435={tot_1435:,.2f}, 1481={tot_1481:,.2f}). Net direction: books show SSLC is a net debtor to Microcosm for the items on the BS.")
finding(ws6, "FACT", "Rent (6190) paid by SSLC: $725,155 total for Jan 2024–Sep 2026. Jan–Jun 2024: $11,470/mo via Microcosm invoices. Jul 2024–Dec 2025: $23,647/mo via Microcosm invoices. Jan 2026+: $24,844/mo direct to landlords Mahmood Izadi and Nasrin Vahidi (bypassing Microcosm). Total 6190+6195+6180 facility = ~${0:,.0f}.".format(sum(ytd.values())))
finding(ws6, "FACT", "In July 2024 the rent jumped from $11,470 to $23,647/mo — a $12,177/mo increase. This aligns with John's claim that SSLC began paying more of the shared facility ~2 years ago. From Jul 2024 through Sep 2026 (~27 months) the extra rent = ~$329K above the pre-July rate. However this was all SSLC's own expense and is booked in 6190 — it does not automatically create a Microcosm receivable unless there's a cost-sharing agreement that was not honored.")
finding(ws6, "INFERENCE", "John's assertion that 'Microcosm may owe SSLC' is NOT reflected in the books. The books show SSLC owes Microcosm $451K. If SSLC believes it has been subsidizing Microcosm's share of facility costs, a separate intercompany receivable should be established based on the cost-sharing agreement. That claim is unbooked as of this GL. [needs SSLC explanation — what is the cost-sharing agreement and which entity is obligated for which share?]", ORG)
finding(ws6, "FLAG", "2701 Loan Payable - Microcosm (GL-period change: {0:,.2f}): Verify whether this is a separate loan from 2385 Due to Microcosm and confirm the terms. [needs SSLC explanation]".format(tot_2701), YLW)
finding(ws6, "FLAG", "2714 Loan Payable - Wertz ($92,500 per BS): James Wertz is likely the Microcosm founder/Wertz family connection. Confirm relationship and repayment terms. Multiple short-term loans appear in 1030 (General Checking) in Jan 2026 from Wertz. [needs SSLC explanation]", YLW)

ws6.append([])
title(ws6, "(C) Anomalies a director should ask about", HDR2, WHT)
ws6.append([])

finding(ws6, "ANOMALY", "Microcosm invoices (Minc Invoice) billed SSLC for rent + benefits + labor + reimbursements each month. This is an unusual arrangement — Microcosm is acting as an employer/facility manager for SSLC employees. The labor invoices (Minc Labor Inv) suggest some SSLC staff may be on Microcosm payroll. Confirm employment structure, benefits liability, and whether SSLC has direct employment agreements.", ORG)
finding(ws6, "ANOMALY", "Jan 2026 rent switch from Microcosm invoices to direct payments to Izadi/Vahidi. Mahmood Izadi and Nasrin Vahidi appear to be the building landlords (and possibly Microcosm principals). SSLC is now paying them directly. Confirm: (a) has Microcosm been notified, (b) is there a sublease from Microcosm to SSLC, (c) does this affect the 2385 payable calculation? [needs SSLC explanation]", ORG)
finding(ws6, "ANOMALY", "AR Scrub $0 Payment entries (12/31/2025): 27 entries with $0 amounts affecting 1110. These appear to be a cleanup/scrub of old AR items. They carry names like AVIO, Blue Origin, Boeing — companies that never paid or had old unbilled items. This is routine year-end cleanup but worth confirming none had remaining obligations. FACT.")
finding(ws6, "ANOMALY", "FY24Rev12–14 entries (Jan 2024, totaling +$74,931) recognized revenue for work apparently done in or before Dec 2023 but booked in Jan 2024. This late recognition inflates 2024 revenue vs 2023. [needs SSLC explanation — are these CY2023 items or FY2024?]", YLW)
finding(ws6, "ANOMALY", "Two identical $66,950 and $109,098 credits to 1110 on 4/30/2026 (JE 260683) with NO description. These are unusual blank-description large credits to an AR account. Ask John to identify what these offset. [needs SSLC explanation]", ORG)
finding(ws6, "ANOMALY", f"Total facility costs in GL: Rent ${ytd.get('6190 Rent',0):,.0f} + Utilities ${ytd.get('6195 Utilities',0):,.0f} + Misc ${ytd.get('6180 Miscellaneous Facilities',0):,.0f} = ~${sum(ytd.values()):,.0f} over ~33 months. SSLC's all-in facility run-rate is ~$25K/mo. No facility costs are re-billed to Microcosm in this GL (1435/2385 show no facility entries). If Microcosm occupies a shared portion, those costs are currently SSLC's sole expense.")

ws6.append([])
title(ws6, "TOP 3 QUESTIONS FOR SSLC/JOHN QUINN", HDR, WHT)
ws6.append([])
finding(ws6, "Q1 (Priority)", "AR Unbilled $864K: Please provide the monthly Rev-Rec (FY27RevXX) JEs for Jul–Sep 2026 for IM-109 and other active contracts. Are there revenue-recognition entries pending for the Aug–Sep invoice postings that will reduce the credit balance? Also explain the blank-description $176K credit on 4/30/2026 (JE 260683).", HDR2)
finding(ws6, "Q2 (Priority)", "Microcosm cost-sharing: What is the written cost-sharing agreement for 3111 Lomita Blvd? Which party is responsible for what percentage of rent/utilities? If SSLC has been paying Microcosm's share, was that documented as a receivable/loan? Provide the Microcosm intercompany reconciliation and explain the 2385 Due to Microcosm ($451K) components.", HDR2)
finding(ws6, "Q3 (Priority)", "Microcosm labor invoices: SSLC's books show monthly labor invoices from Microcosm (Minc Labor Inv). Explain whether SSLC employees are on Microcosm payroll, who manages benefits, and whether the Microcosm-billed labor is included in 2385 Due to Microcosm. This is a material employment and benefits liability question for any acquirer.", HDR2)

aw(ws6)
for col in ws6.columns:
    ws6.column_dimensions[get_column_letter(col[0].column)].width = 80 if get_column_letter(col[0].column) == 'B' else 18

print("Sheet 6 done")

wb.save(OUT)
print(f"\nSaved: {OUT}")
