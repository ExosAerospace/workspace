#!/usr/bin/env python3
"""
mc_cell_onboard_exo3.py — Exo-run account setup for a customer/entity Mission Control cell.
exo3 spec: agent-registry.json -> mc-cell-onboard-exo3. Owner: John Quinn. (Jon 2026-10-22: "all those
account actions built to be as automated as possible with you doing as much of the setups as possible".)

The customer's people make the decisions in their own cell (who is a user, which features are on);
this script carries out the account plumbing on the Exos host so they never touch Cloudflare or Supabase.

  access-sync --entity E [--apply]     Cloudflare Access follows the cell's Admin user list: every active
                                       cell user is on the cell's "approved users" policy; a user disabled
                                       or deleted in the cell is removed. Emails that never were cell users
                                       (e.g. Exos support addresses) are left alone. Runs every 5 min (launchd
                                       com.exos.mc-cell-access-sync-exo3, --apply).
  supabase-create --entity E [--region R] [--apply]
                                       Creates the cell's own hosted database (Supabase project in the Exos
                                       org), waits until healthy, loads the MC schema, stores URL + service
                                       key in secrets.json as <entity>_supabase_url / _service_key. Needs
                                       secrets supabase_mgmt_token + supabase_org_id (one-time, Jon).
  status --entity E                    What is automated for this cell right now, and what still needs a person.

Every state change is DRY-RUN unless --apply. All actions -> logs/fleet-events.jsonl + logs/mc-cell-onboard.jsonl.
"""
import argparse, datetime, json, os, secrets as pysecrets, subprocess, sys, time, urllib.error, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
AUDIT = os.path.join(WS, "logs", "mc-cell-onboard.jsonl")
STATE = os.path.join(WS, "logs", "mc-cell-onboard-state.json")   # emails this script added, per entity
SCHEMA = os.path.join(WS, "erp-foundation", "schema.sql")
CF_ACC = "6b178cbe1c76dfd717c07460d5c0f653"
AGENT, OWNER = "mc-cell-onboard-exo3", "John Quinn"

sys.path.insert(0, os.path.join(WS, "scripts"))
try:
    from fleet_log import event as _fleet_event
except Exception:
    _fleet_event = None


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def audit(action, outcome, detail):
    os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
    with open(AUDIT, "a") as f:
        f.write(json.dumps({"ts": now(), "agent": AGENT, "action": action, "outcome": outcome, "detail": detail}) + "\n")
    if _fleet_event:
        try:
            _fleet_event(AGENT, "govern", action, detail=detail, owner=OWNER, outcome=outcome)
        except Exception:
            pass


def load(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d


def save(p, v):
    tmp = p + ".tmp"
    json.dump(v, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def sec(k):
    return (load(SECRETS, {}) or {}).get(k)


def http(method, url, token, body=None, timeout=30):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url.split('?')[0]} -> HTTP {e.code}: {e.read()[:300]!r}")
    return json.loads(raw) if raw else {}


# ── cell users ──
def cell_users(entity):
    out = subprocess.run(["docker", "exec", f"{entity}-mc-container-exo3", "cat", "/data/users.json"],
                         capture_output=True, text=True, timeout=30)
    if out.returncode:
        raise RuntimeError(f"cannot read {entity} users: {out.stderr.strip()[:200]}")
    u = json.loads(out.stdout)
    return u if isinstance(u, list) else u.get("users", [])


def active(u):
    return u.get("active", True) is not False and not u.get("disabled") and u.get("status", "active") != "inactive"


# ── Cloudflare Access ──
def cf_policy(entity):
    tok = sec("cloudflare_zt_token")
    if not tok:
        raise RuntimeError("cloudflare_zt_token missing from secrets.json")
    host = f"{entity}.exosaero.space"
    apps = http("GET", f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/access/apps?per_page=200", tok)["result"]
    app = next((a for a in apps if (a.get("domain") or "").split("/")[0] == host), None)
    if not app:
        raise RuntimeError(f"no Cloudflare Access app for {host} (run provision_entity_exo3.sh first)")
    pols = http("GET", f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/access/apps/{app['id']}/policies", tok)["result"]
    pol = next((p for p in pols if "approved users" in p["name"].lower()), None)
    if not pol:
        raise RuntimeError(f"no 'approved users' policy on the {host} app")
    return tok, app["id"], pol


def emails_of(pol):
    return [i["email"]["email"].lower() for i in pol.get("include", []) if "email" in i]


def cmd_access_sync(a):
    users = cell_users(a.entity)
    want = sorted({u["email"].lower() for u in users if u.get("email") and active(u)})
    off = {u["email"].lower() for u in users if u.get("email") and not active(u)}
    st = load(STATE, {}) or {}
    mine = set(st.get(a.entity, {}).get("added", []))
    tok, app_id, pol = cf_policy(a.entity)
    have = emails_of(pol)
    add = [e for e in want if e not in have]
    # remove only people the cell itself disabled/deleted — never addresses the cell never listed
    rm = [e for e in have if e in off or (e in mine and e not in want)]
    print(f"[{a.entity}] cell users active={len(want)} · policy has {len(have)} · add {add or '-'} · remove {rm or '-'}")
    if not add and not rm:
        return 0
    if not a.apply:
        print("DRY-RUN — re-run with --apply")
        return 0
    inc = [i for i in pol.get("include", []) if not ("email" in i and i["email"]["email"].lower() in rm)]
    inc += [{"email": {"email": e}} for e in add]
    http("PUT", f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/access/apps/{app_id}/policies/{pol['id']}", tok,
         {"name": pol["name"], "decision": pol["decision"], "include": inc,
          "exclude": pol.get("exclude", []), "require": pol.get("require", [])})
    after = emails_of(cf_policy(a.entity)[2])
    ok = all(e in after for e in add) and not any(e in after for e in rm)
    st.setdefault(a.entity, {})["added"] = sorted((mine | set(add)) - set(rm))
    save(STATE, st)
    audit("access_sync", "ok" if ok else "fail", {"entity": a.entity, "added": add, "removed": rm})
    print("applied" if ok else "WARNING: policy re-read does not match — check Cloudflare dashboard")
    return 0 if ok else 1


# ── Supabase ──
SB = "https://api.supabase.com/v1"


def cmd_supabase_create(a):
    tok, org = sec("supabase_mgmt_token"), sec("supabase_org_id")
    key_url, key_svc = f"{a.entity}_supabase_url", f"{a.entity}_supabase_service_key"
    if sec(key_url):
        print(f"[{a.entity}] already has a database: {sec(key_url)}")
        return 0
    if not tok or not org:
        print("BLOCKED: secrets.json needs supabase_mgmt_token (Supabase → Account → Access Tokens) and "
              "supabase_org_id (the Exos-managed customer org). One-time setup; after that every cell is automatic.")
        audit("supabase_create", "blocked", {"entity": a.entity, "missing": [k for k in ("supabase_mgmt_token", "supabase_org_id") if not sec(k)]})
        return 2
    name = f"mc-{a.entity}"
    existing = [p for p in http("GET", f"{SB}/projects", tok) if p.get("name") == name]
    print(f"[{a.entity}] project {name} in org {org}, region {a.region}: {'exists' if existing else 'will create'}")
    if not a.apply:
        print("DRY-RUN — re-run with --apply")
        return 0
    if existing:
        proj = existing[0]
    else:
        proj = http("POST", f"{SB}/projects", tok, {"name": name, "organization_id": org, "region": a.region,
                                                     "db_pass": pysecrets.token_urlsafe(24), "plan": "pro"}, timeout=60)
    ref = proj["id"] if "id" in proj else proj["ref"]
    for _ in range(60):  # up to ~10 min
        s = http("GET", f"{SB}/projects/{ref}", tok).get("status")
        if s == "ACTIVE_HEALTHY":
            break
        time.sleep(10)
    else:
        audit("supabase_create", "fail", {"entity": a.entity, "ref": ref, "why": "not healthy after 10 min"})
        print("project not healthy after 10 min — re-run later; it resumes from the existing project")
        return 1
    keys = http("GET", f"{SB}/projects/{ref}/api-keys", tok)
    svc = next(k["api_key"] for k in keys if k.get("name") == "service_role")
    if os.path.exists(SCHEMA):
        http("POST", f"{SB}/projects/{ref}/database/query", tok, {"query": open(SCHEMA).read()}, timeout=120)
    s = load(SECRETS, {})
    s[key_url], s[key_svc] = f"https://{ref}.supabase.co", svc
    save(SECRETS, s)
    os.chmod(SECRETS, 0o600)
    audit("supabase_create", "ok", {"entity": a.entity, "ref": ref, "region": a.region, "schema": os.path.exists(SCHEMA)})
    print(f"created {ref}; stored {key_url}/{key_svc}. Next: re-run provision_entity_exo3.sh --entity {a.entity} "
          f"--supabase-url https://{ref}.supabase.co --supabase-key <from secrets> to point the cell at it.")
    return 0


def cmd_status(a):
    print(f"Cell {a.entity}:")
    try:
        users = cell_users(a.entity)
        _, _, pol = cf_policy(a.entity)
        miss = [u["email"] for u in users if active(u) and u.get("email", "").lower() not in emails_of(pol)]
        print(f"  secure access: {len(users)} users; {'all on the access policy' if not miss else 'missing ' + ', '.join(miss)} (auto, every 5 min)")
    except Exception as e:
        print(f"  secure access: ERROR {e}")
    print(f"  database: {'hosted ' + sec(a.entity + '_supabase_url') if sec(a.entity + '_supabase_url') else 'local encrypted volume (hosted: supabase-create)'}")
    print(f"  supabase automation: {'ready' if sec('supabase_mgmt_token') and sec('supabase_org_id') else 'BLOCKED on one-time token (Jon)'}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    for n in ("access-sync", "supabase-create", "status"):
        s = sp.add_parser(n)
        s.add_argument("--entity", required=True)
        s.add_argument("--apply", action="store_true")
        s.add_argument("--region", default="us-east-1")
    a = p.parse_args()
    if not a.entity.isalnum():
        sys.exit("entity must be letters/digits")
    try:
        return {"access-sync": cmd_access_sync, "supabase-create": cmd_supabase_create, "status": cmd_status}[a.cmd](a)
    except Exception as e:
        audit(a.cmd.replace("-", "_"), "fail", {"entity": a.entity, "err": str(e)[:300]})
        print("ERROR:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
