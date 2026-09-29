#!/usr/bin/env python3
"""
po10_activity_report.py — render PO10 subscription activity for Neil's daily /
biweekly notifications. READ-ONLY, NEVER SENDS. Prints to stdout (or writes a
file with --out). Delivery (email to David) is intentionally NOT wired here; it
awaits Neil's approval (Decision D-PO10-NOTIFY-20260819) + confirmed recipient.

Source of truth: mission-control/data/capital_bridge_ledger.json
  - entries[]           = received funds (counted toward the $1M running total)
  - pending_packets[]   = executed packets with funds NOT yet received

Usage:
  python3 po10_activity_report.py --mode daily     [--since-days 1]
  python3 po10_activity_report.py --mode biweekly  [--since-days 14]
"""
import json, os, argparse
from datetime import datetime, timedelta, date

WS     = os.path.expanduser("~/.openclaw/workspace")
LEDGER = os.path.join(WS, "mission-control", "data", "capital_bridge_ledger.json")


def load():
    with open(LEDGER) as f:
        return json.load(f)


def d(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def usd(n):
    return "${:,.0f}".format(n or 0)


def received(led):
    # exo3 sign-off gate: only human-confirmed entries count (pending/rejected/excluded do not).
    return [e for e in led["entries"] if isinstance(e.get("amount"), (int, float))
            and e.get("status") not in ("pending_confirmation", "rejected") and not e.get("excluded_from_total")]


def running_total(led):
    return (led.get("baseline_amount") or 0) + sum(e["amount"] for e in received(led))


def render(led, mode, since_days):
    today = date.today()
    cutoff = today - timedelta(days=since_days)
    total = running_total(led)
    target = led.get("target") or 0
    pct = (total / target * 100) if target else 0
    pend = led.get("pending_packets", [])
    out = []

    if mode == "daily":
        out.append(f"PO10 Funds — daily update ({today:%Y-%m-%d})")
        out.append("")
        recent = [e for e in received(led) if (d(e.get("deposit_date") or e.get("date")) or today) >= cutoff]
        if recent:
            out.append(f"Funds received in the last {since_days} day(s):")
            for e in sorted(recent, key=lambda x: x.get("deposit_date") or x.get("date")):
                out.append(f"  • {e.get('deposit_date') or e['date']} — {e['investor']}: {usd(e['amount'])}")
        else:
            out.append(f"No new funds received in the last {since_days} day(s).")
        out.append("")
        out.append(f"Running total: {usd(total)} of {usd(target)} ({pct:.0f}%).")
        if pend:
            out.append("")
            out.append(f"Executed, funds still outstanding: {usd(sum(p['subscription_amount'] for p in pend))}")
            for p in pend:
                flag = "  ⚠️ AT RISK" if p.get("status") == "at_risk" else ""
                out.append(f"  • {p['investor']}: {usd(p['subscription_amount'])} (signed {p.get('signed_date','?')}){flag}")

    else:  # biweekly
        out.append(f"PO10 Subscription Activity — prior {since_days} days (through {today:%Y-%m-%d})")
        out.append("")
        window = [e for e in received(led) if (d(e.get("deposit_date") or e.get("date")) or today) >= cutoff]
        wsum = sum(e["amount"] for e in window)
        out.append(f"Funds received this period: {usd(wsum)} across {len(window)} investor(s).")
        for e in sorted(window, key=lambda x: x.get("deposit_date") or x.get("date")):
            out.append(f"  • {e.get('deposit_date') or e['date']} — {e['investor']}: {usd(e['amount'])} "
                       f"({e.get('shares','?')} sh @ ${e.get('price_per_share','?')})")
        out.append("")
        out.append(f"Cumulative received: {usd(total)} of {usd(target)} ({pct:.0f}%).")
        if pend:
            out.append("")
            out.append(f"Outstanding executed packets (funds not received): "
                       f"{usd(sum(p['subscription_amount'] for p in pend))}")
            for p in pend:
                flag = "  ⚠️ AT RISK — bank/investment-company issue" if p.get("status") == "at_risk" else ""
                out.append(f"  • {p['investor']}: {usd(p['subscription_amount'])} "
                           f"(signed {p.get('signed_date','?')}){flag}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "biweekly"], default="daily")
    ap.add_argument("--since-days", type=int, default=None)
    ap.add_argument("--out")
    a = ap.parse_args()
    since = a.since_days if a.since_days is not None else (1 if a.mode == "daily" else 14)
    text = render(load(), a.mode, since)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
