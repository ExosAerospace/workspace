#!/usr/bin/env python3
"""
send_confirmation_tracker.py — close the "delivered to inbox but never sent" gap.

Root cause it fixes (Matt Lesiw booking, Aug 2026): the decision-send-watcher
auto-delivers a ready customer draft to Jon's inbox and AUTO-CLOSES the decision.
Nothing then confirms the external hand-send actually happened, so a booking can
sit unsent for weeks while every system reads "done."

This guardrail:
  1. ENROLL — find auto-delivered send-decisions whose draft targets an EXTERNAL
     recipient, and record them in a pending ledger (idempotent).
  2. CONFIRM — read Jon's Proton mailbox (BCC self-copies) for a send TO that
     recipient after delivery; if found, mark sent + clear.  (Exo direct-sends
     also mark sent via mark_sent().)
  3. NUDGE — if a prepared send is still unconfirmed after GRACE_DAYS, DM Jon on
     Discord (throttled once/day) so it can never silently stall again.

Read-only against email. Safe + idempotent. Runs on launchd ~2x/day.
Usage: send_confirmation_tracker.py            # enroll + confirm + nudge
       send_confirmation_tracker.py --dry-run  # no nudge, no ledger write
       send_confirmation_tracker.py --mark-sent <recipient>   # manual clear
"""
import os, re, sys, json, imaplib, email, subprocess, shutil
from datetime import datetime, timezone, timedelta
from email.utils import getaddresses, parsedate_to_datetime

WS = "/Users/exomac/.openclaw/workspace"
DECISIONS = os.path.join(WS, "mission-control/data/decisions.json")
LEDGER = os.path.join(WS, "logs", "pending-external-sends.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
IMAP_USER = "jquinnexo@pm.me"
DM_TARGET = "user:1501632195163590739"          # Jon
GRACE_DAYS = 2                                    # nudge if unsent this long
NUDGE_MAX_DAYS = 21                               # don't nudge on ancient backlog (likely handled off-BCC)
NUDGE_EVERY_HRS = 22
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/shims/openclaw"

INTERNAL = re.compile(r"(exosaero\.com|jquinnexo@|exosmc@|@pm\.me|@proton\.me|noreply|no-reply|mailer-daemon)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
DRAFT_RE = re.compile(r"drafts/[^\s)\"']+\.md")
DRY = "--dry-run" in sys.argv


def now(): return datetime.now(timezone.utc)
def parse_iso(s):
    """Tolerant ISO-8601 parse (handles the 'Z' suffix Python 3.9 rejects)."""
    s = (s or "").strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        try:
            dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            dt = now()
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
def load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d
def save(p, obj):
    tmp = p + ".tmp"; json.dump(obj, open(tmp, "w", encoding="utf-8"), indent=2); os.replace(tmp, p)
def log(m): print(f"[{now().strftime('%Y-%m-%d %H:%M')}] {m}")


def bridge_pass():
    s = load(SECRETS, {})
    return s.get("protonmail_bridge_smtp_password") or s.get("protonmail_bridge_imap_password")


def external_recipient(draft_path):
    """Parse the To: line of a cover-email draft for the external recipient."""
    p = draft_path if os.path.isabs(draft_path) else os.path.join(WS, draft_path)
    if not os.path.exists(p):
        return None, None
    txt = open(p, encoding="utf-8", errors="ignore").read()
    m = re.search(r"^To:\s*(.+)$", txt, re.I | re.M)
    subj = re.search(r"^Subject:\s*(.+)$", txt, re.I | re.M)
    subject = subj.group(1).strip() if subj else ""
    if not m:
        return None, subject
    for e in EMAIL_RE.findall(m.group(1)):
        if not INTERNAL.search(e):
            return e.lower(), subject
    return None, subject


def send_decisions():
    d = load(DECISIONS, [])
    ds = d if isinstance(d, list) else d.get("decisions", d.get("data", []))
    out = []
    for x in ds:
        blob = json.dumps(x).lower()
        delivered = (x.get("status") == "answered" and
                     ("deliver" in str(x.get("answer", "")).lower()
                      or "auto-deliver" in str(x.get("note", "")).lower()))
        looks_send = ("send" in (x.get("title", "") or "").lower()
                      or "send" in str(x.get("source", "")).lower()
                      or str(x.get("relatedItem", "")).upper().startswith("PAY-"))
        if delivered and looks_send:
            out.append(x)
    return out


def enroll(ledger):
    for x in send_decisions():
        did = x.get("id")
        if not did or did in ledger:
            continue
        refs = DRAFT_RE.findall(json.dumps(x))
        recipient, subject = None, x.get("title", "")
        for r in refs:
            rec, subj = external_recipient(r)
            if rec:
                recipient, subject = rec, subj or subject; break
        if not recipient:
            continue  # no external target resolvable -> not our concern
        ledger[did] = {
            "recipient": recipient, "subject": subject[:140],
            "title": x.get("title", "")[:140],
            "delivered_at": x.get("answeredAt") or x.get("updated") or now().isoformat(),
            "enrolled_at": now().isoformat(),
            "related": x.get("relatedItem") or x.get("relatedTaskId") or "",
            "status": "pending", "last_nudge": now().isoformat(),  # suppress immediate nudge on first sight
        }
        log(f"ENROLLED {did}: send to {recipient} — '{subject[:50]}'")


def imap_sent_to(recipients, since):
    """True if Jon's mailbox holds an outbound (self-from) copy TO any recipient
    after `since`. Detects the BCC self-copies Jon's Outlook drops into Proton."""
    pw = bridge_pass()
    if not pw:
        log("WARN: no bridge password; skipping confirm"); return set()
    hit = set()
    try:
        M = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); M.starttls(); M.login(IMAP_USER, pw)
        for folder in ("INBOX", "Sent"):
            try:
                if M.select(folder, readonly=True)[0] != "OK":
                    continue
            except Exception:
                continue
            typ, data = M.search(None, "ALL")
            ids = data[0].split()[-400:]
            for i in reversed(ids):
                typ, d = M.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE)])")
                if not d or not d[0]:
                    continue
                msg = email.message_from_bytes(d[0][1])
                frm = (msg.get("From") or "").lower()
                if "exosaero.com" not in frm and "jquinnexo@" not in frm and "exosmc@" not in frm:
                    continue
                try:
                    dt = parsedate_to_datetime(msg.get("Date"))
                    if dt and dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt and dt < since:
                        continue
                except Exception:
                    pass
                to = set(a.lower() for _, a in getaddresses(msg.get_all("To", []) + msg.get_all("Cc", [])) if a)
                for r in recipients:
                    if r in to:
                        hit.add(r)
        M.logout()
    except Exception as e:
        log(f"WARN: imap confirm failed: {str(e)[:120]}")
    return hit


def confirm(ledger):
    pend = {k: v for k, v in ledger.items() if v.get("status") == "pending"}
    if not pend:
        return
    earliest = min(parse_iso(v["delivered_at"]) for v in pend.values())
    sent = imap_sent_to({v["recipient"] for v in pend.values()}, earliest - timedelta(days=1))
    for did, v in pend.items():
        if v["recipient"] in sent:
            v["status"] = "sent"; v["confirmed_at"] = now().isoformat()
            log(f"CONFIRMED SENT {did}: {v['recipient']}")


def post_discord(text):
    if DRY:
        log(f"[dry] would DM Jon: {text[:80]}"); return False
    env = os.environ.copy()
    env["PATH"] = ":".join([os.path.dirname(OPENCLAW), "/Users/exomac/.local/share/mise/shims",
                            "/opt/homebrew/bin", "/usr/local/bin", env.get("PATH", "")])
    try:
        r = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", DM_TARGET, "-m", text],
                           capture_output=True, text=True, timeout=60, env=env)
        return r.returncode == 0
    except Exception as e:
        log(f"WARN: discord send failed: {e}"); return False


def nudge(ledger):
    for did, v in ledger.items():
        if v.get("status") != "pending":
            continue
        delivered = parse_iso(v["delivered_at"])
        age_days = (now() - delivered).total_seconds() / 86400
        last = parse_iso(v.get("last_nudge", v["enrolled_at"]))
        since_nudge = (now() - last).total_seconds() / 3600
        if GRACE_DAYS <= age_days <= NUDGE_MAX_DAYS and since_nudge >= NUDGE_EVERY_HRS:
            msg = (f"⏳ **Prepared customer send hasn't gone out** ({int(age_days)} days).\n"
                   f"**{v.get('title') or v.get('subject')}** → {v['recipient']}\n"
                   f"The draft is in your inbox, ready to forward. Reply **\"send direct\"** and I'll send it for you, "
                   f"or forward it yourself. (Guardrail: {did})")
            if post_discord(msg):
                v["last_nudge"] = now().isoformat()
                log(f"NUDGED Jon on {did} ({v['recipient']}, {int(age_days)}d)")


def main():
    if "--mark-sent" in sys.argv:
        target = sys.argv[sys.argv.index("--mark-sent") + 1].lower()
        ledger = load(LEDGER, {})
        for did, v in ledger.items():
            if v.get("recipient") == target and v.get("status") == "pending":
                v["status"] = "sent"; v["confirmed_at"] = now().isoformat()
                log(f"MARKED SENT {did}: {target}")
        save(LEDGER, ledger); return 0

    ledger = load(LEDGER, {})
    enroll(ledger)
    confirm(ledger)
    nudge(ledger)
    if not DRY:
        save(LEDGER, ledger)
    pend = sum(1 for v in ledger.values() if v.get("status") == "pending")
    log(f"done: {len(ledger)} tracked, {pend} pending unsent{' (dry-run, not saved)' if DRY else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
