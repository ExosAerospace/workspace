#!/usr/bin/env python3
"""
delivery-sweeper.py — retries anything stuck in outbox/pending and escalates
what can't be delivered. Pairs with deliver.py.

Runs on launchd every ~3 min. For each spooled message:
  - retry the send once per sweep
  - on success -> move to outbox/sent/
  - after MAX_ATTEMPTS total tries (spanning ~an hour of outage) ->
    move to outbox/failed/ AND fire ONE escalation to the system channel
    (so a genuinely undeliverable item surfaces instead of looping forever)

Fail-quiet: never crash-loops, never raises out of main.
"""
import os
import sys
import json
import glob
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deliver as D  # reuse spool dirs, try_send, logging

MAX_ATTEMPTS = 20          # ~1h of coverage at a 3-min sweep w/ inline tries
SENT_RETENTION_DAYS = 7    # prune sent audit copies older than this
INLINE_GRACE_SECS = D.INLINE_ATTEMPTS * D.SEND_TIMEOUT + sum(D.INLINE_BACKOFF) + 30   # ~218s


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _escalate(entry):
    """Last-ditch: surface an undeliverable item to the system channel.
    Uses deliver() itself so even the escalation is spooled/durable; if the
    escalation target is ALSO down it just re-queues, no loss."""
    src = entry.get("source", "?")
    tgt = entry.get("target", "?")
    err = entry.get("last_error", "?")
    preview = (entry.get("text", "") or "").replace("\n", " ")[:140]
    msg = (f"⚠️ Undeliverable after {entry.get('attempts')} tries — content preserved in "
           f"outbox/failed. source={src} target={tgt} err={err}\n> {preview}")
    # escalate to the system channel (default target), not the dead one
    D.deliver(msg, source="delivery-sweeper-escalation")


def sweep():
    D._ensure_dirs()
    pend = sorted(glob.glob(os.path.join(D.PENDING, "*.json")))
    redelivered = failed = 0
    for path in pend:
        # Race guard (2026-10-04 duplicate Cracks Digest; 36 "could not move to sent" dupes in the log):
        # a pending file this young may still be mid inline-send in deliver() (worst case
        # INLINE_ATTEMPTS x SEND_TIMEOUT + backoff ≈ 190s). Leave it to the live sender; the next
        # sweep picks it up if the inline attempts really failed. deliver() rewrites the file after
        # each failed try, so mtime tracks the live sender's last touch.
        try:
            if time.time() - os.path.getmtime(path) < INLINE_GRACE_SECS:
                continue
        except OSError:
            continue
        entry = _load(path)
        if entry is None:
            # unreadable/corrupt — move aside, don't loop on it
            try:
                os.replace(path, os.path.join(D.FAILED, os.path.basename(path)))
            except Exception:
                pass
            continue
        ok, err = D.try_send(entry["target"], entry["text"],
                             channel=entry.get("channel", D.DEFAULT_CHANNEL))
        entry["attempts"] = entry.get("attempts", 0) + 1
        entry["last_attempt"] = D._now_iso()
        entry["last_error"] = err
        if ok:
            D._mark_sent(path, entry)
            redelivered += 1
            D._log(f"SWEEP redelivered [{entry.get('source')}] after {entry['attempts']} tries")
            continue
        if entry["attempts"] >= MAX_ATTEMPTS:
            dest = os.path.join(D.FAILED, os.path.basename(path))
            try:
                D._write_atomic(dest, entry)
                os.remove(path)
            except Exception:
                pass
            failed += 1
            D._log(f"SWEEP EXHAUSTED [{entry.get('source')}] -> failed/: {err}")
            _escalate(entry)
        else:
            try:
                D._write_atomic(path, entry)
            except Exception:
                pass
    if redelivered or failed:
        D._log(f"SWEEP summary: redelivered={redelivered} exhausted={failed} scanned={len(pend)}")
    _prune_sent()


def _prune_sent():
    import time
    cutoff = time.time() - SENT_RETENTION_DAYS * 86400
    for path in glob.glob(os.path.join(D.SENT, "*.json")):
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except Exception:
            pass


DROP = os.path.join(D.OUTBOX, "drop")
DROP_SETTLE_SECS = 3  # skip files written in the last few secs (avoid partial reads)


def process_drops():
    """Deliver agent-written report drops durably.

    An agentTurn cron with file_write but no shell can't call deliver.py.
    Instead it writes a plain report to outbox/drop/<name>.md whose first line
    may be `TARGET: <target>` (and optionally `SOURCE: <name>`), a blank line,
    then the body. We hand the body to deliver.deliver() (which spools-then-
    sends, so it's durable the instant we call it) and remove the drop file.
    """
    import time
    os.makedirs(DROP, exist_ok=True)
    picked = 0
    for path in sorted(glob.glob(os.path.join(DROP, "*.md")) +
                       glob.glob(os.path.join(DROP, "*.txt"))):
        try:
            if time.time() - os.path.getmtime(path) < DROP_SETTLE_SECS:
                continue  # still being written
            raw = open(path).read()
        except Exception:
            continue
        target, source, body = D.DEFAULT_TARGET, "capture-drop", raw
        # parse optional leading headers up to the first blank line
        head, _, rest = raw.partition("\n\n")
        if any(head.startswith(k) for k in ("TARGET:", "SOURCE:")):
            for line in head.splitlines():
                if line.startswith("TARGET:"):
                    target = line.split(":", 1)[1].strip() or target
                elif line.startswith("SOURCE:"):
                    source = line.split(":", 1)[1].strip() or source
            body = rest
        body = (body or "").strip()
        if not body:
            # nothing deliverable — set aside so we don't spin on it
            try:
                os.replace(path, os.path.join(D.FAILED, os.path.basename(path)))
            except Exception:
                pass
            continue
        D.deliver(body, target=target, source=source)  # durable from here
        try:
            os.remove(path)
        except Exception:
            pass
        picked += 1
        D._log(f"DROP delivered [{source}] -> {target} ({len(body)} chars)")
    return picked


def main():
    try:
        process_drops()  # ingest agent report drops first, then drain the spool
        sweep()
    except Exception as e:
        D._log(f"SWEEP fatal (ignored): {type(e).__name__}: {e}")
    sys.exit(0)


if __name__ == "__main__":
    main()
