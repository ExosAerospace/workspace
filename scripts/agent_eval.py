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
Dry-run: AGENT_EVAL_DRYRUN=1 (no escalation, no state write).
"""
import json, os, sys, subprocess, plistlib, time, datetime
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
    print("agent_eval selftest: 18/18 pass")
    import cron_hygiene  # r2 cron-hygiene guards (secrets in prompts, model allowlist, transient crons)
    cron_hygiene.selftest()
    import mail_bridge_guard  # r2 launchd-residuals: Bridge password drift + IMAP auth storm
    mail_bridge_guard.selftest()
    import cron_prompt_guard  # r2-confirm-gaps: propose-only prompt guard for the 5 human-confirm-gap crons
    cron_prompt_guard.selftest()
    return 0

def check_registry_drift(state):
    """Returns the list of NEW unregistered labels (not yet alerted). Never raises."""
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
        if not loaded and one_shot and not (LA / f"{label}.plist").exists():
            why.append("completed (one-shot self-unloaded)")  # fired + removed its own plist = done
        elif not loaded:
            status = "FAIL"; why.append("not loaded in launchd")
        elif les not in (0, None):
            status = "FAIL"; why.append(f"LastExitStatus={les} (crashed)")
        if fails.get(short) or fails.get(label):
            status = "FAIL"; why.append(f"delivery_exhausted x{fails.get(short) or fails.get(label)}")
        # advisory WARN (staleness is best-effort; never escalated)
        if status == "OK":
            if not one_shot and age_h is not None and age_h > cad_h * th["warn_grace"]:
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

    npass = sum(1 for _, s, _, _ in results if s == "OK")
    nwarn = sum(1 for _, s, _, _ in results if s == "WARN")
    nfail = sum(1 for _, s, _, _ in results if s == "FAIL")
    log(f"eval: {npass} OK / {nwarn} WARN / {nfail} FAIL across {len(results)} agents")
    for short, s, why, owner in results:
        if s != "OK": log(f"  {s}: {short} — {why} (owner {owner})")

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
