#!/usr/bin/env python3
"""
sam-osp4-watch.py — Weekly keyword watch on SAM.gov for a NEW OSP-4 on-ramp
(or any responsive-launch / RSLP launch-services) solicitation. Deterministic.

Why this exists: The cleanest door for Exos to join the Tactically Responsive
Space (TacRS / Victus) launch competition is the next on-ramp to the OSP-4
IDIQ (Orbital Services Program-4, run by the Rocket Systems Launch Program).
No on-ramp #3 is announced yet — this catches the solicitation the day it posts
instead of after the response window closes. Unlike sam-amendment-watch.py
(which tracks KNOWN solicitation numbers), this is a TITLE-keyword sweep for a
solicitation whose number we don't have yet.

Reads:
  - ~/.openclaw/secrets.json    (key: sam_api_key)
State:
  - .sam-osp4-watch-state.json  (set of notice IDs already seen)
Alert: emails jquinn@exosaero.com via msmtp/Proton bridge on any NEW notice
matching the watch terms. First run only baselines (no alert spam).
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("sam-osp4-watch")
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

import json, os, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta

WS = '/Users/exomac/.openclaw/workspace'
SECRETS = os.path.expanduser('~/.openclaw/secrets.json')
STATE = os.path.join(WS, '.sam-osp4-watch-state.json')
TO = 'jquinn@exosaero.com'
API = 'https://api.sam.gov/opportunities/v2/search'

# Title-keyword terms to sweep. SAM v2 `title` does substring matching.
# Cast wide but specific enough to avoid generic "launch" noise.
TERMS = [
    'Orbital Services Program',
    'OSP-4',
    'Rocket Systems Launch Program',
    'Tactically Responsive Space',
    'Responsive Launch',
    'Victus',
]

def load_json(p, default):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def get_key():
    return load_json(SECRETS, {}).get('sam_api_key')

def sam_query(key, title):
    today = datetime.now()
    params = {
        'api_key': key,
        'title': title,
        'postedFrom': (today - timedelta(days=90)).strftime('%m/%d/%Y'),
        'postedTo': today.strftime('%m/%d/%Y'),
        'ptype': 'o,p,r,k',  # solicitation, presol, sources-sought, combined
        'limit': '50',
    }
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    return data.get('opportunitiesData', []) or []

def send_alert(new_notices):
    lines = ["SAM.gov OSP-4 / responsive-launch watch found NEW matching notice(s):\n"]
    for n in new_notices:
        lines.append(f"* {n.get('title','(no title)')}")
        lines.append(f"    Type: {n.get('type','')}  |  Posted: {n.get('postedDate','')}")
        lines.append(f"    Sol#: {n.get('solicitationNumber','n/a')}  |  Dept: {n.get('fullParentPathName','')}")
        if n.get('responseDeadLine'):
            lines.append(f"    Response deadline: {n.get('responseDeadLine')}")
        link = n.get('uiLink') or f"https://sam.gov/search/?keywords={urllib.parse.quote(n.get('title',''))}"
        lines.append(f"    {link}\n")
    lines.append("ACTION: If this is the OSP-4 on-ramp #3 (or a responsive-launch on-ramp), "
                 "Exos can compete to join the IDIQ. Review eligibility + response window now.")
    body = "\n".join(lines)
    msg = (f"From: jquinnexo@pm.me\nTo: {TO}\n"
           f"Subject: [SAM WATCH] {len(new_notices)} new OSP-4 / responsive-launch notice(s)\n\n{body}\n")
    p = subprocess.run(['msmtp', '-a', 'protonmail', TO], input=msg.encode(), capture_output=True)
    return p.returncode == 0

def main():
    key = get_key()
    if not key:
        print("NO sam_api_key in secrets.json — skipping."); return 0
    state = load_json(STATE, {})
    seen = set(state.get('seen_ids', []))
    first_run = not seen
    found = {}  # noticeId -> notice
    for term in TERMS:
        try:
            for n in sam_query(key, term):
                nid = n.get('noticeId') or n.get('solicitationNumber') or n.get('title')
                if nid:
                    found[nid] = n
        except Exception as e:
            print(f"  query failed '{term}': {e}")
    new_ids = [nid for nid in found if nid not in seen]
    new_notices = [found[nid] for nid in new_ids]
    for nid in found: seen.add(nid)
    state['seen_ids'] = sorted(seen)
    state['last_run'] = datetime.now().isoformat()
    with open(STATE, 'w') as f: json.dump(state, f, indent=2)
    print(f"Swept {len(TERMS)} terms, {len(found)} total matches, {len(new_ids)} new.")
    if first_run:
        print(f"First run — baselined {len(found)} notices, no alert sent.")
        return 0
    if new_notices:
        ok = send_alert(new_notices)
        print(f"ALERT emailed: {ok} ({len(new_notices)} new notice(s))")
        for n in new_notices:
            print(f"  NEW: {n.get('title','')[:80]}")
    else:
        print("No new notices.")
    print("Done.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
