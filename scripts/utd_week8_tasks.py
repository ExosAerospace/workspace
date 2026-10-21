#!/usr/bin/env python3
"""Create UTD Team Atlas Week 8 weekly tasks (meeting 10/22 -> 10/29). Run once, after Lizi OKs."""
import sys; sys.path.insert(0, '/Users/exomac/.openclaw/workspace/scripts')
import capstone_capture as cc
EM = {"Roel Saenz":"RCS220001@utdallas.edu","Laura Granados Lopez":"LEG240001@utdallas.edu",
      "Karan Vijaya Sankar":"KXV220043@utdallas.edu","Adrian Haro":"AXH230026@utdallas.edu",
      "Brenda Segovia Saldana":"BXS230052@utdallas.edu","Sunidhi Mathew":"SXM220350@utdallas.edu"}
T = [
 ("Roel Saenz","2026-10-23","[Week 8 · Lead] Minutes from Thu 10/22 by Fri 10/23; agenda for Thu 10/29 by Tue 10/27",
  "1. Send the 10/22 minutes to Lizi by Fri 10/23 (decisions, action items, owners, dates).\n2. Send the 10/29 agenda by Tue 10/27.\n3. Post both as notes on this card."),
 ("Roel Saenz","2026-10-29","[Week 8 · Lead] Finish Castelion #3481 + Hypersonix #3482; send Lizi the READY checklist; update the READY scoreboard on #3164",
  "Castelion and Hypersonix were due 10/15. If something is stuck, post one sentence on why and a new date on the card. Castelion CEO = Bryon Hargis; Hypersonix = Matt Hill (Waterhouse is now Deputy Chair). Send Lizi your READY checklist. Then post the team scoreboard on #3164 (lead cards Done per person)."),
 ("Roel Saenz","2026-10-29","[Week 8 · Lead] Final presentation (Thu Nov 20, 10 AM, in person): outline + who presents what",
  "Post a one-page outline on this card: sections, who presents each part, and what the handoff to Exos includes (lead list, templates, AI audit, social content). All work has to be finished before the final presentation."),
 ("Laura Granados Lopez","2026-10-29","[Week 8 · University segment] ONE lead card this week: UMontana #3471. Close out Embry-Riddle #3469 + Purdue #3470",
  "This week's one lead is UMontana #3471 (due 10/29). Embry-Riddle #3469: post 'parked until funding' and move it to Done. Purdue #3470: if it's finished, move it to Done. If not, post one sentence on why and a new date."),
 ("Adrian Haro","2026-10-29","[Week 8 · Commercial segment] New lead cards Salish Kootenai #3912 + Resonon #3913; finish the market table #3567",
  "Exo posted a first draft on both cards. Lizi sends both, so write in her voice: 'early 2027', 'designed for about 2.5 minutes of microgravity', no only/first/fastest, no 'FAA-licensed', no refly. Resonon has no public email, so find a public contact route or note that it needs a warm intro. Market table #3567: sources 2023+, linked."),
 ("Karan Vijaya Sankar","2026-10-29","[Week 8 · Gov/civil segment] New lead cards DIU HyCAT #3907, AFRL #3908, Kratos #3909. Two Done by Thu 10/29",
  "All three are John-send leads, so keep them in John's voice, signed John Quinn, Cofounder and CEO. AFRL was reorganized in 2026: confirm the current name and leader. Use 'early 2027' and 'designed for about 2.5 minutes'. No 'only/first/fastest' and no '2-3 day turnaround'."),
 ("Karan Vijaya Sankar","2026-10-28","[Week 8 · AI audit] Finish last week's audit #3767, add this week's AI errors, one-paragraph trend by Wed 10/28",
  "New AI misses this week: no new lead cards were made for Week 8 on time (Exo's mistake, fixed 10/21), and the old drafts on the new cards still use banned claims ('2-3 day', 'FAA-licensed', refly). Add those to the log along with what the team finds."),
 ("Sunidhi Mathew","2026-10-29","[Week 8 · Lead] New lead cards BAE Systems #3910 + Orbit Fab #3911. Both Done by Thu 10/29",
  "John sends both (large defense company / warm intro), so keep them in John's voice. BAE: confirm the right named person (the draft targets Jeff Palombo). Orbit Fab needs a warm intro first: confirm Peter Shaper is still CEO and list their current programs."),
 ("Sunidhi Mathew","2026-10-29","[Week 8 · Data Trust] Check every lead card moved to Done this week + share your lead-research template",
  "For each teammate card moved to Done this week, check: Is the contact current? Is every claim sourced? Is it signed by the right person (John for government and defense, Lizi for everyone else)? Does it say 'early 2027' with no month, and no only/first/fastest? PASS → leave it in Done. FAIL → post a note saying what's wrong and move it back to In Progress. Also post your lead-research template on this card so the team can use it."),
 ("Brenda Segovia Saldana","2026-10-27","[Week 8 · Creative] Final content calendar with links + Halloween post ready for Lizi by Tue 10/27",
  "Links (Lizi 10/21): no payload questionnaire. BLK3 post → microsite. What is a Payload → exosaero.com/blog/what-can-fly-on-a-reusable-suborbital-rocket. Why Suborbital → exosaero.com/blog/suborbital-flight-testing-before-orbital-launch-why-it-reduces-risk. Payload after Flight → payload calculator at exosaero.com/pricing. Behind the Scenes / Fun Fact → exosaero.com or the blog. Halloween → no link. Fun fact = carbon fiber: BLK3 makes extensive use of carbon fiber composites to cut weight, so it can carry more propellant and loft heavier payloads (source: Payload User Guide). No numbers or dates. The Halloween post goes out Sat 10/31, so Lizi needs it by Tue 10/27."),
]
def main(dry):
    have = {t['title'] for t in cc.supa("GET", "tasks?select=title&tags=cs.{week-8}")}
    for owner, due, title, desc in T:
        if title in have: print('exists', title); continue
        row = {"title": title, "owner": owner, "assigned_to": owner, "assigned_email": EM.get(owner),
               "state": "To Do", "priority": 95, "category": "Payload Sales", "due_date": f"{due}T16:59:00+00:00",
               "description": desc, "tags": ["utd-capstone", "week-8"], "source": "utd_week8_tasks.py"}
        if dry: print('DRY', owner, title); continue
        r = cc.supa("POST", "tasks", row); print(r[0]['id'] if r else r, title)
if __name__ == '__main__': main('--go' not in sys.argv)
