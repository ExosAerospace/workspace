#!/usr/bin/env python3
"""receiving_apply.py — apply a Receiving record (parts received against a QuickBooks PO).

Reads a receipt JSON on stdin:
  { "po": "596", "vendor": "...", "received_by": "Steve", "lines": [
      {"vendor_pn","mfg_pn","item","section","desc","qty","unit_cost","location"} , ... ] }
For each line it runs `inventory_capture.py receive` (on-hand + location + unit cost + PO#), then
appends the receipt to mission-control/data/receiving.json (the receiving ledger). Prints a summary.
"""
import json, os, sys, subprocess, datetime

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IC = os.path.join(WS, "scripts", "inventory_capture.py")
LEDGER = os.path.join(WS, "mission-control", "data", "receiving.json")


def main():
    try:
        rc = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"error": f"bad json: {e}"})); return
    lines = rc.get("lines") or []
    if not lines:
        print(json.dumps({"error": "no lines"})); return
    applied = 0
    for ln in lines:
        args = ["/usr/bin/python3", IC, "receive",
                "--qty", str(ln.get("qty") or 1),
                "--by", rc.get("received_by") or "team",
                "--po", str(rc.get("po") or "")]
        for k, flag in [("vendor_pn", "--vendor-pn"), ("mfg_pn", "--mfg-pn"), ("item", "--item"),
                        ("section", "--section"), ("desc", "--desc"), ("unit_cost", "--unit-cost"),
                        ("location", "--location")]:
            v = ln.get(k)
            if v not in (None, ""):
                args += [flag, str(v)]
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                applied += 1
        except Exception:
            pass
    # append to the receiving ledger
    try:
        ledger = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {"receipts": []}
    except Exception:
        ledger = {"receipts": []}
    receipt = {"id": datetime.datetime.utcnow().strftime("rcv_%Y%m%d%H%M%S%f"),
               "po": rc.get("po"), "vendor": rc.get("vendor"), "received_by": rc.get("received_by"),
               "received_at": datetime.datetime.utcnow().isoformat() + "Z",
               "task": rc.get("task"), "lines": lines,
               "total_cost": round(sum((float(l.get("qty") or 0) * float(l.get("unit_cost") or 0)) for l in lines), 2)}
    ledger["receipts"] = (ledger.get("receipts") or []) + [receipt]
    tmp = LEDGER + ".tmp"; json.dump(ledger, open(tmp, "w"), indent=2); os.replace(tmp, LEDGER)
    print(json.dumps({"ok": True, "applied": applied, "lines": len(lines), "receipt_id": receipt["id"],
                      "total_cost": receipt["total_cost"]}))


if __name__ == "__main__":
    main()
