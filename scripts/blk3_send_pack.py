#!/usr/bin/env python3
"""blk3_send_pack.py: BLK3 payload-prospect "send pack" (Jon, Decision D-7281980 option A, 2026-10-07).

Narrow exception to the no-auto-send rule: BLK3 payload-prospect outreach ONLY, and an email goes out
ONLY after Lizi's (or Jon's) HUMAN click on the day's send-pack Decision. Modeled on
backlog_grind_apply.py (propose -> Decision via ingest API -> human-click-gated apply).

  build [--dry-run]     (launchd com.exos.blk3-send-pack-build, weekdays 08:30 CT)
      Picks up to 8 prospects never emailed:
        1. student-verified leads (Supabase tasks tagged utd-lead, state Done; students' notes give the
           verified contact/email + corrections; do-not-contact notes are honored)
        2. oldest READY/DRAFT PAY- opportunities that have a draft in drafts/payload-outreach-drafts.md
           and a non-guessed address in the pipeline/tracker
      Skips: anything in logs/outreach-sent-registry.json (address, or domain within 60 days) and any
      address/domain in ~/.msmtp.log within 60 days. Writes a FINAL email per item (Lizi's voice,
      "early 2027", no prices, no unverifiable claims, public contact details), lints it, and posts ONE
      Decision (assignedTo/approver Lizi) with numbered items. Plan -> mission-control/data/blk3-send-pack-plan.json.

  apply [--dry-run] [--simulate "ANSWER|NOTE"]   (launchd com.exos.blk3-send-pack-apply, every 600s)
      Acts only if the plan's Decision is answered by a HUMAN (answeredByEmail = lquinn@ or jquinn@).
      "Send approved items" -> sends every item except per-item holds in the note ("hold 2 5");
      "Hold all" -> nothing. Re-checks the registry, guardrails and the daily cap before EACH send.
      Records each send in the registry, the pipeline (opportunity) or lead card, a log, and posts
      one result line to #exomac-system. --simulate only works with --dry-run (testing the gate path).

  eval                   output eval: duplicate-send check + recipient-domain guard over sends log/registry
  selftest               guardrail unit checks + eval

HARD GUARDRAILS (code-enforced, both at build and again at send time):
  .gov / .mil / national-lab, FFRDC and UARC domains + gov org names -> never sent, "route to John".
  Foreign recipients (non-US company or ccTLD) -> held for export review, never sent.
  Adversary countries (export_screen.classify_country) -> dropped.
  CSL denied-party screen (scripts/csl_screen.py) on org + contact -> any hit held.
  Max 8 sends per CT calendar day. Claim lint (no prices/months/only/first/fastest...) -> held.
"""
import json, os, re, sys, subprocess, urllib.request, urllib.parse, fcntl, time
from datetime import datetime, timezone, date, timedelta
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, formatdate

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
DEC_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
PLAN = os.path.join(WS, "mission-control", "data", "blk3-send-pack-plan.json")
OPPS = os.path.join(WS, "mission-control", "data", "opportunities.json")
TRACKER = os.path.join(WS, "opportunities-tracker.md")
PIPELINE = os.path.join(WS, "tasks", "blk3-payload-sales-pipeline.md")
DRAFTS = os.path.join(WS, "drafts", "payload-outreach-drafts.md")
REGISTRY = os.path.join(WS, "logs", "outreach-sent-registry.json")
MSMTP_LOG = os.path.expanduser("~/.msmtp.log")
LOG = os.path.join(WS, "logs", "blk3-send-pack.log")
SENDS = os.path.join(WS, "logs", "blk3-send-pack-sends.jsonl")
TOKEN = os.path.join(WS, "mission-control", "data", ".decisions-token")
MC = "http://127.0.0.1:8080"
MSMTP = "/opt/homebrew/bin/msmtp"
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
CHANNEL = "channel:1501636814849577050"
LIZI = "lquinn@exosaero.com"
JON = "jquinn@exosaero.com"
APPROVERS = {LIZI, JON}
FROM = formataddr(("Lizi Quinn via Exos Aerospace", "jquinnexo@pm.me"))
MAX_ITEMS = 8
DAILY_CAP = 8
RECENT_DAYS = 60
AGENT = "blk3-send-pack"  # fleet_log agent name (launchd labels: -build, -apply)

# --- guardrail data ---------------------------------------------------------------------------
LAB_DOMAINS = (  # national labs, FFRDCs, UARCs (beyond .gov/.mil)
    "jhuapl.edu", "sdl.usu.edu", "ll.mit.edu", "ucar.edu", "aero.org", "mitre.org", "jpl.nasa.gov",
    "slac.stanford.edu", "arl.psu.edu", "apl.uw.edu", "apl.washington.edu", "gtri.gatech.edu",
    "arlut.utexas.edu", "ida.org", "rand.org", "lanl.gov", "llnl.gov", "sandia.gov", "ornl.gov",
    "anl.gov", "pnnl.gov", "inl.gov", "nrel.gov", "lbl.gov", "bnl.gov", "fnal.gov", "nrl.navy.mil",
    "afrl.af.mil", "nasa.gov", "nih.gov", "noaa.gov", "ucsd.edu.gov", "cnsc.us",
)
GOV_ORG_RX = re.compile(r"\b(NASA|National Lab(?:oratory|oratories)?|AFRL|NRL|DEVCOM|DIU|Air Force|"
                        r"Space Force|U\.?S\.? Navy|U\.?S\.? Army|Naval|NIH|NCATS|NOAA|NSF|DoD|DOE|MDA|"
                        r"Johns Hopkins APL|Applied Physics Lab|Space Dynamics Lab|Sandia|Los Alamos|"
                        r"Lawrence Livermore|Oak Ridge|Goddard|Marshall Space|Kirtland|Wallops|NCAR|"
                        r"FFRDC|UARC|Department of)\b", re.I)
US_TLDS = {"com", "org", "net", "edu", "us", "io", "ai", "co", "space", "tech", "aero", "bio",
           "science", "inc", "llc", "systems", "info", "biz", "app", "dev", "health", "energy"}
FOREIGN_RX = re.compile(r"\b(Australia|Australian|United Kingdom|\bUK\b|Britain|British|England|Scotland|"
                        r"Ireland|Canada|Canadian|Germany|German|France|French|Italy|Italian|Spain|Spanish|"
                        r"Portugal|Netherlands|Dutch|Belgium|Switzerland|Swiss|Austria|Sweden|Norway|Denmark|"
                        r"Finland|Poland|Lithuania|Latvia|Estonia|Israel|Japan|Japanese|Korea|Korean|Taiwan|"
                        r"Singapore|India|Indian|Brazil|(?<!New )Mexico|UAE|Dubai|Saudi|New Zealand|Luxembourg|"
                        r"International|Intl|INTL|foreign|Europe|European|Asia|APAC)\b")
FREEMAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com",
            "proton.me", "protonmail.com", "pm.me", "me.com", "live.com", "msn.com"}
GENERIC_LOCAL = re.compile(r"^(info|contact|hello|hi|bd|sales|partnerships?|business|admin|office|media|"
                           r"press|pr|team|support|inquiries|inquiry|general|aero|aerospace|physics|"
                           r"communications|research|ssel|lab|careers|marketing)$", re.I)
DNC_RX = re.compile(r"no more emails|do not (?:e-?mail|contact)|don'?t (?:e-?mail|contact)|not chasing|"
                    r"stop (?:e-?mailing|contacting)|unsubscribe|opted out", re.I)
LINT_RX = re.compile(r"\$|\bprice|\bpricing|\bcost|\bdiscount|\bfree\b|\bonly\b|\bfirst\b|\bfastest\b|\bbest\b|"
                     r"\bleading\b|\bunique\b|\bunmatched\b|\bguarantee|\bdemonstrated\b|\bfully[- ]booked|"
                     r"\bSpaceport America\b.{0,40}\bFlight 2\b|\b2[- ]?3 days?\b|\b48[- ]hour", re.I)
MONTH_RX = re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|"
                      r"December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?\s+(?:\d{1,2}(?:st|nd|rd|th)?,?\s+)?20\d\d"
                      r"|\b(?:January|February|March|April|June|July|August|September|October|November|December)\b")
EMAIL_RX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
GUESS_RX = re.compile(r"guess|unverified|not verified|could not verify|couldn'?t verify|confirm via|"
                      r"standard format|format:|likely|probabl|TBD|placeholder", re.I)


def log(m):
    with open(LOG, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")


def ct_today():
    # America/Chicago calendar day (launchd host runs in CT; fall back to local date)
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Chicago")).date()
    except Exception:
        return date.today()


def sb_headers():
    key = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
    return {"apikey": key, "Authorization": "Bearer " + key, "Content-Type": "application/json"}


def sb_get(p):
    return json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/{p}", headers=sb_headers()), timeout=60))


def sb_post(table, row):
    urllib.request.urlopen(urllib.request.Request(f"{SB}/{table}", data=json.dumps(row).encode(),
                           headers={**sb_headers(), "Prefer": "return=minimal"}, method="POST"), timeout=30).read()


def decisions():
    d = json.load(open(DEC_FILE))
    return d if isinstance(d, list) else d.get("decisions", [])


# --- guardrails -------------------------------------------------------------------------------
def domain_of(addr):
    return addr.rsplit("@", 1)[-1].lower().strip(".") if "@" in (addr or "") else ""


def is_gov(addr, org_text=""):
    d = domain_of(addr)
    if re.search(r"\.(gov|mil)(\.[a-z]{2})?$", d) or ".gov." in d or ".mil." in d:
        return f"gov/.mil domain ({d})"
    for lab in LAB_DOMAINS:
        if d == lab or d.endswith("." + lab):
            return f"national-lab/FFRDC/UARC domain ({d})"
    m = GOV_ORG_RX.search(org_text or "")
    if m:
        return f"government/national-lab organization ({m.group(0)})"
    return ""


def is_foreign(addr, org_text=""):
    d = domain_of(addr)
    tld = d.rsplit(".", 1)[-1] if d else ""
    if tld and tld not in US_TLDS and len(tld) == 2:
        return f"foreign ccTLD .{tld}"
    if tld and tld not in US_TLDS and tld not in ("gov", "mil"):
        return f"non-US TLD .{tld}"
    m = FOREIGN_RX.search(org_text or "")
    if m:
        return f"non-US indicator '{m.group(0)}'"
    return ""


def adversary(org_text):
    try:
        from export_screen import classify_country
    except Exception:
        return ""
    for tok in re.findall(r"[A-Za-z][A-Za-z .']{2,}", org_text or ""):
        v, why = classify_country(tok.strip())
        if v == "block":
            return why
    return ""


_CSL_OK = None


def csl_hits(names):
    """Return list of hit descriptions; raises if the screen itself can't run (caller holds item)."""
    global _CSL_OK
    import csl_screen
    out = []
    for n in names:
        if not n or len(n) < 4:
            continue
        for h in csl_screen.screen(n)[:1]:
            out.append(f"{n} ~ {h['listed_name']} [{h['source']}] {h['score']}")
    _CSL_OK = True
    return out


def lint(text, org=""):
    t = text
    for tok in filter(None, re.split(r"[\s/,()—-]+", org or "")):  # org names may contain 'First' etc.
        if len(tok) > 2:
            t = re.sub(re.escape(tok), " ", t, flags=re.I)
    t = re.sub(r"(?m)^Best Regards,$", "", t)
    return sorted({m.group(0) for m in LINT_RX.finditer(t)} | {m.group(0) for m in MONTH_RX.finditer(t)})


def guard(item, sent_addrs, sent_domains):
    """Return (verdict, reason): verdict in send|route_john|export_hold|drop|skip|hold."""
    addr = (item.get("email") or "").lower()
    txt = " ".join(str(item.get(k) or "") for k in ("org", "title", "segment", "poc", "context_text"))
    txt = re.sub(r"International Space Station|\bISS\b|Space Station", " ", txt, flags=re.I)
    seg = str(item.get("segment") or "")
    gov_txt = " ".join(str(item.get(k) or "") for k in ("org", "title")) + (" " + seg if re.match(r"\s*Gov", seg) else "")
    if not addr or not EMAIL_RX.fullmatch(addr):
        return "skip", "no verified email"
    if domain_of(addr) == "exosaero.com":
        return "skip", "internal address"
    if addr in sent_addrs:
        return "skip", f"already emailed ({sent_addrs[addr]})"
    dom = domain_of(addr)
    a = adversary(txt)
    if a:
        return "drop", a
    g = is_gov(addr, gov_txt)
    if g:
        return "route_john", g + ": route to John"
    f = is_foreign(addr, txt)
    if f:
        return "export_hold", f + ": hold for export review"
    if dom not in FREEMAIL and dom in sent_domains:
        return "skip", f"domain {dom} emailed within {RECENT_DAYS}d ({sent_domains[dom]})"
    try:
        hits = csl_hits([item.get("org"), item.get("contact")])
    except Exception as e:
        return "hold", f"CSL screen unavailable ({str(e)[:60]})"
    if hits:
        return "hold", "CSL hit: " + "; ".join(hits)
    bad = lint(item.get("subject", "") + "\n" + item.get("body", ""), item.get("org", ""))
    if bad:
        return "hold", "claim/price lint: " + ", ".join(bad)
    return "send", ""


# --- already-sent sources ---------------------------------------------------------------------
def load_registry():
    try:
        return json.load(open(REGISTRY))
    except Exception:
        return {}


def sent_index():
    """addr -> when, domain -> when (registry: any address; domains within RECENT_DAYS; msmtp: 60d)."""
    addrs, doms = {}, {}
    cutoff = datetime.now() - timedelta(days=RECENT_DAYS)
    for k, v in load_registry().items():
        a = (v.get("sent_to") or k or "").lower().strip()
        when = str(v.get("sent_date") or "")[:10]
        for one in EMAIL_RX.findall(a) or [a]:
            one = one.lower()
            addrs[one] = f"registry {when}"
            try:
                if datetime.strptime(when, "%Y-%m-%d") >= cutoff:
                    doms.setdefault(domain_of(one), f"registry {when}")
            except Exception:
                pass
    now = datetime.now()
    try:
        for line in open(MSMTP_LOG, errors="replace"):
            m = re.match(r"(\w{3} \d{1,2} \d\d:\d\d:\d\d) .*?recipients=(\S+)", line)
            if not m or "smtpstatus=250" not in line:
                continue
            try:
                ts = datetime.strptime(f"{now.year} {m.group(1)}", "%Y %b %d %H:%M:%S")
                if ts > now + timedelta(days=1):
                    ts = ts.replace(year=now.year - 1)
            except Exception:
                continue
            if ts < cutoff:
                continue
            for r in m.group(2).split(","):
                r = r.lower().strip()
                if domain_of(r) == "exosaero.com" or domain_of(r) == "pm.me":
                    continue
                addrs.setdefault(r, f"msmtp {ts:%Y-%m-%d}")
                doms.setdefault(domain_of(r), f"msmtp {ts:%Y-%m-%d}")
    except FileNotFoundError:
        pass
    return addrs, doms


# --- sources ----------------------------------------------------------------------------------
def name_key(s):
    s = re.sub(r"^\[[^\]]*\]\s*", "", s or "")
    s = s.split(" — ")[0].split(" (")[0].split(" / ")[0]
    return re.sub(r"[^a-z0-9]", "", s.lower())[:18]


def clean_org(s):
    s = re.sub(r"^\[[^\]]*\]\s*", "", s or "")
    s = re.sub(r"[⭐★✅🏛️]+.*$", "", s)
    s = re.sub(r"\s+—\s+(verify|drafted).*$", "", s, flags=re.I)
    org = s.split(" — ")[0].strip()
    org = re.split(r"\s+/\s+(?:Dr\.|Prof)", org)[0].strip()
    org = re.sub(r"\s*\((?:[^)]*\b(?:CEO|Dr\.|Prof|Founder|Lexington|KY|NM|MT|Bozeman|Butte|Missoula)\b[^)]*|"
                 r"[A-Z][a-z]+ [A-Z][a-zA-Z]+)\)\s*$", "", org).strip()
    # "College (Lame Deer, MT — tribal college)" splits on " — " and leaves an unclosed "(" (CDKC #3742)
    org = re.sub(r"\s*\([^)]*$", "", org).strip()
    return org


def pipeline_blocks():
    try:
        text = open(PIPELINE, encoding="utf-8", errors="replace").read()
    except Exception:
        return {}
    out = {}
    for b in re.split(r"\n#### \d+\.\s*", text)[1:]:
        name = b.splitlines()[0].strip()
        out.setdefault(name_key(name), {"name": name, "block": b.split("\n---")[0]})
    return out


def tracker_sections():
    try:
        text = open(TRACKER, encoding="utf-8", errors="replace").read()
    except Exception:
        return {}
    out = {}
    for sec in re.split(r"\n(?=### )", text):
        m = re.match(r"### (PAY-\d+) \| (.+)", sec)
        if m:
            out[m.group(1)] = sec
    return out


def drafts_index():
    """name_key -> earliest drafted date."""
    out = {}
    try:
        txt = open(DRAFTS, encoding="utf-8", errors="replace").read()
    except Exception:
        return out
    for m in re.finditer(r"^## (.+?) — drafted (\d{4}-\d{2}-\d{2})", txt, re.M):
        k = name_key(m.group(1))
        out[k] = min(out.get(k, "9999"), m.group(2))
    return out


def field(block, label):
    m = re.search(rf"\*\*{label}:\*\*\s*(.+)", block or "")
    return re.sub(r"\*\*", "", m.group(1)).strip() if m else ""


def verified_email(*texts):
    """First address on a line that isn't marked as a guess; prefer lines saying verified/confirmed/email."""
    best = None
    for t in texts:
        for line in (t or "").splitlines():
            if GUESS_RX.search(line):
                continue
            for e in EMAIL_RX.findall(line):
                if re.search(r"exosaero\.com|^first|lastname|^name@|example\.", e, re.I):
                    continue
                score = 2 if re.search(r"verified|confirmed|public email|e-?mail", line, re.I) else 1
                if not best or score > best[0]:
                    best = (score, e)
    return best[1] if best else ""


def contact_from(addr, texts, fallback=""):
    """(display name, greeting) from the address local part matched to a name in the notes."""
    local = addr.split("@")[0].lower()
    if GENERIC_LOCAL.match(local) or not local:
        return "", ""
    blob = "\n".join(t for t in texts if t)
    cands = re.findall(r"\b(Dr\.?\s+|Prof\.?\s+|Professor\s+)?([A-Z][a-zé]+(?:-[A-Z][a-z]+)?)\s+"
                       r"(?:[A-Z]\.\s+)?([A-Z][a-zA-Zé'-]+)\b", blob + "\n" + fallback)
    stop = {"Space", "Lab", "Labs", "University", "Research", "Center", "Program", "Systems", "Exos",
            "Aerospace", "Technologies", "Industries", "Director", "Business", "Development", "Public"}
    for title, first, last in cands:
        if first in stop or last in stop:
            continue
        f, l = first.lower(), re.sub(r"[^a-z]", "", last.lower())
        if (len(l) >= 3 and l in local and (f[0] == local[0] or f in local or local == l)) or \
           (len(f) >= 3 and local == f):
            dr = bool(title and title.strip().startswith(("Dr", "Prof"))) or \
                bool(re.search(rf"\bDr\.?\s+{re.escape(first)}\s+{re.escape(last)}|\bDr\.?\s+{re.escape(last)}\b", blob))
            disp = f"{first} {last}"
            return disp, (f"Dr. {last}," if dr else f"Hello {first},")
    m = re.match(r"([a-z]{3,})[._]([a-z]{2,})$", local)
    if m:
        return f"{m.group(1).title()} {m.group(2).title()}", f"Hello {m.group(1).title()},"
    return "", "Hello,"


def open_student_keys():
    """Org keys of UTD lead cards still being researched (not Done/Cancelled). Students raised 10/15 that
    Exos emailed their open leads before research was finished (Ursa Major, Rhea, UT, UMontana, Sierra,
    Hermeus, Castelion went out via pay_candidates). Those orgs are off-limits until the card is Done."""
    tasks = sb_get("tasks?select=id,title,tags,description,state&tags=cs.%7Butd-lead%7D"
                   "&state=not.in.(Done,Cancelled)&limit=500") or []
    keys = set()
    for t in tasks:
        desc = t.get("description") or ""
        lead_tag = next((g[5:] for g in (t.get("tags") or []) if str(g).startswith("lead:")), "")
        lead_line = (re.search(r"^LEAD:\s*(.+)", desc, re.M) or [None, ""])[1]
        for src in (lead_line, lead_tag, t.get("title") or ""):
            if src:
                keys.add(name_key(clean_org(src)))
                keys.add(name_key(src))
    keys.discard("")
    return keys


def utd_candidates():
    tasks = sb_get("tasks?select=id,title,owner,tags,description,completed_at,state"
                   "&tags=cs.%7Butd-lead%7D&state=eq.Done&order=completed_at.asc&limit=500")
    if not tasks:
        return []
    pipe = pipeline_blocks()
    subj = ",".join(f'"task:{t["id"]}"' for t in tasks)
    acts = sb_get("activities?select=subject,owner,body,created_at&subject=in.(" + urllib.parse.quote(subj) +
                  ")&order=created_at.asc&limit=2000")
    out = []
    for t in tasks:
        notes = [a for a in acts if a["subject"] == f"task:{t['id']}"]
        human = [a for a in notes if (a.get("owner") or "") not in ("Exo", "Jon", "Exobot")
                 and not str(a.get("body") or "").startswith("[Update] State")]
        exo_txt = "\n".join(a.get("body") or "" for a in notes if a.get("owner") in ("Exo", "Jon"))
        desc = t.get("description") or ""
        lead_tag = next((g[5:] for g in (t.get("tags") or []) if str(g).startswith("lead:")), "")
        lead_line = (re.search(r"^LEAD:\s*(.+)", desc, re.M) or [None, ""])[1]
        org = clean_org(lead_line or lead_tag or t.get("title"))
        pblock = pipe.get(name_key(lead_line or lead_tag), {}).get("block", "")
        email = verified_email(*[a.get("body") for a in reversed(human)]) or verified_email(pblock)
        head = desc.split("THE AI'S DRAFT")[0]
        head = re.split(r"\n- Active programs", head)[0]
        seg = (re.search(r"- Segment:\s*(.+)", desc) or [None, ""])[1]
        fit = None
        for a in human:
            m = re.search(r"fit(?: score)?\D{0,20}([1-5])\s*/\s*5", a.get("body") or "", re.I)
            if m:
                fit = int(m.group(1))
        verdict = ""
        for a in human:
            m = re.match(r"\s*(PASS|FAIL)\b", a.get("body") or "")
            if m:
                verdict = f"{m.group(1)} ({a.get('owner')})"
        human_txt = [a.get("body") or "" for a in human]
        contact, greet = contact_from(email, human_txt + [head, field(pblock, "POC")], t.get("title") or "")
        dnc = DNC_RX.search(exo_txt + "\n" + "\n".join(human_txt))
        out.append({"source": "utd-lead", "ref": f"task:{t['id']}", "task_id": t["id"], "org": org,
                    "title": t.get("title"), "segment": seg, "email": email.lower() if email else "",
                    "contact": contact, "greeting": greet, "student": t.get("owner"), "fit": fit,
                    "review": verdict, "lead_key": pipe.get(name_key(lead_line or lead_tag), {}).get("name", lead_tag),
                    "context_text": head,
                    "dnc": (f"note says '{dnc.group(0)}' for the original contact" if dnc else ""),
                    "poc": ""})
    return out


def pay_candidates():
    d = json.load(open(OPPS))
    opps = d["opportunities"] if isinstance(d, dict) else d
    pipe, trk, drafts = pipeline_blocks(), tracker_sections(), drafts_index()
    out = []
    for o in opps:
        if not str(o.get("id", "")).startswith("PAY-") or str(o.get("status")).upper() not in ("READY", "DRAFT"):
            continue
        k = name_key(o.get("title"))
        if k not in drafts:
            continue
        pb = pipe.get(k, {}).get("block", "")
        sec = trk.get(o["id"], "")
        email = verified_email(pb, sec)
        poc = field(pb, "POC") or field(sec, "POC")
        contact, greet = contact_from(email, [poc, pb], o.get("title") or "")
        st = (field(pb, "Status") + " " + field(sec, "Status"))
        if re.search(r"\b(LOST|DEAD|CLOSED|DROPPED)\b", st):
            continue  # Lizi-dropped lead (UT/Ursa slipped into the 10/9 pack despite 10/8 LOST)
        out.append({"source": "pay-opportunity", "ref": o["id"], "org": clean_org(o.get("title")),
                    "title": o.get("title"), "segment": field(pb, "Segment") or field(sec, "Segment"),
                    "email": email.lower() if email else "", "contact": contact, "greeting": greet,
                    "poc": poc[:160], "drafted": drafts[k], "lead_key": pipe.get(k, {}).get("name", ""),
                    "hold_flag": ("pipeline/tracker status says HOLD" if re.search(r"\bHOLD\b", st) else "")})
    out.sort(key=lambda x: x["drafted"])
    return out


# --- the email --------------------------------------------------------------------------------
ANGLES = [  # (segment/title regex, interest phrase, tailored sentence)
    (r"broker|aggregat|integrator|NanoRacks|commercial station|research continuity",
     "supporting research customers in microgravity",
     "If any of the teams you work with need a suborbital step before a longer mission, we would be glad "
     "to explore how BLK3 could fit alongside what you already offer them."),
    (r"pharma|biolog|biotech|protein|crystal|cell|medic|life[- ]science|tissue|biomed",
     "microgravity life-science research",
     "For biology and formulation work, having the samples come back to your own lab after the flight "
     "could make it easier to compare results against your ground controls."),
    (r"propuls|propellant|engine|motor|hypersonic|combustion|cryo|thruster|fluid",
     "propulsion and flight-environment testing",
     "For propulsion and fluids work, flying hardware through a real launch and microgravity environment "
     "and then getting it back to inspect could be a useful step between ground testing and an orbital mission."),
    (r"atmospher|chemistry|climate|ionosph|heliophys|space physics|solar|debris|dust",
     "space and atmospheric science",
     "For instrument and sensor teams, a recovered flight could be a practical way to check how hardware "
     "behaves in flight before committing it to a longer campaign."),
    (r"lunar|lander|GNC|navigation|terrain|rover|in-space|satellite|spacecraft|bus",
     "space hardware development",
     "For flight hardware headed to orbit or the Moon, a suborbital flight with recovery could be a helpful "
     "way to gather flight data on components before the bigger mission."),
    (r"photonic|optic|laser|sensor|hyperspectral|imaging|camera|lidar|instrument",
     "space instruments and sensors",
     "For instrument teams, a recovered flight could be a practical way to see how optics and electronics "
     "behave in flight and then look the hardware over afterward."),
    (r"materials|manufactur|composite|additive|semiconductor",
     "in-space materials and manufacturing",
     "For materials and manufacturing work, the recovered samples and hardware return to you after the "
     "flight, so your team can study them directly."),
    (r"universit|college|student|education|EPSCoR|workforce|space grant|tribal|consortium",
     "student and faculty space research",
     "For student and faculty teams, a payload on BLK3 could be a meaningful hands-on project, and we are "
     "happy to talk through possible funding paths, such as Space Grant consortia or research grants."),
]


def compose(item):
    org = re.sub(r"\s*\(.*?\)", "", re.split(r"\s+/\s+", item["org"])[0]).strip()
    poss = org + ("'" if org.endswith("s") else "'s")
    hay = f"{item.get('segment','')} {item.get('title','')}"
    interest, angle = "flight testing hardware in a space environment", (
        "If your team has hardware or an experiment that could benefit from a recovered flight, "
        "we would be glad to talk through whether BLK3 is a good match.")
    for rx, phrase, sentence in ANGLES:
        if re.search(rx, hay, re.I):
            interest, angle = phrase, sentence
            break
    greet = item.get("greeting") or f"Hello {org} team,"
    subject = f"Payload space for {org} on BLK3, early 2027"
    body = f"""{greet}

My name is Lizi Quinn, and I work with the team at Exos Aerospace. We are currently booking payloads for the next flight of BLK3, our reusable suborbital rocket, in early 2027. Given {poss} work in {interest}, it felt like a natural fit to reach out.

Exos has flown commercial payloads since 2018 on our SARGE rocket, and BLK3 is its successor. Exos holds an FAA Part 431 launch license, transitioning to Part 450. A few things that may be helpful as you think it over:

- The payload bay can carry up to 135 kg, so there is room for one larger experiment or several smaller ones.
- BLK3 is designed to give about two and a half minutes of continuous microgravity.
- Your hardware is recovered and returned to you after the flight, so your team can inspect it and work with it directly.

{angle}

If it would be helpful, I'm happy to send over our one-page payload overview, or you can grab a time for a short scoping call here: https://outlook.office365.us/bookwithme/user/abb76930b11b4c02a0d4eb449063a66b%40exosaero.com?anonymous&ismsaljsauthenabled. You're also welcome to tell us what you'd like to fly at https://www.exosaero.com/flight-campaign.

Best Regards,
Lizi
"""
    return subject, body


# --- build ------------------------------------------------------------------------------------
def build(dry):
    today = ct_today()
    if today.weekday() >= 5 and not dry:
        log("build: weekend, skipped")
        return
    addrs, doms = sent_index()
    try:
        utd = utd_candidates()
    except Exception as e:
        utd = []
        log(f"build: utd lead fetch failed: {e}")
    pay = pay_candidates()
    utd_keys = {name_key(c["org"]) for c in utd} | {name_key(c["lead_key"]) for c in utd if c["lead_key"]}
    pay = [p for p in pay if name_key(p["org"]) not in utd_keys]
    try:
        open_keys = open_student_keys()
    except Exception as e:   # fail closed: if we can't see the student board, offer no pipeline items
        log(f"build: open student-card fetch failed ({e}); skipping all pipeline items")
        open_keys, pay = set(), []
    held_open = [p for p in pay if name_key(p["org"]) in open_keys or name_key(clean_org(p["org"])) in open_keys]
    pay = [p for p in pay if p not in held_open]
    for p in held_open:
        log(f"build: skip {p['org']}: open UTD student lead card (research not finished)")
    items, routed, held, skipped = [], [], [], []
    seen = set()
    for c in utd + pay:
        if len(items) >= MAX_ITEMS:
            break
        k = name_key(c["org"])
        if k in seen:
            continue
        seen.add(k)
        if c.get("hold_flag"):
            skipped.append((c, c["hold_flag"])); continue
        if c.get("dnc") and not c.get("email"):
            skipped.append((c, c["dnc"])); continue
        if str(c.get("review") or "").startswith("FAIL"):   # never offer a draft a student QC failed (Jon 10/7)
            skipped.append((c, f"failed student QC ({c['review']}) — fix before it can be offered")); continue
        if c.get("fit") is not None and c["fit"] <= 2:
            skipped.append((c, f"student fit score {c['fit']}/5")); continue
        c["subject"], c["body"] = compose(c)
        v, why = guard(c, addrs, doms)
        c["guard"] = v
        c["guard_reason"] = why
        if v == "send":
            items.append(c)
        elif v == "route_john":
            routed.append(c)
        elif v in ("export_hold", "hold"):
            held.append(c)
        else:
            skipped.append((c, why))
    for n, it in enumerate(items, 1):
        it["n"] = n

    def item_text(it):
        meta = []
        if it["source"] == "utd-lead":
            meta.append(f"student-verified by {it.get('student')} ({it['ref']})" +
                        (f", review {it['review']}" if it.get("review") else "") +
                        (f", fit {it['fit']}/5" if it.get("fit") else ""))
        else:
            meta.append(f"{it['ref']}, drafted {it.get('drafted')}")
        if it.get("dnc"):
            meta.append(it["dnc"] + "; this goes to the newer contact instead")
        return (f"{it['n']}) To: {it.get('contact') + ' ' if it.get('contact') else ''}<{it['email']}>  [{it['org']}]\n"
                f"   ({'; '.join(meta)})\n"
                f"   Subject: {it['subject']}\n\n" + "\n".join("   " + l if l else "" for l in it["body"].splitlines()))

    ctx = ("BLK3 payload-prospect send pack (Jon approved D-7281980, option A). \"Send approved items\" "
           "emails every numbered item below from the outreach address, signed as you, Reply-To and Cc you. "
           "Hold any item in the note, e.g. \"hold 2 5\". \"Hold all\" sends nothing. Nothing goes out without "
           "your click.\n\n" + "\n\n".join(item_text(i) for i in items))
    if routed:
        ctx += "\n\nNOT in this pack, route to John (gov/.mil/national lab): " + "; ".join(
            f"{c['org']} <{c['email']}>" for c in routed)
    if held:
        ctx += "\n\nNOT in this pack, held: " + "; ".join(f"{c['org']} <{c['email']}> ({c['guard_reason']})" for c in held)
    dedupe = f"blk3-send-pack-{today.isoformat()}"
    body = {"title": f"BLK3 send pack {today.isoformat()}: {len(items)} payload emails to approve",
            "question": f"Send the {len(items)} BLK3 payload emails below (hold any by number in the note)?",
            "type": "choice", "options": ["Send approved items", "Hold all"], "priority": "normal",
            "source": "Exo (BLK3 send pack)", "context": ctx,
            "proposedAction": f"On approval Exo emails {len(items)} BLK3 payload prospects as Lizi (per-item holds honored)",
            "assignedTo": LIZI, "approver": LIZI, "agentClass": "blk3-send-pack", "dedupeKey": dedupe}
    plan = {"decision_id": None, "dedupeKey": dedupe, "created": datetime.now(timezone.utc).isoformat(),
            "items": items, "route_to_john": routed, "held": held,
            "skipped": [{"org": c["org"], "ref": c["ref"], "email": c.get("email"), "why": w} for c, w in skipped],
            "executed": False}
    if dry:
        print(f"=== DRY RUN: BLK3 send pack {today} — {len(items)} item(s), {len(routed)} route-to-John, "
              f"{len(held)} held, {len(skipped)} skipped ===\n")
        print(body["title"]); print(body["question"]); print(body["options"]); print()
        print(ctx)
        print("\n--- skipped ---")
        for c, w in skipped:
            print(f"  {c['org']} ({c['ref']}) <{c.get('email') or '-'}>: {w}")
        return plan
    if not items:
        json.dump(plan, open(PLAN + ".tmp", "w"), indent=1, default=str)
        os.replace(PLAN + ".tmp", PLAN)
        log(f"build: no sendable items (routed={len(routed)} held={len(held)} skipped={len(skipped)})")
        print("NO_REPLY")
        return plan
    archive_open_plan()
    tok = open(TOKEN).read().strip()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"{MC}/api/decisions/ingest",
                  data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-exo-token": tok},
                  method="POST"), timeout=30))
    plan["decision_id"] = r.get("id")
    if r.get("deduped"):
        log(f"build: {dedupe} already answered ({r.get('id')}); plan not replaced")
        print("NO_REPLY")
        return plan
    json.dump(plan, open(PLAN + ".tmp", "w"), indent=1, default=str)
    os.replace(PLAN + ".tmp", PLAN)
    log(f"build: decision={plan['decision_id']} items={[i['email'] for i in items]} routed={len(routed)} "
        f"held={len(held)} skipped={len(skipped)}")
    try:
        from fleet_log import event
        event(AGENT, "decide", "propose", detail={"decision": plan["decision_id"], "items": len(items)},
              owner="John Quinn")
    except Exception:
        pass
    print(f"BLK3 send pack: {len(items)} email(s) awaiting Lizi → Decision {plan['decision_id']}")
    return plan


# --- apply ------------------------------------------------------------------------------------
def human_answered(d):
    return str(d.get("answeredByEmail") or "").strip().lower() in APPROVERS


def sends_today():
    n, today = 0, ct_today().isoformat()
    try:
        for line in open(SENDS):
            r = json.loads(line)
            if r.get("ct_date") == today and r.get("status") == "sent":
                n += 1
    except FileNotFoundError:
        pass
    return n


def registry_add(addr, subject, sent_utc):
    """Atomic read-modify-write; re-read immediately before writing to keep other writers' entries."""
    lockf = open(REGISTRY + ".lock", "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        reg = load_registry()
        reg[addr] = {"sent_date": sent_utc.strftime("%Y-%m-%d %H:%M"), "subject": subject, "sent_to": addr,
                     "trackers": ["blk3-payload-sales-pipeline.md"], "detected": sent_utc.strftime("%Y-%m-%d %H:%M"),
                     "source": "blk3-send-pack"}
        tmp = REGISTRY + ".tmp"
        json.dump(reg, open(tmp, "w"), indent=2)
        os.replace(tmp, REGISTRY)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)


def pipeline_mark(it, did, d8):
    """Opportunity note: flip the pipeline block's Status to OUTREACH SENT (bridge carries it to the PAY-)."""
    key = name_key(it.get("lead_key") or it["org"])
    text = open(PIPELINE, encoding="utf-8").read()
    parts = re.split(r"(\n#### \d+\.\s*)", text)
    changed = False
    for i in range(2, len(parts), 2):
        name = parts[i].splitlines()[0]
        if name_key(name) != key:
            continue
        stamp = f" → OUTREACH SENT (Lizi via send pack {d8}, {did}, to {it['email']})"
        new, n = re.subn(r"(- \*\*Status:\*\*[^\n]*)", lambda m: m.group(1) + stamp, parts[i], count=1)
        if n:
            parts[i] = new
            changed = True
        break
    if changed:
        tmp = PIPELINE + ".tmp"
        open(tmp, "w", encoding="utf-8").write("".join(parts))
        os.replace(tmp, PIPELINE)
    return changed


def send_one(it):
    msg = EmailMessage()
    msg["From"] = FROM
    msg["To"] = it["email"]
    msg["Cc"] = LIZI
    msg["Reply-To"] = LIZI
    msg["Subject"] = it["subject"]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="pm.me")
    msg.set_content(it["body"])
    p = subprocess.run([MSMTP, "-a", "protonmail", it["email"], LIZI], input=msg.as_bytes(),
                       capture_output=True, timeout=120)
    return p.returncode == 0, (p.stderr or b"").decode(errors="replace")[:200]


def archive_open_plan():
    """Before today's plan replaces the file, keep an unexecuted earlier plan so a late click still works."""
    try:
        old = json.load(open(PLAN))
    except Exception:
        return
    if old.get("decision_id") and not old.get("executed"):
        dst = PLAN.replace(".json", f"-{old.get('dedupeKey') or old['decision_id']}.json")
        json.dump(old, open(dst, "w"), indent=1, default=str)


def plan_files():
    import glob
    out = [PLAN] if os.path.exists(PLAN) else []
    cutoff = time.time() - 7 * 86400
    for f in sorted(glob.glob(PLAN.replace(".json", "-blk3-send-pack-*.json"))):
        if os.path.getmtime(f) >= cutoff:
            out.append(f)
    return out


def apply(dry, simulate=None):
    global PLAN
    files = [PLAN] if simulate else plan_files()
    if not files and dry:
        print("no plan file")
    main_plan = PLAN
    for f in files:
        PLAN = f
        try:
            apply_one(dry, simulate)
        finally:
            PLAN = main_plan


def apply_one(dry, simulate=None):
    try:
        plan = json.load(open(PLAN))
    except Exception:
        if dry: print("no plan file")
        return
    if plan.get("executed") or (not plan.get("decision_id") and not simulate):
        if dry: print("plan already executed or has no decision")
        return
    if simulate:
        if not dry:
            raise SystemExit("--simulate requires --dry-run")
        ans, _, note = simulate.partition("|")
        d = {"status": "answered", "answer": ans, "note": note, "answeredByEmail": LIZI}
    else:
        d = next((x for x in decisions() if x.get("id") == plan["decision_id"]), None)
    if not d or d.get("status") != "answered":
        if dry: print(f"{plan.get('decision_id')}: not answered yet, nothing to do")
        return
    if not human_answered(d):
        log(f"apply {plan['decision_id']}: answered but not by an approver ({d.get('answeredByEmail') or d.get('answeredBy')}); ignored")
        if dry: print("answered, but not by Lizi/Jon's human click: ignored")
        return
    ans = str(d.get("answer") or "").lower()
    note = str(d.get("note") or "").lower()
    held = {int(n) for m in re.finditer(r"\b(?:hold|skip|keep|no|don'?t send)\s+((?:(?:#?\d+|and)[\s,]*)+)", note)
            for n in re.findall(r"\d+", m.group(1))}
    res, fails = [], []
    go = ans.startswith("send") or ans in ("yes", "approve", "approved")
    if go and not re.search(r"\bhold all\b", ans):
        for it in plan["items"]:
            if it.get("n") in held:
                res.append(f"#{it['n']} {it['org']} held by approver"); continue
            # Re-check everything right before EACH send: registry + msmtp (dupes), guardrails, cap.
            addrs, doms = sent_index()
            v, why = guard(it, addrs, doms)
            if v != "send":
                res.append(f"#{it['n']} {it['org']} NOT sent ({why})"); continue
            if sends_today() >= DAILY_CAP:
                res.append(f"#{it['n']} {it['org']} NOT sent (daily cap {DAILY_CAP} reached)"); continue
            if dry:
                res.append(f"#{it['n']} WOULD send to {it['email']} ({it['org']})"); continue
            ok, err = send_one(it)
            now = datetime.now(timezone.utc)
            rec = {"ts": now.isoformat(), "ct_date": ct_today().isoformat(), "decision": plan["decision_id"],
                   "n": it["n"], "to": it["email"], "org": it["org"], "ref": it["ref"], "subject": it["subject"],
                   "status": "sent" if ok else "failed", "err": "" if ok else err,
                   "approver": d.get("answeredByEmail")}
            with open(SENDS, "a") as f:
                f.write(json.dumps(rec) + "\n")
            if not ok:
                fails.append(f"#{it['n']} {it['org']} send FAILED: {err[:80]}"); continue
            try:
                registry_add(it["email"], it["subject"], now)
            except Exception as e:
                log(f"registry write failed for {it['email']}: {e}")
            d8 = ct_today().isoformat()
            try:
                if it.get("task_id"):
                    sb_post("activities", {"type": "task_note", "subject": f"task:{it['task_id']}", "owner": "Exo",
                                           "status": "completed",
                                           "body": f"📤 Exo: outreach to {it['email']} sent {d8} as Lizi (approved on "
                                                   f"{plan['decision_id']}). Thanks for verifying this lead!"})
                pipeline_mark(it, plan["decision_id"], d8)
            except Exception as e:
                log(f"note write failed for {it['email']}: {e}")
            res.append(f"#{it['n']} sent to {it['email']} ({it['org']})")
    if dry:
        print(f"=== DRY RUN apply ({'simulated' if simulate else plan['decision_id']}): answer={d.get('answer')!r} "
              f"held={sorted(held)} ===")
        print("\n".join(res) or "(nothing to send)")
        return
    plan.update({"executed": True, "executed_at": datetime.now(timezone.utc).isoformat(), "result": res + fails,
                 "held_by_approver": sorted(held), "answer": d.get("answer"), "approver": d.get("answeredByEmail")})
    json.dump(plan, open(PLAN + ".tmp", "w"), indent=1, default=str)
    os.replace(PLAN + ".tmp", PLAN)
    log(f"apply {plan['decision_id']}: {res + fails} held={sorted(held)}")
    try:
        from fleet_log import event
        event(AGENT, "orchestrate", "send", detail={"decision": plan["decision_id"], "result": res + fails},
              owner="John Quinn", outcome="fail" if fails else "ok")
    except Exception:
        pass
    sent = [r for r in res if " sent to " in r]
    by_appr = [r for r in res if "held by approver" in r]
    blocked = [r for r in res if " NOT sent " in r]
    msg = (f"BLK3 send pack {plan['decision_id']}: {len(sent)} sent"
           + (f", {len(by_appr)} held by approver" if by_appr else "")
           + (f", {len(blocked)} blocked at send time" if blocked else "")
           + (f", {len(fails)} FAILED" if fails else "")
           + ("" if go else " (Hold all: nothing sent)")
           + (". " + "; ".join(r.split(" (")[0] for r in sent) if sent else ""))
    subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", CHANNEL, "-m", msg],
                   capture_output=True, timeout=60)


# --- output eval ------------------------------------------------------------------------------
def output_eval(quiet=False):
    """FAIL if (a) any address was sent twice by this flow, or a send-pack recipient was already in the
    registry from another source before the send, or (b) any sent recipient fails the domain guard."""
    problems = []
    seen = {}
    try:
        rows = [json.loads(l) for l in open(SENDS) if l.strip()]
    except FileNotFoundError:
        rows = []
    for r in rows:
        if r.get("status") != "sent":
            continue
        a = r["to"].lower()
        if a in seen:
            problems.append(f"duplicate send to {a} ({seen[a]} and {r['ts'][:10]})")
        seen[a] = r["ts"][:10]
        g = is_gov(a, r.get("org", ""))
        f = is_foreign(a, r.get("org", ""))
        if g or f:
            problems.append(f"guard violation {a}: {g or f}")
    from collections import Counter
    per_day = Counter(r["ct_date"] for r in rows if r.get("status") == "sent")
    for dday, n in per_day.items():
        if n > DAILY_CAP:
            problems.append(f"daily cap exceeded {dday}: {n}")
    verdict = "FAIL" if problems else "PASS"
    if not quiet:
        print(f"blk3-send-pack output eval: {verdict} ({len(seen)} unique sends checked)" +
              ("".join("\n  - " + p for p in problems)))
    return verdict == "PASS"


def selftest():
    ok = True
    def chk(cond, label):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + label)
        ok = ok and cond
    chk(bool(is_gov("a@nasa.gov")), "nasa.gov routed to John")
    chk(bool(is_gov("b@grc.nasa.gov")), "center subdomain routed")
    chk(bool(is_gov("c@jhuapl.edu")), "jhuapl.edu routed")
    chk(bool(is_gov("d@nrl.navy.mil")), "nrl.navy.mil routed")
    chk(bool(is_gov("e@sandia.gov")), "sandia.gov routed")
    chk(bool(is_gov("x@gmail.com", "Adrian Daw (NASA Goddard)")), "gov org on freemail routed")
    chk(not is_gov("f@colorado.edu", "LASP"), "university not routed")
    chk(bool(is_foreign("g@spaceport.com.au")), ".au held")
    chk(bool(is_foreign("h@bioorbit.co.uk")), ".uk held")
    chk(bool(is_foreign("i@x.com", "Space Port Australia")), "foreign org name held")
    chk(not is_foreign("j@varda.com", "Varda Space Industries"), "US company not held")
    chk(bool(adversary("Beijing Institute, China")), "adversary dropped")
    s, b = compose({"org": "Acme Labs", "segment": "University propulsion", "greeting": "Dr. Smith,"})
    chk(not lint(s + b, "Acme Labs"), "template passes claim lint")
    # Lizi 10/13: booking link replaces phone/email; Lizi 10/19: first touch = one-pager, never the PUG
    chk("early 2027" in b and "Lizi Quinn" in b and "bookwithme" in b and "one-page" in b
        and "Payload User" not in b, "template: early 2027 + Lizi + booking link + one-pager (no PUG)")
    chk(bool(lint("one of only three, March 2027, $1M", "")), "lint catches only/month/price")
    v, _ = guard({"email": "z@nasa.gov", "org": "NASA Glenn", "subject": s, "body": b}, {}, {})
    chk(v == "route_john", "guard: gov -> route_john")
    v, _ = guard({"email": "z@acme.com", "org": "Acme", "subject": s, "body": b}, {"z@acme.com": "registry"}, {})
    chk(v == "skip", "guard: registry dupe -> skip")
    v, _ = guard({"email": "y@acme.com", "org": "Acme", "subject": s, "body": b}, {}, {"acme.com": "msmtp"})
    chk(v == "skip", "guard: recent domain -> skip")
    ok = output_eval() and ok
    print("selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    a = sys.argv[1:]
    dry = "--dry-run" in a
    if "--plan" in a:  # testing only: alternate plan file (dry-run only)
        if not dry:
            raise SystemExit("--plan requires --dry-run")
        PLAN = a[a.index("--plan") + 1]
    if a and a[0] == "build":
        p = build(dry)
        if dry and "--plan" in a and p:
            json.dump(p, open(PLAN, "w"), indent=1, default=str)
    elif a and a[0] == "apply":
        sim = a[a.index("--simulate") + 1] if "--simulate" in a else None
        apply(dry, sim)
    elif a and a[0] == "eval":
        sys.exit(0 if output_eval() else 1)
    elif a and a[0] == "selftest":
        sys.exit(0 if selftest() else 1)
    else:
        print(__doc__)
