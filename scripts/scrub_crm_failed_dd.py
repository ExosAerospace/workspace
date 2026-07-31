#!/usr/bin/env python3
"""
CRM FAILED-DD SCRUB — deterministic, zero LLM tokens.

Two passes over the existing CRM contacts:
  1. REGISTRY match (definitive): contact email/domain/name is in the failed-DD
     registry -> flag status=failed-dd, tag do-not-engage, annotate. (auto-applies)
  2. HEURISTIC suspects (advisory): name/org/notes carry classic cold-broker /
     advance-fee scam phrasing -> listed for human review, NOT auto-changed.

Run:  python3 scripts/scrub_crm_failed_dd.py [--apply]   (default = dry-run)
"""
import os, sys, json, re, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failed_dd

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
KEY = json.load(open(SECRETS))["supabase_service_role_key"]
APPLY = "--apply" in sys.argv

# Conservative cold-broker / advance-fee phrasing (scam-pitch tells), advisory only.
SCAM_RE = re.compile(r"(funding solutions|financing solutions|capital associate|"
                     r"funding options for (expansion|operational)|advance[- ]?fee|"
                     r"commitment fee|proof of funds|guaranteed (funding|loan|approval)|"
                     r"we can fund your|business funding specialist)", re.I)
FREEMAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "proton.me", "icloud.com"}


def req(path, method="GET", body=None):
    r = urllib.request.Request(B + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(r, timeout=40) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else []


def all_contacts():
    out, off = [], 0
    while True:
        page = req(f"contacts?select=id,name,email,organization,notes,tags,status&order=id&limit=1000&offset={off}")
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def main():
    contacts = all_contacts()
    print(f"scanning {len(contacts)} CRM contacts (mode: {'APPLY' if APPLY else 'DRY-RUN'})\n")
    reg_hits, suspects = [], []
    for c in contacts:
        email = (c.get("email") or "").lower()
        name = c.get("name") or ""
        org = c.get("organization") or ""
        hit = failed_dd.check(email=email, name=(name or org))
        if hit:
            reg_hits.append((c, hit)); continue
        blob = f"{name} {org} {c.get('notes','')}"
        if SCAM_RE.search(blob):
            dom = email.split("@")[-1] if "@" in email else ""
            suspects.append((c, dom in FREEMAIL or not org))
    # PASS 1: registry matches -> auto-flag
    print(f"=== REGISTRY MATCHES (known failed-DD): {len(reg_hits)} ===")
    for c, hit in reg_hits:
        tags = list(dict.fromkeys((c.get("tags") or []) + ["failed-dd", "do-not-engage"]))
        note = (c.get("notes") or "") + f"\n⚠️ FAILED DD ({hit.get('firm')}): {hit.get('reason','')} [do-not-engage]"
        print(f"  {'[flag]' if APPLY else '[would flag]'} #{c['id']} {c.get('name')} <{c.get('email')}> [{hit.get('firm')}]")
        if APPLY:
            req(f"contacts?id=eq.{c['id']}", "PATCH", {"status": "failed-dd", "tags": tags, "notes": note[:4000]})
    # PASS 2: heuristic suspects -> advisory list only
    print(f"\n=== HEURISTIC SUSPECTS (review, NOT auto-changed): {len(suspects)} ===")
    for c, strong in sorted(suspects, key=lambda x: -x[1])[:40]:
        print(f"  {'‼' if strong else '·'} #{c['id']} {c.get('name')} <{c.get('email')}>  org='{c.get('organization') or ''}'")
    if len(suspects) > 40:
        print(f"  ... and {len(suspects)-40} more")
    print(f"\nDONE — {len(reg_hits)} registry-flagged{' (applied)' if APPLY else ' (dry-run)'}, {len(suspects)} suspects to review.")


if __name__ == "__main__":
    main()
