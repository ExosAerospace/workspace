#!/usr/bin/env python3
"""due_date_inference.py — seed a sensible due_date at task creation.

Every task should be created WITH a date so it can surface as overdue and be sorted,
instead of rotting undated. The assignee can always adjust it; this only provides an
initial date for review.

Inference priority:
  1. Explicit solicitation / submission deadline parsed from the task text
     ("closes June 15", "NOO closes 6/29", "white paper due July 9", ...).
  2. Mission / program anchors (mission-control/data/mission-anchors.json) — e.g. the
     BLK3 March 2027 launch means build/hardware tasks are due launch − 90 days.
  3. Category / priority fallback offset, so nothing is ever created undated.

Anchors live in a config file so launch dates and lead times can be edited without code.
"""
import os, re, json
from datetime import datetime, timezone, timedelta

WORKSPACE = "/Users/exomac/.openclaw/workspace"
ANCHORS_FILE = os.path.join(WORKSPACE, "mission-control/data/mission-anchors.json")

# Deadline keywords, anchored so we grab real deadlines (not version/meeting/program dates).
_KW  = r'(?:due(?:\s+by)?|deadline|closes?|close date|submission deadline|submit(?:\s+by)?|apply by|response due|proposals?\s+due|noo\s+closes?|white\s*paper\s+due)'
_MON = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?'
_NUM = r'\d{1,2}/\d{1,2}(?:/\d{2,4})?'


def parse_deadline(text):
    """Return a datetime for an explicit deadline in the text, or None."""
    if not text:
        return None
    m = (re.search(rf'{_KW}[:\s]+({_MON})', text, re.I)
         or re.search(rf'{_KW}[:\s]+({_NUM})', text, re.I))
    if not m:
        return None
    try:
        from dateutil import parser as dp
        d = dp.parse(m.group(1))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    except Exception:
        return None


def _load_anchors():
    try:
        return json.load(open(ANCHORS_FILE))
    except Exception:
        return []


def _match_anchor(text):
    """Return (due_datetime, name) for the first matching mission anchor, else (None, None)."""
    for a in _load_anchors():
        if not a.get("event_date"):
            continue
        if not re.search(a.get("match", ""), text or "", re.I):
            continue
        req = a.get("requires")
        if req and not re.search(req, text or "", re.I):
            continue
        try:
            ev = datetime.fromisoformat(a["event_date"]).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        return ev - timedelta(days=int(a.get("lead_days", 0))), a.get("name", "mission anchor")
    return None, None


def _default_offset_days(category, priority):
    p = priority or 0
    c = (category or "").lower()
    if p >= 85 or c in ("series a", "revenue"):
        return 7
    if c == "bd":
        return 14
    return 30


def infer_due_date(title="", description="", category=None, priority=None, now=None):
    """Return (iso_due_date, reason). Never None — always seeds a date for assignee review."""
    now = now or datetime.now(timezone.utc)
    text = f"{title or ''}  {description or ''}"

    d = parse_deadline(text)
    if d:
        return d.strftime('%Y-%m-%dT23:59:59Z'), "explicit deadline"

    a_due, a_name = _match_anchor(text)
    if a_due:
        return a_due.strftime('%Y-%m-%dT23:59:59Z'), f"{a_name} (lead time)"

    off = _default_offset_days(category, priority)
    return (now + timedelta(days=off)).strftime('%Y-%m-%dT23:59:59Z'), f"default +{off}d"


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else ""
    print(infer_due_date(t, "", None, None))
