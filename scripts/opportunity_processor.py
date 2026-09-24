#!/usr/bin/env python3
"""
opportunity_processor.py — Exos Opportunity Action Engine

Assigns one worker agent per live opportunity and grinds it to a SINGLE
ready-to-send next step: owner named, deliverable drafted, routed to Mission
Control as SEND / TASK / DECISION / CLOSE.

Defaults (approved 2026-06-22):
  - Wave size 15, ranked hottest-first (run twice daily)
  - Every external email gated behind a Decisions card (nothing auto-sends)
  - Local Qwen for the grind; Claude (Opus) only for top-tier deals

Modes:
  --dry-run  (default)  Report only. No MC posts, no tracker writeback, no drafts sent.
  --live                Stage drafts, POST routes to MC, write next_action back to tracker.
  --limit N             Wave size (default 15)
  --top-only            Only process top-tier opportunities this run
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("opportunity-engine")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gt = _gis_transient(v); _gevent(_GRUN, "transient_skip" if _gt else "error", status="transient" if _gt else "error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---


import os, sys, re, json, time, argparse, urllib.request
from datetime import datetime, timezone, timedelta

WORKSPACE   = "/Users/exomac/.openclaw/workspace"
OPP_JSON    = os.path.join(WORKSPACE, "mission-control/data/opportunities.json")
TRACKER_MD  = os.path.join(WORKSPACE, "opportunities-tracker.md")
DRAFTS_DIR  = os.path.join(WORKSPACE, "drafts")
STATE_FILE  = os.path.join(WORKSPACE, "mission-control/data/opportunity-processor-state.json")
REPORT_DIR  = os.path.join(WORKSPACE, "drafts")
SECRETS     = "/Users/exomac/.openclaw/secrets.json"
MC_BASE     = "http://127.0.0.1:8080"
MC_TOKEN    = os.path.join(WORKSPACE, "mission-control/data/.decisions-token")

# Governance router (execute-vs-escalate). Soft: never let it break BD processing.
try:
    import sys as _gsys2
    _gsys2.path.insert(0, os.path.join(WORKSPACE, "governance"))
    import route as _gov
except Exception:
    _gov = None
AGENT_CLASS = "opportunity-engine"
# CLOSE on an opp scoring below this is reversible bookkeeping -> execute (auto-file),
# don't ask Jon. Above it, a CLOSE still surfaces (closing value deserves a glance).
CLOSE_EXECUTE_FLOOR = float(os.environ.get("OPP_CLOSE_FLOOR", "35"))

sys.path.insert(0, os.path.join(WORKSPACE, "scripts"))
try:
    import kimi_bd  # gated Kimi K3 BD tier; screens content, falls back to local qwen on any issue/block
except Exception:
    kimi_bd = None

OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3.6:35b-a3b"
CLAUDE_MODEL = "claude-opus-4-8"

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW_ISO = datetime.now(timezone.utc).isoformat()

# Statuses that mean "do not work this" (dead / handled / out)
# ITAR-HOLD = De-Risk Orbital foreign target awaiting export clearance; skip until Jon
# clears it (status flips to NEW via the Decision). Treated as do-not-work, not dead.
DEAD_MARKERS = ["CLOSED", "SCAM", "DEAD", "DROPPED", "PASS", "DO NOT ENGA", "LISTING DROP", "INVESTMENT PASS", "ITAR-HOLD"]
# Top-tier triggers → Claude/Opus
TOP_KEYWORDS = ["rofr", "scorpius", "series a", "acquisition", "stratfi", "osc ", "office of strategic capital"]
TOP_VALUE_FLOOR = 10_000_000

# ── helpers ──────────────────────────────────────────────
def load_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default

def mc_token():
    try:
        with open(MC_TOKEN) as f: return f.read().strip()
    except Exception: return ""

def secret(name):
    return load_json(SECRETS, {}).get(name, "")

def mc_post(path, payload):
    try:
        req = urllib.request.Request(MC_BASE + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "x-exo-token": mc_token()},
            method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  ! MC post {path} failed: {e}"); return False

def parse_value(v):
    """Best-effort dollar value from a free-text value field."""
    if not v: return 0
    s = str(v).lower().replace(",", "")
    m = re.search(r"\$?\s*([\d.]+)\s*([mbk])", s)
    if m:
        n = float(m.group(1)); unit = m.group(2)
        return int(n * {"k":1e3,"m":1e6,"b":1e9}[unit])
    m = re.search(r"\$\s*([\d.]+)", s)
    return int(float(m.group(1))) if m else 0

STAGE_HEAT = {
    "ACTIVE":1.0,"DUE DILIGENCE":1.0,"MEETING HELD":0.9,"MEETING SCHEDULED":0.9,
    "SUBMITTED":0.8,"DRAFT":0.85,"SCHEDULING":0.8,"EVALUATING":0.7,
    "NEW":0.75,"TRACKING":0.5,"FOLLOW-UP NEEDED":0.85,"ACTION NEEDED":0.95,
}

def is_dead(opp):
    s = (opp.get("status") or "").upper()
    return any(m in s for m in DEAD_MARKERS)

# ── past-due prune (shared logic with dashboard-data-generator.py) ────────
# A "past-due dead" opp has a concrete deadline strictly before today (UTC) AND
# a status that is NOT a live/acted pursuit. These are treated as do-not-work.
_MONTHS = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}
_RANGE_MARKERS = ("→","->"," to ","through","window")
_LIVE_STATUS_TOKENS = [
    "ACTIVE","SUBMITTED","MEETING","DILIGENCE","SCHEDUL","EXECUT",
    "IN PROGRESS","AWARD","SIGNED","RESOLVED","PITCH DELIVERED",
    "OUTREACH SENT","FOLLOW-UP","INTAKE",
]

def _is_live_status(status):
    s = (status or "").upper()
    return any(tok in s for tok in _LIVE_STATUS_TOKENS)

def _parse_dates(text, today):
    found = []
    def add_no_year(month, day):
        try:
            d = datetime(today.year, month, day).date()
        except ValueError:
            return
        if (today - d).days > 7:
            try:
                d = datetime(today.year + 1, month, day).date()
            except ValueError:
                pass
        found.append(d)
    for m in re.finditer(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text):
        try: found.append(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date())
        except ValueError: pass
    month_alt = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
                 r"jul(?:y)?|aug(?:ust)?|sep(?:t)?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
    for m in re.finditer(month_alt + r"\.?\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?", text, re.IGNORECASE):
        mon = _MONTHS[m.group(1)[:3].lower()]; day = int(m.group(2))
        if m.group(3):
            try: found.append(datetime(int(m.group(3)), mon, day).date())
            except ValueError: pass
        else:
            add_no_year(mon, day)
    for m in re.finditer(r"\b(\d{1,2})\s+" + month_alt + r"\.?(?:\s+(\d{4}))?", text, re.IGNORECASE):
        day = int(m.group(1)); mon = _MONTHS[m.group(2)[:3].lower()]
        if m.group(3):
            try: found.append(datetime(int(m.group(3)), mon, day).date())
            except ValueError: pass
        else:
            add_no_year(mon, day)
    return found

def _deadline_is_past(due_text, today=None):
    """True only if a concrete date parses from due_text and it is < today.
    No concrete date (TBD / rolling / quarter-only like 'Q1 2027') => False (keep)."""
    if today is None:
        today = datetime.now(timezone.utc).date()
    if not due_text:
        return False
    text = str(due_text)
    dates = _parse_dates(text, today)
    if not dates:
        return False
    if len(dates) > 1 and any(mark in text.lower() for mark in [m.lower() for m in _RANGE_MARKERS]):
        chosen = max(dates)
    elif len(dates) > 1:
        future = sorted(d for d in dates if d >= today)
        chosen = future[0] if future else max(dates)
    else:
        chosen = dates[0]
    return chosen < today

def is_past_due_dead(opp):
    return _deadline_is_past(opp.get("due")) and not _is_live_status(opp.get("status",""))

def is_top(opp):
    if parse_value(opp.get("value")) >= TOP_VALUE_FLOOR: return True
    blob = (opp.get("title","") + " " + opp.get("description","") + " " + opp.get("category","")).lower()
    return any(k in blob for k in TOP_KEYWORDS)

def urgency(opp):
    due = opp.get("due") or ""
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", due)
    if not m: return 0.6
    try:
        d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        days = (d - datetime.now()).days
        if days < 0: return 0.4            # overdue / passed
        if days <= 7: return 1.0
        if days <= 30: return 0.85
        return 0.65
    except Exception: return 0.6

def score(opp):
    s = (opp.get("status") or "").upper()
    heat = max([v for k,v in STAGE_HEAT.items() if k in s] or [0.6])
    val = parse_value(opp.get("value"))
    val_score = min(1.0, 0.3 + (val / 25_000_000)) if val else 0.45
    base = int((opp.get("priority") or 40))
    return round((val_score * heat * urgency(opp)) * 100 + base/10, 2)

# ── worker model ─────────────────────────────────────────
AGENT_CONTRACT = """You are an Exos Aerospace BD action agent. Exos Aerospace Systems & Technologies, Inc. is one of only three FAA-licensed reusable rocket launch providers in the US — a suborbital reusable test platform (BLK3 PSRLV) that de-risks orbital programs; affiliate Scorpius holds TRL-9 Type-5 composite cryo tanks with lunar heritage. CEO John Quinn. Greenville, TX.

PUBLISHED RATE CARD (price every quote off this; source exosaero.com/pricing): Full Payload 135kg = $1,012,500; Half 68kg = $510,000; Quarter 34kg = $255,000; 1U = $7,500; 2U = $15,000; 3U = $22,500; 6U = $45,000; custom = max($7,500/kg, $60,000 per 100mm layer); always-add basic integration $500; large-payload integration $5,000; add-ons: live telemetry $25,000, precision pointing $5,000, sealed env $1,200, side mount w/ window/antenna $1,000, in-flight triggers $1,000, external power $750. "Not a final price; discounts for payloads over 20kg" — for any >20kg discount, route DECISION (schedule pending, ref D-109). Never invent a discount.

You are handed ONE opportunity. Reduce it to the SINGLE highest-leverage next step and produce the artifact to execute it. Be concrete — never output placeholders like "[POC TBD]" or "research required"; if a contact is unknown, state the specific named person/office to reach and your best email/role.

Return STRICT JSON only, no prose, with this exact shape:
{
  "next_step": "one sentence: verb + object + recipient",
  "owner": "Exos (Jon)" or a named team member,
  "route": "SEND" | "TASK" | "DECISION" | "CLOSE",
  "deliverable": {
    "type": "email" | "doc" | "none",
    "to": "recipient email or name",
    "cc": "",
    "subject": "if email",
    "body": "the full, ready-to-send draft — no placeholders"
  },
  "confidence": 0.0-1.0,
  "blockers": "the one thing needed to unblock, or empty"
}

Routing rules:
- SEND = an external email is ready to go (owner just approves).
- TASK = internal work needed first; deliverable.type may be "none".
- DECISION = needs Jon's go/no-go or a missing input only he has AND it is consequential (money, a real commitment, a gov/investor/contract call). A routine outreach approval is NOT a DECISION.
- CLOSE = dead/not worth pursuing; explain why in blockers.
CONSIDER THE SOURCING — do NOT manufacture speculative "maybe" decisions. NEVER route DECISION to ask whether a warm/known contact or intro path EXISTS, or to "confirm whether" a relationship or connection is available. That is premature relationship-fishing. Only propose a warm-intro step if a SPECIFIC named contact is already confirmed in our CRM/relationships. If a warm path might help but is unconfirmed, route TASK and note it can be supplied at submission time — Jon will provide the intro if and when it is actually needed. Never ask Jon to validate a hypothetical relationship.
Rules: never overstate traction or claim relationships not confirmed. External docs say "John". Email only ever goes to Jon for approval first."""

# ExO3 #3: prepend the confirmed MTP-as-protocol so opportunity decisions ladder to
# Exos's MTP + hard constraints + decision-priority (config/mtp-protocol.json).
try:
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    import mtp as _mtp
    AGENT_CONTRACT = _mtp.protocol_prompt() + "\n\n" + AGENT_CONTRACT
except Exception:
    pass


def build_prompt(opp):
    return (f"OPPORTUNITY:\n"
            f"id: {opp.get('id')}\n"
            f"title: {opp.get('title')}\n"
            f"status: {opp.get('status')}\n"
            f"type: {opp.get('type')}\n"
            f"category: {opp.get('category')}\n"
            f"value: {opp.get('value')}\n"
            f"due: {opp.get('due')}\n"
            f"current_next_action: {opp.get('next_action')}\n"
            f"description: {opp.get('description')}\n\n"
            f"Produce the single next step now as strict JSON.")

def extract_json(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        try: return json.loads(text[a:b+1])
        except Exception: pass
    return None

def call_ollama(prompt, attempts=2):
    """Non-sensitive BD analysis. Prefers the cheap large-context Kimi K3 tier (export-control
    gated); ANY K3 failure/block/parse-miss falls straight through to local qwen — no regression."""
    if kimi_bd is not None and os.environ.get("OPP_USE_K3", "1") == "1":
        try:
            txt = kimi_bd.ask(prompt, label="opp-engine",
                              system=AGENT_CONTRACT + "\nRespond ONLY with valid JSON, no prose.")
            res = extract_json(txt)
            if res:
                return res
        except Exception as e:
            print(f"    k3 fallback→qwen: {str(e)[:80]}")
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(OLLAMA_URL,
                data=json.dumps({"model": OLLAMA_MODEL, "format": "json", "stream": False,
                    "messages": [{"role":"system","content":AGENT_CONTRACT},
                                 {"role":"user","content":prompt}],
                    "options": {"temperature": 0.3}}).encode(),
                headers={"Content-Type":"application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            res = extract_json(d.get("message",{}).get("content",""))
            if res: return res
            last = "empty/parse-fail"
        except Exception as e:
            last = str(e)
        print(f"    qwen attempt {i+1}/{attempts} failed: {str(last)[:80]}")
    return None

# Top-tier items run on the Claude Code CLI (the $200/mo Max plan) — NOT the
# pay-as-you-go API key (which is dead). One-time check; self-heals if the CLI
# goes away → everything falls back to local qwen.
import subprocess, shutil
_CLAUDE_OK = None
def claude_ok():
    global _CLAUDE_OK
    if _CLAUDE_OK is not None: return _CLAUDE_OK
    if not shutil.which("claude"):
        _CLAUDE_OK = False; return False
    try:
        p = subprocess.run(["claude", "-p", "--model", "opus"], input="Reply with exactly: PONG",
                           capture_output=True, text=True, timeout=60)
        _CLAUDE_OK = "PONG" in (p.stdout or "")
    except Exception as e:
        print(f"  claude CLI unavailable ({str(e)[:45]}) — routing ALL items through local qwen")
        _CLAUDE_OK = False
    if not _CLAUDE_OK:
        print("  claude CLI check failed — routing ALL items through local qwen")
    return _CLAUDE_OK

def call_claude(prompt):
    """Top-tier worker via the Claude Code CLI on the Max plan (no API key needed)."""
    full = AGENT_CONTRACT + "\n\n" + prompt
    try:
        p = subprocess.run(["claude", "-p", "--model", "opus"], input=full,
                           capture_output=True, text=True, timeout=150)
        return extract_json(p.stdout or "")
    except Exception as e:
        print(f"    claude CLI call failed: {str(e)[:80]}")
        return None

def process_one(opp):
    top = is_top(opp)
    use_claude = top and claude_ok()          # only use Claude if the key actually works
    worker = "claude-opus" if use_claude else "qwen-local"
    res = None
    try:
        res = call_claude(build_prompt(opp)) if use_claude else call_ollama(build_prompt(opp))
    except Exception as e:
        print(f"  ! {opp.get('id')} primary worker error: {str(e)[:80]}")
    if not res and use_claude:                # Claude path failed → local fallback
        print(f"    falling back to qwen for {opp.get('id')}")
        res = call_ollama(build_prompt(opp)); worker = "qwen-fallback"
    if res:
        res["_worker"] = worker; res["_tier"] = "top" if top else "standard"
    else:
        print(f"  ! {opp.get('id')} produced no usable result")
    return res

# ── routing (live) ───────────────────────────────────────
def _write_docx(path, opp, res, d):
    """Render a deliverable as a Word document. Jon reviews/sends Word, never .md."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    doc = Document()
    title = doc.add_paragraph()
    tr = title.add_run(f"Next step for {opp.get('id')} — {opp.get('title')}")
    tr.bold = True; tr.font.size = Pt(14); tr.font.color.rgb = RGBColor(0x0B,0x22,0x40)
    meta = doc.add_paragraph()
    mr = meta.add_run(f"Owner: {res.get('owner')}   ·   Route: {res.get('route')}   ·   Worker: {res.get('_worker')}")
    mr.font.size = Pt(9); mr.italic = True
    ns = doc.add_paragraph()
    ns.add_run("Next step: ").bold = True
    ns.add_run(str(res.get("next_step","")))
    if d.get("type") == "email":
        for label in ("to","cc","subject"):
            if d.get(label):
                p = doc.add_paragraph()
                p.add_run(f"{label.capitalize()}: ").bold = True
                p.add_run(str(d.get(label,"")))
        doc.add_paragraph()
        for para in str(d.get("body","")).split("\n"):
            doc.add_paragraph(para)
    else:
        for para in str(d.get("body","")).split("\n"):
            doc.add_paragraph(para)
    doc.save(path)

def stage_deliverable(opp, res):
    d = res.get("deliverable") or {}
    if d.get("type") not in ("email","doc"): return None
    safe = re.sub(r"[^A-Za-z0-9_-]","_", opp.get("id","opp"))
    # Word is the deliverable format Jon works from. Try .docx; fall back to .md only if python-docx is missing.
    try:
        path = os.path.join(DRAFTS_DIR, f"OPP_{safe}_{TODAY}.docx")
        _write_docx(path, opp, res, d)
        return os.path.relpath(path, WORKSPACE)
    except Exception as e:
        print(f"    ! docx render failed ({e}); writing .md fallback")
        path = os.path.join(DRAFTS_DIR, f"OPP_{safe}_{TODAY}.md")
        with open(path,"w") as f:
            f.write(f"# Next step for {opp.get('id')} — {opp.get('title')}\n\n")
            f.write(f"**Owner:** {res.get('owner')}  ·  **Route:** {res.get('route')}  ·  **Worker:** {res.get('_worker')}\n\n")
            f.write(f"**Next step:** {res.get('next_step')}\n\n---\n\n")
            if d.get("type")=="email":
                f.write(f"To: {d.get('to','')}\nCc: {d.get('cc','')}\nSubject: {d.get('subject','')}\n\n{d.get('body','')}\n")
            else:
                f.write(d.get("body",""))
        return os.path.relpath(path, WORKSPACE)

def _ingest_decision(payload):
    """Tag the payload for eval attribution (agentClass + correlationId), then post."""
    if _gov:
        try: payload = _gov.escalate(payload, AGENT_CLASS)
        except Exception: pass
    mc_post("/api/decisions/ingest", payload)

def parse_deadline(text):
    """Extract a submission deadline from opportunity text (mirrors the inbox-capture fix in
    mission-control-imap.py) so decision/task cards carry a real due date and surface as
    overdue instead of rotting silently. Anchored to deadline keywords so we don't grab
    version/meeting/program dates."""
    if not text: return None
    kw  = r'(?:due(?:\s+by)?|deadline|closes?|close date|submission deadline|submit(?:\s+by)?|apply by|response due|proposals?\s+due|noo\s+closes?|white\s*paper\s+due)'
    mon = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?'
    num = r'\d{1,2}/\d{1,2}(?:/\d{2,4})?'
    m = (re.search(rf'{kw}[:\s]+({mon})', text, re.I) or re.search(rf'{kw}[:\s]+({num})', text, re.I))
    if not m: return None
    try:
        from dateutil import parser as _dp
        return _dp.parse(m.group(1)).strftime('%Y-%m-%dT23:59:59Z')
    except Exception:
        return None

def route_to_mc(opp, res, draft_path):
    route = (res.get("route") or "TASK").upper()
    rel = opp.get("id","")
    sc = score(opp)
    # Parse a real submission deadline from the opportunity so downstream cards can go overdue.
    due = parse_deadline(f"{opp.get('title','')} {opp.get('description','') or ''} {res.get('next_step','') or ''}") or opp.get("due")
    if route == "SEND":
        d = res.get("deliverable") or {}
        _ingest_decision({
            "dedupeKey": f"opp-send-{rel}",
            "title": f"Send: {d.get('subject') or opp.get('title')[:80]}",
            "question": f"Send this email to {d.get('to','recipient')}?",
            "context": f"{res.get('next_step')}\n\nDraft staged: {draft_path}",
            "proposedAction": (d.get("body","") or "")[:1200],
            "type": "yesno", "options": ["Send","Edit","Hold"],
            "priority": "high" if res.get("_tier")=="top" else "med",
            "relatedItem": opp.get("title","")[:120], "source": "Opportunity Engine", "dueDate": due})
    elif route == "DECISION":
        # Backstop (Jon 2026-07-31): never surface speculative "does a warm/known contact or intro
        # path EXIST?" asks as decisions — that's premature relationship-fishing. Divert to the
        # research feed (recoverable); Jon supplies a warm intro at submission time if actually needed.
        _SPECULATIVE = re.compile(
            r"confirm whether|whether (?:a |we have |there is |an? )?.{0,40}?(?:warm|known|existing|potential)\b"
            r".{0,40}?(?:contact|intro|introduction|relationship|connection|path|lead)|"
            r"\bdo we (?:have|know)\b|is there a (?:warm|known)|can .{0,30}? intro\b|"
            r"ask jon (?:to confirm|whether)|if (?:we|there) .{0,20}? (?:a )?(?:warm|known) ", re.I)
        ns = res.get("next_step", "")
        if _SPECULATIVE.search(ns):
            mc_post("/api/research/ingest", {
                "id": f"opp-warmpath-{rel}", "title": f"Possible warm path (parked): {opp.get('title','')[:100]}",
                "date": TODAY, "category": "BD Intel", "source": "Opportunity Engine",
                "highlights": [f"Speculative warm-intro step suppressed (no confirmed contact): {ns[:160]}",
                               "Not a decision — Jon provides a warm intro at submission time only if actually needed."],
                "body": f"{ns}\n\nParked rather than asked. Sourcing unconfirmed."})
            return
        # Meta-redundant suppression (Jon 2026-08-26, "reduce the human review cue"): a decision whose
        # ACTION is merely to route/deliver/brief/email something TO Jon for his approval is not a
        # decision — it's Exo asking permission to do the internal delivery Jon already directed.
        # Strip the wrapper: do the work (file to the task feed) instead of consuming a CEO decision.
        # GUARDED — never fires on gov/.mil/investor/contract/ITAR/consequential asks (those still
        # need Jon), and never on an external SEND (route==SEND handles those; Jon keeps send-approval).
        _META_REDUNDANT = re.compile(
            r"(?:email|e-?mail|route|deliver|send|surface|forward|escalate|present|bring|package)\b"
            r".{0,70}?\b(?:jon|john)\b"
            r".{0,90}?(?:for (?:his |your )?(?:approval|go|review|sign-?off|go/?no-?go|decision)|"
            r"requesting (?:his |your )?(?:go|approval|go/?no-?go|sign-?off)|"
            r"to (?:approve|review|decide|sign))|"
            r"deliver (?:a |an )?.{0,40}?(?:brief|memo|summary|readout|package) to (?:jon|john)|"
            r"get (?:jon|john)'?s? (?:go|approval|sign-?off|go/?no-?go)\b", re.I)
        _CONSEQ_KEEP = re.compile(
            r"\.gov\b|\.mil\b|\bafrl\b|\bdarpa\b|\bonr\b|space\s?force|air\s?force|\bnro\b|\bmda\b|"
            r"spacewerx|\bnasa\b|\bsbir\b|\bsttr\b|tacfi|stratfi|\bosc\b|searf|"
            r"series\s*a|\binvestor\b|capital\s+raise|term\s?sheet|\b409a\b|\bmnda\b|\bnda\b|counsel|"
            r"\bitar\b|export.?control|\bddtc\b|\brdre\b|\brde\b|type-?5|scorpius|rofr|\bcui\b", re.I)
        _blob_mr = f"{ns} {opp.get('title','')} {res.get('blockers','') or ''} {res.get('deliverable',{}) if isinstance(res.get('deliverable'),str) else ''}"
        if _META_REDUNDANT.search(ns) and not _CONSEQ_KEEP.search(_blob_mr):
            mc_post("/api/research/ingest", {
                "id": f"opp-metadeliver-{rel}", "title": f"Action (auto, no CEO gate): {opp.get('title','')[:100]}",
                "date": TODAY, "due": due, "category": "BD Intel", "source": "Opportunity Engine",
                "highlights": [f"**Next step:** {ns[:180]}",
                               "Meta-ask suppressed — Exo performs the internal delivery Jon already directed; "
                               "no CEO decision consumed. Any resulting external send still surfaces its own send-approval."],
                "body": f"{ns}\n\nOwner: {res.get('owner','Exo')}\nDraft: {draft_path or 'n/a'}"})
            return
        _ingest_decision({
            "dedupeKey": f"opp-dec-{rel}",
            "title": f"{opp.get('id')}: {res.get('next_step','')[:80]}",
            "question": res.get("next_step","Decision needed"),
            "context": res.get("blockers",""), "proposedAction": res.get("next_step",""),
            "type":"yesno","options":["Approve","Reject"],
            "priority":"high" if res.get("_tier")=="top" else "med",
            "relatedItem": opp.get("title","")[:120], "source":"Opportunity Engine", "dueDate": due})
    elif route == "CLOSE":
        # Execute-path: a low-scoring CLOSE is reversible bookkeeping. File it to the
        # research feed (recoverable) and log it; do NOT consume an inbox decision.
        # A higher-scoring CLOSE still escalates (closing potential value gets a glance).
        if _gov and _gov.delegation_on(AGENT_CLASS) and sc < CLOSE_EXECUTE_FLOOR:
            mc_post("/api/research/ingest", {
                "id": f"opp-autoclose-{rel}", "title": f"Auto-triaged (low score {sc}): {opp.get('title')[:110]}",
                "date": TODAY, "category":"BD Intel","source":"Opportunity Engine",
                "highlights":[f"**Auto-archived** by opportunity-engine (score {sc} < {CLOSE_EXECUTE_FLOOR})",
                              f"**Reason:** {res.get('blockers') or 'low priority / dead'}",
                              "Reversible: reopen from the research feed if needed."],
                "body": f"Auto-closed low-value opportunity {rel}. Reason: {res.get('blockers') or 'n/a'}"})
            try: _gov.executed(AGENT_CLASS, "auto-archive low-value CLOSE", rel, score=sc)
            except Exception: pass
        else:
            _ingest_decision({
                "dedupeKey": f"opp-close-{rel}",
                "title": f"Archive {opp.get('id')}? {opp.get('title')[:60]}",
                "question":"Archive this opportunity?","context": res.get("blockers",""),
                "proposedAction":"Mark CLOSED in tracker","type":"yesno",
                "options":["Archive","Keep"],"priority":"low",
                "relatedItem": opp.get("title","")[:120],"source":"Opportunity Engine"})
    else:  # TASK
        mc_post("/api/research/ingest", {
            "id": f"opp-task-{rel}", "title": f"Action: {opp.get('title')[:120]}",
            "date": TODAY, "due": due, "category":"BD Intel","source":"Opportunity Engine",
            "highlights":[f"**Deadline:** {due or 'none'}",
                          f"**Next step:** {res.get('next_step')}",
                          f"**Owner:** {res.get('owner')}",
                          f"**Blockers:** {res.get('blockers') or 'none'}"],
            "body": f"{res.get('next_step')}\n\nOwner: {res.get('owner')}\nDraft: {draft_path or 'n/a'}"})
        if _gov:
            try: _gov.executed(AGENT_CLASS, "filed TASK to research feed", rel, score=sc)
            except Exception: pass

# ── main ─────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--top-only", action="store_true")
    ap.add_argument("--only-prefix", default="",
                    help="Only process opps whose id starts with this prefix (e.g. PAY). "
                         "Dedicated lane so smaller-value items get priced instead of "
                         "losing the global top-N wave to high-value BD/fundraise opps.")
    args = ap.parse_args()
    live = args.live

    opps = load_json(OPP_JSON, {}).get("opportunities", [])
    state = load_json(STATE_FILE, {})
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()

    live_opps = [o for o in opps if not is_dead(o) and not is_past_due_dead(o)]
    if args.only_prefix:
        live_opps = [o for o in live_opps if str(o.get("id","")).startswith(args.only_prefix)]
    if args.top_only:
        live_opps = [o for o in live_opps if is_top(o)]
    # skip ones processed in last 24h
    fresh = [o for o in live_opps if state.get(o.get("id",""),{}).get("last","") < cutoff]
    fresh.sort(key=score, reverse=True)
    wave = fresh[:args.limit]

    print(f"[{TODAY}] Opportunity Engine — mode={'LIVE' if live else 'DRY-RUN'} | "
          f"live opps={len(live_opps)} fresh={len(fresh)} wave={len(wave)}")

    report = [f"# Opportunity Engine — {'LIVE' if live else 'DRY-RUN'} {TODAY}\n",
              f"Live opportunities: {len(live_opps)} · processing top {len(wave)} by score\n"]
    results = []
    for i, opp in enumerate(wave, 1):
        tier = "TOP" if is_top(opp) else "std"
        print(f"  [{i}/{len(wave)}] {opp.get('id')} ({tier}, score {score(opp)}) {opp.get('title','')[:55]}")
        res = process_one(opp)
        if not res:
            report.append(f"## {opp.get('id')} — ⚠️ no result\n{opp.get('title')}\n")
            continue
        draft_path = stage_deliverable(opp, res) if (live or True) else None  # stage drafts even in dry-run
        if live:
            route_to_mc(opp, res, draft_path)
            state[opp.get("id","")] = {"last": datetime.now().isoformat(), "route": res.get("route")}
        results.append((opp, res, draft_path))
        report.append(
            f"## {opp.get('id')} — {res.get('route')} · {tier}\n"
            f"**{opp.get('title')}**\n\n"
            f"- **Next step:** {res.get('next_step')}\n"
            f"- **Owner:** {res.get('owner')}\n"
            f"- **Deliverable:** {(res.get('deliverable') or {}).get('type')} → {(res.get('deliverable') or {}).get('to','')}\n"
            f"- **Confidence:** {res.get('confidence')} · **Blockers:** {res.get('blockers') or 'none'}\n"
            f"- **Draft:** {draft_path or 'n/a'} · _worker: {res.get('_worker')}_\n")

    if live:
        with open(STATE_FILE,"w") as f: json.dump(state, f, indent=2)

    # route tally
    tally = {}
    for _,r,_ in results: tally[r.get("route","?")] = tally.get(r.get("route","?"),0)+1
    report.insert(2, f"\n**Routes:** " + ", ".join(f"{k}={v}" for k,v in sorted(tally.items())) + "\n")

    rpt_path = os.path.join(REPORT_DIR, f"opportunity-engine-{'live' if live else 'dryrun'}-{TODAY}.md")
    with open(rpt_path,"w") as f: f.write("\n".join(report))
    print(f"\nReport: {rpt_path}")
    print(f"Routes: {tally}")
    if live:
        mc_post("/api/research/ingest", {
            "id": f"opp-engine-run-{TODAY}", "title": f"Opportunity Engine run — {TODAY}",
            "date": TODAY, "category":"BD Intel", "source":"Opportunity Engine",
            "highlights":[f"Processed {len(results)} opportunities",
                          "Routes: " + ", ".join(f"{k}={v}" for k,v in sorted(tally.items()))],
            "body": "\n".join(report)[:4000]})
    return rpt_path

if __name__ == "__main__":
    main()
    # Refresh the AI Mission Desk board from live state after each run (best-effort;
    # never let a board-refresh failure affect the processor's own exit).
    try:
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "program_state.py")], timeout=120)
    except Exception as _e:
        print(f"[program_state] refresh skipped: {_e}")
