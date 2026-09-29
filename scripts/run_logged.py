#!/usr/bin/python3
"""
run_logged.py: shared run logger for the com.exos.* launchd background jobs (exo3 audit remedy).

Usage:  /usr/bin/python3 run_logged.py <job-label> -- <original command ...>

Runs the original command exactly as launchd would have (same argv, env, cwd, stdin, stdout),
tees its stderr through unchanged, and appends ONE JSON line per run to
  <workspace>/logs/runs/YYYY-MM-DD.jsonl
with label, start/end, duration, exit code (or signal) and the last ~50 lines of stderr.

Guarantees:
  - the wrapped command's exit status is passed through unchanged (a signal death is
    re-raised on this process so launchd sees the same signal);
  - env and cwd are not touched;
  - a logging failure never changes the job's outcome (logging errors are swallowed);
  - SIGTERM/SIGINT/SIGHUP/SIGQUIT sent to the wrapper (e.g. launchctl stop / bootout) are
    forwarded to the job.
Python 3.9 compatible (runs under /usr/bin/python3 so it doesn't depend on mise/PATH).
"""
import collections
import datetime
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.environ.get("RUN_LOGGED_DIR_OVERRIDE") or os.path.join(WORKSPACE, "logs", "runs")  # override = tests only
TAIL_LINES = 50
TAIL_BYTES = 64 * 1024        # keep at most this much raw stderr in memory
LINE_MAX = 1000               # clip absurdly long single lines in the log record
DRAIN_GRACE_S = 2.0           # after the job exits, how long to wait for stderr EOF
FORWARD_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)


def _now():
    return datetime.datetime.now().astimezone()


def _append_record(rec):
    try:
        os.makedirs(RUNS_DIR, exist_ok=True)
        path = os.path.join(RUNS_DIR, rec["start"][:10] + ".jsonl")
        line = json.dumps(rec, ensure_ascii=False) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass  # never let logging break the job


def _tail(buf):
    text = bytes(buf).decode("utf-8", errors="replace")
    lines = text.splitlines()[-TAIL_LINES:]
    return [l if len(l) <= LINE_MAX else l[:LINE_MAX] + "...[clipped]" for l in lines]


def _pump(pipe_fd, buf, counter):
    """Copy the job's stderr to our stderr as it arrives; keep a bounded tail."""
    while True:
        try:
            chunk = os.read(pipe_fd, 8192)
        except OSError:
            break
        if not chunk:
            break
        counter[0] += len(chunk)
        try:
            os.write(2, chunk)
        except OSError:
            pass  # our stderr went away; keep draining so the job never blocks
        buf.extend(chunk)
        if len(buf) > TAIL_BYTES:
            del buf[: len(buf) - TAIL_BYTES]


def main(argv):
    if len(argv) >= 2 and argv[1] != "--":
        label, rest = argv[1], argv[2:]
    else:
        sys.stderr.write("usage: run_logged.py <label> -- <command ...>\n")
        return 2
    cmd = rest[1:] if rest[:1] == ["--"] else rest
    if not cmd:
        sys.stderr.write("run_logged.py: no command given\n")
        return 2

    start = _now()
    t0 = time.monotonic()
    rec = {
        "label": label,
        "start": start.isoformat(timespec="seconds"),
        "host": socket.gethostname().split(".")[0],
        "launchd": os.environ.get("XPC_SERVICE_NAME", ""),
        "cmd": " ".join(cmd)[:500],
    }

    buf = bytearray()
    counter = [0]
    try:
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, close_fds=True)
    except OSError as e:
        code = 126 if isinstance(e, PermissionError) else 127
        msg = "run_logged.py: cannot execute %s: %s" % (cmd[0], e)
        try:
            sys.stderr.write(msg + "\n")
        except Exception:
            pass
        end = _now()
        rec.update(end=end.isoformat(timespec="seconds"),
                   duration_s=round(time.monotonic() - t0, 3), exit_code=code,
                   signal=None, ok=False, pid=None, stderr_bytes=0, stderr_tail=[msg])
        _append_record(rec)
        return code

    def _forward(signum, _frame):
        try:
            proc.send_signal(signum)
        except Exception:
            pass

    for s in FORWARD_SIGNALS:
        try:
            signal.signal(s, _forward)
        except Exception:
            pass

    pump = threading.Thread(target=_pump, args=(proc.stderr.fileno(), buf, counter), daemon=True)
    pump.start()
    while True:
        try:
            rc = proc.wait()
            break
        except InterruptedError:
            continue
    # A backgrounded grandchild may hold stderr open; don't let it keep the job "running".
    pump.join(DRAIN_GRACE_S)

    end = _now()
    sig = -rc if rc < 0 else None
    rec.update(
        end=end.isoformat(timespec="seconds"),
        duration_s=round(time.monotonic() - t0, 3),
        exit_code=(128 + sig) if sig else rc,
        signal=(signal.Signals(sig).name if sig else None),
        ok=(rc == 0),
        pid=proc.pid,
        stderr_bytes=counter[0],
        stderr_tail=_tail(buf),
    )
    _append_record(rec)

    if sig:
        # Die the same way the job did so launchd sees an identical termination status.
        for s in FORWARD_SIGNALS:
            try:
                signal.signal(s, signal.SIG_DFL)
            except Exception:
                pass
        try:
            signal.signal(sig, signal.SIG_DFL)
            os.kill(os.getpid(), sig)
            time.sleep(1)
        except Exception:
            pass
        return 128 + sig
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
