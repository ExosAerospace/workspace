#!/usr/bin/env python3
"""
Completion Watchdog — catches QUIET FAILS that never finish.
------------------------------------------------------------
Companion to cron-failure-watchdog.py. That one catches launchd exit!=0 (twice).
This one catches the failures launchd can't see, by reading the govlog substrate
(governance/events.jsonl), where every worker emits start / end / error with a
correlation id:

  (A) STALLED  — a run logged `start` but never logged `end` and it began more than
                 STALL_MIN ago  => it was killed / hung / crashed mid-run and never
                 finished (e.g. a subagent stopped, a SIGKILL, an infinite wait).
  (B) ERRORED  — a run logged an `error` event even though it may have exited 0
                 (internal failure invisible to launchd; e.g. a KeyError that the
                 script swallows). These are "green but broken".

Both are surfaced to ONE place — a Discord alert to #exomac-system + an entry in
tasks/exomac-system.md — deduped so a still-broken thing files once, not every run.
Model-free, launchd-run (com.exos.completion-watchdog), so it is immune to the
failures it watches. First run marks existing history as seen (summary only) so it
does not flood.

Run: python3 scripts/completion-watchdog.py [--dry-run]
"""
import json, os, sys, subprocess, shutil
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from collections import defaultdict
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
EVENTS = os.path.join(WS, "governance", "events.jsonl")
STATE = os.path.join(WS, "logs", "completion-watchdog-state.json")
LOG = os.path.join(WS, "logs", "completion-watchdog.log")
QUEUE = os.path.join(WS, "tasks", "exomac-system.md")
DISCORD_CHANNEL = "channel:1501636814849577050"  # #exomac-system
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"

STALL_MIN = int(os.environ.get("CW_STALL_MIN", "30"))     # start w/o end older than this = stalled
LOOKBACK_H = int(os.environ.get("CW_LOOKBACK_H", "24"))    # only consider recent runs
MAX_ALERT = int(os.environ.get("CW_MAX_ALERT", "12"))      # cap items per alert; rest summarized
TASK_STALL_MIN = int(os.environ.get("CW_TASK_STALL_MIN", "45"))  # running/queued task older than this = stalled
# agents that legitimately run long / stream and should not be stall-flagged
STALL_EXEMPT = {a for a in os.environ.get("CW_STALL_EXEMPT", "").split(",") if a}
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"


def scan_tasks():
    """#1 subagent/task completion: read `openclaw tasks --json` (the registry that tracks
    subagents, crons, and cli tasks). Returns (failed, stalled) as (taskId, runtime, label).
    Catches a subagent that died/was killed or a task hung 'running' — the class govlog misses
    (Agent-tool subagents don't emit govlog)."""
    failed, stalled = [], []
    try:
        out = subprocess.run([OPENCLAW, "tasks", "--json"], capture_output=True, text=True, timeout=60).stdout
        d = json.loads(out)
    except Exception as e:
        logline(f"WARN tasks --json failed: {e}")
        return failed, stalled
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    for t in d.get("tasks", []):
        tid = "task:" + (t.get("taskId") or "")
        stt = (t.get("status") or "").lower()
        label = (t.get("terminalSummary") or t.get("task") or "")[:70].replace("\n", " ")
        rt = t.get("runtime", "?")
        if stt in ("failed", "error"):
            failed.append((tid, rt, label))
        elif stt in ("running", "queued", "in_progress"):
            started = t.get("startedAt") or t.get("createdAt")
            try:
                age = (now_ms - float(started)) / 60000.0
            except (TypeError, ValueError):
                age = 0
            if age >= TASK_STALL_MIN:
                stalled.append((tid, rt, f"{label} (~{round(age)}m {stt})"))
    return failed, stalled


def logline(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {m}\n")


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"seen": [], "initialized": False}


def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w"), indent=2)


def parse_ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return None


def post_discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD_CHANNEL, "-m", text],
                       check=False, timeout=45, capture_output=True)
    except Exception as e:
        logline(f"WARN discord post failed: {e}")


def file_queue(lines):
    try:
        os.makedirs(os.path.dirname(QUEUE), exist_ok=True)
        with open(QUEUE, "a") as f:
            f.write(f"\n## [completion-watchdog {datetime.now():%Y-%m-%d %H:%M}] quiet-fail sweep\n")
            for l in lines:
                f.write(f"- [ ] {l}\n")
    except Exception as e:
        logline(f"WARN queue write failed: {e}")


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(EVENTS):
        logline("no events.jsonl"); return
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=LOOKBACK_H)

    # Build per-run state from recent events.
    runs = {}  # cid -> {agent,start,end,errors[],last}
    with open(EVENTS, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            ts = parse_ts(r.get("ts", ""))
            if not ts or ts < cutoff:
                continue
            cid = r.get("correlation_id") or ""
            if not cid:
                continue
            d = runs.setdefault(cid, {"agent": r.get("agent", "?"), "start": None,
                                      "end": False, "errors": [], "last": ts})
            d["last"] = max(d["last"], ts)
            ev = r.get("event")
            if ev == "start":
                d["start"] = ts
            elif ev == "end":
                d["end"] = True
            # Transient net/mail blips are logged as status="transient" (skips, not
            # defects) — never page on them; sustained outages surface via cron-failure-watchdog.
            if r.get("status") == "transient":
                pass
            elif r.get("status") == "error" or ev == "error":
                d["errors"].append((r.get("detail") or r.get("event") or "error"))

    stalled, errored = [], []
    for cid, d in runs.items():
        agent = d["agent"]
        if d["errors"]:
            errored.append((cid, agent, d["errors"][0]))
        if d["start"] and not d["end"] and agent not in STALL_EXEMPT:
            age = (now - d["start"]).total_seconds() / 60.0
            if age >= STALL_MIN:
                stalled.append((cid, agent, round(age)))

    # #1 — subagent/task completion (from the openclaw tasks registry).
    t_failed, t_stalled = scan_tasks()

    st = load_state()
    seen = set(st.get("seen", []))
    all_ids = ([c for c, *_ in stalled] + [c for c, *_ in errored]
               + [c for c, *_ in t_failed] + [c for c, *_ in t_stalled])

    # First-ever run: baseline all current findings so we don't flood on backlog.
    if not st.get("initialized") and not dry:
        seen.update(all_ids)
        st["seen"] = list(seen)[-8000:]
        st["initialized"] = True
        save_state(st)
        logline(f"initialized; baselined {len(all_ids)} pre-existing findings")
        print(f"initialized — baselined {len(all_ids)} findings (no alert on backlog).")
        return

    new_stalled = [x for x in stalled if x[0] not in seen]
    new_errored = [x for x in errored if x[0] not in seen]
    new_tfail = [x for x in t_failed if x[0] not in seen]
    new_tstall = [x for x in t_stalled if x[0] not in seen]
    if not (new_stalled or new_errored or new_tfail or new_tstall):
        logline("no new quiet-fails")
        print("no new quiet-fails")
        return

    # Collapse govlog errors by agent so a repeatedly-broken worker files once per sweep.
    err_by_agent = defaultdict(list)
    for cid, agent, detail in new_errored:
        err_by_agent[agent].append(detail)

    qlines = []
    for cid, agent, age in new_stalled[:MAX_ALERT]:
        qlines.append(f"STALLED (worker): `{agent}` started but never finished (~{age} min) — killed/hung mid-run.")
    for tid, rt, label in new_tstall[:MAX_ALERT]:
        qlines.append(f"STALLED ({rt} task): {label} — running past {TASK_STALL_MIN}m, likely hung/killed.")
    for tid, rt, label in new_tfail[:MAX_ALERT]:
        qlines.append(f"FAILED ({rt} task): {label}")
    for agent, details in list(err_by_agent.items())[:MAX_ALERT]:
        qlines.append(f"ERRORED (worker): `{agent}` internal error while exiting 'green': {details[0][:120]} (x{len(details)}).")

    n_worker = len(new_stalled) + len(err_by_agent)
    n_task = len(new_tfail) + len(new_tstall)
    header = (f"⚠️ Completion Watchdog — {n_task} failed/stalled task(s) + {n_worker} worker issue(s) "
              f"caught (quiet fails launchd can't see):")
    body = header + "\n" + "\n".join("• " + q for q in qlines[:MAX_ALERT * 2])

    if dry:
        print(body)
    else:
        post_discord(body)
        file_queue(qlines)
        seen.update(x[0] for x in new_stalled + new_errored + new_tfail + new_tstall)
        st["seen"] = list(seen)[-8000:]
        save_state(st)
    logline(f"alerted: {n_task} task issues, {n_worker} worker issues")
    print(f"alerted: {n_task} task issues, {n_worker} worker issues")


if __name__ == "__main__":
    main()
