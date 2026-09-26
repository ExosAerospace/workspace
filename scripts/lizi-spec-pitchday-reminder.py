#!/usr/bin/env python3
"""Reminders for the SpEC Pitch Day sign-up (John: can't-miss). Sign-ups close Tue 2026-09-16.
Fires Mon 9/15 08:00 CT (day-before) and Tue 9/16 08:00 CT (deadline day). Checks MC task #2812;
only nudges if not Done. Emails + Discord-DMs Lizi. Self-unloads after 9/16."""
import os, subprocess, json, urllib.request
from datetime import datetime
LIZI="lquinn@exosaero.com"; LIZI_DISCORD="1506647219351060631"
OPENCLAW="/Users/exomac/.local/share/mise/shims/openclaw"
LABEL="com.exos.lizi-spec-pitchday"; SECRETS=os.path.expanduser("~/.openclaw/secrets.json")
SUPA="https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/tasks?id=eq.2812&select=state"
def task_done():
    try:
        k=json.load(open(SECRETS))["supabase_service_role_key"]
        req=urllib.request.Request(SUPA,headers={"apikey":k,"Authorization":"Bearer "+k})
        rows=json.loads(urllib.request.urlopen(req,timeout=30).read())
        return bool(rows) and str(rows[0].get("state","")).lower() in ("done","complete","completed")
    except Exception: return False
def self_unload():
    uid=os.getuid(); plist=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: subprocess.run(["launchctl","bootout",f"gui/{uid}/{LABEL}"],capture_output=True)
    except Exception: pass
    try:
        if os.path.exists(plist): os.remove(plist)
    except Exception: pass
def notify(subject, body, discord):
    from email.message import EmailMessage
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]=LIZI; m["Subject"]=subject; m.set_content(body)
    try: subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail",LIZI],input=m.as_bytes(),check=True,timeout=60)
    except Exception as e: print("email failed:",e)
    try: subprocess.run([OPENCLAW,"message","send","--channel","discord","--target",LIZI_DISCORD,"-m",discord],timeout=60,capture_output=True)
    except Exception: pass
now=datetime.now(); md=(now.month, now.day)
if md in ((9,15),(9,16)) and not task_done():
    last = " — SIGN-UPS CLOSE TODAY" if md==(9,16) else " (closes tomorrow 9/16)"
    notify("SpEC Pitch Day — register SYD 80 + confirm SSLC presenter"+last+" (MC #2812)",
      ("Hi Lizi,\n\nSpEC Pitch Day (Oct 19, LAX) sign-ups close TUESDAY 9/16 — John flagged this can't-miss.\n"
       "Two things: (1) confirm the SSLC presenter — Markus Rufer (Pres/CEO SMAD) or Jim Wertz (Chairman SSLC) "
       "+ Mike Morey technical, all Torrance-local; the Rufer nomination note is drafted "
       "(drafts/SpEC_PitchDay_Rufer_SSLC_presenter_2026-09-10.md). (2) Register the SYD 80 (YKG-XX Refueler) session "
       "for Exos at space-enterprise.org / specopps@nstxl.org. Ping me for the draft or a pitch one-pager. (MC #2812)\n\n- Exo\n"),
      "📌 SpEC Pitch Day (Oct 19 LAX) sign-ups close 9/16"+last+": confirm the SSLC presenter (Rufer/Wertz + Morey, all Torrance-local) + register the SYD 80 refueler session for Exos. Rufer note drafted — ping me. (MC #2812)")
if md >= (9,16): self_unload()
