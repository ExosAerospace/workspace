#!/usr/bin/env python3
"""QuickBooks Online API client — vendor master + spend for Supplier-Diligence-exo3.

Reads OAuth2 creds from ~/.openclaw/secrets.json:
  qb_client_id, qb_client_secret, qb_refresh_token, qb_realm_id
  (optional: qb_env = "production" [default] | "sandbox")

QuickBooks refresh tokens ROTATE on every use and expire in ~100 days — so this client
persists the new refresh_token back to secrets.json after each refresh. If creds are
absent it raises QBNotConfigured so the caller can fall back to --sample.
"""
import os, json, base64, secrets, urllib.request, urllib.parse, urllib.error, time

SEC_PATH = os.path.expanduser("~/.openclaw/secrets.json")
STATE_PATH = os.path.expanduser("~/.openclaw/.qb_oauth_state.json")

class QBNotConfigured(Exception): pass
class QBReauthRequired(Exception):
    """Refresh/authorization is dead (expired or revoked refresh token / invalid_grant).
    Remediation is a fresh OAuth consent, not a retry."""
class QBAuthCSRF(Exception):
    """OAuth callback `state` did not match — possible CSRF; authorization rejected."""

def _http_err_body(e):
    try: return e.read().decode("utf-8", "replace")
    except Exception: return ""

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

# Intuit OpenID Connect discovery documents — the authoritative source of the current
# OAuth2 endpoints. We fetch these at runtime (cached per-process) so we always use the
# latest authorization/token/revocation endpoints Intuit publishes, and fall back to the
# documented canonical URLs if discovery is briefly unreachable.
_DISCOVERY_URL = {
    "production": "https://developer.api.intuit.com/.well-known/openid_configuration",
    "sandbox":    "https://developer.api.intuit.com/.well-known/openid_sandbox_configuration",
}
_DISCOVERY_FALLBACK = {
    "authorization_endpoint": "https://appcenter.intuit.com/connect/oauth2",
    "token_endpoint":         "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
    "revocation_endpoint":    "https://developer.api.intuit.com/v2/oauth2/tokens/revoke",
    "userinfo_endpoint":      "https://accounts.platform.intuit.com/v1/openid_connect/userinfo",
}
_discovery_cache = {}

def discovery(env=None):
    """Return Intuit's OAuth2 endpoint map from the OpenID discovery document (cached)."""
    env = env or "production"
    if env in _discovery_cache:
        return _discovery_cache[env]
    doc = dict(_DISCOVERY_FALLBACK)
    try:
        url = _DISCOVERY_URL.get(env, _DISCOVERY_URL["production"])
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            live = json.load(r)
        for k in _DISCOVERY_FALLBACK:
            if live.get(k):
                doc[k] = live[k]
    except Exception:
        pass  # fall back to documented canonical endpoints
    _discovery_cache[env] = doc
    return doc

def get_access_token():
    """Refresh + return a bearer access token; persists the rotated refresh_token."""
    d = _sec(); _need(d)
    env = d.get("qb_env", "production")
    token_endpoint = discovery(env)["token_endpoint"]
    basic = base64.b64encode(f"{d['qb_client_id']}:{d['qb_client_secret']}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type":"refresh_token","refresh_token":d["qb_refresh_token"]}).encode()
    req = urllib.request.Request(token_endpoint, data=body,
        headers={"Authorization":f"Basic {basic}","Content-Type":"application/x-www-form-urlencoded","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.load(r)
    except urllib.error.HTTPError as e:
        # 400 invalid_grant == refresh token expired or revoked -> reconnect required (no retry)
        body_txt = _http_err_body(e)
        if e.code in (400, 401) and "invalid_grant" in body_txt:
            raise QBReauthRequired(
                "QuickBooks refresh token expired or revoked - admin must re-authorize (reconnect).") from e
        raise
    # persist rotated refresh token
    if tok.get("refresh_token") and tok["refresh_token"] != d["qb_refresh_token"]:
        d["qb_refresh_token"] = tok["refresh_token"]; _save_sec(d)
    return tok["access_token"], d["qb_realm_id"], d.get("qb_env","production")

def query(sql, access=None, realm=None, env=None, _retried=False):
    if access is None:
        access, realm, env = get_access_token()
    url = f"{_base(env)}/v3/company/{realm}/query?" + urllib.parse.urlencode({"query": sql, "minorversion":"73"})
    req = urllib.request.Request(url, headers={"Authorization":f"Bearer {access}","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.load(r).get("QueryResponse", {})
    except urllib.error.HTTPError as e:
        # 401 == access token expired mid-session: mint a fresh one and retry ONCE.
        if e.code == 401 and not _retried:
            access, realm, env = get_access_token()
            return query(sql, access, realm, env, _retried=True)
        raise

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

def build_authorize_url(scopes="com.intuit.quickbooks.accounting", redirect_uri=None, env=None):
    """Return (authorize_url, state). Generates a cryptographically-random `state` (CSRF
    token) and persists it so exchange_code() can validate the callback."""
    d = _sec(); env = env or d.get("qb_env", "production")
    if not d.get("qb_client_id"):
        raise QBNotConfigured("qb_client_id missing")
    redirect_uri = redirect_uri or d.get("qb_redirect_uri") or "https://developer.intuit.com/app/developer/quickstart"
    state = secrets.token_urlsafe(24)
    json.dump({"state": state, "redirect_uri": redirect_uri, "ts": int(time.time())}, open(STATE_PATH, "w"))
    os.chmod(STATE_PATH, 0o600)
    authz = discovery(env)["authorization_endpoint"]
    url = authz + "?" + urllib.parse.urlencode({
        "client_id": d["qb_client_id"], "response_type": "code",
        "scope": scopes, "redirect_uri": redirect_uri, "state": state})
    return url, state

def exchange_code(redirect_url_or_code, redirect_uri=None, env=None, expected_state=None):
    """Exchange an authorization code for tokens; persist refresh_token + realm.
    Validates the OAuth `state` (CSRF) against the value issued by build_authorize_url()."""
    d = _sec(); env = env or d.get("qb_env", "production")
    saved = {}
    if os.path.exists(STATE_PATH):
        try: saved = json.load(open(STATE_PATH))
        except Exception: saved = {}
    code, realm, got_state = redirect_url_or_code, None, None
    if redirect_url_or_code.startswith("http") or "code=" in redirect_url_or_code:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url_or_code).query)
        code = (q.get("code") or [None])[0]
        realm = (q.get("realmId") or [None])[0]
        got_state = (q.get("state") or [None])[0]
    # CSRF: state echoed back MUST match what we issued
    want = expected_state or saved.get("state")
    if got_state is not None and want is not None and not secrets.compare_digest(got_state, want):
        raise QBAuthCSRF(f"state mismatch - authorization rejected")
    if not code:
        raise ValueError("no authorization code found in input")
    redirect_uri = redirect_uri or saved.get("redirect_uri") or d.get("qb_redirect_uri") or "https://developer.intuit.com/app/developer/quickstart"
    basic = base64.b64encode(f"{d['qb_client_id']}:{d['qb_client_secret']}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}).encode()
    req = urllib.request.Request(discovery(env)["token_endpoint"], data=body,
        headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.load(r)
    d["qb_refresh_token"] = tok["refresh_token"]
    if realm: d["qb_realm_id"] = realm
    d["qb_env"] = env
    _save_sec(d); os.chmod(SEC_PATH, 0o600)
    try: os.remove(STATE_PATH)
    except OSError: pass
    return {"realm": d.get("qb_realm_id"), "refresh_saved": True, "expires_in": tok.get("expires_in")}

def preferences(env=None):
    """Company feature/preference flags (Preferences entity — available on every QBO tier).
    Source of truth for version/tier-specific features that can appear or disappear when a
    user changes their QuickBooks Online plan."""
    return (query("SELECT * FROM Preferences").get("Preferences") or [{}])[0]

def feature_enabled(flag_path, env=None, prefs=None):
    """Dotted lookup into Preferences, e.g. 'VendorAndPurchasesPrefs.TrackingByCustomer' or
    'AccountingInfoPrefs.ClassTrackingPerTxn'. Returns None when the branch is absent — i.e.
    the feature isn't present in the user's current plan — so callers can degrade gracefully
    instead of erroring on a tier-specific entity."""
    node = prefs if prefs is not None else preferences(env)
    for part in flag_path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node

if __name__ == "__main__":
    try:
        vs = list_vendors()
        print(f"vendors: {len(vs)}")
        for v in vs[:10]: print(" ", v["name"], "|", v.get("country") or "?", "| bal", v.get("balance"))
    except QBNotConfigured as e:
        print("QB not configured:", e)
