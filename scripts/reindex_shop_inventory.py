#!/usr/bin/env python3
"""Ingest Steve's full shop workbook (Current_Inventory_Locations*.xlsx) as the INVENTORY OF RECORD.
Writes mission-control/data/shop-inventory.json = every physical line across Warehouse / Parts Room /
Trailer / Assets (rocket + NON-rocket), location forward-filled, qty/value/jurisdiction, plus is_rocket
flag (SKU matches a BLK3 BOM part). Additive; does not touch the BOM (bom-index.json) or photo ledger.

STABLE IDS (exo3, shop-stable-ids, Jon 2026-09-30): SHOP-xxxxx ids are PERMANENT, held in
data/shop-id-registry.json (never reused, never renumbered) so shop-edits.json and photos stay on the
right part across reloads. Precedence per line:
  (a) "Exos ID" column in the sheet with a known id      -> kept
  (b) registry fingerprint category+location+contents    -> matched (tiebreak skus, then occurrence)
  (c) same category+contents, unique on both sides       -> moved (id kept, new location)
  (d) otherwise                                          -> new id from next_id
Registry ids absent from a reload are marked retired (never deleted).

GUARD ("no deletion without Jon's decision"): once the registry has id_column_required=true, an upload
MISSING the Exos ID column on an item sheet, or with >2% of lines blank/duplicate/unknown id, or that
would retire >25% of active ids, is REJECTED: previous shop-inventory.json and the registry are left
untouched, the reason is logged, and a Decision is filed for Jon (never answered here). Jon's
"accept" path: rerun with --file <that file> --override-guard.

  reindex_shop_inventory.py                    # newest non-rejected upload
  reindex_shop_inventory.py --file X --uploader "Steve Norsworthy"
  reindex_shop_inventory.py --seed-registry    # one-time: registry from CURRENT shop-inventory.json
  --dry-run (write nothing)  --decision-dry-run (build decision payload, don't POST)
  --data-dir/--log-dir (selftest isolation)  --no-fleet-log
"""
import openpyxl, json, os, glob, re, sys, argparse, datetime, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control/data")
LOGS = os.path.join(WS, "logs")
ITEM_SHEETS = {"Warehouse", "Parts Room", "Trailer", "Assets", "Sales & Trash"}
HEADER_TOKENS = {"qty", "contents", "exos sku", "source", "source/sku", "asset", "description", "location", "value"}
ID_HEADER = "Exos ID"
ID_RE = re.compile(r"^SHOP-\d{5,}$")
BAD_ID_MAX = 0.02        # >2% blank/duplicate/unknown ids -> reject
RETIRE_MAX = 0.25        # would retire >25% of active ids -> reject
MC = "http://127.0.0.1:8080"


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def newest_locations_xlsx(rejected=()):
    c = [x for x in glob.glob(os.path.join(WS, "mission-control/uploads/*Current_Inventory_Locations*.xlsx"))
         if ".bak" not in x and os.path.basename(x) not in rejected]
    if not c:
        return None
    return max(c, key=os.path.getmtime)


def bom_sku_set():
    """All distinctive part-number-ish strings (>=5 chars) from the BLK3 BOM index, uppercased."""
    s = set()
    p = os.path.join(DATA, "bom-index.json")
    if not os.path.exists(p):
        return s
    try:
        data = json.load(open(p))
    except Exception:
        return s
    rows = data if isinstance(data, list) else data.get("lines", data.get("items", []))
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        for k, v in r.items():
            if isinstance(v, str) and len(v.strip()) >= 5 and re.search(r"[A-Za-z0-9]", v):
                s.add(v.strip().upper())
    return s


def norm_header(row):
    return [str(c).strip().lower() if c is not None else "" for c in row]


def norm(v):
    return re.sub(r"\s+", " ", str(v or "")).strip().lower()


def find_header_row(ws, scan=12):
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=scan, values_only=True), 1):
        cells = norm_header(row)
        hits = sum(1 for c in cells if c in HEADER_TOKENS)
        if hits >= 2:
            return i, cells
    # fallback: row 1
    for row in ws.iter_rows(min_row=1, max_row=1, values_only=True):
        return 1, norm_header(row)
    return 1, []


def col_idx(headers, *names):
    for n in names:
        if n in headers:
            return headers.index(n)
    return None


def cellval(row, idx):
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def tofloat(v):
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).replace(",", "").replace("$", "").strip())
    except Exception:
        return 0.0


def parse_workbook(src, bom=None):
    """-> (items without ids, per_cat counts, sheet info {title: {header_row, id_col (1-based|None)}}).
    Each item carries _sheet, _row (1-based excel row) and _sheet_id (raw Exos ID cell)."""
    bom = bom if bom is not None else bom_sku_set()
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    items, per_cat, sheets = [], {}, {}
    for ws in wb.worksheets:
        if ws.title not in ITEM_SHEETS:
            continue
        hrow, headers = find_header_row(ws)
        ci = {
            "location": col_idx(headers, "location", "generator", "resting place"),
            "source_sku": col_idx(headers, "source/sku", "source", "sku"),
            "contents": col_idx(headers, "contents", "asset"),
            "exos_sku": col_idx(headers, "exos sku"),
            "qty": col_idx(headers, "qty"),
            "unit": col_idx(headers, "unit"),
            "juris": col_idx(headers, "jurisdiction"),
            "value": col_idx(headers, "value"),
            "total": col_idx(headers, "total"),
            "desc": col_idx(headers, "description"),
            "url": col_idx(headers, "url"),
            "comments": col_idx(headers, "comments"),
            "keep": col_idx(headers, "keep"),
            "vendor": col_idx(headers, "vendor"),
            "exos_id": col_idx(headers, ID_HEADER.lower()),
        }
        sheets[ws.title] = {"header_row": hrow, "id_col": (ci["exos_id"] + 1) if ci["exos_id"] is not None else None}
        last_loc = ""
        count = 0
        for rno, row in enumerate(ws.iter_rows(min_row=hrow + 1, values_only=True), hrow + 1):
            loc = cellval(row, ci["location"])
            if loc not in (None, ""):
                last_loc = str(loc).strip()
            contents = cellval(row, ci["contents"])
            exos = cellval(row, ci["exos_sku"])
            src_sku = cellval(row, ci["source_sku"])
            desc = cellval(row, ci["desc"])
            qty = tofloat(cellval(row, ci["qty"]))
            # skip blank/spacer rows: need at least a contents/description/sku or a qty
            if not any([contents, exos, src_sku, desc]) and qty == 0:
                continue
            exos_s = str(exos).strip() if exos not in (None, "") else ""
            src_s = str(src_sku).strip() if src_sku not in (None, "") else ""
            is_rocket = ((len(exos_s) >= 5 and exos_s.upper() in bom) or
                         (len(src_s) >= 5 and src_s.upper() in bom))
            items.append({
                "id": None,
                "category": ws.title,
                "location": last_loc,
                "source_sku": src_s,
                "exos_sku": exos_s,
                "contents": str(contents).strip() if contents not in (None, "") else "",
                "description": str(desc).strip() if desc not in (None, "") else "",
                "qty": qty,
                "unit": str(cellval(row, ci["unit"]) or "").strip(),
                "jurisdiction": str(cellval(row, ci["juris"]) or "").strip(),
                "value": tofloat(cellval(row, ci["value"])),
                "total": tofloat(cellval(row, ci["total"])),
                "url": str(cellval(row, ci["url"]) or "").strip(),
                "comments": str(cellval(row, ci["comments"]) or "").strip(),
                "keep": str(cellval(row, ci["keep"]) or "").strip(),
                "vendor": str(cellval(row, ci["vendor"]) or "").strip(),
                "is_rocket": is_rocket,
                "sale_or_trash": ws.title == "Sales & Trash",
                "_sheet": ws.title,
                "_row": rno,
                "_sheet_id": str(cellval(row, ci["exos_id"]) or "").strip().upper(),
            })
            count += 1
        per_cat[ws.title] = count
    wb.close()
    return items, per_cat, sheets


# ── registry ────────────────────────────────────────────────────────────────────────────────────
def fkey(it):
    return (it["category"], norm(it["location"]), norm(it["contents"]))


def fingerprint(it, occ):
    return {"category": it["category"], "location": norm(it["location"]), "contents": norm(it["contents"]),
            "exos_sku": norm(it["exos_sku"]), "source_sku": norm(it["source_sku"]), "occ": occ}


def with_occ(items):
    seen, out = {}, []
    for it in items:
        k = fkey(it)
        out.append(seen.get(k, 0))
        seen[k] = seen.get(k, 0) + 1
    return out


def empty_registry():
    return {"version": 1, "created_at": now_iso(), "updated_at": now_iso(), "next_id": 1,
            "id_column_required": False, "id_column_name": ID_HEADER, "last_source_file": None,
            "last_summary": None, "ids": {}}


def load_registry(path):
    try:
        return json.load(open(path))
    except Exception:
        return None


def seed_registry(inv_path):
    """Registry from the CURRENT shop-inventory.json: every existing id keeps its number."""
    inv = json.load(open(inv_path))
    items = inv.get("items", [])
    reg = empty_registry()
    occs = with_occ(items)
    mx = 0
    for it, occ in zip(items, occs):
        if it["id"] in reg["ids"]:
            raise SystemExit(f"duplicate id in current inventory: {it['id']}")
        reg["ids"][it["id"]] = dict(fingerprint(it, occ), status="active", first_seen=reg["created_at"],
                                    last_seen=reg["created_at"], retired_at=None)
        mx = max(mx, int(it["id"].split("-")[1]))
    reg["next_id"] = mx + 1
    reg["last_source_file"] = inv.get("source_file")
    reg["seeded_from"] = {"file": os.path.basename(inv_path), "generated_at": inv.get("generated_at"),
                          "source_file": inv.get("source_file"), "count": len(items)}
    return reg


def assign_ids(items, reg):
    """Fill it['id'] + it['_how'] per the precedence rules. Returns (summary, claimed set). Pure (no writes)."""
    ids = reg["ids"]
    claimed = set()
    how = {}
    # (a) Exos ID column
    for i, it in enumerate(items):
        v = it.get("_sheet_id") or ""
        if ID_RE.match(v) and v in ids and v not in claimed:
            it["id"] = v; claimed.add(v); how[i] = "kept"
    # (b) fingerprint category+location+contents
    idx = {}
    for rid, e in ids.items():
        if rid in claimed:
            continue
        idx.setdefault((e["category"], e["location"], e["contents"]), []).append(rid)
    for k in idx:
        idx[k].sort(key=lambda r: (ids[r].get("status") != "active", ids[r].get("occ", 0), r))
    for i, it in enumerate(items):
        if it["id"]:
            continue
        cands = [r for r in idx.get(fkey(it), []) if r not in claimed]
        if not cands:
            continue
        sku = [r for r in cands if ids[r].get("exos_sku") == norm(it["exos_sku"])
               and ids[r].get("source_sku") == norm(it["source_sku"])]
        r = (sku or cands)[0]
        it["id"] = r; claimed.add(r); how[i] = "matched"
    # (c) moved: same category+contents, unique on both sides
    rows_by, regs_by = {}, {}
    for i, it in enumerate(items):
        if not it["id"] and norm(it["contents"]):
            rows_by.setdefault((it["category"], norm(it["contents"])), []).append(i)
    for rid, e in ids.items():
        if rid not in claimed and e["contents"]:
            regs_by.setdefault((e["category"], e["contents"]), []).append(rid)
    for k, rows in rows_by.items():
        c = regs_by.get(k, [])
        if len(rows) == 1 and len(c) == 1:
            items[rows[0]]["id"] = c[0]; claimed.add(c[0]); how[rows[0]] = "moved"
    # (d) new ids
    nxt = reg["next_id"]
    for i, it in enumerate(items):
        if not it["id"]:
            it["id"] = f"SHOP-{nxt:05d}"; nxt += 1; how[i] = "new"
    for i, it in enumerate(items):
        it["_how"] = how[i]
    retired = [r for r, e in ids.items() if e.get("status") == "active" and r not in claimed]
    reactivated = [r for r in claimed if ids[r].get("status") == "retired"]
    summary = {k: sum(1 for v in how.values() if v == k) for k in ("kept", "matched", "moved", "new")}
    summary.update(retired=len(retired), reactivated=len(reactivated), total=len(items))
    return summary, retired, nxt


def apply_to_registry(reg, items, retired, nxt, src):
    ts = now_iso()
    for it, occ in zip(items, with_occ(items)):
        e = reg["ids"].get(it["id"]) or {"first_seen": ts}
        e.update(fingerprint(it, occ), status="active", last_seen=ts, retired_at=None)
        reg["ids"][it["id"]] = e
    for r in retired:
        reg["ids"][r].update(status="retired", retired_at=ts)
    reg["next_id"] = nxt
    reg["updated_at"] = ts
    reg["last_source_file"] = os.path.basename(src)


# ── guard ───────────────────────────────────────────────────────────────────────────────────────
def guard_check(items, per_cat, sheets, reg, retired_n):
    """-> list of rejection reasons ([] = pass). Only enforced once id_column_required is set."""
    if not reg.get("id_column_required"):
        return []
    reasons = []
    missing = [s for s, n in per_cat.items() if n > 0 and not sheets.get(s, {}).get("id_col")]
    if missing:
        reasons.append(f"'{ID_HEADER}' column missing on sheet(s): {', '.join(sorted(missing))}")
    seen, bad = set(), {"blank": 0, "duplicate": 0, "unknown": 0}
    for it in items:
        v = it.get("_sheet_id") or ""
        if not v:
            bad["blank"] += 1
        elif not ID_RE.match(v) or v not in reg["ids"]:
            bad["unknown"] += 1
        elif v in seen:
            bad["duplicate"] += 1
        seen.add(v)
    nbad = sum(bad.values())
    if items and not missing and nbad / len(items) > BAD_ID_MAX:
        reasons.append(f"{nbad} of {len(items)} lines ({100 * nbad / len(items):.1f}%) have a blank/duplicate/"
                       f"unknown Exos ID (blank {bad['blank']}, duplicate {bad['duplicate']}, unknown "
                       f"{bad['unknown']}); limit {int(BAD_ID_MAX * 100)}%")
    active = sum(1 for e in reg["ids"].values() if e.get("status") == "active")
    if active and retired_n / active > RETIRE_MAX:
        reasons.append(f"upload would retire {retired_n} of {active} active ids "
                       f"({100 * retired_n / active:.0f}%; limit {int(RETIRE_MAX * 100)}%)")
    return reasons


def decision_payload(src, uploader, reasons):
    f = os.path.basename(src)
    return {
        "title": "Shop inventory upload rejected: Exos ID column missing/changed",
        "question": (f"A new shop inventory upload ({f}) was rejected because the permanent Exos ID column "
                     "is missing or was changed. The Full Shop Inventory page is still showing the previous "
                     "upload. Keep rejecting, or accept this upload and re-match lines by location+contents?"),
        "context": (f"File: {f}\nUploaded by: {uploader or 'unknown'}\nReasons:\n- " + "\n- ".join(reasons) +
                    "\n\nPer your 2026-09-30 direction the Exos ID column cannot be removed or changed without "
                    "your decision. Accepting re-matches by location+contents; lines that can't be matched get "
                    "new ids and their photos/edits would detach. Accept path (Exo runs after your answer): "
                    f"python3 scripts/reindex_shop_inventory.py --file mission-control/uploads/{f} --override-guard"),
        "proposedAction": "Keep rejecting; ask Steve to re-upload starting from the file with the Exos ID column.",
        "type": "choice",
        "options": ["Keep rejecting — have Steve re-upload with the ID column (recommended)",
                    "Accept this upload and re-match by location+contents"],
        "priority": "high",
        "dedupeKey": f"shop-id-guard:{f}",
        "assignedTo": "jquinn@exosaero.com",
        "approver": "John Quinn",
        "source": "shop-id-guard (reindex_shop_inventory.py)",
        "agentClass": "shop-id-guard-exo3",
        "relatedItem": "/shop-inventory.html",
    }


def file_decision(payload):
    tok = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
    r = urllib.request.Request(MC + "/api/decisions/ingest", data=json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json", "x-exo-token": tok}, method="POST")
    return json.load(urllib.request.urlopen(r, timeout=30))


def fleet(event_action, outcome, detail, enabled):
    if not enabled:
        return
    try:
        sys.path.insert(0, os.path.join(WS, "scripts"))
        import fleet_log
        fleet_log.event("shop-id-guard", "govern", event_action, outcome=outcome, owner="John Quinn", detail=detail)
    except Exception:
        pass


def load_json(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--uploader", default="")
    ap.add_argument("--data-dir", default=DATA)
    ap.add_argument("--log-dir", default=LOGS)
    ap.add_argument("--seed-registry", action="store_true")
    ap.add_argument("--override-guard", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--decision-dry-run", action="store_true")
    ap.add_argument("--no-fleet-log", action="store_true")
    ap.add_argument("--json", action="store_true", help="print result JSON on stdout (selftest)")
    a = ap.parse_args(argv)
    out_p = os.path.join(a.data_dir, "shop-inventory.json")
    reg_p = os.path.join(a.data_dir, "shop-id-registry.json")
    guard_p = os.path.join(a.data_dir, "shop-id-guard.json")
    log_p = os.path.join(a.log_dir, "shop-id-guard.log")
    use_fleet = not a.no_fleet_log and not a.dry_run

    if a.seed_registry:
        if os.path.exists(reg_p):
            raise SystemExit(f"registry already exists: {reg_p} (never re-seed)")
        reg = seed_registry(out_p)
        if not a.dry_run:
            json.dump(reg, open(reg_p, "w"), indent=1, ensure_ascii=False)
        print(f"seeded {len(reg['ids'])} ids, next_id {reg['next_id']} -> {reg_p}")
        return 0

    guard = load_json(guard_p, {"rejected": {}})
    src = a.file or newest_locations_xlsx(rejected=set(guard.get("rejected", {})))
    if not src:
        print("no locations xlsx found", file=sys.stderr); return 1
    reg = load_registry(reg_p) or empty_registry()
    items, per_cat, sheets = parse_workbook(src)
    summary, retired, nxt = assign_ids(items, reg)
    reasons = [] if a.override_guard else guard_check(items, per_cat, sheets, reg, len(retired))
    result = {"file": os.path.basename(src), "summary": summary, "reasons": reasons,
              "ids": [it["id"] for it in items], "rejected": bool(reasons)}

    if reasons:
        payload = decision_payload(src, a.uploader, reasons)
        result["decision_payload"] = payload
        rec = {"at": now_iso(), "file": os.path.basename(src), "uploader": a.uploader, "reasons": reasons}
        if not a.dry_run:
            os.makedirs(a.log_dir, exist_ok=True)
            with open(log_p, "a") as f:
                f.write(json.dumps(dict(rec, action="REJECTED"), ensure_ascii=False) + "\n")
            guard.setdefault("rejected", {})[os.path.basename(src)] = rec
            json.dump(guard, open(guard_p, "w"), indent=1, ensure_ascii=False)
            if a.decision_dry_run:
                result["decision"] = "dry-run (not filed)"
            else:
                try:
                    d = file_decision(payload)
                    result["decision"] = d.get("id")
                except Exception as e:
                    result["decision"] = f"FAILED: {e}"
                    with open(log_p, "a") as f:
                        f.write(json.dumps({"at": now_iso(), "file": rec["file"], "action": "DECISION_FAILED",
                                            "error": str(e)}) + "\n")
        fleet("reindex", "rejected", {"file": rec["file"], "uploader": a.uploader, "reasons": reasons,
                                      "decision": result.get("decision")}, use_fleet)
        print(json.dumps(result) if a.json else
              f"REJECTED {rec['file']}: " + " | ".join(reasons) + f" (decision: {result.get('decision', 'dry-run')})")
        return 3

    out_items = [{k: v for k, v in it.items() if not k.startswith("_")} for it in items]
    out = {
        "generated_at": now_iso(),
        "source_file": os.path.basename(src),
        "counts": per_cat,
        "total": len(out_items),
        "rocket": sum(1 for i in out_items if i["is_rocket"]),
        "id_match": dict(summary, registry=os.path.basename(reg_p), override=bool(a.override_guard)),
        "items": out_items,
    }
    if not a.dry_run:
        apply_to_registry(reg, items, retired, nxt, src)
        reg["last_summary"] = dict(summary, at=reg["updated_at"], file=os.path.basename(src),
                                   override=bool(a.override_guard))
        json.dump(reg, open(reg_p + ".tmp", "w"), indent=1, ensure_ascii=False)
        os.replace(reg_p + ".tmp", reg_p)
        json.dump(out, open(out_p + ".tmp", "w"), indent=1)
        os.replace(out_p + ".tmp", out_p)
        if a.override_guard and os.path.basename(src) in guard.get("rejected", {}):
            guard["rejected"].pop(os.path.basename(src))
            json.dump(guard, open(guard_p, "w"), indent=1, ensure_ascii=False)
    fleet("reindex", "ok", {"file": os.path.basename(src), "uploader": a.uploader, **summary}, use_fleet)
    if a.json:
        print(json.dumps(result))
    else:
        print("wrote" if not a.dry_run else "dry-run (nothing written):", out_p)
        print("source:", os.path.basename(src))
        print("per-category:", per_cat)
        print("total lines:", len(out_items), "| rocket-matched:", out["rocket"])
        print("id match:", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
