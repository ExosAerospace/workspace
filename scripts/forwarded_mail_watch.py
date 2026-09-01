#!/usr/bin/env python3
"""
forwarded_mail_watch.py — near-real-time watcher over Jon's forwarded M365 inbound.

Runs every few minutes (launchd com.exos.forwarded-mail-watch). Uses forwarded_mail.scan()
to find mail Jon forwards from Outlook to Proton, dedups against state, keeps a rolling feed
the capture agents read (so they always have the latest), and posts ONE concise Discord line
to #series-a for each NEW high-signal forward (gov approvals, PI/counterparty replies). First
run baselines silently. Quiet 23:00-08:00 CT for alerts (feed still updates).
"""
import json, os, re, sys, subprocess, shutil
from datetime import datetime
sys.path.insert(0, os.path.join("/Users/exomac/.openclaw/workspace", "scripts"))
import forwarded_mail as fm

WS = "/Users/exomac/.openclaw/workspace"
SEEN = os.path.join(WS, "logs", "forwarded-mail-seen.json")
FEED = os.path.join(WS, "mission-control", "data", "forwarded-inbound.json")
DISCORD = "channel:1501636728711282741"  # #series-a
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"
# high-signal = worth a ping (gov / PI / active-pursuit); everything else just updates the feed
HIGH = re.compile(r"nih\.gov|\.gov\b|\.mil\b|purdue\.edu|uw\.edu|noaa|nasa|era ?commons|"
                  r"institution registration|approv|kelly|park|collicott|teasley|murphy|"
                  r"subaward|solicitation|award|contract", re.I)

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def quiet_hours():
    try:
        h = int(subprocess.run(["date", "+%H"], capture_output=True, text=True).stdout.strip())
        return h >= 23 or h < 8
    except Exception:
        return False

def main():
    rows = fm.scan(since_days=3)
    seen = set(load(SEEN, []))
    first = not seen
    new = [r for r in rows if r["id"] not in seen]
    for r in rows:
        seen.add(r["id"])
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    json.dump(sorted(seen)[-4000:], open(SEEN, "w"))
    # rolling feed (latest 50) — always current for the capture agents
    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    json.dump({"updated": datetime.utcnow().isoformat(timespec="seconds") + "Z",
               "items": rows[:50]}, open(FEED, "w"), indent=2)
    print(f"forwarded-mail-watch: {len(rows)} forwards in window, {len(new)} new"
          + (" (first run — baselined, no alert)" if first else ""))
    if first or not new:
        return
    hot = [r for r in new if HIGH.search(r["subject"] + " " + r["forwarded_from"] + " " + r["snippet"])]
    if not hot or quiet_hours():
        return
    lines = ["📥 **Caught your forward(s)** — now in the inbound feed:"]
    for r in hot[:6]:
        who = r["forwarded_from"] if "@" in r["forwarded_from"] else "unparsed sender"
        lines.append(f"• **{who}** — {r['subject'][:70]}\n    “{r['snippet'][:130]}”")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD, "-m", "\n".join(lines)], capture_output=True, timeout=60)
    except Exception as e:
        print("alert failed:", e)

if __name__ == "__main__":
    main()
