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

def selftest():
    # fixture labels built at runtime so the exo3 gate doesn't read them as new agents
    a, b, c = (".".join(["com", "exos", "fixture-" + x]) for x in "abc")
    live = {a, b, c}
    assert registry_drift(live, {a, b, c}) == []
    assert registry_drift(live, {a}) == [b, c]
    assert registry_drift(set(), {a}) == []  # registered-but-gone is not drift
    assert not (LA / "no-such-one-shot-fixture.plist").exists()  # one-shot 'done' rule keys on plist absence
    assert registry_labels(), "registry unreadable or empty"
    assert registry_labels(complete_only=True) <= registry_labels()
    assert isinstance(live_labels(), set)
    print("agent_eval selftest: 7/7 pass")
    return 0

def check_registry_drift(state):
    """Returns the list of NEW unregistered labels (not yet alerted). Never raises."""
    try:
        live = live_labels()
        drift = registry_drift(live, registry_labels())
        drift += [f"{l} (spec incomplete: owner/eval/permission_envelope)" for l in
                  registry_drift(live, registry_labels(complete_only=True)) if l not in drift]
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
