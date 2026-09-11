#!/usr/bin/env python3
"""sent_folder_registry.py — feed the outreach-sent-registry from the Proton SENT folder.

sent-loop-closer.py only reads Jon's INBOX for BCC'd copies. That misses every message Jon
actually sends FROM the Proton account (jquinnexo@pm.me), which lands in the "Sent" mailbox,
not the inbox. This scans Sent (headers only), pulls external To/Cc recipients, and merges
them into logs/outreach-sent-registry.json so reconcile_sent_tasks.py can close their tasks.

NOTE (hard limit): Jon's primary business mail is jquinn@exosaero.com on Microsoft 365 /
Outlook — a SEPARATE mailbox with no local visibility. Sends from there are invisible unless
he BCCs jquinnexo@pm.me. This script closes the Proton-origin gap only; the Outlook gap needs
either an auto-BCC rule or M365 Graph access.

Read-only against email. Idempotent merge. Default lookback 120 days (env SENT_SCAN_DAYS).
"""
import imaplib, email, json, os, re, sys
import email.header
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime, timedelta, timezone

IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER = "jquinnexo@pm.me"
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
WS = os.path.expanduser("~/.openclaw/workspace")
REGISTRY = os.path.join(WS, "logs", "outreach-sent-registry.json")
LOOKBACK_DAYS = int(os.environ.get("SENT_SCAN_DAYS", "120"))
# Not real external outreach targets. Also drop Exo's own [READY TO SEND] notifications, which
# are sent from the Proton account to Jon and therefore appear in Sent (their recipient is
# internal, so INTERNAL already filters them, but guard the subject too for clarity).
INTERNAL = re.compile(r"(exosaero\.com|jquinnexo@|exosmc@|@pm\.me|@proton\.me|noreply|no-reply|mailer-daemon)", re.I)

def _dec(s):
    try: return str(email.header.make_header(email.header.decode_header(s or "")))
    except Exception: return s or ""

def main():
    reg = json.load(open(REGISTRY)) if os.path.exists(REGISTRY) else {}
    before = len(reg)
    M = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); M.login(EMAIL_USER, EMAIL_PASS)
    typ, _ = M.select("Sent", readonly=True)
    if typ != "OK":
        print("Could not select Sent folder"); return
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    typ, ids = M.search(None, f"(SINCE {since})")
    idlist = ids[0].split()
    added = 0
    for i in range(0, len(idlist), 300):
        typ, data = M.fetch(b",".join(idlist[i:i+300]),
                            "(BODY.PEEK[HEADER.FIELDS (TO CC SUBJECT DATE)])")
        for part in data:
            if not isinstance(part, tuple):
                continue
            h = email.message_from_bytes(part[1])
            subj = _dec(h.get("Subject", ""))[:80]
            try: dt = parsedate_to_datetime(h.get("Date")).strftime("%Y-%m-%d %H:%M")
            except Exception: dt = ""
            for _, addr in getaddresses([h.get("To", ""), h.get("Cc", "")]):
                a = (addr or "").lower().strip()
                if not a or INTERNAL.search(a):
                    continue
                cur = reg.get(a)
                if not cur:
                    reg[a] = {"sent_date": dt, "subject": subj, "source": "sent-folder"}; added += 1
                elif cur.get("source") == "sent-folder" and dt > cur.get("sent_date", ""):
                    cur["sent_date"] = dt; cur["subject"] = subj
    M.logout()
    json.dump(reg, open(REGISTRY, "w"), indent=2)
    print(f"sent-folder scan (last {LOOKBACK_DAYS}d): recipients {before} -> {len(reg)} (+{added})")

if __name__ == "__main__":
    main()
