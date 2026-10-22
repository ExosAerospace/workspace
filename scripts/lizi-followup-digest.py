#!/usr/bin/env python3
"""Dated follow-up digest for Lizi (10/14-11/04 dates at 09:00 CT). Emails only items due today whose
CRM contact hasn't been touched since the send. Self-unloads after 11/04."""
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
 '2026-10-19': [('ECA cert (task #2044, Request ID 57449): notarize + mail the form',
                 'WidePoint-ECA, 11250 Waples Mill Rd, South Tower Ste 210, Fairfax VA 22030 (tracked FedEx/UPS/USPS)',
                 'WidePoint must RECEIVE it by Thu 10/29 or the request is void. Skip if already mailed',
                 "(No email.) Packet: signed+notarized form, payment receipt, copies of driver's license + passport, John's wet-signed affiliation letter. Text Exo the tracking number."),
                ('Montana Tech: Dr. Bryce Hill',
                 'bhill@mtech.edu (reply on thread)',
                 'he replied 10/9: sharing BLK3 with the IEEE club and Robotics club',
                 'Hi Dr. Hill,\n'
                 "Thank you again for sharing BLK3 with your IEEE and Robotics clubs! I wanted to check in and see if either group had questions or interest. I've attached a one-page overview of how "
                 'flying a payload with us works, which might be easy to pass along, and I\'m happy to join a club meeting by video for 15 minutes to walk the students through how a flight works.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('University of Montana: Dr. Paul Lukacs (Interim VP Research)',
                 'paul.lukacs@umontana.edu (reply on thread)',
                 'he replied 10/9: coordinating with aligned faculty, will come back with questions',
                 'Hi Paul,\n'
                 "Thank you again for passing BLK3 along to your faculty. I wanted to check in and see if anyone has questions. I've attached a one-page overview they can look over, and I'm happy "
                 'to set up a short call with any interested researchers.\n'
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
 '2026-10-22': [('ECA cert (task #2044, Request ID 57449): notarize + mail the form',
                 'WidePoint-ECA, 11250 Waples Mill Rd, South Tower Ste 210, Fairfax VA 22030 (tracked FedEx/UPS/USPS)',
                 'LAST SAFE DAY to ship (must arrive by Thu 10/29). Skip if already mailed',
                 "(No email.) Packet: signed+notarized form, payment receipt, copies of driver's license + passport, John's wet-signed affiliation letter. Text Exo the tracking number."),
                ('FAA RFI 9736 comment: due Mon 10/26 (task #3410, Decision D-7282129)',
                 "John (he's back from Japan)",
                 "if John hasn't answered D-7282129 yet, mention it to him today. The deadline is Monday and Exo is ready to file the moment he says go. If it's already filed, ignore this",
                 "John, quick one: the FAA spaceport/corridor RFI comment is due Monday 10/26. Exo has the final version ready to file. Did you already file it, or should Exo submit it now? It's in "
                 'your Decisions.\n'
                 'Lizi'),
                ('MSU Spectrum Lab: Dr. Krishna Rupavatharam (Director)',
                 'krishna.rupavatharam@montana.edu (reply on thread)',
                 'you emailed 10/12; he replied same day: traveling, forwarding to his team to explore options',
                 'Hi Krishna,\n'
                 "Thank you again for passing BLK3 along to your team. I wanted to check in and see if anyone has questions or ideas they'd like to explore. I've attached a one-page overview they can look "
                 'over, and I\'m happy to set up a short call.\n'
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
                 "Just following up on my note about flying a propellant or fluids experiment on BLK3 in early 2027. I've attached a one-page overview in case it's helpful, and I'd be happy to "
                 'set up a quick call with our engineering team.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Rhodium Scientific: Olivia Gamez Holzhaus',
                 'LEO.Life@RhodiumScientific.com (reply on thread)',
                 'sent 10/8 (#3019/#3619)',
                 "Hi Olivia,\nJust following up on my note about a recovered BLK3 pre-flight for Rhodium's biotech payloads. Would a quick call make sense?\nBest Regards,\nLizi"),
                ('GT Space Week LinkedIn requests: Brad Henderson + Luis Zea (Starlab), Eric Lasker (Varda advisor)',
                 'LinkedIn (no public emails)',
                 'connection requests sent 10/15. For anyone who accepted, send a short message (ask Exo to adapt your GT email). Anyone still pending, just leave it',
                 'Hi [Name],\n'
                 "Thanks for connecting! It was great meeting you at Georgia Tech Space Week. I'd love to find a time to talk about whether a BLK3 suborbital flight could fit your work. Happy to "
                 "send over our Payload User's Guide as a first step.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Nature Smart (#2779): Stoke LinkedIn check: Devon Papandrew (VP BD) + John Taylor (Stoke media contact)',
                 'LinkedIn',
                 "if either accepted, ping Exo for the intro message, then loop Mike Mena back in. If neither, consider a quick 'any update on the founding group?' to Mike",
                 'Hi [Name],\n'
                 "Thanks for connecting! I'm with Exos Aerospace. We're part of a small founding group of clean-propellant launch companies (with Scorpius) called the Nature Smart Movement, and "
                 "Stoke's reusable LOX/hydrogen story is a natural fit. Would you be the right person to talk with about it, or could you point me to who is?\n"
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
                 "I hope the semester is going well. I wanted to circle back in case any of your faculty had questions about BLK3. If it's easier, I'm happy to send our one-page overview straight "
                 'to them, or set up a short call with anyone interested.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('JHU/APL SHELLGAME: Larry Paxton + Latoya Lambert (task #2694)',
                 'larry.paxton@jhuapl.edu, Latoya.Lambert@jhuapl.edu (reply on your 10/14 thread)',
                 'NDA fully executed 9/30; you asked for SHELLGAME flight needs 9/30 and followed up 10/14. Skip if Larry replied or booked',
                 'Hi Larry,\n'
                 "Just bumping this up in case it got buried. Even a rough idea of SHELLGAME's size, mass and power would help us hold a spot on an early 2027 BLK3 flight. Happy to work around your "
                 'schedule for a quick call.\n'
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
                 "Just following up on my note about flying D3PP or Araqys hardware on BLK3. If it would help, I'm happy to send over our one-page overview or set up a short call with our team.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Scentience: Kordel France resume for the Lead GN&C role (task #2957)',
                 "kordel@scentience.ai (reply on your 10/13 'payment received' thread)",
                 '10/13 you thanked him for the $4,000 deposit and asked for his resume. Skip if he already sent it (forward it to Exo so it goes to John)',
                 'Hi Kordel,\n'
                 "Just a quick follow-up on the GNC role. If you're still interested, I'd love to get your resume over to John. No rush, just didn't want it to slip through the cracks!\n"
                 'Best Regards,\n'
                 'Lizi')],
 '2026-10-29': [('Georgia Tech Space Week follow-ups (11 people, emailed 10/15)',
                 'reply on each original 10/15 thread: Thomas Orlando, Chris Carr, Binu Tharakan, Hailey Nichols (Locus Lock), Chad Pozarycki (Deleon, task #3793), Mike '
                 'Riccio (NASA Ames), David Williams (OSU/Starlab), Bill Dynan, Jordan McKaig, Vic Paulson',
                 'two weeks since your 10/15 follow-ups. Skip anyone who replied. Not included: Theo Williams and Henry Schwartz (already in conversation) and Carl Kirkconnell (on hold until SSLC '
                 "settles). Chunhui Xu replied 10/16 (call after Nov 6), so she's off this list. Phillip Stancil replied 10/18 (referred you to Dr. Mishra, nudge 11/2), so he's off too. Babbs Isarov (Qcells) replied 10/19 and got the PUG (nudge 11/2)",
                 'Hi [Name],\n'
                 "Just bumping this up in case it got buried after Space Week. I'd still love to find a time to talk about whether a BLK3 flight could fit your work. Happy to send our Payload User's "
                 "Guide if that's easier as a first step.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('SpaceTango: Twyman Clements (CEO, task #1001)',
                 'tclements@spacetango.com (reply on your "BLK3 + Space Tango" thread)',
                 'first note 9/14, nudge 10/15; no reply yet. Skip if he (or Danielle Rosales) replied. If still silent after this, try LinkedIn or ask John for a warm intro',
                 'Hi Twyman,\n'
                 "One last nudge on BLK3. If a call isn't convenient right now, I'm happy to just send over our one-page overview so you can share it with any PIs who might want a quick, "
                 'recoverable flight before an ISS mission. Who would be the best person on your team to talk with?\n'
                 'Best Regards,\n'
                 'Lizi')],
 # Montana Tech / Bryce Hill 11/2 nudge removed 10/21: he replied, clubs declined, he's booked.
 '2026-11-02': [('LinkedIn re-check: Kyle Acierno, Shawn Usman, Adam Escobar, Marshall Smith',
                 'LinkedIn (no email)',
                 'all 4 still pending on 10/21 (requests sent 10/6-10/8)',
                 '(No email.) Check again whether any accepted. For anyone who did, tell Exo in #lizi-channel-2 and it drafts the message. Anyone still pending after nearly 4 weeks, '
                 'just leave it. For Marshall (Starlab), Exo can line up Bradley Henderson (Starlab CCO) instead.'),
                ('Higher Orbits: Michelle Lucas (task #1236), touch 3 by TEXT',
                 'text her cell 281-451-5343 (she offered texting in Feb)',
                 'emails 10/8 + 10/22 unanswered; Go For Launch! Albuquerque is Nov 7-8. Warm contact, so switch channel instead of a 3rd email. Skip if she replied',
                 'Hi Michelle, it\'s Lizi with Exos! I sent a couple of emails about a recovered BLK3 flight as another ride for Go For Launch! student experiments. '
                 'I know this is a crazy week before Albuquerque. Would a quick call after the event work?'),
                ('NCAR ACOM: Dr. Eric Apel (task #2200)',
                 'apel@ucar.edu (reply on your 10/21 note)',
                 'you followed up 10/21 with the booking link + one-pager. Skip if he booked or replied',
                 'Hi Eric,\n'
                 "Just checking back on my note from last week. I'd still love to find a time for a quick Zoom with you and your colleague. Here's my booking link again, or send a couple "
                 "of times that work and I'll set it up.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Embry-Riddle: Siwei Fan (cryo gauging, pipeline #60)',
                 'FANS2@erau.edu (reply on your own thread)',
                 'last check-in: your 9/3 email (Space Grant ballpark + letter of support), then your 10/22 nudge. Skip if he replied',
                 'Hi Siwei,\n'
                 "One last check-in from me. If the Space Grant proposal or the payload build is still moving, we're glad to help with a fuller cost estimate or a letter of support whenever "
                 "you're ready. If the timing isn't right, no worries at all. Just let me know and I'll check back later.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('UGA Small Satellite Research Lab: Dr. Deepak Mishra (task #997)',
                 "dmishra@uga.edu (reply on your 10/19 thread, keep Phillip Stancil cc'd)",
                 'Stancil referred you 10/18; you sent Mishra the one-pager + booking link 10/19. Skip if he replied or booked',
                 'Hi Dr. Mishra,\n'
                 "Just following up on my note from a couple of weeks ago. I'd love to hear what your team is working on and whether a BLK3 flight could help test a sensor or onboard "
                 'processing before orbit. Would a quick 20-minute call work sometime in the next couple of weeks?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Qcells: Babbs (Mary Babb Isarov)',
                 'marybabb.isarov@qcells.com (reply on your "RE: Following up from Georgia Tech Space Week" thread)',
                 'she replied 10/19 asking about suborbital vs other profiles; you sent the Payload User Guide + booking link 10/19 and asked what solar tests/exposure Qcells has in mind. Skip if '
                 'she replied or booked',
                 'Hi Babbs,\n'
                 "Just checking in to see if you had a chance to look through the Payload User Guide. I'd love to hear what kinds of solar cell tests Qcells is thinking about, so I can point "
                 'you to the right flight profile. Would a quick call sometime in the next couple of weeks work?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Georgia Tech Quadrant-i: Jonathan Goldman + Penumbra Autonomy (task #997)',
                 'jongoldman@gatech.edu (reply-all on your "Re: Following up from Georgia Tech Space Week" thread so the Penumbra team stays cc\'d)',
                 "he replied 10/18, cc'd Penumbra Autonomy (prox-ops image processing) and asked about Reditus/Stef Crum; you replied 10/19 with the one-pager. Skip if Penumbra or Goldman replied",
                 'Hi Jonathan and Penumbra team,\n'
                 "Just following up on my note from a couple of weeks ago. I'd love to learn more about where Penumbra is with the image-processing pipeline and whether a BLK3 flight could fit "
                 'your validation plans. Would a quick 20-minute call work sometime in the next couple of weeks?\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Ohio State: Laura Alvarez, business partnerships (task #997)',
                 'alvarez.147@osu.edu (reply on your 10/19 note; cc williams.4219@osu.edu as on his thread)',
                 "Prof. David Williams cc'd her 10/17; you sent Laura the one-pager + booking link 10/19. Starlab intro (Henderson/Zea) still open. Skip if she replied or booked",
                 'Hi Laura,\n'
                 "Just following up on my note from a couple of weeks ago. I'd love to find a time to talk about how a BLK3 flight could support Ohio State's materials and microscopy "
                 'work. Would a quick 20-minute call work sometime in the next couple of weeks?\n'
                 'Best Regards,\n'
                 'Lizi')],
 '2026-11-04': [('UAH Propulsion Research Center: Dr. David Lineberry (task #3019), 3rd and last note',
                 'david.lineberry@uah.edu (reply on your "A flight test option for PRC hardware" thread)',
                 'first note 10/8, follow-up with the one-pager 10/22, no reply yet. This is message 3: if still quiet after it, pause and re-touch ~90 days later with real news. Skip if he or anyone at UAH replied',
                 'Hi Dr. Lineberry,\n'
                 "One last note in case the timing is better now. If a microgravity propellant or fluids test on BLK3 could help any of the PRC's projects, I'd be glad to set up "
                 "a short call with our engineering team. Here's my booking link if that's easier: "
                 "https://outlook.office365.us/bookwithme/user/abb76930b11b4c02a0d4eb449063a66b%40exosaero.com?anonymous&ismsaljsauthenabled\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('UC Irvine CubeSat: Sonia Cruze + Katie Lien',
                 'scruze@uci.edu, klien3@uci.edu (reply on your 10/12 recap thread)',
                 'sent recap + paperwork/payment overview 10/12; waiting on stowed vs ejected, data rate, antenna. Pushed from 10/22 (Lizi: they are good at reaching out). Only send if John has sent them the bay temperature data (#3711) and flight dates (#3712) and they still have not come back',
                 'Hi Sonia and Katie,\n'
                 'Checking in on the BLK3 decisions from our recap: stowed vs. ejected, your telemetry data rate and protocol, and the external antenna. Once we have those, we can put the formal '
                 'quote together. Happy to jump on a quick call if it helps the team decide.\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('NewOrbit Space: press team, for CEO Anatolii Papulov (task #3937)',
                 'press@neworbit.space (reply on your "A flight check for NewOrbit hardware ahead of NEO-1" thread)',
                 "first note 10/21 asking them to pass it to Anatolii or their engineering lead, no reply yet. If still quiet after this, Exo suggests reaching Anatolii on LinkedIn. Skip if anyone at NewOrbit replied",
                 'Hello,\n'
                 "Just following up on my note from a couple of weeks ago. If you were able to pass it along to Anatolii or your engineering team, I'd love to "
                 "set up a short call about a BLK3 flight check for the AURA hardware. Here's my booking link if that's easier: "
                 "https://outlook.office365.us/bookwithme/user/abb76930b11b4c02a0d4eb449063a66b%40exosaero.com?anonymous&ismsaljsauthenabled\n"
                 'Thank you!\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('Array Labs: Ryan Duffy, Head of BD (task #3938)',
                 'ryan@arraylabs.io (reply on your "Flight data for Array Labs hardware before the cluster launch" thread)',
                 "first note 10/21 with the one-pager + booking link, no reply yet. Defense-adjacent: keep it marketing-level, no specs. Skip if Ryan or anyone at Array Labs replied",
                 'Hi Ryan,\n'
                 "Just following up on my note from a couple of weeks ago. I'd love to set up a short call with our engineering team to see whether a BLK3 flight "
                 "could fit Array Labs' hardware testing ahead of the cluster launch. Here's my booking link if that's easier: "
                 "https://outlook.office365.us/bookwithme/user/abb76930b11b4c02a0d4eb449063a66b%40exosaero.com?anonymous&ismsaljsauthenabled\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('UF Space Plants Lab: Dr. Rob Ferl (task #3935)',
                 'robferl@ufl.edu (reply on your "A recoverable suborbital flight option for the Space Plants Lab" thread)',
                 "first note 10/21 with the one-pager + booking link (mentioned Dr. Anna-Lisa Paul), no reply yet. Skip if he, Dr. Paul, or anyone at UF replied",
                 'Hi Dr. Ferl,\n'
                 "Just following up on my note from a couple of weeks ago. I'd love to set up a short call with you and Dr. Paul about whether a BLK3 flight could fit "
                 "the lab's next round of plant gene-expression work. Here's my booking link if that's easier: "
                 "https://outlook.office365.us/bookwithme/user/abb76930b11b4c02a0d4eb449063a66b%40exosaero.com?anonymous&ismsaljsauthenabled\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Scout Space: Jessica Jones, PR (task #3936)',
                 'pr@scout.space (reply on your "A flight check for Scout\'s sensor hardware before the constellation deployment" thread)',
                 "first note 10/21 asking her to pass it to Josiah Gruber or their engineering lead, no reply yet. Skip if she or anyone at Scout replied",
                 'Hi Jessica,\n'
                 "Just following up on my note from a couple of weeks ago. If you were able to pass it along to Josiah or your engineering team, I'd love to "
                 "set up a short call about a BLK3 flight check for Scout's sensor hardware. Here's my booking link if that's easier: "
                 "https://outlook.office365.us/bookwithme/user/abb76930b11b4c02a0d4eb449063a66b%40exosaero.com?anonymous&ismsaljsauthenabled\n"
                 'Thank you!\n'
                 'Best Regards,\n'
                 'Lizi'),
                ('UCLA: Prof. Chee Wei Wong (task #1300)',
                 'cheewei.wong@ucla.edu (reply on your "Flight Testing for Your Optomechanical Inertial Sensor" thread)',
                 'first note 10/7, nudge 10/21, no reply yet. This is the last check-in. If he stays quiet, Exo moves him to a quarterly touch. Skip if he replied',
                 'Hi Professor Wong,\n'
                 "One last check-in on a BLK3 flight for your optomechanical inertial sensor. If the timing isn't right yet, no problem at all. Just let me know when your team is "
                 "planning the next test after the balloon flight and I'll circle back then.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Magma Space: Alessandro Stabile (task #2307)',
                 'LinkedIn message to Alessandro Stabile (NOT the outreach@ inbox: both emails went to a generic address and may never have reached him)',
                 'emails 10/7 + 10/21 to outreach@, no reply. 3-message rule: try a different channel before pausing. If no reply on LinkedIn, Exo moves Magma to a 90-day re-touch (2/3). Skip if they replied',
                 'Hi Alessandro,\n'
                 "I sent a couple of notes to Magma's outreach inbox about flying your maglev reaction wheel on BLK3 and wanted to make sure they reached you. "
                 "If a recovered suborbital test flight could be useful, I'd be glad to set up a short call with our engineering team.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('Axiom: Dr. Chyree Batton (task #2031)',
                 'Chyree@axiomspace.com (reply on your "Re: Exos BLK3 Payload User Guide - great connecting today" thread)',
                 'call 8/18, notes 10/7 + 10/21, no reply yet. This is the last check-in. If there is no reply, Exo moves Axiom to a quarterly touch. Skip if Chyree replied',
                 'Hi Chyree,\n'
                 "One last check-in on a recovered BLK3 test flight for your battery and vacuum qualification work. If the timing isn't right yet, no problem at all. Just let me know "
                 "when your team is planning that qualification round and I'll circle back then.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('MSU Spectrum Lab: Dr. Krishna Rupavatharam (Director)',
                 'krishna.rupavatharam@montana.edu (reply on your "Flight Testing Opportunities for Spectrum Lab" thread)',
                 'first note 10/12 (he replied: traveling, forwarding to his team), check-in + one-pager 10/22, no reply yet. Warm contact, so this asks for a name on his team instead of another nudge. If still quiet, Exo moves Spectrum Lab to the 90-day re-touch (2/3). Skip if he or anyone at Spectrum Lab replied',
                 'Hi Krishna,\n'
                 "I know you're busy, so I'll keep this short. Is there someone on your team I should reach out to directly about a BLK3 flight test? "
                 "I'd be glad to send them the one-pager and set up a short call.\n"
                 'Best Regards,\n'
                 'Lizi'),
                ('MSU BOREALIS: Dr. Angela Des Jardins (task #3287)',
                 'angela.desjardins@montana.edu, cc amy.brown11@montana.edu (reply on your "A next step for BOREALIS student payloads" thread)',
                 'first note 10/8, follow-up + one-pager 10/22, no reply yet. This is the last check-in. If she stays quiet, Exo moves BOREALIS to the 90-day re-touch (2/3). Skip if she or anyone at MSU BOREALIS replied',
                 'Hi Angela,\n'
                 "One last check-in on BLK3 as a next step for your BOREALIS teams. If the timing isn't right this year, no problem at all. Just let me know when "
                 "your students start planning their next payloads and I'll circle back then.\n"
                 'Best Regards,\n'
                 'Lizi')],
 '2027-02-03': [('90-day re-touch: paused contacts (3 messages, no reply)',
                 'UCLA Prof. Chee Wei Wong, Axiom Dr. Chyree Batton, Magma Alessandro Stabile, plus any of 11/4\'s sends that went quiet. Also JHU/APL Josh Wolk: he replied 10/22 (interested in avionics risk-reduction/prototype testing, nothing funded yet, will reach out), so send him a news-only note, no ask',
                 "These were paused under your 3-message rule. A re-touch is a NEW message with real news (flight date, test results, new capability), not another nudge. Skip anyone who replied. "
                 "Tell Exo in #lizi-channel-2 and it will draft each one with the latest BLK3 news",
                 '(Exo drafts these fresh on request with current news; no stale template.)')]}

# ── OUTPUT eval (exo3 R5): `lizi-followup-digest.py selftest` ── read-only; sends nothing.
# Every DUE date must have a launchd trigger (on-disk plist AND the loaded definition), every item
# is a complete (name, to, why, draft) entry, no item repeats within a day, the digest goes to Lizi only.
def selftest():
    import plistlib, re as _re, sys as _sys
    fails=[]
    def chk(name, ok):
        print(("PASS " if ok else "FAIL ")+name)
        if not ok: fails.append(name)
    keys=sorted(DUE)
    okd=all(_re.fullmatch(r"\d{4}-\d{2}-\d{2}",k) for k in keys)
    chk(f"DUE has {len(keys)} valid ISO dates", okd and bool(keys))
    bad=[(k,i) for k in keys for i,it in enumerate(DUE[k]) if len(it)!=4 or not all(isinstance(x,str) and x.strip() for x in it)]
    chk("every item is a complete (name, to, context, draft) entry"+(f" -> {bad[:5]}" if bad else ""), not bad)
    dup=[k for k in keys if len({it[0] for it in DUE[k]})!=len(DUE[k])]
    chk("no item listed twice on the same day"+(f" -> {dup}" if dup else ""), not dup)
    want={(int(k[5:7]),int(k[8:10])) for k in keys}
    pl=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    if os.path.exists(pl):
        cal=plistlib.load(open(pl,"rb")).get("StartCalendarInterval") or []
        cal=cal if isinstance(cal,list) else [cal]
        have={(c.get("Month"),c.get("Day")) for c in cal}
        inval=[c for c in cal if not (1<=int(c.get("Day") or 0)<=31 and 1<=int(c.get("Month") or 0)<=12)]
        miss=sorted(want-have)
        chk("on-disk plist: every DUE date has a valid trigger"+(f" -> missing {miss}" if miss else "")+(f" invalid {inval}" if inval else ""), not miss and not inval)
        lp=subprocess.run(["launchctl","print",f"gui/{os.getuid()}/{LABEL}"],capture_output=True,text=True)
        if lp.returncode==0:
            live=set()
            for blk in _re.findall(r"descriptor = \{(.*?)\}", lp.stdout, _re.S):
                m=_re.search(r'"Month" => (\d+)',blk); d=_re.search(r'"Day" => (\d+)',blk)
                if m and d: live.add((int(m.group(1)),int(d.group(1))))
            lmiss=sorted(want-live)
            chk("loaded launchd job: every DUE date has a trigger"+(f" -> missing {lmiss} (plist fixed on disk? needs a reload)" if lmiss else ""), not lmiss)
    elif date.today().isoformat()<max(keys):
        chk("plist present while DUE dates remain", False)
    chk("digest recipient is Lizi only (internal)", 'msmtp","-a","protonmail","lquinn@exosaero.com"]' in open(__file__).read())
    print(f"lizi-followup-digest selftest: {'PASS' if not fails else 'FAIL'} ({len(fails)} failure(s))")
    _sys.exit(0 if not fails else 1)
import sys as _sys0
if _sys0.argv[1:2]==["selftest"]:
    selftest()
today=date.today().isoformat()
items=DUE.get(today,[])
if items:
    lines=[f"■ {n}\n   To: {to}\n   Context: {why}\n   Draft nudge:\n\n{draft}\n" for n,to,why,draft in items]
    m=EmailMessage(); m["From"]="Exo <jquinnexo@pm.me>"; m["To"]="lquinn@exosaero.com"; m["X-Exo-No-Task"]="1"
    m["Subject"]=f"Follow-ups due today ({date.today():%a %m/%d})"
    m.set_content("Hi Lizi,\n\nThese are due for a follow-up today if they haven't replied. Each has the contact and a ready-to-send nudge (reply on your original thread so they see the history):\n\n"+"\n".join(lines)+
      "\n\nSkip anyone who already replied, and tell me in #lizi-channel-2 so I log it.\n\n- Exo")
    subprocess.run(["/opt/homebrew/bin/msmtp","-a","protonmail","lquinn@exosaero.com"],input=m.as_bytes(),check=True,timeout=60)
if today>="2027-02-03":
    p=os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: os.remove(p)
    except Exception: pass
    subprocess.run(["launchctl","bootout",f"gui/{os.getuid()}/{LABEL}"],capture_output=True)
