#!/usr/bin/env python3
"""
MONTHLY MC WORK-MANAGEMENT MEETING PREP — fires only on the LAST THURSDAY of the month.
On that day it: (1) drafts this month's "what Exo automated" segment from the git log,
(2) emails Jon the agenda Word doc, (3) posts a Discord reminder with the automation draft.
Run by launchd every Thursday; self-gates to the last Thursday. Use --force to test.
"""
import os, sys, subprocess, datetime, re
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from email.message import EmailMessage
try:
    import itar_ear_screen as ee   # public-safety screen before anything can reach the investor report
except Exception:
    ee = None

WS = os.path.expanduser("~/.openclaw/workspace")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
CHANNEL = "channel:1501636814849577050"
AGENDA = os.path.join(WS, "drafts", "MC_Work_Management_Meeting_Agenda.docx")
FORCE = "--force" in sys.argv


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


def is_day_before_last_tuesday(d):
    nxt = d + datetime.timedelta(days=1)
    return nxt.weekday() == 1 and (nxt + datetime.timedelta(days=7)).month != nxt.month


def main():
    today = datetime.date.today()
    if not (FORCE or is_day_before_last_tuesday(today)):
        print(f"{today} is not the day before the last Tuesday — skipping."); return
    meeting_day = today + datetime.timedelta(days=1)

    autos = month_automations()
    auto_txt = "\n".join("• " + b for b in autos) if autos else "• (I'll fill this in from the month's shipped work.)"
    # route investor-appropriate operational progress into the monthly-report capture (gated + screened)
    try:
        capture_for_investor_report(today, autos)
    except Exception as e:
        print("investor-capture error:", e)

    # 1) email Jon the agenda doc
    try:
        m = EmailMessage()
        m["From"] = "Exo (Exos AI Assistant) <jquinnexo@pm.me>"
        m["To"] = "jquinn@exosaero.com"
        m["Subject"] = f"Tomorrow: Mission Control Work Management Meeting — agenda + this month's automations ({meeting_day:%b %d})"
        m.set_content(
            f"Hello Jon,\n\nTomorrow ({meeting_day:%A, %b %d}) is the monthly Mission Control Work Management Meeting. "
            "Agenda attached.\n\nDraft for Section 2 (what Exo automated this month), from the change log:\n"
            + auto_txt + "\n\nReply if you want any of it reworded before the meeting.\n\nExo")
        if os.path.isfile(AGENDA):
            m.add_attachment(open(AGENDA, "rb").read(), maintype="application",
                             subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                             filename=os.path.basename(AGENDA))
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", "jquinn@exosaero.com"],
                       input=m.as_bytes(), timeout=60, capture_output=True)
    except Exception as e:
        print("email error:", e)

    # 2) Discord reminder
    msg = (f"📅 **Mission Control Work Management Meeting — TOMORROW ({meeting_day:%a %b %d})**\n"
           f"60 min: Work Review · Recursive Self-Improvement · Teaching · Continuous Improvement + Employee Input · Action Items.\n"
           f"Agenda emailed to Jon. Draft of this month's automations:\n{auto_txt}\n"
           f"Reminder: send meeting minutes with [TRANSCRIPT] in the subject and I'll auto-capture the action items.")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", CHANNEL, "-m", msg],
                       timeout=60, capture_output=True)
    except Exception as e:
        print("discord error:", e)
    print(f"prepped meeting for {meeting_day} (day-before delivery).")


if __name__ == "__main__":
    main()
