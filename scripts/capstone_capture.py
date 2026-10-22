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
import os, re, sys, json, subprocess, urllib.request, urllib.parse
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
                 f"\n\nALSO ANSWER — follow-up from {author} ({a['created_at'][:16]}):\n{a.get('body')}"})
            try:
                eta = parse_ts(ex["due_date"])
            except Exception:
                pass
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


def main():
    st = {"since": SINCE_DEFAULT, "seen": [], "n": 0}
    if os.path.exists(STATE):
        st.update(json.load(open(STATE)))
    seen = set(st["seen"])
    who = students()
    tasks = supa("GET", "tasks?select=id,title,state,owner,due_date,source,tags&assigned_email=ilike.*utdallas*")
    by_id = {t["id"]: t for t in tasks}
    subj = ",".join(f"task:{i}" for i in by_id)
    q = (f"activities?select=id,type,subject,body,owner,created_at&type=in.(task_note,task_update)"
         f"&created_at=gt.{urllib.parse.quote(st['since'])}&subject=in.({urllib.parse.quote(subj)})&order=created_at")
    acts = supa("GET", q)
    captured = 0
    for a in acts:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        author = (a.get("owner") or "").strip()
        if author.lower() not in who:
            continue  # Exo / staff / automation
        tid = int(a["subject"].split(":")[1])
        t = by_id.get(tid, {})
        tags = t.get("tags") or []
        body = a.get("body") or ""
        is_done = a["type"] == "task_update" and re.search(r"State: .*→ Done", body)
        if a["type"] == "task_update" and not is_done and "State:" not in body:
            continue
        st["n"] += 1
        rec = {"n": st["n"], "ts": a["created_at"], "student": who[author.lower()], "task_id": tid,
               "task": t.get("title"), "kind": "done" if is_done else ("state" if a["type"] == "task_update" else "note"),
               "session": next((x[8:] for x in tags if x.startswith("session:")), None),
               "lead": next((x[5:] for x in tags if x.startswith("lead:")), None), "body": body}
        with open(DATA, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        captured += 1

        if rec["kind"] == "note":
            if is_question(body):
                handle_question(a, author, tid, t, rec["n"])
            else:
                reply(tid, f"✅ Exo: captured as data point #{rec['n']} for Team Atlas's human-vs-AI experiment. "
                           "Thanks! When you're done, drag this task to Done.")
        elif rec["kind"] == "done" and "15-min" in tags:
            mine = [x for x in tasks if (x.get("owner") or "").lower() == author.lower() and "15-min" in (x.get("tags") or [])]
            done = sum(1 for x in mine if x["state"] == "Done" or x["id"] == tid)
            nxt = sorted([x for x in mine if x["state"] != "Done" and x["id"] != tid], key=lambda x: x.get("due_date") or "")
            msg = f"🎯 Exo: session complete. You've closed {done} of {len(mine)} this week."
            msg += (f" Next up: #{nxt[0]['id']} {nxt[0]['title']} (due {fmt_due(nxt[0].get('due_date') or '')})."
                    if nxt else " That's all of your sessions for the week. Great work!")
            reply(tid, msg)
    if acts:
        st["since"] = acts[-1]["created_at"]
    st["seen"] = list(seen)[-3000:]
    json.dump(st, open(STATE, "w"))
    if captured:
        log(f"captured {captured} (total {st['n']})")


OUTBOX = os.path.join(WS, "mission-control/data/capstone-outbox.json")


def process_outbox():
    """Send staged student emails ONLY after Lizi answers their Decision Yes (Jon 9/27:
    Lizi releases, Exo sends directly as the team's prompter). No → cancelled."""
    if not os.path.exists(OUTBOX):
        return
    ob = json.load(open(OUTBOX))
    pend = [x for x in ob if x.get("status") == "pending"]
    if not pend:
        return
    tok = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
    req = urllib.request.Request("http://localhost:8080/api/decisions", headers={"X-Exo-Token": tok})
    decs = json.load(urllib.request.urlopen(req, timeout=20))
    # the API lists only open decisions now; answered ones live in decisions.json
    local = json.load(open(os.path.join(WS, "mission-control/data/decisions.json")))
    decs += local if isinstance(local, list) else local.get("decisions", [])
    for item in pend:
        d = next((z for z in decs if z.get("dedupeKey") == item["decision_dedupe"]), None)
        if not d or d.get("status") != "answered":
            continue
        ans = (d.get("answer") or "").strip().lower()
        if not ans.startswith("yes"):
            item["status"] = "cancelled"; item["decision_answer"] = d.get("answer")
            log(f"outbox {item['key']} cancelled: {d.get('answer')}"); continue
        sent = []
        for e in item["emails"]:
            m = EmailMessage()
            m["From"] = "Exo (Exos Mission Control) <jquinnexo@pm.me>"
            m["To"] = e["to"]; m["Cc"] = item["cc"]; m["Reply-To"] = item["reply_to"]
            m["Subject"] = e["subject"]; m.set_content(e["body"])
            p = subprocess.run(["msmtp", "-a", "protonmail", e["to"], item["cc"]], input=m.as_bytes(), capture_output=True)
            ok = p.returncode == 0
            sent.append({"to": e["to"], "ok": ok, "err": p.stderr.decode()[:120]})
            log(f"outbox {item['key']} -> {e['to']} ok={ok}")
        item["status"] = "sent" if all(x["ok"] for x in sent) else "partial"
        item["sent"] = sent; item["sent_at"] = datetime.now(timezone.utc).isoformat()
    json.dump(ob, open(OUTBOX, "w"), indent=1, ensure_ascii=False)


# ── OUTPUT eval (exo3 R5): `capstone_capture.py selftest` ─────────────────────
# Read-only: fixtures in a temp dir (fake Supabase / decisions API / msmtp) + read-only checks of
# the real outputs. No sends, no Supabase writes, no student contact.
DUP_BASELINE = "2026-10-11T00:00:00+00:00"   # 10/10 re-capture loop (n=373/374 x9) predates the parse_ts fix
OUTBOX_LEGACY_BEFORE = "2026-09-28T00:00:00+00:00"  # wk5-prompter: released by Jon directly, pre-Decision flow
STUDENT_DOMAIN = "@utdallas.edu"


def _selftest_fixture():
    import tempfile, types, shutil
    g = globals()
    saved = {k: g[k] for k in ("WS", "DATA", "STATE", "LOG", "OUTBOX", "supa", "students", "subprocess", "DRY")}
    real_urlopen = urllib.request.urlopen
    tmp = tempfile.mkdtemp(prefix="capcap-selftest-")
    res = []
    try:
        os.makedirs(os.path.join(tmp, "logs")); os.makedirs(os.path.join(tmp, "mission-control/data"))
        g.update(WS=tmp, DRY=False, DATA=os.path.join(tmp, "exp.jsonl"), STATE=os.path.join(tmp, "state.json"),
                 LOG=os.path.join(tmp, "log.txt"), OUTBOX=os.path.join(tmp, "mission-control/data/capstone-outbox.json"))
        now = datetime.now(timezone.utc)
        acts = [
            {"id": "a1", "type": "task_note", "subject": "task:101", "owner": "Test Student",
             "created_at": now.isoformat(), "body": "Checked the POC, it is current."},
            {"id": "a2", "type": "task_note", "subject": "task:101", "owner": "Test Student",
             "created_at": now.isoformat(), "body": "how do I find the funding source?"},
            {"id": "a3", "type": "task_note", "subject": "task:101", "owner": "Exo",
             "created_at": now.isoformat(), "body": "Exo: captured"},
        ]
        posts = []

        def fake_supa(method, path, body=None):
            if method == "GET" and path.startswith("tasks?select=id,title,state,owner"):
                return [{"id": 101, "title": "Lead card", "state": "In Progress", "owner": "Test Student", "tags": []}]
            if method == "GET" and path.startswith("activities?"):
                return list(acts)
            if method == "GET":
                return []
            posts.append((method, path, body))
            return [{"id": 900 + len(posts)}]
        g["supa"] = fake_supa
        g["students"] = lambda: {"test student": "Test Student"}
        main(); first = list(posts)
        main()
        notes = [b for m, p, b in posts if p == "activities"]
        tasks = [b for m, p, b in posts if p == "tasks"]
        rows = [json.loads(l) for l in open(g["DATA"])]
        res.append(("fixture: 2 student notes -> 2 captures, Exo note ignored", len(rows) == 2))
        res.append(("fixture: 1 ack note + 1 question ack, 1 triage task", len(notes) == 2 and len(tasks) == 1))
        res.append(("fixture: re-run posts nothing (no duplicate notes/tasks)", posts == first))
        res.append(("fixture: question triage carries eta + student-task tags",
                    bool(tasks) and "utd-question" in tasks[0]["tags"] and "student-task:101" in tasks[0]["tags"]))
        # outbox: send only on a Lizi Yes; No -> cancelled; open -> untouched; never re-send
        open(os.path.join(tmp, "mission-control/data/.decisions-token"), "w").write("tok")
        json.dump([{"dedupeKey": "k-yes", "status": "answered", "answer": "Yes — send"},
                   {"dedupeKey": "k-no", "status": "answered", "answer": "No"}],
                  open(os.path.join(tmp, "mission-control/data/decisions.json"), "w"))
        mk = lambda key, dd: {"key": key, "decision_dedupe": dd, "status": "pending", "cc": "lquinn@exosaero.com",
                              "reply_to": "lquinn@exosaero.com",
                              "emails": [{"to": "s1@utdallas.edu", "subject": "s", "body": "b"}]}
        json.dump([mk("yes", "k-yes"), mk("no", "k-no"), mk("open", "k-open")], open(g["OUTBOX"], "w"))
        urllib.request.urlopen = lambda *a, **k: __import__("io").BytesIO(
            json.dumps([{"dedupeKey": "k-open", "status": "open"}]).encode())
        sends = []
        g["subprocess"] = types.SimpleNamespace(run=lambda argv, **k: sends.append(argv) or
                                                types.SimpleNamespace(returncode=0, stderr=b""))
        process_outbox(); process_outbox()
        ob = {x["key"]: x for x in json.load(open(g["OUTBOX"]))}
        res.append(("fixture: outbox sends ONLY the Lizi-Yes item, exactly once", len(sends) == 1
                    and ob["yes"]["status"] == "sent"))
        res.append(("fixture: outbox No -> cancelled, open Decision -> still pending",
                    ob["no"]["status"] == "cancelled" and ob["open"]["status"] == "pending"))
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
