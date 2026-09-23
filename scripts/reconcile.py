#!/usr/bin/env python3
"""reconcile.py — receiving reconciliation / "3-way" view: for each open QuickBooks PO, show what was
ORDERED (QB), what we've RECEIVED (MC receiving ledger), and BILLED / candidate Bills (QB AP).

Exos Bills aren't created from POs in QB (no LinkedTxn), so true auto-match isn't possible; we show
received-vs-ordered and suggest Bills from the same vendor near the amount as manual-match candidates.
Prints JSON.
"""
import json, os, subprocess, sys

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIVING = os.path.join(WS, "mission-control", "data", "receiving.json")


def run(script):
    try:
        r = subprocess.run(["/usr/bin/python3", os.path.join(WS, "scripts", script)],
                           capture_output=True, text=True, timeout=40)
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}


def main():
    pos = run("qb_pos.py").get("pos", [])
    bills = run("qb_bills.py")
    by_po_id = bills.get("by_po_id", {})
    by_vendor = bills.get("by_vendor", {})
    try:
        receipts = json.load(open(RECEIVING)).get("receipts", [])
    except Exception:
        receipts = []
    # received cost + lines per PO number
    recv = {}
    for r in receipts:
        po = str(r.get("po") or "")
        e = recv.setdefault(po, {"lines": 0, "cost": 0.0, "parts": []})
        for l in (r.get("lines") or []):
            e["lines"] += 1
            e["cost"] += float(l.get("qty") or 0) * float(l.get("unit_cost") or 0)
            e["parts"].append(l.get("vendor_pn") or l.get("mfg_pn") or l.get("desc") or "")
    out = []
    for p in pos:
        po = str(p.get("po") or "")
        ordered = float(p.get("total") or 0)
        r = recv.get(po, {"lines": 0, "cost": 0.0, "parts": []})
        linked = by_po_id.get(str(p.get("id")), {})
        billed = linked.get("billed")
        # candidate bills: same vendor, total within 20% of ordered
        cands = []
        for b in by_vendor.get(p.get("vendor", ""), []):
            if ordered and abs(b["total"] - ordered) <= max(5.0, 0.20 * ordered):
                cands.append(b)
        if r["lines"] == 0:
            status = "Open — nothing received"
        elif billed or cands:
            status = "Received · bill in QB"
        else:
            status = "Received · not yet billed"
        out.append({"po": po, "vendor": p.get("vendor"), "date": p.get("date"), "ordered": round(ordered, 2),
                    "received_lines": r["lines"], "received_cost": round(r["cost"], 2), "received_parts": r["parts"][:8],
                    "billed": billed, "candidate_bills": cands[:3], "status": status})
    # POs with receipts first, then by date desc
    out.sort(key=lambda x: (x["received_lines"] == 0, x["date"] or ""), reverse=False)
    print(json.dumps({"count": len(out), "pos": out}))


if __name__ == "__main__":
    main()
