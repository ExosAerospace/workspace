#!/usr/bin/env python3
"""
outreach-reply-tracker.py — loops Exo (and Jon) in on outreach OUTCOMES.

We CC info@exosaero.com (auto-forwarded to the intake) + Lizi on outbound outreach and ask
recipients to "reply all". When a counterparty REPLIES, this job:
  1. reads it as positive / negative / acknowledged / needs-follow-up (deterministic keyword heuristic — no egress),
  2. updates their CRM contact (last_contacted, replied tag, next action, note),
  3. DMs Jon on Discord with the outcome so he can triage in seconds.

Only external REPLIES are treated as outcomes. Our own outbound copies (internal From) are logged
as send-confirmations, not outcomes. Export-controlled mail is screened out before anything is read.
Idempotent via a processed-message-id state file. Runs every 20 min via launchd
com.exos.outreach-reply-tracker. Complements lead-auto-capture (which handles brand-new senders).

Compliance: info@ is the public/non-sensitive channel only. Nothing here touches M365 directly.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import imaplib, email, json, os, re, sys, time, shutil, subprocess, urllib.request, urllib.parse
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime, timedelta, timezone, date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itar_ear_screen as ee

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.join(WS, "logs", "outreach-reply-state.json")
LOG = os.path.join(WS, "logs", "outreach-reply-tracker.log")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
INTERNAL_DOMAINS = {"exosaero.com", "pm.me", "proton.me"}
JON_DISCORD = "user:1501632195163590739"
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/shims/openclaw"

# Automated / marketing senders that are never real outreach replies (mirrors lead-auto-capture).
NOREPLY = re.compile(
    r'^(no-?reply|do-?not-?reply|donotreply|noreply|notifications?|news|updates?|invoice|billing|'
    r'statements?|receipts?|alerts?|digest|newsletter|marketing|mailer-daemon|postmaster|bounce|'
    r'automated|automailer|mailer|system|root)([._+-]|@)|'
    r'@(m|email|e|mail|news|mktg|marketing|updates?|reply|notify|mailer|em)\.|'
    r'(mailchimp|sendgrid|substack|calendly|amazonses|sparkpost|mailgun|stripe|intuit|quickbooks|'
    r'docusign|discord|github\.com|slack\.com|zoom\.us|atlassian|paypal|dropbox|linkedin|facebookmail|'
    r'apple\.com|accounts\.google|googlemail|adobe|hubspot|salesforce|'
    r'list-?serv|listsrv|majordomo|mailman|nasaprs|@lists?[.\-]|-request@|-bounces?@|constantcontact)', re.I)
AUTO_SUBJ = re.compile(r'^\s*(automatic reply|auto(?:matic)?[-: ]|out of office|ooo\b|undeliverable|'
                       r'delivery (?:status|has failed)|read: )', re.I)


def real_person(addr, name):
    if not addr or "@" not in addr:
        return False
    if addr.split("@")[-1].lower() in INTERNAL_DOMAINS:
        return False
    return not (NOREPLY.search(addr) or NOREPLY.search(name or ""))


# Outcome read — deterministic. Negative checked first (a "thanks but no" contains positive words too).
NEG = re.compile(r'\b(not interested|no thank|no,? thank|unfortunately|we(?:\'ll| will) pass|'
                 r'gonna pass|going to pass|decline|not a fit|not the right fit|not at this time|'
                 r'no longer|already (?:have|committed|working with)|budget (?:constraints|does not)|'
                 r'remove me|unsubscribe|do not contact|please stop|not pursuing|out of scope)\b', re.I)
POS = re.compile(r'\b(interested|let\'?s (?:talk|connect|chat|set up|schedule|meet)|happy to|'
                 r'glad to|would love|love to|looking forward|sounds (?:good|great)|schedule a|'
                 r'set up a (?:call|meeting|time)|calendar|available (?:on|next|this)|book a|'
                 r'yes,? (?:let|we|i|please)|count us in|count me in|great to (?:hear|connect)|'
                 r'introduce you|make an intro|send (?:me|over) (?:the|more)|tell me more|'
                 r'like to learn|worth a (?:call|conversation)|open to)\b', re.I)


def _k():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def sget(p):
    k = _k()
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        B + p, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=60).read())


def spatch(path, patch):
    k = _k()
    return urllib.request.urlopen(urllib.request.Request(
        B + path, data=json.dumps(patch).encode(),
        headers={"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json"},
        method="PATCH"), timeout=30).read()


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


def _env():
    env = os.environ.copy()
    extra = [os.path.dirname(OPENCLAW), "/Users/exomac/.local/share/mise/shims",
             "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra + [env.get("PATH", "")])
    return env


def post_discord(text):
    try:
        r = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", JON_DISCORD, "-m", text],
                           capture_output=True, text=True, timeout=60, env=_env())
        if r.returncode != 0:
            log(f"WARN discord rc={r.returncode}: {r.stderr[:160]}")
            return False
        return True
    except Exception as e:
        log(f"WARN discord failed: {e}")
        return False


def body_text(msg):
    body = ""
    for p in msg.walk():
        if p.get_content_type() == "text/plain":
            try:
                body += p.get_payload(decode=True).decode(errors="replace")
            except Exception:
                pass
    return body


def strip_quoted(body):
    """Keep only the top (new) part of a reply — drop quoted history so the outcome read
    reflects what THEY just wrote, not the outreach we sent them."""
    out = []
    for ln in body.splitlines():
        s = ln.strip()
        if s.startswith(">"):
            continue
        if re.match(r'^On .+wrote:$', s) or re.match(r'^-{2,}\s*Original Message', s, re.I) or \
           re.match(r'^From:\s', s):
            break
        out.append(ln)
    return "\n".join(out).strip() or body


# Jon forwards PI / counterparty replies from Outlook (From: internal, subject "Fw:"), with the
# real reply embedded in the body. Pull the embedded external sender + their message so the outcome
# isn't lost as "just our own outbound." (Fixes the NIH-MG "Park reply missed because it was a
# forward from jquinn@exosaero.com" gap, 2026-08-28.)
FWD_FROM = re.compile(r'From:\s*(.+?)\s*<\s*([^>\s]+@[^>\s]+)\s*>', re.I)

def _full_text(msg):
    """Plain body if present, else HTML stripped to text — Outlook forwards put the embedded
    reply header only in the HTML part, which body_text() (plain-only) misses."""
    plain = html = ""
    for p in msg.walk():
        ct = p.get_content_type()
        try:
            payload = p.get_payload(decode=True).decode(errors="replace")
        except Exception:
            continue
        if ct == "text/plain":
            plain += payload
        elif ct == "text/html":
            html += payload
    t = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', html)
    t = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</tr>', '\n', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    import html as _h
    t = re.sub(r'[ \t]+', ' ', _h.unescape(t))
    # Outlook forwards may split the embedded reply header/text across plain+HTML — search both.
    return (plain + "\n" + t) if plain.strip() else t

def forwarded_reply(subj, msg):
    body = _full_text(msg)
    is_fwd = re.match(r'^\s*(fw|fwd)\s*:', subj, re.I) or \
        re.search(r'-+\s*Forwarded message', body or "", re.I)
    if not is_fwd:
        return None
    # first EMBEDDED external sender (skip our own internal From lines in the quoted chain)
    for m in FWD_FROM.finditer(body):
        name, addr = m.group(1).strip().strip('"'), m.group(2).strip().lower()
        dom = addr.split("@")[-1]
        if dom in INTERNAL_DOMAINS or not real_person(addr, name):
            continue
        lines = body[m.end():].splitlines()
        j = 0
        while j < len(lines) and (not lines[j].strip() or
              re.match(r'^\s*(Sent|To|Cc|Subject|Date|Reply-To|Importance)\s*:', lines[j], re.I)):
            j += 1
        reply = strip_quoted("\n".join(lines[j:]).strip())
        return addr, name, re.sub(r'\n{2,}', '\n', reply).strip()
    return None


# Pure acknowledgement ("Agreed and thanks for the update.") — short, no question, no ask.
# Before 2026-09-28 these fell through to needs-follow-up and got re-flagged to Jon for a
# week (Edgar/Nitz). Checked on the reply body only, after NEG/POS.
ACK = re.compile(r'\b(agreed|thanks?|thank you|got it|noted|received|acknowledged|understood|'
                 r'will do|sounds good|perfect|appreciate)\b', re.I)


def classify(text, body=None):
    if NEG.search(text):
        return ("negative", "🔴", "Log as declined; no further outreach unless re-engaged")
    if POS.search(text):
        return ("positive", "🟢", "Respond fast — schedule the call / send materials")
    b = (body if body is not None else text).strip()
    if len(b) <= 200 and '?' not in b and ACK.search(b):
        return ("acknowledged", "⚪", "No action — acknowledgement only")
    return ("needs-follow-up", "🟡", "Read + decide next step")


def main():
    since_days = int(sys.argv[sys.argv.index("--since-days") + 1]) if "--since-days" in sys.argv else 3
    dry = "--dry-run" in sys.argv
    pw = json.load(open(SECRETS)).get("protonmail_bridge_smtp_password")
    if not pw:
        print("no IMAP password; abort"); return
    state = set(load_json(STATE, []))
    # index CRM contacts by email for matching
    crm = {}
    for c in sget("contacts?select=id,name,email,organization,stage,status,tags&limit=5000"):
        e = (c.get("email") or "").lower()
        if e:
            crm[e] = c
    print(f"CRM contacts indexed: {len(crm)}")

    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.login(EMAIL_USER, pw)
    m.select("INBOX", readonly=True)
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%d-%b-%Y")
    typ, data = m.search(None, f'(SINCE {since})')
    ids = data[0].split()
    new_state = list(state)
    outcomes = 0; sends = 0; scanned = 0
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
        # only threads that involve the info@ loop-in (or are clearly replies) matter here
        rcpts = " ".join(str(msg.get(h, "")) for h in ("To", "Cc", "Delivered-To", "X-Original-To")).lower()
        looped = "info@exosaero.com" in rcpts
        is_reply = bool(msg.get("In-Reply-To") or msg.get("References")) or \
            re.match(r'^\s*(re|aw|antw|res|fw|fwd)\s*:', subj, re.I) is not None
        if not is_reply:
            continue  # fresh sends / non-replies are lead-capture's job, not outcome tracking
        dom = faddr.split("@")[-1] if "@" in faddr else ""
        body = body_text(msg)
        fwd_reply = None
        # Internal sender is normally just our own outbound copy. EXCEPTION: Jon forwards a PI /
        # counterparty reply from Outlook — pull the embedded external sender + their text.
        if dom in INTERNAL_DOMAINS:
            fr = forwarded_reply(subj, msg)
            if fr:
                faddr, fname, fwd_reply = fr
                dom = faddr.split("@")[-1]
                log(f"forwarded reply detected: {faddr} (fwd by {frm[0][1] if frm else '?'})")
            else:
                sends += 1
                continue
        # drop automated/marketing "Re:" noise and auto-replies / bounces / OOO
        if not real_person(faddr, fname) or AUTO_SUBJ.match(subj) or \
           "auto-replied" in str(msg.get("Auto-Submitted", "")).lower():
            continue
        if ee.screen(subj + "\n" + body[:2500] + "\n" + faddr):
            log(f"HELD (export-control) reply skip: {faddr}")
            continue
        new = fwd_reply if fwd_reply else strip_quoted(body)
        sentiment, emoji, rec_action = classify(subj + "\n" + new, body=new)
        try:
            dt = parsedate_to_datetime(msg.get("Date")).date().isoformat()
        except Exception:
            dt = date.today().isoformat()
        contact = crm.get(faddr)
        cname = (contact.get("name") if contact else "") or fname or faddr.split("@")[0]
        org = (contact.get("organization") if contact else "") or \
            (dom.split(".")[0].title() if dom and dom not in INTERNAL_DOMAINS else "")
        snip = re.sub(r'\s+', ' ', new)[:200]
        loop_tag = "" if looped else " (not via info@ loop)"
        card = (f"📨 Outreach reply {emoji} {sentiment.upper()}{loop_tag}\n"
                f"{cname}" + (f" · {org}" if org else "") + f" <{faddr}>\n"
                f"Re: {subj[:80]}\n"
                f"“{snip}”\n"
                f"→ {rec_action}" + ("" if contact else "  [not in CRM — lead-capture will add]"))
        if dry:
            print("  [dry]", card.replace("\n", " | "))
        else:
            # update CRM activity if we know them
            if contact:
                tags = list({*(contact.get("tags") or []), "replied", f"reply-{sentiment}"})
                note = f"[{dt}] Replied to outreach ({sentiment}): “{snip}”"
                patch = {"last_contacted": dt, "tags": tags,
                         "next_action": rec_action,
                         "next_followup": (date.today() + timedelta(days=(1 if sentiment == "positive" else 3))).isoformat(),
                         "notes": ((contact.get("notes") + "\n") if contact.get("notes") else "") + note}
                if sentiment == "negative":
                    patch["status"] = "not-interested"
                if sentiment == "acknowledged":  # closes the loop — no follow-up date
                    patch.pop("next_followup", None)
                try:
                    spatch("contacts?id=eq." + str(contact["id"]), patch)
                except Exception as e:
                    log(f"WARN crm patch {faddr}: {e}")
            if sentiment != "acknowledged":  # acks are logged to CRM, not pinged to Jon
                post_discord(card)
            log(f"OUTCOME {sentiment} {faddr} (CRM={'y' if contact else 'n'})")
        outcomes += 1
    m.logout()
    if not dry:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(new_state[-6000:], open(STATE, "w"))
    print(f"scanned {scanned} | outreach replies (outcomes): {outcomes} | send-confirmations: {sends}"
          + (" [DRY]" if dry else ""))


if __name__ == "__main__":
    main()
