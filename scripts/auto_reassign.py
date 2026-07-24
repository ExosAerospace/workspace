#!/usr/bin/env python3
"""auto_reassign.py — route open tasks to their domain experience lead.

Companion to schedule_due_dates.py. The scheduler dates the backlog; this offloads it
from Jon onto the person who actually owns each domain, so the calendar isn't a wall of
one name (see North Star: 478/784 open tasks were Jon's).

Definition source: mission-control/data/domain-leads.json (category -> lead+email).
GATE: a category is only reassigned when its entry has confirmed=true — that flag is the
"domain experience lead defined based on employee inputs" switch. Nothing moves until an
operator (or the named lead) confirms.

Guardrails:
  - Only pulls tasks currently owned by Jon or unassigned. Never steals a task already
    owned by another named person.
  - Never touches Series A / Government (locked to Jon) beyond keeping them there.
  - Skips a task whose title/description explicitly names a different assignee.
  - Reassigning sets owner + assigned_to + assigned_email, which the existing
    assignment-notifier (launchd, 5m) emails to the new owner — intended, but the reason
    it stays gated behind confirmed=true.

Dry-run by default; --apply writes + snapshots for rollback.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import os, sys, json, re, urllib.request
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
LEADS_FILE = os.path.join(WS, "mission-control/data/domain-leads.json")
DONE = {"Done", "Completed", "Closed", "Archived", "Cancelled"}
JON = {"jon", "john quinn", "jon quinn", "jquinn", "jon+exo", "", "(unassigned)", None}

def _key():
    return json.load(open(SECRETS))["supabase_service_role_key"]

def q_all(select):
    k = _key(); out = []; off = 0
    while True:
        req = urllib.request.Request(f"{SB}/tasks?select={select}&order=id&offset={off}&limit=1000",
                                     headers={"apikey": k, "Authorization": f"Bearer {k}"})
        c = json.load(urllib.request.urlopen(req, timeout=60)); out += c
        if len(c) < 1000: return out
        off += 1000

def patch(tid, fields):
    k = _key()
    req = urllib.request.Request(f"{SB}/tasks?id=eq.{tid}", data=json.dumps(fields).encode(),
        headers={"apikey": k, "Authorization": f"Bearer {k}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()

def main():
    apply = "--apply" in sys.argv
    cfg = json.load(open(LEADS_FILE))
    leads = cfg.get("leads", {})
    active = {c: v for c, v in leads.items()
              if v.get("confirmed") and v.get("email") and (v["email"] != "jquinn@exosaero.com")}
    if not active:
        print("No confirmed non-Jon domain leads yet — nothing to reassign. "
              "Set confirmed=true on a category in domain-leads.json to enable.")
        return

    tasks = q_all("id,title,owner,state,category,description,assigned_email")
    plan = []
    for t in tasks:
        if (t.get("state") or "") in DONE:
            continue
        cat = t.get("category") or "General"
        L = active.get(cat)
        if not L:
            continue
        owner_norm = (t.get("owner") or "").strip().lower()
        if owner_norm not in JON:
            continue  # already owned by someone specific
        blob = f"{t.get('title','')} {t.get('description','')}".lower()
        # skip if it explicitly names a different person as assignee
        if re.search(r"assignee[:\s]", blob) and L["lead"].split()[0].lower() not in blob:
            continue
        plan.append((t, L))

    print(f"Confirmed domains: {', '.join(active)}")
    print(f"Reassignable open tasks (from Jon/unassigned): {len(plan)}")
    from collections import Counter
    by = Counter(f"{L['lead']} ({t.get('category')})" for t, L in plan)
    for k, n in by.most_common():
        print(f"  -> {k}: {n}")

    if not apply:
        print("\nDRY RUN — re-run with --apply to write (this WILL notify new owners).")
        for t, L in plan[:10]:
            print(f"  #{t['id']} [{t.get('category')}] {(t.get('title') or '')[:55]}  ->  {L['lead']}")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snap = [{"id": t["id"], "prev_owner": t.get("owner"), "prev_email": t.get("assigned_email")}
            for t, _ in plan]
    p = os.path.join(WS, "mission-control/data", f"reassign-snapshot-{stamp}.json")
    json.dump(snap, open(p, "w"), indent=2)
    print(f"\nSnapshot: {p}")
    ok = err = 0
    for t, L in plan:
        try:
            patch(t["id"], {"owner": L["lead"], "assigned_to": L["lead"],
                            "assigned_email": L["email"]})
            ok += 1
        except Exception as e:
            err += 1; print(f"  ERR {t['id']}: {e}")
    print(f"Reassigned {ok} tasks ({err} errors).")

if __name__ == "__main__":
    main()
