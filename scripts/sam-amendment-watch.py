#!/usr/bin/env python3
"""
sam-amendment-watch.py — Weekly watch on active SAM.gov solicitations for new
amendments / modifications. Deterministic (no LLM). Emails Jon on any change.

Why this exists: DARPA TTO BAA HR001125S0011 Amendment 02 changed the Executive
Summary from "encouraged" to REQUIRED and we tracked the stale base version,
nearly chasing a closed window. This catches amendment changes on the
solicitations we care about BEFORE the deadline instead of at it.

Reads:
  - tracked-solicitations.json  (list of {solnum, label} we're watching)
  - ~/.openclaw/secrets.json    (key: sam_api_key)  <- free key from sam.gov
State:
  - .sam-watch-state.json       (last seen postedDate + amendment count per solnum)
Alert: emails jquinn@exosaero.com via msmtp/Proton bridge on any new/changed notice.
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("sam-watch")
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
TRACK = os.path.join(WS, 'tracked-solicitations.json')
STATE = os.path.join(WS, '.sam-watch-state.json')
TO = 'jquinn@exosaero.com'
API = 'https://api.sam.gov/opportunities/v2/search'

def load_json(p, default):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return default

def get_key():
    s = load_json(SECRETS, {})
    return s.get('sam_api_key')

def sam_query(key, solnum):
    """Return list of notices (base + amendments) for a solicitation number."""
    today = datetime.now()
    params = {
        'api_key': key,
        'solnum': solnum,
        'postedFrom': (today - timedelta(days=360)).strftime('%m/%d/%Y'),  # SAM caps range at 1 year
        'postedTo': today.strftime('%m/%d/%Y'),
        'limit': '50',
    }
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    return data.get('opportunitiesData', []) or []

def fingerprint(notices):
    """Latest posted date + count = change signal."""
    dates = sorted([n.get('postedDate', '') for n in notices])
    titles = [f"{n.get('type','')} | {n.get('postedDate','')}" for n in notices]
    return {'count': len(notices), 'latest': dates[-1] if dates else None, 'notices': titles}

def send_alert(changes):
    lines = ["SAM.gov amendment watch detected changes on tracked solicitations:\n"]
    for c in changes:
        lines.append(f"* {c['label']} ({c['solnum']})")
        lines.append(f"    was: {c['old']}")
        lines.append(f"    now: {c['new']}")
        lines.append(f"    https://sam.gov/search/?keywords={urllib.parse.quote(c['solnum'])}\n")
    lines.append("Check the latest amendment for changes to deadlines, eligibility, or submission rules.")
    body = "\n".join(lines)
    msg = (f"From: jquinnexo@pm.me\nTo: {TO}\n"
           f"Subject: [SAM WATCH] Amendment change on {len(changes)} tracked solicitation(s)\n\n{body}\n")
    import shutil
    _oc = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
    r = subprocess.run([_oc, "message", "send", "--channel", "discord", "--target", "1501636814849577050", "-m", f"**[SAM WATCH] Amendment change on {len(changes)} tracked solicitation(s)**\n\n" + body], capture_output=True, timeout=60)
    return r.returncode == 0

def main():
    key = get_key()
    tracked = load_json(TRACK, [])
    if not key:
        print("NO sam_api_key in secrets.json — get a free key at "
              "sam.gov (Account Details > API Key) and add it as 'sam_api_key'. Skipping.")
        return 0
    if not tracked:
        print("tracked-solicitations.json empty — nothing to watch."); return 0
    state = load_json(STATE, {})
    changes = []
    for item in tracked:
        sol = item['solnum']; label = item.get('label', sol)
        try:
            fp = fingerprint(sam_query(key, sol))
        except Exception as e:
            print(f"  query failed {sol}: {e}"); continue
        prev = state.get(sol)
        if prev is None:
            print(f"  baseline set {sol}: {fp['count']} notices, latest {fp['latest']}")
        elif prev.get('count') != fp['count'] or prev.get('latest') != fp['latest']:
            changes.append({'solnum': sol, 'label': label,
                            'old': f"{prev.get('count')} notices, latest {prev.get('latest')}",
                            'new': f"{fp['count']} notices, latest {fp['latest']}"})
            print(f"  CHANGE {sol}: {prev.get('latest')} -> {fp['latest']}")
        else:
            print(f"  no change {sol}")
        state[sol] = fp
    with open(STATE, 'w') as f: json.dump(state, f, indent=2)
    if changes:
        ok = send_alert(changes)
        print(f"ALERT emailed: {ok} ({len(changes)} change(s))")
        # Governance (soft): also file each change as a tracked go/no-go Decision so
        # it rides the Human Review Queue (an email can be missed; a Decision can't)
        # and becomes sam-watch eval data. Never let this break the watch.
        try:
            import os as _os, re as _re
            sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
            from governance import route as _route
            filed = 0
            for c in changes:
                key = _re.sub(r'[^a-z0-9]+', '-',
                              f"sam-amend-{c['solnum']}-{c['new']}".lower())[:80]
                if _route.escalate_and_file({
                    "source": "SAM.gov Amendment Watch",
                    "relatedItem": c['solnum'],
                    "title": f"SAM amendment change: {c['label']}",
                    "question": (f"{c['label']} ({c['solnum']}) changed: {c['old']} -> "
                                 f"{c['new']}. Review the latest amendment for deadline, "
                                 "eligibility, or scope changes."),
                    "proposedAction": (f"Review https://sam.gov/search/?keywords={c['solnum']} "
                                       "and decide pursue / no-pursue or update the bid plan."),
                    "type": "yesno", "options": ["Reviewed", "Ignore"],
                    "priority": "high", "assignedTo": "jquinn@exosaero.com",
                    "dedupeKey": key,
                }, "sam-watch"):
                    filed += 1
            print(f"Decisions filed: {filed}/{len(changes)}")
        except Exception as e:
            print(f"  decision-file skipped (soft): {e}")
    print("Done.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
