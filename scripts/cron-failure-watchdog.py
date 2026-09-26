#!/usr/bin/env python3
"""
Cron Failure Watchdog
---------------------
Deterministic guardrail (no LLM, no auth, no model-call) that enforces Jon's rule:
  "If a cron job fails twice it should immediately become a task assigned to
   exomac-system to work the fix."

How it works:
  1. Pulls LIVE cron state via `openclaw cron list --json` (state.consecutiveErrors).
  2. Any ENABLED job with consecutiveErrors >= THRESHOLD (2) that isn't already
     filed becomes a task in tasks/exomac-system.md + a Discord alert to
     #exomac-system.
  3. Dedupe via logs/cron-watchdog-state.json so a still-broken job is filed once,
     not every run.
  4. Auto-resolves: when a previously-filed job recovers (consecutiveErrors == 0),
     flips its task to resolved-auto and posts a recovery note.

Runs every 30 min via launchd (com.exos.cron-watchdog). Immune to the failures it
watches because it never calls a model.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

WORKSPACE = "/Users/exomac/.openclaw/workspace"
QUEUE = os.path.join(WORKSPACE, "tasks", "exomac-system.md")
STATE = os.path.join(WORKSPACE, "logs", "cron-watchdog-state.json")
LOG = os.path.join(WORKSPACE, "logs", "cron-watchdog.log")
DISCORD_CHANNEL = "channel:1501636814849577050"  # #exomac-system
THRESHOLD = 2

# launchd has a minimal PATH; resolve the openclaw binary explicitly.
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/shims/openclaw"


def now_iso():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def today():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def logline(msg):
    with open(LOG, "a") as f:
        f.write(f"[{now_iso()}] {msg}\n")


def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE)


def get_jobs():
    out = subprocess.run(
        [OPENCLAW, "cron", "list", "--json"],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        logline(f"ERROR: cron list failed rc={out.returncode}: {out.stderr[:300]}")
        sys.exit(0)  # fail quiet; never crash-loop
    return json.loads(out.stdout).get("jobs", [])


def post_discord(text):
    # Durable delivery: spool-to-disk-then-send so a flaked send can't drop
    # an alert. delivery-sweeper.py retries anything left in outbox/pending.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from deliver import deliver
        deliver(text, target=DISCORD_CHANNEL, source="cron-failure-watchdog")
    except Exception as e:
        # last-resort fallback to the old direct path; never crash the cron
        logline(f"WARN: durable deliver failed, direct-sending: {e}")
        try:
            subprocess.run(
                [OPENCLAW, "message", "send", "--channel", "discord",
                 "--target", DISCORD_CHANNEL, "-m", text],
                capture_output=True, text=True, timeout=60,
            )
        except Exception as e2:
            logline(f"WARN: discord post failed: {e2}")


def task_id_for(job_id):
    return f"TASK-SYS-CRON-{job_id[:8]}"


def append_task(job, tid):
    st = job.get("state", {})
    ce = st.get("consecutiveErrors", 0)
    reason = st.get("lastErrorReason", "unknown")
    summary = (st.get("lastDiagnosticSummary") or st.get("lastError") or "").strip()
    summary = summary.replace("\n", " ")[:500]
    block = f"""
### {tid}: Fix failing cron — {job['name']}
- **Status:** open
- **Priority:** {'critical' if ce >= 5 else 'high'}
- **Submitted:** {today()}
- **Submitted by:** Cron Failure Watchdog (auto)
- **Trigger:** cron job failed {ce}x consecutively (rule: fail twice → exomac-system task)
- **Job ID:** {job['id']}
- **Failure reason:** {reason}
- **Last diagnostic:** {summary}
- **Description:** Cron "{job['name']}" has {ce} consecutive failures. Diagnose and fix the runtime/config so it runs green again, then this task auto-resolves on recovery.
"""
    with open(QUEUE, "a") as f:
        f.write(block)


def resolve_task(tid):
    """Flip the Status line of an existing task block to resolved-auto."""
    if not os.path.exists(QUEUE):
        return
    with open(QUEUE) as f:
        text = f.read()
    # locate the task header, then the first **Status:** line after it
    hdr = f"### {tid}:"
    idx = text.find(hdr)
    if idx == -1:
        return
    seg = text[idx:]
    new_seg = re.sub(r"\*\*Status:\*\*\s*open",
                     f"**Status:** resolved-auto ({today()})", seg, count=1)
    if new_seg != seg:
        text = text[:idx] + new_seg
        with open(QUEUE, "w") as f:
            f.write(text)


def main():
    jobs = get_jobs()
    state = load_state()
    filed = state.setdefault("filed", {})  # jobId -> {taskId, errors, filedAt}

    for job in jobs:
        if not job.get("enabled"):
            continue
        jid = job["id"]
        ce = job.get("state", {}).get("consecutiveErrors", 0)
        tid = task_id_for(jid)

        if ce >= THRESHOLD and jid not in filed:
            append_task(job, tid)
            filed[jid] = {"taskId": tid, "errors": ce, "filedAt": now_iso(),
                          "name": job["name"]}
            reason = job.get("state", {}).get("lastErrorReason", "unknown")
            post_discord(
                f"🛠️ **Cron Watchdog → exomac-system**\n"
                f"`{job['name']}` failed **{ce}x** (reason: {reason}). "
                f"Filed **{tid}** in the exomac-system queue.\n"
                f"Rule: fail twice → auto-task for the fix."
            )
            logline(f"FILED {tid} for '{job['name']}' (ce={ce}, reason={reason})")

        elif ce == 0 and jid in filed:
            tid = filed[jid]["taskId"]
            resolve_task(tid)
            post_discord(
                f"✅ **Cron Watchdog**\n`{job['name']}` recovered (0 errors). "
                f"Auto-resolved **{tid}**."
            )
            logline(f"RESOLVED {tid} for '{job['name']}' (recovered)")
            del filed[jid]

    save_state(state)


if __name__ == "__main__":
    main()
