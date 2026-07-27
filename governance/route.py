#!/usr/bin/env python3
"""
route.py -- execute-vs-escalate router for the agent fleet.

Turns the registry.json decision_boundary into two callable paths an agent uses
per item:

  escalate(payload, agent_class)  -> tags the Decisions-inbox payload with
        agentClass + correlationId and logs a `surfaced_decision` event, so the
        item rides the Human Review Queue AND becomes exact per-class eval data.
        Use for one-way doors (external send, go/no-go, commitment).

  executed(agent_class, action, item_id) -> logs an `executed` event for a
        reversible action the agent took itself (file/tag/dedupe/auto-archive).
        Use for the reversible tail that no longer needs the inbox.

Design rule: ESCALATE IS THE DEFAULT. The execute-path is only for actions the
agent class's decision_boundary explicitly lists and that are reversible +
logged + rollback-able. When in doubt, escalate.

One correlation id per agent class per process, shared across both paths.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import govlog  # noqa: E402  (same dir)

_runs = {}

# Decisions inbox (Human Review Queue) endpoint + token file.
_WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECISIONS_API = "http://localhost:8080/api/decisions/ingest"
DTOKEN_FILE = os.path.join(_WS, "mission-control", "data", ".decisions-token")


def _decisions_token():
    try:
        return open(DTOKEN_FILE, encoding="utf-8").read().strip()
    except Exception:
        return ""


def escalate_and_file(payload, agent_class):
    """One-way door: tag the payload (escalate) AND POST it to the Decisions inbox
    so it rides the Human Review Queue and becomes per-class eval data. Idempotent
    on the caller's dedupeKey. Returns True on a 2xx. Soft: never raises."""
    import json as _json
    import urllib.request as _url
    tagged = escalate(payload, agent_class)
    try:
        req = _url.Request(
            DECISIONS_API, data=_json.dumps(tagged).encode(),
            headers={"Content-Type": "application/json",
                     "X-Exo-Token": _decisions_token()})
        with _url.urlopen(req, timeout=20) as r:
            return r.status in (200, 201)
    except Exception:
        return False


def delegation_on(agent_class):
    """Return the explicit per-class delegation_enabled flag from registry.json.

    Delegation (the execute-path) is OFF unless a class is deliberately enabled.
    Returns False on a missing flag, a missing class, or any read/parse error.
    """
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "registry.json")
        with open(path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        for cls in registry.get("classes", []):
            if cls.get("id") == agent_class:
                return bool(cls.get("delegation_enabled", False))
        return False
    except Exception:
        return False


def _run(agent_class):
    if agent_class not in _runs:
        _runs[agent_class] = govlog.new_run(agent_class)
    return _runs[agent_class]


def correlation_id(agent_class):
    return _run(agent_class)["run_id"]


def escalate(payload, agent_class):
    """Return the payload tagged for the inbox + eval attribution; logs it."""
    r = _run(agent_class)
    out = dict(payload)
    out.setdefault("agentClass", agent_class)
    out["correlationId"] = r["run_id"]
    govlog.event(r, "surfaced_decision", status="info",
                 decision_id=str(out.get("dedupeKey") or out.get("id") or ""),
                 outcome="pending")
    return out


def executed(agent_class, action, item_id="", **fields):
    """Log a reversible action the agent took itself (no inbox round-trip)."""
    r = _run(agent_class)
    govlog.event(r, "executed", status="ok", detail=action,
                 item_id=str(item_id), **fields)


if __name__ == "__main__":
    p = escalate({"dedupeKey": "demo-1", "title": "t"}, "opportunity-engine")
    print("escalated:", p)
    executed("opportunity-engine", "auto-archive", "OPP-9", score=12)
    print("ok")
