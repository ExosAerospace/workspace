#!/usr/bin/env python3
"""Jon 2026-10-17 (email command): send the NASA TechLeap Orbital Clarity Challenge to
UTD Team Atlas with a briefing; Lizi approves. Creates one 20-min session task, writes
the briefing .docx, stages 6 emails in capstone-outbox.json, and files ONE Decision on
Lizi's board. capstone_capture.py sends only after Lizi answers Yes."""
import os, json, urllib.request
from docx import Document
from docx.shared import Pt

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
OUTBOX = os.path.join(WS, "mission-control/data/capstone-outbox.json")
DOCX = os.path.join(WS, "drafts/UTD_Orbital_Clarity_Briefing_2026-10-17.docx")
EMAILS = {"Roel": "RCS220001@utdallas.edu", "Laura": "LEG240001@utdallas.edu", "Karan": "KXV220043@utdallas.edu",
          "Adrian": "AXH230026@utdallas.edu", "Brenda": "BXS230052@utdallas.edu", "Sunidhi": "SXM220350@utdallas.edu"}
NASA = "https://www.nasa.gov/directorates/stmd/prizes-challenges-crowdsourcing-program/nasa-techleap-prize-orbital-clarity-challenge"
SITE = "https://occ.nasatechleap.org/"
FAQ = "https://occ.nasatechleap.org/frequently-asked-questions/"
AWARDS = "https://occ.nasatechleap.org/awards/"


def session_task():
    q = SB + "/tasks?select=id&tags=cs.%7Bsession:occ-fit%7D"
    have = json.load(urllib.request.urlopen(urllib.request.Request(q, headers=H)))
    if have:
        return have[0]["id"]
    desc = (
        "NASA's Orbital Clarity Challenge may help some of our payload customers pay for their experiments. "
        "Read Exo's briefing email first (subject: \"Team Atlas: a NASA prize that could fund our customers' experiments\").\n\n"
        "EVERYONE (20 min): go through YOUR OWN lead cards and post ONE note here:\n"
        "   FIT: organization | what they build that measures the upper atmosphere or space environment | link | lead card #\n"
        "   (one line per fit), or: NONE from my cards\n"
        "Roel: on Tue 10/20, check that all 6 notes are in, then drag this task to Done.\n\n"
        "Who fits: groups that build or could build sensors for atmospheric density, pressure or drag "
        "(atmospheric/space-physics labs, instrument makers, small-satellite sensor companies). Most cards won't fit; NONE is a fine answer.\n"
        "Nobody contacts a customer. Lizi decides who gets an invitation and sends it.\n\n"
        f"Sources: {NASA} · {FAQ}"
        "\n\nWhen you post your note, Exo captures it as a data point for the team's human-vs-AI "
        "experiment. Disagreeing with the AI is a useful result.")
    row = {"title": "⏱ 20 min · NASA Orbital Clarity prize: which of our customers fit?", "description": desc,
           "owner": "Roel Saenz", "assigned_to": "Roel Saenz", "assigned_email": EMAILS["Roel"], "state": "To Do",
           "category": "Payload Sales", "due_date": "2026-10-20T22:59:00+00:00", "priority": 99,
           "source": "exo-capstone-15m", "tags": ["utd-capstone", "15-min", "session:occ-fit"]}
    r = urllib.request.Request(SB + "/tasks", data=json.dumps(row).encode(), method="POST",
                               headers={**H, "Prefer": "return=representation"})
    return json.load(urllib.request.urlopen(r))[0]["id"]


def body(first, tid):
    return f"""Hi {first},

John Quinn forwarded a NASA prize that could matter to some of the payload customers in your pipeline, and he asked me to brief the team on it.

WHAT IT IS
The NASA TechLeap Prize "Orbital Clarity Challenge." NASA wants low-cost sensors that can be built in quantity to measure atmospheric density, pressure, or drag in low Earth orbit. Up to four winners can each receive up to $500,000 over three phases ($200K, then $200K, then $100K). NASA also intends to give the final winners a test flight in orbit at no cost.
Key dates: registration closes Oct 28 at 5:00 PM ET. Phase 1 submissions close Nov 11 at 5:00 PM ET.
Sources: {NASA}
and {AWARDS}

WHY IT MATTERS TO OUR CUSTOMERS
The challenge FAQ says prize funds "can be used however the winners see fit" ({FAQ}). So a customer who wins could use part of the money to fund their experiment. One example is a recoverable BLK3 flight to test their sensor and get the hardware back before NASA's orbital test. John's idea is to invite the customers who fit, as a favor to them.
To be clear about what this is not: Exos isn't entering the challenge, and BLK3 isn't the orbital test flight NASA provides. If you describe it, say "a NASA prize that might fund your experiment." Don't say it's an Exos program.

WHO FITS
Only groups that build, or could build, sensors for the upper atmosphere or the space environment: atmospheric and space-physics labs, instrument makers, and small-satellite sensor companies. Most of our pipeline won't fit, and that's fine.

YOUR 20-MINUTE SESSION: task #{tid}, due Tue 10/20
Go through your own lead cards and post one note on #{tid}:
   FIT: organization | what they build that measures the upper atmosphere or space environment | link | lead card #
or: NONE from my cards
Roel checks that all six notes are in on Tuesday. The deadline is tight because invitations have to reach customers before NASA's Oct 28 registration cutoff.

As always, nobody on the team contacts a customer. Lizi decides who gets an invitation and sends it. If anything is unclear, post a question on #{tid} and I'll answer there.

Talk soon,
Exo
Exos Aerospace · Mission Control
"""


def write_docx(text):
    d = Document()
    d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)
    d.add_heading("Team Atlas Briefing: NASA Orbital Clarity Challenge", level=1)
    d.add_paragraph("From Exo to UTD Team Atlas · staged 2026-10-17 · released by Lizi Quinn (Decision)")
    d.add_paragraph("To: RCS220001@utdallas.edu; LEG240001@utdallas.edu; KXV220043@utdallas.edu; AXH230026@utdallas.edu; "
                    "BXS230052@utdallas.edu; SXM220350@utdallas.edu (one email each)\nCc: lquinn@exosaero.com\n"
                    "Reply-To: lquinn@exosaero.com\nSubject: Team Atlas: a NASA prize that could fund our customers' experiments (from Exo)")
    for para in text.split("\n\n"):
        d.add_paragraph(para)
    d.save(DOCX)


def main():
    tid = session_task()
    emails = [{"to": a, "first": f, "subject": "Team Atlas: a NASA prize that could fund our customers' experiments (from Exo)",
               "body": body(f, tid)} for f, a in EMAILS.items()]
    write_docx(body("[first name]", tid))
    ob = json.load(open(OUTBOX)) if os.path.exists(OUTBOX) else []
    ob = [x for x in ob if x.get("key") != "occ-briefing"]
    ob.append({"key": "occ-briefing", "decision_dedupe": "utd-occ-briefing", "status": "pending",
               "cc": "lquinn@exosaero.com", "reply_to": "lquinn@exosaero.com", "emails": emails})
    json.dump(ob, open(OUTBOX, "w"), indent=1, ensure_ascii=False)
    tok = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
    payload = {"source": "Exo (email command)", "relatedItem": f"task #2149 (Orbital Clarity) / student session #{tid}",
        "title": "Release Exo's Orbital Clarity briefing to the 6 UTD students?",
        "question": ("John forwarded NASA's Orbital Clarity Challenge (register by Oct 28, 5 PM ET; up to $500K per winner; "
                     "the FAQ says prize funds can be used however winners see fit). He asked Exo to brief Team Atlas, with you approving. "
                     "Six emails, one per student, from Exo, cc you, Reply-To you. Each explains the prize and assigns one 20-min session "
                     f"(#{tid}, due Tue 10/20): flag which of their lead cards fit (upper-atmosphere/space-environment sensor builders). "
                     "Students contact nobody; you pick who gets an invitation. Full text is in Context. Release them?"),
        "context": body("Roel", tid),
        "proposedAction": ("On Yes, Exo emails all 6 students (cc lquinn@exosaero.com, Reply-To you) within ~10 minutes. "
                           "On No, nothing is sent; add a note with your edits and Exo revises and re-files."),
        "type": "yesno", "options": ["Yes — Exo sends to the 6 students", "No — hold"], "priority": "high",
        "assignedTo": "lquinn@exosaero.com", "dedupeKey": "utd-occ-briefing"}
    r = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json", "X-Exo-Token": tok})
    print("task", tid, "| decision:", urllib.request.urlopen(r).read().decode()[:300])


if __name__ == "__main__":
    main()
