#!/usr/bin/env python3
"""inventory_capture.py — turn a photo taken on a Mission Control task into a BOM-matched
inventory record. Deterministic engine + queue. The VISION step (look at the photo, name the
component) runs in the MAIN Exo session (isolated crons can't read local files); this script
gives that session everything it needs and does the writing.

Flow:
  1. A photo is uploaded to a task (MC 'Take Photo' button) OR someone posts '@exo inv' on a task.
     -> an entry is enqueued here (kind=upload / kind=command).
  2. A launchd dispatcher (com.exos.inventory-capture) sees pending entries and wakes the main
     Exo session with the INVENTORY_CAPTURE_RUNBOOK.
  3. The main session: `next` -> Read the image -> `bom-search` -> `record` (or `ask` the uploader).

Subcommands:
  reindex-bom                          rebuild mission-control/data/bom-index.json from the BLK3 BOM xlsx
  enqueue --task ID --upload UPLID --file STORED --filename NAME --by WHO --kind upload|command
  pending                              print count of pending entries
  next                                 pop-context (does NOT delete): next pending entry as JSON + abs image path
  bom-search "keywords"                search the BOM index; JSON matches (item/pn/desc/section)
  record --queue QID --task ID --by WHO [--bom-key K] [--vendor-pn P] [--mfg-pn P]
         [--item I] [--section S] [--desc D] [--qty N] [--location L] [--note ...]
                                       upsert inventory record, mark entry done, post a ✅ note to the task
  ask --queue QID --task ID --uploader WHO --question "..."
                                       post a ❓ note to the task tagging the uploader; mark entry awaiting-reply
  status                               summary of queue + inventory
"""
import json, os, sys, re, argparse, urllib.request
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
MC = os.path.join(WS, "mission-control")
UPLOADS = os.path.join(MC, "uploads")
BOM_XLSX = os.path.join(UPLOADS, "1787343333564_BLK3_BOM_8-21-2026.xlsx")
BOM_INDEX = os.path.join(MC, "data", "bom-index.json")
INVENTORY = os.path.join(MC, "data", "inventory.json")
QUEUE = os.path.join(WS, "logs", "inventory-capture-queue.jsonl")
LOG = os.path.join(WS, "logs", "inventory-capture.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"
IMG_EXT = (".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif")


def now():
    return datetime.now(timezone.utc).isoformat()


def logline(m):
    try:
        with open(LOG, "a") as f:
            f.write(f"{now()} {m}\n")
    except Exception:
        pass


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def supa(method, path, body=None):
    req = urllib.request.Request(
        SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode()
            return json.loads(t) if t else []
    except Exception as e:
        logline(f"WARN supa {method} {path[:40]}: {e}")
        return None


def task_note(taskid, msg):
    supa("POST", "activities", {"type": "task_note", "subject": f"task:{taskid}",
         "body": msg, "owner": "Exo", "status": "completed"})


def flag_awaiting(taskid):
    try:
        cur = supa("GET", f"tasks?id=eq.{taskid}&select=tags,priority") or []
        tags = (cur[0].get("tags") or []) if cur else []
        if "awaiting-exo-answer" not in tags:
            tags = tags + ["awaiting-exo-answer"]
        pr = max(int(cur[0].get("priority") or 0), 88) if cur else 88
        supa("PATCH", f"tasks?id=eq.{taskid}", {"tags": tags, "priority": pr})
    except Exception as e:
        logline(f"WARN flag_awaiting {taskid}: {e}")


# ── QUEUE (append-only jsonl; each line an entry with a mutable 'status') ──
def read_queue():
    out = []
    if not os.path.exists(QUEUE):
        return out
    for ln in open(QUEUE):
        ln = ln.strip()
        if not ln:
            continue
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


def set_status(qid, status, extra=None):
    entries = read_queue()
    for e in entries:
        if e.get("id") == qid:
            e["status"] = status
            e["updated_at"] = now()
            if extra:
                e.update(extra)
    write_queue(entries)


def cmd_enqueue(a):
    if not a.file or not a.file.lower().endswith(IMG_EXT):
        # non-image uploads are ignored (only photos become inventory captures)
        print("skip non-image")
        return
    entries = read_queue()
    # de-dupe by upload id
    if a.upload and any(e.get("upload_id") == a.upload for e in entries):
        print("dup")
        return
    qid = "iq_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    entry = {"id": qid, "task_id": str(a.task), "upload_id": a.upload,
             "stored_name": a.file, "filename": a.filename or a.file,
             "uploaded_by": a.by or "Unknown", "kind": a.kind or "upload",
             "status": "pending", "created_at": now()}
    with open(QUEUE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    logline(f"enqueue {qid} task {a.task} by {a.by} ({a.kind})")
    print(qid)


def cmd_pending(a):
    print(sum(1 for e in read_queue() if e.get("status") == "pending"))


def cmd_next(a):
    for e in read_queue():
        if e.get("status") == "pending":
            img = os.path.join(UPLOADS, e.get("stored_name", ""))
            e = dict(e)
            e["image_path"] = img
            e["image_exists"] = os.path.exists(img)
            e["bom_index"] = BOM_INDEX
            e["inventory"] = INVENTORY
            print(json.dumps(e, indent=2))
            return
    print("EMPTY")


# ── BOM INDEX ──
def cmd_reindex(a):
    import openpyxl
    wb = openpyxl.load_workbook(BOM_XLSX, data_only=True)
    rows = []
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        # header assumed at row index 1 (0-based) per BLK3 BOM layout
        for r in ws.iter_rows(min_row=3, values_only=True):
            if not r:
                continue
            def g(i):
                return (str(r[i]).strip() if i < len(r) and r[i] is not None else "")
            item, qty, vpn, mpn, desc, vendor = g(0), g(1), g(2), g(3), g(4), g(5)
            cost = g(8)
            if not (vpn or mpn or desc):
                continue
            rows.append({"section": sheet, "item": item, "qty": qty, "vendor_pn": vpn,
                         "mfg_pn": mpn, "description": desc, "vendor": vendor, "cost": cost})
    data = {"source": os.path.basename(BOM_XLSX), "generated_at": now(), "count": len(rows), "rows": rows}
    os.makedirs(os.path.dirname(BOM_INDEX), exist_ok=True)
    json.dump(data, open(BOM_INDEX, "w"), indent=2)
    print(f"indexed {len(rows)} BOM lines across {len(wb.sheetnames)} sheets -> {BOM_INDEX}")


def cmd_bom_search(a):
    idx = load(BOM_INDEX, {"rows": []})
    q = " ".join(a.query).lower().strip()
    toks = [t for t in re.split(r"[\s,/]+", q) if t]
    scored = []
    for row in idx.get("rows", []):
        hay = " ".join([row.get("vendor_pn", ""), row.get("mfg_pn", ""),
                        row.get("description", ""), row.get("vendor", ""),
                        row.get("section", ""), row.get("item", "")]).lower()
        sc = 0
        for t in toks:
            if t in hay:
                sc += 2
                # exact P/N hit is a strong signal
                if t == row.get("vendor_pn", "").lower() or t == row.get("mfg_pn", "").lower():
                    sc += 6
        if sc:
            scored.append((sc, row))
    scored.sort(key=lambda x: -x[0])
    print(json.dumps([{"score": s, **r} for s, r in scored[:12]], indent=2))


# ── INVENTORY ──
def inv_load():
    return load(INVENTORY, {"records": [], "updated_at": None})


def inv_save(inv):
    inv["updated_at"] = now()
    os.makedirs(os.path.dirname(INVENTORY), exist_ok=True)
    tmp = INVENTORY + ".tmp"
    json.dump(inv, open(tmp, "w"), indent=2)
    os.replace(tmp, INVENTORY)


def rec_key(vendor_pn, mfg_pn, item, desc):
    return (vendor_pn or mfg_pn or (item + ":" + desc[:24]) or desc[:24]).strip().upper()


REPORT_NAME = "BLK3_Inventory_Report.xlsx"
REPORT_PATH = os.path.join(UPLOADS, REPORT_NAME)
UPLOADS_META = os.path.join(UPLOADS, "_meta.json")
REPORT_TASK = "3024"          # the Computer-section build/review task the report is pinned to


def build_report():
    """Regenerate the CANONICAL inventory spreadsheet from the BOM (all sections) joined to the live
    inventory ledger, and pin it as a document on the build task so it's always openable in MC.
    Called after every record/ask so the spreadsheet updates on every upload."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
    except Exception as e:
        logline(f"WARN report openpyxl: {e}"); return
    bom = load(BOM_INDEX, {"rows": []})
    inv = inv_load()
    by = {}
    for r in inv.get("records", []):
        for k in [r.get("vendor_pn"), r.get("mfg_pn"), r.get("key")]:
            if k:
                by[str(k).strip().upper()] = r
        if r.get("section") and r.get("item"):
            by[f"{r['section'].upper()}#{r['item']}"] = r
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Inventory"
    cols = ["Section", "Item", "Vendor P/N", "Mfg P/N", "Description", "Req Qty",
            "On-Hand", "Short", "Location(s)", "Photos", "Last Updated"]
    ws.append(cols)
    hdr = Font(bold=True, color="FFFFFF"); fill = PatternFill("solid", fgColor="1C1C1C")
    for c in ws[1]:
        c.font = hdr; c.fill = fill; c.alignment = Alignment(vertical="center")
    short_fill = PatternFill("solid", fgColor="FFE0E0")
    have_fill = PatternFill("solid", fgColor="E2F5E2")
    rows_total = short_total = onhand_total = 0
    for row in bom.get("rows", []):
        sec, item = row.get("section", ""), row.get("item", "")
        vpn, mpn, desc, qty = row.get("vendor_pn", ""), row.get("mfg_pn", ""), row.get("description", ""), row.get("qty", "")
        rec = None
        for k in [vpn, mpn]:
            if k and str(k).strip().upper() in by:
                rec = by[str(k).strip().upper()]; break
        if rec is None and item:
            rec = by.get(f"{sec.upper()}#{item}")
        oh = rec.get("qty_on_hand", 0) if rec else 0
        try:
            req = float(str(qty).strip())
        except Exception:
            req = None
        shortv = round(req - oh, 3) if (req is not None and oh < req) else 0
        loc = ", ".join(rec.get("locations", [])) if rec else ""
        nph = len(rec.get("photos", [])) if rec else 0
        upd = (rec.get("updated_at", "") or "")[:19].replace("T", " ") if rec else ""
        ws.append([sec, item, vpn, mpn, desc, qty, oh, shortv or "", loc, nph or "", upd])
        rows_total += 1
        onhand_total += oh
        if shortv:
            short_total += 1
            for c in ws[ws.max_row]:
                c.fill = short_fill
        elif oh:
            for c in ws[ws.max_row]:
                c.fill = have_fill
    widths = [16, 6, 18, 18, 40, 8, 8, 8, 20, 8, 20]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:K{ws.max_row}"
    # summary sheet
    s = wb.create_sheet("Summary")
    s.append(["BLK3 Inventory — canonical report"]); s["A1"].font = Font(bold=True, size=14)
    s.append(["Generated", now()[:19].replace("T", " ")])
    s.append(["BOM lines", rows_total])
    s.append(["Records with on-hand", sum(1 for r in inv.get("records", []) if r.get("qty_on_hand", 0) > 0)])
    s.append(["Lines short", short_total])
    s.append(["Total units on-hand", round(onhand_total, 3)])
    s.append(["Inventory records", len(inv.get("records", []))])
    s.column_dimensions["A"].width = 24; s.column_dimensions["B"].width = 28
    wb.save(REPORT_PATH)
    _pin_report(rows_total, short_total)
    logline(f"report refreshed: {rows_total} lines, {short_total} short -> {REPORT_PATH}")


def _pin_report(rows_total, short_total):
    """Upsert the report as a stable document on the build task so it shows (and updates in place)
    on that task's Documents tab in Mission Control."""
    try:
        meta = json.load(open(UPLOADS_META)) if os.path.exists(UPLOADS_META) else []
    except Exception:
        meta = []
    size = os.path.getsize(REPORT_PATH) if os.path.exists(REPORT_PATH) else 0
    entry = next((m for m in meta if m.get("id") == "blk3-inv-report"), None)
    if entry is None:
        entry = {"id": "blk3-inv-report", "filename": REPORT_NAME, "stored_name": REPORT_NAME,
                 "extension": ".xlsx", "task_id": REPORT_TASK, "project_id": None, "decision_id": None,
                 "uploaded_by": "Exo (inventory)", "current": True}
        meta.append(entry)
    entry["size"] = size
    entry["uploaded_at"] = now()
    entry["task_id"] = REPORT_TASK
    tmp = UPLOADS_META + ".tmp"
    json.dump(meta, open(tmp, "w"))
    os.replace(tmp, UPLOADS_META)


def cmd_record(a):
    inv = inv_load()
    key = a.bom_key or rec_key(a.vendor_pn or "", a.mfg_pn or "", a.item or "", a.desc or "")
    if not key:
        print("ERROR: need a key (--bom-key or --vendor-pn/--mfg-pn/--desc)")
        sys.exit(2)
    rec = next((r for r in inv["records"] if r.get("key") == key), None)
    existed = rec is not None
    # Safe count semantics (Jon 2026-09-22): an explicit --qty always wins (stock receipt).
    # Otherwise a photo of a NEW part records the first unit (+1); a photo of an ALREADY-recorded
    # part just CONFIRMS it and attaches the photo (+0) — re-photographing never double-counts.
    if a.qty not in (None, ""):
        qty = float(a.qty)
    else:
        qty = 0 if existed else 1
    entry_photo = None
    e = next((x for x in read_queue() if x.get("id") == a.queue), None) if a.queue else None
    if e:
        entry_photo = {"task": e.get("task_id"), "upload": e.get("upload_id"),
                       "file": e.get("stored_name"), "by": e.get("uploaded_by"), "at": now()}
    if rec is None:
        rec = {"key": key, "vendor_pn": a.vendor_pn or "", "mfg_pn": a.mfg_pn or "",
               "item": a.item or "", "section": a.section or "", "description": a.desc or "",
               "qty_on_hand": 0, "unit": "ea", "locations": [], "photos": [], "history": []}
        inv["records"].append(rec)
    rec["qty_on_hand"] = round(rec.get("qty_on_hand", 0) + qty, 3)
    if a.location and a.location not in rec["locations"]:
        rec["locations"].append(a.location)
    if a.section and not rec.get("section"):
        rec["section"] = a.section
    if a.desc and not rec.get("description"):
        rec["description"] = a.desc
    if a.vendor_pn and not rec.get("vendor_pn"):
        rec["vendor_pn"] = a.vendor_pn
    if a.mfg_pn and not rec.get("mfg_pn"):
        rec["mfg_pn"] = a.mfg_pn
    if entry_photo:
        rec["photos"].append(entry_photo)
    rec["history"].append({"at": now(), "by": a.by or "Exo", "delta": qty,
                           "note": a.note or "photo-captured", "queue": a.queue})
    rec["updated_at"] = now()
    inv_save(inv)
    if a.queue:
        set_status(a.queue, "recorded", {"inventory_key": key})
    if a.task:
        loc = f" · loc: {a.location}" if a.location else ""
        pn = a.vendor_pn or a.mfg_pn or ""
        pn = f" · P/N {pn}" if pn else ""
        verb = "recorded"
        tail = f"→ on-hand now **{rec['qty_on_hand']} {rec['unit']}**"
        if existed and qty == 0:
            verb = "confirmed (photo added, count unchanged)"
            tail = f"→ on-hand stays **{rec['qty_on_hand']} {rec['unit']}**"
        elif qty:
            tail = f"→ +{qty:g}, on-hand now **{rec['qty_on_hand']} {rec['unit']}**"
        task_note(a.task, f"✅ Exo (inventory): {verb} **{rec.get('description') or key}**"
                          f"{pn} {tail}{loc}. "
                          f"(from photo by {a.by or 'team'}; BOM section {rec.get('section') or '—'})")
    build_report()
    logline(f"record key={key} +{qty} -> {rec['qty_on_hand']} task {a.task}")
    print(json.dumps({"key": key, "qty_on_hand": rec["qty_on_hand"]}, indent=2))


def cmd_ask(a):
    q = a.question.strip()
    if a.queue:
        set_status(a.queue, "awaiting-reply", {"question": q})
    if a.task:
        flag_awaiting(a.task)
        task_note(a.task, f"❓ Exo (inventory): @{a.uploader or 'uploader'} — I need one detail to log the part "
                          f"you photographed: {q} Reply here on this task and I'll record it.")
    build_report()
    logline(f"ask task {a.task} uploader {a.uploader}: {q[:80]}")
    print("asked")


def cmd_report(a):
    build_report()
    print(f"report -> {REPORT_PATH}")


def cmd_consume(a):
    """Record a CONSUMPTION: parts used/installed leave stock. Decrements on-hand (or sets an
    explicit --remaining), logs the transaction, refreshes the report, posts a note."""
    inv = inv_load()
    key = a.bom_key or rec_key(a.vendor_pn or "", a.mfg_pn or "", a.item or "", a.desc or "")
    if not key:
        print("ERROR: need a key (--bom-key or --vendor-pn/--mfg-pn/--desc)"); sys.exit(2)
    rec = next((r for r in inv["records"] if r.get("key") == key), None)
    if rec is None:
        rec = {"key": key, "vendor_pn": a.vendor_pn or "", "mfg_pn": a.mfg_pn or "",
               "item": a.item or "", "section": a.section or "", "description": a.desc or "",
               "qty_on_hand": 0, "unit": "ea", "locations": [], "photos": [], "history": []}
        inv["records"].append(rec)
    qty = float(a.qty or 0)
    if a.remaining not in (None, ""):
        rec["qty_on_hand"] = round(float(a.remaining), 3)
    else:
        rec["qty_on_hand"] = round(rec.get("qty_on_hand", 0) - qty, 3)
    if a.location and a.location not in rec["locations"]:
        rec["locations"].append(a.location)
    for fld, val in [("section", a.section), ("description", a.desc), ("vendor_pn", a.vendor_pn), ("mfg_pn", a.mfg_pn)]:
        if val and not rec.get(fld):
            rec[fld] = val
    rec["history"].append({"at": now(), "by": a.by or "Exo", "delta": -qty,
                           "note": a.note or "consumed", "location": a.location or "", "queue": None})
    rec["updated_at"] = now()
    inv_save(inv)
    # short vs BOM for the note
    bom = load(BOM_INDEX, {"rows": []})
    req = None
    for row in bom.get("rows", []):
        if row.get("section", "").lower() == (rec.get("section") or "").lower() and str(row.get("item")) == str(rec.get("item")):
            try:
                req = float(str(row.get("qty")).strip())
            except Exception:
                req = None
            break
    shortnote = ""
    if req is not None and rec["qty_on_hand"] < req:
        shortnote = f" · SHORT {round(req - rec['qty_on_hand'], 3)} vs BOM (req {req:g}) → reorder"
    build_report()
    if a.task:
        loc = f" at {a.location}" if a.location else ""
        task_note(a.task, f"🔻 Exo (inventory): consumed **{qty:g} × {rec.get('description') or key}**{loc} "
                          f"→ on-hand now **{rec['qty_on_hand']:g} {rec['unit']}**{shortnote}. (per {a.by or 'team'})")
    logline(f"consume key={key} -{qty} -> {rec['qty_on_hand']} loc {a.location} task {a.task}")
    print(json.dumps({"key": key, "qty_on_hand": rec["qty_on_hand"], "short_vs_bom": (round(req - rec['qty_on_hand'], 3) if req is not None else None)}, indent=2))


def cmd_status(a):
    q = read_queue()
    inv = inv_load()
    byst = {}
    for e in q:
        byst[e.get("status", "?")] = byst.get(e.get("status", "?"), 0) + 1
    print(json.dumps({"queue": byst, "inventory_records": len(inv.get("records", [])),
                      "inventory_units": round(sum(r.get("qty_on_hand", 0) for r in inv.get("records", [])), 2)}, indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reindex-bom")
    e = sub.add_parser("enqueue")
    e.add_argument("--task"); e.add_argument("--upload"); e.add_argument("--file")
    e.add_argument("--filename"); e.add_argument("--by"); e.add_argument("--kind", default="upload")
    sub.add_parser("pending")
    sub.add_parser("next")
    b = sub.add_parser("bom-search"); b.add_argument("query", nargs="+")
    r = sub.add_parser("record")
    for f in ["queue", "task", "by", "bom-key", "vendor-pn", "mfg-pn", "item", "section", "desc", "qty", "location", "note"]:
        r.add_argument("--" + f)
    k = sub.add_parser("ask")
    k.add_argument("--queue"); k.add_argument("--task"); k.add_argument("--uploader"); k.add_argument("--question", required=True)
    cs = sub.add_parser("consume")
    for f in ["bom-key", "vendor-pn", "mfg-pn", "item", "section", "desc", "qty", "remaining", "location", "by", "note", "task"]:
        cs.add_argument("--" + f)
    sub.add_parser("status")
    sub.add_parser("report")
    a = p.parse_args()
    # normalize dashed dests
    for src, dst in [("bom_key", "bom_key"), ("vendor_pn", "vendor_pn"), ("mfg_pn", "mfg_pn")]:
        pass
    {"reindex-bom": cmd_reindex, "enqueue": cmd_enqueue, "pending": cmd_pending,
     "next": cmd_next, "bom-search": cmd_bom_search, "record": cmd_record,
     "ask": cmd_ask, "status": cmd_status, "report": cmd_report, "consume": cmd_consume}[a.cmd](a)


if __name__ == "__main__":
    main()
