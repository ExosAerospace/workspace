#!/usr/bin/env python3
"""
Supabase Disk IO maintenance — scheduled hygiene job for the Mission Control project
(ref pcrgpuoljylqcumijvnw).

WHY THIS EXISTS
---------------
MC's Supabase project has twice tripped the "running out of Disk IO Budget" alert
(2026-09-02, 2026-09-09) and again on 2026-09-24. Root cause each time = READ
AMPLIFICATION: a growing fleet of launchd pollers each pulling list reads from the
same tables, multiplied across auto-refreshing dashboard tabs. The 9/9 fix (short-TTL
read cache in mission-control/server.js + throttled hot watchers) held for two weeks,
but the fleet keeps growing (~140 com.exos.* jobs as of 9/24), so the load creeps back.

We do NOT have a Supabase management token or DB password, so the raw Disk IO metric
is not queryable headlessly. Instead this job watches the CONTROLLABLE DRIVERS we own:

  1. Read-cache regression guard — confirm the in-memory list cache is still live in
     server.js with TTL > 0 (a bad edit / env override would silently kill it).
  2. Poller-load audit — enumerate every com.exos.* launchd job, find the ones that
     read Supabase/MC, and sum their runs/hour. This is our proxy for origin read load.
     Compare to the stored baseline and flag material growth.
  3. Hot-reader interval floors — the five watchers we deliberately throttled on 9/9
     must not have regressed below their tuned floor.
  4. Free-lever status — track whether the one-click index SQL (drops 3 cold CRM
     indexes + adds a trigram) has been run in Supabase Studio yet. Until it has,
     running it is the correct next step BEFORE spending money on a compute upgrade.

OUTPUT
------
Writes a health report to logs/ and a state file. Stays SILENT (log only) when
everything is green. DMs Jon on Discord only on a real regression:
  • cache disabled/missing, OR
  • total poll load grew > POLL_GROWTH_ALERT_PCT since baseline, OR
  • a throttled hot-reader dropped below its floor.

ESCALATION LADDER (matches memory guidance):
  new alert  ->  (a) run the free index SQL first  ->  (b) only if it still trips,
  escalate the compute add-on UPGRADE as a Decision. This job flags (a); it will
  print the (b) recommendation once index_sql_confirmed is true and load is still high.

Safe to run manually:  python3 scripts/supabase_diskio_maintenance.py [--verbose]
Reset the baseline:     python3 scripts/supabase_diskio_maintenance.py --rebaseline
Mark the index SQL run: python3 scripts/supabase_diskio_maintenance.py --index-sql-done
"""
import os, sys, json, glob, subprocess, datetime, shutil, re

ROOT = os.path.expanduser("~/.openclaw/workspace")
LA_DIR = os.path.expanduser("~/Library/LaunchAgents")
SERVER_JS = os.path.join(ROOT, "mission-control/server.js")
STATE = os.path.join(ROOT, "mission-control/data/diskio-maintenance-state.json")
LOG = os.path.join(ROOT, "logs/supabase-diskio-maintenance.out.log")
ONECLICK_SQL = os.path.join(ROOT, "drafts/RUN_IN_SUPABASE_STUDIO_MC_indexes_ONECLICK.sql")
PROJECT_REF = "pcrgpuoljylqcumijvnw"

DM_TARGET = "user:1501632195163590739"          # Jon
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/shims/openclaw"

# Alert threshold: how much the total poll load may grow vs baseline before we DM Jon.
POLL_GROWTH_ALERT_PCT = 20.0

# The five hot readers deliberately throttled on 2026-09-09 and their interval FLOORS
# (seconds). If any drops below its floor, someone un-did the throttle -> flag.
HOT_READER_FLOORS = {
    "decision-send-watcher": 180,
    "task-note-command":     300,
    "decision-note-router":  300,
    "delivery-sweeper":      300,
}

# Markers that mean a script reads Supabase/MC (i.e. contributes origin read load).
SB_MARKERS = ("supabase", "rest/v1", "supabase_util", "mission-control/data",
              "pcrgpuoljylqcumijvnw", "/api/", "localhost:", "127.0.0.1:")

VERBOSE = "--verbose" in sys.argv


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = f"[{now_iso()}] {msg}"
    with open(LOG, "a") as f:
        f.write(line + "\n")
    if VERBOSE:
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


def _subprocess_env():
    env = os.environ.copy()
    extra = [os.path.dirname(OPENCLAW), "/Users/exomac/.local/share/mise/shims",
             "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra + [env.get("PATH", "")])
    return env


def dm_jon(text):
    try:
        r = subprocess.run(
            [OPENCLAW, "message", "send", "--channel", "discord",
             "--target", DM_TARGET, "-m", text],
            capture_output=True, text=True, timeout=60, env=_subprocess_env())
        if r.returncode != 0:
            log(f"WARN: discord send rc={r.returncode}: {r.stderr[:200]}")
            return False
        return True
    except Exception as e:
        log(f"WARN: discord send failed: {e}")
        return False


def plist_json(path):
    try:
        out = subprocess.run(["plutil", "-convert", "json", "-o", "-", path],
                             capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def runs_per_hour(pj):
    """Approximate runs/hour from StartInterval or StartCalendarInterval."""
    if "StartInterval" in pj:
        try:
            sec = float(pj["StartInterval"])
            return 3600.0 / sec if sec > 0 else 0.0
        except Exception:
            return 0.0
    sci = pj.get("StartCalendarInterval")
    if sci is None:
        return 0.0
    # A dict = one fire spec; a list = several. Estimate fires/day, /24 for /hour.
    specs = sci if isinstance(sci, list) else [sci]
    fires_per_day = 0.0
    for s in specs:
        if not isinstance(s, dict):
            continue
        if "Minute" in s and "Hour" not in s and "Weekday" not in s and "Day" not in s:
            fires_per_day += 24.0          # every hour at :MM
        elif "Hour" in s and "Weekday" not in s and "Day" not in s:
            fires_per_day += 1.0           # once a day
        elif "Weekday" in s:
            fires_per_day += 1.0 / 7.0     # once a week
        elif "Day" in s:
            fires_per_day += 1.0 / 30.0    # once a month
        else:
            fires_per_day += 1.0
    return fires_per_day / 24.0


def script_target(pj):
    args = pj.get("ProgramArguments") or []
    # Find the last arg that looks like a script path or embedded python invocation.
    for a in reversed(args):
        if not isinstance(a, str):
            continue
        m = re.search(r"(/[^\s]+\.py)", a)
        if m:
            return m.group(1)
        if a.endswith(".py") or a.endswith(".js") or a.endswith(".sh"):
            return a
    return None


def hits_supabase(script_path):
    if not script_path or not os.path.exists(script_path):
        return False
    try:
        with open(script_path, "r", errors="ignore") as f:
            txt = f.read().lower()
    except Exception:
        return False
    return any(m in txt for m in SB_MARKERS)


def audit_pollers():
    rows = []
    for pl in sorted(glob.glob(os.path.join(LA_DIR, "com.exos.*.plist"))):
        if pl.endswith(".bak") or ".bak-" in pl:
            continue
        pj = plist_json(pl)
        if not pj:
            continue
        label = pj.get("Label", os.path.basename(pl).replace(".plist", ""))
        tgt = script_target(pj)
        rph = runs_per_hour(pj)
        sb = hits_supabase(tgt)
        rows.append({"label": label, "target": tgt, "runs_per_hour": round(rph, 3),
                     "hits_sb": sb})
    return rows


def check_cache():
    """Return (ok, detail). ok=False means the read cache is missing or disabled."""
    try:
        with open(SERVER_JS) as f:
            js = f.read()
    except Exception as e:
        return False, f"server.js unreadable: {e}"
    if "_sbCache" not in js or "SB_CACHE_TTL_MS" not in js:
        return False, "read-cache block not found in server.js"
    m = re.search(r"MC_SB_CACHE_TTL_MS\s*\|\|\s*'(\d+)'", js)
    default_ttl = int(m.group(1)) if m else None
    # Env override (if MC is launched with MC_SB_CACHE_TTL_MS) would beat the default;
    # we can only see the source default here.
    if default_ttl is None:
        return True, "cache present; TTL default not parsed"
    if default_ttl <= 0:
        return False, f"cache present but default TTL={default_ttl} (disabled)"
    return True, f"cache present; default TTL={default_ttl}ms"


def check_hot_readers(rows):
    """Return list of (label, interval_sec, floor) for any that dropped below floor."""
    violations = []
    intervals = {}
    for pl in glob.glob(os.path.join(LA_DIR, "com.exos.*.plist")):
        pj = plist_json(pl)
        if not pj:
            continue
        label = pj.get("Label", "").replace("com.exos.", "")
        if label in HOT_READER_FLOORS and "StartInterval" in pj:
            try:
                intervals[label] = int(pj["StartInterval"])
            except Exception:
                pass
    for name, floor in HOT_READER_FLOORS.items():
        iv = intervals.get(name)
        if iv is not None and iv < floor:
            violations.append((name, iv, floor))
    return violations, intervals


def main():
    st = load_state()

    if "--index-sql-done" in sys.argv:
        st["index_sql_confirmed"] = True
        st["index_sql_confirmed_at"] = now_iso()
        save_state(st)
        print("Recorded: one-click index SQL confirmed run.")
        return

    rows = audit_pollers()
    sb_rows = [r for r in rows if r["hits_sb"]]
    total_sb_rph = round(sum(r["runs_per_hour"] for r in sb_rows), 2)
    n_sb = len(sb_rows)

    cache_ok, cache_detail = check_cache()
    violations, hot_intervals = check_hot_readers(rows)
    index_confirmed = bool(st.get("index_sql_confirmed"))

    baseline = st.get("baseline")
    if baseline is None or "--rebaseline" in sys.argv:
        baseline = {"total_sb_rph": total_sb_rph, "n_sb": n_sb, "set_at": now_iso()}
        st["baseline"] = baseline
        log(f"Baseline set: {n_sb} SB pollers, {total_sb_rph} runs/hr")

    growth_pct = 0.0
    if baseline.get("total_sb_rph", 0) > 0:
        growth_pct = round((total_sb_rph - baseline["total_sb_rph"])
                           / baseline["total_sb_rph"] * 100.0, 1)

    # ---- decide severity ----
    alerts = []
    if not cache_ok:
        alerts.append(f"READ CACHE REGRESSED: {cache_detail}")
    if violations:
        for name, iv, floor in violations:
            alerts.append(f"HOT READER un-throttled: {name} at {iv}s (floor {floor}s)")
    if growth_pct > POLL_GROWTH_ALERT_PCT:
        alerts.append(f"Poll load +{growth_pct}% vs baseline "
                      f"({baseline['total_sb_rph']}->{total_sb_rph} runs/hr, "
                      f"{baseline.get('n_sb')}->{n_sb} SB pollers)")

    # top contributors for the report
    top = sorted(sb_rows, key=lambda r: r["runs_per_hour"], reverse=True)[:10]

    cache_word = "OK" if cache_ok else "REGRESSED"
    floors_word = "OK" if not violations else "VIOLATED"
    floors_detail = ", ".join(
        "{}={}s".format(k, hot_intervals.get(k, "?")) for k in HOT_READER_FLOORS)
    if index_confirmed:
        index_word = "confirmed run"
    else:
        index_word = ("NOT yet run (free lever — run "
                      "drafts/RUN_IN_SUPABASE_STUDIO_MC_indexes_ONECLICK.sql "
                      "in Supabase Studio)")
    base_at = str(baseline.get("set_at", "?"))[:10]

    report = [
        "Supabase Disk IO maintenance — {}  (project {})".format(now_iso(), PROJECT_REF),
        "  read cache : {} — {}".format(cache_word, cache_detail),
        "  SB pollers : {} jobs, ~{} origin-read runs/hr (baseline {} @ {}, {:+.1f}%)".format(
            n_sb, total_sb_rph, baseline.get("total_sb_rph"), base_at, growth_pct),
        "  hot floors : {} ({})".format(floors_word, floors_detail),
        "  index SQL  : {}".format(index_word),
        "  top read pollers (runs/hr):",
    ]
    for r in top:
        report.append("    {:>6}  {}".format(r["runs_per_hour"], r["label"]))
    report_txt = "\n".join(report)
    log(report_txt)

    # persist snapshot/history
    st["last_run"] = now_iso()
    st["last_total_sb_rph"] = total_sb_rph
    st["last_n_sb"] = n_sb
    st["last_cache_ok"] = cache_ok
    st["last_growth_pct"] = growth_pct
    hist = st.get("history", [])
    hist.append({"at": now_iso(), "total_sb_rph": total_sb_rph, "n_sb": n_sb,
                 "cache_ok": cache_ok, "growth_pct": growth_pct})
    st["history"] = hist[-52:]   # keep ~1yr of weekly points
    save_state(st)

    if alerts:
        head = "⚠️ MC Supabase Disk IO — maintenance flag"
        body = head + "\n" + "\n".join("• " + a for a in alerts)
        # escalation recommendation
        if index_confirmed:
            body += ("\n\nFree levers exhausted (index SQL already run). "
                     "Next step = escalate a compute add-on UPGRADE Decision.")
        else:
            body += ("\n\nNext step (free, do first): run "
                     "drafts/RUN_IN_SUPABASE_STUDIO_MC_indexes_ONECLICK.sql in Supabase "
                     "Studio, and consider trimming/lengthening the top pollers above "
                     "before any paid compute upgrade.")
        dm_jon(body)
        log("ALERT sent to Jon: " + "; ".join(alerts))
        print(body)
    else:
        log("All green — no alert.")
        if VERBOSE:
            print(report_txt)
            print("\nAll green — no alert sent.")


if __name__ == "__main__":
    main()
