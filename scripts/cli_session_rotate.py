#!/usr/bin/env python3
"""cli_session_rotate.py — detect and reset oversized / watchdog-killed claude-cli sessions.

Run with no args for a dry-run report. Pass --apply to rotate (rename .jsonl → .jsonl.rotated).
After rotation the next OpenClaw turn starts a fresh CLI session (transcript-missing binding clear),
reseeded from the compact OpenClaw SQLite transcript.

Usage:
  python3 scripts/cli_session_rotate.py            # dry-run: list oversized + recently killed sessions
  python3 scripts/cli_session_rotate.py --apply    # rotate sessions that meet rotation criteria
  python3 scripts/cli_session_rotate.py --selftest # basic smoke test (no files touched)
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

WORKSPACE_PROJECT = str(Path.home() / ".claude" / "projects" / "-Users-exomac--openclaw-workspace")
LOG_GLOB = "/tmp/openclaw/openclaw-*.log"

# ~250K tokens ≈ 15 MB of JSONL (conservative; JSONL has heavy JSON overhead)
OVERSIZE_BYTES = 15 * 1024 * 1024

# Only rotate sessions killed within the last 48 hours
KILL_WINDOW_HOURS = 48


def find_oversized_sessions() -> list[dict]:
    """Return list of {path, uuid, size_mb} for JSONL files above OVERSIZE_BYTES."""
    results = []
    for path in glob.glob(os.path.join(WORKSPACE_PROJECT, "*.jsonl")):
        sz = os.path.getsize(path)
        if sz >= OVERSIZE_BYTES:
            uuid = os.path.basename(path).replace(".jsonl", "")
            results.append({"path": path, "uuid": uuid, "size_mb": sz / 1024 / 1024})
    results.sort(key=lambda x: x["size_mb"], reverse=True)
    return results


def find_recent_kills(hours: int = KILL_WINDOW_HOURS) -> list[dict]:
    """Parse openclaw logs and return kills within `hours` of now."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    pattern = re.compile(
        r'"message":"cli watchdog timeout: provider=claude-cli model=(?P<model>\S+) '
        r'session=(?P<session>[0-9a-f-]{36})'
    )
    ts_pattern = re.compile(r'"date":"(?P<ts>[^"]+)"')
    kills = []
    seen = set()
    for log_path in sorted(glob.glob(LOG_GLOB)):
        try:
            with open(log_path) as f:
                for line in f:
                    m = pattern.search(line)
                    if not m:
                        continue
                    session_id = m.group("session")
                    model = m.group("model")
                    tm = ts_pattern.search(line)
                    ts_str = tm.group("ts") if tm else None
                    ts = None
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        except ValueError:
                            pass
                    if ts and ts < cutoff:
                        continue
                    key = (session_id, ts_str)
                    if key in seen:
                        continue
                    seen.add(key)
                    kills.append({"session": session_id, "model": model, "ts": ts_str})
        except OSError:
            pass
    return kills


def should_rotate(session_id: str, oversized: set[str], kills: list[dict]) -> str | None:
    """Return reason string if the session should be rotated, else None."""
    killed_ids = {k["session"] for k in kills}
    if session_id in killed_ids and session_id in oversized:
        return "watchdog-killed + oversized"
    if session_id in killed_ids:
        return "watchdog-killed"
    if session_id in oversized:
        return "oversized"
    return None


def rotate_session(path: str, dry_run: bool) -> str:
    dest = path + ".rotated"
    if dry_run:
        return f"WOULD rename {os.path.basename(path)} → {os.path.basename(dest)}"
    os.rename(path, dest)
    return f"ROTATED {os.path.basename(path)} → {os.path.basename(dest)}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually rotate sessions (default: dry-run)")
    ap.add_argument("--selftest", action="store_true", help="smoke test and exit")
    args = ap.parse_args()

    if args.selftest:
        # Verify we can scan the project dir
        assert os.path.isdir(WORKSPACE_PROJECT), f"project dir missing: {WORKSPACE_PROJECT}"
        kills = find_recent_kills(hours=9999)  # any kills ever
        assert isinstance(kills, list)
        oversized = find_oversized_sessions()
        assert isinstance(oversized, list)
        print("SELFTEST PASS")
        sys.exit(0)

    dry_run = not args.apply

    oversized = find_oversized_sessions()
    kills = find_recent_kills()

    oversized_ids = {s["uuid"] for s in oversized}
    killed_ids = {k["session"] for k in kills}
    rotation_candidates = killed_ids | oversized_ids

    print(f"[cli_session_rotate] {datetime.now().isoformat()} dry_run={dry_run}")
    print(f"  Oversized (≥{OVERSIZE_BYTES//1024//1024}MB): {len(oversized)}")
    for s in oversized:
        print(f"    {s['uuid']}  {s['size_mb']:.1f}MB")

    print(f"  Watchdog kills last {KILL_WINDOW_HOURS}h: {len(killed_ids)} distinct sessions")
    for k in kills:
        print(f"    {k['session']}  {k['model']}  {k['ts']}")

    print(f"  Rotation candidates: {len(rotation_candidates)}")
    rotated = 0
    for session_id in sorted(rotation_candidates):
        path = os.path.join(WORKSPACE_PROJECT, f"{session_id}.jsonl")
        if not os.path.exists(path):
            print(f"    {session_id}: JSONL already gone (previously rotated or never landed)")
            continue
        reason = should_rotate(session_id, oversized_ids, kills)
        msg = rotate_session(path, dry_run)
        print(f"    {msg}  [{reason}]")
        rotated += 1

    if dry_run:
        print(f"\n  Pass --apply to execute {rotated} rotation(s).")
    else:
        print(f"\n  Done. {rotated} session(s) rotated.")


if __name__ == "__main__":
    main()
