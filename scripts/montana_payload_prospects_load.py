#!/usr/bin/env python3
"""
montana_payload_prospects_load.py — load the verified Montana payload-customer prospects
(config/montana-payload-prospects.json) into the Supabase CRM (companies + contacts).
exo3 spec: agent-registry.json → montana-payload-prospects-load-exo3. Owner: John Quinn.
MC task #3287.

  python3 scripts/montana_payload_prospects_load.py            # DRY-RUN: show inserts/merges
  python3 scripts/montana_payload_prospects_load.py --apply    # write
  python3 scripts/montana_payload_prospects_load.py --selftest # offline data-quality eval

De-dupe: pages the FULL companies/contacts tables (PostgREST caps responses at 1000 rows).
Companies match on normalized name; contacts on email, else normalized name + org. Existing
rows are never overwritten: tags are unioned and one provenance line is appended to notes.

Flag: payload prospects get tags payload / BLK3-payload / payload-prospect /
montana-payload-prospect / fly-exos-2027 / montana-t<N>. T3 gov/defense orgs are relationship
targets, NOT payload prospects, and get montana-relationship-target instead. Nothing is written
to mission-control/data/payload-customers.json — that registry is PAYING customers only.
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "config", "montana-payload-prospects.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
AGENT = "montana-payload-prospects-load-exo3"
OWNER = "John Quinn"
COMMON = ["montana-spaceport-2026-09-30", "bd-013", "exo3"]
PAYLOAD = ["payload", "BLK3-payload", "payload-prospect", "montana-payload-prospect", "fly-exos-2027"]
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

sys.path.insert(0, os.path.join(WS, "scripts"))
try:
    from fleet_log import event as fleet_event, new_corr
except Exception:
    fleet_event, new_corr = None, (lambda: "nocorr")


def key():
    return json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]


def sb(method, q, body=None):
    k = key()
    req = urllib.request.Request(SB + q, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json",
                                          "Prefer": "return=representation"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def page(table, select):
    rows, off = [], 0
    while True:
        chunk = sb("GET", f"/{table}?select={select}&order=id&limit=1000&offset={off}")
        rows += chunk
        if len(chunk) < 1000:
            return rows
        off += 1000


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def name_key(s):
    s = re.sub(r"^(dr\.?|prof\.?|col\.?|ltc|msgt|brig\.? gen\.?)\s+", "", (s or "").strip(), flags=re.I)
    s = re.sub(r",.*$", "", s)                      # drop ", Ph.D., PE"
    s = re.sub(r"\s*\(.*?\)\s*", " ", s)            # drop "(Trent)"
    parts = s.split()
    return norm(parts[0] + parts[-1]) if len(parts) >= 2 else norm(s)


def tags_for(org):
    t = COMMON + [f"montana-{org['tier'].lower()}"]
    t += PAYLOAD if org["payload_prospect"] else ["montana-relationship-target"]
    return t


def plan(data, companies, contacts):
    co_by = {norm(c["name"]): c for c in companies}
    ct_by_email = {(c.get("email") or "").lower(): c for c in contacts if c.get("email")}
    ct_by_name = {}
    for c in contacts:
        ct_by_name.setdefault(name_key(c.get("name")), []).append(c)
    ops = []
    for o in data["orgs"]:
        tags = tags_for(o)
        desc = f"{o['what_they_do']}\n\nFit: {o['fit_note']}\nCSL: {o['csl']}. Source: {data['source']} (verified {data['verified']})."
        co = co_by.get(norm(o["name"]))
        if co:
            ops.append(("merge_company", co, {"tags": sorted(set((co.get("tags") or []) + tags))}, o))
        else:
            ops.append(("insert_company", None, {
                "name": o["name"], "website": o["website"] or None, "industry": "Payload prospect — " + o["tier_label"].split("— ")[-1] if o["payload_prospect"] else "Gov/Defense relationship (Montana)",
                "tier": o["tier_label"], "status": "Prospect", "owner": OWNER, "description": desc, "tags": tags,
                "address": o["city"] or None}, o))
        for c in o["contacts"]:
            ctags = tags + (["verified-poc"] + (["email-not-public"] if not c["email"] else []))
            note = (f"[{data['source']}] {c['title']} — verified {c['verified_date']} via {c['source_url']}. "
                    f"{c.get('evidence', '')}".strip() + ("" if c["email"] else " Email not public."))
            hit = ct_by_email.get(c["email"].lower()) if c["email"] else None
            if not hit:
                cands = [x for x in ct_by_name.get(name_key(c["name"]), []) if not x.get("email") or not c["email"] or x["email"].lower() == c["email"].lower()]
                orgk = norm(o["name"])[:10]
                cands = [x for x in cands if norm(x.get("organization"))[:6] and (norm(x.get("organization"))[:10] in norm(o["research_name"]) or orgk[:6] in norm(x.get("organization")))]
                hit = cands[0] if cands else None
            if hit:
                patch = {"tags": sorted(set((hit.get("tags") or []) + ctags)),
                         "notes": ((hit.get("notes") or "") + "\n" + note).strip()}
                if not hit.get("email") and c["email"]:
                    patch["email"] = c["email"]
                if not hit.get("title"):
                    patch["title"] = c["title"]
                if data["source"] in (hit.get("notes") or ""):
                    patch.pop("notes")                  # idempotent re-run
                ops.append(("merge_contact", hit, patch, c))
            else:
                ops.append(("insert_contact", None, {
                    "name": c["name"], "email": c["email"] or None, "phone": c["phone"] or None, "organization": o["name"],
                    "title": c["title"], "type": "Payload Prospect" if o["payload_prospect"] else "Government",
                    "stage": "Research", "status": "Active", "tier": o["tier_label"], "owner": OWNER,
                    "source": data["source"], "tags": ctags, "notes": note, "_org": o["name"]}, c))
    return ops


def run(apply):
    corr = new_corr()
    data = json.load(open(DATA))
    companies = page("companies", "id,name,tags")
    contacts = page("contacts", "id,name,email,organization,title,tags,notes")
    print(f"CRM paged: {len(companies)} companies, {len(contacts)} contacts")
    ops = plan(data, companies, contacts)
    for kind, row, body, _ in ops:
        label = body.get("name") or (row or {}).get("name")
        print(f"  {kind:15} {label}{'  (existing id ' + str(row['id']) + ')' if row else ''}")
    counts = {k: sum(1 for o in ops if o[0] == k) for k in ("insert_company", "merge_company", "insert_contact", "merge_contact")}
    print(counts)
    if not apply:
        print("DRY-RUN — nothing written. Re-run with --apply.")
        return 0
    co_ids = {}
    for kind, row, body, o in ops:
        if kind == "insert_company":
            co_ids[body["name"]] = sb("POST", "/companies", body)[0]["id"]
        elif kind == "merge_company":
            sb("PATCH", f"/companies?id=eq.{row['id']}", body); co_ids[o["name"]] = row["id"]
    for kind, row, body, c in ops:
        if kind == "insert_contact":
            org = body.pop("_org")
            body["company_id"] = co_ids.get(org)
            sb("POST", "/contacts", body)
        elif kind == "merge_contact":
            sb("PATCH", f"/contacts?id=eq.{row['id']}", body)
    if fleet_event:
        fleet_event(AGENT, "orchestrate", "crm_load", corr=corr, owner=OWNER, outcome="ok", detail=counts)
    print(f"APPLIED (corr {corr}).")
    return 0


def selftest():
    d = json.load(open(DATA))
    res = []
    ck = lambda n, ok: res.append((n, bool(ok)))
    cs = [c for o in d["orgs"] for c in o["contacts"]]
    ck("every contact has a source URL + verified date", all(c["source_url"].startswith("http") and c["verified_date"] for c in cs))
    ck("every email is well-formed or blank+noted", all((EMAIL_RE.match(c["email"]) if c["email"] else c["email_note"] == "email not public") for c in cs))
    ck("no aggregator-only sources (theorg/zoominfo/rocketreach)", not any(re.search(r"theorg|zoominfo|rocketreach|inknowvation", c["source_url"]) for c in cs))
    ck("T3 orgs are NOT flagged payload prospects", all(not o["payload_prospect"] for o in d["orgs"] if o["tier"] == "T3"))
    ck("every org CSL-screened", all(o["csl"].startswith("clear") for o in d["orgs"]))
    ck("dropped orgs carry a reason", all(x["reason"] for x in d["dropped_orgs"]))
    ck("payload-customers.json untouched by design", "payload-customers" not in open(__file__).read().split("def plan")[1].split("def selftest")[0])
    ck("name_key normalizes titles", name_key("Brock J. LaMeres, Ph.D., PE") == name_key("Brock LaMeres") and name_key("Dr. Peter Roos") == "peterroos")
    fake = {"orgs": [d["orgs"][0]], "source": d["source"], "verified": d["verified"]}
    c0 = d["orgs"][0]["contacts"][0]
    ops = plan(fake, [{"id": "x", "name": d["orgs"][0]["name"], "tags": ["a"]}], [{"id": "y", "name": c0["name"], "email": c0["email"], "organization": "", "tags": None, "notes": ""}])
    ck("dedupe: existing company merges, not inserts", ops[0][0] == "merge_company" and "a" in ops[0][2]["tags"])
    ck("dedupe: existing contact (by email) merges", any(o[0] == "merge_contact" and o[1]["id"] == "y" for o in ops))
    for n, ok in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"selftest: {sum(ok for _, ok in res)}/{len(res)} passed")
    return 0 if all(ok for _, ok in res) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else run(a.apply))
