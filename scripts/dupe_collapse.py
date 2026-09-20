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
            f"{SB}/tasks?select=id,title,state,owner,description,category,created_at&order=id&offset={off}&limit=1000",
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
    return {"john quinn": "jon", "jon+exo": "jon", "jquinn": "jon", "exo": "exo"}.get(o, o)

# D-7281739 fix #1: strip "aging counters" so a re-run or a date-stamped re-send of the SAME task
# (the Neil/TACFI blow-up: "GTL … (NEW June 17)" vs "(NEW June 20)", "…8 days overdue", "day 3",
# "round 2", "v3") collapses to one dedup key instead of spawning a near-duplicate every time.
# Only date/aging tokens are removed — real numerics (BLK3, PY26.2, $500K, Phase III, 137) survive.
_MONTHS = (r"january|february|march|april|may|june|july|august|september|october|november|december|"
           r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec")
def strip_aging(s):
    s = (s or "").lower()
    s = re.sub(r"\(\s*new[^)]*\)", " ", s)                                  # "(NEW June 17)"
    s = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", s)                            # 2026-06-17
    s = re.sub(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", " ", s)                 # 6/17, 6/17/26
    s = re.sub(rf"\b(?:{_MONTHS})\s+\d{{1,2}}(?:,?\s*\d{{4}})?\b", " ", s)  # "june 17", "june 17, 2026"
    s = re.sub(r"\b\d+\s*days?\s*overdue\b", " ", s)                        # "8 days overdue"
    s = re.sub(r"\b(?:day|round|attempt|try|rev|revision|version|v)\s*#?\d+\b", " ", s)  # "day 3","v3"
    s = re.sub(r"\b(?:new|newly|updated?|refresh(?:ed)?)\b", " ", s)        # bare aging adjectives
    s = re.sub(r"#\d+", " ", s)                                             # "#2"
    s = re.sub(r"\(\s*\d+\s*\)", " ", s)                                    # "(2)"
    return s

def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", strip_aging(s))).strip()

def catn(c):
    return re.sub(r"\s+", " ", (c or "general").strip().lower())

tasks = [x for x in qall() if (x.get("state") or "") not in DONE]
g = defaultdict(list)
for x in tasks:
    # key on category + aging-stripped normalized title + owner (was: exact-normalized title + owner)
    g[(catn(x.get("category")), norm(x["title"]), ownn(x.get("owner")))].append(x)

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
    import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from attachment_migrate import migrate_attachments
    moved_total = 0
    for l, k in plan:
        note = (l.get("description") or "") + f"\n\n[DEDUP 2026-07-29] Duplicate of #{k['id']} (same owner + title). Closed; canonical = #{k['id']}."
        patch(l["id"], {"state": "Done", "description": note.strip()})
        moved = migrate_attachments(l["id"], k["id"])  # repoint docs onto the survivor (no more dropped attachments)
        if moved:
            moved_total += moved
            print(f"    migrated {moved} attachment(s) #{l['id']} -> #{k['id']}")
    print(f"snapshot {p}\nclosed {len(plan)} duplicates; migrated {moved_total} attachment(s)")
