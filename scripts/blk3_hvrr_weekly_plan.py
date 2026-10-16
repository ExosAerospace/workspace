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

# Proposed targets. Each = (target, done-when evidence, MC task refs). Owners confirm or adjust in the meeting.
TARGETS = [
    ("Phil Eaton", "peaton@exosaero.com", "BLK3 program lead (#1712)", [
        ("BLK3 integrated master schedule: OVERDUE 3 weeks. Every open BLK3 Flight task needs a real owner "
         "and a date back-planned from early-2027 first flight. Deliver the schedule to #1712 by Wed 10/22.",
         "Schedule file attached to #1712 by Wed 10/22 EOD", "#1712"),
        ("Recovery section: post current % complete with photos and close at least one fab step. "
         "No activity since 9/7 — this is the 4th straight week.",
         "Photo + step update on #78", "#78"),
        ("Fin tooling: confirm the machinist job is scheduled (full-size fins, geometry locked). "
         "Send the fin spec package if not yet sent. Note confirmation on #76.",
         "Machinist job scheduled; note on #76", "#76"),
        ("BLK3 restricted drawings (#1872 Cancelled — explain): post a note on #1872 explaining the "
         "cancellation and identify where the drawings requirement lives now (or reopen it).",
         "Note on #1872 explaining cancellation", "#1872"),
        ("$10M building policy: reassign #1374 to Victor per Jon's 9/30 instruction. Close it out.",
         "#1374 reassigned to Victor, state updated", "#1374"),
    ]),
    ("Neil Milburn", "nmilburn@exosaero.com", "HVRR / Hermes PM, BLK3 licensing", [
        ("HVRR flight-ready WBS: add owned, dated subtasks under #3073 for CFD + GNC updates, aerodynamic nose cone, "
         "shock-absorbing landing legs, 14 CFR 101 waiver draft, and CMTF free-flight campaign. Each must have an owner and date.",
         "Subtasks under #3073 with owner and date for all 5 items", "#3073"),
        ("BLK3 Part 450 package: advance at least one WBS section — post its status and any new draft on #2802.",
         "Status note + section advance on #2802", "#2802"),
    ]),
    ("Steve Norsworthy", "snorsworthy@exosaero.com", "Computer section build, long-leads", [
        ("Long-lead items: confirm SDI505 IMU, Athena IV CPU, and Cambium 900 MHz radio are on order. "
         "If not, issue purchase requests this week. Post confirmation on #3024.",
         "Long-lead confirmation + any PRs posted on #3024", "#3024"),
        ("Computer-section build: photograph and log each component installed this week on #3024.",
         "Photos per component on #3024", "#3024"),
    ]),
    ("Mike Talley", "mtalley@exosaero.com", "Fabrication / GSE", [
        ("Bulkheads: post current % complete with photos. OVERDUE 4 weeks — no update since 9/7.",
         "Photo + state on #86", "#86"),
        ("GHe tank envelope: if #3056 He tank decision arrives this week, put the large GHe tank envelope "
         "in the design model and sketch the support concept. Post note on blocker if #3056 still open.",
         "Model screenshot on #90/#92 or blocker note", "#90, #92, #3056"),
        ("Launch stool: inspect it and the scale system, write the repair/modify list. OVERDUE 4 weeks.",
         "Repair/modify list on #102/#103", "#102, #103"),
    ]),
    ("Victor Castilleja", "vcastilleja@exosaero.com", "Shop / build capture, HVRR certs", [
        ("Clean the HVRR tanks (#2409). OVERDUE 3 weeks — no movement since 9/29.",
         "#2409 Done with photo", "#2409"),
        ("Mount the GPS antenna (#82). OVERDUE 4 weeks — no movement since 9/7.",
         "#82 Done with photo", "#82"),
        ("BLK3 cost-fill: send vendor RFQs for the 10 highest-value open lines on #3076. No movement since 9/24.",
         "RFQ list on #3076", "#3076"),
        ("HVRR parts cert log (#2408): scan and log certs for at least 2 more subassemblies.",
         "Updated workbook on #2408", "#2408"),
    ]),
    ("Russ Blink", "rblink@exosaero.com", "Avionics / FSW / telemetry — ESCALATED", [
        ("Telemetry component selection → #94: OVERDUE since 10/2 (4 weeks). Post the selection or a written "
         "gap note by EOD Tuesday. If blocked, state the blocker in writing.",
         "Selection or written gap note on #94 by Tue 10/21", "#94"),
        ("Harness design: interconnect diagram and harness list for the computer section — post draft on #85. "
         "OVERDUE 4 weeks.",
         "Draft on #85", "#85"),
        ("Recovery servo serial control: post status and remaining FSW steps on #80.",
         "Status note on #80", "#80"),
        ("Ground telemetry support quote: send the request and note it on #96.",
         "Request sent, noted on #96", "#96"),
    ]),
    ("John Quinn", "jquinn@exosaero.com", "CEO: owns the plan", [
        ("HP He tank path (#3056): make the final call — Track A (boss seal), B (conformal coating), "
         "or C (new tank). Pressurization section and GHe envelope (Mike #90/#92) are gated on this.",
         "Decision recorded on #3056", "#3056"),
        ("Russ Blink escalation: 4 weeks zero avionics activity. Direct intervention required.",
         "Outcome noted on #3666 or #94", "#3666, #94"),
        ("Run the Friday scorecard: committed vs done by person.", "Scorecard on this plan task", "this task"),
    ]),
    ("Lizi Quinn", "lquinn@exosaero.com", "Payload manifest → build inputs", [
        ("Confirm UTD/Comet status following check-in email sent 10/12. Update #1300 with any changes.",
         "Updated note on #1300 with UTD/Comet confirmation", "#1300"),
    ]),
]

AGENDA = [
    ("1. Mission and rules (John), 5 min",
     ["Until further notice, the team's focus is BLK3 to flight (next vehicle, preparing for first flight "
      "early 2027 under the Part 431→450 transition) and the HVRR flight-ready build.",
      "Method: plan the work, work the plan. Weekly targets are committed Tuesday, updated daily, and scored Friday."]),
    ("2. Wk 10/12–10/16 scorecard, 10 min",
     ["Phil: 0/5 done; master schedule (3 wks overdue), fin tooling, recovery section all open. #1872 cancelled without explanation.",
      "Neil: 1/3 done (PIEE login); HVRR WBS and Part 450 carry forward.",
      "Steve: 0/2 done; long-lead confirmation and build photos not posted.",
      "Mike: 0/3 done; bulkheads/launch stool independent misses; GHe gated on #3056.",
      "Victor: 0/4 done; GPS antenna and HVRR tank cleaning 3–4 weeks overdue.",
      "Russ: 0/4 done — 4 consecutive weeks zero activity. ESCALATE today.",
      "John: 1/3 done (scorecard); He tank decision still open.",
      "Lizi: 1/1 done (payload snapshot 10/12). ✓"]),
    ("3. Critical path walk, 10 min",
     ["BLK3 (Phil): master schedule (blind without it), recovery section, fin tooling, pressurization (gated #3056), "
      "computer section (Steve long-leads), avionics (Russ — 4 weeks dark).",
      "HVRR / Hermes FA9300-26-C-6011 (Neil): WBS subtasks for CFD/GNC, nose cone, landing legs, Part 101 waiver, CMTF."]),
    ("4. Targets by employee for this week, 20 min",
     ["Each owner confirms or adjusts their targets (next pages). Targets are locked in Mission Control after the meeting."]),
    ("5. Blockers and decisions, 10 min",
     ["HP He tank final call (#3056): SSLC Parylene evaluation ongoing — gates pressurization section.",
      "Russ Blink: 4 weeks zero avionics deliverables; John direct intervention required.",
      "Phil master schedule: critical-path tracking is blind without it — 3rd ask.",
      "#1872 cancellation: what happened to the restricted drawings requirement?"]),
    ("6. Cadence and close, 5 min",
     ["Daily: update your task by 4 pm (note, photo, or state change). Exo flags only the slips.",
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
