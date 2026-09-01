#!/usr/bin/env python3
"""
DD SCREEN — single source of truth for "can we engage this firm?" across the
Series A pipeline (daily worklist + any draft/outreach send path). Combines the
two DD stores so nothing that failed diligence can be worked or auto-contacted:

  1. config/failed-dd-registry.json      — hand-curated DO-NOT-ENGAGE blocklist
     (scam / cold-broker / advance-fee / sanctions / debarment), matched via
     failed_dd.check() on email, domain, or exact firm/person name.
  2. mission-control/data/dd-registry.json — nightly CRM DD engine verdicts
     (pass / caution / fail), keyed by domain, each carrying company + verdict.

API:
  verdict_for(firm=, email=, domain=) -> 'fail' | 'caution' | 'pass' | ''
      'fail'  = on the do-not-engage blocklist OR the CRM engine scored it fail.
      'caution' = CRM engine flagged for human review before contact.
  is_blocked(firm=, email=, domain=) -> True when verdict == 'fail' (never auto-contact).

CLI:
  python3 scripts/dd_screen.py check "Firm Name" [email-or-domain]
"""
import os, sys, json, re

WS = os.path.expanduser("~/.openclaw/workspace")
CRM_DD = os.path.join(WS, "mission-control", "data", "dd-registry.json")

try:
    import failed_dd  # same scripts/ dir (on sys.path when run/imported from scripts/)
except Exception:
    failed_dd = None

_RANK = {"fail": 3, "caution": 2, "pass": 1}


def _norm(s):
    """Lowercase, punctuation->space, collapse spaces. Light on purpose so distinct
    firms stay distinct (e.g. 'Craft Capital' != 'Craft Ventures')."""
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def _load_crm_verdicts():
    try:
        reg = json.load(open(CRM_DD))
    except Exception:
        return {}
    out = {}
    for v in (reg.values() if isinstance(reg, dict) else reg):
        if not isinstance(v, dict):
            continue
        name = _norm(v.get("company"))
        verd = str(v.get("verdict") or "").strip().lower()
        if not name or verd not in _RANK:
            continue
        if name not in out or _RANK[verd] > _RANK[out[name]]:
            out[name] = verd
    return out


def _load_fund_active():
    """name->bool map: firms the DD deep-dive validated as an ACTIVE space/tech fund with
    ~12-mo funding traction (fund_active_12mo). Used to re-include a validated caution firm."""
    try:
        reg = json.load(open(CRM_DD))
    except Exception:
        return {}
    out = {}
    for v in (reg.values() if isinstance(reg, dict) else reg):
        if not isinstance(v, dict):
            continue
        name = _norm(v.get("company"))
        if name and v.get("fund_active_12mo"):
            out[name] = True
    return out


_CRM_CACHE = None
_FUND_CACHE = None


def crm_verdicts():
    """name->verdict map from the CRM DD engine (cached). {} if unreadable."""
    global _CRM_CACHE
    if _CRM_CACHE is None:
        _CRM_CACHE = _load_crm_verdicts()
    return _CRM_CACHE


def fund_active_for(firm=None):
    """True if the DD deep-dive validated this firm as an active space/tech fund (cached)."""
    global _FUND_CACHE
    if _FUND_CACHE is None:
        _FUND_CACHE = _load_fund_active()
    return bool(_FUND_CACHE.get(_norm(firm)))


def verdict_for(firm=None, email=None, domain=None):
    """Worst-case verdict across both DD stores. Blocklist match => 'fail'."""
    if failed_dd is not None:
        try:
            if failed_dd.check(email=email, domain=domain, name=(firm or "").strip().lower()):
                return "fail"
        except Exception:
            pass
    return crm_verdicts().get(_norm(firm), "")


def is_blocked(firm=None, email=None, domain=None):
    """True if this firm must never be auto-contacted (failed DD / do-not-engage)."""
    return verdict_for(firm=firm, email=email, domain=domain) == "fail"


def _cli():
    if len(sys.argv) >= 3 and sys.argv[1] == "check":
        firm = sys.argv[2]
        ident = sys.argv[3] if len(sys.argv) > 3 else ""
        email = ident if "@" in ident else None
        domain = ident if ("." in ident and "@" not in ident) else None
        v = verdict_for(firm=firm, email=email, domain=domain)
        label = {"fail": "❌ BLOCKED (failed DD — do not engage)",
                 "caution": "⚠️ CAUTION (human review before contact)",
                 "pass": "✅ PASS (clear to engage)",
                 "": "— no DD record (unscreened)"}[v]
        print(f"{firm}: {label}")
        sys.exit(1 if v == "fail" else 0)
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    _cli()
