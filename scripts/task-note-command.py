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
  REPLY-FIRST / EXO-FIRST (Jon 2026-10-03) — notes never spawn top-level tasks unless asked:
    @Exobot task: <title> | create a task ...  -> the ONLY path to a new top-level task
    directive naming a person ("have Neil renew the license") -> SUBTASK of this task -> that person
    directive with no named person ("order a new servo")      -> Exo does it (Exo subtask), answers here,
                                                                  hands off only what needs a human
    question / FYI                                             -> Exo subtask, answered on this task
  ANY note containing a question mark "?" (even WITHOUT @exo) is auto-answered on the task
    -> routed to the answer loop; Exo posts the answer on the task (Jon 2026-09-10). Guards:
       never answers Exo's own posts, and won't retro-answer questions older than QM_SINCE.

Every processed note gets a "✅ Exo:" confirmation reply on the task. Idempotent (state = processed
activity ids). Baseline-safe: the first run records existing @Exobot notes and does nothing, so it
never fires on historical comments. Deterministic; local Ollama only for owner routing (bounded).
"""
import json, os, re, subprocess, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
UPLOADS_META = os.path.join(WS, "mission-control", "uploads", "_meta.json")
INVCAP = os.path.join(WS, "scripts", "inventory_capture.py")
IMG_EXT = (".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif")
ROSTER = os.path.join(WS, "mission-control", "data", "routing-roster.json")
STATE = os.path.join(WS, "logs", "task-note-command-state.json")
LOG = os.path.join(WS, "logs", "task-note-command.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]

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
# Sandboxed early_adopter users (UTD capstone). Their notes are captured + acked by
# scripts/capstone_capture.py instead of this router.
try:
    _u = json.load(open(os.path.join("/Users/exomac/.openclaw/workspace", "mission-control", "users.json")))
    _u = _u if isinstance(_u, list) else (_u.get("users") or list(_u.values()))
    SANDBOX_AUTHORS = {(x.get("name") or "").strip().lower() for x in _u
                       if isinstance(x, dict) and x.get("role") == "early_adopter" and x.get("name")}
except Exception:
    SANDBOX_AUTHORS = set()
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
    # export control -> Empowered Official John Quinn (reviewer Denise Shirey); NOT Neil (Jon 2026-10-10)
    (r"export|itar|\bear\b|ddtc|deemed export", "jquinn@exosaero.com"),
    (r"licens|compliance|cmmc|cui|part 450|faa", "nmilburn@exosaero.com"),
    (r"contract|legal|agreement|\bnda\b|mnda|counsel|term sheet", "jquinn@exosaero.com"),
]


def logline(m):
    try:
        with open(LOG, "a") as f: f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception: pass


def fleet(action, detail, outcome="ok"):
    """exo3 telemetry: one line to logs/fleet-events.jsonl (never breaks the router)."""
    if os.environ.get("TNC_SELFTEST"):
        return
    try:
        sys.path.insert(0, os.path.join(WS, "scripts"))
        import fleet_log
        fleet_log.event("task-note-command", "orchestrate", action, detail=detail, owner="John Quinn", outcome=outcome)
    except Exception:
        pass


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


def exo_subtask(taskid, title, desc, tags, priority=70, suggested=None):
    """REPLY-FIRST (Jon 2026-10-03): a question/FYI/directive on a task NEVER becomes a new top-level
    task. It becomes an Exo-owned SUBTASK of the task it was asked on (parent:<id> tag -> hidden from
    the board, rolled up under the parent card, excluded from burndown 'created'). The answer loop
    (task-question-answer.py) works it and posts the result on the parent task. `suggested` = the
    person we'd have assigned before; Exo does it first and only hands off what truly needs a human."""
    tg = ["subtask", f"parent:{taskid}", "note-routed", "exo-first"] + list(tags)
    if suggested:
        desc += f" Suggested human owner if it truly needs one: {suggested['name']} <{suggested['email']}>."
    return supa("POST", "tasks", {"title": title, "owner": "Exo", "assigned_email": "exo@exosaero.com",
         "state": "To Do", "priority": priority, "category": "Task", "source": "task-note-command",
         "tags": tg, "description": desc})


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


def enqueue_task_photos(taskid, by):
    """@exo inv on a task -> queue that task's photo uploads for BOM/inventory matching.
    Reads the uploads registry, takes image uploads on this task (most-recent first, cap 8),
    and hands each to inventory_capture.py (which de-dupes by upload id)."""
    try:
        meta = json.load(open(UPLOADS_META))
    except Exception:
        meta = []
    imgs = [m for m in meta if str(m.get("task_id")) == str(taskid)
            and str(m.get("extension", "")).lower() in IMG_EXT and m.get("current") is not False]
    imgs.sort(key=lambda m: m.get("uploaded_at", ""), reverse=True)
    n = 0
    for m in imgs[:8]:
        try:
            r = subprocess.run(["/usr/bin/python3", INVCAP, "enqueue",
                 "--task", str(taskid), "--upload", str(m.get("id", "")),
                 "--file", str(m.get("stored_name", "")), "--filename", str(m.get("filename", "")),
                 "--by", m.get("uploaded_by") or by or "team", "--kind", "command"],
                capture_output=True, text=True, timeout=20)
            if r.stdout.strip() and r.stdout.strip() not in ("dup", "skip non-image"):
                n += 1
        except Exception as e:
            logline(f"WARN inv enqueue {taskid}: {e}")
    return n


def directive_after(body):
    """Return the command text after the FIRST trigger (@exo/@exobot text OR an Exobot mention token)."""
    m = MENTION_RE.search(body or "")
    tail = (body or "")[m.end():] if m else (body or "")
    tail = re.sub(r"<@[&!]?\d+>", "", tail)  # strip any residual mention tokens
    return tail.strip(" :,-—\n\t")


def link_dotted_subtasks():
    """Self-heal (Jon 10/9 "why do we keep duplicating this task?"): a task titled "<parent-id>.<n> ..."
    is a subtask, but sessions created them without the parent:<id> tag, so the board showed them as
    duplicate top-level cards next to the parent. Tag any such task created in the last 3 days."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        rows = supa("GET", "tasks?select=id,title,tags&created_at=gte." + urllib.parse.quote(since) + "&limit=500") or []
        for t in rows:
            m = re.match(r"\s*(\d{3,5})\.\d+\b", t.get("title") or "")
            tg = t.get("tags") or []
            if not m or any(str(x).startswith("parent:") for x in tg) or int(m.group(1)) == t["id"]:
                continue
            if not (supa("GET", f"tasks?select=id&id=eq.{m.group(1)}") or []):
                continue
            supa("PATCH", f"tasks?id=eq.{t['id']}", {"tags": sorted(set(tg + ["subtask", "parent:" + m.group(1)]))})
            logline(f"linked dotted subtask #{t['id']} -> parent #{m.group(1)}")
    except Exception as e:
        logline(f"WARN link_dotted_subtasks: {e}")


REPEAT_WINDOW_S = 300


def _norm(b):
    return re.sub(r"\s+", " ", (b or "").strip().lower())


def _similar(a, b):
    """Near-duplicate re-sends of the SAME ask (e.g. one word edited and re-posted), not different commands
    like "hours 3.5" then "done" (those stay separate)."""
    import difflib
    a, b = _norm(a), _norm(b)
    return a == b or (min(len(a), len(b)) >= 40 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.75)


def coalesce_repeats(cmds, rows, seen, taskid_of):
    """One reply per request (Jon 10/17, #3808: one ask, posted 3x in 40s, got 3 identical acks + 3 subtasks).
    Same author + same task + within REPEAT_WINDOW_S: (a) an exact repeat of a note already handled is
    marked seen and dropped; (b) a burst of new notes is routed once, as the newest note with the distinct
    texts merged (near-duplicates only: different short commands in a row stay separate). Every absorbed note id is added to `seen` so later runs never re-route it."""
    def ts(r):
        return datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
    def key(r):
        return (taskid_of(r), (r.get("owner") or "").strip().lower())
    handled = [r for r in rows if r["id"] in seen and taskid_of(r)]
    fresh = sorted((r for r in cmds if r["id"] not in seen), key=ts)
    out, used = [], set()
    for i, r in enumerate(fresh):
        if r["id"] in used:
            continue
        if any(key(h) == key(r) and _similar(h.get("body"), r.get("body"))
               and abs((ts(r) - ts(h)).total_seconds()) <= REPEAT_WINDOW_S for h in handled):
            seen.add(r["id"]); logline(f"repeat dropped {r['id']} task {taskid_of(r)}")
            fleet("repeat_dropped", {"note": r["id"], "task": taskid_of(r)}); continue
        group = [r] + [x for x in fresh[i + 1:] if x["id"] not in used and key(x) == key(r)
                       and (ts(x) - ts(r)).total_seconds() <= REPEAT_WINDOW_S and _similar(x.get("body"), r.get("body"))]
        if len(group) > 1:
            texts = []
            for g in group:
                if _norm(g.get("body")) not in [_norm(t) for t in texts]:
                    texts.append(g.get("body") or "")
            merged = dict(group[-1], body=texts[0] if len(texts) == 1 else
                          texts[0] + "\n\n(also, same request:)\n" + "\n".join(texts[1:]))
            for g in group[:-1]:
                used.add(g["id"]); seen.add(g["id"])
            logline(f"coalesced {len(group)} notes on task {taskid_of(r)} -> {group[-1]['id']}")
            fleet("coalesced", {"task": taskid_of(r), "kept": group[-1]["id"], "absorbed": [g["id"] for g in group[:-1]]})
            out.append(merged); used.add(group[-1]["id"])
        else:
            out.append(r); used.add(r["id"])
    return out + [r for r in cmds if r["id"] in seen]   # already-seen rows pass through (skipped below)


def main():
    import sys
    link_dotted_subtasks()
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
    cmds = coalesce_repeats(cmds, rows, seen, taskid_of)
    for r in cmds:
        aid = r["id"]
        if aid in seen: continue
        seen.add(aid)
        owner_of_note = (r.get("owner") or "")
        if SKIP_OWNERS.match(owner_of_note.strip()):
            continue  # automation-authored, not a human command
        if owner_of_note.strip().lower() in SANDBOX_AUTHORS:
            continue  # UTD capstone (early_adopter): handled by capstone_capture.py, never
                      # free-form routed (would create staff tasks / answer with internal context)
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
            nid = exo_subtask(taskid, f"[Exo answering] {qtext[:60] or 'question'}",
                 f"Question posted on task #{taskid} (by {owner_of_note or 'team'}): {qtext}. Exo to review and answer.",
                 ["needs-attention", "auto-question"])
            newid = nid[0]["id"] if nid else "?"
            flag_awaiting(taskid)
            reply(taskid, "✅ Exo: got your question — I'll answer right here on this task shortly.")
            logline(f"auto-q {aid} task {taskid} -> sub #{newid}"); acted += 1; continue
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

        # 0) inventory capture: "@exo inv" / "@exo inventory" -> queue this task's photo(s) so the
        # main Exo session matches each to the BLK3 BOM and records it in inventory.
        if re.match(r"(inv|inventory)\b", low):
            n = enqueue_task_photos(taskid, owner_of_note)
            if n:
                reply(taskid, f"✅ Exo (inventory): queued {n} photo(s) from this task — I'll match each "
                              f"to the BOM and record it to inventory (I'll ask you right here if I need a detail).")
            else:
                reply(taskid, "✅ Exo (inventory): no photo on this task yet. Tap **📷 Take Photo → this task** "
                              "on the Documents tab, shoot the component, and I'll log it automatically.")
            logline(f"inv {aid} task {taskid} queued {n}"); acted += 1; continue

        # 0b) section build procedure: "@exo procedure [Section]" -> regenerate that section's
        # illustrated build/inventory procedure (BOM order + banked photos + on-hand). One doc per
        # section, on demand — never per photo, never a new task.
        mproc = re.match(r"(?:build\s+)?proc(?:edure)?\b\s*(.*)", low)
        if mproc:
            sec_arg = mproc.group(1).strip()
            secmap = {"computer": "Computer", "engine": "Engine Bay", "engine bay": "Engine Bay",
                      "fin": "Fin Can", "fin can": "Fin Can", "pressure": "Pressure Section",
                      "tank": "Tanks", "tanks": "Tanks", "payload": "Payload Section",
                      "recovery": "Recovery section", "top": "BLK3 Top Level"}
            section = next((v for k, v in secmap.items() if sec_arg.startswith(k)), "Computer")
            try:
                pr = subprocess.run(["/usr/bin/python3",
                     os.path.join(WS, "scripts", "section_build_procedure.py"), section, "--email"],
                     capture_output=True, text=True, timeout=120)
                tail = [l for l in pr.stdout.splitlines() if l.startswith("summary:")]
                reply(taskid, f"✅ Exo (procedure): regenerated the **BLK3 {section}** build & inventory "
                              f"procedure ({tail[0][8:].strip() if tail else 'done'}) — DRAFT in the Process "
                              f"Library and emailed to John for approval.")
            except Exception as ex:
                reply(taskid, f"✅ Exo (procedure): couldn't rebuild the {section} procedure ({ex}).")
            logline(f"procedure {aid} task {taskid} section {section}"); acted += 1; continue

        # 0c) effort tracking (weekly-task-agenda-exo3, Jon 10/16): "@Exobot est 6h" (estimate to
        # complete), "@Exobot week 4h" (planned this week), "@Exobot hours 3.5 [for Mike] [#86]" (actuals
        # ledger per task/person/week). Must run BEFORE free-form routing, or "hours 3.5" becomes a subtask.
        try:
            sys.path.insert(0, os.path.join(WS, "scripts"))
            import task_effort
            if task_effort.handle_note(taskid, cmd, owner_of_note, r.get("created_at"), aid, reply):
                logline(f"effort {aid} task {taskid}: {cmd[:60]}"); acted += 1; continue
        except Exception as ex:
            logline(f"WARN effort {aid} task {taskid}: {ex}")

        # EXPLICIT new task: "@exo task: <title>" / "create a task ..." / "build a task ..." — the ONLY
        # path that creates a new top-level task from a note (Jon 2026-10-03). Owner = named person,
        # else Exo. Linked back to this task in the description.
        mtask = re.match(r"(?:(?:new\s+)?task\s*[:\-]|(?:create|build|make|open)\s+(?:a\s+)?(?:new\s+)?task\b"
                         r"\s*(?:for\s+\w+\s*)?[:\-]?)\s*(.+)", cmd, re.I)
        if mtask and mtask.group(1).strip():
            ttitle = re.sub(r"^to\s+", "", mtask.group(1).strip(), flags=re.I)
            p = resolve_person(cmd, roster)
            nt = supa("POST", "tasks", {"title": ttitle[:70], "owner": p["name"] if p else "Exo",
                 "assigned_email": p["email"] if p else "exo@exosaero.com", "state": "To Do", "priority": 74,
                 "category": "Task", "source": "task-note-command", "tags": ["note-routed", "explicit-task"],
                 "assigned_at": datetime.now(timezone.utc).isoformat(),
                 "description": f"Explicitly requested from a note on task #{taskid} (by {owner_of_note}): {ttitle}"})
            ntid = nt[0]["id"] if nt else "?"
            reply(taskid, f"✅ Exo: created task #{ntid} → {p['name'] if p else 'Exo'} for “{ttitle[:110]}” (you asked for a task).")
            logline(f"explicit-task {aid} task {taskid} -> #{ntid}"); acted += 1; continue

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

        # 4) free-form directive -> route to the right owner as a linked task.
        # A QUESTION is never a directive, even if it contains an action verb ("where do i go to
        # login for you to investigate this" spawned #3318 — Jon 10/1). Questions fall to 5) and
        # get answered on the original task.
        is_question = cmd.rstrip().endswith("?") or re.match(
            r"(where|what|why|how|when|who|which|can|could|should|would|is|are|do|does|did|will)\b", low)
        if ACTION.search(cmd) and not is_question:
            # EXO-FIRST (Jon 2026-10-03): only an EXPLICITLY named person gets the work (as a subtask of
            # this task). A domain-guessed owner no longer gets it dumped on them — Exo does it first and
            # hands off only the piece that truly needs a human (decision / approval / physical action).
            named = resolve_person(cmd, roster)
            if named:
                nid = supa("POST", "tasks", {"title": cmd[:70], "owner": named["name"], "assigned_to": named["name"],
                     "assigned_email": named["email"], "state": "To Do", "priority": 74, "category": "Task",
                     "source": "task-note-command", "tags": ["note-routed", "subtask", f"parent:{taskid}"],
                     "assigned_at": datetime.now(timezone.utc).isoformat(),
                     "description": f"Delegated from a note on task #{taskid} (by {owner_of_note}). Directive: {cmd}"})
                newid = nid[0]["id"] if nid else "?"
                reply(taskid, f"✅ Exo: added subtask #{newid} on this task → {named['name']} for “{cmd[:110]}”.")
                logline(f"route {aid} task {taskid} -> {named['name']} sub #{newid}"); acted += 1; continue
            guess = domain_owner(cmd, by_email)
            nid = exo_subtask(taskid, f"[Exo doing] {cmd[:62]}",
                 f"From a note on task #{taskid} (by {owner_of_note}). Directive: {cmd}. Exo to do it itself.",
                 ["needs-owner"], priority=74, suggested=guess)
            newid = nid[0]["id"] if nid else "?"
            flag_awaiting(taskid)   # Exo-owned directive: surface the ORIGINAL task to the top too
            # Never tell the requester we "created a task" (Jon #2414 10/2): do it, reply HERE.
            reply(taskid, "✅ Exo: on it — I'll do this myself and post the result right here. "
                          "If any piece needs a person (a decision, approval, or hands-on step) I'll say exactly what.")
            logline(f"route {aid} task {taskid} -> Exo-first sub #{newid} (guess={guess and guess['email']})"); acted += 1; continue

        # 5) unrecognized @Exobot note (question/FYI) -> Exo subtask on THIS task; answered here.
        nid = exo_subtask(taskid, f"[Exo answering] {cmd[:60] or 'follow up'}",
             f"@Exobot note on task #{taskid} (by {owner_of_note}): {cmd}. Exo to review and act.",
             ["needs-attention"])
        newid = nid[0]["id"] if nid else "?"
        flag_awaiting(taskid)   # surface the ORIGINAL task to the top until answered
        reply(taskid, "✅ Exo: got it — I'll answer right here on this task shortly.")
        logline(f"triage {aid} task {taskid} -> sub #{newid}"); acted += 1

    state["seen"] = list(seen)[-4000:]  # bound growth
    json.dump(state, open(STATE, "w"))
    print(f"acted {acted}")


def selftest():
    """Failure replay (weekly-task-agenda-exo3, 2026-10-16): before the effort hook, "@Exobot hours 3.5"
    fell through to step 5 and spawned an "[Exo answering]" subtask instead of logging time. Stubs
    Supabase + uses temp state/store; never touches live tasks."""
    import tempfile
    global STATE, LOG, supa
    tmp = tempfile.mkdtemp()
    STATE = os.path.join(tmp, "state.json"); LOG = os.path.join(tmp, "log")
    json.dump({"seen": []}, open(STATE, "w"))
    os.environ["TASK_EFFORT_STORE"] = os.path.join(tmp, "te.json")
    now = datetime.now(timezone.utc).isoformat()
    rows = [{"id": "st-1", "type": "task_note", "subject": "task:86", "body": "@Exobot hours 3.5", "owner": "Mike Talley", "created_at": now},
            {"id": "st-2", "type": "task_note", "subject": "task:86", "body": "@Exobot est 60h", "owner": "Mike Talley", "created_at": now},
            {"id": "st-3", "type": "task_note", "subject": "task:86", "body": "@Exobot week 6h", "owner": "Jon", "created_at": now},
            {"id": "st-4", "type": "task_note", "subject": "task:86", "body": "@Exobot done", "owner": "Mike Talley", "created_at": now}]
    calls = []

    def fake(method, path, body=None):
        calls.append((method, path, body))
        if method == "GET" and path.startswith("activities"):
            return rows
        if method == "GET":
            return []
        return [{"id": 99999}]
    supa = fake
    main()
    posts = [c for c in calls if c[0] == "POST"]
    new_tasks = [c for c in posts if c[1] == "tasks"]
    replies = [c[2]["body"] for c in posts if c[1] == "activities"]
    patches = [c for c in calls if c[0] == "PATCH"]
    store = json.load(open(os.environ["TASK_EFFORT_STORE"]))
    checks = {
        "no subtask spawned for effort notes": not new_tasks,
        "hours logged + confirmed": any("logged 3.5 h on #86" in x for x in replies),
        "estimate set + confirmed": any("estimate to complete #86 = 60 h" in x for x in replies),
        "week plan set": any("planned 6 h on #86" in x for x in replies),
        "store ledger has 3.5 h for Mike": any(a["hours"] == 3.5 and a["email"] == "mtalley@exosaero.com" for a in store["actuals"]),
        "'done' still marks Done (router intact)": any(c[2] == {"state": "Done"} for c in patches),
    }
    # Failure replay (Jon 10/17, #3808): one ask posted 3x within 40s got 3 identical acks + 3 subtasks.
    t0 = datetime.now(timezone.utc)
    ask = "@Exobot can you pull the NYK contact list and draft the intro note for Toshi to send this week please"
    burst = [{"id": f"rp-{i}", "subject": "task:3808", "owner": "Jon", "body": ask + ("" if i < 2 else " thanks"),
              "created_at": (t0 + timedelta(seconds=20 * i)).isoformat()} for i in range(3)]
    tid = lambda r: re.match(r"task:(\d+)$", r["subject"]).group(1)
    sn = set()
    routed = [r for r in coalesce_repeats(list(burst), burst, sn, tid) if r["id"] not in sn]
    checks["3x repeat burst -> routed once (newest kept)"] = len(routed) == 1 and routed[0]["id"] == "rp-2"
    checks["absorbed repeats marked seen"] = {"rp-0", "rp-1"} <= sn
    late = {"id": "rp-3", "subject": "task:3808", "owner": "Jon", "body": ask, "created_at": (t0 + timedelta(seconds=90)).isoformat()}
    sn2 = {"rp-2"}
    out2 = [r for r in coalesce_repeats([late], burst + [late], sn2, tid) if r["id"] not in sn2]
    checks["repeat of already-handled note dropped"] = not out2 and "rp-3" in sn2
    cmds2 = [{"id": "dc-1", "subject": "task:86", "owner": "Mike", "body": "@Exobot hours 3.5", "created_at": t0.isoformat()},
             {"id": "dc-2", "subject": "task:86", "owner": "Mike", "body": "@Exobot done", "created_at": (t0 + timedelta(seconds=10)).isoformat()}]
    checks["different short commands stay separate"] = len(coalesce_repeats(cmds2, cmds2, set(), tid)) == 2
    bad = [k for k, v in checks.items() if not v]
    print(f"task-note-command selftest: {len(checks) - len(bad)} passed, {len(bad)} failed" + (f": {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        os.environ["TNC_SELFTEST"] = "1"
        sys.exit(selftest())
    main()
