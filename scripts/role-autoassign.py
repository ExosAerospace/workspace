#!/usr/bin/env python3
"""
ROLE AUTO-ASSIGN — resolves team/role-queued tasks to the best-matched member using
the capability matrix (config/capability-matrix.json, built from the team surveys).

Trigger: an OPEN task whose owner is a role/queue placeholder ("R&D Team", "RD Team",
"Team", "Unassigned", blank) OR tagged 'auto-assign' / 'rd-team'. For each, classify the
functional domain from its text, pick the highest-rated AVAILABLE member, and assign it
(owner + assigned_to + assigned_email). The existing assignment-notifier emails the owner.

Weighting rules baked in from the surveys:
  * Neil rates high on nearly everything but is RETIRING (train-successor) — excluded from
    NET-NEW auto-assignment unless he's the only competent option, then flagged 'successor-needed'.
  * Phil owns BLK3 flight-hardware by assignment even though his ratings are pending.
Safe: only touches role/queue-owned or opted-in tasks. Idempotent + logged.
Run: python3 scripts/role-autoassign.py [--dry-run]
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("role-autoassign")
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


# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import os, re, json, sys, urllib.request
from datetime import datetime

WS = os.path.expanduser('~/.openclaw/workspace')
SUPA = 'https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/'
SUPA_KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
MATRIX = os.path.join(WS, 'config', 'capability-matrix.json')
LOG = os.path.join(WS, 'logs', 'role-autoassign.jsonl')
DRY = '--dry-run' in sys.argv

# Only DELIBERATELY role-queued tasks (a role placeholder owner) — NOT blank/unassigned,
# so it never silently grabs and mis-classifies an ordinary unowned task.
ROLE_OWNERS = {'r&d team', 'rd team', 'r&d', 'rd-team'}
OPT_IN_TAGS = {'auto-assign', 'rd-team', 'role:rd-team'}

# task text -> functional domain (first match wins; order = specificity)
DOMAIN_KEYWORDS = [
    ('regulatory_faa_export', r'\b(part 450|part 420|faa|launch licens|licensing|range safety|itar|ear|export control|coa|waiver|ast\b)\b'),
    ('propulsion', r'\b(propuls|rdre|engine|combustion|thrust|injector|nozzle|hot ?fire|igniter)\b'),
    ('structures_tanks', r'\b(structure|composite|ips|tank|airframe|layup|pressure vessel|cryo tank)\b'),
    ('avionics_gnc', r'\b(avionics|gnc|guidance|sensor|flight computer|telemetry|imu|gps)\b'),
    ('flight_software', r'\b(flight software|firmware|embedded|flight code|autopilot software)\b'),
    ('test_integration_launchops', r'\b(test|integrat|range|launch ops|hot ?fire|recovery|checkout|rehearsal|static fire)\b'),
    ('manufacturing_supply', r'\b(manufactur|machin|fabricat|production|supply chain|procure|purchas|shop|assembl|weld|harness)\b'),
    ('finance_accounting', r'\b(quickbooks|invoice|payroll|accounting|bookkeep|financial statement|budget|tax|reconcil)\b'),
    ('proposals_contracts', r'\b(sbir|sttr|tacfi|proposal|white paper|solicitation|rfp|rfi|contract|capture)\b'),
    ('business_development', r'\b(outreach|partnership|business development|\bbd\b|customer|lead|pipeline|conference)\b'),
    ('investor_relations', r'\b(investor|series a|fundrais|capital raise|term sheet|valuation|cap table)\b'),
    ('program_management', r'\b(schedule|milestone|program|project plan|gantt|coordinat|sequenc)\b'),
    ('it_automation', r'\b(script|automation|dashboard|database|integration|api|server|it\b|network)\b'),
]


def supa(path, method='GET', body=None):
    req = urllib.request.Request(SUPA + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={'apikey': SUPA_KEY, 'Authorization': 'Bearer ' + SUPA_KEY,
        'Content-Type': 'application/json', 'Prefer': 'return=representation'})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else []


def classify(text):
    t = (text or '').lower()
    for domain, pat in DOMAIN_KEYWORDS:
        if re.search(pat, t):
            return domain
    return None


def pick_member(domain, matrix):
    """Return (email, name, rating, flag) best-matched available member for a domain."""
    members = matrix['members']
    # Phil owns BLK3 flight-hardware domains by assignment (ratings pending)
    hw_domains = {'propulsion', 'structures_tanks', 'avionics_gnc', 'flight_software', 'test_integration_launchops'}
    ranked = []
    for em, m in members.items():
        if m.get('status') == 'pending_ratings':
            # give Phil a proxy score on his assigned hardware domains
            if domain in hw_domains and 'peaton' in em:
                ranked.append((3.5, em, m['name'], 'by-assignment'))
            continue
        r = (m.get('ratings') or {}).get(domain, 0)
        if r <= 0:
            continue
        retiring = 'retir' in (m.get('constraint', '').lower())
        ranked.append((r, em, m['name'], 'retiring' if retiring else ''))
    if not ranked:
        return None
    ranked.sort(key=lambda x: (-x[0], x[3] == 'retiring'))  # rating desc, retiring last
    # Prefer a non-retiring competent (>=3) option over a retiring one
    non_retiring = [x for x in ranked if x[3] != 'retiring' and x[0] >= 3]
    if non_retiring:
        best = non_retiring[0]
        return (best[1], best[2], best[0], best[3])
    best = ranked[0]
    flag = 'successor-needed' if best[3] == 'retiring' else best[3]
    return (best[1], best[2], best[0], flag)


def main():
    matrix = json.load(open(MATRIX))
    tasks = supa("tasks?select=id,title,description,owner,assigned_email,tags,state&state=neq.Done&limit=3000")
    candidates = []
    for t in tasks:
        owner = (t.get('owner') or '').strip().lower()
        tags = set((str(x) or '').lower() for x in (t.get('tags') or []))
        if owner not in ROLE_OWNERS and not (tags & OPT_IN_TAGS):
            continue
        candidates.append(t)

    print(f"{'[DRY] ' if DRY else ''}role/queue tasks needing assignment: {len(candidates)}")
    assigned = 0
    for t in candidates:
        domain = classify((t.get('title') or '') + ' ' + (t.get('description') or ''))
        if not domain:
            print(f"  · #{t['id']} — no clear domain, left for manual: {(t.get('title') or '')[:50]}")
            continue
        pick = pick_member(domain, matrix)
        if not pick:
            print(f"  · #{t['id']} — domain {domain} but no rated member, manual: {(t.get('title') or '')[:50]}")
            continue
        email, name, rating, flag = pick
        flagtxt = f" [{flag}]" if flag else ""
        print(f"  → #{t['id']} [{domain}] -> {name} (rating {rating}){flagtxt}: {(t.get('title') or '')[:45]}")
        if not DRY:
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            supa("tasks?id=eq." + str(t['id']), 'PATCH',
                 {"owner": name, "assigned_to": name, "assigned_email": email, "assigned_at": now})
            os.makedirs(os.path.dirname(LOG), exist_ok=True)
            with open(LOG, 'a') as f:
                f.write(json.dumps({'ts': now, 'task_id': t['id'], 'domain': domain,
                                    'assigned_to': name, 'email': email, 'rating': rating, 'flag': flag}) + '\n')
        assigned += 1
    print(f"\n{'DRY-RUN — ' if DRY else ''}{assigned} task(s) {'would be ' if DRY else ''}auto-assigned.")


if __name__ == '__main__':
    main()
