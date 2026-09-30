#!/usr/bin/env python3
"""
sam-flightopps-watch.py — Weekly keyword watch on SAM.gov for a NEW NASA Flight
Opportunities provider on-ramp (or any suborbital flight-services) solicitation.

Why this exists: On 2026-04-20 the Flight Opportunities Contracting Officer
(Melissa Newell, AFRC) told Exos the program is NOT currently on-ramping flight
providers, and that any future on-ramp will be posted to SAM.gov. This catches
that solicitation the day it posts instead of after the response window closes.
Getting BLK3 onto the Flight Opportunities provider roster = NASA-funded student
and research payloads (TechRise, TechFlights, etc.) get assigned to us.

Unlike sam-amendment-watch.py (tracks KNOWN solicitation numbers), this is a
TITLE-keyword sweep for a solicitation whose number we don't have yet. Mirrors
sam-osp4-watch.py.

Reads:
  - ~/.openclaw/secrets.json         (key: sam_api_key)
State:
  - .sam-flightopps-watch-state.json (set of notice IDs already seen)
Alert: emails jquinn@exosaero.com (cc jquinnexo@pm.me) via msmtp/Proton bridge on
any NEW notice matching the watch terms. First run only baselines (no alert spam).
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("sam-flightopps-watch")
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

import json, os, subprocess, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta

WS = '/Users/exomac/.openclaw/workspace'
SECRETS = os.path.expanduser('~/.openclaw/secrets.json')
STATE = os.path.join(WS, '.sam-flightopps-watch-state.json')
TO = 'jquinn@exosaero.com'
CC = 'jquinnexo@pm.me'
API = 'https://api.sam.gov/opportunities/v2/search'

# Two-pronged sweep to catch the on-ramp regardless of how it is titled:
#  1) BROAD suborbital-specific titles across ALL orgs (very low noise — there
#     are ~0 federal solicitations titled "suborbital" at any given time).
#  2) NASA-SCOPED flight/payload/launch terms — the on-ramp comes from NASA AFRC
#     (Armstrong), and NASA posts so few notices that a broad "Flight"/"Payload"
#     sweep restricted to NASA yields only a handful, so we won't miss a
#     differently-titled on-ramp (the prior one was numbered 80AFRC23R0001) and
#     won't drown in DoD "Flight" noise.
BROAD_TERMS = [
    'Flight Opportunities',
    'Suborbital',
    'Suborbital Flight',
    'Commercial Suborbital',
    'Reusable Suborbital',
    'Suborbital Reusable Launch',
]
NASA_ORG = 'NASA'
NASA_TERMS = [
    'Flight',
    'Suborbital',
    'Payload',
    'Reusable',
    'Launch Services',
    'Flight Test',
]

# (label, extra query params) — deduped downstream by noticeId
QUERIES = (
    [(f"title:{t}", {'title': t}) for t in BROAD_TERMS]
    + [(f"NASA/title:{t}", {'title': t, 'organizationName': NASA_ORG}) for t in NASA_TERMS]
)

def load_json(p, default):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def get_key():
    return load_json(SECRETS, {}).get('sam_api_key')

def sam_query(key, extra):
    today = datetime.now()
    params = {
        'api_key': key,
        'postedFrom': (today - timedelta(days=90)).strftime('%m/%d/%Y'),
        'postedTo': today.strftime('%m/%d/%Y'),
        'ptype': 'o,p,r,k,s',  # solicitation, presol, sources-sought, combined, special notice
        'limit': '50',
    }
    params.update(extra)
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    return data.get('opportunitiesData', []) or []

def send_alert(new_notices):
    lines = ["SAM.gov Flight Opportunities / suborbital-services watch found NEW matching notice(s):\n"]
    for n in new_notices:
        lines.append(f"* {n.get('title','(no title)')}")
        lines.append(f"    Type: {n.get('type','')}  |  Posted: {n.get('postedDate','')}")
        lines.append(f"    Sol#: {n.get('solicitationNumber','n/a')}  |  Dept: {n.get('fullParentPathName','')}")
        if n.get('responseDeadLine'):
            lines.append(f"    Response deadline: {n.get('responseDeadLine')}")
        link = n.get('uiLink') or f"https://sam.gov/search/?keywords={urllib.parse.quote(n.get('title',''))}"
        lines.append(f"    {link}\n")
    lines.append("ACTION: If this is the NASA Flight Opportunities provider on-ramp (or a suborbital "
                 "flight-services solicitation), Exos can compete to join the roster and receive assigned "
                 "payloads. Review eligibility + response window NOW — the CO (Newell) said this is the "
                 "only channel. Some hits will be noise (any 'suborbital' title); ignore non-relevant ones.")
    # MC #1539 standing guardrail: every NASA IDIQ response is pre-cleared against the two
    # 2023 FO IDIQ4 disqualifiers before it goes to John (exo3 gate: nasa-idiq-preclear-exo3).
    if any('IDIQ' in f"{n.get('title','')} {n.get('type','')}".upper()
           or 'NASA' in (n.get('fullParentPathName') or '').upper() for n in new_notices):
        lines.append("\nNASA IDIQ PRE-CLEAR (MC #1539) — before any response routes to John:\n"
                     "  1) Past performance LEADS with the FAA-licensed, flight-qualified BLK3 (license 3/13/26, "
                     "heritage since 2018) — not AFWERX (2023: 'not a representative qualified launch vehicle').\n"
                     "  2) Full year-by-year 5-contract-year Price Volume with cost basis — not ROM/summary "
                     "(2023: 'insufficient financial detail over five contract years'). OSP-4 anchor: 3-day, $1,017,500/flight.\n"
                     "  Gate: python3 scripts/nasa_idiq_preclear_exo3.py <response file> (must PASS).")
    body = "\n".join(lines)
    msg = (f"From: jquinnexo@pm.me\nTo: {TO}\nCc: {CC}\n"
           f"Subject: [SAM WATCH] {len(new_notices)} new Flight Opportunities / suborbital notice(s)\n\n{body}\n")
    import shutil
    _oc = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
    r = subprocess.run([_oc, "message", "send", "--channel", "discord", "--target", "1501636814849577050", "-m", f"**[SAM WATCH] {len(new_notices)} new Flight Opportunities / suborbital notice(s)**\n\n" + body], capture_output=True, timeout=60)
    return r.returncode == 0

def main():
    key = get_key()
    if not key:
        print("NO sam_api_key in secrets.json — skipping."); return 0
    state = load_json(STATE, {})
    seen = set(state.get('seen_ids', []))
    first_run = not seen
    found = {}  # noticeId -> notice
    for label, extra in QUERIES:
        try:
            for n in sam_query(key, extra):
                nid = n.get('noticeId') or n.get('solicitationNumber') or n.get('title')
                if nid:
                    found[nid] = n
        except Exception as e:
            print(f"  query failed '{label}': {e}")
    new_ids = [nid for nid in found if nid not in seen]
    new_notices = [found[nid] for nid in new_ids]
    for nid in found: seen.add(nid)
    state['seen_ids'] = sorted(seen)
    state['last_run'] = datetime.now().isoformat()
    with open(STATE, 'w') as f: json.dump(state, f, indent=2)
    print(f"Swept {len(QUERIES)} queries, {len(found)} total matches, {len(new_ids)} new.")
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
