#!/usr/bin/env python3
"""Offline tests for capstone_question_answerer.py (NO network / DB / Discord / model).
Covers: answer parsing+validation (success, truncated, BLOCKED, missing markers, too long),
worker post+verify (success only when the activity row reads back + triage Done; an
"ANSWERED" line is never trusted), retry cadence (3 attempts, 15 min apart) and the SLA
watchdog (fires on exhaustion OR ETA, whichever first; fires again if the new ETA slips; capped),
and the daily stale check (silent when none).
Run:  python3 scripts/test_capstone_question_answerer.py
"""
import os, sys, json, tempfile, uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capstone_question_answerer as qa  # noqa: E402

cc = qa.cc
TMP = tempfile.mkdtemp(prefix="cqa-test-")
qa.STATE = os.path.join(TMP, "state.json")
qa.LOG = os.path.join(TMP, "log.txt")
qa.RUNLOG_DIR = os.path.join(TMP, "runs")
qa.BACKLOG = []

FAILS = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


# ── fake Supabase / Discord / spawn ─────────────────────────────────────────
class DB:
    def __init__(self):
        self.tasks, self.acts, self.drop_insert = {}, {}, False

    def supa(self, method, path, body=None):
        tbl, _, q = path.partition("?")
        if tbl == "tasks":
            if method == "GET":
                if "id=eq." in q:
                    i = int(q.split("id=eq.")[1].split("&")[0])
                    return [dict(self.tasks[i])] if i in self.tasks else []
                return [dict(t) for t in self.tasks.values() if t["state"] not in ("Done", "Cancelled")
                        and "utd-question" in t["tags"]]
            if method == "PATCH":
                i = int(q.split("id=eq.")[1])
                self.tasks[i].update(body)
                return [self.tasks[i]]
        if tbl == "activities":
            if method == "POST":
                aid = str(uuid.uuid4())
                if not self.drop_insert:
                    self.acts[aid] = dict(body, id=aid)
                return [dict(body, id=aid)]
            if method == "GET":
                aid = q.split("id=eq.")[1].split("&")[0]
                return [self.acts[aid]] if aid in self.acts else []
        raise AssertionError(f"unexpected supa {method} {path}")


db = DB()
cc.supa = db.supa
SENT, SPAWNED = [], []
qa.discord = lambda text: SENT.append(text) or True
qa.spawn_worker = lambda tid, attempt: SPAWNED.append((tid, attempt))


def notes(sid):
    return [a for a in db.acts.values() if a["subject"] == f"task:{sid}"]


def mk_task(i, sid, eta, created=None):
    db.tasks[i] = {"id": i, "title": f"[UTD question] Test: q{i} (task #{sid})", "state": "To Do",
                   "description": "", "due_date": eta.isoformat(),
                   "created_at": (created or eta - timedelta(hours=4)).isoformat(),
                   "tags": ["utd-question", f"eta:{eta.isoformat()}", f"student-task:{sid}"]}
    return db.tasks[i]


def agent_json(text, finish="stop"):
    return json.dumps({"status": "ok", "result": {"payloads": [{"text": text}], "meta": {
        "finalAssistantVisibleText": text, "terminalReply": {"text": text},
        "completion": {"finishReason": finish}}}})


# ── 1. parsing / validation ─────────────────────────────────────────────────
good = "<<<ANSWER>>>\nUse the PUG section 3 ([source](https://exosaero.com)). Lizi will confirm scope.\n<<<END>>>"
a, e = qa.parse_agent_output(agent_json(good))
check("parse: success extracts answer", e is None and a.startswith("Use the PUG"))
a, e = qa.parse_agent_output(good)
check("parse: plain-text output also works", e is None and a)
a, e = qa.parse_agent_output(agent_json("<<<ANSWER>>>\nLong answer that got cut", finish="length"))
check("parse: truncated (finishReason=length) rejected", a is None and "truncated" in e)
a, e = qa.parse_agent_output(agent_json("I need to draft... Let me first create the answer file:\n"
                                        "⚠️ Reply truncated at the model's output token limit. The text above is partial."))
check("parse: truncation banner (3363 a2) rejected", a is None and "truncated" in e)
a, e = qa.parse_agent_output(agent_json("<<<ANSWER>>>\npartial answer with no end marker"))
check("parse: missing END marker rejected", a is None and "END" in e)
a, e = qa.parse_agent_output(agent_json("BLOCKED #3361: Terminal and file_write tools unavailable"))
check("parse: BLOCKED rejected", a is None and "BLOCKED" in e)
a, e = qa.parse_agent_output(agent_json("Here is my review...\n\nANSWERED #3360"))
check("parse: bare 'ANSWERED' with no markers rejected (3360)", a is None and "marker" in e)
a, e = qa.parse_agent_output(agent_json("<<<ANSWER>>>   <<<END>>>"))
check("parse: empty answer rejected", a is None and "empty" in e)
a, e = qa.parse_agent_output(agent_json("<<<ANSWER>>>" + "word " * 600 + "<<<END>>>"))
check("parse: >450 words rejected", a is None and "too long" in e)
a, e = qa.parse_agent_output("", rc=1)
check("parse: nonzero rc rejected", a is None and "rc=1" in e)
a, e = qa.parse_agent_output(json.dumps({"status": "error", "summary": "model failed"}))
check("parse: agent status=error rejected", a is None and "status=error" in e)

# ── 2. worker: post + verify ────────────────────────────────────────────────
now = datetime.now(timezone.utc)
t = mk_task(501, 9501, now + timedelta(hours=2))
r = qa.worker(501, 1, fake_raw=agent_json(good))
check("worker: success posts note on student task", r["ok"] and len(notes(9501)) == 1
      and notes(9501)[0]["body"].startswith("💬 Exo: Use the PUG"))
check("worker: success marks triage Done", db.tasks[501]["state"] == "Done")
check("worker: result file written", os.path.exists(qa.result_path(501, 1)))

t = mk_task(502, 9502, now + timedelta(hours=2))
r = qa.worker(502, 1, fake_raw=agent_json("Here is the answer.\nANSWERED #502"))
check("worker: 'ANSWERED' w/o markers = failure, nothing posted, still open",
      not r["ok"] and not notes(9502) and db.tasks[502]["state"] == "To Do")

t = mk_task(503, 9503, now + timedelta(hours=2))
db.drop_insert = True
r = qa.worker(503, 1, fake_raw=agent_json(good))
db.drop_insert = False
check("worker: insert not readable back = failure, triage NOT marked Done",
      not r["ok"] and db.tasks[503]["state"] == "To Do" and "not found" in r["error"])

# ── 3. retries + watchdog (exhaustion first) ────────────────────────────────
for p in (qa.STATE,):
    if os.path.exists(p):
        os.remove(p)
db.tasks.clear(); db.acts.clear(); SENT.clear(); SPAWNED.clear()
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc)   # Mon 10:00 CDT
mk_task(601, 9601, T0 + timedelta(hours=4), created=T0)  # ETA 14:00 CDT


def fail_result(tid, attempt, at):
    os.makedirs(qa.RUNLOG_DIR, exist_ok=True)
    json.dump({"ok": False, "error": "agent BLOCKED: test", "finished": at.isoformat()},
              open(qa.result_path(tid, attempt), "w"))


qa.run(now=T0)
check("run: dispatch attempt 1", SPAWNED == [(601, 1)])
fail_result(601, 1, T0 + timedelta(minutes=5))
qa.run(now=T0 + timedelta(minutes=15))
check("run: no retry < 15 min after failure", SPAWNED == [(601, 1)])
qa.run(now=T0 + timedelta(minutes=20))
check("run: retry attempt 2 ≥15 min after failure", SPAWNED[-1] == (601, 2))
fail_result(601, 2, T0 + timedelta(minutes=25))
qa.run(now=T0 + timedelta(minutes=40))
check("run: retry attempt 3", SPAWNED[-1] == (601, 3))
fail_result(601, 3, T0 + timedelta(minutes=45))
check("watchdog: nothing sent before exhaustion/ETA", not SENT and not notes(9601))
qa.run(now=T0 + timedelta(minutes=55))
check("run: no 4th attempt", SPAWNED[-1] == (601, 3) and len(SPAWNED) == 3)
check("watchdog: fires on exhaustion BEFORE ETA (1 Discord + 1 student note)",
      len(SENT) == 1 and len(notes(9601)) == 1 and "#601" in SENT[0] and "3/3" in SENT[0])
eta_tag = qa.tag(db.tasks[601], "eta:")
check("watchdog: new ETA written to eta: tag and due_date",
      eta_tag == db.tasks[601]["due_date"] and qa.cc.parse_ts(eta_tag) > T0 + timedelta(minutes=55))
qa.run(now=T0 + timedelta(minutes=70))
qa.run(now=T0 + timedelta(hours=3))
check("watchdog: no repeat while new ETA still ahead", len(SENT) == 1 and len(notes(9601)) == 1)
qa.run(now=qa.cc.parse_ts(eta_tag) + timedelta(minutes=1))
check("watchdog: fires AGAIN when the new ETA slips (old bug: latched forever)",
      len(SENT) == 2 and len(notes(9601)) == 2 and "passed" in SENT[1])
qa.run(now=qa.cc.parse_ts(qa.tag(db.tasks[601], "eta:")) + timedelta(hours=1))
check("watchdog: capped at MAX_ESCALATIONS (stale-check takes over)", len(SENT) == 2 and len(notes(9601)) == 2)

# ── 4. watchdog: ETA first (worker still running) ───────────────────────────
db.tasks.clear(); db.acts.clear(); SENT.clear(); SPAWNED.clear(); os.remove(qa.STATE)
mk_task(701, 9701, T0 + timedelta(hours=1), created=T0)
qa.run(now=T0)
qa.run(now=T0 + timedelta(hours=1, minutes=1))
check("watchdog: fires when ETA passes even with attempt still running",
      len(SENT) == 1 and len(notes(9701)) == 1 and "passed" in SENT[0])
st = json.load(open(qa.STATE))
check("watchdog: escalation recorded in state", len(st["escalations"]["701"]) == 1)

# ── 5. backlog skip ─────────────────────────────────────────────────────────
db.tasks.clear(); db.acts.clear(); SENT.clear(); SPAWNED.clear(); os.remove(qa.STATE)
qa.BACKLOG = [801]
mk_task(801, 9801, T0 - timedelta(hours=10), created=T0 - timedelta(hours=14))
qa.run(now=T0)
check("backlog: skipped task never dispatched/escalated", not SPAWNED and not SENT)
qa.BACKLOG = []

# ── 6. daily stale check ────────────────────────────────────────────────────
db.tasks.clear(); SENT.clear()
mk_task(901, 9901, T0 + timedelta(hours=4), created=T0 - timedelta(hours=2))
check("stale-check: silent when nothing > 8h", qa.stale_check(now=T0) is None and not SENT)
mk_task(902, 9902, T0, created=T0 - timedelta(hours=9))
msg = qa.stale_check(now=T0)
check("stale-check: alerts on > 8h, lists only stale ones",
      len(SENT) == 1 and "#902" in SENT[0] and "#901" not in SENT[0])

print(f"\n{len(FAILS)} failure(s)" + (": " + ", ".join(FAILS) if FAILS else ""))
sys.exit(1 if FAILS else 0)
