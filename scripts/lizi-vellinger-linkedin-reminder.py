#!/usr/bin/env python3
"""One-shot reminder to Lizi: send John Vellinger (Redwire/SpaceMD) a LinkedIn
follow-up message re: BLK3 Flight 2 pharma pre-screen. Fires Mon 2026-08-24 09:00 CT
via launchd (com.exos.lizi-vellinger-linkedin), then self-unloads. Idempotent: a
state file guards against re-send if the job ever re-fires before unload."""

import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     ".lizi-vellinger-reminder-sent")
LABEL = "com.exos.lizi-vellinger-linkedin"

SMTP_HOST = "127.0.0.1"
SMTP_PORT = 1025
EMAIL_USER = "jquinnexo@pm.me"
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
LIZI_EMAIL = "Lquinn@exosaero.com"


def self_unload():
    """Remove this job from launchd so it never fires again."""
    uid = os.getuid()
    plist = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try:
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"],
                       capture_output=True)
    except Exception:
        pass
    try:
        if os.path.exists(plist):
            os.remove(plist)
    except Exception:
        pass


def main():
    if os.path.exists(STATE):
        self_unload()
        return

    subject = "Reminder: LinkedIn follow-up to John Vellinger (Redwire/SpaceMD)"
    text = """Hi Lizi,

Reminder for BLK3 Flight 2 outreach:

Send John Vellinger (CEO, Redwire/SpaceMD) a LinkedIn message following up on the
connection request you sent 8/17. Angle: Exos BLK3 Flight 2 as a fast, low-cost
suborbital microgravity pre-screen for SpaceMD's PIL-BOX pharma work (the Lilly /
BMS compound screening) before committing to an orbital run.

You also emailed Tere.Riley@rdw.com to get routed to the right person on his team.

- Exo
"""
    html = """<html><body style="font-family:-apple-system,system-ui,sans-serif;color:#1a1a1a;line-height:1.6;">
<p>Hi Lizi,</p>
<p><strong>Reminder for BLK3 Flight 2 outreach:</strong></p>
<p>Send <strong>John Vellinger</strong> (CEO, Redwire/SpaceMD) a LinkedIn message
following up on the connection request you sent 8/17. Angle: Exos BLK3 Flight 2 as a
fast, low-cost suborbital microgravity pre-screen for SpaceMD's PIL-BOX pharma work
(the Lilly / BMS compound screening) before committing to an orbital run.</p>
<p>You also emailed <a href="mailto:Tere.Riley@rdw.com">Tere.Riley@rdw.com</a> to get
routed to the right person on his team.</p>
<p>&mdash; Exo</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = LIZI_EMAIL
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, LIZI_EMAIL, msg.as_string())

    with open(STATE, "w") as f:
        f.write("sent\n")
    print(f"Reminder sent to {LIZI_EMAIL}")
    self_unload()


if __name__ == "__main__":
    main()
