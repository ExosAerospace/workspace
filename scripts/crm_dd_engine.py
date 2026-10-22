#!/usr/bin/env python3
"""CRM nightly DD-clearing engine (v2).

Walks every business domain in the CRM (mission-control/crm-data.json), screens each with:
  1. failed-DD registry  2. SAM.gov debarment + OFAC sanctions (hard fail)  3. web (Tavily) + local
  Ollama classification -> verdict pass/caution/fail, with a CONFIDENCE and cited SOURCES.
High-stakes counterparties (investors / Tier 1 / money-IP-ITAR) get a DEEPER DD (adverse media +
ownership/foreign-control searches). Records go to dd-registry.json (the CRM DD field); fails/cautions
also get a dossier (log_dd.py). Soft (model) fails route a human-in-the-loop Decision to the owner
before blacklisting; SAM/OFAC/registry fails are auto-added to failed_dd. Stale records (>180d) and
low-confidence passes are automatically re-screened. Cost-capped, windowed 00:00-05:00, resumable.

  python3 scripts/crm_dd_engine.py                         # nightly (windowed) full run
  python3 scripts/crm_dd_engine.py --now --limit 3          # test a few now
  python3 scripts/crm_dd_engine.py --domain x.com --company "X"   # real-time single company
"""
import os, sys, json, time, datetime, subprocess, urllib.request, urllib.parse, re

WS = os.path.expanduser("~/.openclaw/workspace")
SEC = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
CONTACTS = os.path.join(WS, "mission-control", "crm-data.json")
REG = os.path.join(WS, "mission-control", "data", "dd-registry.json")
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
TAVILY = SEC["tavily_api_key"]; SAM_KEY = SEC.get("sam_api_key", "")
OLLAMA = "http://localhost:11434/api/chat"; MODEL = "qwen3.6:35b-a3b"
SDN_CSV = os.path.join(WS, "data-cache", "sdn.csv"); _SDN = None
FREE_MAIL = {"gmail.com","yahoo.com","hotmail.com","outlook.com","proton.me","pm.me","icloud.com",
             "aol.com","me.com","live.com","msn.com","exosaero.com"}
MAX_SEARCHES = int(os.environ.get("DD_MAX_SEARCHES", "1200"))  # ~$9.6/run ceiling for the ~920-domain live CRM (<$20); resumable across nights
STALE_DAYS = int(os.environ.get("DD_STALE_DAYS", "180"))       # re-DD every ~6 months
WINDOW_END = datetime.time(5, 0)
NOW = "--now" in sys.argv
LIMIT = None
if "--limit" in sys.argv:
    try: LIMIT = int(sys.argv[sys.argv.index("--limit")+1])
    except Exception: pass
DOMAIN = next((sys.argv[i+1] for i,a in enumerate(sys.argv) if a == "--domain" and i+1 < len(sys.argv)), None)
COMPANY_ARG = next((sys.argv[i+1] for i,a in enumerate(sys.argv) if a == "--company" and i+1 < len(sys.argv)), None)

OWNER_EMAIL = {"jon":"jquinn@exosaero.com","john":"jquinn@exosaero.com","john quinn":"jquinn@exosaero.com",
               "lizi":"lquinn@exosaero.com","lizi quinn":"lquinn@exosaero.com","phil":"peaton@exosaero.com",
               "phil eaton":"peaton@exosaero.com","steve":"snorsworthy@exosaero.com",
               "steve norsworthy":"snorsworthy@exosaero.com","toshi":"toshihisa@exosaero.com"}
HS_CAT = ("investor","capital","vc","venture","family office","angel","fund","private equity","broker","lp")


def load_json(p, default):
    try: return json.load(open(p))
    except Exception: return default

def _norm(s): return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()

def _meta_from(c):
    email = c.get("email") or ""
    dom = (c.get("domain") or (email.split("@")[-1] if "@" in email else "")).lower().strip().rstrip(".,;:'\" ")
    if not dom or "." not in dom or dom in FREE_MAIL:
        return None, None
    # Government domains and directory/contact-list rows are not vendors/investors to vet — excluding
    # them stops false-positive DD fails and the resulting decision re-nags (e.g. ibc.doi.gov / "DARPA Contact List").
    nm = (c.get("company") or c.get("organization") or c.get("name") or c.get("contact") or "").lower()
    if dom.endswith((".gov", ".mil")) or ".mil" in dom or ".gov" in dom or dom.split(".")[-2:] == ["doi", "gov"]:
        return None, None
    if any(k in nm for k in ("contact list", "contacts", "open bids", "vendor contact", "gov and vendor")):
        return None, None
    cat = (c.get("category") or ""); tier = str(c.get("tier") or "")
    tags = " ".join(c.get("tags") or []) if isinstance(c.get("tags"), list) else str(c.get("tags") or "")
    blob = (cat + " " + tags + " " + (c.get("fit_thesis") or "")).lower()
    hs = (tier.strip() == "Tier 1") or any(k in blob for k in HS_CAT) or ("itar" in blob)
    name = c.get("company") or c.get("organization") or c.get("name") or c.get("contact") or dom
    return dom, {"name": name, "owner": c.get("owner") or "Jon", "category": cat, "tier": tier, "high_stakes": hs}

def companies_from_supabase():
    key = SEC.get("supabase_service_role_key")
    if not key: return None
    base = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/contacts"
    hdr = {"apikey": key, "Authorization": "Bearer " + key}
    out = {}; off = 0
    try:
        while True:
            req = urllib.request.Request(f"{base}?select=*&limit=1000&offset={off}", headers=hdr)
            rows = json.load(urllib.request.urlopen(req, timeout=45))
            if not rows: break
            for c in rows:
                if not isinstance(c, dict): continue
                dom, meta = _meta_from(c)
                if dom and dom not in out: out[dom] = meta
            if len(rows) < 1000: break
            off += 1000
        return out or None
    except Exception as e:
        print("supabase fetch failed, falling back to crm-data.json:", e); return None

def companies_from_file():
    d = load_json(CONTACTS, [])
    items = d if isinstance(d, list) else (d.get("contacts") or [])
    out = {}
    for c in items:
        if not isinstance(c, dict): continue
        dom, meta = _meta_from(c)
        if dom and dom not in out: out[dom] = meta
    return out

def companies():
    return companies_from_supabase() or companies_from_file()

# ---- compliance ----
def failed_dd_check(dom):
    try:
        r = subprocess.run(["python3", os.path.join(WS,"scripts","failed_dd.py"), "check", dom],
                           capture_output=True, timeout=30, text=True)
        return "MATCH" in (r.stdout or "").upper() and "NO MATCH" not in (r.stdout or "").upper()
    except Exception:
        return False

def failed_dd_add(firm, dom, reason):
    try:
        subprocess.run(["python3", os.path.join(WS,"scripts","failed_dd.py"), "add", "--firm", firm,
                        "--domain", dom, "--reason", reason, "--category", "sanctions/debarment"],
                       capture_output=True, timeout=30)
    except Exception: pass

SAM_UNVERIFIED = None  # set by sam_excluded when hits overflow the first page

def sam_excluded(name):
    global SAM_UNVERIFIED; SAM_UNVERIFIED = None
    if not SAM_KEY or not name: return None
    url = (f"https://api.sam.gov/entity-information/v4/exclusions?api_key={SAM_KEY}"
           f"&exclusionName={urllib.parse.quote(name)}")
    try:
        with urllib.request.urlopen(url, timeout=25) as r:
            d = json.load(r)
        # exclusionName is a substring search ("UPS" hits "Diesel Tune-Ups of RI") — only a
        # normalized exact-name match counts as a hit on THIS entity.
        target = _norm_entity(name)
        hits = []
        for x in d.get("excludedEntity") or []:
            i = x.get("exclusionIdentification") or {}
            nm = i.get("entityName") or " ".join(filter(None, [i.get("firstName"), i.get("lastName")]))
            if nm and _norm_entity(nm) == target:
                hits.append(f"{nm} (UEI {i.get('ueiSAM') or 'n/a'})")
        global SAM_UNVERIFIED
        tot, seen = (d.get("totalRecords") or 0), len(d.get("excludedEntity") or [])
        SAM_UNVERIFIED = (f"{tot} SAM name hits, only {seen} checked for exact match — verify manually"
                          if not hits and tot > seen else None)
        if hits:
            return f"SAM.gov exclusion/debarment on record ({len(hits)} exact-name match: {'; '.join(hits[:3])}) — do not engage."
    except Exception: return None
    return None

_ENTITY_SUFFIXES = {"inc","incorporated","llc","l","c","ltd","limited","corp","corporation","co",
                    "company","lp","llp","plc","the","pllc","pc"}

def _norm_entity(s):
    toks = re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split()
    return " ".join(t for t in toks if t not in _ENTITY_SUFFIXES)

def _load_sdn():
    global _SDN
    if _SDN is not None: return _SDN
    names = []
    try:
        import csv
        if (not os.path.exists(SDN_CSV)) or (time.time() - os.path.getmtime(SDN_CSV) > 7*86400):
            try:
                os.makedirs(os.path.dirname(SDN_CSV), exist_ok=True)
                open(SDN_CSV,"wb").write(urllib.request.urlopen("https://www.treasury.gov/ofac/downloads/sdn.csv", timeout=60).read())
            except Exception: pass
        for row in csv.reader(open(SDN_CSV, encoding="latin-1")):
            if len(row) >= 2 and row[1] and row[1] != "-0-": names.append(_norm(row[1]))
    except Exception: names = []
    _SDN = set(n for n in names if len(n) >= 5); return _SDN

def ofac_hit(name):
    n = _norm(name)
    if len(n) < 6: return None
    sdn = _load_sdn()
    if n in sdn: return f"Exact OFAC SDN sanctions match: '{name}' — do not engage."
    if len(n) >= 9:
        for s in sdn:
            if n in s: return f"OFAC SDN sanctions name match ('{name}' in a listed entity) — verify."
    return None

# ---- web + model ----
def tavily(query, depth="basic"):
    body = json.dumps({"api_key": TAVILY, "query": query, "max_results": 5,
                       "search_depth": depth, "include_answer": True}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        d = json.load(r)
    txt = (d.get("answer") or "") + "\n"; urls = []
    for x in d.get("results", [])[:5]:
        txt += f"- {x.get('title','')}: {x.get('content','')[:400]}\n"
        if x.get("url"): urls.append(x["url"])
    return txt.strip()[:4500], urls[:4]

RUBRIC = ("You are a due-diligence screener for Exos Aerospace (a US aerospace / government contractor). "
          "Given web findings about a company, decide if Exos can safely engage. Return STRICT JSON only: "
          "{\"verdict\":\"pass|caution|fail\",\"confidence\":\"low|medium|high\",\"summary\":\"one line\"}. "
          "pass = legitimate, real operating company, no red flags. caution = thin/unclear info, small/new, "
          "or minor concerns worth a human look. fail = scam / advance-fee / cold-broker / sanctioned / "
          "fraudulent / defunct / adverse legal findings. confidence reflects how strong the evidence is. "
          "The current date is August 2026 — recent 2024-2026 activity is NORMAL, not a red flag. Empty or "
          "genuinely ambiguous findings => caution + low confidence, never pass.")

def classify(company, dom, findings, deep=False):
    extra = (" This is a HIGH-STAKES counterparty (investor / Tier-1 / handles money, IP, or ITAR). Weigh "
             "adverse media, litigation, regulatory actions, ownership/parent, and foreign-ownership/CFIUS "
             "exposure. But only treat adverse media as FAIL-worthy when the findings SPECIFICALLY and "
             "CREDIBLY name THIS company; generic, unattributed, or ambiguous fraud/scam/SEC content is NOT "
             "grounds for fail — use caution instead.") if deep else ""
    payload = json.dumps({"model": MODEL, "stream": False, "format": "json",
        "messages": [{"role":"system","content":RUBRIC+extra},
                     {"role":"user","content":f"Company: {company}\nDomain: {dom}\n\nWeb findings:\n{findings or '(none found)'}"}]}).encode()
    with urllib.request.urlopen(urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type":"application/json"}), timeout=150) as r:
        d = json.load(r)
    raw = (d.get("message") or {}).get("content") or "{}"
    try: j = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S); j = json.loads(m.group(0)) if m else {}
    v = (j.get("verdict") or "caution").lower().strip()
    if v not in ("pass","caution","fail"): v = "caution"
    conf = (j.get("confidence") or "low").lower().strip()
    if conf not in ("low","medium","high"): conf = "low"
    return v, (j.get("summary") or "")[:240], conf

_FUND_HINT = ("capital", "ventures", "venture", " vc", "vc ", "fund", "equity", "partners",
              "angel", "family office", "investment", "invest", "holdings")

def _looks_like_fund(name):
    n = f" {(name or '').lower()} "
    return any(k in n for k in _FUND_HINT)

FUND_RUBRIC = (
    "You are validating whether a firm belongs on Exos Aerospace's ACTIVE Series A investor "
    "outreach list. Given web findings about the firm, decide whether it is BOTH: (a) an operating "
    "venture / investment / PE fund, family office, or angel group that invests in aerospace, space, "
    "defense, deep tech, or frontier/hard tech; AND (b) shows REAL funding traction in roughly the "
    "last 12 months — a new fund close, announced new investments, or actively deploying capital. "
    "The current date is September 2026, so 2025-2026 activity counts as recent. Return STRICT JSON "
    "only: {\"active\":true|false,\"confidence\":\"low|medium|high\",\"why\":\"one line\"}. "
    "active=true ONLY with specific evidence of recent investment/fundraising by THIS firm in a "
    "relevant sector. Not an investor, dormant, wrong sector, or thin/generic evidence => active=false.")

def fund_active_check(company, dom, findings):
    """Local-model gate: is this a currently-active space/tech fund with ~12-mo funding traction?
    Runs ONE targeted recency search (recent investments / new-fund close) on top of the deep-dive
    findings so the model has real evidence, then classifies. Conservative: only True on specific
    recent evidence at medium/high confidence — a thin 'maybe' does NOT re-surface a firm for cold
    contact. Returns (active_bool, n_searches)."""
    n = 0
    try:
        recent, _ = tavily(f'{company} {dom} recent investments 2025 2026 new fund close portfolio deals aerospace space deep tech', depth="advanced")
        n = 1
        findings = (findings or "") + "\n\n[RECENT FUND ACTIVITY]\n" + recent
    except Exception:
        pass
    try:
        payload = json.dumps({"model": MODEL, "stream": False, "format": "json",
            "messages": [{"role":"system","content":FUND_RUBRIC},
                         {"role":"user","content":f"Company: {company}\nDomain: {dom}\n\nWeb findings:\n{findings or '(none found)'}"}]}).encode()
        with urllib.request.urlopen(urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type":"application/json"}), timeout=150) as r:
            d = json.load(r)
        raw = (d.get("message") or {}).get("content") or "{}"
        try: j = json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, re.S); j = json.loads(m.group(0)) if m else {}
        active = j.get("active") in (True, "true", "1")
        conf = (j.get("confidence") or "low").lower().strip()
        return bool(active and conf in ("medium", "high")), n
    except Exception as e:
        print("  fund_active_check failed:", e)
        return False, n

def log_dossier(company, dom, verdict, summary):
    try:
        subprocess.run(["python3", os.path.join(WS,"scripts","log_dd.py"), "--firm", company, "--domain", dom,
                        "--verdict", verdict, "--requester", "CRM nightly DD engine", "--summary", summary],
                       capture_output=True, timeout=30)
    except Exception as e: print("log_dd failed:", e)

def route_decision(company, dom, summary, owner, deep_confirmed=False):
    """Human-in-the-loop: a DEEP-VERIFIED fail -> Decision for the owner to confirm do-not-engage
    before blacklisting. (Quick fails are cleared or confirmed by the deep-dive escalation first, so
    only deep-confirmed fails reach here.)"""
    store = load_json(DECISIONS, {"decisions": []})
    arr = store if isinstance(store, list) else store.setdefault("decisions", [])
    dk = f"dd-fail-{dom}"
    # Never re-raise once a decision for this domain already exists in ANY state (open OR answered).
    # (Previously this only skipped OPEN ones, so answering a decision let the next run spawn a new one —
    #  the re-nag Jon saw on ibc.doi.gov after confirming it twice.)
    if any(x.get("dedupeKey") == dk for x in arr):
        return
    today = datetime.datetime.now().isoformat(timespec="seconds")
    owner_email = OWNER_EMAIL.get((owner or "").lower().strip(), "jquinn@exosaero.com")
    lead = (f"Automated DD flagged {company} ({dom}) as FAIL and a DEEP-DIVE re-screen CONFIRMED it"
            if deep_confirmed else f"Automated DD flagged {company} ({dom}) as FAIL")
    arr.append({"id": f"dec-{dk}", "created": today, "updated": today, "source": "crm-dd-engine",
                "relatedItem": dom, "title": f"Confirm do-not-engage: {company}",
                "question": f"{lead} — {summary} Confirm do-not-engage (blacklist), or override to keep engaging with a reason?",
                "context": summary, "proposedAction": "Add to failed-DD registry (do-not-engage)",
                "type": "confirm", "options": ["Confirm do-not-engage", "Override — keep engaging (add reason)"],
                "priority": 80, "dedupeKey": dk, "status": "open", "answer": "", "note": "",
                "assignedTo": owner_email, "owner": owner, "deep_confirmed": deep_confirmed})
    json.dump(store, open(DECISIONS, "w"), indent=1)

def clear_decision(dom):
    """Delete any do-not-engage Decision for this domain — used when a company is NOT a fail (the
    deep-dive cleared it, or it passes on re-screen). A cleared company must not leave a stale
    do-not-engage Decision on the board."""
    try:
        store = load_json(DECISIONS, {"decisions": []})
        arr = store if isinstance(store, list) else store.get("decisions", [])
        dk = f"dd-fail-{dom}"
        kept = [x for x in arr if not (x.get("source") == "crm-dd-engine"
                                       and (x.get("dedupeKey") == dk or x.get("relatedItem") == dom))]
        if len(kept) != len(arr):
            if isinstance(store, list): store = kept
            else: store["decisions"] = kept
            json.dump(store, open(DECISIONS, "w"), indent=1)
            print(f"  cleared {len(arr)-len(kept)} do-not-engage decision(s) for {dom} (no longer a fail)")
    except Exception as e:
        print("clear_decision failed:", e)

# ---- core screen ----
def _screen_pass(dom, name, deep=False):
    """One DD pass. quick = 1 overview search + base rubric. deep = adds adverse-media + ownership
    searches (advanced Tavily) and the stricter, name-specific classify rubric."""
    findings, srcs = tavily(f'{name} {dom} company overview: what they do, leadership, funding, headquarters, legitimacy')
    n_searches = 1
    adverse_hay = ""
    if deep:
        try:
            adv, u2 = tavily(f'{name} {dom} lawsuit fraud investigation SEC regulatory sanction controversy', depth="advanced")
            own, u3 = tavily(f'{name} {dom} owner parent company acquisition foreign ownership headquarters country')
            findings += "\n\n[ADVERSE MEDIA]\n" + adv + "\n\n[OWNERSHIP]\n" + own
            srcs = (srcs + u2 + u3)[:8]; n_searches = 3
            adverse_hay = adv + " " + " ".join(u2)   # the evidence a FAIL rests on
        except Exception: pass
    v, s, conf = classify(name, dom, findings, deep=deep)
    # NAME-CONFUSION GUARD: downgrade a model FAIL to caution (human review) when the fail evidence
    # never references the entity's OWN domain label — i.e. a namesake collision (e.g. Scentience vs
    # 'Sentient'/'Sentient Technologies'). Prevents silently blocking a legitimate counterparty on
    # adverse media about a different, similarly-named company. Hard fails (SAM/OFAC/failed-registry)
    # never reach here — they short-circuit before classify.
    if v == "fail":
        label = re.sub(r"[^a-z0-9]", "", re.sub(r"^www\.", "", (dom or "").lower()).split(".")[0])
        evidence = adverse_hay if deep else findings
        hay = re.sub(r"[^a-z0-9]", "", (evidence or "").lower())
        if len(label) >= 5 and label not in hay:
            s = ("[name-confusion guard] " + s +
                 f" — adverse findings did not reference the entity's own domain ({dom}); routed to HUMAN REVIEW instead of auto-fail.")
            v = "caution"; conf = "low"
    rec = {"verdict":v,"summary":s,"source":"tavily+ollama","confidence":conf,
           "sources":srcs,"depth":("deep" if deep else "quick"),"_searches":n_searches}
    # On a deep screen of an investor-looking firm, also validate whether it's an ACTIVE space/tech
    # fund with ~12-mo traction. This is the flag the Series A worklist gates caution firms on:
    # a caution that's a validated active fund is re-included instead of auto-dropped.
    if deep and _looks_like_fund(name):
        active, fn = fund_active_check(name, dom, findings)
        rec["fund_active_12mo"] = active
        rec["_searches"] += fn
    return rec


def screen_one(dom, name, high_stakes=False, owner="Jon"):
    """Returns dict: verdict, summary, source, confidence, sources[], depth (+ escalation fields).

    ESCALATION GATE: a shallow (quick) scan FAIL is treated as UNCONFIRMED. Before any
    do-not-engage action, we auto-trigger a DEEP-DIVE re-screen (more sources + the stricter,
    name-specific rubric) to CONFIRM or CLEAR the finding — because companies Exos knows / has
    worked with were false-failing the initial shallow scan. Registry / SAM / OFAC fails are
    compliance-certain and skip this (they short-circuit above)."""
    comp = sam_excluded(name) or ofac_hit(name)
    if failed_dd_check(dom):
        return {"verdict":"fail","summary":"Matches Exos failed-DD registry (known do-not-engage).",
                "source":"failed_dd","confidence":"high","sources":[],"depth":"quick"}
    if comp:
        failed_dd_add(name, dom, comp)   # SAM/OFAC = compliance-certain, auto-blacklist
        return {"verdict":"fail","summary":comp,"source":"sam/ofac","confidence":"high","sources":[],"depth":"quick"}

    r = _screen_pass(dom, name, deep=high_stakes)

    # A non-high-stakes (quick) FAIL is not actioned until a deep-dive confirms it.
    if r["verdict"] == "fail" and not high_stakes:
        deep = _screen_pass(dom, name, deep=True)
        deep["escalated"] = True
        deep["initial_verdict"] = "fail"
        deep["initial_summary"] = r["summary"]
        deep["_searches"] = r.get("_searches", 1) + deep.get("_searches", 3)
        if deep["verdict"] == "fail":
            deep["summary"] = "Deep-dive CONFIRMED fail — " + deep["summary"]
        else:
            deep["summary"] = (f"Quick scan flagged FAIL, but deep-dive did NOT confirm "
                               f"(now {deep['verdict'].upper()}) — " + deep["summary"])
        return deep

    # A quick CAUTION is also UNCONFIRMED: caution = thin/unclear info, which a deeper scan
    # (more sources + stricter rubric) can resolve to a clean PASS or harden to a fail. Escalate
    # it the same way as a fail so cautions self-clear instead of parking on the list forever.
    if r["verdict"] == "caution" and not high_stakes:
        deep = _screen_pass(dom, name, deep=True)
        deep["escalated"] = True
        deep["initial_verdict"] = "caution"
        deep["initial_summary"] = r["summary"]
        deep["_searches"] = r.get("_searches", 1) + deep.get("_searches", 3)
        if deep["verdict"] == "pass":
            deep["summary"] = "Quick scan flagged CAUTION, but deep-dive CLEARED it (now PASS) — " + deep["summary"]
        elif deep["verdict"] == "fail":
            deep["summary"] = "Quick scan flagged CAUTION; deep-dive escalated to FAIL — " + deep["summary"]
        else:
            deep["summary"] = "Deep-dive re-screen still CAUTION — " + deep["summary"]
        return deep
    return r

def write_record(reg, dom, name, r, owner="Jon"):
    reg[dom] = {"company": name, "status": r["verdict"], "verdict": r["verdict"],
                "date": datetime.date.today().isoformat(), "summary": r["summary"],
                "source": r["source"], "confidence": r.get("confidence","low"),
                "depth": r.get("depth","quick"), "sources": r.get("sources", []),
                "escalated": r.get("escalated", False)}
    if r.get("escalated"):
        reg[dom]["initial_verdict"] = r.get("initial_verdict")
    if "fund_active_12mo" in r:
        reg[dom]["fund_active_12mo"] = bool(r["fund_active_12mo"])
    if r["verdict"] in ("fail","caution"):
        log_dossier(name, dom, r["verdict"], r["summary"])
    # Only a fail that has been deep-verified reaches the do-not-engage Decision. After the
    # escalation gate, any quick fail has already been re-screened deep; high-stakes fails were
    # deep from the start — so a routed fail is always deep-confirmed.
    if r["verdict"] == "fail" and r["source"] == "tavily+ollama":
        route_decision(name, dom, r["summary"], owner,
                       deep_confirmed=(r.get("escalated", False) or r.get("depth") == "deep"))
    else:
        # not a fail (incl. a deep-dive that CLEARED an initial fail) -> remove any stale do-not-engage Decision
        clear_decision(dom)

def needs_dd(rec):
    """Stale (>180d), never-scored, error/pending, a low-confidence pass, or a model FAIL that was
    never deep-verified -> re-screen (the last case runs the fail through the deep-dive escalation
    gate to confirm or clear it — retroactively fixes shallow false-positive fails)."""
    if not rec: return True
    if rec.get("status") in (None,"pending","error"): return True
    if rec.get("status") == "pass" and rec.get("confidence") == "low": return True
    if (rec.get("status") == "fail" and rec.get("source") == "tavily+ollama"
            and rec.get("depth") != "deep" and not rec.get("escalated")):
        return True
    # A shallow CAUTION was never deep-verified -> re-screen through the escalation gate to
    # clear it to pass or confirm it (keeps the worklist from parking unresolved cautions).
    if (rec.get("status") == "caution" and rec.get("source") == "tavily+ollama"
            and rec.get("depth") != "deep" and not rec.get("escalated")):
        return True
    # A caution on an investor-looking firm that was never fund-validated -> re-screen so the
    # deep-dive stamps fund_active_12mo (the flag the worklist gates caution re-inclusion on).
    # Covers already-deep caution funds the escalation clause above would otherwise skip.
    if (rec.get("status") == "caution" and rec.get("source") == "tavily+ollama"
            and _looks_like_fund(rec.get("company")) and "fund_active_12mo" not in rec):
        return True
    try:
        age = (datetime.date.today() - datetime.date.fromisoformat((rec.get("date") or "")[:10])).days
        if age > STALE_DAYS: return True
    except Exception: return True
    return False

def in_window():
    return NOW or datetime.datetime.now().time() < WINDOW_END

def main():
    reg = load_json(REG, {})
    if not isinstance(reg, dict): reg = {}

    if DOMAIN:   # real-time single-company mode (fired on new-lead capture)
        dom = DOMAIN.lower().strip(); name = COMPANY_ARG or dom
        try:
            r = screen_one(dom, name, high_stakes=False)
            write_record(reg, dom, name, r); json.dump(reg, open(REG,"w"), indent=1)
            print(f"[{r['verdict'].upper()}] {dom} ({r['confidence']}) — {r['summary'][:70]}")
        except Exception as e:
            print("single-domain DD error:", e)
        return

    comps = companies()
    pending = [(dom, m) for dom, m in comps.items() if needs_dd(reg.get(dom))]
    pending.sort(key=lambda x: (not x[1]["high_stakes"], x[0]))   # high-stakes first
    if LIMIT: pending = pending[:LIMIT]
    print(f"CRM domains: {len(comps)} | pending this run: {len(pending)} (high-stakes: {sum(1 for _,m in pending if m['high_stakes'])})")
    searches = 0; done = 0
    for dom, m in pending:
        if not in_window(): print("window closed (05:00) — stopping"); break
        if searches >= MAX_SEARCHES: print(f"search cap {MAX_SEARCHES} reached — stopping (cost guard)"); break
        try:
            r = screen_one(dom, m["name"], high_stakes=m["high_stakes"], owner=m["owner"])
            searches += r.pop("_searches", 1)
            write_record(reg, dom, m["name"], r, owner=m["owner"])
            done += 1
            json.dump(reg, open(REG,"w"), indent=1)
            print(f"[{r['verdict'].upper():7}] {'*' if m['high_stakes'] else ' '} {dom} ({r['confidence']}) — {r['summary'][:60]}")
        except Exception as e:
            reg[dom] = {"company": m["name"], "status": "error", "date": datetime.date.today().isoformat(), "summary": str(e)[:120]}
            json.dump(reg, open(REG,"w"), indent=1); print(f"[ERROR  ] {dom} — {e}")
        time.sleep(1)
    remaining = [d for d,m in comps.items() if needs_dd(reg.get(d))]
    print(f"\nprocessed {done} | searches {searches} (~${searches*0.008:.2f}) | remaining {len(remaining)} | "
          f"fails {sum(1 for v in reg.values() if isinstance(v,dict) and v.get('status')=='fail')}")
    if not remaining:
        open(os.path.join(WS,"logs","crm-dd-complete.flag"),"w").write(datetime.datetime.now().isoformat())
        try: subprocess.run(["python3", os.path.join(WS,"scripts","crm_dd_announce.py")], capture_output=True, timeout=180)
        except Exception as e: print("announce failed:", e)
        print("ALL CRM COMPANIES CLEARED — completion flag written; team announcement sent.")

if __name__ == "__main__":
    main()
