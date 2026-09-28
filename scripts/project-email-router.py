#!/usr/bin/env python3
"""
Exos Aerospace — Project Email Router
Scans ProtonMail via Bridge IMAP for project-addressed emails (+alias),
parses them with AI, updates Supabase tasks, and posts to Discord channels.

Usage:
  python3 project-email-router.py              # Single scan
  python3 project-email-router.py --daemon      # Run every 2 minutes
  python3 project-email-router.py --setup       # Create Discord channels
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---

import imaplib
import email
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from email.header import decode_header

# ── Config ──
IMAP_HOST = '127.0.0.1'
IMAP_PORT = 1143
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = os.environ.get('PROTON_BRIDGE_PASS', __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password'])

SUPABASE_URL = 'https://pcrgpuoljylqcumijvnw.supabase.co'
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"])

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHANNELS_FILE = os.path.join(SCRIPT_DIR, 'project-channels.json')
PROCESSED_FILE = os.path.join(SCRIPT_DIR, '.project-email-processed.json')
LOG_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'logs')

SCAN_INTERVAL = 120  # seconds between scans in daemon mode


# ── Helpers ──

def load_channels():
    with open(CHANNELS_FILE) as f:
        return json.load(f)

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()

def save_processed(ids):
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(ids), f)

def decode_mime_header(raw):
    parts = decode_header(raw or '')
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or 'utf-8', errors='ignore'))
        else:
            decoded.append(part)
    return ' '.join(decoded)

def extract_email_address(sender):
    match = re.search(r'<([^>]+)>', sender)
    return match.group(1).lower() if match else sender.strip().lower()

def extract_alias(to_addresses):
    """Extract +alias from recipient addresses. Returns alias or None."""
    for addr in to_addresses:
        addr_lower = addr.lower()
        match = re.search(r'jquinnexo\+([a-z0-9-]+)@', addr_lower)
        if match:
            return match.group(1)
    return None

def get_email_body(msg):
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    return payload.decode(charset, errors='ignore')
            elif ct == 'text/html' and not any(
                p.get_content_type() == 'text/plain' for p in msg.walk()
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    html = payload.decode(charset, errors='ignore')
                    # Basic HTML strip
                    text = re.sub(r'<[^>]+>', ' ', html)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            return payload.decode(charset, errors='ignore')
    return ''

def get_all_recipients(msg):
    """Get all To, CC, BCC addresses."""
    addrs = []
    for header in ['to', 'cc', 'bcc', 'delivered-to']:
        raw = msg.get(header, '')
        if raw:
            decoded = decode_mime_header(raw)
            addrs.extend(re.findall(r'[\w.+-]+@[\w.-]+', decoded.lower()))
    return addrs

def match_project_by_alias(alias, channels_config):
    """Match email +alias to project config."""
    for ch in channels_config['channels']:
        slug = ch['project_slug']
        email_alias = ch['email_alias']
        # Match by slug directly or by alias in email
        alias_in_email = re.search(r'\+([a-z0-9-]+)@', email_alias)
        if alias_in_email and alias_in_email.group(1) == alias:
            return ch
    return None

def match_project_by_content(subject, body, channels_config):
    """Fuzzy match email content to project using keywords."""
    text = (subject + ' ' + body[:1000]).lower()
    best_match = None
    best_score = 0
    for ch in channels_config['channels']:
        score = sum(1 for kw in ch['keywords'] if kw in text)
        if score > best_score:
            best_score = score
            best_match = ch
    if best_score >= 2:
        return best_match
    return None


# ── Supabase API ──

def supabase_request(method, path, body=None):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    if method == 'POST':
        headers['Prefer'] = 'return=representation'
    elif method == 'PATCH':
        headers['Prefer'] = 'return=representation'

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        result = resp.read().decode()
        return json.loads(result) if result else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else str(e)
        print(f"  Supabase {method} {path} error {e.code}: {err_body}")
        return None

def find_matching_task(project_id, subject, body):
    """Find the most relevant task in a project based on email subject/body."""
    tasks = supabase_request('GET', f'tasks?project_id=eq.{project_id}&state=neq.Done&order=priority.desc&limit=100')
    if not tasks:
        return None

    text = (subject + ' ' + body[:500]).lower()
    best_task = None
    best_score = 0

    for task in tasks:
        title = (task.get('title') or '').lower()
        desc = (task.get('description') or '').lower()
        score = 0

        # Check word overlap between email and task
        title_words = set(re.findall(r'\w{3,}', title))
        for word in title_words:
            if word in text:
                score += 2

        desc_words = set(re.findall(r'\w{4,}', desc))
        for word in desc_words:
            if word in text:
                score += 1

        if score > best_score:
            best_score = score
            best_task = task

    if best_score >= 3:
        return best_task
    return None

def find_project_id(project_name, category):
    """Find or create project in Supabase."""
    # Search by name
    encoded_name = urllib.parse.quote(project_name)
    projects = supabase_request('GET', f'projects?name=ilike.{encoded_name}&limit=1')
    if projects and len(projects) > 0:
        return projects[0]['id']

    # Create project
    new_proj = supabase_request('POST', 'projects', {
        'name': project_name,
        'status': 'active',
        'category': category,
    })
    if new_proj and isinstance(new_proj, list) and len(new_proj) > 0:
        print(f"  Created project: {project_name}")
        return new_proj[0]['id']
    return None

def update_task_from_email(task, subject, body, sender_email, sender_name):
    """Update a task based on email content."""
    body_lower = body.lower()

    # Detect status changes from email content
    completion_signals = ['completed', 'done', 'finished', 'wrapped up', 'all set',
                          'taken care of', 'shipped', 'delivered', 'submitted', 'sent off']
    blocked_signals = ['blocked', 'waiting on', 'stuck', 'need approval', 'pending review',
                       'can\'t proceed', 'delayed', 'held up']
    progress_signals = ['working on', 'in progress', 'started', 'making progress',
                        'halfway', 'update on', 'progress report']

    new_state = None
    if any(sig in body_lower for sig in completion_signals):
        new_state = 'Done'
    elif any(sig in body_lower for sig in blocked_signals):
        new_state = 'To Do'  # "Blocked" retired (Jon 9/2) — not-in-progress = To Do
    elif any(sig in body_lower for sig in progress_signals):
        new_state = 'In Progress'

    updates = {}
    if new_state and new_state != task.get('state'):
        updates['state'] = new_state
        if new_state == 'Done':
            updates['completed_at'] = datetime.now(timezone.utc).isoformat()
            updates['progress'] = 100

    # Append email summary to description
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    email_note = f"\n\n[{timestamp}] Email from {sender_name}: {subject}"
    if body[:200].strip():
        email_note += f"\n{body[:200].strip()}"

    existing_desc = task.get('description') or ''
    updates['description'] = (existing_desc + email_note)[:4000]

    if updates:
        result = supabase_request('PATCH', f"tasks?id=eq.{task['id']}", updates)
        state_msg = f" → state={new_state}" if new_state else ""
        print(f"  Task updated: '{task.get('title')}'{state_msg}")
        return new_state

    return None

def create_activity_from_email(project_id, task_id, subject, body, sender_email, sender_name):
    """Log an activity entry for the email."""
    activity_note = f"Email from {sender_name} ({sender_email}): {subject}\n\n{body[:500]}"
    comment = {
        'project_id': project_id,
        'body': activity_note,
    }
    if task_id:
        comment['task_id'] = task_id
    supabase_request('POST', 'comments', comment)

def create_task_from_email(project_id, subject, body, sender_email, sender_name, category):
    """Create a new task from an email when no matching task is found."""
    # Only create tasks for emails that look action-oriented
    action_signals = ['please', 'need to', 'action required', 'todo', 'to do',
                      'follow up', 'schedule', 'send', 'review', 'prepare',
                      'submit', 'complete', 'deadline', 'by friday', 'by monday',
                      'asap', 'urgent', 'priority']
    body_lower = body.lower()
    subject_lower = subject.lower()

    if not any(sig in body_lower or sig in subject_lower for sig in action_signals):
        return None  # Informational email, don't create a task

    task = {
        'title': f"[Email] {subject[:120]}",
        'description': f"From: {sender_name} ({sender_email})\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{body[:1000]}",
        'state': 'To Do',
        'category': category or 'BD',
        'priority': 60,
        'owner': 'Jon',
        'source': f'Email from {sender_name}',
        'project_id': project_id,
    }
    # Dedupe guard: never create a task whose title already exists (prevents re-import loops).
    try:
        import urllib.parse as _up
        _existing = supabase_request('GET', f"tasks?title=eq.{_up.quote(task['title'])}&select=id&limit=1")
        if _existing and isinstance(_existing, list) and len(_existing) > 0:
            print(f"  Skipped duplicate task (already exists): '{task['title']}'")
            return _existing[0]
    except Exception:
        pass
    result = supabase_request('POST', 'tasks', task)
    if result and isinstance(result, list) and len(result) > 0:
        print(f"  Created task: '{task['title']}'")
        return result[0]
    return None


# ── Discord Integration ──

def send_discord_update(channel_name, project_name, subject, sender_name,
                        task_title=None, state_change=None, task_created=False):
    """Send project update to Discord via OpenClaw sessions messaging."""
    # Build the update message
    lines = [f"**{project_name}** — Email Update"]
    lines.append(f"From: {sender_name}")
    lines.append(f"Subject: {subject}")

    if task_title and state_change:
        emoji = {'Done': '✅', 'Blocked': '🔴', 'In Progress': '🔵'}.get(state_change, '📋')
        lines.append(f"{emoji} Task **{task_title}** → {state_change}")
    elif task_title:
        lines.append(f"📋 Updated task: **{task_title}**")
    elif task_created:
        lines.append(f"📌 New task created from email")
    else:
        lines.append(f"💬 Activity logged (no task matched)")

    message = '\n'.join(lines)

    # Post via OpenClaw's Discord messaging (using the sessions_send MCP tool pattern)
    # For now, write to a notifications file that can be picked up by the cron system
    notif_file = os.path.join(SCRIPT_DIR, 'discord-notifications.jsonl')
    notification = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'channel_name': channel_name,
        'message': message,
        'project': project_name,
    }
    with open(notif_file, 'a') as f:
        f.write(json.dumps(notification) + '\n')

    print(f"  Discord [{channel_name}]: {subject[:60]}")
    return True


# ── Main Scanner ──

def scan_project_emails():
    """Connect to IMAP, scan for project-addressed emails, process them."""
    channels_config = load_channels()
    processed = load_processed()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scanning for project emails...")

    try:
        mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mail.starttls()
        mail.login(EMAIL_USER, EMAIL_PASS)
    except Exception as e:
        print(f"  IMAP connection failed: {e}")
        print(f"  Is Proton Bridge running? Check: lsof -i :{IMAP_PORT}")
        return

    try:
        mail.select('INBOX')

        # Search for recent emails (last 3 days to catch any we missed)
        from datetime import timedelta
        since_date = (datetime.now() - timedelta(days=3)).strftime('%d-%b-%Y')
        status, msg_ids = mail.search(None, f'(SINCE {since_date})')

        if status != 'OK' or not msg_ids[0]:
            print("  No recent emails found")
            mail.logout()
            return

        ids = msg_ids[0].split()
        print(f"  Found {len(ids)} emails in last 3 days")

        new_count = 0
        matched_count = 0
        task_updates = 0

        for eid in ids:
            eid_str = eid.decode()
            if eid_str in processed:
                continue

            status, data = mail.fetch(eid, '(RFC822)')
            if status != 'OK':
                continue

            msg = email.message_from_bytes(data[0][1])
            subject = decode_mime_header(msg.get('subject', ''))
            sender = decode_mime_header(msg.get('from', ''))
            sender_email = extract_email_address(sender)
            sender_name = re.sub(r'\s*<[^>]+>\s*', '', decode_mime_header(msg.get('from', ''))).strip()
            if not sender_name or sender_name == sender_email:
                sender_name = sender_email.split('@')[0]
            recipients = get_all_recipients(msg)
            body = get_email_body(msg)

            new_count += 1

            # Step 1: Try to match by +alias in recipient
            alias = extract_alias(recipients)
            project_config = None

            if alias:
                project_config = match_project_by_alias(alias, channels_config)
                if project_config:
                    print(f"  [+{alias}] {sender_name}: {subject[:60]}")

            # Step 2: Fuzzy match by content if no alias
            if not project_config:
                project_config = match_project_by_content(subject, body, channels_config)
                if project_config:
                    print(f"  [auto:{project_config['project_slug']}] {sender_name}: {subject[:60]}")

            if not project_config:
                # No project match — skip (don't route general emails)
                processed.add(eid_str)
                continue

            matched_count += 1

            # Step 3: Find or create the project in Supabase
            project_id = find_project_id(
                project_config['project_name'],
                project_config['category']
            )

            if not project_id:
                print(f"  Could not find/create project: {project_config['project_name']}")
                processed.add(eid_str)
                continue

            # Step 4: Try to match to an existing task
            task = find_matching_task(project_id, subject, body)
            state_change = None
            task_created = False

            if task:
                state_change = update_task_from_email(task, subject, body, sender_email, sender_name)
                if state_change:
                    task_updates += 1
            else:
                # Step 5: Create a new task if email is action-oriented
                new_task = create_task_from_email(
                    project_id, subject, body, sender_email, sender_name,
                    project_config['category']
                )
                if new_task:
                    task = new_task
                    task_created = True

            # Step 6: Log activity/comment on the project
            create_activity_from_email(
                project_id,
                task.get('id') if task else None,
                subject, body, sender_email, sender_name
            )

            # Step 7: Post to Discord
            send_discord_update(
                channel_name=project_config['discord_channel_name'],
                project_name=project_config['project_name'],
                subject=subject,
                sender_name=sender_name,
                task_title=task.get('title') if task else None,
                state_change=state_change,
                task_created=task_created,
            )

            processed.add(eid_str)

        save_processed(processed)
        print(f"  Scan complete: {new_count} new, {matched_count} matched to projects, {task_updates} task updates")

    except Exception as e:
        print(f"  Scan error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            mail.logout()
        except:
            pass


def setup_discord_channels():
    """Output the Discord channel creation commands."""
    config = load_channels()
    print("=" * 60)
    print("DISCORD CHANNEL SETUP")
    print("=" * 60)
    print(f"\nServer ID: {config['discord_server_id']}")
    print(f"Category: {config['discord_category_name']}")
    print(f"\nChannels to create under '{config['discord_category_name']}':\n")
    for ch in config['channels']:
        print(f"  #{ch['discord_channel_name']:<20s}  {ch['project_name']}")
        print(f"    Email: {ch['email_alias']}")
    print(f"\n  #{config['default_channel']['discord_channel_name']:<20s}  (default / unmatched)")
    print("\n" + "=" * 60)
    print("\nTo create channels, the Discord bot needs 'Manage Channels' permission.")
    print("After creating channels, update project-channels.json with the channel IDs.")
    print("=" * 60)


def run_daemon():
    """Run continuously, scanning every SCAN_INTERVAL seconds."""
    print(f"Project Email Router daemon started (scanning every {SCAN_INTERVAL}s)")
    while True:
        try:
            scan_project_emails()
        except Exception as e:
            print(f"Scan cycle error: {e}")
        time.sleep(SCAN_INTERVAL)


if __name__ == '__main__':
    if '--daemon' in sys.argv:
        run_daemon()
    elif '--setup' in sys.argv:
        setup_discord_channels()
    else:
        scan_project_emails()
