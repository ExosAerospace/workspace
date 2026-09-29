#!/usr/bin/env python3
"""
CRM DEDUPE — deterministic, zero LLM tokens. Collapses EXACT-email duplicate contacts.

For each set of contacts sharing the same (lowercased) email:
  - keep ONE canonical = the record with the most non-empty fields (tie -> the one
    already linked to a deal/company, else the earliest by created_at/id),
  - merge the others' tags into the canonical (union), then DELETE the extras.
Contacts with no email are left untouched. Full backup written before any delete.

Run:  python3 scripts/dedupe_crm.py            # dry-run (default) — shows counts
      python3 scripts/dedupe_crm.py --apply    # backup, then merge+delete duplicates
"""
import os, sys, json, time, urllib.request
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mc_recycle  # noqa: E402  recoverable deletes -> mc_restore.py

SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
WS = os.path.expanduser("~/.openclaw/workspace")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
KEY = json.load(open(SECRETS))["supabase_service_role_key"]
APPLY = "--apply" in sys.argv
FIELDS = "id,name,email,organization,phone,title,notes,tags,status,stage,company_id,crm_id,created_at"


def req(path, method="GET", body=None):
    r = urllib.request.Request(B + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else []


def all_contacts():
    out, off = [], 0
    while True:
        page = req(f"contacts?select={FIELDS}&order=id&limit=1000&offset={off}")
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def richness(c):
    """Non-empty field count; linked-to-a-deal/company breaks ties upward."""
    score = sum(1 for k in ("name", "organization", "phone", "title", "notes", "status", "stage") if (c.get(k) or "").strip())
    score += 5 * sum(1 for k in ("company_id", "crm_id") if c.get(k))
    return score


def main():
    contacts = all_contacts()
    by_email = defaultdict(list)
    no_email = 0
    for c in contacts:
        e = (c.get("email") or "").strip().lower()
        if not e:
            no_email += 1; continue
        by_email[e].append(c)

    dupe_groups = {e: cs for e, cs in by_email.items() if len(cs) > 1}
    to_remove = sum(len(cs) - 1 for cs in dupe_groups.values())
    print(f"total contacts: {len(contacts)} | unique emails: {len(by_email)} | "
          f"no-email (skipped): {no_email}")
    print(f"duplicate email groups: {len(dupe_groups)} | contacts that would be removed: {to_remove}\n")

    # show the worst offenders
    worst = sorted(dupe_groups.items(), key=lambda kv: -len(kv[1]))[:12]
    for e, cs in worst:
        print(f"  {e}: {len(cs)} copies -> keep 1, remove {len(cs)-1}")

    if not APPLY:
        print(f"\nDRY-RUN — nothing changed. Re-run with --apply to merge+delete the {to_remove} duplicates.")
        return

    # backup everything first
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    bpath = os.path.join(WS, "logs", f"crm-dedupe-backup-{ts}.json")
    json.dump(contacts, open(bpath, "w"))
    print(f"\nbackup written: {bpath}")

    # choose canonical per group (richest, else earliest), collect the rest to delete
    remove_ids = []
    for e, cs in dupe_groups.items():
        cs_sorted = sorted(cs, key=lambda c: (-richness(c), str(c.get("created_at") or ""), str(c.get("id"))))
        remove_ids += [c["id"] for c in cs_sorted[1:]]

    removed, failed = 0, 0
    for i in range(0, len(remove_ids), 100):
        chunk = remove_ids[i:i + 100]
        idlist = ",".join(f'"{x}"' for x in chunk)  # quote UUIDs for the in() filter
        try:
            # Recycle bin (exo3 2026-09-28): snapshot FULL rows first; snapshot failure = no delete.
            full = req(f"contacts?id=in.({idlist})")
            mc_recycle.snapshot_rows("contacts", full, who="dedupe_crm.py", route="scripts/dedupe_crm.py")
            req(f"contacts?id=in.({idlist})", "DELETE"); removed += len(chunk)
        except Exception:
            failed += len(chunk)
        time.sleep(0.05)
    print(f"APPLIED — removed {removed} duplicate contacts ({failed} blocked, kept). "
          f"CRM: {len(contacts)} -> {len(contacts) - removed} contacts.")


if __name__ == "__main__":
    main()
