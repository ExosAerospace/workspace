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
  ANY note containing a question mark "?" (even WITHOUT @exo) is auto-answered on the task
    -> routed to the answer loop; Exo posts the answer on the task (Jon 2026-09-10). Guards:
       never answers Exo's own posts, and won't retro-answer questions older than QM_SINCE.

Every processed note gets a "✅ Exo:" confirmation reply on the task. Idempotent (state = processed
activity ids). Baseline-safe: the first run records existing @Exobot notes and does nothing, so it
never fires on historical comments. Deterministic; local Ollama only for owner routing (bounded).
"""
import json, os, re, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
ROSTER = os.path.join(WS, "mission-control", "data", "routing-roster.json")
STATE = os.path.join(WS, "logs", "task-note-command-state.json")
LOG = os.path.join(WS, "logs", "task-note-command.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"

# Trigger recognition — accept all three forms, case-insensitively:
#   "@exo" / "@exobot" text (any case: @Exo, @EXO, @ExoBot …)
#   the Discord role/user mention token the client inserts when you type "@Exo"
#   e.g. <@&1501704079901069386> (role), <@1501704079901069386> / <@!…> (user).
EXO_MENTION_IDS = ["1501704079901069386"]  # @Exobot Discord role
MENTION_RE = re.compile(r"@exo(?:bot)?\b|<@[&!]?(?:" + "|".join(EXO_MENTION_IDS) + r")>", re.I)
# Auto-answer ANY task note that contains a question mark, even without @exo (Jon 2026-09-10).
# QM_SINCE prevents a retroactive burst: question notes older than this are recorded-as-seen and
# NOT answered (so deploying the feature doesn't re-answer a week of historical questions).
QM_SINCE = "2026-09-10T17:00:00+00:00"

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


def flag_awaiting(taskid):
    """Make an unanswered @Exobot question VISIBLE: tag the original task 'awaiting-exo-answer' and
    bump its priority so it rises to the top of the board. The answerer clears the tag when it posts
    the answer. This is why questions no longer silently vanish into a background queue."""
    try:
        cur = supa("GET", f"tasks?id=eq.{taskid}&select=tags,priority") or []
        tags = (cur[0].get("tags") or []) if cur else []
        if "awaiting-exo-answer" not in tags:
            tags = tags + ["awaiting-exo-answer"]
        pr = max(int(cur[0].get("priority") or 0), 90) if cur else 90
        supa("PATCH", f"tasks?id=eq.{taskid}", {"tags": tags, "priority": pr})
    except Exception as e:
        logline(f"WARN flag_awaiting {taskid}: {e}")


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


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_due(text):
    """Parse a due date from 'due <date>' in a command; ISO or None. Future-biased."""
    from datetime import date as _date
    m = re.search(r"\bdue\s*(?:date)?\s*:?\s*([^\n.;]{0,30})", text, re.I)
    w = (m.group(1) if m else text).lower()
    today = _date.today()
    mm = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z.]*\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(20\d{2}))?", w)
    if mm:
        try:
            d = _date(int(mm.group(3) or today.year), _MONTHS[mm.group(1)[:3]], int(mm.group(2)))
            if not mm.group(3) and d < today: d = _date(d.year + 1, d.month, d.day)
            return d.isoformat()
        except ValueError: pass
    mm = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b", w)
    if mm:
        try:
            d = _date(int(mm.group(3) or today.year), int(mm.group(1)), int(mm.group(2)))
            if not mm.group(3) and d < today: d = _date(d.year + 1, d.month, d.day)
            return d.isoformat()
        except ValueError: pass
    return None


def directive_after(body):
    """Return the command text after the FIRST trigger (@exo/@exobot text OR an Exobot mention token)."""
    m = MENTION_RE.search(body or "")
    tail = (body or "")[m.end():] if m else (body or "")
    tail = re.sub(r"<@[&!]?\d+>", "", tail)  # strip any residual mention tokens
    return tail.strip(" :,-—\n\t")


def main():
    import sys
    roster = load(ROSTER, [])
    by_email = {p["email"].lower(): p for p in roster}
    state = load(STATE, None)

    # Pull recent task comments (last 7 days) and filter for the trigger in Python — the DB can't
    # gate on the role-mention token, so we fetch by recency and match with MENTION_RE.
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    q = ("activities?select=id,type,subject,body,owner,created_at"
         "&type=in.(task_note,comment)"
         "&created_at=gte." + urllib.parse.quote(since) +
         "&order=created_at.desc&limit=400")
    rows = supa("GET", q) or []
    # keep only ones truly mentioning @exo/@exobot OR the Exobot mention token, on a task:<id>
    def taskid_of(r):
        m = re.match(r"task:(\d+)$", (r.get("subject") or ""))
        return m.group(1) if m else None
    # Candidates: notes that @-mention Exo OR that contain a question mark (auto-answer).
    cmds = [r for r in rows if taskid_of(r)
            and (MENTION_RE.search(r.get("body") or "") or ("?" in (r.get("body") or "")))]

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
        # Question-mark auto-answer: a note WITHOUT @exo that contains "?" is routed straight to
        # the answer loop (no command parsing — a plain question must never trigger done/close/etc.).
        if not MENTION_RE.search(body):
            if body.lstrip().startswith("✅ Exo"):
                continue  # never answer Exo's own posts
            if (r.get("created_at") or "") < QM_SINCE:
                continue  # pre-feature question: already marked seen; do not retro-answer
            qtext = body.strip()
            nid = supa("POST", "tasks", {"title": f"[note] {qtext[:60] or 'question'} (task #{taskid})",
                 "owner": "Exo", "assigned_email": "exo@exosaero.com", "state": "To Do", "priority": 70,
                 "category": "Task", "source": "task-note-command",
                 "tags": ["note-routed", "needs-attention", "auto-question"],
                 "description": f"Question posted on task #{taskid} (by {owner_of_note or 'team'}): {qtext}. Exo to review and answer."})
            newid = nid[0]["id"] if nid else "?"
            flag_awaiting(taskid)
            reply(taskid, f"✅ Exo: got your question — I'll post the answer here on this task shortly (ref #{newid}).")
            logline(f"auto-q {aid} task {taskid} -> #{newid}"); acted += 1; continue
        cmd = directive_after(body)
        low = cmd.lower()
        did = []
        # A structured command must be the LEADING intent — only match state/priority/reassign
        # verbs in the first few words. Otherwise a keyword buried in a sentence/question
        # (e.g. "...still holding the old Blocked State- fix it") wrongly fires a state change.
        # Long notes (a real instruction or question) fall through to free-form / question handling.
        words = low.split()
        cmdzone = " ".join(words[:5])
        is_short_cmd = len(words) <= 6

        # 1) reassignment (leading verb only)
        if re.search(r"\b(reassign|assign|hand|give|have|route|delegate)\b", cmdzone):
            p = resolve_person(cmd, roster)
            if p:
                supa("PATCH", f"tasks?id=eq.{taskid}", {"owner": p["name"], "assigned_to": p["name"],
                     "assigned_email": p["email"], "assigned_at": datetime.now(timezone.utc).isoformat()})
                did.append(f"reassigned to {p['name']}")
        # 2) state changes — leading verb AND a short note (guards against incidental keywords)
        if is_short_cmd and re.search(r"\b(done|close[d]?|complete[d]?|resolved?|paid|finished)\b", cmdzone):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "Done"}); did.append("marked Done")
        elif is_short_cmd and re.search(r"\b(reopen|re-open)\b", cmdzone):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "To Do"}); did.append("reopened")
        elif is_short_cmd and re.search(r"\b(unblock|resume|proceed)\b", cmdzone):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "To Do"}); did.append("unblocked")
        elif is_short_cmd and re.search(r"\b(block|blocked|on hold|hold|pause|waiting)\b", cmdzone):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "To Do"}); did.append("moved to To Do (not started)")  # "Blocked" retired (Jon 9/2)
        # 3) priority bump (leading + short)
        if is_short_cmd and re.search(r"\b(urgent|asap|high priority|top priority|escalate|critical)\b", cmdzone):
            supa("PATCH", f"tasks?id=eq.{taskid}", {"priority": 92}); did.append("prioritized")
        # 3b) due date  (@Exobot due 8/17  |  due Aug 17)
        if re.search(r"\bdue\b", low):
            iso = parse_due(cmd)
            if iso:
                supa("PATCH", f"tasks?id=eq.{taskid}", {"due_date": iso}); did.append(f"due {iso}")

        # subtask: "@exo subtask: <title>" -> create a child task under THIS task (parent:<id> tag)
        msub = re.match(r"subtask\s*[:\-]?\s+(.+)", cmd, re.I)
        if msub and msub.group(1).strip():
            stitle = msub.group(1).strip()[:70]
            par = (supa("GET", f"tasks?id=eq.{taskid}&select=category,owner,priority") or [{}])
            par = par[0] if par else {}
            child = supa("POST", "tasks", {"title": stitle, "owner": par.get("owner") or owner_of_note or "Jon",
                 "state": "To Do", "priority": par.get("priority") or 60, "category": par.get("category"),
                 "source": "subtask", "tags": ["subtask", "parent:" + str(taskid)]})
            cid = child[0]["id"] if child else "?"
            did.append(f"added subtask #{cid}: {stitle}")

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
                flag_awaiting(taskid)   # Exo-owned directive: surface the ORIGINAL task to the top too
            newid = nid[0]["id"] if nid else "?"
            reply(taskid, f"✅ Exo: created task #{newid} → {who} for “{cmd[:110]}”.")
            logline(f"route {aid} task {taskid} -> {who} #{newid}"); acted += 1; continue

        # 5) unrecognized @Exobot note (question/FYI) -> Exo triage so the main session handles it
        nid = supa("POST", "tasks", {"title": f"[note] {cmd[:60] or 'follow up'} (task #{taskid})",
             "owner": "Exo", "assigned_email": "exo@exosaero.com", "state": "To Do", "priority": 70,
             "category": "Task", "source": "task-note-command", "tags": ["note-routed", "needs-attention"],
             "description": f"@Exobot note on task #{taskid} (by {owner_of_note}): {cmd}. Exo to review and act."})
        newid = nid[0]["id"] if nid else "?"
        flag_awaiting(taskid)   # surface the ORIGINAL task to the top until answered
        reply(taskid, f"✅ Exo: got your question — I'll post the answer here on this task shortly (ref #{newid}).")
        logline(f"triage {aid} task {taskid} -> #{newid}"); acted += 1

    state["seen"] = list(seen)[-4000:]  # bound growth
    json.dump(state, open(STATE, "w"))
    print(f"acted {acted}")


main()
