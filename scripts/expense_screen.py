#!/usr/bin/env python3
"""expense_screen.py — Exobot pre-approval screen for expense reports.

Reads a JSON payload on stdin:
  { "line_items": [ {date, category, description, location, amount, miles?, from?, to?} ], ... }
Compares each line against area-aware expected-cost bands (mission-control/data/expense-norms.json)
and emits flags for anything out of the normal range, so the reviewer sees concerns BEFORE approving.

Deterministic (model out of the path). Prints JSON:
  { "total": <num>, "mileage_total": <num>, "flags": [ {ref, severity, message} ], "summary": "<one-liner>" }
"""
import json, os, sys

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NORMS = os.path.join(WS, "mission-control", "data", "expense-norms.json")


def load_norms():
    try:
        return json.load(open(NORMS))
    except Exception:
        return {"mileage_rate": 0.70, "categories": {}, "high_cost_areas": {"tokens": [], "multiplier": 1.0},
                "mileage": {}}


def is_high_cost(location, hca):
    loc = (location or "").lower()
    return any(tok and tok in loc for tok in hca.get("tokens", []))


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"total": 0, "mileage_total": 0, "flags": [], "summary": "no data"}))
        return
    norms = load_norms()
    rate = float(norms.get("mileage_rate", 0.70))
    cats = norms.get("categories", {})
    hca = norms.get("high_cost_areas", {"tokens": [], "multiplier": 1.0})
    mult = float(hca.get("multiplier", 1.0))
    mi = norms.get("mileage", {})

    items = payload.get("line_items", []) or []
    flags = []
    total = 0.0
    mileage_total_mi = 0.0
    mileage_total_usd = 0.0
    day_cat = {}   # (date,category) -> summed amount
    seen = {}      # (date,category,amount) -> count  (duplicate detection)

    for i, it in enumerate(items):
        ref = f"line {i+1}"
        cat = (it.get("category") or "Other").strip()
        loc = it.get("location") or ""
        desc = (it.get("description") or "").strip()
        label = f"{cat}" + (f" — {desc}" if desc else "") + (f" ({loc})" if loc else "")

        # Mileage lines: amount is derived from miles * IRS rate.
        if cat.lower() == "mileage":
            miles = float(it.get("miles") or 0)
            amt = round(miles * rate, 2)
            mileage_total_mi += miles
            mileage_total_usd += amt
            total += amt
            if miles <= 0:
                flags.append({"ref": ref, "severity": "info", "message": f"{ref}: mileage line has 0 miles."})
            if mi.get("single_trip_flag_over_miles") and miles > mi["single_trip_flag_over_miles"]:
                flags.append({"ref": ref, "severity": "review",
                              "message": f"{ref}: {miles:.0f} mi single trip exceeds {mi['single_trip_flag_over_miles']} mi — confirm route/purpose."})
            # sanity: if a submitted amount disagrees with miles*rate, flag it
            if it.get("amount") not in (None, "", 0) and abs(float(it["amount"]) - amt) > 0.01:
                flags.append({"ref": ref, "severity": "review",
                              "message": f"{ref}: entered ${float(it['amount']):.2f} ≠ {miles:.0f} mi × ${rate:.2f} = ${amt:.2f} (using computed value)."})
            continue

        amt = round(float(it.get("amount") or 0), 2)
        total += amt
        band = cats.get(cat) or cats.get("Other") or {}
        flag_over = band.get("flag_over")
        if flag_over is not None and cat in ("Lodging", "Meals") and is_high_cost(loc, hca):
            flag_over = round(flag_over * mult, 2)
        if flag_over is not None and amt > flag_over:
            hc = " (high-cost area cap applied)" if cat in ("Lodging", "Meals") and is_high_cost(loc, hca) else ""
            flags.append({"ref": ref, "severity": "review",
                          "message": f"{ref}: {label} = ${amt:,.2f} is above the ${flag_over:,.0f} {cat} norm{hc} — verify receipt/justification."})
        # per-day category rollup (meals etc.)
        d = it.get("date") or "?"
        day_cat[(d, cat)] = day_cat.get((d, cat), 0) + amt
        # duplicate detection
        key = (d, cat, amt)
        seen[key] = seen.get(key, 0) + 1

    # per-day category caps
    for (d, cat), s in day_cat.items():
        band = cats.get(cat) or {}
        dfo = band.get("day_flag_over")
        if dfo is not None and s > dfo:
            flags.append({"ref": f"{cat} on {d}", "severity": "review",
                          "message": f"{cat} on {d} totals ${s:,.2f}, above the ${dfo:,.0f}/day norm — confirm all lines are valid."})
    # duplicates
    for (d, cat, amt), n in seen.items():
        if n > 1 and amt > 0:
            flags.append({"ref": f"{cat} {d}", "severity": "review",
                          "message": f"Possible duplicate: {n}× {cat} of ${amt:,.2f} on {d}."})

    # mileage period cap
    if mi.get("period_flag_over_miles") and mileage_total_mi > mi["period_flag_over_miles"]:
        flags.append({"ref": "mileage total", "severity": "review",
                      "message": f"Total mileage {mileage_total_mi:.0f} mi exceeds the {mi['period_flag_over_miles']} mi/period norm."})

    n = len(flags)
    reviewy = sum(1 for f in flags if f["severity"] == "review")
    if reviewy:
        summary = f"⚠️ Pre-screen: {reviewy} item(s) above area-normal costs — review before approving."
    else:
        summary = "✅ Pre-screen: all lines within area-normal cost ranges."
    print(json.dumps({
        "total": round(total, 2),
        "mileage_total_miles": round(mileage_total_mi, 1),
        "mileage_total_usd": round(mileage_total_usd, 2),
        "mileage_rate": rate,
        "flags": flags,
        "flag_count": reviewy,
        "summary": summary,
    }))


main()
