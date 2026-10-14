#!/usr/bin/env python3
"""Dated follow-up digest for Lizi (10/14-10/26 dates at 09:00 CT). Emails only items due today whose
CRM contact hasn't been touched since the send. Self-unloads after 10/26."""
import os, json, subprocess, urllib.request
from datetime import date
from email.message import EmailMessage
LABEL="com.exos.lizi-followup-digest"
DUE={'2026-10-14': [('VSFB Mission Development Zone whitepaper (task #3699/#3701)',
                 'John submits (D-7282079)',
                 'due Fri 10/16 4:00 PM PT',
                 "(No email.) Nothing for you unless John can't upload from Japan. He has the SAFE email and uploads the final whitepaper himself. If he asks you to step in, tell Exo and it will "
                 'hand you the final PDF + confirmation email.'),
                ('John Cothran: watch invoice #0075 (phone number needed)',
                 'cothranprp@gmail.com (reply on your earlier thread)',
                 'his invoice is ready except his phone number',
                 'Hi John,\n'
                 'Just following up on your watch order. I have everything I need for your invoice except a phone number. Could you send that over when you get a chance? Thank you!\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('PIEE / SPRS: confirm our 110/110 score is posted + affirmed (task #2813)',
                 'https://piee.eb.mil',
                 'you registered 10/8; John approval requested (D-7282021). SpaceWERX needs the score posted by 10/21',
                 "(No email.) 1) Log into PIEE. If the SPRS tile shows, you're approved. If not, ping John or Neil to approve your role. 2) In SPRS, confirm the 110/110 CMMC L2 (Self) entry John "
                 "posted 8/31 is there AND shows as affirmed. 3) If it isn't affirmed, ping John to click Affirm. Ask Exo in #lizi-channel-2 to walk through it.")],
 '2026-10-15': [('ECA (MLOA) certificate, task #2044: finish the WidePoint application',
                 'eca.orc.com (Firefox on the Mac mini)',
                 "Exos is now in WidePoint's org list (10/14); block ~30 uninterrupted minutes",
                 '(No email.) Firefox > eca.orc.com > Buy Now > Medium Assurance Identity and Encryption > DIB Cyber Incident Reporting > 3 Years (Browser) > org CAGE 7EMY6 > your info > pay $354 '
                 "(company card, save receipt) > SAVE the key password > download the forms but DON'T sign until ready to notarize + mail (30-day clock). Ping Exo in #lizi-channel-2 with "
                 'screenshots.'),
                ('SpaceTango: Danielle Rosales',
                 'reply on your 10/5 thread',
                 'emailed 10/5 (#1001)',
                 'Hi Danielle,\n'
                 "Just checking in on my note from last week about BLK3. We're booking payloads for early 2027 flights, and I'd love to find a time to talk about how we might work together for your "
                 'customers. Would a quick call work?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Watch follow-up to the 531-investor list (task #3408)',
                 'the same investor list (via David or your send list), after the website post from the 10/14 weekly is live',
                 'first email went ~10/1; 3 reserved so far',
                 'Hi [Name],\n'
                 'Quick follow-up on the BLK3 Edition space-flown watch: only 6 of the 10 set aside for Exos investors are left (check current count before sending) at $675, with delivery after the '
                 "early 2027 flight. Each one comes with a certificate of flight. You can read more in this week's investor update [link to website post]. If you'd like one, just reply and I'll get "
                 'you set up!\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('David Mitchell: Nov 7 investor notice',
                 'reply on your Teams-link email to David',
                 'you sent him the Teams link 10/8; notice must go out by ~10/23 (15-day bylaw) / 10/28 (Texas 10-day min)',
                 'Hi David,\nJust checking that the Nov 7 investor meeting notice went out with the Teams link and the record date. Anything you need from me?\nBest Regards,\nLizi')],
 '2026-10-19': [('Montana Tech: Dr. Bryce Hill',
                 'bhill@mtech.edu (reply on thread)',
                 'he replied 10/9: sharing BLK3 with the IEEE club and Robotics club',
                 'Hi Dr. Hill,\n'
                 "Thank you again for sharing BLK3 with your IEEE and Robotics clubs! I wanted to check in and see if either group had questions or interest. I'm happy to join a club meeting by "
                 'video for 15 minutes to walk the students through how a flight works, and to send over our Payload User Guide.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('University of Montana: Dr. Paul Lukacs (Interim VP Research)',
                 'paul.lukacs@umontana.edu (reply on thread)',
                 'he replied 10/9: coordinating with aligned faculty, will come back with questions',
                 'Hi Paul,\n'
                 "Thank you again for passing BLK3 along to your faculty. I wanted to check in and see if anyone has questions. I'm happy to set up a short call with interested researchers, or send "
                 'over our Payload User Guide so they can see what fits.\n'
                 'Best Regards,\n'
                 'Lizi')],
 '2026-10-20': [('LinkedIn check: pending connection requests',
                 'LinkedIn (no email)',
                 'requests sent 10/6-10/8; Olivia Borgue accepted 10/13',
                 '(No email.) Check whether these accepted: Kyle Acierno (Exobiosphere CEO) https://www.linkedin.com/in/kyleacierno ; Shawn Usman (Rhea) '
                 'https://www.linkedin.com/in/shawn-usman-8b4169169 ; Adam Escobar (Space Lab Tech) https://www.linkedin.com/in/adam-escobar-6a2a08171 ; Marshall Smith (Starlab) '
                 'https://www.linkedin.com/in/marshall-smith4 . For anyone who accepted, tell Exo in #lizi-channel-2 and it drafts the message. Still nothing from Marshall? Exo can line up Bradley '
                 'Henderson (Starlab CCO) instead.'),
                ('NCAR ACOM: Dr. Eric Apel + colleague (task #2200)',
                 'apel@ucar.edu (reply on your 10/13 thread)',
                 '10/13 you sent the Payload User Guide + booking link for a Zoom. Skip if they already booked',
                 'Hi Eric,\n'
                 "I just wanted to check whether you and your colleague had a chance to look over the Payload User Guide. I'd love to find a time for that Zoom. Here's my booking link again, or just "
                 "send a couple of times that work for you both and I'll get it set up. I'm happy to bring someone from our technical team along too.\n"
                 'Best Regards,\n'
                 'Lizi')],
 '2026-10-21': [('Axiom: Chyree Batton',
                 'Chyree@axiomspace.com (reply on thread)',
                 'sent 10/7',
                 'Hi Chyree,\n'
                 'Just following up on my note about a recovered BLK3 test flight for your battery and vacuum qualification work. Happy to set up a short technical call whenever works for your '
                 'team.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('JHU/APL: Josh Wolk',
                 'joshua.wolk@jhuapl.edu (reply on thread)',
                 'follow-up sent 10/7',
                 'Hi Josh,\n'
                 "Just circling back on my note from earlier this month. If you can share a bit about the payloads you're working on, I'd love to set up a short call with our engineering team. We "
                 'can put an NDA in place first if needed.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Magma Space: Alessandro Stabile',
                 'outreach@magma-space.com',
                 'sent 10/7 (#2307)',
                 "Hi Alessandro,\nFollowing up on my note about flying your maglev reaction wheel on BLK3 in early 2027. Would a quick call be helpful to see if it's a fit?\nBest Regards,\nLizi"),
                ('UCLA: Prof. Chee Wei Wong',
                 'cheewei.wong@ucla.edu',
                 'sent 10/7',
                 'Hi Professor Wong,\n'
                 'Just following up on my note about a BLK3 rocket flight as a next step after your balloon test. Happy to set up a short call whenever works for you.\n'
                 'Best Regards,\n'
                 'Lizi')],
 '2026-10-22': [('MSU Spectrum Lab: Dr. Krishna Rupavatharam (Director)',
                 'krishna.rupavatharam@montana.edu (reply on thread)',
                 'you emailed 10/12; he replied same day: traveling, forwarding to his team to explore options',
                 'Hi Krishna,\n'
                 "Thank you again for passing BLK3 along to your team. I wanted to check in and see if anyone has questions or ideas they'd like to explore. I'm happy to set up a short call or send "
                 'over our Payload User Guide so they can see what fits.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('UC Irvine CubeSat: Sonia Cruze + Katie Lien',
                 'scruze@uci.edu, klien3@uci.edu (reply on your 10/12 recap thread)',
                 'sent recap + paperwork/payment overview 10/12; waiting on stowed vs ejected, data rate, antenna',
                 'Hi Sonia and Katie,\n'
                 'Checking in on the BLK3 decisions from our recap: stowed vs. ejected, your telemetry data rate and protocol, and the external antenna. Once we have those, we can put the formal '
                 'quote together. Happy to jump on a quick call if it helps the team decide.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Rhea Space Activity: Shawn Usman (Founder & CEO)',
                 "shawn.usman@rheaspaceactivity.com (best-guess address; check it didn't bounce) + LinkedIn",
                 'emailed 10/9 + LinkedIn request 10/7',
                 'Dr. Usman,\n'
                 'Following up on my note about flying AutoNav hardware on BLK3 in early 2027. Since the flight is recovered, your team gets the hardware and data back to work with directly. Would a '
                 'short call in the next couple of weeks work?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Montana Space Grant: Angela Des Jardins',
                 'angela.desjardins@montana.edu, cc amy.brown11@montana.edu',
                 'sent 10/8 (#3287)',
                 'Hi Angela,\nJust following up on my note about BLK3 as a next step for BOREALIS student payloads. Would a short call work in the next couple of weeks?\nBest Regards,\nLizi'),
                ('Carthage: Kevin Crosby',
                 'reply on your 10/8 thread',
                 'sent 10/8',
                 'Hi Professor Crosby,\nJust following up on my note about a possible BLK3 follow-on flight for your ullage trapping work. Would you have time for a quick call?\nBest Regards,\nLizi'),
                ('Purdue Zucrow: Prof. Timothée Pourpoint',
                 'reply on your 9/21 thread (timothee@purdue.edu)',
                 'first note 9/21, follow-up sent 10/8 (#3012). This is touch 3, so ask for a referral',
                 'Hi Professor Pourpoint,\n'
                 "I know this is a busy time of the semester, so I'll keep it short. If a recovered BLK3 flight in early 2027 isn't a fit for your group right now, could you point me to anyone at "
                 "Zucrow whose work might be? I'd really appreciate it.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Aurora Engineering: Alex Barrie',
                 'abarrie@auroraengineering.com',
                 'only if you sent the 10/8 intro',
                 "Hi Alex,\nJust following up on my note about testing Aurora's autonomy work on BLK3 in early 2027. Would a quick call be worthwhile?\nBest Regards,\nLizi"),
                ('Higher Orbits: Michelle Lucas',
                 'michelle@higherorbits.org (reply on thread)',
                 'emailed 10/8 (#1236), no LinkedIn request; Go For Launch! Albuquerque is Nov 7-8',
                 'Hi Michelle,\n'
                 'Just following up on my note about a recovered BLK3 flight as another ride for Go For Launch! student experiments. Would a quick call work before your Albuquerque event in '
                 'November?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('ND Space Grant: Dr. Caitlin Milera',
                 'caitlin.milera@und.edu',
                 'sent 10/8 (#2038): funding a UND student flight via Space Grant / ND NASA EPSCoR',
                 'Hi Dr. Milera,\n'
                 'Just following up on my note about funding a UND student flight-test payload on BLK3 through Space Grant or ND NASA EPSCoR. Would a quick call work in the next couple of weeks?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('UND: Jake Carstens',
                 'jacob.carstens@und.edu (reply on thread)',
                 'nudge sent 10/8 asking for an intro to Dr. David Delene',
                 'Hi Jake,\nJust a gentle bump on the intro to Dr. Delene. No rush at all, and thanks again for your help!\nBest Regards,\nLizi'),
                ('K2 Space: Karan Kunjur',
                 'karan@k2space.com (reply on thread; note karan@k2.space bounced)',
                 'referral-partnership note sent 10/8 (#2005): BLK3 as a pre-orbital step for K2 hosted-payload customers',
                 'Hi Karan,\n'
                 'Just following up on my note about a referral partnership. A recovered BLK3 flight could give your hosted payload customers flight data on new hardware before they commit to an '
                 'orbital slot. Would a 15-minute call work in the next couple of weeks?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('BioServe: Stefanie Countryman',
                 'Stefanie.Countryman@colorado.edu (reply on your 10/8 thread)',
                 '10/8 you answered her pressurization/bay/ICD questions + sent the PUG (#1310); she has no current fit, so this is a light keep-warm touch',
                 'Hi Stefanie,\n'
                 'I wanted to check whether the Payload User Guide answered your questions about the bay. If any of your teams have hardware that could use a quick flight check before a longer '
                 "mission, I'd be happy to set up a short call with our engineers.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Salish Kootenai College: Dean Matt Seeley',
                 'matt_seeley@skc.edu (reply on thread)',
                 'sent 10/8 (#3287): student/faculty research on BLK3, 1U from $7,500, Montana Space Grant funding angle',
                 'Hi Dean Seeley,\n'
                 "Just following up on my note about a BLK3 flight for SKC student or faculty research. I'd be happy to send over our university payload one-pager, or set up a quick call if that's "
                 'easier. Is there anyone on your team I should connect with?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('CWRU: Dr. Mohammad Kassemi (ZBOT cryo research)',
                 'mohammad.kassemi@case.edu (reply on thread)',
                 'sent 10/8 (D-7282012)',
                 'Hello Dr. Kassemi,\n'
                 'Just following up on my note about a recovered BLK3 flight as a complement to your ZBOT work. Would a short call in the next couple of weeks be useful?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Beyond Reach Labs: Mitchell Fogelson',
                 'founders@beyondreachlabs.io (reply on thread)',
                 'sent 10/8 (D-7282010): Flarewing fold-and-deploy test before their Q2 2027 orbital demo',
                 'Hi Mitchell,\nJust following up on my note about a BLK3 flight test for a small Flarewing unit ahead of your 2027 demo. Would a quick call be worthwhile?\nBest Regards,\nLizi'),
                ('PoliTo: Roberta Fusaro (requirements feedback + admin paperwork)',
                 'roberta.fusaro@polito.it, cc paola.callegari@polito.it (reply on the PoliTOrbital thread)',
                 '10/8 you sent the challenge requirements v0.1 + design-in-Italy/build-in-US one-pager and asked for the admin templates + company-register paperwork (#3398, #3403). Skip if Paola '
                 'already sent the paperwork or answered the PEC/signature questions',
                 'Hi Roberta,\n'
                 "I hope the team has had a chance to look over the challenge requirements and the build approach. We'd be happy to work through any questions or changes by email.\n"
                 'Also, just checking on the admin templates and company-register paperwork, and whether Paola had a chance to look at our PEC and digital signature questions on the letter. Once we '
                 "have those, we'll get everything signed and sent.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('UAH Propulsion Research Center: Dr. David Lineberry',
                 'david.lineberry@uah.edu (reply on thread)',
                 'sent 10/8 (#3019): microgravity propellant/fluids experiments on BLK3, offered call + Payload User Guide',
                 'Hi Dr. Lineberry,\n'
                 "Just following up on my note about flying a propellant or fluids experiment on BLK3 in early 2027. I've attached our Payload User Guide in case it's helpful, and I'd be happy to "
                 'set up a quick call with our engineering team.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('UAH Propulsion Research Center: Dr. David Lineberry',
                 'david.lineberry@uah.edu (reply on thread)',
                 'sent 10/8 (#3019)',
                 'Hi Dr. Lineberry,\nJust following up on my note about a recovered BLK3 flight for Propulsion Research Center work. Would a quick call be useful?\nBest Regards,\nLizi'),
                ('Rhodium Scientific: Olivia Gamez Holzhaus',
                 'LEO.Life@RhodiumScientific.com (reply on thread)',
                 'sent 10/8 (#3019/#3619)',
                 "Hi Olivia,\nJust following up on my note about a recovered BLK3 pre-flight for Rhodium's biotech payloads. Would a quick call make sense?\nBest Regards,\nLizi"),
                ('Salish Kootenai College: Matt Seeley (cc Lee Slater)',
                 'matt_seeley@skc.edu (reply on thread)',
                 'sent 10/8',
                 'Hi Dean Seeley,\nJust following up on my note about a BLK3 flight for SKC students or faculty in early 2027. Would a quick call be useful?\nBest Regards,\nLizi')],
 '2026-10-26': [('UTD AIAA / Comet Rocketry: Mi Vo + Olivia Johnson (task #2753)',
                 'mi.vo@utdallas.edu + Olivia (reply on your 10/12 check-in thread, cc Phil + Don Proeschel)',
                 '10/12 you asked for early experiment ideas + shop-tour dates/headcount; design coordination + slot payment due mid-Dec',
                 'Hi Mi and Olivia,\n'
                 'Just checking in on the BLK3 experiment. Even a rough idea is a great starting point, and Phil and I are happy to hop on a short call to help shape it. If you have a couple of '
                 "dates and a headcount for the Greenville shop tour, send them over and we'll get it on the calendar. Mid-December will come up fast, so it would be great to get a concept going "
                 'soon.\n'
                 'Best Regards,\n'
                 'Lizi')],
 '2026-10-27': [('GSA Orlando trip (task #3780): re-check Southwest fares',
                 'southwest.com',
                 'you planned to wait ~2 weeks for the next SWA fare sale before booking',
                 '(No email.) Re-price: out Fri 1/8 DAL->MCO 8:00a #1271 (was $174 Choice) and back Fri 1/15 MCO->DAL 8:15a #1722 (was $174 Choice), 3 travelers. If lower, book and tell Exo the '
                 'confirmation; it updates #3780.'),
                ('University of Montana: Dr. Paul Lukacs (Interim VP Research, task #3659)',
                 'paul.lukacs@umontana.edu (reply on thread)',
                 'he replied 10/9 (passing to faculty); you followed up 10/14 offering a call or the PUG. Skip if he or a faculty member replied',
                 'Hi Paul,\n'
                 "I hope the semester is going well. I wanted to circle back in case any of your faculty had questions about BLK3. If it's easier, I'm happy to send the Payload User Guide straight "
                 'to them, or set up a short call with anyone interested.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('JHU/APL SHELLGAME: Larry Paxton + Latoya Lambert (task #2694), escalate via Josh Wolk',
                 'larry.paxton@jhuapl.edu, Latoya.Lambert@jhuapl.edu (reply on your 10/14 thread) + joshua.wolk@jhuapl.edu (separate note)',
                 'NDA fully executed 9/30; you asked for SHELLGAME flight needs 9/30 and followed up 10/14. Skip if Larry replied or booked',
                 'To Larry + Latoya (same thread):\n'
                 'Hi Larry,\n'
                 "Just bumping this up in case it got buried. Even a rough idea of SHELLGAME's size, mass and power would help us hold a spot on an early 2027 BLK3 flight. Happy to work around your "
                 'schedule for a quick call.\n'
                 'Best Regards,\n'
                 'Lizi\n'
                 '\n'
                 'To Josh Wolk (separate note):\n'
                 'Hi Josh,\n'
                 "Quick favor: we have an NDA in place with APL for Larry Paxton's SHELLGAME work and I've reached out a couple of times about a BLK3 flight. If you cross paths with Larry, would you "
                 "mind mentioning it? I'd really appreciate it.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Chief Dull Knife College: Jim Bertin',
                 'jbertin@cdkc.edu (reply on your 10/13 thread)',
                 "you emailed 10/13 (#3742); he's also the Montana Space Grant campus rep",
                 'Hello Jim,\n'
                 "Just following up on my note about a BLK3 payload for your students in early 2027. If it would help, I'm happy to send our Payload User's Guide or find a time for a quick call.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Dcubed: Dr. Thomas Sinn',
                 'thomas.sinn@dcubed-space.com (reply on your 10/13 thread)',
                 'you emailed 10/13 about D3PP/Araqys on BLK3, early 2027 (#3738)',
                 'Hello Dr. Sinn,\n'
                 "Just following up on my note about flying D3PP or Araqys hardware on BLK3. If it would help, I'm happy to send over our Payload User Guide or set up a short call with our team.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Scentience: Kordel France resume for the Lead GN&C role (task #2957)',
                 "kordel@scentience.ai (reply on your 10/13 'payment received' thread)",
                 '10/13 you thanked him for the $4,000 deposit and asked for his resume. Skip if he already sent it (forward it to Exo so it goes to John)',
                 'Hi Kordel,\n'
                 "Just a quick follow-up on the GNC role. If you're still interested, I'd love to get your resume over to John. No rush, just didn't want it to slip through the cracks!\n"
                 'Best Regards,\n'
                 'Lizi')]}
today=date.today().isoformat()
items=DUE.get(today,[])
if items:
    lines=[f"■ {n}\n   To: {to}\n   Context: {why}\n   Draft nudge:\n\n{draft}\n" for n,to,why,draft in items]
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]=f"Follow-ups due today ({date.today():%a %m/%d})"
    m.set_content("Hi Lizi,\n\nThese are due for a follow-up today if they haven't replied. Each has the contact and a ready-to-send nudge (reply on your original thread so they see the history):\n\n"+"\n".join(lines)+
      "\n\nSkip anyone who already replied, and tell me in #lizi-channel-2 so I log it.\n\n- Exo")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
if today>="2026-10-27":
    p=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: os.remove(p)
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
