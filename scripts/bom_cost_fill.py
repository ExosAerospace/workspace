#!/usr/bin/env python3
"""bom_cost_fill.py — fill + provenance every BLK3 BOM line cost.

Separates cost SOURCES so the board can show what was PAID vs what we FOUND:
  basis = "paid"      → actual $ paid (QuickBooks PO/Bill, receiving, Scorpius QB) — authoritative
  basis = "found"     → newly researched (vendor site / quote) for a line that had no cost
  basis = "bom-sheet" → the cost already on Steve's BLK3 BOM (prior/known reference)

Overlay lives in mission-control/data/bom-costs.json (keyed section#item) so it is NOT wiped when
the BOM is re-indexed. /api/inventory + the report read it to color/label Paid vs Found.

CLI:
  uncosted            list BOM lines with no cost (neither BOM-sheet nor overlay)
  set --section S --item I --cost C --basis paid|found --source SRC [--ref R] [--note N]
  report              basis breakdown + remaining-uncosted count (exit 0 iff uncosted==0)
"""
import json, os, sys, argparse
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
BOM = os.path.join(WS, "mission-control/data/bom-index.json")
OVER = os.path.join(WS, "mission-control/data/bom-costs.json")


def _f(v):
    try:
        return float(str(v).strip().replace("$", "").replace(",", ""))
    except Exception:
        return 0.0


def load_bom():
    return json.load(open(BOM)).get("rows", [])


def load_over():
    try:
        return json.load(open(OVER))
    except Exception:
        return {"costs": {}}


def save_over(d):
    json.dump(d, open(OVER, "w"), indent=1)


def key(r):
    return f"{r.get('section','')}#{r.get('item','')}"


def effective(r, over):
    """Return (unit_cost, basis, source, ref) using overlay first, then BOM-sheet cost."""
    k = key(r)
    o = over.get("costs", {}).get(k)
    if o and _f(o.get("unit_cost")) > 0:
        return _f(o["unit_cost"]), o.get("basis", "found"), o.get("source", ""), o.get("ref", "")
    if _f(r.get("cost")) > 0:
        return _f(r.get("cost")), "bom-sheet", r.get("vendor", ""), ""
    return 0.0, "none", "", ""


def cmd_uncosted(a):
    over = load_over()
    n = 0
    for r in load_bom():
        c, basis, *_ = effective(r, over)
        if c <= 0:
            n += 1
            print(f"{key(r):24} qty={r.get('qty','')!s:4} | {r.get('description','')[:46]:46} | vpn={r.get('vendor_pn','')} | vend={r.get('vendor','')}")
    print(f"\nUNCOSTED: {n}")


def cmd_set(a):
    over = load_over()
    over.setdefault("costs", {})[f"{a.section}#{a.item}"] = {
        "unit_cost": _f(a.cost), "basis": a.basis, "source": a.source,
        "ref": a.ref or "", "note": a.note or "",
        "date": datetime.now(timezone.utc).isoformat(),
    }
    save_over(over)
    print(f"set {a.section}#{a.item} = ${_f(a.cost):.2f} [{a.basis}] {a.source} {a.ref or ''}")


def cmd_report(a):
    over = load_over()
    rows = load_bom()
    tally = {"paid": [0, 0.0], "found": [0, 0.0], "bom-sheet": [0, 0.0], "none": [0, 0.0]}
    ext = 0.0
    for r in rows:
        c, basis, *_ = effective(r, over)
        q = _f(r.get("qty")) or 1
        tally[basis][0] += 1
        tally[basis][1] += c
        ext += c * q
    print("BLK3 cost coverage by basis (lines / sum unit-cost):")
    for b in ("paid", "found", "bom-sheet", "none"):
        print(f"  {b:9} {tally[b][0]:4} lines  ${tally[b][1]:,.2f}")
    print(f"  extended (unit x qty) total: ${ext:,.2f}")
    print(f"  remaining uncosted: {tally['none'][0]}")
    sys.exit(0 if tally["none"][0] == 0 else 1)


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("uncosted").set_defaults(fn=cmd_uncosted)
    st = s.add_parser("set")
    for f in ("section", "item", "cost", "basis", "source"):
        st.add_argument("--" + f, required=True)
    st.add_argument("--ref"); st.add_argument("--note")
    st.set_defaults(fn=cmd_set)
    s.add_parser("report").set_defaults(fn=cmd_report)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
