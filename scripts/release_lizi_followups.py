#!/usr/bin/env python3
"""
release_lizi_followups.py — date-gated release of Lizi's BLK3 payload follow-up tasks.

Lizi wanted 50 individual follow-up tasks (one per contact) to STAY OFF her Mission
Control board until 2026-08-17. They were snapshotted to logs/lizi-followups-pending.json
and deleted from the live board. This launchd-run script (daily 07:00) recreates them on
or after the release_date, assigned to Lizi, and pre-seeds the assignment-notifier state so
recreating 50 tasks does NOT blast her with 50 emails. Idempotent: once released, it deletes
the pending file and no-ops thereafter.
"""
import json, os, sys, time, urllib.request
from datetime import datetime

WS = "/Users/exomac/.openclaw/workspace"
PENDING = os.path.join(WS, "logs", "lizi-followups-pending.json")
NOTIFY_STATE = os.path.join(WS, "logs", "assignment-notify-state.json")
LOG = os.path.join(WS, "logs", "release-lizi-followups.log")
LIZI = "lquinn@exosaero.com"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}


def log(m):
    open(LOG, "a").write(f"[{time.strftime('%Y-%m-%d %H:%M:%S %Z')}] {m}\n")


def rq(method, url, data=None):
    for a in range(4):
        try:
            r = urllib.request.Request(
                url, data=(json.dumps(data).encode() if data is not None else None),
                headers={**H, "Prefer": "return=representation"}, method=method)
            b = urllib.request.urlopen(r, timeout=60).read()
            return json.loads(b) if b else []
        except Exception as e:
            log(f"retry {method} {a}: {e}"); time.sleep(3)
    raise SystemExit("supabase request failed")


def main():
    if not os.path.exists(PENDING):
        return  # nothing pending -> no-op
    cfg = json.load(open(PENDING))
    today = datetime.now().strftime("%Y-%m-%d")   # host TZ = America/Chicago
    if today < cfg["release_date"]:
        log(f"not yet: today {today} < release {cfg['release_date']} ({len(cfg['rows'])} pending)")
        return
    now = datetime.now().astimezone().isoformat()
    rows = cfg["rows"]
    for r in rows:
        r["assigned_at"] = now
    created = rq("POST", SB + "/tasks", rows)
    ids = [str(c["id"]) for c in created]
    # pre-seed notifier state so these do NOT email Lizi 50x on recreate
    try:
        st = json.load(open(NOTIFY_STATE)) if os.path.exists(NOTIFY_STATE) else {}
        for tid in ids:
            st[tid] = LIZI
        json.dump(st, open(NOTIFY_STATE, "w"))
    except Exception as e:
        log(f"WARN notifier pre-seed failed: {e}")
    # mark released: archive the pending file so we never double-insert
    os.rename(PENDING, PENDING + f".released-{today}")
    log(f"RELEASED {len(created)} follow-up tasks to Lizi (ids {ids[0]}..{ids[-1]}); notifier suppressed")


if __name__ == "__main__":
    main()
