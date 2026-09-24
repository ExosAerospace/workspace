#!/usr/bin/env python3
"""
mc-snapshot-export.py — periodic full-table backup of the Mission Control Supabase DB.

Dumps each core table to mission-control/data/<table>-snapshot-latest.json (a stable path the
app / restore tooling can read) plus a rotating timestamped copy for point-in-time history.
Pages past PostgREST's 1000-row cap. Resilient: if the DB is unreachable this cycle it skips
quietly (no error, keeps the previous snapshot), matching the fleet's transient-blip policy.

Runs via launchd com.exos.mc-snapshot-export (every ~10 min).
"""
import json, os, time, urllib.request, urllib.error, glob, datetime

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control", "data")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
KEY = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"
TABLES = ["tasks", "decisions", "opportunities", "contacts", "activities"]
KEEP = 12            # timestamped copies to retain per table (~2h of history at 10-min cadence)
PAGE = 1000          # PostgREST hard cap per response
TIMEOUT = 12


def fetch_all(table):
    """Return all rows for a table, paging past the 1000-row cap. Raises on any failure so the
    caller can skip this table without overwriting a good snapshot with a partial/empty one."""
    rows, offset = [], 0
    while True:
        url = f"{SUPA}{table}?select=*&order=id&limit={PAGE}&offset={offset}"
        req = urllib.request.Request(url, headers={"apikey": KEY, "Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if not (200 <= r.status < 300):
                raise RuntimeError(f"{table} HTTP {r.status}")
            chunk = json.load(r)
        if not isinstance(chunk, list):
            raise RuntimeError(f"{table} non-list payload")
        rows.extend(chunk)
        if len(chunk) < PAGE:
            break
        offset += PAGE
    return rows


def rotate(table):
    files = sorted(glob.glob(os.path.join(DATA, f"{table}-snapshot-*.json")))
    for old in files[:-KEEP]:
        try: os.remove(old)
        except Exception: pass


def main():
    os.makedirs(DATA, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    ok, skipped = [], []
    for t in TABLES:
        try:
            rows = fetch_all(t)
        except Exception:
            skipped.append(t)   # DB down / table unreachable this cycle — keep prior snapshot
            continue
        payload = {"table": t, "captured_at": datetime.datetime.now().astimezone().isoformat(),
                   "count": len(rows), "rows": rows}
        blob = json.dumps(payload, ensure_ascii=False, default=str)
        with open(os.path.join(DATA, f"{t}-snapshot-latest.json"), "w", encoding="utf-8") as f:
            f.write(blob)
        with open(os.path.join(DATA, f"{t}-snapshot-{stamp}.json"), "w", encoding="utf-8") as f:
            f.write(blob)
        rotate(t)
        ok.append(f"{t}:{len(rows)}")
    line = f"{datetime.datetime.now().isoformat()} snapshot ok=[{', '.join(ok)}] skipped={skipped}"
    with open(os.path.join(WS, "logs", "mc-snapshot-export.log"), "a") as f:
        f.write(line + "\n")
    print(line)


if __name__ == "__main__":
    main()
