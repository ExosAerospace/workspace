#!/usr/bin/env python3
"""schedule_due_dates.py — assign every OPEN task a due_date inside the next 6 months.

Goal (Jon, 2026-07-23): a realistic schedule where all open work is dated to complete
within ~6 months, priority-first and load-smoothed so nothing rots undated and the
earliest weeks hold the highest-priority items.

Method
------
1. Pull all open tasks from Supabase (state not in DONE set).
2. KEEP any task already dated within the window (today+GRACE .. today+HORIZON):
   those are real, achievable dates (explicit deadlines / mission anchors) — don't stomp.
3. SCHEDULE the rest — undated, overdue, or beyond the 6-month horizon — by ranking on
   (priority desc, category weight desc, created_at asc), then packing into 26 weekly
   buckets with an even per-week cap. Highest-priority work lands in the earliest weeks;
   the backlog spreads evenly out to week 26. due_date = that week's Friday 23:59:59Z.
4. --apply PATCHes due_date via the service-role key. A pre-write snapshot of every
   changed task's prior due_date is saved for rollback.

Dry-run by default. Add --apply to write.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import os, sys, json, math, urllib.request
from datetime import datetime, timezone, timedelta, date

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
DONE = {"Done", "Completed", "Closed", "Archived", "Cancelled"}

GRACE_DAYS = 3          # don't due-date anything before today+3
HORIZON_DAYS = 182      # ~6 months
WEEKS = 26

# North-Star aligned category weights (tie-breaker after priority).
CAT_WEIGHT = {
    "series a": 100, "capital": 100, "fundraising": 100, "funding": 100,
    "revenue": 90, "payload sales": 85, "blk3 flight": 80, "bd": 75,
    "government": 70, "partnership": 65, "licensing": 60, "strategy": 55,
    "astro-x": 50, "exos admin": 30, "general": 40,
}

def _key():
    return json.load(open(SECRETS))["supabase_service_role_key"]

def q_all(select, extra=""):
    """Paginated GET of every row (past the 1000 default cap)."""
    k = _key()
    out, step, off = [], 1000, 0
    while True:
        p = f"{SB}/tasks?select={select}{extra}&order=id&offset={off}&limit={step}"
        req = urllib.request.Request(p, headers={"apikey": k, "Authorization": f"Bearer {k}"})
        chunk = json.load(urllib.request.urlopen(req, timeout=60))
        out.extend(chunk)
        if len(chunk) < step:
            return out
        off += step

def patch(task_id, fields):
    k = _key()
    req = urllib.request.Request(
        f"{SB}/tasks?id=eq.{task_id}", data=json.dumps(fields).encode(),
        headers={"apikey": k, "Authorization": f"Bearer {k}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"},
        method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()

def d10(s):
    return (s or "")[:10]

def main():
    apply = "--apply" in sys.argv
    now = datetime.now(timezone.utc)
    today = now.date()
    win_start = today + timedelta(days=GRACE_DAYS)
    win_end = today + timedelta(days=HORIZON_DAYS)

    # First Friday on/after win_start, then one Friday per week for 26 weeks.
    first_fri = win_start + timedelta(days=(4 - win_start.weekday()) % 7)
    week_fridays = [first_fri + timedelta(weeks=i) for i in range(WEEKS)]
    # keep every bucket inside the horizon
    week_fridays = [f if f <= win_end else win_end for f in week_fridays]

    tasks = q_all("id,title,owner,state,priority,due_date,category,created_at")
    opn = [t for t in tasks if (t.get("state") or "") not in DONE]

    keep, sched = [], []
    for t in opn:
        dd = d10(t.get("due_date"))
        if dd and str(win_start) <= dd <= str(win_end):
            keep.append(t)
        else:
            sched.append(t)

    def rank(t):
        return (-(t.get("priority") or 0),
                -CAT_WEIGHT.get((t.get("category") or "general").lower(), 40),
                t.get("created_at") or "")
    sched.sort(key=rank)

    cap = math.ceil(len(sched) / WEEKS) if sched else 0
    plan = []              # (task, friday)
    per_week = [0] * WEEKS
    wk = 0
    for t in sched:
        while wk < WEEKS - 1 and per_week[wk] >= cap:
            wk += 1
        per_week[wk] += 1
        plan.append((t, week_fridays[wk]))

    print(f"Open tasks: {len(opn)} | kept (already dated in window): {len(keep)} | "
          f"to schedule: {len(sched)} | per-week cap: {cap}")
    print("Weekly load (scheduled only):")
    for i, f in enumerate(week_fridays):
        if per_week[i]:
            print(f"  wk{i+1:>2} {f}  {'#'*per_week[i]} {per_week[i]}")

    if not apply:
        print("\nDRY RUN — re-run with --apply to write. Sample of first 8:")
        for t, f in plan[:8]:
            print(f"  {f} p{t.get('priority')} [{t.get('category')}] {(t.get('title') or '')[:60]}")
        return

    # snapshot for rollback
    snap = [{"id": t["id"], "prev_due_date": t.get("due_date")} for t, _ in plan]
    stamp = now.strftime("%Y%m%d-%H%M%S")
    snap_path = os.path.join(WS, "mission-control/data", f"due-date-schedule-snapshot-{stamp}.json")
    json.dump(snap, open(snap_path, "w"), indent=2)
    print(f"\nSnapshot: {snap_path}")

    ok = err = 0
    for t, f in plan:
        try:
            patch(t["id"], {"due_date": f"{f}T23:59:59Z"})
            ok += 1
        except Exception as e:
            err += 1
            print(f"  ERR {t['id']}: {e}")
    print(f"Applied {ok} due dates ({err} errors). Kept {len(keep)} existing.")

if __name__ == "__main__":
    main()
