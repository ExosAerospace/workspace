#!/usr/bin/env python3
"""
Sept 16 reminder for Lizi's Georgia Tech Space Week prep deliverables.

Fires once via launchd (com.exos.spaceweek-prep-reminder) on Tue 2026-09-16 ~08:00 CT.
Checks MC tasks #2767 (conference prep sheet) and #2768 (tailored university one-pager
capabilities handout) in Supabase. Emails Lizi a reminder for whichever are NOT yet Done,
noting the 9/17 deadline. If both are already Done, it does nothing (silent).
Requested by Lizi 2026-09-09.
"""
import json, os, shutil, subprocess, sys, urllib.request
from datetime import datetime, timezone

TASK_IDS = [2767, 2768]
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
LOG = os.path.expanduser("~/.openclaw/workspace/logs/spaceweek-prep-reminder.log")


def logline(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")


def open_tasks():
    k = json.load(open(SECRETS))["supabase_service_role_key"]
    ids = ",".join(str(i) for i in TASK_IDS)
    req = urllib.request.Request(
        SUPA + f"tasks?id=in.({ids})&select=id,title,state,due_date",
        headers={"apikey": k, "Authorization": "Bearer " + k})
    rows = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return [r for r in rows if str(r.get("state", "")).lower() not in ("done", "complete", "completed")]


def send_reminder(pending):
    from email.message import EmailMessage
    lines = "\n".join(f"  - Task #{t['id']}: {t['title']}" for t in pending)
    msg = EmailMessage()
    msg["From"] = "jquinnexo@pm.me"
    msg["To"] = "lquinn@exosaero.com"
    msg["Reply-To"] = "lquinn@exosaero.com"
    msg["Subject"] = "[REMINDER — due tomorrow 9/17] Georgia Tech Space Week prep deliverables"
    msg["X-Priority"] = "1"; msg["Importance"] = "High"
    msg.set_content(
        "Lizi,\n\n"
        "Quick reminder — your Georgia Tech Space Week prep items are due TOMORROW, "
        "Thursday 9/17:\n\n"
        f"{lines}\n\n"
        "The prep sheet kicks off the moment the poster presenter list drops — forward it to "
        "me and I'll cross-match against the BLK3 payload profile and hand you a ranked hit "
        "list. The tailored university one-pager I can have drafted for your review on request; "
        "just say go.\n\n"
        "Ping me here (this channel) if you want either one moved forward now.\n\n"
        "- Exo")
    msmtp = shutil.which("msmtp") or "/opt/homebrew/bin/msmtp"
    p = subprocess.run([msmtp, "-t"], input=msg.as_bytes(), capture_output=True)
    return p.returncode == 0, p.stderr.decode()[:200]


def main():
    try:
        pending = open_tasks()
    except Exception as e:
        logline(f"ERROR reading tasks: {e}")
        return 1
    if not pending:
        logline("both tasks already Done — no reminder sent")
        return 0
    ok, err = send_reminder(pending)
    logline(f"pending={[t['id'] for t in pending]} → reminder email {'SENT' if ok else 'FAILED: '+err}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
