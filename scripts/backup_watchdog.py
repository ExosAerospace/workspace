#!/usr/bin/env python3
"""
backup_watchdog.py — watches the DR backup-health sentinel and enforces the safety policy.

Runs hourly (launchd). If the last successful Studio->Mini backup is stale/missing or a
pause is already set:
  1. Sets the backup-health PAUSE flag  -> risky/state-mutating crons no-op (via backup_health_gate).
  2. Notifies Jon (Discord DM + #exomac-system) and emails him — DEDUPED (one alert per
     outage, then at most one reminder / 24h), so it never spams.
When health returns, it clears the pause and sends a single recovery note.

Usage: python3 scripts/backup_watchdog.py [--force-alert]
"""
import os, sys, json, time, subprocess
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import backup_health_gate as gate

CFG = json.load(open(os.path.join(WS, "config", "dr-backup.json")))
STATE_DIR = gate.STATE_DIR
ALERT_MARK = os.path.join(STATE_DIR, "backup-watchdog-lastalert.json")
LOG = os.path.join(WS, "logs", "backup-watchdog.log")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
REMINDER_EVERY_H = 24

def logline(s):
    os.makedirs(os.path.join(WS, "logs"), exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat()} {s}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def _openclaw_send(target, text):
    if not os.path.exists(OPENCLAW):
        logline(f"WARN openclaw not at {OPENCLAW}; skip discord to {target}"); return
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", target, "-m", text], timeout=60, check=False)
    except Exception as e:
        logline(f"WARN discord send to {target} failed: {e}")

def notify(text):
    _openclaw_send(CFG.get("alert_discord_dm_target", "user:1501632195163590739"), text)
    sysch = CFG.get("alert_discord_system_channel")
    if sysch:
        _openclaw_send(sysch, text)
    # email via msmtp (best-effort)
    to = CFG.get("alert_email_to", "jquinn@exosaero.com")
    try:
        msg = f"To: {to}\nSubject: [Exos DR] backup-health alert\n\n{text}\n"
        subprocess.run(["msmtp", to], input=msg.encode(), timeout=60, check=False)
    except Exception as e:
        logline(f"WARN email alert failed: {e}")

def load_mark():
    try: return json.load(open(ALERT_MARK))
    except Exception: return {}

def save_mark(d):
    os.makedirs(STATE_DIR, exist_ok=True)
    json.dump(d, open(ALERT_MARK, "w"), indent=2)

def main():
    force = "--force-alert" in sys.argv[1:]
    ok, reason = gate.is_healthy()
    mark = load_mark()
    now = time.time()

    if ok and not force:
        # recovered?
        if mark.get("state") == "alerted":
            gate.clear_pause()
            notify("✅ Exos DR backup RECOVERED — Studio→Mini backup is healthy again; "
                   "paused Studio-only tasks have auto-resumed.")
            save_mark({"state": "healthy", "since": now})
            logline("recovered: pause cleared, resume note sent")
        else:
            logline(f"healthy — {reason}")
        return

    # NOT healthy -> enforce pause + alert (deduped)
    gate.set_pause(f"watchdog: {reason}")
    last = mark.get("last_alert_epoch", 0)
    already = mark.get("state") == "alerted"
    due_reminder = (now - last) > REMINDER_EVERY_H * 3600
    if force or (not already) or due_reminder:
        notify(f"🔴 Exos DR backup NOT HEALTHY — {reason}\n"
               f"Action taken: Studio-only / state-mutating tasks are PAUSED until a good backup lands "
               f"(read-only jobs keep running). They auto-resume on the next successful backup.\n"
               f"Check: `python3 scripts/backup_health_gate.py --status` and the last DR backup run "
               f"(`logs/dr-backup.log`).")
        save_mark({"state": "alerted", "last_alert_epoch": now, "reason": reason})
        logline(f"ALERTED + PAUSED — {reason}")
    else:
        logline(f"still unhealthy ({reason}); alert suppressed (deduped, next reminder in "
                f"{REMINDER_EVERY_H}h)")

if __name__ == "__main__":
    main()
