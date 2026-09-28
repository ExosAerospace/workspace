#!/usr/bin/env python3
"""
capital_bridge_funds.py — auto-tracker for PO10 funds received (APEX Capital Bridge).

Trigger convention (Jon, 2026-07-29): the team CCs a Proton alias (exosmc@pm.me,
jquinnexo@pm.me, ...) on a "funds received" email. This script scans the Proton
Bridge INBOX, finds those notifications, parses the investor name + dollar amount,
and appends them to the Capital Bridge ledger, keeping a running total. It also
refreshes a single Mission Control task with the running total so Jon can see the
bridge fill from the board.

Design:
- READ-ONLY on email. Never sends. Idempotent (dedupes by Message-ID).
- Amount MUST be present in the subject/body to be added to the total. If a
  "funds received" mail arrives with no dollar figure, the entry is recorded with
  needs_amount=true and flagged, but does NOT change the total.
- Reversible: appends to mission-control/data/capital_bridge_ledger.json only.

Usage: python3 capital_bridge_funds.py [--since-days N]   (default 14)
"""
import imaplib, email, json, os, re, sys, ssl, argparse, urllib.request, urllib.parse
from email.utils import getaddresses
from email.header import decode_header, make_header
from datetime import datetime, timedelta

WS      = os.path.expanduser("~/.openclaw/workspace")
LEDGER  = os.path.join(WS, "mission-control", "data", "capital_bridge_ledger.json")
LOG     = os.path.join(WS, "logs", "capital-bridge-funds.log")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")

IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER = "jquinnexo@pm.me"
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']   # Proton Bridge local password (same as other intake scripts)

SB_URL = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
TASK_TITLE = "Capital Bridge — PO10 Funds Received (auto-tracker)"
JON = "jquinn@exosaero.com"

# Any Proton alias that lands in this mailbox counts as an intake trigger.
SELF_ALIASES = {"exosmc@pm.me", "exosmc@proton.me", "jquinnexo@pm.me", "jquinnexo@proton.me"}

# "<Name> funds received"  /  "funds received from <Name>"  /  "received funds ..."
FUNDS_RE   = re.compile(r"funds?\s+rec(?:ei|ie)ved|rec(?:ei|ie)ved\s+funds?", re.I)
# Skip aggregate/report emails — these carry cumulative dollar figures that must NOT
# be parsed as a single PO10 receipt (caused a $613k false entry from the July
# Monthly Investor Report, 2026-07-31). A "funds received" line inside a report body
# should never inflate the running total.
SKIP_SUBJECT_RE = re.compile(r"monthly\s+(?:investor\s+)?report|investor\s+report|"
                             r"statement|summary|digest|recap|roll[\s-]?up|newsletter", re.I)
NAME_LEAD  = re.compile(r"^\s*(?:re|fw|fwd)\s*:\s*", re.I)
NAME_FROM_SUBJ = re.compile(r"^(.+?)\s+funds?\s+rec(?:ei|ie)ved", re.I)
NAME_AFTER = re.compile(r"funds?\s+rec(?:ei|ie)ved\s+from\s+([A-Z][\w.\-']+(?:\s+[A-Z][\w.\-']+){0,3})", re.I)
# $12,500  |  $12,500.00  |  USD 12,500  |  12,500 USD
AMOUNT_RE  = re.compile(r"(?:\$|USD\s*)\s*([\d]{1,3}(?:,\d{3})+(?:\.\d{2})?|\d{4,}(?:\.\d{2})?)|([\d]{1,3}(?:,\d{3})+(?:\.\d{2})?)\s*(?:USD|dollars)", re.I)


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
    print(msg)


def sb_key():
    try:
        return json.load(open(SECRETS))["supabase_service_role_key"]
    except Exception:
        return None


def sb(method, path, payload=None):
    key = sb_key()
    if not key:
        return None
    h = {"apikey": key, "Authorization": "Bearer " + key,
         "Content-Type": "application/json", "Prefer": "return=representation"}
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(SB_URL + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
        b = r.read().decode()
        return json.loads(b) if b else []


def load_ledger():
    with open(LEDGER) as f:
        return json.load(f)


def save_ledger(d):
    d["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    with open(LEDGER, "w") as f:
        json.dump(d, f, indent=2)


def decode(s):
    if not s:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


def body_text(msg):
    parts = []
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type() == "text/plain":
                try:
                    parts.append(p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "ignore"))
                except Exception:
                    pass
    else:
        try:
            parts.append(msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "ignore"))
        except Exception:
            pass
    return "\n".join(parts)


def parse_amount(text):
    """Return the largest plausible dollar amount found, or None."""
    best = None
    for m in AMOUNT_RE.finditer(text):
        raw = m.group(1) or m.group(2)
        if not raw:
            continue
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        if val >= 500:  # ignore tiny numbers / years
            best = val if best is None else max(best, val)
    return best


def parse_investor(subject, body):
    subj = NAME_LEAD.sub("", subject).strip()
    m = NAME_FROM_SUBJ.match(subj)
    if m:
        return m.group(1).strip()
    m = NAME_AFTER.search(subject + "\n" + body)
    if m:
        return m.group(1).strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=14)
    args = ap.parse_args()

    led = load_ledger()
    seen = set(led.get("seen_message_ids", []))
    new_entries = []
    imap_ok = True

    try:
        mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mail.sock.settimeout(20)
        mail.starttls()
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("INBOX", readonly=True)
        since = (datetime.now() - timedelta(days=args.since_days)).strftime("%d-%b-%Y")
        status, data = mail.search(None, f'(SINCE {since})')
        ids = data[0].split() if status == "OK" and data and data[0] else []
        log(f"scanning {len(ids)} inbox messages since {since}")
        for num in ids:
            st, md = mail.fetch(num, "(RFC822)")
            if st != "OK" or not md or not md[0]:
                continue
            msg = email.message_from_bytes(md[0][1])
            subject = decode(msg.get("Subject", ""))
            body = body_text(msg)
            if not FUNDS_RE.search(subject) and not FUNDS_RE.search(body):
                continue
            if SKIP_SUBJECT_RE.search(subject):
                log(f"SKIP aggregate/report email (not a single receipt): {subject[:70]}")
                continue
            mid = (msg.get("Message-ID") or "").strip() or f"nomid-{subject[:40]}"
            if mid in seen:
                continue
            recips = [a.lower() for _, a in getaddresses(
                [msg.get("To", ""), msg.get("Cc", ""), msg.get("From", "")])]
            hit_alias = next((a for a in recips if a in SELF_ALIASES), None)
            investor = parse_investor(subject, body)
            amount = parse_amount(subject + "\n" + body)
            frm = decode(msg.get("From", ""))
            date = ""
            try:
                date = email.utils.parsedate_to_datetime(msg.get("Date")).date().isoformat()
            except Exception:
                pass
            entry = {
                "date": date or datetime.now().date().isoformat(),
                "investor": investor or "(unparsed — see source)",
                "amount": amount,
                "po": "PO10",
                "source": f"Email '{subject}' from {frm}",
                "message_id": mid,
                "cc_alias_hit": hit_alias,
                "needs_amount": amount is None,
            }
            if amount is None:
                entry["note"] = "No dollar figure found in email; recorded but NOT added to total. Reply with the amount to complete."
            new_entries.append(entry)
            seen.add(mid)
            log(f"NEW receipt: {entry['investor']} | ${amount if amount else 'TBD'} | alias={hit_alias} | {subject[:60]}")
        mail.logout()
    except Exception as e:
        log(f"ERROR: IMAP error: {e}")
        imap_ok = False

    if new_entries:
        led["entries"].extend(new_entries)
        led["seen_message_ids"] = sorted(seen)
        save_ledger(led)

    # Running total = confirmed baseline + all entries with a numeric amount
    counted = [e for e in led["entries"] if isinstance(e.get("amount"), (int, float))]
    pending = [e for e in led["entries"] if e.get("needs_amount")]
    total = (led.get("baseline_amount") or 0) + sum(e["amount"] for e in counted)
    target = led.get("target") or 0
    log(f"TOTAL PO10 received: ${total:,.0f} of ${target:,.0f} "
        f"({len(counted)} logged receipts, {len(pending)} awaiting amount)")

    mc_ok = update_mc_task(led, total, target, counted, pending)
    if not (imap_ok and mc_ok):
        log("ERROR: run incomplete — " + ", ".join(
            n for n, ok in (("IMAP read failed", imap_ok), ("MC task update failed", mc_ok)) if not ok))
        sys.exit(1)
    return led, total


def update_mc_task(led, total, target, counted, pending):
    """Create/refresh the single MC task carrying the running total. Returns False on failure."""
    pct = (total / target * 100) if target else 0
    lines = [
        "**APEX Capital Bridge — PO10 funds received (auto-tracked).**",
        "",
        f"Running total: **${total:,.0f}** of ${target:,.0f} target ({pct:.0f}%).",
        f"Baseline (pre-tracker, {led.get('baseline_as_of')}): ${led.get('baseline_amount',0):,.0f} — confirm w/ Mitchell/Neil.",
        "",
        "How it fills: team CCs **exosmc@pm.me** on a 'funds received' email with the "
        "dollar amount in it; the tracker appends it here automatically.",
        "",
        "**Logged receipts:**",
    ]
    for e in counted:
        lines.append(f"- {e['date']} — {e['investor']}: ${e['amount']:,.0f}")
    if not counted:
        lines.append("- (none with a confirmed amount yet)")
    if pending:
        lines.append("")
        lines.append("**Awaiting dollar amount:**")
        for e in pending:
            lines.append(f"- {e['date']} — {e['investor']} ({e.get('note','amount missing')})")
    desc = "\n".join(lines)

    try:
        existing = sb("GET", f"tasks?title=eq.{urllib.parse.quote(TASK_TITLE)}&select=id&limit=1")
        if existing:
            tid = existing[0]["id"]
            sb("PATCH", f"tasks?id=eq.{tid}", {"description": desc,
                "updated_at": datetime.now().astimezone().isoformat(timespec="seconds")})
            log(f"MC task {tid} refreshed")
        else:
            res = sb("POST", "tasks", {
                "title": TASK_TITLE, "description": desc, "state": "In Progress",
                "category": "Fundraising", "priority": 80, "owner": "Jon",
                "assigned_email": JON, "assigned_to": "John Quinn",
                "source": "capital-bridge-funds"})
            tid = res[0]["id"] if res else None
            log(f"MC task created -> {tid}")
        if tid and led.get("mc_task_id") != tid:
            led["mc_task_id"] = tid
            save_ledger(led)
        return True
    except Exception as e:
        log(f"ERROR: MC task update failed: {e}")
        return False


if __name__ == "__main__":
    main()
