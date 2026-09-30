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

WEEK_START = datetime.date(2026, 9, 28)
WEEK_END = datetime.date(2026, 10, 2)
WK = f"{WEEK_START:%Y-%m-%d}"
SOURCE = f"exo-blk3-hvrr-weekly-{WK}"
OUT = os.path.join(WS, "drafts", f"BLK3_HVRR_Weekly_Plan_and_Meeting_Agenda_{WK}.docx")

# Proposed targets. Each = (target, done-when evidence, MC task refs). Owners confirm or adjust in the meeting.
TARGETS = [
    ("Phil Eaton", "peaton@exosaero.com", "BLK3 program lead (#1712)", [
        ("BLK3 integrated master schedule: every open Blk3 Flight task gets a real owner and a due date "
         "back-planned from the flight date (the current Dec/Jan dates are Teamwork-import placeholders). "
         "Mark the critical path.", "Schedule attached to #1712 by Wed 9/30 EOD", "#1712"),
        ("Recovery section: list the remaining fab steps with % complete, and close at least one step this week.",
         "Step list + photo on #78", "#78"),
        ("Fin redesign: freeze the fin geometry, or name the exact data still missing (Missile DATCOM, #1435).",
         "Decision or gap note on #76", "#76, #1435"),
        ("Release the restricted BLK3 engineering drawings (Quinn/Eaton/Blink only). Overdue since 8/22.",
         "Drawings on #1872", "#1872"),
        # Added by John 9/30 (Mission Score >100, quick wins).
        ("Prior payload customer list for the UTD Capstone data request (holding up 6 people). Attach the docs.",
         "List attached, #2631 Done", "#2631"),
        ("$10M BLK3 vehicle-coverage adder: attach the latest building policy and reassign to Victor to make the inquiry. "
         "Same for any other admin tasks on your plate.", "Policy on #1374, reassigned to Victor", "#1374"),
    ]),
    ("Neil Milburn", "nmilburn@exosaero.com", "HVRR / Hermes PM, BLK3 licensing", [
        ("Hermes kick-off: the contract puts CLIN0001 kick-off in 30 Sep-30 Oct 2026, but #3081 is dated 1/15/27. "
         "Lock a kick-off date with Harvazinski/CO, or get the PSI-driven delay confirmed in writing.",
         "Date or written CO confirmation on #3081", "#3073, #3081"),
        ("HVRR flight-ready WBS: break the Hermes SOW into owned, dated tasks (CFD + GNC updates, aero nose cone, "
         "shock-absorbing landing legs, 14 CFR 101 waiver draft, insurance, CMTF free-flight campaign).",
         "WBS subtasks under #3073, each with an owner and date", "#3073"),
        ("BLK3 Part 450 package: advance the next WBS section and post its status.",
         "Status note on #2802", "#2802, #2693"),
        ("Hermes CUI handling: stand up the CUI marking + GCC High storage path before the first deliverable.",
         "#3234 In Progress with plan noted", "#3234"),
    ]),
    ("Steve Norsworthy", "snorsworthy@exosaero.com", "Computer section build, inventory, HVRR certs", [
        ("Computer section: confirm the 3 long-lead items (SDI505 IMU, Athena IV CPU, Cambium 900 MHz radio) and "
         "finish the have/short list. Shortages go out as purchase requests.",
         "Have/short list on #3024", "#3024"),
        ("Close out the BLK3 inventory have/short report.", "#3035/#3037/#3038 Done or merged", "#3035, #3037, #3038"),
        ("HVRR parts cert log: scan and log the certs for at least 2 of the 7 subassemblies.",
         "Updated workbook on #2408", "#2408"),
        ("BLK3 cost-fill: enter shop cost on the 17 Exos-made/labor lines.", "#3075 Done", "#3075"),
    ]),
    ("Mike Talley", "mtalley@exosaero.com", "Fabrication / GSE", [
        ("Bulkheads: finish fabrication, or post the % complete with photos.", "Photo + state on #86", "#86"),
        ("Pressurization section: put the large GHe tank envelope in the design model and sketch the support concept. "
         "Tank selection depends on the HP He tank decision (#3056).",
         "Model screenshot on #90/#92", "#90, #92"),
        ("Launch stool: inspect it and the scale system, and write the repair/modify list.",
         "List on #102/#103", "#102, #103"),
    ]),
    ("Victor Castilleja", "vcastilleja@exosaero.com", "Shop / build capture", [
        ("Clean the HVRR tanks.", "#2409 Done with photo", "#2409"),
        ("Mount the GPS antenna.", "#82 Done with photo", "#82"),
        ("Capture the computer-section build with Steve: photos per component on the task.",
         "Photos on #3024", "#3024"),
        ("BLK3 cost-fill: send vendor RFQs for the 10 highest-value open lines.", "RFQ list on #3076", "#3076"),
    ]),
    ("Russ Blink", "rblink@exosaero.com", "Avionics / FSW / telemetry", [
        ("Select the on-board telemetry components (due 10/2).", "Selection on #94", "#94"),
        ("Harness design: interconnect diagram and harness list for the computer section.",
         "Draft on #85", "#85"),
        ("Recovery servo serial control: status and remaining FSW steps.", "Note on #80", "#80"),
        ("Request the ground telemetry support quote.", "Request sent, noted on #96", "#96"),
    ]),
    ("John Quinn", "jquinn@exosaero.com", "CEO: owns the plan", [
        ("Approve Phil's BLK3 master schedule and Neil's HVRR WBS by Thu 10/1.", "Approval noted on #1712 / #3073", "#1712, #3073"),
        ("Decide on the HP He tank (D-1 test protocol, D-2 vac-impregnation). The pressurization build is gated on it.",
         "Decision recorded on #3056", "#3056"),
        ("Run the Friday scorecard: committed vs done by person.", "Scorecard on this plan task", "this task"),
    ]),
    ("Lizi Quinn", "lquinn@exosaero.com", "Payload manifest → build inputs", [
        ("Send engineering a snapshot of payload inputs that drive the build (committed payloads, mass, power/data, "
         "ejection needs), so integration design is based on the real manifest.",
         "Snapshot on #1300", "#1300, #2360"),
    ]),
]

AGENDA = [
    ("1. Mission and rules (John), 5 min",
     ["Until further notice, the team's focus is BLK3 to flight and the HVRR flight-ready build.",
      "Method: plan the work, work the plan. Weekly targets are committed Tuesday, updated daily, and scored Friday."]),
    ("2. Critical path walk, 15 min",
     ["BLK3 (Phil): recovery section, fins, pressurization (GHe tank), computer/avionics section, telemetry/FSW, "
      "harnesses, GSE; licensing (Neil: Part 431 today, Part 450 package).",
      "HVRR / Hermes FA9300-26-C-6011 (Neil): kick-off window 30 Sep-30 Oct; SOW = CFD/GNC, nose cone, landing legs, "
      "Part 101 waiver, insurance; free-flight campaign at CMTF 2027 Q1/Q2; PSI engine delivery is the known dependency."]),
    ("3. Targets by employee for this week, 25 min",
     ["Each owner confirms or adjusts their targets (next pages). Targets are locked in Mission Control after the meeting."]),
    ("4. Blockers and decisions, 10 min",
     ["HP He tank path (#3056), which gates the pressurization section",
      "Hermes kick-off date vs. PSI engine delay (#3081)",
      "Fin geometry freeze (#76 / #1435)",
      "Computer-section long-lead parts (#3024)"]),
    ("5. Cadence and close, 5 min",
     ["Daily: update your task by 4 pm (note, photo, or state). Exo flags only the slips.",
      "Friday 3 pm: scorecard of committed vs done. A miss gets a cause and a recovery date.",
      "Friday: Exo drafts next week's targets from the board; owners confirm them Tuesday."]),
]

RULES = [
    "Every open BLK3/HVRR task has exactly one owner and a real date. No placeholder dates.",
    "Done means evidence in Mission Control: a file, a photo, or a state change. A verbal \"done\" doesn't count.",
    "A blocker older than 24 hours escalates to John the same day.",
    "No new non-BLK3/HVRR work gets pulled in during the week without John's OK.",
    "Targets are sized to one week. Big tasks are broken into weekly steps.",
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
    p = d.add_paragraph(f"Weekly Plan and Team Meeting Agenda  |  Week of {WEEK_START:%b %d} – {WEEK_END:%b %d, %Y}  |  "
                        "Meeting Tue Sep 29, 10:00–11:00 CT  |  Chair: John Quinn")
    p.runs[0].italic = True
    d.add_paragraph("Standing focus (John, 9/29): BLK3 to flight and the HVRR flight-ready build, until further notice. "
                    "Method: plan the work, work the plan. All targets below are PROPOSED from the Mission Control board. "
                    "Owners confirm or adjust them in the meeting, then they are locked.")
    d.add_heading("Agenda (60 min)", level=1)
    for title, bullets in AGENDA:
        d.add_paragraph(title).runs[0].bold = True
        for b in bullets:
            d.add_paragraph(b, style="List Bullet")
    d.add_heading("Operating rules", level=1)
    for r in RULES:
        d.add_paragraph(r, style="List Number")
    d.add_heading(f"Targets by employee (complete by Fri {WEEK_END:%b %d})", level=1)
    for name, email, role, items in TARGETS:
        d.add_heading(f"{name}  ({role})", level=2)
        t = d.add_table(rows=1, cols=4); t.style = "Table Grid"
        for i, hd in enumerate(["#", "Target", "Done when", "MC"]):
            t.rows[0].cells[i].text = hd
        for n, (tgt, done, ref) in enumerate(items, 1):
            c = t.add_row().cells
            c[0].text, c[1].text, c[2].text, c[3].text = str(n), tgt, done, ref
        set_widths(t, [0.35, 3.9, 1.75, 0.9])
        d.add_paragraph("Committed ☐   Adjusted ☐   Friday: Done ___ / " + str(len(items)))
    d.add_heading("Friday scorecard", level=1)
    t = d.add_table(rows=1, cols=5); t.style = "Table Grid"
    for i, hd in enumerate(["Owner", "Committed", "Done", "Missed: cause", "Recovery date"]):
        t.rows[0].cells[i].text = hd
    for name, _, _, items in TARGETS:
        c = t.add_row().cells; c[0].text = name; c[1].text = str(len(items))
    set_widths(t, [1.6, 0.9, 0.7, 2.4, 1.3])
    d.add_heading("Appendix: other monthly items (handout, not discussed)", level=1)
    d.add_paragraph("The monthly 'What Exo automated' list and the standing finance item (PO7 notes-due, #2982) "
                    "went out in yesterday's email. They are read-ahead only today, to protect meeting time for the build.")
    d.save(OUT)
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
        desc = (f"WEEKLY TARGETS: week of {WEEK_START:%b %d} – {WEEK_END:%b %d} (BLK3 to Flight + HVRR flight-ready build)\n"
                f"Standing focus set by John 2026-09-29: plan the work, work the plan. PROPOSED at the 9/29 meeting. "
                f"Confirm or adjust in the meeting, then these are your commitments for the week.\n\n"
                + "\n".join(f"{n}. {t}\n   Done when: {dn}  [{ref}]" for n, (t, dn, ref) in enumerate(items, 1))
                + f"\n\nDaily: update the referenced tasks by 4 pm. Friday 3 pm: scorecard (committed vs done).\n"
                  f"Plan doc: {os.path.basename(OUT)}")
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
