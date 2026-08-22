#!/usr/bin/env python3
"""
payload_task_spawn.py — spawn a UTD-capstone TASK for each payload-sales outreach item
that decision_triage delegated to UTD (Jon's standing rule 2026-08-21:
payload sales -> UTD, BLK3 sales -> Lizi).

WHY: routing the DECISION off Jon's board is inert for the UTD students — they are
early_adopter users sandboxed to the tasks board, scoped to category == "Payload Sales"
(mission-control/server.js). So the real hand-off is a Supabase TASK in that category.
This turns each delegated payload approval into an actionable item in the students' queue.

SAFE-BY-DESIGN (no external email blast): tasks are created with
owner = "UTD EXO3 Payload Capstone" (a LABEL, not a login account) and assigned_email = null,
so assignment-notifier.py's resolve() returns no address and never emails. Students see the
work by category scope; Lizi remains the Exos-side gate on the decision.

Idempotent: task id = "PAYDLG-<decision-id>"; re-runs skip anything already spawned and
stamp `spawned_task` on the decision. Run:  python3 scripts/payload_task_spawn.py [--dry]
"""
import os, re, sys, json, urllib.request, urllib.parse

WS = os.path.expanduser("~/.openclaw/workspace")
DEC = os.path.join(WS, "mission-control", "data", "decisions.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
HDR = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
DRY = "--dry" in sys.argv
CATEGORY = "Payload Sales"
OWNER_LABEL = "UTD EXO3 Payload Capstone"   # NOT a user account -> notifier stays silent


def sb(method, path, body=None, prefer=None):
    h = dict(HDR)
    if prefer:
        h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(SB + "/" + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None


def clean_title(t):
    t = re.sub(r"^\s*(send:|approval\s*[—:-]+|approval\s*&\s*send:)\s*", "", t or "", flags=re.I).strip()
    return ("[Payload] " + t)[:180] if t else "[Payload] Outreach item"


def is_payload_delegated(d):
    return (str(d.get("delegation", "")).lower().startswith("payload sales")
            and not d.get("spawned_task"))


MARK = "source decision "   # stable marker embedded in description for dedupe


def already_spawned_ids():
    """Decision-ids that already have a payload-delegation task (guards even if the
    decisions.json flag was lost). tasks.id is an auto-increment bigint, so we key on
    the marker we embed in the task description rather than a custom id."""
    rows = sb("GET", "tasks?source=eq.payload-delegation&select=description&limit=2000") or []
    seen = set()
    for r in rows:
        m = re.search(re.escape(MARK) + r"([A-Za-z0-9_-]+)", r.get("description") or "")
        if m:
            seen.add(m.group(1))
    return seen


def main():
    raw = json.load(open(DEC))
    arr = raw if isinstance(raw, list) else raw.get("decisions", [])
    todo = [d for d in arr if is_payload_delegated(d)]
    print(f"payload items to spawn as UTD tasks: {len(todo)}")
    seen = already_spawned_ids()
    made = skipped = 0
    for d in todo:
        did = str(d.get("id") or "").strip()
        if not did:
            continue
        if did in seen:                      # task already exists in Supabase
            d["spawned_task"] = True
            skipped += 1
            continue
        desc = ((d.get("question") or "") + "\n\n" + (d.get("proposedAction") or "")).strip()
        task = {
            "title": clean_title(d.get("title")), "state": "To Do",
            "owner": OWNER_LABEL, "assigned_to": OWNER_LABEL, "assigned_email": None,
            "category": CATEGORY, "priority": 60, "source": "payload-delegation",
            "tags": ["payload", "utd", "auto-delegated"],
            "description": (desc[:600] + f"\n\n[Auto-delegated per Jon's standing rule · {MARK}{did} · Exos gate: Lizi]"),
        }
        if DRY:
            print("  DRY would create -", task["title"][:60]); made += 1; continue
        created = sb("POST", "tasks", task, prefer="return=representation")
        new_id = (created[0].get("id") if isinstance(created, list) and created else True)
        d["spawned_task"] = new_id
        seen.add(did)
        made += 1
        print("  +", new_id, "-", task["title"][:60])
    if not DRY:
        (open(DEC, "w")).write(json.dumps(raw, indent=2))
    print(f"\n{'DRY ' if DRY else ''}done: created {made}, already-existed {skipped}, total handled {made+skipped}")


if __name__ == "__main__":
    main()
