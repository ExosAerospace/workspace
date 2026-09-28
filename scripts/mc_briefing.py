#!/usr/bin/env python3
"""
Deterministic Mission Control briefing generator.
Reads the LIVE Supabase board (not stale files, not web search) and prints a
grounded briefing: open blockers, near-term deadlines, recent completions.

Root-cause fix (2026-07-08): the LLM briefing crons run sandboxed and cannot
reach localhost/files, so they fell back to Google and resurfaced closed/past
items. This script queries Supabase REST directly on the host and only reports
LIVE, non-Done state.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, urllib.request, urllib.parse, datetime, sys
from exos_capability_gate import is_aligned, filter_new_aligned, escalate

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
import os  # supabase secret key loader (exo3 audit fix #1)
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
DONE = {"Done", "Completed", "Closed", "Archived"}
HORIZON_DAYS = 14

def q(path):
    req = urllib.request.Request(
        f"{SB}/{path}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def parse_due(s):
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s[:10])
    except Exception:
        return None

def sam_open_solicitations(today):
    """Deterministic gov-opportunity feed. Queries SAM.gov and keeps ONLY items
    whose responseDeadLine is today or later. Structurally cannot surface closed
    solicitations — this is the reliable replacement for the LLM web-dredgers
    that leaked expired grants."""
    try:
        key = json.load(open("/Users/exomac/.openclaw/secrets.json")).get("sam_api_key")
    except Exception:
        return []
    if not key:
        return []
    frm = (today - datetime.timedelta(days=90)).strftime("%m/%d/%Y")
    to = today.strftime("%m/%d/%Y")
    terms = ["reusable launch", "suborbital", "spaceport", "rotating detonation",
             "responsive space launch", "launch services", "launch site"]
    # Use title= (targeted title-substring match), NOT q=. Verified live 2026-08-19:
    # &q=<term> returns ~30-38k loosely/unmatched records (mowers, rifle clips) incl.
    # Award Notices; &title=<term> actually filters on the title. ptype restricts to
    # solicitation-type notices (o=Solicitation, p=Presol, k=Combined, r=Sources Sought),
    # excluding Award Notices/Justifications.
    queries = ["&title=" + urllib.parse.quote(t) for t in terms]
    queries += ["&ncode=336414"]  # NAICS: Guided Missile & Space Vehicle Manufacturing
    seen = {}
    for qp in queries:
        url = ("https://api.sam.gov/opportunities/v2/search?api_key=" + key +
               qp + "&ptype=o,p,k,r&postedFrom=" + frm + "&postedTo=" + to + "&limit=50")
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=20) as r:
                data = json.load(r)
        except Exception:
            continue
        # Capability gate lives in the shared module (exos_capability_gate) so relevance
        # is defined ONCE and reused by every scan — no per-cron copy-paste to drift.
        for o in (data.get("opportunitiesData") or []):
            dl = o.get("responseDeadLine")
            title = (o.get("title") or "")
            if not dl:
                continue
            if not is_aligned(title):
                continue
            try:
                d = datetime.date.fromisoformat(dl[:10])
            except Exception:
                continue
            if d >= today:
                seen[o.get("noticeId")] = (d, title, o.get("uiLink"))
    return sorted(seen.values(), key=lambda x: x[0])

def main():
    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=HORIZON_DAYS)
    tasks = q("tasks?select=id,title,owner,state,priority,due_date,category,completed_at,updated_at&order=priority.desc&limit=1000")

    open_tasks = [t for t in tasks if (t.get("state") or "") not in DONE]

    stale_cut = today - datetime.timedelta(days=30)
    dated = []       # actionable: due within last 30d .. +horizon
    stale = []       # aged overdue (>30d) — pollution, needs cleanup
    for t in open_tasks:
        d = parse_due(t.get("due_date"))
        if not d:
            continue
        if d < stale_cut:
            stale.append((d, t))
        elif d <= horizon:
            dated.append((d, t))
    dated.sort(key=lambda x: x[0])

    # recent completions (last 3 days) for "accomplishments"
    recent = []
    cutoff = today - datetime.timedelta(days=3)
    for t in tasks:
        if (t.get("state") or "") in DONE:
            c = parse_due(t.get("completed_at") or t.get("updated_at"))
            if c and c >= cutoff:
                recent.append((c, t))
    recent.sort(key=lambda x: x[0], reverse=True)

    L = []
    L.append(f"📋 Mission Control Briefing — {today:%A, %B %-d, %Y} (live Supabase board)")
    L.append(f"Open: {len(open_tasks)} | Due ≤{HORIZON_DAYS}d: {len(dated)}")
    L.append("")

    L.append("🔴 DEADLINES (next 14 days)")
    if dated:
        for d, t in dated[:15]:
            days = (d - today).days
            when = "TODAY" if days == 0 else ("TOMORROW" if days == 1 else f"{days}d ({d:%b %-d})")
            flag = "⚠️OVERDUE " if days < 0 else ""
            L.append(f"  • {flag}{when} — {(t.get('title') or '')[:88]} [{t.get('state')}]")
    else:
        L.append("  (none dated in window)")
    if stale:
        L.append(f"  … plus {len(stale)} aged tasks overdue >30d (stale — need close/re-date, not real deadlines)")
    L.append("")

    if recent:
        L.append("✅ CLOSED in last 3 days")
        for c, t in recent[:8]:
            L.append(f"  • {(t.get('title') or '')[:90]}")
        L.append("")

    sam = sam_open_solicitations(today)
    if sam:
        # escalate genuinely-new aligned solicitations to the monthly report + shared
        # dedup ledger, so no other scan re-reports them and they land in the record.
        items = [{"title": title, "due": f"{d:%Y-%m-%d}", "link": link} for d, title, link in sam]
        new_aligned = filter_new_aligned(items, source="mc_briefing/SAM")
        escalate(new_aligned, source="mc_briefing/SAM")
        L.append("🛰️ OPEN GOV SOLICITATIONS (SAM.gov — Exos-capability-gated, open only)")
        for d, title, link in sam[:8]:
            days = (d - today).days
            L.append(f"  • due {d:%b %-d} ({days}d) — {(title or '')[:82]}")
        if new_aligned:
            L.append(f"  ↑ {len(new_aligned)} new escalated to reports/aligned-opportunities-{today:%Y-%m}.md")
        L.append("")

    L.append("Source: live board (non-Done) + SAM.gov open solicitations. No web-dredged/closed items.")
    print("\n".join(L))

if __name__ == "__main__":
    main()
