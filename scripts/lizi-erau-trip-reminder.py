#!/usr/bin/env python3
"""Two-shot reminder for Lizi's ERAU Oct 5/6 trip decision:
 - Mon 2026-09-14 08:00 CT: price out the trip + confirm Exo's estimate (MC #2792)
 - Tue 2026-09-15 08:00 CT: email Allison with the payload-research agenda ask (MC #2793, go/no-go driver)
Checks the relevant task's state; only nudges if not Done. Emails + Discord-DMs Lizi. Self-unloads after 9/15."""
import os, subprocess, json, urllib.request
from datetime import datetime
LIZI="lquinn@exosaero.com"; LIZI_DISCORD="1506647219351060631"
OPENCLAW="/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"
LABEL="com.exos.lizi-erau-trip"
SECRETS=os.path.expanduser("~/.openclaw/secrets.json")
SUPA="https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/tasks?id=eq.{}&select=state"

def task_done(tid):
    try:
        k=json.load(open(SECRETS))["supabase_service_role_key"]
        req=urllib.request.Request(SUPA.format(tid),headers={"apikey":k,"Authorization":"Bearer "+k})
        rows=json.loads(urllib.request.urlopen(req,timeout=30).read())
        return bool(rows) and str(rows[0].get("state","")).lower() in ("done","complete","completed")
    except Exception:
        return False

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
if md==(9,14):
    if not task_done(2792):
        notify("ERAU trip (Oct 5/6) — price it out today (MC #2792)",
          ("Hi Lizi,\n\nToday's task: price out the ERAU Daytona visit and confirm Exo's estimate.\n"
           "Exo est ~$700 (2 days, reg WAIVED): airfare DFW<->DAB ~$375 (economy, 1-stop ATL), 1 night hotel near\n"
           "campus ~$85-103, ground+meals ~$225. Confirm against real bookings. Remember: recruiting is NOT a\n"
           "priority, payloads ARE — the trip is justified only by payload/research value, not the Expo. (MC #2792)\n\n- Exo\n"),
          "📌 ERAU trip: price it out today + confirm my ~$700 estimate (2 days, reg waived). Payload value only — recruiting isn't the point. (MC #2792)")
elif md==(9,15):
    if not task_done(2793):
        notify("ERAU — email Allison today: the agenda ask (MC #2793)",
          ("Hi Lizi,\n\nToday's task: send Allison (cc Liz) the follow-up asking her to build a research/payload agenda\n"
           "around the Oct 5/6 visit — faculty + flight-oriented student orgs + teams with flyable hardware. Their\n"
           "willingness to line that up IS your go/no-go signal.\n\nDraft is ready: drafts/ERAU_Allison_agenda_followup_DRAFT_2026-09-15.md\n"
           "Ping me and I'll drop it in front of you. (MC #2793)\n\n- Exo\n"),
          "📌 ERAU: email Allison today — ask her to build the payload/research agenda around Oct 5/6 (that's the go/no-go). Draft's ready, ping me for it. (MC #2793)")
    self_unload()
elif md > (9,15):
    self_unload()
