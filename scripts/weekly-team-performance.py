#!/usr/bin/env python3
"""
weekly-team-performance.py — management snapshot of the per-employee Mission Control metrics
(the same data as the /people.html "Team Performance" dashboard), emailed to John Quinn and
DM'd to him on Discord ahead of the weekly leadership meeting.

This is the LEADERSHIP report (whole-team workload for Jon to review), distinct from
weekly-employee-report.py (which nudges each individual). Metrics are computed with the exact
same definitions and name-normalization as the /api/people-metrics endpoint so the email and the
web dashboard always agree.

Run: python3 scripts/weekly-team-performance.py            → email Jon + Discord DM
     python3 scripts/weekly-team-performance.py --preview  → print to stdout, send nothing
     python3 scripts/weekly-team-performance.py --no-discord → email only
Scheduled Mondays (early) via launchd com.exos.weekly-team-performance.
"""

# --- supabase retry/backoff shim ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
try:
    import supabase_util as _sbu; _sbu.install()
except Exception:
    pass
# --- end shim ---

import json, os, sys, subprocess, urllib.request, re
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

WS = "/Users/exomac/.openclaw/workspace"
USERS = os.path.join(WS, "mission-control", "users.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
JON_EMAIL = "jquinn@exosaero.com"
JON_DISCORD = "1501632195163590739"
def _base_url():
    # Use the app's own configured URL (mission-control/.public-url) so the link tracks whatever
    # host MC is currently reachable at (the LAN IP moves via DHCP).
    try:
        u = open(os.path.join(WS, "mission-control", ".public-url")).read().strip()
        if u:
            return u.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:8080"
BASE_URL = _base_url()

PREVIEW = "--preview" in sys.argv
NO_DISCORD = "--no-discord" in sys.argv

ALIAS = {
    'jon': 'John Quinn', 'john quinn': 'John Quinn', 'jquinn': 'John Quinn', 'jon+exo': 'John Quinn', 'j quinn': 'John Quinn', 'quinn': 'John Quinn',
    'lizi quinn': 'Lizi Quinn', 'lquinn': 'Lizi Quinn', 'elizabeth quinn': 'Lizi Quinn', 'lizi': 'Lizi Quinn',
    'neil milburn': 'Neil Milburn', 'neil': 'Neil Milburn', 'nmilburn': 'Neil Milburn',
    'steve norsworthy': 'Steve Norsworthy', 'steven norsworthy': 'Steve Norsworthy', 'snorsworthy': 'Steve Norsworthy', 'steve': 'Steve Norsworthy',
    'phil eaton': 'Phil Eaton', 'phillip eaton': 'Phil Eaton', 'peaton': 'Phil Eaton', 'phil': 'Phil Eaton',
    'kyle ballard': 'Kyle Ballard', 'kballard': 'Kyle Ballard', 'kyle': 'Kyle Ballard',
    'russ blink': 'Russ Blink', 'russell blink': 'Russ Blink', 'rblink': 'Russ Blink', 'russ': 'Russ Blink',
    'mike talley': 'Mike Talley', 'michael talley': 'Mike Talley', 'mtalley': 'Mike Talley', 'mike': 'Mike Talley',
    'toshihisa kumazawa': 'Toshihisa Kumazawa', 'toshi': 'Toshihisa Kumazawa', 'toshihisa': 'Toshihisa Kumazawa',
    'andrew overman': 'Andrew Overman', 'aoverman': 'Andrew Overman',
    'victor castilleja': 'Victor Castilleja', 'vcastilleja': 'Victor Castilleja', 'victor': 'Victor Castilleja',
    'exo': 'Exo (AI)',
}
HUMANS = ['John Quinn', 'Lizi Quinn', 'Neil Milburn', 'Steve Norsworthy', 'Phil Eaton', 'Kyle Ballard',
          'Russ Blink', 'Mike Talley', 'Toshihisa Kumazawa', 'Andrew Overman', 'Victor Castilleja']
ACTIVE = {'To Do', 'In Progress', 'Queued', 'Open'}
_SUFFIX = re.compile(r'\s*\+\s*\d+\s+other[s]?\s*$', re.I)


def canon(raw):
    if not raw:
        return '(unassigned)'
    o = _SUFFIX.sub('', str(raw)).strip()
    return ALIAS.get(o.lower(), o)


def supa(path):
    k = json.load(open(SECRETS))["supabase_service_role_key"]
    out, off = [], 0
    while True:
        sep = '&' if '?' in path else '?'
        url = f"{SB}{path}{sep}limit=1000&offset={off}"
        req = urllib.request.Request(url, headers={"apikey": k, "Authorization": "Bearer " + k})
        chunk = json.loads(urllib.request.urlopen(req, timeout=45).read())
        out += chunk
        if len(chunk) < 1000:
            break
        off += 1000
    return out


def pdate(x):
    if not x:
        return None
    try:
        return datetime.fromisoformat(x.replace('Z', '+00:00'))
    except Exception:
        return None


def compute():
    rows = supa("tasks?select=id,owner,state,priority,due_date,completed_at,assigned_to&order=id")
    now = datetime.now(timezone.utc)
    wk, cut7, cut30 = now + timedelta(days=7), now - timedelta(days=7), now - timedelta(days=30)
    M = {}
    def blank():
        return dict(total=0, open=0, inprog=0, blocked=0, overdue=0, dueweek=0, high=0,
                    nodue=0, done=0, done7=0, done30=0)
    for t in rows:
        p = canon(t.get('owner') or t.get('assigned_to'))
        m = M.setdefault(p, blank())
        m['total'] += 1
        st, pr = t.get('state'), t.get('priority') or 0
        if st in ACTIVE:
            m['open'] += 1
            if st == 'In Progress': m['inprog'] += 1
            if pr >= 80: m['high'] += 1
            dd = pdate(t.get('due_date'))
            if dd:
                if dd < now: m['overdue'] += 1
                elif dd <= wk: m['dueweek'] += 1
            else:
                m['nodue'] += 1
        elif st == 'Done':
            m['done'] += 1
            ca = pdate(t.get('completed_at'))
            if ca and ca >= cut7: m['done7'] += 1
            if ca and ca >= cut30: m['done30'] += 1
    try:
        roster = {u['name'] for u in json.load(open(USERS)) if u.get('active')}
    except Exception:
        roster = set()
    is_human = lambda n: n in HUMANS or n in roster
    emps = sorted([dict(name=n, **M[n]) for n in M if is_human(n)], key=lambda e: -e['open'])
    exo = next((dict(name=n, **M[n]) for n in M if n == 'Exo (AI)'), None)
    others = sorted([dict(name=n, **M[n]) for n in M if not is_human(n) and n != 'Exo (AI)'],
                    key=lambda e: -(e['open'] + e['total']))
    tot = {k: sum(e[k] for e in emps) for k in
           ['total', 'open', 'inprog', 'blocked', 'overdue', 'dueweek', 'high', 'done7', 'done30']}
    return dict(rows=len(rows), emps=emps, exo=exo, others=others, tot=tot, now=now)


def html_report(d):
    tot, now = d['tot'], d['now']
    def rowhtml(e, bold=False):
        st = ' style="font-weight:700;background:#eef4ff"' if bold else ''
        def c(v, warn=False, bad=False, good=False):
            col = '#b45309' if warn else '#b91c1c' if bad else '#15803d' if good else '#111'
            return f'<td style="text-align:right;padding:6px 10px;border-bottom:1px solid #e5e9f0;color:{col}">{v or "·"}</td>'
        share = round(100 * e['open'] / (tot['open'] or 1))
        return ('<tr' + st + '>'
                f'<td style="padding:6px 10px;border-bottom:1px solid #e5e9f0">{e["name"]}</td>'
                + c(e['open']) + c(e['inprog']) + c(e['high'], warn=True) + c(e['overdue'], bad=True)
                + c(e['dueweek'], warn=True) + c(e['done7'], good=True)
                + c(e['total']) + f'<td style="text-align:right;padding:6px 10px;border-bottom:1px solid #e5e9f0;color:#111">{share}%</td>'
                + '</tr>')
    head = ''.join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:2px solid #cbd5e1;font-size:12px;color:#475569">{h}</th>'
                   for h, a in [('Employee', 'left'), ('Open', 'right'), ('In Prog', 'right'), ('High Pri', 'right'),
                                ('Overdue', 'right'), ('Due ≤7d', 'right'),
                                ('Closed 7d', 'right'), ('Total', 'right'), ('Load', 'right')])
    body = ''.join(rowhtml(e) for e in d['emps'])
    totrow = rowhtml({'name': f'Team total ({len(d["emps"])})', 'open': tot['open'], 'inprog': tot['inprog'],
                      'high': tot['high'], 'overdue': tot['overdue'], 'dueweek': tot['dueweek'],
                      'blocked': tot['blocked'], 'done7': tot['done7'], 'total': tot['total']}, bold=True)
    exo = d['exo']
    exohtml = ''
    if exo:
        exohtml = (f'<p style="color:#475569;font-size:13px;margin:14px 0 4px"><b>Exo (AI)</b> — automation workload (shown separately): '
                   f'{exo["open"]} open · {exo["done7"]} closed this week · {exo["total"]} total.</p>')
    others = [o for o in d['others'] if o['open'] > 0]
    othershtml = ''
    if others:
        othershtml = ('<p style="color:#475569;font-size:13px;margin:8px 0"><b>Queues &amp; unrostered owners:</b> '
                      + ' · '.join(f'{o["name"]} ({o["open"]} open)' for o in others) + '</p>')
    return f"""<html><body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#111;max-width:820px">
<h2 style="margin:0 0 2px">Team Performance — weekly snapshot</h2>
<p style="color:#475569;margin:0 0 14px;font-size:13px">Mission Control · {d['rows']:,} tasks · generated {now.astimezone().strftime('%a %b %-d, %Y %-I:%M %p %Z')}</p>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">
  {"".join(f'<div style="border:1px solid #e5e9f0;border-left:4px solid {clr};border-radius:8px;padding:8px 12px"><div style="font-size:20px;font-weight:700">{v}</div><div style="font-size:11px;color:#475569">{l}</div></div>' for v,l,clr in [(tot["open"],"Open across team","#0080ff"),(tot["high"],"High-priority open","#eab308"),(tot["overdue"],"Overdue","#ef4444"),(tot["dueweek"],"Due ≤ 7 days","#eab308"),(tot["done7"],"Closed last 7 days","#22c55e")])}
</div>
<table style="border-collapse:collapse;width:100%;font-size:13px"><thead><tr>{head}</tr></thead>
<tbody>{body}{totrow}</tbody></table>
{exohtml}{othershtml}
<p style="margin:16px 0 4px"><a href="{BASE_URL}/people.html" style="background:#0080ff;color:#fff;padding:8px 14px;border-radius:8px;text-decoration:none;font-size:13px">Open the live dashboard →</a></p>
<p style="color:#94a3b8;font-size:11px;margin-top:14px">Attribution = task owner, normalized across name variants. Open = active states (To Do, In Progress, Queued). High Pri = priority ≥ 80. Closed = completion timestamp in the window. On the dashboard, click any number to open that person's filtered tasks.</p>
</body></html>"""


def text_report(d):
    tot = d['tot']
    lines = [f"TEAM PERFORMANCE — weekly snapshot ({d['rows']:,} tasks)", ""]
    lines.append(f"Team open: {tot['open']} | high-pri: {tot['high']} | overdue: {tot['overdue']} | "
                 f"due<=7d: {tot['dueweek']} | closed 7d: {tot['done7']}")
    lines.append("")
    lines.append(f"{'Employee':20s}{'Open':>6}{'InPr':>6}{'High':>6}{'Ovrd':>6}{'<=7d':>6}{'Cls7':>6}{'Total':>7}")
    for e in d['emps']:
        lines.append(f"{e['name']:20s}{e['open']:6d}{e['inprog']:6d}{e['high']:6d}{e['overdue']:6d}"
                     f"{e['dueweek']:6d}{e['done7']:6d}{e['total']:7d}")
    lines.append(f"{'TEAM TOTAL':20s}{tot['open']:6d}{tot['inprog']:6d}{tot['high']:6d}{tot['overdue']:6d}"
                 f"{tot['dueweek']:6d}{tot['done7']:6d}{tot['total']:7d}")
    lines.append("")
    lines.append(f"Live dashboard: {BASE_URL}/people.html")
    return "\n".join(lines)


def discord_summary(d):
    tot = d['tot']
    top = d['emps'][0] if d['emps'] else None
    lines = ["**📊 Team Performance — weekly snapshot** (for the leadership meeting)",
             f"Team: **{tot['open']} open** · {tot['high']} high-pri · **{tot['overdue']} overdue** · "
             f"{tot['dueweek']} due ≤7d · {tot['done7']} closed this week"]
    if top:
        share = round(100 * top['open'] / (tot['open'] or 1))
        lines.append(f"Heaviest load: **{top['name']}** — {top['open']} open ({share}% of the board), "
                     f"{top['high']} high-pri, {top['overdue']} overdue.")
    lines.append(f"Full table in your inbox · dashboard: <{BASE_URL}/people.html>")
    return "\n".join(lines)


def send_email(subject, html, text):
    m = EmailMessage()
    m["From"] = "Exos Mission Control <jquinnexo@pm.me>"
    m["To"] = JON_EMAIL
    m["Reply-To"] = JON_EMAIL
    m["Subject"] = subject
    m.set_content(text)
    m.add_alternative(html, subtype="html")
    p = subprocess.run(["msmtp", "-a", "protonmail", JON_EMAIL], input=bytes(m), capture_output=True, timeout=60)
    return p.returncode == 0, (p.stderr.decode()[:300] if p.returncode else "")


def send_discord(msg):
    try:
        p = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON_DISCORD, "-m", msg],
                           capture_output=True, timeout=60)
        return p.returncode == 0
    except Exception:
        return False


def main():
    d = compute()
    subject = f"Team Performance — weekly snapshot ({d['now'].astimezone().strftime('%b %-d')})"
    html, text = html_report(d), text_report(d)
    if PREVIEW:
        print(text)
        print("\n[preview] no email/Discord sent. HTML length:", len(html))
        return
    ok, err = send_email(subject, html, text)
    print("email:", "ok" if ok else f"FAIL {err}")
    if not NO_DISCORD:
        dok = send_discord(discord_summary(d))
        print("discord:", "ok" if dok else "FAIL")


if __name__ == "__main__":
    main()
