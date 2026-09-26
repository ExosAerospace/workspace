#!/usr/bin/env python3
"""
fleet_status_heartbeat.py — hourly fleet/Supabase check; DMs Jon on EXCEPTION ONLY.

Combines, in a single Discord DM:
  • Fleet health — enabled OpenClaw cron jobs OK vs error (from ~/.openclaw/state/openclaw.sqlite)
    + launchd com.exos.* agents with a bad last exit code.
  • Supabase health — mem/disk/connections via scripts/supabase_metrics_pull.py, with threshold flags.

Cadence: launchd hourly, 24/7. Silent when everything is in tolerance (Jon 2026-09-26: "report
on exception only — I don't need a notification that they are in tolerance every hour"). It only
DMs on a real problem: persistent cron errors, a bad launchd exit, a Supabase threshold breach,
or metrics/DB unavailable. Transient single cron errors alone do not trigger a DM.
"""
import json, os, sqlite3, subprocess, shutil, datetime
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
    CT = ZoneInfo("America/Chicago")
except Exception:
    CT = None

WS = Path("/Users/exomac/.openclaw/workspace")
DB = Path(os.path.expanduser("~/.openclaw/state/openclaw.sqlite"))
JON_ID = "1501632195163590739"
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
THRESH = {"disk_pct": 80.0, "mem_pct": 88.0, "pg_connections": 55.0}


def _env():
    env = os.environ.copy()
    env["PATH"] = ":".join([os.path.dirname(OPENCLAW), "/Users/exomac/.local/share/mise/shims",
                            "/opt/homebrew/bin", "/usr/local/bin", env.get("PATH", "")])
    return env


def cron_health():
    out = {"ok": 0, "err": 0, "none": 0, "errors": [], "persistent": 0}
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        for name, status, err, cerr in con.execute(
            "SELECT name, last_run_status, last_error, consecutive_errors FROM cron_jobs WHERE enabled=1"):
            if status == "ok":
                out["ok"] += 1
            elif status == "error":
                out["err"] += 1
                out["errors"].append((name, (err or "")[:80], cerr or 0))
                if (cerr or 0) >= 2:
                    out["persistent"] += 1
            else:
                out["none"] += 1
        con.close()
    except Exception as e:
        out["db_error"] = str(e)[:120]
    return out


def launchd_bad():
    # A job is "bad" only if it is NOT currently running (PID "-") AND its last run exited with a
    # POSITIVE error code. Running services (PID present) are healthy regardless of a stale last
    # exit, and negative codes are signal terminations (e.g. -15 SIGTERM from a normal restart).
    bad = []
    try:
        r = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=20)
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[2].startswith("com.exos."):
                pid, code, label = parts[0], parts[1], parts[2]
                try:
                    ec = int(code)
                except Exception:
                    ec = 0
                if pid == "-" and ec > 0:
                    bad.append((label, code))
    except Exception:
        pass
    return bad


def supabase():
    try:
        r = subprocess.run(["python3", str(WS / "scripts" / "supabase_metrics_pull.py"), "--json"],
                           capture_output=True, text=True, timeout=40)
        d = json.loads(r.stdout.strip() or "{}")
        if not d.get("ok"):
            return None, ["metrics fetch failed"]
        breaches = [k for k, lim in THRESH.items() if d.get(k) is not None and d[k] >= lim]
        return d, breaches
    except Exception:
        return None, ["metrics fetch failed"]


def dm(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", f"user:{JON_ID}", "-m", text],
                       capture_output=True, timeout=60, env=_env())
    except Exception:
        pass


def main():
    now = datetime.datetime.now(CT) if CT else datetime.datetime.now()

    ch = cron_health()
    bad = launchd_bad()
    sb, breaches = supabase()

    problem = bool(ch.get("persistent") or bad or breaches or sb is None or ch.get("db_error"))
    if not problem:
        return  # in tolerance → stay silent (exception-only, any hour)

    lead = "🔴"
    total = ch["ok"] + ch["err"] + ch["none"]
    fleet = f"Fleet: {ch['ok']}/{total} crons OK"
    persistent = [n for n, _, c in ch["errors"] if (c or 0) >= 2]
    transient = ch["err"] - len(persistent)
    if persistent:
        fleet += f" · {len(persistent)} FAILING ({', '.join(persistent[:3])})"
    if transient:
        fleet += f" · {transient} transient err (self-clears)"
    if bad:
        fleet += f" · launchd bad-exit: {', '.join(n for n, _ in bad[:3])}"
    elif not ch.get("db_error"):
        fleet += " · launchd OK"

    if sb:
        sbl = f"Supabase (t4g.micro): mem {sb['mem_pct']}% · disk {sb['disk_pct']}% · {int(sb['pg_connections'])} conns"
        if breaches:
            sbl += f"  ⚠ OVER: {', '.join(breaches)}"
    else:
        sbl = "Supabase: metrics unavailable"

    tag = now.strftime("%-I:%M %p CT")
    msg = f"{lead} Fleet exception ({tag})\n  {fleet}\n  {sbl}"
    dm(msg)


if __name__ == "__main__":
    main()
