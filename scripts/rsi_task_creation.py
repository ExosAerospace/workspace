#!/usr/bin/env python3
"""rsi_task_creation.py — §15 of the weekly RSI: the REPLY-FIRST / EXO-FIRST recursive loop (Jon 2026-10-03).

Rule under audit:
  - A question/FYI/directive on a task never becomes a new top-level task unless explicitly asked
    ("@exo task: ..."). It's answered on the task, or becomes a SUBTASK (parent:<id>).
  - Exo does anything it is capable of; a human gets at most the decision/approval or the one
    hands-on step (source=exo-handoff subtasks).

Measures (7 days, top-level tasks only — subtasks are not new work):
  created vs closed (net), note-spawned top-level violations, Exo-handoffs to humans, and
  human-assigned subtasks that Exo could plausibly have done (sampled for the review).
Exception-only output: if net <= 0 and 0 violations, prints a single PASS line.
Escalation: net > 0 two weeks running -> the RSI proposes the next fix as a Decision for Jon.

Usage: python3 scripts/rsi_task_creation.py   (or import: report_section(days))
"""
import json, os, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
HIST = os.path.join(WS, "logs", "rsi-task-creation-history.jsonl")
NOTE_SOURCES = ("task-note-command", "decision-note-router", "capstone-capture")


def _key():
    return json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]


def _all(since):
    k, out, off = _key(), [], 0
    since = urllib.parse.quote(since)
    while True:
        url = (f"{SB}/tasks?select=id,title,state,owner,source,tags,created_at,completed_at"
               f"&or=(created_at.gte.{since},completed_at.gte.{since})&order=id&limit=1000&offset={off}")
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            url, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=60))
        out += r
        if len(r) < 1000:
            return out
        off += 1000


def _sub(t):
    return any(str(g).startswith("parent:") for g in (t.get("tags") or []))


def measure(days=7):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _all(since)
    new = [t for t in rows if (t.get("created_at") or "") >= since]
    top = [t for t in new if not _sub(t)]
    closed = [t for t in rows if not _sub(t) and (t.get("completed_at") or "") >= since
              and t.get("state") in ("Done", "Cancelled")]
    viol = [t for t in top if t.get("source") in NOTE_SOURCES
            and not {"explicit-task", "decision-routed", "utd-question"} & set(t.get("tags") or [])]
    handoffs = [t for t in new if t.get("source") == "exo-handoff"]
    human_subs = [t for t in new if _sub(t) and (t.get("owner") or "Exo") != "Exo"
                  and t.get("source") != "exo-handoff"]
    exo_subs = [t for t in new if _sub(t) and (t.get("owner") or "") == "Exo"]
    return {"ts": datetime.now(timezone.utc).isoformat(), "days": days,
            "created": len(top), "closed": len(closed), "net": len(top) - len(closed),
            "violations": [t["id"] for t in viol], "handoffs": len(handoffs),
            "human_subtasks": [(t["id"], t.get("owner"), (t.get("title") or "")[:60]) for t in human_subs][:10],
            "exo_subtasks": len(exo_subs)}


def report_section(days=7):
    m = measure(days)
    prev = []
    try:
        prev = [json.loads(l) for l in open(HIST)][-1:]
    except Exception:
        pass
    with open(HIST, "a") as f:
        rec = {k: m[k] for k in ("ts", "created", "closed", "net", "handoffs", "exo_subtasks")}
        rec["violations"] = len(m["violations"])
        f.write(json.dumps(rec) + "\n")
    L = ["\n## 15. Reply-first / Exo-first task loop"]
    if m["net"] <= 0 and not m["violations"]:
        L.append(f"- PASS: top-level created {m['created']} ≤ closed {m['closed']}; 0 note-spawned violations; "
                 f"Exo handled {m['exo_subtasks']} in-task, {m['handoffs']} human handoff(s).")
        return L
    L.append(f"- top-level created {m['created']} vs closed {m['closed']} → net {m['net']:+d} "
             f"(Exo in-task items {m['exo_subtasks']}, human handoffs {m['handoffs']})")
    if m["violations"]:
        L.append(f"- VIOLATIONS (note-spawned top-level tasks, no explicit ask): {m['violations'][:15]} "
                 "→ fix the generating script this week")
    if m["human_subtasks"]:
        L.append("- human-assigned subtasks to sample for 'could Exo have done it?': " +
                 "; ".join(f"#{i} {o}: {t}" for i, o, t in m["human_subtasks"][:6]))
    if m["net"] > 0 and prev and prev[0].get("net", 0) > 0:
        L.append("- ESCALATE: net > 0 two weeks running → propose the next lever as a Decision "
                 "(stale-close threshold, subtask follow-up nudges, or a new generator fix).")
    return L


if __name__ == "__main__":
    print("\n".join(report_section(7)))
