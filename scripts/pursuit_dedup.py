#!/usr/bin/env python3
"""
pursuit_dedup.py — keep ONE open task per noisy recurring pursuit.

Problem: some pursuits (e.g. NIH Microgravity STTR) get a NEW "nudge / status /
decision" task spawned every day by the capture agent + email intake, so the same
unresolved item piles up as 15+ near-duplicate tasks the board can't manage.
dupe_collapse.py only catches EXACT same-title dupes; these are semantically the
same but lexically varied, so exact-title dedup misses them.

Fix: an EXPLICIT, SAFE config. For each configured pursuit, among the owner's OPEN
tasks that match its keyword rules (all_of + any_of) and do NOT match its guard
list (not_any — the genuinely-distinct action tasks), keep ONE canonical task
(In Progress > highest priority > most recently updated) and cancel the rest.

Explicit config = no fuzzy false-merge: distinct action tasks are protected by
not_any, and only listed pursuits are ever touched. Add a pursuit here when a new
one starts spamming. Cancelled tasks are hidden by the board (dedup-by-cancel).

Usage: pursuit_dedup.py            # dry-run: print what it WOULD cancel
       pursuit_dedup.py --apply    # cancel the duplicates (snapshotted first)
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
WS = "/Users/exomac/.openclaw/workspace"
APPLY = "--apply" in sys.argv
OPEN_STATES_EXCLUDED = {"Done", "Completed", "Closed", "Archived", "Cancelled"}
RANK = {"In Progress": 4, "Queued": 3, "To Do": 2, "Blocked": 1}

# --- Config: one entry per noisy recurring pursuit. Keep it explicit + guarded. ---
PURSUITS = [
    {
        "key": "nih-mg-sttr-pi-lock",
        "label": "NIH Microgravity STTR — PI-lock / forward-Kelly decision",
        "owner": "jon",
        "all_of": ["nih"],
        # nudge/status/decision restatements of the same recurring item:
        "any_of": ["pi outreach", "pi lock", "forward kelly", "nudge", "seed inquiry",
                   "shortlist", "binary decision", "final window", "sttr deadline",
                   "days to", "days:", "still pending", "go-ahead", "roses-2026",
                   "62 days", "gate passed", "aug 4 gate", "concept + capture"],
        # genuinely-distinct action tasks that must NEVER be collapsed —
        # specific deliverables and per-PI sends, not generic pursuit nudges:
        "not_any": ["call prep", "register", "registration", "compliance",
                    "research security", "who is", "co-pi", "weldon", "estelle",
                    "tagle", "nasa rfi", "purdue path",
                    "reply-chase", "reply chase", "bd outreach", "specific aims",
                    "pre-submission", "presubmission", "warm-intro", "warm intro",
                    "han", "vunjak", "sethu", "mei he", "stanford", "columbia",
                    "tamu", "collicott"],
    },
]


def ownn(o):
    o = (o or "").strip().lower()
    return {"john quinn": "jon", "jon+exo": "jon", "jquinn": "jon"}.get(o, o)


def qall():
    out, off = [], 0
    while True:
        req = urllib.request.Request(
            f"{SB}/tasks?select=id,title,state,owner,priority,updated_at,created_at&order=id&offset={off}&limit=1000",
            headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
        r = json.load(urllib.request.urlopen(req, timeout=60)); out += r
        if len(r) < 1000:
            return out
        off += 1000


def patch(tid, fields):
    req = urllib.request.Request(
        f"{SB}/tasks?id=eq.{tid}", data=json.dumps(fields).encode(),
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()


def matches(task, p):
    t = (task.get("title") or "").lower()
    if ownn(task.get("owner")) != p["owner"]:
        return False
    if not all(k in t for k in p["all_of"]):
        return False
    if p.get("any_of") and not any(k in t for k in p["any_of"]):
        return False
    if p.get("not_any") and any(k in t for k in p["not_any"]):
        return False
    return True


def canon_rank(task):
    # higher = keep. In Progress, then priority, then most recently updated.
    return (RANK.get(task.get("state"), 0), task.get("priority") or 0,
            task.get("updated_at") or task.get("created_at") or "")


def main():
    tasks = [t for t in qall() if (t.get("state") or "") not in OPEN_STATES_EXCLUDED]
    stamp = datetime.now(timezone.utc).isoformat()
    total_cancel = 0
    snapshot = []
    for p in PURSUITS:
        group = [t for t in tasks if matches(t, p)]
        if len(group) <= 1:
            print(f"[{p['key']}] {len(group)} open task(s) — nothing to collapse.")
            continue
        group.sort(key=canon_rank, reverse=True)
        keep, cancel = group[0], group[1:]
        print(f"[{p['key']}] {len(group)} open → keep #{keep['id']} "
              f"({keep.get('state')}, p{keep.get('priority')}): {str(keep.get('title'))[:55]}")
        for t in cancel:
            print(f"    cancel #{t['id']} ({t.get('state')}): {str(t.get('title'))[:60]}")
            snapshot.append({"id": t["id"], "prev_state": t.get("state"),
                             "title": t.get("title"), "pursuit": p["key"], "kept": keep["id"]})
            if APPLY:
                patch(t["id"], {"state": "Cancelled"})
            total_cancel += 1
    if APPLY and snapshot:
        os.makedirs(f"{WS}/logs", exist_ok=True)
        fn = f"{WS}/logs/pursuit-dedup-{stamp[:10]}.json"
        # append-safe: one file per day
        prev = json.load(open(fn)) if os.path.exists(fn) else []
        json.dump(prev + snapshot, open(fn, "w"), indent=1)
        print(f"APPLIED: cancelled {total_cancel}; snapshot → {fn}")
    else:
        print(f"{'DRY-RUN' if not APPLY else 'DONE'}: {total_cancel} task(s) "
              f"{'would be' if not APPLY else ''} cancelled.")


if __name__ == "__main__":
    main()
