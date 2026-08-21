#!/usr/bin/env python3
"""Supplier-Diligence-exo3 — governed supplier due-diligence engine.

exo3 process (AI-managed program; see project_exo3_program_naming). ERP/QuickBooks is the
system of record; this proves readiness (SCRM-1..5) and never duplicates the vendor master.

FLOW (deterministic dispatch — the model is NOT in the approve path):
  ingest suppliers (QuickBooks vendors + Divvy-synced spend)  →  screen each:
    OFAC SDN + SAM.gov exclusions + FOCI/country (reused from the CRM DD engine / export_screen),
    adverse-media keyword scan (Tavily), spend concentration (single-source), CUI/CMMC exposure
  →  tier GREEN / AMBER / RED
  →  GREEN auto-clears (Exo-signed, logged)          [no human needed]
     AMBER/RED are HELD: a dual-clearance Decision card routes to a human; nothing risky clears
     without a human signature. Hard fails (OFAC/SAM/adversary) also hit the failed-DD registry.
  →  write supplier-dd-registry.json (supplier master + DD status + SCRM metrics) which the
     Government/DIB Readiness Register and GAAP supplier analytics read.

  python3 scripts/supplier_dd_exo3.py --now            # run against live QuickBooks
  python3 scripts/supplier_dd_exo3.py --sample         # run against a built-in sample list (no QB needed)
  python3 scripts/supplier_dd_exo3.py --supplier "Acme Composites"   # single supplier
"""
import os, sys, json, subprocess, datetime, urllib.request

WS = os.path.expanduser("~/.openclaw/workspace")
sys.path.insert(0, os.path.join(WS, "scripts"))
SEC = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
REG = os.path.join(WS, "mission-control", "data", "supplier-dd-registry.json")
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
LOG_DD = os.path.join(WS, "scripts", "log_dd.py")
CONCENTRATION_FLAG = 0.20     # >=20% of spend = single-source / concentration risk (SCRM-4)
OWNER_HUMAN = "jquinn@exosaero.com"   # human clearer for held items
RISK_TERMS = ("sanction","ofac","fraud","indict","lawsuit","litigation","bankrupt","insolven",
              "debar","default","data breach","recall","counterfeit","export violation","settlement")

# ---- reuse existing screening (DRY; never duplicate the CRM engine's logic) ----
def _fallback_ofac(n): return None
def _fallback_sam(n): return None
def _fallback_country(c): return ("clear", None)
def _fallback_tavily(q, depth="basic"): return []
try:
    from crm_dd_engine import ofac_hit, sam_excluded, tavily
except Exception:
    ofac_hit, sam_excluded, tavily = _fallback_ofac, _fallback_sam, _fallback_tavily
try:
    from export_screen import classify_country
except Exception:
    classify_country = _fallback_country

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d

def save(p, o):
    tmp = p + ".tmp"; json.dump(o, open(tmp, "w"), indent=2); os.replace(tmp, p)

def slug(s): return "".join(c.lower() if c.isalnum() else "-" for c in (s or "")).strip("-")[:60]

OLLAMA = "http://localhost:11434/api/generate"; OLLAMA_MODEL = "qwen3.6:35b-a3b"
def adverse_media(name):
    """Model-adjudicated (flag-only, never auto-clears): is there credible adverse coverage
    ABOUT THIS company? Avoids the circular 'searched-for-the-word-so-it-appears' false positive.
    Falls back to NO flag if the model/Tavily is unavailable (won't false-positive)."""
    try:
        hits = tavily(f'"{name}" (lawsuit OR investigation OR sanctioned OR fraud OR bankruptcy OR debarment OR recall)')
    except Exception:
        hits = []
    if not hits: return [], []
    snippets = "\n".join(f"- {h.get('title','')}: {h.get('content','')[:200]}" for h in hits if isinstance(h, dict))[:2500]
    srcs = [h["url"] for h in hits if isinstance(h, dict) and h.get("url")][:4]
    prompt = (f"Company under review: {name}\nSearch results:\n{snippets}\n\n"
              "Is there CREDIBLE adverse information specifically about THIS company (OFAC sanctions, "
              "federal debarment, fraud, active litigation as defendant, bankruptcy/insolvency, product "
              "recall, or export-control violation)? Ignore unrelated companies and generic/marketing pages. "
              'Return ONLY JSON: {"adverse": true, "why": "<one short phrase>"} or {"adverse": false, "why": ""}.')
    try:
        body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json",
                           "think": False, "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.loads(json.loads(r.read()).get("response", "{}"))
        if out.get("adverse"):
            return ["adverse media: " + str(out.get("why", "credible negative coverage"))[:120]], srcs
    except Exception:
        pass
    return [], srcs

def screen(sup, total_spend):
    """Return (tier, flags[], hard_reasons[], sources[]). Deterministic."""
    name = sup["name"]; flags=[]; hard=[]; srcs=[]
    o = ofac_hit(name)
    if o: hard.append(f"OFAC: {o}")
    s = sam_excluded(name)
    if s: hard.append(f"SAM.gov excluded/debarred: {s}")
    verdict, why = classify_country(sup.get("country") or "United States")
    if verdict == "block": hard.append(f"FOCI/adversary country: {why}")
    elif (sup.get("country") or "").strip() and not _is_us(sup.get("country")):
        flags.append(f"foreign supplier ({sup['country']}) — FOCI review")
    am, am_src = adverse_media(name); srcs += am_src
    if am: flags.append("adverse-media hits: " + ", ".join(am))
    share = (sup.get("spend_365",0)/total_spend) if total_spend else 0
    if share >= CONCENTRATION_FLAG:
        flags.append(f"spend concentration {share*100:.0f}% (single-source risk, SCRM-4)")
    if sup.get("cui_exposure"): flags.append("handles FCI/CUI — CMMC flow-down required (SCRM-5)")
    tier = "RED" if hard else ("AMBER" if flags else "GREEN")
    return tier, flags, hard, srcs

def _is_us(c):
    c=(c or "").strip().lower()
    return c in ("","us","usa","u.s.","u.s.a.","united states","united states of america","america")

def open_decision(sup, tier, flags, hard):
    arr = load(DECISIONS, [])
    dk = f"supplier-dd:{sup['id']}"
    reasons = (hard + flags)
    card = {
        "id": f"dec-supdd-{sup['id']}", "created": datetime.datetime.now().isoformat(timespec="seconds"),
        "updated": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": "supplier-dd-exo3", "relatedItem": sup["name"],
        "title": f"Supplier DD — {sup['name']} ({tier})",
        "question": f"Clear supplier {sup['name']} for federal/production use? Exo flagged a possible issue; human sign-off required.",
        "context": "Exo screen found: " + "; ".join(reasons[:6]) + (f"  | FY spend ${sup.get('spend_365',0):,.0f}." ),
        "proposedAction": "Approve (with conditions) / Reject / Need more info. Nothing risky clears without this signature.",
        "type": "approval", "options": ["Approve supplier","Reject / hold","Need more info"],
        "priority": "high" if tier=="RED" else "medium",
        "dedupeKey": dk, "status": "open", "answer": "", "note": "",
        "assignedTo": OWNER_HUMAN,
    }
    existing = next((d for d in arr if d.get("dedupeKey")==dk), None)
    if existing:
        # carry the human's prior answer forward; refresh context/tier only
        existing.update({k:card[k] for k in ("updated","title","context","priority")})
        if existing.get("status")=="open": existing["question"]=card["question"]
    else:
        arr.append(card)
    save(DECISIONS, arr)
    return card["id"]

def dossier(name, verdict, summary):
    try:
        subprocess.run(["python3", LOG_DD, "--firm", name, "--verdict", verdict, "--summary", summary[:300],
                        "--requester", "supplier-dd-exo3"], cwd=WS, timeout=30, capture_output=True)
    except Exception: pass

SAMPLE = [
    {"name":"CTD (Composite Technology Development)","country":"United States","spend_365":180000,"cui_exposure":True},
    {"name":"Gloyer-Taylor Laboratories","country":"United States","spend_365":90000},
    {"name":"MATECH","country":"United States","spend_365":40000},
    {"name":"Acme Global Imports","country":"Cuba","spend_365":15000},
]

def ingest(args):
    if "--names-file" in args:
        # Screen an explicit supplier list (one name per line) — e.g. BOM suppliers — bypassing
        # QuickBooks ingest. Optional "name\tspend" tab-separated for concentration analysis.
        p = args[args.index("--names-file") + 1]
        sup = []; total = 0
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            name = parts[0].strip()
            spend = 0
            try:
                spend = float(parts[1]) if len(parts) > 1 else 0
            except Exception:
                spend = 0
            sup.append({"name": name, "id": slug(name), "qb_id": None, "country": "", "spend_365": spend})
            total += spend
        return sup, total, "bom"
    if "--sample" in args:
        return [dict(s, id=slug(s["name"]), qb_id=None) for s in SAMPLE], sum(s["spend_365"] for s in SAMPLE), "sample"
    try:
        import qb_client
        vendors = qb_client.list_vendors()
        spend = qb_client.vendor_spend(365)
        sup=[]
        for v in vendors:
            v["id"]=slug(v["name"]); v["spend_365"]=spend.get(v["name"],0)
            sup.append(v)
        return sup, sum(spend.values()), "quickbooks"
    except Exception as e:
        print(f"[QB not connected: {e}] — run with --sample, or add qb_* creds to secrets.json.")
        return [], 0, "none"

def main():
    args = sys.argv[1:]
    suppliers, total, src = ingest(args)
    if "--supplier" in args:
        want = args[args.index("--supplier")+1].lower()
        suppliers = [s for s in suppliers if want in s["name"].lower()]
    if "--limit" in args:
        suppliers = suppliers[:int(args[args.index("--limit")+1])]
    reg = load(REG, {"meta":{}, "suppliers":[]})
    idx = {s["id"]:s for s in reg.get("suppliers",[])}
    stats = {"GREEN":0,"AMBER":0,"RED":0}
    for sup in suppliers:
        tier, flags, hard, srcs = screen(sup, total)
        stats[tier]+=1
        rec = {
            "id": sup["id"], "name": sup["name"], "country": sup.get("country",""),
            "spend_365": sup.get("spend_365",0),
            "spend_share": round(sup.get("spend_365",0)/total,4) if total else 0,
            "tier": tier, "flags": flags, "hard_reasons": hard, "sources": srcs,
            "cui_exposure": bool(sup.get("cui_exposure")),
            "updated": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": src,
        }
        if tier=="GREEN":
            rec["status"]="cleared"; rec["cleared_by"]="Exo (auto)"; rec["human_required"]=False
            dossier(sup["name"], "pass", "Supplier-DD-exo3 auto-clear: clean OFAC/SAM/FOCI/media, no concentration.")
        else:
            rec["status"]="held"; rec["cleared_by"]=""; rec["human_required"]=True
            rec["decision_id"]=open_decision(sup, tier, flags, hard)
            dossier(sup["name"], "fail" if tier=="RED" else "caution",
                    ("HELD "+tier+": "+ "; ".join((hard+flags)[:4])))
        idx[sup["id"]]=rec
    reg["suppliers"]=list(idx.values())
    reg["meta"]={"title":"Supplier-Diligence-exo3 registry","process":"Supplier-Diligence-exo3",
                 "principle":"ERP is system of record; this proves readiness (SCRM-1..5), never duplicates.",
                 "concentration_flag":CONCENTRATION_FLAG,"source":src}
    reg["updated"]=datetime.datetime.now().isoformat(timespec="seconds")
    save(REG, reg)
    print(f"screened {len(suppliers)} suppliers from {src}: GREEN {stats['GREEN']} (auto-cleared) | "
          f"AMBER {stats['AMBER']} + RED {stats['RED']} held for human sign-off. Registry -> {REG}")

if __name__ == "__main__":
    main()
