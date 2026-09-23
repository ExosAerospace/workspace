#!/usr/bin/env python3
"""
gen_blocked_senders.py — Build the canonical Exos blocked-senders list.

ONE output feeds BOTH:
  1. peaton's per-machine classic-Outlook updater (Exos_DD_Blocked_Senders_V6)
  2. the company-wide M365 GCC High tenant rule (Deploy-Exos-Blocked-Senders-Tenant.ps1)

Sources merged (dedup, sorted):
  - config/failed-dd-registry.json  -> every entity with verdict 'do-not-engage'
    (domains + full emails).  This is the auto-fed weekly channel.
  - email-blocklist/seed_peaton_initial.txt -> peaton's original curated list.

Format written (matches the updater's parser exactly):
  - one entry per line
  - accepts domain.com | user@domain.com | @domain.com | *@domain.com
  - blank lines and lines starting with '#' are ignored by consumers
  - entries trimmed, de-duplicated, sorted

Safety:
  - REVIEW_HOLD domains look like they could be real firms. They are written
    COMMENTED-OUT under a PENDING REVIEW banner so they never block org-wide
    until a human confirms. Uncomment (or remove from REVIEW_HOLD) to activate.

Run:  python3 scripts/gen_blocked_senders.py
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "config", "failed-dd-registry.json")
SEED = os.path.join(ROOT, "email-blocklist", "seed_peaton_initial.txt")
OUT = os.path.join(ROOT, "email-blocklist", "Blocked_Senders_Current.txt")
MANIFEST = os.path.join(ROOT, "email-blocklist", "blocked_senders_manifest.json")

# Domains that resemble legitimate firms — held for human confirmation before
# any org-wide block. Raised to peaton 2026-09-03. Remove an entry here once
# confirmed as a real bad actor to let it go live.
REVIEW_HOLD = {
    "capitolsupply.com",   # known GSA supplier
    "uscapital.com",
    "namtek.com",
    "beacongroup.aero",
    # --- Held 2026-09-23 (John): real gov/edu/firm domains swept in via spoofed
    #     senders that failed DD. Blocking the whole domain would bounce legit
    #     inbound. Confirm truly-bad before letting any of these go live. ---
    # Gov / .mil / .gov
    "navy.mil", "mda.mil", "spaceforce.mil", "smdc.army.mil", "us.army.mil",
    "usmc.mil", "mail.mil", "spawar.navy.mil", "nsoc.health.mil",
    "space.texas.gov", "aero.org",
    # Universities
    "stanford.edu", "columbia.edu", "brown.edu", "colorado.edu", "bcm.edu",
    "kingston.ac.uk",
    # Real firms
    "anduril.com", "planet.com", "umbra.space", "ge.com", "emerson.com",
    "netsuite.com", "cantor.com", "firstcitizens.com",
    # Malformed parse artifacts (trailing punctuation / junk tokens)
    "navy.mil.", "navy.mil;", "proton.me>", "01dd3563.bbded",
}


def norm(entry: str) -> str:
    """Normalize an entry to its bare domain-or-address form for dedup."""
    e = entry.strip()
    if not e or e.startswith("#"):
        return ""
    if e.startswith("*@"):
        e = e[2:]
    elif e.startswith("@"):
        e = e[1:]
    if not e or any(c.isspace() for c in e):
        return ""
    return e.lower()


def load_seed(path):
    out = set()
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            n = norm(line)
            if n:
                out.add(n)
    return out


def load_registry(path):
    """Return (entries, source_count). Pull do-not-engage domains + emails."""
    out = set()
    n_ent = 0
    if not os.path.exists(path):
        return out, n_ent
    data = json.load(open(path, "r", encoding="utf-8"))
    for ent in data.get("entities", []):
        if ent.get("verdict") != "do-not-engage":
            continue
        n_ent += 1
        for d in ent.get("domains", []) or []:
            n = norm(str(d))
            if n:
                out.add(n)
        for em in ent.get("emails", []) or []:
            n = norm(str(em))
            if n:
                out.add(n)
    return out, n_ent


def main():
    seed = load_seed(SEED)
    reg, n_ent = load_registry(REGISTRY)
    merged = seed | reg

    active = sorted(e for e in merged if e not in REVIEW_HOLD)
    held = sorted(e for e in merged if e in REVIEW_HOLD)

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip()
    lines = []
    lines.append("# Exos DD — Canonical Blocked-Senders List")
    lines.append(f"# Generated: {stamp} by scripts/gen_blocked_senders.py")
    lines.append(f"# Sources: failed-dd-registry.json ({n_ent} do-not-engage entities) + peaton seed")
    lines.append(f"# Active entries: {len(active)}   |   Held for review: {len(held)}")
    lines.append("# Format: one entry/line; domain.com | user@domain.com | @domain.com | *@domain.com")
    lines.append("# Lines starting with '#' are ignored by both the Outlook updater and the tenant rule.")
    lines.append("#")
    lines.extend(active)
    if held:
        lines.append("#")
        lines.append("# ---- PENDING REVIEW (look like real firms; confirm before org-wide block) ----")
        lines.append("# Uncomment a line (or remove it from REVIEW_HOLD in the generator) to activate.")
        for h in held:
            lines.append(f"# {h}")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    manifest = {
        "generated": stamp,
        "active_count": len(active),
        "held_count": len(held),
        "held": held,
        "registry_entities": n_ent,
        "seed_entries": len(seed),
        "output": os.path.relpath(OUT, ROOT),
    }
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    print(f"Wrote {OUT}")
    print(f"  active={len(active)}  held={len(held)}  (registry_entities={n_ent}, seed={len(seed)})")
    if held:
        print("  HELD for review:", ", ".join(held))


if __name__ == "__main__":
    sys.exit(main())
