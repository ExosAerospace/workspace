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


# Substrings that mark a transient network/service blip (ProtonMail Bridge briefly
# down, DNS hiccup, upstream 5xx/reset/timeout) rather than a code defect. These are
# expected — the worker just couldn't reach mail/net this cycle and should skip, not
# page. Sustained outages still surface via cron-failure-watchdog (launchd exit!=0 x2).
_TRANSIENT_MARKERS = (
    "connection refused", "errno 61", "errno 8", "errno 51", "errno 54",
    "errno 60", "errno 65", "nodename nor servname", "name or service not known",
    "temporary failure in name resolution", "getaddrinfo failed",
    "connection reset", "connection aborted", "network is unreachable",
    "no route to host", "urlopen error", "max retries exceeded", "timed out",
    "timeout", "socket error: eof", "eof occurred", "bad gateway",
    " 502", " 503", " 504", "read timed out", "connection timed out",
)


def is_transient(exc) -> bool:
    """True if `exc` (an Exception OR a text blob like captured stderr) looks like a
    transient network/service outage that should be skipped, not flagged as broken."""
    try:
        import socket, urllib.error
        if isinstance(exc, (ConnectionError, socket.gaierror, socket.timeout, TimeoutError,
                            urllib.error.URLError)):
            return True
        if isinstance(exc, OSError) and getattr(exc, "errno", None) in (8, 51, 54, 60, 61, 65):
            return True
    except Exception:
        pass
    s = str(exc).lower()
    return any(m in s for m in _TRANSIENT_MARKERS)


def log_uncaught(run: dict, exc) -> str:
    """Route an uncaught exception to the log: transient blips become a benign
    'transient_skip' (status=transient, ignored by the completion watchdog); genuine
    failures stay a real 'error'. Returns the correlation id."""
    if is_transient(exc):
        return event(run, "transient_skip", status="transient", detail=str(exc)[:160])
    return event(run, "error", status="error", detail=str(exc)[:160])


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
