#!/usr/bin/env python3
"""One-time MC heads-up task for Steve Norsworthy (cc Victor Castilleja): the shop inventory workbook now
carries a permanent Exos ID column (exo3 shop-stable-ids; Jon 2026-09-30 #exomac-system 13:02 CDT:
"let Victor know as well").

Internal only: NO email, NO Discord. MC tasks have one assignee and no cc field, so the task is assigned to
Steve and Victor is cc'd in the body + a cc: tag. The assignment-notifier email is suppressed the same way
blk3_hvrr_weekly_plan.py does it; to close the race with the 5-min poller the task is created unassigned,
the suppress entry is written, THEN the assignee is set. Idempotent on source. The new workbook's
uploads/_meta.json entry is attached to the task (task_id).

  shop_ids_headsup_task.py            # dry-run: print the task
  shop_ids_headsup_task.py --apply
"""
import json, os, sys, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
SUP = os.path.join(WS, "logs", "assignment-notify-suppress.json")
META = os.path.join(WS, "mission-control", "uploads", "_meta.json")
SOURCE = "exo3-shop-stable-ids"
STORED = "1790791766628_Current_Inventory_Locations_EXOS-ID_2026-09-30.xlsx"
STEVE, STEVE_EMAIL = "Steve Norsworthy", "snorsworthy@exosaero.com"

TITLE = "Shop inventory sheet: new permanent Exos ID column — please use this file from now on"
DESC = f"""Steve, every line in your shop inventory workbook now has a permanent Exos ID in the last column of each sheet (Warehouse, Parts Room, Trailer, Assets). It keeps photos and edits in Mission Control attached to the right part, even when rows move.

Please:
- Start from the attached file ({STORED.split('_', 1)[1]}) from now on, and keep uploading it to MC as usual.
- Add, edit, move and delete rows as normal. For a new row, leave the Exos ID blank. MC assigns one on the next upload.
- If you copy a row, clear the Exos ID in the copy.
- The Exos ID column is locked, so it can't be deleted or moved. Per Jon, removing or changing it needs his decision, and MC will reject an upload without it.

cc: Victor Castilleja (FYI, per Jon).
Owner-approved by John Quinn, 2026-09-30."""


def sb(method, path, body=None, prefer=None):
    h = dict(H)
    if prefer:
        h["Prefer"] = prefer
    r = urllib.request.Request(SB + "/" + path, method=method, headers=h,
                               data=json.dumps(body).encode() if body is not None else None)
    raw = urllib.request.urlopen(r, timeout=30).read().decode()
    return json.loads(raw) if raw.strip() else None


def main():
    apply = "--apply" in sys.argv
    row = {"title": TITLE, "state": "To Do", "owner": STEVE, "category": "General", "priority": 75,
           "source": SOURCE, "due_date": "2026-10-02T22:00:00+00:00",
           "tags": ["shop-inventory", "exos-id", "cc:vcastilleja@exosaero.com", "owner-approved-jquinn"],
           "description": DESC}
    if not apply:
        print(json.dumps(row, indent=1, ensure_ascii=False)); print("(dry-run; --apply to create)"); return
    have = sb("GET", f"tasks?source=eq.{SOURCE}&select=id,assigned_email") or []
    if have:
        tid = have[0]["id"]; print("exists:", tid)
    else:
        tid = sb("POST", "tasks", row, prefer="return=representation")[0]["id"]
        print("created (unassigned):", tid)
    try:
        sup = json.load(open(SUP)); sup = sup if isinstance(sup, dict) else {}
    except Exception:
        sup = {}
    sup[str(tid)] = STEVE_EMAIL
    json.dump(sup, open(SUP, "w"))
    sb("PATCH", f"tasks?id=eq.{tid}", {"assigned_to": STEVE, "assigned_email": STEVE_EMAIL})
    meta = json.load(open(META))
    hit = [m for m in meta if m.get("stored_name") == STORED]
    for m in hit:
        m["task_id"] = str(tid)
    with open(META + ".tmp", "w") as f:
        f.write(json.dumps(meta, indent=2))
    os.replace(META + ".tmp", META)
    print(json.dumps({"task_id": tid, "assigned_email": STEVE_EMAIL, "attached": len(hit)}))


if __name__ == "__main__":
    main()
