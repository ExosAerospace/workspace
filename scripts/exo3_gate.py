#!/usr/bin/env python3
"""
exo3_gate.py — enforced ExO3 design-compliance gate for code commits.

Runs as a shared-tree pre-commit hook. It classifies the staged change and
BLOCKS the commit on exactly ONE high-precision ExO3 invariant, so routine
commits (and the crons that share this working tree) are never jammed:

  BLOCK  A NEW `com.exos.<id>` agent appears in staged additions but is NOT
         registered in mission-control/data/agent-registry.json with a named
         human owner + an eval. (ExO3 Fiduciary-Wedge + Trusted-Evals pillars:
         "no new autonomous agent without an owner and an eval.")

Everything softer is a NON-BLOCKING WARN (printed, never stops the commit):
  WARN   New AI-managed page/module without the `-exo3` naming convention.
  WARN   A known DECIDE/GOVERN mechanism changed without a decision-trace /
         eval / fleet_log reference (Four-Pillars nudge).

SAFETY — FAIL-OPEN. Any internal error prints a notice and exits 0. A bug in
this gate must never brick commits for the whole Exo fleet. Only a deliberate
BLOCK exits 2; the hook stops the commit ONLY on exit code 2.

OVERRIDE (logged): env `EXO3_GATE_OVERRIDE="reason"` or `[exo3-skip: reason]`
in the commit message. Every run is logged with a correlation id to
logs/exo3-gate.jsonl.

Usage:
  python3 scripts/exo3_gate.py --staged        # pre-commit: check staged diff
  python3 scripts/exo3_gate.py --check f ...    # check specific files (current)
  python3 scripts/exo3_gate.py --report         # advisory only, always exit 0
  python3 scripts/exo3_gate.py --selftest       # eval: synthetic pass + block
"""
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "mission-control", "data", "agent-registry.json")
LOG = os.path.join(ROOT, "logs", "exo3-gate.jsonl")

AGENT_ID_RE = re.compile(r"com\.exos\.[a-z0-9][a-z0-9._-]*")
# markers that indicate an agent is actually being *created/scheduled* (not just mentioned)
AGENT_CREATE_MARKERS = ("launchd", "launchagents", "startinterval",
                        "startcalendarinterval", ".plist", "launchctl")
# Known DECIDE/GOVERN mechanisms — changes here should carry a decision-trace / eval.
DECIDE_GOVERN_FILES = {
    "opportunity_processor.py", "decision_triage.py", "research_agent.py",
    "overnight_resolver.py", "decision-note-router.py", "crm_dd_engine.py",
    "gen_blocked_senders.py", "legacy_triage_decisions.py",
}
FOUR_PILLAR_MARKERS = ("decision_trace", "fleet_log", "agent_eval", "eval_suite", "mtp")


def _run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=30)


def registry_labels():
    try:
        j = json.load(open(REGISTRY))
        return {a.get("label", "") for a in (j.get("agents") or []) if a.get("label")}
    except Exception:
        return set()


def staged_files():
    r = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return [f for f in r.stdout.splitlines() if f.strip()]


def added_lines_by_file():
    """Return {path: [added lines]} from the staged diff (new content only)."""
    out = {}
    r = _run(["git", "diff", "--cached", "--unified=0", "--diff-filter=ACM"])
    cur = None
    for ln in r.stdout.splitlines():
        if ln.startswith("+++ b/"):
            cur = ln[6:]
            out.setdefault(cur, [])
        elif ln.startswith("+") and not ln.startswith("+++") and cur is not None:
            out[cur].append(ln[1:])
    return out


def new_files():
    r = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=A"])
    return [f for f in r.stdout.splitlines() if f.strip()]


def classify(added, files, newf, labels):
    """Return list of findings: {level, rule, file, msg, fix}."""
    findings = []
    # R1 (BLOCK): a new com.exos.<id> in added content, in an agent-creation context,
    # not registered in agent-registry.json.
    for path, lines in added.items():
        # The gate's own source (and test fixtures) carry synthetic agent ids — don't scan them.
        if path.endswith("scripts/exo3_gate.py") or "/tests/" in path or os.path.basename(path).startswith("test_"):
            continue
        blob = "\n".join(lines).lower()
        is_create_ctx = path.endswith(".plist") or any(m in blob for m in AGENT_CREATE_MARKERS)
        if not is_create_ctx:
            continue
        for m in AGENT_ID_RE.findall("\n".join(lines)):
            aid = m.rstrip(".-_")
            if aid in labels:
                continue
            # tolerate the gate registering itself
            if aid == "com.exos.exo3-gate":
                continue
            findings.append({
                "level": "BLOCK", "rule": "R1-agent-unregistered", "file": path,
                "msg": f"New agent '{aid}' is created here but is not in agent-registry.json.",
                "fix": (f"Add '{aid}' to mission-control/data/agent-registry.json (agents[]) with a named "
                        "human_owner (Fiduciary Wedge) + an eval_suite, before committing. "
                        "No new autonomous agent without an owner and an eval."),
            })
    # de-dup R1 by (aid,file)
    seen = set(); dedup = []
    for f in findings:
        k = (f["rule"], f.get("msg"))
        if k in seen: continue
        seen.add(k); dedup.append(f)
    findings = dedup

    # R2 (WARN): new AI-managed page/module without -exo3 naming.
    for f in newf:
        base = os.path.basename(f).lower()
        if f.startswith("mission-control/") and f.endswith(".html"):
            title = ""
            try:
                txt = open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read(4000)
                mt = re.search(r"<title>(.*?)</title>", txt, re.S | re.I)
                title = (mt.group(1) if mt else "").lower()
            except Exception:
                pass
            if "exo3" not in base and "exo3" not in title:
                findings.append({
                    "level": "WARN", "rule": "R2-exo3-naming", "file": f,
                    "msg": "New Mission Control page — confirm whether it's an AI-managed program.",
                    "fix": "If AI-managed, name it <Name>-exo3 (keep the descriptive subtitle). If it's a plain view, ignore.",
                })

    # R3 (WARN): DECIDE/GOVERN mechanism changed without a Four-Pillars marker.
    for f in files:
        if os.path.basename(f) in DECIDE_GOVERN_FILES:
            lines = added.get(f, [])
            blob = "\n".join(lines).lower()
            if lines and not any(m in blob for m in FOUR_PILLAR_MARKERS):
                findings.append({
                    "level": "WARN", "rule": "R3-decide-govern-pillars", "file": f,
                    "msg": "DECIDE/GOVERN mechanism changed without a decision-trace / eval / fleet_log reference.",
                    "fix": "Consider emitting a decision_trace, a corr-ID via fleet_log, or an eval threshold (Four Pillars).",
                })
    # R4 (WARN): an agent's script changed but no improvement-ledger entry was staged (exo3 VALIDATE
    # step, Jon 2026-10-04 — every fix is a hypothesis measured before/after against telemetry).
    try:
        reg = json.load(open(os.path.join(ROOT, "mission-control", "data", "agent-registry.json"))).get("agents", [])
        agent_scripts = {os.path.basename(str(a.get("script") or "").split()[0]) for a in reg if a.get("script")}
    except Exception:
        agent_scripts = set()
    if "mission-control/data/improvement-ledger.json" not in files:
        for f in files:
            if f.startswith("scripts/") and f.endswith(".py") and f not in newf and os.path.basename(f) in agent_scripts:
                findings.append({
                    "level": "WARN", "rule": "R4-improvement-ledger", "file": f,
                    "msg": "Agent script changed without an improvement-ledger entry (no before/after measurement).",
                    "fix": "If this is a fix/tuning: python3 scripts/improvement_ledger.py add --agent <label> --change <commit> "
                           "--hypothesis '...' --metrics reliability,turnaround[,cost] — the weekly RSI §16 verdicts it in 7 days.",
                })
    return findings


def override_reason(mode):
    env = os.environ.get("EXO3_GATE_OVERRIDE", "").strip()
    if env:
        return env
    # best-effort: scan the commit message file for [exo3-skip: reason]
    for cand in (os.environ.get("COMMIT_EDITMSG"), os.path.join(ROOT, ".git", "COMMIT_EDITMSG")):
        try:
            if cand and os.path.exists(cand):
                m = re.search(r"\[exo3-skip:\s*([^\]]+)\]", open(cand, encoding="utf-8", errors="replace").read(), re.I)
                if m:
                    return m.group(1).strip()
        except Exception:
            pass
    return ""


def log_run(mode, findings, decision, override=""):
    rec = {
        "at": datetime.now(timezone.utc).isoformat(),
        "corr_id": uuid.uuid4().hex[:12],
        "agent": "com.exos.exo3-gate",
        "mode": mode,
        "decision": decision,
        "blocks": [f["rule"] for f in findings if f["level"] == "BLOCK"],
        "warns": [f["rule"] for f in findings if f["level"] == "WARN"],
        "override": override,
    }
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import fleet_log  # type: ignore
        fleet_log.emit("com.exos.exo3-gate", "gate_run", rec)  # best-effort structured logger
        return
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def render(findings):
    blocks = [f for f in findings if f["level"] == "BLOCK"]
    warns = [f for f in findings if f["level"] == "WARN"]
    for f in blocks:
        print(f"  \033[31m✖ BLOCK\033[0m [{f['rule']}] {f['file']}\n    {f['msg']}\n    → {f['fix']}")
    for f in warns:
        print(f"  \033[33m▲ WARN\033[0m  [{f['rule']}] {f['file']}\n    {f['msg']}\n    → {f['fix']}")
    return blocks, warns


def gate(mode):
    labels = registry_labels()
    files = staged_files() if mode != "check" else sys.argv[2:]
    added = added_lines_by_file() if mode != "check" else {
        f: (open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read().splitlines()
            if os.path.exists(os.path.join(ROOT, f)) else []) for f in files
    }
    newf = new_files() if mode != "check" else files
    findings = classify(added, files, newf, labels)
    blocks, warns = render(findings)
    if not findings:
        print("  \033[32m✓ exo3-gate: no agent/DECIDE/GOVERN concerns in staged change.\033[0m")
    if blocks:
        ovr = override_reason(mode)
        if ovr:
            print(f"  \033[33m⚠ exo3-gate OVERRIDDEN\033[0m: {ovr} (logged)")
            log_run(mode, findings, "override", ovr)
            return 0
        print("\n  exo3-gate blocked this commit. Register the agent (owner + eval), or override with:")
        print("    EXO3_GATE_OVERRIDE=\"why\" git commit ...   or add \"[exo3-skip: why]\" to the message.")
        log_run(mode, findings, "block")
        return 2
    log_run(mode, findings, "pass")
    return 0


def selftest():
    """ExO3 eval for the gate itself: a clean change passes, a synthetic new agent blocks."""
    labels = {"com.exos.assignment-notifier"}
    ok1 = classify({"scripts/foo.py": ["print('hi')"]}, ["scripts/foo.py"], [], labels)
    case1 = not any(f["level"] == "BLOCK" for f in ok1)
    bad = classify(
        {"scripts/new_agent.py": ["# launchd com.exos.brand-new-thing", "StartInterval 900"]},
        ["scripts/new_agent.py"], ["scripts/new_agent.py"], labels)
    case2 = any(f["level"] == "BLOCK" and "brand-new-thing" in f["msg"] for f in bad)
    # a mention (no create context) must NOT block
    mention = classify({"README.md": ["see com.exos.brand-new-thing docs"]}, ["README.md"], [], labels)
    case3 = not any(f["level"] == "BLOCK" for f in mention)
    passed = case1 and case2 and case3
    print(f"selftest: clean-passes={case1} new-agent-blocks={case2} mention-ignored={case3} -> {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def main():
    mode = "staged"
    if "--report" in sys.argv:
        mode = "report"
    elif "--check" in sys.argv:
        mode = "check"
    elif "--selftest" in sys.argv:
        return selftest()
    try:
        rc = gate(mode)
        if mode == "report":
            return 0
        return rc
    except Exception as e:
        # FAIL-OPEN: never brick the shared tree on a gate bug.
        print(f"  exo3-gate: internal error, allowing commit (fail-open): {e}")
        try:
            log_run(mode, [], "fail-open:" + str(e)[:120])
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
