#!/usr/bin/env python3
"""One-shot: Sun 2026-10-11 09:00 CT email Lizi to check Up/Link 1:1 acceptances before the 10/12 hotel refund deadline. Self-unloads."""
import os, subprocess
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-uplink-meetings-reminder"
if date.today()>=date(2026,10,11):
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]="Reminder: check John's Up/Link meeting acceptances (hotel refund deadline is tomorrow, 10/12)"
    m.set_content("""Hi Lizi,

Time to check which of John's Up/Link 1:1 requests have been accepted:
https://uplink.vimeet.events  (log in as John; Agenda / Meetings tab)

Requests went to: Crystal Shen (NYSE), Chris Quilty (Quilty Space), Alyssa Goessler Goodwin (AE Industrial), Jamie Graham (KippsDeSanto), Dr. Melissa Patton (Space Grove), Charlie Stephens (Fidelity), Michael Roberts (ISS National Lab), Molly Sullivan (Space Tango), John Vellinger (SpaceMD), Elizabeth Reynolds (TRISH), Nestor Levin (SpaceWERX), Woody Woodhouse (Leonardo DRS), Gabriel Swiney (Office of Space Commerce).

Decision rule we agreed on:
- 5+ good acceptances (esp. NYSE, Quilty, AE Industrial, ISS National Lab, Space Tango): keep the full trip (Mon reception + Tue/Wed summit).
- 2-3: shorten to the Mon 10/19 VIP reception + Tue, and cut the extra hotel night(s).
- ~0: reception only, or skip.

The NYC hotel is fully refundable only through MONDAY 10/12, so any change has to happen by tomorrow. Also make sure John's unavailable times are blocked in the Agenda tab.

Paste me the accepted list and I'll add the meetings to his NYC schedule.

- Exo
""")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
    try: os.remove(os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist"))
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
