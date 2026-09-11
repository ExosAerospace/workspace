#!/usr/bin/env python3
"""One-shot reminder to Lizi: follow up on the Planet Labs LinkedIn outreach.
Fires Tue 2026-09-01 09:00 CT via launchd (com.exos.lizi-planet-linkedin), then
self-unloads. Idempotent: a state file guards against re-send if the job ever
re-fires before unload.

Context: this is Send #32 of 63 (BLK3 F2 / payload outreach). On 2026-08-25 Lizi
sent LinkedIn connection requests to Robbie Schingler (Co-founder & CSO) and James
Mason (Chief Space Officer) at Planet Labs. IMPORTANT: she sent them from her
PERSONAL LinkedIn, not the Exos company profile (Exos LinkedIn wouldn't load; only
the phone app worked on the plane)."""

import os
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     ".lizi-planet-reminder-sent")
LABEL = "com.exos.lizi-planet-linkedin"

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

    subject = "Reminder: LinkedIn follow-ups - Planet, Spire, Capella"
    text = """Hi Lizi,

One-week follow-up on the BLK3 payload LinkedIn outreach.

PLANET LABS (Send #32) - requests sent 8/25:
  - Robbie Schingler - Co-founder & Chief Strategy Officer
  - James Mason - Chief Space Officer (the right target for instrument qualification)

SPIRE GLOBAL (Send #33):
  - Eric "Mell" Mellinger - Chief Commercial Officer. ACCEPTED your request 8/25 and
    you sent him a message (PUG + call ask). If no reply yet, send a short nudge.
    (The original "Gina Ruebensaal" target was a wrong-company name collision - she's
    at a consulting firm called Spire Strategies. Corrected in the campaign list.)

CAPELLA SPACE (Send #34) - request sent 8/25:
  - Christian Lenz - Chief Technology Officer (SAR sensor/antenna component testing).
    Follow up with a message if he accepted.

Heads up: you sent these from your PERSONAL LinkedIn, not the Exos company profile
(the Exos account wouldn't load on the plane). So check your personal LinkedIn for
accepts/replies, not the Exos one.

For anyone who accepted:
  - Send them a message + the Payload User Guide and offer a tentative slot on an
    upcoming BLK3 flight.
  - Angle: fast, repeatable suborbital environment to qualify sensors/instruments
    (and, for Spire, antennas) before they fly orbital; two-day turnaround.
  - Do NOT quote $/kg pricing (needs Jon's approval first).

If no response yet, a short LinkedIn nudge is fine, or ask for a pointer to whoever
owns payload/instrument qualification on their side.

- Exo
"""
    html = """<html><body style="font-family:-apple-system,system-ui,sans-serif;color:#1a1a1a;line-height:1.6;">
<p>Hi Lizi,</p>
<p><strong>One-week follow-up on the BLK3 payload LinkedIn outreach.</strong></p>
<p><strong>Planet Labs (Send #32)</strong> &ndash; requests sent 8/25:</p>
<ul>
<li><strong>Robbie Schingler</strong> &ndash; Co-founder &amp; Chief Strategy Officer</li>
<li><strong>James Mason</strong> &ndash; Chief Space Officer (the right target for instrument qualification)</li>
</ul>
<p><strong>Spire Global (Send #33):</strong></p>
<ul>
<li><strong>Eric &ldquo;Mell&rdquo; Mellinger</strong> &ndash; Chief Commercial Officer. <strong>Accepted</strong>
your request 8/25 and you sent him a message (PUG + call ask). If no reply yet, send a short nudge.</li>
</ul>
<p style="color:#555;font-size:13px;">(The original &ldquo;Gina Ruebensaal&rdquo; target was a wrong-company name
collision &mdash; she's at a consulting firm called Spire Strategies. Corrected in the campaign list.)</p>
<p><strong>Capella Space (Send #34)</strong> &ndash; request sent 8/25:</p>
<ul>
<li><strong>Christian Lenz</strong> &ndash; Chief Technology Officer (SAR sensor/antenna component testing).
Follow up with a message if he accepted.</li>
</ul>
<p><strong>Heads up:</strong> you sent these from your <strong>personal LinkedIn</strong>, not the
Exos company profile (the Exos account wouldn't load on the plane). So check your personal
LinkedIn for accepts/replies, not the Exos one.</p>
<p><strong>For anyone who accepted:</strong></p>
<ul>
<li>Send a message + the Payload User Guide and offer a tentative slot on an upcoming BLK3 flight.</li>
<li>Angle: fast, repeatable suborbital environment to qualify sensors/instruments (and, for Spire,
antennas) before they fly orbital; two-day turnaround.</li>
<li>Do <strong>not</strong> quote $/kg pricing (needs Jon's approval first).</li>
</ul>
<p>If no response yet, a short LinkedIn nudge is fine, or ask for a pointer to whoever owns
payload/instrument qualification on their side.</p>
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
