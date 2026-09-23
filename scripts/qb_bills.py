#!/usr/bin/env python3
"""qb_bills.py — pull recent Bills (AP invoices) from QuickBooks and index the amount billed against
each Purchase Order (via the Bill line LinkedTxn -> PurchaseOrder). Feeds the 3-way match
(PO ordered vs received vs billed). Prints JSON, 5-min cache.
"""
import json, os, sys, time

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(WS, "mission-control", "data", "qb-bills-cache.json")
TTL = 300


def fetch():
    sys.path.insert(0, os.path.join(WS, "scripts"))
    import qb_client
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=400)).isoformat()
    rows, start = [], 1
    while start <= 1000:
        r = qb_client.query(f"SELECT * FROM Bill WHERE TxnDate >= '{since}' "
                            f"ORDER BY TxnDate DESC STARTPOSITION {start} MAXRESULTS 100")
        b = r.get("Bill", [])
        rows += b
        if len(b) < 100:
            break
        start += 100
    # index billed amount per linked PO id (works IF bills are created from POs) + per vendor
    # (candidate matching, since Exos bills aren't PO-linked in QB).
    by_po, by_vendor = {}, {}
    for bill in rows:
        docn = bill.get("DocNumber", "")
        vend = (bill.get("VendorRef") or {}).get("name", "")
        dt = bill.get("TxnDate", "")
        total = float(bill.get("TotalAmt") or 0)
        by_vendor.setdefault(vend, []).append({"bill": docn, "date": dt, "total": round(total, 2)})
        for l in bill.get("Line", []):
            amt = l.get("Amount") or 0
            for lt in (l.get("LinkedTxn") or []):
                if (lt.get("TxnType") or "") == "PurchaseOrder":
                    pid = str(lt.get("TxnId"))
                    e = by_po.setdefault(pid, {"billed": 0.0, "bills": [], "vendor": vend})
                    e["billed"] = round(e["billed"] + float(amt), 2)
                    if docn and docn not in e["bills"]:
                        e["bills"].append(docn)
                    if dt:
                        e["last_bill_date"] = dt
    return {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "by_po_id": by_po,
            "by_vendor": by_vendor, "bill_count": len(rows)}


def main():
    if "--refresh" not in sys.argv and os.path.exists(CACHE) and (time.time() - os.path.getmtime(CACHE)) < TTL:
        print(open(CACHE).read()); return
    try:
        data = fetch()
        tmp = CACHE + ".tmp"; json.dump(data, open(tmp, "w")); os.replace(tmp, CACHE)
        print(json.dumps(data))
    except Exception as e:
        if os.path.exists(CACHE):
            print(open(CACHE).read())
        else:
            print(json.dumps({"error": str(e), "by_po_id": {}}))


if __name__ == "__main__":
    main()
