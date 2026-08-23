#!/usr/bin/env python3
"""
weekly-rsi.py — Weekly Recursive Self-Improvement (the LEARN layer of the Intelligence Stack).

Runs Sunday night. Audits the CEO Decision Architecture (Mission Score) against reality and
proposes tuning — this is what makes prioritization *recursive*: it learns from what actually
got done and from Jon's manual overrides. Deterministic Python (no LLM) so it can't hit the
claude-cli/toolsAllow trap that silently killed past meta-eval jobs.

Produces each week:
  1. Prioritization accuracy — did the high-scored tasks actually move/close?
  2. Overdue high-value tasks — routed to owner (workload sharing).
  3. Assignment-fit — assignments vs the capability matrix (once surveys land).
  4. Cron health — any automated job failing, incl. the daily-maintenance thrash.
  5. Override signal — where human priority diverges from Mission Score → weight-tuning proposal.
Output: a dated report in reports/, a "Weekly CEO Prioritization Review" Decision for Jon,
and a Discord summary. Read-only on tasks; only appends a report + one Decision + an alert.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, os, re, subprocess, time, hashlib, urllib.request
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from datetime import datetime, timezone, date, timedelta

WS = "/Users/exomac/.openclaw/workspace"
DATA = os.path.join(WS, "mission-control", "data")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
DEC_FILE = os.path.join(DATA, "decisions.json")
SCORES = os.path.join(DATA, "mission-scores.json")
CAPMATRIX = os.path.join(DATA, "capability-matrix.json")
WATCHDOG_LOG = os.path.join(WS, "logs", "cron-watchdog.log")
REPORTS = os.path.join(WS, "reports")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"


def supa_get(path):
    k = json.load(open(SECRETS))["supabase_service_role_key"]
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(
                SUPA + path, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=30).read())
        except Exception:
            if i == 3:
                raise
            time.sleep(2)


def alert(text):
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.15.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", text],
                       capture_output=True, text=True, timeout=60, env=env)
    except Exception:
        pass


def days_since(iso):
    if not iso:
        return None
    try:
        d = datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return None


def main():
    today = date.today()
    week_ago = today - timedelta(days=7)
    tasks = [t for t in supa_get("tasks?select=id,title,state,priority,due_date,owner,assigned_email,"
                                 "source,updated_at,completed_at&limit=5000")
             if t.get("source") != "mc-board-legacy"]
    scores = (json.load(open(SCORES)).get("scores", {})) if os.path.exists(SCORES) else {}
    open_tasks = [t for t in tasks if str(t.get("state", "")).lower() not in ("done", "complete", "completed")]

    def sc(t):
        return (scores.get(str(t["id"])) or {}).get("score", 0)

    # 1) PRIORITIZATION ACCURACY — of the current top-20 by score, how many moved in the last 7 days?
    ranked = sorted(open_tasks, key=sc, reverse=True)
    top20 = ranked[:20]
    moved = [t for t in top20 if (days_since(t.get("updated_at")) is not None and days_since(t.get("updated_at")) <= 7)]
    closed_week = [t for t in tasks if str(t.get("state", "")).lower() in ("done", "complete", "completed")
                   and days_since(t.get("completed_at") or t.get("updated_at")) is not None
                   and days_since(t.get("completed_at") or t.get("updated_at")) <= 7]
    accuracy = round(100 * len(moved) / len(top20)) if top20 else 0

    # 2) OVERDUE HIGH-VALUE — overdue, open, sorted by Mission Score, grouped by owner
    overdue = [t for t in open_tasks if (days_since(t.get("due_date")) or -999) > 0]
    overdue.sort(key=sc, reverse=True)
    by_owner = {}
    for t in overdue:
        by_owner.setdefault(t.get("assigned_email") or t.get("owner") or "unassigned", []).append(t)

    # 3) ASSIGNMENT-FIT — needs the capability matrix (built as surveys return)
    have_matrix = os.path.exists(CAPMATRIX)
    matrix_note = ("capability matrix present — fit-scoring active" if have_matrix
                   else "capability matrix PENDING (surveys due 2026-07-26); fit-scoring will activate once profiles land")

    # 4) CRON HEALTH — surface anything the watchdog flagged recently
    cron_issues = []
    if os.path.exists(WATCHDOG_LOG):
        try:
            lines = open(WATCHDOG_LOG, errors="replace").read().splitlines()[-200:]
            for ln in lines:
                if re.search(r'FAIL|failing|error|no output|silent|stalled', ln, re.I):
                    cron_issues.append(ln[-160:])
        except Exception:
            pass
    cron_issues = cron_issues[-10:]

    # 5) OVERRIDE SIGNAL — where a human-set priority diverges hard from Mission Score
    divergence = []
    for t in open_tasks:
        p = t.get("priority") or 0
        s = sc(t)
        if s and abs(p - s) >= 35:
            divergence.append((t, p, s))
    divergence.sort(key=lambda x: -abs(x[1] - x[2]))
    divergence = divergence[:12]

    # ---- Build the report ----
    stamp = today.isoformat()
    L = []
    L.append(f"# Weekly CEO Prioritization Review — {stamp}\n")
    L.append("_Recursive Self-Improvement (LEARN layer). Mission Score is in SHADOW; this audit tunes it before it goes live._\n")
    # North-Star strategic mix (from mission-scores.json)
    try:
        _sc = json.load(open(SCORES)).get("scores", {})
        from collections import Counter as _C
        _mix = _C(v.get("north_star") for v in _sc.values())
        _tot = sum(_mix.values()) or 1
        _lab = {"series_a": "Series A", "revenue": "Revenue", "part_450": "Part 450", "unaligned": "Ladders to NOTHING"}
        L.append("## 0. Strategic mix (North Star alignment)")
        for _ns in ["series_a", "revenue", "part_450", "unaligned"]:
            L.append(f"- {_lab.get(_ns,_ns)}: {_mix.get(_ns,0)} ({round(100*_mix.get(_ns,0)/_tot)}%)")
        if _mix.get("unaligned", 0) / _tot > 0.15:
            L.append(f"- ⚠️ {_mix.get('unaligned',0)} tasks ladder to no North Star — kill/defer candidates.")
        L.append("")
    except Exception:
        pass
    L.append(f"## 1. Prioritization accuracy\n- Top-20 by Mission Score with activity in the last 7 days: **{len(moved)}/{len(top20)} ({accuracy}%)**")
    L.append(f"- Tasks closed this week: **{len(closed_week)}**")
    if accuracy < 50:
        L.append("- ⚠️ Under half the top-scored work moved — either the score is off or the top items are blocked/mis-owned. See sections 2 & 5.")
    L.append(f"\n## 2. Overdue high-value tasks ({len(overdue)}) — shareable backlog by owner")
    for owner, items in sorted(by_owner.items(), key=lambda kv: -max((sc(t) for t in kv[1]), default=0)):
        L.append(f"\n**{owner}** — {len(items)} overdue")
        for t in items[:6]:
            od = days_since(t.get("due_date"))
            L.append(f"  - ★{sc(t)} · {od}d overdue · #{t['id']} {(t.get('title') or '')[:60]}")
    L.append(f"\n## 3. Assignment-fit\n- {matrix_note}")
    L.append(f"\n## 4. Cron / agent health")
    if cron_issues:
        L.append("- ⚠️ Issues flagged by the watchdog:")
        for c in cron_issues:
            L.append(f"  - `{c}`")
    else:
        L.append("- ✅ No cron failures flagged this week.")
    L.append(f"\n## 5. Override signal → weight-tuning proposal")
    if divergence:
        L.append("Tasks where the human priority and Mission Score disagree most (candidate tuning cases):")
        for t, p, s in divergence:
            L.append(f"  - #{t['id']} human={p} vs score={s} · {(t.get('title') or '')[:55]}")
        L.append("\n**Proposed action:** review 2-3 of these; if the human priority is right, the pillar/urgency weights for that work type get nudged next week. This is the recursive loop.")
    else:
        L.append("- No large divergences — Mission Score is tracking human intent well.")
    # ==== Recursive self-improvement extensions (Jon 2026-08-13): my perf, employee perf,
    # all-programs + consortium coverage, and proactive "where you need me" prompts. Each guarded. ====
    _REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _MCDATA = os.path.dirname(DEC_FILE)
    pursuits = []
    # 6. Exo (AI) performance this week
    try:
        import subprocess as _sp
        commits = _sp.run(["git", "-C", _REPO, "log", "--since=7 days ago", "--oneline"],
                          capture_output=True, text=True, timeout=15).stdout.strip().splitlines()
        L.append("\n## 6. Exo (AI) performance this week")
        L.append(f"- Shipped **{len(commits)} commits** to Mission Control / automation this week.")
        for c in commits[:6]:
            L.append(f"  - {c[:92]}")
        L.append(f"- Tasks closed system-wide this week: **{len(closed_week)}**.")
    except Exception:
        pass
    # 7. Employee performance — throughput this week
    try:
        from collections import Counter as _Counter
        closed_by = _Counter((t.get('assigned_to') or t.get('owner') or 'unassigned') for t in closed_week)
        L.append("\n## 7. Employee performance — tasks closed this week")
        for who, n in closed_by.most_common(10):
            L.append(f"  - {who}: {n}")
        L.append("  (Full detail in the weekly employee report.)")
    except Exception:
        pass
    # 8. Programs & Consortium coverage
    try:
        cj = json.load(open(os.path.join(_MCDATA, 'consortium.json')))
        pursuits = cj.get('pursuits', [])
        L.append(f"\n## 8. Programs & Consortium coverage ({len(pursuits)} pursuits)")
        for pu in pursuits:
            gaps = [m for m in pu.get('members', []) if (m.get('backup') in (None, '', 'TBD', '2-deep TBD'))]
            note = (f"; ⚠️ {len(gaps)} scope(s) need a 2-deep backup" if gaps else "; backups covered")
            L.append(f"  - **{pu.get('name')}** [{pu.get('status')}] — {len(pu.get('members', []))} partners{note}")
    except Exception:
        pass
    # 9. Where Exos needs me — how I can help (proactive)
    try:
        L.append("\n## 9. Where Exos needs me this week — how I can help")
        _help = []
        if overdue:
            _help.append(f"Draft status-nudges for the {len(overdue)} overdue high-value items and route them to owners.")
        if any((m.get('backup') in (None, '', 'TBD', '2-deep TBD')) for pu in pursuits for m in pu.get('members', [])):
            _help.append("Source 2-deep backups for consortium scopes still marked TBD — protects FFP delivery.")
        for pu in pursuits:
            if pu.get('status') in ('Concept', 'Forming'):
                _help.append(f"Draft the teaming agreement + partner outreach for '{pu.get('name')}'.")
        _help.append("Run the consortium lens on this week's new opportunities and propose the 2-3 strongest prime plays.")
        for h in _help[:6]:
            L.append(f"  - {h}")
        L.append("\n_Reply to the Decision card or tell me which to run._")
    except Exception:
        pass

    report = "\n".join(L)

    os.makedirs(REPORTS, exist_ok=True)
    rp = os.path.join(REPORTS, f"weekly-rsi-{stamp}.md")
    open(rp, "w").write(report)

    # ---- Decision card for Jon (human-in-the-loop approval of any tuning) ----
    try:
        arr = json.load(open(DEC_FILE))
        arr = arr if isinstance(arr, list) else arr.get("decisions", [])
    except Exception:
        arr = []
    dedupe = "rsi-" + stamp
    if not any(d.get("dedupeKey") == dedupe for d in arr):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        arr.append({
            "id": "RSI-" + hashlib.sha1(dedupe.encode()).hexdigest()[:6].upper(),
            "created": now, "updated": now, "source": "Weekly RSI",
            "title": f"Weekly CEO Prioritization Review — {stamp}",
            "question": (f"This week: {accuracy}% of top-scored work moved, {len(overdue)} overdue items, "
                         f"{len(divergence)} score-vs-human divergences, "
                         f"{'cron issues flagged' if cron_issues else 'crons healthy'}. "
                         "Approve applying the proposed Mission-Score weight tuning next week?"),
            "context": report[:1800],
            "proposedAction": "Review the full report in reports/ and approve/adjust weight tuning.",
            "type": "yesno", "options": ["Yes — apply proposed tuning", "No — hold weights, I'll adjust"],
            "priority": "medium", "dedupeKey": dedupe, "status": "open",
            "answer": None, "note": "", "answeredAt": None,
            "assignedTo": "jquinn@exosaero.com", "approver": "jquinn@exosaero.com",
        })
        tmp = DEC_FILE + ".tmp"
        json.dump(arr, open(tmp, "w"), indent=2)
        os.replace(tmp, DEC_FILE)

    alert(f"🧠 Weekly RSI review ({stamp}): top-scored work moved {accuracy}% · {len(overdue)} overdue · "
          f"{'⚠️ cron issues' if cron_issues else 'crons OK'} · {len(divergence)} tuning candidates. "
          f"Decision card posted to your inbox; full report reports/weekly-rsi-{stamp}.md")
    print(f"RSI done: accuracy={accuracy}% overdue={len(overdue)} divergence={len(divergence)} cron_issues={len(cron_issues)} -> {rp}")


if __name__ == "__main__":
    main()
