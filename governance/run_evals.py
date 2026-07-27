#!/usr/bin/env python3
"""
run_evals.py -- Trusted Evals pillar: the Quiet-Drift detector.

Quiet Drift is the dominant production failure mode: agents don't crash, they
degrade slowly, and you find out in escalations instead of dashboards. The
defense is a quantified threshold per agent class plus a runner that checks it.

This runner computes, per agent class, the **human-override rate** -- the share
of the class's surfaced proposals that Jon rejected or modified in the Decisions
inbox -- and compares it to the class's override_rate_ceiling in registry.json.
A class over its ceiling is flagged. (Override rate is the framework's named
twin signal alongside an accuracy floor; it's the one we can measure from real
data today.)

Two data sources:
  - mission-control/data/decisions.json  -- the real Human Review Queue (now)
  - governance/events.jsonl              -- per-class correlation substrate
                                            (populates as agents adopt govlog)

Decision->class mapping: uses an explicit `agentClass` field on a decision when
present; otherwise falls back to a system-level rollup (honest: we don't guess a
class we can't prove). As agents emit `surfaced_decision` events with their tag
+ decision_id, per-class attribution becomes exact.

Output: a RED/AMBER/GREEN governance report. Exit code 2 if any class is RED, so
it can gate a cron or wake an escalation.

Usage:  python3 run_evals.py [--json]
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(ROOT)
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
EVENTS = os.path.join(ROOT, "events.jsonl")
REGISTRY = os.path.join(ROOT, "registry.json")

# Heuristic answer classification. An "override" = Jon declined or changed the
# agent's proposed action. Transparent and tunable; not a model call.
APPROVE = re.compile(r"\b(approve|approved|yes|execute|go|send it|proceed|confirm|do it|agree|accept)\b", re.I)
OVERRIDE = re.compile(r"\b(no|reject|declin|hold|don'?t|do not|change|modify|revise|stop|cancel|instead|rework|not yet)\b", re.I)


def classify(answer: str) -> str:
    """Return 'approve', 'override', or 'unclear' for a human answer string."""
    if not answer or not answer.strip():
        return "unclear"
    a = answer.strip()
    # Override cues win ties: a "yes but change X" is still a modification.
    if OVERRIDE.search(a):
        return "override"
    if APPROVE.search(a):
        return "approve"
    return "unclear"


def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def load_events():
    rows = []
    if os.path.exists(EVENTS):
        with open(EVENTS, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    return rows


# Conservative source->class fallback for decisions that predate agentClass
# tagging. Only UNAMBIGUOUS sources are mapped; everything else stays in the
# _system rollup (we don't guess a class we can't prove — see module docstring).
SOURCE_MAP = {
    "Opportunity Engine": "opportunity-engine",
    "Overnight Resolver": "resolver",
    "De-Risk Orbital Engine": "derisk-orbital",
    "SAM.gov Amendment Watch": "sam-watch",
    "BLK3 Payload Sales Engine": "payload-sales",
}


def main():
    as_json = "--json" in sys.argv
    reg = load(REGISTRY, {"classes": []})
    classes = {c["id"]: c for c in reg.get("classes", [])}
    decisions = load(DECISIONS, [])
    events = load_events()

    # Map decision_id -> agent class from events (forward path).
    dec_to_class = {}
    for e in events:
        if e.get("event") == "surfaced_decision" and e.get("decision_id"):
            dec_to_class[str(e["decision_id"])] = e.get("agent")

    # Tally answered decisions per class (+ a system rollup bucket).
    tally = {}  # class_id -> {decided, approve, override, unclear}
    def bucket(cid):
        return tally.setdefault(cid, {"decided": 0, "approve": 0, "override": 0, "unclear": 0})

    for d in decisions:
        if (d.get("status") or "").lower() != "answered":
            continue
        cid = (d.get("agentClass") or dec_to_class.get(str(d.get("id")))
               or SOURCE_MAP.get(d.get("source")) or "_system")
        b = bucket(cid)
        verdict = classify(d.get("answer", ""))
        b["decided"] += 1
        b[verdict] += 1

    # Build the report.
    report = {"generated": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
              "events_logged": len(events), "decisions_total": len(decisions), "classes": []}
    worst = "GREEN"
    rank = {"GREEN": 0, "AMBER": 1, "RED": 2}

    # Per registered class (+ any system bucket).
    ids = list(classes.keys())
    if "_system" in tally and "_system" not in ids:
        ids.append("_system")

    for cid in ids:
        cfg = classes.get(cid, {})
        b = tally.get(cid, {"decided": 0, "approve": 0, "override": 0, "unclear": 0})
        ceiling = cfg.get("override_rate_ceiling", 0.40)
        min_runs = cfg.get("min_runs_for_eval", 8)
        decided = b["decided"]
        ovr = (b["override"] / decided) if decided else 0.0
        if decided < min_runs:
            flag = "GREEN"  # insufficient data -> not drifting yet
            note = f"insufficient data ({decided}/{min_runs} decided)"
        elif ovr > ceiling:
            flag = "RED"
            note = f"override rate {ovr:.0%} exceeds ceiling {ceiling:.0%} -- Quiet Drift signal"
        elif ovr > ceiling * 0.75:
            flag = "AMBER"
            note = f"override rate {ovr:.0%} approaching ceiling {ceiling:.0%}"
        else:
            flag = "GREEN"
            note = f"override rate {ovr:.0%} within ceiling {ceiling:.0%}"
        if rank[flag] > rank[worst]:
            worst = flag
        report["classes"].append({
            "class": cid, "tier": cfg.get("autonomy_tier", "?"),
            "decided": decided, "override": b["override"], "approve": b["approve"],
            "unclear": b["unclear"], "override_rate": round(ovr, 3),
            "ceiling": ceiling, "flag": flag, "note": note,
        })

    report["overall"] = worst

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print(f"\n  GOVERNANCE EVAL REPORT  ({report['generated']})")
        print(f"  decisions={report['decisions_total']}  events_logged={report['events_logged']}  overall={worst}\n")
        for c in report["classes"]:
            mark = {"GREEN": "[OK ]", "AMBER": "[!! ]", "RED": "[RED]"}[c["flag"]]
            print(f"  {mark} {c['class']:<18} tier={c['tier']:<22} "
                  f"decided={c['decided']:>3} override={c['override_rate']:.0%}  {c['note']}")
        print()

    sys.exit(2 if worst == "RED" else 0)


if __name__ == "__main__":
    main()
