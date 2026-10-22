#!/usr/bin/python3
"""failure_fixer_exo3.py — automatic failure → fix dispatcher for the ExoMac agent fleet.

Jon 2026-10-08: "If we have failures — launch a fix and I'll just approve the fix instead of having to
advise to fix every time there's a fail."  Every fleet failure must reach Jon WITH a fix already
launched: applied (safe/internal/reversible) or staged as ONE "Approve fix" Decision card.

Pipeline (launchd com.exos.failure-fixer-exo3, every 15 min; also invoked by fleet_status_heartbeat
right before it DMs, so a fresh failure is never shown bare):

  1. COLLECT  — reuses the existing detectors, no duplicated logic:
       • OpenClaw crons: fleet_status_heartbeat.cron_health() (state_json schema) → consecutiveErrors ≥ 2,
         details/receipts from ~/.openclaw/state/openclaw.sqlite (read-only)
       • launchd com.exos.*: fleet_status_heartbeat.launchd_bad() + logs/runs/*.jsonl stderr tails
       • quiet fails: completion-watchdog.scan_events() (governance/events.jsonl) — an agent whose LATEST
         run errored and that errored ≥2 times with the same error class in 24h, or stalled ≥2 times
     Each failure gets a stable signature  <kind>:<job>:<sha1(error-class)[:8]>.
  2. DISPATCH — one failure signature = one fix run (state: logs/failure-fixer/state.json).
       Guardrails: ≤3 fix runs/hour, one in-flight run per file set, never itself.
       A fix run = ONE headless `openclaw agent --message-file … --json` turn (the same mechanism
       task-question-answer / mc-email-command use; no cron → no toolsAllow injection trap) that
       root-causes and either APPLIES a safe internal fix (verify, scoped commit, improvement-ledger
       entry) or STAGES a patch for Jon. The worker then enforces the outcome deterministically:
       forbidden-path check (secrets/BOMs/decisions.json/migrate.js) → auto-revert + escalate,
       ledger backstop, and files the "Approve fix: <job> — <cause>" Decision via /api/decisions/ingest.
  3. EXECUTE  — when a HUMAN answers "Approve fix" on one of those cards (decisions.json read-only,
       backlog_grind_apply.human_answered): git apply the staged patch to index+worktree (only our hunks),
       run allow-listed apply commands, verify, commit, ledger entry, close-the-loop line in #exomac-system.
       Verify fails → reverse the patch, mark approved_failed. "Hold"/"Discuss" are recorded.
  4. REPORT   — fix_status_line() feeds fleet_status_heartbeat's DM ("→ fix applied (commit X)",
       "→ fix awaiting your approval: D-xxx", "→ fix in progress"); applied fixes go out as ONE daily
       digest line to #exomac-system (R-NONEWS: silent when none).

Usage:
  failure_fixer_exo3.py collect [--json] [--fixture F]
  failure_fixer_exo3.py run [--test] [--fixture F] [--dry-run]     (launchd entrypoint)
  failure_fixer_exo3.py worker --sig SIG [--test] [--apply]         (spawned per fix run)
  failure_fixer_exo3.py report --job NAME --error TEXT [--file PATH]  (manual: e.g. a misclassified alert)
  failure_fixer_exo3.py status [--json]
  failure_fixer_exo3.py --selftest                                   (eval_suite; replays the guardrails)
--test: separate state (logs/failure-fixer/test-state.json), Decisions written to
        logs/failure-fixer/test-decisions/ instead of POSTed, no Discord, agent told STAGE-ONLY.
"""
import contextlib, fcntl, glob, hashlib, importlib.util, json, os, plistlib, re, shlex, sqlite3, subprocess, sys, \
    time, urllib.request
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SCRIPTS = os.path.join(WS, "scripts")
sys.path.insert(0, SCRIPTS)
FF_DIR = os.path.join(WS, "logs", "failure-fixer")
STATE = os.path.join(FF_DIR, "state.json")
TEST_STATE = os.path.join(FF_DIR, "test-state.json")
PATCH_DIR = os.path.join(FF_DIR, "patches")
RUN_DIR = os.path.join(FF_DIR, "runs")
TEST_DEC_DIR = os.path.join(FF_DIR, "test-decisions")
LOG = os.path.join(WS, "logs", "failure-fixer-exo3.log")
DB = os.path.expanduser("~/.openclaw/state/openclaw.sqlite")
DEC_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
TOKEN_FILE = os.path.join(WS, "mission-control", "data", ".decisions-token")
MC = "http://127.0.0.1:8080"
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
SYS_CHANNEL = "channel:1501636814849577050"   # #exomac-system
AGENT_ID = "failure-fixer-exo3"
SELF_LABEL = "com.exos." + AGENT_ID
PY = "/usr/bin/python3"

MAX_RUNS_PER_HOUR = 3
MAX_EPISODES = 2            # auto fix runs per signature; a 3rd recurrence → escalation Decision only
RUN_TIMEOUT_S = 1800        # one agent turn
STALE_RUN_S = RUN_TIMEOUT_S + 900
RETRY_FAILED_RUN_S = 3600   # a CRASHED fix run (not a fix attempt) may retry once after 1h
DIGEST_HOUR = 7

# Never touched by an automatic fix (Jon / memory rules): secrets, BOMs, decisions.json, migrate.js.
FORBIDDEN = [r"(^|/)secrets?(\.json)?$", r"\.decisions-token$", r"(^|/)\.env", r"token", r"credential",
             r"(^|/)bom-index[^/]*\.json$", r"(^|/)bom-(costs|edits)", r"(^|/)bom[^/]*\.xlsx$",
             r"mission-control/data/decisions\.json$", r"(^|/)migrate\.js$", r"\.openclaw/openclaw\.json$"]
# Commands an approved card may run deterministically (anything else → agent apply run).
CMD_ALLOW = [r"^openclaw cron (edit|run|enable) [\w\-]+( |$)", r"^launchctl (kickstart|bootstrap|bootout|enable) .*com\.exos\.",
             r"^/usr/bin/python3 scripts/[\w\-]+\.py( |$)"]
CMD_DENY = r"msmtp|sendmail|smtplib|message send|git push|rm -rf|decisions\.json|migrate\.js|secrets\.json|curl .*-X ?(POST|PUT|DELETE)"

TEST = False


def now_ts():
    return time.time()


def iso(ts=None):
    return datetime.fromtimestamp(ts or now_ts(), timezone.utc).isoformat(timespec="seconds")


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{iso()} {'[TEST] ' if TEST else ''}{m}\n")


def trace(action, detail, outcome=None, corr=None, level="info"):
    try:
        import fleet_log
        return fleet_log.event(AGENT_ID, "govern", action, corr=corr, detail=detail, owner="John Quinn",
                               outcome=outcome, level=level)
    except Exception:
        return None


# ───────────────────────────── state ─────────────────────────────
def state_path():
    return TEST_STATE if TEST else STATE


@contextlib.contextmanager
def state_lock():
    os.makedirs(FF_DIR, exist_ok=True)
    with open(os.path.join(FF_DIR, ".state.lock"), "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def load_state(p=None):
    try:
        with open(p or state_path()) as f:
            return json.load(f)
    except Exception:
        return {"fixes": {}, "launches": []}


def save_state(st, p=None):
    p = p or state_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1, default=str)
    os.replace(tmp, p)   # never truncate-before-read


def update_rec(sig, **fields):
    with state_lock():
        st = load_state()
        rec = st["fixes"].setdefault(sig, {"sig": sig})
        rec.update(fields)
        save_state(st)
        return rec


# ─────────────────────────── signatures ───────────────────────────
def error_class(text):
    t = str(text or "").strip().lower()
    t = re.sub(r"'([^']{25,})'|\"([^\"]{25,})\"", "<q>", t)              # long quoted payloads vary
    t = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", t)
    t = re.sub(r"(?:/[\w.\-@]+){2,}", "<path>", t)
    t = re.sub(r"\b0x[0-9a-f]+\b|\b[0-9a-f]{7,}\b", "<hex>", t)
    t = re.sub(r"\d+(\.\d+)?", "<n>", t)
    t = re.sub(r"\s+", " ", t)
    return t[:100]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:60] or "x"


def signature(kind, ident, err):
    return f"{kind}:{slug(ident)}:{hashlib.sha1(error_class(err).encode()).hexdigest()[:8]}"


def make_failure(kind, ident, job, error, file_set=None, definition="", log_tail="", last_fail_at=None, extra=None):
    f = {"kind": kind, "ident": ident, "job": job, "error": str(error or "")[:2000],
         "error_class": error_class(error), "file_set": sorted(set(file_set or [f"{kind}:{ident}"])),
         "definition": str(definition or "")[:6000], "log_tail": str(log_tail or "")[-5000:],
         "last_fail_at": last_fail_at or 0}     # 0 = unknown → never counted as a post-fix recurrence
    f["sig"] = signature(kind, ident, error)
    if extra:
        f.update(extra)
    return f


# ─────────────────────────── collectors ───────────────────────────
def _heartbeat():
    import fleet_status_heartbeat
    return fleet_status_heartbeat


def _watchdog():
    spec = importlib.util.spec_from_file_location("completion_watchdog", os.path.join(SCRIPTS, "completion-watchdog.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _script_refs(text):
    out = set()
    for m in re.finditer(r"(?:/Users/exomac/\.openclaw/workspace/)?((?:scripts|mission-control|governance)/[\w./\-]+\.(?:py|sh|js))", text or ""):
        p = m.group(1)
        if not p.endswith("run_logged.py") and os.path.exists(os.path.join(WS, p)):
            out.add(p)
    return out


def cron_failures():
    hb = _heartbeat()
    ch = hb.cron_health()
    names = [n for n, _, c in ch.get("errors", []) if (c or 0) >= 2]
    out = []
    if not names:
        return out
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    try:
        for name in names:
            for job_id, job_json, state_json in con.execute(
                    "SELECT job_id, job_json, state_json FROM cron_jobs WHERE enabled=1 AND name=?", (name,)):
                st = json.loads(state_json or "{}")
                err = st.get("lastError") or st.get("lastErrorMessage") or st.get("lastDiagnosticSummary") or "error"
                rc = con.execute("SELECT status, error_text, started_at_ms FROM cron_run_receipts WHERE job_id=? "
                                 "ORDER BY started_at_ms DESC LIMIT 6", (job_id,)).fetchall()
                tail = "\n".join(f"{iso(s / 1000)} {stt}: {(e or '')[:400]}" for stt, e, s in rc)
                try:
                    jj = json.dumps(json.loads(job_json), indent=1)
                except Exception:
                    jj = job_json
                out.append(make_failure("cron", job_id, name, err, ["cron:" + job_id] + sorted(_script_refs(jj)),
                                        jj, tail, (st.get("lastRunAtMs") or 0) / 1000 or None,
                                        {"consecutiveErrors": st.get("consecutiveErrors")}))
    finally:
        con.close()
    return out


def _runs_for(label, days=2):
    recs = []
    for i in range(days):
        p = os.path.join(WS, "logs", "runs", (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") + ".jsonl")
        try:
            with open(p, errors="ignore") as fh:
                for line in fh:
                    if label in line:
                        try:
                            r = json.loads(line)
                        except Exception:
                            continue
                        if r.get("label") == label:
                            recs.append(r)
        except FileNotFoundError:
            pass
    recs.sort(key=lambda r: r.get("start") or "")
    return recs


def _tail(path, n=40):
    try:
        with open(path, errors="ignore") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return ""


def launchd_failure(label, code, plist_path=None):
    plist_path = plist_path or os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
    try:
        with open(plist_path, "rb") as f:
            pl = plistlib.load(f)
        ptxt = open(plist_path).read()
    except Exception:
        pl, ptxt = {}, "(plist not found)"
    args = " ".join(pl.get("ProgramArguments") or [])
    files = sorted(_script_refs(args)) or [label]
    runs = _runs_for(label)
    bad = [r for r in runs if not r.get("ok")]
    last = bad[-1] if bad else {}
    stderr = "\n".join(last.get("stderr_tail") or [])
    errline = next((l for l in reversed(stderr.splitlines()) if l.strip()), "")
    tail = ("Last failing runs (logs/runs):\n" + "\n".join(
        f"{r.get('start')} exit={r.get('exit_code')} sig={r.get('signal')}" for r in bad[-3:]) +
        f"\n--- stderr tail ---\n{stderr}\n--- {pl.get('StandardErrorPath', '')} tail ---\n" +
        _tail(pl.get("StandardErrorPath", "")))
    lf = None
    try:
        lf = datetime.fromisoformat(last.get("end")).timestamp() if last.get("end") else None
    except Exception:
        pass
    return make_failure("launchd", label, label, f"exit {code}: {errline}", files, ptxt, tail, lf)


def launchd_failures():
    return [launchd_failure(label, code) for label, code in _heartbeat().launchd_bad() if label != SELF_LABEL]


def _govlog_files(agent):
    hits = set()
    pat = re.compile(r"new_run\(\s*['\"]" + re.escape(agent) + r"['\"]")
    for p in glob.glob(os.path.join(SCRIPTS, "*.py")):
        try:
            if pat.search(open(p, errors="ignore").read()):
                hits.add(os.path.relpath(p, WS))
        except Exception:
            pass
    return sorted(hits) or [f"govlog:{agent}"]


def govlog_failures():
    cw = _watchdog()
    runs, stalled, errored = cw.scan_events()
    latest = {}
    for cid, d in runs.items():
        a = d["agent"]
        if a not in latest or d["last"] > latest[a]["last"]:
            latest[a] = d
    out = []
    by = {}
    for cid, agent, detail in errored:
        by.setdefault((agent, error_class(detail)), []).append(detail)
    for (agent, cls), dets in by.items():
        lr = latest.get(agent) or {}
        if agent == AGENT_ID or len(dets) < 2 or not lr.get("errors") or error_class(lr["errors"][0]) != cls:
            continue
        out.append(make_failure("govlog", agent, agent, dets[-1], _govlog_files(agent), "",
                                f"{len(dets)} errored runs in {cw.LOOKBACK_H}h (governance/events.jsonl):\n" +
                                "\n".join(str(x)[:300] for x in dets[-5:]), lr["last"].timestamp()))
    sc = {}
    for cid, agent, age in stalled:
        sc[agent] = sc.get(agent, 0) + 1
    for agent, n in sc.items():
        if n >= 2 and agent != AGENT_ID:
            out.append(make_failure("govlog", agent, agent, "stalled: start without end (killed/hung mid-run)",
                                    _govlog_files(agent), "", f"{n} stalled runs in {cw.LOOKBACK_H}h"))
    return out


def eval_failures():
    """agent_eval OUTPUT/liveness FAILs (selftest exit≠0, 'not loaded') from its LATEST hourly pass — launchd exit
    codes can't see these (Jon 10/22: '4 automated jobs failing — is Exo automatically addressing this?')."""
    logp = os.path.join(WS, "logs", "agent-eval.log")
    if not os.path.exists(logp):
        return []
    lines = open(logp, errors="replace").read().splitlines()[-3000:]
    start = max((i for i, l in enumerate(lines) if re.search(r"\] eval: \d+ OK", l)), default=None)
    if start is None:
        return []
    stamp = lines[start][1:20]
    st = {}
    try:
        st = json.load(open(os.path.join(WS, "state", "agent-eval-state.json")))
    except Exception:
        pass
    out = []
    for l in lines[start + 1:]:
        if not l.startswith("[" + stamp[:16]) or re.search(r"\] eval: \d+ OK", l):
            break   # same pass = same minute, until the next summary line
        m = re.search(r"FAIL: (\S+) — (.+?) \(owner", l)
        if not m:
            continue
        ident, why = m.group(1), m.group(2)
        key = ident if ident.startswith(("selftest:", "cron:")) else "com.exos." + ident
        tail = (st.get(key) or {}).get("tail", "")
        label = key.split(":", 1)[1] if key.startswith("selftest:") else key
        out.append(make_failure("eval", key, label, why if "not due" not in why else f"selftest failing: {tail[-300:]}",
                                log_tail=tail))
    return out


def collect(fixture=None):
    if fixture:
        raw = json.load(open(fixture))
        out = []
        for r in (raw if isinstance(raw, list) else [raw]):
            if r.get("kind") == "launchd" and r.get("plist"):
                f = launchd_failure(r["ident"], r.get("code", 1), r["plist"])
                if r.get("log_tail"):
                    f["log_tail"] = r["log_tail"]
                if r.get("error"):
                    f.update(error=r["error"], error_class=error_class(r["error"]),
                             sig=signature("launchd", r["ident"], r["error"]))
                if r.get("file_set"):
                    f["file_set"] = r["file_set"]
                out.append(f)
            else:
                out.append(make_failure(r["kind"], r["ident"], r.get("job", r["ident"]), r["error"], r.get("file_set"),
                                        r.get("definition", ""), r.get("log_tail", ""), r.get("last_fail_at")))
        return out
    out = []
    for fn in (cron_failures, launchd_failures, govlog_failures, eval_failures):
        try:
            out.extend(fn())
        except Exception as e:
            log(f"WARN collector {fn.__name__} failed: {e}")
    return out


# ─────────────────────────── guardrails ───────────────────────────
def forbidden(path):
    p = str(path)
    return any(re.search(rx, p, re.I) for rx in FORBIDDEN)


def cmd_allowed(cmd):
    c = cmd.strip()
    return bool(c) and not re.search(CMD_DENY, c, re.I) and any(re.search(rx, c) for rx in CMD_ALLOW)


VERIFY_DENY = r"git (apply|commit|reset|checkout|stash|revert|push)"


def verify_allowed(cmd):
    return bool(cmd) and not re.search(CMD_DENY, cmd, re.I) and not re.search(VERIFY_DENY, cmd)


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def in_flight(st):
    out = []
    for r in st["fixes"].values():
        if r.get("status") == "in_progress":
            if pid_alive(r.get("pid")) and now_ts() - r.get("run_started", 0) < STALE_RUN_S:
                out.append(r)
    return out


def can_launch(st, f):
    recent = [t for t in st.get("launches", []) if now_ts() - t < 3600]
    if len(recent) >= MAX_RUNS_PER_HOUR:
        return False, "rate-limit (3 fix runs/hour)"
    fs = set(f.get("file_set") or [])
    for r in in_flight(st):
        if r["sig"] != f["sig"] and fs & set(r.get("file_set") or []):
            return False, f"file set busy ({r['sig']})"
    return True, ""


# ─────────────────────────── dispatch ───────────────────────────
ACTIVE_DONE = ("applied", "approved_applied", "no_fix")


def spawn_worker(sig, apply=False):
    os.makedirs(RUN_DIR, exist_ok=True)
    out = open(os.path.join(RUN_DIR, slug(sig) + (".apply" if apply else "") + ".out"), "a")
    argv = [PY, os.path.abspath(__file__), "worker", "--sig", sig] + (["--test"] if TEST else []) + (["--apply"] if apply else [])
    p = subprocess.Popen(argv, stdout=out, stderr=out, stdin=subprocess.DEVNULL, start_new_session=True, cwd=WS)
    return p.pid


def dispatch(failures, launcher=spawn_worker, dry=False):
    """Returns list of (sig, action). One failure signature = one fix attempt."""
    acts = []
    with state_lock():
        st = load_state()
        fx = st.setdefault("fixes", {})
        st.setdefault("launches", [])
        cur = {f["sig"] for f in failures}
        # reap stale / dead runs
        for r in fx.values():
            if r.get("status") == "in_progress" and (not pid_alive(r.get("pid")) or now_ts() - r.get("run_started", 0) > STALE_RUN_S):
                r.update(status="fix_run_failed", run_ended=now_ts(), note="worker died or timed out")
        # resolution: an active fix whose failure is no longer present
        for sig, r in fx.items():
            if sig not in cur and r.get("status") in ACTIVE_DONE + ("queued", "fix_run_failed") and not r.get("resolved_at"):
                r["resolved_at"] = now_ts()
                if r.get("status") == "queued":
                    r["status"] = "resolved"
        for f in sorted(failures, key=lambda x: x["sig"]):
            sig = f["sig"]
            r = fx.get(sig)
            if r is None:
                r = fx[sig] = {"sig": sig, "status": "queued", "episode": 1, "attempts": 0, "first_seen": now_ts()}
                acts.append((sig, "new"))
            else:
                recurred = (r.get("status") in ("applied", "approved_applied") and
                            (f.get("last_fail_at") or 0) > (r.get("applied_at") or 0) + 60)
                if r.get("status") == "resolved" or recurred or (r.get("resolved_at") and r.get("status") in ACTIVE_DONE):
                    r["history"] = (r.get("history") or []) + [{k: r.get(k) for k in ("episode", "status", "outcome", "commits", "decision_id", "applied_at")}]
                    r.update(episode=r.get("episode", 1) + 1, status="queued", attempts=0, resolved_at=None,
                             decision_id=None, commits=[], outcome=None)
                    acts.append((sig, "recurred"))
                elif r.get("status") == "fix_run_failed" and r.get("attempts", 0) < 2 and \
                        now_ts() - (r.get("run_ended") or 0) > RETRY_FAILED_RUN_S:
                    r["status"] = "queued"
            r.update({k: f[k] for k in ("kind", "ident", "job", "error", "error_class", "file_set", "definition",
                                        "log_tail", "last_fail_at")})
            r["last_seen"] = now_ts()
            if r["status"] != "queued":
                continue
            if r.get("episode", 1) > MAX_EPISODES and not r.get("jon_approved_rerun"):
                r["status"] = "escalate"
                acts.append((sig, "escalate"))
                continue
            ok, why = can_launch(st, f)
            if not ok:
                r["queued_reason"] = why
                acts.append((sig, "held: " + why))
                continue
            if dry:
                acts.append((sig, "would-launch"))
                continue
            st["launches"].append(now_ts())
            st["launches"] = [t for t in st["launches"] if now_ts() - t < 86400]
            r.update(status="in_progress", run_started=now_ts(), attempts=r.get("attempts", 0) + 1, queued_reason=None)
            r["pid"] = launcher(sig)
            acts.append((sig, f"launched pid={r['pid']}"))
            trace("fix_run_launched", {"sig": sig, "job": f["job"], "episode": r["episode"]})
        if not dry:
            save_state(st)
    return acts


# ─────────────────────────── fix run (worker) ───────────────────────────
RULES = """RULES (failure-fixer-exo3 — Jon 10/8: "launch a fix and I'll just approve the fix"):
1. ROOT-CAUSE it. Read the job's script/config, the log tail, recent git log for those paths. Fix the GENERATOR, not
   just this instance. If the failure is transient/self-cleared (network blip, provider outage, already fixed), say so
   (outcome "no_fix") — do not invent a change.
2. SAFE / INTERNAL / REVERSIBLE fix (our own script code/config, path fixes, /usr/bin/python3 pin, model switch to a
   model in the allowed list, retry/timeout tuning, `openclaw cron edit <id> --clear-tools` for the claude-cli toolsAllow
   trap) → APPLY it:
   a. verify by re-running the job (`launchctl kickstart -k gui/$(id -u)/<label>`, `openclaw cron run <id>`, or the
      script's --selftest/--dry-run). If a real run would send external messages/email, use the dry-run/selftest path.
   b. commit ONLY the paths you changed (`git add <path>`; NEVER -A/-a). If a file is already dirty from another
      session, commit only your hunks: `git diff -U0 <path>` → filter to your hunks → `git apply --cached --unidiff-zero`.
      If anything else is already staged in the index, leave it alone. Message: "failure-fixer-exo3: <job> — <cause>".
   c. add an improvement-ledger entry: /usr/bin/python3 scripts/improvement_ledger.py add --agent <label|cron:slug>
      --change <commit> --hypothesis "<cause> fixed by <change>" --metrics reliability --signature "<error text>"
      (leave mission-control/data/improvement-ledger.json uncommitted if it carries other sessions' edits).
   d. a fix that changes an agent's BEHAVIOR must ship with an eval that replays this failure (exo3) — add/extend its
      --selftest when practical; if not, stage instead.
3. NEEDS JON (credentials/logins, external action, money, policy, deleting data, anything irreversible, or a file you
   would edit is dirty with another session's uncommitted work you'd have to touch) → DO NOT APPLY. Stage it:
   write a unified diff relative to HEAD containing ONLY your hunks to PATCH_FILE (a/ b/ prefixes, repo-relative
   paths, must pass `git apply --check --cached PATCH_FILE`), then restore the working tree so nothing of yours is left
   uncommitted. Non-file steps go in apply_commands (allowed: `openclaw cron edit|run|enable <id> …`,
   `launchctl kickstart|bootstrap|bootout … com.exos.*`, `/usr/bin/python3 scripts/<x>.py …`). Do NOT post a Decision
   yourself — the dispatcher files ONE "Approve fix" card from your JSON.
4. NEVER: read/print/modify secrets or tokens (~/.openclaw/secrets.json, .decisions-token, Keychain); modify BOMs
   (bom-index*.json, bom-costs/edits, BOM xlsx — read-only); write mission-control/data/decisions.json directly; run or
   edit migrate.js; touch other sessions' uncommitted changes; send ANY external email/message (no msmtp, no
   `openclaw message send`, no cron runs that deliver externally); git push; edit ~/.openclaw/openclaw.json protected
   model paths. Do not spawn subagents. Stay inside the failing job's file set unless the root cause is a shared lib
   (then stage, don't apply).
5. Be brief. When done, reply with ONLY one JSON object, no prose:
{"outcome":"applied"|"staged"|"no_fix","cause":"<one line, <=90 chars>","diagnosis":"<root cause, <=900 chars>",
 "change":"<exact change, <=600 chars>","files":["repo/relative/paths"],"commits":["<full sha>"],
 "patch_file":"<PATCH_FILE or empty>","apply_commands":["..."],
 "verify_command":"<read-only command proving the fix, run from the workspace AFTER the dispatcher has applied the patch;
   never git apply/commit/reset in it; exit 0 = fixed>",
 "tested":"<how you verified + result>","needs_jon_reason":"<why staged, else empty>"}"""

TEST_RULES = """TEST MODE (failure-fixer-exo3 selftest of the dispatch path): this is a FIXTURE job, not a real fleet
job. STAGE ONLY — outcome must be "staged" or "no_fix". Do not apply, commit, kickstart, run crons, or post anything.
Write the patch to PATCH_FILE (the fixture may be untracked: then it only needs to pass `git apply --check PATCH_FILE`)
and leave the fixture file itself unchanged."""


def build_prompt(r, apply_mode=False):
    patch_file = os.path.join(PATCH_DIR, slug(r["sig"]) + f".e{r.get('episode', 1)}.patch")
    hist = r.get("history") or []
    head = (f"You are Exo running an automatic FIX RUN for a failing ExoMac fleet job (dispatcher: {AGENT_ID}).\n"
            f"Workspace: {WS} (shared git tree — read AGENTS.md 'Git Hygiene').\n\n")
    if apply_mode:
        o = r.get("outcome") or {}
        head += (f"Jon APPROVED the staged fix on Decision {r.get('decision_id')} (\"Approve fix\"). Apply EXACTLY the staged "
                 f"change below (no scope creep), verify, commit scoped paths, add the ledger entry, then reply with the JSON "
                 f"(outcome \"applied\").\nSTAGED FIX:\n{json.dumps(o, indent=1)[:5000]}\n\n")
    body = (f"FAILURE\n  job: {r['job']}\n  kind: {r['kind']}  id: {r['ident']}\n  signature: {r['sig']} (episode {r.get('episode', 1)})\n"
            f"  error: {r['error']}\n  file set: {', '.join(r.get('file_set') or [])}\n")
    if hist:
        body += f"  PRIOR FIX ATTEMPTS FOR THIS SIGNATURE (did not hold): {json.dumps(hist)[:1500]}\n"
    body += f"\nRECENT LOG TAIL\n{r.get('log_tail', '')[-4000:]}\n\nJOB DEFINITION\n{r.get('definition', '')[:6000]}\n\n"
    rules = RULES.replace("PATCH_FILE", patch_file)
    if TEST:
        rules += "\n\n" + TEST_RULES.replace("PATCH_FILE", patch_file)
    return head + body + rules, patch_file


def extract_reply(jdata):
    res = (jdata or {}).get("result", {}) or {}
    txt = "\n".join((p.get("text") or "").strip() for p in (res.get("payloads") or []) if p.get("text")).strip()
    return txt or ((res.get("meta", {}) or {}).get("finalAssistantVisibleText") or "").strip()


def parse_outcome(raw):
    for m in reversed(list(re.finditer(r"\{(?:[^{}]|\{[^{}]*\})*\"outcome\"(?:[^{}]|\{[^{}]*\}|\[[^\]]*\])*\}", raw or "", re.S))):
        try:
            return json.loads(m.group(0))
        except Exception:
            continue
    i, j = (raw or "").find("{"), (raw or "").rfind("}")
    for cand in (raw, (raw or "")[i:j + 1] if i >= 0 else ""):
        try:
            o = json.loads(cand)
            if isinstance(o, dict) and o.get("outcome"):
                return o
        except Exception:
            pass
    return None


def sub_env():
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/shims:/Users/exomac/.local/share/mise/installs/node/24.21.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    return env


def run_agent(prompt, skey):
    os.makedirs(RUN_DIR, exist_ok=True)
    pf = os.path.join(RUN_DIR, slug(skey) + ".prompt.txt")
    with open(pf, "w") as f:
        f.write(prompt)
    r = subprocess.run([OPENCLAW, "agent", "--session-key", skey, "--message-file", pf, "--json",
                        "--timeout", str(RUN_TIMEOUT_S)], capture_output=True, text=True,
                       timeout=RUN_TIMEOUT_S + 180, env=sub_env(), cwd=WS)
    try:
        jd = json.loads(r.stdout)
        raw = extract_reply(jd)
        ok = r.returncode == 0 and jd.get("status") in ("ok", None)
    except Exception:
        raw, ok = r.stdout or "", False
    with open(os.path.join(RUN_DIR, slug(skey) + ".reply.txt"), "w") as f:
        f.write(raw or (r.stderr or "")[-4000:])
    return ok, raw, (r.stderr or "")[-600:]


def git(*a, check=False, **kw):
    return subprocess.run(["git", "-C", WS] + list(a), capture_output=True, text=True, check=check, **kw)


def commit_files(sha):
    r = git("show", "--name-only", "--pretty=format:", sha)
    return [l for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else []


def patch_paths(patch_file):
    try:
        txt = open(patch_file).read()
    except Exception:
        return []
    return sorted({m.group(1) for m in re.finditer(r"^\+\+\+ b/(\S+)", txt, re.M)} |
                  {m.group(1) for m in re.finditer(r"^--- a/(\S+)", txt, re.M)})


def tracked(path):
    return git("ls-files", "--error-unmatch", path).returncode == 0


def validate_patch(patch_file):
    """→ (ok, why, paths, cached_ok)"""
    if not patch_file or not os.path.exists(patch_file):
        return False, "no patch file", [], False
    paths = patch_paths(patch_file)
    bad = [p for p in paths if forbidden(p)]
    if bad:
        return False, f"patch touches forbidden paths {bad}", paths, False
    all_tracked = bool(paths) and all(tracked(p) for p in paths)
    if all_tracked:
        r = git("apply", "--check", "--cached", patch_file)
        return r.returncode == 0, (r.stderr.strip()[:300] or "ok"), paths, True
    r = git("apply", "--check", patch_file)
    return r.returncode == 0, (r.stderr.strip()[:300] or "ok"), paths, False


def ledger_has(commits):
    try:
        d = json.load(open(os.path.join(WS, "mission-control", "data", "improvement-ledger.json")))
        blob = json.dumps(d)
        return any(c[:7] in blob for c in commits)
    except Exception:
        return False


def ledger_add(r, commit, cause):
    if TEST or not commit or ledger_has([commit]):
        return
    agent = r["ident"] if r["kind"] == "launchd" else ("cron:" + slug(r["job"]) if r["kind"] == "cron" else r["ident"])
    argv = [PY, os.path.join(SCRIPTS, "improvement_ledger.py"), "add", "--agent", agent, "--change", commit,
            "--hypothesis", f"{cause} — fixed by {AGENT_ID} ({r['sig']})", "--metrics", "reliability",
            "--signature", r["error"][:160]]
    if r["kind"] == "cron":
        argv += ["--cron", r["ident"]]
    if r["kind"] == "govlog":
        argv += ["--govlog", r["ident"]]
    subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=WS)


def post(text):
    if TEST:
        log(f"(test: no post) {text}")
        return
    try:
        from deliver import deliver
        deliver(text, target=SYS_CHANNEL, source=AGENT_ID)
    except Exception as e:
        log(f"WARN post failed: {e}")


def decision_body(r, o):
    cause = (o.get("cause") or r["error_class"])[:90]
    title = f"Approve fix: {r['job'][:60]} — {cause}"
    if TEST:
        title = "[TEST] " + title
    patch_txt = ""
    if o.get("patch_file") and os.path.exists(o["patch_file"]):
        patch_txt = open(o["patch_file"]).read()
    ctx = (f"FAILURE: {r['job']} ({r['kind']} {r['ident']})\n{r['error'][:500]}\nSignature {r['sig']} · episode {r.get('episode', 1)}\n\n"
           f"DIAGNOSIS: {o.get('diagnosis', '')}\n\nWHY IT NEEDS YOU: {o.get('needs_jon_reason') or 'see diagnosis'}\n\n"
           f"EXACT CHANGE: {o.get('change', '')}\n")
    if patch_txt:
        ctx += f"\nPatch ({os.path.relpath(o['patch_file'], WS)}):\n{patch_txt[:3500]}\n"
    if o.get("apply_commands"):
        ctx += "\nCommands on approve:\n" + "\n".join("  " + c for c in o["apply_commands"]) + "\n"
    ctx += (f"\nHOW TESTED: {o.get('tested', '')}\nVERIFY ON APPROVE: {o.get('verify_command', '')}\n"
            + (f"\nVALIDATION NOTE: {o['_validation']}\n" if o.get("_validation") else "") +
            f"\nOn \"Approve fix\": {AGENT_ID} applies exactly this change, re-verifies, commits scoped paths, logs an "
            f"improvement-ledger entry and posts the result in #exomac-system. \"Hold\" = leave it; \"Discuss\" = add a note.")
    return {"title": title[:160], "question": f"Apply the staged fix for {r['job'][:60]}?", "type": "choice",
            "options": ["Approve fix (recommended)", "Hold", "Discuss"], "priority": "med",
            "source": f"Exo ({AGENT_ID})", "agentClass": AGENT_ID, "context": ctx[:9000],
            "proposedAction": (o.get("change") or "")[:600], "correlationId": r.get("corr") or "",
            "dedupeKey": f"failure-fix:{r['sig']}:e{r.get('episode', 1)}" + (":test" if TEST else "")}


def file_decision(body):
    if TEST:
        os.makedirs(TEST_DEC_DIR, exist_ok=True)
        did = "TEST-" + hashlib.sha1(body["dedupeKey"].encode()).hexdigest()[:7]
        rec = {**body, "id": did, "status": "open", "answer": None, "created": iso()}
        p = os.path.join(TEST_DEC_DIR, did + ".json")
        if os.path.exists(p):
            return did
        json.dump(rec, open(p + ".tmp", "w"), indent=1)
        os.replace(p + ".tmp", p)
        return did
    tok = open(TOKEN_FILE).read().strip()
    req = urllib.request.Request(f"{MC}/api/decisions/ingest", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-exo-token": tok})
    return json.load(urllib.request.urlopen(req, timeout=30)).get("id")


def worker(sig, apply_mode=False):
    with state_lock():          # waits for the dispatcher that spawned us to finish saving state
        st = load_state()
    r = st["fixes"].get(sig)
    if not r:
        print("unknown sig"); return 1
    corr = r.get("corr") or trace("fix_run_start", {"sig": sig, "apply": apply_mode})
    update_rec(sig, corr=corr, pid=os.getpid())
    prompt, patch_file = build_prompt(r, apply_mode)
    skey = f"agent:main:{AGENT_ID}-{hashlib.sha1((sig + str(r.get('episode'))).encode()).hexdigest()[:10]}" + \
           ("-apply" if apply_mode else "") + ("-test" if TEST else "")
    started = now_ts()
    head_before = git("rev-parse", "HEAD").stdout.strip()
    try:
        ok, raw, err = run_agent(prompt, skey)
    except Exception as e:
        ok, raw, err = False, "", str(e)
    o = parse_outcome(raw) if ok else None
    if not o:
        update_rec(sig, status="fix_run_failed" if not apply_mode else "approved_failed", run_ended=now_ts(),
                   note=f"agent run failed/unparsable: {err[-300:] or raw[-300:]}")
        log(f"{sig}: fix run FAILED ({err[-200:]})")
        trace("fix_run_failed", {"sig": sig}, outcome="error", corr=corr, level="warn")
        return 1
    o.setdefault("patch_file", "")
    if o.get("patch_file") and not os.path.isabs(o["patch_file"]):
        o["patch_file"] = os.path.join(WS, o["patch_file"])
    if not o.get("patch_file") and os.path.exists(patch_file):
        o["patch_file"] = patch_file
    outcome = o.get("outcome")
    if TEST and outcome == "applied":
        outcome = o["outcome"] = "staged"
        o["_validation"] = "TEST mode: applied → downgraded to staged"
    fields = {"outcome": o, "run_ended": now_ts(), "cause": (o.get("cause") or "")[:120]}

    if outcome == "applied":
        commits = []
        for c in o.get("commits") or []:
            if git("cat-file", "-e", f"{c}^{{commit}}").returncode == 0 and \
                    git("merge-base", "--is-ancestor", head_before, c).returncode == 0 and c[:7] != head_before[:7]:
                commits.append(git("rev-parse", c).stdout.strip())
        touched = sorted({p for c in commits for p in commit_files(c)})
        bad = [p for p in touched if forbidden(p)]
        if bad:
            for c in reversed(commits):
                git("revert", "--no-edit", c)
            o["_validation"] = f"Fix run committed forbidden paths {bad}; auto-reverted ({', '.join(c[:7] for c in commits)})."
            fields.update(status="awaiting_approval", commits=[])
            outcome = "staged"
            trace("guardrail_revert", {"sig": sig, "paths": bad, "commits": commits}, outcome="reverted", corr=corr, level="warn")
        else:
            for c in commits:
                ledger_add(r, c, o.get("cause", ""))
            fields.update(status="approved_applied" if apply_mode else "applied", commits=commits, applied_at=now_ts())
            update_rec(sig, **fields)
            log(f"{sig}: APPLIED {[c[:7] for c in commits]} — {o.get('cause')}")
            trace("fix_applied", {"sig": sig, "commits": commits, "cause": o.get("cause")}, outcome="applied", corr=corr)
            if apply_mode:
                post(f"✅ {r.get('decision_id')} approved fix applied: {r['job']} — {o.get('cause', '')}"
                     + (f" (commit {commits[0][:7]})" if commits else ""))
            return 0

    if outcome == "staged":
        if apply_mode:
            update_rec(sig, status="approved_failed", **{k: v for k, v in fields.items() if k != "status"},
                       note="apply run could not apply the approved fix")
            post(f"⚠️ {r.get('decision_id')} approved fix for {r['job']} could not be applied by the apply run — "
                 f"{o.get('needs_jon_reason') or o.get('diagnosis', '')[:200]}")
            return 1
        vok, why, paths, _ = validate_patch(o.get("patch_file"))
        if o.get("patch_file") and not vok:
            o["_validation"] = (o.get("_validation", "") + f" Patch did not validate ({why}); on approve Exo re-applies via an apply run.").strip()
            o["patch_file_invalid"] = True
        badcmds = [c for c in (o.get("apply_commands") or []) if not cmd_allowed(c)]
        if badcmds:
            o["_validation"] = (o.get("_validation", "") + f" Non-allow-listed commands {badcmds} will run via an agent apply run on approve.").strip()
        rr = dict(r, corr=corr)
        try:
            did = file_decision(decision_body(rr, o))
        except Exception as e:
            fields.update(status="fix_run_failed", note=f"decision ingest failed: {e}")
            update_rec(sig, **fields)
            log(f"{sig}: decision ingest FAILED {e}")
            return 1
        fields.update(status="awaiting_approval", decision_id=did, files=paths or o.get("files") or [])
        update_rec(sig, **fields)
        log(f"{sig}: STAGED → Decision {did} — {o.get('cause')}")
        trace("fix_staged", {"sig": sig, "decision": did, "cause": o.get("cause")}, outcome="staged", corr=corr)
        return 0

    fields.update(status="no_fix")
    update_rec(sig, **fields)
    log(f"{sig}: NO_FIX — {o.get('cause')}")
    trace("fix_not_needed", {"sig": sig, "cause": o.get("cause")}, outcome="no_fix", corr=corr)
    return 0


# ─────────────────────────── approval executor ───────────────────────────
def load_decisions():
    if TEST:
        out = []
        for p in glob.glob(os.path.join(TEST_DEC_DIR, "*.json")):
            try:
                out.append(json.load(open(p)))
            except Exception:
                pass
        return out
    d = json.load(open(DEC_FILE))
    return d if isinstance(d, list) else d.get("decisions", [])


def human_answered(d):
    if TEST:
        return bool(d.get("answeredByEmail") or d.get("answeredBy"))
    if d.get("answeredByEmail"):
        return True
    try:
        import backlog_grind_apply
        return backlog_grind_apply.human_answered(d)
    except Exception:
        return False


def execute_approved(r):
    """Deterministic apply of a staged patch / allow-listed commands. Returns status string."""
    o = r.get("outcome") or {}
    pf = o.get("patch_file") if not o.get("patch_file_invalid") else None
    cmds = o.get("apply_commands") or []
    v0 = o.get("verify_command") or ""
    if (not pf and not cmds) or any(not cmd_allowed(c) for c in cmds) or (v0 and not verify_allowed(v0)):
        return "needs_agent_apply"
    paths, cached = [], False
    if pf:
        ok, why, paths, cached = validate_patch(pf)
        if not ok:
            return "needs_agent_apply"
        if cached and not TEST:
            other = [p for p in git("diff", "--cached", "--name-only").stdout.split() if p]
            if other:
                return "deferred: index has other staged files " + ",".join(other[:3])
        if git("apply", pf).returncode != 0:
            return "needs_agent_apply"
        if cached and not TEST:
            if git("apply", "--cached", pf).returncode != 0:
                git("apply", "-R", pf)
                return "needs_agent_apply"
    for c in cmds:
        subprocess.run(shlex.split(c), capture_output=True, text=True, timeout=600, cwd=WS, env=sub_env())
    v = o.get("verify_command") or ""
    vok, vout = True, "(no verify command)"
    if v:
        vr = subprocess.run(["/bin/zsh", "-c", v], capture_output=True, text=True, timeout=900, cwd=WS, env=sub_env())
        vok, vout = vr.returncode == 0, (vr.stdout + vr.stderr)[-400:]
    if not vok:
        if pf:
            git("apply", "-R", pf)
            if cached and not TEST:
                git("apply", "-R", "--cached", pf)
        update_rec(r["sig"], status="approved_failed", note=f"verify failed: {vout}", run_ended=now_ts())
        post(f"⚠️ {r.get('decision_id')} approved fix for {r['job']} FAILED verification — patch reversed. {vout[-200:]}")
        return "approved_failed"
    commit = ""
    if pf and cached and not TEST:
        msg = f"{AGENT_ID}: approved fix {r['job']} — {o.get('cause', '')} ({r.get('decision_id')})\n\nsig {r['sig']}"
        cr = git("commit", "-m", msg)
        if cr.returncode == 0:
            commit = git("rev-parse", "HEAD").stdout.strip()
            ledger_add(r, commit, o.get("cause", ""))
        else:
            git("reset", "-q", "--", *paths)
            update_rec(r["sig"], status="approved_failed", note=f"commit failed: {(cr.stderr or cr.stdout)[-300:]}")
            return "approved_failed"
    update_rec(r["sig"], status="approved_applied", commits=[commit] if commit else [], applied_at=now_ts(),
               verify_output=vout, run_ended=now_ts())
    trace("approved_fix_applied", {"sig": r["sig"], "decision": r.get("decision_id"), "commit": commit}, outcome="applied")
    post(f"✅ {r.get('decision_id')} approved fix applied: {r['job']} — {o.get('cause', '')}"
         + (f" (commit {commit[:7]})" if commit else "") + "; verified.")
    log(f"{r['sig']}: approved fix applied {commit[:7]} verify={vout[-120:]!r}")
    return "approved_applied"


def run_executor():
    st = load_state()
    waiting = [r for r in st["fixes"].values() if r.get("status") in ("awaiting_approval", "escalated") and r.get("decision_id")]
    if not waiting:
        return []
    decs = {d.get("id"): d for d in load_decisions()}
    res = []
    for r in waiting:
        d = decs.get(r["decision_id"])
        if not d or str(d.get("status")).lower() != "answered" or not human_answered(d):
            continue
        ans = str(d.get("answer") or "").lower()
        if ans.startswith("approve") and r.get("status") == "escalated":
            update_rec(r["sig"], status="queued", jon_approved_rerun=True, decision_id=None)
            res.append((r["sig"], "escalation approved → one more fix run next sweep"))
            continue
        if ans.startswith("approve"):
            if in_flight(st):
                busy = [x for x in in_flight(st) if set(x.get("file_set") or []) & set(r.get("file_set") or [])]
                if busy:
                    res.append((r["sig"], "deferred: file set busy")); continue
            out = execute_approved(r)
            if out == "needs_agent_apply":
                update_rec(r["sig"], status="in_progress", run_started=now_ts())
                pid = spawn_worker(r["sig"], apply=True)
                update_rec(r["sig"], pid=pid)
                out = f"agent apply run pid={pid}"
            res.append((r["sig"], out))
        elif ans.startswith("hold"):
            update_rec(r["sig"], status="held", note=d.get("note") or "")
            res.append((r["sig"], "held"))
        else:
            update_rec(r["sig"], status="discuss", note=d.get("note") or "")
            res.append((r["sig"], "discuss"))
    return res


def escalate(st):
    """A signature that recurred past MAX_EPISODES → one Decision, no further auto runs."""
    for r in list(st["fixes"].values()):
        if r.get("status") != "escalate":
            continue
        o = {"cause": f"recurred {r.get('episode', 1) - 1}x after fixes", "diagnosis":
             "Automatic fixes for this failure signature did not hold: " + json.dumps(r.get("history") or [])[:1500],
             "change": "No new automatic change. Approve = launch one more agent fix run with this history; Hold = leave it.",
             "needs_jon_reason": f"failure recurred after {MAX_EPISODES} automatic fix episodes", "tested": "n/a"}
        try:
            did = file_decision(decision_body(r, o))
            update_rec(r["sig"], status="escalated", decision_id=did, outcome=o)
        except Exception as e:
            log(f"escalate {r['sig']} failed: {e}")


# ─────────────────────────── reporting ───────────────────────────
def fix_status_line(kind, name, st=None):
    """Suffix for fleet_status_heartbeat lines. kind: cron|launchd|govlog; name: cron name / label / agent."""
    st = st or load_state(STATE)
    cands = [r for r in st.get("fixes", {}).values() if r.get("kind") == kind and name in (r.get("job"), r.get("ident"))]
    if not cands:
        return "→ fix queued (next 15-min sweep)"
    r = max(cands, key=lambda x: x.get("last_seen") or 0)
    s, did, cm = r.get("status"), r.get("decision_id"), (r.get("commits") or [""])[0][:7]
    return {
        "queued": f"→ fix queued ({r.get('queued_reason') or 'next sweep'})",
        "in_progress": "→ fix in progress",
        "applied": f"→ fix applied (commit {cm})" if cm else f"→ fix applied ({(r.get('cause') or '')[:60]})",
        "approved_applied": f"→ approved fix applied (commit {cm})" if cm else "→ approved fix applied",
        "awaiting_approval": f"→ fix awaiting your approval: {did}",
        "escalated": f"→ fixes didn't hold — your call: {did}",
        "escalate": "→ fixes didn't hold — Decision being filed",
        "approved_failed": f"→ approved fix failed verify (reversed) — {did}",
        "held": f"→ fix on hold ({did})", "discuss": f"→ fix marked Discuss ({did})",
        "no_fix": f"→ diagnosed, no code fix needed: {(r.get('cause') or '')[:70]}",
        "fix_run_failed": "→ fix run failed; auto-retry in 1h",
        "resolved": "→ resolved",
    }.get(s, f"→ fix {s}")


def daily_digest():
    if TEST:
        return
    with state_lock():
        st = load_state()
        today = datetime.now().strftime("%Y-%m-%d")
        if st.get("digest_last") == today or datetime.now().hour < DIGEST_HOUR:
            return
        st["digest_last"] = today
        done = set(st.get("digested") or [])
        items = [r for r in st["fixes"].values() if r.get("status") in ("applied", "approved_applied")
                 and now_ts() - (r.get("applied_at") or 0) < 86400 and f"{r['sig']}:{r.get('episode')}" not in done]
        for r in items:
            done.add(f"{r['sig']}:{r.get('episode')}")
        st["digested"] = sorted(done)[-500:]
        save_state(st)
    if items:   # R-NONEWS: no line when nothing was fixed
        post("🛠 Auto-fixes (24h): " + "; ".join(
            f"{r['job'][:40]} — {(r.get('cause') or '')[:60]}" + (f" ({r['commits'][0][:7]})" if r.get("commits") else "")
            for r in items))


def cmd_run(fixture=None, dry=False):
    os.makedirs(FF_DIR, exist_ok=True)
    run_lock = open(os.path.join(FF_DIR, ".run.lock" + (".test" if TEST else "")), "w")
    try:
        fcntl.flock(run_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)   # launchd sweep vs heartbeat-triggered sweep
    except OSError:
        print(json.dumps({"skipped": "another sweep is running"}))
        return
    fails = collect(fixture)
    acts = dispatch(fails, dry=dry)
    if not dry:
        escalate(load_state())
        ex = run_executor()
        daily_digest()
    else:
        ex = []
    if acts or ex:
        log(f"run: failures={len(fails)} actions={acts} executor={ex}")
    print(json.dumps({"failures": [f["sig"] for f in fails], "actions": acts, "executor": ex}))


def cmd_report(job, error, files):
    """Manual entry (e.g. a misclassified alert Jon flagged) → same pipeline."""
    f = make_failure("manual", slug(job), job, error, files or [f"manual:{slug(job)}"], last_fail_at=now_ts())
    acts = dispatch([f])
    print(json.dumps(acts))


# ─────────────────────────── selftest (eval_suite) ───────────────────────────
def selftest():
    global STATE, TEST_STATE, FF_DIR
    import tempfile
    tmp = tempfile.mkdtemp(prefix="ffx-")
    saved = (STATE, TEST_STATE, FF_DIR)
    STATE = TEST_STATE = os.path.join(tmp, "state.json")
    FF_DIR = tmp
    res = {}
    try:
        a = signature("cron", "j1", "Timeout after 30123ms on run 5f3a9c2e-1111-2222-3333-444455556666")
        b = signature("cron", "j1", "Timeout after 999ms on run 0f3a9c2e-aaaa-2222-3333-444455556666")
        c = signature("cron", "j1", "KeyError 'trackers'")
        res["sig_stable"] = a == b and a != c
        lbl = "com.exos" + ".fixture-a"     # not a literal label (exo3 gate R1)
        launched = []
        mypid = os.getpid()

        def fake(sig):
            launched.append(sig); return mypid
        # one agent per file set: two failures sharing scripts/shared.py → only one run
        pair = [make_failure("launchd", lbl + "p", lbl + "p", "exit 1: P", ["scripts/shared.py"]),
                make_failure("launchd", lbl + "q", lbl + "q", "exit 1: Q", ["scripts/shared.py"])]
        dispatch(pair, launcher=fake)
        st = load_state()
        res["file_set_lock"] = len(launched) == 1 and "file set busy" in (st["fixes"][pair[1]["sig"]].get("queued_reason") or "")
        save_state({"fixes": {}, "launches": []})
        launched.clear()
        fs = [make_failure("launchd", f"{lbl}{i}", f"{lbl}{i}", f"exit 1: E{i}", [f"scripts/f{i}.py"]) for i in range(5)]
        dispatch(fs, launcher=fake)
        res["rate_limit_3"] = len(launched) == 3
        dispatch(fs, launcher=fake)
        res["dedupe_one_attempt"] = len(launched) == 3          # same failures again → no new runs
        res["self_excluded"] = SELF_LABEL not in json.dumps([f["ident"] for f in launchd_failures()])
        res["forbidden"] = all(forbidden(p) for p in ["mission-control/data/bom-index-hvrr.json", "mission-control/data/decisions.json",
                                                       "mission-control/migrate.js", "mission-control/data/.decisions-token",
                                                       "/Users/exomac/.openclaw/secrets.json"]) and not forbidden("scripts/x.py")
        res["cmd_allow"] = cmd_allowed("openclaw cron edit abc-123 --clear-tools") and not cmd_allowed("msmtp a@b.c") \
            and not cmd_allowed("bash -c 'curl -X POST https://x'") and cmd_allowed("launchctl kickstart -k gui/501/" + lbl + "1")
        with state_lock():
            st = load_state()
            r = st["fixes"][launched[0]]
            r.update(status="awaiting_approval", decision_id="D-1")
            st["fixes"][launched[1]].update(status="applied", commits=["abcdef1234567"])
            save_state(st)
        st = load_state()
        res["status_lines"] = (fix_status_line("launchd", r["job"], st) == "→ fix awaiting your approval: D-1" and
                               fix_status_line("launchd", st["fixes"][launched[1]]["job"], st) == "→ fix applied (commit abcdef1)" and
                               fix_status_line("launchd", st["fixes"][launched[2]]["job"], st) == "→ fix in progress")
        global TEST
        t0 = TEST
        TEST = True
        body = decision_body(dict(r, sig=r["sig"], episode=1), {"cause": "bad path", "change": "x"})
        TEST = t0
        res["decision_shape"] = (body["title"].startswith("[TEST] Approve fix: ") and
                                 body["options"] == ["Approve fix (recommended)", "Hold", "Discuss"] and
                                 body["dedupeKey"].startswith("failure-fix:"))
        # recurrence after an applied fix → new episode (fix didn't hold)
        f1 = dict(next(f for f in fs if f["sig"] == launched[1]), last_fail_at=now_ts() + 120)
        acts = dispatch([f1], launcher=fake)
        res["recurrence_new_episode"] = any(x[1] == "recurred" for x in acts)
        res["verify_guard"] = verify_allowed("/usr/bin/python3 scripts/x.py --selftest") and \
            not verify_allowed("git apply p.patch && python3 x.py")
        res["parse_outcome"] = (parse_outcome('noise {"outcome":"staged","cause":"x","files":["a"]} tail') or {}).get("outcome") == "staged"
    finally:
        STATE, TEST_STATE, FF_DIR = saved
    ok = all(res.values())
    print(json.dumps(res), "->", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    global TEST
    a = sys.argv[1:]
    TEST = "--test" in a

    def opt(k):
        return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None
    if "--selftest" in a:
        sys.exit(selftest())
    cmd = a[0] if a else "run"
    if cmd == "collect":
        fs = collect(opt("--fixture"))
        if "--json" in a:
            print(json.dumps(fs, indent=1, default=str))
        else:
            print(f"{len(fs)} failure(s)")
            for f in fs:
                print(f"  {f['sig']}  {f['job']}: {f['error'][:110]}  files={f['file_set']}")
    elif cmd == "run":
        cmd_run(opt("--fixture"), dry="--dry-run" in a)
    elif cmd == "worker":
        sys.exit(worker(opt("--sig"), apply_mode="--apply" in a))
    elif cmd == "report":
        cmd_report(opt("--job"), opt("--error"), [opt("--file")] if opt("--file") else None)
    elif cmd == "status":
        st = load_state()
        if "--json" in a:
            print(json.dumps(st, indent=1, default=str))
        else:
            for r in st["fixes"].values():
                print(f"{r.get('status'):18} {r['sig']}  {r.get('job')}  {r.get('decision_id') or ''} {(r.get('commits') or [''])[0][:7]}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
