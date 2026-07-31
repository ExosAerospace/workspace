#!/usr/bin/env python3
"""
export_screen.py — country policy for OUTBOUND marketing outreach.

Jon's standing policy (2026-07-31): marketing our services to the world is the
job. Being outside the US does not make a target an enemy. So:
  - ADVERSARY / communist / comprehensively-embargoed nations -> BLOCK silently.
    Do not draft, do not stage, do not file a decision. No decision to be made.
  - Everyone else (US, allies like Germany/Italy/France, and neutral nations)
    -> CLEAR for marketing outreach. No decision. Do not ask.

IMPORTANT SCOPE: this governs *marketing outreach* only (a note that our
suborbital test service exists). It does NOT authorize sharing controlled
technical data. Any actual ITAR/EAR-controlled technical-data transfer remains
gated by the separate ITAR data-transfer process (DD -> Dossier -> TDTCA -> EO
sign-off) and the inbound itar_ear_screen. Outreach drafts stay marketing-only.

Basis for the blocklist: ITAR 22 CFR 126.1 proscribed destinations plus the
comprehensively sanctioned / adversary states. Tune BLOCK_TOKENS as policy shifts.

Usage:
    from export_screen import classify_country
    verdict, reason = classify_country("France")   # -> ("clear", None)
    verdict, reason = classify_country("China")     # -> ("block", "adversary/embargoed: china")
"""
import re

# Adversary / communist / comprehensively-embargoed. Lowercase match tokens.
BLOCK_TOKENS = (
    "china", "prc", "people's republic of china", "hong kong", "macau", "macao",
    "russia", "russian federation", "belarus",
    "north korea", "dprk", "korea, north", "n. korea",
    "iran", "cuba", "syria", "venezuela",
    "myanmar", "burma", "nicaragua",
)

# A few obvious US allies, for display/logging only (logic doesn't need this —
# anything not in BLOCK_TOKENS is cleared).
ALLY_TOKENS = (
    "united states", "usa", "us", "u.s.", "america", "domestic",
    "germany", "italy", "france", "united kingdom", "uk", "britain", "england",
    "canada", "australia", "japan", "south korea", "korea, south", "netherlands",
    "belgium", "spain", "portugal", "sweden", "norway", "denmark", "finland",
    "poland", "czech", "austria", "switzerland", "ireland", "new zealand",
    "israel", "luxembourg", "estonia", "latvia", "lithuania", "greece",
    "romania", "bulgaria", "croatia", "slovakia", "slovenia", "hungary",
    "iceland", "singapore", "taiwan", "india", "brazil", "mexico", "uae",
)


def _norm(country):
    return re.sub(r"[^a-z0-9 ,.\-']", "", str(country or "").strip().lower())


def _matches(c, tokens):
    if not c:
        return False
    words = c.replace(",", " ").split()
    return any(t == c or t in words or c.startswith(t) or (" " in t and t in c)
               for t in tokens)


def classify_country(country):
    """Return (verdict, reason). verdict in {'block','clear'}.
    Unknown/blank country -> 'clear' (marketing outreach is not a controlled
    export; the ITAR data-transfer gate handles any later technical exchange)."""
    c = _norm(country)
    if _matches(c, BLOCK_TOKENS):
        return "block", f"adversary/embargoed: {c or 'unknown'}"
    return "clear", None


def is_ally(country):
    """True for a recognized US ally (display convenience only)."""
    return _matches(_norm(country), ALLY_TOKENS)


if __name__ == "__main__":
    for t in ["France", "Germany", "Italy", "China", "Russia", "Iran",
              "North Korea", "Cuba", "United States", "Brazil", "", "Unknownistan"]:
        print(f"{t or '(blank)':16} -> {classify_country(t)}")
