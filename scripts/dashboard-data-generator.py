#!/usr/bin/env python3
"""
dashboard-data-generator.py
Exos Aerospace — Dashboard Data Generator

Parses markdown files to produce JSON data files consumed by the HTML dashboards:
  - exos-mission-control.md  → tasks.json
  - opportunities-tracker.md → opportunities.json
  - SERIES_A_SCORED_CRM.md   → crm.json

Output directory: /Users/exomac/.openclaw/workspace/mission-control/data/

Runs as part of the Wednesday 8 AM CRM refresh cron.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("dashboard-data")
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


import json
import os
import re
import sys
from datetime import datetime, timezone

# ── PATHS ──
WORKSPACE = '/Users/exomac/.openclaw/workspace'
MC_MD     = os.path.join(WORKSPACE, 'exos-mission-control.md')
OPP_MD    = os.path.join(WORKSPACE, 'opportunities-tracker.md')
CRM_MD    = os.path.join(WORKSPACE, 'SERIES_A_SCORED_CRM.md')
DATA_DIR  = os.path.join(WORKSPACE, 'mission-control', 'data')

os.makedirs(DATA_DIR, exist_ok=True)

NOW_ISO = datetime.now(timezone.utc).isoformat()
NOW_DISPLAY = datetime.now().strftime('%Y-%m-%d %H:%M')


# ══════════════════════════════════════════════
# UTILITIES
# ══════════════════════════════════════════════

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def strip_emoji(text):
    """Remove leading emoji + whitespace from a string."""
    return re.sub(r'^[\U00010000-\U0010ffff\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF\u2702-\u27B0\u00A9\u00AE\u203C\u2049\u20E3\u2122\u2139\u2194-\u2199\u21A9-\u21AA\u231A-\u231B\u2328\u23CF\u23E9-\u23F3\u23F8-\u23FA\u24C2\u25AA-\u25AB\u25B6\u25C0\u25FB-\u25FE\u2600-\u2604\u260E\u2611\u2614-\u2615\u2618\u261D\u2620\u2622-\u2623\u2626\u262A\u262E-\u262F\u2638-\u263A\u2640\u2642\u2648-\u2653\u265F-\u2660\u2663\u2665-\u2666\u2668\u267B\u267F\u2692-\u2697\u2699\u269B-\u269C\u26A0-\u26A1\u26AA-\u26AB\u26B0-\u26B1\u26BD-\u26BE\u26C4-\u26C5\u26CE-\u26CF\u26D1\u26D3-\u26D4\u26E9-\u26EA\u26F0-\u26F5\u26F7-\u26FA\u26FD\u2702\u2705\u2708-\u270D\u270F\u2712\u2714\u2716\u271D\u2721\u2728\u2733-\u2734\u2744\u2747\u274C\u274E\u2753-\u2755\u2757\u2763-\u2764\u2795-\u2797\u27A1\u27B0\u27BF\u2934-\u2935\u2B05-\u2B07\u2B1B-\u2B1C\u2B50\u2B55\u3030\u303D\u3297\u3299\uFE0F\u200D]+\s*', '', text).strip()

def write_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'  Written: {path}')


# ══════════════════════════════════════════════
# PAST-DUE PRUNE HELPERS (shared with opportunity_processor.py)
# A "past-due dead" opportunity has a concrete deadline strictly before today
# (UTC) AND a status that is NOT a live/acted pursuit. Such items are dropped.
# ══════════════════════════════════════════════

_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

_RANGE_MARKERS = ('→', '->', ' to ', 'through', 'window')

_LIVE_STATUS_TOKENS = [
    'ACTIVE', 'SUBMITTED', 'MEETING', 'DILIGENCE', 'SCHEDUL', 'EXECUT',
    'IN PROGRESS', 'AWARD', 'SIGNED', 'RESOLVED', 'PITCH DELIVERED',
    'OUTREACH SENT', 'FOLLOW-UP', 'INTAKE',
]


def _is_live_status(status):
    """True if the status indicates a live / already-acted pursuit (KEEP)."""
    s = (status or '').upper()
    return any(tok in s for tok in _LIVE_STATUS_TOKENS)


def _parse_dates(text, today):
    """Return a list of date objects parsed from text (no year => inferred)."""
    found = []

    def infer_year(month, day):
        for yr in (today.year, today.year + 1, today.year - 1):
            try:
                return datetime(yr, month, day).date()
            except ValueError:
                return None
        return None

    def add_no_year(month, day):
        # Use current year; if already >7 days in the past, roll to next year.
        try:
            d = datetime(today.year, month, day).date()
        except ValueError:
            return
        if (today - d).days > 7:
            try:
                d = datetime(today.year + 1, month, day).date()
            except ValueError:
                pass
        found.append(d)

    # ISO YYYY-MM-DD
    for m in re.finditer(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', text):
        try:
            found.append(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date())
        except ValueError:
            pass

    month_alt = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'

    # Month D[, YYYY]  (day must not run straight into another number)
    for m in re.finditer(month_alt + r'\.?\s+(\d{1,2})(?!\s*\d)(?:\s*,?\s*(\d{4}))?', text, re.IGNORECASE):
        mon = _MONTHS[m.group(1)[:3].lower()]
        day = int(m.group(2))
        if m.group(3):
            try:
                found.append(datetime(int(m.group(3)), mon, day).date())
            except ValueError:
                pass
        else:
            add_no_year(mon, day)

    # D Month [YYYY]
    for m in re.finditer(r'\b(\d{1,2})(?!\d)\s+' + month_alt + r'\.?(?:\s+(\d{4}))?', text, re.IGNORECASE):
        day = int(m.group(1))
        mon = _MONTHS[m.group(2)[:3].lower()]
        if m.group(3):
            try:
                found.append(datetime(int(m.group(3)), mon, day).date())
            except ValueError:
                pass
        else:
            add_no_year(mon, day)

    return found


def _deadline_is_past(due_text, today=None):
    """True only if a concrete date can be parsed from due_text and it is < today.

    No concrete date (TBD / rolling / quarter-only like "Q1 2027") => False (keep).
    """
    if today is None:
        today = datetime.now(timezone.utc).date()
    if not due_text:
        return False
    text = str(due_text)
    dates = _parse_dates(text, today)
    if not dates:
        return False

    if len(dates) > 1 and any(mark in text.lower() for mark in [m.lower() for m in _RANGE_MARKERS]):
        chosen = max(dates)
    elif len(dates) > 1:
        future = sorted(d for d in dates if d >= today)
        chosen = future[0] if future else max(dates)
    else:
        chosen = dates[0]

    return chosen < today


def _is_past_due_dead(opp):
    """Drop condition: past-due deadline AND not a live/acted status."""
    return _deadline_is_past(opp.get('due')) and not _is_live_status(opp.get('status', ''))


# ══════════════════════════════════════════════
# 1. PARSE MISSION CONTROL  → tasks.json
# ══════════════════════════════════════════════

# Status emoji → normalized state
EMOJI_STATUS = {
    '🔴': 'Blocked',
    '🟡': 'Ready',
    '🔵': 'In Progress',
    '✅': 'Done',
    '⏸': 'On Hold',
}

# Map section headers to default state
SECTION_STATE = {
    'BLOCKED': 'Blocked',
    'SBIR PHASE III': 'In Progress',
    'READY': 'Ready',
    'IN PROGRESS': 'In Progress',
    'COMPLETED': 'Done',
}

# Priority by section
SECTION_PRIORITY = {
    'SBIR PHASE III': 95,
    'BLOCKED': 60,
    'IN PROGRESS': 70,
    'READY': 50,
    'COMPLETED': 20,
}

def detect_status_from_text(text):
    """Detect status emoji in a block of text; returns (state, emoji_found)."""
    for emoji, state in EMOJI_STATUS.items():
        if emoji in text:
            return state, True
    return None, False

def parse_owner(text):
    """Extract owner from [EXO], [JON], [ASSIGN:name] tags."""
    if '[JON]' in text and '[EXO]' in text:
        return 'Jon+Exo'
    if '[JON]' in text:
        return 'Jon'
    if '[EXO]' in text:
        return 'Exo'
    m = re.search(r'\[ASSIGN:([^\]]+)\]', text)
    if m:
        return m.group(1).strip()
    return None

def parse_due_date(text):
    """Extract a due date from a task block. Returns ISO date string or None."""
    # Patterns: Due: 2026-05-21, Due: May 21, DEADLINE MAY 21, Due: This week, Due: ASAP
    # We only return a real parseable date
    patterns = [
        r'\*\*Due:\*\*\s*(\d{4}-\d{2}-\d{2})',
        r'\*\*Due:\*\*\s*(\w+ \d{1,2},?\s*\d{4})',
        r'\*\*Due:\*\*\s*(\w+ \d{1,2})',
        r'DEADLINE\s+(\w+\s+\d{1,2})',
        r'due\s+(\d{4}-\d{2}-\d{2})',
        r'Submit.*?(\d{4}-\d{2}-\d{2})',
    ]
    current_year = datetime.now().year
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip().rstrip(',')
            # Try various formats
            for fmt in ('%Y-%m-%d', '%B %d %Y', '%b %d %Y', '%B %d', '%b %d'):
                try:
                    d = datetime.strptime(raw, fmt)
                    if d.year == 1900:  # strptime without year
                        d = d.replace(year=current_year)
                    return d.strftime('%Y-%m-%d')
                except ValueError:
                    continue
    return None

def parse_mission_control(content):
    """
    Parse the mission control markdown.
    Strategy: walk line by line. Track current ## section, then collect ### task blocks.
    ## lines set section context. ### lines start a new task block.
    Everything between ### lines is the body of the previous task.
    """
    tasks = []
    task_id_counter = 1

    current_section = None
    current_section_priority = 50

    # Collect (raw_title_line, body_lines) for each task
    pending_title = None
    pending_body_lines = []

    def flush_task(raw_title, body_lines, section, sec_priority):
        nonlocal task_id_counter
        body = '\n'.join(body_lines).strip()
        combined = raw_title + '\n' + body

        # Parse task ID
        id_match = re.match(r'^([A-Z][A-Z0-9]*-\d+[A-Z]?)\s*\|?\s*', raw_title)
        task_id_str = id_match.group(1) if id_match else None

        # Title: strip ID prefix
        title = raw_title
        if id_match:
            title = raw_title[id_match.end():]
        # Strip trailing status indicators like "— ✅ DONE"
        title = re.sub(r'\s*[—–-]\s*(✅|🔴|🟡|🔵|⏸).*$', '', title).strip()
        title = strip_emoji(title).strip('*').strip()
        if not title and raw_title:
            title = raw_title[:80]

        # State: from **Status:** field first
        state = section or 'Blocked'
        status_match = re.search(r'\*\*Status:\*\*\s*([^\n]+)', body)
        if status_match:
            status_text = status_match.group(1)
            detected, found = detect_status_from_text(status_text)
            if found:
                state = detected
            elif any(kw in status_text.upper() for kw in
                     ['COMPLETED', 'DONE', 'CLOSED', 'SUBMITTED', 'SENT', 'RESOLVED', 'UNBLOCKED', 'ACTIVE']):
                if '✅' in status_text:
                    state = 'Done'
            elif 'BLOCKED' in status_text.upper():
                state = 'To Do'  # "Blocked" retired (Jon 9/2) — not-in-progress = To Do

        # Section overrides
        if section == 'Done':
            state = 'Done'

        # If title contains ✅ it's done
        if '✅' in raw_title:
            state = 'Done'

        # Owner
        owner = parse_owner(combined) or 'Exo'

        # Due date
        due_date = parse_due_date(combined)

        # Priority
        priority = sec_priority
        if 'HIGH' in body.upper() and 'PRIORITY' in body.upper():
            priority = min(priority + 15, 100)
        if '⚠️' in body:
            priority = min(priority + 10, 100)
        if 'OVERDUE' in body.upper():
            priority = min(priority + 20, 100)

        # Category from ID prefix
        category = section or 'General'
        if task_id_str:
            cat_map = [
                ('P3-', 'SBIR Phase III'),
                ('P15A-', 'In Progress'),
                ('B-', 'Blocked'),
                ('P-', 'In Progress'),
                ('R-', 'Ready'),
                ('C-', 'Completed'),
            ]
            for prefix, cat in cat_map:
                if task_id_str.startswith(prefix.rstrip('-') + '-') or task_id_str == prefix.rstrip('-'):
                    # Check startswith the letter part
                    letter_part = re.match(r'^([A-Z][A-Z0-9]*)', task_id_str)
                    if letter_part and prefix.startswith(letter_part.group(1)):
                        category = cat
                        break

        tasks.append({
            'id': task_id_str or f'T-{task_id_counter:03d}',
            'title': title,
            'state': state,
            'owner': owner,
            'due_date': due_date,
            'priority': priority,
            'category': category,
            'description': body[:400],
            'source': 'mission-control-md',
        })
        task_id_counter += 1

    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()

        # ## section header (exactly two leading #, not ###)
        if re.match(r'^## [^#]', stripped):
            # Flush any pending task
            if pending_title is not None:
                flush_task(pending_title, pending_body_lines, current_section, current_section_priority)
                pending_title = None
                pending_body_lines = []

            # Determine section type from header text
            header_upper = stripped.upper()
            matched_section = None
            matched_priority = 50
            for key, state in SECTION_STATE.items():
                if key in header_upper:
                    matched_section = state
                    matched_priority = SECTION_PRIORITY.get(key, 50)
                    break
            if matched_section:
                current_section = matched_section
                current_section_priority = matched_priority
            else:
                # Non-task section (CRON SCHEDULE, KEY CONTACTS, HOW THIS WORKS)
                current_section = None
            continue

        # ### task header
        if re.match(r'^### ', stripped) and current_section is not None:
            # Flush previous task
            if pending_title is not None:
                flush_task(pending_title, pending_body_lines, current_section, current_section_priority)
            pending_title = stripped.lstrip('# ').strip()
            pending_body_lines = []
            continue

        # Body line for current task
        if pending_title is not None:
            pending_body_lines.append(line)

    # Flush last task
    if pending_title is not None and current_section is not None:
        flush_task(pending_title, pending_body_lines, current_section, current_section_priority)

    return tasks


# ══════════════════════════════════════════════
# 2. PARSE OPPORTUNITIES  → opportunities.json
# ══════════════════════════════════════════════

def parse_opportunities(content):
    opportunities = []

    # Split by ### headers
    blocks = re.split(r'^(###.+)$', content, flags=re.MULTILINE)

    i = 0
    while i < len(blocks):
        chunk = blocks[i]
        if not chunk.startswith('###'):
            i += 1
            continue

        raw_header = chunk.strip('# ').strip()
        body = blocks[i + 1] if i + 1 < len(blocks) else ''
        i += 2

        # Parse ID and title
        id_match = re.match(r'^([A-Z]+-\d+)\s*\|\s*(.+)', raw_header)
        if not id_match:
            continue
        opp_id = id_match.group(1)
        title = id_match.group(2).strip()

        # Status
        status = 'NEW'
        status_match = re.search(r'\*\*Status:\*\*\s*([^\n]+)', body)
        if status_match:
            raw_status = status_match.group(1).strip()
            # Normalize
            s_upper = raw_status.upper()
            if 'DRAFT' in s_upper:
                status = 'DRAFT'
            elif 'SUBMITTED' in s_upper:
                status = 'SUBMITTED'
            elif 'TRACKING' in s_upper or 'MONITOR' in s_upper:
                status = 'TRACKING'
            elif 'CLOSED' in s_upper or 'COMPLETED' in s_upper:
                status = 'CLOSED'
            elif 'ACTIVE' in s_upper or 'ADVANCING' in s_upper or 'ENGAGED' in s_upper:
                status = 'ACTIVE'
            elif 'MEETING HELD' in s_upper:
                status = 'MEETING HELD'
            elif 'DUE DILIGENCE' in s_upper:
                status = 'DUE DILIGENCE'
            elif 'EVALUATING' in s_upper:
                status = 'EVALUATING'
            elif 'NEW' in s_upper:
                status = 'NEW'
            else:
                # Keep first word up to —
                status = raw_status.split('—')[0].strip()[:30]

        # Type
        opp_type = 'Other'
        type_match = re.search(r'\*\*Type:\*\*\s*([^\n]+)', body)
        if type_match:
            opp_type = type_match.group(1).strip()

        # Value
        value = None
        value_match = re.search(r'\*\*Value:\*\*\s*([^\n]+)', body)
        if value_match:
            value = value_match.group(1).strip()

        # Due date
        due_date = None
        due_match = re.search(r'\*\*Due:\*\*\s*([^\n]+)', body)
        if due_match:
            due_date = due_match.group(1).strip()[:60]

        # Next action
        next_action = None
        next_match = re.search(r'\*\*Next action:\*\*\s*([^\n]+)', body, re.IGNORECASE)
        if next_match:
            next_action = next_match.group(1).strip()[:200]

        # Category: derive from ID prefix
        prefix = opp_id.split('-')[0]
        cat_map = {
            'OPP': 'Opportunity',
            'FUND': 'Fundraising',
            'BD': 'Business Development',
        }
        category = cat_map.get(prefix, 'Other')

        # Priority score: ACTIVE/DUE DILIGENCE > DRAFT > TRACKING > NEW
        priority_map = {
            'ACTIVE': 80, 'DUE DILIGENCE': 85, 'MEETING HELD': 70,
            'DRAFT': 60, 'SUBMITTED': 65, 'TRACKING': 40,
            'EVALUATING': 45, 'NEW': 30, 'CLOSED': 10,
        }
        priority = priority_map.get(status, 40)
        # Deadline boost
        if '⚠️' in body or 'DEADLINE' in body.upper() or 'OVERDUE' in body.upper():
            priority = min(priority + 20, 100)

        # Description: first 300 chars
        description = body.strip()[:300].strip()

        opportunities.append({
            'id': opp_id,
            'title': title,
            'status': status,
            'type': opp_type,
            'category': category,
            'value': value,
            'due': due_date,
            'next_action': next_action,
            'priority': priority,
            'description': description,
        })

    return opportunities


# ══════════════════════════════════════════════
# 2b. PARSE RESEARCH BRIEFS  → research.json
# ══════════════════════════════════════════════

import glob

# Source globs for research/intel briefs the dashboard should surface.
RESEARCH_SOURCES = [
    # (glob pattern, category, source-label)
    (os.path.join(WORKSPACE, 'memory', 'email-digest-*.md'),  'Inbox Digest',  'Daily Email Digest'),
    (os.path.join(WORKSPACE, 'memory', '*-bd-intel.md'),      'BD Intel',      'BD Intelligence'),
    (os.path.join(WORKSPACE, 'memory', '*-research-*.md'),    'Research',      'Research Team'),
    (os.path.join(WORKSPACE, '*_Brief.md'),                   'Strategy Brief','Strategy Brief'),
    (os.path.join(WORKSPACE, '*_Briefing*.md'),              'Strategy Brief','Strategy Brief'),
    (os.path.join(WORKSPACE, '*_BRIEF.md'),                   'Strategy Brief','Strategy Brief'),
]

# Files manually pushed by the cloud research agents / ingest API live here and
# are merged in verbatim (already-structured JSON entries).
RESEARCH_INGEST = os.path.join(DATA_DIR, 'research-ingest.json')

DATE_IN_NAME = re.compile(r'(20\d{2})[-_]?(\d{2})[-_]?(\d{2})')


def _extract_date(filename, content):
    """Best-effort ISO date for a brief: filename first, then first date in body."""
    m = DATE_IN_NAME.search(os.path.basename(filename))
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = DATE_IN_NAME.search(content[:400])
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    # fall back to file mtime
    try:
        return datetime.fromtimestamp(os.path.getmtime(filename)).strftime('%Y-%m-%d')
    except Exception:
        return None


def _summarize(content, category):
    """Pull a short human summary + bullet highlights from a brief body."""
    lines = [l.rstrip() for l in content.splitlines()]
    # Title = first markdown H1, else filename-derived later
    title = None
    highlights = []
    for l in lines:
        s = l.strip()
        if title is None and s.startswith('# '):
            title = s.lstrip('# ').strip()
            continue
        # Collect subject/finding lines as highlights
        if s.startswith('### '):
            highlights.append(s.lstrip('# ').strip())
        elif re.match(r'^[-*]\s+\*\*', s):  # bolded bullet = key finding
            highlights.append(re.sub(r'^[-*]\s+', '', s))
        elif s.startswith('- ') and category in ('BD Intel', 'Research'):
            highlights.append(s[2:].strip())
        if len(highlights) >= 12:
            break
    return title, highlights


def parse_research():
    """Scan known research/intel sources into a unified brief feed."""
    briefs = []
    seen_paths = set()

    for pattern, category, source_label in RESEARCH_SOURCES:
        for path in glob.glob(pattern):
            if path in seen_paths or not os.path.isfile(path):
                continue
            seen_paths.add(path)
            try:
                content = read_file(path)
            except Exception:
                continue
            if not content.strip():
                continue

            date = _extract_date(path, content)
            title, highlights = _summarize(content, category)
            if not title:
                base = os.path.splitext(os.path.basename(path))[0]
                title = base.replace('_', ' ').replace('-', ' ').strip()

            # Count items (### sections) as a signal of brief richness
            item_count = content.count('\n### ') + (1 if content.lstrip().startswith('### ') else 0)

            briefs.append({
                'id': os.path.splitext(os.path.basename(path))[0],
                'title': title,
                'date': date,
                'category': category,
                'source': source_label,
                'item_count': item_count,
                'highlights': highlights[:10],
                'body': content.strip()[:4000],
                'file': os.path.relpath(path, WORKSPACE),
            })

    # Merge any agent/API-ingested briefs (already structured)
    if os.path.isfile(RESEARCH_INGEST):
        try:
            ingested = json.loads(read_file(RESEARCH_INGEST))
            if isinstance(ingested, list):
                briefs.extend(ingested)
        except Exception as e:
            print(f'  WARN: could not read research-ingest.json: {e}')

    # Sort newest-first by date (None last), then title
    briefs.sort(key=lambda b: (b.get('date') or '0000-00-00', b.get('title') or ''), reverse=True)
    return briefs


# ══════════════════════════════════════════════
# 3. PARSE SERIES A CRM  → crm.json
# ══════════════════════════════════════════════

def parse_crm_table_row(row_text, tier, default_stage=None):
    """Parse a single markdown table row into a dict."""
    # Split by | and strip
    cells = [c.strip() for c in row_text.strip('|').split('|')]
    return cells

def normalize_flags(flag_text):
    """Extract flag codes from backtick-wrapped flags."""
    return re.findall(r'`([^`]+)`', flag_text)

def parse_crm(content):
    contacts = []

    # We'll parse each table section separately
    # Sections: TIER 1, TIER 2 (subsections), NEW TARGETS

    # Split by section headers
    sections = re.split(r'^(#{1,3}\s+.+)$', content, flags=re.MULTILINE)

    current_tier = 'Tier 1'
    current_subsection = ''

    i = 0
    while i < len(sections):
        chunk = sections[i]
        if re.match(r'^#{1,3}\s+', chunk):
            header = chunk.strip('# ').strip()
            if 'TIER 1' in header.upper():
                current_tier = 'Tier 1'
                current_subsection = ''
            elif 'TIER 2' in header.upper():
                current_tier = 'Tier 2'
                current_subsection = ''
            elif 'NEW TARGET' in header.upper():
                current_tier = 'New Target'
                current_subsection = ''
            elif 'FLAGGED' in header.upper() or 'NOT A FIT' in header.upper() or 'ARCHIVE' in header.upper():
                current_tier = 'Not a Fit'
                current_subsection = ''
            elif 'SCORING' in header.upper() or 'HOW THIS' in header.upper():
                current_tier = None  # skip metadata sections
            else:
                # Sub-section within Tier 2
                current_subsection = header.strip()
            i += 1
            continue

        if current_tier is None:
            i += 1
            continue

        # Look for markdown table rows in this chunk
        lines = chunk.split('\n')
        for line in lines:
            line = line.strip()
            if not line.startswith('|'):
                continue
            # Skip header/separator rows
            if re.match(r'^\|[-| ]+\|$', line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            if not cells or not cells[0]:
                continue

            # Remove bold markers
            firm_raw = cells[0].replace('**', '').strip()
            if not firm_raw or firm_raw.lower() in ('firm', 'company', '---', 'id', 'item'):
                continue  # header row

            # Determine column layout by tier and context
            # TIER 1 full table: Firm | Category | Stage | Score | Flags | Notes
            # TIER 2 defense table: Firm | Stage | Score | Flags | Notes
            # NEW TARGETS: Firm | Contact | Score | Flags | Source
            # NOT A FIT: Firm | Stage | Score | Flag

            contact = {
                'firm': firm_raw,
                'tier': current_tier,
                'subsection': current_subsection,
            }

            if current_tier == 'Tier 1' and len(cells) >= 6:
                contact['category'] = cells[1].strip()
                contact['stage'] = cells[2].strip()
                score_raw = cells[3].strip().replace('**', '')
                contact['score'] = int(score_raw) if score_raw.isdigit() else 0
                contact['flags'] = normalize_flags(cells[4])
                contact['notes'] = cells[5].strip()[:300]

            elif current_tier == 'Tier 2' and len(cells) >= 5:
                # Firm | Stage | Score | Flags | Notes
                contact['stage'] = cells[1].strip()
                score_raw = cells[2].strip().replace('**', '')
                contact['score'] = int(score_raw) if score_raw.isdigit() else 0
                contact['flags'] = normalize_flags(cells[3])
                contact['notes'] = cells[4].strip()[:300]

            elif current_tier == 'New Target' and len(cells) >= 5:
                # Firm | Contact | Score | Flags | Source
                contact['contact'] = cells[1].strip()
                score_raw = cells[2].strip().replace('**', '')
                contact['score'] = int(score_raw) if score_raw.isdigit() else 0
                contact['flags'] = normalize_flags(cells[3])
                contact['notes'] = cells[4].strip()[:200]

            elif current_tier == 'Not a Fit' and len(cells) >= 4:
                contact['stage'] = cells[1].strip()
                score_raw = cells[2].strip().replace('**', '')
                contact['score'] = int(score_raw) if score_raw.isdigit() else 0
                contact['flags'] = normalize_flags(cells[3]) if len(cells) > 3 else []

            else:
                # Minimal: just firm name was found
                contact['score'] = 0
                contact['flags'] = []

            # HIGH_PRIORITY flag detection from notes
            if 'HIGH_PRIORITY' in contact.get('flags', []):
                contact['is_high_priority'] = True
            else:
                # Also check if score >= 70 in notes or bold firm name implies priority
                contact['is_high_priority'] = contact.get('score', 0) >= 70

            # Detect BOUNCED
            contact['bounced'] = 'BOUNCED' in str(contact.get('notes', ''))

            # Detect STALE
            contact['stale'] = 'STALE' in str(contact.get('notes', ''))

            contacts.append(contact)

        i += 1

    # Deduplicate by firm name (keep highest score)
    seen = {}
    for c in contacts:
        key = c['firm'].lower().strip()
        if key not in seen or c.get('score', 0) > seen[key].get('score', 0):
            seen[key] = c
    return list(seen.values())


# ══════════════════════════════════════════════
# CRM MIRROR
# ══════════════════════════════════════════════

def mirror_opportunities_to_supabase(opportunities):
    """One-way mirror: refresh opportunities into the Supabase `deals` table
    (source=mc-opportunity-mirror) so they show in the unified CRM alongside
    companies/contacts. The .md stays the source of truth; this never writes back.
    Full refresh each run (delete-by-source then insert). Reversible: delete deals
    where source=mc-opportunity-mirror. amount/close_date are left null on purpose —
    the opportunity value/due are narrative text, not clean figures."""
    import urllib.request as _ur, urllib.error as _ue
    try:
        key = json.load(open(os.path.expanduser('~/.openclaw/secrets.json'))).get('supabase_service_role_key', '')
    except Exception:
        key = ''
    if not key or key.startswith('PASTE') or key.startswith('sb_publishable'):
        print('  [mirror] no Supabase service key — skipping CRM deals mirror')
        return
    base = 'https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/'
    def req(path, method='GET', body=None, extra=None):
        h = {'apikey': key, 'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        if extra:
            h.update(extra)
        r = _ur.Request(base + path, data=(json.dumps(body).encode() if body is not None else None),
                        headers=h, method=method)
        with _ur.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read().decode()
    def prio(p):
        try:
            p = int(p)
        except Exception:
            return None
        return 'High' if p >= 70 else ('Medium' if p >= 40 else 'Low')
    rows = []
    for o in opportunities:
        notes = []
        if o.get('value'):       notes.append('Value: ' + str(o['value']))
        if o.get('due'):         notes.append('Due: ' + str(o['due']))
        if o.get('next_action'): notes.append('Next: ' + str(o['next_action']))
        if o.get('description'): notes.append(str(o['description']))
        rows.append({
            'name': (o.get('title') or o.get('id') or 'Untitled')[:300],
            'stage': (o.get('status') or 'DRAFT')[:60],
            'priority': prio(o.get('priority')),
            'source': 'mc-opportunity-mirror',
            'tags': [t for t in ['opp:' + str(o.get('id', '')), o.get('category'), o.get('type')] if t],
            'notes': ('\n'.join(notes))[:4000],
        })
    try:
        req('deals?source=eq.mc-opportunity-mirror', method='DELETE', extra={'Prefer': 'return=minimal'})
        n = 0
        for i in range(0, len(rows), 100):
            req('deals', method='POST', body=rows[i:i + 100], extra={'Prefer': 'return=minimal'})
            n += len(rows[i:i + 100])
        print(f'  [mirror] opportunities mirrored to CRM deals: {n}')
    except _ue.HTTPError as e:
        print('  [mirror] failed:', e.code, e.read().decode()[:200])
    except Exception as e:
        print('  [mirror] failed:', e)


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

def main():
    print(f'\n[{NOW_DISPLAY}] Exos Dashboard Data Generator')
    print('=' * 50)

    # 1. Tasks — decision-ranking enrichment table, now sourced LIVE from Supabase.
    # The legacy MC board items were migrated into Supabase 2026-07-06 (source=mc-board-legacy,
    # tagged mc:<id>), retiring exos-mission-control.md. This table now self-updates: edit a
    # legacy row in Supabase and the change flows here on the next run.
    print('\n[1/3] Loading MC enrichment tasks from Supabase...')
    import urllib.request as _ur
    _SB = 'https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/'
    _KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp'
    mc_tasks = None
    try:
        _req = _ur.Request(
            _SB + 'tasks?select=title,description,state,due_date,owner,tags&source=eq.mc-board-legacy&limit=2000',
            headers={'apikey': _KEY, 'Authorization': 'Bearer ' + _KEY})
        mc_tasks = []
        for r in json.load(_ur.urlopen(_req, timeout=30)):
            mcid = next((str(t).split('mc:', 1)[1] for t in (r.get('tags') or []) if str(t).startswith('mc:')), None)
            if not mcid:
                continue
            mc_tasks.append({'id': mcid, 'title': r.get('title'), 'state': r.get('state'),
                             'due': r.get('due_date'), 'owner': r.get('owner'),
                             'description': r.get('description')})
    except Exception as _e:
        print('  [tasks] Supabase fetch failed — keeping existing tasks.json:', _e)
        mc_tasks = None
    if mc_tasks is not None:
        write_json('tasks.json', {'generated_at': NOW_ISO, 'generated_display': NOW_DISPLAY,
                                  'source': 'Supabase (mc-board-legacy)', 'count': len(mc_tasks),
                                  'tasks': mc_tasks})
        print(f'  MC enrichment tasks from Supabase: {len(mc_tasks)}')
        # Drift self-check: the enrichment set should hold ~100 legacy items. A sharp drop
        # means rows were deleted/retagged in Supabase — surface it, don't shrink silently.
        if len(mc_tasks) < 90:
            print(f'  ⚠️ [drift] MC enrichment dropped to {len(mc_tasks)} (expected ~100) — '
                  f'check Supabase source=mc-board-legacy rows')

    # 2. Opportunities
    print('\n[2/3] Parsing Opportunities Tracker...')
    opp_content = read_file(OPP_MD)
    opportunities = parse_opportunities(opp_content)

    # Prune past-due dead opportunities (concrete deadline in the past + not live/acted)
    pruned = [o for o in opportunities if _is_past_due_dead(o)]
    if pruned:
        opportunities = [o for o in opportunities if not _is_past_due_dead(o)]
        print(f"[prune] dropped {len(pruned)} past-due opportunities: "
              + ", ".join(o.get('title', o.get('id', '?')) for o in pruned))
    else:
        print("[prune] dropped 0 past-due opportunities: ")

    # Apply manual UI edits (opportunity-overrides.json, written by the detail/edit panel) so
    # they survive this markdown->json regeneration instead of being clobbered every run.
    try:
        ov_path = os.path.join(DATA_DIR, 'opportunity-overrides.json')
        if os.path.exists(ov_path):
            with open(ov_path) as _f:
                ov = json.load(_f)
            applied = 0
            for o in opportunities:
                patch = ov.get(o.get('id'))
                if not patch:
                    continue
                for k, v in patch.items():
                    if not k.startswith('_'):
                        o[k] = v
                applied += 1
            if applied:
                print(f'  [overrides] applied manual edits to {applied} opportunities')
    except Exception as _e:
        print('  [overrides] skipped:', _e)

    opps_out = {
        'generated_at': NOW_ISO,
        'generated_display': NOW_DISPLAY,
        'source': 'opportunities-tracker.md',
        'count': len(opportunities),
        'opportunities': opportunities,
    }
    write_json('opportunities.json', opps_out)
    print(f'  Opportunities parsed: {len(opportunities)}')
    mirror_opportunities_to_supabase(opportunities)
    by_cat = {}
    for o in opportunities:
        by_cat[o['category']] = by_cat.get(o['category'], 0) + 1
    for cat, cnt in sorted(by_cat.items()):
        print(f'    {cat}: {cnt}')

    # 3. CRM — now a TIERED VIEW of the Supabase CRM (single source of truth),
    #    not a separate hand-maintained file. Falls back to the md if Supabase is down.
    print('\n[3/3] Building tiered CRM view from Supabase...')
    import urllib.request as _ur
    SB_URL = 'https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/'
    SB_KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp'
    _TIER_ORDER = {'Tier 1': 0, 'Tier 2': 1, 'Tier 3': 2, 'New Target': 3, 'Not a Fit': 9}
    contacts = []
    crm_source = 'Supabase companies (tiered view)'
    try:
        _req = _ur.Request(
            SB_URL + 'companies?select=name,tier,industry,status,description&limit=5000',
            headers={'apikey': SB_KEY, 'Authorization': 'Bearer ' + SB_KEY})
        for c in json.load(_ur.urlopen(_req, timeout=30)):
            tier = c.get('tier')
            if not tier or tier == 'None':
                continue
            contacts.append({
                'firm': c.get('name'),
                'tier': tier,
                'is_high_priority': tier == 'Tier 1',
                'flags': ['HIGH_PRIORITY'] if tier == 'Tier 1' else [],
                'category': c.get('industry') or 'Financial Investor',
                'stage': c.get('status') or '',
                'notes': c.get('description') or '',
            })
        contacts.sort(key=lambda x: _TIER_ORDER.get(x['tier'], 5))
    except Exception as _e:
        print('  [crm] Supabase fetch failed, falling back to md:', _e)
        contacts = parse_crm(read_file(CRM_MD))
        crm_source = 'SERIES_A_SCORED_CRM.md (fallback)'

    # Apply manual worklist edits (crm-overrides.json, written by the Series A detail panel):
    # next_action / last_touched / stage / tier / notes, keyed by firm. Survives regeneration.
    try:
        _ovp = os.path.join(DATA_DIR, 'crm-overrides.json')
        if os.path.exists(_ovp):
            with open(_ovp) as _f:
                _cov = json.load(_f)
            for c in contacts:
                patch = _cov.get(c.get('firm'))
                if not patch:
                    continue
                for k, v in patch.items():
                    if not k.startswith('_'):
                        c[k] = v
                if c.get('tier') == 'Tier 1':
                    c['is_high_priority'] = True
    except Exception as _e:
        print('  [crm] overrides skipped:', _e)

    # Real priority score so the Series A tab ranks top-to-bottom (0-100). Weights: tier base,
    # high-priority flag, penalties for bounced/stale, and follow-up urgency from last_touched
    # (overdue ranks UP so it surfaces; freshly touched ranks down; never-touched gets a nudge).
    from datetime import date as _date
    _today = _date.today()
    _TIER_BASE = {'Tier 1': 60, 'Tier 2': 40, 'Tier 3': 20, 'New Target': 30, 'A': 50, 'Not a Fit': 0}
    def _crm_score(c):
        s = _TIER_BASE.get(c.get('tier'), 10)
        if c.get('is_high_priority'):
            s += 15
        fl = [str(f).upper() for f in (c.get('flags') or [])]
        if 'BOUNCED' in fl or c.get('bounced'):
            s -= 40
        if 'STALE' in fl or c.get('stale'):
            s -= 10
        lt = c.get('last_touched')
        if lt:
            try:
                d = (_today - _date.fromisoformat(str(lt)[:10])).days
                s += 15 if d >= 14 else 8 if d >= 7 else -5
            except Exception:
                pass
        else:
            s += 5  # never touched — needs a first contact
        return max(0, min(100, s))
    for c in contacts:
        c['score'] = _crm_score(c)
        c.setdefault('next_action', '')
        c.setdefault('last_touched', '')
    contacts.sort(key=lambda x: (-x.get('score', 0), _TIER_ORDER.get(x['tier'], 5)))

    high_priority = [c for c in contacts if c.get('is_high_priority')]
    crm_out = {
        'generated_at': NOW_ISO,
        'generated_display': NOW_DISPLAY,
        'source': crm_source,
        'count': len(contacts),
        'high_priority_count': len(high_priority),
        'contacts': contacts,
    }
    write_json('crm.json', crm_out)
    print(f'  Contacts parsed: {len(contacts)}')
    by_tier = {}
    for c in contacts:
        by_tier[c['tier']] = by_tier.get(c['tier'], 0) + 1
    for tier, cnt in sorted(by_tier.items()):
        print(f'    {tier}: {cnt}')
    print(f'  High priority: {len(high_priority)}')

    # 4. Research briefs
    print('\n[4/4] Parsing Research & Intel Briefs...')
    briefs = parse_research()
    research_out = {
        'generated_at': NOW_ISO,
        'generated_display': NOW_DISPLAY,
        'source': 'memory/ digests + intel + strategy briefs + ingest API',
        'count': len(briefs),
        'briefs': briefs,
    }
    write_json('research.json', research_out)
    print(f'  Briefs parsed: {len(briefs)}')
    by_rcat = {}
    for b in briefs:
        by_rcat[b['category']] = by_rcat.get(b['category'], 0) + 1
    for cat, cnt in sorted(by_rcat.items()):
        print(f'    {cat}: {cnt}')

    print(f'\nDone. Data written to {DATA_DIR}')
    print('Files: tasks.json, opportunities.json, crm.json, research.json')
    # Reconcile the pipeline against the Supabase CRM (links + stage-conflict flags).
    try:
        import subprocess
        subprocess.run(['python3', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crm-pipeline-reconcile.py')], check=False)
        subprocess.run(['python3', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validate-trackers.py')], check=False)
    except Exception as e:
        print('[reconcile] skipped:', e)
    print('=' * 50)


if __name__ == '__main__':
    main()
