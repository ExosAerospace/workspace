#!/usr/bin/env python3
"""qb_pos.py — pull open Purchase Orders from QuickBooks (the PO system of record) for the MC
Receiving module. Prints JSON. Caches to mission-control/data/qb-pos-cache.json (5 min) so the
Receiving page doesn't hammer the QB API. Use --refresh to force a live pull.
"""
import json, os, sys, time

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(WS, "mission-control", "data", "qb-pos-cache.json")
TTL = 300


def fetch():
    sys.path.insert(0, os.path.join(WS, "scripts"))
    import qb_client
    rows, start = [], 1
    while start <= 500:   # cap at 500 most-recent POs
        r = qb_client.query(f"SELECT * FROM PurchaseOrder ORDER BY MetaData.LastUpdatedTime DESC "
                            f"STARTPOSITION {start} MAXRESULTS 100")
        pos = r.get("PurchaseOrder", [])
        rows += pos
        if len(pos) < 100:
            break
        start += 100
    rows = [p for p in rows if (p.get("POStatus") or "").lower() == "open"]   # filter Open in Python
    out = []
    for p in rows:
        lines = []
        for l in p.get("Line", []):
            d = l.get("ItemBasedExpenseLineDetail") or l.get("AccountBasedExpenseLineDetail") or {}
            ref = d.get("ItemRef") or d.get("AccountRef") or {}
            if not l.get("Amount") and not ref.get("name"):
                continue
            lines.append({"category": ref.get("name", ""), "description": l.get("Description", ""),
                          "qty": d.get("Qty"), "rate": d.get("UnitPrice"), "amount": l.get("Amount")})
        out.append({"id": p.get("Id"), "po": p.get("DocNumber"), "date": p.get("TxnDate"),
                    "vendor": (p.get("VendorRef") or {}).get("name", ""), "status": p.get("POStatus"),
                    "total": p.get("TotalAmt"), "memo": p.get("Memo", ""), "lines": lines})
    return {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "count": len(out), "pos": out}


def main():
    refresh = "--refresh" in sys.argv
    if not refresh and os.path.exists(CACHE) and (time.time() - os.path.getmtime(CACHE)) < TTL:
        print(open(CACHE).read()); return
    try:
        data = fetch()
        tmp = CACHE + ".tmp"; json.dump(data, open(tmp, "w")); os.replace(tmp, CACHE)
        print(json.dumps(data))
    except Exception as e:
        # fall back to stale cache if the live pull fails, else surface the error
        if os.path.exists(CACHE):
            print(open(CACHE).read())
        else:
            print(json.dumps({"error": str(e), "pos": []}))


if __name__ == "__main__":
    main()
