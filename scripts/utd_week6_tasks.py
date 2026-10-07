#!/usr/bin/env python3
"""Create UTD Team Atlas Week 6 weekly tasks (meeting 10/8 -> 10/15). Run once, after Lizi OKs."""
import sys; sys.path.insert(0, '/Users/exomac/.openclaw/workspace/scripts')
import capstone_capture as cc
EM = {"Roel Saenz":"RCS220001@utdallas.edu","Laura Granados Lopez":"LEG240001@utdallas.edu",
      "Karan Vijaya Sankar":"KXV220043@utdallas.edu","Adrian Haro":"AXH230026@utdallas.edu",
      "Brenda Segovia Saldana":"BXS230052@utdallas.edu","Sunidhi Mathew":"SXM220350@utdallas.edu"}
T = [
 ("Roel Saenz","2026-10-09","[Week 6 · Lead] Minutes from Thu 10/8 within 24 hrs; agenda for Thu 10/15 by Tue 10/13",
  "1. Send the 10/8 meeting minutes to Lizi by Fri 10/9 (decisions, action items, owners, dates).\n2. Send the 10/15 agenda by Tue 10/13.\n3. Post both as a note on this card too."),
 ("Roel Saenz","2026-10-14","[Week 6 · Lead] Post the READY scoreboard on #3164 by Wed 10/14 (Done cards per person vs. target)",
  "Target: +5 lead cards Done per week for the team.\n1. Count each person's lead cards in Done (board, tag utd-lead).\n2. Post one note on #3164: name, Done this week, still open, blockers.\n3. Finish your own open cards first: Firehawk #3156, Phase Four #3158."),
 ("Laura Granados Lopez","2026-10-15","[Week 6 · University segment] Finish #3143–3145, then start #3469–3471. Three Done by Thu 10/15",
  "1. Finish Montana State #3143, UAH #3144, Michigan #3145.\n2. Then start Embry-Riddle #3469, Purdue #3470, UMontana #3471.\n3. Also still open: ICP v1 (#3130). Share with Lizi by Tue 10/13."),
 ("Karan Vijaya Sankar","2026-10-15","[Week 6 · Gov/civil segment] Your new lead cards #3472–3474. Two Done by Thu 10/15",
  "NCATS #3472, Draper #3473, Bridger Photonics #3474. Same steps as last week: verify contact, program, funding, fit; clean draft; one PASS/FAIL note; then Done."),
 ("Karan Vijaya Sankar","2026-10-14","[Week 6 · AI audit] Add this week's AI errors to the audit log; one-paragraph trend by Wed 10/14",
  "1. Add new errors the team caught (e.g., SDL out-of-date title; UCF correction = Exo verification miss).\n2. Group by type: stale contact / unsupported claim / missed our own history / other.\n3. One-paragraph trend summary as a note here. This feeds the Week 8 mid-project readout."),
 ("Adrian Haro","2026-10-15","[Week 6 · Commercial segment] Your new lead cards #3475–3478. Two Done by Thu 10/15",
  "Impulse Space #3475, Sierra Space #3476, Space Forge #3477, York Space Systems #3478. Same steps as last week."),
 ("Adrian Haro","2026-10-14","[Week 6 · Market landscape] One-page table: other ways customers fly payloads today, with sources",
  "Columns: option (e.g., sounding rockets, parabolic flights, other suborbital vehicles, ISS), what it offers, typical wait, who uses it, source link.\nRules: credible sources from 2023 or newer, linked; no claims about Exos you can't source. Post as a note by Wed 10/14."),
 ("Brenda Segovia Saldana","2026-10-13","[Week 6 · Creative] Microsite copy pass: fill the placeholder text by Tue 10/13",
  "Layout approved (#3138). Fill: About / Who We Are / Vision / Team; The Flight (launch→return, process steps); Who Flies segment names (use the 5 one-pager segments); Reserve intro; 6 FAQ questions.\nConfirmed: phone (430) 966-4005, info@exosaero.com, '25 years' line. Partners: approved ones on exosaero.com. Questionnaire button: https://www.exosaero.com/payload-questionnaire\nTiming: say 'early 2027', never a month. Numbers = 'designed for', not flown results."),
 ("Sunidhi Mathew","2026-10-15","[Week 6 · Lead] Your new lead cards #3483–3485. Two Done by Thu 10/15",
  "United Therapeutics #3483, Rhea Space Activity #3484, Exobiosphere #3485. Same steps as last week."),
 ("Sunidhi Mathew","2026-10-15","[Week 6 · Data Trust] Check every lead card moved to Done this week (contact + claims)",
  "For each teammate card moved to Done this week: contact current? every claim sourced? draft clean? PASS → leave in Done; FAIL → note what's wrong and move back to In Progress."),
]
def main(dry):
    have = {t['title'] for t in cc.supa("GET", "tasks?select=title&tags=cs.{week-6}")}
    for owner, due, title, desc in T:
        if title in have: print('exists', title); continue
        row = {"title": title, "owner": owner, "assigned_to": owner, "assigned_email": EM.get(owner),
               "state": "To Do", "priority": 95, "category": "Payload Sales", "due_date": f"{due}T16:59:00+00:00",
               "description": desc, "tags": ["utd-capstone", "week-6"], "source": "utd_week6_tasks.py"}
        if dry: print('DRY', owner, title); continue
        r = cc.supa("POST", "tasks", row); print(r[0]['id'] if r else r, title)
if __name__ == '__main__': main('--go' not in sys.argv)
