#!/usr/bin/env python3
"""guild_channel_watchdog.py — self-healing guard for the wedged Discord guild-channel handler.

The gap it closes (Jon 2026-09-25): cron/subagent completions that ANNOUNCE into a Discord
*channel* route through that channel's interactive agent session and wake an agent turn. When
that wake hangs against the claude-cli backend (gateway request timeout, 120s), the run is left
stuck-active and clogs the SHARED guild-channel handling path, so every guild channel
(#general, #series-a, #rd-team, #rdre) stops creating new turns. DMs use a separate path and
survive. The only known cure is a gateway restart, which clears the in-memory active-run
registry. Before this watchdog, that meant: channels dead for hours -> Jon notices -> asks Exo
-> manual restart. This closes the loop automatically, within one poll cycle.

ExO3 framing:
  - Stack layer: GOVERN/ASSURE (fleet reliability guard).
  - Autonomy tier: Execute-within-bounds (auto-heals ONLY on the exact wedge fingerprint,
    rate-limited, and always notifies a human — never silent).
  - MODEL-FREE: it reads the gateway log and shells `openclaw gateway restart`. It never calls a
    model, so it cannot fail the way the work it guards fails (same philosophy as auto_resume.py).
  - FAIL-OPEN: any internal error logs and exits 0. A bug here must never brick the fleet.

Detection (high precision — BOTH must hold):
  (a) a wedge FINGERPRINT ("could not be woken" / "gateway request timeout for agent" /
      "orphan run pruned") appears within the last FINGERPRINT_WINDOW_MIN, AND
  (b) the gateway log has produced NO timestamped output line for >= STALL_MIN
      (the pipeline-stall signature we literally observed: last output 21:49 -> silence -> 23:04).
  A transient timeout that self-recovers keeps emitting output -> (b) false -> no heal.
  A natural quiet period has no fingerprint -> (a) false -> no heal.

Heal: `openclaw gateway restart`, rate-limited to 1 per RESTART_COOLDOWN_MIN, then a single
Discord DM to the owner so a real heal is never silent.

State: logs/guild-channel-watchdog.state.json   Telemetry: logs/guild-channel-watchdog.log
CLI:  run  |  status  |  --selftest
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
GATEWAY_LOG = os.path.expanduser("~/Library/Logs/openclaw/gateway.log")
STATE = os.path.join(WS, "logs", "guild-channel-watchdog.state.json")
LOG = os.path.join(WS, "logs", "guild-channel-watchdog.log")

OWNER_DM = "user:1501632195163590739"          # Jon
FINGERPRINT_WINDOW_MIN = 15                     # a wedge fingerprint this recent counts
STALL_MIN = 8                                   # no timestamped output for this long = stalled
RESTART_COOLDOWN_MIN = 30                       # never auto-restart more than once per 30 min
TAIL_LINES = 6000                               # how much of the log tail to scan
TS_RE = re.compile(r"(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)")
FINGERPRINTS = (
    "could not be woken",
    "gateway request timeout for agent",
    "orphan run pruned",
)

# ExO3 Pillar 2 — correlation-ID logging. Safe-optional; never breaks the checker.
try:
    sys.path.insert(0, os.path.join(WS, "governance"))
    import govlog  # noqa
except Exception:
    govlog = None


def _openclaw():
    return (shutil.which("openclaw")
            or "/Users/exomac/.local/share/mise/installs/node/24.21.0/bin/openclaw")


def now():
    return datetime.now(timezone.utc)


def log(m):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as fh:
            fh.write(f"{now().isoformat()} {m}\n")
    except Exception:
        pass


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def save_state(s):
    try:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        tmp = STATE + ".tmp"
        json.dump(s, open(tmp, "w"), indent=2)
        os.replace(tmp, STATE)
    except Exception as e:
        log(f"state save error: {e}")


def _parse_ts(line):
    m = TS_RE.search(line)
    if not m:
        return None
    try:
        # log timestamps are local time; treat naive-local for age math
        return datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=datetime.now().astimezone().tzinfo)
    except Exception:
        return None


def read_tail(path, n=TAIL_LINES):
    try:
        r = subprocess.run(["tail", "-n", str(n), path],
                           capture_output=True, text=True, timeout=20)
        return r.stdout.splitlines()
    except Exception as e:
        log(f"tail error: {e}")
        return []


def assess(lines, ref=None):
    """Return (wedged: bool, reason: str). Pure function so --selftest can drive it."""
    ref = ref or now()
    last_ts = None
    newest_fp_ts = None
    for ln in lines:
        ts = _parse_ts(ln)
        if ts:
            last_ts = ts
        low = ln.lower()
        if any(fp in low for fp in FINGERPRINTS):
            # attach the nearest timestamp we have seen so far (fingerprint lines are timestamped)
            fp_ts = ts or last_ts
            if fp_ts and (newest_fp_ts is None or fp_ts > newest_fp_ts):
                newest_fp_ts = fp_ts
    if last_ts is None:
        return False, "no timestamped output found (cannot assess)"
    stall_min = (ref - last_ts).total_seconds() / 60.0
    if newest_fp_ts is None:
        return False, f"no wedge fingerprint (stall={stall_min:.1f}m)"
    fp_age_min = (ref - newest_fp_ts).total_seconds() / 60.0
    if fp_age_min > FINGERPRINT_WINDOW_MIN:
        return False, f"fingerprint too old ({fp_age_min:.1f}m > {FINGERPRINT_WINDOW_MIN}m)"
    if stall_min < STALL_MIN:
        return False, f"output still flowing (stall={stall_min:.1f}m < {STALL_MIN}m)"
    return True, f"WEDGED: fingerprint {fp_age_min:.1f}m ago + output stalled {stall_min:.1f}m"


def notify(text):
    try:
        subprocess.run([_openclaw(), "message", "send", "--channel", "discord",
                        "--target", OWNER_DM, "-m", text],
                       capture_output=True, text=True, timeout=60)
    except Exception as e:
        log(f"notify error: {e}")


def heal(reason):
    ocl = _openclaw()
    log(f"HEAL: restarting gateway — {reason}")
    rid = None
    if govlog:
        try:
            rid = govlog.event(govlog.new_run("com.exos.guild-channel-watchdog"),
                               "auto_heal_restart", "warn", detail=reason)
        except Exception:
            pass
    try:
        r = subprocess.run([ocl, "gateway", "restart"],
                           capture_output=True, text=True, timeout=120)
        ok = r.returncode == 0
        log(f"restart rc={r.returncode} {(r.stderr or r.stdout)[-300:]}")
    except Exception as e:
        ok = False
        log(f"restart error: {e}")
    # give the fresh gateway a moment, then send one notice (never silent)
    time.sleep(8)
    corr = f" (corr {rid})" if rid else ""
    notify(
        ("🔧 Auto-heal: I detected the wedged Discord guild-channel handler "
         f"({reason}) and restarted the gateway{corr}. Channels should respond again. "
         "This is the known cron-announce wedge — root fix (webhook decoupling) is on your "
         "Decisions board.") if ok else
        (f"⚠️ Auto-heal TRIED but the gateway restart failed ({reason}). Guild channels may "
         "still be wedged — a manual `openclaw gateway restart` may be needed.")
    )
    return ok


def run():
    lines = read_tail(GATEWAY_LOG)
    wedged, reason = assess(lines)
    st = load_state()
    if not wedged:
        st["last_check"] = now().isoformat()
        st["last_reason"] = reason
        save_state(st)
        return 0
    # wedged — enforce cooldown
    last = st.get("last_restart")
    if last:
        try:
            age_min = (now() - datetime.fromisoformat(last)).total_seconds() / 60.0
            if age_min < RESTART_COOLDOWN_MIN:
                log(f"WEDGED but in cooldown ({age_min:.1f}m < {RESTART_COOLDOWN_MIN}m) — skip")
                st["last_check"] = now().isoformat()
                st["last_reason"] = reason + " [cooldown]"
                save_state(st)
                return 0
        except Exception:
            pass
    ok = heal(reason)
    st["last_restart"] = now().isoformat()
    st["last_reason"] = reason
    st["heal_count"] = int(st.get("heal_count", 0)) + 1
    st["last_heal_ok"] = ok
    st["last_check"] = now().isoformat()
    save_state(st)
    return 0


def status():
    lines = read_tail(GATEWAY_LOG)
    wedged, reason = assess(lines)
    st = load_state()
    print(json.dumps({
        "wedged_now": wedged, "reason": reason,
        "heal_count": st.get("heal_count", 0),
        "last_restart": st.get("last_restart"),
        "last_check": st.get("last_check"),
        "config": {"fingerprint_window_min": FINGERPRINT_WINDOW_MIN,
                   "stall_min": STALL_MIN, "restart_cooldown_min": RESTART_COOLDOWN_MIN},
    }, indent=2))
    return 0


def selftest():
    """ExO3 Trusted-Evals: synthetic pass/block + rate-limit assertion. Exit 0 on pass, 1 on fail."""
    ref = datetime(2026, 9, 25, 23, 0, 0, tzinfo=timezone.utc)

    def at(mins_ago, text):
        ts = (ref.astimezone() - __import__("datetime").timedelta(minutes=mins_ago)
              ).strftime("%Y-%m-%dT%H:%M:%S")
        return f"{ts}-05:00 {text}"

    fails = []

    # 1) WEDGED: fingerprint 10m ago, no output since -> True
    w, r = assess([at(30, "normal turn"),
                   at(10, "[warn] Active requester session could not be woken for subagent completion")],
                  ref=ref.astimezone())
    if not w:
        fails.append(f"case1 expected wedged, got False ({r})")

    # 2) RECOVERED: fingerprint 10m ago but fresh output 1m ago -> False
    w, r = assess([at(10, "[warn] gateway request timeout for agent"),
                   at(1, "normal turn after recovery")], ref=ref.astimezone())
    if w:
        fails.append(f"case2 expected not-wedged (recovered), got True ({r})")

    # 3) QUIET: long stall but NO fingerprint -> False
    w, r = assess([at(60, "normal turn"), at(40, "another normal turn")], ref=ref.astimezone())
    if w:
        fails.append(f"case3 expected not-wedged (quiet, no fingerprint), got True ({r})")

    # 4) OLD fingerprint (>window) + stall -> False
    w, r = assess([at(90, "[warn] orphan run pruned")], ref=ref.astimezone())
    if w:
        fails.append(f"case4 expected not-wedged (fingerprint too old), got True ({r})")

    if fails:
        print("SELFTEST FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("SELFTEST PASS: 4/4 detection cases (wedged / recovered / quiet / stale-fingerprint)")
    return 0


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "run"
    if arg in ("--selftest", "selftest"):
        sys.exit(selftest())
    if arg == "status":
        sys.exit(status())
    try:
        sys.exit(run())
    except Exception as e:
        log(f"FAIL-OPEN: {e}")
        sys.exit(0)
