#!/usr/bin/env python3
"""
utd_capstone_sessions.py — week-5 "15-minute session" tasks for UTD Team Atlas.

Jon (2026-09-27): students should close work in short 15-20 min Mission Control
sessions, see milestones completed working WITH Exo, and Exo captures every input
and decision as experiment data (scripts/capstone_capture.py logs + acks notes).

Each session = one Supabase task with ONE output (a note in a fixed shape), an
Exo-drafted starting point where useful, and "drag to Done". Idempotent via a
"session:<key>" tag. source="exo-capstone-15m" (assignment-notifier skips it; the
students get one consolidated prompter email instead of per-task mail).

Run: python3 scripts/utd_capstone_sessions.py [--dry-run]
"""
import os, sys, json, argparse, urllib.request

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

WHO = {
    "Roel": ("Roel Saenz", "RCS220001@utdallas.edu"),
    "Laura": ("Laura Granados Lopez", "LEG240001@utdallas.edu"),
    "Karan": ("Karan Vijaya Sankar", "KXV220043@utdallas.edu"),
    "Adrian": ("Adrian Haro", "AXH230026@utdallas.edu"),
    "Brenda": ("Brenda Segovia Saldana", "BXS230052@utdallas.edu"),
    "Sunidhi": ("Sunidhi Mathew", "SXM220350@utdallas.edu"),
}
MON, TUE, WED, THU = ("2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01")
FOOT = ("\n\nWhen you post your note, Exo captures it as a data point for the team's human-vs-AI "
        "experiment and replies with your next session. Disagreeing with the AI is a useful result.")


def lead_sessions(stu, card, short, poc, d1, d2, d3):
    return [
        (stu, f"lead{card}-contact", d1, f"⏱ 15 min · {short}: is the contact still there?",
         f"Lead card #{card} has Exo's research on {short}.\n"
         f"1. Drag card #{card} to In Progress.\n"
         f"2. Look up {poc} on the organization's website and LinkedIn.\n"
         "3. Post one note here:\n   CONTACT: name, title, still in the role? (Y/N), link\n"
         "   If they've left, name who replaced them.\n4. Drag this task to Done."),
        (stu, f"lead{card}-money", d2, f"⏱ 20 min · {short}: find the program and the money",
         f"Using card #{card} as your starting point, post one note here:\n"
         "   PROGRAM: one 2025-2026 link showing the work is active\n"
         "   FUNDING: how they could pay for a flight (NASA Flight Opportunities, SBIR/STTR, NIH/NSF grant, "
         "DoD test program, company R&D or venture money) + link\n"
         "   FIT: 1-5 and one sentence why\nThen drag this task to Done."),
        (stu, f"lead{card}-draft", d3, f"⏱ 20 min · {short}: fix the AI's draft, then move the card to Done",
         f"The AI's draft is on card #{card}. Post one note here:\n"
         "   ERRORS: numbered list of what the AI got wrong: wrong facts, claims with no source "
         "(\"only\", \"first\", \"fastest\"), anything off in tone\n"
         "   DRAFT: your corrected version, under 150 words, no prices\n"
         "BLK3 facts you can use: 135 kg payload bay, about 100-110 km, a few minutes of microgravity, "
         "hardware back in 2-3 days, Flight 2 about March 2027.\n"
         f"Then drag this task AND card #{card} to Done. The lead now counts as READY."),
    ]


S = []
# ---------------- Laura ----------------
S += lead_sessions("Laura", 3141, "LASP", "Dr. Brian Fleming", MON, TUE, WED)
S += lead_sessions("Laura", 3142, "Texas A&M", "Prof. Adonios Karpetis and Prof. Karen Taminger (pick the right one)", TUE, WED, THU)
S += [
    ("Laura", "icp-segments", MON, "⏱ 20 min · ICP: correct Exo's 5-segment starter table",
     "Exo drafted a starting point from the pipeline. Correct it; your edits are the data.\n"
     "1. University/academic: buyer = PI or lab director; money = NASA Flight Opportunities, NSF, NASA ROSES; trigger = new grant award\n"
     "2. Defense & government test: buyer = program manager at a lab or test center; money = SBIR/STTR, test budgets; trigger = test-campaign milestone\n"
     "3. In-space & orbital startups: buyer = CTO or head of engineering; money = venture, SBIR; trigger = new funding round, pre-orbital qualification\n"
     "4. Sensor/avionics/component qualification: buyer = engineering lead; money = R&D budget, SBIR; trigger = TRL or qualification gate\n"
     "5. STEM/education: buyer = program director; money = Space Grant, donors; trigger = academic year or program launch\n"
     "Post one note: the corrected table (buyer / money / trigger for each), plus one real example organization per segment. Drag to Done."),
    ("Laura", "icp-send", WED, "⏱ 20 min · ICP: add disqualifiers, send the one-pager to Lizi",
     "Take your corrected table, add 3-5 disqualifiers (who is NOT a buyer: e.g. needs orbit, needs weeks of microgravity, no budget path), "
     "and put it on one page. Email it to Lizi (lquinn@exosaero.com) and post the link or text here. Drag this task, plus tasks 3130, 2733 and 2734, to Done."),
]
# ---------------- Karan ----------------
S += lead_sessions("Karan", 3146, "NASA Glenn", "Dr. Jason Hartwig", MON, TUE, WED)
S += lead_sessions("Karan", 3147, "Sandia", "Ben English", TUE, WED, THU)
S += [
    ("Karan", "audit-sheet", WED, "⏱ 20 min · AI audit: set up the sheet and load Exo's captured data",
     "Exo posts the team's captured results (contact checks, fit scores, error lists) as a note on this task by Wed 9/30 at 6 pm.\n"
     "1. Make one sheet with these columns: lead, AI fit rank, team fit 1-5, agree?, contact correct?, number of errors, error types.\n"
     "2. Fill one row per lead from Exo's note.\n3. Post the sheet link here and drag to Done."),
    ("Karan", "audit-findings", THU, "⏱ 15 min · AI audit: 3 findings for Thursday's meeting",
     "From your sheet, post 3 one-line findings, e.g. \"The AI's contact was out of date on 2 of 6 leads.\" "
     "Roel puts them on the agenda. Drag to Done."),
]
# ---------------- Adrian ----------------
S += lead_sessions("Adrian", 3151, "Varda", "Will Bruey", MON, TUE, WED)
S += lead_sessions("Adrian", 3152, "Rhodium Scientific", "Olivia Gamez Holzhaus", TUE, WED, THU)
S += [
    ("Adrian", "ready-checklist", MON, "⏱ 20 min · READY checklist: edit Exo's starter and publish it",
     "Exo's starter checklist. Keep, cut, reword or add; each decision is captured.\n"
     "1. Contact verified current, with a link\n2. Program active, with a 2025-2026 source\n"
     "3. A named way they could pay for a flight\n4. Fits BLK3 (payload size, a few minutes of microgravity, recovered hardware)\n"
     "5. Every claim in the draft has a source; no \"only / first / fastest\" without proof\n6. No prices in the draft\n"
     "7. Corrected draft posted on the card\n"
     "Post your final list here, email it to the team and Lizi, then drag this task, plus 3134 and 2739, to Done."),
]
# ---------------- Roel ----------------
S += [
    ("Roel", "im-in", MON, "⏱ 15 min · Open your board and post \"I'm in\" plus one question",
     "Look over your tasks and the capstone tracker (https://mc.exosaero.space/capstone-tracker.html). "
     "Post one note: \"I'm in\", plus the one thing that's least clear to you. Exo answers on this task. Drag to Done."),
    ("Roel", "standup", MON, "⏱ 15 min · Run the Monday stand-up; post who committed to what",
     "15 minutes on Teams. Each person opens their board and names which ⏱ sessions and lead cards they'll finish by Thursday.\n"
     "Post one note: each name and their commitment. Drag this task and task 2730 to Done."),
    ("Roel", "agenda", TUE, "⏱ 15 min · Send Thursday's agenda (Exo drafted it)",
     "Exo's draft. Edit it and email it to Lizi and Senthil by Tue night.\n"
     "Team Atlas: Thu 10/1 sponsor meeting\n1. READY scoreboard: target 6 lead cards Done (Roel)\n"
     "2. Round-robin, 1 minute each: cards finished + the biggest error found in the AI's work\n"
     "3. AI audit: first 3 findings (Karan)\n4. ICP one-pager (Laura), READY checklist (Adrian)\n"
     "5. One-pager + LinkedIn teaser (Brenda)\n6. Quality checks: PASS/FAIL so far (Sunidhi)\n7. Asks for Exos\n"
     "Post \"sent\" here and drag this task and 3127 to Done (3127 stays open until the minutes are out)."),
    ("Roel", "wed-check", WED, "⏱ 15 min · Wednesday check: who's stuck?",
     "Open the capstone tracker and each teammate's cards. Post one note: READY count now vs. the target of 6, "
     "and any card that hasn't moved since Monday, with a name. Nudge those people. Drag to Done."),
    ("Roel", "status", WED, "⏱ 20 min · Weekly status to Lizi (fill in Exo's template)",
     "Template:\nFunnel: start of week 4 NEW / 53 RESEARCHING / 9 READY → now __ / __ / __\n"
     "Cards Done this week: Laura _, Karan _, Adrian _, Sunidhi _, Roel _\n"
     "Moved: …\nBlockers: …\nAsks for Exos: …\n"
     "Email it to Lizi, post \"sent\" here, and drag this task and 3128 to Done."),
]
# ---------------- Brenda ----------------
S += [
    ("Brenda", "teaser", MON, "⏱ 20 min · LinkedIn teaser: pick one of Exo's 3 openings and make it yours",
     "A) \"Last week Team Atlas from UT Dallas visited Exos Aerospace in Greenville, TX, to see where reusable rockets get built.\"\n"
     "B) \"What does it take to fly an experiment to space and get it back in days? Our UTD capstone team got a first-hand look at Exos Aerospace.\"\n"
     "C) \"From classroom to launch site: Team Atlas spent an afternoon at Exos Aerospace learning how suborbital payload flights come together.\"\n"
     "Pick one (or write your own), finish the post in 2-3 more sentences, and choose one Exos-approved photo. No specs, customers or prices. "
     "Email it to Lizi and Senthil, and post the text plus which option you chose and why. Drag this task and 3137 to Done."),
    ("Brenda", "onepager-top", TUE, "⏱ 20 min · One-pager: headline + 3 \"what you get\" bullets",
     "Exo's starter bullets, from the Payload User's Guide:\n- 135 kg payload bay on a reusable rocket\n"
     "- A few minutes of microgravity at about 100-110 km\n- Your hardware back in 2-3 days, so you can fly again\n"
     "Write a headline (SPACEavailable™ is the brand) and rewrite the bullets in your words. Post both here. Drag to Done."),
    ("Brenda", "onepager-send", WED, "⏱ 20 min · One-pager: who it's for + how to reserve; send v1 to Lizi",
     "Add a \"who flies\" line (use the 5 segments on Laura's ICP) and a call to action (\"Contact Exos to reserve a slot\"). No prices. "
     "Lay it out with Lizi's brand kit, email v1 to Lizi, and post the file link here. Drag this task and 3136 to Done."),
    ("Brenda", "site-pages", THU, "⏱ 20 min · Microsite: page list + one line per page",
     "Pages: Home / The Flight / Who Flies / Reserve / About Exos. Post one sentence on what each page must do, and change the list if you disagree. "
     "This is step 1 of task 3138 (the wireframe follows Friday). Drag to Done."),
]
# ---------------- Sunidhi ----------------
S += [
    ("Sunidhi", "qc-list", MON, "⏱ 15 min · Quality-check list: edit Exo's starter",
     "Exo's starter:\n1. Contact still in the role (open the link)\n2. Email from a public source, or marked as guessed\n"
     "3. Program + funding links real and current\n4. Draft claims match the Payload User's Guide\n5. No prices\n6. Nothing sensitive\n"
     "Keep, cut or add, and post your final list. Drag this task and 2745 to Done."),
    ("Sunidhi", "data-rules", TUE, "⏱ 15 min · Send the team the data-rules note (Exo drafted it)",
     "Draft, edit freely: \"Quick reminder on data rules for Team Atlas: we use public information only; nothing export-controlled, CUI or ITAR; "
     "no prices in any draft; and we never contact a prospect ourselves, Lizi sends everything. If you run into something that looks sensitive, "
     "stop and tell Lizi.\"\nEmail it to the team with Lizi cc'd, post \"sent\" here, then drag this task and 2746 to Done."),
    ("Sunidhi", "ucf-check", TUE, "⏱ 20 min · UCF: check the contact and the 3 risky claims",
     "Open card #3159 and drag it to In Progress. Check that Dr. Philip Metzger is still Director of the Hawking Center, and whether the email is public. "
     "Then check the draft's claims: \"the only one currently selling payload slots\", \"fastest recover-and-refly of any U.S. option\", and the launch site. "
     "Post one note: CONTACT: Y/N + link, then CLAIMS: each one supported or unsupported + source. Drag to Done."),
    ("Sunidhi", "ucf-verdict", WED, "⏱ 15 min · UCF: PASS or FAIL",
     "On card #3159, post PASS or FAIL, a numbered error list, and a corrected draft if needed. PASS → drag #3159 to Done. Drag this task to Done."),
    ("Sunidhi", "axiom-check", WED, "⏱ 20 min · Axiom: check Dr. Lucie Low's title and the draft's claims",
     "Open card #3160 and drag it to In Progress. Confirm her current title (the AI has corrected it once already), check the University Alliance claim, "
     "and check the draft against the Payload User's Guide. Post one note: CONTACT, then CLAIMS. Drag to Done."),
    ("Sunidhi", "axiom-verdict", THU, "⏱ 15 min · Axiom: PASS or FAIL",
     "On card #3160, post PASS or FAIL, a numbered error list, and a corrected draft if needed. PASS → drag #3160 to Done. Drag this task to Done."),
    ("Sunidhi", "qc-sweep", THU, "⏱ 15 min · Thursday-morning check of every card teammates moved to Done",
     "Before the meeting, open every lead card teammates moved to Done. For each, post PASS or FAIL on that card, using your list. "
     "FAIL = drag it back to In Progress with the fix. Post here: how many checked, how many passed. Drag to Done."),
]


def existing():
    req = urllib.request.Request(SB + "/tasks?select=id,tags&source=eq.exo-capstone-15m", headers=H)
    return {t[8:] for r in json.load(urllib.request.urlopen(req)) for t in (r.get("tags") or []) if t.startswith("session:")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    have = existing()
    for stu, key, due, title, desc in S:
        if key in have:
            print("skip", key); continue
        owner, email = WHO[stu]
        row = {"title": title, "description": desc + FOOT, "owner": owner, "assigned_to": owner,
               "assigned_email": email, "state": "To Do", "category": "Payload Sales",
               "due_date": due + "T16:59:00+00:00", "priority": 99, "source": "exo-capstone-15m",
               "tags": ["utd-capstone", "week-5", "15-min", "session:" + key]}
        if a.dry_run:
            print("DRY", stu, due, title); continue
        r = urllib.request.Request(SB + "/tasks", data=json.dumps(row).encode(), method="POST",
                                   headers={**H, "Prefer": "return=representation"})
        print("#%s" % json.load(urllib.request.urlopen(r))[0]["id"], stu, due, title)


if __name__ == "__main__":
    sys.exit(main())
