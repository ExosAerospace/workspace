#!/usr/bin/env python3
"""
payload_questionnaire.py — carry the website payload questionnaire's contact block into the CRM + payload orders.

The quote form (https://www.exosaero.com/payload-questionnaire → Formspree mrewgrql, subject "New EXOS BLK3
Payload Questionnaire Submission") already REQUIRES: payloadCustomer, payloadAdministrator, phoneNumber, email,
billingAddress/billingCity/billingState/billingZip/billingCountry and shippingAddress/City/State/Zip/Country.
Before 10/12 nothing read those fields, so invoice #0071 sat blocked for "missing phone/address" (task #3418).

What this does for each submission (direct Formspree notification or a human forward of one):
  - CRM contacts (Supabase): UPSERT BY EMAIL — every record with that email gets the phone if its phone is empty;
    a structured "Billing address: street; city, ST zip" line is added to notes (contacts has no address column).
    A new contact is created only when NO record with that email exists.
  - CRM company (the contact's company_id): address filled if empty.
  - Payload orders (mission-control/data/payload-orders.json) whose contact_email matches: contact_phone and
    billing_address filled if empty — billing_address uses qb_invoice.py's "street; city, ST zip" format.
  Never overwrites a non-empty value with a different one: conflicts are logged to logs/payload-questionnaire.log
  and printed. Nothing is sent to anyone.

Run:
  python3 scripts/payload_questionnaire.py --backfill            # dry-run over every submission in All Mail
  python3 scripts/payload_questionnaire.py --backfill --live     # write
  python3 scripts/payload_questionnaire.py --since-days 3 --live # recent INBOX only (payload_intake_quote.py
                                                                 # also calls process_message() every 10 min)
"""
import email, html, imaplib, json, os, re, sys, time, urllib.parse, urllib.request
from email.header import decode_header, make_header

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
ORDERS = os.path.join(WS, "mission-control", "data", "payload-orders.json")
STATE = os.path.join(WS, "logs", "payload-questionnaire-state.json")
LOG = os.path.join(WS, "logs", "payload-questionnaire.log")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"

SUBJECT_RE = re.compile(r"payload questionnaire submission", re.I)
# Every input name on the form (order as rendered by Formspree).
FIELDS = ["customerName", "payloadName", "payloadClass", "payloadDetails", "description", "powerRequired",
          "integrationAssistance", "voltageRequired", "currentRequired", "internalBatteries", "rfReceiver",
          "rfTransmitter", "clockFrequencies", "serialPorts", "massKg", "lengthMm", "widthMm", "heightMm",
          "volumeCm3", "volumeU", "flightParameters", "environmentNeeds", "hazardMaterials", "specialAccess",
          "payloadCustomer", "payloadAdministrator", "phoneNumber", "email",
          "billingAddress", "billingCity", "billingState", "billingZip", "billingCountry",
          "shippingAddress", "shippingCity", "shippingState", "shippingZip", "shippingCountry"]
FIELDSET = set(FIELDS)
US = {"", "us", "usa", "u.s.", "u.s.a.", "united states", "united states of america"}


# ── parsing ──────────────────────────────────────────────────────────────────
def _text(msg):
    plain, htm = [], []
    for p in (msg.walk() if msg.is_multipart() else [msg]):
        if "attachment" in str(p.get("Content-Disposition") or ""):
            continue
        ct = p.get_content_type()
        try:
            s = p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            continue
        (plain if ct == "text/plain" else htm if ct == "text/html" else []).append(s)
    out = []
    for h in htm:
        t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
        t = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|td|th|li|h\d|table)>", "\n", t)
        out.append(html.unescape(re.sub(r"<[^>]+>", " ", t)))
    return "\n".join(plain + out)


def parse(text):
    """Formspree renders 'key' on one line and the value on the following line(s). Also accepts 'key: value'.
    Returns the FIRST submission found in the text (a forward chain repeats one submission)."""
    f, cur = {}, None
    for raw in text.splitlines():
        line = re.sub(r"[\s\xa0]+", " ", raw.lstrip("> ")).strip()
        if not line:
            continue
        # keys are matched case-exact ("email", not a signature's "Email:")
        m = re.match(r"^([A-Za-z0-9]+)\s*:\s*(.*)$", line)
        if line in FIELDSET or (m and m.group(1) in FIELDSET):
            k = line if line in FIELDSET else m.group(1)
            if k in f:          # second copy of the submission in a forward chain → stop
                break
            f[k] = "" if line in FIELDSET else m.group(2).strip(); cur = k; continue
        if line.lower().startswith("submitted "):
            f["_submitted"] = line[len("submitted "):].strip(); cur = None
            if "billingAddress" in f:
                break
            continue
        if cur:
            f[cur] = (f[cur] + " " + line).strip() if f[cur] else line
    if "email" in f:
        m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", f["email"])
        f["email"] = m.group(0).lower() if m else ""
    return f if (f.get("email") and ("phoneNumber" in f or "billingAddress" in f)) else None


def fmt_address(f, kind="billing"):
    """'street; city, ST zip' (+ '; Country' if not US) — the format qb_invoice.py's bill_block expects."""
    g = lambda s: (f.get(kind + s) or "").strip()
    street, city, st, z, ctry = g("Address"), g("City"), g("State"), g("Zip"), g("Country")
    if not street:
        return None
    line2 = ", ".join(x for x in [city, " ".join(x for x in [st, z] if x)] if x)
    parts = [street] + ([line2] if line2 else []) + ([] if ctry.lower() in US else [ctry])
    return "; ".join(parts)


def is_questionnaire(subject, text=""):
    return bool(SUBJECT_RE.search(subject or "")) or ("payloadAdministrator" in text and "billingAddress" in text)


# ── comparison helpers ───────────────────────────────────────────────────────
def digits(p):
    d = re.sub(r"\D", "", p or "")
    return d[1:] if len(d) == 11 and d.startswith("1") else d


def addr_key(a):
    toks = re.findall(r"[a-z0-9]+", (a or "").lower())
    drop = {"usa", "us", "united", "states", "of", "america"}
    ab = {"drive": "dr", "street": "st", "avenue": "ave", "road": "rd", "boulevard": "blvd", "lane": "ln", "suite": "ste"}
    return " ".join(ab.get(t, t) for t in toks if t not in drop)


def same_addr(a, b):
    ka, kb = addr_key(a), addr_key(b)
    return ka == kb or (ka and kb and (ka in kb or kb in ka))


# ── IO ───────────────────────────────────────────────────────────────────────
def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as fh:
        fh.write(time.strftime("%Y-%m-%d %H:%M ") + m + "\n")


def _key():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def sb(method, path, body=None):
    k = _key()
    r = urllib.request.Request(SB + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                               headers={"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json",
                                        "Prefer": "return=representation"})
    raw = urllib.request.urlopen(r, timeout=30).read().decode()
    return json.loads(raw) if raw.strip() else []


def contacts_by_email(addr):
    rows = sb("GET", "contacts?select=id,name,email,phone,organization,notes,company_id,created_at"
                     f"&email=ilike.{urllib.parse.quote(addr)}&order=created_at.asc")
    return [r for r in rows if (r.get("email") or "").strip().lower() == addr]


ADDR_LINE = re.compile(r"^Billing address:\s*(.+?)\s*(?:\[[^\]]*\])?\s*$", re.I | re.M)


# ── apply one submission ─────────────────────────────────────────────────────
def apply(f, live, src="", res=None):
    res = res if res is not None else {"contacts_updated": 0, "contacts_created": 0, "companies_updated": 0,
                                       "orders_updated": 0, "conflicts": []}
    addr = f["email"]; phone = (f.get("phoneNumber") or "").strip() or None
    bill = fmt_address(f, "billing"); ship = fmt_address(f, "shipping")
    when = f.get("_submitted") or src
    tag = f"[payload questionnaire {when}]".replace("  ", " ")
    W = "" if live else "[dry] "

    def conflict(where, field, have, got):
        c = f"{where} {field}: has '{have}', questionnaire says '{got}' — kept existing"
        res["conflicts"].append(c); print("  ! CONFLICT " + c); log(("" if live else "[dry] ") + "CONFLICT " + c)

    # 1) CRM contacts — upsert by email
    rows = contacts_by_email(addr)
    if not rows:
        org = (f.get("customerName") or f.get("payloadCustomer") or "").strip()
        rec = {"name": (f.get("payloadAdministrator") or addr.split("@")[0]).strip(), "email": addr, "phone": phone,
               "organization": org, "source": "payload-questionnaire", "stage": "Lead", "type": "Lead", "status": "new",
               "owner": "Jon", "tags": ["inbound", "lead", "website", "payload-questionnaire"],
               "notes": "\n".join(x for x in [f"Billing address: {bill} {tag}" if bill else "",
                                               f"Shipping address: {ship} {tag}" if ship and not same_addr(ship, bill) else ""] if x)}
        print(f"  {W}+ CRM contact {rec['name']} <{addr}> phone={phone} billing={bill}")
        if live:
            sb("POST", "contacts", rec); log(f"created contact {addr} from questionnaire {when}")
        res["contacts_created"] += 1
        rows = []
    company_ids = set()
    for r in rows:
        patch = {}
        if r.get("company_id"):
            company_ids.add(r["company_id"])
        if phone:
            if not (r.get("phone") or "").strip():
                patch["phone"] = phone
            elif digits(r["phone"]) != digits(phone):
                conflict(f"contact {r['id']} <{addr}>", "phone", r["phone"], phone)
        notes = r.get("notes") or ""
        if bill:
            m = ADDR_LINE.search(notes)
            if not m:
                add = f"Billing address: {bill} {tag}"
                if ship and not same_addr(ship, bill) and "Shipping address:" not in notes:
                    add += f"\nShipping address: {ship} {tag}"
                patch["notes"] = (notes.rstrip() + "\n" + add).strip()
            elif not same_addr(m.group(1), bill):
                conflict(f"contact {r['id']} <{addr}>", "billing address", m.group(1), bill)
        if patch:
            print(f"  {W}~ CRM contact {r['id']} <{addr}> ({r.get('name')}): " +
                  ", ".join(f"{k}={'+Billing address line' if k == 'notes' else v}" for k, v in patch.items()))
            if live:
                sb("PATCH", f"contacts?id=eq.{r['id']}", patch); log(f"contact {r['id']} <{addr}> filled {list(patch)} from questionnaire {when}")
            res["contacts_updated"] += 1

    # 2) CRM company (linked via company_id) — address only (the phone is the administrator's cell, not the company's)
    for cid in company_ids:
        co = (sb("GET", f"companies?id=eq.{cid}&select=id,name,address") or [None])[0]
        if not co or not bill:
            continue
        if not (co.get("address") or "").strip():
            print(f"  {W}~ CRM company {co['name']}: address={bill}")
            if live:
                sb("PATCH", f"companies?id=eq.{cid}", {"address": bill}); log(f"company {co['name']} address filled from questionnaire {when}")
            res["companies_updated"] += 1
        elif not same_addr(co["address"], bill):
            conflict(f"company {co['name']}", "address", co["address"], bill)

    # 3) payload orders with this contact email (read → transform in memory → tmp → os.replace; MC reads it live)
    try:
        d = json.loads(open(ORDERS).read())
    except Exception:
        d = {"orders": []}
    changed = False
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for o in d.get("orders", []):
        if (o.get("contact_email") or "").strip().lower() != addr:
            continue
        upd = []
        if phone:
            if not (o.get("contact_phone") or "").strip():
                o["contact_phone"] = phone; upd.append("contact_phone")
            elif digits(o["contact_phone"]) != digits(phone):
                conflict(f"order {o['id']}", "contact_phone", o["contact_phone"], phone)
        if bill:
            if not (o.get("billing_address") or "").strip():
                o["billing_address"] = bill; upd.append("billing_address")
            elif not same_addr(o["billing_address"], bill):
                conflict(f"order {o['id']}", "billing_address", o["billing_address"], bill)
        if upd:
            print(f"  {W}~ payload order {o['id']}: " + ", ".join(f"{k}={o[k]}" for k in upd))
            o.setdefault("history", []).append({"at": stamp, "by": "Exo", "email": "exo", "action": "updated",
                                                "detail": f"{', '.join(upd)} from payload questionnaire ({when})"})
            o["updated_at"] = stamp
            res["orders_updated"] += 1; changed = True
    if changed and live:
        tmp = ORDERS + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(d, fh, indent=1)
        os.replace(tmp, ORDERS)
        log(f"payload orders for {addr} filled from questionnaire {when}")
    return res


def process_message(msg, live, seen=None):
    """Hook for mailbox scanners (payload_intake_quote.py). Returns the parsed fields or None."""
    subject = str(make_header(decode_header(msg.get("Subject", ""))))
    text = _text(msg)
    if not is_questionnaire(subject, text):
        return None
    f = parse(text)
    if not f:
        return None
    key = f"{f['email']}|{f.get('_submitted', '')}"
    if seen is not None and key in seen:
        return None
    print(f"questionnaire: {f.get('payloadCustomer') or f.get('customerName')} <{f['email']}> submitted {f.get('_submitted')}")
    apply(f, live, src=msg.get("Date", ""))
    if seen is not None:
        seen.add(key)
    return f


def main():
    live = "--live" in sys.argv
    backfill = "--backfill" in sys.argv
    days = int(sys.argv[sys.argv.index("--since-days") + 1]) if "--since-days" in sys.argv else 3
    pw = json.load(open(SECRETS))["protonmail_bridge_smtp_password"]
    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.login(EMAIL_USER, pw)
    m.select('"All Mail"' if backfill else "INBOX", readonly=True)
    if backfill:
        _t, data = m.search(None, "BODY", "payloadAdministrator")
    else:
        since = time.strftime("%d-%b-%Y", time.localtime(time.time() - days * 86400))
        _t, data = m.search(None, "SINCE", since, "BODY", "payloadAdministrator")
    ids = data[0].split() if data and data[0] else []
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {"seen": []}
    seen = set() if backfill else set(st.get("seen", []))
    subs = {}
    for i in ids:
        _t, dd = m.fetch(i, "(BODY.PEEK[])")
        msg = email.message_from_bytes(dd[0][1])
        subject = str(make_header(decode_header(msg.get("Subject", ""))))
        f = parse(_text(msg)) if is_questionnaire(subject, "payloadAdministrator billingAddress") else None
        if f:
            subs.setdefault(f"{f['email']}|{f.get('_submitted', '')}", (f, msg.get("Date", "")))
    m.logout()
    print(f"{len(ids)} message(s) matched, {len(subs)} distinct submission(s){'' if live else '  [DRY RUN]'}")
    res = {"contacts_updated": 0, "contacts_created": 0, "companies_updated": 0, "orders_updated": 0, "conflicts": []}
    for key, (f, date) in subs.items():
        if key in seen:
            continue
        print(f"\n• {f.get('payloadCustomer') or f.get('customerName')} <{f['email']}> phone={f.get('phoneNumber')} "
              f"billing={fmt_address(f)} (submitted {f.get('_submitted')})")
        apply(f, live, src=date, res=res)
        seen.add(key)
    print(f"\ncontacts updated {res['contacts_updated']} · created {res['contacts_created']} · companies {res['companies_updated']}"
          f" · orders {res['orders_updated']} · conflicts {len(res['conflicts'])}{'' if live else '  [DRY RUN]'}")
    if live and not backfill:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        tmp = STATE + ".tmp"; json.dump({"seen": sorted(seen)[-2000:]}, open(tmp, "w")); os.replace(tmp, STATE)


if __name__ == "__main__":
    main()
