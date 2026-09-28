#!/usr/bin/env python3
"""
Daily Supabase backup for Exos Mission Control.
Dumps every CRM table (paginated, full rows) to a dated, gzipped snapshot,
plus the local users.json (access-control source of truth).
Retains the last RETENTION_DAYS daily snapshots. Writes a heartbeat file the
Cron Failure Watchdog / verification can read.

Install: launchd com.exos.supabase-backup (daily). Safe to run manually.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import os, sys, json, gzip, time, urllib.request, urllib.error, datetime, shutil

SB   = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY  = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
ROOT = os.path.expanduser("~/.openclaw/workspace")
BKDIR = os.path.join(ROOT, "mission-control/data/backups/supabase")
USERS = os.path.join(ROOT, "mission-control/users.json")
HEARTBEAT = os.path.join(BKDIR, "_last_backup.json")
TABLES = ["contacts", "companies", "deals", "tasks", "activities", "templates"]
RETENTION_DAYS = 30
PAGE = 1000
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}

def fetch_all(table):
    rows, offset = [], 0
    while True:
        url = f"{SB}/{table}?select=*&limit={PAGE}&offset={offset}"
        req = urllib.request.Request(url, headers=H)
        try:
            with urllib.request.urlopen(req, timeout=60) as f:
                batch = json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:  # table doesn't exist — skip
                return None
            raise
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        offset += PAGE
    return rows

def main():
    day = datetime.date.today().isoformat()
    dest = os.path.join(BKDIR, day)
    os.makedirs(dest, exist_ok=True)
    summary = {"date": day, "started": datetime.datetime.now().isoformat(timespec="seconds"),
               "tables": {}, "ok": True, "errors": []}

    for t in TABLES:
        try:
            rows = fetch_all(t)
            if rows is None:
                summary["tables"][t] = "absent"
                continue
            with gzip.open(os.path.join(dest, f"{t}.json.gz"), "wt", encoding="utf-8") as g:
                json.dump(rows, g, ensure_ascii=False)
            summary["tables"][t] = len(rows)
        except Exception as e:
            summary["ok"] = False
            summary["errors"].append(f"{t}: {e}")
            summary["tables"][t] = "ERROR"

    # users.json (local access-control roles) — critical, not in Supabase
    try:
        if os.path.exists(USERS):
            shutil.copy2(USERS, os.path.join(dest, "users.json"))
            summary["tables"]["users.json"] = "copied"
    except Exception as e:
        summary["ok"] = False
        summary["errors"].append(f"users.json: {e}")

    summary["finished"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(os.path.join(dest, "_manifest.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(HEARTBEAT, "w") as f:
        json.dump(summary, f, indent=2)

    # retention: prune day-dirs older than RETENTION_DAYS
    cutoff = datetime.date.today() - datetime.timedelta(days=RETENTION_DAYS)
    for name in os.listdir(BKDIR):
        p = os.path.join(BKDIR, name)
        if os.path.isdir(p):
            try:
                if datetime.date.fromisoformat(name) < cutoff:
                    shutil.rmtree(p)
            except ValueError:
                pass

    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary["ok"] else 1)

if __name__ == "__main__":
    os.makedirs(BKDIR, exist_ok=True)
    main()
