#!/usr/bin/env python3
"""
capstone_question_answerer.py — makes sure every UTD capstone student question gets answered.

capstone_capture.py turns a student question into an Exo triage task tagged utd-question
(+ eta:<ISO>, student-task:<id>) and acks the student with a concrete ETA. This job
(launchd com.exos.capstone-question-answerer, every 15 min):

  1. DISPATCH: each open utd-question task not yet dispatched → one detached
     `openclaw agent --session-key agent:main:utd-question-<id> --message-file <tmp> --timeout 900`
     run with the note, task, program-safety rules and the SOURCING GUARDRAIL. The agent posts
     its answer with `capstone_question_answerer.py post-answer` (same activity insert as
     capstone_capture.reply()) which also marks the triage task Done.
     Retried once if the task is still open 2h after dispatch.
  2. SLA WATCHDOG: open past its ETA → one student note "Still working on this. New ETA: …"
     (ETA + 4h, same overnight rule) + one Discord alert to #1539382179120021616. Never repeated.

State: logs/capstone-question-answerer-state.json (dispatched / sla / skip). Deterministic;
the only LLM step is the dispatched agent turn.

  capstone_question_answerer.py                    # normal run
  capstone_question_answerer.py --dry-run [--fake] # no dispatch, no writes, no state change
  capstone_question_answerer.py post-answer --triage <id> --file <answer.txt>
"""
import os, sys, json, subprocess, tempfile, argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone_capture as cc  # noqa: E402  (shares supa/reply/ETA helpers)

WS = cc.WS
STATE = os.path.join(WS, "logs/capstone-question-answerer-state.json")
LOG = os.path.join(WS, "logs/capstone-question-answerer.log")
RUNLOG_DIR = os.path.join(WS, "logs/capstone-question-agent")
DISCORD_CHANNEL = "1539382179120021616"
RETRY_AFTER = timedelta(hours=2)
MAX_DISPATCH_PER_RUN = 3
OPEN_STATES = "(Done,Cancelled)"
SELF = os.path.abspath(__file__)
# Backlog being answered by another agent (2026-10-01) — never auto-dispatch / SLA-alert these.
BACKLOG = [3204, 3221, 3230, 3235, 3285, 3292, 3293, 3294, 3295, 3299, 3300]

DRY = "--dry-run" in sys.argv
cc.DRY = DRY


def log(m):
    line = f"[{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}] {m}"
    if DRY:
        print(line)
        return
    with open(LOG, "a") as f:
        f.write(line + "\n")


def load_state():
    st = {"dispatched": {}, "sla": {}, "skip": list(BACKLOG)}
    if os.path.exists(STATE):
        st.update(json.load(open(STATE)))
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
    import re
    m = re.search(r"\(task #(\d+)\)", t.get("title") or "")
    return int(m.group(1)) if m else None


def open_questions():
    return cc.supa("GET", "tasks?select=id,title,state,description,due_date,tags,created_at"
                          f"&tags=cs.%7Butd-question%7D&state=not.in.{OPEN_STATES}&order=id")


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
    return f"""UTD CAPSTONE STUDENT QUESTION — answer it now. Triage task #{t['id']}.

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
1. Answer the student's question as Exo, on their task #{sid}. Be direct, short, useful.
2. PROGRAM-SAFE ONLY: the student is a sandboxed UTD early_adopter under NDA. Public / program
   information only. NO pricing, customers, financials, CUI/ITAR/export-controlled data, or any
   internal data. Questions about assignments, priorities, grading or scope → say Lizi will
   confirm, and route it to Lizi (mention "Lizi" in the answer).
3. SOURCING GUARDRAIL: make NO factual statement without a credible, current source
   (primary/official, dated 2023 or later), linked inline next to the claim. If you cannot find
   one, say plainly that it could not be verified. Treat these Exos claims as UNVERIFIED unless
   you find a current primary source: "only one selling payload slots", "2-3 day turnaround",
   "fastest recover-and-refly", "Flight 1 booked". Do not repeat them as fact.
4. POST the answer (this is the same Supabase activity insert capstone_capture.reply() uses,
   and it also marks triage task #{t['id']} Done). Write the answer text to a file, then run:
     python3 {SELF} post-answer --triage {t['id']} --file <answer_file>
   Do not post any other way, do not email anyone, do not post to Discord.
5. Reply with one line: ANSWERED #{t['id']} (or BLOCKED #{t['id']}: <reason> if you truly could not
   answer — in that case do NOT run post-answer).
"""


def dispatch(t, attempt):
    msg = build_message(t)
    cmd_base = ["openclaw", "agent", "--session-key", f"agent:main:utd-question-{t['id']}",
                "--timeout", "900"]
    if DRY:
        print(f"[dry-run] would dispatch #{t['id']} attempt {attempt}: {' '.join(cmd_base)} --message-file <tmp>")
        print("[dry-run] message:\n" + msg)
        return
    os.makedirs(RUNLOG_DIR, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix=f"utdq-{t['id']}-", suffix=".md", dir=RUNLOG_DIR)
    with os.fdopen(fd, "w") as f:
        f.write(msg)
    out = open(os.path.join(RUNLOG_DIR, f"{t['id']}-attempt{attempt}.log"), "a")
    # detached: an agent turn can take up to 15 min; don't block the 15-min launchd cadence
    subprocess.Popen(cmd_base + ["--message-file", path], stdout=out, stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True, cwd=WS)


def discord(text):
    cmd = ["openclaw", "message", "send", "--channel", "discord", "--target", f"channel:{DISCORD_CHANNEL}",
           "-m", text]
    if DRY:
        print("[dry-run] " + " ".join(cmd[:-2]) + f" -m {text!r}")
        return True
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        log(f"discord send failed rc={p.returncode}: {(p.stderr or p.stdout)[-300:]}")
    return p.returncode == 0


def run(fake=None):
    st = load_state()
    now = datetime.now(timezone.utc)
    tasks = open_questions()
    if fake:
        tasks.append(fake)
    skip = set(st["skip"])
    n_disp = 0
    for t in tasks:
        k = str(t["id"])
        if t["id"] in skip:
            continue
        # 1. dispatch / retry once
        d = st["dispatched"].get(k)
        if d is None and n_disp < MAX_DISPATCH_PER_RUN:
            dispatch(t, 1)
            st["dispatched"][k] = {"at": now.isoformat(), "attempts": 1}
            n_disp += 1
            log(f"dispatched #{k}")
        elif d and d["attempts"] < 2 and now - cc.parse_ts(d["at"]) >= RETRY_AFTER and n_disp < MAX_DISPATCH_PER_RUN:
            dispatch(t, 2)
            d.update({"at": now.isoformat(), "attempts": 2})
            n_disp += 1
            log(f"retried #{k} (still open 2h after dispatch)")
        # 2. SLA watchdog (once per task)
        eta_s = tag(t, "eta:")
        if not eta_s or k in st["sla"]:
            continue
        eta = cc.parse_ts(eta_s)
        if now <= eta:
            continue
        new_eta = cc.compute_eta(max(eta, now))  # ETA+4h (never already in the past)
        sid = student_task_id(t)
        if sid:
            cc.reply(sid, f"⏳ Exo: Still working on this. New ETA: {cc.fmt_eta(new_eta)} (ref #{k}).")
        cc.supa("PATCH", f"tasks?id=eq.{t['id']}", {"due_date": new_eta.isoformat()})
        ok = discord(f"⏰ UTD question SLA missed: triage task #{k} \"{t['title'][:120]}\" was due "
                     f"{cc.fmt_eta(eta)} and is still open. Student told new ETA {cc.fmt_eta(new_eta)}.")
        st["sla"][k] = {"at": now.isoformat(), "old_eta": eta_s, "new_eta": new_eta.isoformat(), "discord_ok": ok}
        log(f"SLA slip #{k}: student notified, new ETA {new_eta.isoformat()}, discord ok={ok}")
    save_state(st)
    if DRY:
        print(f"[dry-run] open utd-question tasks: {[t['id'] for t in tasks]}; skipped(backlog): "
              f"{[t['id'] for t in tasks if t['id'] in skip]}; dispatched this run: {n_disp}")


def post_answer(triage_id, path):
    t = cc.supa("GET", f"tasks?select=id,title,state,tags&id=eq.{triage_id}")
    if not t:
        sys.exit(f"triage task #{triage_id} not found")
    t = t[0]
    sid = student_task_id(t)
    if not sid:
        sys.exit(f"can't find the student task for #{triage_id}")
    body = open(path).read().strip()
    if not body:
        sys.exit("empty answer")
    cc.reply(sid, body if body.startswith("Exo") or body.startswith("💬") else f"💬 Exo: {body}")
    cc.supa("PATCH", f"tasks?id=eq.{triage_id}", {"state": "Done", "completed_at": datetime.now(timezone.utc).isoformat()})
    log(f"answered #{triage_id} on task #{sid}; triage marked Done")
    print(f"posted answer on task #{sid}; triage #{triage_id} Done")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "post-answer":
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd"); ap.add_argument("--triage", type=int, required=True)
        ap.add_argument("--file", required=True); ap.add_argument("--dry-run", action="store_true")
        a = ap.parse_args()
        post_answer(a.triage, a.file)
        sys.exit(0)
    fake = None
    if DRY and "--fake" in sys.argv:
        created = datetime.now(timezone.utc) - timedelta(hours=6)
        eta = cc.compute_eta(created)
        fake = {"id": 999999, "title": "[UTD question] Test Student: how do I validate a lead? (task #99999)",
                "state": "To Do", "created_at": created.isoformat(), "due_date": eta.isoformat(),
                "tags": ["utd-question", f"eta:{eta.isoformat()}", "student-task:99999"],
                "description": "UTD capstone student Test Student asked on task #99999 (Fake):\n\n"
                               "how do I validate a lead card's contact info?\n\nETA promised ..."}
    run(fake)
