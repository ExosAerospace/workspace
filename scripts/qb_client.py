#!/usr/bin/env python3
"""QuickBooks Online API client — vendor master + spend for Supplier-Diligence-exo3.

Reads OAuth2 creds from ~/.openclaw/secrets.json:
  qb_client_id, qb_client_secret, qb_refresh_token, qb_realm_id
  (optional: qb_env = "production" [default] | "sandbox")

QuickBooks refresh tokens ROTATE on every use and expire in ~100 days — so this client
persists the new refresh_token back to secrets.json after each refresh. If creds are
absent it raises QBNotConfigured so the caller can fall back to --sample.
"""
import os, json, base64, urllib.request, urllib.parse, time

SEC_PATH = os.path.expanduser("~/.openclaw/secrets.json")

class QBNotConfigured(Exception): pass

def _sec():
    return json.load(open(SEC_PATH))

def _save_sec(d):
    json.dump(d, open(SEC_PATH, "w"), indent=2)

def _need(d):
    miss = [k for k in ("qb_client_id","qb_client_secret","qb_refresh_token","qb_realm_id") if not d.get(k)]
    if miss:
        raise QBNotConfigured("missing QuickBooks creds in secrets.json: " + ", ".join(miss))

def _base(env):
    return "https://sandbox-quickbooks.api.intuit.com" if env == "sandbox" else "https://quickbooks.api.intuit.com"

def get_access_token():
    """Refresh + return a bearer access token; persists the rotated refresh_token."""
    d = _sec(); _need(d)
    basic = base64.b64encode(f"{d['qb_client_id']}:{d['qb_client_secret']}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type":"refresh_token","refresh_token":d["qb_refresh_token"]}).encode()
    req = urllib.request.Request("https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer", data=body,
        headers={"Authorization":f"Basic {basic}","Content-Type":"application/x-www-form-urlencoded","Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)
    # persist rotated refresh token
    if tok.get("refresh_token") and tok["refresh_token"] != d["qb_refresh_token"]:
        d["qb_refresh_token"] = tok["refresh_token"]; _save_sec(d)
    return tok["access_token"], d["qb_realm_id"], d.get("qb_env","production")

def query(sql, access=None, realm=None, env=None):
    if access is None:
        access, realm, env = get_access_token()
    url = f"{_base(env)}/v3/company/{realm}/query?" + urllib.parse.urlencode({"query": sql, "minorversion":"73"})
    req = urllib.request.Request(url, headers={"Authorization":f"Bearer {access}","Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r).get("QueryResponse", {})

def list_vendors():
    """Return active + inactive vendors: [{id,name,active,email,city,country,balance}]."""
    access, realm, env = get_access_token()
    out, start = [], 1
    while True:
        qr = query(f"SELECT * FROM Vendor STARTPOSITION {start} MAXRESULTS 1000", access, realm, env)
        vs = qr.get("Vendor", [])
        for v in vs:
            addr = v.get("BillAddr", {}) or {}
            out.append({
                "qb_id": v.get("Id"), "name": v.get("DisplayName") or v.get("CompanyName"),
                "active": v.get("Active", True), "email": (v.get("PrimaryEmailAddr") or {}).get("Address",""),
                "city": addr.get("City",""), "country": addr.get("Country",""),
                "balance": v.get("Balance", 0), "tax_id": v.get("TaxIdentifier",""),
            })
        if len(vs) < 1000: break
        start += 1000
    return out

def vendor_spend(days=365):
    """Aggregate spend by vendor name from Bills + Purchases over the window. {name: total}."""
    access, realm, env = get_access_token()
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=days)).isoformat()
    spend = {}
    for entity, datefield in (("Bill","TxnDate"), ("Purchase","TxnDate")):
        start = 1
        while True:
            qr = query(f"SELECT * FROM {entity} WHERE {datefield} >= '{since}' STARTPOSITION {start} MAXRESULTS 1000", access, realm, env)
            rows = qr.get(entity, [])
            for r in rows:
                ref = (r.get("VendorRef") or r.get("EntityRef") or {})
                nm = ref.get("name") or ref.get("value") or "?"
                spend[nm] = spend.get(nm, 0) + float(r.get("TotalAmt", 0) or 0)
            if len(rows) < 1000: break
            start += 1000
    return spend

if __name__ == "__main__":
    try:
        vs = list_vendors()
        print(f"vendors: {len(vs)}")
        for v in vs[:10]: print(" ", v["name"], "|", v.get("country") or "?", "| bal", v.get("balance"))
    except QBNotConfigured as e:
        print("QB not configured:", e)
