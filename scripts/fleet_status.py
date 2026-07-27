#!/usr/bin/env python3
"""
fleet_status.py — aggregate the Exos agent fleet into one Mission Control panel.

Writes mission-control/data/fleet.json, consumed by mission-control/fleet.html.
Deterministic; no model. One screen answer to "what is every agent doing, is it
healthy, and what is waiting on me?" Sources:
  - governance/run_evals.py --json   -> per-class override rate + RED/AMBER/GREEN
  - governance/registry.json         -> autonomy tier, delegation, purpose
  - governance/events.jsonl          -> last correlation-logged event per class
  - openclaw cron list --json        -> per-cron last run/status/next/model
  - mission-control/data/decisions.json    -> awaiting-Jon (open) + by source
  - mission-control/data/opportunities.json-> parseable $ pipeline
  - drafts/payload-outreach-drafts.md-> staged drafts count

Usage: fleet_status.py [--print]
"""
import os
import re
import sys
import json
import shutil
import subprocess

WS = "/Users/exomac/.openclaw/workspace"
OUT = os.path.join(WS, "mission-control/data/fleet.json")
EVENTS = os.path.join(WS, "governance/events.jsonl")
REGISTRY = os.path.join(WS, "governance/registry.json")
DECISIONS = os.path.join(WS, "mission-control/data/decisions.json")
OPPS = os.path.join(WS, "mission-control/data/opportunities.json")
DRAFTS = os.path.join(WS, "drafts/payload-outreach-drafts.md")
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
DEAD = ("DROP", "DEAD", "LOST", "CLOSED", "KILL")


def _load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def evals():
    try:
        r = subprocess.run([sys.executable, os.path.join(WS, "governance/run_evals.py"),
                            "--json"], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout)
    except Exception:
        return {"classes": []}


def last_events():
    """agent -> {ts, status} of its most recent event."""
    out = {}
    try:
        for line in open(EVENTS, encoding="utf-8"):
            try:
                e = json.loads(line)
            except Exception:
                continue
            a = e.get("agent")
            if a:
                out[a] = {"ts": e.get("ts"), "status": e.get("status")}
    except Exception:
        pass
    return out


def agents_logged():
    """Distinct agents emitting correlation-ID events = the unified log substrate
    coverage (govlog-native + task-ledger-wrapped jobs after unification)."""
    seen = set()
    try:
        for line in open(EVENTS, encoding="utf-8"):
            try:
                a = json.loads(line).get("agent")
            except Exception:
                continue
            if a:
                seen.add(a)
    except Exception:
        pass
    return len(seen)


def crons():
    try:
        r = subprocess.run([OPENCLAW, "cron", "list", "--json"],
                           capture_output=True, text=True, timeout=30)
        d = json.loads(r.stdout)
        jobs = d if isinstance(d, list) else d.get("jobs", d.get("crons", []))
    except Exception:
        jobs = []
    out = []
    for j in jobs:
        st = j.get("state", {}) or {}
        out.append({
            "name": j.get("name"),
            "enabled": j.get("enabled", True),
            "last_run_ms": j.get("lastRunAtMs") or st.get("lastRunAtMs"),
            "last_status": j.get("lastRunStatus") or st.get("lastRunStatus"),
            "next_run_ms": j.get("nextRunAtMs") or st.get("nextRunAtMs"),
            "model": (j.get("payload", {}) or {}).get("model"),
        })
    out.sort(key=lambda x: x.get("next_run_ms") or 9e18)
    return out


def pipeline_value():
    """Sum the first $-amount on each LIVE opportunity. Honest: opportunity
    'value' is free text, so this is 'parseable identified pipeline', not GAAP."""
    d = _load(OPPS, [])
    items = d if isinstance(d, list) else d.get("opportunities", d.get("items", []))
    total, priced, payload_buyers = 0, 0, 0
    for x in items:
        status = (x.get("status") or "").upper()
        if any(k in status for k in DEAD):
            continue
        if str(x.get("id", "")).startswith("PAY-"):
            payload_buyers += 1
        m = re.search(r"\$([\d,]+(?:\.\d+)?)", str(x.get("value") or ""))
        if m:
            try:
                total += float(m.group(1).replace(",", ""))
                priced += 1
            except Exception:
                pass
    return {"total": total, "priced": priced, "payload_buyers": payload_buyers,
            "opps_live": sum(1 for x in items
                             if not any(k in (x.get("status") or "").upper() for k in DEAD))}


def decisions_summary():
    d = _load(DECISIONS, [])
    items = d if isinstance(d, list) else d.get("decisions", [])
    open_items = [x for x in items if x.get("status") in ("open", "pending")]
    by_source = {}
    for x in open_items:
        s = x.get("source") or "—"
        by_source[s] = by_source.get(s, 0) + 1
    top = sorted(by_source.items(), key=lambda kv: -kv[1])[:8]
    return {"open": len(open_items),
            "by_source": [{"source": s, "open": n} for s, n in top]}


def drafts_staged():
    try:
        return len(re.findall(r"^## ", open(DRAFTS, encoding="utf-8").read(), re.M))
    except Exception:
        return 0


def build():
    ev = evals()
    reg = {c["id"]: c for c in _load(REGISTRY, {"classes": []}).get("classes", [])}
    le = last_events()
    classes = []
    g = a = r = 0
    for c in ev.get("classes", []):
        cid = c["class"]
        rc = reg.get(cid, {})
        flag = c.get("flag", "GREEN")
        g += flag == "GREEN"; a += flag == "AMBER"; r += flag == "RED"
        classes.append({
            "id": cid,
            "purpose": rc.get("purpose", ""),
            "autonomy_tier": rc.get("autonomy_tier", ""),
            "delegation_enabled": rc.get("delegation_enabled", False),
            "flag": flag,
            "override_rate": c.get("override_rate"),
            "ceiling": c.get("ceiling"),
            "decided": c.get("decided"),
            "note": c.get("note", ""),
            "last_event": le.get(cid, {}).get("ts"),
        })
    cr = crons()
    dec = decisions_summary()
    pv = pipeline_value()
    kpis = {
        "agents_green": g, "agents_amber": a, "agents_red": r,
        "classes_total": len(classes),
        "crons_total": len(cr),
        "crons_error": sum(1 for x in cr if x.get("last_status") == "error"),
        "crons_disabled": sum(1 for x in cr if not x.get("enabled")),
        "open_decisions": dec["open"],
        "pipeline_value": pv["total"],
        "pipeline_priced": pv["priced"],
        "opps_live": pv["opps_live"],
        "payload_buyers": pv["payload_buyers"],
        "drafts_staged": drafts_staged(),
        "agents_logged": agents_logged(),
    }
    return {"generated": _now(), "kpis": kpis, "classes": classes,
            "crons": cr, "decisions": dec}


def _now():
    # No Date.now shenanigans needed here (plain script); use system clock.
    import datetime
    return datetime.datetime.now().astimezone().isoformat()


def main():
    data = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w"), indent=2)
    if "--print" in sys.argv:
        print(json.dumps(data["kpis"], indent=2))
        print(f"classes={len(data['classes'])} crons={len(data['crons'])} -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
