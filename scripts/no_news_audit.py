#!/usr/bin/env python3
"""
no_news_audit.py — fleet rule R-NONEWS enforcement (Jon 2026-09-30).

Jon: "stop telling me things like 'No new technical or competitive movement' ... If there is nothing
new I do not need you to tell me that." Every recurring OpenClaw cron carries the R-NONEWS block
(config/cron-no-news-rule.txt): no news -> final reply exactly NO_REPLY, no message-tool post.

Two deterministic, read-only checks (no LLM, no writes):
  1. COVERAGE  — every enabled recurring cron (schedule_kind != 'at') has "R-NONEWS" in its prompt.
                 Catches new crons created without the rule. Missing -> issue.
  2. OUTPUT    — scans what cron runs actually SENT Jon in the last N days (message-tool sends +
                 final assistant text, from the claude-cli session transcripts) for no-news filler.
                 A post whose headline is a no-news statement ("steady state", "no movement",
                 "nothing to action", ...) should have been NO_REPLY -> issue, named by cron.
                 Filler lines inside an otherwise-real post are counted as a softer signal.

Wired into weekly-rsi.py via rsi_self_audit.run_all() (module 13) and the nightly Agent
Meta-Evaluator cron runs it with --days 1.

Usage:
  no_news_audit.py [--days 7]   # print report, exit 1 if issues
  no_news_audit.py --selftest
"""
import glob, json, os, re, sqlite3, sys, time

DB = os.path.expanduser("~/.openclaw/state/openclaw.sqlite")
TRANSCRIPTS = os.path.expanduser("~/.claude/projects/-Users-exomac--openclaw-workspace")
RULE_TAG = "R-NONEWS"

NO_NEWS = re.compile(
    r"\b(no (new |real )?(movement|change|changes|activity|updates?|signal|developments?)"
    r"|steady[- ]state|nothing (new|to action|to report|actionable|needs (your|jon'?s) (attention|decision))"
    r"|no (decisions?|action) (needed|required)|nothing needs (your|a) decision"
    r"|still no (foa|reply|response|nofo|movement)|unchanged since|no new \w+( or \w+)? (movement|signal)"
    r"|all (green|clear|quiet)|clean (run|check|scan)|null result)", re.I)
SILENT = re.compile(r"^\s*(NO_REPLY|HEARTBEAT_OK)\s*$", re.I)
CRON_HDR = re.compile(r"\[cron:([0-9a-f-]{36}) ([^\]]+)\]")


def coverage(db=DB):
    con = sqlite3.connect("file:%s?mode=ro" % db, uri=True, timeout=10)
    try:
        rows = con.execute("select job_id, name, schedule_kind, payload_message from cron_jobs where enabled=1").fetchall()
    finally:
        con.close()
    return [(jid, name) for jid, name, sk, msg in rows if sk != "at" and RULE_TAG not in (msg or "")]


def _outbound(path):
    """(cron_id, cron_name, [sent texts]) for a cron-run transcript, else None."""
    cid = cname = None
    sent, last_text = [], ""
    for ln in open(path, errors="replace"):
        try:
            e = json.loads(ln)
        except Exception:
            continue
        if cid is None and e.get("type") == "queue-operation":
            m = CRON_HDR.search(str(e.get("content") or ""))
            if not m:
                return None
            cid, cname = m.group(1), m.group(2)
            continue
        msg = e.get("message") or {}
        if msg.get("role") != "assistant" or not isinstance(msg.get("content"), list):
            continue
        texts = []
        for b in msg["content"]:
            if b.get("type") == "tool_use" and b.get("name", "").endswith("message"):
                inp = b.get("input") or {}
                if inp.get("action") in ("send", "thread-reply") and inp.get("message"):
                    sent.append(inp["message"])
            elif b.get("type") == "text" and b.get("text", "").strip():
                texts.append(b["text"])
        if texts:
            last_text = texts[-1]
    if cid is None:
        return None
    if last_text and not SILENT.match(last_text) and not sent:
        sent.append(last_text)  # announce-mode delivery of the final text
    return cid, cname, sent


def classify(text):
    """('pure'|'padded'|'ok', n_filler_lines). pure = headline itself is a no-news statement."""
    lines = [l.strip(" *-#>\t") for l in text.splitlines() if l.strip()]
    if not lines:
        return "ok", 0
    filler = sum(1 for l in lines if NO_NEWS.search(l))
    head = " ".join(lines[:1])
    if NO_NEWS.search(head) or filler == len(lines) or (len(lines) >= 3 and filler >= len(lines) - 1):
        return "pure", filler
    return ("padded" if filler else "ok"), filler


def output_scan(days=7, root=TRANSCRIPTS):
    cutoff = time.time() - days * 86400
    pure, padded = {}, {}
    for p in glob.glob(os.path.join(root, "*.jsonl")):
        if os.path.getmtime(p) < cutoff:
            continue
        r = _outbound(p)
        if not r:
            continue
        cid, cname, sent = r
        for t in sent:
            kind, n = classify(t)
            if kind == "pure":
                pure.setdefault(cname, []).append(t.splitlines()[0][:100])
            elif kind == "padded":
                padded[cname] = padded.get(cname, 0) + n
    return pure, padded


def audit(days=7):
    lines, issues = [], []
    try:
        miss = coverage()
        if miss:
            issues.append("r-nonews-missing: %d cron(s)" % len(miss))
            lines.append("- ⚠️ %d recurring cron(s) lack the R-NONEWS rule (append config/cron-no-news-rule.txt): %s"
                         % (len(miss), ", ".join(n for _, n in miss)))
        else:
            lines.append("- ✅ Every recurring cron carries R-NONEWS.")
    except Exception as e:
        lines.append("- (coverage check skipped: %s)" % e)
    pure, padded = output_scan(days)
    for name, heads in sorted(pure.items()):
        issues.append("no-news-post: %s x%d" % (name, len(heads)))
        lines.append("- ⚠️ %s posted %d no-news message(s) that should have been NO_REPLY, e.g. \"%s\""
                     % (name, len(heads), heads[0]))
    for name, n in sorted(padded.items(), key=lambda x: -x[1]):
        lines.append("- ℹ️ %s padded real posts with %d no-news line(s) — trim." % (name, n))
    if not pure:
        lines.append("- ✅ No pure no-news posts in the last %dd." % days)
    return {"title": "13. No-news noise (R-NONEWS)", "lines": lines, "issues": issues}


def _selftest():
    ok = True
    cases = [
        ("**NIH Microgravity — 9/30 run: steady state, nothing to action.**\n- Task 2613 unchanged since 9/24", "pure"),
        ("**NOAA ERB/AC4 SACSS — 9/30 scan.** No movement: no new AC4/ERB NOFO", "pure"),
        ("**Decision needed:** send the NASA debrief request? Draft in your inbox.", "ok"),
        ("**Award posted:** AFWERX X closes 10/14 — fit 8/10.\n- No change on the other two topics.", "padded"),
    ]
    for text, want in cases:
        got = classify(text)[0]
        print("%s %s -> %s" % ("PASS" if got == want else "FAIL", text.splitlines()[0][:60], got))
        ok &= got == want
    print("SELFTEST " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    d = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 7
    r = audit(d)
    print("## " + r["title"] + "\n" + "\n".join(r["lines"]))
    raise SystemExit(1 if r["issues"] else 0)
