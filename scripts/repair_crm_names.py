#!/usr/bin/env python3
"""
CRM NAME REPAIR — no-email contacts whose name is a placeholder ("Position",
"Vendor Contacts", etc.) but that carry a real TITLE get their name set from the
title, so they become identifiable role-contacts instead of blank placeholders.
Safe UPDATE only (no deletes). Zero LLM tokens. Backup written first.

Run:  python3 scripts/repair_crm_names.py            # dry-run
      python3 scripts/repair_crm_names.py --apply
"""
import os, sys, json, re, time, urllib.request

SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
WS = os.path.expanduser("~/.openclaw/workspace")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
KEY = json.load(open(SECRETS))["supabase_service_role_key"]
APPLY = "--apply" in sys.argv
PH = re.compile(r'^(position|vendor contacts?|vacant|contracting office|gov and vendor|n/?a|unknown|tbd|contact list|point of contact|poc)\b', re.I)


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
        pg = req(f"contacts?select=id,name,email,organization,phone,title,tags&order=id&limit=1000&offset={off}")
        out += pg
        if len(pg) < 1000:
            return out
        off += 1000


def main():
    targets = [c for c in all_contacts()
               if not (c.get("email") or "").strip()
               and PH.match((c.get("name") or "").strip())
               and (c.get("title") or "").strip()]
    print(f"repairable placeholder-name contacts (have title): {len(targets)}")
    if APPLY:
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        json.dump(targets, open(os.path.join(WS, "logs", f"crm-name-repair-backup-{ts}.json"), "w"))
        print(f"backup written: logs/crm-name-repair-backup-{ts}.json")
    done = 0
    for c in targets:
        new_name = re.sub(r"\s+", " ", c["title"]).strip()[:120]
        tags = list(dict.fromkeys((c.get("tags") or []) + ["name-repaired"]))
        if not APPLY:
            if done < 8:
                print(f"  '{c.get('name')}' -> '{new_name[:70]}' @ {c.get('organization')}")
        else:
            try:
                req(f"contacts?id=eq.{c['id']}", "PATCH", {"name": new_name, "tags": tags}); done += 1
            except Exception:
                pass
            time.sleep(0.03)
    print(f"\n{'REPAIRED ' + str(done) if APPLY else 'DRY-RUN — ' + str(len(targets)) + ' would be repaired'}.")


if __name__ == "__main__":
    main()
