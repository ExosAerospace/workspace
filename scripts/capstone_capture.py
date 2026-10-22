#!/usr/bin/env python3
"""
capstone_capture.py — Exo as the UTD Team Atlas "prompter" + experiment recorder.

Jon (2026-09-27): students work in short 15-20 min MC sessions WITH Exo; Exo learns
from their inputs/decisions and captures the result of every experiment.

Every ~10 min (launchd com.exos.capstone-capture):
  - reads new notes + state changes on UTD students' tasks (Supabase `activities`)
  - appends each to mission-control/data/capstone-experiments.jsonl (the dataset:
    contact checks, fit scores, AI-error lists, corrected drafts, checklist edits…)
  - replies on the task as Exo: note → "captured"; session moved to Done →
    milestone count + the student's next session
  - a student QUESTION (is_question: '?' outside URLs, question-word opener, or request
    phrasing) becomes an Exo triage task tagged utd-question + eta:<ISO> (due_date = ETA:
    +4h, rolled to 10 AM CT if it lands 9 PM-8 AM) and the student gets a concrete ETA.
    capstone_question_answerer.py dispatches the answer and runs the SLA watchdog.
  Test: capstone_capture.py --dry-run --fake "how do I ..."   (no writes)

Deterministic, idempotent (state file tracks seen activity ids). Student notes are
excluded from task-note-command.py, so this is their only automation path.
"""
import os, re, sys, json, subprocess, urllib.request, urllib.parse, urllib.error
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
DATA = os.path.join(WS, "mission-control/data/capstone-experiments.jsonl")
STATE = os.path.join(WS, "logs/capstone-capture-state.json")
LOG = os.path.join(WS, "logs/capstone-capture.log")
SINCE_DEFAULT = "2026-09-27T16:00:00+00:00"  # go-live; nothing earlier is replayed


CT = ZoneInfo("America/Chicago")
DRY = "--dry-run" in sys.argv
ETA_HOURS = 4

# ── question detection (deterministic) ──────────────────────────────────────
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
QWORD_RE = re.compile(r"^\W*(how|what|why|when|where|who|can|could|should|is|are|do|does|will)\b", re.I)
PHRASE_RE = re.compile(r"@exo|please clarify|can you|\bhelp\b", re.I)
MENTION_RE = re.compile(r"@exo", re.I)  # also matches @exobot
# Lead-check reports (PASS/FAIL/ERRORS/(a) CONTACT/numbered lists) quote drafted cold emails
# full of "?"/"help"/"can you" — for those, only an explicit @exo mention makes it a question.
REPORT_RE = re.compile(r"^\W*(pass|fail|errors?|\(a\)|contact\b|\d+[.)])", re.I)


def is_question(body):
    """True if a student note is a question/request for Exo.
    '?' counts only outside URLs; also question-word openers and request phrasing."""
    text = URL_RE.sub(" ", body or "")
    if REPORT_RE.match(text.strip()):
        return bool(MENTION_RE.search(text))
    if "?" in text:
        return True
    if QWORD_RE.match(text.strip()):
        return True
    return bool(PHRASE_RE.search(text))


# ── ETA: +4h, but never 9 PM–8 AM Central (roll to 10 AM) ────────────────────
def compute_eta(start, hours=ETA_HOURS):
    """start: aware datetime. Returns aware UTC datetime."""
    loc = (start + timedelta(hours=hours)).astimezone(CT)
    if loc.hour >= 21:
        loc = (loc + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    elif loc.hour < 8:
        loc = loc.replace(hour=10, minute=0, second=0, microsecond=0)
    return loc.astimezone(timezone.utc).replace(second=0, microsecond=0)


def fmt_eta(dt):
    loc = dt.astimezone(CT)
    return loc.strftime("%A %-I:%M %p ") + loc.tzname()  # e.g. "Thursday 2:05 PM CDT"


def parse_ts(s):
    # py3.9 fromisoformat only takes 3 or 6 fractional digits; Supabase/PostgREST
    # trims trailing zeros (e.g. ".91331"), so pad/truncate the fraction to 6.
    s = s.replace("Z", "+00:00")
    s = re.sub(r"\.(\d+)", lambda m: "." + (m.group(1) + "000000")[:6], s, count=1)
    return datetime.fromisoformat(s)


def log(m):
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}] {m}\n")


def supa(method, path, body=None):
    if DRY and method != "GET":
        print(f"[dry-run] {method} {path} {json.dumps(body, ensure_ascii=False)[:600]}")
        return [{"id": "DRY"}]
    req = urllib.request.Request(SB + "/" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                                          "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read().decode()
        return json.loads(t) if t else []


def students():
    u = json.load(open(os.path.join(WS, "mission-control/users.json")))
    u = u if isinstance(u, list) else (u.get("users") or list(u.values()))
    return {x["name"].strip().lower(): x["name"] for x in u
            if isinstance(x, dict) and x.get("role") == "early_adopter" and x.get("name")}


def reply(tid, msg):
    supa("POST", "activities", {"type": "task_note", "subject": f"task:{tid}", "body": msg,
                                "owner": "Exo", "status": "completed"})


# ── crash-safety (MC 10/22): per-item atomic state + idempotent side effects ──
# A crash mid-loop used to re-capture and re-ack every note since the last full run (10/10 x9).
# Now: each side effect first checks whether it already happened for this source activity id,
# and state is persisted (temp + os.replace) right after each item's side effects succeed. A
# failed item is left unmarked (and `since` never advances past it) so the next run retries it.
class _Crash(BaseException):
    """selftest-only: simulates the process dying (not caught by per-item error handling)."""


_ITEM_HOOK = None    # selftest: called after each item is committed (raise _Crash to simulate a kill)
_OUTBOX_HOOK = None  # selftest: called after each outbox email result is persisted


def atomic_json(path, obj, **kw):
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, **kw)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def _captured_index():
    """activity_id -> n for rows already in the dataset (rows written before 10/22 carry no id)."""
    idx, top = {}, 0
    if os.path.exists(DATA):
        for line in open(DATA):
            try:
                r = json.loads(line)
            except Exception:
                continue  # torn tail line from a crash mid-write
            top = max(top, r.get("n") or 0)
            if r.get("activity_id"):
                idx[r["activity_id"]] = r["n"]
    return idx, top


def _append_capture(rec):
    with open(DATA, "a+") as f:
        f.seek(0, 2)
        if f.tell():
            f.seek(f.tell() - 1); last = f.read(1); f.seek(0, 2)
            if last != "\n":
                f.write("\n")  # never glue a new row onto a torn line
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())


def _exo_notes_since(tid, ts):
    """Exo notes on a student task at/after the source note (an ack always follows its note)."""
    return supa("GET", f"activities?select=body,created_at&subject=eq.task:{tid}&owner=eq.Exo&type=eq.task_note"
                       f"&created_at=gte.{urllib.parse.quote(ts)}&order=created_at.desc&limit=500") or []


def _ack_exists(tid, ts, pattern):
    if DRY:
        return False
    rx = re.compile(pattern)
    return any(rx.search(r.get("body") or "") for r in _exo_notes_since(tid, ts))


def _n_ack_pattern(n):
    return rf"data point #{n}(?!\d)"


def _src_marker(aid):
    return f"[src:{aid}]"


def _triage_for(aid):
    """Existing triage entry for this source activity: its own task (tag) or a fold (marker)."""
    if DRY:
        return None, None
    r = supa("GET", f"tasks?select=id,due_date&tags=cs.%7Bstudent-activity:{aid}%7D&limit=1") or []
    if r:
        return r[0], "own"
    r = supa("GET", "tasks?select=id,due_date&description=like."
                    + urllib.parse.quote(f"*{_src_marker(aid)}*") + "&limit=1") or []
    return (r[0], "fold") if r else (None, None)


def fmt_due(d):
    try:
        return parse_ts(d).strftime("%a %-m/%-d")
    except Exception:
        return ""


def handle_question(a, author, tid, t, n):
    """Create the Exo triage task (with ETA) and ack the student with a concrete ETA."""
    # ETA = created + 4h; if the note is being processed late (job was down), base on now so
    # the promised ETA is never already in the past.
    now = datetime.now(timezone.utc)
    created = parse_ts(a["created_at"])
    eta = compute_eta(created if now - created < timedelta(minutes=30) else now)
    # REPLY-FIRST (Jon 2026-10-03): one open question entry per student task. A follow-up question on
    # the same task is folded into the still-undispatched entry (same ETA) instead of a new task
    # (#3133 alone once spawned 9). If the open entry is already dispatched, open a fresh one.
    def _eta_of(row, default):
        try:
            return parse_ts(row["due_date"])
        except Exception:
            return default

    # Idempotent (crash-safe): if this source note already has its triage entry (own task via the
    # student-activity tag, or folded via the [src:id] marker), reuse it; ack only if not yet acked.
    prior, how = _triage_for(a["id"])
    if prior:
        eta = _eta_of(prior, eta)
        if not _ack_exists(tid, a["created_at"], _n_ack_pattern(n)):
            if how == "own":
                reply(tid, f"✅ Exo: captured (data point #{n}). Got your question. "
                           f"I'll answer here by {fmt_eta(eta)} (ref #{prior['id']}).")
            else:
                reply(tid, f"✅ Exo: captured (data point #{n}). Got your follow-up. I'll answer it here along "
                           f"with your earlier question by {fmt_eta(eta)}.")
        return eta
    try:
        ast = json.load(open(os.path.join(WS, "logs/capstone-question-answerer-state.json")))
        dispatched = {str(k) for k in (ast.get("dispatched") or {})}
    except Exception:
        dispatched = set()
    if not DRY:
        cur = supa("GET", f"tasks?select=id,description,due_date&tags=cs.%7Bstudent-task:{tid}%7D"
                          f"&tags=cs.%7Butd-question%7D&state=not.in.(Done,Cancelled)&order=id.desc&limit=1") or []
        if cur and str(cur[0]["id"]) not in dispatched:
            ex = cur[0]
            supa("PATCH", f"tasks?id=eq.{ex['id']}", {"description": (ex.get("description") or "") +
                 f"\n\nALSO ANSWER — follow-up from {author} ({a['created_at'][:16]}) {_src_marker(a['id'])}:\n{a.get('body')}"})
            eta = _eta_of(ex, eta)
            reply(tid, f"✅ Exo: captured (data point #{n}). Got your follow-up. I'll answer it here along "
                       f"with your earlier question by {fmt_eta(eta)}.")
            return eta
    nid = supa("POST", "tasks", {
        "title": f"[UTD question] {author}: {(a.get('body') or '').strip()[:60]} (task #{tid})",
        "owner": "Exo", "assigned_email": "exo@exosaero.com", "state": "To Do", "priority": 85,
        "category": "Task", "source": "capstone-capture", "due_date": eta.isoformat(),
        "tags": ["utd-question", "needs-attention", f"eta:{eta.isoformat()}", f"student-task:{tid}",
                 f"student-activity:{a['id']}"],
        "description": (f"UTD capstone student {author} asked on task #{tid} ({t.get('title')}):\n\n{a.get('body')}\n\n"
                        f"ETA promised to student: {fmt_eta(eta)}.\n"
                        f"ANSWER ON TASK #{tid} as Exo. The student is a sandboxed early_adopter under NDA: "
                        "answer only with public / program information (PUG facts, process, their tasks). "
                        "No pricing, customers, financials, CUI/ITAR, or other internal data. "
                        "If unsure, route to Lizi. Auto-dispatched by capstone_question_answerer.py.")})
    ref = nid[0]["id"] if nid else "?"
    reply(tid, f"✅ Exo: captured (data point #{n}). Got your question. "
               f"I'll answer here by {fmt_eta(eta)} (ref #{ref}).")
    return eta


def dry_run_fake():
    """--dry-run --fake "note text": simulate one student note end to end, no writes."""
    body = sys.argv[sys.argv.index("--fake") + 1]
    a = {"id": "fake-1", "created_at": datetime.now(timezone.utc).isoformat(), "body": body, "type": "task_note"}
    print(f"note: {body!r}\nis_question: {is_question(body)}")
    if is_question(body):
        eta = handle_question(a, "Test Student", 99999, {"title": "Fake session task"}, 0)
        print(f"eta: {eta.isoformat()} = {fmt_eta(eta)}")
    else:
        reply(99999, "✅ Exo: captured as data point #0 for Team Atlas's human-vs-AI experiment. ...")


def _process_item(a, author, who, tasks, by_id, st, cap_idx):
    """All side effects for one student activity, each idempotent on the source activity id.
    Returns True if anything was captured."""
    tid = int(a["subject"].split(":")[1])
    t = by_id.get(tid, {})
    tags = t.get("tags") or []
    body = a.get("body") or ""
    is_done = a["type"] == "task_update" and re.search(r"State: .*→ Done", body)
    if a["type"] == "task_update" and not is_done and "State:" not in body:
        return False
    # 1. capture (dataset row keyed by activity_id; a crash after this reuses the same n)
    n = cap_idx.get(a["id"])
    new_row = n is None
    if new_row:
        n = st["n"] + 1
    rec = {"n": n, "ts": a["created_at"], "student": who[author.lower()], "task_id": tid,
           "task": t.get("title"), "kind": "done" if is_done else ("state" if a["type"] == "task_update" else "note"),
           "session": next((x[8:] for x in tags if x.startswith("session:")), None),
           "lead": next((x[5:] for x in tags if x.startswith("lead:")), None), "body": body,
           "activity_id": a["id"]}
    if new_row:
        _append_capture(rec)
        cap_idx[a["id"]] = n
    st["n"] = max(st["n"], n)
    # 2. ack / triage (each checks for an existing one first)
    if rec["kind"] == "note":
        if is_question(body):
            handle_question(a, author, tid, t, n)
        elif not _ack_exists(tid, a["created_at"], _n_ack_pattern(n)):
            reply(tid, f"✅ Exo: captured as data point #{n} for Team Atlas's human-vs-AI experiment. "
                       "Thanks! When you're done, drag this task to Done.")
    elif rec["kind"] == "done" and "15-min" in tags and not _ack_exists(tid, a["created_at"], r"^🎯 Exo: session complete"):
        mine = [x for x in tasks if (x.get("owner") or "").lower() == author.lower() and "15-min" in (x.get("tags") or [])]
        done = sum(1 for x in mine if x["state"] == "Done" or x["id"] == tid)
        nxt = sorted([x for x in mine if x["state"] != "Done" and x["id"] != tid], key=lambda x: x.get("due_date") or "")
        msg = f"🎯 Exo: session complete. You've closed {done} of {len(mine)} this week."
        msg += (f" Next up: #{nxt[0]['id']} {nxt[0]['title']} (due {fmt_due(nxt[0].get('due_date') or '')})."
                if nxt else " That's all of your sessions for the week. Great work!")
        reply(tid, msg)
    return new_row


def _save_state(st, seen):
    st["seen"] = seen[-3000:]  # ordered list: oldest dropped first
    atomic_json(STATE, st)


def main():
    st = {"since": SINCE_DEFAULT, "seen": [], "n": 0}
    if os.path.exists(STATE):
        st.update(json.load(open(STATE)))
    seen = list(st["seen"]); seen_set = set(seen)
    cap_idx, top_n = _captured_index()
    st["n"] = max(st["n"], top_n)
    who = students()
    tasks = supa("GET", "tasks?select=id,title,state,owner,due_date,source,tags&assigned_email=ilike.*utdallas*")
    by_id = {t["id"]: t for t in tasks}
    subj = ",".join(f"task:{i}" for i in by_id)
    q = (f"activities?select=id,type,subject,body,owner,created_at&type=in.(task_note,task_update)"
         f"&created_at=gt.{urllib.parse.quote(st['since'])}&subject=in.({urllib.parse.quote(subj)})&order=created_at")
    acts = supa("GET", q)
    captured, failed = 0, []
    for a in acts:
        if a["id"] in seen_set:
            continue
        author = (a.get("owner") or "").strip()
        if author.lower() in who:
            try:
                captured += bool(_process_item(a, author, who, tasks, by_id, st, cap_idx))
            except Exception as e:  # leave unmarked: next run retries it (side effects are idempotent)
                failed.append(a)
                log(f"item {a['id']} (task {a.get('subject')}) failed, will retry: {type(e).__name__}: {e}")
                continue
        # commit this item: mark seen; `since` advances only while no earlier item has failed, and
        # stays 1µs behind it so a crash can't skip a not-yet-processed note with the same timestamp
        # (the query is created_at=gt.since; `seen` filters the re-fetched ones)
        seen.append(a["id"]); seen_set.add(a["id"])
        if not failed:
            st["since"] = (parse_ts(a["created_at"]) - timedelta(microseconds=1)).isoformat()
        if author.lower() in who:
            _save_state(st, seen)
        if _ITEM_HOOK:
            _ITEM_HOOK(a)
    if failed:
        # strictly before the first failed item so `created_at=gt.since` re-fetches it
        if parse_ts(st["since"]) >= parse_ts(failed[0]["created_at"]):
            st["since"] = (parse_ts(failed[0]["created_at"]) - timedelta(microseconds=1)).isoformat()
    _save_state(st, seen)
    if captured or failed:
        log(f"captured {captured} (total {st['n']})" + (f", {len(failed)} failed (retry next run)" if failed else ""))


OUTBOX = os.path.join(WS, "mission-control/data/capstone-outbox.json")


def process_outbox():
    """Send staged student emails ONLY after Lizi answers their Decision Yes (Jon 9/27:
    Lizi releases, Exo sends directly as the team's prompter). No → cancelled.
    Crash-safe / never double-sends: the item is marked `sending` and each email gets an
    in-flight record persisted (temp + os.replace) BEFORE msmtp runs, then its result right
    after. A rerun skips every email that already has a record; an in-flight record left by a
    crash is never re-sent (status ends `partial`, flagged for manual verification)."""
    if not os.path.exists(OUTBOX):
        return
    ob = json.load(open(OUTBOX))
    pend = [x for x in ob if x.get("status") in ("pending", "sending")]
    if not pend:
        return
    save = lambda: atomic_json(OUTBOX, ob, indent=1, ensure_ascii=False)
    decs = []
    if any(x.get("status") == "pending" for x in pend):
        tok = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
        req = urllib.request.Request("http://localhost:8080/api/decisions", headers={"X-Exo-Token": tok})
        decs = json.load(urllib.request.urlopen(req, timeout=20))
        # the API lists only open decisions now; answered ones live in decisions.json
        local = json.load(open(os.path.join(WS, "mission-control/data/decisions.json")))
        decs += local if isinstance(local, list) else local.get("decisions", [])
    for item in pend:
        if item["status"] == "pending":
            d = next((z for z in decs if z.get("dedupeKey") == item["decision_dedupe"]), None)
            if not d or d.get("status") != "answered":
                continue
            ans = (d.get("answer") or "").strip().lower()
            if not ans.startswith("yes"):
                item["status"] = "cancelled"; item["decision_answer"] = d.get("answer"); save()
                log(f"outbox {item['key']} cancelled: {d.get('answer')}"); continue
            item["status"] = "sending"; item["sent"] = []; save()
        sent = item.setdefault("sent", [])
        for i, e in enumerate(item["emails"]):
            if i < len(sent):
                continue  # already attempted (result or in-flight record): never re-send
            sent.append({"to": e["to"], "ok": None, "attempt_at": datetime.now(timezone.utc).isoformat(),
                         "err": "in-flight: run interrupted before result; NOT re-sent, verify manually"})
            save()
            m = EmailMessage()
            m["From"] = "Exo (Exos Mission Control) <jquinnexo@pm.me>"
            m["To"] = e["to"]; m["Cc"] = item["cc"]; m["Reply-To"] = item["reply_to"]
            m["Subject"] = e["subject"]; m.set_content(e["body"])
            p = subprocess.run(["msmtp", "-a", "protonmail", e["to"], item["cc"]], input=m.as_bytes(), capture_output=True)
            ok = p.returncode == 0
            sent[i] = {"to": e["to"], "ok": ok, "err": p.stderr.decode()[:120]}
            save()
            log(f"outbox {item['key']} -> {e['to']} ok={ok}")
            if _OUTBOX_HOOK:
                _OUTBOX_HOOK(item, e)
        item["status"] = "sent" if all(x.get("ok") is True for x in sent) else "partial"
        item["sent_at"] = datetime.now(timezone.utc).isoformat()
        save()


# ── OUTPUT eval (exo3 R5): `capstone_capture.py selftest` ─────────────────────
# Read-only: fixtures in a temp dir (fake Supabase / decisions API / msmtp) + read-only checks of
# the real outputs. No sends, no Supabase writes, no student contact.
DUP_BASELINE = "2026-10-11T00:00:00+00:00"   # 10/10 re-capture loop (n=373/374 x9) predates the parse_ts fix
OUTBOX_LEGACY_BEFORE = "2026-09-28T00:00:00+00:00"  # wk5-prompter: released by Jon directly, pre-Decision flow
STUDENT_DOMAIN = "@utdallas.edu"


class _FakeSB:
    """Stateful in-memory stand-in for Supabase (selftest only). Answers exactly the queries this
    script issues, honours created_at filters, and can crash/fail on the Nth write."""

    def __init__(self, acts, tasks, crash_at=None, crash_after=False, fail_at=None):
        self.acts, self.student_tasks = acts, tasks
        self.notes, self.tasks, self.writes = [], [], []
        self.crash_at, self.crash_after, self.fail_at, self.nw = crash_at, crash_after, fail_at, 0

    def __call__(self, method, path, body=None):
        up = urllib.parse.unquote(path)
        if method == "GET":
            if up.startswith("tasks?select=id,title,state,owner"):
                return [dict(t) for t in self.student_tasks]
            if up.startswith("activities?select=id,type"):
                since = parse_ts(re.search(r"created_at=gt\.([^&]+)", up).group(1))
                return [x for x in self.acts if parse_ts(x["created_at"]) > since]
            m = re.match(r"activities\?select=body,created_at&subject=eq\.(task:\d+)&owner=eq\.Exo.*created_at=gte\.([^&]+)", up)
            if m:
                return [x for x in self.notes if x["subject"] == m.group(1) and parse_ts(x["created_at"]) >= parse_ts(m.group(2))]
            m = re.search(r"tags=cs\.\{student-activity:([^}]+)\}", up)
            if m:
                return [t for t in self.tasks if f"student-activity:{m.group(1)}" in t["tags"]][:1]
            m = re.search(r"description=like\.\*(.+?)\*&", up)
            if m:
                return [t for t in self.tasks if m.group(1) in t["description"]][:1]
            m = re.search(r"tags=cs\.\{student-task:(\d+)\}&tags=cs\.\{utd-question\}", up)
            if m:
                return sorted([t for t in self.tasks if f"student-task:{m.group(1)}" in t["tags"]],
                              key=lambda t: -t["id"])[:1]
            return []
        self.nw += 1
        if self.fail_at == self.nw:
            raise urllib.error.URLError("fixture: transient Supabase failure")
        if self.crash_at == self.nw and not self.crash_after:
            raise _Crash("fixture: killed before write reached Supabase")
        if method == "POST" and path == "activities":
            self.notes.append(dict(body, created_at=datetime.now(timezone.utc).isoformat()))
            res = [{"id": f"note-{len(self.notes)}"}]
        elif method == "POST" and path == "tasks":
            self.tasks.append(dict(body, id=1000 + len(self.tasks)))
            res = [{"id": self.tasks[-1]["id"]}]
        elif method == "PATCH":
            tid = int(path.split("eq.")[1])
            next(t for t in self.tasks if t["id"] == tid).update(body)
            res = [{"id": tid}]
        else:
            raise AssertionError(f"unexpected write {method} {path}")
        self.writes.append((method, path, body))
        if self.crash_at == self.nw and self.crash_after:
            raise _Crash("fixture: killed after write landed, before the response")
        return res


def _selftest_fixture():
    import tempfile, types, shutil
    g = globals()
    saved = {k: g[k] for k in ("WS", "DATA", "STATE", "LOG", "OUTBOX", "supa", "students", "subprocess", "DRY",
                               "_ITEM_HOOK", "_OUTBOX_HOOK")}
    real_urlopen = urllib.request.urlopen
    tmp = tempfile.mkdtemp(prefix="capcap-selftest-")
    res = []
    try:
        os.makedirs(os.path.join(tmp, "logs")); os.makedirs(os.path.join(tmp, "mission-control/data"))
        g.update(WS=tmp, DRY=False, DATA=os.path.join(tmp, "exp.jsonl"), STATE=os.path.join(tmp, "state.json"),
                 LOG=os.path.join(tmp, "log.txt"), OUTBOX=os.path.join(tmp, "mission-control/data/capstone-outbox.json"))
        g["students"] = lambda: {"test student": "Test Student"}

        def reset():
            for f in (g["DATA"], g["STATE"]):
                if os.path.exists(f):
                    os.remove(f)

        now = datetime.now(timezone.utc)
        acts = [
            {"id": "a1", "type": "task_note", "subject": "task:101", "owner": "Test Student",
             "created_at": now.isoformat(), "body": "Checked the POC, it is current."},
            {"id": "a2", "type": "task_note", "subject": "task:101", "owner": "Test Student",
             "created_at": now.isoformat(), "body": "how do I find the funding source?"},
            {"id": "a3", "type": "task_note", "subject": "task:101", "owner": "Exo",
             "created_at": now.isoformat(), "body": "Exo: captured"},
        ]
        one_task = [{"id": 101, "title": "Lead card", "state": "In Progress", "owner": "Test Student", "tags": []}]
        sb = _FakeSB(acts, one_task)
        g["supa"] = sb
        main(); first = list(sb.writes)
        main()
        notes = [b for m, p, b in sb.writes if p == "activities"]
        tasks = [b for m, p, b in sb.writes if p == "tasks"]
        rows = [json.loads(l) for l in open(g["DATA"])]
        res.append(("fixture: 2 student notes -> 2 captures, Exo note ignored", len(rows) == 2))
        res.append(("fixture: 1 ack note + 1 question ack, 1 triage task", len(notes) == 2 and len(tasks) == 1))
        res.append(("fixture: re-run posts nothing (no duplicate notes/tasks)", sb.writes == first))
        res.append(("fixture: question triage carries eta + student-task tags",
                    bool(tasks) and "utd-question" in tasks[0]["tags"] and "student-task:101" in tasks[0]["tags"]))

        # ── crash-mid-loop fixtures: plain note, new question, follow-up fold, same-timestamp pair,
        #    15-min Done, Exo note, question on a second task ──
        T = lambda s: (now - timedelta(seconds=60) + timedelta(seconds=s)).isoformat()
        cacts = [
            {"id": "c1", "type": "task_note", "subject": "task:101", "owner": "Test Student", "created_at": T(1), "body": "Checked the POC, it is current."},
            {"id": "c2", "type": "task_note", "subject": "task:101", "owner": "Test Student", "created_at": T(2), "body": "how do I find the funding source?"},
            {"id": "c3", "type": "task_note", "subject": "task:101", "owner": "Test Student", "created_at": T(3), "body": "also, who signs the LOS?"},
            {"id": "c4", "type": "task_note", "subject": "task:102", "owner": "Test Student", "created_at": T(3), "body": "Fit score 7, notes attached."},
            {"id": "c5", "type": "task_update", "subject": "task:102", "owner": "Test Student", "created_at": T(4), "body": "State: In Progress → Done"},
            {"id": "c6", "type": "task_note", "subject": "task:102", "owner": "Exo", "created_at": T(5), "body": "Exo: captured"},
            {"id": "c7", "type": "task_note", "subject": "task:102", "owner": "Test Student", "created_at": T(6), "body": "can you check my draft?"},
        ]
        ctasks = [{"id": 101, "title": "Lead card", "state": "In Progress", "owner": "Test Student", "tags": []},
                  {"id": 102, "title": "Session 3", "state": "Done", "owner": "Test Student", "tags": ["15-min"]},
                  {"id": 103, "title": "Session 4", "state": "To Do", "owner": "Test Student", "tags": ["15-min"],
                   "due_date": T(86400)}]
        stu = [x for x in cacts if x["owner"] != "Exo"]
        questions = [x["id"] for x in stu if x["type"] == "task_note" and is_question(x["body"])]

        def invariants(sb):
            """Every student item captured exactly once, acked exactly once, one triage entry per question."""
            errs = []
            rows = [json.loads(l) for l in open(g["DATA"]) if l.strip()] if os.path.exists(g["DATA"]) else []
            by = {}
            for r in rows:
                by.setdefault(r.get("activity_id"), []).append(r)
            ns = [r["n"] for r in rows]
            if len(ns) != len(set(ns)):
                errs.append("duplicate n")
            for x in stu:
                got = by.get(x["id"], [])
                if len(got) != 1:
                    errs.append(f"{x['id']} captured {len(got)}x"); continue
                if x["type"] == "task_note":
                    k = sum(1 for nt in sb.notes if nt["subject"] == x["subject"]
                            and re.search(_n_ack_pattern(got[0]["n"]), nt["body"]))
                    if k != 1:
                        errs.append(f"{x['id']} acked {k}x")
            k = sum(1 for nt in sb.notes if nt["body"].startswith("🎯"))
            if k != 1:
                errs.append(f"done acked {k}x")
            if len(sb.notes) != len([x for x in stu if x["type"] == "task_note"]) + 1:
                errs.append(f"{len(sb.notes)} Exo notes total")
            for q in questions:
                k = sum(1 for t in sb.tasks if f"student-activity:{q}" in t["tags"]) + \
                    sum(t["description"].count(_src_marker(q)) for t in sb.tasks if f"student-activity:{q}" not in t["tags"])
                if k != 1:
                    errs.append(f"question {q} has {k} triage entries")
            return errs

        def world(sb):
            return (sorted(nt["body"] for nt in sb.notes), [(t["id"], sorted(t["tags"]), t["description"]) for t in sb.tasks])

        reset(); base = _FakeSB(cacts, ctasks); g["supa"] = base
        main()
        W = base.nw
        res.append((f"fixture: clean run baseline ({len(stu)} captures, {len(base.notes)} acks, {len(base.tasks)} triage, 1 fold)",
                    not invariants(base) and len(base.tasks) == 2 and W == 9))

        def rerun_until_quiet(sb):
            g["_ITEM_HOOK"] = None
            for _ in range(3):
                main()

        # (a) process killed after item k (k = 1..all), then rerun
        bad = []
        for k in range(1, len(cacts) + 1):
            reset(); sb = _FakeSB(cacts, ctasks); g["supa"] = sb
            cnt = [0]

            def hook(a, k=k):
                cnt[0] += 1
                if cnt[0] == k:
                    raise _Crash(f"after item {k}")
            g["_ITEM_HOOK"] = hook
            try:
                main()
            except _Crash:
                pass
            rerun_until_quiet(sb)
            e = invariants(sb) + ([] if world(sb) == world(base) else ["world differs from clean run"])
            if e:
                bad.append(f"k={k}: {e}")
        res.append((f"fixture: crash after item k (k=1..{len(cacts)}) + rerun -> no dup acks/triage, all captured"
                    + (" -> " + "; ".join(bad[:3]) if bad else ""), not bad))

        # (b) process killed mid-item on every write, before AND after it lands, then rerun
        bad = []
        for w in range(1, W + 1):
            for after in (False, True):
                reset(); sb = _FakeSB(cacts, ctasks, crash_at=w, crash_after=after); g["supa"] = sb
                try:
                    main()
                except _Crash:
                    pass
                sb.crash_at = None
                rerun_until_quiet(sb)
                e = invariants(sb) + ([] if world(sb) == world(base) else ["world differs from clean run"])
                if e:
                    bad.append(f"w={w} after={after}: {e}")
        res.append((f"fixture: crash mid-item at each of {W} writes (before/after landing) + rerun -> no dups, all captured"
                    + (" -> " + "; ".join(bad[:3]) if bad else ""), not bad))

        # (c) ordinary exception on one item: run continues, failed item left unmarked, next run retries it
        bad = []
        for w in range(1, W + 1):
            reset(); sb = _FakeSB(cacts, ctasks, fail_at=w); g["supa"] = sb
            main()
            st = json.load(open(g["STATE"]))
            unmarked = [x["id"] for x in stu if x["id"] not in st["seen"]]
            if len(unmarked) != 1:
                bad.append(f"w={w}: {len(unmarked)} unmarked after failure")
            elif st["since"] >= next(x["created_at"] for x in stu if x["id"] == unmarked[0]):
                bad.append(f"w={w}: since advanced past failed item")
            sb.fail_at = None
            main(); main()
            e = invariants(sb)
            if e:
                bad.append(f"w={w}: {e}")
        res.append(("fixture: failed item left unmarked + retried next run, nothing lost or duplicated"
                    + (" -> " + "; ".join(bad[:3]) if bad else ""), not bad))

        # outbox: send only on a Lizi Yes; No -> cancelled; open -> untouched; never re-send
        open(os.path.join(tmp, "mission-control/data/.decisions-token"), "w").write("tok")
        json.dump([{"dedupeKey": "k-yes", "status": "answered", "answer": "Yes — send"},
                   {"dedupeKey": "k-no", "status": "answered", "answer": "No"}],
                  open(os.path.join(tmp, "mission-control/data/decisions.json"), "w"))
        mk = lambda key, dd, n=1: {"key": key, "decision_dedupe": dd, "status": "pending", "cc": "lquinn@exosaero.com",
                                   "reply_to": "lquinn@exosaero.com",
                                   "emails": [{"to": f"s{i}@utdallas.edu", "subject": "s", "body": "b"} for i in range(1, n + 1)]}
        json.dump([mk("yes", "k-yes"), mk("no", "k-no"), mk("open", "k-open")], open(g["OUTBOX"], "w"))
        urllib.request.urlopen = lambda *a, **k: __import__("io").BytesIO(
            json.dumps([{"dedupeKey": "k-open", "status": "open"}]).encode())
        sends = []
        crash_send = [None]

        def fake_run(argv, **k):
            sends.append(argv[3])
            if crash_send[0] == len(sends):
                raise _Crash("killed during msmtp")  # delivery outcome unknown
            return types.SimpleNamespace(returncode=0, stderr=b"")
        g["subprocess"] = types.SimpleNamespace(run=fake_run)
        process_outbox(); process_outbox()
        ob = {x["key"]: x for x in json.load(open(g["OUTBOX"]))}
        res.append(("fixture: outbox sends ONLY the Lizi-Yes item, exactly once", len(sends) == 1
                    and ob["yes"]["status"] == "sent"))
        res.append(("fixture: outbox No -> cancelled, open Decision -> still pending",
                    ob["no"]["status"] == "cancelled" and ob["open"]["status"] == "pending"))
        # outbox crash: (A) killed after email 1's result persisted -> rerun sends only email 2;
        #               (B) killed inside msmtp for email 2 -> rerun never re-sends it (partial, flagged)
        bad = []
        for case in ("A", "B"):
            sends.clear()
            json.dump([mk("yes", "k-yes", 3)], open(g["OUTBOX"], "w"))
            crash_send[0] = 2 if case == "B" else None

            def ohook(item, e, case=case):
                if case == "A" and e["to"] == "s1@utdallas.edu":
                    raise _Crash("after email 1")
            g["_OUTBOX_HOOK"] = ohook
            try:
                process_outbox()
            except _Crash:
                pass
            g["_OUTBOX_HOOK"] = None; crash_send[0] = None
            process_outbox(); process_outbox()
            it = json.load(open(g["OUTBOX"]))[0]
            if len(sends) != len(set(sends)):
                bad.append(f"{case}: re-sent {sends}")
            if case == "A" and not (sorted(sends) == ["s1@utdallas.edu", "s2@utdallas.edu", "s3@utdallas.edu"]
                                    and it["status"] == "sent"):
                bad.append(f"A: sends={sends} status={it['status']}")
            if case == "B" and not (sorted(sends) == ["s1@utdallas.edu", "s2@utdallas.edu", "s3@utdallas.edu"]
                                    and it["status"] == "partial" and it["sent"][1]["ok"] is None
                                    and len(it["sent"]) == 3):
                bad.append(f"B: sends={sends} status={it['status']}")
        res.append(("fixture: outbox crash mid-send + rerun -> never double-sends, rest still delivered"
                    + (" -> " + "; ".join(bad) if bad else ""), not bad))
        res.append(("fixture: is_question rules", is_question("can you check this?") and
                    not is_question("see https://x.com/?a=1") and not is_question("PASS: contact ok, can you")
                    and is_question("PASS: @exo is this right")))
        e = compute_eta(datetime(2026, 10, 22, 2, 0, tzinfo=timezone.utc))  # 21:00 CT + 4h -> next 10 AM
        res.append(("fixture: ETA never lands 9 PM-8 AM CT", e.astimezone(CT).hour == 10))
    finally:
        urllib.request.urlopen = real_urlopen
        g.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def _selftest_live():
    res = []
    # 1. outbox: every sent item was released by a Lizi Yes before it went out; students only; once each
    try:
        ob = json.load(open(OUTBOX)) if os.path.exists(OUTBOX) else []
        local = json.load(open(os.path.join(WS, "mission-control/data/decisions.json")))
        decs = {z.get("dedupeKey"): z for z in (local if isinstance(local, list) else local.get("decisions", []))}
        errs = []
        keys = [x.get("key") for x in ob]
        if len(keys) != len(set(keys)):
            errs.append("duplicate outbox key")
        for x in ob:
            if x.get("status") not in ("sent", "partial"):
                continue
            to = [e["to"].lower() for e in x.get("emails", [])]
            if len(to) != len(set(to)):
                errs.append(f"{x['key']}: duplicate recipient")
            if any(not t.endswith(STUDENT_DOMAIN) for t in to):
                errs.append(f"{x['key']}: non-student recipient")
            if len(x.get("sent") or []) != len(to):
                errs.append(f"{x['key']}: sent {len(x.get('sent') or [])} for {len(to)} staged emails")
            if (x.get("sent_at") or "") < OUTBOX_LEGACY_BEFORE and x.get("decision_answer"):
                continue  # pre-Decision release, recorded explicitly
            d = decs.get(x.get("decision_dedupe"))
            if not d or d.get("status") != "answered" or not (d.get("answer") or "").strip().lower().startswith("yes"):
                errs.append(f"{x['key']}: sent without a Yes on Decision {x.get('decision_dedupe')}")
            elif (d.get("answeredAt") or "") and parse_ts(d["answeredAt"]) > parse_ts(x["sent_at"]):
                errs.append(f"{x['key']}: sent before the Decision was answered")
        res.append(("live: outbox sends only after Lizi-Yes, students only, once each"
                    + (" -> " + "; ".join(errs) if errs else ""), not errs))
    except Exception as e:
        res.append((f"live: outbox check error {e}", False))
    # 2. experiment dataset: no activity captured twice since the baseline
    try:
        rows = [json.loads(l) for l in open(DATA) if l.strip()]
        seen, dup = set(), []
        for r in rows:
            if (r.get("ts") or "") < DUP_BASELINE:
                continue
            k = (r.get("ts"), r.get("task_id"), r.get("kind"), r.get("body"))
            (dup.append(k) if k in seen else seen.add(k))
        res.append((f"live: capstone-experiments.jsonl no duplicate captures since {DUP_BASELINE[:10]}"
                    + (f" -> {len(dup)} dup(s) e.g. task {dup[0][1]} {dup[0][0]}" if dup else ""), not dup))
    except Exception as e:
        res.append((f"live: dataset check error {e}", False))
    # 3. Supabase (GET only): no identical Exo ack posted twice on a student task in the last 7 days
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        rows = supa("GET", "activities?select=subject,body,created_at&owner=eq.Exo&type=eq.task_note"
                           f"&created_at=gt.{urllib.parse.quote(since)}&body=like.*data%20point%20%23*&limit=5000")
        c = {}
        for r in rows:
            k = (r.get("subject"), r.get("body"))
            c[k] = c.get(k, 0) + 1
        dup = [(k[0], v) for k, v in c.items() if v > 1]
        res.append((f"live: no duplicate Exo acks on student tasks (7d, {len(rows)} acks)"
                    + (f" -> {dup[:5]}" if dup else ""), not dup))
    except Exception as e:
        res.append((f"live: Supabase read error {e}", False))
    return res


def selftest():
    res = _selftest_fixture() + _selftest_live()
    for name, ok in res:
        print(("PASS " if ok else "FAIL ") + name)
    nf = sum(1 for _, ok in res if not ok)
    print(f"capstone_capture selftest: {'PASS' if not nf else 'FAIL'} ({len(res) - nf}/{len(res)})")
    return 0 if not nf else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    if DRY:
        if "--fake" in sys.argv:
            dry_run_fake()
        sys.exit(0)
    main()
    try:
        process_outbox()
    except Exception as e:
        log(f"outbox error: {e}")
