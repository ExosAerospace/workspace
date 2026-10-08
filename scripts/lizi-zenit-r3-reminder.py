#!/usr/bin/env python3
"""One-shot: Mon 2026-11-16 09:00 CT email Lizi to check NSPIRES for the NASA EPSCoR R3 cycle and send dates to Roberto Zenit (Brown). Self-unloads."""
import os, subprocess
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-zenit-r3-reminder"
if date.today()>=date(2026,11,16):
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]="Reminder: NASA EPSCoR R3 dates for Roberto Zenit (Brown)"
    m.set_content("""Hi Lizi,

Mid-November reminder: check whether NASA has posted the new EPSCoR Rapid Response Research (R3) call, and if so send Roberto Zenit (roberto_zenit@brown.edu) the dates as promised. Last cycle was released Nov 2024 and due Feb 26, 2025.

Where to look: NSPIRES (nspires.nasaprs.com, Solicitations > Open, search "EPSCoR R3") or the RI Space Grant / RI NASA EPSCoR site. Or just reply in #lizi-channel-2 and I'll look it up and draft the email.

Task #1883. Any letter of support goes through John.

- Exo""")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
    p=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: os.remove(p)
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
