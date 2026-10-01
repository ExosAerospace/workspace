#!/usr/bin/env python3
"""qb_supply.py — QuickBooks bridge for the MC Supply Chain module (erp-foundation + lib/supply-chain.js).

  pull         → JSON {vendors, pos, accounts} on stdout. Vendors (all, incl. inactive) + Purchase Orders
                 (all statuses, ≤1000 most recent) + the expense accounts recent POs use (for the MC PO form).
  push-po      → stdin JSON {vendor_qb_id, txn_date, due_date, memo, private_note, lines:[{description, qty,
                 unit_price, account_id}]} → creates a QB PurchaseOrder. DocNumber = next short numeric PO number
                 (books use custom txn numbers). Prints {"qb_id","doc_number"}.
  create-vendor→ stdin JSON {name, email, phone} → QB Vendor. Prints {"qb_id"}.

A QB PurchaseOrder is a NON-POSTING transaction (no GL impact). Only called after an MC PO is approved.
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WS, "scripts"))
import qb_client as q


def _post(path, body, params=None, _retried=False):
    access, realm, env = q.get_access_token()
    url = f"{q._base(env)}/v3/company/{realm}/{path}?" + urllib.parse.urlencode({"minorversion": "73", **(params or {})})
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {access}", "Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401 and not _retried:
            return _post(path, body, params, True)
        raise RuntimeError(f"QB POST {path} → {e.code}: {q._http_err_body(e)[:400]}") from e


def _all(entity, where="", order="MetaData.LastUpdatedTime DESC", cap=1000):
    rows, start = [], 1
    while start <= cap:
        r = q.query(f"SELECT * FROM {entity} {where} ORDERBY {order} STARTPOSITION {start} MAXRESULTS 100".replace("ORDERBY", "ORDER BY"))
        got = r.get(entity, [])
        rows += got
        if len(got) < 100:
            break
        start += 100
    return rows


def pull():
    vendors = []
    for v in _all("Vendor", "WHERE Active IN (true, false)", "DisplayName", cap=3000):
        addr = v.get("BillAddr") or {}
        vendors.append({"qb_id": v["Id"], "name": v.get("DisplayName"), "company": v.get("CompanyName"),
                        "email": (v.get("PrimaryEmailAddr") or {}).get("Address"), "phone": (v.get("PrimaryPhone") or {}).get("FreeFormNumber"),
                        "country": addr.get("Country") or "", "city": addr.get("City") or "", "state": addr.get("CountrySubDivisionCode") or "",
                        "active": bool(v.get("Active", True)), "balance": v.get("Balance"), "is_1099": bool(v.get("Vendor1099"))})
    pos, acct_use = [], {}
    for p in _all("PurchaseOrder"):
        lines = []
        for l in p.get("Line", []):
            d = l.get("ItemBasedExpenseLineDetail") or l.get("AccountBasedExpenseLineDetail") or {}
            ref = d.get("ItemRef") or d.get("AccountRef") or {}
            if not l.get("Amount") and not ref.get("name") and not l.get("Description"):
                continue
            if d.get("AccountRef"):
                k = (d["AccountRef"].get("value"), d["AccountRef"].get("name"))
                acct_use[k] = acct_use.get(k, 0) + 1
            lines.append({"qb_line_id": l.get("Id"), "description": l.get("Description", ""), "category": ref.get("name", ""),
                          "qty": d.get("Qty"), "unit_price": d.get("UnitPrice"), "amount": l.get("Amount")})
        pos.append({"qb_id": p["Id"], "doc_number": p.get("DocNumber"), "txn_date": p.get("TxnDate"), "due_date": p.get("DueDate"),
                    "vendor_qb_id": (p.get("VendorRef") or {}).get("value"), "vendor_name": (p.get("VendorRef") or {}).get("name"),
                    "status": p.get("POStatus"), "total": p.get("TotalAmt"), "memo": p.get("Memo", ""),
                    "private_note": p.get("PrivateNote", ""), "lines": lines})
    uses = {k[0]: n for k, n in acct_use.items()}
    accounts = []
    for t in ("Expense", "Cost of Goods Sold", "Other Expense", "Fixed Asset"):
        for a in q.query(f"SELECT Id, FullyQualifiedName, Active FROM Account WHERE AccountType = '{t}' MAXRESULTS 500").get("Account", []):
            if a.get("Active", True):
                accounts.append({"id": a["Id"], "name": a["FullyQualifiedName"], "type": t, "uses": uses.get(a["Id"], 0)})
    accounts.sort(key=lambda a: (-a["uses"], a["name"]))
    return {"vendors": vendors, "pos": pos, "accounts": accounts}


def next_po_number():
    r = q.query("SELECT DocNumber FROM PurchaseOrder ORDER BY MetaData.CreateTime DESC MAXRESULTS 300")
    nums = [int(x["DocNumber"]) for x in r.get("PurchaseOrder", []) if str(x.get("DocNumber", "")).isdigit() and len(x["DocNumber"]) <= 6]
    return str(max(nums) + 1) if nums else "1"


def push_po(d):
    body = {
        "VendorRef": {"value": str(d["vendor_qb_id"])},
        "TxnDate": d.get("txn_date"), "DocNumber": d.get("doc_number") or next_po_number(),
        "Memo": (d.get("memo") or "")[:4000], "PrivateNote": (d.get("private_note") or "")[:4000],
        "POStatus": "Open",
        "Line": [{"DetailType": "AccountBasedExpenseLineDetail", "Amount": round(float(l["qty"]) * float(l["unit_price"]), 2),
                  "Description": (l.get("description") or "")[:4000],
                  "AccountBasedExpenseLineDetail": {"AccountRef": {"value": str(l["account_id"])}}}
                 for l in d["lines"]],
    }
    if d.get("due_date"):
        body["DueDate"] = d["due_date"]
    body = {k: v for k, v in body.items() if v not in (None, "")}
    po = _post("purchaseorder", body)["PurchaseOrder"]
    return {"qb_id": po["Id"], "doc_number": po.get("DocNumber")}


def _po_sync(qb_id):
    r = q.query(f"SELECT * FROM PurchaseOrder WHERE Id = '{int(qb_id)}'").get("PurchaseOrder") or []
    if not r:
        raise RuntimeError(f"QB PO {qb_id} not found")
    return r[0]


def close_po(d):
    cur = _po_sync(d["qb_id"])
    if cur.get("POStatus") == "Closed":
        return {"qb_id": cur["Id"], "status": "Closed"}
    po = _post("purchaseorder", {"Id": cur["Id"], "SyncToken": cur["SyncToken"], "sparse": True, "POStatus": "Closed"})["PurchaseOrder"]
    return {"qb_id": po["Id"], "status": po.get("POStatus")}


def delete_po(d):
    """Test cleanup only: refuses anything whose DocNumber doesn't start with TEST-."""
    cur = q.query(f"SELECT Id, SyncToken, DocNumber FROM PurchaseOrder WHERE Id = '{int(d['qb_id'])}'").get("PurchaseOrder") or []
    if not cur or not str(cur[0].get("DocNumber", "")).startswith("TEST-"):
        raise RuntimeError("delete-po only removes TEST- POs")
    _post("purchaseorder", {"Id": cur[0]["Id"], "SyncToken": cur[0]["SyncToken"]}, {"operation": "delete"})
    return {"deleted": cur[0]["Id"]}


def create_vendor(d):
    body = {"DisplayName": d["name"], "CompanyName": d["name"]}
    if d.get("email"): body["PrimaryEmailAddr"] = {"Address": d["email"]}
    if d.get("phone"): body["PrimaryPhone"] = {"FreeFormNumber": d["phone"]}
    v = _post("vendor", body)["Vendor"]
    return {"qb_id": v["Id"]}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pull"
    try:
        if cmd == "pull":
            out = pull()
        elif cmd == "push-po":
            out = push_po(json.load(sys.stdin))
        elif cmd == "create-vendor":
            out = create_vendor(json.load(sys.stdin))
        elif cmd == "close-po":
            out = close_po(json.load(sys.stdin))
        elif cmd == "delete-po":
            out = delete_po(json.load(sys.stdin))
        elif cmd == "next-po":
            out = {"doc_number": next_po_number()}
        else:
            raise SystemExit("unknown command " + cmd)
        print(json.dumps(out))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)
