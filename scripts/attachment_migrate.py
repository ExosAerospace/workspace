#!/usr/bin/env python3
"""Shared helper: migrate task attachments when a duplicate task is collapsed into a canonical one.

Root cause (diagnosed 2026-09-20): attachments in mission-control/uploads/_meta.json link to a
task by a raw `task_id` string that NO code ever repointed. When dedup closes/cancels a loser task
into a canonical survivor, the loser's docs strand on the now-closed duplicate and vanish from the
task the user keeps working. This repoints them onto the survivor and resolves doc_key version
collisions (newest = current). Idempotent; atomic write.
"""
import os, json
from collections import defaultdict

WS = os.path.expanduser("~/.openclaw/workspace")
META = os.path.join(WS, "mission-control", "uploads", "_meta.json")


def migrate_attachments(loser_id, winner_id, meta_path=META):
    """Repoint every _meta.json attachment from loser_id -> winner_id. Returns count moved."""
    lid, wid = str(loser_id), str(winner_id)
    if lid == wid or not lid or not wid:
        return 0
    try:
        meta = json.load(open(meta_path))
    except Exception:
        return 0
    moved = 0
    for m in meta:
        if str(m.get("task_id")) == lid:
            m["task_id"] = wid
            moved += 1
    if not moved:
        return 0
    # resolve doc_key collisions now sharing the winner: newest = current, versions renumbered
    groups = defaultdict(list)
    for m in meta:
        if str(m.get("task_id")) == wid and m.get("doc_key"):
            groups[m["doc_key"]].append(m)
    for items in groups.values():
        items.sort(key=lambda x: (x.get("version") or 0, x.get("uploaded_at") or ""))
        n = len(items)
        for i, m in enumerate(items, 1):
            m["version"] = i
            m["current"] = (i == n)
    tmp = meta_path + ".tmp"
    json.dump(meta, open(tmp, "w"), indent=1)
    os.replace(tmp, meta_path)
    return moved


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        print("migrated", migrate_attachments(sys.argv[1], sys.argv[2]), "attachment(s)")
    else:
        print("usage: attachment_migrate.py <loser_task_id> <winner_task_id>")
