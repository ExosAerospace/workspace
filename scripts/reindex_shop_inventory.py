#!/usr/bin/env python3
"""Ingest Steve's full shop workbook (Current_Inventory_Locations*.xlsx) as the INVENTORY OF RECORD.
Writes mission-control/data/shop-inventory.json = every physical line across Warehouse / Parts Room /
Trailer / Assets (rocket + NON-rocket), location forward-filled, qty/value/jurisdiction, plus is_rocket
flag (SKU matches a BLK3 BOM part). Additive; does not touch the BOM (bom-index.json) or photo ledger."""
import openpyxl, json, os, glob, re, sys

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control/data")
OUT = os.path.join(DATA, "shop-inventory.json")
ITEM_SHEETS = {"Warehouse", "Parts Room", "Trailer", "Assets", "Sales & Trash"}
HEADER_TOKENS = {"qty", "contents", "exos sku", "source", "source/sku", "asset", "description", "location", "value"}


def newest_locations_xlsx():
    c = [x for x in glob.glob(os.path.join(WS, "mission-control/uploads/*Current_Inventory_Locations*.xlsx"))
         if ".bak" not in x]
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


def main():
    src = newest_locations_xlsx()
    if not src:
        print("no locations xlsx found", file=sys.stderr); sys.exit(1)
    bom = bom_sku_set()
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    items = []
    per_cat = {}
    nid = 0
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
        }
        last_loc = ""
        count = 0
        for row in ws.iter_rows(min_row=hrow + 1, values_only=True):
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
            nid += 1
            items.append({
                "id": f"SHOP-{nid:05d}",
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
            })
            count += 1
        per_cat[ws.title] = count
    wb.close()
    out = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "source_file": os.path.basename(src),
        "counts": per_cat,
        "total": len(items),
        "rocket": sum(1 for i in items if i["is_rocket"]),
        "items": items,
    }
    json.dump(out, open(OUT, "w"), indent=1)
    print("wrote", OUT)
    print("source:", os.path.basename(src))
    print("per-category:", per_cat)
    print("total lines:", len(items), "| rocket-matched:", out["rocket"])


if __name__ == "__main__":
    main()
