#!/usr/bin/env python3
"""
deliver.py — durable Discord (and any-channel) delivery for Exos crons.

The problem this fixes: 26+ launchd scripts shell out to
`openclaw message send ...` fire-and-forget. When the send flakes
(provider blip, cap, network), they log a WARN and the *already-generated*
content is lost. That is the "team asks / brief written but never lands"
class of loss.

The fix: spool the message to disk BEFORE attempting to send.
  1. Write the payload atomically to outbox/pending/<id>.json.
  2. Try to send (a few quick inline retries).
  3. On success -> move the spool file to outbox/sent/.
  4. On failure -> LEAVE it in outbox/pending/ for delivery-sweeper.py,
     which retries on a schedule and escalates after exhausting attempts.

Content is durable on disk from step 1, so nothing is ever silently dropped.

Usage as a library (preferred — drop-in for a script's post_discord):
    from deliver import deliver
    deliver("some text", target="channel:123...", source="my-cron")

Usage as a CLI:
    python3 deliver.py --target channel:123 --source my-cron -m "text"
    echo "text" | python3 deliver.py --target channel:123 --source my-cron

deliver() NEVER raises — a delivery problem must not crash the caller.
It returns True if the message was accepted by the CLI this call, False if
it was spooled for the sweeper to retry.
"""
import os
import sys
import json
import time
import shutil
import hashlib
import argparse
import subprocess
from datetime import datetime, timezone

WORKSPACE = os.environ.get("EXO_WORKSPACE", "/Users/exomac/.openclaw/workspace")
OUTBOX = os.path.join(WORKSPACE, "outbox")
PENDING = os.path.join(OUTBOX, "pending")
SENT = os.path.join(OUTBOX, "sent")
FAILED = os.path.join(OUTBOX, "failed")
LOG = os.path.join(WORKSPACE, "logs", "deliver.log")

DEFAULT_CHANNEL = "discord"
DEFAULT_TARGET = "channel:1501636814849577050"  # #exomac-system

# launchd has a minimal PATH; resolve openclaw explicitly. EXO_DELIVER_BIN lets
# tests point at a stub to simulate a failing/slow provider without spamming.
OPENCLAW = (
    os.environ.get("EXO_DELIVER_BIN")
    or shutil.which("openclaw")
    or "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"
)

INLINE_ATTEMPTS = 3          # quick tries within a single deliver() call
INLINE_BACKOFF = (2, 6)      # seconds between inline retries
SEND_TIMEOUT = 60            # per-send subprocess timeout


def _ensure_dirs():
    for d in (PENDING, SENT, FAILED, os.path.dirname(LOG)):
        os.makedirs(d, exist_ok=True)


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _log(msg):
    try:
        _ensure_dirs()
        with open(LOG, "a") as f:
            f.write(f"[{_now_iso()}] {msg}\n")
    except Exception:
        pass  # logging must never break delivery


def _spool_id(text, target):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    h = hashlib.sha1(f"{target}|{text}".encode("utf-8")).hexdigest()[:8]
    return f"{ts}-{h}"


def _write_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)  # atomic on same filesystem


def spool(text, target=DEFAULT_TARGET, channel=DEFAULT_CHANNEL, source="unknown"):
    """Write the payload to outbox/pending and return its file path."""
    _ensure_dirs()
    sid = _spool_id(text, target)
    entry = {
        "id": sid,
        "created": _now_iso(),
        "channel": channel,
        "target": target,
        "text": text,
        "source": source,
        "attempts": 0,
        "last_attempt": None,
        "last_error": None,
    }
    path = os.path.join(PENDING, sid + ".json")
    _write_atomic(path, entry)
    return path


def try_send(target, text, channel=DEFAULT_CHANNEL):
    """One send attempt. Returns (ok: bool, err: str|None). Never raises."""
    try:
        out = subprocess.run(
            [OPENCLAW, "message", "send", "--channel", channel,
             "--target", target, "-m", text],
            capture_output=True, text=True, timeout=SEND_TIMEOUT,
        )
        if out.returncode == 0:
            return True, None
        return False, (out.stderr or out.stdout or f"rc={out.returncode}").strip()[:500]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:500]


def _mark_sent(pending_path, entry):
    entry["sent"] = _now_iso()
    dest = os.path.join(SENT, os.path.basename(pending_path))
    try:
        _write_atomic(dest, entry)
        os.remove(pending_path)
    except Exception as e:
        _log(f"WARN could not move to sent: {e}")


def deliver(text, target=DEFAULT_TARGET, channel=DEFAULT_CHANNEL, source="unknown"):
    """
    Durable delivery. Spools first, then tries to send with inline retries.
    Returns True if delivered this call, False if left in the spool for the
    sweeper. Never raises.
    """
    if not text or not str(text).strip():
        return True  # nothing to send
    text = str(text)
    pending_path = spool(text, target=target, channel=channel, source=source)
    try:
        with open(pending_path) as f:
            entry = json.load(f)
    except Exception:
        entry = {"attempts": 0}

    for i in range(INLINE_ATTEMPTS):
        ok, err = try_send(target, text, channel=channel)
        entry["attempts"] = entry.get("attempts", 0) + 1
        entry["last_attempt"] = _now_iso()
        entry["last_error"] = err
        if ok:
            _mark_sent(pending_path, entry)
            if i > 0:
                _log(f"OK after {i+1} inline tries [{source}] -> {target}")
            return True
        # persist attempt count so the sweeper continues the countdown
        try:
            _write_atomic(pending_path, entry)
        except Exception:
            pass
        if i < INLINE_ATTEMPTS - 1:
            time.sleep(INLINE_BACKOFF[min(i, len(INLINE_BACKOFF) - 1)])

    _log(f"SPOOLED (inline failed x{INLINE_ATTEMPTS}) [{source}] -> {target}: {entry.get('last_error')}")
    return False


def _cli():
    ap = argparse.ArgumentParser(description="Durable channel delivery")
    ap.add_argument("-m", "--message", help="message text (or pipe via stdin)")
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--channel", default=DEFAULT_CHANNEL)
    ap.add_argument("--source", default="cli")
    args = ap.parse_args()
    text = args.message if args.message is not None else sys.stdin.read()
    ok = deliver(text, target=args.target, channel=args.channel, source=args.source)
    print("delivered" if ok else "spooled-for-retry")
    sys.exit(0)  # spooled is not a failure; content is safe on disk


if __name__ == "__main__":
    _cli()
