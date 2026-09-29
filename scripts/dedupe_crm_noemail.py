#!/usr/bin/env python3
"""
CRM DEDUPE (no-email contacts) — conservative second pass, zero LLM tokens.

Contacts with no email can't be matched by address, so we match on EXACT
normalized (name + organization) where BOTH are present and the name is real
(>2 chars). Keep the richest record, remove the rest. Anything with only a name
(no org) or junk is left ALONE — too risky to merge without a second signal.

Run:  python3 scripts/dedupe_crm_noemail.py            # dry-run (shows matches)
      python3 scripts/dedupe_crm_noemail.py --apply     # backup, then merge
"""
import os, sys, json, re, time, urllib.request
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


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def richness(c):
    score = sum(1 for k in ("phone", "title", "notes", "status", "stage") if (c.get(k) or "").strip())
    score += 5 * sum(1 for k in ("company_id", "crm_id") if c.get(k))
    return score


def main():
    noemail = [c for c in all_contacts() if not (c.get("email") or "").strip()]
    groups = defaultdict(list)
    unmergeable = 0
    for c in noemail:
        nm, org = norm(c.get("name")), norm(c.get("organization"))
        if len(nm) > 2 and org:               # require BOTH name and org
            groups[(nm, org)].append(c)
        else:
            unmergeable += 1
    dupes = {k: cs for k, cs in groups.items() if len(cs) > 1}
    to_remove = sum(len(cs) - 1 for cs in dupes.values())
    print(f"no-email contacts: {len(noemail)} | with name+org: {sum(len(cs) for cs in groups.values())} | "
          f"unmergeable (no name/org): {unmergeable}")
    print(f"name+org duplicate groups: {len(dupes)} | would remove: {to_remove}\n")
    for (nm, org), cs in sorted(dupes.items(), key=lambda kv: -len(kv[1]))[:25]:
        print(f"  {cs[0].get('name')} @ {cs[0].get('organization')}: {len(cs)} copies")

    if not APPLY:
        print(f"\nDRY-RUN — nothing changed. Re-run with --apply to merge the {to_remove} duplicates.")
        return

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    bpath = os.path.join(WS, "logs", f"crm-dedupe-noemail-backup-{ts}.json")
    json.dump(noemail, open(bpath, "w"))
    print(f"\nbackup written: {bpath}")

    remove_ids = []
    for k, cs in dupes.items():
        cs_sorted = sorted(cs, key=lambda c: (-richness(c), str(c.get("created_at") or ""), str(c.get("id"))))
        remove_ids += [c["id"] for c in cs_sorted[1:]]
    removed, failed = 0, 0
    for i in range(0, len(remove_ids), 100):
        chunk = remove_ids[i:i + 100]
        idlist = ",".join(f'"{x}"' for x in chunk)
        try:
            # Recycle bin (exo3 2026-09-28): snapshot FULL rows first; snapshot failure = no delete.
            full = req(f"contacts?id=in.({idlist})")
            mc_recycle.snapshot_rows("contacts", full, who="dedupe_crm_noemail.py", route="scripts/dedupe_crm_noemail.py")
            req(f"contacts?id=in.({idlist})", "DELETE"); removed += len(chunk)
        except Exception:
            failed += len(chunk)
        time.sleep(0.05)
    print(f"APPLIED — merged {removed} no-email duplicates ({failed} blocked).")


if __name__ == "__main__":
    main()
