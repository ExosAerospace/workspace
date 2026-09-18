#!/usr/bin/env python3
"""
archive-submissions.py — Submission attachment archiver for safekeeping.

RULE (per Jon, 2026-05-31): Jon cc's jquinnexo@pm.me on any submission he sends.
This script scans the jquinnexo@pm.me mailbox (Inbox + Sent) for messages that
involve jquinnexo@pm.me in To/CC/From, saves EVERY attachment to a permanent
archive folder, and records each one in a Mission Control manifest so there is
an auditable copy of everything Jon has sent out.

Dedup: by (message-id + filename). Safe to run repeatedly.
Scheduled via OpenClaw cron alongside the Mission Control Email Tracker.
"""
import imaplib
import email
import json
import os
import re
import socket
import hashlib
from datetime import datetime, timedelta
from email.header import decode_header

socket.setdefaulttimeout(30)

IMAP_HOST = '127.0.0.1'
IMAP_PORT = 1143
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
TRACK_ADDRESS = 'jquinnexo@pm.me'   # primary cc address Jon uses to flag submissions (display)
import os as _pa_os, sys as _pa_sys; _pa_sys.path.insert(0, _pa_os.path.dirname(_pa_os.path.abspath(__file__)))
from proton_aliases import PROTON_ALIASES as _CANON_ALIASES
TRACK_ADDRESSES = set(_CANON_ALIASES)  # match ANY of Jon's 4 Proton aliases (source: proton_aliases.py)

WORKSPACE = '/Users/exomac/.openclaw/workspace'
ARCHIVE_DIR = os.path.join(WORKSPACE, 'submissions-archive')
MANIFEST = os.path.join(ARCHIVE_DIR, 'SUBMISSIONS_LOG.md')
TRACKER = os.path.join(WORKSPACE, 'logs', 'submissions-archived.json')
LOOKBACK_DAYS = 14

# Skip inline noise: signatures images, tracking pixels, etc.
SKIP_NAMES = {'smime.p7s', 'signature.asc'}
SKIP_EXT = {'.p7s', '.asc', '.ics'}


def dec(raw):
    parts = decode_header(raw or '')
    out = []
    for p, cs in parts:
        out.append(p.decode(cs or 'utf-8', 'ignore') if isinstance(p, bytes) else p)
    return ' '.join(out).strip()


def addr_list(msg, *headers):
    addrs = []
    for h in headers:
        raw = msg.get(h, '')
        for part in raw.split(','):
            m = re.search(r'<([^>]+)>', part)
            a = (m.group(1) if m else part).strip().lower()
            if a:
                addrs.append(a)
    return addrs


def load_tracker():
    try:
        with open(TRACKER) as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_tracker(keys):
    os.makedirs(os.path.dirname(TRACKER), exist_ok=True)
    with open(TRACKER, 'w') as f:
        json.dump(sorted(keys)[-5000:], f)


def safe_name(name):
    name = dec(name) or 'attachment'
    name = re.sub(r'[^A-Za-z0-9._\- ]', '_', name).strip().replace(' ', '_')
    return name[:120] or 'attachment'


def ensure_manifest():
    if not os.path.exists(MANIFEST):
        with open(MANIFEST, 'w') as f:
            f.write("# Exos — Submissions Archive Log\n\n")
            f.write("_Auto-maintained. Every attachment from mail involving "
                    f"`{TRACK_ADDRESS}` is saved to this folder for safekeeping._\n\n")
            f.write("| Archived (CT) | Email date | From → To/CC | Subject | File | Size |\n")
            f.write("|---|---|---|---|---|---|\n")


def append_manifest(row):
    ensure_manifest()
    with open(MANIFEST, 'a') as f:
        f.write(row + "\n")


def human_size(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == 'B' else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def scan_folder(mail, folder, processed, new_keys, stats):
    status, _ = mail.select(folder, readonly=True)
    if status != 'OK':
        return
    since = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%d-%b-%Y')
    status, data = mail.search(None, f'SINCE {since}')
    if status != 'OK' or not data or not data[0]:
        return
    ids = data[0].split()[-100:]
    for i in ids:
        try:
            status, msg_data = mail.fetch(i, '(BODY.PEEK[])')
        except Exception:
            continue
        if status != 'OK':
            continue
        for part in msg_data:
            if not isinstance(part, tuple):
                continue
            msg = email.message_from_bytes(part[1])
            involved = set(addr_list(msg, 'to', 'cc', 'from'))
            if not (involved & TRACK_ADDRESSES):
                continue
            if not msg.is_multipart():
                continue

            msg_id = (msg.get('Message-ID') or '').strip() or hashlib.md5(part[1][:2000]).hexdigest()
            subject = dec(msg.get('subject', '')) or '(no subject)'
            frm = dec(msg.get('from', ''))
            to_cc = ', '.join(addr_list(msg, 'to', 'cc'))
            edate = dec(msg.get('date', ''))[:31]

            for sub in msg.walk():
                disp = str(sub.get('Content-Disposition', ''))
                fname = sub.get_filename()
                if not fname and 'attachment' not in disp:
                    continue
                if not fname:
                    continue
                clean = safe_name(fname)
                ext = os.path.splitext(clean)[1].lower()
                if clean in SKIP_NAMES or ext in SKIP_EXT:
                    continue
                payload = sub.get_payload(decode=True)
                if not payload:
                    continue

                key = hashlib.md5((msg_id + '|' + clean).encode()).hexdigest()
                if key in processed:
                    continue

                # Date-prefixed, collision-safe filename
                prefix = datetime.now().strftime('%Y-%m-%d')
                out_name = f"{prefix}__{clean}"
                out_path = os.path.join(ARCHIVE_DIR, out_name)
                n = 1
                while os.path.exists(out_path):
                    stem, x = os.path.splitext(out_name)
                    out_path = os.path.join(ARCHIVE_DIR, f"{stem}_{n}{x}")
                    n += 1
                with open(out_path, 'wb') as fh:
                    fh.write(payload)

                size = human_size(len(payload))
                now = datetime.now().strftime('%Y-%m-%d %H:%M')
                safe_subj = subject.replace('|', '/')[:80]
                append_manifest(
                    f"| {now} | {edate} | {frm.replace('|','/')[:40]} → {to_cc[:60]} "
                    f"| {safe_subj} | `{os.path.basename(out_path)}` | {size} |"
                )
                print(f"  ARCHIVED: {os.path.basename(out_path)} ({size}) from '{subject[:50]}'")
                new_keys.add(key)
                stats['saved'] += 1


def main():
    print(f"[{datetime.now():%Y-%m-%d %H:%M}] Submissions archiver — scanning mail involving {TRACK_ADDRESS}")
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    ensure_manifest()
    processed = load_tracker()
    new_keys = set(processed)
    stats = {'saved': 0}
    try:
        mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        mail.sock.settimeout(20)
        mail.starttls()
        mail.login(EMAIL_USER, EMAIL_PASS)
        for folder in ['INBOX', 'Sent', 'Archive', 'All Mail']:
            try:
                scan_folder(mail, folder, processed, new_keys, stats)
            except Exception as e:
                print(f"  ({folder} skipped: {e})")
        mail.logout()
    except Exception as e:
        print(f"IMAP error: {e}")
    save_tracker(new_keys)
    print(f"Done. {stats['saved']} new attachment(s) archived → {ARCHIVE_DIR}")


if __name__ == '__main__':
    main()
