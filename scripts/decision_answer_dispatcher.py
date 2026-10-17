#!/usr/bin/env python3
"""decision_answer_dispatcher.py — every answered Decision gets executed without Jon chasing it.

Jon 2026-10-17 03:52: "Fix it so that this does not happen again. I am tired of chasing my responses."
(D-7282137 was approved at 01:24 three minutes after filing; nothing executed it until he asked at 03:51.)

Gap: dedicated handlers exist for a few card families (QB invoices, send-it cards, backlog grind,
payload waivers), but a Decision filed ad hoc by an Exo session ("Apply my recommendations" on a model
fix, a deck change, ...) had NO executor; the filing session only acted if it happened to look again.

What this does (launchd com.exos.decision-answer-dispatcher, every 120 s):
  1. Reads mission-control/data/decisions.json. Picks decisions answered by a HUMAN (not Exo/agents) since
     install, that are actionable (Apply / Approve / Yes / an option — not Hold / No / Reject / Cancel / Defer)
     and not already dispatched.
  2. Skips families with their own executor (HANDLED_SOURCES / HANDLED_DEDUPE, "Send:" cards -> send-watcher,
     note-only / Hold-with-note answers -> decision-note-router acts on the note).
  3. Wakes the session that filed it (originSession field, or the channel named in `source`, else Jon's
     #exomac-system control session) with an EXECUTE prompt: the full card + answer + note, "check first
     whether it is already done; never redo; then execute, attach outputs to the related task, post one
     short result line to Jon". Runs detached so the dispatcher never blocks.
  4. Records it in logs/decision-answer-dispatcher-state.json. If the session wake fails, retries next run
     (max 3), then DMs Jon once so nothing dies silently.
Run: python3 scripts/decision_answer_dispatcher.py [--dry-run] [--baseline] [--selftest]
"""
import json, os, re, subprocess, sys, shutil
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
STATE = os.path.join(WS, "logs", "decision-answer-dispatcher-state.json")
LOG = os.path.join(WS, "logs", "decision-answer-dispatcher.log")
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
JON_DM = "user:1501632195163590739"
CONTROL = "agent:main:discord:channel:1501636814849577050"          # #exomac-system
CHANNEL_SESSIONS = {                                                 # `source` text -> owning session
    "#exomac-system": CONTROL,
    "#rd-team": "agent:main:discord:channel:1501636614034821320",
}
# Families that already have a deterministic executor — never double-dispatch these.
HANDLED_SOURCES = ("QB Invoicing", "Exo (backlog grind)", "Payload order-to-cash", "payload-cadence",
                   "decision-send-watcher", "Weekly RSI", "Self-Improvement Implementer")
HANDLED_DEDUPE = ("payload-waiver:", "backlog-grind-", "qb-invoice", "send:", "cm-drift:")
NOTE_ONLY = re.compile(r"^\s*(📝|instruction\b)", re.I)
NON_ACTION = re.compile(r"^\s*(hold|no\b|reject|cancel|defer|not now|skip|decline)", re.I)
BOT = re.compile(r"\b(exo|exobot|agent|cron|bot|resolver|triage)\b", re.I)
DRY = "--dry-run" in sys.argv
MAX_TRIES = 3


def now():
    return datetime.now(timezone.utc).isoformat()


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{now()} {m}\n")


def fleet(action, detail, outcome):
    """exo3 telemetry → logs/fleet-events.jsonl (decision-trace: which answer woke which session)."""
    if DRY:
        return
    try:
        sys.path.insert(0, os.path.join(WS, "scripts"))
        import fleet_log
        fleet_log.event("decision-answer-dispatcher", "orchestrate", action, detail=detail, owner="John Quinn", outcome=outcome)
    except Exception:
        pass


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def decisions():
    d = load(DECISIONS, [])
    return d if isinstance(d, list) else d.get("decisions", [])


def human(d):
    by, em = (d.get("answeredBy") or "").strip(), (d.get("answeredByEmail") or "").strip().lower()
    if em.startswith("exo@"):
        return False
    return bool(by or em) and not BOT.search(by)


def handled_elsewhere(d):
    src, key = d.get("source") or "", d.get("dedupeKey") or ""
    return any(s.lower() in src.lower() for s in HANDLED_SOURCES) or any(key.startswith(k) for k in HANDLED_DEDUPE)


def target_session(d):
    if d.get("originSession"):
        return d["originSession"]
    src = d.get("source") or ""
    for tag, sk in CHANNEL_SESSIONS.items():
        if tag in src:
            return sk
    return CONTROL


def candidates(ds, st):
    out = []
    for d in ds:
        if d.get("status") != "answered" or not d.get("answeredAt"):
            continue
        if d["answeredAt"] < st.get("installed", "9999"):
            continue
        rec = st["dispatched"].get(d["id"])
        if rec and (rec.get("ok") or rec.get("tries", 0) >= MAX_TRIES) and rec.get("answeredAt") == d["answeredAt"]:
            continue                                   # done (a re-answer with a new timestamp re-dispatches)
        if not human(d) or handled_elsewhere(d):
            continue
        ans = (d.get("answer") or "").strip()
        if NON_ACTION.match(ans) or NOTE_ONLY.match(ans) or (d.get("title") or "").startswith("Send:"):
            continue   # hold/no: nothing to execute · note-only answers: decision-note-router acts on the note ·
                       # "Send:" cards: decision-send-watcher emails the draft

        out.append(d)
    return out


def prompt(d):
    return (
        f"DECISION ANSWERED — EXECUTE NOW (auto-dispatch; Jon must not have to chase this).\n"
        f"{d['id']}: {d.get('title')}\nQuestion: {d.get('question')}\n"
        f"Answer: {d.get('answer')} — by {d.get('answeredBy')} at {d.get('answeredAt')}\n"
        f"Note from Jon: {d.get('note') or '(none)'}\nProposed action on the card: {d.get('proposedAction') or '(see context)'}\n"
        f"Related task: #{d.get('relatedItem') or d.get('relatedTaskId') or '-'}\n\nContext:\n{(d.get('context') or '')[:6000]}\n\n"
        "Do this now: (1) check whether it was already executed (task notes, files, git log, sent mail); if so, "
        "do not redo it — just confirm. (2) Otherwise execute exactly what was approved (apply any override in the "
        "note). If the answer was Hold/No with a note, do what the note says. (3) Attach outputs to the related MC task "
        "with scripts/mc-attach.py and email deliverables to Jon if the card promised them. (4) Post ONE short result "
        "line to Jon in this channel: what was done, or the concrete blocker. No questions back unless truly blocked."
    )


def wake(session, text):
    if DRY:
        print("WOULD WAKE", session, text[:120].replace("\n", " ")); return True
    try:
        subprocess.Popen([OPENCLAW, "agent", "--session-key", session, "-m", text],
                         stdout=open(LOG, "a"), stderr=subprocess.STDOUT, start_new_session=True, cwd=WS)
        return True
    except Exception as e:
        log(f"wake error {session}: {e}")
        return False


def notify(text):
    if DRY:
        print("WOULD DM", text); return
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON_DM, "-m", text],
                       capture_output=True, text=True, timeout=60)
    except Exception as e:
        log(f"notify error: {e}")


def main():
    import fcntl
    lockf = open(STATE + ".lock", "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)   # one run at a time (overlapping runs double-woke D-7282131)
    except BlockingIOError:
        print("another run in progress"); return
    st = load(STATE, None)
    if st is None or "--baseline" in sys.argv:
        st = {"installed": now(), "dispatched": (st or {}).get("dispatched", {})}
        if not DRY:
            json.dump(st, open(STATE, "w"), indent=1)
        print(f"baseline set {st['installed']}"); return
    n = 0
    for d in candidates(decisions(), st):
        rec = st["dispatched"].setdefault(d["id"], {"tries": 0})
        rec.update(answeredAt=d["answeredAt"], session=target_session(d), last=now())
        rec["tries"] = rec.get("tries", 0) + 1
        ok = wake(rec["session"], prompt(d))
        rec["ok"] = ok
        log(f"{'dispatched' if ok else 'WAKE FAILED'} {d['id']} -> {rec['session']} (try {rec['tries']})")
        fleet("dispatch", {"decision": d["id"], "session": rec["session"], "try": rec["tries"],
                           "answeredAt": d["answeredAt"]}, "ok" if ok else "wake_failed")
        if not DRY:
            json.dump(st, open(STATE, "w"), indent=1)       # persist per dispatch, not just at the end
        if not ok and rec["tries"] >= MAX_TRIES:
            notify(f"⚠️ {d['id']} ({d.get('title','')[:80]}) was answered but I could not start the follow-through "
                   f"after {MAX_TRIES} tries. Exo will pick it up in #exomac-system.")
        n += 1
    if not DRY:
        json.dump(st, open(STATE, "w"), indent=1)
    print(f"dispatched {n}")


def selftest():
    global DECISIONS, STATE, LOG, DRY
    import tempfile
    t = tempfile.mkdtemp(); DECISIONS = os.path.join(t, "d.json"); STATE = os.path.join(t, "s.json"); LOG = os.path.join(t, "l")
    DRY = True
    json.dump({"installed": "2026-10-17T00:00:00Z", "dispatched": {}}, open(STATE, "w"))
    base = dict(status="answered", answeredAt="2026-10-17T06:24:00Z", answeredBy="John Quinn")
    ds = [dict(base, id="D-1", title="model fix", answer="Apply my recommendations", source="Exo (Series A model review)"),
          dict(base, id="D-2", title="invoice", answer="Approve & send", source="QB Invoicing (exo3)"),
          dict(base, id="D-3", title="hold", answer="Hold"),
          dict(base, id="D-4", title="by bot", answer="Apply", answeredBy="Exo"),
          dict(base, id="D-5", title="old", answer="Apply", answeredAt="2026-10-16T00:00:00Z"),
          dict(base, id="D-6", title="rd", answer="Yes", source="Exo (#rd-team OOSL)"),
          dict(base, id="D-7", title="hold w/ note", answer="Hold", note="change X then send"),
          dict(base, id="D-8", title="note only", answer="📝 Instruction", note="@exo do Y"),
          dict(base, id="D-9", title="opp route", answer="Approve", source="Opportunity Engine")]
    json.dump(ds, open(DECISIONS, "w"))
    got = {d["id"]: target_session(d) for d in candidates(decisions(), load(STATE, {}))}
    checks = {"model-fix card dispatched to control": got.get("D-1") == CONTROL,
              "QB card left to its own executor": "D-2" not in got,
              "pure Hold not executed": "D-3" not in got,
              "bot answers ignored": "D-4" not in got,
              "pre-install answers ignored": "D-5" not in got,
              "#rd-team card routed to #rd-team": got.get("D-6", "").endswith("1501636614034821320"),
              "Hold-with-note left to note router": "D-7" not in got,
              "note-only answer left to note router": "D-8" not in got,
              "Opportunity Engine approval dispatched": got.get("D-9") == CONTROL}
    bad = [k for k, v in checks.items() if not v]
    print(f"decision_answer_dispatcher selftest: {len(checks)-len(bad)}/{len(checks)} pass" + (f" FAIL {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
