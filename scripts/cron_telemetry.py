#!/usr/bin/env python3
"""
cron_telemetry.py — mirror OpenClaw cron run history into the fleet telemetry spine
(exo3 audit THEME 3: the OpenClaw crons emitted no telemetry).

Reads the OpenClaw state DB READ-ONLY (~/.openclaw/state/openclaw.sqlite, opened mode=ro;
tables cron_jobs + cron_run_logs, or cron_run_receipts on OpenClaw >= 2026.9.7) and emits ONE fleet_log event per NEW finished cron run:

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


# ---- store schema adapter ------------------------------------------------------------------
# OpenClaw 2026.9.7 (installed 2026-10-01 ~11:00 CDT) moved cron_jobs' flat columns into job_json /
# state_json and replaced cron_run_logs with cron_run_receipts. Every exo3 cron check went blind
# ("no such column: schedule_kind"). These helpers return rows with the LEGACY column names from
# either schema, so callers (agent_eval, cron_hygiene, cron_prompt_guard) don't care which is live.
JOB_KEYS = ("job_id", "name", "enabled", "schedule_kind", "schedule_expr", "every_ms", "at", "created_at_ms",
            "last_run_at_ms", "last_run_status", "consecutive_errors", "next_run_at_ms", "delete_after_run")


def _columns(con, table):
    return {r[1] for r in con.execute("pragma table_info(%s)" % table)}


def _tables(con):
    return {r[0] for r in con.execute("select name from sqlite_master where type in ('table','view')")}


def job_rows(con):
    """[dict] one per cron, legacy column names + payload_kind/model/tools_allow_json/message, agent_id,
    declaration_key (system-declared jobs, e.g. heartbeat:main) and the raw job_json."""
    if "state_json" not in _columns(con, "cron_jobs"):         # legacy flat schema
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute("select * from cron_jobs")]
        finally:
            con.row_factory = None
    out = []
    for jid, name, en, agent, pk, decl, jj, sj in con.execute(
            "select job_id, name, enabled, agent_id, payload_kind, declaration_key, job_json, state_json from cron_jobs"):
        try: j = json.loads(jj or "{}")
        except Exception: j = {}
        try: st = json.loads(sj or "{}")
        except Exception: st = {}
        sch, pl = j.get("schedule") or {}, j.get("payload") or {}
        out.append({
            "job_id": jid, "name": name, "enabled": en, "agent_id": agent or j.get("agentId"),
            "declaration_key": decl or j.get("declarationKey"),
            "schedule_kind": sch.get("kind"), "schedule_expr": sch.get("expr"), "every_ms": sch.get("everyMs"),
            "at": sch.get("at"), "created_at_ms": j.get("createdAtMs"),
            "last_run_at_ms": st.get("lastRunAtMs"), "last_run_status": st.get("lastRunStatus") or st.get("lastStatus"),
            "consecutive_errors": st.get("consecutiveErrors") or 0, "next_run_at_ms": st.get("nextRunAtMs"),
            "delete_after_run": int(bool(j.get("deleteAfterRun"))),
            "payload_kind": pk or pl.get("kind"), "payload_model": pl.get("model"),
            "payload_tools_allow_json": json.dumps(pl["toolsAllow"]) if "toolsAllow" in pl else None,
            "payload_message": pl.get("message") or pl.get("text"), "job_json": jj})
    return out


def run_rows(con):
    """[dict] finished runs, legacy cron_run_logs names. On the receipts schema seq = finished_at_ms
    (monotonic per job; any legacy small-int high-water mark is below it, so nothing is lost)."""
    if "cron_run_logs" in _tables(con):
        q = ("select job_id, seq, ts, status, error, duration_ms, model, provider, run_id, "
             "delivery_status, total_tokens from cron_run_logs order by ts asc, seq asc")
    else:
        q = ("select job_id, finished_at_ms as seq, finished_at_ms as ts, status, error_text as error, "
             "finished_at_ms - started_at_ms as duration_ms, null as model, null as provider, "
             "coalesce(request_run_id, receipt_id) as run_id, null as delivery_status, null as total_tokens "
             "from cron_run_receipts where status != 'running' order by finished_at_ms asc, receipt_id asc")
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(q)]
    finally:
        con.row_factory = None


def load_cron_jobs_full(db=DB):
    """{job_id: row} with every adapter field (incl. job_json / payload_message)."""
    con = connect(db)
    try:
        return {r["job_id"]: r for r in job_rows(con)}
    finally:
        con.close()


def load_cron_jobs(db=DB):
    """{job_id: dict} for every cron in the store (enabled or not)."""
    extra = ("agent_id", "declaration_key", "payload_kind")
    return {jid: {k: r.get(k) for k in JOB_KEYS + extra} for jid, r in load_cron_jobs_full(db).items()}


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
        rows = run_rows(con)
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
        if job.get("payload_kind") == "heartbeat":
            continue  # platform heartbeat ticks (2026.9.7 stores them as cron rows) are not agent runs
        label = ent.get("label") or ("cron:" + (slug(job.get("name")) or jid))
        layer = str(ent.get("stack_layer") or "ORCHESTRATE").split("/")[0].strip().upper()
        st = (r["status"] or "unknown").lower()
        err = r["error"] or ""
        timeout = "timeout" in err.lower() or "timed out" in err.lower() or st == "timeout"
        outcome = {"ok": "ok", "error": "failed", "timeout": "failed", "skipped": "skipped",
                   "interrupted": "failed", "superseded": "skipped"}.get(st, st)
        level = "warn" if (outcome == "failed" or timeout) else "info"
        detail = {"cron_id": jid, "cron_name": job.get("name"), "seq": seq, "run_id": r["run_id"],
                  "run_at": datetime.datetime.fromtimestamp(r["ts"] / 1000, datetime.timezone.utc).isoformat(),
                  "status": st, "duration_ms": r["duration_ms"], "model": r["model"],
                  "delivery_status": r["delivery_status"], "total_tokens": r["total_tokens"],
                  "registered": bool(ent)}
        if job.get("declaration_key"):
            detail["system_declared"] = job["declaration_key"]
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
        # 8 OpenClaw 2026.9.7 receipts schema (job_json/state_json + cron_run_receipts)
        db2, sp2 = os.path.join(d, "v2.sqlite"), os.path.join(d, "state2.json")
        con = sqlite3.connect(db2)
        con.execute("create table cron_jobs (store_key text, job_id text, declaration_key text, owner_agent_id text, "
                    "name text, description text, enabled int, agent_id text, payload_kind text, job_json text, "
                    "state_json text default '{}', updated_at int)")
        con.execute("create table cron_run_receipts (receipt_id text, store_key text, job_id text, config_revision text, "
                    "agent_id text, request_run_id text, status text, owner_pid int, owner_start_time int, "
                    "started_at_ms int, finished_at_ms int, error_text text)")
        jj = {"id": "j1", "name": "Fixture Daily Watch", "agentId": "research-web", "createdAtMs": 0,
              "schedule": {"kind": "cron", "expr": "0 9 * * *"},
              "payload": {"kind": "agentTurn", "model": "anthropic/x", "toolsAllow": ["*"], "message": "hi"}}
        con.execute("insert into cron_jobs values ('k','j1',null,null,'Fixture Daily Watch',null,1,'research-web','agentTurn',?,?,0)",
                    (json.dumps(jj), json.dumps({"lastRunAtMs": int(now * 1000 - H), "consecutiveErrors": 2, "lastRunStatus": "error"})))
        hb = {"id": "hb", "name": "heartbeat-main", "schedule": {"kind": "every", "everyMs": 3 * H}, "payload": {"kind": "heartbeat"},
              "deleteAfterRun": False}
        con.execute("insert into cron_jobs values ('k','hb','heartbeat:main',null,'heartbeat-main',null,1,'main','heartbeat',?,'{}',0)",
                    (json.dumps(hb),))
        for rid, jid, st, fin, err in [("r1", "j1", "ok", now * 1000 - 2 * H, None), ("r2", "j1", "interrupted", now * 1000 - H, "gateway stopped"),
                                       ("r3", "hb", "skipped", now * 1000 - H, "heartbeat skipped: quiet-hours"), ("r4", "j1", "running", None, None)]:
            con.execute("insert into cron_run_receipts values (?, 'k', ?, 'c', 'a', null, ?, 1, 1, ?, ?, ?)",
                        (rid, jid, st, int((fin or now * 1000) - 1000), int(fin) if fin else None, err))
        con.commit(); con.close()
        jobs2 = load_cron_jobs(db2)
        check(jobs2["j1"]["schedule_kind"] == "cron" and jobs2["j1"]["schedule_expr"] == "0 9 * * *"
              and jobs2["j1"]["consecutive_errors"] == 2 and jobs2["j1"]["agent_id"] == "research-web", "v2 job fields from job_json/state_json")
        check(score_cron(dict(jobs2["j1"]), th, now)[0] == "FAIL", "v2 consecutive errors still FAIL")
        full = load_cron_jobs_full(db2)["j1"]
        check(full["payload_tools_allow_json"] == '["*"]' and full["payload_message"] == "hi" and full["payload_model"] == "anthropic/x",
              "v2 payload fields")
        got2 = []
        n2 = run_pass(db2, sp2, rp, emit=lambda *a, **k: got2.append((a, k)), now_s=now)
        check(n2 == 2 and [g[1]["outcome"] for g in got2] == ["ok", "failed"], "v2 receipts: finished runs only, heartbeat skipped, interrupted=failed")
        check(run_pass(db2, sp2, rp, emit=lambda *a, **k: got2.append((a, k)), now_s=now) == 0, "v2 dedupe on re-run")
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
