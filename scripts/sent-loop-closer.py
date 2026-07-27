#!/usr/bin/env python3
"""
SENT LOOP-CLOSER — fixes the false-nudge bug across all capture agents.

Jon sends outreach from Outlook / M365 (invisible to these agents) and BCCs
jquinnexo@proton.me. Those BCC copies land in the Proton INBOX as messages
FROM jquinn@exosaero.com. This script reads them, matches the recipient against
the target emails referenced in capture/*.md trackers, and records/annotates a
confirmed send so the agents stop nudging Jon to send something he already sent.

Safe + idempotent. Read-only against email; append-only against trackers.
Run standalone or on a schedule (e.g., hourly) ahead of the capture crons.
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("sent-loop-closer")
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

import imaplib, email, os, re, json, glob, sys, html as _html
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime, timedelta

IMAP_HOST, IMAP_PORT = '127.0.0.1', 1143
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = 'SPqYBivj98-jyF3RujLKxA'
SELF_DOMAIN = 'exosaero.com'                 # Jon's send identity
LOOKBACK_DAYS = 60
WS = os.path.expanduser('~/.openclaw/workspace')
CAP_DIR = os.path.join(WS, 'capture')
REGISTRY = os.path.join(WS, 'logs', 'outreach-sent-registry.json')

# addresses that are NOT external outreach targets
INTERNAL = re.compile(r'(exosaero\.com|jquinnexo@|@pm\.me|@proton\.me|noreply|no-reply|mailer-daemon)', re.I)
EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')


def build_target_registry():
    """email(lower) -> [tracker basenames that reference it]"""
    reg = {}
    for path in glob.glob(os.path.join(CAP_DIR, '*.md')):
        try:
            txt = open(path, encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for m in set(e.lower() for e in EMAIL_RE.findall(txt)):
            if INTERNAL.search(m):
                continue
            reg.setdefault(m, [])
            if os.path.basename(path) not in reg[m]:
                reg[m].append(os.path.basename(path))
    return reg


import os as _pa_os, sys as _pa_sys; _pa_sys.path.insert(0, _pa_os.path.dirname(_pa_os.path.abspath(__file__)))
from proton_aliases import PROTON_ALIASES as _CANON_ALIASES
SELF_FROMS = (SELF_DOMAIN,) + tuple(sorted(_CANON_ALIASES))  # domain + all 4 Proton aliases (source: proton_aliases.py)
# recipient headers inside a forwarded/quoted block (tolerates >, *, markdown)
FWD_TO_RE = re.compile(r'(?im)^\s*[>*\s]*(?:to|cc)\s*:\s*(.+)$')


def _is_self(frm):
    f = (frm or '').lower()
    return any(s in f for s in SELF_FROMS)


def _text_body(msg):
    """Plain-text body; fall back to stripped HTML (Outlook forwards are HTML-only)."""
    plain, htmls = [], []
    if msg.is_multipart():
        for p in msg.walk():
            ct = p.get_content_type()
            if ct == 'text/plain':
                try: plain.append(p.get_payload(decode=True).decode(errors='replace'))
                except Exception: pass
            elif ct == 'text/html':
                try: htmls.append(p.get_payload(decode=True).decode(errors='replace'))
                except Exception: pass
    else:
        try: plain.append(msg.get_payload(decode=True).decode(errors='replace'))
        except Exception: pass
    txt = '\n'.join(plain).strip()
    if not txt and htmls:
        h = '\n'.join(htmls)
        h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)
        h = re.sub(r'(?is)<br\s*/?>', '\n', h)
        h = re.sub(r'(?is)</(p|div|tr)>', '\n', h)
        txt = _html.unescape(re.sub(r'(?s)<[^>]+>', ' ', h))
    return txt


def _is_forward(subject, body):
    if re.match(r'(?i)^\s*(fwd?|fw)\s*:', subject or ''):
        return True
    b = body or ''
    if re.search(r'(?i)forwarded message', b) or re.search(r'(?i)-{2,}\s*original message', b):
        return True
    # an inline header block: a From: line and a To: line carrying an address
    return bool(re.search(r'(?im)^\s*[>*\s]*from\s*:', b) and re.search(r'(?im)^\s*[>*\s]*to\s*:.*@', b))


def _forwarded_recipients(body):
    """Original recipients pulled from the To:/Cc: lines of a forwarded block."""
    recips = set()
    for m in FWD_TO_RE.finditer(body or ''):
        for e in EMAIL_RE.findall(m.group(1)):
            el = e.lower()
            if not INTERNAL.search(el):
                recips.add(el)
    return recips


def fetch_self_sends():
    """INBOX/Archive messages FROM Jon. Header-only fast path; a full body is fetched only
    for self-addressed possible-forwards. INCREMENTAL: per-folder UID high-water-mark so
    steady-state runs only touch new mail, guarded by UIDVALIDITY and a forced full 60-day
    sweep at most every FULL_SWEEP_HOURS (a missed send can never linger beyond that)."""
    STATE_FILE = os.path.join(WS, 'logs', 'slc-imap-state.json')
    FULL_SWEEP_HOURS = 20
    since = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime('%d-%b-%Y')
    HDRS = '(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE)])'

    try:
        state = json.load(open(STATE_FILE))
    except Exception:
        state = {}
    fstates = state.get('folders', {})
    last_full = float(state.get('last_full', 0))
    now_ts = datetime.now().timestamp()
    full_sweep = (now_ts - last_full) > FULL_SWEEP_HOURS * 3600

    out = []
    mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
    try:
        mail.login(EMAIL_USER, EMAIL_PASS)
        # INBOX (BCC self-copies land here) + Archive. 'All Mail' just duplicates these and
        # 'Sent' is Proton-side (never holds M365 sends), so scanning them only wastes fetches.
        for folder in ['INBOX', 'Archive']:
            try:
                rv, _ = mail.select(folder, readonly=True)
                if rv != 'OK':
                    continue
            except Exception:
                continue
            uv = mail.untagged_responses.get('UIDVALIDITY')
            uidval = (uv[0].decode() if isinstance(uv[0], bytes) else str(uv[0])) if uv else None
            fs = fstates.get(folder, {})
            prev_max = int(fs.get('max_uid', 0))
            incremental = (not full_sweep) and uidval is not None and fs.get('uidvalidity') == uidval and prev_max > 0
            uids = set()
            for frm in SELF_FROMS:
                crit = (f'(FROM "{frm}") UID {prev_max + 1}:*' if incremental
                        else f'(SINCE {since}) (FROM "{frm}")')
                typ, data = mail.uid('search', None, crit)
                if typ == 'OK' and data and data[0]:
                    uids.update(data[0].split())
            max_uid = prev_max
            for uid in sorted(uids, key=lambda x: int(x)):
                iu = int(uid)
                if incremental and iu <= prev_max:      # IMAP 'N:*' can echo the last msg
                    continue
                if iu > max_uid:
                    max_uid = iu
                t, md = mail.uid('fetch', uid, HDRS)
                if t != 'OK' or not md or not md[0]:
                    continue
                msg = email.message_from_bytes(md[0][1])
                frm = msg.get('From', '')
                if not _is_self(frm):
                    continue
                subject = (msg.get('Subject', '') or '').strip()
                # (1) BCC self-copy: header recipients are the external target
                recips = set(a.lower() for _, a in getaddresses(msg.get_all('To', []) + msg.get_all('Cc', [])) if a
                             and not INTERNAL.search(a.lower()))
                fwd = bool(re.match(r'(?i)^\s*(fwd?|fw)\s*:', subject))
                # (2) forward Jon sent in: the real recipient is hidden in the forwarded body.
                # Only pay for a body fetch when the header gave NO external recipient.
                if not recips:
                    tb, bmd = mail.uid('fetch', uid, '(BODY.PEEK[])')
                    if tb == 'OK' and bmd and bmd[0]:
                        body = _text_body(email.message_from_bytes(bmd[0][1]))
                        if _is_forward(subject, body):
                            fwd = True
                            recips |= _forwarded_recipients(body)
                if not recips:
                    continue
                try:
                    dstr = parsedate_to_datetime(msg.get('Date')).strftime('%Y-%m-%d %H:%M')
                except Exception:
                    dstr = msg.get('Date', '')
                out.append({'date': dstr, 'from': frm, 'to': sorted(recips),
                            'subject': subject, 'folder': folder, 'forward': fwd})
            fstates[folder] = {'uidvalidity': uidval, 'max_uid': max_uid}
    finally:
        try: mail.logout()
        except Exception: pass

    state = {'folders': fstates, 'last_full': (now_ts if full_sweep else last_full)}
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        json.dump(state, open(STATE_FILE, 'w'), indent=2)
    except Exception:
        pass
    # de-dup identical (subject,to,date) across folders
    seen, uniq = set(), []
    for m in out:
        k = (m['subject'], tuple(sorted(m['to'])), m['date'])
        if k not in seen:
            seen.add(k); uniq.append(m)
    return uniq


def _tokens(local):
    return set(t for t in re.split(r'[._+-]+', local.lower()) if t)

def match_targets(recipient, reg):
    """Return tracked emails matching recipient: exact, or same domain with a
    subset local-part token match (handles thomas.teasley vs thomas.w.teasley)."""
    matches = set()
    if recipient in reg:
        matches.add(recipient)
    rlocal, _, rdom = recipient.partition('@')
    rtok = _tokens(rlocal)
    for tgt in reg:
        tlocal, _, tdom = tgt.partition('@')
        if tdom != rdom:
            continue
        ttok = _tokens(tlocal)
        small, big = (ttok, rtok) if len(ttok) <= len(rtok) else (rtok, ttok)
        if len(small) >= 2 and small <= big:
            matches.add(tgt)
    return matches


def annotate_tracker(basename, target, date, subject):
    """Append an idempotent auto-confirmation to a tracker's end. Returns True if newly added."""
    path = os.path.join(CAP_DIR, basename)
    if not os.path.exists(path):
        return False
    txt = open(path, encoding='utf-8', errors='ignore').read()
    marker = f'SENT CONFIRMED (auto): {target}'
    if marker in txt:
        return False
    block = txt.rstrip() + '\n'
    if '## AUTO SENT-CONFIRMATIONS (loop-closer)' not in txt:
        block += ('\n## AUTO SENT-CONFIRMATIONS (loop-closer)\n'
                  '*Written by scripts/sent-loop-closer.py from Jon\'s BCC\'d Proton copies. '
                  'If a target appears here, Jon ALREADY SENT it from Outlook — do NOT nudge to send it again; '
                  'switch to reply-watch.*\n')
    block += f'- **SENT CONFIRMED (auto): {target}** on {date} — subject "{subject}". Nudge-to-send STOPPED; reply-watch only.\n'
    open(path, 'w', encoding='utf-8').write(block)
    return True


def main():
    reg = build_target_registry()
    sends = fetch_self_sends()

    print(f"=== SENT LOOP-CLOSER — {datetime.now():%Y-%m-%d %H:%M} ===")
    print(f"Tracked target emails across capture/: {len(reg)}")
    print(f"Self-sends (From {SELF_DOMAIN}) in last {LOOKBACK_DAYS}d: {len(sends)}\n")

    registry = {}
    if os.path.exists(REGISTRY):
        try: registry = json.load(open(REGISTRY))
        except Exception: registry = {}

    cleared = []
    if sends:
        print("--- NEW sends detected this cycle (date | to | subject) ---")
        for m in sorted(sends, key=lambda x: x['date']):
            tag = ' [fwd]' if m.get('forward') else ''
            print(f"  {m['date']}{tag}  ->  {', '.join(m['to']) or '(none)'}  |  {m['subject'][:70]}")
        for m in sends:
            for r in m['to']:
                for tgt in match_targets(r, reg):
                    label = tgt if tgt == r else f"{tgt} (sent to {r})"
                    for tracker in reg[tgt]:
                        newly = annotate_tracker(tracker, label, m['date'], m['subject'])
                        registry[tgt] = {'sent_date': m['date'], 'subject': m['subject'], 'sent_to': r,
                                         'trackers': reg[tgt], 'detected': datetime.now().strftime('%Y-%m-%d %H:%M')}
                        if newly:
                            cleared.append((tracker, label, m['date']))
        os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)
        json.dump(registry, open(REGISTRY, 'w'), indent=2)
    else:
        print("No new sends this cycle (incremental fast path). Registry + payload gate still refreshed below.")

    print("\n--- MATCHES against tracked targets (these clear nudges) ---")
    if registry:
        for r, v in sorted(registry.items()):
            print(f"  ✅ {r}  sent {v['sent_date']}  -> {', '.join(v['trackers'])}")
    else:
        print("  (no self-send recipients matched a tracked target)")

    print("\n--- Trackers annotated THIS run ---")
    for tracker, r, d in cleared:
        print(f"  • {tracker}: {r} ({d})")
    if not cleared:
        print("  (none new — already recorded or no matches)")
    print(f"\nRegistry: {REGISTRY}")

    # Deterministic gate (wired 2026-07-17): right after the registry refreshes, prune any
    # already-sent drafts out of the payload serving pool so the payload crons can never
    # re-serve outreach Jon already emailed. Runs every cycle with the freshest registry.
    try:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        gate = subprocess.run([sys.executable, os.path.join(here, 'payload_sent_filter.py')],
                              capture_output=True, text=True, timeout=60)
        print(gate.stdout.strip())
    except Exception as e:
        print(f"[payload-sent-filter] skipped: {e}")


if __name__ == '__main__':
    main()
