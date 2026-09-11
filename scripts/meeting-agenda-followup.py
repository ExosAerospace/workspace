#!/usr/bin/env python3
"""Conditional follow-up on the 8/25 monthly meeting agenda sent to John for approval.

Two one-shot launchd modes:
  --mode nudge  (today 8/24 ~14:30 CT): if John hasn't replied/approved, nudge him (email + Discord DM).
  --mode neil   (8/25 08:00 CT):        if John still hasn't approved, send the FINAL agenda to Neil to run.

"Approved / engaged" = any email FROM jquinn@exosaero.com in the inbox since 2026-08-24 whose subject
references the agenda (he replied to the approval thread). If John engaged, both modes stand down.

Each mode self-unloads its launchd job after running so nothing recurs.
"""
import os, sys, imaplib, email, socket, subprocess
socket.setdefaulttimeout(40)

MODE = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else ""
IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER, EMAIL_PASS = "jquinnexo@pm.me", __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
JOHN = "jquinn@exosaero.com"
LIZI = "lquinn@exosaero.com"
NEIL = "nmilburn@exosaero.com"
JON_DISCORD = "1501632195163590739"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"
LABELS = {"nudge": "com.exos.meeting-agenda-nudge", "neil": "com.exos.meeting-agenda-neil"}

AGENDA = """AGENDA — Mission Control Work Management Meeting (60 min)
Tuesday, August 25, 2026, 9:00 AM Central

NOTE: John and Lizi are traveling (in the air) and cannot attend. Neil to run the meeting. Please RECORD it so John and Lizi can re-watch.

1. Work Management Review (15): board status (open/blocked/overdue); action items auto-captured from Teams minutes; priorities and North Star alignment (Series A / Revenue / Part 450); confirm owners and due dates.
   Added focus items this month:
   - Texas STEP grant — Japan trade-mission application: complete and ready to submit (deadline Sept 10); confirm final budget option and submit.
   - Japan October trip (John + Toshi): HOSPO / SPACE COTAN + JETRO sessions; Exos Aerospace Japan entity formation.

2. Recursive Self-Improvement (10): what Exo automated this month and how each item helps.

3. Teaching Session (10): hands-on how-to on one Mission Control / Exobot capability.

4. Continuous Improvement and Employee Input (20): open floor; ideas captured live as Mission Control items; triage the top improvement.

5. Action Items and Close (5): confirm action items (auto-logged and assigned); set next meeting.

ZERO ADMIN: email the meeting minutes with [TRANSCRIPT] in the subject line and Exo auto-creates and assigns the action items."""


def john_engaged():
    """True if John has replied to the approval thread (subject references the agenda)."""
    try:
        m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.starttls(); m.login(EMAIL_USER, EMAIL_PASS)
        m.select("INBOX", readonly=True)
        typ, data = m.search(None, "FROM", JOHN, "SINCE", "24-Aug-2026", "SUBJECT", "agenda")
        hit = bool(data and data[0] and data[0].split())
        m.logout()
        return hit
    except Exception as e:
        print("imap check failed (assume not engaged):", e)
        return False


def send(to_list, cc, subject, body):
    from email.message import EmailMessage
    m = EmailMessage()
    m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = ", ".join(to_list)
    if cc: m["Cc"] = cc
    m["Subject"] = subject; m.set_content(body)
    rcpts = to_list + ([cc] if cc else [])
    subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail"] + rcpts,
                   input=m.as_bytes(), check=True, timeout=90)


def self_unload():
    label = LABELS.get(MODE)
    if not label: return
    uid = os.getuid()
    plist = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
    try: subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"], capture_output=True)
    except Exception: pass
    try:
        if os.path.exists(plist): os.remove(plist)
    except Exception: pass


def main():
    engaged = john_engaged()
    if engaged:
        print(f"[{MODE}] John has engaged/approved — standing down."); self_unload(); return

    if MODE == "nudge":
        body = (f"Hi Jon,\n\nQuick nudge — tomorrow's monthly meeting agenda (Tue 8/25, 9:00 AM CT) is waiting "
                f"for your approval so it can go to Neil to run while you and Lizi are traveling.\n\n"
                f"Please reply 'approved' (with any edits) and forward to Neil (nmilburn@exosaero.com), or just "
                f"reply and I'll send the final to Neil for you. If I don't hear back, I'll send the agenda to "
                f"Neil at 8:00 AM CT tomorrow so he has it before the meeting.\n\n— Exo\n")
        send([JOHN], LIZI, "Nudge: approve tomorrow's meeting agenda (Tue 8/25) for Neil", body)
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON_DISCORD,
                            "-m", "📋 Nudge: tomorrow's 8/25 meeting agenda is waiting on your approval to send to Neil. "
                                  "Reply approved (or I'll send it to Neil at 8am CT so he can run it while you + Lizi travel)."],
                           timeout=60, capture_output=True)
        except Exception: pass
        print("[nudge] sent nudge to John (email + Discord).")

    elif MODE == "neil":
        body = (f"Hi Neil,\n\nJohn and Lizi are traveling (in the air) and cannot attend tomorrow's monthly "
                f"Mission Control Work Management Meeting (Tuesday 8/25, 9:00 AM CT). Could you please run it, and "
                f"RECORD it so John and Lizi can re-watch afterward?\n\nThe agenda is below. Reminder: email the "
                f"minutes with [TRANSCRIPT] in the subject line and Exo will auto-create and assign the action items.\n\n"
                f"{AGENDA}\n\nThank you,\nExo (for John)\n")
        send([NEIL], f"{JOHN}, {LIZI}", "Please run tomorrow's Work Management Meeting (Tue 8/25, 9am CT) + record", body)
        print("[neil] sent final agenda to Neil (cc John + Lizi).")

    else:
        print("unknown mode:", MODE); return

    self_unload()


if __name__ == "__main__":
    main()
