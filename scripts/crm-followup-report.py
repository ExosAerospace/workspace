#!/usr/bin/env python3
"""
crm-followup-report.py — Weekly CRM follow-up report for LQuinn.

Deterministic replacement for the model-call cron that was timing out.
Pulls active contacts from Supabase, groups them, and emails a plain-text
report to lquinn@exosaero.com via msmtp/Proton Bridge (smtplib).

Groups:
  1) HIGH PRIORITY active conversations
  2) FOLLOW-UP DUE (by days since last contact: 30+, 14-30, <14)
  3) CONTACTED NO REPLY (3-strike discontinue candidates)
Excludes stage in {Closed Lost, Closed, Passed} and status != Active.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import urllib.request, json, smtplib, ssl
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://pcrgpuoljylqcumijvnw.supabase.co'
KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp'
TO = 'lquinn@exosaero.com'

HIGH_STAGES = {'Engaged', 'Meeting Held', 'Meeting Requested', 'Meeting Scheduled',
               'Term Sheet / Proposal', 'Due Diligence', 'Active Partnership', 'Active'}
EXCLUDE_STAGES = {'Closed Lost', 'Closed', 'Passed'}


def fetch_all():
    rows, offset, page = [], 0, 1000
    while True:
        path = (f'/rest/v1/contacts?select=name,organization,email,stage,status,'
                f'last_contacted,next_action,priority_score&order=last_contacted.asc'
                f'&limit={page}&offset={offset}')
        req = urllib.request.Request(BASE + path, headers={
            'apikey': KEY, 'Authorization': f'Bearer {KEY}'})
        batch = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows


def days_since(ts):
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return None


def line(c):
    ds = days_since(c.get('last_contacted'))
    ds_txt = f"{ds}d" if ds is not None else "never"
    na = c.get('next_action')
    s = f"  - {c.get('name') or '(no name)'} | {c.get('organization') or ''} | {c.get('email') or ''} | last: {ds_txt}"
    if na:
        s += f" | next: {na}"
    return s


def build():
    rows = fetch_all()
    active = [c for c in rows
              if (c.get('status') == 'Active')
              and (c.get('stage') not in EXCLUDE_STAGES)]

    high = [c for c in active if c.get('stage') in HIGH_STAGES]
    contacted = [c for c in active if c.get('stage') == 'Contacted']

    high_ids = {id(c) for c in high}
    contacted_ids = {id(c) for c in contacted}
    followup = [c for c in active if id(c) not in high_ids and id(c) not in contacted_ids]

    def by_age(c):
        d = days_since(c.get('last_contacted'))
        return -1 if d is None else d
    high.sort(key=lambda c: -(c.get('priority_score') or 0))
    followup.sort(key=by_age, reverse=True)

    over30 = [c for c in followup if (days_since(c.get('last_contacted')) or 0) >= 30]
    mid = [c for c in followup if 14 <= (days_since(c.get('last_contacted')) or 0) < 30]
    recent = [c for c in followup if (days_since(c.get('last_contacted')) or -1) < 14]

    today = datetime.now().strftime('%Y-%m-%d')
    L = []
    L.append(f"CRM Follow-Up Report - {today}")
    L.append(f"Total active contacts: {len(active)}")
    L.append("")
    L.append(f"1) HIGH PRIORITY ACTIVE CONVERSATIONS ({len(high)})")
    L += [line(c) for c in high] or ["  (none)"]
    L.append("")
    L.append(f"2) FOLLOW-UP DUE ({len(followup)})")
    L.append(f"  Overdue 30+ days ({len(over30)}):")
    L += [line(c) for c in over30[:40]] or ["    (none)"]
    if len(over30) > 40:
        L.append(f"    ... and {len(over30)-40} more")
    L.append(f"  14-30 days ({len(mid)}):")
    L += [line(c) for c in mid[:30]] or ["    (none)"]
    if len(mid) > 30:
        L.append(f"    ... and {len(mid)-30} more")
    L.append(f"  Under 14 days ({len(recent)}):")
    L += [line(c) for c in recent[:20]] or ["    (none)"]
    if len(recent) > 20:
        L.append(f"    ... and {len(recent)-20} more")
    L.append("")
    L.append(f"3) CONTACTED - NO REPLY ({len(contacted)}) - 3-strike discontinue candidates")
    L += [line(c) for c in contacted[:40]] or ["  (none)"]
    if len(contacted) > 40:
        L.append(f"    ... and {len(contacted)-40} more")
    L.append("")
    L.append("Generated automatically by Exo. CRM: localhost:8080/crm.html")
    return today, "\n".join(L)


def send(subject, body):
    import subprocess
    cfg = {}
    for ln in open(str(Path.home() / '.msmtprc')):
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        parts = ln.split(None, 1)
        if len(parts) != 2:
            continue
        k, v = parts[0], parts[1].strip()
        if k in ('host', 'port', 'user', 'password', 'from', 'tls_trust_file', 'passwordeval'):
            cfg[k] = v
    if 'password' not in cfg and 'passwordeval' in cfg:
        cfg['password'] = subprocess.check_output(
            cfg['passwordeval'], shell=True, text=True).strip()
    from email.message import EmailMessage
    msg = EmailMessage()
    msg['From'] = cfg['from']; msg['To'] = TO; msg['Subject'] = subject
    msg.set_content(body)
    ctx = ssl.create_default_context(cafile=cfg.get('tls_trust_file'))
    ctx.check_hostname = False
    with smtplib.SMTP(cfg['host'], int(cfg['port']), timeout=45) as s:
        s.starttls(context=ctx)
        s.login(cfg['user'], cfg['password'])
        s.send_message(msg)


if __name__ == '__main__':
    today, body = build()
    send(f'CRM Follow-Up Report - {today}', body)
    print(f"CRM_FOLLOWUP_OK sent to {TO} ({len(body)} chars)")
