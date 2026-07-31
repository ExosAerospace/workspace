#!/usr/bin/env python3
"""Collapse GENUINE duplicate tasks: same normalized title AND same owner.
Preserves legitimate one-per-person broadcasts (same title, different owners).
Keeps the most-advanced copy; closes the rest as Done with a merge note. Snapshotted."""
import json, urllib.request, re, os
from collections import defaultdict
from datetime import datetime, timezone

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
WS = "/Users/exomac/.openclaw/workspace"
DONE = {"Done", "Completed", "Closed", "Archived", "Cancelled"}
RANK = {"In Progress": 4, "Queued": 3, "To Do": 2, "Blocked": 1}
APPLY = "--apply" in os.sys.argv

def qall():
    out, off = [], 0
    while True:
        req = urllib.request.Request(
            f"{SB}/tasks?select=id,title,state,owner,description,created_at&order=id&offset={off}&limit=1000",
            headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
        r = json.load(urllib.request.urlopen(req, timeout=60)); out += r
        if len(r) < 1000: return out
        off += 1000

def patch(tid, f):
    req = urllib.request.Request(f"{SB}/tasks?id=eq.{tid}", data=json.dumps(f).encode(),
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()

def ownn(o):
    o = (o or "").strip().lower()
    return {"john quinn": "jon", "jon+exo": "jon", "jquinn": "jon"}.get(o, o)

def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()

tasks = [x for x in qall() if (x.get("state") or "") not in DONE]
g = defaultdict(list)
for x in tasks:
    g[(norm(x["title"]), ownn(x.get("owner")))].append(x)

plan = []
for key, v in g.items():
    if len(v) < 2:
        continue
    v.sort(key=lambda x: (-RANK.get(x.get("state"), 0), -len(x.get("description") or ""), x["id"]))
    keep = v[0]
    for l in v[1:]:
        plan.append((l, keep))

print(f"genuine same-owner duplicate tasks: {len(plan)}")
for l, k in plan:
    print(f"  close #{l['id']} [{l['state']}] {l['title'][:46]!r} (own {l.get('owner')}) -> keep #{k['id']} [{k['state']}]")

if not APPLY:
    print("\nDRY RUN — add --apply to close them.")
else:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snap = [{"id": l["id"], "prev_state": l["state"], "survivor": k["id"]} for l, k in plan]
    p = os.path.join(WS, "mission-control/data", f"dupe-collapse-snapshot-{stamp}.json")
    json.dump(snap, open(p, "w"), indent=2)
    for l, k in plan:
        note = (l.get("description") or "") + f"\n\n[DEDUP 2026-07-29] Duplicate of #{k['id']} (same owner + title). Closed; canonical = #{k['id']}."
        patch(l["id"], {"state": "Done", "description": note.strip()})
    print(f"snapshot {p}\nclosed {len(plan)} duplicates")
