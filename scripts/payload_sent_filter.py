#!/usr/bin/env python3
"""
payload_sent_filter.py — deterministic gate that keeps the payload crons from re-serving
outreach that Jon has already emailed.

The payload crons ("Payload Sales — 3 a day", "Exos Sales Agent", "BLK3 Payload Sales")
stage READY drafts from capture/Draft_*.md. Relying on the agent to *remember* what was
already sent is unreliable — it re-served Space Tango after Jon had sent it. This gate is
deterministic: it reads the authoritative sent-registry (logs/outreach-sent-registry.json,
maintained by sent-loop-closer.py from Jon's sent copies) and MOVES any draft whose
recipient was already emailed into capture/sent/, so the crons physically cannot pick it up.

Matching (any one is enough):
  1. The draft file is listed as a tracker on a sent recipient in the registry.
  2. Any email address appearing in the draft body is a sent recipient (fuzzy on local-part
     to tolerate alias variants, e.g. thomas.teasley vs thomas.w.teasley).

Reversible: drafts are MOVED to capture/sent/, never deleted, and every move is logged and
annotated into capture/Sales_Pipeline.md. Idempotent: safe to run every cycle.
"""
import json, os, re, glob, shutil, datetime

WS       = "/Users/exomac/.openclaw/workspace"
REGISTRY = os.path.join(WS, "logs", "outreach-sent-registry.json")
POOL     = os.path.join(WS, "capture")
SENT_DIR = os.path.join(POOL, "sent")
PIPELINE = os.path.join(POOL, "Sales_Pipeline.md")
LOG      = os.path.join(WS, "logs", "payload-sent-filter.log")
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(m.rstrip() + "\n")


def load_registry():
    try:
        return json.load(open(REGISTRY))
    except Exception:
        return {}


def local_part(addr):
    # normalize local-part for fuzzy alias matching: drop middle-initial style tokens
    lp = addr.split("@")[0].lower()
    return lp.replace(".", "")


def main():
    reg = load_registry()
    sent_emails = {k.lower() for k in reg.keys()}
    sent_localdomain = {}
    for k in reg.keys():
        if "@" in k:
            sent_localdomain.setdefault(k.split("@")[-1].lower(), set()).add(local_part(k))
    sent_files = set()
    for v in reg.values():
        for t in (v.get("trackers") or []):
            sent_files.add(os.path.basename(t))

    today = datetime.date.today().isoformat()
    os.makedirs(SENT_DIR, exist_ok=True)
    moved = []

    for path in sorted(glob.glob(os.path.join(POOL, "Draft_*.md"))):
        fn = os.path.basename(path)
        reason = None
        if fn in sent_files:
            reason = "draft is tracked to an already-emailed recipient"
        else:
            txt = open(path, encoding="utf-8", errors="ignore").read()
            emails = {e.lower() for e in EMAIL_RE.findall(txt)}
            exact = emails & sent_emails
            if exact:
                reason = "recipient already emailed (" + ", ".join(sorted(exact)) + ")"
            else:
                # fuzzy: same domain + same collapsed local-part (alias tolerance)
                for e in emails:
                    dom = e.split("@")[-1].lower()
                    if local_part(e) in sent_localdomain.get(dom, set()):
                        reason = f"recipient already emailed (alias match: {e})"
                        break
        if reason:
            shutil.move(path, os.path.join(SENT_DIR, fn))
            moved.append((fn, reason))
            log(f"{today} MOVED {fn} -> capture/sent/  [{reason}]")

    if moved and os.path.exists(PIPELINE):
        with open(PIPELINE, "a", encoding="utf-8") as f:
            f.write(f"\n<!-- payload-sent-filter {today}: pruned already-sent drafts -->\n")
            for fn, reason in moved:
                f.write(f"- [AUTO-SENT-GATE {today}] {fn} removed from serving pool - {reason}.\n")

    print(f"payload-sent-filter: moved {len(moved)} already-sent draft(s) out of the serving pool")
    for fn, reason in moved:
        print(f"  - {fn}  ({reason})")
    return len(moved)


if __name__ == "__main__":
    main()
