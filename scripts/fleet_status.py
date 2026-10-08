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
    "/Users/exomac/.local/share/mise/shims/openclaw"
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


def agents_deployed(cr):
    """Every live agent supporting Exos work (Jon 10/8): loaded com.exos.* launchd agents on this Mac
    + enabled OpenClaw scheduled agents. Registered count shown alongside for coverage."""
    import subprocess
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=20).stdout
        launchd = sorted({ln.split()[-1] for ln in out.splitlines() if ln.split() and ln.split()[-1].startswith("com.exos.")})
    except Exception:
        launchd = []
    crons_on = [x for x in cr if x.get("enabled")]
    try:
        reg = json.load(open(os.path.join(WS, "mission-control", "data", "agent-registry.json"))).get("agents", [])
        registered = sum(1 for a in reg if "retired" not in str(a.get("lifecycle", "")))
    except Exception:
        registered = None
    return {"total": len(launchd) + len(crons_on), "launchd": len(launchd), "crons": len(crons_on), "registered": registered}


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
    """Sum the identified $-amount on each LIVE opportunity. Honest: opportunity
    'value' is free text, so this is 'parseable identified pipeline', not GAAP.
    A won/booked deal can carry an explicit numeric contract_value (preferred,
    exact) plus payload_value / amount_received and a payload_buyer flag. For
    free-text-only opps we keep the conservative bare-number parse — deliberately
    NOT honoring K/M/B suffixes there, because the corpus mixes market-size
    mentions ('$6B program', '$20T') that would otherwise inflate the total."""
    d = _load(OPPS, [])
    items = d if isinstance(d, list) else d.get("opportunities", d.get("items", []))
    total, priced, payload_buyers = 0, 0, 0
    payload_value, payload_received = 0, 0
    for x in items:
        status = (x.get("status") or "").upper()
        if any(k in status for k in DEAD):
            continue
        is_payload = str(x.get("id", "")).startswith("PAY-") or bool(
            x.get("payload_buyer"))
        if is_payload:
            payload_buyers += 1
        # Explicit numeric contract_value wins (exact); else legacy free-text parse.
        cv = x.get("contract_value")
        if cv is not None:
            val = float(cv)
        else:
            m = re.search(r"\$([\d,]+(?:\.\d+)?)", str(x.get("value") or ""))
            val = float(m.group(1).replace(",", "")) if m else None
        # BLK3 PAY- prospects all carry the same full-bay LIST price — summing them inflates the
        # pipeline (~$60M+ of identical list prices), so they're counted as buyers, not dollars (10/8).
        list_priced = str(x.get("id", "")).startswith("PAY-") and x.get("contract_value") is None
        if val and not list_priced:
            total += val
            priced += 1
        # Booked payload value = only deals explicitly tagged payload_value
        # (set when a payload contract is won), not prospective pipeline.
        if x.get("payload_value") is not None:
            payload_value += float(x.get("payload_value"))
        if x.get("amount_received") is not None:
            payload_received += float(x.get("amount_received"))
    # Booked payload value also includes signed Payload Orders and curated contracts of record
    # (config/payload-booked.json, e.g. entX OPP-007) — previously only opp stamps counted, so $0 showed.
    seen = {str(x.get("id")) for x in items if x.get("payload_value") is not None}
    po = _load(os.path.join(WS, "mission-control", "data", "payload-orders.json"), [])
    for o in (po if isinstance(po, list) else po.get("orders", [])):
        if "cancel" in str(o.get("status") or "").lower():
            continue
        payload_value += float(o.get("contract_value") or 0)
        payload_received += float(o.get("amount_received") or o.get("amount_paid") or 0)
    for c in _load(os.path.join(WS, "config", "payload-booked.json"), {}).get("contracts", []):
        if str(c.get("id")) in seen:
            continue
        payload_value += float(c.get("contract_value") or 0)
        payload_received += float(c.get("amount_received") or 0)
    return {"total": total, "priced": priced, "payload_buyers": payload_buyers,
            "payload_value": payload_value, "payload_received": payload_received,
            "opps_live": sum(1 for x in items
                             if not any(k in (x.get("status") or "").upper() for k in DEAD))}


def decisions_summary():
    d = _load(DECISIONS, [])
    items = d if isinstance(d, list) else d.get("decisions", [])
    open_items = [x for x in items if x.get("status") in ("open", "pending")]
    by_source, by_owner = {}, {}
    for x in open_items:
        s = x.get("source") or "—"
        by_source[s] = by_source.get(s, 0) + 1
        # legacy/unassigned decisions default to Jon (the original "Needs Jon" queue)
        o = x.get("assignedTo") or "jquinn@exosaero.com"
        by_owner[o] = by_owner.get(o, 0) + 1
    top = sorted(by_source.items(), key=lambda kv: -kv[1])[:8]
    owners = sorted(by_owner.items(), key=lambda kv: -kv[1])
    return {"open": len(open_items),
            "by_source": [{"source": s, "open": n} for s, n in top],
            "by_owner": [{"owner": o, "open": n} for o, n in owners]}


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
        "payload_value": pv["payload_value"],
        "payload_received": pv["payload_received"],
        "drafts_staged": drafts_staged(),
        "agents_logged": agents_logged(),
    }
    try:   # live health from the hourly agent_eval run (every checked agent), not the 12 legacy classes
        last = [ln for ln in open(os.path.join(WS, "logs", "agent-eval.log")) if "] eval: " in ln][-1]
        m = re.search(r"eval: (\d+) OK / (\d+) WARN / (\d+) FAIL across (\d+)", last)
        if m:
            kpis.update({"eval_ok": int(m.group(1)), "eval_warn": int(m.group(2)), "eval_fail": int(m.group(3)),
                         "eval_total": int(m.group(4)), "eval_at": last[1:20]})
    except Exception:
        pass
    dep = agents_deployed(cr)
    kpis.update({"agents_deployed": dep["total"], "agents_deployed_launchd": dep["launchd"],
                 "agents_deployed_crons": dep["crons"], "agents_registered": dep["registered"]})
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
