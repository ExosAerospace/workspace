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

OUT = os.path.join(WS, "mission-control", "data", "csl-screening.json")
DISPO = os.path.join(WS, "mission-control", "data", "csl-dispositions.json")
DISCORD = "channel:1501636728711282741"  # #series-a
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"

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
    open_flags = [f for f in flags if not f["disposition"]]
    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "csl_entities": len(csl._ENT),
        "csl_list_date": datetime.fromtimestamp(os.path.getmtime(csl.CACHE)).strftime("%Y-%m-%d"),
        "counts": {"screened": len(parties), "flagged": len(flags),
                   "open": len(open_flags), "cleared": len(flags) - len(open_flags),
                   "clear": len(parties) - len(flags)},
        "flags": sorted(flags, key=lambda f: (bool(f["disposition"]), -f["score"])),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(report, open(OUT, "w"), indent=2)
    print(f"CSL nightly: {len(parties)} screened · {len(flags)} flagged · {len(open_flags)} open · "
          f"{len(parties)-len(flags)} clear (CSL {report['csl_list_date']}, {len(csl._ENT)} entities)")

    if new_flags and "--no-alert" not in sys.argv:
        lines = ["🛡️ **CSL denied-party sweep — NEW flag(s) to disposition**"]
        for f in new_flags[:15]:
            lines.append(f"• **{f['party']}** [{f['party_type']}] → {f['listed_name']} "
                         f"({f['list'].split(' - ')[0]}; {f['programs']}; {f['countries'] or 'n/a'}) score {f['score']}")
        lines.append(f"\nReview + disposition in Mission Control → /compliance-screening.html "
                     f"(likely name collisions, but each needs a logged clear/confirm).")
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", DISCORD, "-m", "\n".join(lines)], capture_output=True, timeout=60)
        except Exception as e:
            print("discord alert failed:", e)

if __name__ == "__main__":
    main()
