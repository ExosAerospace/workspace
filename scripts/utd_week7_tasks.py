#!/usr/bin/env python3
"""Create UTD Team Atlas Week 7 weekly tasks (meeting 10/15 -> 10/22). Run once, after Lizi OKs."""
import sys; sys.path.insert(0, '/Users/exomac/.openclaw/workspace/scripts')
import capstone_capture as cc
EM = {"Roel Saenz":"RCS220001@utdallas.edu","Laura Granados Lopez":"LEG240001@utdallas.edu",
      "Karan Vijaya Sankar":"KXV220043@utdallas.edu","Adrian Haro":"AXH230026@utdallas.edu",
      "Brenda Segovia Saldana":"BXS230052@utdallas.edu","Sunidhi Mathew":"SXM220350@utdallas.edu"}
T = [
 ("Roel Saenz","2026-10-16","[Week 7 · Lead] Minutes from Thu 10/15 within 24 hrs; agenda for Thu 10/22 by Tue 10/20",
  "1. Send the 10/15 minutes to Lizi by Fri 10/16 (decisions, action items, owners, dates).\n2. Send the 10/22 agenda by Tue 10/20.\n3. Post both as notes on this card."),
 ("Roel Saenz","2026-10-22","[Week 7 · Lead] Finish Hermeus #3480, Castelion #3481, Hypersonix #3482 + post the READY scoreboard on #3164",
  "Exo posted a first draft on each card 10/14. Update the CEOs first: Hermeus = Zach Shore (Piplica now Exec Chairman), Castelion = Bryon Hargis, Hypersonix = Matt Hill (Waterhouse now Deputy Chair). Log each as an AI error. Then post the team READY scoreboard on #3164 (Done per person vs. +5/week)."),
 ("Laura Granados Lopez","2026-10-22","[Week 7 · University segment] Finish Purdue #3470 + UMontana #3471; close Embry-Riddle #3469 as parked",
  "Exo posted a first draft on each card 10/14. Embry-Riddle: no funding yet, so post a note saying 'parked until funding (NASA TechFlights window)' and move it to Done. Purdue: contact is Prof. Steven Collicott (see Exo note)."),
 ("Adrian Haro","2026-10-22","[Week 7 · Commercial segment] Finish Sierra Space #3476 (new CEO) + the market landscape table #3567",
  "Sierra Space's CEO is now Dan Jablonsky (from 3/2/2026); update the contact and log it as an AI error. Impulse Space #3475 stays on hold unless Lizi reopens it. Market table: carry over #3567 (sources 2023+, linked)."),
 ("Karan Vijaya Sankar","2026-10-22","[Week 7 · Gov/civil segment] New lead cards #3756–3758. Two Done by Thu 10/22",
  "MIT Lincoln Lab #3756, DEVCOM AvMC #3757, The Aerospace Corp #3758. All gov/FFRDC, so Jon sends. The AI drafts are OLD (signed as John, may name a month): rewrite in Lizi's voice, 'early 2027', 'designed for about 2.5 minutes'."),
 ("Karan Vijaya Sankar","2026-10-21","[Week 7 · AI audit] Add this week's AI errors + response-time check; one-paragraph trend by Wed 10/21",
  "New this week: stale CEOs (Sierra, Hermeus, Hypersonix), '5-7 min' microgravity in research text (correct ~2.5 min designed), missing drafts on week-7 cards (fixed 10/14). Also track Exo response time (median 1.3 min since 10/9)."),
 ("Sunidhi Mathew","2026-10-22","[Week 7 · Lead] New lead cards #3759–3761. Two Done by Thu 10/22",
  "Redwire #3759, Benchmark Space Systems #3760, Voyager Technologies #3761. The AI drafts are OLD (signed as John, may name a month): rewrite in Lizi's voice, 'early 2027', 'designed for about 2.5 minutes'."),
 ("Sunidhi Mathew","2026-10-22","[Week 7 · Data Trust] Check every lead card moved to Done this week (contact + claims)",
  "For each teammate card moved to Done this week: contact current? every claim sourced? signed by Lizi (Jon for gov)? 'early 2027', no month? no only/first/fastest? PASS → leave in Done; FAIL → note what's wrong and move back to In Progress."),
 ("Brenda Segovia Saldana","2026-10-22","[Week 7 · Creative] One short LinkedIn post per segment (5) from your messaging, for Lizi to approve",
  "Use your approved segment messaging + headlines. 40-80 words each, one per segment, each ending with the payload questionnaire link: https://www.exosaero.com/payload-questionnaire. Post all 5 as one note here. Also: review the live microsite build when Lizi shares it."),
]
def main(dry):
    have = {t['title'] for t in cc.supa("GET", "tasks?select=title&tags=cs.{week-7}")}
    for owner, due, title, desc in T:
        if title in have: print('exists', title); continue
        row = {"title": title, "owner": owner, "assigned_to": owner, "assigned_email": EM.get(owner),
               "state": "To Do", "priority": 95, "category": "Payload Sales", "due_date": f"{due}T16:59:00+00:00",
               "description": desc, "tags": ["utd-capstone", "week-7"], "source": "utd_week7_tasks.py"}
        if dry: print('DRY', owner, title); continue
        r = cc.supa("POST", "tasks", row); print(r[0]['id'] if r else r, title)
if __name__ == '__main__': main('--go' not in sys.argv)
