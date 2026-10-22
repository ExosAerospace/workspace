#!/usr/bin/env python3
"""
agent_eval.py — ExO 3.0 GOVERN/ASSURE Pillar-1 eval runner (Eval Wave 1).

Non-invasive: reads existing signals for each monitored agent and scores it
against config/agent-evals.json — no changes to the agents themselves. Detects
Quiet Drift (a silently dead/failing agent) BEFORE it shows up in John's escalation.

Signals per agent:
  - launchd LastExitStatus (crash detection)     via `launchctl list <label>`
  - StandardOutPath mtime (ran-recently/staleness) via the agent's plist
  - fleet-events.jsonl in the window: delivery_exhausted (FAIL) / spooled (WARN)

Emits one eval event per agent to fleet_log; on a NEW FAIL, escalates one deduped
alert to the system channel via deliver. Runs hourly via launchd.
Declared config 'selftest' commands run at most once per 24h per agent (120s timeout, repo
root); a non-zero exit/timeout is an OUTPUT-eval FAIL (deduped alert with output tail).
Dry-run: AGENT_EVAL_DRYRUN=1 (no escalation, no state write).
AGENT_EVAL_SELFTEST_ONLY=<regex on label> restricts which selftests run (manual passes).
"""
import json, os, re, sys, subprocess, plistlib, time, datetime, hashlib, shutil, tempfile
from pathlib import Path

WS = Path("/Users/exomac/.openclaw/workspace")
CFG = WS / "config" / "agent-evals.json"
EVENTS = WS / "logs" / "fleet-events.jsonl"
STATE = WS / "state" / "agent-eval-state.json"
LOG = WS / "logs" / "agent-eval.log"
LA = Path.home() / "Library" / "LaunchAgents"
DRY = os.environ.get("AGENT_EVAL_DRYRUN") == "1"
sys.path.insert(0, str(WS / "scripts"))
import cron_telemetry  # OpenClaw cron store (read-only), interval math, cron scoring

def log(m):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f: f.write(f"[{ts}] {m}\n")
    print(m)

def launchctl_status(label):
    """Return (loaded: bool, LastExitStatus: int|None, pid: int|None)."""
    try:
        out = subprocess.run(["launchctl", "list", label], capture_output=True, text=True, timeout=15)
        if out.returncode != 0: return False, None, None  # not loaded
        les = pid = None
        for ln in out.stdout.splitlines():
            if "LastExitStatus" in ln: les = int(ln.split("=")[1].strip().rstrip(";"))
            if '"PID"' in ln: pid = int(ln.split("=")[1].strip().rstrip(";"))
        return True, les, pid
    except Exception:
        return False, None, None

def best_activity_mtime(label):
    """Newest mtime across the agent's known output artifacts (stdout/stderr logs,
    its own logfile, its state/log files). Best-effort liveness — advisory only."""
    cands = []
    p = LA / f"{label}.plist"
    script = None
    if p.exists():
        try:
            d = plistlib.load(open(p, "rb"))
            for k in ("StandardOutPath", "StandardErrorPath"):
                sp = d.get(k)
                if sp and os.path.exists(sp): cands.append(os.path.getmtime(sp))
            args = d.get("ProgramArguments", [])
            # run_logged.py wrapper: [python, run_logged.py, label, --, <real cmd...>]
            if isinstance(args, list) and len(args) > 4 and str(args[1]).endswith("/run_logged.py"):
                args = args[4:]
            import re as _re
            m = _re.search(r'/([^/\s]+)\.(py|js|sh)', ' '.join(args) if isinstance(args, list) else str(args))
            if m: script = m.group(1)
        except Exception:
            pass
    short = label.replace("com.exos.", "")
    for base in {short, (script or "")}:
        if not base: continue
        for d in (WS / "logs", WS / "state"):
            for f in d.glob(f"*{base}*"):
                try: cands.append(f.stat().st_mtime)
                except Exception: pass
    return max(cands) if cands else None

def window_events(since_ts):
    fails, warns = {}, {}
    if not EVENTS.exists(): return fails, warns
    for ln in EVENTS.read_text(errors="ignore").splitlines()[-5000:]:
        try: r = json.loads(ln)
        except Exception: continue
        try:
            t = datetime.datetime.fromisoformat(r["ts"]).timestamp()
        except Exception:
            continue
        if t < since_ts: continue
        who = (r.get("detail", {}) or {}).get("origin") or r.get("agent")
        if r.get("action") == "delivery_exhausted" or r.get("outcome") == "failed":
            fails[who] = fails.get(who, 0) + 1
        elif r.get("outcome") == "spooled" or r.get("level") == "warn":
            warns[who] = warns.get(who, 0) + 1
    return fails, warns

REGISTRY = WS / "mission-control" / "data" / "agent-registry.json"

SPEC_FIELDS = ("human_owner", "eval_suite", "permission_envelope")

def _blank(v):
    return str(v or "").strip().upper() in ("", "TBD", "MISSING", "NONE")

def registry_labels(complete_only=False):
    reg = json.load(open(REGISTRY))
    agents = reg.get("agents", [])
    if isinstance(agents, dict): agents = list(agents.values())
    return {a.get("label") for a in agents if a.get("label")
            and not (complete_only and any(_blank(a.get(f)) for f in SPEC_FIELDS))}

_SIDE_EFFECT_PE_RE = re.compile(
    r"deliver|discord post|smtp|msmtp|sends email|supabase.*write|quickbooks|qb write|openclaw message",
    re.IGNORECASE
)

def eval_coverage(registry_path=None):
    """Return dict: {total_agents, side_effecting, output_eval, liveness_only, coverage_pct}."""
    try:
        reg = json.load(open(registry_path or REGISTRY))
        agents = reg.get("agents", [])
        if isinstance(agents, dict): agents = list(agents.values())
        total = len([a for a in agents if a.get("label")])
        side = [a for a in agents if a.get("label") and
                _SIDE_EFFECT_PE_RE.search(str(a.get("permission_envelope") or ""))]
        output = [a for a in side if str(a.get("eval_type") or "").strip().lower() == "output"]
        liveness = [a for a in side if a not in output]
        pct = round(100.0 * len(output) / len(side), 1) if side else 100.0
        return {
            "total_agents": total,
            "side_effecting": len(side),
            "output_eval": len(output),
            "liveness_only": len(liveness),
            "coverage_pct": pct,
        }
    except Exception as e:
        return {"error": str(e)}

def live_labels():
    """Every com.exos.* agent that can run: plists in ~/Library/LaunchAgents plus
    anything loaded in launchd (catches jobs bootstrapped from outside that dir)."""
    live = {p.stem for p in LA.glob("com.exos.*.plist")}
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=15).stdout
        for ln in out.splitlines():
            parts = ln.split("\t")
            if len(parts) == 3 and parts[2].startswith("com.exos."): live.add(parts[2])
    except Exception:
        pass
    return live

def registry_drift(live, registered):
    """Live agents with no registry entry (no named owner / eval) — the exo3 gate only
    sees committed code, so a plist loaded outside git slips past it. Sorted list."""
    return sorted(l for l in live if l not in registered)

TRANSIENT_CLASS = "cron-class:transient-agent-reminder"
TRANSIENT_HORIZON_S = 31 * 86400

def transient_class_entry(path=None):
    """The registry's class spec for self-deleting one-shot reminder crons, or None if it is
    missing or incomplete (then every one-shot is drift again: fail-closed)."""
    try:
        agents = json.load(open(path or REGISTRY)).get("agents", [])
    except Exception:
        return None
    e = next((a for a in agents if a.get("label") == TRANSIENT_CLASS), None)
    return e if e and not any(_blank(e.get(f)) for f in SPEC_FIELDS) else None

def is_transient(j, now_s=None):
    """A one-shot (schedule kind 'at') that deletes itself after running and is due within
    31 days. Recurring, kept, or far-future one-shots are NOT transient and still need an entry."""
    if j.get("schedule_kind") != "at" or not j.get("delete_after_run"): return False
    nxt = j.get("next_run_at_ms")
    return nxt is None or nxt / 1000.0 <= (now_s or time.time()) + TRANSIENT_HORIZON_S

def cron_drift(jobs, reg_crons, transient_class=None, now_s=None):
    """OpenClaw crons (jobs: {id: {name,...}}) with no complete openclaw-cron registry entry,
    matched on cron_id so a rename is not drift. A job covered by the registered transient
    reminder class (is_transient) is not drift. Returns display strings."""
    out = []
    for jid, j in sorted(jobs.items()):
        e = reg_crons.get(jid)
        if not e and j.get("payload_kind") == "heartbeat": continue  # OpenClaw >= 2026.9.7 heartbeat ticks (not agents)
        if not e and transient_class and is_transient(j, now_s): continue
        name = "cron:%s (openclaw cron %s)" % (cron_telemetry.slug(j.get("name")), jid[:8])
        if not e: out.append(name)
        elif any(_blank(e.get(f)) for f in SPEC_FIELDS): out.append(name + " (spec incomplete: owner/eval/permission_envelope)")
    return out

def check_crons(cfg, state, now):
    """Score every live OpenClaw cron (config entry kind openclaw-cron, else defaults).
    Returns (results, new_fail_alerts) in the same shapes as the launchd loop. Never raises."""
    results, new_fails = [], []
    try:
        jobs = cron_telemetry.load_cron_jobs()
    except Exception as e:
        log(f"cron checks skipped (OpenClaw state DB unreadable): {e}")
        return results, new_fails
    by_id = {th.get("cron_id"): (label, th) for label, th in cfg["agents"].items() if th.get("kind") == "openclaw-cron"}
    for jid, job in jobs.items():
        label, th = by_id.get(jid) or ("cron:" + cron_telemetry.slug(job.get("name")), {})
        status, why = cron_telemetry.score_cron(job, th, now)
        if status == "SKIP": continue
        owner = th.get("owner", "John Quinn")
        results.append((label, status, "; ".join(why) or "healthy", owner))
        try:
            import fleet_log
            fleet_log.event("agent_eval", "govern", "eval", outcome=status.lower(), owner=owner,
                            detail={"agent": label, "cron_id": jid, "why": why})
        except Exception:
            pass
        if status == "FAIL" and state.get(label, {}).get("status") != "FAIL":
            new_fails.append((label, "; ".join(why), owner))
        state[label] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    return results, new_fails

def check_cron_hygiene(state, now):
    """exo3 r2 cron-hygiene guards (scripts/cron_hygiene.py): credentials in cron prompts (FAIL),
    enabled cron model not in allowlist (FAIL), anthropic cron with toolsAllow (WARN), unregistered
    non-transient cron run (WARN). One result per (label, check); state key 'hygiene:<label>'."""
    results, new_fails = [], []
    try:
        import cron_hygiene
        found = cron_hygiene.check(now)
    except Exception as e:
        log(f"cron hygiene checks skipped: {e}")
        return results, new_fails
    merged = {}
    for label, status, why in found:
        st, ws = merged.get(label, ("OK", []))
        merged[label] = ("FAIL" if "FAIL" in (st, status) else "WARN", ws + [why])
    for label, (status, whys) in merged.items():
        key = "hygiene:" + label
        results.append((key, status, "; ".join(whys), "John Quinn"))
        try:
            import fleet_log
            fleet_log.event("agent_eval", "govern", "cron_hygiene", outcome=status.lower(), owner="John Quinn",
                            detail={"agent": label, "why": whys})
        except Exception:
            pass
        if status == "FAIL" and state.get(key, {}).get("status") != "FAIL":
            new_fails.append((key, "; ".join(whys), "John Quinn"))
        state[key] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    for key in [k for k in state if k.startswith("hygiene:") and k[8:] not in merged]:
        state[key] = {"status": "OK", "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    return results, new_fails

def check_mail_bridge(state, now):
    """exo3 r2 launchd-residuals guard (scripts/mail_bridge_guard.py): secrets.json Bridge password drift vs
    ~/.config/exos/bridge-studio.pw (FAIL) and a multi-job Bridge auth-error storm in logs/runs (FAIL).
    State key 'mailbridge:<label>'; FAIL alert fires once on transition via the existing path."""
    results, new_fails = [], []
    try:
        import mail_bridge_guard
        found = mail_bridge_guard.check(now)
    except Exception as e:
        log(f"mail bridge checks skipped: {e}")
        return results, new_fails
    key = "mailbridge:" + mail_bridge_guard.LABEL
    status = "FAIL" if found else "OK"
    why = "; ".join(w for _, _, w in found) or "healthy"
    results.append((key, status, why, "John Quinn"))
    try:
        import fleet_log
        fleet_log.event("agent_eval", "govern", "mail_bridge", outcome=status.lower(), owner="John Quinn",
                        detail={"why": [w for _, _, w in found]})
    except Exception:
        pass
    if status == "FAIL" and state.get(key, {}).get("status") != "FAIL":
        new_fails.append((key, why, "John Quinn"))
    state[key] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    return results, new_fails

def check_cron_prompt_guard(state):
    """exo3 r2 (r2-confirm-gaps) scripts/cron_prompt_guard.py: the 5 human-confirm-gap crons must keep
    propose-only prompts (no autonomous wording / literal credentials; APAC live file not written by the
    scan). The guard emits its own fleet_log events. State key 'promptguard:<label>'."""
    results, new_fails = [], []
    try:
        import cron_prompt_guard
        found = cron_prompt_guard.check(dry=DRY)
    except Exception as e:
        log(f"cron prompt guard skipped: {e}")
        return results, new_fails
    for label, status, why, owner in found:
        key = "promptguard:" + label
        results.append((key, status, why, owner))
        if status == "FAIL" and state.get(key, {}).get("status") != "FAIL":
            new_fails.append((key, why, owner))
        state[key] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    return results, new_fails

def check_held_release_integrity(state, now, _decisions=None):
    """OUTPUT eval for gated-release loops (e.g. FNEX term sheet, 10/5): a counterparty card
    (dedupeKey '...-ms') must never be released (assignedTo outside @exosaero.com) while John's
    matching card ('...-jon') is still unanswered. FAIL names the prematurely released card."""
    results, new_fails = [], []
    try:
        decs = _decisions if _decisions is not None else json.load(open(WS / "mission-control" / "data" / "decisions.json"))
        decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    except Exception:
        return results, new_fails
    by_key = {str(d.get("dedupeKey") or ""): d for d in decs}
    bad = []
    for k, d in by_key.items():
        if not k.endswith("-ms"):
            continue
        who = str(d.get("assignedTo") or "")
        if str(d.get("status") or "").lower() not in ("open", "pending"):
            continue   # closed/superseded cards aren't live in front of the counterparty
        if "@" not in who or who.lower().endswith("@exosaero.com") or who.startswith("HELD"):
            continue
        jon = by_key.get(k[:-3] + "-jon")
        if jon and jon.get("status") != "answered":
            bad.append(f"{d.get('id')} released to {who} before John answered {jon.get('id')}")
    label = "output:held-release-integrity"
    status = "FAIL" if bad else "OK"
    results.append((label, status, "; ".join(bad) or "no premature releases", "John Quinn"))
    if bad and state.get(label, {}).get("status") != "FAIL":
        new_fails.append((label, "; ".join(bad), "John Quinn"))
    state[label] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    return results, new_fails

def check_duplicate_sends(state, now, _sent_dir=None):
    """OUTPUT-level eval: scan outbox/sent/ for duplicate (target, text-hash) pairs
    within 15 min, and entries where attempts>1 and last_error contains 'timeout'
    (pre-fix pattern: timed-out retries that landed multiple times).
    One deduped FAIL alert per offending source via the standard new_fail_alerts path."""
    results, new_fails = [], []
    sent_dir = Path(_sent_dir) if _sent_dir else (WS / "outbox" / "sent")
    if not sent_dir.exists():
        return results, new_fails

    scan_window_s = 2 * 3600    # look back 2h
    dup_window_s  = 15 * 60     # flag pairs within 15 min
    cutoff = now - scan_window_s

    recent = []
    for p in sent_dir.glob("*.json"):
        try:
            e = json.loads(p.read_text())
            raw_ts = e.get("sent") or e.get("last_attempt") or e.get("created")
            if not raw_ts:
                continue
            ts = datetime.datetime.fromisoformat(raw_ts).timestamp()
            if ts < cutoff:
                continue
            text_hash = hashlib.sha1((e.get("text") or "").encode()).hexdigest()[:12]
            recent.append({
                "file": p.name,
                "target": e.get("target", ""),
                "text_hash": text_hash,
                "ts": ts,
                "source": e.get("source", "unknown"),
                "attempts": int(e.get("attempts") or 1),
                "last_error": str(e.get("last_error") or ""),
            })
        except Exception:
            continue

    recent.sort(key=lambda x: x["ts"])

    offenders = {}  # source -> [description, ...]
    # Check (target, text_hash) duplicates within 15 min
    for i, a in enumerate(recent):
        for b in recent[i + 1:]:
            if b["ts"] - a["ts"] > dup_window_s:
                break
            if a["target"] == b["target"] and a["text_hash"] == b["text_hash"]:
                src = a["source"]
                offenders.setdefault(src, []).append(
                    f"dup target={a['target'][:40]} hash={a['text_hash']} "
                    f"({a['file']} + {b['file']})"
                )

    # Check attempts>1 where last send timed out (pre-fix retry pattern)
    for e in recent:
        if e["attempts"] > 1 and "timeout" in e["last_error"].lower():
            src = e["source"]
            offenders.setdefault(src, []).append(
                f"multi-attempt-timeout target={e['target'][:40]} "
                f"attempts={e['attempts']} file={e['file']}"
            )

    key_prefix = "dupsend:"
    for src, issues in offenders.items():
        key = key_prefix + src
        status = "FAIL"
        why = "; ".join(issues[:3])
        results.append((key, status, why, "John Quinn"))
        try:
            import fleet_log
            fleet_log.event("agent_eval", "govern", "dup_send", outcome="fail",
                            owner="John Quinn", detail={"source": src, "issues": issues})
        except Exception:
            pass
        if state.get(key, {}).get("status") != "FAIL":
            new_fails.append((key, why, "John Quinn"))
        state[key] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}

    # Clear resolved keys
    for key in [k for k in state if k.startswith(key_prefix)
                and k[len(key_prefix):] not in offenders]:
        state[key] = {"status": "OK", "ts": datetime.datetime.now().isoformat(timespec="seconds")}

    return results, new_fails


SELFTEST_EVERY_S = 24 * 3600   # each declared selftest runs at most once per 24h per agent
SELFTEST_TIMEOUT_S = 120
SELFTEST_RUN_BUDGET_S = 900    # wall-clock cap per hourly run; leftovers (oldest-first) run next hour
SELFTEST_TAIL_LINES = 10

def _run_selftest_cmd(cmd, timeout=SELFTEST_TIMEOUT_S, cwd=None):
    """Run one declared selftest command from the repo root. Returns (passed, rc, tail).
    rc None = timeout (whole process group killed). Selftests are fixture/GET-only by design."""
    import shlex, signal
    try:
        p = subprocess.Popen(shlex.split(cmd), cwd=str(cwd or WS), stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, start_new_session=True,
                             stdin=subprocess.DEVNULL)
    except Exception as e:
        return False, -1, f"could not start: {e}"
    try:
        out, _ = p.communicate(timeout=timeout)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        try: os.killpg(p.pid, signal.SIGKILL)
        except Exception: p.kill()
        try: out, _ = p.communicate(timeout=10)
        except Exception: out = ""
        rc = None
    lines = [l for l in (out or "").splitlines() if l.strip()][-SELFTEST_TAIL_LINES:]
    if rc is None: lines.append(f"TIMEOUT after {timeout}s")
    return rc == 0, rc, "\n".join(lines)

def check_selftests(cfg, state, now, _runner=None, only=None, budget_s=SELFTEST_RUN_BUDGET_S):
    """OUTPUT eval: execute each agent's declared config 'selftest' command at most once per 24h
    (last run in state 'selftest:<label>'.last_run). Non-zero exit or timeout = FAIL -> one deduped alert
    on transition (same new_fails path) carrying the last ~10 output lines; PASS is silent.
    Not-due agents carry their last status forward. Identical commands run once per pass.
    `only` = regex on label (AGENT_EVAL_SELFTEST_ONLY) to restrict a manual pass. Never raises."""
    results, new_fails = [], []
    runner = _runner or _run_selftest_cmd
    try:
        rx = re.compile(only) if only else None
    except re.error:
        rx = None
    todo = []
    for label, th in cfg.get("agents", {}).items():
        cmd = str(th.get("selftest") or "").strip()
        if not cmd or th.get("paused") or (rx and not rx.search(label)): continue
        todo.append((state.get("selftest:" + label, {}).get("last_run") or 0, label, th, cmd))
    todo.sort(key=lambda x: (x[0], x[1]))   # oldest-run first so the budget never starves anyone
    cache, t0 = {}, time.time()
    for last_run, label, th, cmd in todo:
        key, short = "selftest:" + label, label.replace("com.exos.", "")
        prev = state.get(key, {})
        owner = th.get("owner", "John Quinn")
        due = now - last_run >= SELFTEST_EVERY_S
        if due and cache and cmd not in cache and time.time() - t0 > budget_s:
            due = False   # out of budget this hour; stays due
        if not due:
            if prev.get("status"):
                results.append((key, prev["status"], "selftest not due (last %s)" % prev.get("ts", "?"), owner))
            continue
        if cmd not in cache:
            cache[cmd] = runner(cmd)
        passed, rc, tail = cache[cmd]
        status = "OK" if passed else "FAIL"
        why = "selftest PASS" if passed else (
            "selftest %s: %s\n%s" % ("TIMEOUT" if rc is None else f"exit {rc}", cmd, tail))
        results.append((key, status, why, owner))
        try:
            import fleet_log
            fleet_log.event("agent_eval", "govern", "selftest", outcome=status.lower(), owner=owner,
                            detail={"agent": label, "cmd": cmd, "rc": rc, "tail": tail[-1500:]})
        except Exception:
            pass
        if status == "FAIL" and prev.get("status") != "FAIL":
            new_fails.append((key, why, owner))
        state[key] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                      "last_run": now, "rc": rc, "tail": tail[-1500:]}
    return results, new_fails

def selftest_coverage(cfg, state):
    """(declared, passing): agents with a config selftest, and those whose last selftest PASSED."""
    decl = [l for l, th in cfg.get("agents", {}).items() if str(th.get("selftest") or "").strip()]
    return len(decl), sum(1 for l in decl if state.get("selftest:" + l, {}).get("status") == "OK")

def _selftest_runner_selftest():
    """Fixture cases for check_selftests: pass, fail, timeout, 24h throttle, dedupe, budget, real runner."""
    a, b, c = (".".join(["com", "exos", "fixture-st-" + x]) for x in "abc")
    cfg = {"agents": {a: {"owner": "O", "selftest": "fx pass"}, b: {"owner": "O", "selftest": "fx fail"},
                      c: {"owner": "O", "selftest": "fx hang"}, "x": {"owner": "O"}}}
    calls = []
    def fake(cmd):
        calls.append(cmd)
        return {"fx pass": (True, 0, "ok"), "fx fail": (False, 3, "\n".join(f"l{i}" for i in range(10))),
                "fx hang": (False, None, "partial\nTIMEOUT after 120s")}[cmd]
    st, now = {}, time.time()
    res, nf = check_selftests(cfg, st, now, _runner=fake)
    r = {k: (s, w) for k, s, w, _ in res}
    assert r["selftest:" + a][0] == "OK" and r["selftest:" + b][0] == "FAIL" and r["selftest:" + c][0] == "FAIL", r
    assert "exit 3" in r["selftest:" + b][1] and "l9" in r["selftest:" + b][1]       # tail in alert
    assert "TIMEOUT" in r["selftest:" + c][1]
    assert sorted(k for k, _, _ in nf) == ["selftest:" + b, "selftest:" + c]         # pass -> silent
    assert len(calls) == 3 and "selftest:x" not in st
    # 24h throttle: 1h later nothing reruns, statuses carry forward, no re-alert
    res2, nf2 = check_selftests(cfg, st, now + 3600, _runner=fake)
    assert len(calls) == 3 and nf2 == [] and len(res2) == 3
    assert all("not due" in w for _, _, w, _ in res2)
    # 24h+ later: reruns; a still-failing selftest does NOT re-alert (deduped)
    res3, nf3 = check_selftests(cfg, st, now + SELFTEST_EVERY_S + 1, _runner=fake)
    assert len(calls) == 6 and nf3 == []
    # identical commands run once per pass; only-filter; budget defers oldest-first
    cfg2 = {"agents": {a: {"selftest": "fx pass"}, b: {"selftest": "fx pass"}}}
    calls.clear(); check_selftests(cfg2, {}, now, _runner=fake); assert calls == ["fx pass"]
    calls.clear(); check_selftests(cfg, {}, now, _runner=fake, only="st-a$"); assert calls == ["fx pass"]
    calls.clear(); s4 = {}; check_selftests(cfg, s4, now, _runner=fake, budget_s=-1)
    assert len(calls) == 1 and sum(1 for k in s4 if k.startswith("selftest:")) == 1
    assert selftest_coverage(cfg, st) == (3, 1)
    # real runner: pass, fail (tail), timeout (process-group kill)
    py = sys.executable
    ok, rc, tail = _run_selftest_cmd(f"{py} -c \"print('hi')\"")
    assert ok and rc == 0 and tail == "hi"
    ok, rc, tail = _run_selftest_cmd(f"{py} -c \"import sys; [print(i) for i in range(30)]; sys.exit(2)\"")
    assert not ok and rc == 2 and tail.splitlines() == [str(i) for i in range(20, 30)]
    t = time.time(); ok, rc, tail = _run_selftest_cmd(f"{py} -c \"import time; time.sleep(30)\"", timeout=1)
    assert not ok and rc is None and "TIMEOUT" in tail and time.time() - t < 15
    ok, rc, _ = _run_selftest_cmd("/nonexistent/binary-fixture")
    assert not ok

def _dup_send_selftest():
    """Selftest fixture for check_duplicate_sends. Fixture labels don't use literal com.exos.*."""
    tmp = Path(tempfile.mkdtemp())
    sent_dir = tmp / "outbox" / "sent"
    sent_dir.mkdir(parents=True)

    def mk(fname, target, text, ts_offset, source, attempts=1, last_error=None):
        ts_s = time.time() + ts_offset
        ts_iso = datetime.datetime.fromtimestamp(ts_s, tz=datetime.timezone.utc).isoformat()
        e = {"id": fname, "created": ts_iso, "sent": ts_iso,
             "target": target, "text": text,
             "source": source, "attempts": attempts, "last_error": last_error}
        (sent_dir / (fname + ".json")).write_text(json.dumps(e))

    src_a = "-".join(["fixture", "alpha"])   # not a literal com.exos.* string
    src_b = "-".join(["fixture", "beta"])

    # Two identical (target, text) within 5 min -> dup flagged for src_a
    mk("d1", "channel:T1", "hello dup", -100, src_a)
    mk("d2", "channel:T1", "hello dup", -100 + 300, src_a)   # 5 min later
    # Same text, different target -> not a dup
    mk("d3", "channel:T2", "hello dup", -100, src_a)
    # Same target, different text -> not a dup
    mk("d4", "channel:T1", "different text", -100, src_a)
    # Same (target, text) but >15 min apart -> not flagged in the dup window
    mk("d5", "channel:T1", "old msg", -7200 + 10, src_a)    # near edge of 2h window
    mk("d6", "channel:T1", "old msg", -7200 + 10 + 1000, src_a)   # 1000s later = >15 min
    # attempts>1 with timeout -> flagged for src_b
    mk("d7", "channel:T3", "timeout post", -60, src_b, attempts=2, last_error="timeout (assumed delivered)")
    # attempts>1 but no timeout -> NOT flagged by the timeout check (still no dup either)
    mk("d8", "channel:T3", "error post", -60, src_b, attempts=2, last_error="network error")

    try:
        now_t = time.time()
        state = {}
        res, fails = check_duplicate_sends(state, now_t, _sent_dir=sent_dir)
        src_keys = {r[0].replace("dupsend:", "") for r in res}
        assert src_a in src_keys, f"{src_a} expected in results, got {src_keys}"
        assert src_b in src_keys, f"{src_b} expected in results (timeout), got {src_keys}"
        # all FAIL
        assert all(r[1] == "FAIL" for r in res), "expected all FAIL"
        # new_fails on first run
        assert len(fails) == len(res), "first run should have all as new_fails"
        # second run: same state -> no new_fails
        _, fails2 = check_duplicate_sends(state, now_t, _sent_dir=sent_dir)
        assert fails2 == [], f"dedup: expected no new fails on re-run, got {fails2}"
        # empty dir -> no results
        empty_dir = tmp / "empty" / "sent"
        empty_dir.mkdir(parents=True)
        res_empty, _ = check_duplicate_sends({}, now_t, _sent_dir=empty_dir)
        assert res_empty == [], "empty dir should yield no results"
        # nonexistent dir -> no results, no crash
        res_nx, _ = check_duplicate_sends({}, now_t, _sent_dir=tmp / "nonexistent")
        assert res_nx == [], "nonexistent dir should yield no results"
    finally:
        shutil.rmtree(tmp)


def selftest():
    # fixture labels built at runtime so the exo3 gate doesn't read them as new agents
    a, b, c = (".".join(["com", "exos", "fixture-" + x]) for x in "abc")
    live = {a, b, c}
    assert registry_drift(live, {a, b, c}) == []
    assert registry_drift(live, {a}) == [b, c]
    assert registry_drift(set(), {a}) == []  # registered-but-gone is not drift
    assert cron_drift({"hb": {"name": "heartbeat-main", "payload_kind": "heartbeat"}}, {}) == []  # platform heartbeat row is not drift
    assert cron_drift({"sc": {"name": "skill-review", "payload_kind": "agentTurn"}}, {}) != []  # system AI job still is
    assert not (LA / "no-such-one-shot-fixture.plist").exists()  # one-shot 'done' rule keys on plist absence
    assert registry_labels(), "registry unreadable or empty"
    assert registry_labels(complete_only=True) <= registry_labels()
    assert isinstance(live_labels(), set)
    # openclaw cron drift (matched on cron_id; rename is not drift) + liveness scoring
    full = {"human_owner": "x", "eval_suite": "x", "permission_envelope": "x"}
    jobs = {"id-a": {"name": "Fixture A"}, "id-b": {"name": "Fixture B"}}
    assert cron_drift(jobs, {"id-a": full, "id-b": full}) == []
    d = cron_drift(jobs, {"id-a": full})
    assert len(d) == 1 and d[0].startswith("cron:fixture-b")
    assert "spec incomplete" in cron_drift(jobs, {"id-a": full, "id-b": dict(full, eval_suite="TBD")})[0]
    # transient one-shot reminder class (r2-cron-hygiene): only at+delete_after_run within 31d, only if class registered
    now0 = time.time()
    tj = {"id-a": {"name": "Fixture A"},
          "id-t": {"name": "Fixture T", "schedule_kind": "at", "delete_after_run": 1, "next_run_at_ms": (now0 + 3600) * 1000},
          "id-k": {"name": "Fixture K", "schedule_kind": "at", "delete_after_run": 0, "next_run_at_ms": (now0 + 3600) * 1000},
          "id-f": {"name": "Fixture F", "schedule_kind": "at", "delete_after_run": 1, "next_run_at_ms": (now0 + 90 * 86400) * 1000},
          "id-r": {"name": "Fixture R", "schedule_kind": "cron", "delete_after_run": 1}}
    d = cron_drift(tj, {"id-a": full}, full, now0)
    assert sorted(x.split(" ")[0] for x in d) == ["cron:fixture-f", "cron:fixture-k", "cron:fixture-r"], d
    assert len(cron_drift(tj, {"id-a": full}, None, now0)) == 4  # class missing/incomplete -> fail-closed
    assert transient_class_entry("/nonexistent") is None
    now = time.time()
    daily = {"enabled": 1, "schedule_kind": "cron", "schedule_expr": "0 9 * * *", "consecutive_errors": 0,
             "last_run_at_ms": (now - 3600) * 1000}
    th = {"warn_grace": 2.5, "fail_consecutive_errors": 2}
    assert cron_telemetry.score_cron(daily, th, now)[0] == "OK"
    assert cron_telemetry.score_cron(dict(daily, last_run_at_ms=(now - 4 * 86400) * 1000), th, now)[0] == "WARN"
    assert cron_telemetry.score_cron(dict(daily, consecutive_errors=3), th, now)[0] == "FAIL"
    assert cron_telemetry.score_cron(dict(daily, enabled=0), th, now)[0] == "SKIP"
    assert isinstance(cron_telemetry.registry_crons(REGISTRY), dict)
    _dup_send_selftest()
    _selftest_runner_selftest()
    print("agent_eval selftest-runner: pass/fail/timeout/24h-throttle/dedupe/budget pass")
    # eval_coverage: reads live registry; just verify keys and types are correct
    cov = eval_coverage()
    assert "error" not in cov, f"eval_coverage returned error: {cov}"
    assert isinstance(cov["coverage_pct"], float)
    assert cov["side_effecting"] >= cov["output_eval"]
    assert 0.0 <= cov["coverage_pct"] <= 100.0
    print(f"eval_coverage: {cov['output_eval']}/{cov['side_effecting']} = {cov['coverage_pct']}%")
    print("agent_eval selftest: 27/27 pass")
    import cron_hygiene  # r2 cron-hygiene guards (secrets in prompts, model allowlist, transient crons)
    cron_hygiene.selftest()
    import mail_bridge_guard  # r2 launchd-residuals: Bridge password drift + IMAP auth storm
    mail_bridge_guard.selftest()
    import cron_prompt_guard  # r2-confirm-gaps: propose-only prompt guard for the 5 human-confirm-gap crons
    cron_prompt_guard.selftest()
    import drop_tombstone_exo3  # John 10/18: a human drop is permanent across generators (PAY-7143 x6)
    assert drop_tombstone_exo3.selftest(), "drop_tombstone_exo3 selftest FAIL"
    return 0

AUTO_REG_DECISION = "exo3-auto-register-crons"

def auto_register_enabled():
    """Auto-registration of session-created OpenClaw crons is OFF until Jon approves the Decision
    (dedupeKey exo3-auto-register-crons) with a HUMAN click; approval is then persisted in config."""
    try:
        cfg = json.load(open(CFG))
        if cfg.get("auto_register_crons"): return True
        decs = json.load(open(WS / "mission-control" / "data" / "decisions.json"))
        decs = decs if isinstance(decs, list) else decs.get("decisions", [])
        d = next((x for x in decs if x.get("dedupeKey") == AUTO_REG_DECISION), None)
        if d and d.get("status") == "answered" and d.get("answeredByEmail") and \
           str(d.get("answer") or "").lower().startswith(("approve", "apply", "yes")):
            cfg["auto_register_crons"] = True; cfg["auto_register_crons_approved"] = d.get("id")
            json.dump(cfg, open(CFG, "w"), indent=1)
            return True
    except Exception as e:
        log(f"auto-register flag check failed: {e}")
    return False

def auto_register_crons():
    """Register unregistered OpenClaw crons from their live definition (scripts/register_cron.py)."""
    done = []
    try:
        jobs = cron_telemetry.load_cron_jobs(); reg = cron_telemetry.registry_crons(REGISTRY)
        for jid in cron_drift_ids(jobs, reg):
            r = subprocess.run([sys.executable, str(WS / "scripts" / "register_cron.py"), jid],
                               capture_output=True, text=True, timeout=90)
            if r.returncode == 0: done.append(r.stdout.strip())
            else: log(f"auto-register {jid[:8]} failed: {r.stderr.strip()[:200]}")
    except Exception as e:
        log(f"auto-register skipped: {e}")
    return done

def cron_drift_ids(jobs, reg_crons):
    tc = transient_class_entry()
    return [jid for jid, j in jobs.items() if not reg_crons.get(jid) and j.get("payload_kind") != "heartbeat"
            and not (tc and is_transient(j, None))]

def self_retired(label):
    """A launchd job that unloads ITSELF when its work is done (script docstring says self-retire /
    self-unload) and whose last recorded run exited 0 is finished, not dead. Keeps finished one-shot
    watchers from paging as 'not loaded' (false FAIL, naftu-attestation-ready 2026-10-07)."""
    try:
        pl = LA / f"{label}.plist"
        if pl.exists():
            args = " ".join(plistlib.load(open(pl, "rb")).get("ProgramArguments") or [])
            cands = [c for c in re.findall(r"(/Users/exomac/\.openclaw/workspace/scripts/[\w.\-]+\.py)", args)
                     if not c.endswith("/run_logged.py") and not c.endswith("/task_ledger.py")]
            if not cands or not re.search(r"self[- ]?(retire|unload)", open(cands[-1], errors="replace").read(4000), re.I):
                return False
        last = None
        for f in sorted((WS / "logs" / "runs").glob("*.jsonl"))[-14:]:
            for ln in open(f):
                if f'"{label}"' in ln:
                    try: last = json.loads(ln)
                    except Exception: pass
        # self-bootout SIGTERMs its own process, so the final run of a self-retiring job reads 143/SIGTERM
        return bool(last and (last.get("exit_code") in (0, 143) or last.get("signal") == "SIGTERM"))
    except Exception:
        return False

def auto_register_internal_oneshots():
    """D-7281949 extension (2026-10-07): register unregistered launchd jobs that are internal-only,
    self-removing reminders — script docstring says it self-unloads AND every email address in the
    script is @exosaero.com (Discord posts allowed). Anything that can reach an outside address still
    alerts. Entry is derived from the plist + script and carries an OUTPUT eval (exo3 gate R5)."""
    done = []
    try:
        reg = json.load(open(REGISTRY)); have = {a.get("label") for a in reg.get("agents", [])}
        for label in registry_drift(live_labels(), have):
            pl = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
            if not pl.exists(): continue
            spec = plistlib.load(open(pl, "rb"))
            args = " ".join(spec.get("ProgramArguments") or [])
            cands = [c for c in re.findall(r"(/Users/exomac/\.openclaw/workspace/scripts/[\w.\-]+\.py)", args)
                     if not c.endswith("/run_logged.py") and not c.endswith("/task_ledger.py")]
            m = re.match(r"(.*)", cands[-1]) if cands else None
            if not m or not os.path.exists(m.group(1)): continue
            src = open(m.group(1), encoding="utf-8", errors="replace").read()
            doc = (re.search(r'"""(.*?)"""', src, re.S) or [None, ""])[1].strip()
            if not re.search(r"self-unload", doc, re.I): continue
            emails = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", src))
            if any(not e.lower().endswith("@exosaero.com") for e in emails if not e.lower().endswith("@pm.me")): continue
            when = spec.get("StartCalendarInterval") or ({"every_s": spec.get("StartInterval")} if spec.get("StartInterval") else {})
            reg["agents"].append({
                "label": label, "script": os.path.basename(m.group(1)), "kind": "one-shot", "schedule": json.dumps(when),
                "purpose": re.sub(r"\s+", " ", doc)[:300], "stack_layer": "ORCHESTRATE", "autonomy_tier": "Execute-within-bounds",
                "human_owner": "John Quinn",
                "permission_envelope": "internal only: emails/posts to " + (", ".join(sorted(emails)) or "Discord") + "; removes its own plist. No external recipients (auto-verified).",
                "memory_boundary": "none (stateless)", "escalation": "recipient acts on the reminder", "eval_type": "output",
                "eval_suite": "one-shot liveness (exit 0, self-unload) + OUTPUT: agent_eval check_duplicate_sends; recipients verified internal at registration",
                "telemetry": str(spec.get("StandardOutPath") or ""), "reusability_scope": "single-use", "risk_tier": "LOW",
                "lifecycle": "self-removing", "registered": datetime.date.today().isoformat(),
                "envelope_source": "agent_eval auto-registration (D-7281949 ext.): plist + script scan"})
            done.append(label)
        if done:
            json.dump(reg, open(REGISTRY, "w"), indent=1, ensure_ascii=False)
    except Exception as e:
        log(f"auto-register one-shots skipped: {e}")
    return done

def check_registry_drift(state):
    """Returns the list of NEW unregistered labels (not yet alerted). Never raises."""
    if auto_register_enabled():
        for line in auto_register_internal_oneshots():
            log(f"auto-registered internal one-shot: {line}")
            state.setdefault("_auto_registered", []).append(
                {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "line": f"{line} (internal one-shot)"})
        for line in auto_register_crons():
            log(f"auto-registered: {line}")
            state.setdefault("_auto_registered", []).append(
                {"ts": datetime.datetime.now().isoformat(timespec="seconds"), "line": line})
    try:
        live = live_labels()
        drift = registry_drift(live, registry_labels())
        drift += [f"{l} (spec incomplete: owner/eval/permission_envelope)" for l in
                  registry_drift(live, registry_labels(complete_only=True)) if l not in drift]
        try:
            drift += cron_drift(cron_telemetry.load_cron_jobs(), cron_telemetry.registry_crons(REGISTRY),
                                transient_class_entry())
        except Exception as e:
            log(f"cron registry drift check skipped: {e}")
    except Exception as e:
        log(f"registry drift check skipped: {e}")
        return []
    prev = set(state.get("_registry_drift", {}).get("labels", []))
    state["_registry_drift"] = {"labels": drift, "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    if drift: log(f"registry drift: {len(drift)} unregistered live agent(s): {', '.join(drift)}")
    else: log("registry drift: 0 — every live com.exos.* agent is registered")
    try:
        import fleet_log
        fleet_log.event("agent_eval", "govern", "registry_drift", outcome="fail" if drift else "ok",
                        owner="John Quinn", detail={"unregistered": drift})
    except Exception:
        pass
    return [l for l in drift if l not in prev]

def main():
    if "--selftest" in sys.argv: return selftest()
    cfg = json.load(open(CFG))
    win_h = cfg.get("window_hours", 26)
    now = time.time()
    since = now - win_h * 3600
    fails, warns = window_events(since)
    state = {}
    if STATE.exists():
        try: state = json.load(open(STATE))
        except Exception: state = {}
    results = []
    new_fail_alerts = []
    for label, th in cfg["agents"].items():
        if th.get("kind") == "openclaw-cron": continue  # scored by check_crons()
        loaded, les, pid = launchctl_status(label)
        mt = best_activity_mtime(label)
        age_h = (now - mt) / 3600 if mt else None
        cad_h = th["cadence_s"] / 3600
        short = label.replace("com.exos.", "")
        status, why = "OK", []
        one_shot = th.get("one_shot", False)
        # FAIL only on reliable signals (keeps escalations trustworthy)
        if th.get("host") and th.get("host") != "studio":
            why.append(f"runs on {th['host']} (liveness checked remotely)")  # e.g. failover-monitor on the Mini
        elif th.get("paused"):
            why.append(f"paused on purpose: {th.get('paused')}")
        elif not loaded and one_shot and not (LA / f"{label}.plist").exists():
            why.append("completed (one-shot self-unloaded)")  # fired + removed its own plist = done
        elif not loaded and self_retired(label):
            why.append("completed (self-retired after a clean last run)")  # e.g. naftu-attestation-ready 10/7
        elif not loaded:
            status = "FAIL"; why.append("not loaded in launchd")
        elif les not in (0, None) and not pid:
            status = "FAIL"; why.append(f"LastExitStatus={les} (crashed)")
        elif les not in (0, None):
            why.append(f"running (pid {pid}); previous exit {les}")   # e.g. SIGTERM from a deliberate restart
        if fails.get(short) or fails.get(label):
            status = "FAIL"; why.append(f"delivery_exhausted x{fails.get(short) or fails.get(label)}")
        # advisory WARN (staleness is best-effort; never escalated)
        if status == "OK":
            if not one_shot and not any(w.startswith("completed") for w in why) and age_h is not None and age_h > cad_h * th["warn_grace"]:
                status = "WARN"; why.append(f"possibly stale (no activity {age_h:.0f}h)")
            elif warns.get(short):
                status = "WARN"; why.append(f"spooled x{warns.get(short)}")
        results.append((short, status, "; ".join(why) or "healthy", th["owner"]))
        try:
            import fleet_log
            fleet_log.event("agent_eval", "govern", "eval", outcome=status.lower(),
                            owner=th["owner"], detail={"agent": label, "why": why, "age_h": age_h})
        except Exception:
            pass
        prev = state.get(label, {}).get("status")
        if status == "FAIL" and prev != "FAIL":
            new_fail_alerts.append((short, "; ".join(why), th["owner"]))
        state[label] = {"status": status, "ts": datetime.datetime.now().isoformat(timespec="seconds")}

    cron_results, cron_fails = check_crons(cfg, state, now)
    results += cron_results
    new_fail_alerts += cron_fails
    hy_results, hy_fails = check_cron_hygiene(state, now)
    results += hy_results
    new_fail_alerts += hy_fails
    pg_results, pg_fails = check_cron_prompt_guard(state)
    results += pg_results
    new_fail_alerts += pg_fails
    mb_results, mb_fails = check_mail_bridge(state, now)
    results += mb_results
    new_fail_alerts += mb_fails
    ds_results, ds_fails = check_duplicate_sends(state, now)
    results += ds_results
    new_fail_alerts += ds_fails
    hr_results, hr_fails = check_held_release_integrity(state, now)
    results += hr_results
    new_fail_alerts += hr_fails
    st_results, st_fails = check_selftests(cfg, state, now, only=os.environ.get("AGENT_EVAL_SELFTEST_ONLY"))
    results += st_results
    new_fail_alerts += st_fails

    npass = sum(1 for _, s, _, _ in results if s == "OK")
    nwarn = sum(1 for _, s, _, _ in results if s == "WARN")
    nfail = sum(1 for _, s, _, _ in results if s == "FAIL")
    log(f"eval: {npass} OK / {nwarn} WARN / {nfail} FAIL across {len(results)} agents")
    for short, s, why, owner in results:
        if s != "OK": log(f"  {s}: {short} — {why} (owner {owner})")
    for short, s, why, owner in st_results:
        if s == "OK" and "PASS" in why: log(f"  selftest PASS: {short}")

    cov = eval_coverage()
    if "error" not in cov:
        cov["selftest_declared"], cov["selftest_pass"] = selftest_coverage(cfg, state)
        log(f"eval-coverage: {cov['output_eval']}/{cov['side_effecting']} side-effecting agents "
            f"have output evals ({cov['coverage_pct']}%); {cov['liveness_only']} still liveness-only; "
            f"selftests passing {cov['selftest_pass']}/{cov['selftest_declared']} declared")
        try:
            import fleet_log
            fleet_log.event("agent_eval", "govern", "eval_coverage", outcome="info",
                            owner="John Quinn", detail=cov)
        except Exception:
            pass

    new_drift = check_registry_drift(state)
    if new_drift and not DRY:
        msg = ("[[reply_to_current]] ⚠️ exo3 registry drift: live agent(s) running with NO registry entry "
               "(no named owner / eval):\n" + "\n".join(f"• {l}" for l in new_drift) +
               "\nRegister each in mission-control/data/agent-registry.json (owner + eval) or unload it.")
        try:
            import deliver
            deliver.deliver(msg, source="agent_eval")
        except Exception as e:
            log(f"drift escalation send failed: {e}")

    if new_fail_alerts and not DRY:
        lines = "\n".join(f"• {a} — {w} (owner {o})" for a, w, o in new_fail_alerts)
        msg = ("[[reply_to_current]] ⚠️ Agent eval FAIL (Quiet-Drift guard):\n" + lines +
               "\nThese send/critical agents look dead or are failing delivery. Check logs/agent-eval.log.")
        try:
            import deliver
            deliver.deliver(msg, source="agent_eval")
        except Exception as e:
            log(f"escalation send failed: {e}")

    if not DRY:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        json.dump(state, open(STATE, "w"), indent=2)
    return 0

if __name__ == "__main__":
    sys.exit(main())
