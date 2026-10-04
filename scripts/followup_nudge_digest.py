#!/usr/bin/env python3
"""followup_nudge_digest.py — daily "Follow-ups due" DM to Jon.

Reads logs/sent-followup-log.json (built by sent_followup_tracker.py). Surfaces contacts Jon emailed
who have NOT replied, where the last send is between MIN and MAX days old (recent enough to chase,
not so old it's dead). One batched DM, deduped so a given contact re-nudges at most every RENUDGE days.
--dry-run prints, sends nothing.
"""
import time
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
    # A send to several people is ONE thread: if any recipient of that same send replied afterwards, or
    # anyone at the same org domain replied after it, the thread is answered (10/4: Graham + Raquel were
    # flagged "no reply" though Michael Sheldon had answered the same Ainigma email).
    def norm_subj(x):
        x = dec(x or "").strip().lower()
        while x[:3] in ("re:", "fw:") or x[:4] == "fwd:":
            x = x.split(":", 1)[1].strip()
        return x
    BROAD = ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com", "proton.me",
             "protonmail.com", "pm.me", "me.com", "live.com", "msn.com", "sbcglobal.net", "comcast.net")
    def domain(a):
        d = a.rsplit("@", 1)[-1].lower()
        # big shared domains (free mail, .mil/.gov/.edu) are not one org — never merge on them
        return None if d in BROAD or d.endswith((".mil", ".gov", ".edu")) else d
    answered_sends, org_reply = set(), {}
    for a, c in contacts.items():
        if c.get("replied") and c.get("last_reply"):
            answered_sends.add((c.get("last_sent"), norm_subj(c.get("subj"))))
            d = domain(a)
            if d and c["last_reply"] > org_reply.get(d, ""):
                org_reply[d] = c["last_reply"]

    for a, c in contacts.items():
        if c.get("replied") or c.get("cleared") or not c.get("last_sent"):
            continue
        if (c["last_sent"], norm_subj(c.get("subj"))) in answered_sends:
            continue
        if domain(a) and org_reply.get(domain(a), "") > c["last_sent"]:
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
        # Retry: a gateway restart/outage makes the send hang (10/2 run died on an uncaught TimeoutExpired).
        err = ""
        for attempt in range(3):
            if attempt:
                time.sleep(45)
            try:
                r = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", "user:" + JON,
                                    "-m", msg], capture_output=True, text=True, timeout=90, env=env())
                if r.returncode == 0:
                    break
                err = f"rc={r.returncode}: {(r.stderr or r.stdout or '').strip()[:300]}"
            except subprocess.TimeoutExpired:
                err = "timed out after 90s (gateway unreachable?)"
            print(f"WARN: discord send attempt {attempt + 1}/3 failed — {err}", file=sys.stderr)
        else:   # don't mark as nudged — the batch retries next run
            print(f"ERROR: discord send failed after 3 attempts — {err}", file=sys.stderr)
            sys.exit(1)
        for age, name, a, subj, tid in batch:   # mark ONLY the 5 sent (rest reappear tomorrow)
            st[a] = now.isoformat()
        json.dump(st, open(STATE, "w"), indent=2)


if __name__ == "__main__":
    main()
