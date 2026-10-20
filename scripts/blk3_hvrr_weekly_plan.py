#!/usr/bin/env python3
"""
BLK3-to-Flight + HVRR Flight-Ready Build: weekly plan ("plan the work, work the plan").
Jon, 2026-09-29: team meetings focus on BLK3 to flight and the HVRR flight-ready build
until further notice, with targets by employee for completion each week.

Builds the meeting agenda + per-employee weekly targets (.docx) and, with --create-tasks,
creates one weekly-target task per employee (tag blk3-hvrr-weekly, source exo-blk3-hvrr-weekly-<week>)
so the board carries the plan. Idempotent: skips any employee whose task already exists for the week.
"""
import sys, os, json, datetime
sys.path.insert(0, "/Users/exomac/.openclaw/workspace/scripts")
import supabase_util; supabase_util.install()
import urllib.request
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
SUP = os.path.join(WS, "logs", "assignment-notify-suppress.json")

WEEK_START = datetime.date(2026, 10, 19)
WEEK_END = datetime.date(2026, 10, 23)
WK = f"{WEEK_START:%Y-%m-%d}"
SOURCE = f"exo-blk3-hvrr-weekly-{WK}"
OUT = os.path.join(WS, "drafts", f"BLK3_HVRR_Weekly_Plan_and_Meeting_Agenda_{WK}.docx")

# Lizi 10/20: agendas in plain English — no Exobot jargon. Short sentences, simple words, spell out acronyms the
# first time, no arrows or symbols used as words. Keep real names people use (BLK3, HVRR, task numbers, people).
PLAIN_ENGLISH_RULE = "Lizi 10/20: agendas in plain English — no Exobot jargon."

# Proposed targets. Each = (target, how we know it is finished, Mission Control task numbers).
# Owners confirm or adjust in the meeting. Keep the word "OVERDUE" where a target is late: the weekly agenda
# builder (weekly_task_agenda_exo3.py) looks for it to flag late goals.
TARGETS = [
    ("Phil Eaton", "peaton@exosaero.com", "BLK3 program lead (#1712)", [
        ("BLK3 full schedule: OVERDUE 3 weeks. Every open BLK3 flight task needs one owner and a real date, "
         "working back from the first flight in early 2027. Attach the schedule to #1712 by Wednesday 10/22.",
         "Schedule file is attached to #1712 by end of day Wednesday 10/22", "#1712"),
        ("Recovery section: post how far along it is (percent done) with photos, and finish at least one build step. "
         "There has been no update since 9/7. This is the 4th week in a row.",
         "Photo and step update posted on #78", "#78"),
        ("Fin tooling: confirm the machine shop job is booked (full-size fins, fin shape final). "
         "Send the fin specification package if it has not gone out yet. Note the confirmation on #76.",
         "Machine shop job is booked, and a note is on #76", "#76"),
        ("$10M building policy task: hand #1374 over to Victor, as Jon asked on 9/30. Close it out.",
         "#1374 is assigned to Victor and its status is updated", "#1374"),
    ]),
    ("Neil Milburn", "nmilburn@exosaero.com", "HVRR / Hermes project manager, BLK3 FAA license", [
        ("HVRR ready-to-fly work list: under #3073, add a task with an owner and a date for each of these 5 items: "
         "airflow simulation and guidance and flight-control updates (CFD and GNC), the nose cone shape, shock-absorbing landing legs, "
         "the FAA Part 101 waiver draft (FAA rules for amateur rockets), and the CMTF free-flight test campaign.",
         "All 5 tasks are under #3073, each with an owner and a date", "#3073"),
        ("BLK3 FAA launch license package (Part 450, the FAA's launch license rules): move at least one section "
         "forward. Post its status and any new draft on #2802.",
         "Status note and the updated section are posted on #2802", "#2802"),
    ]),
    ("Steve Norsworthy", "snorsworthy@exosaero.com", "Computer section build, parts that take a long time to arrive", [
        ("Parts with long lead times: confirm the SDI505 motion sensor (IMU), the Athena IV flight computer, and the "
         "Cambium 900 MHz radio are ordered. If not, send the purchase requests this week. Post the confirmation on #3024.",
         "Order confirmation and any purchase requests are posted on #3024", "#3024"),
        ("Computer section build: take a photo of each part installed this week and post it on #3024.",
         "A photo for each part is posted on #3024", "#3024"),
    ]),
    ("Mike Talley", "mtalley@exosaero.com", "Fabrication and ground equipment", [
        ("Bulkheads: post how far along they are (percent done) with photos. OVERDUE 4 weeks. No update since 9/7.",
         "Photo and status posted on #86", "#86"),
        ("Helium tank space: if the helium tank decision (#3056) comes in this week, add the large helium tank to the "
         "design model and sketch how it will be held in place. If #3056 is still open, post a note saying you are waiting on it.",
         "Model screenshot on #90 or #92, or a note that you are waiting", "#90, #92, #3056"),
        ("Launch stool: inspect it and its scale, and write a list of what needs repair or changes. OVERDUE 4 weeks.",
         "Repair and change list posted on #102 or #103", "#102, #103"),
    ]),
    ("Victor Castilleja", "vcastilleja@exosaero.com", "Shop work, build photos, HVRR part certificates", [
        ("Clean the HVRR tanks (#2409). OVERDUE 3 weeks. No progress since 9/29.",
         "#2409 marked Done, with a photo", "#2409"),
        ("Mount the GPS antenna (#82). OVERDUE 4 weeks. No progress since 9/7.",
         "#82 marked Done, with a photo", "#82"),
        ("BLK3 parts pricing: ask vendors for price quotes on the 10 highest-value open parts on #3076. "
         "No progress since 9/24.",
         "List of quote requests posted on #3076", "#3076"),
        ("HVRR part certificates (#2408): scan and record the certificates for at least 2 more sub-assemblies.",
         "Updated spreadsheet posted on #2408", "#2408"),
    ]),
    ("Russ Blink", "rblink@exosaero.com", "Electronics, flight software, and telemetry (sending flight data to the ground). Needs John's help", [
        ("Telemetry parts, for sending flight data to the ground (#94): OVERDUE since 10/2 (4 weeks). Post the parts you picked, or a written note on "
         "what is still missing, by end of day Tuesday. If something is in your way, say what it is in writing.",
         "Parts list or a written note posted on #94 by Tuesday 10/21", "#94"),
        ("Wiring harness design: post a draft wiring diagram and wire list for the computer section on #85. "
         "OVERDUE 4 weeks.",
         "Draft posted on #85", "#85"),
        ("Recovery servo control (a small motor in the recovery system, run by the flight computer): post the status and the flight software "
         "steps still left on #80.",
         "Status note posted on #80", "#80"),
        ("Ground telemetry support: ask for a price quote and note it on #96.",
         "Quote request sent and noted on #96", "#96"),
    ]),
    ("John Quinn", "jquinn@exosaero.com", "CEO, owns the plan", [
        ("High-pressure helium tank (#3056): make the final choice. Option A: fix the seal at the tank fitting (boss seal). "
         "Option B: add a protective coating (conformal coating). Option C: get a new tank. The Pressure Section and Mike's helium tank work (#90, #92) "
         "cannot move until this is decided.",
         "Decision written on #3056", "#3056"),
        ("Russ Blink: 4 weeks with no electronics work posted. John needs to step in directly.",
         "Outcome noted on #3666 or #94", "#3666, #94"),
        ("Run the Friday results: what each person promised, and what got done.",
         "Results posted on this plan task", "this task"),
    ]),
    ("Lizi Quinn", "lquinn@exosaero.com", "Customer payloads, and what the build team needs to know about them", [
        ("Confirm the UTD/Comet status after the check-in email sent 10/12. Update #1300 with any changes.",
         "Note posted on #1300 confirming the UTD/Comet status", "#1300"),
    ]),
]

AGENDA = [
    ("1. Goal and ground rules (John), 5 minutes",
     ["Until further notice, the team focuses on two things: getting BLK3 (our next rocket) to its first flight in "
      "early 2027, and finishing the HVRR build so it is ready to fly. BLK3 is moving from the FAA's older Part 431 "
      "rules to the newer Part 450 launch license rules.",
      "How we work: plan the work, then work the plan. Each person agrees to their goals on Tuesday, "
      "updates them every day, and we check results on Friday."]),
    ("2. Last week's results (Oct 12 to Oct 16), 10 minutes",
     ["Phil: 0 of 5 done. The full schedule (3 weeks late), fin tooling, and recovery section are all still open.",
      "Neil: 1 of 3 done (login to PIEE, the government contracting portal). The HVRR work list and the Part 450 license package move to this week.",
      "Steve: 0 of 2 done. The long-lead parts confirmation and build photos were not posted.",
      "Mike: 0 of 3 done. Bulkheads and launch stool were missed. The helium tank work is waiting on #3056.",
      "Victor: 0 of 4 done. The GPS antenna and HVRR tank cleaning are 3 to 4 weeks late.",
      "Russ: 0 of 4 done. This is the 4th week in a row with no work posted. John needs to step in today.",
      "John: 1 of 3 done (Friday results). The helium tank decision is still open.",
      "Lizi: 1 of 1 done (payload update on 10/12)."]),
    ("3. The most important work, in order, 10 minutes",
     ["BLK3 (Phil): the full schedule (we cannot see what is late without it), recovery section, fin tooling, "
      "pressure system (waiting on the helium tank decision, #3056), computer section (Steve's long-lead parts), "
      "and electronics (Russ, no updates in 4 weeks).",
      "HVRR / Hermes, Air Force contract FA9300-26-C-6011 (Neil): tasks for airflow and flight-control updates, "
      "nose cone, landing legs, FAA Part 101 waiver, and CMTF test flights."]),
    ("4. This week's goals for each person, 20 minutes",
     ["Each person agrees to their goals on the next pages, or changes them. After the meeting the goals are set in Mission Control."]),
    ("5. What is holding work up, and decisions needed, 10 minutes",
     ["High-pressure helium tank final choice (#3056): SSLC is still testing a Parylene coating. The pressure system waits on this.",
      "Russ Blink: 4 weeks with no electronics work delivered. John needs to step in directly.",
      "Phil's full schedule: we cannot see what is late without it. This is the 3rd time we have asked."]),
    ("6. Weekly routine and wrap-up, 5 minutes",
     ["Every day by 4 pm: update your task (a note, a photo, or a status change). Exobot only points out what is slipping.",
      "Friday 3 pm: results, showing what each person promised and what got done. If something was missed, "
      "say why and give a new date.",
      "Friday: Exobot drafts next week's goals from the task board. Each person confirms theirs on Tuesday."]),
]

RULES = [
    "Every open BLK3 or HVRR task has exactly one owner and a real due date. No placeholder dates.",
    "A task is only done when there is proof in Mission Control: a file, a photo, or a status change. Saying \"done\" out loud does not count.",
    "If something has been stuck for more than 24 hours, tell John that same day.",
    "Do not start new work outside BLK3 and HVRR during the week unless John says OK.",
    "Each goal should fit in one week. Big jobs are split into weekly steps.",
]


def set_widths(t, inches):
    t.autofit = False
    for col, w in zip(t.columns, inches):
        col.width = Inches(w)
    for row in t.rows:
        for cell, w in zip(row.cells, inches):
            cell.width = Inches(w)


def build_doc():
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    h = d.add_heading("BLK3 to Flight + HVRR Flight-Ready Build", level=0)
    p = d.add_paragraph(f"Weekly plan and team meeting agenda. Week of {WEEK_START:%B %-d} to {WEEK_END:%B %-d, %Y}. "
                        f"Meeting: Tuesday {WEEK_START + datetime.timedelta(days=1):%B %-d}, 10:00 to 11:00 Central. "
                        "Meeting leader: John Quinn.")
    p.runs[0].italic = True
    d.add_paragraph("Our focus until further notice (John, 9/29): get BLK3 to its first flight, and finish the HVRR build "
                    "so it is ready to fly. How we work: plan the work, then work the plan. The goals below are suggestions "
                    "taken from the Mission Control task board. Each person agrees to them or changes them in the meeting. "
                    "After that, they are set for the week.")
    d.add_heading("Agenda (60 minutes)", level=1)
    for title, bullets in AGENDA:
        d.add_paragraph(title).runs[0].bold = True
        for b in bullets:
            d.add_paragraph(b, style="List Bullet")
    d.add_heading("Ground rules", level=1)
    for r in RULES:
        d.add_paragraph(r, style="List Number")
    d.add_heading(f"This week's goals for each person (finish by Friday {WEEK_END:%B %-d})", level=1)
    for name, email, role, items in TARGETS:
        d.add_heading(f"{name}  ({role})", level=2)
        t = d.add_table(rows=1, cols=4); t.style = "Table Grid"
        for i, hd in enumerate(["No.", "Goal", "Finished when", "Mission Control task"]):
            t.rows[0].cells[i].text = hd
        for n, (tgt, done, ref) in enumerate(items, 1):
            c = t.add_row().cells
            c[0].text, c[1].text, c[2].text, c[3].text = str(n), tgt, done, ref
        set_widths(t, [0.35, 3.9, 1.75, 0.9])
        d.add_paragraph("Agreed: ☐   Changed: ☐   Friday: ___ of " + str(len(items)) + " done")
    d.add_heading("Friday results", level=1)
    t = d.add_table(rows=1, cols=5); t.style = "Table Grid"
    for i, hd in enumerate(["Person", "Goals agreed", "Done", "If missed: why", "New date"]):
        t.rows[0].cells[i].text = hd
    for name, _, _, items in TARGETS:
        c = t.add_row().cells; c[0].text = name; c[1].text = str(len(items))
    set_widths(t, [1.6, 0.9, 0.7, 2.4, 1.3])
    d.add_heading("Extra: other monthly items (to read on your own, not discussed)", level=1)
    d.add_paragraph("Two items went out in yesterday's email: the monthly list of what Exobot automated, and the standing "
                    "finance item on the 2021 PO7 notes coming due (#2982). Please read them on your own. We are skipping "
                    "them today to save meeting time for the build.")
    d.save(OUT)
    import agenda_task_status; agenda_task_status.annotate_docx(OUT)  # Lizi 10/20: live MC status on every task ref
    return OUT


def sb(method, path, body=None, prefer=None):
    hh = dict(H)
    if prefer:
        hh["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(SB + "/" + path, data=data, headers=hh, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None


def create_tasks():
    existing = sb("GET", f"tasks?source=eq.{SOURCE}&select=id,title,assigned_email") or []
    have = {e["assigned_email"]: e["id"] for e in existing}
    made = {}
    for name, email, role, items in TARGETS:
        if email in have:
            made[name] = have[email]; continue
        # NOTE: keep the "N. goal\n   Done when: ...  [#refs]" line format exactly — weekly_task_agenda_exo3.parse_lines reads it.
        desc = (f"WEEKLY TARGETS: your goals for the week of {WEEK_START:%B %-d} to {WEEK_END:%B %-d} "
                f"(BLK3 to first flight, and the HVRR build ready to fly)\n"
                f"Our focus, set by John on 9/29: plan the work, then work the plan. These goals were suggested at the "
                f"9/29 meeting. Agree to them or change them in the meeting. After that, they are your goals for the week.\n\n"
                + "\n".join(f"{n}. {t}\n   Done when: {dn}  [{ref}]" for n, (t, dn, ref) in enumerate(items, 1))
                + f"\n\nEvery day by 4 pm: post an update on the tasks listed above. Friday 3 pm: we check results "
                  f"(what you agreed to, and what got done).\n"
                  f"Plan document: {os.path.basename(OUT)}")
        row = {"title": f"WK {WEEK_START:%m/%d}–{WEEK_END:%m/%d} targets: {name} (BLK3 to Flight / HVRR)",
               "state": "To Do", "owner": name, "assigned_to": name, "assigned_email": email,
               "category": "Blk3 Flight", "priority": 95, "source": SOURCE,
               "due_date": f"{WEEK_END:%Y-%m-%d}T22:00:00+00:00",
               "tags": ["blk3-hvrr-weekly", f"wk-{WK}", "plan-the-work"], "description": desc}
        c = sb("POST", "tasks", row, prefer="return=representation")
        made[name] = c[0]["id"]
    # Suppress assignment emails: John presents these in the meeting first.
    try:
        sup = json.load(open(SUP)); sup = sup if isinstance(sup, dict) else {}
    except Exception:
        sup = {}
    for name, email, _, _ in TARGETS:
        sup[str(made[name])] = email
    json.dump(sup, open(SUP, "w"))
    return made


if __name__ == "__main__":
    print(build_doc())
    if "--create-tasks" in sys.argv:
        print(json.dumps(create_tasks(), indent=1))
