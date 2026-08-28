# -*- coding: utf-8 -*-
"""
qb_deposit_sync.py — keep the $800K build-capital tracker current from ACTUAL QuickBooks bank
deposits. Reads Deposit entities (each line = money into the bank), classifies each line to a
build-capital lane by payer + memo, and:
  - CONFIDENT match -> credit that lane (accumulated in the ledger; tracker net-to-build updated)
  - AMBIGUOUS      -> flag to a pending-review list; NEVER silently booked
Deterministic, rule-based (no model in the money path). Idempotent: each deposit line is keyed by
"<DepositId>:<lineIndex>" and never counted twice.

Lanes (match Exos_BuildCapital_800K_Tracker.xlsx rows 6-9, net-to-build column E):
  payload  = new payload-sales bookings (UTD/Lizi)     -> E6
  sbir_nasa= SBIR / NASA grants for work                -> E7
  po10     = Reg D 504 investor subscriptions           -> E8
  usaf     = USAF contract (Karmen/Hermes/FA9300)       -> E9

Run:  python3 scripts/qb_deposit_sync.py [--dry] [--since 2026-07-01]
"""
import os, sys, re, json, datetime

WS = os.path.expanduser("~/.openclaw/workspace")
sys.path.insert(0, os.path.join(WS, "scripts"))
LEDGER = os.path.join(WS, "mission-control", "data", "build_capital_deposits.json")
TRACKER = os.path.join(WS, "drafts", "Exos_BuildCapital_800K_Tracker.xlsx")
BRIDGE = os.path.join(WS, "mission-control", "data", "capital_bridge_ledger.json")
DRY = "--dry" in sys.argv
def _arg(flag, default):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default
SINCE = _arg("--since", "2026-07-01")

# ---- classification signals -------------------------------------------------
USAF_CONTRACT = re.compile(r"\bkarmen\b|\bhermes\b|FA9300|HVRR|RDRE\s*(contract|flight)", re.I)
GOV_GRANT = re.compile(r"\bNASA\b|\bUSAF\b|air\s?force|\bAFRL\b|\bSBIR\b|\bSTTR\b|\bDoD\b|DFAS|"
                       r"treasury|space\s?force|spacewerx|\bONR\b|\bMDA\b|flight\s+opportunit", re.I)
INVESTOR = re.compile(r"\b504\b|reg\.?\s?d\b|subscription|\bSAFE\b|convertible|investor|equity\s+invest|"
                      r"capital\s+contribution|PO10|unit\s+purchase|stock\s+purchase", re.I)
# Deposit posted to an equity account = investor money (504). Strongest, most reliable PO10 signal.
EQUITY_ACCT = re.compile(r"capital\s*stock|common\s*stock|preferred\s*stock|paid.?in\s*capital|additional\s+paid", re.I)
INTEREST = re.compile(r"interest\s+(payment|income)|\bdividend\b", re.I)
PAYLOAD = re.compile(r"payload|\bBLK3\b|flight\s?2|\bbay\b|manifest|\bslot\b|suborbital|entX|ent-?x|"
                     r"microgravity|rideshare|cubesat|1U|2U|SARGE", re.I)

def load_known_investors():
    names = set()
    try:
        d = json.load(open(BRIDGE))
        for r in (d.get("receipts") or d.get("entries") or []):
            n = (r.get("investor") or r.get("name") or "").strip().lower()
            if n and len(n) > 2: names.add(n)
    except Exception:
        pass
    return names

def classify(payer, memo, investors):
    blob = f"{payer} {memo}".strip()
    low = blob.lower()
    if INTEREST.search(blob):                                        return None, "interest/dividend — not a build lane"
    if USAF_CONTRACT.search(blob):                                   return "usaf", "USAF contract signal"
    if EQUITY_ACCT.search(payer):                                    return "po10", "posted to equity account (504 investor)"
    if any(n in low for n in investors) or INVESTOR.search(blob):    return "po10", "investor / 504 signal"
    if GOV_GRANT.search(blob):                                       return "sbir_nasa", "gov/grant signal"
    if PAYLOAD.search(blob):                                         return "payload", "payload signal"
    return None, "no clear signal"

# ---- QB pull ----------------------------------------------------------------
def fetch_deposit_lines(since):
    import qb_client as qb
    access, realm, env = qb.get_access_token()
    lines = []
    start = 1
    while True:
        qr = qb.query(f"SELECT * FROM Deposit WHERE TxnDate >= '{since}' STARTPOSITION {start} MAXRESULTS 1000",
                      access, realm, env)
        rows = qr.get("Deposit", [])
        for d in rows:
            did = d.get("Id"); dt = d.get("TxnDate"); note = d.get("PrivateNote") or ""
            for i, ln in enumerate(d.get("Line", []) or []):
                det = ln.get("DepositLineDetail") or {}
                ent = (det.get("Entity") or {})
                payer = ent.get("name") or (det.get("AccountRef") or {}).get("name") or ""
                memo = ln.get("Description") or note
                amt = float(ln.get("Amount", 0) or 0)
                if amt <= 0:
                    continue
                lines.append({"key": f"{did}:{i}", "date": dt, "payer": payer, "memo": memo, "amount": amt})
        if len(rows) < 1000:
            break
        start += 1000
    return lines

def main():
    led = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {
        "seen": {}, "lanes": {"payload":0,"sbir_nasa":0,"po10":0,"usaf":0}, "matched": [], "pending": []}
    investors = load_known_investors()
    try:
        lines = fetch_deposit_lines(SINCE)
    except Exception as e:
        print(f"QB pull failed ({type(e).__name__}): {str(e)[:160]} — no changes made."); return
    new_conf = 0; new_pend = 0
    for L in lines:
        if L["key"] in led["seen"]:
            continue
        lane, why = classify(L["payer"], L["memo"], investors)
        led["seen"][L["key"]] = True
        if lane:
            led["lanes"][lane] = round(led["lanes"][lane] + L["amount"], 2)
            led["matched"].append({**L, "lane": lane, "why": why})
            new_conf += 1
        else:
            led["pending"].append({**L, "why": why})
            new_pend += 1
    led["last_run"] = datetime.datetime.now().isoformat(timespec="seconds")
    led["since"] = SINCE
    print(f"deposit lines pulled since {SINCE}: {len(lines)} | new confident: {new_conf} | new pending: {new_pend}")
    print("lane totals (net-to-build):", {k: f"${v:,.0f}" for k,v in led["lanes"].items()})
    if led["pending"]:
        print(f"PENDING review ({len(led['pending'])}) — flagged, NOT booked:")
        for p in led["pending"][-8:]:
            print(f"   {p['date']}  ${p['amount']:,.0f}  payer='{p['payer'][:30]}'  memo='{p['memo'][:40]}'")
    if DRY:
        print("\n(dry-run — no ledger/tracker writes)"); return
    json.dump(led, open(LEDGER, "w"), indent=2)
    # update tracker net-to-build cells E6..E9
    try:
        import openpyxl
        wb = openpyxl.load_workbook(TRACKER); s = wb.active
        rowmap = {"payload":6, "sbir_nasa":7, "po10":8, "usaf":9}
        today = datetime.date.today().isoformat()
        for lane, r in rowmap.items():
            s.cell(r, 5, round(led["lanes"][lane], 2)).number_format = "#,##0"
            s.cell(r, 7, f"auto-synced {today}")
        wb.save(TRACKER)
        print(f"tracker updated: {TRACKER}")
    except Exception as e:
        print(f"tracker update skipped ({type(e).__name__}: {str(e)[:120]}) — ledger saved.")

if __name__ == "__main__":
    main()
