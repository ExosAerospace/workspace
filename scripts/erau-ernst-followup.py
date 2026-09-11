#!/usr/bin/env python3
"""One-shot reminder (Mon 2026-08-31, 9:00 CT): if Jeremy Ernst (ERAU) hasn't replied with his
researcher questions since the 8/24 call, remind Lizi to follow up. If he has replied, stand down.
Self-unloads after running (launchd com.exos.erau-ernst-followup)."""
import os, imaplib, socket, subprocess
socket.setdefaulttimeout(40)
IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER, EMAIL_PASS = "jquinnexo@pm.me", __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
LIZI = "lquinn@exosaero.com"
LIZI_DISCORD = "1506647219351060631"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"
LABEL = "com.exos.erau-ernst-followup"


def ernst_replied():
    try:
        m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.starttls(); m.login(EMAIL_USER, EMAIL_PASS)
        m.select("INBOX", readonly=True)
        for addr in ("ernstj1@erau.edu", "jeremy.ernst@erau.edu"):
            typ, data = m.search(None, "FROM", addr, "SINCE", "24-Aug-2026")
            if data and data[0] and data[0].split():
                m.logout(); return True
        m.logout(); return False
    except Exception as e:
        print("imap check failed (assume no reply):", e); return False


def self_unload():
    uid = os.getuid()
    plist = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
    try: subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    except Exception: pass
    try:
        if os.path.exists(plist): os.remove(plist)
    except Exception: pass


def main():
    if ernst_replied():
        print("Ernst replied — standing down."); self_unload(); return
    from email.message import EmailMessage
    body = ("Hi Lizi,\n\nReminder: it's been a week since the 8/24 Embry-Riddle call and Jeremy Ernst "
            "(VP Research, ernstj1@erau.edu) hasn't sent his researchers' questions yet. Might be worth a "
            "quick nudge to keep it warm, and to confirm ERAU interest in being named in the NIH Sept 8 "
            "briefing. Want me to draft the follow-up? Just ask.\n\n— Exo\n")
    m = EmailMessage(); m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = LIZI
    m["Subject"] = "Reminder: nudge Jeremy Ernst (ERAU) — questions not in yet"
    m.set_content(body)
    try:
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", LIZI],
                       input=m.as_bytes(), check=True, timeout=60)
        print("reminder emailed to Lizi")
    except Exception as e:
        print("email failed:", e)
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", LIZI_DISCORD,
                        "-m", "📌 Reminder: Jeremy Ernst (ERAU) hasn't sent his researchers' questions yet "
                              "(a week since the 8/24 call). Want me to draft a nudge + confirm the NIH Sept 8 name-drop?"],
                       timeout=60, capture_output=True)
    except Exception: pass
    self_unload()


if __name__ == "__main__":
    main()
