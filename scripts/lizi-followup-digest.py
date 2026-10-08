#!/usr/bin/env python3
"""Dated follow-up digest for Lizi (10/15, 10/20, 10/21, 10/22 at 09:00 CT). Emails only items due today whose
CRM contact hasn't been touched since the send. Self-unloads after 10/22."""
import os, json, subprocess, urllib.request
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-followup-digest"
DUE={
 "2026-10-14":[
  ("John Cothran: watch invoice #0075 (phone number needed)","cothranprp@gmail.com (reply on your earlier thread)","his invoice is ready except his phone number",
   "Hi John,\nJust following up on your watch order. I have everything I need for your invoice except a phone number. Could you send that over when you get a chance? Thank you!\nBest Regards,\nLizi"),
  ("PIEE / SPRS: post our CMMC score (task #2813)","https://piee.eb.mil","you registered 10/8; John approval requested (D-7282021). SpaceWERX needs the score posted by 10/21",
   "(No email.) 1) Log into PIEE. If the SPRS tile shows, you're approved. If not, ping John or Neil to approve your role. 2) Get our current NIST 800-171 / CMMC L2 self-assessment score and assessment date from Atomus. 3) In SPRS > Cyber Reports > NIST SP 800-171, enter it. Ask Exo in #lizi-channel-2 to walk through it.")],
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
   "Hi Karan,\nJust following up on my note about a referral partnership. A recovered BLK3 flight could give your hosted payload customers flight data on new hardware before they commit to an orbital slot. Would a 15-minute call work in the next couple of weeks?\nBest Regards,\nLizi"),
  ("BioServe: Stefanie Countryman","Stefanie.Countryman@colorado.edu (reply on your 10/8 thread)","10/8 you answered her pressurization/bay/ICD questions + sent the PUG (#1310); she has no current fit, so this is a light keep-warm touch",
   "Hi Stefanie,\nI wanted to check whether the Payload User Guide answered your questions about the bay. If any of your teams have hardware that could use a quick flight check before a longer mission, I'd be happy to set up a short call with our engineers.\nBest Regards,\nLizi"),
  ("Salish Kootenai College: Dean Matt Seeley","matt_seeley@skc.edu (reply on thread)","sent 10/8 (#3287): student/faculty research on BLK3, 1U from $7,500, Montana Space Grant funding angle",
   "Hi Dean Seeley,\nJust following up on my note about a BLK3 flight for SKC student or faculty research. I'd be happy to send over our university payload one-pager, or set up a quick call if that's easier. Is there anyone on your team I should connect with?\nBest Regards,\nLizi"),
  ("CWRU: Dr. Mohammad Kassemi (ZBOT cryo research)","mohammad.kassemi@case.edu (reply on thread)","sent 10/8 (D-7282012)",
   "Hello Dr. Kassemi,\nJust following up on my note about a recovered BLK3 flight as a complement to your ZBOT work. Would a short call in the next couple of weeks be useful?\nBest Regards,\nLizi"),
  ("Beyond Reach Labs: Mitchell Fogelson","founders@beyondreachlabs.io (reply on thread)","sent 10/8 (D-7282010): Flarewing fold-and-deploy test before their Q2 2027 orbital demo",
   "Hi Mitchell,\nJust following up on my note about a BLK3 flight test for a small Flarewing unit ahead of your 2027 demo. Would a quick call be worthwhile?\nBest Regards,\nLizi"),
  ("PoliTo: Roberta Fusaro (requirements feedback + admin paperwork)","roberta.fusaro@polito.it, cc paola.callegari@polito.it (reply on the PoliTOrbital thread)","10/8 you sent the challenge requirements v0.1 + design-in-Italy/build-in-US one-pager and asked for the admin templates + company-register paperwork (#3398, #3403). Skip if Paola already sent the paperwork or answered the PEC/signature questions",
   "Hi Roberta,\nI hope the team has had a chance to look over the challenge requirements and the build approach. We'd be happy to work through any questions or changes by email.\nAlso, just checking on the admin templates and company-register paperwork, and whether Paola had a chance to look at our PEC and digital signature questions on the letter. Once we have those, we'll get everything signed and sent.\nBest Regards,\nLizi"),
  ("UAH Propulsion Research Center: Dr. David Lineberry","david.lineberry@uah.edu (reply on thread)","sent 10/8 (#3019): microgravity propellant/fluids experiments on BLK3, offered call + Payload User Guide",
   "Hi Dr. Lineberry,\nJust following up on my note about flying a propellant or fluids experiment on BLK3 in early 2027. I've attached our Payload User Guide in case it's helpful, and I'd be happy to set up a quick call with our engineering team.\nBest Regards,\nLizi")]}
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
