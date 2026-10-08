#!/usr/bin/env python3
"""Dated follow-up digest for Lizi (10/15, 10/20, 10/21, 10/22 at 09:00 CT). Emails only items due today whose
CRM contact hasn't been touched since the send. Self-unloads after 10/22."""
import os, json, subprocess, urllib.request
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-followup-digest"
DUE={
 "2026-10-09":[
  ("ECA certificate for CMMC (#2813): retrieve by Sat 10/10","your email: look for the 'Certificate Issuance Notice'","if it isn't retrieved within 30 days of the ~9/10 forms date, the application restarts; SpaceWERX (due 10/21) needs the SPRS score posted",
   "(No email to send.) Steps: 1) find the Certificate Issuance Notice, 2) retrieve + install the cert in your browser, 3) confirm whose name it's under (it must match whoever posts the score in PIEE: John or Neil), 4) tell Exo in #lizi-channel-2 if you get stuck.")],
 "2026-10-14":[
  ("John Cothran: watch invoice #0075 (phone number needed)","cothranprp@gmail.com (reply on your earlier thread)","his invoice is ready except his phone number",
   "Hi John,\nJust following up on your watch order. I have everything I need for your invoice except a phone number. Could you send that over when you get a chance? Thank you!\nBest Regards,\nLizi")],
 "2026-10-15":[
  ("SpaceTango: Danielle Rosales","reply on your 10/5 thread","emailed 10/5 (#1001)",
   "Hi Danielle,\nJust checking in on my note from last week about BLK3. We're booking payloads for early 2027 flights, and I'd love to find a time to talk about how we might work together for your customers. Would a quick call work?\nBest Regards,\nLizi"),
  ("Watch buyers (task #3408)","reply on each buyer's thread","watch-list email sent ~10/5",
   "Hi [Name],\nJust following up on the watch. I wanted to make sure you got my last email, and I'm happy to answer any questions or get the invoice over to you whenever you're ready.\nBest Regards,\nLizi"),
  ("David Mitchell: Nov 7 investor notice","reply on your Teams-link email to David","you sent him the Teams link 10/8; notice must go out by ~10/23 (15-day bylaw) / 10/28 (Texas 10-day min)",
   "Hi David,\nJust checking that the Nov 7 investor meeting notice went out with the Teams link and the record date. Anything you need from me?\nBest Regards,\nLizi")],
 "2026-10-20":[
  ("NCAR: Eric Apel","reply on his 10/6 thread","warm reply 10/6",
   "Hi Eric,\nFollowing up on our exchange from earlier this month. I'd love to set up a short call to talk through what an atmospheric chemistry payload on BLK3 could look like. What times work for you in the next week or two?\nBest Regards,\nLizi")],
 "2026-10-21":[
  ("Axiom: Chyree Batton","Chyree@axiomspace.com (reply on thread)","sent 10/7",
   "Hi Chyree,\nJust following up on my note about a recovered BLK3 test flight for your battery and vacuum qualification work. Happy to set up a short technical call whenever works for your team.\nBest Regards,\nLizi"),
  ("JHU/APL: Josh Wolk","joshua.wolk@jhuapl.edu (reply on thread)","follow-up sent 10/7",
   "Hi Josh,\nJust circling back on my note from earlier this month. If you can share a bit about the payloads you're working on, I'd love to set up a short call with our engineering team. We can put an NDA in place first if needed.\nBest Regards,\nLizi"),
  ("Magma Space: Alessandro Stabile","outreach@magma-space.com","sent 10/7 (#2307)",
   "Hi Alessandro,\nFollowing up on my note about flying your maglev reaction wheel on BLK3 in early 2027. Would a quick call be helpful to see if it's a fit?\nBest Regards,\nLizi"),
  ("UCLA: Prof. Chee Wei Wong","cheewei.wong@ucla.edu","sent 10/7",
   "Hi Professor Wong,\nJust following up on my note about a BLK3 rocket flight as a next step after your balloon test. Happy to set up a short call whenever works for you.\nBest Regards,\nLizi")],
 "2026-10-22":[
  ("Montana Space Grant: Angela Des Jardins","angela.desjardins@montana.edu, cc amy.brown11@montana.edu","sent 10/8 (#3287)",
   "Hi Angela,\nJust following up on my note about BLK3 as a next step for BOREALIS student payloads. Would a short call work in the next couple of weeks?\nBest Regards,\nLizi"),
  ("Carthage: Kevin Crosby","reply on your 10/8 thread","sent 10/8",
   "Hi Professor Crosby,\nJust following up on my note about a possible BLK3 follow-on flight for your ullage trapping work. Would you have time for a quick call?\nBest Regards,\nLizi"),
  ("Purdue Zucrow: Prof. Timothée Pourpoint","reply on your 9/21 thread (timothee@purdue.edu)","first note 9/21, follow-up sent 10/8 (#3012). This is touch 3, so ask for a referral",
   "Hi Professor Pourpoint,\nI know this is a busy time of the semester, so I'll keep it short. If a recovered BLK3 flight in early 2027 isn't a fit for your group right now, could you point me to anyone at Zucrow whose work might be? I'd really appreciate it.\nBest Regards,\nLizi"),
  ("Aurora Engineering: Alex Barrie","abarrie@auroraengineering.com","only if you sent the 10/8 intro",
   "Hi Alex,\nJust following up on my note about testing Aurora's autonomy work on BLK3 in early 2027. Would a quick call be worthwhile?\nBest Regards,\nLizi"),
  ("Higher Orbits: Michelle Lucas","michelle@higherorbits.org (reply on thread) / LinkedIn linkedin.com/in/michellellucas","sent 10/8 (#1236); Go For Launch! Albuquerque is Nov 7-8",
   "Hi Michelle,\nJust following up on my note about a recovered BLK3 flight as another ride for Go For Launch! student experiments. Would a quick call work before your Albuquerque event in November?\nBest Regards,\nLizi"),
  ("ND Space Grant: Dr. Caitlin Milera","caitlin.milera@und.edu","sent 10/8 (#2038): funding a UND student flight via Space Grant / ND NASA EPSCoR",
   "Hi Dr. Milera,\nJust following up on my note about funding a UND student flight-test payload on BLK3 through Space Grant or ND NASA EPSCoR. Would a quick call work in the next couple of weeks?\nBest Regards,\nLizi"),
  ("UND: Jake Carstens","jacob.carstens@und.edu (reply on thread)","nudge sent 10/8 asking for an intro to Dr. David Delene",
   "Hi Jake,\nJust a gentle bump on the intro to Dr. Delene. No rush at all, and thanks again for your help!\nBest Regards,\nLizi"),
  ("K2 Space: Karan Kunjur","karan@k2space.com (reply on thread; note karan@k2.space bounced)","referral-partnership note sent 10/8 (#2005): BLK3 as a pre-orbital step for K2 hosted-payload customers",
   "Hi Karan,\nJust following up on my note about a referral partnership. A recovered BLK3 flight could give your hosted payload customers flight data on new hardware before they commit to an orbital slot. Would a 15-minute call work in the next couple of weeks?\nBest Regards,\nLizi")]}
today=date.today().isoformat()
items=DUE.get(today,[])
if items:
    lines=[f"■ {n}\n   To: {to}\n   Context: {why}\n   Draft nudge:\n\n{draft}\n" for n,to,why,draft in items]
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]=f"Follow-ups due today ({date.today():%a %m/%d})"
    m.set_content("Hi Lizi,\n\nThese are due for a follow-up today if they haven't replied. Each has the contact and a ready-to-send nudge (reply on your original thread so they see the history):\n\n"+"\n".join(lines)+
      "\n\nSkip anyone who already replied, and tell me in #lizi-channel-2 so I log it.\n\n- Exo")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
if today>="2026-10-22":
    p=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: os.remove(p)
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
