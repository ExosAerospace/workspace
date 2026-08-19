#!/usr/bin/env python3
"""
Single source of truth for Exos opportunity relevance + cross-scan de-duplication.

Every scan/briefing (mc_briefing SAM feed, BD Daily Intel, research digests) should
gate through here so that (a) only Exos-capability-aligned items surface, and (b) the
same opportunity is never reported twice across different scans.

- is_aligned(text)          -> bool   (capability ALLOW gate + anti-pattern DENY backstop)
- norm(title)               -> str    (dedup key)
- filter_new_aligned(items) -> list   (aligned AND not seen before; records the new ones)
- escalate(items, source)   -> int    (append new aligned opportunities to the monthly report)

Dedup ledger: mission-control/data/seen-opportunities.json
Report:       reports/aligned-opportunities-YYYY-MM.md
"""
import os, re, json, datetime

ROOT = "/Users/exomac/.openclaw/workspace"
LEDGER = os.path.join(ROOT, "mission-control/data/seen-opportunities.json")
REPORT_DIR = os.path.join(ROOT, "reports")

# ── Exos capabilities: an item must match at least one of these ──
ALLOW = (
    "reusable launch", "suborbital", "spaceport", "space launch", "launch service",
    "launch site", "responsive launch", "responsive space", "sounding rocket",
    "rotating detonation", "detonation engine", "rdre",
    "cryogenic", "cryocooler", "propellant transfer", "in-space refuel", "on-orbit refuel",
    "in-space propellant", "fluid management", "composite tank", "linerless", "type-5", "type 5",
    "hosted payload", "payload flight", "flight test service", "microgravity",
    "rocket motor case", "solid rocket motor case", "composite overwrap",
    "hypersonic flight", "hypersonic test",
)
# ── Anti-patterns: reject even if an ALLOW term is present ──
DENY = (
    "interceptor", "counter-small", "counter small", "c-uas", "c-suas", "patriot",
    "guided missile", "multiple launch rocket", "mlrs", "terminal stage", "warhead",
    "missile defense", "tracking to intercept", "landsat", "spacecraft bus",
    "satellite bus", "gps iii", "weather satellite",
)

def is_aligned(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ALLOW) and not any(k in t for k in DENY)

def norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()

def _load():
    try:
        return json.load(open(LEDGER))
    except Exception:
        return {}

def _save(d):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(d, open(LEDGER, "w"), indent=2)

def seen_keys(days: int = 45):
    """Keys reported within the last `days` (older ones expire so re-opens can resurface)."""
    d = _load()
    cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    return {k for k, v in d.items() if v.get("first_seen", "") >= cutoff}

def filter_new_aligned(items, source: str, today=None):
    """items: list of dicts each with at least a 'title'. Returns the subset that is
    Exos-aligned AND not seen in the ledger; records those as seen."""
    today = today or datetime.date.today().isoformat()
    d = _load()
    fresh = seen_keys()
    out = []
    for it in items:
        title = it.get("title") if isinstance(it, dict) else str(it)
        if not is_aligned(title):
            continue
        k = norm(title)
        if not k or k in fresh:
            continue
        d.setdefault(k, {"first_seen": today, "source": source, "title": title})
        fresh.add(k)
        out.append(it)
    _save(d)
    return out

def escalate(items, source: str, today=None):
    """Append new aligned opportunities to the monthly report file. Returns count written."""
    if not items:
        return 0
    today = today or datetime.date.today().isoformat()
    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f"aligned-opportunities-{today[:7]}.md")
    new = not os.path.exists(path)
    with open(path, "a") as f:
        if new:
            f.write(f"# Exos-Aligned Opportunities — {today[:7]}\n\n"
                    "Capability-gated, de-duplicated across scans. Source: exos_capability_gate.\n\n")
        for it in items:
            title = it.get("title") if isinstance(it, dict) else str(it)
            extra = ""
            if isinstance(it, dict):
                bits = [str(it[k]) for k in ("due", "deadline", "value", "agency", "link") if it.get(k)]
                if bits:
                    extra = "  (" + " · ".join(bits) + ")"
            f.write(f"- [{today}] [{source}] {title}{extra}\n")
    return len(items)

if __name__ == "__main__":
    import sys
    # tiny self-test
    tests = [("Suborbital Reusable Launch Services On-Ramp", True),
             ("Next Generation Counter-Small UAS Missile", False),
             ("Landsat 10 Spacecraft", False),
             ("Cryogenic Fluid Management Propellant Transfer", True)]
    ok = all(is_aligned(t) == e for t, e in tests)
    print("self-test:", "PASS" if ok else "FAIL")
    for t, e in tests:
        print(f"  {is_aligned(t)!s:5} (want {e!s:5}) | {t}")
