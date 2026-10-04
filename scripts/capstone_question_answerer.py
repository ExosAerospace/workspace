#!/usr/bin/env python3
"""
capstone_question_answerer.py — makes sure every UTD capstone student question gets answered.

capstone_capture.py turns a student question into an Exo triage task tagged utd-question
(+ eta:<ISO>, student-task:<id>) and acks the student with a concrete ETA. This job
(launchd com.exos.capstone-question-answerer, every 15 min):

  1. DISPATCH: each open utd-question task → one detached WORKER (`<this> worker --triage <id>
     --attempt <n>`). The model is NOT in the critical path: the worker runs
     `openclaw agent --json` (fresh session per attempt), the agent only RETURNS the answer text
     between <<<ANSWER>>> ... <<<END>>> (it is told not to post anything). The worker validates it
     (rc 0, markers present, not truncated, no BLOCKED, non-empty, sane length), posts it itself
     (same activity insert as capstone_capture.reply()), marks the triage task Done, and only
     counts success after re-reading the activity row and the Done state from Supabase.
     An "ANSWERED" line from the model is never trusted.
  2. RETRY: a failed attempt is retried ≥15 min after it failed, up to MAX_ATTEMPTS (3).
     A worker with no result after WORKER_STALE is counted as failed.
  3. ESCALATION (SLA watchdog): when attempts are exhausted OR the current ETA has passed
     (whichever first) → ONE holding note to the student with a new ETA + ONE Discord alert
     to #1539382179120021616 via `openclaw message send`. The new ETA is written back to the
     task's eta: tag and due_date, so if it ALSO slips the watchdog fires again
     (up to MAX_ESCALATIONS notes per question; the daily stale check covers anything beyond).
  4. STALE CHECK (`stale-check`, launchd com.exos.capstone-question-stale-check, 9:00 AM CT):
     Discord alert listing every utd-question open > 8 h. Silent when there are none.

State: logs/capstone-question-answerer-state.json (dispatched / escalations / skip).
Worker results: logs/capstone-question-agent/<id>-a<n>.result.json (+ raw agent JSON .out.json).

  capstone_question_answerer.py                    # normal run
  capstone_question_answerer.py --dry-run [--fake] # no dispatch, no writes, no state change
  capstone_question_answerer.py worker --triage <id> --attempt <n> [--dry-run]
  capstone_question_answerer.py stale-check [--dry-run]
  capstone_question_answerer.py post-answer --triage <id> --file <answer.txt>   # manual path
"""
import os, re, sys, json, subprocess, tempfile, argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone_capture as cc  # noqa: E402  (shares supa/reply/ETA helpers)

WS = cc.WS
STATE = os.path.join(WS, "logs/capstone-question-answerer-state.json")
LOG = os.path.join(WS, "logs/capstone-question-answerer.log")
RUNLOG_DIR = os.path.join(WS, "logs/capstone-question-agent")
DISCORD_CHANNEL = "1539382179120021616"
MAX_ATTEMPTS = 3
RETRY_GAP = timedelta(minutes=15)
AGENT_TIMEOUT_S = 900
WORKER_STALE = timedelta(seconds=AGENT_TIMEOUT_S + 600)   # no result file by then = failed attempt
MAX_DISPATCH_PER_RUN = 3
MAX_ESCALATIONS = 2          # student holding notes per question; daily stale check covers the rest
STALE_HOURS = 8
MAX_ANSWER_WORDS = 450       # prompt asks for ≤250; anything this long ignored the brief
OPEN_STATES = "(Done,Cancelled)"
SELF = os.path.abspath(__file__)
A_OPEN, A_END = "<<<ANSWER>>>", "<<<END>>>"
# Being answered by other agents — never auto-dispatch / escalate these (stale-check still sees them).
BACKLOG = [3204, 3221, 3230, 3235, 3285, 3292, 3293, 3294, 3295, 3299, 3300,  # 2026-10-01
           3357, 3358, 3359, 3360, 3361, 3362, 3363]                           # 2026-10-04 backlog

DRY = "--dry-run" in sys.argv
cc.DRY = DRY


def log(m):
    line = f"[{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}] {m}"
    if DRY:
        print(line)
        return
    with open(LOG, "a") as f:
        f.write(line + "\n")


def now_utc():
    return datetime.now(timezone.utc)


def load_state():
    st = {"dispatched": {}, "escalations": {}, "skip": list(BACKLOG)}
    if os.path.exists(STATE):
        st.update(json.load(open(STATE)))
    st.setdefault("escalations", {})
    st["skip"] = sorted(set(st["skip"]) | set(BACKLOG))
    return st


def save_state(st):
    if DRY:
        return
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def tag(t, prefix):
    return next((x[len(prefix):] for x in (t.get("tags") or []) if x.startswith(prefix)), None)


def student_task_id(t):
    v = tag(t, "student-task:")
    if v:
        return int(v)
    m = re.search(r"\(task #(\d+)\)", t.get("title") or "")
    return int(m.group(1)) if m else None


def open_questions():
    return cc.supa("GET", "tasks?select=id,title,state,description,due_date,tags,created_at"
                          f"&tags=cs.%7Butd-question%7D&state=not.in.{OPEN_STATES}&order=id")


def get_task(tid):
    r = cc.supa("GET", f"tasks?select=id,title,state,description,due_date,tags,created_at&id=eq.{tid}")
    return r[0] if r else None


# ── prompt ───────────────────────────────────────────────────────────────────
def build_message(t):
    sid = student_task_id(t)
    student_task = {}
    note = ""
    if sid:
        r = cc.supa("GET", f"tasks?select=id,title,description,owner&id=eq.{sid}")
        student_task = r[0] if r else {}
    act_id = tag(t, "student-activity:")
    if act_id:
        r = cc.supa("GET", f"activities?select=body,owner,created_at&id=eq.{act_id}")
        note = r[0]["body"] if r else ""
    if not note:  # fall back to the note quoted in the triage description
        note = (t.get("description") or "").split("\n\n")[1] if "\n\n" in (t.get("description") or "") else ""
    return f"""UTD CAPSTONE STUDENT QUESTION — write the answer. Triage task #{t['id']}.

STUDENT NOTE (verbatim):
<<<
{note}
>>>

STUDENT'S TASK #{sid}: {student_task.get('title', '?')} (owner: {student_task.get('owner', '?')})
Task description:
<<<
{(student_task.get('description') or '')[:4000]}
>>>

TRIAGE TASK #{t['id']}: {t['title']}
<<<
{(t.get('description') or '')[:3000]}
>>>

INSTRUCTIONS
1. Write the answer to the student's question as Exo, for their task #{sid}. Be direct, short,
   useful. If the triage description has "ALSO ANSWER" follow-ups, answer every one in the same answer.
2. PROGRAM-SAFE ONLY: the student is a sandboxed UTD early_adopter under NDA. Public / program
   information only. NO pricing, customers, financials, CUI/ITAR/export-controlled data, or any
   internal data. Questions about assignments, priorities, grading or scope → say Lizi will
   confirm, and route it to Lizi (mention "Lizi" in the answer).
3. SOURCING GUARDRAIL: make NO factual statement without a credible, current source
   (primary/official, dated 2023 or later), linked inline next to the claim. If you cannot find
   one, say plainly that it could not be verified. Treat these Exos claims as UNVERIFIED unless
   you find a current primary source: "only one selling payload slots", "2-3 day turnaround",
   "fastest recover-and-refly", "Flight 1 booked". Do not repeat them as fact.
   (Read-only web lookups to check sources are fine.)
4. DO NOT POST ANYTHING. Do not run any command, script, terminal or file tool to post, do not
   write files, do not email, do not post to Discord. The calling script posts your answer.
5. OUTPUT FORMAT — your reply must be ONLY the answer text, under 250 words, wrapped exactly:
{A_OPEN}
<the answer the student will read, plain text / markdown, no preamble>
{A_END}
   Nothing before {A_OPEN} or after {A_END}. If you truly cannot answer, reply with a single line
   BLOCKED: <reason>  (and no markers).
"""


# ── validation (pure; unit-tested) ──────────────────────────────────────────
TRUNC_RE = re.compile(r"truncated at the model'?s output token limit|reply truncated", re.I)
TRUNC_FINISH = {"length", "max_tokens", "max_output_tokens", "token_limit", "truncated"}


def parse_agent_output(raw, rc=0):
    """raw = stdout of `openclaw agent --json` (or plain text). Returns (answer|None, error|None)."""
    if rc != 0:
        return None, f"openclaw agent rc={rc}: {(raw or '')[-200:]!r}"
    text, finish = raw or "", ""
    try:
        d = json.loads(raw)
        if d.get("status") not in (None, "ok"):
            return None, f"agent status={d.get('status')}: {str(d.get('summary'))[:200]}"
        res = d.get("result") or {}
        meta = res.get("meta") or {}
        text = ((meta.get("terminalReply") or {}).get("text")
                or meta.get("finalAssistantVisibleText")
                or "\n".join(p.get("text") or "" for p in res.get("payloads") or []))
        comp = meta.get("completion") or {}
        finish = str(comp.get("finishReason") or comp.get("stopReason") or "").lower()
    except (ValueError, AttributeError):
        pass  # plain-text output
    text = text or ""
    if finish in TRUNC_FINISH or TRUNC_RE.search(text):
        return None, f"truncated output (finish={finish or 'n/a'})"
    m = re.search(r"\bBLOCKED\b.*", text)
    if m:
        return None, f"agent BLOCKED: {m.group(0)[:200]}"
    i = text.find(A_OPEN)
    if i < 0:
        return None, "missing <<<ANSWER>>> marker"
    j = text.find(A_END, i + len(A_OPEN))
    if j < 0:
        return None, "missing <<<END>>> marker (truncated?)"
    ans = text[i + len(A_OPEN):j].strip()
    if not ans:
        return None, "empty answer"
    if A_OPEN in ans:
        return None, "nested/duplicated markers"
    n = len(ans.split())
    if n > MAX_ANSWER_WORDS:
        return None, f"answer too long ({n} words > {MAX_ANSWER_WORDS})"
    return ans, None


# ── posting (verified) ──────────────────────────────────────────────────────
def post_and_verify(triage_id, sid, answer):
    """Same insert as cc.reply(); success = the activity row reads back AND triage reads back Done."""
    body = answer if answer.startswith(("Exo", "💬")) else f"💬 Exo: {answer}"
    if DRY:
        cc.supa("POST", "activities", {"type": "task_note", "subject": f"task:{sid}", "body": body,
                                       "owner": "Exo", "status": "completed"})
        return True, "dry-run"
    row = cc.supa("POST", "activities", {"type": "task_note", "subject": f"task:{sid}", "body": body,
                                         "owner": "Exo", "status": "completed"})
    aid = row[0].get("id") if row else None
    chk = cc.supa("GET", f"activities?select=id,subject&id=eq.{aid}") if aid else []
    if not chk or chk[0].get("subject") != f"task:{sid}":
        return False, f"activity row not found after insert (id={aid})"
    cc.supa("PATCH", f"tasks?id=eq.{triage_id}", {"state": "Done", "completed_at": now_utc().isoformat()})
    t = get_task(triage_id)
    if not t or t.get("state") != "Done":
        return False, f"activity {aid} posted but triage #{triage_id} not Done (state={t and t.get('state')})"
    return True, f"activity {aid}"


def result_path(tid, attempt):
    return os.path.join(RUNLOG_DIR, f"{tid}-a{attempt}.result.json")


def worker(triage_id, attempt, fake_raw=None, fake_task=None):
    """One attempt: agent → parse → validate → post → verify. Writes the result file."""
    res = {"triage": triage_id, "attempt": attempt, "started": now_utc().isoformat()}
    try:
        t = fake_task or get_task(triage_id)
        if not t:
            res.update(ok=False, error="triage task not found")
        elif t.get("state") in ("Done", "Cancelled"):
            res.update(ok=True, skipped=f"already {t['state']}")
        elif not student_task_id(t):
            res.update(ok=False, error="no student task id")
        else:
            if fake_raw is not None:
                raw, rc = fake_raw, 0
            else:
                msg = build_message(t)
                os.makedirs(RUNLOG_DIR, exist_ok=True)
                fd, mpath = tempfile.mkstemp(prefix=f"utdq-{triage_id}-a{attempt}-", suffix=".md", dir=RUNLOG_DIR)
                with os.fdopen(fd, "w") as f:
                    f.write(msg)
                skey = f"agent:main:utd-question-{triage_id}-a{attempt}-{int(now_utc().timestamp())}"  # fresh ctx
                p = subprocess.run(["openclaw", "agent", "--session-key", skey, "--timeout", str(AGENT_TIMEOUT_S),
                                    "--json", "--message-file", mpath],
                                   capture_output=True, text=True, timeout=AGENT_TIMEOUT_S + 300, cwd=WS)
                raw, rc = p.stdout, p.returncode
                if not DRY:
                    with open(os.path.join(RUNLOG_DIR, f"{triage_id}-a{attempt}.out.json"), "w") as f:
                        f.write(raw + ("\n--- stderr ---\n" + p.stderr[-4000:] if p.stderr else ""))
            ans, err = parse_agent_output(raw, rc)
            if err:
                res.update(ok=False, error=err)
            else:
                # re-check right before posting: a human/other agent may have answered meanwhile
                t2 = fake_task or get_task(triage_id)
                if t2 and t2.get("state") in ("Done", "Cancelled"):
                    res.update(ok=True, skipped=f"closed during attempt ({t2['state']})")
                else:
                    ok, info = post_and_verify(triage_id, student_task_id(t), ans)
                    res.update(ok=ok, info=info, words=len(ans.split()))
                    if not ok:
                        res["error"] = info
    except subprocess.TimeoutExpired:
        res.update(ok=False, error="openclaw agent timed out")
    except Exception as e:  # noqa: BLE001 — any failure must surface as a failed attempt, never silence
        res.update(ok=False, error=f"{type(e).__name__}: {e}"[:300])
    res["finished"] = now_utc().isoformat()
    log(f"worker #{triage_id} a{attempt}: " + ("OK " + str(res.get("info") or res.get("skipped"))
                                               if res["ok"] else "FAIL " + res["error"]))
    if DRY:
        print(json.dumps(res))
    else:
        os.makedirs(RUNLOG_DIR, exist_ok=True)
        with open(result_path(triage_id, attempt) + ".tmp", "w") as f:
            json.dump(res, f)
        os.replace(result_path(triage_id, attempt) + ".tmp", result_path(triage_id, attempt))
    return res


def spawn_worker(tid, attempt):
    cmd = [sys.executable, SELF, "worker", "--triage", str(tid), "--attempt", str(attempt)]
    if DRY:
        print(f"[dry-run] would spawn: {' '.join(cmd)}")
        return
    os.makedirs(RUNLOG_DIR, exist_ok=True)
    out = open(os.path.join(RUNLOG_DIR, f"{tid}-a{attempt}.worker.log"), "a")
    # detached: an agent turn can take up to 15 min; don't block the 15-min launchd cadence
    subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                     start_new_session=True, cwd=WS)


def discord(text):
    cmd = ["openclaw", "message", "send", "--channel", "discord", "--target", f"channel:{DISCORD_CHANNEL}",
           "-m", text]
    if DRY:
        print("[dry-run] " + " ".join(cmd[:-2]) + f" -m {text!r}")
        return True
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except Exception as e:  # noqa: BLE001
        log(f"discord send exception: {e}")
        return False
    if p.returncode != 0:
        log(f"discord send failed rc={p.returncode}: {(p.stderr or p.stdout)[-300:]}")
    return p.returncode == 0


# ── main loop ───────────────────────────────────────────────────────────────
def current_eta(t, st):
    """Latest promised ETA: escalation new_eta > eta: tag > due_date."""
    esc = st["escalations"].get(str(t["id"])) or []
    if esc:
        return cc.parse_ts(esc[-1]["new_eta"])
    s = tag(t, "eta:") or t.get("due_date")
    return cc.parse_ts(s) if s else None


def refresh_attempt(k, d, now):
    """Fold a finished worker's result file into state. Returns d."""
    if d.get("status") != "running":
        return d
    rp = result_path(k, d["attempts"])
    if os.path.exists(rp):
        r = json.load(open(rp))
        d["status"] = "ok" if r.get("ok") else "failed"
        d["finished_at"] = r.get("finished")
        if not r.get("ok"):
            d["last_error"] = r.get("error")
    elif now - cc.parse_ts(d["at"]) > WORKER_STALE:
        d.update(status="failed", finished_at=now.isoformat(), last_error="worker produced no result (stale)")
    return d


def escalate(t, st, now, reason, eta, sid_reply=True):
    """One holding note to the student + one Discord alert; new ETA written back to the task."""
    k = str(t["id"])
    esc = st["escalations"].setdefault(k, [])
    new_eta = cc.compute_eta(max(eta, now) if eta else now)
    sid = student_task_id(t)
    noted = False
    if sid and sid_reply:
        cc.reply(sid, f"⏳ Exo: Still working on this. New ETA: {cc.fmt_eta(new_eta)} (ref #{k}).")
        noted = True
    tags = [x for x in (t.get("tags") or []) if not x.startswith("eta:")] + [f"eta:{new_eta.isoformat()}"]
    cc.supa("PATCH", f"tasks?id=eq.{t['id']}", {"due_date": new_eta.isoformat(), "tags": tags})
    d = st["dispatched"].get(k) or {}
    ok = discord(f"⏰ UTD question needs a human: triage task #{k} \"{' '.join(t['title'].split())[:120]}\" — {reason}. "
                 f"Auto-answer attempts: {d.get('attempts', 0)}/{MAX_ATTEMPTS}"
                 + (f" (last error: {d['last_error'][:160]})" if d.get("last_error") else "")
                 + (f". Student told new ETA {cc.fmt_eta(new_eta)}." if noted else
                    f". No student task found to notify; ETA moved to {cc.fmt_eta(new_eta)}.")
                 + (" Last automatic alert for this question; daily 9 AM check keeps listing it."
                    if len(esc) + 1 >= MAX_ESCALATIONS else ""))
    esc.append({"at": now.isoformat(), "reason": reason, "old_eta": eta.isoformat() if eta else None,
                "new_eta": new_eta.isoformat(), "student_noted": noted, "discord_ok": ok})
    log(f"ESCALATED #{k} ({reason}): student noted={noted}, new ETA {new_eta.isoformat()}, discord ok={ok}")
    return ok


def run(fake=None, now=None):
    st = load_state()
    now = now or now_utc()
    tasks = list(open_questions())
    if fake:
        tasks.append(fake)
    skip = set(st["skip"])
    for k, d in st["dispatched"].items():   # fold finished workers (incl. tasks already closed) into state
        if d.get("status") == "running":
            refresh_attempt(k, d, now)
    n_disp = 0
    for t in tasks:
        k = str(t["id"])
        if t["id"] in skip:
            continue
        d = st["dispatched"].get(k)
        if d is not None and "status" not in d:   # legacy (pre-2026-10-04) entry: treat as failed attempt(s)
            d.update(status="failed", finished_at=d["at"], last_error="legacy dispatch (agent self-post)")
        if d is not None:
            refresh_attempt(k, d, now)
        # 1. dispatch / retry (≥15 min after a failure, up to MAX_ATTEMPTS)
        if d is None and n_disp < MAX_DISPATCH_PER_RUN:
            spawn_worker(t["id"], 1)
            st["dispatched"][k] = d = {"at": now.isoformat(), "attempts": 1, "status": "running"}
            n_disp += 1
            log(f"dispatched #{k} attempt 1")
        elif (d and d["status"] == "failed" and d["attempts"] < MAX_ATTEMPTS
              and now - cc.parse_ts(d.get("finished_at") or d["at"]) >= RETRY_GAP and n_disp < MAX_DISPATCH_PER_RUN):
            n = d["attempts"] + 1
            spawn_worker(t["id"], n)
            d.update(at=now.isoformat(), attempts=n, status="running")
            n_disp += 1
            log(f"retry #{k} attempt {n} (last error: {d.get('last_error')})")
        if d and d.get("status") == "ok":
            continue  # posted + verified; drops out of the open list next run
        # 2. watchdog — attempts exhausted OR current ETA passed, whichever first.
        #    Each escalation moves the ETA forward, so it fires again only if the NEW ETA also slips.
        if len(st["escalations"].get(k) or []) >= MAX_ESCALATIONS:
            continue  # beyond this the daily stale-check keeps it visible (no per-15-min spam)
        eta = current_eta(t, st)
        exhausted = bool(d and d["status"] == "failed" and d["attempts"] >= MAX_ATTEMPTS
                         and not d.get("exhaust_escalated"))
        overdue = bool(eta is None or now > eta)
        if exhausted or overdue:
            reason = (f"ETA {cc.fmt_eta(eta)} passed" if eta and now > eta else
                      "no ETA on task" if eta is None else f"auto-answer failed {MAX_ATTEMPTS}x")
            escalate(t, st, now, reason, eta)
            if d and d["status"] == "failed" and d["attempts"] >= MAX_ATTEMPTS:
                d["exhaust_escalated"] = True
    save_state(st)
    if DRY:
        print(f"[dry-run] open utd-question tasks: {[t['id'] for t in tasks]}; skipped(backlog): "
              f"{[t['id'] for t in tasks if t['id'] in skip]}; dispatched this run: {n_disp}")
    return st


def stale_check(now=None):
    """Daily 9 AM CT: alert if any utd-question is open > STALE_HOURS. Silent otherwise (R-NONEWS)."""
    now = now or now_utc()
    stale = [t for t in open_questions() if now - cc.parse_ts(t["created_at"]) > timedelta(hours=STALE_HOURS)]
    if not stale:
        log("stale-check: none")
        return None
    lines = [f"• #{t['id']} open {int((now - cc.parse_ts(t['created_at'])).total_seconds() // 3600)}h — "
             f"{' '.join(t['title'].split())[:100]}" for t in stale]
    msg = (f"⚠️ {len(stale)} UTD student question(s) open > {STALE_HOURS}h — need an answer:\n" + "\n".join(lines))[:1900]
    ok = discord(msg)
    log(f"stale-check: {len(stale)} stale {[t['id'] for t in stale]}, discord ok={ok}")
    if not ok:
        sys.exit(1)   # surface in launchd/run_logged instead of failing silently
    return msg


def post_answer(triage_id, path):
    """Manual path (humans / other agents): post an answer file and mark the triage task Done."""
    t = get_task(triage_id)
    if not t:
        sys.exit(f"triage task #{triage_id} not found")
    sid = student_task_id(t)
    if not sid:
        sys.exit(f"can't find the student task for #{triage_id}")
    body = open(path).read().strip()
    if not body:
        sys.exit("empty answer")
    ok, info = post_and_verify(triage_id, sid, body)
    log(f"post-answer #{triage_id} on task #{sid}: ok={ok} {info}")
    if not ok:
        sys.exit(f"post failed: {info}")
    print(f"posted answer on task #{sid}; triage #{triage_id} Done ({info})")


def fake_task():
    created = now_utc() - timedelta(hours=6)
    eta = cc.compute_eta(created)
    return {"id": 999999, "title": "[UTD question] Test Student: how do I validate a lead? (task #99999)",
            "state": "To Do", "created_at": created.isoformat(), "due_date": eta.isoformat(),
            "tags": ["utd-question", f"eta:{eta.isoformat()}", "student-task:99999"],
            "description": "UTD capstone student Test Student asked on task #99999 (Fake):\n\n"
                           "how do I validate a lead card's contact info?\n\nETA promised ..."}


if __name__ == "__main__":
    sub = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    if sub in ("post-answer", "worker", "stale-check"):
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--triage", type=int)
        ap.add_argument("--file"); ap.add_argument("--attempt", type=int, default=1)
        ap.add_argument("--dry-run", action="store_true")
        a = ap.parse_args()
        if sub == "post-answer":
            post_answer(a.triage, a.file)
        elif sub == "worker":
            r = worker(a.triage, a.attempt)
            sys.exit(0 if r["ok"] else 2)
        else:
            stale_check()
        sys.exit(0)
    run(fake_task() if DRY and "--fake" in sys.argv else None)
