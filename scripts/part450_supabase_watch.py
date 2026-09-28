#!/usr/bin/env python3
"""
part450_supabase_watch.py — ExO3 agent: com.exos.part450-supabase-watch-exo3

Watches whether Neil's Part 450 licensing tasking (the BLK3 Part 450 WBS, MC task
#2802 and its subtree) is pushing the Mission Control Supabase project toward a
compute upgrade — and, if so, alerts NEIL directly (not Jon) with John's standing
note that additional Supabase support is anticipated.

WHY THIS EXISTS
---------------
The Part 450 application package is a large, multi-deliverable regulatory effort:
Monte Carlo dispersion runs, malfunction analyses, §450.141 computing-system V&V
evidence, activity logs, document rows — all landing in the same Supabase project
(ref pcrgpuoljylqcumijvnw) that already runs on the small t4g.micro instance and has
repeatedly brushed its Disk-IO budget. As Neil's tasking scales, it is a plausible
contributor to the load that forces the upgrade off t4g.micro. John wants Neil told
— proactively — that this is anticipated, and alerted if/when his tasking is actively
contributing while the system is near capacity.

DESIGN (edge-triggered, de-duped, low added load)
-------------------------------------------------
1. Live infra metrics come from scripts/supabase_metrics_pull.py --json (Prometheus
   privileged endpoint — NOT origin table reads, so this check adds ~zero Disk-IO).
2. Part 450 footprint = row counts attributable to Neil's tasking (subtree of #2802 +
   part450-tagged tasks + activities on that subtree). Cheap HEAD count, once daily.
3. ALERT NEIL when the system is AT/NEAR the upgrade line AND Neil's tasking is
   actively growing (delta > 0 vs the stored baseline) — i.e., his work is a live
   contributor, not just ambient fleet load. Edge-triggered via state file so Neil is
   not re-alerted on the same standing condition.
4. Every alert carries John's anticipation note + the concrete upgrade recommendation
   (move off t4g.micro to a Supabase compute add-on).

Jon's Jon-facing hard breach alerts (the hourly supabase metrics watcher: disk>=80 /
mem>=88 / conns>=55) are untouched — this is a SEPARATE, earlier, Neil-scoped signal.

Usage:
  python3 scripts/part450_supabase_watch.py           # run one check (launchd daily)
  python3 scripts/part450_supabase_watch.py --verbose # print the assessment
  python3 scripts/part450_supabase_watch.py --rebaseline   # reset footprint baseline
  python3 scripts/part450_supabase_watch.py --selftest     # eval: synthetic breach path
ExO3: owner Neil Milburn / John Quinn · autonomy Recommends-with-Context ·
permission_envelope below · eval_suite = --selftest · telemetry = fleet_log + log file.
"""
import os, sys, json, time, base64, urllib.request, urllib.parse, subprocess, shutil
from datetime import datetime, timezone

ROOT = os.path.expanduser("~/.openclaw/workspace")
STATE = os.path.join(ROOT, "logs/part450-supabase-watch-state.json")
LOGF = os.path.join(ROOT, "logs/part450-supabase-watch.log")
METRICS = os.path.join(ROOT, "scripts/supabase_metrics_pull.py")
SUPA_REF = "pcrgpuoljylqcumijvnw"
SUPA_REST = f"https://{SUPA_REF}.supabase.co/rest/v1"
SUPA_READ_KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]  # read/count only (same key server uses)

NEIL_EMAIL = "nmilburn@exosaero.com"
JON_EMAIL = "jquinn@exosaero.com"
NEIL_DISCORD = None  # email is Neil's channel; Discord DM reserved for Jon's fleet alerts

PARENT_TASK = 2802

# "Approaching upgrade" thresholds — deliberately EARLIER than Jon's hard breach
# (disk>=80/mem>=88/conns>=55) so Neil gets a heads-up before it's an outage.
WARN = {"disk_pct": 75.0, "mem_pct": 85.0, "pg_connections": 50.0, "io_rps": 1200.0}

JOHN_NOTE = ("John anticipates the Part 450 licensing effort will require additional "
             "Supabase support — i.e. a compute upgrade off the current t4g.micro "
             "instance to a paid Supabase compute add-on. Treat this as expected, not a surprise.")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def log(msg):
    line = f"[{now_iso()}] {msg}"
    try:
        with open(LOGF, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if "--verbose" in sys.argv or "--selftest" in sys.argv:
        print(line)


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2)
    os.replace(tmp, STATE)


def fleet_log_event(action, outcome, detail):
    try:
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import fleet_log
        fleet_log.event(agent="com.exos.part450-supabase-watch-exo3", kind="govern",
                        action=action, corr=fleet_log.new_corr(),
                        owner="Neil Milburn / John Quinn", outcome=outcome, detail=detail)
    except Exception as e:
        log(f"WARN: fleet_log failed: {e}")


def get_metrics():
    try:
        r = subprocess.run(["/usr/bin/python3", METRICS, "--json"],
                           capture_output=True, text=True, timeout=45)
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}


def _count(path_and_query):
    """PostgREST exact count via HEAD-style GET with Prefer: count=exact (cheap)."""
    url = f"{SUPA_REST}/{path_and_query}"
    req = urllib.request.Request(url, method="GET", headers={
        "apikey": SUPA_READ_KEY, "Authorization": "Bearer " + SUPA_READ_KEY,
        "Prefer": "count=exact", "Range": "0-0", "Range-Unit": "items"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cr = r.headers.get("Content-Range", "")  # e.g. "0-0/1234"
            if "/" in cr:
                tail = cr.rsplit("/", 1)[1]
                return int(tail) if tail.isdigit() else 0
    except Exception as e:
        log(f"WARN: count failed [{path_and_query}]: {e}")
    return 0


def part450_footprint():
    """Rows attributable to Neil's Part 450 tasking. Cheap; runs once/day."""
    subtree = _count("tasks?tags=cs." + urllib.parse.quote('{"parent:%d"}' % PARENT_TASK))
    tagged = _count("tasks?tags=cs." + urllib.parse.quote('{"part450"}'))
    # activities logged against the WBS parent timeline
    acts = _count("activities?subject=eq." + urllib.parse.quote(f"task:{PARENT_TASK}"))
    total = subtree + tagged + acts
    return {"subtree": subtree, "part450_tagged": tagged, "wbs_activities": acts, "total": total}


def send_neil(subject, body):
    try:
        r = subprocess.run(["/usr/bin/python3", os.path.join(ROOT, "scripts/send_email.py"),
                            "--to", NEIL_EMAIL, "--cc", JON_EMAIL,
                            "--subject", subject, "--body", body],
                           capture_output=True, text=True, timeout=90)
        ok = r.returncode == 0
        log(("SENT to Neil: " if ok else "SEND FAILED: ") + subject + (" | " + r.stderr[:200] if not ok else ""))
        return ok
    except Exception as e:
        log(f"SEND EXC: {e}")
        return False


def assess(metrics, fp):
    near = []
    if metrics.get("ok"):
        for k, lim in WARN.items():
            val = metrics.get(k) if k != "io_rps" else metrics.get("disk_reads_per_s")
            if val is not None and val >= lim:
                near.append((k, val, lim))
    return near


def main():
    st = load_state()

    if "--rebaseline" in sys.argv:
        fp = part450_footprint()
        st["baseline_footprint"] = fp
        st["baseline_ts"] = now_iso()
        save_state(st)
        log(f"REBASELINE footprint={fp}")
        print(json.dumps({"rebaselined": fp}))
        return

    metrics = get_metrics()
    fp = part450_footprint()
    baseline = st.get("baseline_footprint") or fp
    if "baseline_footprint" not in st:
        st["baseline_footprint"] = fp
        st["baseline_ts"] = now_iso()
    growth = fp["total"] - baseline.get("total", fp["total"])
    near = assess(metrics, fp)

    log(f"metrics_ok={metrics.get('ok')} disk={metrics.get('disk_pct')} mem={metrics.get('mem_pct')} "
        f"io_r={metrics.get('disk_reads_per_s')} conns={metrics.get('pg_connections')} "
        f"fp_total={fp['total']} growth={growth} near={[n[0] for n in near]}")

    # Alert condition: system AT/NEAR upgrade line AND Neil's tasking actively growing.
    should_alert = bool(near) and growth > 0
    prev_near = set(st.get("alerted_metrics", []))
    now_near = set(n[0] for n in near)
    new_condition = should_alert and not now_near.issubset(prev_near)

    if new_condition:
        lines = [f"Neil,", "",
                 "Heads-up from Mission Control's Supabase watcher on the Part 450 licensing effort.",
                 "",
                 "Your Part 450 tasking (BLK3 Part 450 WBS, MC #2802 + subtree) is actively growing "
                 f"AND the Supabase project (t4g.micro) is now near its upgrade line:", ""]
        for k, val, lim in near:
            label = {"disk_pct": "Disk usage", "mem_pct": "Memory", "pg_connections": "DB connections",
                     "io_rps": "Disk read IO/s"}.get(k, k)
            lines.append(f"  • {label}: {val} (warn at {lim})")
        lines += ["",
                  f"Part 450 footprint: {fp['total']} rows "
                  f"({fp['subtree']} subtasks, {fp['part450_tagged']} part450-tagged, {fp['wbs_activities']} WBS activities) "
                  f"— up {growth} since baseline.",
                  "",
                  JOHN_NOTE,
                  "",
                  "Recommended next step: budget a Supabase compute add-on (upgrade off t4g.micro). "
                  "No action needed from you right now beyond awareness — John is anticipating the spend. "
                  "The free lever (index SQL) is tracked separately by the diskio-maintenance job.",
                  "",
                  "— Exo (automated Part 450 Supabase watcher)"]
        send_neil("Part 450 tasking → Supabase upgrade anticipated (heads-up)", "\n".join(lines))
        st["alerted_metrics"] = list(now_near)
        st["last_alert_ts"] = now_iso()
        fleet_log_event("neil_supabase_upgrade_alert", "alerted",
                        {"near": [n[0] for n in near], "footprint": fp, "growth": growth})
    elif not near and prev_near:
        st["alerted_metrics"] = []  # recovered; re-arm
        log("recovered — re-armed")

    st["last_run"] = now_iso()
    st["last_footprint"] = fp
    st["last_metrics"] = {k: metrics.get(k) for k in ("disk_pct", "mem_pct", "disk_reads_per_s", "pg_connections")} if metrics.get("ok") else {"error": metrics.get("error")}
    save_state(st)
    if "--verbose" in sys.argv:
        print(json.dumps({"metrics": metrics, "footprint": fp, "growth": growth,
                          "near": [n[0] for n in near], "alerted": new_condition}, indent=2))


def selftest():
    """ExO3 eval: synthetic breach must produce an alert decision; healthy must not."""
    fake_metrics_breach = {"ok": True, "disk_pct": 78.0, "mem_pct": 40.0,
                           "disk_reads_per_s": 200.0, "pg_connections": 20}
    fake_metrics_ok = {"ok": True, "disk_pct": 50.0, "mem_pct": 40.0,
                       "disk_reads_per_s": 200.0, "pg_connections": 20}
    n1 = assess(fake_metrics_breach, {})
    n2 = assess(fake_metrics_ok, {})
    ok = (any(k == "disk_pct" for k, _, _ in n1)) and (len(n2) == 0)
    print(("PASS" if ok else "FAIL") + f": breach_near={[k for k,_,_ in n1]} healthy_near={[k for k,_,_ in n2]}")
    fleet_log_event("selftest", "ok" if ok else "fail", {"breach_near": [k for k, _, _ in n1]})
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        main()
