#!/usr/bin/env python3
"""
recurring-tasks.py — makes Mission Control tasks recur (the capability MC lacked).

Teamwork carried recurrence rules (rrule) that MC didn't. We stamped them onto the matching
MC tasks as a tag `recur:<RRULE>` (e.g. recur:FREQ=MONTHLY). This job perpetuates them: when a
recurring task's current instance is completed (no active instance left in its family), it
creates the NEXT instance on the correct future date, same owner/assignee, still tagged recur —
so crane-truck / generator / battery / radio runs never fall through as dead one-offs again.

Idempotent: only creates a next instance when the family has NO active (To Do / In Progress)
task. Runs daily via launchd com.exos.recurring-tasks.
"""
import json, os, re, calendar, urllib.request, time
from datetime import date

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"


def _k():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def get(p):
    k = _k()
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        B + p, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=60).read())


def create(rec):
    k = _k()
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        B + "tasks", data=json.dumps(rec).encode(),
        headers={"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json",
                 "Prefer": "return=representation"}, method="POST"), timeout=30).read())[0]["id"]


def norm(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())[:50]


def add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def next_due(base, rr):
    f = (re.search(r'FREQ=(\w+)', rr) or [None, 'MONTHLY'])[1]
    iv = int((re.search(r'INTERVAL=(\d+)', rr) or [None, '1'])[1])
    today = date.today()
    d = base
    guard = 0
    while d <= today and guard < 500:
        if f == 'WEEKLY':
            d = date.fromordinal(d.toordinal() + 7 * iv)
        elif f == 'DAILY':
            d = date.fromordinal(d.toordinal() + iv)
        elif f == 'YEARLY':
            d = add_months(d, 12 * iv)
        else:  # MONTHLY (default)
            d = add_months(d, iv)
        guard += 1
    return d


def parse_date(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def main():
    tasks = get("tasks?select=id,title,state,due_date,owner,assigned_email,tags,completed_at,source&limit=5000")

    def rrule_of(t):
        for x in (t.get("tags") or []):
            if str(x).startswith("recur:"):
                return str(x)[6:]
        return None

    # families keyed by normalized title, seeded from any task carrying a recur: tag
    fam_rr = {}
    fam_meta = {}
    for t in tasks:
        rr = rrule_of(t)
        if rr:
            nt = norm(t.get("title"))
            fam_rr[nt] = rr
            fam_meta[nt] = {"title": t.get("title"), "owner": t.get("owner"),
                            "assigned_email": t.get("assigned_email"), "tags": t.get("tags")}

    from collections import defaultdict
    by = defaultdict(list)
    for t in tasks:
        by[norm(t.get("title"))].append(t)

    created = 0
    for nt, rr in fam_rr.items():
        inst = by.get(nt, [])
        active = [i for i in inst if str(i.get("state", "")).lower() not in ("done", "complete", "completed")]
        if active:
            continue  # current cycle still pending — do nothing
        # all done → create the next instance from the latest instance's due date
        latest = max(inst, key=lambda i: (parse_date(i.get("due_date")) or date(2000, 1, 1),
                                          parse_date(i.get("completed_at")) or date(2000, 1, 1)))
        base = parse_date(latest.get("due_date")) or parse_date(latest.get("completed_at")) or date.today()
        nd = next_due(base, rr)
        meta = fam_meta[nt]
        tags = [x for x in (meta.get("tags") or []) if not str(x).startswith("recur:")] + ["recur:" + rr, "recurring-auto"]
        tid = create({"title": meta["title"], "state": "To Do", "priority": 45,
                      "due_date": nd.isoformat(), "owner": meta.get("owner") or "Exo",
                      "assigned_email": meta.get("assigned_email"), "source": "recurring-auto",
                      "tags": tags,
                      "description": f"Auto-generated recurring task ({rr}). Prior instance completed."})
        created += 1
        print(f"  + #{tid} '{meta['title'][:40]}' next due {nd} ({rr})")
        time.sleep(0.05)
    print(f"recurring regenerator: {len(fam_rr)} recurring families | created {created} next-instance(s)")


if __name__ == "__main__":
    main()
