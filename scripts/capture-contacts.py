#!/usr/bin/env python3
"""
capture-contacts.py — auto-capture every external contact from email into a contacts table.

Scans INBOX + Sent (incremental by UID; full backfill on first run since BACKFILL_SINCE),
extracts each external person you correspond with, filters newsletters/no-reply/internal,
and merges into mission-control/data/contacts.json — deduped by email, with first/last
touch, in/out counts, company (from domain), sample subjects, a company rollup, and a
"known in investor CRM" flag. Idempotent; preserves first_seen. Fail-soft.

Wired into the dashboard refresh so the CRM grows itself as contacts are made.
"""
import imaplib, email, json, os, re, glob
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import getaddresses, parsedate_to_datetime

WS = "/Users/exomac/.openclaw/workspace"
OUT = os.path.join(WS, "mission-control", "data", "contacts.json")
STATE = os.path.join(WS, "logs", "contacts-capture-state.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
BACKFILL_SINCE = "01-Jan-2026"

OWN = {"exosaero.com", "pm.me", "proton.me", "protonmail.com", "exosaero.onmicrosoft.com"}
PERSONAL = {"gmail.com", "outlook.com", "yahoo.com", "aol.com", "hotmail.com",
            "icloud.com", "me.com", "proton.me", "protonmail.com", "live.com", "msn.com"}
SKIP_ADDR = re.compile(
    r"no[-_.]?reply|do[-_.]?not[-_.]?reply|donotreply|mailer-daemon|postmaster|"
    r"notifications?@|notification@|bounce|calendar-notification|@news\.|@updates\.|"
    r"@mail\.|@email\.|@e\.|@marketing\.|newsletter|sendgrid|mailchimp|substack|"
    r"amazonses|@m\.discord|insideapple|@id\.apple|invoice|receipts?\+|stripe\.com|"
    r"realvnc|finelo|members\.|@info\.", re.I)
KNOWN_SOURCES = ["mission-control/crm-data.json", "mission-control/data/crm.json",
                 "SERIES_A_SCORED_CRM.md", "stratelligence" ]  # last is harmless filler


def dec(s):
    if not s:
        return ""
    out = ""
    for t, enc in decode_header(s):
        out += t.decode(enc or "utf-8", "ignore") if isinstance(t, bytes) else t
    return out


def load_json(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def save_json(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)


def known_emails():
    rx = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
    s = set()
    for f in ["mission-control/crm-data.json", "mission-control/data/crm.json",
              "SERIES_A_SCORED_CRM.md", "opportunities-tracker.md"]:
        try:
            for e in rx.findall(open(os.path.join(WS, f), encoding="utf-8", errors="ignore").read()):
                s.add(e.lower())
        except Exception:
            pass
    return s


def domain_of(e):
    return e.split("@")[-1].lower() if "@" in e else ""


_ALIASES = None
def _aliases():
    global _ALIASES
    if _ALIASES is None:
        _ALIASES = {k.lower(): v for k, v in
                    load_json(os.path.join(WS, "config", "company-aliases.json"), {}).items()
                    if not k.startswith("_")}
    return _ALIASES


def company_from(domain):
    if not domain or domain in PERSONAL:
        return "(personal / unknown)"
    al = _aliases()
    if domain in al:
        return al[domain]
    # generic gov/mil fallback if not explicitly mapped
    if domain.endswith(".mil"):
        return "U.S. Military (" + domain + ")"
    if domain.endswith(".gov"):
        parts = domain.split(".")
        return (parts[-3] if len(parts) >= 3 else parts[0]).upper() + " (gov)"
    parts = domain.split(".")
    root = parts[-2] if len(parts) >= 2 else parts[0]
    root = root.replace("-", " ")
    root = re.sub(r"(?<=[a-zA-Z])(?=[0-9])|(?<=[0-9])(?=[a-zA-Z])", " ", root)  # split letters/digits
    return root.title()


def keep(addr):
    if not addr or "@" not in addr:
        return False
    if domain_of(addr) in OWN:
        return False
    if SKIP_ADDR.search(addr):
        return False
    return True


def main():
    pw = load_json(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if not pw:
        print("no IMAP password; abort")
        return
    state = load_json(STATE, {})
    known = known_emails()
    db = {c["email"]: c for c in load_json(OUT, {}).get("contacts", [])}
    prev_count = len(db)

    try:
        m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        m.starttls()
        m.login(EMAIL_USER, pw)
    except Exception as e:
        print("IMAP login failed:", e)
        return

    def upsert(name, addr, direction, dt, subj):
        addr = addr.lower().strip()
        if not keep(addr):
            return
        c = db.get(addr)
        iso = dt.strftime("%Y-%m-%d") if dt else ""
        if not c:
            c = {"email": addr, "name": dec(name).strip().strip('"'),
                 "company": company_from(domain_of(addr)), "domain": domain_of(addr),
                 "first_seen": iso, "last_seen": iso, "in_count": 0, "out_count": 0,
                 "subjects": [], "known_crm": addr in known, "first_seen_run": True}
            db[addr] = c
        nm = dec(name).strip().strip('"')
        if nm and not c.get("name"):
            c["name"] = nm
        c[direction + "_count"] = c.get(direction + "_count", 0) + 1
        if iso:
            if not c.get("first_seen") or iso < c["first_seen"]:
                c["first_seen"] = iso
            if not c.get("last_seen") or iso > c["last_seen"]:
                c["last_seen"] = iso
                if subj:
                    c["last_subject"] = subj[:80]
        if subj and len(c["subjects"]) < 3 and subj[:60] not in c["subjects"]:
            c["subjects"].append(subj[:60])

    for c in db.values():
        c["first_seen_run"] = False  # reset; mark only contacts newly added this run

    full = os.environ.get("CAPTURE_FULL") == "1"
    if full:
        # One-time full-history pass over the entire mailbox (All Mail, no date floor).
        # Direction inferred per message: sent if From is one of our own addresses.
        try:
            m.select('"All Mail"')
            typ, data = m.uid("search", None, "ALL")
            uids = [int(x) for x in data[0].split()] if data and data[0] else []
        except Exception as e:
            print("All Mail scan failed:", e)
            uids = []
        print(f"full backfill: scanning {len(uids)} messages in All Mail")
        for i, u in enumerate(uids):
            typ, d = m.uid("fetch", str(u), "(BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE SUBJECT)])")
            if not d or not d[0]:
                continue
            msg = email.message_from_bytes(d[0][1])
            try:
                dt = parsedate_to_datetime(msg["Date"]).replace(tzinfo=None)
            except Exception:
                dt = None
            subj = dec(msg["Subject"])
            frm = getaddresses([msg.get("From", "")])
            outbound = any(domain_of(a) in OWN for _, a in frm)
            if outbound:
                for nm, ad in getaddresses([msg.get("To", "")]) + getaddresses([msg.get("Cc", "")]):
                    upsert(nm, ad, "out", dt, subj)
            else:
                for nm, ad in frm:
                    upsert(nm, ad, "in", dt, subj)
    else:
        for folder, direction in [("INBOX", "in"), ("Sent", "out")]:
            try:
                m.select(folder)
            except Exception:
                continue
            last_uid = int(state.get(folder, 0))
            if last_uid:
                typ, data = m.uid("search", None, f"UID {last_uid+1}:*")
            else:
                typ, data = m.uid("search", None, "SINCE", BACKFILL_SINCE)
            uids = [int(x) for x in data[0].split()] if data and data[0] else []
            uids = [u for u in uids if u > last_uid]
            maxu = last_uid
            for u in uids:
                maxu = max(maxu, u)
                typ, d = m.uid("fetch", str(u), "(BODY.PEEK[HEADER.FIELDS (FROM TO CC DATE SUBJECT)])")
                if not d or not d[0]:
                    continue
                msg = email.message_from_bytes(d[0][1])
                try:
                    dt = parsedate_to_datetime(msg["Date"]).replace(tzinfo=None)
                except Exception:
                    dt = None
                subj = dec(msg["Subject"])
                if folder == "INBOX":
                    for nm, ad in getaddresses([msg.get("From", "")]):
                        upsert(nm, ad, "in", dt, subj)
                else:
                    for nm, ad in getaddresses([msg.get("To", "")]) + getaddresses([msg.get("Cc", "")]):
                        upsert(nm, ad, "out", dt, subj)
            state[folder] = maxu
    try:
        m.logout()
    except Exception:
        pass

    contacts = list(db.values())
    for c in contacts:
        c["total"] = c.get("in_count", 0) + c.get("out_count", 0)
        c["known_crm"] = c["email"] in known
        c["company"] = company_from(c.get("domain", ""))  # re-derive from current alias map
    contacts.sort(key=lambda c: (c.get("last_seen") or "", c.get("total", 0)), reverse=True)

    # company rollup
    comp = {}
    for c in contacts:
        if c["company"] == "(personal / unknown)":
            continue
        g = comp.setdefault(c["company"], {"company": c["company"], "domain": c["domain"],
                                           "contacts": 0, "last_seen": ""})
        g["contacts"] += 1
        if c.get("last_seen", "") > g["last_seen"]:
            g["last_seen"] = c["last_seen"]
    companies = sorted(comp.values(), key=lambda g: g["last_seen"], reverse=True)

    new_this_run = [c["email"] for c in contacts if c.get("first_seen_run")]
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    save_json(OUT, {"generated_display": stamp, "count": len(contacts),
                    "companies_count": len(companies),
                    "new_this_run": new_this_run,
                    "untracked_count": len([c for c in contacts if not c["known_crm"]]),
                    "contacts": contacts, "companies": companies})
    save_json(STATE, state)
    print(f"contacts: {len(contacts)} ({len(contacts)-prev_count} new), "
          f"{len(companies)} companies, {len(new_this_run)} added this run @ {stamp}")


if __name__ == "__main__":
    main()
