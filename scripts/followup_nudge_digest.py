#!/usr/bin/env python3
"""followup_nudge_digest.py — daily "Follow-ups due" DM to Jon.

Reads logs/sent-followup-log.json (built by sent_followup_tracker.py). Surfaces contacts Jon emailed
who have NOT replied, where the last send is between MIN and MAX days old (recent enough to chase,
not so old it's dead). One batched DM, deduped so a given contact re-nudges at most every RENUDGE days.
--dry-run prints, sends nothing.
"""
import json, os, sys, subprocess
from datetime import datetime, timezone
from email.header import decode_header


def dec(s):
    try:
        return "".join((b.decode(c or "utf-8", "ignore") if isinstance(b, bytes) else b)
                       for b, c in decode_header(s or "")).strip()
    except Exception:
        return s or ""

WS = os.path.expanduser("~/.openclaw/workspace")
LOG = os.path.join(WS, "logs", "sent-followup-log.json")
STATE = os.path.join(WS, "logs", "followup-nudge-state.json")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
JON = "1501632195163590739"
# 7d before a first nudge; stop chasing past 45d; re-nudge the SAME contact at most every 10d
# (outreach-appropriate, not aggressive); feed at most 5/day so the backlog drains gently.
MIN_DAYS, MAX_DAYS, RENUDGE, MAX_PER_DAY = 7, 45, 10, 5


def env():
    e = dict(os.environ)
    e["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.21.0/bin:/opt/homebrew/bin:"
                 "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    return e


def age_days(iso, now):
    try:
        d = datetime.fromisoformat(iso)
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return (now - d).total_seconds() / 86400.0
    except Exception:
        return -1


def main():
    dry = "--dry-run" in sys.argv
    now = datetime.now(timezone.utc)
    try:
        contacts = json.load(open(LOG)).get("contacts", {})
    except Exception:
        print("no follow-up log yet"); return
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}

    due = []
    for a, c in contacts.items():
        if c.get("replied") or c.get("cleared") or not c.get("last_sent"):
            continue
        age = age_days(c["last_sent"], now)
        if age < MIN_DAYS or age > MAX_DAYS:
            continue
        last_nudge = st.get(a)
        if last_nudge and age_days(last_nudge, now) < RENUDGE:
            continue
        due.append((int(age), c.get("name", a), a, dec(c.get("subj", "")), c.get("task_id")))

    if not due:
        print("no follow-ups due"); return
    due.sort(reverse=True)                 # oldest first — chase the most overdue
    batch = due[:MAX_PER_DAY]              # at most 5/day; the rest wait for tomorrow
    remaining = len(due) - len(batch)
    lines = ["📮 **Follow-ups due** — no reply yet (up to 5/day):"]
    for age, name, a, subj, tid in batch:
        tag = f" · task #{tid}" if tid else ""
        lines.append(f"• **{age}d** — {name} <{a}>{tag}\n   ↳ {subj[:70]}")
    if remaining > 0:
        lines.append(f"…{remaining} more queued — I'll feed 5/day until you're caught up.")
    lines.append("✓ Clear answered ones: https://mc.exosaero.space/followups.html")
    msg = "\n".join(lines)[:1900]
    print(msg)
    if not dry:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", "user:" + JON, "-m", msg],
                       capture_output=True, text=True, timeout=60, env=env())
        for age, name, a, subj, tid in batch:   # mark ONLY the 5 sent (rest reappear tomorrow)
            st[a] = now.isoformat()
        json.dump(st, open(STATE, "w"), indent=2)


if __name__ == "__main__":
    main()
