#!/usr/bin/env python3
"""mail_search.py — READ-ONLY header search of Jon's mailbox (Proton Bridge IMAP, All Mail).

Used by the Decisions Daily Update (R-017) to check whether a decision's action already happened
(e.g. John already sent/signed/returned it) before surfacing it as open. Headers only — never
reads bodies, never modifies flags.

  python3 scripts/mail_search.py --since 2026-09-20 "Velocity" "Caswell"
Prints: date | from | to | subject  (newest last, up to 10 per term)
"""
import argparse, email, imaplib, json, os
from datetime import datetime
from email.header import decode_header


def dh(s):
    return ''.join(p.decode(c or 'utf-8', 'ignore') if isinstance(p, bytes) else p for p, c in decode_header(s or ''))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--since', required=True, help='YYYY-MM-DD')
    ap.add_argument('terms', nargs='+')
    a = ap.parse_args()
    since = datetime.strptime(a.since, '%Y-%m-%d').strftime('%d-%b-%Y')
    pw = json.load(open(os.path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
    M = imaplib.IMAP4('127.0.0.1', 1143)
    M.login('jquinnexo@pm.me', pw)
    M.select('"All Mail"', readonly=True)
    for term in a.terms:
        ids = set()
        for crit in ('SUBJECT', 'FROM', 'TO'):
            _, d = M.search(None, 'SINCE', since, crit, '"%s"' % term.replace('"', ''))
            ids |= set(d[0].split())
        print(f'### {term}: {len(ids)} message(s)')
        for n in sorted(ids, key=int)[-10:]:
            _, d = M.fetch(n, '(BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT)])')
            h = email.message_from_bytes(d[0][1])
            print(f"  {(h['Date'] or '')[:22]} | {dh(h['From'])[:45]} | {dh(h['To'])[:45]} | {dh(h['Subject'])[:110]}")
    M.logout()


if __name__ == '__main__':
    main()
