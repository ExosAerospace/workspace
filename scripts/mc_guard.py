#!/usr/bin/env python3
"""mc_guard.py — control + reporting for the Mission Control Guard (mission-control/lib/guard.js).

  python3 scripts/mc_guard.py status            # mode, locked identities, thresholds
  python3 scripts/mc_guard.py unlock <key>      # ONLY on Jon's (or, in an entity cell, a cell admin's) instruction;
                                                #   releases a permanent lock or a temp ("access paused") lock
  python3 scripts/mc_guard.py selftest          # liveness/eval: robots, bait, blocklist, evidence chain + unit test
  python3 scripts/mc_guard.py unit              # offline unit test of the graduated response (temp lock tier)
  python3 scripts/mc_guard.py weekly [--dry]    # top data users (7d) + watch-mode tuning proposal → DM Jon

The weekly job (launchd com.exos.mc-guard-weekly, Sat 08:00) is exception-light: it always sends the
top-users table (Jon asked for it), and adds threshold-tuning numbers while scoring is watch-only.
"""
import json, os, sys, hashlib, shutil, subprocess, urllib.request, statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MC = os.path.join(WS, "mission-control")
LOG_DIR = os.path.join(WS, "logs", "mc-guard")
BASE = "http://127.0.0.1:8080"
JON = "user:1501632195163590739"


def token():
    with open(os.path.join(MC, "data", ".guard-admin-token")) as f:
        return f.read().strip()


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"X-Guard-Token": token(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def dm(text, dry=False):
    if dry:
        print(text); return
    subprocess.run([sys.executable, os.path.join(WS, "scripts", "deliver.py"), "--target", JON,
                    "--source", "mc-guard-weekly", "-m", text], cwd=WS, timeout=120)


def verify_chain():
    path = os.path.join(LOG_DIR, "evidence.jsonl")
    if not os.path.exists(path):
        return True, 0
    prev, n = "GENESIS", 0
    with open(path) as f:
        for line in f:
            r = json.loads(line); n += 1
            if r.get("prev") != prev:
                return False, n
            prev = r.get("hash")
    return True, n


def unit():
    """Offline node test of lib/guard.js (temp lock 15m -> 60m -> permanent, 423, expiry, tripwire, cell admins).
    Uses a temp state dir, no DMs, no Cloudflare. Returns (ok, last output line)."""
    node = shutil.which("node") or next((p for p in ("/opt/homebrew/bin/node", "/usr/local/bin/node") if os.path.exists(p)), None)
    if not node:
        return None, "node not found (unit test skipped)"
    r = subprocess.run([node, os.path.join(MC, "tests", "guard_templock_selftest.js")], cwd=WS,
                       capture_output=True, text=True, timeout=120)
    out = (r.stdout + r.stderr).strip()
    return r.returncode == 0, out


def selftest():
    fails = []
    ok_unit, out = unit()
    if ok_unit is False:
        fails.append("unit test FAILED: " + out.splitlines()[-1][:200] if out else "unit test FAILED")
    try:
        with urllib.request.urlopen(BASE + "/robots.txt", timeout=10) as r:
            if b"/api/export/all" not in r.read():
                fails.append("robots.txt missing bait")
    except Exception as e:
        fails.append(f"robots.txt: {e}")
    try:
        st = api("GET", "/api/admin/guard/status")
        if st.get("scoring_mode") not in ("watch", "enforce"):
            fails.append("bad scoring_mode")
    except Exception as e:
        fails.append(f"status API: {e}")
    try:  # loopback automation is exempt: tripwire must answer 404 and NOT lock anything
        urllib.request.urlopen(BASE + "/api/export/all", timeout=10)
        fails.append("tripwire path served content")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            fails.append(f"tripwire returned {e.code}")
    ok, n = verify_chain()
    if not ok:
        fails.append(f"evidence hash chain BROKEN at entry {n}")
    print("SELFTEST", "PASS" if not fails else "FAIL", fails)
    return 0 if not fails else 1


def weekly(dry=False):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    rows = []
    p = os.path.join(LOG_DIR, "hourly.jsonl")
    if os.path.exists(p):
        for line in open(p):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if datetime.fromisoformat(r["hour"].replace("Z", "+00:00")) >= since and not r.get("automation"):
                rows.append(r)
    per = defaultdict(lambda: dict(req=0, records=0, downloads=0, bytes=0, denied=0, peak_score=0, peak_rpm=0, hours=0, ua_auto=False, email=""))
    for r in rows:
        a = per[r["key"]]
        for k in ("req", "records", "downloads", "bytes", "denied"):
            a[k] += r.get(k, 0)
        a["peak_score"] = max(a["peak_score"], r.get("peak_score", 0))
        a["peak_rpm"] = max(a["peak_rpm"], r.get("peak_rpm", 0))
        a["hours"] += 1
        a["ua_auto"] = a["ua_auto"] or r.get("ua_auto", False)
        a["email"] = a["email"] or r.get("email", "")
    top = sorted(per.items(), key=lambda kv: (kv[1]["downloads"], kv[1]["records"], kv[1]["req"]), reverse=True)[:8]
    try:
        st = api("GET", "/api/admin/guard/status")
    except Exception as e:
        st = {"scoring_mode": "?", "locked": {}, "error": str(e)}
    lines = [f"🛡️ **MC Guard — weekly data-use report** (last 7 days · scoring: {st.get('scoring_mode')})"]
    if not top:
        lines.append("- No non-automation activity recorded.")
    for key, a in top:
        who = a["email"] or key
        lines.append(f"- **{who}**: {a['downloads']} downloads ({a['bytes'] / 1e6:.0f} MB), {a['records']} records, "
                     f"{a['req']} requests, peak {a['peak_rpm']}/min, peak score {a['peak_score']}"
                     + (" · ⚠️ automated client" if a["ua_auto"] else ""))
    if st.get("locked"):
        lines.append("Locked: " + ", ".join(f"{k} ({v.get('reason')})" for k, v in st["locked"].items()))
    if st.get("temp_locked"):
        lines.append("Paused (temp): " + ", ".join(f"{k} until {v.get('until')} (#{v.get('n')})" for k, v in st["temp_locked"].items()))
    if st.get("scoring_mode") == "watch" and rows:
        def p99(vals):
            vals = sorted(vals)
            return vals[min(len(vals) - 1, int(len(vals) * 0.99))] if vals else 0
        lines.append("**Tuning (watch-only):** observed per-user-hour p99 — "
                     f"rate {p99([r.get('peak_rpm', 0) for r in rows])}/min, "
                     f"records {p99([r.get('records', 0) for r in rows])}/hr, "
                     f"downloads {p99([r.get('downloads', 0) for r in rows])}/hr. "
                     "Current lockout thresholds: rate 300/min, 1000 records/hr, 75 downloads/hr.")
    ok, n = verify_chain()
    if not ok:
        lines.append(f"🔴 Evidence log hash chain BROKEN at entry {n} — possible tampering.")
    dm("\n".join(lines), dry)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(api("GET", "/api/admin/guard/status"), indent=2))
    elif cmd == "unlock" and len(sys.argv) > 2:
        print(json.dumps(api("POST", "/api/admin/guard/unlock", {"key": sys.argv[2]}), indent=2))
    elif cmd == "selftest":
        sys.exit(selftest())
    elif cmd == "unit":
        ok_unit, out = unit()
        print(out)
        sys.exit(0 if ok_unit else 1)
    elif cmd == "weekly":
        rc = selftest()
        sys.exit(weekly(dry="--dry" in sys.argv) or rc)
    else:
        print(__doc__); sys.exit(2)
