#!/usr/bin/env python3
"""
program_state.py — builds mission-control/data/program.json for the AI Mission Desk
board, combining a seeded program skeleton with LIVE signals (decision gates,
file/driver evidence, pipeline counts). Run after the daily drivers; program.html
renders from the result so the board stops going stale. Idempotent, append-safe.
"""
import json, os, subprocess
from datetime import datetime, timezone

WS   = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control", "data")
OUT  = os.path.join(DATA, "program.json")


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def arr(obj, *keys):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in keys:
            if isinstance(obj.get(k), list):
                return obj[k]
    return []


# ---- live signals -----------------------------------------------------------
decisions = {d.get("id"): d for d in arr(load(os.path.join(DATA, "decisions.json"), []), "decisions")}
opps      = arr(load(os.path.join(DATA, "opportunities.json"), []), "opportunities")
tasks     = arr(load(os.path.join(DATA, "tasks.json"), []), "tasks")


def launchd_labels():
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=15).stdout
        return out
    except Exception:
        return ""

LD = launchd_labels()


def gate(gid):
    d = decisions.get(gid)
    if not d:
        return {"id": gid, "status": "open", "answer": None, "title": ""}
    return {"id": gid, "status": d.get("status", "open"), "answer": d.get("answer"),
            "title": d.get("title", "")}


def file_done(rel):
    return os.path.exists(os.path.join(WS, rel))


def driver_status(label_substr, state_file=None):
    live = label_substr in LD
    last = None
    if state_file:
        p = os.path.join(DATA, state_file)
        if os.path.exists(p):
            last = datetime.fromtimestamp(os.path.getmtime(p), tz=timezone.utc).isoformat()
    return ("live" if live else "scheduled"), last


# ---- deliverable resolver ---------------------------------------------------
def deliverable(name, **kw):
    st = kw.get("status_seed", "todo")
    note = ""
    if kw.get("evidence_file"):
        st = "done" if file_done(kw["evidence_file"]) else "todo"
        note = kw["evidence_file"]
    elif kw.get("evidence_driver"):
        s, last = driver_status(*kw["evidence_driver"])
        st = "live" if s == "live" else "scheduled"
        note = f"last run {last[:16].replace('T',' ')}" if last else "scheduled"
    elif kw.get("gate"):
        g = gate(kw["gate"])
        if g["status"] == "answered":
            st, note = "unblocked", f"{kw['gate']} resolved: {g['answer']}"
        else:
            st, note = "blocked", f"blocked on {kw['gate']}"
    return {"name": name, "status": st, "note": note, "owner": kw.get("owner", ""), "gate": kw.get("gate")}


def milestone_status(m):
    g = gate(m["gate"]) if m.get("gate") else None
    dels = m["deliverables"]
    done = lambda d: d["status"] in ("done", "live", "unblocked")
    started = lambda d: d["status"] in ("done", "live", "unblocked", "in_progress")
    dep = m.get("depends_on")
    dep_complete = True
    if dep:
        depm = next((x for x in MILESTONES if x["id"] == dep), None)
        dep_complete = depm and depm.get("_status") == "Complete"
    if all(done(d) for d in dels) and (not g or g["status"] == "answered"):
        return "Complete"
    # Demonstrated work outranks the dependency hold: if the deliverables are built/running,
    # the milestone is In Progress even if a go-live gate is still open.
    if any(started(d) for d in dels):
        return "In Progress"
    if not dep_complete:
        return "On Hold"
    return "On Hold"


# ---- seed -------------------------------------------------------------------
MILESTONES = [
    {"id": "PROG-001", "name": "Day 30 — Capture & Configure", "due": "2026-07-26", "gate": "D-109",
     "deliverables": [
         deliverable("Rate card encoded", evidence_file="pricing/rate-card.json"),
         deliverable("Sourcing agent live", evidence_driver=("opportunit", None)),
         deliverable("Opportunity processor running", evidence_driver=("opportunity-engine", "opportunity-processor-state.json")),
         deliverable("Flight configurator v1", gate="D-109"),
         deliverable("Lead auto-capture (inbound → CRM)", evidence_file="scripts/lead-auto-capture.py"),
         deliverable("Program lead", owner="John Quinn", status_seed="done"),
     ]},
    {"id": "PROG-002", "name": "Day 60 — Quote & Contract", "due": "2026-08-25", "gate": "D-110",
     "depends_on": "PROG-001",
     "deliverables": [
         deliverable("Agent auto-drafts mission scope + quote", evidence_file="scripts/quote_contract_pipeline.py"),
         deliverable("Contract + FAA / exemption package auto-generated", evidence_file="scripts/quote_contract_pipeline.py"),
         deliverable("Package routes into Decisions for one-click approval", evidence_file="scripts/quote_contract_pipeline.py"),
     ]},
    {"id": "PROG-003", "name": "Day 90 — First End-to-End", "due": "2026-09-25", "gate": "D-111",
     "depends_on": "PROG-002",
     "deliverables": [
         deliverable("First customer lead → signed paper through the Desk", status_seed="todo"),
         deliverable("Human-touched only: relationship + signature", status_seed="todo"),
         deliverable("Inbound-to-quote time measured (target: minutes)", status_seed="todo"),
     ]},
]
for m in MILESTONES:
    m["_status"] = milestone_status(m)
    m["status"] = m.pop("_status")
    m["gate_state"] = gate(m["gate"]) if m.get("gate") else None

# drivers
src_s, src_last = driver_status("opportunit", None)
proc_s, proc_last = driver_status("opportunity-engine", "opportunity-processor-state.json")
DRIVERS = [
    {"name": "Sourcing agent (opportunities_agent.py)", "schedule": "05:45 daily", "status": src_s, "last_run": src_last},
    {"name": "Opportunity processor (opportunity_processor.py)", "schedule": "06:15 + 18:15 daily", "status": proc_s, "last_run": proc_last},
    {"name": "Email → MC tracker (mc-email-tracker.py)", "schedule": "every 20 min", "status": ("live" if "mc-email-tracker" in LD else "scheduled"), "last_run": None},
]

# pipeline metrics
from collections import Counter
cat = Counter((o.get("category") or "Opportunity") for o in opps)
open_dec = sum(1 for d in decisions.values() if (d.get("status") or "open") == "open")
PIPELINE = {
    "opportunities": len(opps),
    "by_category": dict(cat),
    "tasks": len(tasks),
    "decisions_open": open_dec,
    "decisions_total": len(decisions),
}

GATES = [gate(g) for g in ("D-109", "D-110", "D-111")]

program = {
    "generated": datetime.now(timezone.utc).isoformat(),
    "milestones": MILESTONES,
    "drivers": DRIVERS,
    "pipeline": PIPELINE,
    "gates": GATES,
}
os.makedirs(DATA, exist_ok=True)
with open(OUT, "w") as f:
    json.dump(program, f, indent=2)

print("program.json written.")
for m in MILESTONES:
    print(f"  {m['id']} {m['status']:<12} ({sum(1 for d in m['deliverables'] if d['status'] in ('done','live','unblocked'))}/{len(m['deliverables'])} deliverables ready)")
for g in GATES:
    print(f"  {g['id']}: {g['status']}" + (f" — {g['answer']}" if g['answer'] else ""))
