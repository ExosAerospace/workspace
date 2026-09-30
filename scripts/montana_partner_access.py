#!/usr/bin/env python3
"""
montana_partner_access.py — grant/revoke Mission Control seats for Montana Spaceport partners
(role `montana_partner`). exo3 spec: agent-registry.json → montana-partner-access-exo3.
Owner: John Quinn. MC task #3288 (parent #3287).

Human-confirm: every state change is DRY-RUN by default and needs --apply. A person runs
this after Jon confirms the partner's email; nothing here runs on a schedule.

  list                                         show pending/active seats + matching MC users
  add --name N --org O --email E [--apply]     create the MC user (temp password, forced reset),
      [--no-cloudflare]                        add E to the Cloudflare Access "approved users"
                                               policy, mark the seat active
  deactivate --email E [--apply]               set the MC user inactive (reversible) + remove E
      [--no-cloudflare]                        from the Cloudflare policy, mark the seat revoked
  --selftest [--live]                          offline checks; --live also probes the running MC
                                               as throwaway users (partner / must-reset partner /
                                               admin / early_adopter), then deletes them

Every grant/revoke is logged to logs/fleet-events.jsonl (fleet_log) and
logs/montana-partner-access.jsonl (audit trail).
"""
import argparse, datetime, hashlib, http.cookiejar, json, os, re, secrets, shutil, string, sys, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
MC = os.path.join(WS, "mission-control")
USERS = os.path.join(MC, "users.json")
SEATS = os.path.join(MC, "data", "montana-partner-seats.json")
AUDIT = os.path.join(WS, "logs", "montana-partner-access.jsonl")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
ROLE = "montana_partner"
AGENT = "montana-partner-access-exo3"
OWNER = "John Quinn"
MC_URL = "http://127.0.0.1:8080"
PUBLIC_URL = "https://mc.exosaero.space"
CF_ACC = "6b178cbe1c76dfd717c07460d5c0f653"
CF_APP = "e4fef0a6-7c43-42d0-91ca-ff9e22fa70ea"
CF_POL = "3bf75a2c-33f7-4901-bfac-ae153fb47d9b"   # "Mission Control — approved users"
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

sys.path.insert(0, os.path.join(WS, "scripts"))
try:
    from fleet_log import event as _fleet_event, new_corr
except Exception:  # logging must never block a grant
    _fleet_event, new_corr = None, (lambda: secrets.token_hex(8))


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def audit(action, outcome, detail, corr):
    rec = {"ts": now(), "corr": corr, "agent": AGENT, "action": action, "outcome": outcome, "detail": detail}
    try:
        os.makedirs(os.path.dirname(AUDIT), exist_ok=True)
        with open(AUDIT, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        print(f"  (audit log write failed: {e})")
    if _fleet_event:
        try:
            _fleet_event(AGENT, "govern", action, corr=corr, detail=detail, owner=OWNER, outcome=outcome)
        except Exception:
            pass


def hash_password(pw, salt):
    # mirrors server.js hashPassword(): crypto.pbkdf2Sync(pw, salt, 100000, 64, 'sha256')
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100000, dklen=64).hex()


def temp_password():
    word = "".join(secrets.choice(string.ascii_lowercase) for _ in range(6))
    num = "".join(secrets.choice(string.digits) for _ in range(3))
    return f"ExosMT-{word}-{num}"


def max_id(users):
    """users.json mixes int and string ids — only numeric ones count for the next id."""
    return max([int(u["id"]) for u in users if str(u.get("id", "")).isdigit()] or [0])


def load(p):
    with open(p) as f:
        return json.load(f)


def save_atomic(p, obj, backup_tag=None):
    if backup_tag:
        shutil.copy2(p, f"{p}.bak-{backup_tag}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}")
    tmp = f"{p}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    if os.path.exists(p):
        shutil.copymode(p, tmp)   # users.json is 0600 — never widen it
    os.replace(tmp, p)


# ── Cloudflare Access (app-scoped PUT — the account-level path 404s; see reference_mc_cloudflare_access) ──
def cf_req(method, body=None):
    tok = load(SECRETS).get("cloudflare_zt_token")
    if not tok:
        raise RuntimeError("cloudflare_zt_token missing from secrets.json")
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACC}/access/apps/{CF_APP}/policies/{CF_POL}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    if not d.get("success"):
        raise RuntimeError(f"Cloudflare API error: {d.get('errors')}")
    return d["result"]


def cf_emails(pol):
    return [i["email"]["email"].lower() for i in pol.get("include", []) if "email" in i]


def cf_set(email, present):
    """Add/remove one email on the approved-users include list. Returns 'added'|'removed'|'unchanged'."""
    pol = cf_req("GET")
    have = email.lower() in cf_emails(pol)
    if have == present:
        return "unchanged"
    inc = pol.get("include", [])
    if present:
        inc = inc + [{"email": {"email": email}}]
    else:
        inc = [i for i in inc if not ("email" in i and i["email"]["email"].lower() == email.lower())]
    cf_req("PUT", {"name": pol["name"], "decision": pol["decision"], "include": inc,
                   "exclude": pol.get("exclude", []), "require": pol.get("require", [])})
    after = cf_emails(cf_req("GET"))
    if (email.lower() in after) != present:
        raise RuntimeError("Cloudflare policy did not take the change (verify in dashboard)")
    return "added" if present else "removed"


def cf_manual_step(email, present=True):
    verb = "ADD" if present else "REMOVE"
    return (f"Cloudflare step ({verb}): one.dash.cloudflare.com (Jquinn@exosaero.com account) → Zero Trust → Access → "
            f"Applications → mc → policy \"Mission Control — approved users\" → Include → Emails → {verb.lower()} {email} → Save.")


def find_seat(seats, name, org, email):
    for s in seats["seats"]:
        if s.get("email") and s["email"].lower() == email.lower():
            return s
    first = (name or "").split()[0].lower() if name else ""
    for s in seats["seats"]:
        if s["status"] == "pending" and s["name"].split()[0].lower() == first and (not org or org.lower()[:8] in s["org"].lower() or s["org"].lower()[:8] in org.lower()):
            return s
    return None


def cmd_list(_a):
    seats = load(SEATS)
    users = {u["email"].lower(): u for u in load(USERS) if u.get("email")}
    print(f"Montana partner seats ({SEATS}):")
    for s in seats["seats"]:
        u = users.get((s.get("email") or "").lower())
        mc = f"MC user #{u['id']} role={u['role']} active={u['active']}{' must_reset' if u.get('must_reset') else ''}" if u else "no MC user"
        print(f"  [{s['status']:8}] {s['seat_id']:12} {s['name']:12} {s['org'][:40]:40} email={s.get('email') or '(pending)'} — {mc}")
    others = [u for u in users.values() if u.get("role") == ROLE and u["email"].lower() not in {(s.get('email') or '').lower() for s in seats['seats']}]
    for u in others:
        print(f"  [no-seat ] MC user #{u['id']} {u['name']} {u['email']} active={u['active']}")


def cmd_add(a):
    corr = new_corr()
    email = a.email.strip()
    if not EMAIL_RE.match(email):
        sys.exit(f"ERROR: not a valid email: {email!r}")
    users = load(USERS)
    seats = load(SEATS)
    existing = next((u for u in users if (u.get("email") or "").lower() == email.lower()), None)
    if existing and existing.get("role") != ROLE:
        sys.exit(f"ERROR: {email} already exists as MC user #{existing['id']} with role {existing['role']} — refusing to change an internal account.")
    seat = find_seat(seats, a.name, a.org, email)
    print(f"Plan for {a.name} <{email}> ({a.org}) — role {ROLE}:")
    print(f"  seat: {seat['seat_id'] + ' (' + seat['status'] + ')' if seat else 'NEW seat will be created'}")
    print(f"  MC user: {'re-activate #' + str(existing['id']) + ' + new temp password' if existing else 'create new user'} (must_reset=true)")
    print(f"  Cloudflare: {'skip (--no-cloudflare)' if a.no_cloudflare else 'add to approved-users policy via API'}")
    if not a.apply:
        print("\nDRY-RUN — nothing changed. Re-run with --apply once Jon has confirmed this email.")
        return 0
    pw, salt = temp_password(), secrets.token_hex(32)
    if existing:
        existing.update({"active": True, "password_hash": hash_password(pw, salt), "password_salt": salt, "must_reset": True})
        uid = existing["id"]
    else:
        uid = max_id(users) + 1
        users.append({"id": uid, "email": email, "name": a.name, "role": ROLE, "org": a.org,
                      "password_hash": hash_password(pw, salt), "password_salt": salt,
                      "created_at": now(), "active": True, "last_login": None, "must_reset": True})
    save_atomic(USERS, users, backup_tag="montana-partner")
    cf_result, cf_note = "skipped", cf_manual_step(email, True)
    if not a.no_cloudflare:
        try:
            cf_result = cf_set(email, True)
            cf_note = f"Cloudflare Access policy: {cf_result} (verified by re-reading the policy)."
        except Exception as e:
            cf_result = f"FAILED: {e}"
            cf_note = f"Cloudflare API failed ({e}). Do it by hand — " + cf_manual_step(email, True)
    if not seat:
        seat = {"seat_id": "mt-" + re.sub(r"[^a-z0-9]+", "-", a.name.lower()).strip("-"), "name": a.name, "org": a.org, "created": now()[:10]}
        seats["seats"].append(seat)
    seat.update({"name": a.name, "org": a.org, "email": email, "status": "active", "activated_at": now(), "mc_user_id": uid})
    detail = {"email": email, "name": a.name, "org": a.org, "mc_user_id": uid, "seat": seat["seat_id"], "cloudflare": cf_result}
    seats.setdefault("events", []).append({"ts": now(), "action": "grant", **detail, "corr": corr})
    save_atomic(SEATS, seats)
    audit("access_grant", "ok" if not str(cf_result).startswith("FAILED") else "partial", detail, corr)
    print(f"\nAPPLIED (corr {corr}). MC user #{uid} created/activated, role {ROLE}, forced reset on first login.")
    print(f"  {cf_note}")
    print("\nSend to the partner (Jon sends — never Exo directly to Montana partners):")
    print(f"  1. Open {PUBLIC_URL} and enter {email} at the Cloudflare screen; a one-time code is emailed from noreply@notify.cloudflare.com (check spam).")
    print(f"  2. Sign in to Mission Control with {email} and temporary password: {pw}")
    print("  3. You'll be taken to 'Set password' — choose your own (8+ chars). You then land on the Montana partner view.")
    return 0


def cmd_deactivate(a):
    corr = new_corr()
    email = a.email.strip()
    users = load(USERS)
    u = next((x for x in users if (x.get("email") or "").lower() == email.lower()), None)
    if not u or u.get("role") != ROLE:
        sys.exit(f"ERROR: no {ROLE} user with email {email}")
    print(f"Plan: set MC user #{u['id']} {u['name']} inactive (reversible; sessions die on next server check); "
          f"{'skip Cloudflare' if a.no_cloudflare else 'remove from Cloudflare approved-users policy'}.")
    if not a.apply:
        print("DRY-RUN — nothing changed. Re-run with --apply.")
        return 0
    u["active"] = False
    save_atomic(USERS, users, backup_tag="montana-partner")
    cf_result = "skipped"
    if not a.no_cloudflare:
        try:
            cf_result = cf_set(email, False)
        except Exception as e:
            cf_result = f"FAILED: {e}"
            print("  " + cf_manual_step(email, False))
    seats = load(SEATS)
    for s in seats["seats"]:
        if (s.get("email") or "").lower() == email.lower():
            s.update({"status": "revoked", "revoked_at": now()})
    seats.setdefault("events", []).append({"ts": now(), "action": "revoke", "email": email, "cloudflare": cf_result, "corr": corr})
    save_atomic(SEATS, seats)
    audit("access_revoke", "ok", {"email": email, "mc_user_id": u["id"], "cloudflare": cf_result}, corr)
    print(f"APPLIED: #{u['id']} inactive; Cloudflare: {cf_result}. Note: the MC login rejects inactive users; "
          "restart MC or wait for session expiry (24h) to end a live session.")
    return 0


# ── eval ──────────────────────────────────────────────────────────────────────────────────────
PARTNER_ALLOWED = ["/api/me", "/api/montana-partner/summary", "/api/montana-partner/prospects", "/api/montana-partner/tasks"]
PARTNER_DENIED = [  # finance / CRM / decisions / investor / cap table / other tasks / vault / dossiers / uploads / admin
    "/api/operational-finance", "/api/capital-bridge", "/api/commissions", "/api/companies", "/api/contacts",
    "/api/crm", "/api/deals", "/api/decisions", "/api/tasks", "/api/task-desc?id=1", "/api/dossiers",
    "/api/uploads", "/api/admin/users", "/api/dataroom", "/api/chat", "/api/payload-customers", "/api/dd",
    "/api/capstone-program", "/api/opportunities", "/api/vault", "/api/hr", "/api/cap-table", "/api/series-a",
    "/api/investors", "/api/tasks/updates?task_id=1",
]
PARTNER_REDIRECT_PAGES = ["/", "/index.html", "/crm.html", "/finance.html", "/decisions.html", "/vault.html", "/dossier.html",
                          "/dataroom.html", "/docusign", "/data/decisions.json", "/data/capital_bridge_ledger.json", "/users.json.bak"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def mc_client():
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), NoRedirect())


def mc_call(op, path, method="GET", body=None):
    req = urllib.request.Request(MC_URL + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        r = op.open(req, timeout=20)
        return r.status, r.headers.get("Location"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location"), e.read()


def selftest(live):
    results = []

    def check(name, ok, info=""):
        results.append((name, bool(ok), info))

    # Offline: server wiring + data files
    src = open(os.path.join(MC, "server.js")).read()
    check("server: montana_partner sandbox block present", "session.role === 'montana_partner'" in src)
    check("server: role accepted by admin user API", src.count("'dd_reviewer', 'montana_partner'") >= 2)
    check("server: feeds gated to montana_partner/admin/manager", "['montana_partner', 'admin', 'manager'].includes(s.role)" in src)
    check("server: prospects feed whitelists fields (no email/phone)", "select=name,title,organization,company_id" in src and "select=id,name,industry,tier,website,description,tags" in src)
    check("server: forced reset honoured", "mpUser && mpUser.must_reset" in src and "delete user.must_reset" in src)
    seats = load(SEATS)
    check("seats: none activated without an email", all(s["status"] != "active" or s.get("email") for s in seats["seats"]))
    check("seats: Edgar/Sean/Isaiah seeded", {s["seat_id"] for s in seats["seats"]} >= {"mt-edgar", "mt-sean", "mt-isaiah"})
    mp = load(os.path.join(MC, "data", "montana-partner.json"))
    blob = json.dumps({k: mp.get(k) for k in ("program", "status", "offer", "docs")}).lower()   # only what the feed serves
    check("partner content: no finance/investor/CUI terms", not re.search(r"\b(series a|investors?|cap[ -]table|409a|runway|itar|cui|\$6m|capital bridge)\b", blob))
    check("partner content: spaceport not claimed operational", "planned" in blob and "not yet licensed" in blob)
    check("email validation rejects junk", not EMAIL_RE.match("edgar@") and EMAIL_RE.match("a.b@montanaspaceport.com"))

    if live:
        users = load(USERS)
        tag = secrets.token_hex(4)
        base_id = max_id(users) + 1000
        temps = []

        def mk(role, suffix, extra=None):
            pw, salt = "Selftest-" + secrets.token_hex(12), secrets.token_hex(32)
            u = {"id": base_id + len(temps), "email": f"selftest-{suffix}-{tag}@exos-selftest.invalid", "name": f"Selftest {suffix}",
                 "role": role, "password_hash": hash_password(pw, salt), "password_salt": salt, "created_at": now(), "active": True,
                 "selftest": True}
            if role == "early_adopter":
                u["project"] = "Payload Sales"
            u.update(extra or {})
            temps.append(u)
            return u, pw

        creds = [mk(ROLE, "mp"), mk(ROLE, "mpreset", {"must_reset": True}), mk("admin", "admin"), mk("early_adopter", "ea")]
        cur = load(USERS)
        cur.extend(t for t, _ in creds)
        save_atomic(USERS, cur)
        try:
            ops = {}
            for (u, pw) in creds:
                op = mc_client()
                st, _, _ = mc_call(op, "/api/login", "POST", {"email": u["email"], "password": pw})
                check(f"login {u['role']}{' (must_reset)' if u.get('must_reset') else ''}", st == 200, f"HTTP {st}")
                ops[u["email"]] = op
            mp_op, rs_op, ad_op, ea_op = (ops[u["email"]] for u, _ in creds)
            for p in PARTNER_ALLOWED:
                st, _, _ = mc_call(mp_op, p)
                check(f"partner ALLOWED {p}", st == 200, f"HTTP {st}")
            st, _, body = mc_call(mp_op, "/api/montana-partner/prospects")
            leak = any(k in body.decode("utf-8", "ignore").lower() for k in ['"email"', '"phone"', '"notes"'])
            check("partner prospects carry no email/phone/notes fields", st == 200 and not leak)
            st, _, _ = mc_call(mp_op, "/api/montana-partner/summary")
            for p in PARTNER_DENIED:
                st, _, _ = mc_call(mp_op, p)
                check(f"partner DENIED {p}", st in (401, 403), f"HTTP {st}")
            st, loc, _ = mc_call(mp_op, "/api/tasks", "POST", {"title": "selftest should not be created"})
            check("partner DENIED POST /api/tasks", st == 403, f"HTTP {st}")
            st, loc, _ = mc_call(mp_op, "/api/montana-partner/note", "POST", {"task_id": 1, "body": "selftest"})
            check("partner note on untagged task DENIED", st == 403, f"HTTP {st}")
            for p in PARTNER_REDIRECT_PAGES:
                st, loc, _ = mc_call(mp_op, p)
                check(f"partner page {p} → partner view", st in (302, 403) and (st == 403 or "montana-partner" in (loc or "") or loc == "/"), f"HTTP {st} → {loc}")
            st, _, _ = mc_call(mp_op, "/montana-partner.html")
            check("partner page /montana-partner.html served", st == 200, f"HTTP {st}")
            st, _, _ = mc_call(rs_op, "/api/montana-partner/summary")
            check("must_reset partner blocked from feeds", st == 403, f"HTTP {st}")
            st, loc, _ = mc_call(rs_op, "/montana-partner.html")
            check("must_reset partner redirected to set-password", st == 302 and "set-password" in (loc or ""), f"HTTP {st} → {loc}")
            # Existing roles unaffected
            for p in ["/api/tasks", "/api/companies", "/api/decisions", "/api/montana-partner/summary", "/api/admin/users"]:
                st, _, _ = mc_call(ad_op, p)
                check(f"admin still ALLOWED {p}", st == 200, f"HTTP {st}")
            st, _, _ = mc_call(ea_op, "/api/tasks")
            check("early_adopter still ALLOWED /api/tasks", st == 200, f"HTTP {st}")
            for p in ["/api/companies", "/api/montana-partner/summary", "/api/decisions"]:
                st, _, _ = mc_call(ea_op, p)
                check(f"early_adopter still DENIED {p}", st == 403, f"HTTP {st}")
            for op in ops.values():
                mc_call(op, "/api/logout", "POST", {})
        finally:
            cur = load(USERS)
            ids = {t["id"] for t, _ in creds}
            cur = [u for u in cur if u.get("id") not in ids]
            save_atomic(USERS, cur)
            check("cleanup: throwaway users removed", not any(u.get("selftest") for u in load(USERS)))

    fails = [r for r in results if not r[1]]
    for name, ok, info in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  [' + info + ']') if info and not ok else ''}")
    print(f"\nselftest: {len(results) - len(fails)}/{len(results)} passed{' (live)' if live else ' (offline)'}")
    audit("selftest", "pass" if not fails else "fail", {"passed": len(results) - len(fails), "total": len(results), "live": live}, new_corr())
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--live", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    p = sub.add_parser("add")
    p.add_argument("--name", required=True); p.add_argument("--org", required=True); p.add_argument("--email", required=True)
    p.add_argument("--apply", action="store_true"); p.add_argument("--no-cloudflare", action="store_true")
    d = sub.add_parser("deactivate")
    d.add_argument("--email", required=True); d.add_argument("--apply", action="store_true"); d.add_argument("--no-cloudflare", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.live))
    if a.cmd == "list":
        return cmd_list(a)
    if a.cmd == "add":
        sys.exit(cmd_add(a))
    if a.cmd == "deactivate":
        sys.exit(cmd_deactivate(a))
    ap.print_help()


if __name__ == "__main__":
    main()
