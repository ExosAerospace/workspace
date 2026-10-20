#!/usr/bin/env python3
"""
MONTHLY MC WORK-MANAGEMENT MEETING PREP — the monthly meeting now runs on the LAST
TUESDAY of the month (10:00-11:00 CT), replacing that week's weekly team meeting.
This prep fires the DAY BEFORE the last Tuesday and: (1) drafts this month's "what Exo
automated" segment from the git log, (2) emails Jon the agenda Word doc, (3) posts a
Discord reminder with the automation draft.
Run by launchd Monday 15:00; self-gates to the day before the last Tuesday. Use --force to test.
"""
import os, sys, subprocess, datetime, re
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from email.message import EmailMessage
try:
    import itar_ear_screen as ee   # public-safety screen before anything can reach the investor report
except Exception:
    ee = None

WS = os.path.expanduser("~/.openclaw/workspace")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
CHANNEL = "channel:1501636814849577050"
AGENDA = os.path.join(WS, "drafts", "MC_Work_Management_Meeting_Agenda.docx")
FORCE = "--force" in sys.argv
# Lizi 10/20: agendas in plain English — no Exobot jargon. The email and Discord reminder below use short, plain
# sentences; acronyms are spelled out; no arrows or symbols standing in for words.
PLAIN_ENGLISH_RULE = "Lizi 10/20: agendas in plain English — no Exobot jargon."


def is_last_tuesday(d):
    return d.weekday() == 1 and (d + datetime.timedelta(days=7)).month != d.month


def month_automations():
    """Draft bullets from git commit subjects in the last ~35 days (feature/automation-ish)."""
    try:
        out = subprocess.run(["git", "-C", WS, "log", "--since=35 days ago", "--pretty=format:%s", "-n", "300"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        out = ""
    kw = re.compile(r"(auto|add|wire|new |enable|build|fix|convert|dedup|registr|assign|schedul|capture|flag)", re.I)
    seen, bullets = set(), []
    for line in out.splitlines():
        s = line.strip()
        if s and kw.search(s) and s.lower() not in seen:
            seen.add(s.lower()); bullets.append(s)
        if len(bullets) >= 12:
            break
    return bullets


def capture_for_investor_report(today, autos):
    """Append operational/work-management progress to this month's investor-report capture,
    GATED: export-screened, and clearly marked as review-and-reframe (not verbatim to investors).
    Jon reviews the compiled monthly report before it goes to David, so he is the final gate."""
    path = os.path.join(WS, "reports", f"monthly-report-capture-{today:%Y-%m}.md")
    safe = []
    for b in autos:
        if ee is None or not ee.screen(b):   # drop anything the export screen flags
            safe.append(b)
    if not safe:
        return
    block = (f"\n\n## OPERATIONS & WORK MANAGEMENT — Mission Control (AI-native operations)\n"
             f"[REVIEW before including in the investor report to David: reframe into investor voice and CUT any "
             f"internal-only / non-public specifics. Captured from the {today:%B} work-management meeting per Jon.]\n"
             f"Operational leverage shipped this month (Exos operating as an AI-native / ExO 3.0 firm):\n"
             + "\n".join(f"- {b}" for b in safe) + "\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(block)


def capture_notes_due(today):
    """Standing monthly inquiry (Jon 2026-09-20): track convertible notes coming due —
    conversion vs cash payout — and prompt David/Kyle to provide the current detail.
    Tracked by Neil in Mission Control (task #2982)."""
    path = os.path.join(WS, "reports", f"monthly-report-capture-{today:%Y-%m}.md")
    block = (
        "\n\n## NOTES DUE — CONVERTIBLE NOTE TRACKING (standing finance item)\n"
        "[Owner: Neil Milburn (MC #2982). David Mitchell + Kyle Ballard PROVIDE the detail each month.]\n"
        "PO7 (2021, 7% simple, 5-yr) convertible notes are reaching maturity in 2026. Jon's read: "
        "all but ~$150K convert to equity and do NOT require cash payout.\n"
        "REQUEST TO DAVID + KYLE this cycle — for every note now due, provide: principal, accrued interest, "
        "maturity date, and status (CONVERTED / CASH PAYOUT DUE / PENDING ELECTION), plus the running cash-payout total.\n"
        "→ Cash payouts reduce cash this year; conversions do not. Feeds the monthly financials report.\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(block)
    return ("Convertible notes coming due: David and Kyle will report which 2021 PO7 notes turn into shares and "
            "which must be paid back in cash (estimated cash payout about $150K). Neil tracks this on Mission Control task #2982.")


def is_day_before_last_tuesday(d):
    nxt = d + datetime.timedelta(days=1)
    return nxt.weekday() == 1 and (nxt + datetime.timedelta(days=7)).month != nxt.month


def main():
    today = datetime.date.today()
    if not (FORCE or is_day_before_last_tuesday(today)):
        print(f"{today} is not the day before the last Tuesday — skipping."); return
    meeting_day = today + datetime.timedelta(days=1)

    autos = month_automations()
    auto_txt = "\n".join("- " + b for b in autos) if autos else "- I will fill this in from the work finished this month."
    # route investor-appropriate operational progress into the monthly-report capture (gated + screened)
    try:
        capture_for_investor_report(today, autos)
    except Exception as e:
        print("investor-capture error:", e)
    # standing monthly inquiry: convertible notes coming due (David/Kyle provide detail; Neil tracks)
    notes_due_line = ""
    try:
        notes_due_line = capture_notes_due(today)
    except Exception as e:
        print("notes-due-capture error:", e)

    # 1) email Jon the agenda doc
    try:
        m = EmailMessage()
        m["From"] = "Exo (Exos AI Assistant) <jquinnexo@pm.me>"
        m["To"] = "jquinn@exosaero.com"
        m["Subject"] = f"Tomorrow: Monthly Work Meeting agenda, and what Exobot automated this month ({meeting_day:%b %-d})"
        m.set_content(
            f"Hello Jon,\n\nTomorrow ({meeting_day:%A, %B %-d}) is the monthly Work Meeting, where we review how we use "
            "Mission Control. The agenda is attached.\n\nDraft for section 2, what Exobot automated this month. "
            "It is taken from the list of software changes, so some lines may need rewording:\n"
            + auto_txt
            + (f"\n\nFinance item we cover every month:\n- {notes_due_line}" if notes_due_line else "")
            + "\n\nReply if you want any of this reworded before the meeting.\n\nExo")
        if os.path.isfile(AGENDA):
            try:  # Lizi 10/20: every task ref on an agenda carries its live MC status
                sys.path.insert(0, os.path.join(WS, "scripts")); import agenda_task_status
                agenda_task_status.annotate_docx(AGENDA)
            except Exception as e:
                print("agenda status stamp failed:", e)
            m.add_attachment(open(AGENDA, "rb").read(), maintype="application",
                             subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                             filename=os.path.basename(AGENDA))
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", "jquinn@exosaero.com"],
                       input=m.as_bytes(), timeout=60, capture_output=True)
    except Exception as e:
        print("email error:", e)

    # 2) Discord reminder
    msg = (f"📅 **Monthly Work Meeting tomorrow ({meeting_day:%a %b %-d})**\n"
           f"60 minutes. Topics: review of the work; how Exobot improved itself; teaching; ideas from the team "
           f"to work better; action items.\n"
           f"The agenda was emailed to Jon. Draft list of what Exobot automated this month:\n{auto_txt}\n"
           f"After the meeting, email the meeting notes with [TRANSCRIPT] in the subject line, and I will add the action items to Mission Control.")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", CHANNEL, "-m", msg],
                       timeout=60, capture_output=True)
    except Exception as e:
        print("discord error:", e)
    print(f"prepped meeting for {meeting_day} (day-before delivery).")


if __name__ == "__main__":
    main()
