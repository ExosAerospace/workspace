#!/usr/bin/env python3
"""One-shot: Wed 2026-10-14 09:00 CT email Lizi to send the SHELLGAME nudge to Larry Paxton (JHU/APL). Self-unloads."""
import os, subprocess
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-paxton-nudge-reminder"
if date.today()>=date(2026,10,14):
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]="Reminder: nudge Larry Paxton (JHU/APL, SHELLGAME) today"
    m.set_content("""Hi Lizi,

Reminder to send Larry Paxton (larry.paxton@jhuapl.edu) a follow-up today if he hasn't replied to your 9/30 email. Reply on that same thread.

Draft:

Hi Larry,
I wanted to follow up on SHELLGAME now that the NDA is in place. We're booking payloads for our BLK3 flights in early 2027, and I'd love to understand what you'd need from a flight. Even rough numbers on size, mass and power would help us see if it's a fit. If a quick 20-minute call is easier, I'm happy to set one up with our engineering team.
Best Regards,
Lizi

If there's still nothing by ~10/28, the next step is asking Josh Wolk to nudge him internally. Task #2694.

- Exo""")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
    p=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: os.remove(p)
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
