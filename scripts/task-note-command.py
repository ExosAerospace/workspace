#!/usr/bin/env python3
"""task-note-command.py — act on @Exobot commands posted in a TASK note/comment.

Parity with decision-note-router, but for notes attached to a task (activities.subject = "task:<id>").
When anyone posts a task comment containing "@Exobot ...", this watcher (launchd, ~2 min) reads it
and acts:

  Structured commands (executed immediately on that task):
    @Exobot done | close | complete | resolved | paid        -> state Done
    @Exobot reopen                                            -> state To Do
    @Exobot block | hold | pause                              -> state Blocked
    @Exobot unblock | resume                                  -> state To Do
    @Exobot reassign to <name> | have <name> | give to <name> -> reassign owner (roster-resolved)
    @Exobot urgent | asap | high priority | escalate          -> bump priority
  Free-form directive ("@Exobot order a new servo", "@Exobot have Neil renew the license"):
    -> create a linked task auto-assigned to the resolved owner (or an Exo triage task).
  Anything else with @Exobot (a question/FYI):
    -> create an Exo triage task so the main Exo session handles it (nothing lost).

Every processed note gets a "✅ Exo:" confirmation reply on the task. Idempotent (state = processed
activity ids). Baseline-safe: the first run records existing @Exobot notes and does nothing, so it
never fires on historical comments. Deterministic; local Ollama only for owner routing (bounded).
"""
import json, os, re, urllib.request, urllib.parse
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
ROSTER = os.path.join(WS, "mission-control", "data", "routing-roster.json")
STATE = os.path.join(WS, "logs", "task-note-command-state.json")
LOG = os.path.join(WS, "logs", "task-note-command.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"

# Skip notes authored by automation (prevent loops / only act on human commands).
SKIP_OWNERS = re.compile(r"^(exo|decisions|mission control|mc\b|expense-workflow|.*-router|.*-watcher)", re.I)
ACTION = re.compile(r"\b(handle|take care of|manage|order|buy|purchase|procure|source|renew|prepare|"
                    r"draft|send|fix|schedule|call|contact|reach\s?out|follow\s?up|investigate|"
                    r"resolve|create|build|arrange|coordinate|set\s?up|research|file|submit|pay|book|"
                    r"quote|email|write|update|review)\b", re.I)
DOMAIN = [
    (r"expense|invoice|reimburs|payment|payroll|budget|accounting|quickbooks|finance|\bap\b", "kballard@exosaero.com"),
    (r"machin|fabricat|production|work order|shop\b|tooling|composite layup|manufactur|facilit|crane|building|maintenance", "peaton@exosaero.com"),
    (r"avionics|sensor|electronics|wiring|instrumentation|daq|test bench|flight software|gnc", "snorsworthy@exosaero.com"),
    (r"software|mission control|website|web app|dashboard|\bbug\b|database|server|\bit\b|login", "exo@exosaero.com"),
    (r"sales|customer|investor|outreach|marketing|payload sale|\blead\b|crm|business develop", "lquinn@exosaero.com"),
    (r"japan|hospo|space cotan|kumazawa", "toshihisa@exosaero.com"),
    (r"export|itar|\bear\b|licens|compliance|cmmc|cui|part 450|faa", "nmilburn@exosaero.com"),
    (r"contract|legal|agreement|\bnda\b|mnda|counsel|term sheet", "jquinn@exosaero.com"),
]


def logline(m):
    try:
        with open(LOG, "a") as f: f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception: pass


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def supa(method, path, body=None):
    req = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode(); return json.loads(t) if t else []
    except Exception as e:
        logline(f"WARN supa {method} {path[:40]}: {e}"); return None


def reply(taskid, msg):
    supa("POST", "activities", {"type": "task_note", "subject": f"task:{taskid}",
         "body": msg, "owner": "Exo", "status": "completed"})


# Common nicknames -> canonical @exosaero email (names people actually type).
ALIASES = {"lizi": "lquinn@exosaero.com", "liz": "lquinn@exosaero.com", "elizabeth": "lquinn@exosaero.com",
           "toshi": "toshihisa@exosaero.com", "vic": "vcastilleja@exosaero.com", "victor": "vcastilleja@exosaero.com",
           "phil": "peaton@exosaero.com", "steve": "snorsworthy@exosaero.com", "neil": "nmilburn@exosaero.com",
           "kyle": "kballard@exosaero.com", "mike": "mtalley@exosaero.com", "russ": "rblink@exosaero.com",
           "andrew": "aoverman@exosaero.com", "jon": "jquinn@exosaero.com", "john": "jquinn@exosaero.com"}


def resolve_person(text, roster):
    """First roster person whose nickname, first, or full name appears in the directive text."""
    low = text.lower()
    by_email = {p["email"].lower(): p for p in roster}
    # explicit "to/have/give/assign/for <Name>" first (catches nicknames via ALIASES)
    m = re.search(r"\b(?:to|have|give to|assign(?:\s+to)?|for|delegate to)\s+([A-Za-z]+)", low)
    cand = m.group(1) if m else None
    if cand:
        if cand in ALIASES and ALIASES[cand] in by_email: return by_email[ALIASES[cand]]
        for p in roster:
            if p["first"].lower() == cand: return p
    # any nickname token present
    for tok, em in ALIASES.items():
        if re.search(rf"\b{tok}\b", low) and em in by_email: return by_email[em]
    for p in roster:
        if p["name"].lower() in low or re.search(rf"\b{re.escape(p['first'].lower())}\b", low):
            return p
    return None


def domain_owner(text, by_email):
    for pat, em in DOMAIN:
        if re.search(pat, text, re.I): return by_email.get(em)
    return None


def directive_after(body):
    """Return the text following the FIRST @Exobot mention (that's the command)."""
    m = re.search(r"@exo(?:bot)?\b[:,\-\s]*(.*)", body, re.I | re.S)
    return (m.group(1) if m else body).strip()


def main():
    import sys
    roster = load(ROSTER, [])
    by_email = {p["email"].lower(): p for p in roster}
    state = load(STATE, None)

    # Pull recent task comments mentioning @Exobot.
    q = ("activities?select=id,type,subject,body,owner,created_at"
         "&type=in.(task_note,comment)"
         "&body=ilike." + urllib.parse.quote("*@exo*") +
         "&order=created_at.desc&limit=400")
    rows = supa("GET", q) or []
    # keep only ones truly mentioning @exobot/@exo on a task:<id>
    def taskid_of(r):
        m = re.match(r"task:(\d+)$", (r.get("subject") or ""))
        return m.group(1) if m else None
    cmds = [r for r in rows if taskid_of(r) and re.search(r"@exo(bot)?\b", r.get("body") or "", re.I)]

    if state is None:  # BASELINE — record existing, act on nothing
        state = {"seen": [r["id"] for r in cmds]}
        json.dump(state, open(STATE, "w"))
        logline(f"baseline {len(cmds)}"); print(f"baseline {len(cmds)}"); return

    seen = set(state.get("seen", []))
    acted = 0
    for r in cmds:
        aid = r["id"]
        if aid in seen: continue
        seen.add(aid)
        owner_of_note = (r.get("owner") or "")
        if SKIP_OWNERS.match(owner_of_note.strip()):
            continue  # automation-authored, not a human command
        taskid = taskid_of(r)
        body = r.get("body") or ""
        cmd = directive_after(body)
        low = cmd.lower()
        did = []

        # 1) reassignment
        if re.search(r"\b(reassign|assign|hand|give|have|route|delegate)\b", low):
            p = resolve_person(cmd, roster)
            if p:
                supa("PATCH", f"tasks?id=eq.{taskid}", {"owner": p["name"], "assigned_to": p["name"],
                     "assigned_email": p["email"], "assigned_at": datetime.now(timezone.utc).isoformat()})
                did.append(f"reassigned to {p['name']}")
        # 2) state changes
        if re.search(r"\b(done|close[d]?|complete[d]?|resolved?|paid|finished)\b", low):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "Done"}); did.append("marked Done")
        elif re.search(r"\b(reopen|re-open)\b", low):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "To Do"}); did.append("reopened")
        elif re.search(r"\b(unblock|resume|proceed)\b", low):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "To Do"}); did.append("unblocked")
        elif re.search(r"\b(block|blocked|on hold|hold|pause|waiting)\b", low):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "Blocked"}); did.append("set Blocked")
        # 3) priority bump
        if re.search(r"\b(urgent|asap|high priority|top priority|escalate|critical)\b", low):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"priority": 92}); did.append("prioritized")

        if did:
            reply(taskid, f"✅ Exo: {', '.join(did)} (per {owner_of_note or 'note'}: “{cmd[:120]}”).")
            logline(f"act {aid} task {taskid}: {did}"); acted += 1; continue

        # 4) free-form directive -> route to the right owner as a linked task
        if ACTION.search(cmd):
            p = resolve_person(cmd, roster) or domain_owner(cmd, by_email)
            if p:
                nid = supa("POST", "tasks", {"title": cmd[:70], "owner": p["name"], "assigned_to": p["name"],
                     "assigned_email": p["email"], "state": "To Do", "priority": 74, "category": "Task",
                     "source": "task-note-command", "tags": ["note-routed"],
                     "assigned_at": datetime.now(timezone.utc).isoformat(),
                     "description": f"Routed from a note on task #{taskid} (by {owner_of_note}). Directive: {cmd}"})
                who = p["name"]
            else:
                nid = supa("POST", "tasks", {"title": f"[route] {cmd[:64]}", "owner": "Exo",
                     "assigned_email": "exo@exosaero.com", "state": "To Do", "priority": 74, "category": "Task",
                     "source": "task-note-command", "tags": ["note-routed", "needs-owner"],
                     "description": f"From a note on task #{taskid} (by {owner_of_note}). Directive: {cmd}. Exo to own/assign."})
                who = "Exo (triage)"
            newid = nid[0]["id"] if nid else "?"
            reply(taskid, f"✅ Exo: created task #{newid} → {who} for “{cmd[:110]}”.")
            logline(f"route {aid} task {taskid} -> {who} #{newid}"); acted += 1; continue

        # 5) unrecognized @Exobot note (question/FYI) -> Exo triage so the main session handles it
        nid = supa("POST", "tasks", {"title": f"[note] {cmd[:60] or 'follow up'} (task #{taskid})",
             "owner": "Exo", "assigned_email": "exo@exosaero.com", "state": "To Do", "priority": 70,
             "category": "Task", "source": "task-note-command", "tags": ["note-routed", "needs-attention"],
             "description": f"@Exobot note on task #{taskid} (by {owner_of_note}): {cmd}. Exo to review and act."})
        newid = nid[0]["id"] if nid else "?"
        reply(taskid, f"✅ Exo: noted — queued as #{newid} for review.")
        logline(f"triage {aid} task {taskid} -> #{newid}"); acted += 1

    state["seen"] = list(seen)[-4000:]  # bound growth
    json.dump(state, open(STATE, "w"))
    print(f"acted {acted}")


main()
