#!/usr/bin/env python3
"""
Cracks Digest — ONE calm daily summary of everything that fell through.
----------------------------------------------------------------------
Jon: "one calm summary, not a stream." The 20-min completion-watchdog alerts NEW
urgent quiet-fails as they happen; this posts once a day (launchd, ~07:00 CT) with
the full last-24h picture PLUS the "scheduled-but-never-ran" check (#2) that the
urgent watchdog does not do. Model-free.

Sources:
  - `openclaw tasks --json`         -> failed / cancelled tasks (subagents, crons, cli)
  - governance/events.jsonl         -> internal errors + start-without-end stalls (24h)
  - governance/events.jsonl (14d)   -> #2 DID-NOT-RUN: agents whose time-since-last-start
                                       exceeds 3x their own median cadence (self-calibrating)

Posts one message to #exomac-system. Posts an explicit "all clear" when nothing is
wrong, so Jon gets positive confirmation and can stop policing.

Run: python3 scripts/cracks-digest.py [--dry-run]
"""
import json, os, sys, subprocess, shutil, statistics
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from collections import defaultdict
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
EVENTS = os.path.join(WS, "governance", "events.jsonl")
LOG = os.path.join(WS, "logs", "cracks-digest.log")
DISCORD_CHANNEL = "channel:1501636814849577050"  # #exomac-system
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"

STALL_MIN = 30
CADENCE_DAYS = int(os.environ.get("CD_CADENCE_DAYS", "14"))     # history window for cadence
CADENCE_MULT = float(os.environ.get("CD_CADENCE_MULT", "3.0"))  # overdue if gap > mult x median
CADENCE_MIN_RUNS = int(os.environ.get("CD_MIN_RUNS", "6"))      # need this much history to judge
CADENCE_FLOOR_MIN = int(os.environ.get("CD_FLOOR_MIN", "90"))   # never flag under this many minutes


def logline(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {m}\n")


def post_discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD_CHANNEL, "-m", text],
                       check=False, timeout=45, capture_output=True)
    except Exception as e:
        logline(f"WARN discord post failed: {e}")


def parse_ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return None


def tasks_failed():
    failed, cancelled = [], []
    try:
        out = subprocess.run([OPENCLAW, "tasks", "--json"], capture_output=True, text=True, timeout=60).stdout
        d = json.loads(out)
    except Exception as e:
        logline(f"WARN tasks --json: {e}")
        return failed, cancelled
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    for t in d.get("tasks", []):
        created = t.get("endedAt") or t.get("createdAt") or 0
        try:
            recent = (now_ms - float(created)) / 3600000.0 <= 24
        except (TypeError, ValueError):
            recent = True
        if not recent:
            continue
        stt = (t.get("status") or "").lower()
        label = (t.get("terminalSummary") or t.get("task") or "")[:75].replace("\n", " ")
        if stt in ("failed", "error"):
            failed.append(f"{t.get('runtime','?')}: {label}")
        elif stt == "cancelled":
            cancelled.append(f"{t.get('runtime','?')}: {label}")
    return failed, cancelled


def govlog_scan():
    """Return (errored_by_agent, stalled_agents, cadence_overdue) over the windows."""
    now = datetime.now(timezone.utc)
    day_cut = now - timedelta(hours=24)
    cad_cut = now - timedelta(days=CADENCE_DAYS)
    runs = {}
    starts = defaultdict(list)  # agent -> [start ts] for cadence
    try:
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
                if not ts or ts < cad_cut:
                    continue
                agent = r.get("agent", "?")
                if r.get("event") == "start":
                    starts[agent].append(ts)
                if ts < day_cut:
                    continue
                cid = r.get("correlation_id") or ""
                if not cid:
                    continue
                d = runs.setdefault(cid, {"agent": agent, "start": None, "end": False, "err": None})
                if r.get("event") == "start":
                    d["start"] = ts
                elif r.get("event") == "end":
                    d["end"] = True
                if r.get("status") == "error" or r.get("event") == "error":
                    d["err"] = r.get("detail") or "error"
    except FileNotFoundError:
        return {}, [], []

    errored = defaultdict(int)
    stalled = []
    for cid, d in runs.items():
        if d["err"]:
            errored[d["agent"]] += 1
        if d["start"] and not d["end"] and (now - d["start"]).total_seconds() / 60 >= STALL_MIN:
            stalled.append(d["agent"])

    overdue = []
    for agent, tss in starts.items():
        if len(tss) < CADENCE_MIN_RUNS:
            continue
        tss.sort()
        gaps = [(tss[i] - tss[i - 1]).total_seconds() / 60 for i in range(1, len(tss))]
        med = statistics.median(gaps)
        since = (now - tss[-1]).total_seconds() / 60
        thresh = max(CADENCE_MULT * med, CADENCE_FLOOR_MIN)
        if since > thresh:
            overdue.append((agent, round(since / 60, 1), round(med)))
    return dict(errored), sorted(set(stalled)), sorted(overdue, key=lambda x: -x[1])


def main():
    dry = "--dry-run" in sys.argv
    failed, cancelled = tasks_failed()
    errored, stalled, overdue = govlog_scan()

    lines = []
    if failed:
        lines.append(f"**❌ Failed tasks (24h): {len(failed)}**")
        lines += [f"• {x}" for x in failed[:15]]
    if stalled:
        lines.append(f"**⏳ Stalled workers (start, no finish): {len(stalled)}**")
        lines += [f"• `{a}`" for a in stalled[:15]]
    if errored:
        lines.append(f"**🟠 Green-but-errored workers (24h): {len(errored)}**")
        lines += [f"• `{a}` (x{n})" for a, n in sorted(errored.items(), key=lambda x: -x[1])[:15]]
    if overdue:
        lines.append(f"**🔕 May have STOPPED running (overdue vs own cadence): {len(overdue)}**")
        lines += [f"• `{a}` — last ran {h}h ago (normally ~every {m}m)" for a, h, m in overdue[:15]]
    if cancelled:
        lines.append(f"_ℹ️ {len(cancelled)} cancelled task(s) (often intentional) — not counted as failures._")

    stamp = datetime.now().strftime("%a %Y-%m-%d")
    if lines:
        body = f"🗒️ **Cracks Digest — {stamp}** (things that fell through in the last 24h)\n" + "\n".join(lines)
        body += "\n_Urgent items are also alerted live by the completion-watchdog._"
    else:
        body = f"🗒️ **Cracks Digest — {stamp}: ✅ all clear.** No failed/stalled tasks, no green-but-broken workers, nothing overdue vs its cadence."

    if dry:
        print(body)
    else:
        post_discord(body)
    logline(f"digest posted: {len(failed)} failed, {len(stalled)} stalled, {len(errored)} errored, {len(overdue)} overdue")
    print(f"failed={len(failed)} stalled={len(stalled)} errored={len(errored)} overdue={len(overdue)}")


if __name__ == "__main__":
    main()
