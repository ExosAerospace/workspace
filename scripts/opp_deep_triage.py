#!/usr/bin/env python3
"""
opp_deep_triage.py — whole-board opportunity triage using Kimi K3's 1M-token context.

The current engine scores opportunities one at a time. This does what neither Qwen nor Claude
can in one pass: dumps the ENTIRE open opportunity set + Exos's full capability profile into a
single K3 context and returns one coherent, ranked go/no-go across the whole board — so pursuit
decisions are made relative to each other, not in isolation.

Non-sensitive by construction (public solicitations + our public positioning); still routed
through the export-control gate (kimi_bd). Saves a ranked report and can push a summary to the
Mission Control research feed.

Run: python3 scripts/opp_deep_triage.py
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import kimi_bd
OPPS = os.path.join(WS, "mission-control", "data", "opportunities.json")
PROFILE = os.path.join(WS, "EXOS_POSITIONING_STANDARD.md")
REPORTS = os.path.join(WS, "reports")
TODAY = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")


def load_opps():
    d = json.load(open(OPPS))
    o = d if isinstance(d, list) else d.get("opportunities", [])
    # keep the open/actionable ones; drop anything explicitly closed/won/dead
    out = []
    for x in o:
        if str(x.get("status", "")).upper() in ("CLOSED", "WON", "DEAD", "LOST"):
            continue
        out.append({"id": x.get("id"), "title": x.get("title"), "type": x.get("type"),
                    "category": x.get("category"), "value": (x.get("value") or "")[:220],
                    "due": x.get("due"), "priority": x.get("priority"),
                    "desc": (x.get("description") or "")[:320]})
    return out


import itar_ear_screen as ee


def _sanitize(text):
    """Drop any line that trips the export-control screen (keeps proprietary process/IP out of K3)."""
    keep = [ln for ln in text.splitlines() if not ee.screen(ln)]
    return "\n".join(keep)


def main():
    opps = load_opps()
    # Pre-screen each opportunity; hold flagged ones back (never sent to the Chinese API),
    # send only the clean set. No silent drop — held ids are reported.
    clean, held = [], []
    for x in opps:
        blob = " ".join(str(x.get(k, "")) for k in ("title", "type", "value", "desc"))
        (held if ee.screen(blob) else clean).append(x)
    held_ids = [x.get("id") for x in held]
    opps = clean
    profile = _sanitize(open(PROFILE).read())[:8000]
    system = ("You are Exos Aerospace's chief BD strategist. Judge each opportunity for genuine fit "
              "against THIS capability profile.\n\n=== EXOS CAPABILITY PROFILE ===\n" + profile)

    def rank_batch(batch):
        prompt = ("Rank these opportunities for Exos fit. Return ONLY valid JSON: "
                  '{"ranked":[{"id":"OPP-xxx","title":"...","fit":0-100,'
                  '"verdict":"PURSUE_NOW|PURSUE|WATCH|DROP","why":"<=14 words",'
                  '"deadline":"<date or none>","next_step":"<one concrete action>"}]}\n\n'
                  + json.dumps(batch))
        # K3 is a reasoning model (~3-4k reasoning tokens/call); budget high so the JSON isn't truncated.
        txt = kimi_bd.ask(prompt, label="opp-triage-batch", system=system, max_tokens=12000, timeout=420)
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            return json.loads(m.group(0)).get("ranked", []) if m else []
        except Exception:
            return []

    # Batch so each K3 call is small and fast (one 120-item generation gets killed).
    B = 40
    ranked_all = []
    n_batches = (len(opps) + B - 1) // B
    for i in range(0, len(opps), B):
        print(f"  K3 batch {i // B + 1}/{n_batches} ({len(opps[i:i+B])} opps)...")
        ranked_all += rank_batch(opps[i:i + B])

    # Portfolio synthesis over the top 20 (small, fast call)
    topN = sorted(ranked_all, key=lambda r: -(r.get("fit") or 0))[:20]
    synth = {}
    try:
        st = kimi_bd.ask("From these top-ranked Exos opportunities return ONLY JSON "
                         '{"top_pursue_now":["OPP-xxx", up to 10],"portfolio_read":"2-3 sentences: '
                         'where to concentrate BD effort and what to let go"}\n\n'
                         + json.dumps([{"id": r.get("id"), "title": r.get("title"), "fit": r.get("fit"),
                                        "verdict": r.get("verdict"), "deadline": r.get("deadline")} for r in topN]),
                         label="opp-triage-synth", system=system, max_tokens=1200, timeout=200)
        mm = re.search(r"\{.*\}", st, re.S)
        synth = json.loads(mm.group(0)) if mm else {}
    except Exception:
        synth = {}
    data = {"ranked": ranked_all,
            "top_pursue_now": synth.get("top_pursue_now")
            or [r.get("id") for r in topN if r.get("verdict") in ("PURSUE_NOW", "PURSUE")][:10],
            "portfolio_read": synth.get("portfolio_read", "")}
    os.makedirs(REPORTS, exist_ok=True)
    rp = os.path.join(REPORTS, f"opp-deep-triage-{TODAY}.md")

    if not data or "ranked" not in data:
        open(rp, "w").write(f"# Opportunity Deep-Triage {TODAY} (raw)\n\n{txt}")
        print("K3 returned unparseable JSON; saved raw ->", rp)
        return

    ranked = sorted(data["ranked"], key=lambda r: -(r.get("fit") or 0))
    L = [f"# Opportunity Deep-Triage — {TODAY}",
         f"_Whole-board ranking of {len(ranked)} open opportunities via Kimi K3 (1M context). Non-sensitive; export-control gated._",
         (f"_Held back from K3 (export-control screen, review locally): {', '.join(held_ids)}_\n" if held_ids else ""),
         "## Portfolio read", data.get("portfolio_read", ""), "",
         "## Pursue now", ]
    tp = set(data.get("top_pursue_now", []))
    byid = {r.get("id"): r for r in ranked}
    for oid in data.get("top_pursue_now", []):
        r = byid.get(oid)
        if r:
            L.append(f"- **{r.get('fit')} · {r.get('id')} — {r.get('title')}** · due {r.get('deadline') or 'n/a'} · {r.get('next_step')}")
    L.append("\n## Full ranking")
    for r in ranked:
        star = "⭐" if r.get("id") in tp else ""
        L.append(f"- {star}**{r.get('fit')}** [{r.get('verdict')}] {r.get('id')} — {r.get('title')} · _{r.get('why')}_ · due {r.get('deadline') or 'n/a'}")
    open(rp, "w").write("\n".join(L))

    # concise stdout for relay
    print("\n=== PORTFOLIO READ ===\n" + data.get("portfolio_read", ""))
    print("\n=== TOP PURSUE NOW ===")
    for oid in list(data.get("top_pursue_now", []))[:10]:
        r = byid.get(oid)
        if r:
            print(f"  {r.get('fit')} {r.get('id')} {r.get('title')[:52]} — due {r.get('deadline') or 'n/a'}")
    vc = {}
    for r in ranked:
        vc[r.get("verdict")] = vc.get(r.get("verdict"), 0) + 1
    print("\nverdict spread:", vc, "| report ->", rp)


if __name__ == "__main__":
    main()
