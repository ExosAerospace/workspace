#!/usr/bin/env python3
"""
csl_nightly.py — nightly Consolidated Screening List (CSL) sweep of all Exos parties.

Screens every CRM organization + supplier/vendor against the full 11-list CSL (via
csl_screen.py), merges human dispositions, and writes a Mission-Control-readable report
+ posts new (undispositioned) flags to Discord. This is the in-house replacement for the
routine restricted-party screening currently done in Descartes Visual Compliance.

launchd: com.exos.csl-screen (daily). Output: mission-control/data/csl-screening.json
Dispositions: mission-control/data/csl-dispositions.json  ({party_norm: {status,note,by,date}})
"""
import json, os, sys, time, subprocess, shutil
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import csl_screen as csl
import csl_adjudicate as adj

OUT = os.path.join(WS, "mission-control", "data", "csl-screening.json")
DISPO = os.path.join(WS, "mission-control", "data", "csl-dispositions.json")
DISCORD = "channel:1501636728711282741"  # #series-a
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def main():
    csl._build()
    dispo = load(DISPO, {})
    parties = [(o, "CRM") for o in csl.crm_orgs()] + [(s, "supplier") for s in csl.suppliers()]
    flags, new_flags = [], []
    for name, src in parties:
        matches = csl.screen(name)
        if not matches:
            continue
        top = matches[0]
        d = dispo.get(csl.norm(name))
        rec = {"party": name, "party_type": src, "listed_name": top["listed_name"],
               "list": top["source"], "programs": top["programs"], "countries": top["countries"],
               "score": top["score"], "disposition": d}
        flags.append(rec)
        if not d:  # undispositioned = needs human review
            new_flags.append(rec)
    # --- Auto-triage (John, 2026-09-10): investigate each NEW flag before it reaches John.
    # Auto-clear ONLY deterministic verified-registry collisions (logged, reversible).
    # exo3 audit P1 #4: a model 'clear' is a PROPOSAL — the flag stays OPEN (no disposition
    # written) and is routed to a human with the model rationale. Fail CLOSED. ---
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    auto_cleared, escalate = [], []
    for f in new_flags:
        try:
            r = adj.adjudicate(f)
        except Exception as e:
            r = {"verdict": "escalate", "method": "adj-error", "rationale": f"Escalated (adjudicator error: {str(e)[:60]})."}
        if r.get("verdict") == "clear" and r.get("method") == "verified-registry":
            d = {"status": "cleared", "note": r["rationale"],
                 "by": f"Exo auto-triage ({r['method']})", "date": today}
            dispo[csl.norm(f["party"])] = d
            f["disposition"] = d
            auto_cleared.append(f)
        else:
            if r.get("verdict") == "proposed_clear":
                f["proposal"] = {"verdict": "proposed_clear", "method": r.get("method"),
                                 "rationale": r.get("rationale"), "date": today,
                                 "status": "pending human confirm"}
            escalate.append(f)
    proposed = [f for f in escalate if f.get("proposal")]
    if auto_cleared:
        json.dump(dispo, open(DISPO, "w"), indent=2)

    open_flags = [f for f in flags if not f["disposition"]]
    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "csl_entities": len(csl._ENT),
        "csl_list_date": datetime.fromtimestamp(os.path.getmtime(csl.CACHE)).strftime("%Y-%m-%d"),
        "counts": {"screened": len(parties), "flagged": len(flags),
                   "open": len(open_flags), "cleared": len(flags) - len(open_flags),
                   "auto_cleared_today": len(auto_cleared), "proposed_clear_pending_human": len(proposed),
                   "clear": len(parties) - len(flags)},
        "flags": sorted(flags, key=lambda f: (bool(f["disposition"]), -f["score"])),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(report, open(OUT, "w"), indent=2)
    print(f"CSL nightly: {len(parties)} screened · {len(flags)} flagged · {len(open_flags)} open · "
          f"{len(auto_cleared)} auto-cleared · {len(escalate)} escalated ({len(proposed)} model-proposed clear) · "
          f"{len(parties)-len(flags)} clear (CSL {report['csl_list_date']}, {len(csl._ENT)} entities)")

    # Only ping John for flags that genuinely need his judgment. Auto-clears are logged (MC page).
    if escalate and "--no-alert" not in sys.argv:
        lines = ["🛡️ **CSL denied-party sweep — flag(s) needing your review**"]
        for f in escalate[:15]:
            lines.append(f"• **{f['party']}** [{f['party_type']}] → {f['listed_name']} "
                         f"({f['list'].split(' - ')[0]}; {f['programs']}; {f['countries'] or 'n/a'}) score {f['score']}")
            if f.get("proposal"):
                lines.append(f"   ↳ 🤖 Exo PROPOSES clear (pending your confirm): {f['proposal']['rationale'][:220]}")
        if auto_cleared:
            lines.append(f"\n🤖 {len(auto_cleared)} verified-registry name-collision(s) auto-cleared + logged (no action needed).")
        lines.append("\nReview + disposition in Mission Control → /compliance-screening.html")
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", DISCORD, "-m", "\n".join(lines)], capture_output=True, timeout=60)
        except Exception as e:
            print("discord alert failed:", e)
    elif auto_cleared:
        print(f"  {len(auto_cleared)} auto-cleared, 0 escalations — no Discord alert sent (logged to MC).")

if __name__ == "__main__":
    main()
