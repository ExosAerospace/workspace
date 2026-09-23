#!/usr/bin/env python3
"""receiving_capture_dispatch.py — launchd (com.exos.receiving-capture, ~90s).

When a packing-list photo is queued (Receiving page camera), wake a full-tool Exo session to read it
and draft the received lines (isolated crons can't read local files). Cooldown so it doesn't re-poke.
"""
import json, os, subprocess, time
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
QUEUE = os.path.join(WS, "logs", "receiving-capture-queue.jsonl")
STATE = os.path.join(WS, "logs", "receiving-capture-dispatch-state.json")
LOG = os.path.join(WS, "logs", "receiving-capture.log")
RUNBOOK = os.path.join(WS, "drafts", "RECEIVING_CAPTURE_RUNBOOK.md")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
SESSION = "agent:inventory-capture"
COOLDOWN_S = 150


def logline(m):
    try:
        open(LOG, "a").write(f"{datetime.now(timezone.utc).isoformat()} dispatch {m}\n")
    except Exception:
        pass


def pending_ids():
    ids = []
    if os.path.exists(QUEUE):
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
    if (time.time() - st.get("last_wake", 0)) < COOLDOWN_S and set(ids) <= set(st.get("last_ids", [])):
        return
    prompt = (f"[Receiving Capture] {len(ids)} packing-list photo(s) queued. Follow the runbook exactly: "
              f"read `{RUNBOOK}` and drain the queue using `python3 scripts/receiving_capture.py "
              f"next/clear-draft/add-draft/finish` + `inventory_capture.py bom-search`. Read each photo, "
              f"draft the received line items (part # + qty) matched to the BLK3 BOM. This is a DRAFT for "
              f"human confirmation — do NOT check anything into inventory.")
    try:
        r = subprocess.run([OPENCLAW, "agent", "--session-key", SESSION, "-m", prompt, "--json", "--timeout", "600"],
                           capture_output=True, text=True, timeout=660, cwd=WS)
        if r.returncode != 0:
            logline(f"ERROR wake rc={r.returncode}: {(r.stderr or r.stdout)[:200]}")
        else:
            logline(f"woke processor for {len(ids)} pending")
    except Exception as e:
        logline(f"WARN wake: {e}")
    json.dump({"last_wake": time.time(), "last_ids": ids}, open(STATE, "w"))


if __name__ == "__main__":
    main()
