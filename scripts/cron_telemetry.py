#!/usr/bin/env python3
"""
cron_telemetry.py — mirror OpenClaw cron run history into the fleet telemetry spine
(exo3 audit THEME 3: the OpenClaw crons emitted no telemetry).

Reads the OpenClaw state DB READ-ONLY (~/.openclaw/state/openclaw.sqlite, opened mode=ro;
tables cron_jobs + cron_run_logs) and emits ONE fleet_log event per NEW finished cron run:

    agent   = registry label for the cron (cron:<slug(name)>, matched on cron_id)
    kind    = the cron's stack layer (sense|interpret|decide|orchestrate|learn|govern)
    action  = "cron_run"
    outcome = ok | failed | skipped
    level   = warn on error/timeout, else info

A per-job high-water mark (run-log seq) lives in state/cron-telemetry-state.json, so a
re-run never double-emits. On the very first pass (no state file) only runs from the last
--backfill-hours (default 24) are emitted; older history is marked seen.

Never touches the crons, the gateway or the network. Also the shared helper module for
agent_eval.py's cron checks (load_cron_jobs, cron_interval_s, score_cron).

Usage:
  cron_telemetry.py                 # one pass (launchd com.exos.cron-telemetry, every 15 min)
  cron_telemetry.py --dry-run       # print what would be emitted; no events, no state write
  cron_telemetry.py --selftest      # fixture DB, no real state touched
"""
import datetime, json, os, re, sqlite3, sys, tempfile, time

WS = "/Users/exomac/.openclaw/workspace"
DB = os.path.expanduser("~/.openclaw/state/openclaw.sqlite")
STATE = os.path.join(WS, "state", "cron-telemetry-state.json")
REGISTRY = os.path.join(WS, "mission-control", "data", "agent-registry.json")
sys.path.insert(0, os.path.join(WS, "scripts"))

LAYER_KIND = {"SENSE": "sense", "INTERPRET": "interpret", "DECIDE": "decide",
              "ORCHESTRATE": "orchestrate", "LEARN": "learn", "GOVERN": "govern"}


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:60].rstrip("-")


def connect(db=DB):
    return sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)


def load_cron_jobs(db=DB):
    """{job_id: dict} for every cron in the store (enabled or not)."""
    con = connect(db)
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "select job_id, name, enabled, schedule_kind, schedule_expr, every_ms, at, created_at_ms, "
            "last_run_at_ms, last_run_status, consecutive_errors, next_run_at_ms, delete_after_run from cron_jobs").fetchall()
        return {r["job_id"]: dict(r) for r in rows}
    finally:
        con.close()


def registry_crons(path=REGISTRY):
    """{cron_id: registry entry} for kind openclaw-cron."""
    try:
        agents = json.load(open(path)).get("agents", [])
    except Exception:
        return {}
    return {a["cron_id"]: a for a in agents if a.get("kind") == "openclaw-cron" and a.get("cron_id")}


# ---- cron schedule math (stdlib only; croniter is not installed) ----------------------------
_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


def _field(spec, lo, hi):
    out = set()
    for part in spec.split(","):
        step = 1
        if "/" in part:
            part, st = part.split("/", 1); step = int(st)
        if part in ("*", ""):
            a, b = lo, hi
        elif "-" in part:
            a, b = (int(x) for x in part.split("-", 1))
        else:
            a = int(part); b = hi if step > 1 else a
        out.update(range(a, b + 1, step))
    return out


def cron_interval_s(expr, horizon_days=62):
    """Longest gap (seconds) between consecutive fire times of a 5-field cron expression,
    scanned over horizon_days from a fixed Monday. Conservative interval for liveness."""
    f = expr.split()
    if len(f) != 5:
        return None
    mins, hrs, dom, mon, dow = (_field(x, *r) for x, r in zip(f, _RANGES))
    dow = {0 if d == 7 else d for d in dow}
    dom_any, dow_any = f[2] == "*", f[4] == "*"
    start = datetime.datetime(2026, 1, 5)  # a Monday
    fires = []
    for day in range(horizon_days):
        d = start + datetime.timedelta(days=day)
        if d.month not in mon:
            continue
        dm, dw = d.day in dom, (d.isoweekday() % 7) in dow
        ok = (dm and dw) if (dom_any or dow_any) else (dm or dw)
        if not ok:
            continue
        for h in sorted(hrs):
            for m in sorted(mins):
                fires.append(d + datetime.timedelta(hours=h, minutes=m))
    if len(fires) < 2:
        return horizon_days * 86400
    return int(max((b - a).total_seconds() for a, b in zip(fires, fires[1:])))


def job_interval_s(job):
    k = job.get("schedule_kind")
    if k == "every":
        return int((job.get("every_ms") or 0) / 1000) or None
    if k == "cron" and job.get("schedule_expr"):
        return cron_interval_s(job["schedule_expr"])
    return None  # one-shot 'at'


def _at_ms(job):
    try:
        return datetime.datetime.fromisoformat(job["at"].replace("Z", "+00:00")).timestamp() * 1000
    except Exception:
        return None


def score_cron(job, th, now_s):
    """(status, [why]) for one cron. th: agent-evals entry (warn_grace, fail_consecutive_errors,
    cadence_s). Disabled -> SKIP. FAIL on consecutive errors (reliable signal); WARN on staleness."""
    if not job.get("enabled"):
        return "SKIP", ["disabled"]
    why, status = [], "OK"
    ce = job.get("consecutive_errors") or 0
    if ce >= th.get("fail_consecutive_errors", 2):
        status = "FAIL"; why.append("consecutive_errors=%d (last: %s)" % (ce, job.get("last_run_status")))
    last = job.get("last_run_at_ms")
    if job.get("schedule_kind") == "at":
        due = _at_ms(job)
        if status == "OK" and due and not last and now_s * 1000 > due + 86400 * 1000:
            status = "WARN"; why.append("one-shot still unrun >24h after due")
        return status, why
    cad = th.get("cadence_s") or job_interval_s(job)
    if status == "OK" and cad:
        ref = last or job.get("created_at_ms")
        age = now_s - (ref or 0) / 1000
        if age > cad * th.get("warn_grace", 2.5):
            status = "WARN"
            why.append(("no run for %.0fh" % (age / 3600)) + (" (never ran)" if not last else "")
                       + "; limit %.0fh" % (cad * th.get("warn_grace", 2.5) / 3600))
    return status, why


# ---- telemetry pass --------------------------------------------------------------------------
def load_state(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".cron-telemetry.")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def run_pass(db=DB, state_path=STATE, registry_path=REGISTRY, emit=None, dry=False,
             backfill_hours=24, now_s=None):
    """Emit one event per new finished run. Returns number of run events emitted."""
    now_s = now_s or time.time()
    if emit is None:
        import fleet_log
        emit = fleet_log.event
    first = not os.path.exists(state_path)
    state = load_state(state_path)
    hwm = state.get("hwm", {})
    reg = registry_crons(registry_path)
    jobs = load_cron_jobs(db)
    con = connect(db)
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "select job_id, seq, ts, status, error, duration_ms, model, provider, run_id, "
            "delivery_status, total_tokens from cron_run_logs order by ts asc, seq asc").fetchall()
    finally:
        con.close()
    cutoff_ms = (now_s - backfill_hours * 3600) * 1000
    n = 0
    for r in rows:
        jid, seq = r["job_id"], r["seq"]
        if seq <= hwm.get(jid, -1):
            continue
        hwm[jid] = seq
        if first and r["ts"] < cutoff_ms:
            continue  # first pass: older history is baseline, not news
        ent = reg.get(jid) or {}
        job = jobs.get(jid) or {}
        label = ent.get("label") or ("cron:" + (slug(job.get("name")) or jid))
        layer = str(ent.get("stack_layer") or "ORCHESTRATE").split("/")[0].strip().upper()
        st = (r["status"] or "unknown").lower()
        err = r["error"] or ""
        timeout = "timeout" in err.lower() or "timed out" in err.lower() or st == "timeout"
        outcome = {"ok": "ok", "error": "failed", "timeout": "failed", "skipped": "skipped"}.get(st, st)
        level = "warn" if (outcome == "failed" or timeout) else "info"
        detail = {"cron_id": jid, "cron_name": job.get("name"), "seq": seq, "run_id": r["run_id"],
                  "run_at": datetime.datetime.fromtimestamp(r["ts"] / 1000, datetime.timezone.utc).isoformat(),
                  "status": st, "duration_ms": r["duration_ms"], "model": r["model"],
                  "delivery_status": r["delivery_status"], "total_tokens": r["total_tokens"],
                  "registered": bool(ent)}
        if err:
            detail["error"] = err[:300]
        if dry:
            print("would emit", label, outcome, level, detail["run_at"])
        else:
            emit(label, LAYER_KIND.get(layer, "orchestrate"), "cron_run", outcome=outcome, level=level,
                 owner=ent.get("human_owner"), detail=detail)
        n += 1
    if not dry:
        state.update({"hwm": hwm, "last_pass": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                      "last_emitted": n})
        save_state(state_path, state)
    return n


# ---- selftest --------------------------------------------------------------------------------
def selftest():
    import shutil
    d = tempfile.mkdtemp(prefix="cron-telemetry-selftest.")
    try:
        db, sp, rp = (os.path.join(d, x) for x in ("t.sqlite", "state.json", "reg.json"))
        con = sqlite3.connect(db)
        con.execute("create table cron_jobs (job_id text, name text, enabled int, schedule_kind text, "
                    "schedule_expr text, every_ms int, at text, created_at_ms int, last_run_at_ms int, "
                    "last_run_status text, consecutive_errors int, next_run_at_ms int, delete_after_run int default 0)")
        con.execute("create table cron_run_logs (store_key text, job_id text, seq int, ts int, status text, "
                    "error text, duration_ms int, model text, provider text, run_id text, delivery_status text, "
                    "total_tokens int)")
        now = 1790700000.0
        H = 3600 * 1000
        con.execute("insert into cron_jobs values ('j1','Fixture Daily Watch',1,'cron','0 9 * * *',null,null,0,?, 'ok',0,null,0)",
                    (int(now * 1000 - H),))
        con.execute("insert into cron_jobs values ('j2','Fixture Unregistered',1,'every',null,3600000,null,0,null,null,0,null,0)")
        runs = [("j1", 1, now * 1000 - 72 * H, "ok", None), ("j1", 2, now * 1000 - 2 * H, "error", "Error: job timed out"),
                ("j2", 1, now * 1000 - 1 * H, "ok", None)]
        for jid, seq, ts, st, err in runs:
            con.execute("insert into cron_run_logs values ('k',?,?,?,?,?,1000,'m','p','r',null,5)", (jid, seq, int(ts), st, err))
        con.commit(); con.close()
        json.dump({"agents": [{"label": "cron:fixture-daily-watch", "kind": "openclaw-cron", "cron_id": "j1",
                               "stack_layer": "SENSE", "human_owner": "Fixture Owner"}]}, open(rp, "w"))
        got = []
        emit = lambda *a, **k: got.append((a, k))
        ok = 0

        def check(cond, name):
            nonlocal ok
            assert cond, name
            ok += 1
        # 1 first pass: 72h-old run is baseline, 2 recent runs emitted
        check(run_pass(db, sp, rp, emit=emit, backfill_hours=24, now_s=now) == 2, "first pass emits recent only")
        # 2 error/timeout -> failed + warn, kind from layer, registered label + owner
        a, k = got[0]
        check(a[0] == "cron:fixture-daily-watch" and a[1] == "sense" and k["outcome"] == "failed"
              and k["level"] == "warn" and k["owner"] == "Fixture Owner", "error run -> failed/warn")
        # 3 unregistered job falls back to cron:<slug(name)>, info level
        check(got[1][0][0] == "cron:fixture-unregistered" and got[1][1]["level"] == "info", "unregistered label fallback")
        # 4 re-run emits nothing (high-water mark)
        check(run_pass(db, sp, rp, emit=emit, now_s=now) == 0, "dedupe on re-run")
        # 5 a new run is emitted exactly once
        con = sqlite3.connect(db)
        con.execute("insert into cron_run_logs values ('k','j1',3,?,'ok',null,1,'m','p','r',null,1)", (int(now * 1000),))
        con.commit(); con.close()
        check(run_pass(db, sp, rp, emit=emit, now_s=now) == 1 and got[-1][1]["outcome"] == "ok", "new run emitted once")
        # 6 interval math
        check(cron_interval_s("0 9 * * *") == 86400, "daily interval")
        check(cron_interval_s("0 12 * * 2") == 7 * 86400, "weekly interval")
        check(cron_interval_s("0 1 * * 1-5") == 3 * 86400, "weekday interval (Fri->Mon)")
        check(cron_interval_s("0 21 2-30/2 * *") == 3 * 86400, "every-other-day wraps month")
        check(25 * 86400 <= cron_interval_s("0 18 28-31 * *") <= 29 * 86400, "month-end interval")
        # 7 scoring
        th = {"warn_grace": 2.5, "fail_consecutive_errors": 2}
        j = {"enabled": 1, "schedule_kind": "cron", "schedule_expr": "0 9 * * *", "consecutive_errors": 0,
             "last_run_at_ms": (now - 3600) * 1000}
        check(score_cron(j, th, now)[0] == "OK", "fresh daily OK")
        check(score_cron(dict(j, last_run_at_ms=(now - 3 * 86400) * 1000), th, now)[0] == "WARN", "stale daily WARN")
        check(score_cron(dict(j, consecutive_errors=2), th, now)[0] == "FAIL", "2 consecutive errors FAIL")
        check(score_cron(dict(j, consecutive_errors=1), th, now)[0] == "OK", "1 error not FAIL")
        check(score_cron(dict(j, enabled=0), th, now)[0] == "SKIP", "disabled SKIP")
        at = {"enabled": 1, "schedule_kind": "at", "at": "2026-01-01T00:00:00Z", "consecutive_errors": 0}
        check(score_cron(at, th, now)[0] == "WARN", "overdue unrun one-shot WARN")
        check(score_cron(dict(at, at="2099-01-01T00:00:00Z"), th, now)[0] == "OK", "future one-shot OK")
        print("cron_telemetry selftest: %d/%d pass" % (ok, ok))
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    dry = "--dry-run" in sys.argv
    bf = 24
    if "--backfill-hours" in sys.argv:
        bf = float(sys.argv[sys.argv.index("--backfill-hours") + 1])
    n = run_pass(dry=dry, backfill_hours=bf)
    msg = "cron_telemetry: %d run event(s) %s" % (n, "(dry-run)" if dry else "emitted")
    print(datetime.datetime.now().isoformat(timespec="seconds"), msg)
    if not dry:
        try:
            import fleet_log
            fleet_log.event("cron_telemetry", "govern", "pass", outcome="ok", owner="Exo (infra) / John Quinn",
                            detail={"emitted": n})
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
