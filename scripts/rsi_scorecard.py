#!/usr/bin/env python3
"""
rsi_scorecard.py — pass/fail performance targets at the top of the weekly RSI report.
Jon 2026-10-22 ("yes" to the four proposed targets). Read-only.

  1. Response time   ≥90% of requests get a first reply ≤5 min AND 0 pickup misses (response_watch.py)
  2. ETA accuracy    ≥80% of final answers land by the promised ETA (data/eta-log.jsonl)
  3. Priority        ≥70% of the top-20 Mission-Score tasks moved this week (weekly-rsi §1)
  4. Fleet health    0 FAIL in the latest agent_eval run (logs/agent-eval.log)

Run: python3 scripts/rsi_scorecard.py [--selftest]
"""
import json, os, re, sys
from datetime import datetime, timedelta

WS = "/Users/exomac/.openclaw/workspace"
LAT_LOG = os.path.join(WS, "data", "response-latency.jsonl")
ETA_LOG = os.path.join(WS, "data", "eta-log.jsonl")
EVAL_LOG = os.path.join(WS, "logs", "agent-eval.log")


def _rows(path, since):
    if not os.path.exists(path):
        return []
    out = []
    for l in open(path):
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("ts", "") >= since:
            out.append(r)
    return out


def response(days=7):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = _rows(LAT_LOG, since)
    if not rows:
        return None, "no data"
    within = sum(1 for r in rows if r["latency_min"] <= 5)
    miss = sum(1 for r in rows if r.get("nudged"))
    pct = round(100 * within / len(rows))
    return (pct >= 90 and miss == 0), f"{pct}% ≤5 min, {miss} pickup misses ({len(rows)} requests)"


def eta(days=7):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = _rows(ETA_LOG, since)
    if not rows:
        return None, "no data"
    on = sum(1 for r in rows if r["actual_min"] <= r["promised_min"])
    pct = round(100 * on / len(rows))
    return pct >= 80, f"{pct}% on time ({on}/{len(rows)})"


def fleet():
    if not os.path.exists(EVAL_LOG):
        return None, "no data"
    last = None
    for l in open(EVAL_LOG, errors="replace"):
        m = re.search(r"eval: (\d+) OK / (\d+) WARN / (\d+) FAIL", l)
        if m:
            last = m
    if not last:
        return None, "no data"
    fails = int(last.group(3))
    return fails == 0, f"{fails} FAIL / {last.group(2)} WARN in latest agent_eval run"


def lines(accuracy, days=7):
    checks = [("Response time", "≥90% first reply ≤5 min, 0 pickup misses", response(days)),
              ("ETA accuracy", "≥80% of final answers by promised ETA", eta(days)),
              ("Priority", "≥70% of top-20 tasks moved", (accuracy >= 70, f"{accuracy}% moved")),
              ("Fleet health", "0 failing agents", fleet())]
    passed = sum(1 for *_, (ok, _) in checks if ok)
    L = [f"## Scorecard — {passed}/{len(checks)} targets met"]
    for name, target, (ok, actual) in checks:
        mark = "✅" if ok else ("⚪" if ok is None else "❌")
        L.append(f"- {mark} **{name}** — {actual} (target: {target})")
    L.append("")
    return L, passed, len(checks)


def selftest():
    L, p, n = lines(75)
    assert n == 4 and L[0].startswith("## Scorecard") and len(L) == 6, L
    print("\n".join(L))
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print("\n".join(lines(int(sys.argv[1]) if len(sys.argv) > 1 else 0)[0]))
