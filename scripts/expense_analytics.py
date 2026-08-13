#!/usr/bin/env python3
"""expense_analytics.py — Exobot expense monitoring + reporting.

Scans the expense ledger (mission-control/data/expense-reports.json) and reports:
  • Mileage reimbursement per employee (miles, $, effective rate) vs the IRS rate.
  • Every line item that the pre-screen flagged as out of area-normal cost range.
  • Spend by category and by employee.

Usage:
  python3 scripts/expense_analytics.py            # print markdown report
  python3 scripts/expense_analytics.py --email    # also email it to Jon
  python3 scripts/expense_analytics.py --days 30  # window (default: all)

Deterministic; safe to run on a launchd timer.
"""
import json, os, sys, subprocess
from datetime import datetime, timezone, timedelta

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(WS, "mission-control", "data", "expense-reports.json")
NORMS = os.path.join(WS, "mission-control", "data", "expense-norms.json")
JON = "jquinn@exosaero.com"


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def main():
    days = None
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception:
            days = None
    led = load(LEDGER, [])
    norms = load(NORMS, {})
    rate = float(norms.get("mileage_rate", 0.70))

    cutoff = None
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    reports = []
    for e in led:
        ts = e.get("submitted_at")
        if cutoff and ts:
            try:
                if datetime.fromisoformat(ts.replace("Z", "+00:00")) < cutoff:
                    continue
            except Exception:
                pass
        reports.append(e)

    by_emp = {}       # email -> {name, miles, mileage_usd, total, count}
    by_cat = {}       # category -> $
    flagged = []      # (report_id, submitter, message)
    for e in reports:
        who = e.get("submitter_name") or e.get("submitter_email") or "?"
        em = (e.get("submitter_email") or "?").lower()
        rec = by_emp.setdefault(em, {"name": who, "miles": 0.0, "mileage_usd": 0.0, "total": 0.0, "count": 0})
        rec["count"] += 1
        rec["total"] += float(e.get("amount") or 0)
        sc = e.get("screen") or {}
        rec["miles"] += float(sc.get("mileage_total_miles") or 0)
        rec["mileage_usd"] += float(sc.get("mileage_total_usd") or 0)
        for it in (e.get("line_items") or []):
            cat = it.get("category") or "Other"
            by_cat[cat] = by_cat.get(cat, 0) + float(it.get("amount") or 0)
        for f in (sc.get("flags") or []):
            if f.get("severity") == "review":
                flagged.append((e.get("id"), who, f.get("message")))

    win = f"last {days} days" if days else "all time"
    L = [f"# Exos Expense Monitoring — {win}",
         f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · IRS mileage rate ${rate:.2f}/mi · {len(reports)} report(s)_", ""]

    L.append("## Mileage reimbursement by employee")
    if by_emp:
        any_mile = False
        for em, r in sorted(by_emp.items(), key=lambda kv: -kv[1]["miles"]):
            if r["miles"] <= 0:
                continue
            any_mile = True
            eff = (r["mileage_usd"] / r["miles"]) if r["miles"] else 0
            note = "" if abs(eff - rate) < 0.005 else f"  ⚠️ effective ${eff:.3f}/mi ≠ ${rate:.2f}"
            L.append(f"- **{r['name']}** — {r['miles']:.0f} mi = ${r['mileage_usd']:,.2f}{note}")
        if not any_mile:
            L.append("- _No mileage claimed in this window._")
    else:
        L.append("- _No reports in this window._")

    L += ["", "## Flagged expenses (out of area-normal range)"]
    if flagged:
        for rid, who, msg in flagged:
            L.append(f"- `{rid}` · {who}: {msg}")
    else:
        L.append("- ✅ None — all line items within area-normal cost ranges.")

    L += ["", "## Spend by category"]
    if by_cat:
        for cat, amt in sorted(by_cat.items(), key=lambda kv: -kv[1]):
            L.append(f"- {cat}: ${amt:,.2f}")
    else:
        L.append("- _No itemized lines yet (pre-web-form reports have no line items)._")

    L += ["", "## Spend by employee"]
    for em, r in sorted(by_emp.items(), key=lambda kv: -kv[1]["total"]):
        L.append(f"- {r['name']}: ${r['total']:,.2f} across {r['count']} report(s)")

    report = "\n".join(L)
    print(report)

    if "--email" in sys.argv:
        mail = (f"From: Exos Mission Control <jquinnexo@pm.me>\nTo: {JON}\n"
                f"Subject: Expense monitoring digest — {win}\n\n{report}\n")
        try:
            subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", JON],
                           input=mail.encode(), timeout=30, check=False)
            print("\n[emailed to Jon]", file=sys.stderr)
        except Exception as ex:
            print(f"\n[email failed: {ex}]", file=sys.stderr)


main()
