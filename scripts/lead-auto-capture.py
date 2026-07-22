#!/usr/bin/env python3
"""
lead-auto-capture.py — inbound → CRM lead auto-capture (ExO3 program rollout).

Every genuinely NEW external person who emails our intake becomes a lead in the Supabase CRM:
a contact record (stage=Lead, source=inbound-lead), deduped against the existing CRM by email,
flagged for follow-up. No inbound lead is lost. Internal senders, no-reply/automated addresses,
and anyone already in the CRM are skipped. Export-controlled mail is screened out (itar_ear_screen)
before any capture. Idempotent via a processed-message-id state file.

Runs every 20 min via launchd com.exos.lead-auto-capture.
"""
import imaplib, email, json, os, re, sys, time, urllib.request
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime, timedelta, timezone, date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itar_ear_screen as ee

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.join(WS, "logs", "lead-capture-state.json")
LOG = os.path.join(WS, "logs", "lead-capture.log")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
INTERNAL_DOMAINS = {"exosaero.com", "pm.me", "proton.me"}
SELF = {"jquinnexo@pm.me", "jquinn@exosaero.com", "exosmc@proton.me", "exosmc@pm.me"}
GENERIC = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com",
           "protonmail.com", "me.com", "live.com", "msn.com"}
NOREPLY = re.compile(
    r'^(no-?reply|do-?not-?reply|donotreply|noreply|notifications?|news|updates?|invoice|billing|'
    r'statements?|receipts?|alerts?|digest|newsletter|marketing|mailer-daemon|postmaster|bounce|'
    r'automated|automailer|mailer|system|root)([._+-]|@)|'          # automated/marketing local-parts
    r'@(m|email|e|mail|news|mktg|marketing|updates?|reply|notify|mailer|em)\.|'   # marketing subdomains
    r'(mailchimp|sendgrid|substack|calendly|amazonses|sparkpost|mailgun|stripe|intuit|quickbooks|'
    r'docusign|discord|github\.com|slack\.com|zoom\.us|atlassian|paypal|dropbox|linkedin|facebookmail|'
    r'apple\.com|accounts\.google|googlemail|adobe|hubspot|salesforce)', re.I)


def _k():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def sget(p):
    k = _k()
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        B + p, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=60).read())


def screate(rec):
    k = _k()
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        B + "contacts", data=json.dumps(rec).encode(),
        headers={"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json",
                 "Prefer": "return=representation"}, method="POST"), timeout=30).read())[0]["id"]


def load_json(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a").write(time.strftime("%Y-%m-%d %H:%M ") + m + "\n")


def dec(h):
    if not h:
        return ""
    return "".join((b.decode(c or "utf-8", "replace") if isinstance(b, bytes) else b)
                   for b, c in decode_header(h))


def org_from(domain):
    if not domain or domain in GENERIC:
        return ""
    base = domain.split(".")[0]
    return base.replace("-", " ").title()


def keep(addr, name):
    if not addr or "@" not in addr:
        return False
    d = addr.split("@")[-1].lower()
    if addr.lower() in SELF or d in INTERNAL_DOMAINS:
        return False
    if NOREPLY.search(addr) or NOREPLY.search(name or ""):
        return False
    return True


def _external(addr, name=""):
    a = (addr or "").lower()
    return bool(a) and "@" in a and a.split("@")[-1] not in INTERNAL_DOMAINS and keep(a, name)


def extract_lead(fname, faddr, msg, body, info_channel):
    """Return (name, email, source) for the ACTUAL lead, or None.
    Direct external sender → the sender. info@/human-forwarded (From is internal) →
    dig out the original inquirer from Reply-To, the forwarded 'From:' header, or the body."""
    if _external(faddr, fname):
        return ((fname or faddr.split("@")[0]).strip(), faddr, "inbound-lead")
    src = "website-inquiry" if info_channel else "forwarded-lead"
    for nm, ad in getaddresses([msg.get("Reply-To", "")]):
        if _external(ad, nm):
            return ((nm or ad.split("@")[0]).strip(), ad.lower(), src)
    m = re.search(r'From:\s*"?([^"<\n]*?)"?\s*<([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})>', body)
    if m and _external(m.group(2), m.group(1)):
        return ((m.group(1).strip() or m.group(2).split("@")[0]), m.group(2).lower(), src)
    for ad in re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', body):
        if _external(ad):
            return (ad.split("@")[0], ad.lower(), src)
    return None


def main():
    since_days = int(sys.argv[sys.argv.index("--since-days") + 1]) if "--since-days" in sys.argv else 7
    dry = "--dry-run" in sys.argv
    pw = json.load(open(SECRETS)).get("protonmail_bridge_smtp_password")
    if not pw:
        print("no IMAP password; abort"); return
    state = set(load_json(STATE, []))
    existing = set((c.get("email") or "").lower() for c in sget("contacts?select=email&limit=5000"))
    print(f"existing CRM contacts: {len(existing)}")

    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.login(EMAIL_USER, pw)
    m.select("INBOX", readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%d-%b-%Y")
    typ, data = m.search(None, f'(SINCE {since})')
    ids = data[0].split()
    captured = 0; scanned = 0; new_state = list(state)
    for i in ids[-400:]:
        st, d = m.fetch(i, "(RFC822)")
        if st != "OK" or not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        mid = msg.get("Message-ID") or f"idx-{i.decode()}"
        if mid in state:
            continue
        new_state.append(mid); scanned += 1
        subj = dec(msg.get("Subject"))
        frm = getaddresses([msg.get("From", "")])
        fname, faddr = (dec(frm[0][0]), (frm[0][1] or "").lower()) if frm else ("", "")
        body = ""
        for p in msg.walk():
            if p.get_content_type() == "text/plain":
                try: body += p.get_payload(decode=True).decode(errors="replace")
                except Exception: pass
        # export-control screen — controlled mail is never captured (human-gated lane)
        if ee.screen(subj + "\n" + body[:2500] + "\n" + faddr):
            log(f"HELD (export-control) lead skip: {faddr}")
            continue
        # info@ website-inquiry channel (auto lane) vs direct vs human-forward
        rcpts = " ".join(str(msg.get(h, "")) for h in ("To", "Cc", "Delivered-To", "X-Original-To", "X-Forwarded-To")).lower()
        info_channel = "info@exosaero.com" in rcpts or faddr == "info@exosaero.com"
        lead = extract_lead(fname, faddr, msg, body, info_channel)
        if not lead:
            continue
        name, addr, src = lead
        if addr in existing:
            continue  # already a CRM contact — not a new lead
        try:
            dt = parsedate_to_datetime(msg.get("Date")).date().isoformat()
        except Exception:
            dt = date.today().isoformat()
        org = org_from(addr.split("@")[-1])
        rec = {"name": (name or addr.split("@")[0]).strip(), "email": addr, "organization": org,
               "owner": "Jon", "source": src, "stage": "Lead", "status": "new", "type": "Lead",
               "tags": ["inbound", "lead", "exo3"] + (["website"] if src == "website-inquiry" else []),
               "priority_score": 40, "last_contacted": dt,
               "next_action": "Qualify inbound lead", "next_followup": (date.today() + timedelta(days=3)).isoformat(),
               "notes": f"Auto-captured {src} from email “{subj[:80]}” on {dt}."}
        if dry:
            print(f"  [dry] would capture LEAD: {rec['name']} <{addr}>" + (f" ({org})" if org else ""))
        else:
            cid = screate(rec); log(f"LEAD captured: {rec['name']} <{addr}> (contact #{cid})")
            print(f"  + LEAD #{cid}: {rec['name']} <{addr}>" + (f" ({org})" if org else ""))
        existing.add(addr); captured += 1
    m.logout()
    if not dry:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(new_state[-5000:], open(STATE, "w"))
    print(f"scanned {scanned} new inbound | leads captured: {captured}{' [DRY]' if dry else ''}")


if __name__ == "__main__":
    main()
