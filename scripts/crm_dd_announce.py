#!/usr/bin/env python3
"""Announce the CRM auto-DD feature to the team ONCE, after the nightly engine clears the CRM.
Posts to the team Discord channel + emails the leadership. Guarded by a sent-marker (never double-sends).
  python3 scripts/crm_dd_announce.py           # sends only if complete + not already sent
  python3 scripts/crm_dd_announce.py --force    # send now regardless
"""
import os, sys, json, subprocess, datetime
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from email.message import EmailMessage

WS = os.path.expanduser("~/.openclaw/workspace")
MARK = os.path.join(WS, "logs", "crm-dd-announced.flag")
FLAG = os.path.join(WS, "logs", "crm-dd-complete.flag")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
CHAN = "1501635980975804590"   # #general team channel
TEAM = ["snorsworthy@exosaero.com", "peaton@exosaero.com", "lquinn@exosaero.com", "jquinn@exosaero.com"]
FORCE = "--force" in sys.argv

MSG = ("New in Mission Control: automatic due diligence on every company in our CRM. Each company now "
       "shows a DD badge (pass / caution / fail) with the date it was checked, and any company that fails "
       "DD is flagged with a red glowing box so it is impossible to miss. The system screens the whole CRM "
       "overnight, re-checks new companies automatically as they are added, and flags SAM.gov debarment and "
       "OFAC sanctions hits. Want DD on a specific company? Email @Exobot (exosmc@pm.me) or ask in Mission "
       "Control and it will run the check and log the result so the whole team can see it and nobody "
       "duplicates work.")


def main():
    if os.path.exists(MARK):
        print("already announced"); return
    if not (FORCE or os.path.exists(FLAG)):
        print("CRM DD not complete yet; not announcing"); return
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", CHAN,
                        "-m", "📋 " + MSG + "\n— Exo"], timeout=60, capture_output=True)
    except Exception as e:
        print("discord failed:", e)
    for to in TEAM:
        try:
            m = EmailMessage(); m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = to
            m["Subject"] = "New in Mission Control — automatic company due diligence on the CRM"
            m.set_content("Hello,\n\n" + MSG + "\n\nExo\n")
            subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", to],
                           input=m.as_bytes(), timeout=60, capture_output=True)
        except Exception as e:
            print("email failed", to, e)
    open(MARK, "w").write(datetime.datetime.now().isoformat())
    print("announcement sent + marked")


if __name__ == "__main__":
    main()
