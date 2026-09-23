#!/usr/bin/env python3
"""receiving_capture.py — photo-to-receiving: read a packing-list/parts photo, draft the received
lines (part # + qty) matched to the BLK3 BOM, for a human to confirm on the Receiving page.

The vision step runs in a full-tool Exo session (isolated crons can't read local files), woken by
com.exos.receiving-capture; this script is the deterministic engine + draft store.

Subcommands:
  enqueue --po P --file STORED --by WHO      queue a captured photo for reading
  pending                                    count pending
  next                                       next pending entry as JSON (+ abs image path, bom index)
  add-draft --po P [--vendor-pn/--mfg-pn/--item/--section/--desc/--qty]   append a drafted line
  clear-draft --po P                         reset a PO's draft (before a new capture)
  finish --id ID --po P                      mark the capture done + stamp the draft ready
"""
import json, os, sys, argparse
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
MC = os.path.join(WS, "mission-control")
UPLOADS = os.path.join(MC, "uploads")
BOM_INDEX = os.path.join(MC, "data", "bom-index.json")
QUEUE = os.path.join(WS, "logs", "receiving-capture-queue.jsonl")
DRAFTS = os.path.join(MC, "data", "receiving-drafts.json")
LOG = os.path.join(WS, "logs", "receiving-capture.log")


def now():
    return datetime.now(timezone.utc).isoformat()


def logline(m):
    try:
        open(LOG, "a").write(f"{now()} {m}\n")
    except Exception:
        pass


def read_queue():
    out = []
    if os.path.exists(QUEUE):
        for ln in open(QUEUE):
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
    return out


def write_queue(entries):
    tmp = QUEUE + ".tmp"
    with open(tmp, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    os.replace(tmp, QUEUE)


def load_drafts():
    try:
        return json.load(open(DRAFTS))
    except Exception:
        return {"drafts": {}}


def save_drafts(d):
    tmp = DRAFTS + ".tmp"
    json.dump(d, open(tmp, "w"), indent=2)
    os.replace(tmp, DRAFTS)


def cmd_enqueue(a):
    qid = "rc_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    with open(QUEUE, "a") as f:
        f.write(json.dumps({"id": qid, "po": a.po, "stored_name": a.file, "by": a.by or "team",
                            "status": "pending", "created_at": now()}) + "\n")
    logline(f"enqueue {qid} po {a.po} by {a.by}")
    print(qid)


def cmd_pending(a):
    print(sum(1 for e in read_queue() if e.get("status") == "pending"))


def cmd_next(a):
    for e in read_queue():
        if e.get("status") == "pending":
            e = dict(e)
            e["image_path"] = os.path.join(UPLOADS, e.get("stored_name", ""))
            e["image_exists"] = os.path.exists(e["image_path"])
            e["bom_index"] = BOM_INDEX
            print(json.dumps(e, indent=2))
            return
    print("EMPTY")


def cmd_clear_draft(a):
    d = load_drafts()
    d["drafts"][str(a.po)] = {"lines": [], "status": "reading", "updated_at": now()}
    save_drafts(d)
    print("cleared")


def cmd_add_draft(a):
    d = load_drafts()
    entry = d["drafts"].setdefault(str(a.po), {"lines": [], "status": "reading", "updated_at": now()})
    entry["lines"].append({"vendor_pn": a.vendor_pn or "", "mfg_pn": a.mfg_pn or "", "item": a.item or "",
                           "section": a.section or "", "desc": a.desc or "", "qty": a.qty or "1"})
    entry["updated_at"] = now()
    save_drafts(d)
    print(f"draft line added to PO {a.po} ({len(entry['lines'])} total)")


def cmd_finish(a):
    entries = read_queue()
    for e in entries:
        if e.get("id") == a.id:
            e["status"] = "done"
            e["finished_at"] = now()
    write_queue(entries)
    d = load_drafts()
    entry = d["drafts"].setdefault(str(a.po), {"lines": [], "status": "ready", "updated_at": now()})
    entry["status"] = "ready"
    entry["updated_at"] = now()
    save_drafts(d)
    logline(f"finish {a.id} po {a.po} -> {len(entry['lines'])} lines")
    print("finished")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enqueue"); e.add_argument("--po"); e.add_argument("--file"); e.add_argument("--by")
    sub.add_parser("pending")
    sub.add_parser("next")
    cd = sub.add_parser("clear-draft"); cd.add_argument("--po", required=True)
    ad = sub.add_parser("add-draft")
    for f in ["po", "vendor-pn", "mfg-pn", "item", "section", "desc", "qty"]:
        ad.add_argument("--" + f)
    fi = sub.add_parser("finish"); fi.add_argument("--id", required=True); fi.add_argument("--po", required=True)
    a = p.parse_args()
    {"enqueue": cmd_enqueue, "pending": cmd_pending, "next": cmd_next, "clear-draft": cmd_clear_draft,
     "add-draft": cmd_add_draft, "finish": cmd_finish}[a.cmd](a)


if __name__ == "__main__":
    main()
