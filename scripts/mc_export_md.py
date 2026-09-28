#!/usr/bin/env python3
"""
Render exos-mission-control.md and opportunities-tracker.md as LIVE snapshots of
Supabase. The board moved to Supabase (tasks + deals); these flat MD files were
left empty, and every legacy cron that still reads them was starving. This makes
them a read-only mirror of Supabase so those crons get real data with no rewiring.

Source of truth is Supabase — DO NOT hand-edit the MD files; edits are overwritten
on the next run (launchd com.exos.mc-md-export).
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, urllib.request, datetime

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
import os  # supabase secret key loader (exo3 audit fix #1)
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
WS = "/Users/exomac/.openclaw/workspace"
DONE = {"Done", "Completed", "Closed", "Archived"}

def q(path):
    req = urllib.request.Request(f"{SB}/{path}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def parse_d(s):
    if not s: return None
    try: return datetime.date.fromisoformat(s[:10])
    except Exception: return None

def render_mc(today):
    tasks = q("tasks?select=id,title,owner,state,priority,due_date,category,completed_at,updated_at&order=priority.desc&limit=2000")
    if not tasks:
        return None  # never overwrite the board file with an empty/failed Supabase read
    opent = [t for t in tasks if (t.get("state") or "") not in DONE]
    L = [f"# Exos Mission Control (LIVE from Supabase — do not hand-edit)",
         f"_Generated {today:%Y-%m-%d %H:%M} from Supabase tasks. Source of truth = Supabase, NOT this file._",
         "", f"**Open:** {len(opent)} | **Total:** {len(tasks)}", ""]


    td = today.date() if isinstance(today, datetime.datetime) else today
    horizon = td + datetime.timedelta(days=30)
    stale_cut = td - datetime.timedelta(days=45)
    dated = [(parse_d(t.get("due_date")), t) for t in opent if parse_d(t.get("due_date"))]
    near = sorted([(d, t) for d, t in dated if stale_cut <= d <= horizon], key=lambda x: x[0])
    L.append("## Deadlines (next 30 days)")
    for d, t in near[:30]:
        days = (d - td).days
        tag = "OVERDUE " if days < 0 else ""
        L.append(f"- {tag}{d:%b %-d} ({days}d) — #{t['id']} {(t.get('title') or '')[:100]} [{t.get('state')}]")
    if not near: L.append("- (none dated in window)")
    L.append("")

    import collections
    bycat = collections.defaultdict(list)
    for t in opent: bycat[t.get("category") or "Uncategorized"].append(t)
    L.append("## Open items by category")
    for cat, items in sorted(bycat.items(), key=lambda kv: -len(kv[1])):
        L.append(f"### {cat} ({len(items)})")
        for t in sorted(items, key=lambda x: -(x.get("priority") or 0))[:15]:
            L.append(f"- [{t.get('state')}] #{t['id']} {(t.get('title') or '')[:110]}")
        if len(items) > 15: L.append(f"- ...and {len(items)-15} more")
        L.append("")
    return "\n".join(L)

def render_opps(today):
    deals = q("deals?select=id,name,stage,amount,probability,close_date,owner,priority,notes,lost_reason&order=amount.desc.nullslast&limit=1000")
    dead = {"lost", "dead", "closed lost", "abandoned"}
    live = [d for d in deals if (d.get("stage") or "").lower() not in dead]
    L = [f"# Exos Opportunities / Pipeline (LIVE from Supabase — do not hand-edit)",
         f"_Generated {today:%Y-%m-%d %H:%M} from Supabase deals. Source of truth = Supabase, NOT this file._",
         "", f"**Active deals:** {len(live)} | **Total:** {len(deals)}", ""]
    import collections
    bystage = collections.defaultdict(list)
    for d in live: bystage[d.get("stage") or "Unstaged"].append(d)
    for stage, items in sorted(bystage.items(), key=lambda kv: -sum((x.get("amount") or 0) for x in kv[1])):
        tot = sum((x.get("amount") or 0) for x in items)
        L.append(f"## {stage} ({len(items)}" + (f", ${tot:,.0f}" if tot else "") + ")")
        for d in sorted(items, key=lambda x: -((x.get("amount") or 0))):
            amt = f"${d['amount']:,.0f}" if d.get("amount") else "TBD"
            nxt = (d.get("notes") or "").strip().replace("\n", " ")[:120]
            L.append(f"- #{d['id']} {(d.get('name') or '')[:80]} — {amt}" + (f" — {nxt}" if nxt else ""))
        L.append("")
    return "\n".join(L)

def main():
    today = datetime.datetime.now()
    md = render_mc(today)
    if md and len(md) > 300:
        open(f"{WS}/exos-mission-control.md", "w").write(md)
        print(f"{today:%Y-%m-%d %H:%M} exported exos-mission-control.md from Supabase tasks")
    else:
        print(f"{today:%Y-%m-%d %H:%M} SKIPPED write: tasks read empty/short — leaving existing file intact")
    # NOTE: DO NOT mirror opportunities-tracker.md here. That file is a GENERATION SOURCE
    # (dashboard-data-generator.py -> opportunities.json -> Supabase deals mirror). Overwriting it
    # from the deals table clobbered the pipeline on 2026-07-13. This exporter owns ONLY exos-mission-control.md.

if __name__ == "__main__":
    main()
