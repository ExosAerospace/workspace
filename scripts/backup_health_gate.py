#!/usr/bin/env python3
"""
backup_health_gate.py — shared DR backup-health gate for the Studio->offsite-Mini topology.

Two jobs:
  1. The daily backup writes a "healthy" sentinel here on success (write_healthy()).
  2. Risky / state-mutating crons import this and call guard_or_exit() at startup.
     If the last successful backup is stale (default >26h) OR a pause flag is set,
     the risky job logs and no-ops (graceful exit 0) so state can't drift further
     out of sync while we are unprotected. Read-only jobs simply don't call it.

Sentinel:  ~/.openclaw/state/backup-healthy.json
Pause flag: ~/.openclaw/state/backup-paused.flag   (created by the watchdog on outage;
            removed automatically when health returns)

CLI:
  python3 backup_health_gate.py --status        # print current health, exit 0
  python3 backup_health_gate.py --check         # exit 0 if healthy, 1 if not (for shell gates)
  python3 backup_health_gate.py --guard NAME    # simulate a risky-cron guard
  python3 backup_health_gate.py --write SHA     # mark healthy (used by the backup script)
  python3 backup_health_gate.py --pause "reason"
  python3 backup_health_gate.py --resume
"""
import os, sys, json, time
from datetime import datetime, timezone

STATE_DIR = os.path.expanduser("~/.openclaw/state")
SENTINEL  = os.path.join(STATE_DIR, "backup-healthy.json")
PAUSE     = os.path.join(STATE_DIR, "backup-paused.flag")
DEFAULT_MAX_AGE_H = 26

def _now():
    return datetime.now(timezone.utc)

def _load_cfg_max_age():
    try:
        cfg = json.load(open(os.path.expanduser("~/.openclaw/workspace/config/dr-backup.json")))
        return float(cfg.get("max_age_hours", DEFAULT_MAX_AGE_H))
    except Exception:
        return DEFAULT_MAX_AGE_H

def read_state():
    try:
        return json.load(open(SENTINEL))
    except Exception:
        return None

def write_healthy(manifest_sha="", host=None):
    os.makedirs(STATE_DIR, exist_ok=True)
    st = {
        "last_success_iso": _now().isoformat(),
        "last_success_epoch": int(time.time()),
        "manifest_sha": manifest_sha,
        "host": host or os.uname().nodename,
    }
    tmp = SENTINEL + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2)
    os.replace(tmp, SENTINEL)
    # a successful backup clears any standing pause
    if os.path.exists(PAUSE):
        try: os.remove(PAUSE)
        except Exception: pass
    return st

def is_healthy(max_age_h=None):
    """Return (bool healthy, str reason)."""
    if os.path.exists(PAUSE):
        try: reason = open(PAUSE).read().strip() or "manual/watchdog pause"
        except Exception: reason = "pause flag set"
        return False, f"PAUSED: {reason}"
    max_age_h = max_age_h if max_age_h is not None else _load_cfg_max_age()
    st = read_state()
    if not st:
        return False, "no successful backup on record (sentinel missing)"
    age_h = (time.time() - st.get("last_success_epoch", 0)) / 3600.0
    if age_h > max_age_h:
        return False, f"last backup {age_h:.1f}h ago (> {max_age_h:.0f}h threshold)"
    return True, f"healthy — last backup {age_h:.1f}h ago"

def guard_or_exit(job_name="risky-cron", log=None):
    """Risky/state-mutating crons call this FIRST. If unhealthy, log + graceful exit(0)."""
    ok, reason = is_healthy()
    if not ok:
        msg = f"[backup-gate] {job_name} SKIPPED — DR backup not healthy: {reason}"
        (log or print)(msg)
        sys.exit(0)
    return True

def set_pause(reason="watchdog: backup stale"):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(PAUSE, "w") as f:
        f.write(f"{_now().isoformat()} — {reason}\n")

def clear_pause():
    if os.path.exists(PAUSE):
        os.remove(PAUSE)
        return True
    return False

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--status":
        ok, reason = is_healthy()
        st = read_state()
        print(f"health: {'OK' if ok else 'NOT HEALTHY'} — {reason}")
        print(f"sentinel: {json.dumps(st) if st else '(none)'}")
        print(f"pause flag: {'SET' if os.path.exists(PAUSE) else 'clear'}")
        sys.exit(0)
    if a[0] == "--check":
        ok, _ = is_healthy(); sys.exit(0 if ok else 1)
    if a[0] == "--guard":
        name = a[1] if len(a) > 1 else "test"
        guard_or_exit(name); print(f"[backup-gate] {name} allowed to run (healthy)"); sys.exit(0)
    if a[0] == "--write":
        sha = a[1] if len(a) > 1 else ""
        print("wrote:", write_healthy(sha)); sys.exit(0)
    if a[0] == "--pause":
        set_pause(a[1] if len(a) > 1 else "manual"); print("paused"); sys.exit(0)
    if a[0] == "--resume":
        print("resumed" if clear_pause() else "was not paused"); sys.exit(0)
    print(__doc__); sys.exit(2)
