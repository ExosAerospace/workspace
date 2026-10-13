#!/usr/bin/env python3
"""exo3_code_audit.py — weekly exo3 CODE compliance audit (Jon 2026-10-13: "Do you do a weekly exo3 code
compliance audit of any type?"). The commit gate only blocks NEW unregistered agents; behavior changes to existing
code (payload-orders, mc-attach, doc-families on 10/11-10/13) slipped through with no failure-replay eval, no
registry owner, no telemetry. This audit closes that gap.

For every code file changed in the last N days (scripts/*.py, mission-control/lib/*.js, mission-control/server.js):
  1. OWNER  — a registry entry (mission-control/data/agent-registry.json) whose script/eval_suite names the file
  2. EVAL   — that entry's eval_suite has a runnable selftest command, and it PASSES when run now
  3. TRACE  — the file emits fleet telemetry (fleet_log / fleet-events / glog)
  4. LEDGER — if any commit touching it says fix/bug, an improvement-ledger entry exists for its label
Exception-only: gaps -> ONE Decision card (dedupe per ISO week) + the weekly RSI §17 section. Clean -> one line.

Usage:  exo3_code_audit.py [--days 7] [--no-decision]   |   exo3_code_audit.py --selftest
Called by scripts/weekly-rsi.py (§17). Owner: John Quinn. Registered as capability of com.exos.weekly-rsi.
"""
import json, os, re, subprocess, sys, datetime, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
REGISTRY = os.path.join(WS, "mission-control/data/agent-registry.json")
LEDGER = os.path.join(WS, "mission-control/data/improvement-ledger.json")
TOKEN = os.path.join(WS, "mission-control/data/.decisions-token")
CODE = re.compile(r"^(scripts/[^/]+\.py|mission-control/lib/[^/]+\.js|mission-control/server\.js)$")
SKIP = re.compile(r"(^scripts/test_|\.bak|/tests/|selftest)")
TELEMETRY = re.compile(r"fleet_log|fleet-events|\bglog\(|fleet\(")
# One-off deliverable builders (a deck/letter/model generated once) are not processes: counted, not gated -
# UNLESS something schedules them (launchd plist / cron payload) or the registry names them.
ONE_OFF = re.compile(r"^scripts/(build|make|render|gen|draft|_)[\w\-]*\.py$")
LAUNCH_DIR = os.path.expanduser("~/Library/LaunchAgents")
EVAL_CMD = re.compile(r"(scripts/[\w\-.]+\.py(?:\s+[\w\-]+)?\s+--selftest|mission-control/tests/[\w\-.]+\.js)")


def git(*args):
    return subprocess.run(["git", "-C", WS] + list(args), capture_output=True, text=True, timeout=60).stdout


def changed_files(days):
    """{path: [commit subjects]} for code files changed in the window (files that still exist)."""
    out, cur = {}, None
    for ln in git("log", f"--since={days}.days", "--name-only", "--pretty=format:@@%h %s").splitlines():
        if ln.startswith("@@"):
            cur = ln[2:]
        elif ln.strip() and CODE.match(ln) and not SKIP.search(ln) and os.path.exists(os.path.join(WS, ln)):
            out.setdefault(ln, []).append(cur)
    return out


def load_registry(path=REGISTRY):
    r = json.load(open(path))
    return r["agents"] if isinstance(r, dict) else r


def ledger_labels(path=LEDGER):
    try:
        d = json.load(open(path))
        rows = d if isinstance(d, list) else d.get("entries", d.get("items", []))
        return {e.get("agent") for e in rows if isinstance(e, dict)}
    except Exception:
        return set()


def entries_for(path, agents):
    base = os.path.basename(path)
    return [a for a in agents if base in (str(a.get("script", "")) + " " + str(a.get("eval_suite", "")))]


def scheduled_names():
    """Text of every launchd plist + openclaw cron payload: a file named here runs unattended."""
    txt = []
    try:
        for n in os.listdir(LAUNCH_DIR):
            if n.startswith("com.exos."):
                txt.append(open(os.path.join(LAUNCH_DIR, n), errors="ignore").read())
    except Exception:
        pass
    try:
        txt.append(subprocess.run(["openclaw", "cron", "list", "--json"], capture_output=True, text=True, timeout=60).stdout)
    except Exception:
        pass
    return "\n".join(txt)


def run_eval(cmd):
    cmd = ("node " if cmd.endswith(".js") else "/usr/bin/python3 ") + cmd
    try:
        p = subprocess.run(cmd, shell=True, cwd=WS, capture_output=True, text=True, timeout=180)
        return p.returncode == 0, (p.stdout + p.stderr).strip().splitlines()[-1:] or [""]
    except Exception as e:
        return False, [str(e)[:120]]


def audit(days=7, agents=None, files=None, ledger=None, runner=run_eval, reader=None, scheduled=None):
    agents = load_registry() if agents is None else agents
    files = changed_files(days) if files is None else files
    ledger = ledger_labels() if ledger is None else ledger
    reader = reader or (lambda p: open(os.path.join(WS, p), errors="ignore").read())
    scheduled = scheduled_names() if scheduled is None else scheduled
    rows, ran, one_off = [], {}, []
    for path, commits in sorted(files.items()):
        gaps, ents = [], entries_for(path, agents)
        if not ents and ONE_OFF.match(path) and os.path.basename(path) not in scheduled:
            one_off.append(path); continue
        if not ents:
            gaps.append("OWNER: no registry entry names this file")
        cmds = sorted({c.strip() for e in ents for c in EVAL_CMD.findall(str(e.get("eval_suite", "")))})
        if ents and not cmds:
            gaps.append("EVAL: registry entry has no runnable selftest")
        for c in cmds:
            if c not in ran:
                ran[c] = runner(c)
            if not ran[c][0]:
                gaps.append(f"EVAL FAILING: {c} -> {ran[c][1][0][:100]}")
        try:
            waived = any(re.match(r"\s*(none|n/a)", str(e.get("telemetry", "")), re.I) for e in ents)
            if not waived and not TELEMETRY.search(reader(path)):
                gaps.append("TRACE: no fleet telemetry in the file")
        except Exception:
            pass
        if any(re.search(r"\b(fix|bug)", c or "", re.I) for c in commits) and ents and not any(e.get("label") in ledger for e in ents):
            gaps.append("LEDGER: fix commit without an improvement-ledger entry")
        rows.append({"file": path, "labels": [e.get("label") for e in ents], "commits": len(commits), "gaps": gaps})
    return {"files": len(rows), "evals_run": len(ran), "evals_failed": sum(1 for v in ran.values() if not v[0]),
            "gaps": [r for r in rows if r["gaps"]], "rows": rows, "one_off": one_off}


def file_decision(res, week):
    lines = [f"- {g['file']} ({', '.join(g['labels']) or 'unregistered'}): " + "; ".join(g["gaps"]) for g in res["gaps"]]
    body = {"title": f"exo3 code audit {week}: {len(res['gaps'])} change(s) missing exo3 pieces",
            "question": "Approve Exo bringing these changes into exo3 compliance (failure-replay selftest, registry owner/change_log, telemetry, ledger)?",
            "context": (f"Weekly exo3 code compliance audit (scripts/exo3_code_audit.py). {res['files']} code files changed in 7 days; "
                        f"{res['evals_run']} selftests run, {res['evals_failed']} failing.\n" + "\n".join(lines))[:3800],
            "proposedAction": "Exo remediates each gap in the same commit as its fix and re-runs this audit",
            "type": "yesno", "options": ["Yes — remediate", "Hold"], "priority": "high" if res["evals_failed"] else "med",
            "source": "exo3 code audit (weekly RSI §17)", "dedupeKey": f"exo3-code-audit-{week}"}
    rq = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json", "x-exo-token": open(TOKEN).read().strip()})
    return json.loads(urllib.request.urlopen(rq, timeout=30).read()).get("id")


def fleet(action, detail):
    try:
        sys.path.insert(0, os.path.join(WS, "scripts"))
        from fleet_log import event
        event("exo3-code-audit", "govern", action, detail=detail, owner="John Quinn")
    except Exception:
        pass


def report_section(days=7, decide=True):
    """Lines for weekly-rsi §17. Files a Decision only when gaps exist (exception-only)."""
    res = audit(days)
    week = datetime.date.today().strftime("%G-W%V")
    L = ["\n## 17. exo3 code compliance audit"]
    if res["one_off"]:
        L.append(f"- {len(res['one_off'])} one-off deliverable builder script(s) changed (not scheduled, not gated)")
    if not res["gaps"]:
        L.append(f"- clean: {res['files']} changed code files all have owner + passing selftest + telemetry ({res['evals_run']} selftests run)")
    else:
        did = None
        if decide:
            try:
                did = file_decision(res, week)
            except Exception as e:
                L.append(f"- (decision filing failed: {e})")
        L.append(f"- {len(res['gaps'])}/{res['files']} changed files missing exo3 pieces; {res['evals_run']} selftests run, {res['evals_failed']} failing" + (f" → Decision {did}" if did else ""))
        kinds = {}
        for g in res["gaps"]:
            for x in g["gaps"]:
                k = x.split(":")[0]; kinds[k] = kinds.get(k, 0) + 1
        L.append("- by type: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])))
        L.extend(f"  - {g['file']}: " + "; ".join(g["gaps"]) for g in sorted(res["gaps"], key=lambda g: ("EVAL FAILING" not in " ".join(g["gaps"]), "OWNER" not in " ".join(g["gaps"])))[:25])
    fleet("weekly_audit", {"files": res["files"], "gaps": len(res["gaps"]), "evals_failed": res["evals_failed"]})
    return L


def selftest():
    """Replays the 10/13 miss: payload-orders.js changed with no registry entry / eval / telemetry."""
    agents = [{"label": "good-exo3", "script": "scripts/good.py", "eval_suite": "python3 scripts/good.py --selftest"},
              {"label": "broken-exo3", "script": "scripts/broken.py", "eval_suite": "python3 scripts/broken.py --selftest"},
              {"label": "noeval", "script": "scripts/noeval.py", "eval_suite": "agent_eval hourly liveness"}]
    files = {"scripts/good.py": ["a1 add feature"], "scripts/broken.py": ["b1 tweak"], "scripts/noeval.py": ["c1 fix bug"],
             "mission-control/lib/payload-orders.js": ["d1 in-kind path"]}
    src = {"scripts/good.py": "from fleet_log import event", "scripts/broken.py": "fleet_log", "scripts/noeval.py": "print()",
           "mission-control/lib/payload-orders.js": "module.exports = {}"}
    runner = lambda c: (("good" in c), ["selftest: 3/3 pass" if "good" in c else "FAIL: x"])
    files["scripts/build_board_deck.py"] = ["e1 deck"]; files["scripts/build_nightly.py"] = ["f1 x"]
    src["scripts/build_board_deck.py"] = src["scripts/build_nightly.py"] = ""
    agents.append({"label": "view", "script": "scripts/view.py", "eval_suite": "python3 scripts/good.py --selftest", "telemetry": "none needed (read-only)"})
    files["scripts/view.py"] = ["g1 view"]; src["scripts/view.py"] = ""
    r = audit(agents=agents, files=files, ledger=set(), runner=runner, reader=lambda p: src[p], scheduled="<string>build_nightly.py</string>")
    g = {x["file"]: " | ".join(x["gaps"]) for x in r["gaps"]}
    checks = [
        ("scripts/good.py" not in g, "fully compliant file has no gaps"),
        ("EVAL FAILING" in g.get("scripts/broken.py", ""), "failing selftest is reported"),
        ("no runnable selftest" in g.get("scripts/noeval.py", "") and "TRACE" in g.get("scripts/noeval.py", "") and "LEDGER" in g.get("scripts/noeval.py", ""), "liveness-only eval + no telemetry + unledgered fix reported"),
        ("OWNER" in g.get("mission-control/lib/payload-orders.js", ""), "10/13 replay: unregistered payload-orders.js change is caught"),
        (r["evals_run"] == 2 and r["evals_failed"] == 1, "each selftest runs once"),
        (r["one_off"] == ["scripts/build_board_deck.py"], "unscheduled one-off builder is counted, not gated"),
        ("OWNER" in g.get("scripts/build_nightly.py", ""), "a builder that launchd/cron runs IS gated"),
        ("scripts/view.py" not in g, "registry 'telemetry: none needed' waives TRACE"),
        (bool(EVAL_CMD.findall("node mission-control/tests/payload_orders_selftest.js (13 checks)")), "node selftests recognized"),
    ]
    for ok, name in checks:
        assert ok, "FAIL: " + name
    print(f"exo3_code_audit selftest: {len(checks)}/{len(checks)} pass")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 7
    print("\n".join(report_section(days, decide="--no-decision" not in sys.argv)))
