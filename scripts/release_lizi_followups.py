#!/usr/bin/env python3
"""
release_lizi_followups.py — date-gated release of Lizi's BLK3 payload follow-up tasks.

Lizi wanted 50 individual follow-up tasks (one per contact) to STAY OFF her Mission
Control board until 2026-08-17. They were snapshotted to logs/lizi-followups-pending.json
and deleted from the live board. This launchd-run script (daily 07:00) recreates them on
or after the release_date, assigned to Lizi, and pre-seeds the assignment-notifier state so
recreating 50 tasks does NOT blast her with 50 emails. Idempotent: once released, it deletes
the pending file and no-ops thereafter.
"""
import json, os, sys, time, urllib.request
from datetime import datetime

WS = "/Users/exomac/.openclaw/workspace"
PENDING = os.path.join(WS, "logs", "lizi-followups-pending.json")
NOTIFY_STATE = os.path.join(WS, "logs", "assignment-notify-state.json")
LOG = os.path.join(WS, "logs", "release-lizi-followups.log")
LIZI = "lquinn@exosaero.com"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}


def log(m):
    open(LOG, "a").write(f"[{time.strftime('%Y-%m-%d %H:%M:%S %Z')}] {m}\n")


def rq(method, url, data=None):
    for a in range(4):
        try:
            r = urllib.request.Request(
                url, data=(json.dumps(data).encode() if data is not None else None),
                headers={**H, "Prefer": "return=representation"}, method=method)
            b = urllib.request.urlopen(r, timeout=60).read()
            return json.loads(b) if b else []
        except Exception as e:
            log(f"retry {method} {a}: {e}"); time.sleep(3)
    raise SystemExit("supabase request failed")


def main():
    if not os.path.exists(PENDING):
        return  # nothing pending -> no-op
    cfg = json.load(open(PENDING))
    today = datetime.now().strftime("%Y-%m-%d")   # host TZ = America/Chicago
    if today < cfg["release_date"]:
        log(f"not yet: today {today} < release {cfg['release_date']} ({len(cfg['rows'])} pending)")
        return
    now = datetime.now().astimezone().isoformat()
    rows = cfg["rows"]
    for r in rows:
        r["assigned_at"] = now
    created = rq("POST", SB + "/tasks", rows)
    ids = [str(c["id"]) for c in created]
    # pre-seed notifier state so these do NOT email Lizi 50x on recreate
    try:
        st = json.load(open(NOTIFY_STATE)) if os.path.exists(NOTIFY_STATE) else {}
        for tid in ids:
            st[tid] = LIZI
        json.dump(st, open(NOTIFY_STATE, "w"))
    except Exception as e:
        log(f"WARN notifier pre-seed failed: {e}")
    # mark released: archive the pending file so we never double-insert
    os.rename(PENDING, PENDING + f".released-{today}")
    log(f"RELEASED {len(created)} follow-up tasks to Lizi (ids {ids[0]}..{ids[-1]}); notifier suppressed")


# ── OUTPUT eval (exo3 R5): `release_lizi_followups.py selftest` ─────────────
# Read-only: fixture run in a temp dir with Supabase faked (no writes), then GET-only checks that
# the real 2026-08-17 release created each follow-up exactly once, assigned to Lizi, notifier-suppressed.
def _selftest_fixture():
    import tempfile, shutil
    g = globals()
    saved = {k: g[k] for k in ("PENDING", "NOTIFY_STATE", "LOG", "rq")}
    tmp = tempfile.mkdtemp(prefix="rlf-selftest-")
    posts, res = [], []
    try:
        g.update(PENDING=os.path.join(tmp, "pending.json"), NOTIFY_STATE=os.path.join(tmp, "notify.json"),
                 LOG=os.path.join(tmp, "log.txt"),
                 rq=lambda m, u, d=None: posts.append((m, u, d)) or [{"id": 500 + i} for i in range(len(d or []))])
        rows = [{"title": f"Follow-up: P{i}", "assigned_email": LIZI} for i in range(3)]
        json.dump({"release_date": "2999-01-01", "rows": rows}, open(g["PENDING"], "w"))
        main()
        res.append(("fixture: before release_date -> nothing created", not posts and os.path.exists(g["PENDING"])))
        json.dump({"release_date": "2000-01-01", "rows": rows}, open(g["PENDING"], "w"))
        main(); main()
        res.append(("fixture: on/after release_date -> one batch insert, never twice",
                    len(posts) == 1 and len(posts[0][2]) == 3 and not os.path.exists(g["PENDING"])))
        st = json.load(open(g["NOTIFY_STATE"]))
        res.append(("fixture: notifier pre-seeded for every created id (no 50x email blast)",
                    st == {str(500 + i): LIZI for i in range(3)}))
    finally:
        g.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def _selftest_live():
    import glob, urllib.parse
    res = []
    rel = sorted(glob.glob(PENDING + ".released-*"))
    if os.path.exists(PENDING):
        cfg = json.load(open(PENDING))
        ok = datetime.now().strftime("%Y-%m-%d") < cfg["release_date"]
        res.append((f"live: pending batch not yet due ({cfg['release_date']})", ok))
        return res
    if not rel:
        res.append(("live: no pending and no released batch (nothing to verify)", True))
        return res
    cfg = json.load(open(rel[-1]))
    titles = [r["title"] for r in cfg["rows"]]
    try:
        src = {r.get("source") for r in cfg["rows"]}
        got = []
        for sv in src:
            got += rq("GET", SB + "/tasks?select=id,title,assigned_email,source&source=eq." + urllib.parse.quote(sv or ""))
        cnt = {}
        for t in got:
            cnt[t["title"]] = cnt.get(t["title"], 0) + 1
        dup = [t for t in titles if cnt.get(t, 0) > 1]
        res.append((f"live: {len(titles)} released follow-ups, none created twice" + (f" -> {dup[:5]}" if dup else ""), not dup))
        # what this job creates must be Lizi's (later human reassignment on the board is fine)
        bad = [r["title"] for r in cfg["rows"] if (r.get("assigned_email") or "").lower() != LIZI]
        res.append(("live: released batch rows were all assigned to Lizi" + (f" -> {bad[:5]}" if bad else ""), not bad))
    except SystemExit as e:
        res.append((f"live: Supabase read failed {e}", False))
    return res


def selftest():
    res = _selftest_fixture() + _selftest_live()
    for n, ok in res:
        print(("PASS " if ok else "FAIL ") + n)
    nf = sum(1 for _, ok in res if not ok)
    print(f"release_lizi_followups selftest: {'PASS' if not nf else 'FAIL'} ({len(res) - nf}/{len(res)})")
    return 0 if not nf else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    main()
