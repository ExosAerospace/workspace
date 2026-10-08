#!/usr/bin/env python3
"""One-shot: Tue 2026-10-13 09:00 CT email Lizi to check whether Olivia Borgue / Kyle Acierno (Exobiosphere) accepted her LinkedIn requests. Self-unloads."""
import os, subprocess
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-exobiosphere-reminder"
if date.today()>=date(2026,10,13):
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]="Reminder: LinkedIn follow-ups (Exobiosphere, Rhea, Space Lab)"
    m.set_content("Hi Lizi,\n\nQuick reminder to check LinkedIn for Exobiosphere:\n\n- Dr. Olivia Borgue, Co-Founder (your preferred contact): https://lu.linkedin.com/in/oliviaborgue\n- Kyle Acierno, CEO: https://www.linkedin.com/in/kyleacierno\n\nIf either accepted, send the message from #lizi-channel-2 (10/6): recoverable suborbital shakedown of their screening hardware before their 2027 orbital mission, early 2027. You can open with the Notre Dame connection (their platform is installed in Dr. Meenal Datta's lab).\nIf neither accepted, tell me and I'll find another route in.\n\nALSO: Rhea Space Activity, Shawn Usman (Founder & CEO): https://www.linkedin.com/in/shawn-usman-8b4169169 (request sent 10/7). If he accepted, send the message from #lizi-channel-2 (10/7): flight data for AutoNav on a recoverable BLK3 flight, early 2027.\n\nALSO: Space Lab Technologies, Adam Escobar (President & CEO): https://www.linkedin.com/in/adam-escobar-6a2a08171 (request + note sent 10/7). If he accepted, ask for a short call about giving uG-LilyPond a new ride on BLK3 (New Shepard is paused), and ask him to loop in Christine.\n\nALSO: Higher Orbits, Michelle Lucas: https://www.linkedin.com/in/michellellucas (if you sent a LinkedIn request 10/8, check if she accepted).\n\nALSO: Starlab Space, Marshall Smith (CEO): https://www.linkedin.com/in/marshall-smith4 (request sent 10/8). If he accepted, message: \"Hi Marshall, thanks for connecting! Exos has been flying commercial payloads since 2018, and BLK3, our latest FAA-licensed reusable rocket, flies in early 2027. For researchers headed to Starlab, a short recoverable flight could be a low-cost way to check hardware before committing station time. Would a quick call make sense?\" If no response, try Bradley Henderson (Starlab Chief Commercial Officer).\n\n- Exo")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
    p=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: os.remove(p)
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
