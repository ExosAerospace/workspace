#!/usr/bin/env python3
"""One-shot (Wed 2026-09-16, 8:00 CT): nudge Lizi to check whether her Stoke Space LinkedIn
connect requests were accepted and, if so, send the intro messages. Emails + Discord-DMs Lizi,
then self-unloads. Context: SSLC clean-fuel 'Nature Smart' feature — Mike asked for a Stoke contact;
Lizi sent requests to Devon Papandrew (VP BD) + Kristen Russell (marketing/comms) + others; could NOT
request Andy Lapsa (CEO) — needs an alternate path."""
import os, subprocess
from email.message import EmailMessage
LIZI="lquinn@exosaero.com"; LIZI_DISCORD="1506647219351060631"
OPENCLAW="/Users/exomac/.local/share/mise/shims/openclaw"
LABEL="com.exos.lizi-stoke-linkedin"
def self_unload():
    uid=os.getuid(); plist=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: subprocess.run(["launchctl","bootout",f"gui/{uid}/{LABEL}"],capture_output=True)
    except Exception: pass
    try:
        if os.path.exists(plist): os.remove(plist)
    except Exception: pass
body=("Hi Lizi,\n\nDid your Stoke Space LinkedIn requests get accepted?\n"
      "  - Devon Papandrew (VP, Business Development) - the partnerships gateway\n"
      "  - Kristen Russell (Marketing/Brand/Communications) - owns story/feature asks\n"
      "  - (plus any others you sent)\n\n"
      "If yes: send the intro message tied to the SSLC clean-fuel 'Nature Smart' feature — Stoke's\n"
      "LOX/hydrogen clean-propulsion story + name recognition is exactly Mike's pick — and you can\n"
      "layer in the BLK3 angle (recoverable suborbital flight-test to de-risk their landing/recovery\n"
      "GNC hardware before their own recovery attempts). Ping Exo and I'll draft the messages.\n\n"
      "Also: you couldn't send ANDY LAPSA (CEO) a request. Once Papandrew or Russell connects, ask them\n"
      "to point you to Andy — or ping me and I'll hunt his email / a warm path in.\n\n"
      "Then loop Mike back in with the intro once someone connects.\n\n"
      "If nothing's accepted yet, just hold and re-check in a few days.\n\n- Exo\n")
m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]=LIZI
m["Subject"]="Stoke Space - check your LinkedIn connects + send the intros"; m.set_content(body)
try:
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail",LIZI],input=m.as_bytes(),check=True,timeout=60); print("emailed Lizi")
except Exception as e: print("email failed:",e)
try:
    subprocess.run([OPENCLAW,"message","send","--channel","discord","--target",LIZI_DISCORD,"-m",
      "📌 Stoke Space: did your LinkedIn requests (Devon Papandrew - VP BD, Kristen Russell - marketing/comms) get accepted? If yes, ping me and I'll draft the intros for the SSLC clean-fuel 'Nature Smart' feature (+ BLK3 recovery de-risk angle), then loop Mike in. Andy Lapsa (CEO) still needs a path in. If nothing's accepted, hold and re-check."],
      timeout=60,capture_output=True)
except Exception: pass
self_unload()
