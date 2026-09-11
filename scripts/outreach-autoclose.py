#!/usr/bin/env python3
"""
OUTREACH AUTO-CLOSE — closes sales/cold-outreach tasks once the send is detected.

Jon sends outreach from Outlook/M365 and BCCs jquinnexo@pm.me (copies land in the
Proton INBOX FROM jquinn@exosaero.com). This reads those, extracts the external
recipient(s), resolves the domain -> company (config/outreach-domain-map.json),
and marks any OPEN task that (a) is opted in via an auto-close tag AND (b) references
that recipient email / company / domain -> Done. Idempotent, logged, tag-gated so it
can never touch a task that wasn't explicitly flagged for auto-close.

Opt-in tags (case-insensitive, any one): outreach, cold-outreach, autoclose-on-send.
Run:  python3 scripts/outreach-autoclose.py [--dry-run] [--verbose]
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("outreach-autoclose")
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


# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import imaplib, email, os, re, json, sys, urllib.request
from email.utils import getaddresses
from datetime import datetime, timedelta

IMAP_HOST, IMAP_PORT = '127.0.0.1', 1143
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
SELF_FROMS = ('exosaero.com', 'jquinnexo@pm.me', 'jquinnexo@proton.me')
INTERNAL = re.compile(r'(exosaero\.com|jquinnexo@|@pm\.me|@proton\.me|noreply|no-reply|mailer-daemon)', re.I)
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
FWD_TO_RE = re.compile(r'(?im)^\s*[>*\s]*(?:to|cc)\s*:\s*(.+)$')
LOOKBACK_DAYS = 14

WS = os.path.expanduser('~/.openclaw/workspace')
SUPA = 'https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/'
SUPA_KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp'
LOG = os.path.join(WS, 'logs', 'outreach-autoclose.jsonl')
STATE = os.path.join(WS, 'logs', 'outreach-autoclose-state.json')
MAP_FILE = os.path.join(WS, 'config', 'outreach-domain-map.json')
AUTOCLOSE_TAGS = {'outreach', 'cold-outreach', 'autoclose-on-send'}
SENT_SUBJECTS = set()  # lowercased subjects of Jon's recent sends (for match-subject:<kw> auto-close)

DRY = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv or DRY


def log_line(rec):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f:
        f.write(json.dumps(rec) + '\n')


def load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def supa(path, method='GET', body=None):
    req = urllib.request.Request(
        SUPA + path,
        data=(json.dumps(body).encode() if body is not None else None),
        method=method,
        headers={'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + SUPA_KEY,
                 'Content-Type': 'application/json', 'Prefer': 'return=representation'})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else []


def _is_self(frm):
    f = (frm or '').lower()
    return any(s in f for s in SELF_FROMS)


def _text_body(msg):
    try:
        if msg.is_multipart():
            for p in msg.walk():
                if p.get_content_type() == 'text/plain':
                    return p.get_payload(decode=True).decode('utf-8', 'ignore')
            for p in msg.walk():
                if p.get_content_type() == 'text/html':
                    h = p.get_payload(decode=True).decode('utf-8', 'ignore')
                    return re.sub(r'<[^>]+>', ' ', h)
        else:
            return (msg.get_payload(decode=True) or b'').decode('utf-8', 'ignore')
    except Exception:
        pass
    return ''


def collect_recipients():
    """Set of external recipient emails from Jon's recent sends (BCC self-copies + forwards)."""
    since = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%d-%b-%Y')
    emails = set()
    mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
    try:
        mail.login(EMAIL_USER, EMAIL_PASS)
        for folder in ['INBOX', 'Archive']:
            try:
                rv, _ = mail.select(folder, readonly=True)
                if rv != 'OK':
                    continue
            except Exception:
                continue
            uids = set()
            for frm in SELF_FROMS:
                typ, data = mail.uid('search', None, f'(SINCE {since}) (FROM "{frm}")')
                if typ == 'OK' and data and data[0]:
                    uids.update(data[0].split())
            for uid in uids:
                t, md = mail.uid('fetch', uid, '(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT)])')
                if t != 'OK' or not md or not md[0]:
                    continue
                msg = email.message_from_bytes(md[0][1])
                if not _is_self(msg.get('From', '')):
                    continue
                SENT_SUBJECTS.add((msg.get('Subject', '') or '').lower())
                recips = set(a.lower() for _, a in getaddresses(msg.get_all('To', []) + msg.get_all('Cc', []))
                             if a and EMAIL_RE.fullmatch(a.strip()) and not INTERNAL.search(a.lower()))
                if not recips:  # forwarded-in: real recipients hidden in body
                    tb, bmd = mail.uid('fetch', uid, '(BODY.PEEK[])')
                    if tb == 'OK' and bmd and bmd[0]:
                        body = _text_body(email.message_from_bytes(bmd[0][1]))
                        for m in FWD_TO_RE.finditer(body or ''):
                            for e in EMAIL_RE.findall(m.group(1)):
                                el = e.lower()
                                if not INTERNAL.search(el):
                                    recips.add(el)
                emails |= recips
    finally:
        try:
            mail.logout()
        except Exception:
            pass
    return emails


def main():
    dmap = {k.lower(): v for k, v in load_json(MAP_FILE, {}).items()}
    recips = collect_recipients()
    domains = set(e.split('@', 1)[1] for e in recips if '@' in e)
    companies = set(dmap[d].lower() for d in domains if d in dmap)
    if VERBOSE:
        print(f"[collect] {len(recips)} recipients, {len(domains)} domains, {len(companies)} mapped companies")
        for e in sorted(recips):
            dom = e.split('@', 1)[1] if '@' in e else ''
            print("   send ->", e, ("[" + dmap[dom] + "]" if dom in dmap else ""))

    state = load_json(STATE, {'closed': []})
    already = set(state.get('closed', []))
    tasks = supa("tasks?select=id,title,description,tags,state,category&state=neq.Done&limit=3000")
    closed = []
    for t in tasks:
        if t['id'] in already:
            continue
        tags = set((str(x) or '').lower() for x in (t.get('tags') or []))
        if not (tags & AUTOCLOSE_TAGS):
            continue  # tag-gated: only opted-in outreach tasks are eligible
        hay = ((t.get('title') or '') + ' ' + (t.get('description') or '')).lower()
        matched = None
        # (1) exact recipient email present in the task — the gold-standard signal.
        for e in recips:
            if e in hay:
                matched = ('email', e); break
        # (2) a CURATED prime's company name present (domain map only — never shared
        #     domains like nasa.gov/.edu/.mil, which would false-close).
        if not matched:
            for c in companies:
                if c and c in hay:
                    matched = ('company', c); break
        # (3) subject-keyword rule: a task opts in with a 'match-subject:<kw>' tag and
        #     auto-closes when any of Jon's recent sends carries <kw> in its subject
        #     (for recurring sends to a fixed recipient, e.g. the weekly investor update).
        if not matched:
            for tg in tags:
                if tg.startswith('match-subject:'):
                    kw = tg.split(':', 1)[1].strip()
                    if kw and any(kw in subj for subj in SENT_SUBJECTS):
                        matched = ('subject', kw); break
        if not matched:
            continue
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        rec = {'ts': now, 'task_id': t['id'], 'title': (t.get('title') or '')[:80],
               'match': matched[0], 'value': matched[1], 'dry_run': DRY}
        if not DRY:
            note = (f"\n\n[AUTO-CLOSED {now}] Outreach send detected ({matched[0]}: {matched[1]}). "
                    "Task auto-completed by outreach-autoclose.")
            supa("tasks?id=eq." + str(t['id']), 'PATCH',
                 {"state": "Done", "completed_at": now,
                  "description": ((t.get('description') or '') + note)[:8000]})
            state.setdefault('closed', []).append(t['id'])
        closed.append(rec)
        log_line(rec)
        print(f"{'[DRY] would close' if DRY else '[CLOSED]'} #{t['id']} {rec['title']!r} ({matched[0]}: {matched[1]})")

    if not DRY:
        json.dump(state, open(STATE, 'w'), indent=2)
    print(f"\n{'DRY-RUN ' if DRY else ''}done — {len(closed)} outreach task(s) {'would be ' if DRY else ''}closed.")


if __name__ == '__main__':
    main()
