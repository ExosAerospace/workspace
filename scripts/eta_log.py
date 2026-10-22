#!/usr/bin/env python3
"""eta_log.py — log promised vs actual delivery times so ETA defaults can be tuned (Jon 10/2).
Actual = time from the ask to the FINAL, complete answer, not the first ack (Jon 10/22). Use --asked HH:MM.

  python3 scripts/eta_log.py add --task "Howmet DD" --kind research --promised 90 --actual 8
  python3 scripts/eta_log.py report [--days 7]     # per-kind actual/promised ratio + suggested default

Weekly RSI (scripts/weekly-rsi.py §14) calls report_section(). Store: data/eta-log.jsonl.
"""
import argparse, json, math, os, statistics, time
from datetime import datetime, timedelta

WS = "/Users/exomac/.openclaw/workspace"
LOG = os.path.join(WS, "data", "eta-log.jsonl")

# Current ETA defaults in minutes (keep in sync with AGENTS.md "Ack + ETA").
# Recalibrated 2026-10-16 (Jon: "correct the gross prediction errors"): 118 logged asks, 85 (72%) promised
# >2x the actual time; median promise was 2.6x actual because promises ignored these defaults and padded
# (edit: default 10 but median promise 25; actual median 8). New defaults = p80 of actual minutes per kind
# (late pickup outliers excluded), NO extra pad. Get the clock time with:  eta_log.py eta --kind build
DEFAULTS = {"quick": 5, "edit": 15, "research": 15, "build": 25}
PAD_FLAG = 1.5    # a promise > 1.5x the default is logged as PADDED and counted in the weekly report
LATE_OUTLIER = 3  # actual > 3x promised = a pickup/routing miss, not an estimation error
BAND = (0.6, 1.1)  # healthy actual/promised ratio; outside it, propose a retune


def add(task, kind, promised, actual, channel=""):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    rec = {"ts": datetime.now().isoformat(timespec="seconds"), "task": task, "kind": kind,
           "promised_min": promised, "actual_min": actual, "channel": channel}
    d = DEFAULTS.get(kind)
    if d and promised > PAD_FLAG * d:
        rec["padded"] = True
        print(f"WARNING: promised {promised:g} min is >{PAD_FLAG}x the {kind} default ({d} min). Use `eta_log.py eta --kind {kind}`.")
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def load(days=7):
    if not os.path.exists(LOG):
        return []
    cut = datetime.now() - timedelta(days=days)
    out = []
    for line in open(LOG):
        try:
            r = json.loads(line)
            if datetime.fromisoformat(r["ts"]) >= cut and r.get("promised_min"):
                out.append(r)
        except Exception:
            pass
    return out


def analyze(days=7):
    by = {}
    for r in load(days):
        by.setdefault(r.get("kind", "other"), []).append(r)
    rows = []
    for kind, rs in sorted(by.items()):
        ratio = statistics.median(r["actual_min"] / r["promised_min"] for r in rs)
        p80 = sorted(r["actual_min"] for r in rs)[max(0, int(len(rs) * 0.8) - 1)]
        cur = DEFAULTS.get(kind)
        clean = sorted(r["actual_min"] for r in rs if r["actual_min"] <= LATE_OUTLIER * r["promised_min"]) or [p80]
        p80 = clean[max(0, math.ceil(len(clean) * 0.8) - 1)]
        suggest = max(5, round(p80 / 5) * 5)  # p80 actual (late pickup misses excluded), nearest 5 min, no pad
        rows.append({"kind": kind, "n": len(rs), "ratio": round(ratio, 2), "p80_actual": p80,
                     "default": cur, "suggest": suggest,
                     "off": not (BAND[0] <= ratio <= BAND[1])})
    return rows


def report_section(days=7):
    """Lines for the weekly RSI report. Exception-only (R-NONEWS): returns [] when calibrated."""
    rows = [r for r in analyze(days) if r["off"]]
    if not rows:
        return []
    L = ["\n## 14. ETA calibration (tune ack ETAs)"]
    for r in rows:
        verdict = "too conservative" if r["ratio"] < BAND[0] else "too optimistic"
        L.append(f"- **{r['kind']}** ({r['n']} asks): actual/promised median {r['ratio']} → {verdict}. "
                 f"p80 actual {r['p80_actual']} min; default {r['default']} → suggest **{r['suggest']} min**.")
    L.append("- Action: update DEFAULTS in scripts/eta_log.py + AGENTS.md 'Ack + ETA' to the suggested values.")
    rs = load(days)
    pad = [r for r in rs if DEFAULTS.get(r.get("kind")) and r["promised_min"] > PAD_FLAG * DEFAULTS[r["kind"]]]
    late = [r for r in rs if r["actual_min"] > LATE_OUTLIER * r["promised_min"]]
    if pad:
        L.append(f"- Padding: {len(pad)}/{len(rs)} promises were >{PAD_FLAG}x the default. Use `eta_log.py eta`, don't estimate by feel.")
    if late:
        L.append(f"- Pickup misses (actual >{LATE_OUTLIER}x promised = request sat unanswered): " +
                 "; ".join(f"{r['task'][:40]} ({r['promised_min']:g}→{r['actual_min']:g} min)" for r in late))
    return L


def eta(kind, items=1, now=None):
    """ETA clock for an ack: the kind default (+5 min per extra parallel item, not stacked), rounded up to :05."""
    mins = DEFAULTS[kind] + 5 * max(0, items - 1)
    now = now or datetime.now()
    t = now + timedelta(minutes=mins)
    t = t + timedelta(minutes=(-t.minute) % 5, seconds=-t.second, microseconds=-t.microsecond)
    return mins, t.strftime("%-I:%M %p")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("add")
    a.add_argument("--task", required=True)
    a.add_argument("--kind", choices=list(DEFAULTS) + ["other"], required=True)
    a.add_argument("--promised", type=float, required=True)
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--actual", type=float)
    # Jon 10/22: actual = ask -> FINAL complete answer (not the first ack/partial update)
    g.add_argument("--asked", help="HH:MM (today, local) the ask arrived; actual = minutes from then until now (the final answer)")
    a.add_argument("--channel", default="")
    r = sp.add_parser("report")
    r.add_argument("--days", type=int, default=7)
    e = sp.add_parser("eta")
    e.add_argument("--kind", choices=list(DEFAULTS), required=True)
    e.add_argument("--items", type=int, default=1, help="parallel deliverables in one ask (+5 min each, not stacked)")
    args = ap.parse_args()
    if args.cmd == "eta":
        m, clock = eta(args.kind, args.items)
        print(f"{m} min -> by {clock} CDT")
    elif args.cmd == "add":
        actual = args.actual
        if args.asked:
            import datetime as _dt
            now = _dt.datetime.now()
            h, mi = map(int, args.asked.split(":"))
            actual = round((now - now.replace(hour=h, minute=mi, second=0, microsecond=0)).total_seconds() / 60, 1)
        print(add(args.task, args.kind, args.promised, actual, args.channel))
    else:
        for row in analyze(args.days):
            print(row)
        print("\n".join(report_section(args.days)) or "(calibrated — nothing to report)")
