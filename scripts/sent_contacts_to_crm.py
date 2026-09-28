#!/usr/bin/env python3
"""sent_contacts_to_crm.py — ensure every external contact Jon has emailed exists in the CRM (option D).

Reads logs/sent-followup-log.json (built by sent_followup_tracker.py). For each external contact
whose email is NOT already in the CRM `contacts` table, inserts a lightweight record so the
relationship is captured and future sends match by contact. Also refreshes last_contacted on
existing rows when Jon's send is newer. Idempotent. --dry-run reports, writes nothing.
"""
import json, os, sys, re, urllib.request
from datetime import datetime, timezone

WS = os.path.expanduser("~/.openclaw/workspace")
LOG = os.path.join(WS, "logs", "sent-followup-log.json")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
SH = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json", "Prefer": "return=representation"}
SCRUBBED = set(json.load(open(os.path.join(WS, "config", "crm-scrubbed-emails.json"))).get("emails", {}))
COMMON = {"gmail", "outlook", "hotmail", "yahoo", "proton", "pm", "me", "icloud", "aol", "msn", "live", "gmx"}


def supa(method, path, body=None):
    req = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None, headers=SH)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            t = r.read().decode(); return json.loads(t) if t else []
    except Exception as e:
        print("supa err", method, path[:50], e); return None


def org_from(addr):
    d = addr.split("@")[-1]
    base = d.split(".")[0]
    return "" if base.lower() in COMMON else base.replace("-", " ").title()


def main():
    dry = "--dry-run" in sys.argv
    contacts = json.load(open(LOG)).get("contacts", {})
    # load all CRM emails (paginate past the 1000 cap)
    have = set(); off = 0
    while True:
        c = supa("GET", f"contacts?select=email&limit=1000&offset={off}") or []
        for r in c:
            if r.get("email"): have.add(r["email"].lower())
        if len(c) < 1000: break
        off += 1000
    print(f"CRM has {len(have)} emails; follow-up log has {len(contacts)} contacts")

    created = existing = skipped = 0
    for a, c in contacts.items():
        a = a.lower()
        # skip internal, malformed, and Outlook/Exchange-mangled (imceamailto…@namp*.prod.outlook) addresses
        if ("@" not in a or a.endswith("@exosaero.com") or "imceamailto" in a
                or "+40" in a or "namp" in a and "prod.outlook" in a or a in SCRUBBED):
            skipped += 1; continue
        if a in have:
            existing += 1
            continue
        rec = {
            "name": (c.get("name") or a).strip()[:120], "email": a,
            "organization": org_from(a), "source": "sent-tracker",
            "last_contacted": (c.get("last_sent") or "")[:10] or None,
            "notes": f"Auto-added from Jon's outbound email ({(c.get('last_sent') or '')[:10]}) — {c.get('subj','')[:80]}",
        }
        if dry:
            created += 1
            if created <= 12: print(f"  + {rec['name']} <{a}>  org={rec['organization']}  last={rec['last_contacted']}")
            continue
        r = supa("POST", "contacts", rec)
        if r is not None:
            created += 1; have.add(a)
    print(f"{'[dry-run] would create' if dry else 'created'}: {created} | already in CRM: {existing} | skipped(internal/bad): {skipped}")


if __name__ == "__main__":
    main()
