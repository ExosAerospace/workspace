#!/usr/bin/env python3
"""inventory_capture_dispatch.py — launchd (com.exos.inventory-capture, ~every 3 min).

Isolated cron agentTurns can't read local files, so the vision step (look at the photo, name the
part) must run in a normal full-tool Exo session. This deterministic script just: (1) checks the
inventory-capture queue for pending photos, and (2) if there are any and we haven't just poked the
processor, wakes a dedicated full-tool session (`openclaw agent`) with the runbook to drain them.

Idempotent + quiet: a cooldown prevents re-waking for the same backlog every 3 min.
"""
import json, os, subprocess, time
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
QUEUE = os.path.join(WS, "logs", "inventory-capture-queue.jsonl")
STATE = os.path.join(WS, "logs", "inventory-capture-dispatch-state.json")
LOG = os.path.join(WS, "logs", "inventory-capture.log")
RUNBOOK = os.path.join(WS, "drafts", "INVENTORY_CAPTURE_RUNBOOK.md")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
SESSION = "agent:inventory-capture"     # dedicated session; keeps it out of #exomac-system
COOLDOWN_S = 240                        # don't re-poke the processor more than once / 4 min


def logline(m):
    try:
        with open(LOG, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} dispatch {m}\n")
    except Exception:
        pass


def pending_ids():
    ids = []
    if not os.path.exists(QUEUE):
        return ids
    for ln in open(QUEUE):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
            if e.get("status") == "pending":
                ids.append(e.get("id"))
        except Exception:
            pass
    return ids


def main():
    ids = pending_ids()
    if not ids:
        return
    st = {}
    try:
        st = json.load(open(STATE))
    except Exception:
        pass
    last = st.get("last_wake", 0)
    # Only skip if we recently woke AND the pending set hasn't grown since.
    if (time.time() - last) < COOLDOWN_S and set(ids) <= set(st.get("last_ids", [])):
        return
    prompt = (f"[Inventory Capture] {len(ids)} photo(s) are queued for BOM/inventory matching. "
              f"Follow the runbook exactly: read `{RUNBOOK}` and drain the queue to EMPTY "
              f"using `python3 scripts/inventory_capture.py next/bom-search/record/ask`. "
              f"Read each image, match it to the BLK3 BOM, record it, and ask the uploader on the "
              f"task if you can't identify a part. Do not guess part numbers. "
              f"DO NOT create any task/decision/subtask for a photo — a photo only updates inventory "
              f"and the existing task (record/ask only).")
    try:
        subprocess.run([OPENCLAW, "agent", "--session-key", SESSION, "-m", prompt,
                        "--json", "--timeout", "600"],
                       capture_output=True, text=True, timeout=660, cwd=WS)
        logline(f"woke processor for {len(ids)} pending")
    except Exception as e:
        logline(f"WARN wake: {e}")
    json.dump({"last_wake": time.time(), "last_ids": ids}, open(STATE, "w"))


if __name__ == "__main__":
    main()
