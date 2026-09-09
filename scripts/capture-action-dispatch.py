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


# Per-run cap on NEW emails to Jon. A batch of many new READY-ACTION blocks (e.g. the payload
# engine authoring dozens at once) must NOT dump into his inbox in one run — it drips out,
# highest-priority first, so he's never flooded. Unchanged (deduped) blocks are free no-ops and
# don't count against the cap. Deferred blocks simply go on the next cron cycle.
MAX_NEW_PER_RUN = int(os.environ.get("CAD_MAX_PER_RUN", "3"))

# Priority may be an int ("85") or a word ("high"/"medium"/"low") in a READY-ACTION block.
# int("high") used to crash the whole dispatch silently — coerce instead.
def _prio(v, default=75):
    try:
        return int(v)
    except (TypeError, ValueError):
        return {"high": 90, "med": 70, "medium": 70, "normal": 70, "low": 50}.get(
            str(v).strip().lower(), default)


# --- UTD Payload Sales routing (Jon, 2026-08-17): payload outreach follow-ups are the UTD
# capstone students' work queue, NOT reminders to Jon. A payload-sales READY-ACTION block
# becomes a task in the "Payload Sales" category (the student-scoped board) and does NOT email
# Jon. Gov/research outreach (NIH, NOAA/SACSS, etc.) is out of student scope and still flows to
# Jon as a ready-to-send. Narravity/Napier are RESTRICTED — never on the student board (memory
# project_utd_capstone): routed to "Payload — Restricted", tracked, no email, off the queue.
PAYLOAD_CAT = "Payload Sales"
RESTRICTED_CAT = "Payload — Restricted"
UTD_QUEUE_OWNER = "UTD Capstone Queue"
_RESTRICTED_RE = re.compile(r"narravity|napier", re.I)

def _is_payload_sales(b):
    key = (b.get("key") or "").lower()
    cat = (b.get("category") or "").lower()
    return key.startswith("payload-") or cat in ("payload sales", "payload")

def _is_restricted(b):
    blob = " ".join(str(b.get(k, "")) for k in ("key", "subject", "task_title", "body"))
    return bool(_RESTRICTED_RE.search(blob))


# Route a deliverable to the RESPONSIBLE PARTY, not always Jon (Jon directive 2026-09-08).
# Jon's domain is checked FIRST so a BD/gov item that merely contains a word like "machine"
# is not misrouted to engineering. Anything external/gov still lands with the owner for THEM
# to send; nothing auto-fires externally.
_JON_RE = re.compile(r"series a|capital|investor|fundrais|\bBD\b|business develop|partnership|\bMOU\b|"
                     r"\bLOI\b|term sheet|valuation|ROFR|scorpius|\bgov\b|DARPA|AFRL|AFWERX|SpaceWERX|"
                     r"NASA|NOAA|DIU|DIB|OTA\b|SBIR|STTR|TACFI|SEARF|RFI|RFP|proposal|contract|congress|"
                     r"senator|\bboard\b|acquisition|consortium|spaceport|corridor|\bTSC\b|data ?room|\bdeck\b|teaser", re.I)
_ENG_RE = re.compile(r"BLK3 (drawing|engineering|recovery|test)|recovery method|drop test|\bthermal\b|"
                     r"structural|RDRE hardware|propuls|avionics|\bGNC\b|machining|machined|machine controls|"
                     r"\bCNC\b|\bCFC\b|\bdrawing\b", re.I)
_FIELD_RE = re.compile(r"\bcrane\b|\bgenerator\b|\bcompressor\b|forklift|site prep|ground ops", re.I)
_ADMIN_RE = re.compile(r"\bIT-00|device setup|onboarding|new device|backup drive|write-enable|itinerary|"
                       r"\bexpense\b|bamboo|\bHR\b|wellbeing|\bsurvey\b|\bbadge\b|wi-?fi|\bpassword\b|SMTP|"
                       r"registration|calendar|schedul", re.I)

def _route_owner(b):
    blob = " ".join(str(b.get(k, "")) for k in ("key", "subject", "task_title", "body"))
    if _JON_RE.search(blob):   return "Jon"              # CEO/BD/capital/gov (gov sends still via Jon)
    if _ENG_RE.search(blob):   return "Phil Eaton"
    if _FIELD_RE.search(blob): return "Steve Norsworthy"
    if _ADMIN_RE.search(blob): return "Lizi Quinn"
    return "Jon"                                          # unsure -> Jon (safe default)


def _log_capture_review(b):
    """Surface a Jon-routed capture to the monthly review digest instead of his task board.
    Reviewed at the weekly meeting; anything worth doing gets promoted via an explicit @exo command."""
    try:
        from datetime import datetime
        month = datetime.now().strftime("%Y-%m")
        path = os.path.join(WS, "memory", f"capture-review-{month}.md")
        new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if new:
                f.write(f"# Capture review — {month}\n\n"
                        "Inbound-derived captures that routed to Jon. NOT tasks — review here; "
                        "promote to a task only via an explicit @exo instruction to exosmc.\n\n")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            title = b.get("task_title") or b.get("subject") or b.get("key")
            f.write(f"- [{ts}] (p{_prio(b.get('priority', 75))}) {title}  —  key:`{b.get('key')}`\n")
    except Exception as e:
        print(f"  ! capture-review log failed: {e}")


def main():
    dry = "--dry-run" in sys.argv
    found = dispatched = skipped = 0
    paths = []
    for d in TRACKER_DIRS:
        paths += glob.glob(os.path.join(d, "*.md"))
    # Pass 1: collect all valid, non-template blocks.
    cands = []
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
            if "<" in b["key"] or "<" in b["subject"] or b["key"] in ("selftest-key", "example"):
                continue
            found += 1
            cands.append((os.path.basename(path), b))
    # Highest priority first so the cap always spends the budget on the most important sends.
    cands.sort(key=lambda pb: -_prio(pb[1].get("priority", 75)))

    deferred = 0
    for fname, b in cands:
        label = f"{fname} :: {b['key']}"
        # Routing decision: payload outreach → UTD student board (no Jon email); restricted
        # (Narravity/Napier) → tracked off-board, no email; everything else → Jon ready-to-send.
        payload = _is_payload_sales(b)
        restricted = payload and _is_restricted(b)
        if restricted:
            route, category, owner, do_email, do_mc = "RESTRICTED", RESTRICTED_CAT, "Jon+Exo", False, True
        elif payload:
            route, category, owner, do_email, do_mc = "UTD-QUEUE", PAYLOAD_CAT, UTD_QUEUE_OWNER, False, True
        else:
            owner = _route_owner(b)
            if owner == "Jon":
                # Jon's rule (2026-09-09): inbound/forwarded email must NOT spawn a task on his
                # board or an email nag. Only an explicit @exo instruction to exosmc creates a Jon
                # task. A capture that routes to Jon is surfaced to the capture-review digest for
                # later review — never auto-tasked, never auto-emailed.
                route, category, owner, do_email, do_mc = "JON-REVIEW", b.get("category", "BD"), "Jon", False, False
            else:
                route, category, do_email, do_mc = "OWNER", b.get("category", "BD"), True, True
        if dry:
            print(f"  [dry-run] [{route}] {label} -> cat={category!r} owner={owner!r} email={do_email}")
            continue
        # The per-run cap protects Jon's INBOX only. Board-only routes (payload/restricted) never
        # email him, so they are not gated by it — the student queue fills fully each run.
        if do_email and dispatched >= MAX_NEW_PER_RUN:
            deferred += 1
            continue
        try:
            res = ready_action.deliver(
                key=b["key"], subject=b["subject"], body=b["body"],
                to_line=b.get("to", ""), cc_line=b.get("cc", ""),
                task_title=b.get("task_title"), category=category,
                priority=_prio(b.get("priority", 75)),
                do_email=do_email, do_mc=do_mc, owner=owner)
            if res.get("skipped"):
                skipped += 1
            else:
                if do_email:
                    dispatched += 1
                if route == "JON-REVIEW":
                    _log_capture_review(b)
                print(f"  dispatched [{route}]: {label} | emailed={res.get('emailed')} task={res.get('task_id')}")
        except Exception as e:
            print(f"  ! dispatch failed for {label}: {e}")
    tail = f" | {deferred} deferred (cap {MAX_NEW_PER_RUN}/run)" if deferred else ""
    print(f"\nREADY-ACTION blocks: {found} found | {dispatched} emailed-to-Jon | {skipped} unchanged{tail}")


if __name__ == "__main__":
    main()
