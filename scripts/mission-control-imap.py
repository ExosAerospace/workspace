# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("email-router")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gt = _gis_transient(v); _gevent(_GRUN, "transient_skip" if _gt else "error", status="transient" if _gt else "error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import imaplib
import email
import subprocess
import time
import json
import os
import re
import socket
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

# Prevent IMAP calls from hanging indefinitely
socket.setdefaulttimeout(30)

IMAP_HOST = '127.0.0.1'
IMAP_PORT = 1143
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']

SUPABASE_URL = 'https://pcrgpuoljylqcumijvnw.supabase.co'
SUPABASE_KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp'

def decode_mime_header(raw):
    """Decode MIME-encoded email header (e.g. =?utf-8?q?...?=)."""
    from email.header import decode_header
    parts = decode_header(raw or '')
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or 'utf-8', errors='ignore'))
        else:
            decoded.append(part)
    return ' '.join(decoded)

def extract_email_address(sender):
    """Extract bare email from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1).lower() if match else sender.strip().lower()

def update_crm_contact(sender_email, subject, body=None):
    """Find matching contact in Supabase and update last_contacted."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/contacts?email=ilike.{urllib.parse.quote(sender_email)}&limit=1"
        req = urllib.request.Request(url, headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
        })
        resp = urllib.request.urlopen(req)
        contacts = json.loads(resp.read().decode())

        if not contacts:
            print(f"  CRM: No contact found for {sender_email}")
            return False

        contact = contacts[0]
        now = datetime.now(timezone.utc).isoformat()
        note_update = f"[{datetime.now().strftime('%Y-%m-%d')}] Email: {subject[:100]}"
        existing_notes = contact.get('notes') or ''
        # Prepend new note, keep last 2000 chars
        updated_notes = (note_update + ' | ' + existing_notes)[:2000] if existing_notes else note_update

        update = {
            'last_contacted': now,
            'notes': updated_notes,
        }

        patch_url = f"{SUPABASE_URL}/rest/v1/contacts?id=eq.{contact['id']}"
        patch_req = urllib.request.Request(patch_url, data=json.dumps(update).encode(), headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal',
        }, method='PATCH')
        urllib.request.urlopen(patch_req)
        print(f"  CRM: Updated '{contact.get('name')}' at {contact.get('organization')} — last_contacted = now")

        # Log activity in activities table
        activity = {
            'type': 'email',
            'subject': subject[:200],
            'body': body[:500] if body else None,
            'contact_id': contact['id'],
            'owner': 'Email Bridge',
            'status': 'completed',
        }
        act_req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/activities",
            data=json.dumps(activity).encode(),
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal',
            },
            method='POST'
        )
        urllib.request.urlopen(act_req)
        print(f"  CRM: Logged email activity for '{contact.get('name')}'")
        return True
    except Exception as e:
        print(f"  CRM update error: {e}")
        return False

def import_spreadsheet(filepath, sender_email):
    """Import a CRM spreadsheet attachment into Supabase, upserting by email or name+company."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(filepath)
        ws = wb.active
        headers = [str(cell.value or '').strip().lower() for cell in ws[1]]
        print(f"  Spreadsheet: {ws.max_row - 1} rows, headers: {headers}")

        # Map common header names to our fields
        def find_col(names):
            for n in names:
                if n in headers:
                    return headers.index(n)
            return None

        col_name = find_col(['name', 'contact', 'contact name'])
        col_company = find_col(['company', 'organization', 'org'])
        col_email = find_col(['email', 'email address', 'e-mail'])
        col_title = find_col(['title', 'role', 'job title'])
        col_phone = find_col(['phone', 'phone number', 'tel'])
        col_stage = find_col(['stage', 'status', 'deal stage'])
        col_tier = find_col(['tier', 'priority'])
        col_notes = find_col(['notes', 'comments', 'note'])
        col_linkedin = find_col(['linkedin', 'linkedin url'])
        col_category = find_col(['category', 'type'])
        col_next = find_col(['next action', 'next_action', 'follow up', 'follow up sent'])
        col_score = find_col(['priority score', 'priority_score', 'score'])

        imported = 0
        updated = 0
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            row = list(row)
            name = str(row[col_name] or '').strip() if col_name is not None else ''
            company = str(row[col_company] or '').strip() if col_company is not None else ''
            row_email = str(row[col_email] or '').strip() if col_email is not None else ''

            if not name and not row_email:
                skipped += 1
                continue

            # Try to find existing contact by email first, then name+org
            existing = None
            if row_email:
                url = f"{SUPABASE_URL}/rest/v1/contacts?email=ilike.{urllib.parse.quote(row_email)}&limit=1"
                req = urllib.request.Request(url, headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'})
                resp = urllib.request.urlopen(req)
                results = json.loads(resp.read().decode())
                if results:
                    existing = results[0]

            if not existing and name:
                url = f"{SUPABASE_URL}/rest/v1/contacts?name=ilike.{urllib.parse.quote(name)}&organization=ilike.{urllib.parse.quote(company)}&limit=1"
                req = urllib.request.Request(url, headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'})
                resp = urllib.request.urlopen(req)
                results = json.loads(resp.read().decode())
                if results:
                    existing = results[0]

            # Build update/insert payload
            fields = {}
            if name: fields['name'] = name
            if company: fields['organization'] = company
            if row_email: fields['email'] = row_email
            if col_title is not None and row[col_title]: fields['title'] = str(row[col_title]).strip()
            if col_phone is not None and row[col_phone]: fields['phone'] = str(row[col_phone]).strip()
            if col_stage is not None and row[col_stage]: fields['stage'] = str(row[col_stage]).strip()
            if col_tier is not None and row[col_tier]: fields['tier'] = str(row[col_tier]).strip()
            if col_notes is not None and row[col_notes]: fields['notes'] = str(row[col_notes]).strip()
            if col_linkedin is not None and row[col_linkedin]: fields['linkedin'] = str(row[col_linkedin]).strip()
            if col_category is not None and row[col_category]: fields['type'] = str(row[col_category]).strip()
            if col_next is not None and row[col_next]:
                val = row[col_next]
                if hasattr(val, 'strftime'):
                    fields['next_followup'] = val.strftime('%Y-%m-%dT00:00:00Z')
                else:
                    fields['next_action'] = str(val).strip()
            if col_score is not None and row[col_score]:
                try: fields['priority_score'] = int(float(str(row[col_score])))
                except: pass

            if existing:
                # Update existing contact
                patch_url = f"{SUPABASE_URL}/rest/v1/contacts?id=eq.{existing['id']}"
                patch_req = urllib.request.Request(patch_url, data=json.dumps(fields).encode(), headers={
                    'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json', 'Prefer': 'return=minimal',
                }, method='PATCH')
                urllib.request.urlopen(patch_req)
                updated += 1
            else:
                # Insert new contact
                fields['status'] = 'Active'
                fields['source'] = f'Spreadsheet import from {sender_email}'
                post_req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/contacts", data=json.dumps(fields).encode(), headers={
                    'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json', 'Prefer': 'return=minimal',
                }, method='POST')
                urllib.request.urlopen(post_req)
                imported += 1

        print(f"  Spreadsheet import: {imported} new, {updated} updated, {skipped} skipped")

        # Log import as activity
        activity = {
            'type': 'note',
            'subject': f'CRM spreadsheet import ({imported} new, {updated} updated)',
            'body': f'Imported from {sender_email}. File had {ws.max_row - 1} rows.',
            'owner': sender_email,
            'status': 'completed',
        }
        act_req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/activities", data=json.dumps(activity).encode(), headers={
            'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json', 'Prefer': 'return=minimal',
        }, method='POST')
        urllib.request.urlopen(act_req)
        return True
    except Exception as e:
        print(f"  Spreadsheet import error: {e}")
        import traceback; traceback.print_exc()
        return False


def process_email(subject, sender, body, attachments=None):
    print(f"Processing email from {sender} regarding '{subject}'...")

    sender_email = extract_email_address(sender)

    # Check for spreadsheet attachments — auto-import CRM data
    if attachments:
        for filepath, filename in attachments:
            if filename.lower().endswith(('.xlsx', '.xls', '.csv')):
                print(f"  Found spreadsheet attachment: {filename}")
                import_spreadsheet(filepath, sender_email)

    # Update CRM contact record
    update_crm_contact(sender_email, subject, body)

    # Log to daily email digest file for Exo to review
    today = datetime.now().strftime('%Y-%m-%d')
    digest_path = f'/Users/exomac/.openclaw/workspace/memory/email-digest-{today}.md'

    sender_email = extract_email_address(sender)
    decoded_subject = decode_mime_header(subject) if '=?' in subject else subject

    try:
        # Append to daily digest
        entry = f"\n### {datetime.now().strftime('%H:%M')} | {decoded_subject}\n"
        entry += f"**From:** {sender}\n"
        if body:
            # Extract first meaningful line (skip empty lines and signatures)
            preview = body.strip()[:300].split('\n')[0].strip()
            if preview:
                entry += f"**Preview:** {preview}\n"
        entry += "\n"

        with open(digest_path, 'a') as f:
            if os.path.getsize(digest_path) == 0 if os.path.exists(digest_path) else True:
                f.write(f"# Email Digest — {today}\n\n")
            f.write(entry)

        print(f"  Logged to digest: {digest_path}")
    except Exception as e:
        print(f"  Digest log error: {e}")

def extract_recipients(msg):
    """Extract all To/CC email addresses."""
    addrs = []
    for header in ['to', 'cc']:
        raw = msg.get(header, '')
        if raw:
            for part in raw.split(','):
                addr = extract_email_address(part)
                if addr:
                    addrs.append(addr)
    return addrs

_UPLOADS_DIR = os.path.expanduser('~/.openclaw/workspace/mission-control/uploads')
_UPLOADS_META = os.path.join(_UPLOADS_DIR, '_meta.json')
_ALLOWED_ATTACH = {'.pdf', '.docx', '.xlsx', '.pptx', '.png', '.jpg', '.jpeg', '.csv', '.zip'}

def extract_text_body(msg):
    """Return the text/plain body of an email.message.Message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and 'attachment' not in str(part.get('Content-Disposition', '')):
                try:
                    return (part.get_payload(decode=True) or b'').decode('utf-8', errors='ignore')
                except Exception:
                    pass
        return ""
    try:
        return (msg.get_payload(decode=True) or b'').decode('utf-8', errors='ignore')
    except Exception:
        return ""

def sanitize_body(text):
    """Clean an email body before it is stored as a task description.

    Some multipart messages slip through with raw MIME residue (boundary lines,
    Content-* headers, quoted-printable soft breaks), which produced garbled task
    descriptions like '--<hex> Content-Transfer-Encoding: quoted-printable ...'.
    Strip that residue and decode quoted-printable only when the body is actually raw QP.
    """
    if not text:
        return None
    is_raw_qp = bool(re.search(r'Content-Transfer-Encoding:\s*quoted-printable', text, re.I))
    kept = []
    for ln in text.splitlines():
        s = ln.strip()
        if re.match(r'^--[-_A-Za-z0-9=]{8,}$', s):               # MIME boundary line (open or close)
            continue
        if re.match(r'^(?:Content-(?:Type|Transfer-Encoding|Disposition|ID)|MIME-Version)\s*:', s, re.I):
            continue
        kept.append(ln)
    out = "\n".join(kept)
    if is_raw_qp:
        try:
            import quopri
            out = quopri.decodestring(out.encode('utf-8', 'ignore')).decode('utf-8', 'ignore')
        except Exception:
            pass
    out = re.sub(r'[ \t]+\n', '\n', out)
    out = re.sub(r'\n{3,}', '\n\n', out).strip()
    return (out[:500] or None) if out else None

def save_email_attachments_to_task(msg, task_id):
    """Save an email's file attachments to mission-control/uploads/ and link them to the task's
    Documents (same store the MC upload UI uses). Closes the gap where email-created tasks showed
    'No documents attached' even though the email carried the deck/package."""
    if not msg or not msg.is_multipart():
        return 0
    try:
        meta = json.load(open(_UPLOADS_META))
    except Exception:
        meta = []
    count = 0
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        fn = decode_mime_header(fn)
        ext = os.path.splitext(fn)[1].lower()
        if ext not in _ALLOWED_ATTACH:
            continue
        try:
            data = part.get_payload(decode=True)
        except Exception:
            data = None
        if not data or len(data) > 25 * 1024 * 1024:   # 25 MB cap (matches the UI)
            continue
        ts = int(time.time() * 1000)
        safe = re.sub(r'[^a-zA-Z0-9._-]', '_', fn)
        stored = f"{ts}_{safe}"
        try:
            with open(os.path.join(_UPLOADS_DIR, stored), 'wb') as f:
                f.write(data)
        except Exception as e:
            print(f"  Attachment save failed ({fn}): {e}")
            continue
        meta.append({
            "id": os.urandom(8).hex(),
            "filename": fn, "stored_name": stored, "size": len(data),
            "extension": ext, "task_id": str(task_id), "project_id": None, "decision_id": None,
            "uploaded_by": "Exo (email capture)",
            "uploaded_at": datetime.now(timezone.utc).isoformat(), "current": True,
        })
        count += 1
    if count:
        try:
            json.dump(meta, open(_UPLOADS_META, 'w'), indent=2)
            print(f"  Linked {count} attachment(s) to task {task_id}")
        except Exception as e:
            print(f"  Attachment meta write failed: {e}")
    return count

_DISPLAY_NAME_CACHE = None

def resolve_display_name(team_email):
    """Map a team email to its canonical display name from the MC roster
    (mission-control/users.json — the single source of truth), so auto-created
    tasks read 'Phil Eaton', not the email-prefix 'Peaton'. Falls back to the
    title-cased prefix only for addresses not on the roster."""
    global _DISPLAY_NAME_CACHE
    email_l = (team_email or '').strip().lower()
    if _DISPLAY_NAME_CACHE is None:
        _DISPLAY_NAME_CACHE = {}
        try:
            _p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '..', 'mission-control', 'users.json')
            with open(_p) as _f:
                _u = json.load(_f)
            _users = _u if isinstance(_u, list) else _u.get('users', [])
            for _x in _users:
                _e = (_x.get('email') or '').strip().lower()
                _n = (_x.get('name') or '').strip()
                if _e and _n:
                    _DISPLAY_NAME_CACHE[_e] = _n
        except Exception as _e:
            print(f"  (display-name roster unavailable, using prefix fallback: {_e})")
    if email_l in _DISPLAY_NAME_CACHE:
        return _DISPLAY_NAME_CACHE[email_l]
    return email_l.split('@')[0].replace('.', ' ').title()

def is_task_worthy(team_email, subject, body):
    """Gate the intake so we stop auto-creating a task for EVERY sent email (the root of the
    +300/week task inflation). A sent email becomes a task only when it is a genuine delegation.
    Skip: self-copies to Jon (captures, already digested), automated/newsletter/notification noise,
    and bare FYI/forwards with no actual ask. Keep anything with a real request, deadline, or question."""
    blob = ((subject or '') + ' ' + (body or '')[:1000]).lower().strip()
    # 1) self-copy to Jon = a capture/forward-to-self, not a delegated task
    if team_email == 'jquinn@exosaero.com':
        return False
    # 2) automated / non-actionable noise
    NOISE = ('unsubscribe', 'newsletter', 'no-reply', 'noreply', 'out of office', 'automatic reply',
             'auto-reply', 'read receipt', 'delivery status', 'undeliverable', 'mailer-daemon',
             '[mission control]', 'calendar invite', 'accepted:', 'declined:', 'do not reply')
    if any(k in blob for k in NOISE):
        return False
    # 3) require SOME actionable signal — a request, deadline, or question; otherwise it's an FYI
    ASK = ('please', 'can you', 'could you', 'need ', 'needs ', 'review', 'send ', 'draft', 'prepare',
           'complete', 'provide', 'follow up', 'follow-up', 'action', 'due', 'deadline', 'by ',
           'let me know', 'confirm', 'update', 'assign', 'handle', 'get me', 'pull ', 'sign', '?')
    return any(k in blob for k in ASK)


def process_outbound_to_team(msg, subject, body):
    """When we send email to @exosaero.com, auto-create/assign a task."""
    recipients = extract_recipients(msg)
    team_recipients = [r for r in recipients if r.endswith('@exosaero.com')]
    if not team_recipients:
        return

    # (a) Exo's OWN automated status replies (subject "…, Exo update") are outbound from Exo to the
    # requester, not new delegations. They were looping back through this intake and spawning
    # duplicate reply-thread cards ("Re: X, Exo update"). Never turn them into tasks.
    if re.search(r',?\s*exo\s+update\s*$', (subject or ''), flags=re.I):
        print("  Skipped: Exo's own automated reply (…Exo update) — not a task")
        return

    # (a2) Exo's OWN automated digests / newsletters (weekly report, previews, briefings) are
    # broadcasts, not delegations. They were looping back through this Sent-folder intake and
    # spawning a redundant "Your Mission Control weekly" card on top of tasks people already have
    # (Kyle flagged the flood). Never turn Exo's own digests into tasks.
    _subj_l = (subject or '').strip().lower()
    DIGEST_SUBJECTS = ('your mission control weekly', 'mission control weekly', 'weekly mc report',
                       'your mission control daily', 'mission control daily', "today's brief", 'daily brief')
    if _subj_l.startswith('[preview]') or any(s in _subj_l for s in DIGEST_SUBJECTS):
        print("  Skipped: Exo automated digest/newsletter — not a task")
        return

    # (a3) Anything Exo composed and sent on Jon's behalf carries a "(via Exo)" sign-off. That is Exo
    # acting on an already-tracked item, not a fresh human delegation, so it must not spawn its own card.
    if re.search(r'\bvia exo\b', (body or ''), flags=re.I):
        print("  Skipped: Exo-authored outbound (…via Exo) — not a task")
        return

    for team_email in team_recipients:
        team_name = resolve_display_name(team_email)
        print(f"  Outbound to team: {team_email} ({team_name})")

        # INTAKE GATE — only genuine delegations become tasks (kills the every-email-is-a-task flood)
        if not is_task_worthy(team_email, subject, body):
            print(f"  Skipped (self-copy / noise / FYI, not task-worthy): {team_email}")
            continue

        # Create a task assigned to this team member
        combined = (subject + ' ' + (body or '')).lower()

        # Detect category
        if any(kw in combined for kw in ['series a', 'investor', 'fundrais', 'raise', 'term sheet', 'deck', 'pitch']):
            category = 'Series A'
        elif any(kw in combined for kw in ['revenue', 'contract', 'purchase', 'customer', 'deal', 'proposal', 'quote', 'rfi', 'rfp', 'capability statement']):
            category = 'Revenue'
        else:
            category = 'BD'

        # Base priority
        priority = 70
        if any(kw in combined for kw in ['urgent', 'asap', 'critical', 'immediate']):
            priority = 90
        elif category in ('Series A', 'Revenue'):
            priority = 85

        # Seed a due_date at creation so nothing is created undated (root cause of the 2026-07
        # "missed submissions" cleanup). Priority: explicit solicitation deadline > mission/program
        # anchor (e.g. BLK3 build tasks due launch − 90d) > category/priority default. The assignee
        # can adjust; this just provides an initial date for review.
        due_date = None
        _due_reason = None
        try:
            import sys as _sys
            _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from due_date_inference import infer_due_date
            due_date, _due_reason = infer_due_date(subject, body, category, priority)
        except Exception as _e:
            # Fallback: explicit-deadline-only parse if the module is unavailable
            _KW=r'(?:due(?:\s+by)?|deadline|closes?|submission deadline|submit(?:\s+by)?|noo\s+closes?)'
            _MON=r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?'
            _m=re.search(rf'{_KW}[:\s]+({_MON})', combined, re.I)
            if _m:
                try:
                    from dateutil import parser as dateparser
                    due_date = dateparser.parse(_m.group(1)).strftime('%Y-%m-%dT23:59:59Z')
                except Exception:
                    pass

        task = {
            'title': subject[:200] if subject else 'Task from email',
            'description': sanitize_body(body),
            'category': category,
            'priority': priority,
            'due_date': due_date,
            # Owner follows the assignee (the person the email was sent to), not a blanket
            # default to Jon — that default was silently piling team deliverables onto Jon's board.
            'owner': team_name or 'Jon',
            'assigned_to': team_name,
            'assigned_email': team_email,
            'assigned_at': datetime.now(timezone.utc).isoformat(),
            'source': f'Email to {team_email}',
            'state': 'To Do',
        }

        # Dedupe guard: skip if an equivalent OPEN task already exists.
        # Exact-title matching was too weak — variant subjects for the SAME deliverable
        # (e.g. "[READY TO SEND] X", "[FORWARD 5/5 — ONE PAGE] X", "[FORWARD 5/5 — bonus] X")
        # each slipped through as separate cards (the Brent Money 6/2 dupes). Now we compare on a
        # NORMALIZED title (leading [..] tags stripped, case/whitespace folded) plus a conservative
        # fuzzy match, scoped to the same assignee (or unassigned) and to OPEN tasks only.
        import difflib, urllib.parse as _up
        def _norm_title(t):
            # Peel interleaved reply/forward prefixes, [..] tags, and the notifier prefix so
            # thread variants of the SAME deliverable normalize to one canonical string.
            # ("Re: Fw: [Mission Control] Task assigned to you: PD Aerospace ..., Exo update"
            #  -> "pd aerospace ..."). Without this, every reply/forward spawned a new task.
            t = t or ''
            prev = None
            while prev != t:
                prev = t
                t = re.sub(r'^\s*(?:re|fw|fwd)\s*:\s*', '', t, flags=re.I)          # Re:/Fw:/Fwd:
                t = re.sub(r'^\s*\[[^\]]*\]\s*', '', t)                             # one leading [..] tag
                t = re.sub(r'^\s*task assigned to you\s*:?\s*', '', t, flags=re.I)  # notifier prefix
            t = re.sub(r'(?:\s*,?\s*exo update)+\s*$', '', t, flags=re.I)           # trailing thread suffix
            t = re.sub(r'\s+', ' ', t).strip().lower().strip(' .:-—')
            return t
        norm_new = _norm_title(task['title'])
        # (b) A task closed within this window still blocks a same-owner+title re-ingest — a thread
        # re-processed days later is a dupe loop, not genuinely new work.
        _recent_cut = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
        already_exists = False
        try:
            _q = (f"{SUPABASE_URL}/rest/v1/tasks?select=id,title,state,completed_at,created_at"
                  f"&or=(assigned_email.eq.{_up.quote(team_email)},assigned_email.is.null)&limit=800")
            _chk = urllib.request.Request(_q, headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'})
            for _e in json.load(urllib.request.urlopen(_chk)):
                if _e.get('state') == 'Done' or _e.get('completed_at'):
                    _c = (_e.get('completed_at') or _e.get('created_at') or '')[:10]
                    if _c < _recent_cut:
                        continue                                    # old closed task: doesn't block new work
                    # else: recently closed -> fall through and let it block a re-ingest dupe
                _ne = _norm_title(_e.get('title'))
                if _ne and norm_new and (_ne == norm_new or difflib.SequenceMatcher(None, _ne, norm_new).ratio() >= 0.90):
                    already_exists = True
                    print(f"  Dedupe: '{task['title'][:40]}' ~ existing #{_e.get('id')} '{(_e.get('title') or '')[:40]}'")
                    break
        except Exception:
            already_exists = False

        if already_exists:
            print(f"  Skipped duplicate task (already exists): {task['title'][:50]}")
        else:
            try:
                req = urllib.request.Request(
                    f"{SUPABASE_URL}/rest/v1/tasks",
                    data=json.dumps(task).encode(),
                    headers={
                        'apikey': SUPABASE_KEY,
                        'Authorization': f'Bearer {SUPABASE_KEY}',
                        'Content-Type': 'application/json',
                        'Prefer': 'return=representation',
                    },
                    method='POST'
                )
                created = json.load(urllib.request.urlopen(req))
                new_id = (created[0].get('id') if isinstance(created, list) and created
                          else created.get('id') if isinstance(created, dict) else None)
                print(f"  Task created (#{new_id}) and assigned to {team_name} ({team_email})")
                # Carry any email file attachments onto the new task's Documents.
                if new_id:
                    save_email_attachments_to_task(msg, new_id)
            except Exception as e:
                print(f"  Error creating task for {team_email}: {e}")

# Track which emails we've already processed
INBOX_TRACKER = os.path.expanduser('~/.openclaw/workspace/logs/inbox-processed.json')
SENT_TRACKER = os.path.expanduser('~/.openclaw/workspace/logs/sent-processed.json')

def load_tracker(path):
    try:
        with open(path) as f:
            return set(json.load(f))
    except:
        return set()

def save_tracker(path, ids):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(list(ids)[-500:], f)  # Keep last 500

def load_sent_tracker():
    return load_tracker(SENT_TRACKER)

def save_sent_tracker(ids):
    save_tracker(SENT_TRACKER, ids)

def check_sent_folder():
    """Scan Sent folder for outbound emails to @exosaero.com team."""
    try:
        mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mail.sock.settimeout(15)
        mail.starttls()
        mail.login(EMAIL_USER, EMAIL_PASS)

        # Try common sent folder names
        sent_folder = None
        for folder_name in ['Sent', 'INBOX.Sent', 'Sent Messages', 'Sent Items']:
            status, _ = mail.select(folder_name, readonly=True)
            if status == 'OK':
                sent_folder = folder_name
                break

        if not sent_folder:
            # List folders to find sent
            status, folders = mail.list()
            if status == 'OK':
                for f in folders:
                    decoded = f.decode() if isinstance(f, bytes) else f
                    if 'sent' in decoded.lower():
                        match = re.search(r'"([^"]*[Ss]ent[^"]*)"', decoded)
                        if match:
                            sent_folder = match.group(1)
                            mail.select(sent_folder, readonly=True)
                            break

        if not sent_folder:
            print("  Could not find Sent folder")
            mail.logout()
            return

        print(f"  Scanning sent folder: {sent_folder}")

        # Search for recent emails (last 3 days)
        from datetime import timedelta
        since_date = (datetime.now() - timedelta(days=3)).strftime('%d-%b-%Y')
        status, data = mail.search(None, f'SINCE {since_date}')

        processed = load_sent_tracker()
        new_processed = set(processed)

        if status == 'OK' and data[0]:
            mail_ids = data[0].split()
            print(f"  Found {len(mail_ids)} sent emails in last 3 days")

            # Only process the most recent 20 emails to avoid long hangs
            mail_ids = mail_ids[-20:]

            for i in mail_ids:
                msg_id = i.decode() if isinstance(i, bytes) else str(i)
                if msg_id in processed:
                    new_processed.add(msg_id)
                    continue

                try:
                    mail.sock.settimeout(10)
                except Exception:
                    pass

                # Fetch headers only first — much faster than full body
                status, hdr_data = mail.fetch(i, '(BODY.PEEK[HEADER.FIELDS (TO CC SUBJECT)])')
                if status != 'OK':
                    new_processed.add(msg_id)
                    continue

                recipients = []
                subject = ''
                for response_part in hdr_data:
                    if isinstance(response_part, tuple):
                        hdr_msg = email.message_from_bytes(response_part[1])
                        subject = decode_mime_header(hdr_msg.get('subject', ''))
                        recipients = extract_recipients(hdr_msg)

                # Skip internal system notification emails — these are generated by
                # assignment-notifier.py and would create a feedback loop if processed.
                # Peel leading Re:/Fw:/Fwd: before matching so that FORWARDED or REPLIED
                # notification emails ("Re: [Mission Control] Task assigned to you: X",
                # "Fw: Task assigned to you: X") are also recognized as system mail and skipped.
                # Without this, wrapped notifications slipped through and created nested-prefix
                # tasks like "[Mission Control] Task assigned to you: [Mission Control] ...".
                _subj_probe = subject or ''
                _p = None
                while _p != _subj_probe:
                    _p = _subj_probe
                    _subj_probe = re.sub(r'^\s*(?:re|fw|fwd)\s*:\s*', '', _subj_probe, flags=re.I)
                _is_system_notification = any(_subj_probe.startswith(pfx) for pfx in [
                    '[Mission Control]', 'Task assigned to you', '[TaskAssign]',
                    '[EXO]', 'HEARTBEAT', '[Cron', '[Nightly',
                ])
                if _is_system_notification:
                    new_processed.add(msg_id)
                    continue

                # Only fetch body if relevant (@exosaero.com recipient)
                if any(r.endswith('@exosaero.com') for r in recipients):
                    # Fetch the FULL message (not just TEXT) so email attachments survive and can be
                    # linked to the created task's Documents, instead of only the body text.
                    status2, full_data = mail.fetch(i, '(BODY.PEEK[])')
                    real_msg = None
                    if status2 == 'OK':
                        for response_part in full_data:
                            if isinstance(response_part, tuple):
                                try:
                                    real_msg = email.message_from_bytes(response_part[1])
                                except Exception:
                                    real_msg = None
                    if real_msg is not None:
                        body = extract_text_body(real_msg)
                        msg_for_task = real_msg
                    else:
                        body = ""
                        msg_for_task = email.message_from_bytes(
                            (f"To: {', '.join(recipients)}\nSubject: {subject}\n\n").encode())
                    if not msg_for_task.get('To'):
                        msg_for_task['To'] = ', '.join(recipients)
                    print(f"  Processing outbound to team: {subject[:60]}")
                    process_outbound_to_team(msg_for_task, subject, body)


                new_processed.add(msg_id)

        save_sent_tracker(new_processed)
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"  Sent folder scan error: {e}")
        import traceback; traceback.print_exc()

def check_inbox():
    import tempfile
    try:
        mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mail.sock.settimeout(15)
        mail.starttls()
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('inbox')

        processed = load_tracker(INBOX_TRACKER)
        new_processed = set(processed)

        status, data = mail.search(None, 'UNSEEN')
        if status == 'OK':
            mail_ids = data[0].split()
            for i in mail_ids:
                msg_id = i.decode() if isinstance(i, bytes) else str(i)
                if msg_id in processed:
                    continue
                status, msg_data = mail.fetch(i, '(BODY.PEEK[])')
                if status == 'OK':
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject = msg['subject'] or ''
                            sender = msg['from'] or ''

                            body = ""
                            attachments = []

                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disp = str(part.get('Content-Disposition', ''))

                                    # Extract attachments
                                    if 'attachment' in content_disp or part.get_filename():
                                        filename = part.get_filename() or 'attachment'
                                        if filename.lower().endswith(('.xlsx', '.xls', '.csv')):
                                            payload = part.get_payload(decode=True)
                                            if payload:
                                                tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='_' + filename)
                                                tmpfile.write(payload)
                                                tmpfile.close()
                                                attachments.append((tmpfile.name, filename))
                                                print(f"  Saved attachment: {filename} ({len(payload)} bytes)")

                                    # Extract body text
                                    elif content_type == "text/plain" and not body:
                                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            else:
                                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

                            process_email(subject, sender, body, attachments)

                            # Clean up temp files
                            for filepath, _ in attachments:
                                try: os.unlink(filepath)
                                except: pass

                new_processed.add(msg_id)

        save_tracker(INBOX_TRACKER, new_processed)
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"IMAP Error: {e}")

if __name__ == '__main__':
    import threading
    print("Starting Mission Control Email Tracker...")
    check_inbox()
    print("Scanning sent folder for team assignments...")
    t = threading.Thread(target=check_sent_folder, daemon=True)
    t.start()
    t.join(timeout=45)
    if t.is_alive():
        print("  Sent folder scan timed out — skipping")
    print("Done.")
