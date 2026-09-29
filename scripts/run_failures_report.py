#!/usr/bin/python3
"""
run_failures_report.py: daily summary of failed background-job runs (exo3 audit remedy).

Reads the last 24h of logs/runs/*.jsonl (written by scripts/run_logged.py) and writes
  reports/run-failures/YYYY-MM-DD.md
listing every job with a failed run (non-zero exit or signal) plus the tail of its stderr,
and jobs that were expected to run in the window but never logged a run (only for jobs that
are known to be wrapped: they have logged at least once before, or the conversion manifest
says their wrapped plist was loaded before the window began).

If, and only if, there are failures or missed runs, it upserts ONE open MC task
(owner Exo, source run-failures-report) so a human reviews them: an existing open task from
this source gets today's summary prepended to its description; otherwise a new task is
created. No email, no Discord.

Run:  python3 scripts/run_failures_report.py            # normal
      python3 scripts/run_failures_report.py --dry-run  # print report, write nothing
      python3 scripts/run_failures_report.py --no-task  # write report file, skip MC task
Launchd: com.exos.run-failures-report, daily 06:30.
"""
import datetime
import glob
import json
import os
import plistlib
import sys
import urllib.parse
import urllib.request

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(WS, "logs", "runs")
MANIFEST = os.path.join(RUNS, "conversion-manifest.json")
OUTDIR = os.path.join(WS, "reports", "run-failures")
AGENTS = os.path.expanduser("~/Library/LaunchAgents")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/tasks"
SOURCE = "run-failures-report"
TASK_TITLE = "Background job failures (run log) - review"
DRY = "--dry-run" in sys.argv
NO_TASK = "--no-task" in sys.argv or DRY
WINDOW = datetime.timedelta(hours=24)
TAIL_SHOW = 12


def parse_ts(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None


def load_runs():
    """All run records, oldest first (every file, so first-seen per label is known)."""
    recs = []
    for f in sorted(glob.glob(os.path.join(RUNS, "*.jsonl"))):
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                r["_start"] = parse_ts(r.get("start", ""))
                r["_end"] = parse_ts(r.get("end", "")) or r["_start"]
                if r["_start"]:
                    recs.append(r)
    recs.sort(key=lambda r: r["_start"])
    return recs


def load_manifest():
    try:
        return json.load(open(MANIFEST)).get("jobs", {})
    except Exception:
        return {}


def _cal_matches(t, spec):
    wd = (t.isoweekday() % 7)  # launchd: 0 (or 7) = Sunday
    for k, v in spec.items():
        if k == "Minute" and t.minute != v: return False
        if k == "Hour" and t.hour != v: return False
        if k == "Day" and t.day != v: return False
        if k == "Month" and t.month != v: return False
        if k == "Weekday" and wd != (v % 7): return False
    return True


def expected_in(label, frm, to):
    """True if the job's launchd schedule should have fired in [frm, to]. None = unknown."""
    path = os.path.join(AGENTS, label + ".plist")
    try:
        p = plistlib.load(open(path, "rb"))
    except Exception:
        return None
    if p.get("Disabled"):
        return False
    if "StartInterval" in p:
        return (to - frm).total_seconds() >= 1.5 * int(p["StartInterval"])
    cal = p.get("StartCalendarInterval")
    if cal:
        specs = cal if isinstance(cal, list) else [cal]
        t = frm.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        # leave 15 min slack at the end so a job that is still running isn't "missed"
        stop = to - datetime.timedelta(minutes=15)
        while t <= stop:
            if any(_cal_matches(t, s) for s in specs):
                return True
            t += datetime.timedelta(minutes=1)
        return False
    return None  # RunAtLoad/KeepAlive-only: no schedule to check


def build(now):
    since = now - WINDOW
    recs = load_runs()
    manifest = load_manifest()
    first_seen = {}
    for r in recs:
        first_seen.setdefault(r["label"], r["_start"])
    window = [r for r in recs if r["_end"] >= since]

    by_label = {}
    for r in window:
        by_label.setdefault(r["label"], []).append(r)
    failed = {}
    for lab, rs in by_label.items():
        bad = [r for r in rs if not r.get("ok")]
        if bad:
            failed[lab] = (rs, bad)

    missing = []
    known = set(first_seen)
    for lab, m in manifest.items():
        if m.get("status") in ("converted", "already") and m.get("loaded_at"):
            ts = parse_ts(m["loaded_at"])
            if ts and ts <= since:
                known.add(lab)
    for lab in sorted(known):
        if lab in by_label:
            continue
        eff = first_seen.get(lab)
        m = manifest.get(lab, {})
        if m.get("loaded_at"):
            lt = parse_ts(m["loaded_at"])
            eff = min(x for x in (eff, lt) if x) if (eff or lt) else None
        if not eff or eff > since:
            continue  # wasn't wrapped for the whole window; can't tell
        exp = expected_in(lab, since, now)
        if exp:
            missing.append(lab)
    return window, by_label, failed, missing


def render(now, window, by_label, failed, missing):
    d = now.strftime("%Y-%m-%d")
    out = ["# Background job run failures: %s" % d, "",
           "Window: last 24h ending %s. Source: logs/runs/*.jsonl (scripts/run_logged.py)." %
           now.strftime("%Y-%m-%d %H:%M %Z"), "",
           "Runs logged: %d across %d jobs. Jobs with failures: %d. Expected but never ran: %d." %
           (len(window), len(by_label), len(failed), len(missing)), ""]
    if not failed and not missing:
        out += ["No failures. Nothing to review.", ""]
        return "\n".join(out)
    if failed:
        out += ["## Failed runs", ""]
        for lab in sorted(failed, key=lambda l: -len(failed[l][1])):
            rs, bad = failed[lab]
            last = bad[-1]
            why = ("signal %s" % last["signal"]) if last.get("signal") else ("exit %s" % last.get("exit_code"))
            out.append("### %s: %d of %d runs failed" % (lab, len(bad), len(rs)))
            out.append("Last failure %s (%s, %.1fs). Command: `%s`" % (
                last["_start"].strftime("%m-%d %H:%M"), why, last.get("duration_s") or 0, last.get("cmd", "")[:200]))
            tail = (last.get("stderr_tail") or [])[-TAIL_SHOW:]
            if tail:
                out.append("")
                out.append("```")
                out += [l[:300] for l in tail]
                out.append("```")
            else:
                out.append("(no stderr output)")
            out.append("")
    if missing:
        out += ["## Expected but never ran", "",
                "These jobs are wrapped by run_logged and their launchd schedule should have fired in the "
                "window, but no run was logged. Check `launchctl print gui/$(id -u)/<label>`.", ""]
        out += ["- %s" % lab for lab in missing]
        out.append("")
    return "\n".join(out)


def _key():
    return json.load(open(SECRETS)).get("supabase_service_role_key")


def _req(method, url, body=None):
    k = _key()
    h = {"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json",
         "Prefer": "return=representation"}
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers=h, method=method)
    return json.load(urllib.request.urlopen(req, timeout=40))


def upsert_task(now, report, report_rel, n_failed, n_missing):
    summary = "[%s] %d job(s) failed, %d expected job(s) never ran. Report: %s" % (
        now.strftime("%Y-%m-%d"), n_failed, n_missing, report_rel)
    q = SB + "?" + urllib.parse.urlencode({"select": "id,description,state", "source": "eq." + SOURCE,
                                           "state": "neq.Done", "order": "id.desc", "limit": "1"})
    existing = _req("GET", q)
    body_new = summary + "\n\n" + report
    if existing:
        t = existing[0]
        desc = (body_new + "\n\n---- earlier ----\n" + (t.get("description") or ""))[:30000]
        _req("PATCH", SB + "?id=eq.%s" % t["id"], {"description": desc})
        return t["id"], "updated"
    task = {"title": TASK_TITLE, "state": "To Do", "owner": "Exo", "assigned_email": "exo@exosaero.com",
            "category": "Task", "priority": 70, "source": SOURCE,
            "description": "Proposed review (human confirms fixes): background jobs failed or missed runs.\n\n"
                           + body_new[:28000]}
    created = _req("POST", SB, task)
    return (created[0].get("id") if created else None), "created"


def main():
    now = datetime.datetime.now().astimezone()
    window, by_label, failed, missing = build(now)
    report = render(now, window, by_label, failed, missing)
    rel = os.path.join("reports", "run-failures", now.strftime("%Y-%m-%d") + ".md")
    if DRY:
        print(report)
        return 0
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(WS, rel), "w") as f:
        f.write(report)
    print("wrote %s (%d runs, %d failed jobs, %d missed)" % (rel, len(window), len(failed), len(missing)))
    if (failed or missing) and not NO_TASK:
        try:
            tid, how = upsert_task(now, report, rel, len(failed), len(missing))
            print("MC task #%s %s" % (tid, how))
        except Exception as e:
            print("ERROR: MC task upsert failed: %s" % e, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
