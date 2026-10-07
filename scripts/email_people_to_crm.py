# -*- coding: utf-8 -*-
"""
email_people_to_crm.py — capture EVERY person from EVERY email into the primary CRM.

Jon's rule (2026-09-02): every person appearing in an email should land in the CRM with all the
information the email provides. Two paths:
  - Person has an ORG, PHONE, or EMAIL -> upsert a real CRM contact (Supabase `contacts`) with all
    provided fields (name, organization, email, phone, title). Never clobber existing non-empty data.
  - Person is a NAME reference only (no org/phone/email) -> NOT enough for a standalone contact.
    Append the name to the NOTES of the primary contact on that email, so we know who they're
    working with (e.g. "Works with: Jane Doe (per '<subject>', <date>)").

Extraction uses the local Ollama model (cost-free). Source of truth = Supabase `contacts` (the JSON
exports are downstream). Incremental by IMAP UID, idempotent, fail-soft.

SAFETY: defaults to DRY-RUN (prints what it would do, writes nothing). Pass --live to write.
Run:
  python3 scripts/email_people_to_crm.py --since 14 --limit 15        # dry-run last 14 days, 15 msgs
  python3 scripts/email_people_to_crm.py --since 14 --live            # live: upsert + note
"""
import os, sys, json, re, imaplib, email, urllib.request, urllib.parse
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime, timedelta

WS = os.path.expanduser("~/.openclaw/workspace")
SEC = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
STATE = os.path.join(WS, "logs", "email-people-crm-state.json")
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
SB_KEY = SEC["supabase_service_role_key"]
OLLAMA = "http://localhost:11434/api/chat"; MODEL = "qwen3.6:35b-a3b"

DRY = "--live" not in sys.argv
def _arg(f, d):
    return sys.argv[sys.argv.index(f) + 1] if f in sys.argv else d
SINCE_DAYS = int(_arg("--since", "14"))
LIMIT = int(_arg("--limit", "0")) or None

OWN = {"exosaero.com", "pm.me", "proton.me", "protonmail.com", "exosaero.onmicrosoft.com"}
SKIP = re.compile(r"no[-_.]?reply|do[-_.]?not[-_.]?reply|donotreply|mailer-daemon|postmaster|"
                  r"notifications?@|bounce|newsletter|sendgrid|mailchimp|substack|amazonses|"
                  r"@news\.|@mail\.|@email\.|@marketing\.|invoice|receipts?\+|stripe\.com|info@|sales@|support@", re.I)
OWN_NAMES = {"john quinn", "jon quinn", "john m quinn", "elizabeth quinn", "lizi quinn",
             "exo", "exobot", "exomac", "exos", "exos aerospace", "mission control",
             "phil eaton", "steve norsworthy", "neil milburn", "toshihisa kumazawa", "toshi"}


def dec(s):
    if not s: return ""
    out = ""
    for part, enc in decode_header(s):
        out += part.decode(enc or "utf-8", "ignore") if isinstance(part, bytes) else part
    return out

def domain_of(a): return a.split("@")[-1].lower() if "@" in a else ""
def is_own(a): return domain_of(a) in OWN
try:
    SCRUBBED = set(json.load(open(os.path.expanduser("~/.openclaw/workspace/config/crm-scrubbed-emails.json"))).get("emails", {}))
except Exception:
    SCRUBBED = set()
def keep_addr(a):
    a = (a or "").lower().strip()
    return bool(a) and "@" in a and not is_own(a) and not SKIP.search(a) and a not in SCRUBBED

def _html_to_text(h):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"')):
        t = t.replace(a, b)
    return re.sub(r"[ \t]*\n\s*", "\n", re.sub(r"[ \t]+", " ", t)).strip()

def get_body(msg):
    """Prefer text/plain; fall back to stripped text/html (most modern email is HTML-only)."""
    plain, html = "", ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        ct = part.get_content_type()
        if "attachment" in str(part.get("Content-Disposition") or ""): continue
        if ct not in ("text/plain", "text/html"): continue
        try: payload = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore")
        except Exception: continue
        if ct == "text/plain" and not plain: plain = payload
        elif ct == "text/html" and not html: html = payload
    if plain.strip(): return plain
    return _html_to_text(html) if html else ""


# ---- Supabase ----
def sb(method, path, body=None):
    req = urllib.request.Request(SB + "/" + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
        "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt.strip() else []

def find_contact(email_addr=None, name=None, org=None):
    try:
        if email_addr:
            q = "contacts?email=ilike.%s&select=id,name,organization,email,phone,title,linkedin,notes,source" % urllib.parse.quote(email_addr)
            r = sb("GET", q)
            if r: return r[0]
        if name:
            flt = "name=ilike.%s" % urllib.parse.quote(name)
            if org: flt += "&organization=ilike.%s" % urllib.parse.quote(org)
            r = sb("GET", "contacts?%s&select=id,name,organization,email,phone,title,linkedin,notes,source" % flt)
            if r: return r[0]
    except Exception as e:
        print("  find_contact err:", e)
    return None


# ---- Ollama extraction ----
RUBRIC = (
    "You extract PEOPLE from a business email for CRM capture. Return STRICT JSON only: "
    "{\"people\":[{\"name\":\"\",\"organization\":\"\",\"email\":\"\",\"phone\":\"\",\"title\":\"\"}]}. "
    "Include every REAL person: the sender, named human recipients, and anyone NAMED in the body "
    "(a signature block, 'our POC is Jane Smith', 'reach out to Bob Lee at Acme (bob@acme.com)'). "
    "Fill ONLY fields explicitly present in the email; leave the rest as empty string. "
    "NEVER invent an email, phone, or organization. If a person is named with NO org/email/phone, "
    "still include them with only name filled. EXCLUDE: John/Jon Quinn, Lizi/Elizabeth Quinn, anyone "
    "@exosaero.com, and generic role addresses (no-reply, info@, sales@, support@). Output JSON only.")

def extract_people(subject, from_hdr, to_hdr, cc_hdr, body):
    content = ("Subject: %s\nFrom: %s\nTo: %s\nCc: %s\n\nBody:\n%s"
               % (subject, from_hdr, to_hdr, cc_hdr, (body or "")[:6000]))
    payload = json.dumps({"model": MODEL, "stream": False, "format": "json",
        "messages": [{"role": "system", "content": RUBRIC}, {"role": "user", "content": content}]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(OLLAMA, data=payload,
                headers={"Content-Type": "application/json"}), timeout=150) as r:
            raw = (json.load(r).get("message") or {}).get("content") or "{}"
        try: j = json.loads(raw)
        except Exception:
            mm = re.search(r"\{.*\}", raw, re.S); j = json.loads(mm.group(0)) if mm else {}
        out = []
        for p in (j.get("people") or []):
            nm = (p.get("name") or "").strip()
            if not nm or nm.lower() in OWN_NAMES: continue
            em = (p.get("email") or "").strip().lower()
            if em and (is_own(em) or SKIP.search(em)): em = ""
            org = (p.get("organization") or "").strip()
            if org.lower() in ("exos", "exos aerospace", "exos aerospace systems & technologies"): continue
            out.append({"name": nm, "organization": org, "email": em,
                        "phone": (p.get("phone") or "").strip(), "title": (p.get("title") or "").strip()})
        return out
    except Exception as e:
        print("  extract err:", e); return []


# ---- routing ----
def has_hard_info(p): return bool(p.get("email") or p.get("phone") or p.get("organization"))

def upsert_contact(p, subj, iso):
    existing = find_contact(email_addr=p.get("email") or None, name=p["name"], org=p.get("organization") or None)
    prov = "Email auto-capture (%s)" % iso
    if existing:
        patch = {}
        for src, col in (("organization", "organization"), ("email", "email"), ("phone", "phone"), ("title", "title")):
            if p.get(src) and not (existing.get(col) or "").strip():
                patch[col] = p[src]
        if patch:
            if DRY: print("  [dry] PATCH contact %s <- %s" % (existing.get("name"), patch))
            else: sb("PATCH", "contacts?id=eq.%s" % existing["id"], patch)
            return "updated"
        return "exists"
    row = {"name": p["name"], "organization": p.get("organization") or None, "email": p.get("email") or None,
           "phone": p.get("phone") or None, "title": p.get("title") or None, "status": "Active",
           "type": "Contact", "owner": "Jon", "source": prov, "notes": "Auto-captured from email '%s' (%s)." % (subj[:80], iso)}
    if DRY: print("  [dry] CREATE contact: %s | org=%s email=%s phone=%s" % (p["name"], p.get("organization"), p.get("email"), p.get("phone")))
    else: sb("POST", "contacts", row)
    return "created"

def note_on_primary(primary, name, subj, iso):
    if not primary:
        print("  [skip note] no primary contact for name-only '%s'" % name); return "no-primary"
    line = "Works with: %s (per '%s', %s)" % (name, subj[:60], iso)
    notes = primary.get("notes") or ""
    if ("Works with: %s" % name) in notes:
        return "note-exists"
    new_notes = (notes + ("\n" if notes else "") + line).strip()
    if DRY: print("  [dry] NOTE on %s: %s" % (primary.get("name") or primary.get("email"), line))
    else: sb("PATCH", "contacts?id=eq.%s" % primary["id"], {"notes": new_notes})
    return "noted"


def main():
    pw = SEC.get("protonmail_bridge_smtp_password")
    if not pw: print("no IMAP password; abort"); return
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    since = (datetime.now() - timedelta(days=SINCE_DAYS)).strftime("%d-%b-%Y")
    try:
        m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.starttls(); m.login(EMAIL_USER, pw)
    except Exception as e:
        print("IMAP login failed:", e); return

    stats = {"created": 0, "updated": 0, "exists": 0, "noted": 0, "note-exists": 0, "msgs": 0}
    seen = set(state.get("seen_uids", []))
    for folder in ("INBOX", "Sent"):
        try:
            if m.select(folder, readonly=True)[0] != "OK": continue
        except Exception: continue
        typ, data = m.uid("SEARCH", None, "SINCE", since)
        uids = (data[0].split() if data and data[0] else [])
        if LIMIT: uids = uids[-LIMIT:]
        for uid in uids:
            uidk = "%s:%s" % (folder, uid.decode())
            if uidk in seen: continue
            typ, md = m.uid("FETCH", uid, "(RFC822)")
            if not md or not md[0]: continue
            msg = email.message_from_bytes(md[0][1])
            subj = dec(msg.get("Subject", "")); frm = dec(msg.get("From", ""))
            to = dec(msg.get("To", "")); cc = dec(msg.get("Cc", ""))
            try: dt = parsedate_to_datetime(msg.get("Date")); iso = dt.strftime("%Y-%m-%d")
            except Exception: iso = datetime.now().strftime("%Y-%m-%d")
            body = get_body(msg)
            stats["msgs"] += 1

            # primary external correspondent: the external party on the email — From if it's
            # external (inbound), else the first external To/Cc (outbound mail we sent).
            all_addr = [a for _, a in getaddresses([msg.get("From", ""), msg.get("To", ""), msg.get("Cc", "")])]
            primary_addr = next((a for a in all_addr if keep_addr(a)), None)
            primary = find_contact(email_addr=primary_addr) if primary_addr else None
            if primary_addr and not primary:
                # create the correspondent as a full contact (has email)
                name_map = {a: n for n, a in getaddresses([msg.get("From", ""), msg.get("To", ""), msg.get("Cc", "")])}
                fn = dec(name_map.get(primary_addr, ""))
                upsert_contact({"name": fn.strip().strip('"') or primary_addr.split("@")[0],
                                "email": primary_addr, "organization": "", "phone": "", "title": ""}, subj, iso)
                primary = find_contact(email_addr=primary_addr) if not DRY else \
                    {"id": None, "name": fn or primary_addr, "notes": ""}

            people = extract_people(subj, frm, to, cc, body)
            print("• [%s] %s — %d people" % (iso, subj[:60], len(people)))
            for p in people:
                if has_hard_info(p):
                    r = upsert_contact(p, subj, iso); stats[r] = stats.get(r, 0) + 1
                else:
                    r = note_on_primary(primary, p["name"], subj, iso); stats[r] = stats.get(r, 0) + 1
            seen.add(uidk)

    if not DRY:
        state["seen_uids"] = sorted(seen)[-5000:]
        json.dump(state, open(STATE, "w"), indent=1)
    print("\n%s — msgs:%d created:%d updated:%d exists:%d noted:%d" %
          ("DRY-RUN" if DRY else "LIVE", stats["msgs"], stats.get("created", 0), stats.get("updated", 0),
           stats.get("exists", 0), stats.get("noted", 0)))


if __name__ == "__main__":
    main()
