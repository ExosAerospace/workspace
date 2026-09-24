#!/usr/bin/env python3
"""
task_ledger.py — thin, durable task ledger for traceability/error-tracking.

Reuses launchd for execution (no new runner layer). Two uses:
  1) WRAP a job so each run is recorded with exit code, duration, and output tail:
       task_ledger.py run --name "Email->MC Tracker" --source launchd -- python3 foo.py --x
     Runs the command, appends one event to logs/task-ledger.jsonl, and EXITS WITH THE
     COMMAND'S OWN EXIT CODE (so launchd still sees real success/failure).
  2) LOG a one-off / inline task result manually:
       task_ledger.py log --name "Build X" --source inline --status ok --note "done"

The Mission Control Jobs panel reads logs/task-ledger.jsonl + live `launchctl list`.
Append-only; never deletes.
"""
import json, os, sys, time, subprocess, argparse
from datetime import datetime, timezone

LEDGER = "/Users/exomac/.openclaw/workspace/logs/task-ledger.jsonl"


def _emit_govlog(rec):
    """Unify the two telemetry layers: mirror every ledger entry into the govlog
    correlation-ID substrate (governance/events.jsonl), so the ~12 launchd jobs
    wrapped by this ledger become visible to the same fleet view and evals as the
    govlog-native agents. Additive: the task-ledger.jsonl (MC Jobs panel) is
    untouched. Soft by construction: never breaks the wrapped job."""
    try:
        import re as _re
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "governance"))
        import govlog
        name = rec.get("name") or "job"
        agent = _re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:40] or "job"
        run = govlog.new_run(agent)
        status = rec.get("status") or "info"
        detail = str(name)[:120]
        # Reclassify a transient network/service blip (mail Bridge down, DNS, 5xx) as a
        # benign skip so the completion watchdog stays quiet; surface the real reason too.
        if status == "error" and govlog.is_transient(rec.get("output_tail") or ""):
            status = "transient"
            detail = f"{name}: transient net/mail blip — {(rec.get('output_tail') or '').strip().splitlines()[-1][:80] if (rec.get('output_tail') or '').strip() else 'unreachable'}"
        govlog.event(run, "run", status=status,
                     detail=detail[:160], exit_code=rec.get("exit_code"),
                     duration_s=rec.get("duration_s"), source=rec.get("source"))
    except Exception:
        pass


def append(rec):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    rec.setdefault("ts", datetime.now(timezone.utc).isoformat())
    with open(LEDGER, "a") as f:
        f.write(json.dumps(rec) + "\n")
    _emit_govlog(rec)


def cmd_run(a):
    cmd = a.cmd
    if not cmd:
        print("no command given after --", file=sys.stderr); return 2
    start = time.time()
    started = datetime.now(timezone.utc).isoformat()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True)
        rc = p.returncode
        out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr else "")
    except Exception as e:
        rc = 1
        out = f"launch error: {e}"
    dur = round(time.time() - start, 1)
    tail = "\n".join(out.strip().splitlines()[-12:])
    append({
        "name": a.name, "source": a.source, "started": started,
        "finished": datetime.now(timezone.utc).isoformat(), "duration_s": dur,
        "status": "ok" if rc == 0 else "error", "exit_code": rc,
        "output_tail": tail[:2000],
    })
    # passthrough output + exit code so launchd/console behaviour is unchanged
    if out:
        sys.stdout.write(out)
    return rc


def cmd_snapshot(a):
    """Capture launchd com.exos.* job health from the USER domain to a file the
    daemon-run server can read (the server's own domain can't see user agents)."""
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=15).stdout
    except Exception:
        out = ""
    jobs = []
    for line in out.splitlines():
        if "com.exos." not in line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        pid, last, label = parts[0], parts[1], parts[2]
        jobs.append({"label": label, "pid": None if pid == "-" else pid, "last_exit": last,
                     "running": pid not in ("-", "0"),
                     "status": "ok" if last in ("-", "0") else "error"})
    jobs.sort(key=lambda j: j["label"])
    p = "/Users/exomac/.openclaw/workspace/logs/launchd-snapshot.json"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump({"generated": datetime.now(timezone.utc).isoformat(), "jobs": jobs}, f, indent=2)
    print(f"snapshot: {len(jobs)} com.exos jobs")
    return 0


def cmd_log(a):
    append({
        "name": a.name, "source": a.source, "status": a.status,
        "exit_code": a.exit, "note": a.note or "", "duration_s": a.duration,
        "finished": datetime.now(timezone.utc).isoformat(),
    })
    print(f"logged: {a.name} [{a.status}]")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("run")
    r.add_argument("--name", required=True)
    r.add_argument("--source", default="launchd")
    r.add_argument("cmd", nargs=argparse.REMAINDER)
    sub.add_parser("snapshot")
    l = sub.add_parser("log")
    l.add_argument("--name", required=True)
    l.add_argument("--source", default="inline")
    l.add_argument("--status", default="ok")
    l.add_argument("--exit", type=int, default=0)
    l.add_argument("--duration", type=float, default=None)
    l.add_argument("--note", default="")
    a = ap.parse_args()
    if a.mode == "run":
        # strip a leading "--" left in REMAINDER
        if a.cmd and a.cmd[0] == "--":
            a.cmd = a.cmd[1:]
        sys.exit(cmd_run(a))
    elif a.mode == "snapshot":
        sys.exit(cmd_snapshot(a))
    else:
        sys.exit(cmd_log(a))


if __name__ == "__main__":
    main()
