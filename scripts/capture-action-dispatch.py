#!/usr/bin/env python3
"""
capture-action-dispatch.py — deterministic delivery for Jon-gated capture-agent actions.

Scans capture/*.md for READY-ACTION blocks (written by the capture crons) and, for each,
emails Jon the ready-to-send AND opens a Mission Control task via ready_action.deliver().
Idempotent (keyed by `key` + content hash), so it runs on a schedule without spamming.

This takes the model OUT of the delivery path: the crons only author the block; delivery is
code. Enforces feedback_send_or_mc_task_or_dead — no action ever dies as a file path again.

Block format inside any capture/*.md (HTML comment, invisible in rendered markdown):

  <!-- READY-ACTION
  key: noaa-murphy-reply
  task_title: Send reply to Daniel Murphy (NOAA CSL)
  to: daniel.m.murphy@noaa.gov
  cc: Gregory.J.Frost@noaa.gov; victoria.breeze@noaa.gov
  subject: RE: ESA document on atmospheric impacts of reentry
  category: BD
  priority: 85
  body:
  Hello Daniel,
  ...full ready-to-send text...
  END-READY-ACTION -->

Run: python3 scripts/capture-action-dispatch.py [--dry-run]
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("capture-dispatch")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gevent(_GRUN, "error", status="error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import os, re, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ready_action

WS = os.path.expanduser("~/.openclaw/workspace")
# All agent state-tracker locations. A file is only acted on if it contains a READY-ACTION
# block, so scanning extra dirs is safe (opt-in) and future-proofs new agents/trackers.
TRACKER_DIRS = [os.path.join(WS, d) for d in ("capture", "captures", "tasks")]
BLOCK_RE = re.compile(r"<!--\s*READY-ACTION\s*(.*?)\s*END-READY-ACTION\s*-->", re.DOTALL)
FIELDS = ("key", "task_title", "to", "cc", "subject", "category", "priority")


def parse_block(text):
    d, body_lines, in_body = {}, [], False
    for line in text.splitlines():
        if in_body:
            body_lines.append(line); continue
        m = re.match(r"^\s*(\w+)\s*:\s*(.*)$", line)
        if m and m.group(1).lower() in FIELDS + ("body",):
            k = m.group(1).lower()
            if k == "body":
                in_body = True
                if m.group(2).strip():
                    body_lines.append(m.group(2))
            else:
                d[k] = m.group(2).strip()
        elif line.strip():
            # continuation of a non-body field is unusual; ignore stray lines
            pass
    d["body"] = "\n".join(body_lines).strip()
    return d


def main():
    dry = "--dry-run" in sys.argv
    found = dispatched = skipped = 0
    paths = []
    for d in TRACKER_DIRS:
        paths += glob.glob(os.path.join(d, "*.md"))
    for path in sorted(paths):
        try:
            txt = open(path, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for raw in BLOCK_RE.findall(txt):
            b = parse_block(raw)
            if not b.get("key") or not b.get("subject") or not b.get("body"):
                print(f"  ! malformed READY-ACTION in {os.path.basename(path)} (need key/subject/body) — skipped")
                continue
            # Ignore the documentation/template block (placeholder <angle-bracket> fields) and self-tests.
            if "<" in b["key"] or "<" in b["subject"] or b["key"] in ("selftest-key", "example"):
                continue
            found += 1
            label = f"{os.path.basename(path)} :: {b['key']}"
            if dry:
                print(f"  [dry-run] would dispatch: {label} -> task '{b.get('task_title') or b['subject']}'")
                continue
            try:
                res = ready_action.deliver(
                    key=b["key"], subject=b["subject"], body=b["body"],
                    to_line=b.get("to", ""), cc_line=b.get("cc", ""),
                    task_title=b.get("task_title"), category=b.get("category", "BD"),
                    priority=int(b.get("priority", 75) or 75))
                if res.get("skipped"):
                    skipped += 1
                else:
                    dispatched += 1
                    print(f"  dispatched: {label} | emailed={res.get('emailed')} task={res.get('task_id')}")
            except Exception as e:
                print(f"  ! dispatch failed for {label}: {e}")
    print(f"\nREADY-ACTION blocks: {found} found | {dispatched} newly dispatched | {skipped} unchanged")


if __name__ == "__main__":
    main()
