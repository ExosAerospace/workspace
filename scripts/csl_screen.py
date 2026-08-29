#!/usr/bin/env python3
"""
csl_screen.py — in-house Consolidated Screening List (CSL) denied-party screener.

Replaces the core restricted-party-screening function of Descartes Visual Compliance using
the U.S. government's free bulk CSL file (11 lists: BIS Entity/Denied/Unverified, State
AECA-debarred + nonproliferation, OFAC SDN + non-SDN, etc.). No API key, no rate limits;
mirrors how supplier-DD already pulls OFAC sdn.csv.

Usage:
  python3 scripts/csl_screen.py --name "Some Company Ltd"      # screen one party
  python3 scripts/csl_screen.py --parity                       # screen our CRM orgs + suppliers
  python3 scripts/csl_screen.py --selftest                     # known-listed + clean controls
"""
import json, os, re, sys, time, urllib.request, difflib
from collections import defaultdict

WS = "/Users/exomac/.openclaw/workspace"
CACHE = os.path.join(WS, "data-cache", "csl_consolidated.json")
CSL_URL = "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json"
MAX_AGE = 24 * 3600  # refresh daily (source lists update daily)
SUFFIX = re.compile(r'\b(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|co|company|'
                    r'gmbh|s\.a|sa|plc|pllc|lp|llp|pte|bv|nv|ag|srl|spa|pjsc|ojsc|jsc|ooo|oao|zao)\b\.?', re.I)
PUNCT = re.compile(r'[^a-z0-9 ]+')

def norm(s):
    s = (s or "").lower()
    s = PUNCT.sub(' ', s)
    s = SUFFIX.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip()

def refresh():
    if os.path.exists(CACHE) and time.time() - os.path.getmtime(CACHE) < MAX_AGE:
        return
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    data = urllib.request.urlopen(CSL_URL, timeout=120).read()
    open(CACHE, "wb").write(data)

_IDX = None  # token -> set of (norm_name, entity_ref); ENT holds entity metadata
_NAMES = None
_ENT = None
def _build():
    global _IDX, _NAMES, _ENT
    if _IDX is not None:
        return
    refresh()
    results = json.load(open(CACHE))["results"]
    _IDX = defaultdict(set); _NAMES = {}; _ENT = {}
    for e in results:
        eid = e.get("_id") or e.get("id") or id(e)
        _ENT[eid] = e
        names = [e.get("name")] + (e.get("alt_names") or [])  # ID docs excluded — they mis-match
        for nm in names:
            if not isinstance(nm, str):
                continue
            n = norm(nm)
            if len(n) < 4:
                continue
            _NAMES[n] = eid
            for tok in set(n.split()):
                if len(tok) >= 4:
                    _IDX[tok].add(n)

def _toks(n):
    return set(t for t in n.split() if len(t) >= 3)

def screen(query, threshold=0.90):
    """Return match dicts. Precision-tuned: exact normalized match, or high full-string
    similarity WITH real token overlap — no bare-substring/generic-token flagging (that was
    the false-positive engine). Matches still get human dispositioning, VC-style."""
    _build()
    q = norm(query)
    if len(q) < 4:
        return []
    qt = _toks(q)
    hits = {}
    def add(n, score):
        eid = _NAMES.get(n)
        if eid is None: return
        prev = hits.get(eid)
        if prev is None or score > prev["score"]:
            e = _ENT[eid]
            addrs = "; ".join(sorted({a.get("country", "") for a in (e.get("addresses") or []) if a.get("country")}))
            hits[eid] = {"score": round(score, 3), "listed_name": e.get("name"),
                         "source": e.get("source"), "type": e.get("type"),
                         "programs": ", ".join(e.get("programs") or []) or (e.get("standard_order") or ""),
                         "countries": addrs}
    if q in _NAMES:
        add(q, 1.0)
    cand = set()
    for tok in qt:
        if len(tok) >= 4:
            cand |= _IDX.get(tok, set())
    for n in cand:
        if q == n:
            add(n, 1.0); continue
        nt = _toks(n)
        if not nt or not qt:
            continue
        overlap = len(qt & nt) / min(len(qt), len(nt))   # fraction of the shorter name's tokens shared
        ratio = difflib.SequenceMatcher(None, q, n).ratio()
        # flag only when the whole names are close AND they genuinely share tokens
        if ratio >= threshold and overlap >= 0.6:
            add(n, ratio)
    return sorted(hits.values(), key=lambda h: -h["score"])

# ---- party sources for the parity run ----
def crm_orgs():
    try:
        k = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
        req = urllib.request.Request(
            "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/contacts?select=organization&limit=5000",
            headers={"apikey": k, "Authorization": "Bearer " + k})
        rows = json.load(urllib.request.urlopen(req, timeout=60))
        return sorted({(r.get("organization") or "").strip() for r in rows if (r.get("organization") or "").strip()})
    except Exception as e:
        print("  (CRM pull failed:", str(e)[:80], ")"); return []

def suppliers():
    p = os.path.join(WS, "mission-control", "data", "supplier-dd-registry.json")
    try:
        d = json.load(open(p))
        rows = d if isinstance(d, list) else d.get("suppliers", [])
        return sorted({(r.get("name") or "").strip() for r in rows if (r.get("name") or "").strip()})
    except Exception:
        return []

def main():
    a = sys.argv
    if "--selftest" in a:
        _build()
        print(f"CSL loaded: {len(_ENT)} entities, {len(_NAMES)} names indexed "
              f"(cache age {int((time.time()-os.path.getmtime(CACHE))/3600)}h)")
        for ctrl in ["Rosoboronexport", "Huawei Technologies", "Exos Aerospace Systems"]:
            m = screen(ctrl)
            tag = "🔴 HIT" if m else "🟢 clear"
            print(f"  {tag}  {ctrl}" + (f"  -> {m[0]['listed_name']} [{m[0]['source']}] score {m[0]['score']}" if m else ""))
        return
    if "--name" in a:
        q = a[a.index("--name") + 1]
        m = screen(q)
        print(json.dumps(m, indent=2) if m else f"🟢 no CSL match for: {q}")
        return
    if "--parity" in a:
        _build()
        parties = [(o, "CRM") for o in crm_orgs()] + [(s, "supplier") for s in suppliers()]
        print(f"Screening {len(parties)} parties against CSL ({len(_ENT)} entities)...")
        flagged = 0
        for name, src in parties:
            m = screen(name)
            if m:
                flagged += 1
                top = m[0]
                print(f"  🔴 {name} [{src}] -> {top['listed_name']} | {top['source']} | "
                      f"{top['programs']} | {top['countries']} | score {top['score']}")
        print(f"\nParity result: {len(parties)} screened, {flagged} flagged, {len(parties)-flagged} clear.")
        return
    print(__doc__)

if __name__ == "__main__":
    main()
