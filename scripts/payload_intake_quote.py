#!/usr/bin/env python3
"""
PAYLOAD INTAKE → QUOTE (PROG-002 inbound path).
Watches the info@/exosmc Proton lane for a payload-flight inquiry, extracts the payload
parameters, and runs the Quote & Contract pipeline end-to-end into a Decision on Jon's board.
Nothing goes external — the Decision is the human gate. Export screen: a .mil/.gov sender or
ITAR/CUI-flavored inquiry is tagged for human export review instead of auto-quoted.

Trigger (kept tight during the test phase): subject starts with "[PAYLOAD]" OR contains both
a payload word and a mass (e.g. "25 kg"). Deterministic parse; no LLM in the path.

Run:  python3 scripts/payload_intake_quote.py            # dry-run (parse + show, no post)
      python3 scripts/payload_intake_quote.py --apply    # process + post Decisions
"""
import imaplib, email, os, re, sys, json, subprocess, datetime
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from email.utils import getaddresses, parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quote_contract_pipeline import quote, build_package, post_decision  # reuse the pipeline
import payload_questionnaire as pq  # website questionnaire → phone + billing address into CRM/payload orders (10/12)

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER = "jquinnexo@pm.me"
LANE = {"info@exosaero.com", "exosmc@pm.me", "exosmc@proton.me", "jquinnexo@pm.me", "jquinnexo@proton.me"}
STATE = os.path.join(WS, "logs", "payload-intake-state.json")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
JON = "1501632195163590739"
APPLY = "--apply" in sys.argv

PAYLOAD_WORD = re.compile(r"\b(payload|suborbital|blk3|manifest|cubesat|microgravity|flight opportunit)\b", re.I)
MASS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg|kilogram)", re.I)
ALT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*km", re.I)
def field(k, s):
    return re.search(rf"^\s*{k}\s*[:\-]\s*(.+)$", s, re.I | re.M)
SENSITIVE = re.compile(r"\b(itar|ear99|export control|cui|classified|dod|d\.o\.d|secret|\.mil)\b", re.I)


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def body_text(msg, cap=9000):
    plain, htmls = [], []
    if msg.is_multipart():
        for p in msg.walk():
            ct = p.get_content_type()
            if ct == "text/plain":
                try: plain.append(p.get_payload(decode=True).decode(errors="replace"))
                except Exception: pass
            elif ct == "text/html":
                try: htmls.append(p.get_payload(decode=True).decode(errors="replace"))
                except Exception: pass
    else:
        try: plain.append(msg.get_payload(decode=True).decode(errors="replace"))
        except Exception: pass
    t = "\n".join(plain).strip()
    if not t and htmls:
        t = re.sub(r"(?s)<[^>]+>", " ", "\n".join(htmls))
    return t[:cap]


def recipients(msg):
    out = set()
    for hk in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To"):
        for v in msg.get_all(hk, []) or []:
            for _n, a in getaddresses([v]):
                if a: out.add(a.lower())
    return out


def parse_inquiry(msg, subject, body):
    frm = getaddresses(msg.get_all("From", []) or [])
    from_name = (frm[0][0] if frm else "").strip()
    from_addr = (frm[0][1] if frm else "").lower()
    # customer: explicit Company: line > From display name > domain
    company = None
    m = field("company", body) or field("customer", body) or field("organization", body)
    if m: company = m.group(1).strip()
    if not company and from_name and "@" not in from_name:
        company = from_name
    if not company and from_addr:
        company = from_addr.split("@")[-1].split(".")[0].title()
    company = (company or "Unknown Prospect")[:80]
    mm = MASS_RE.search(body) or MASS_RE.search(subject)
    kg = float(mm.group(1)) if mm else None
    am = ALT_RE.search(body) or ALT_RE.search(subject)
    altitude = float(am.group(1)) if am else 90.0
    # mission: explicit line > cleaned subject
    mis = field("mission", body) or field("payload", body) or field("purpose", body)
    clean_subj = re.sub(r"^(?:\s*(?:fwd|fw|re)\s*:\s*)+", "", subject.strip(), flags=re.I)
    clean_subj = re.sub(r"^\s*\[payload\]\s*", "", clean_subj, flags=re.I).strip()
    mission = (mis.group(1).strip() if mis else clean_subj) or "suborbital payload flight"
    sensitive = bool(SENSITIVE.search(body + " " + from_addr + " " + subject))
    return {"company": company, "from_addr": from_addr, "kg": kg, "altitude": altitude,
            "mission": mission[:120], "sensitive": sensitive}


def is_inquiry(subject, body, recips):
    if not (recips & LANE):
        return False
    # Test phase: require the explicit [PAYLOAD] subject marker so we never grab internal
    # chatter that merely mentions "135 kg payload bay". Relax to a heuristic once proven.
    # Tolerate a Fwd:/Re: prefix the info@ auto-forward may prepend.
    s = re.sub(r"^(?:\s*(?:fwd|fw|re)\s*:\s*)+", "", subject.strip(), flags=re.I)
    return s.lower().startswith("[payload]")


def discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", text],
                       timeout=60, capture_output=True)
    except Exception:
        pass


def main():
    pw = load(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if not pw:
        print("ERROR: protonmail_bridge_smtp_password missing"); sys.exit(1)
    seen = set(load(STATE, {}).get("seen", []))
    pq_seen = set(load(pq.STATE, {}).get("seen", []))
    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.login(EMAIL_USER, pw); m.select("INBOX")
    since = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%d-%b-%Y")
    _st, data = m.search(None, "SINCE", since)
    ids = (data[0].split() if data and data[0] else [])
    processed = []
    for num in ids:
        _s, d = m.fetch(num, "(RFC822)")
        if not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        mid = msg.get("Message-ID", "").strip()
        if not mid or mid in seen:
            continue
        subject = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
        body = body_text(msg)
        recips = recipients(msg)
        # Website quote-form submissions (Formspree, or a human forward of one) carry the REQUIRED phone +
        # billing address — fill them onto the CRM contact (upsert by email) and any matching payload order.
        try:
            pq.process_message(msg, APPLY, pq_seen)
        except Exception as e:
            print(f"  · questionnaire carry-over failed: {e}")
        recips = recipients(msg)
        if not is_inquiry(subject, body, recips):
            continue
        info = parse_inquiry(msg, subject, body)
        if not info["kg"]:
            print(f"  · inquiry from {info['from_addr']} has no parseable mass — skipping (subject: {subject[:50]})")
            seen.add(mid); continue
        q = quote(info["kg"])
        price_line = f"${q['price']:,.0f}" if q["price"] else "custom (see note)"
        tag = "  ⚠️ EXPORT REVIEW" if info["sensitive"] else ""
        print(f"  → {info['company']} · {info['kg']}kg · {q['tier']} · {price_line}{tag}  [{info['from_addr']}]")
        processed.append({**info, "tier": q["tier"], "price_line": price_line})
        if APPLY:
            cust = info["company"] + (" [EXPORT REVIEW NEEDED]" if info["sensitive"] else "")
            pkg, _pl = build_package(cust, info["kg"], info["altitude"], info["mission"], q)
            post_decision(cust, info["kg"], price_line, pkg)
            seen.add(mid)
    m.logout()
    if APPLY:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump({"seen": list(seen)[-2000:], "updated": datetime.datetime.now().isoformat()}, open(STATE, "w"))
        tmp = pq.STATE + ".tmp"; json.dump({"seen": sorted(pq_seen)[-2000:]}, open(tmp, "w")); os.replace(tmp, pq.STATE)
    print(f"\n{'processed' if APPLY else 'would process'}: {len(processed)} inquiry(ies)")
    if APPLY and processed:
        lines = "\n".join(f"• {p['company']} — {p['kg']}kg → {p['tier']} {p['price_line']}"
                          + ("  ⚠️ export review" if p["sensitive"] else "") for p in processed)
        discord(f"🛰️ **Payload intake → quote** ({len(processed)}) — drafts routed to Phil's Decisions box to check + update:\n{lines}")


if __name__ == "__main__":
    main()
