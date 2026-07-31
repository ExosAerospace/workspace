#!/usr/bin/env python3
"""
govlog.py -- the Searchable-Logs-with-Correlation-IDs pillar (Python side).

Every autonomous worker (cron, research agent, opportunity processor, email
router, resolver) imports this and emits structured events to a single
append-only JSONL substrate: governance/events.jsonl.

The point is the *correlation id*: one agent run == one run_id, threaded through
every event and (via dal.js) into the ERP audit_log. That makes a chain of
agent actions queryable back to the decision that spawned them -- the Four
Pillars "Searchable Logs with Correlation IDs" requirement, and the substrate
the eval runner (run_evals.py) reads to compute override rate and detect Quiet
Drift.

Zero dependencies (stdlib only). Safe to import from any script.

Usage:
    from governance.govlog import new_run, event
    run = new_run("research-grant-scanner")          # correlation id for this run
    event(run, "start")
    event(run, "found", detail="3 grants", count=3)
    event(run, "surfaced_decision", decision_id="D-117", outcome="pending")
    event(run, "end", status="ok")
"""
import json
import os
import sys
import time
import uuid

_ROOT = os.path.dirname(os.path.abspath(__file__))
_LOG = os.path.join(_ROOT, "events.jsonl")


def new_run(agent: str) -> dict:
    """Open a correlated run. Returns a context dict carrying the correlation id."""
    return {"agent": agent, "run_id": uuid.uuid4().hex[:16]}


def event(run: dict, event: str, status: str = "info", detail: str = "", **fields) -> str:
    """Append one structured event. Returns the run_id (the correlation id)."""
    rid = run.get("run_id") if isinstance(run, dict) else str(run)
    agent = run.get("agent") if isinstance(run, dict) else "unknown"
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "correlation_id": rid,
        "agent": agent,
        "event": event,
        "status": status,
    }
    if detail:
        row["detail"] = detail
    row.update(fields)
    line = json.dumps(row, ensure_ascii=False, default=str)
    # Append is atomic for small lines on POSIX; open per-call to stay fork-safe.
    with open(_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return rid


if __name__ == "__main__":
    # Smoke test / CLI: `python3 govlog.py <agent> <event> [detail]`
    a = sys.argv[1] if len(sys.argv) > 1 else "govlog-selftest"
    r = new_run(a)
    event(r, sys.argv[2] if len(sys.argv) > 2 else "selftest",
          detail=sys.argv[3] if len(sys.argv) > 3 else "ok")
    print(f"wrote event run_id={r['run_id']} -> {_LOG}")
