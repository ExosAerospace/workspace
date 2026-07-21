#!/usr/bin/env python3
"""
research_agent.py — Local Exos research-agent runner.

Replaces the cloud RemoteTriggers that fired daily but never delivered (no
messaging tool, ephemeral sandbox, no access to the real workspace). Runs the
research prompt via the `claude` CLI on the Max plan (web search built in),
then DELIVERS the brief three ways:
  1. Mission Control Research feed  (POST /api/research/ingest — localhost)
  2. Discord channel                (Discord REST API, bot token)
  3. Local archive                  (memory/<date>-research-<name>.md — also
                                     picked up by dashboard-data-generator.py)

Usage: research_agent.py --name grant-scanner [--model sonnet] [--no-discord]
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("research")
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

import os, sys, re, json, argparse, subprocess, urllib.request
from datetime import datetime
import shutil as _sh, glob as _gl, os as _os
_CLAUDE = _sh.which("claude") or next(iter(sorted(_gl.glob(_os.path.expanduser("~/.local/share/mise/installs/node/*/bin/claude")), reverse=True)), "claude")

WORKSPACE = "/Users/exomac/.openclaw/workspace"
CONFIG    = os.path.join(WORKSPACE, "scripts/research_agents.json")
SECRETS   = "/Users/exomac/.openclaw/secrets.json"
MEM_DIR   = os.path.join(WORKSPACE, "memory")
MC_BASE   = "http://127.0.0.1:8080"
MC_TOKEN  = os.path.join(WORKSPACE, "mission-control/data/.decisions-token")
TODAY     = datetime.now().strftime("%Y-%m-%d")

# Governance router (soft). Research auto-files briefs to the feed = execute-path;
# actionable-item escalation is a future feature (briefs already go to Discord).
try:
    sys.path.insert(0, os.path.join(WORKSPACE, "governance"))
    import route as _gov
except Exception:
    _gov = None

def load_json(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def secret(name):
    return load_json(SECRETS, {}).get(name, "")

def mc_token():
    try:
        with open(MC_TOKEN) as f: return f.read().strip()
    except Exception: return ""

def run_claude(prompt, model):
    """Generate the brief via the Claude Code CLI (Max plan, web search enabled)."""
    full = (prompt +
            "\n\nProduce a concise markdown intelligence brief NOW. Begin with a single "
            "'# <title>' line, then use '### ' for each finding/item. Be specific (names, "
            "numbers, links, contacts). Do not ask questions or request confirmation. "
            "If nothing materially new, say so in one line under the title.")
    # Pre-approve only read-only web tools so the headless run never blocks on a
    # permission prompt and can't write/exec on the box.
    p = subprocess.run(
        [_CLAUDE, "-p", "--model", model, "--allowedTools", "WebSearch", "WebFetch"],
        input=full, capture_output=True, text=True, timeout=900)
    out = (p.stdout or "").strip()
    if not out:
        raise RuntimeError(f"empty claude output (stderr: {(p.stderr or '')[:200]})")
    return out

def summarize(md):
    title = None
    highlights = []
    for ln in md.splitlines():
        s = ln.strip()
        if title is None and s.startswith("# "):
            title = s.lstrip("# ").strip(); continue
        if s.startswith("### "):
            highlights.append(s.lstrip("# ").strip())
        elif re.match(r"^[-*]\s+\*\*", s):
            highlights.append(re.sub(r"^[-*]\s+", "", s))
        if len(highlights) >= 12: break
    return (title or f"Research Brief {TODAY}"), highlights[:10]

def deliver_mc(agent, title, highlights, body):
    payload = {
        "id": f"{agent['_name']}-{TODAY}",
        "title": title, "date": TODAY,
        "category": agent.get("category", "Research"),
        "source": agent.get("source", agent["display"]),
        "item_count": body.count("\n### "),
        "highlights": [f"**{h}**" if not h.startswith("**") else h for h in highlights],
        "body": body[:8000],
    }
    try:
        req = urllib.request.Request(MC_BASE + "/api/research/ingest",
            data=json.dumps(payload).encode(),
            headers={"Content-Type":"application/json","x-exo-token":mc_token()}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  MC deliver failed: {e}"); return False

def deliver_discord(agent, title, highlights, body):
    chan = agent.get("discord_channel_id"); tok = secret("discord_token")
    if not chan or not tok:
        print("  Discord: no channel/token, skipped"); return False
    hl = "\n".join(f"• {re.sub(r'\\*\\*','',h)[:180]}" for h in highlights[:6])
    msg = (f"📡 **{agent['display']} — {TODAY}**\n**{title}**\n\n{hl}\n\n"
           f"_Full brief in Mission Control → Research_")
    msg = msg[:1900]
    try:
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{chan}/messages",
            data=json.dumps({"content": msg}).encode(),
            headers={"Content-Type":"application/json","Authorization":f"Bot {tok}"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  Discord deliver failed: {e}"); return False

def archive(agent, md):
    path = os.path.join(MEM_DIR, f"{TODAY}-research-{agent['_name']}.md")
    with open(path, "w") as f: f.write(md)
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--no-discord", action="store_true")
    args = ap.parse_args()

    cfg = load_json(CONFIG, {}).get("agents", {})
    if args.name not in cfg:
        print(f"Unknown agent '{args.name}'. Available: {', '.join(cfg)}"); sys.exit(1)
    agent = cfg[args.name]; agent["_name"] = args.name

    print(f"[{TODAY}] Research agent: {agent['display']} (model {args.model})")
    md = run_claude(agent["prompt"], args.model)
    title, highlights = summarize(md)
    print(f"  brief: '{title}' · {md.count(chr(10)+'### ')} items · {len(md)} chars")

    arc = archive(agent, md);            print(f"  archived: {os.path.relpath(arc, WORKSPACE)}")
    ok_mc = deliver_mc(agent, title, highlights, md);  print(f"  Mission Control: {'OK' if ok_mc else 'FAIL'}")
    if _gov and ok_mc:
        try: _gov.executed("research", f"filed brief to research feed ({args.name})",
                           agent["_name"], items=md.count(chr(10) + "### "))
        except Exception: pass
    ok_dc = False if args.no_discord else deliver_discord(agent, title, highlights, md)
    if not args.no_discord: print(f"  Discord: {'OK' if ok_dc else 'FAIL'}")
    print("done.")

if __name__ == "__main__":
    main()
