#!/usr/bin/env python3
"""
cron_prompt_guard.py — exo3 r2 (r2-confirm-gaps, 2026-09-29). Deterministic guard that keeps the
five "human-confirm gap" OpenClaw crons propose-only. AI proposes, a human confirms.

Reads the OpenClaw state DB READ-ONLY (~/.openclaw/state/openclaw.sqlite, mode=ro). Never edits a cron.

Checks, per guarded cron (GUARDS below):
  1. FORBIDDEN text in the live prompt (the old autonomous wording, e.g. "IMPLEMENT NOW",
     "action=update", "launchctl kickstart", "AUTO-APPEND", a literal X-Exo-Token or Supabase JWT)
     -> FAIL.
  2. REQUIRED text missing (the propose-only wording, e.g. reads .decisions-token) -> FAIL.
  3. Prompt hash changed since the last pass -> WARN ("confirm a human made this change"), and
     FAIL if, in that window, an OpenClaw *cron-run* session (session_key ':cron:') invoked the cron
     tool — i.e. an agent, not a human session, may have rewritten a prompt.
Fleet-wide (every cron): any cron-tool call from a cron-run session since the last pass -> WARN
(names the calling job). Limitation: a cron that shells out to `openclaw cron edit` via exec shows up
only as a Bash/exec call (the audit log stores a hash, not the command), so it is caught by (3)'s
hash drift + (1)/(2) text rules, not by attribution.

Usage:
  cron_prompt_guard.py            # one pass, prints results, updates state, emits fleet_log events
  cron_prompt_guard.py --selftest # replays the pre-fix prompts (must FAIL) and fixtures
Imported by agent_eval.py (check()) so results ride the hourly eval + its deduped FAIL alert.
"""
import hashlib, json, os, re, sqlite3, sys, time, datetime
from pathlib import Path

WS = Path("/Users/exomac/.openclaw/workspace")
DB = os.path.expanduser("~/.openclaw/state/openclaw.sqlite")
STATE = WS / "state" / "cron-prompt-guard-state.json"

LITERAL_TOKEN = r"[Xx]-[Ee]xo-[Tt]oken:\s*['\"]?[A-Za-z0-9]{16,}"   # a pasted token, not $MCTOKEN
LITERAL_JWT = r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}"            # pasted Supabase key

GUARDS = {
    "77ee570f-6957-456f-a687-7d28bedeabc3": {
        "label": "cron:decisions-matrix-daily-update-r-017",
        "forbid": [r"Auto-close stale open decisions", r"PATCH it closed", LITERAL_TOKEN, LITERAL_JWT],
        "require": [r"\.decisions-token", r"PROPOSE closes"],
    },
    "ed638bd8-d478-487b-a238-9f2f789a8466": {
        "label": "cron:agent-self-improvement-implementer-weekly",
        "forbid": [r"IMPLEMENT NOW", r"action\s*=\s*update", r"action\s*=\s*remove", r"openclaw\s+cron\s+(edit|rm|remove|disable|enable|add)",
                   r"Implement approved changes", LITERAL_TOKEN, LITERAL_JWT],
        "require": [r"\.decisions-token", r"reports/self-improvement/", r"PROPOSE-ONLY"],
    },
    "28a46633-1a11-439a-887b-dfb24224b12a": {
        "label": "cron:apac-deal-flow-weekly-scan",
        "forbid": [r"launchctl\s+kickstart", r"AUTO-APPEND", r"restart MC", LITERAL_TOKEN, LITERAL_JWT],
        "require": [r"apac-candidates-staging\.json"],
    },
    "f2ec7aca-8136-43c1-98b4-d2a94340d1ad": {
        "label": "cron:overnight-resolver",
        "forbid": [r"EXECUTE IT YOURSELF", r"EXECUTE it directly", r"execute or stage", LITERAL_TOKEN, LITERAL_JWT],
        "require": [r"\.decisions-token", r"PROPOSE-ONLY"],
    },
    "1f60acb4-e0e0-4ae0-a877-9749eb380d6e": {
        "label": "cron:overnight-resolver-opus-escalation",
        "forbid": [r"EXECUTE IT YOURSELF", r"EXECUTE it directly", r"execute or stage", LITERAL_TOKEN, LITERAL_JWT],
        "require": [r"\.decisions-token", r"PROPOSE-ONLY"],
    },
}
CRON_TOOLS = ("cron", "mcp__openclaw__cron")


def connect(db=DB):
    return sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)


def load_prompts(db=DB):
    con = connect(db)
    try:
        rows = con.execute("select job_id, name, enabled, payload_message from cron_jobs").fetchall()
        return {r[0]: {"name": r[1], "enabled": bool(r[2]), "prompt": r[3] or ""} for r in rows}
    finally:
        con.close()


def cron_tool_calls_by_cron_sessions(since_ms, db=DB):
    """[(job_id_of_caller, tool_name, occurred_at)] — cron-tool calls made from a cron-run session."""
    con = connect(db)
    try:
        rows = con.execute(
            "select session_key, tool_name, occurred_at from audit_events where occurred_at > ? and "
            "tool_name in (%s) and session_key like '%%:cron:%%' and action like '%%started%%'" % ",".join("?" * len(CRON_TOOLS)),
            (since_ms, *CRON_TOOLS)).fetchall()
    finally:
        con.close()
    out = []
    for sk, tool, ts in rows:
        m = re.search(r":cron:([0-9a-f-]{36})", sk or "")
        out.append((m.group(1) if m else sk, tool, ts))
    return out


def scan_prompt(prompt, spec):
    """Returns list of violations (empty = compliant)."""
    why = []
    for pat in spec["forbid"]:
        if re.search(pat, prompt or ""):
            why.append("forbidden text present: /%s/" % ("literal X-Exo-Token" if pat == LITERAL_TOKEN else "literal JWT" if pat == LITERAL_JWT else pat))
    for pat in spec["require"]:
        if not re.search(pat, prompt or ""):
            why.append("required propose-only text missing: /%s/" % pat)
    return why


def sha(s):
    return hashlib.sha256((s or "").encode()).hexdigest()[:16]


def check(db=DB, state_path=STATE, dry=False, now_ms=None, emit=True):
    """Returns [(label, status, why, owner)] for the guarded crons (+ one fleet row). Never raises."""
    now_ms = now_ms or int(time.time() * 1000)
    results = []
    try:
        jobs = load_prompts(db)
    except Exception as e:
        return [("cron-prompt-guard", "WARN", "state DB unreadable: %s" % e, "John Quinn")]
    state = {}
    try:
        state = json.load(open(state_path))
    except Exception:
        state = {}
    since = int(state.get("_last_pass_ms") or now_ms - 3600 * 1000)
    try:
        calls = cron_tool_calls_by_cron_sessions(since, db)
    except Exception:
        calls = []
    for jid, spec in GUARDS.items():
        j = jobs.get(jid)
        if not j:
            results.append((spec["label"], "WARN", "guarded cron not found (removed?)", "John Quinn")); continue
        why = scan_prompt(j["prompt"], spec)
        status = "FAIL" if why else "OK"
        h, prev = sha(j["prompt"]), state.get(jid)
        if prev and prev != h:
            if calls:
                status = "FAIL"
                why.append("prompt changed while a cron-run session used the cron tool (%s) — agent edit suspected"
                           % ", ".join(sorted({c[0][:8] for c in calls})))
            elif status == "OK":
                status = "WARN"
                why.append("prompt changed since last pass — confirm a human session made it")
        state[jid] = h
        results.append((spec["label"], status, "; ".join(why) or "propose-only prompt intact", "John Quinn"))
    if calls:
        results.append(("cron-prompt-guard:fleet", "WARN", "cron tool used from cron-run session(s): %s"
                        % ", ".join(sorted({c[0][:8] for c in calls})), "John Quinn"))
    state["_last_pass_ms"] = now_ms
    if not dry:
        try:
            Path(state_path).parent.mkdir(parents=True, exist_ok=True)
            json.dump(state, open(state_path, "w"), indent=1)
        except Exception:
            pass
    if not dry and emit:
        try:
            sys.path.insert(0, str(WS / "scripts"))
            import fleet_log
            for label, st, why, owner in results:
                fleet_log.event("cron_prompt_guard", "govern", "eval", outcome=st.lower(), owner=owner,
                                detail={"agent": label, "why": why})
        except Exception:
            pass
    return results


def selftest():
    import tempfile, glob
    n = 0
    def ok(cond, name):
        nonlocal n
        assert cond, name
        n += 1
        print("  ok", name)
    # 1. replay the PRE-FIX prompts from the cron backups (if present) -> each must be flagged
    bdir = WS / "logs" / "audit-workers" / "cron-backups"
    for jid, spec in GUARDS.items():
        files = sorted(glob.glob(str(bdir / ("%s.20260929T224247.json" % jid))))
        if files:
            j = json.load(open(files[0]))
            p = (j.get("payload") or {}).get("message") or (j.get("payload") or {}).get("text") or ""
            ok(scan_prompt(p, spec), "pre-fix prompt of %s is flagged" % spec["label"])
        else:
            ok(True, "pre-fix backup for %s not present (skipped)" % spec["label"])
    # 2. fixtures: compliant vs forbidden
    si = GUARDS["ed638bd8-d478-487b-a238-9f2f789a8466"]
    good = "PROPOSE-ONLY. token=$(cat mission-control/data/.decisions-token) write reports/self-improvement/x.md"
    ok(scan_prompt(good, si) == [], "compliant self-improvement fixture passes")
    ok(scan_prompt(good + " IMPLEMENT NOW", si), "IMPLEMENT NOW re-introduced -> flagged")
    ok(scan_prompt(good + " use cron tool (action=get then action=update)", si), "action=update re-introduced -> flagged")
    ok(scan_prompt(good + " -H 'X-Exo-Token: " + "a1" * 12 + "'", si), "literal token -> flagged")
    ap = GUARDS["28a46633-1a11-439a-887b-dfb24224b12a"]
    ok(scan_prompt("write to apac-candidates-staging.json", ap) == [], "compliant APAC fixture passes")
    ok(scan_prompt("write to apac-candidates-staging.json then launchctl kickstart -k x", ap), "kickstart re-introduced -> flagged")
    # 3. change attribution against a temp sqlite
    with tempfile.TemporaryDirectory() as d:
        db, sp = os.path.join(d, "t.sqlite"), os.path.join(d, "s.json")
        con = sqlite3.connect(db)
        con.execute("create table cron_jobs (job_id text, name text, enabled int, payload_message text)")
        con.execute("create table audit_events (session_key text, tool_name text, occurred_at int, action text)")
        jid = "ed638bd8-d478-487b-a238-9f2f789a8466"
        con.execute("insert into cron_jobs values (?,?,?,?)", (jid, "SI", 1, good))
        con.commit(); con.close()
        r = dict((l, s) for l, s, _, _ in check(db, sp, dry=False, emit=False, now_ms=1000))
        ok(r["cron:agent-self-improvement-implementer-weekly"] == "OK", "first pass on compliant prompt OK")
        con = sqlite3.connect(db)
        con.execute("update cron_jobs set payload_message=? where job_id=?", (good + " (tweaked by human)", jid)); con.commit(); con.close()
        r = dict((l, s) for l, s, _, _ in check(db, sp, dry=False, emit=False, now_ms=2000))
        ok(r["cron:agent-self-improvement-implementer-weekly"] == "WARN", "unattributed prompt change -> WARN")
        con = sqlite3.connect(db)
        con.execute("update cron_jobs set payload_message=? where job_id=?", (good + " (tweaked by agent)", jid))
        con.execute("insert into audit_events values (?,?,?,?)", ("agent:main:cron:%s:run:x" % jid, "mcp__openclaw__cron", 2500, "tool.action.started"))
        con.commit(); con.close()
        r = dict((l, s) for l, s, _, _ in check(db, sp, dry=False, emit=False, now_ms=3000))
        ok(r["cron:agent-self-improvement-implementer-weekly"] == "FAIL", "prompt change + cron-tool call from a cron session -> FAIL")
        ok(r.get("cron-prompt-guard:fleet") == "WARN", "fleet row names the cron-session cron-tool caller")
    print("cron_prompt_guard selftest: %d/%d pass" % (n, n))
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    res = check(dry="--dry" in sys.argv)
    for label, st, why, _ in res:
        print("%-5s %s — %s" % (st, label, why))
    return 1 if any(s == "FAIL" for _, s, _, _ in res) else 0


if __name__ == "__main__":
    sys.exit(main())
