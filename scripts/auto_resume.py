#!/usr/bin/env python3
"""auto_resume.py — self-accountability for work Exo starts.

The gap it closes (Jon 2026-09-24): a delegated/background build can die silently on session
rotation, leaving zero progress and no resume — the user ends up babysitting. The completion-watchdog
DETECTS stalls but does not RESUME them.

This is a MODEL-FREE checker (launchd com.exos.auto-resume, ~15 min). It reads a durable commitment
ledger; for each open commitment it runs a machine-checkable DONE test (shell/git). If done → posts ✅
to the requester channel and closes it. If not done and past the cooldown → it RE-DRIVES the work by
waking a full-tool session (`openclaw agent --session-key ...`) with the self-contained resume prompt,
incrementing attempts. After max attempts it marks the item STUCK and pings the channel ONCE so a real
failure is never silent. The checker never calls a model itself, so it can't fail the way the work can.

Ledger: governance/commitments.json
CLI:
  register --id ID --title T --check 'SHELL' --resume 'PROMPT' [--session KEY] [--channel ID] [--max N] [--cooldown MIN]
  done ID | reopen ID | list | run   (run = the launchd loop)
"""
import json, os, sys, subprocess, shutil, time, argparse
from datetime import datetime, timezone
# ExO3 Pillar 2 — correlation-ID logging (govlog). Safe-optional; never breaks the checker.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "governance"))
    import govlog
except Exception:
    govlog = None

WS = "/Users/exomac/.openclaw/workspace"
LEDGER = os.path.join(WS, "governance", "commitments.json")
LOG = os.path.join(WS, "logs", "auto-resume.log")
LOCK = os.path.join(WS, "logs", "auto-resume.lock")
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
DEFAULT_CHANNEL = "channel:1501636614034821320"   # #rd-team (requester)
DEFAULT_SESSION = "agent:auto-resume"             # dedicated full-tool session for re-drives
DEFAULT_MAX = 3
DEFAULT_COOLDOWN_MIN = 20
CHECK_TIMEOUT = 90
WAKE_TIMEOUT = 1500  # 25 min: a single re-drive does the next uncommitted stage, then the loop re-checks


def now():
    return datetime.now(timezone.utc).isoformat()


def log(m):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        open(LOG, "a").write(f"{now()} {m}\n")
    except Exception:
        pass


def load():
    try:
        return json.load(open(LEDGER))
    except Exception:
        return {"commitments": []}


def save(d):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(d, open(LEDGER, "w"), indent=1)


def notify(channel, text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", channel, "-m", text],
                       capture_output=True, text=True, timeout=60)
    except Exception as e:
        log(f"notify fail: {e}")


def run_check(cmd):
    try:
        r = subprocess.run(cmd, shell=True, cwd=WS, capture_output=True, text=True, timeout=CHECK_TIMEOUT)
        return r.returncode == 0
    except Exception as e:
        log(f"check error [{cmd[:60]}]: {e}")
        return False


def wake(session, prompt):
    try:
        r = subprocess.run([OPENCLAW, "agent", "--session-key", session, "-m", prompt],
                           capture_output=True, text=True, timeout=WAKE_TIMEOUT)
        if r.returncode != 0:
            log(f"wake rc={r.returncode}: {(r.stderr or r.stdout)[:200]}")
        return r.returncode == 0
    except Exception as e:
        log(f"wake error: {e}")
        return False


def cmd_register(a):
    d = load()
    d["commitments"] = [c for c in d.get("commitments", []) if c["id"] != a.id]
    d["commitments"].append({
        "id": a.id, "title": a.title, "check": a.check, "resume": a.resume,
        "session": a.session or DEFAULT_SESSION, "channel": a.channel or DEFAULT_CHANNEL,
        "max_attempts": a.max or DEFAULT_MAX, "cooldown_min": a.cooldown or DEFAULT_COOLDOWN_MIN,
        "attempts": 0, "status": "open", "created": now(), "last_attempt": 0, "last_check": None,
    })
    save(d)
    print(f"registered commitment {a.id}: {a.title}")


def cmd_mark(a, status):
    d = load()
    for c in d.get("commitments", []):
        if c["id"] == a.id:
            c["status"] = status
            if status == "open":
                c["attempts"] = 0
    save(d)
    print(f"{a.id} -> {status}")


def cmd_list(a):
    d = load()
    for c in d.get("commitments", []):
        print(f"[{c['status']:6}] {c['id']} att {c['attempts']}/{c['max_attempts']} — {c['title']}")


def cmd_run(a):
    # simple lock so overlapping launchd runs don't double-wake
    try:
        if os.path.exists(LOCK) and (time.time() - os.path.getmtime(LOCK)) < WAKE_TIMEOUT:
            print("locked; another run active"); return
        open(LOCK, "w").write(now())
    except Exception:
        pass
    d = load()
    changed = False
    grun = govlog.new_run("auto-resume-exo3") if govlog else None
    if grun: govlog.event(grun, "start", open_count=sum(1 for c in d.get("commitments", []) if c["status"] == "open"))
    for c in d.get("commitments", []):
        if c["status"] != "open":
            continue
        c["last_check"] = now()
        if run_check(c["check"]):
            c["status"] = "done"; changed = True
            notify(c["channel"], f"✅ Auto-resume: **{c['title']}** is complete (verified). Closing it out.")
            log(f"DONE {c['id']}")
            if grun: govlog.event(grun, "commitment_done", detail=c["id"], outcome="done")
            continue
        if c["attempts"] >= c["max_attempts"]:
            if c["status"] != "stuck":
                c["status"] = "stuck"; changed = True
                notify(c["channel"], f"⚠️ Auto-resume: **{c['title']}** is STUCK after {c['attempts']} attempts — needs a human. (id {c['id']})")
                log(f"STUCK {c['id']}")
                if grun: govlog.event(grun, "commitment_stuck", status="error", detail=c["id"])
            continue
        if (time.time() - (c.get("last_attempt") or 0)) < c["cooldown_min"] * 60:
            continue
        c["attempts"] += 1; c["last_attempt"] = time.time(); changed = True
        log(f"RESUME {c['id']} attempt {c['attempts']}/{c['max_attempts']}")
        ok = wake(c["session"], c["resume"])
        if grun: govlog.event(grun, "commitment_resume", detail=c["id"], attempt=c["attempts"],
                              status="ok" if ok else "error",
                              note="" if ok else "wake failed (often claude-cli auth expiry overnight — no headless renew)")
        save(d)  # persist attempt count before the long wake completes cycle
    if changed:
        save(d)
    if grun:
        opn = sum(1 for c in d.get("commitments", []) if c["status"] == "open")
        govlog.event(grun, "end", status="ok", open_remaining=opn)
    try:
        os.remove(LOCK)
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register"); r.add_argument("--id", required=True); r.add_argument("--title", required=True)
    r.add_argument("--check", required=True); r.add_argument("--resume", required=True)
    r.add_argument("--session"); r.add_argument("--channel"); r.add_argument("--max", type=int); r.add_argument("--cooldown", type=int)
    r.set_defaults(fn=cmd_register)
    for nm in ("done", "reopen"):
        s = sub.add_parser(nm); s.add_argument("id"); s.set_defaults(fn=(lambda a, st=("done" if nm == "done" else "open"): cmd_mark(a, st)))
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
