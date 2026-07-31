#!/usr/bin/env python3
"""
derisk_orbital_outreach.py — The "De-Risk Orbital" outreach engine.

A standing, account-based demand engine that operationalizes Exos's core thesis:
the FAA-licensed reusable SUBORBITAL test platform that de-risks ORBITAL programs.
Runs daily. Sources targets across three pools, enriches each (named POC, program,
funding, why-fit), prices off the rate card, and stages them into the Opportunities
tracker so the existing Opportunity Processor (06:15 / 18:15) drafts the outreach
and gates each send to Decisions. NOTHING auto-sends — draft-only to Jon.

Three pools (config: all three in parallel each run):
  A  Suborbital repeat-fliers   — flown payloads before (New Shepard, Virgin Galactic,
     UP Aerospace SpaceLoft, NASA sounding rockets, Masten heritage). Warmest.
  B  Orbital launch developers   — message = LAUNCHER RISK MITIGATION (fly avionics/
     GNC/TPS/stage-sep/engine components/recovery suborbital before betting a vehicle).
  C  Orbital sat/payload devs     — message = TRL ADVANCEMENT / flight qualification
     before an expensive orbital ride.

Lead CTA (config): the open BLK3 Flight 2 bay slot, ~Mar-2027, Spaceport America.

COUNTRY POLICY (Jon's standing policy 2026-07-31, via export_screen.classify_country):
marketing our services to the world is the job, and being outside the US is not being
an enemy. Adversary / embargoed nations (China, Russia, Belarus, North Korea, Iran,
Cuba, Syria, Venezuela, Myanmar, Nicaragua) are dropped silently — no outreach, no
draft, no decision, no ask. Everyone else, US + allies (Germany, Italy, France, etc.)
+ neutral nations, is cleared for marketing outreach and flows straight to the
processor for pricing + draft. NO per-target export decision is filed for outreach.
This governs MARKETING only; any controlled technical-data transfer stays gated by the
separate ITAR data-transfer process, and inbound controlled content by itar_ear_screen.

Usage: derisk_orbital_outreach.py [--model sonnet] [--limit 9] [--dry-run] [--no-discord]
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("derisk-orbital")
    _gevent(_GRUN, "start")
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
except Exception:
    _GRUN = None
    def _gevent(*a, **k): pass
# --- /governance ---

import os, re, json, argparse, subprocess, urllib.request, hashlib
from datetime import datetime
import shutil as _sh, glob as _gl, os as _os
_CLAUDE = _sh.which("claude") or next(iter(sorted(_gl.glob(_os.path.expanduser("~/.local/share/mise/installs/node/*/bin/claude")), reverse=True)), "claude")

WORKSPACE = "/Users/exomac/.openclaw/workspace"
SECRETS   = "/Users/exomac/.openclaw/secrets.json"
OPP_MD    = os.path.join(WORKSPACE, "opportunities-tracker.md")
OPP_JSON  = os.path.join(WORKSPACE, "mission-control/data/opportunities.json")
RATE_CARD = os.path.join(WORKSPACE, "pricing/rate-card.json")
GENERATOR = os.path.join(WORKSPACE, "scripts/dashboard-data-generator.py")
MC_BASE   = "http://127.0.0.1:8080"
MC_TOKEN  = os.path.join(WORKSPACE, "mission-control/data/.decisions-token")
DISCORD_CHANNEL = "1501636671492460554"   # #blk3-payload
TODAY     = datetime.now().strftime("%Y-%m-%d")

BEGIN = "<!-- DERISK-ORBITAL-AUTO:BEGIN (managed by derisk_orbital_outreach.py) -->"
END   = "<!-- DERISK-ORBITAL-AUTO:END -->"

# Anything not clearly US-domestic gets the ITAR gate (fail-safe toward screening).
US_TOKENS = ("us", "usa", "u.s.", "u.s.a.", "united states", "united states of america", "america", "domestic")

# Country policy for outbound marketing outreach (Jon's standing policy 2026-07-31):
# block adversary/embargoed nations silently, clear allies + neutral nations with
# no decision. Centralized in export_screen so every outreach engine screens the same.
import os as _os2, sys as _sys2
_sys2.path.insert(0, _os2.path.dirname(_os2.path.abspath(__file__)))
from export_screen import classify_country

POOLS = """POOL A — SUBORBITAL REPEAT-FLIERS (warmest; they already buy suborbital):
  Organizations/PIs that have ALREADY flown a payload suborbitally — Blue Origin New
  Shepard payload customers, Virgin Galactic research-flight payloads, UP Aerospace
  SpaceLoft customers, NASA Sounding Rocket Program PIs (Wallops/WFF), past Masten /
  Exos SARGE fliers, parabolic-to-suborbital researchers. Message: a REUSABLE,
  FAA-licensed platform with 2-3 day turnaround and recover-and-refly.

POOL B — ORBITAL LAUNCH DEVELOPERS (highest-value; risk mitigation):
  Companies building an orbital launch vehicle — e.g. Stoke Space, Relativity, Firefly,
  ABL, Rocket Lab (Neutron), Phantom Space, Vaya Space, Gilmour, Isar, RFA, Orbex,
  Skyrora, iRocket, Aevum, and similar worldwide. Message: LAUNCHER RISK MITIGATION —
  flight-test your avionics, GNC, TPS, stage-separation, engine components, and recovery
  systems on a cheap reusable suborbital hop BEFORE betting an orbital vehicle on them.

POOL C — ORBITAL SATELLITE / PAYLOAD DEVELOPERS (biggest TAM; TRL advancement):
  Builders of orbital hardware needing flight heritage — sensors/instruments, ADCS/star
  trackers, in-space propulsion (electric/cryo/CFM), optics, deployables, novel materials,
  RF payloads, SDA-tranche vendors, defense space primes' components. Message: TRL
  ADVANCEMENT / flight qualification before committing to an expensive orbital ride."""

PROMPT = (
    "You are the De-Risk Orbital outreach-sourcing agent for Exos Aerospace "
    "(Greenville, TX; CEO John Quinn). Exos is one of only three FAA-licensed reusable "
    "rocket launch providers in the US and the only one currently SELLING suborbital "
    "payload capacity. Core thesis: Exos is the reusable SUBORBITAL test platform that "
    "DE-RISKS ORBITAL programs — it is NOT an orbital launch competitor.\n\n"
    "LEAD OFFER for every target: the open SPACEavailable(TM) bay on BLK3 Flight 2 "
    "(~Mar-2027, Spaceport America) — 135kg / 25\"x36\", reusable, 2-3 day turnaround, "
    "hardware recovered and returned. Tie each target's specific program to that slot.\n\n"
    "Source NEW targets across ALL THREE pools below (rotate, return a mix of all three). "
    "Search globally — include international launch and satellite developers. "
    "EXCLUDE targets based in adversary or embargoed nations (China, Russia, Belarus, "
    "North Korea, Iran, Cuba, Syria, Venezuela, Myanmar, Nicaragua); we do not market to them.\n\n"
    + POOLS +
    "\n\nFor EACH target return: org (company/lab), pool ('A'|'B'|'C'), country (the org's "
    "home country — be precise, this drives export screening), a named POC with title and "
    "best-guess email, the specific program/hardware that needs flight data, the funding "
    "source that could pay for a flight, why BLK3 fits in ONE sentence tied to risk "
    "mitigation or TRL advancement, an estimated deal value priced off the rate card, the "
    "single best next action (staging only — NEVER 'send email externally'), and a source URL. "
    "Exclude anyone already in our pipeline (SwRI, Space Port Australia, Innovation First, "
    "SpaceTango, Purdue, Texas A&M, Redwire, AFRL/SpaceWERX). Prioritize fit + reachability + funding."
)


def load_json(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def secret(name): return load_json(SECRETS, {}).get(name, "")

def mc_token():
    try:
        with open(MC_TOKEN) as f: return f.read().strip()
    except Exception: return ""

def mc_post(path, payload):
    try:
        req = urllib.request.Request(MC_BASE + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "x-exo-token": mc_token()},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  ! MC post {path} failed: {e}"); return False


def run_claude(model, limit):
    rate = json.dumps(load_json(RATE_CARD, {}))
    full = (PROMPT +
        "\n\nRate card (price every target off this):\n" + rate +
        f"\n\nOutput ONLY a fenced ```json block containing an array of up to {limit} NEW target "
        "objects with keys: org, pool, country, poc_name, poc_title, poc_email, program, funding, "
        "why_fit, value, next_action, source_url. No prose outside the json block. "
        "If nothing materially new, return [].")
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
    s = blob.find("["); e = blob.rfind("]")
    if s != -1 and e != -1: blob = blob[s:e+1]
    try:
        items = json.loads(blob)
        return items if isinstance(items, list) else []
    except Exception as ex:
        print(f"  parse failed: {ex}"); return []


def norm_key(name):
    base = re.split(r"[(/—–,-]", str(name))[0]
    words = re.sub(r"[^a-z0-9 ]", "", base.lower()).split()
    if not words: return str(name).lower().strip()
    if words[0] in ("space", "texas", "new", "los", "san", "blue", "rocket"):
        return " ".join(words[:2])
    return words[0]

def dro_id(key):
    n = int(hashlib.md5(("dro" + key).encode()).hexdigest(), 16) % 9000 + 1000
    return f"DRO-{n}"

def is_foreign(country):
    c = str(country or "").strip().lower()
    if not c:
        return True   # unknown origin → screen it
    return not any(tok == c or tok in c.split() or c.startswith(tok) for tok in US_TOKENS)


def existing_keys():
    """Org tokens already represented in the tracker (any prefix) — don't re-pitch."""
    keys = set()
    try:
        md = open(OPP_MD).read()
        for title in re.findall(r"^###\s+\S+\s*\|\s*(.+)$", md, re.MULTILINE):
            keys.add(norm_key(title))
    except Exception:
        pass
    # hard exclusions from the active pipeline
    for n in ("swri", "space port", "innovation", "spacetango", "purdue", "texas", "redwire", "afrl"):
        keys.add(n)
    return keys


POOL_LABEL = {"A": "Suborbital repeat-flier", "B": "Orbital launch developer (risk mitigation)",
              "C": "Orbital sat/payload developer (TRL advancement)"}

def render_block(oid, it, foreign):
    g = lambda k: str(it.get(k, "") or "").strip()
    pool = (g("pool") or "B").upper()[:1]
    poc = ", ".join(x for x in [g("poc_name"), g("poc_title"), g("poc_email")] if x)
    status = (f"NEW — DRO sourced {TODAY}; lead w/ open BLK3 Mar-2027 slot"
              + (" · international target: marketing outreach only, controlled technical-data transfer stays ITAR-gated"
                 if foreign else ""))
    desc = (f"De-Risk Orbital target ({POOL_LABEL.get(pool,'orbital')}). {g('why_fit')} "
            f"Program: {g('program')}. Funding: {g('funding')}.")
    return (
        f"\n### {oid} | {g('org')}\n"
        f"**Status:** {status}\n"
        f"**Type:** De-Risk Orbital Outreach (Pool {pool})\n"
        f"**Segment:** {POOL_LABEL.get(pool, 'Orbital')}\n"
        f"**Country:** {g('country') or 'unknown'}\n"
        f"**Value:** {g('value') or '$1,012,500 (full-bay list; final quote priced off rate card)'}\n"
        f"**Due:** BLK3 Flight 2 — March 2027\n"
        f"**POC:** {poc or 'TBD — enrich'}\n"
        f"**Why fit:** {g('why_fit')}\n"
        f"**Next action:** {g('next_action') or 'Price off rate card; draft Mar-2027 slot outreach for Jon to approve.'}\n"
        f"**Source:** {g('source_url')}\n"
        f"_desc: {desc[:220]}_\n"
    )


def regenerate():
    try:
        r = subprocess.run(["python3", GENERATOR], capture_output=True, text=True, timeout=120)
        return r.returncode == 0
    except Exception as e:
        print(f"  generator failed: {e}"); return False


def deliver_discord(staged, blocked_n):
    tok = secret("discord_token")
    if not tok: print("  Discord: no token"); return False
    by = {"A": 0, "B": 0, "C": 0}
    lines = []
    for oid, it, foreign in staged:
        p = str(it.get("pool", "B")).upper()[:1]
        by[p] = by.get(p, 0) + 1
        flag = " 🌍intl" if foreign else ""
        lines.append(f"• **{oid}** {str(it.get('org',''))[:60]} — Pool {p}{flag}")
    body = "\n".join(lines[:12]) or "_No new targets this run._"
    msg = (f"🚀 **De-Risk Orbital Outreach — {TODAY}**\n"
           f"{len(staged)} new target{'s' if len(staged)!=1 else ''} staged → Opportunities "
           f"(A:{by['A']} repeat-fliers · B:{by['B']} launch devs · C:{by['C']} sat/payload)\n"
           f"{blocked_n} blocked (adversary/embargoed, no outreach).\n\n"
           f"{body}\n\n_Draft-only. Processor prices + drafts; you approve every send in Decisions._")[:1900]
    try:
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL}/messages",
            data=json.dumps({"content": msg}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bot {tok}"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  Discord failed: {e}"); return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--limit", type=int, default=9)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-discord", action="store_true")
    args = ap.parse_args()

    print(f"[{TODAY}] De-Risk Orbital engine · model={args.model} · limit={args.limit}")
    raw = run_claude(args.model, args.limit)
    items = parse_items(raw)
    print(f"  sourced {len(items)} candidate targets")

    existing = existing_keys()
    staged, seen, blocked = [], set(), []
    for it in items:
        org = str(it.get("org", "")).strip()
        if not org:
            continue
        key = norm_key(org)
        if key in seen or key in existing:
            continue
        seen.add(key)
        verdict, reason = classify_country(it.get("country"))
        if verdict == "block":
            # Adversary/embargoed nation: no outreach, no draft, no decision, no ask.
            blocked.append((org, it.get("country", "?")))
            continue
        foreign = is_foreign(it.get("country"))
        staged.append((dro_id(key), it, foreign))

    if blocked:
        print(f"  blocked {len(blocked)} adversary/embargoed (no outreach): "
              + ", ".join(f"{o} [{c}]" for o, c in blocked[:8]))

    if args.dry_run:
        print(f"  [dry-run] {len(staged)} would stage, {len(blocked)} blocked:")
        for oid, it, foreign in staged:
            print(f"    {oid}  P{str(it.get('pool','?')).upper()[:1]}  "
                  f"{'🌍' if foreign else '  '} {str(it.get('org',''))[:50]:50} [{it.get('country','?')}]")
        return

    if not staged:
        if not args.no_discord: deliver_discord([], 0)
        print("  nothing new."); return

    # write managed section (idempotent: replace prior DRO auto-section)
    section = (BEGIN + f"\n\n## DE-RISK ORBITAL — auto-sourced {TODAY}\n"
               + "".join(render_block(oid, it, f) for oid, it, f in staged) + "\n" + END + "\n")
    cur = open(OPP_MD).read()
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    cur = pattern.sub("", cur) if pattern.search(cur) else cur
    open(OPP_MD, "w").write(cur.rstrip() + "\n\n" + section)
    print(f"  staged {len(staged)} targets: " + ", ".join(oid for oid, _, _ in staged))

    # No per-target export decision for marketing outreach (Jon's policy 2026-07-31):
    # allies + neutral nations are cleared to market to; adversary/embargoed nations
    # were already dropped above. Any controlled technical-data transfer, if it ever
    # occurs, stays gated by the separate ITAR data-transfer process, not here.

    print(f"  regenerate dashboard: {'OK' if regenerate() else 'FAIL'}")
    if not args.no_discord:
        print(f"  Discord: {'OK' if deliver_discord(staged, len(blocked)) else 'FAIL'}")
    try: _gevent(_GRUN, "executed", detail=f"{len(staged)} staged, {len(blocked)} blocked")
    except Exception: pass
    print("done.")


if __name__ == "__main__":
    main()
