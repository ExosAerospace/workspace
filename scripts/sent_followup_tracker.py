#!/usr/bin/env python3
"""sent_followup_tracker.py — log Jon's outbound sends to the right task + track awaiting-reply.

Jon Bcc's jquinnexo@pm.me on sends from @exosaero.com. Those land in the Proton inbox. This:
  1. Builds a per-CONTACT follow-up log (logs/sent-followup-log.json): last send, subject, task
     (if a confident match), and whether the contact has replied since — the reliable core.
  2. Annotates the ORIGINAL task with "📤 Sent to <name> on <date> — <subj>" ONLY for HIGH-confidence
     matches (contact's org/name token appears in the task title) — never creates tasks.
  3. Everything without a confident task match goes to a REVIEW list (logs/sent-untracked-review.json)
     for Jon to link manually — no task noise.
  4. Reply detection: an inbound email FROM the contact AFTER the last send stops the awaiting-reply
     clock. The nudge watcher (separate) reads this log.

Idempotent. --dry-run prints a summary and writes nothing. --days N sets the lookback (default 185).
"""
import imaplib, email, json, os, re, sys, urllib.request
from email.utils import getaddresses, parsedate_to_datetime
from email.header import decode_header
from datetime import datetime, timedelta, timezone


def dec(s):
    try:
        return "".join((b.decode(c or "utf-8", "ignore") if isinstance(b, bytes) else b)
                       for b, c in decode_header(s or "")).strip()
    except Exception:
        return s or ""

WS = os.path.expanduser("~/.openclaw/workspace")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
SH = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json", "Prefer": "return=representation"}
LOG = os.path.join(WS, "logs", "sent-followup-log.json")
REVIEW = os.path.join(WS, "logs", "sent-untracked-review.json")
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
EMAILRE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
SELF = {"jquinnexo@pm.me", "jquinnexo@proton.me", "exosmc@pm.me", "exosmc@proton.me"}
COMMON = {"gmail", "outlook", "hotmail", "yahoo", "proton", "pm", "me", "icloud", "aol", "msn", "live"}


def supa(method, path, body=None):
    req = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None, headers=SH)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            t = r.read().decode(); return json.loads(t) if t else []
    except Exception:
        return None


def load_tasks():
    tasks = []; off = 0
    while True:
        c = supa("GET", f"tasks?select=id,title,description,state&order=id.asc&limit=1000&offset={off}") or []
        tasks += c
        if len(c) < 1000: break
        off += 1000
    return tasks


def org_token(addr):
    dom = addr.split("@")[-1].split(".")[0].lower()
    return dom if dom and dom not in COMMON else ""


def name_tokens(addr):
    lp = addr.split("@")[0].lower()
    return [t for t in re.split(r"[._+\-]", lp) if len(t) >= 3]


def match_task(addr, tasks_by_email, tasks):
    """Return (task, confidence). HIGH = org/name token in task TITLE. LOW = email in task but title
    doesn't corroborate (e.g. a vendor email inside an unrelated task). None = no task references it."""
    cand = tasks_by_email.get(addr.lower(), [])
    if not cand:
        return None, None
    org = org_token(addr); names = name_tokens(addr)
    for t in cand:
        title = (t.get("title") or "").lower()
        if (org and org in title) or any(n in title for n in names):
            return t, "high"
    return cand[0], "low"


def main():
    dry = "--dry-run" in sys.argv
    days = 185
    if "--days" in sys.argv:
        try: days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception: pass

    tasks = load_tasks()
    tasks_by_email = {}
    for t in tasks:
        for e in set(EMAILRE.findall((t.get("title", "") + " " + (t.get("description") or "")).lower())):
            tasks_by_email.setdefault(e.lower(), []).append(t)

    pw = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["protonmail_bridge_smtp_password"]
    M = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); M.login(EMAIL_USER, pw); M.select("INBOX", readonly=True)
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

    # Outbound: Jon's sends.  Inbound-from-contact: to detect replies.
    st, d = M.search(None, f'(SINCE {since}) (FROM "exosaero.com")')
    out_ids = d[0].split() if d and d[0] else []
    st, d = M.search(None, f'(SINCE {since})')
    all_ids = d[0].split() if d and d[0] else []

    contacts = {}   # email -> {name,last_sent,subj,task_id,conf,sends[]}
    def hdr(i, fields):
        t, x = M.fetch(i, f"(BODY.PEEK[HEADER.FIELDS ({fields})])")
        return email.message_from_bytes(x[0][1]) if x and x[0] else None

    sends = 0
    for i in out_ids:
        h = hdr(i, "FROM TO CC SUBJECT DATE")
        if not h: continue
        frm = (getaddresses(h.get_all("From", [])) or [("", "")])[0][1].lower()
        if not frm.endswith("@exosaero.com"): continue
        recips = [(n, a.lower()) for n, a in getaddresses(h.get_all("To", []) + h.get_all("Cc", []))]
        ext = [(n, a) for n, a in recips if a and not a.endswith("@exosaero.com") and a not in SELF]
        if not ext: continue
        try: dt = parsedate_to_datetime(h.get("Date", "")).astimezone(timezone.utc)
        except Exception: dt = None
        subj = dec(h.get("Subject", ""))[:120]
        sends += 1
        for nm, a in ext:
            c = contacts.setdefault(a, {"name": nm or a, "last_sent": None, "subj": "", "task_id": None,
                                        "conf": None, "sends": 0, "replied": False, "last_reply": None})
            c["sends"] += 1
            if dt and (c["last_sent"] is None or dt.isoformat() > c["last_sent"]):
                c["last_sent"] = dt.isoformat() if dt else None; c["subj"] = subj
                if nm: c["name"] = nm

    # reply detection: inbound FROM a tracked contact, dated after their last_sent
    for i in all_ids:
        h = hdr(i, "FROM DATE")
        if not h: continue
        frm = (getaddresses(h.get_all("From", [])) or [("", "")])[0][1].lower()
        if frm in contacts:
            try: dt = parsedate_to_datetime(h.get("Date", "")).astimezone(timezone.utc).isoformat()
            except Exception: dt = None
            c = contacts[frm]
            if dt and c["last_sent"] and dt > c["last_sent"]:
                c["replied"] = True
                if not c["last_reply"] or dt > c["last_reply"]: c["last_reply"] = dt
    M.logout()

    # task matching
    high = low = none_ = 0
    review = []
    for a, c in contacts.items():
        t, conf = match_task(a, tasks_by_email, tasks)
        if conf == "high":
            c["task_id"] = t["id"]; c["conf"] = "high"; c["task_title"] = t.get("title", "")[:60]; high += 1
        elif conf == "low":
            c["conf"] = "low"; c["task_id"] = t["id"]; c["task_title"] = t.get("title", "")[:60]; low += 1
            review.append({"contact": a, "name": c["name"], "maybe_task": t["id"], "maybe_title": t.get("title", "")[:60], "last_sent": c["last_sent"], "subj": c["subj"]})
        else:
            c["conf"] = "none"; none_ += 1
            review.append({"contact": a, "name": c["name"], "maybe_task": None, "last_sent": c["last_sent"], "subj": c["subj"]})

    awaiting = [a for a, c in contacts.items() if c["last_sent"] and not c["replied"]]
    print(f"window: {days} days | outbound sends: {sends} | distinct external contacts: {len(contacts)}")
    print(f"task match — HIGH (org/name in title, safe to annotate): {high}")
    print(f"            LOW (email in a task but title unconfirmed → REVIEW): {low}")
    print(f"            NONE (no task references them → REVIEW): {none_}")
    print(f"awaiting reply (sent, no response yet): {len(awaiting)}")

    if dry:
        print("\n--- sample HIGH-confidence task annotations that WOULD be written ---")
        n = 0
        for a, c in contacts.items():
            if c["conf"] == "high" and n < 12:
                print(f"  #{c['task_id']} \"{c.get('task_title','')}\" ← sent to {c['name']} <{a}> {(c['last_sent'] or '')[:10]} {'(replied)' if c['replied'] else '(awaiting)'}")
                n += 1
        return

    # WRITE: contact log + review list always; task annotations for HIGH only (idempotent via a marker)
    json.dump({"generated": datetime.now(timezone.utc).isoformat(), "contacts": contacts}, open(LOG, "w"), indent=2)
    json.dump({"generated": datetime.now(timezone.utc).isoformat(), "review": review}, open(REVIEW, "w"), indent=2)
    prior = {}
    marker_path = os.path.join(WS, "logs", "sent-followup-annotated.json")
    try: prior = json.load(open(marker_path))
    except Exception: prior = {}
    written = 0
    for a, c in contacts.items():
        if c["conf"] != "high" or not c["last_sent"]: continue
        key = f"{c['task_id']}|{a}|{c['last_sent'][:10]}"
        if prior.get(key): continue
        supa("POST", "activities", {"type": "task_note", "subject": f"task:{c['task_id']}",
             "body": f"📤 Email sent to {c['name']} <{a}> on {c['last_sent'][:10]} — {c['subj']}"
                     + ("" if c['replied'] else "  ·  ⏳ awaiting reply"), "owner": "Exo", "status": "completed"})
        prior[key] = True; written += 1
    json.dump(prior, open(marker_path, "w"), indent=2)
    print(f"WROTE: contact log ({len(contacts)}), review list ({len(review)}), task annotations ({written})")


if __name__ == "__main__":
    main()
