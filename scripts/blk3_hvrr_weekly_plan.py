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

WEEK_START = datetime.date(2026, 10, 12)
WEEK_END = datetime.date(2026, 10, 16)
WK = f"{WEEK_START:%Y-%m-%d}"
SOURCE = f"exo-blk3-hvrr-weekly-{WK}"
OUT = os.path.join(WS, "drafts", f"BLK3_HVRR_Weekly_Plan_and_Meeting_Agenda_{WK}.docx")

# Proposed targets. Each = (target, done-when evidence, MC task refs). Owners confirm or adjust in the meeting.
TARGETS = [
    ("Phil Eaton", "peaton@exosaero.com", "BLK3 program lead (#1712)", [
        ("BLK3 integrated master schedule: every open BLK3 Flight task gets a real owner and a due date "
         "back-planned from the flight date. This was due wk 9/28 and is still open — deliver by Wed 10/14.",
         "Schedule attached to #1712 by Wed 10/14 EOD", "#1712"),
        ("Recovery section: list the remaining fab steps with % complete, and close at least one step this week. "
         "No activity since 9/7 — post a note with current status.",
         "Step list + photo on #78", "#78"),
        ("Fin tooling: pull the original fin spec package (John located it this weekend), send it to the machinist, "
         "and confirm the tooling job is scheduled. Geometry is locked: full-size fins. (#76 action from 10/6 meeting.)",
         "Machinist job confirmed; note on #76", "#76"),
        ("BLK3 restricted drawings (overdue since 8/22): release to #1872.",
         "Drawings attached on #1872", "#1872"),
        ("$10M building policy inquiry: complete the reassignment to Victor on #1374 (Jon's instruction from 9/30).",
         "#1374 reassigned to Victor", "#1374"),
    ]),
    ("Neil Milburn", "nmilburn@exosaero.com", "HVRR / Hermes PM, BLK3 licensing", [
        ("HVRR flight-ready WBS: break the remaining Hermes SOW work into owned, dated tasks — specifically: "
         "CFD + GNC updates, aerodynamic nose cone, shock-absorbing landing legs, 14 CFR 101 waiver draft, "
         "insurance, CMTF free-flight campaign. Add each as a subtask under #3073 with owner and date.",
         "Subtasks under #3073, each with an owner and date", "#3073"),
        ("BLK3 Part 450 package: advance the next WBS section (post its status and any new draft on #2802).",
         "Status note + advance on #2802", "#2802, #2693"),
        ("PIEE login: complete the 30-day re-login on #3250 to keep the account active.",
         "#3250 Done", "#3250"),
    ]),
    ("Steve Norsworthy", "snorsworthy@exosaero.com", "Computer section build, inventory", [
        ("Computer section: confirm the 3 long-lead items (SDI505 IMU, Athena IV CPU, Cambium 900 MHz radio) — "
         "are they on order? If not, issue purchase requests this week.",
         "Long-lead confirmation + any PRs on #3024", "#3024"),
        ("Computer-section build capture: photograph and log each component installed this week on #3024.",
         "Photos per component on #3024", "#3024"),
    ]),
    ("Mike Talley", "mtalley@exosaero.com", "Fabrication / GSE", [
        ("Bulkheads: post current % complete with photos. No update since 9/7.", "Photo + state on #86", "#86"),
        ("GHe tank envelope: once Jon resolves the HP He tank path (#3056), put the large GHe tank envelope "
         "in the design model and sketch the support concept. Monitor #3056 this week.",
         "Model screenshot on #90/#92 (or note on blocker if #3056 still open)", "#90, #92, #3056"),
        ("Launch stool: inspect it and the scale system, write the repair/modify list. No update since 9/7.",
         "List on #102/#103", "#102, #103"),
    ]),
    ("Victor Castilleja", "vcastilleja@exosaero.com", "Shop / build capture, HVRR certs", [
        ("Clean the HVRR tanks (#2409). No movement since 9/29.", "#2409 Done with photo", "#2409"),
        ("Mount the GPS antenna (#82). No movement since 9/7.", "#82 Done with photo", "#82"),
        ("BLK3 cost-fill: send vendor RFQs for the 10 highest-value open lines on #3076.",
         "RFQ list on #3076", "#3076"),
        ("HVRR parts cert log (#2408, now assigned to you): scan and log certs for at least 2 more subassemblies "
         "(Steve logged 3 PDFs; 7 subassemblies total).",
         "Updated workbook on #2408", "#2408"),
    ]),
    ("Russ Blink", "rblink@exosaero.com", "Avionics / FSW / telemetry", [
        ("Telemetry component selection: OVERDUE since 10/2. Post the selection (or a written gap note) on #94.",
         "Selection or gap note on #94", "#94"),
        ("Harness design: interconnect diagram and harness list for the computer section — post draft on #85.",
         "Draft on #85", "#85"),
        ("Recovery servo serial control: post status and remaining FSW steps on #80.",
         "Note on #80", "#80"),
        ("Ground telemetry support quote: send the request and note it on #96.",
         "Request sent, noted on #96", "#96"),
    ]),
    # John is in Japan ~10/12 — targets are light/async
    ("John Quinn", "jquinn@exosaero.com", "CEO: owns the plan (Japan trip ~10/12)", [
        ("HP He tank path (#3056): make the call — re-test track A/B/C or procure new tank. "
         "Pressurization section and GHe envelope (Mike) are gated on this. Async OK.",
         "Decision recorded on #3056", "#3056"),
        ("Run the Friday scorecard: committed vs done by person.", "Scorecard on this plan task", "this task"),
    ]),
    ("Lizi Quinn", "lquinn@exosaero.com", "Payload manifest → build inputs", [
        ("Update the payload snapshot on #1300 with any new commitments or changes since 9/30 "
         "(UCI status, UTD/Comet confirmation). Engineering needs current numbers for integration design.",
         "Updated snapshot on #1300", "#1300, #2360"),
    ]),
]

AGENDA = [
    ("1. Mission and rules (John), 5 min",
     ["Until further notice, the team's focus is BLK3 to flight and the HVRR flight-ready build.",
      "Method: plan the work, work the plan. Weekly targets are committed Tuesday, updated daily, and scored Friday.",
      "Note: John is traveling to Japan ~10/12; async participation this week."]),
    ("2. Wk 9/28–10/9 scorecard (2 weeks), 10 min",
     ["Phil: 1/6 done; master schedule and drawings still open.",
      "Neil: 2/4 done (kick-off + CUI); WBS and Part 450 carry forward.",
      "Steve: 2/4 done (inventory closeout + cost-fill); computer-section carry forward.",
      "Mike: 0/3 done; GSE/fab work blocked or untouched.",
      "Victor: 0/4 done; GPS antenna, HVRR tanks, cost-fill RFQs all open.",
      "Russ: 0/4 done; all avionics targets untouched — escalation required.",
      "John: 1/3 done (He tank partial); master schedule approval and scorecard carry forward.",
      "Lizi: 1/1 done (payload snapshot)."]),
    ("3. Critical path walk, 10 min",
     ["BLK3 (Phil): recovery section, fin tooling (geometry locked—full-size), pressurization (GHe; gated on #3056), "
      "computer/avionics section (Steve/Victor), telemetry/FSW (Russ), master schedule (still open).",
      "HVRR / Hermes FA9300-26-C-6011 (Neil): kicked off; CLIN0001 invoiced. "
      "WBS subtasks needed for CFD/GNC, nose cone, landing legs, Part 101 waiver, CMTF campaign."]),
    ("4. Targets by employee for this week, 20 min",
     ["Each owner confirms or adjusts their targets (next pages). Targets are locked in Mission Control after the meeting."]),
    ("5. Blockers and decisions, 10 min",
     ["HP He tank final call (#3056): re-test track A/B/C or new tank — gates pressurization section.",
      "Russ Blink: zero activity on avionics for 2 weeks; escalate today.",
      "Phil master schedule: critical-path visibility is zero without it.",
      "BLK3 restricted drawings (#1872): overdue since 8/22."]),
    ("6. Cadence and close, 5 min",
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
