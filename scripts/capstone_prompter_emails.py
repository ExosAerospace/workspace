#!/usr/bin/env python3
"""Build the week-5 Exo "prompter" emails to UTD Team Atlas from the live session
tasks, stage them in mission-control/data/capstone-outbox.json, and file ONE Decision
on Lizi's board. capstone_capture.py sends them only after Lizi answers Yes."""
import os, json, urllib.request
from datetime import datetime
from collections import defaultdict

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
OUTBOX = os.path.join(WS, "mission-control/data/capstone-outbox.json")
MC = "https://mc.exosaero.space"
EMAILS = {"Roel": "RCS220001@utdallas.edu", "Laura": "LEG240001@utdallas.edu", "Karan": "KXV220043@utdallas.edu",
          "Adrian": "AXH230026@utdallas.edu", "Brenda": "BXS230052@utdallas.edu", "Sunidhi": "SXM220350@utdallas.edu"}
ROLE = {
 "Roel": "As team lead you own the team's READY number (task #3164): 6 lead cards Done by Thursday. Your sessions are the ones that keep everyone moving.",
 "Laura": "You own the university segment and the ICP. Two of your lead cards, LASP (#3141) and Texas A&M (#3142), are the ones to finish by Thursday.",
 "Karan": "You own the government segment and the AI audit. The audit is the heart of the project: every error your teammates find in the AI's work lands in your sheet.",
 "Adrian": "You own the commercial segment and the READY checklist the whole team uses. Please do the checklist session first, on Monday.",
 "Brenda": "You own the creative side: the LinkedIn teaser, the payload one-pager, and the microsite.",
 "Sunidhi": "You're the team's quality gate. Nothing reaches Lizi without your PASS. Thank you for already getting your tasks moving; you're ahead of the team.",
}

def get(p):
    r = urllib.request.Request(SB + p, headers={"apikey": KEY, "Authorization": "Bearer " + KEY})
    return json.load(urllib.request.urlopen(r))

def body_for(first, sessions):
    days = defaultdict(list)
    for t in sorted(sessions, key=lambda x: (x["due_date"], x["id"])):
        d = datetime.fromisoformat(t["due_date"].replace("Z", "+00:00")).strftime("%a %-m/%-d")
        days[d].append(f"  #{t['id']}  {t['title'].replace('⏱ ', '')}")
    plan = "\n".join(f"{d}\n" + "\n".join(v) for d, v in days.items())
    return f"""Hi {first},

I'm Exo, the AI that works alongside the Exos team, and starting this week I'm Team Atlas's prompter in Mission Control.

First, an apology. We found a gap on our side. Your leads lived in a file you couldn't open, so the research and draft outreach I had already done for each lead was invisible to you. The tasks on your board were also too broad, with due dates in December, to tell you what to do next. That's our miss, not yours. You may also have received a pile of automated "task assigned" emails today; please ignore those. This email is the one to use.

Here's how it works now. Your board ({MC}) has short sessions, each marked with ⏱, and each takes 15-20 minutes. Every session asks for one thing: post one note, then drag the task to Done. When you post, I capture your answer and reply on the task with your next session. What you check and decide (whether a contact is current, whether you agree with my fit score, which of my claims are wrong) is the data for the team's human-vs-AI experiment. If you disagree with me, that is a result, not a mistake, so please don't hold back.

{ROLE[first]}

Your sessions this week:
{plan}

On Thursday, Lizi will go through the sessions and lead cards each person has closed, so aim to have yours done before the meeting. If something on a task is unclear, post your question as a note on it and I'll answer there. As always, nobody on the team contacts a prospect; Lizi reviews and sends everything.

Talk soon,
Exo
Exos Aerospace · Mission Control
"""

def main():
    rows = get("/tasks?select=id,title,owner,due_date,state&source=eq.exo-capstone-15m&order=due_date")
    emails = []
    for first, addr in EMAILS.items():
        mine = [r for r in rows if r["owner"].split()[0] == first and r["state"] != "Done"]
        emails.append({"to": addr, "first": first,
                       "subject": "Team Atlas: your 15-minute sessions for this week (from Exo)",
                       "body": body_for(first, mine)})
    ob = json.load(open(OUTBOX)) if os.path.exists(OUTBOX) else []
    ob = [x for x in ob if x.get("key") != "wk5-prompter"]
    ob.append({"key": "wk5-prompter", "decision_dedupe": "utd-wk5-prompter-emails", "status": "pending",
               "cc": "lquinn@exosaero.com", "reply_to": "lquinn@exosaero.com", "emails": emails})
    json.dump(ob, open(OUTBOX, "w"), indent=1, ensure_ascii=False)
    preview = "\n\n".join(f"TO {e['to']}\n{e['body']}" for e in emails)
    tok = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
    payload = {"source": "UTD Capstone (Exo prompter)", "relatedItem": "task #3164 / UTD Team Atlas week 5",
        "title": "Release Exo's week-5 prompter emails to the 6 UTD students?",
        "question": ("Jon asked Exo to act as Team Atlas's prompter. Six emails, one per student, from Exo, cc you, Reply-To you. "
                     "Each apologizes for the setup gap and lists that student's 15-20 min Mission Control sessions for Mon-Thu, "
                     "ahead of Thursday's deliverables review. Full text is in Context. Release them?"),
        "context": preview[:20000],
        "proposedAction": ("On Yes, Exo emails all 6 students directly (cc lquinn@exosaero.com, Reply-To you) within ~10 minutes. "
                           "On No, nothing is sent; add a note with the edits you want and Exo revises and re-files."),
        "type": "yesno", "options": ["Yes — Exo sends to the 6 students", "No — hold"], "priority": "high",
        "assignedTo": "lquinn@exosaero.com", "dedupeKey": "utd-wk5-prompter-emails"}
    r = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json", "X-Exo-Token": tok})
    print(urllib.request.urlopen(r).read().decode()[:300])

if __name__ == "__main__":
    main()
