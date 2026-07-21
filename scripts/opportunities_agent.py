#!/usr/bin/env python3
"""
opportunities_agent.py — Continuous demand-generation agent for the AI Mission Desk.

Runs daily. Sources NEW prospects + solicitations that can fill the Opportunities
pipeline (Mission Control → Opportunities), enriches each (POC, value, fit, next
action), and writes them into opportunities-tracker.md as OPP-/BD- blocks. Then it
regenerates the dashboard JSON and posts a summary to Discord.

DRAFT-ONLY by policy: this agent NEVER sends external email. It stages opportunities
+ drafts into the pipeline for a human (Lizi/Jon) to send. New high-value items that
need a human go/no-go are pushed to the Decisions inbox.

This is the "Capture" + "Qualify/Score" front end of the program.html pipeline; the
rate card (pricing/rate-card.json) is the "Quote" brain it prices against.

Usage: opportunities_agent.py [--lane payload|broad] [--model sonnet] [--dry-run] [--no-discord]
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("opportunities")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
except Exception:
    pass
# --- /governance ---

import os, sys, re, json, argparse, subprocess, urllib.request
from datetime import datetime
import shutil as _sh, glob as _gl, os as _os
_CLAUDE = _sh.which("claude") or next(iter(sorted(_gl.glob(_os.path.expanduser("~/.local/share/mise/installs/node/*/bin/claude")), reverse=True)), "claude")

WORKSPACE = "/Users/exomac/.openclaw/workspace"
SECRETS   = "/Users/exomac/.openclaw/secrets.json"
OPP_MD    = os.path.join(WORKSPACE, "opportunities-tracker.md")
RATE_CARD = os.path.join(WORKSPACE, "pricing/rate-card.json")
GENERATOR = os.path.join(WORKSPACE, "scripts/dashboard-data-generator.py")
MC_BASE   = "http://127.0.0.1:8080"
MC_TOKEN  = os.path.join(WORKSPACE, "mission-control/data/.decisions-token")
DISCORD_CHANNEL = "1501636671492460554"   # #blk3-payload
TODAY     = datetime.now().strftime("%Y-%m-%d")

LANES = {
    "payload": {
        "display": "BLK3 Payload Demand Engine",
        "prompt": (
            "You are the demand-generation agent for Exos Aerospace (Greenville, TX; CEO John Quinn). "
            "Exos is one of only three FAA-licensed reusable rocket launch providers in the US, and the only one "
            "currently SELLING suborbital payload capacity. We are filling SPACEavailable(TM) — the 135kg / 25\"x36\" "
            "bay on BLK3 Flight 2 (~Mar-Apr 2027, Spaceport America), flying days after a fully-manifested Flight 1. "
            "Published rate card: $7,500/kg; Full bay $1,012,500, Half $510,000, Quarter $255,000; cubesat 1U $7,500 "
            "up to 6U $45,000; add-ons (live telemetry $25k, precision pointing $5k, etc).\n\n"
            "Find NEW payload BUYERS we are not already pursuing. Use web search across: NASA Flight Opportunities / "
            "TechFlights PIs; university propulsion, microgravity, materials & bio labs with active flight-relevant "
            "research and funding; commercial flight-qualification startups (in-space propulsion, cryo/CFM, avionics, "
            "sensors, ADCS, deployables); microgravity science/materials/bio (Redwire, Varda, Space Forge, pharma); "
            "brokers/aggregators (SpaceTango, Voyager); international/education suborbital research groups. "
            "Exclude anyone already in our pipeline (SwRI, Space Port Australia, Innovation First, SpaceTango, Purdue, "
            "Texas A&M, Redwire, AFRL/SpaceWERX).\n\n"
            "For EACH new prospect: a named POC (best-guess email + title), the segment, why BLK3 fits, an estimated "
            "deal value priced off the rate card, their funding source, and the single best next action. Prioritize "
            "fit + reachability + funding."
        ),
    },
    "broad": {
        "display": "Exos Opportunity Engine",
        "prompt": (
            "You are the opportunity-sourcing agent for Exos Aerospace (Greenville, TX; CEO John Quinn). Exos: "
            "one of only three FAA-licensed reusable suborbital launch providers in the US; flight-test platform that "
            "de-risks orbital programs; RDRE flight-test role; Scorpius Type-5 cryo tank heritage (lunar). "
            "Series A up to $25M open.\n\n"
            "Find NEW opportunities to fill the Mission Control pipeline across ALL vectors: government solicitations "
            "(SAM.gov, SBIR/STTR, SpaceWERX/AFWERX/DIU, NASA NSPIRES), commercial partnerships, payload customers, "
            "wet-lease prospects, strategic/technical collaborations, and warm investor leads. Exclude items already "
            "in our pipeline. For each: agency/company, solicitation # or contact, deadline, estimated value, why it "
            "fits Exos, direct link, and a named POC. Prioritize near-term deadlines and high fit."
        ),
    },
}

def load_json(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def secret(name): return load_json(SECRETS, {}).get(name, "")

def mc_token():
    try:
        with open(MC_TOKEN) as f: return f.read().strip()
    except Exception: return ""

def run_claude(prompt, model):
    rate = json.dumps(load_json(RATE_CARD, {}))
    full = (prompt +
        "\n\nRate card (price every opportunity off this):\n" + rate +
        "\n\nOutput ONLY a fenced ```json block containing an array of up to 8 NEW opportunity objects, each with: "
        "title, segment, type (Payload Sale | Gov Solicitation | Partnership | Investor | Other), value (string, "
        "priced off the rate card where relevant), due (string or ''), poc (name + best-guess email + title), "
        "why_fit (1 sentence), next_action (1 sentence, NEVER 'send email externally' — staging only), source_url. "
        "No prose outside the json block. If nothing materially new, return an empty array [].")
    p = subprocess.run(
        [_CLAUDE, "-p", "--model", model, "--allowedTools", "WebSearch", "WebFetch"],
        input=full, capture_output=True, text=True, timeout=900)
    out = (p.stdout or "").strip()
    if not out:
        raise RuntimeError(f"empty claude output (stderr: {(p.stderr or '')[:200]})")
    return out

def parse_items(raw):
    m = re.search(r"```json\s*(.*?)```", raw, re.DOTALL)
    blob = m.group(1).strip() if m else raw.strip()
    # tolerate a leading/trailing array
    s = blob.find("["); e = blob.rfind("]")
    if s != -1 and e != -1: blob = blob[s:e+1]
    try:
        items = json.loads(blob)
        return items if isinstance(items, list) else []
    except Exception as ex:
        print(f"  parse failed: {ex}"); return []

def next_opp_id(md):
    nums = [int(n) for n in re.findall(r"^### (?:\S+\s)?OPP-(\d+)", md, re.MULTILINE)]
    start = (max(nums) + 1) if nums else 1
    return start

def render_block(opp_id, it):
    g = lambda k: str(it.get(k, "") or "").strip()
    return (
        f"\n### OPP-{opp_id:03d} | {g('title')}\n"
        f"**Status:** NEW — auto-sourced {TODAY} (Opportunities Engine)\n"
        f"**Type:** {g('type') or 'Other'}\n"
        f"**Segment:** {g('segment')}\n"
        f"**Value:** {g('value') or 'TBD (price off rate card)'}\n"
        f"**Due:** {g('due') or 'Rolling'}\n"
        f"**POC:** {g('poc')}\n"
        f"**Why fit:** {g('why_fit')}\n"
        f"**Next action:** {g('next_action')}\n"
        f"**Source:** {g('source_url')}\n"
    )

def append_opps(items):
    with open(OPP_MD) as f: md = f.read()
    start = next_opp_id(md)
    blocks, ids = [], []
    for k, it in enumerate(items):
        oid = start + k
        blocks.append(render_block(oid, it)); ids.append(f"OPP-{oid:03d}")
    section = f"\n\n## AUTO-SOURCED — {TODAY} (Opportunities Engine)\n" + "".join(blocks)
    with open(OPP_MD, "a") as f: f.write(section)
    return ids

def regenerate():
    try:
        subprocess.run(["python3", GENERATOR], capture_output=True, text=True, timeout=120)
        return True
    except Exception as e:
        print(f"  generator failed: {e}"); return False

def deliver_discord(lane, items, ids):
    tok = secret("discord_token")
    if not tok: print("  Discord: no token"); return False
    lines = []
    for it, oid in zip(items, ids):
        lines.append(f"• **{oid}** {str(it.get('title',''))[:80]} — {str(it.get('value','TBD'))[:24]}")
    body = "\n".join(lines[:10]) or "_No new opportunities this run._"
    msg = (f"🛰️ **{LANES[lane]['display']} — {TODAY}**\n"
           f"{len(ids)} new opportunit{'y' if len(ids)==1 else 'ies'} staged → Mission Control / Opportunities\n\n"
           f"{body}\n\n_Draft-only. Review + send in Mission Control._")[:1900]
    try:
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL}/messages",
            data=json.dumps({"content": msg}).encode(),
            headers={"Content-Type":"application/json","Authorization":f"Bot {tok}"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  Discord failed: {e}"); return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", default="payload", choices=list(LANES))
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-discord", action="store_true")
    args = ap.parse_args()

    print(f"[{TODAY}] Opportunities agent · lane={args.lane} · model={args.model}")
    raw = run_claude(LANES[args.lane]["prompt"], args.model)
    items = parse_items(raw)
    print(f"  sourced {len(items)} candidate opportunities")
    if args.dry_run:
        print(json.dumps(items, indent=2)[:2000]); return
    if not items:
        if not args.no_discord: deliver_discord(args.lane, [], [])
        print("  nothing new."); return
    ids = append_opps(items);   print(f"  staged: {', '.join(ids)}")
    ok = regenerate();          print(f"  dashboard regenerate: {'OK' if ok else 'FAIL'}")
    if not args.no_discord:
        print(f"  Discord: {'OK' if deliver_discord(args.lane, items, ids) else 'FAIL'}")
    try:
        _gevent(_GRUN, "executed", detail=f"{len(ids)} opps staged ({args.lane})")
    except Exception: pass
    print("done.")

if __name__ == "__main__":
    main()
