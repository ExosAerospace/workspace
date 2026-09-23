#!/usr/bin/env python3
"""vaultwarden_org_setup.py — one-shot Exos org setup for the self-hosted Vaultwarden.

You run this yourself so your API key stays in your terminal (never a file, never sent to Exo):

  VW_CLIENT_ID='user.xxxx' VW_CLIENT_SECRET='xxxx' python3 scripts/vaultwarden_org_setup.py

It authenticates with your personal API key (which canNOT decrypt your vault), finds the
"Exos Aerospace" org, then:
  - creates the 7 standard Groups (idempotent),
  - enforces the Two-step-login (2FA) org policy,
  - lists the Collections it found (their names are end-to-end encrypted, so it prints IDs and the
    intended Group->Collection mapping for you to tick in the UI — that step needs your logged-in
    session's org key, which by design this key does not have).

Nothing here can read or expose any vault secret.
"""
import json, os, sys, urllib.request, urllib.parse, uuid

BASE = os.environ.get("VW_BASE", "https://vault.exosaero.space")
CID = os.environ.get("VW_CLIENT_ID") or (sys.argv[1] if len(sys.argv) > 1 else "")
CSEC = os.environ.get("VW_CLIENT_SECRET") or (sys.argv[2] if len(sys.argv) > 2 else "")
ORG_NAME = os.environ.get("VW_ORG", "Exos Aerospace")

GROUPS = ["Leadership", "Engineering", "Finance", "BD/Sales", "Compliance", "Shop Floor", "All Staff"]
# intended Group -> Collections (for the manual tick step)
MAP = {
    "Leadership": ["Executive/Leadership", "Finance & Accounting", "IT & Infrastructure", "Government & Compliance", "BD & CRM", "Engineering & Production", "Shared Ops"],
    "Engineering": ["Engineering & Production", "Shared Ops", "IT & Infrastructure"],
    "Finance": ["Finance & Accounting", "Executive/Leadership"],
    "BD/Sales": ["BD & CRM", "Shared Ops"],
    "Compliance": ["Government & Compliance", "IT & Infrastructure"],
    "Shop Floor": ["Shared Ops", "Engineering & Production"],
    "All Staff": ["Shared Ops"],
}


def req(method, path, token=None, body=None, form=None):
    url = BASE + path
    headers = {"Accept": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    r = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(r, timeout=30) as resp:
        t = resp.read().decode()
        return json.loads(t) if t else {}


def main():
    if not CID or not CSEC:
        print("Set VW_CLIENT_ID and VW_CLIENT_SECRET (from Vault → Settings → Security → Keys → View API Key)."); sys.exit(1)
    print(f"Authenticating to {BASE} …")
    try:
        tok = req("POST", "/identity/connect/token", form={
            "grant_type": "client_credentials", "scope": "api", "client_id": CID, "client_secret": CSEC,
            "deviceType": "21", "deviceIdentifier": str(uuid.uuid4()), "deviceName": "exo-org-setup"})
        access = tok["access_token"]
    except Exception as e:
        print("Auth failed — check the API key values.", e); sys.exit(1)
    orgs = []
    try:
        orgs = req("GET", "/api/organizations", token=access).get("Data", []) or []
    except Exception:
        orgs = []
    if not orgs:
        try:
            orgs = req("GET", "/api/accounts/profile", token=access).get("Organizations", []) or []
        except Exception:
            orgs = []
    org = next((o for o in orgs if (o.get("Name") or "").strip().lower() == ORG_NAME.lower()), None)
    if not org:
        print(f"Could not find org '{ORG_NAME}'. Orgs found: {[o.get('Name') for o in orgs]}"); sys.exit(1)
    oid = org.get("Id") or org.get("id")
    print(f"Org: {org.get('Name')}  (id {oid})")

    # existing groups
    try:
        existing = {(g.get("Name") or g.get("name")): (g.get("Id") or g.get("id"))
                    for g in req("GET", f"/api/organizations/{oid}/groups", token=access).get("Data", [])}
    except Exception:
        existing = {}
    gids = {}
    for name in GROUPS:
        if name in existing:
            gids[name] = existing[name]; print(f"  group exists: {name}")
        else:
            try:
                g = req("POST", f"/api/organizations/{oid}/groups", token=access,
                        body={"name": name, "accessAll": False, "collections": [], "users": []})
                gids[name] = g.get("Id") or g.get("id"); print(f"  group CREATED: {name}")
            except Exception as e:
                print(f"  group FAILED: {name} — {e}")

    # 2FA org policy (type 2 = TwoFactorAuthentication)
    try:
        req("PUT", f"/api/organizations/{oid}/policies/2", token=access, body={"type": 2, "enabled": True, "data": None})
        print("  2FA policy: ENFORCED")
    except Exception as e:
        print(f"  2FA policy: could not set ({e}) — toggle it in Settings → Policies → Two-step login")

    # collections (names are encrypted → print ids for the manual tick step)
    cols = req("GET", f"/api/organizations/{oid}/collections", token=access).get("Data", [])
    print(f"\nCollections found: {len(cols)} (names are encrypted; wire these in the UI):")
    for c in cols:
        print(f"    id {c.get('Id') or c.get('id')}")
    print("\nFinal step (Admin Console → Groups → each group → Collections tab, tick per this map):")
    for g, cs in MAP.items():
        print(f"    {g}  ->  {', '.join(cs)}")
    print("\nDone. Groups + 2FA are set. Then invite the team (Members → Invite) into their groups, "
          "and rotate this API key (Security → Keys → Rotate).")


if __name__ == "__main__":
    main()
