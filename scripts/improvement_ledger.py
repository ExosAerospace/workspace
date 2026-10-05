#!/usr/bin/env python3
"""improvement_ledger.py — the exo3 VALIDATE step: every fix is a hypothesis, measured before/after (Jon 2026-10-04).

"Feedback from repeated operation becomes a competitive advantage" only if each fix is checked against
real operation. Each ledger entry = one change (commit) to one agent, with a hypothesis and the metrics
it should move. Baselines and results come from telemetry that already exists — nothing self-reported:

  reliability  launchd: logs/runs/*.jsonl ok-rate (run_logged.py) + "green-but-errored" events in
               governance/events.jsonl (the quiet failures launchd can't see); cron: openclaw cron runs status
  turnaround   median run duration (launchd duration_s / cron durationMs)
  cost         cron: median total_tokens per run (launchd jobs run local = no token cost)
  dup_sends    duplicate Discord posts (deliver.log "could not move to sent" = sweeper/live-send race)

Lifecycle: add (baseline = 7 days before the change) → measure (≥7 days after: verdict IMPROVED /
NO CHANGE / REGRESSED / RECURRED) → weekly RSI §16 reports verdicts + the fleet scorecard trend.
REGRESSED → revert Decision for Jon; NO CHANGE → the fix didn't address the root cause, reopen it.

Usage:
  improvement_ledger.py add --agent <label> [--govlog NAME] [--cron ID] --change <commit> \
        --hypothesis "..." --metrics reliability,turnaround[,cost,dup_sends] [--at ISO]
  improvement_ledger.py measure          # verdicts for entries ≥7 days old (prints RSI lines)
  improvement_ledger.py scorecard        # fleet trend: this week vs last week
"""
import json, os, sys, glob, re, subprocess, statistics, argparse
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
LEDGER = os.path.join(WS, "mission-control", "data", "improvement-ledger.json")
EVENTS = os.path.join(WS, "governance", "events.jsonl")
RUNS = os.path.join(WS, "logs", "runs")
DELIVER = os.path.join(WS, "logs", "deliver.log")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
WINDOW = timedelta(days=7)


def _dt(s):
    try:
        s = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(s).replace("Z", "+00:00"))   # -0500 → -05:00 (py3.9)
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def load():
    try:
        return json.load(open(LEDGER))
    except Exception:
        return {"entries": []}


def save(d):
    json.dump(d, open(LEDGER + ".tmp", "w"), indent=1, ensure_ascii=False)
    os.replace(LEDGER + ".tmp", LEDGER)


def _runs(label, a, b):
    out = []
    for p in glob.glob(os.path.join(RUNS, "*.jsonl")):
        day = os.path.basename(p)[:10]
        if day < (a - timedelta(days=1)).date().isoformat() or day > (b + timedelta(days=1)).date().isoformat():
            continue
        for l in open(p):
            try:
                r = json.loads(l)
            except Exception:
                continue
            if r.get("label") == label and (t := _dt(r.get("start"))) and a <= t < b:
                out.append(r)
    return out


def _gov_errors(name, a, b):
    if not name or not os.path.exists(EVENTS):
        return None
    n = 0
    lo, hi = a.isoformat()[:10], b.isoformat()[:10]
    for l in open(EVENTS):
        if f'"{name}"' not in l or '"error"' not in l:
            continue
        try:
            e = json.loads(l)
        except Exception:
            continue
        if e.get("agent") == name and e.get("event") == "error" and (t := _dt(e.get("ts"))) and a <= t < b:
            n += 1
    return n


def _cron_runs(cid, a, b):
    try:
        r = subprocess.run([OPENCLAW, "cron", "runs", "--id", cid, "--limit", "200", "--json"],
                           capture_output=True, text=True, timeout=60)
        ents = json.loads(r.stdout).get("entries", [])
    except Exception:
        return []
    out = []
    for e in ents:
        if e.get("action") != "finished":
            continue
        t = datetime.fromtimestamp((e.get("runAtMs") or e.get("ts") or 0) / 1000, timezone.utc)
        if a <= t < b:
            out.append(e)
    return out


def _dup_sends(a, b):
    n = 0
    if os.path.exists(DELIVER):
        for l in open(DELIVER):
            if "could not move to sent" in l and (m := re.match(r"\[([^\]]+)\]", l)) and (t := _dt(m.group(1))) and a <= t < b:
                n += 1
    return n


def metrics(e, a, b):
    """Measure one entry's metrics over [a, b)."""
    m = {}
    if e.get("cron"):
        rs = _cron_runs(e["cron"], a, b)
        if rs:
            m["runs"] = len(rs)
            m["reliability"] = round(sum(1 for r in rs if r.get("status") == "ok") / len(rs), 3)
            m["turnaround_s"] = round(statistics.median((r.get("durationMs") or 0) / 1000 for r in rs), 1)
            toks = [((r.get("usage") or {}).get("total_tokens") or 0) for r in rs]
            m["cost_tokens"] = int(statistics.median(toks)) if toks else None
    else:
        rs = _runs(e["agent"], a, b)
        if rs:
            m["runs"] = len(rs)
            errs = _gov_errors(e.get("govlog"), a, b) or 0
            ok = sum(1 for r in rs if r.get("ok"))
            m["reliability"] = round(max(0, ok - errs) / len(rs), 3)   # green-but-errored counts as a failure
            m["quiet_errors"] = errs
            m["turnaround_s"] = round(statistics.median(r.get("duration_s") or 0 for r in rs), 1)
        elif e.get("govlog"):
            m["quiet_errors"] = _gov_errors(e["govlog"], a, b)
    if "dup_sends" in e.get("metrics", []):
        m["dup_sends"] = _dup_sends(a, b)
    if e.get("error_signature"):
        m["sig_errors"] = _sig_errors(e["error_signature"], a, b)
    return m


def _sig_errors(sig, a, b):
    """Occurrences of the targeted failure signature anywhere in governance events + watchdog log."""
    n = 0
    if os.path.exists(EVENTS):
        for l in open(EVENTS):
            if sig in l and (t := _dt(json.loads(l).get("ts"))) and a <= t < b:
                n += 1
    wd = os.path.join(WS, "logs", "completion-watchdog.log")
    if os.path.exists(wd):
        for l in open(wd):
            if sig in l and (mm := re.search(r"(20\d\d-\d\d-\d\d[T ]\d\d:\d\d:\d\d)", l)) and (t := _dt(mm.group(1).replace(" ", "T") + "-05:00")) and a <= t < b:
                n += 1
    return n


def verdict(e, before, after):
    """IMPROVED if every targeted metric is better or equal and at least one is better; REGRESSED if any worse."""
    better = worse = 0
    checks = []
    def cmp(key, higher_is_better, tol):
        nonlocal better, worse
        x, y = before.get(key), after.get(key)
        if x is None or y is None:
            return
        if (y - x) * (1 if higher_is_better else -1) > tol: better += 1; checks.append(f"{key} {x}→{y} ✓")
        elif (x - y) * (1 if higher_is_better else -1) > tol: worse += 1; checks.append(f"{key} {x}→{y} ✗")
        else: checks.append(f"{key} {x}→{y} =")
    want = set(e.get("metrics", []))
    if "reliability" in want: cmp("reliability", True, 0.005); cmp("quiet_errors", False, 0)
    if "turnaround" in want: cmp("turnaround_s", False, max(1.0, 0.1 * (before.get("turnaround_s") or 0)))
    if "cost" in want: cmp("cost_tokens", False, 0.1 * (before.get("cost_tokens") or 0))
    if "dup_sends" in want: cmp("dup_sends", False, 0)
    if e.get("error_signature"): cmp("sig_errors", False, 0)
    recurred = bool(e.get("error_signature")) and (after.get("sig_errors") or 0) > 0
    v = "REGRESSED" if worse else ("RECURRED" if recurred else ("IMPROVED" if better else "NO CHANGE"))
    return v, checks


def cmd_add(a):
    d = load()
    at = _dt(a.at) if a.at else datetime.now(timezone.utc)
    e = {"id": f"IMP-{len(d['entries']) + 1:03d}", "agent": a.agent, "govlog": a.govlog, "cron": a.cron,
         "change": a.change, "hypothesis": a.hypothesis, "metrics": [x.strip() for x in a.metrics.split(",") if x.strip()],
         "error_signature": a.signature, "at": at.isoformat(), "status": "measuring"}
    e["baseline"] = metrics(e, at - WINDOW, at)
    d["entries"].append(e); save(d)
    print(f"{e['id']} {a.agent}: baseline {e['baseline']}")


def cmd_measure(print_lines=True):
    d = load(); now = datetime.now(timezone.utc); lines = []
    for e in d["entries"]:
        at = _dt(e["at"])
        if e.get("status") != "measuring" or now - at < WINDOW:
            continue
        e["after"] = metrics(e, at, at + WINDOW)
        e["verdict"], e["checks"] = verdict(e, e.get("baseline", {}), e["after"])
        e["status"] = "verdict"; e["measured_at"] = now.isoformat()
        lines.append(f"- {e['id']} {e['agent']} ({e['change']}): **{e['verdict']}** — {'; '.join(e['checks']) or 'no comparable data'}"
                     f" · hypothesis: {e['hypothesis'][:90]}")
    save(d)
    pending = [e for e in d["entries"] if e.get("status") == "measuring"]
    if pending:
        lines.append(f"- measuring ({len(pending)}): " + ", ".join(f"{e['id']} {e['agent']} (due {(_dt(e['at']) + WINDOW).date()})" for e in pending))
    if print_lines:
        print("\n".join(lines) or "nothing to measure")
    return lines


def scorecard():
    """Fleet trend across ALL launchd jobs: this week vs last week (reliability incl. quiet errors, turnaround)."""
    now = datetime.now(timezone.utc)
    def week(a, b):
        rs = []
        for p in glob.glob(os.path.join(RUNS, "*.jsonl")):
            for l in open(p):
                try:
                    r = json.loads(l)
                except Exception:
                    continue
                if (t := _dt(r.get("start"))) and a <= t < b:
                    rs.append(r)
        gov = 0
        if os.path.exists(EVENTS):
            lo = a.isoformat()[:10]
            for l in open(EVENTS):
                if '"error"' in l and l[8:18] >= lo:
                    try:
                        e = json.loads(l)
                    except Exception:
                        continue
                    if e.get("event") == "error" and (t := _dt(e.get("ts"))) and a <= t < b:
                        gov += 1
        if not rs:
            return None
        ok = sum(1 for r in rs if r.get("ok"))
        return {"runs": len(rs), "fail": len(rs) - ok, "quiet_errors": gov,
                "reliability": round(max(0, ok - gov) / len(rs), 4),
                "p50_s": round(statistics.median(r.get("duration_s") or 0 for r in rs), 2),
                "dup_sends": _dup_sends(a, b)}
    cur, prev = week(now - WINDOW, now), week(now - 2 * WINDOW, now - WINDOW)
    return cur, prev


def report_section():
    L = ["\n## 16. Improvement ledger — did our fixes actually work?"]
    L += cmd_measure(print_lines=False) or ["- no fixes due for verdict this week"]
    try:   # crons auto-registered by agent_eval this week (D-7281949) — HIGH risk listed for review
        st = json.load(open(os.path.join(WS, "state", "agent-eval-state.json")))
        wk = (datetime.now() - WINDOW).isoformat()
        ar = [x["line"] for x in st.get("_auto_registered", []) if isinstance(x, dict) and x.get("ts", "") >= wk]
        if ar:
            L.append(f"- auto-registered crons this week ({len(ar)}; review HIGH): " + "; ".join(ar))
    except Exception:
        pass
    cur, prev = scorecard()
    if cur:
        p = (lambda k: f" (prev {prev[k]})" if prev else "")
        L.append(f"- fleet (launchd, 7d): {cur['runs']} runs · reliability {cur['reliability']}{p('reliability')} · "
                 f"hard fails {cur['fail']}{p('fail')} · quiet errors {cur['quiet_errors']}{p('quiet_errors')} · "
                 f"p50 {cur['p50_s']}s{p('p50_s')} · dup posts {cur['dup_sends']}{p('dup_sends')}")
    return L


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd")
    x = sp.add_parser("add")
    x.add_argument("--agent", required=True); x.add_argument("--govlog"); x.add_argument("--cron")
    x.add_argument("--change", required=True); x.add_argument("--hypothesis", required=True)
    x.add_argument("--metrics", default="reliability,turnaround"); x.add_argument("--signature")
    x.add_argument("--at")
    sp.add_parser("measure"); sp.add_parser("scorecard"); sp.add_parser("report")
    a = ap.parse_args()
    if a.cmd == "add": cmd_add(a)
    elif a.cmd == "measure": cmd_measure()
    elif a.cmd == "scorecard": print(json.dumps(scorecard(), indent=1))
    elif a.cmd == "report": print("\n".join(report_section()))
    else: print(__doc__)
