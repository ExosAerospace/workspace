#!/usr/bin/env python3
"""
itar_ear_screen.py — backup export-control screen for the email intake.

BACKUP net, not the primary control: the employee's judgment (only route non-CUI/
non-ITAR/EAR email to the intake) is primary. This catches emails that slip through
by scanning subject + body + attachment names for controlled content. Three layers:
  1. Explicit markers — ITAR / EAR / CUI / export-control terms (a *mention*).
  2. Controlled ARTIFACTS — CAD / native-engineering / analysis file types
     (.sldprt, .step, .catpart, .dwg, FEA/CFD/CAM, Simulink, PCB, etc.). The file
     itself is the trigger, not any keyword in it.
  3. Controlled TECHNICAL DATA — rocket engineering parameters that exceed the
     export-cleared Payload User's Guide (engine internals, GNC/flight-SW internals,
     composite layup/resin process, structural margins, trajectory/perf data).
     Cleared payload-INTERFACE specs (bay size, 135 kg to 100 km, g/vibe env,
     turnaround, keep-out) are intentionally NOT triggers.
On a hit the calling watcher HOLDS the email (does not capture it to a task and does
not run it as a command), quarantines it, and alerts.

Conservative by design toward false positives: a hit means "hold for human review,"
which is safe. Import and use:
    from itar_ear_screen import screen, attachment_names, quarantine_and_alert
    hits = screen(subject + "\\n" + body + "\\n" + " ".join(attachment_names(msg)))
    if hits:
        quarantine_and_alert(message_id, sender, subject, hits, source="tracker")
        # ...skip processing this email...
"""
import json, os, re, subprocess, time, hashlib, urllib.request, sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from proton_aliases import is_self as _is_self   # @exosaero.com + Jon/ops aliases => internal
except Exception:
    def _is_self(a):
        return (a or "").strip().lower().endswith("@exosaero.com")

WS = "/Users/exomac/.openclaw/workspace"
QLOG = os.path.join(WS, "logs", "itar-ear-quarantine.jsonl")
DECISIONS_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON_DISCORD = "1501632195163590739"

# Layer 1 = genuine control MARKINGS only (the item declares/marks ITSELF controlled).
# A bare topical mention of ITAR/EAR/CUI/TAA/MLA does NOT hold on its own (that is business/
# compliance discussion, per Jon 2026-07-19 "not just its mention"). Actual controlled content
# is caught by layers 2-4 (CAD artifacts / technical data / LLM), so a mention with real
# controlled data still holds — via those layers, not via the mention.
MARKINGS = [
    (r'(?m)^\s*CUI//|\bCUI//(?:SP-|CTI|EXPT|SP\b)', 'CUI// banner'),
    (r'distribution statement\s+[b-f]\b', 'Distribution Statement B-F'),
    (r'contains technical data.{0,60}(export|itar|controll)', 'technical-data export marking'),
    (r'export of which is restricted', 'export-restricted marking'),
    (r'itar[-\s]controlled technical data|controlled by (?:the )?itar', 'ITAR-controlled marking'),
    (r'\bECCN[:\s]+\d[A-Z]\d', 'ECCN classification'),
    (r'//\s*NOFORN\b|\bNOFORN\b', 'NOFORN marking'),
    # Real classification markings only — NOT a bare business "CONFIDENTIAL" header. Requires
    # TOP SECRET, a dissemination-control // (SECRET//NOFORN), or a classification-authority block.
    (r'(?m)^\s*TOP\s+SECRET\b|\b(?:TOP\s+SECRET|SECRET|CONFIDENTIAL|FOUO)\s*//|\bclassified by\s*[:\-]|\bderived from\s*[:\-]|\bdeclassify on\s*[:\-]', 'classification marking'),
    # --- Extra hard-hold pins (Jon 2026-07-19): bare terms that on their own imply a
    # controlled context, so they HOLD even without a full marking/banner. ---
    (r'\bUSML\b|\bU\.?\s?S\.?\s*Munitions List\b|\bMunitions List\b', 'USML / Munitions List'),
    (r'\bdeemed export\b', 'deemed export'),
    (r'\bcommodity jurisdiction\b|\bCJ request\b', 'commodity jurisdiction'),
    (r'\bDSP[-\s]?\d{1,3}\b', 'DDTC license (DSP-#)'),
    (r'\b22\s*C\.?\s?F\.?\s?R\.?\s*121\b|\bUSML\s+Categor', 'USML / 22 CFR 121 citation'),
    (r'\bEAR99\b.{0,60}(?:classif|controll|eccn)|(?:classif|eccn|controll)\w*.{0,60}\bEAR99\b', 'EAR99 classification'),
]
_COMPILED = [(re.compile(p, re.I | re.S), label) for p, label in MARKINGS]

# Retained for reference/context only — these TOPICAL terms no longer auto-HOLD by themselves.
TOPICAL_MENTIONS = ["ITAR", "EAR", "EAR99", "ECCN", "USML", "DDTC", "defense article",
    "defense service", "deemed export", "22 CFR", "15 CFR", "commodity jurisdiction",
    "technical assistance agreement / TAA", "manufacturing license agreement / MLA", "CUI",
    "controlled unclassified information", "export control", "international traffic in arms"]

# --- Depth layer 2: controlled ARTIFACTS by file type (attachment names or body refs).
# The file itself is the trigger. CAD / native-engineering / analysis / EDA / GNC-model
# formats — these carry geometry, performance, or source that exceeds cleared content.
CAD_EXTS = [
    # SolidWorks / neutral CAD / Parasolid / CATIA / Inventor / Creo·NX·ProE / AutoCAD
    "sldprt", "sldasm", "slddrw", "step", "stp", "iges", "igs", "x_t", "x_b", "xmt_txt",
    "catpart", "catproduct", "cgr", "ipt", "iam", "idw", "prt", "asm", "drw", "dwg", "dxf",
    # mesh / neutral solids
    "stl", "3mf", "sat", "jt", "3dm",
    # FEA / CFD / CAM (Abaqus, Nastran, Fluent, mesh, toolpaths)
    "inp", "odb", "cae", "nas", "bdf", "cas", "msh", "cgns", "nc", "gcode", "cnc", "tap", "sim", "fem",
    # EDA / PCB
    "brd", "sch", "kicad_pcb", "gbr",
    # GNC / control models
    "slx", "mdl",
]
CAD_RX = re.compile(r'\.(' + "|".join(CAD_EXTS) + r')(?![A-Za-z0-9])', re.I)

# --- Depth layer 3: controlled TECHNICAL DATA beyond the export-cleared Payload User's
# Guide. Terms chosen to be INTERNAL engineering only — NOT the cleared interface specs
# (payload bay dims, 135 kg / 100 km, g-loads, vibration, shock, turnaround, keep-out).
TECHDATA = [
    # Propulsion internals / performance
    (r'\bspecific impulse\b|(?<![A-Za-z])Isp(?![A-Za-z])', 'Isp/specific impulse'),
    (r'\bchamber pressure\b', 'chamber pressure'),
    (r'\bexpansion ratio\b|\bnozzle contour\b|\bthroat (diameter|area)\b', 'nozzle/throat geometry'),
    (r'\bmixture ratio\b|\bO/?F ratio\b', 'O/F mixture ratio'),
    (r'\binjector\b|\b(regenerative|film)[\s-]?cool', 'engine injector/cooling design'),
    (r'\bcharacteristic velocity\b|\bc[\-\s]?star\b|\bc\*\b', 'c* / characteristic velocity'),
    (r'\bturbopump\b|\bimpeller\b', 'turbomachinery design'),
    (r'\bpropellant (formulation|chemistry)\b|\bgrain geometry\b|\bburn rate\b', 'propellant formulation/grain'),
    (r'\bthrust (curve|profile)\b', 'thrust curve'),
    (r'\bdetonation (wave|cell)\b|\bfill fraction\b', 'RDRE detonation physics'),
    # GNC / flight-software internals
    (r'\bcontrol law\b|\bcontrol gains?\b|\bgain schedule\b', 'control law/gains'),
    (r'\bKalman\b|\bstate estimator\b|\bnavigation filter\b', 'nav filter/estimator'),
    (r'\bflight software (source|code)\b|\bGNC source\b|\bautocoder\b', 'flight-software source'),
    (r'\bguidance algorithm\b|\bcontrol algorithm parameters?\b|\b6[\s-]?DOF\b|\bsix[\s-]degree', 'guidance / 6-DOF model'),
    (r'\bmonte carlo (dispersion|analysis)\b|\btrajectory optimization\b', 'trajectory dispersion/optimization'),
    # Composite / structural IP (Type-5 tank, IPS)
    (r'\bply (schedule|book)\b|\blay[\s-]?up\b|\blaminate schedule\b|\bfiber orientation\b', 'composite layup/ply schedule'),
    (r'\b(filament )?winding (pattern|angle)\b', 'winding pattern'),
    (r'\bcure cycle\b|\bautoclave cycle\b|\bprepreg\b|\bresin (formulation|chemistry|system)\b', 'cure/resin process'),
    (r'\bmargin of safety\b|\bknockdown factor\b|\ballowables\b', 'structural margins/allowables'),
    # Drawings / manufacturing detail
    (r'\bGD&T\b|\bgeometric dimensioning\b|\btolerance stack', 'GD&T / tolerance'),
    (r'\bweldment\b|\bCNC program\b|\bmachining (program|detail)\b', 'manufacturing detail'),
    # Performance beyond cleared envelope
    (r'\bdelta[\s-]?v\b|\bmass fraction\b|\bburnout velocity\b|\bstaging velocity\b', 'performance (delta-v / mass fraction)'),
]
_TECHDATA_C = [(re.compile(p, re.I), label) for p, label in TECHDATA]


def screen(text):
    """Return a de-duplicated list of matched controlled-content indicators.
    Layer 1 = explicit export-control markers; layer 2 = CAD/engineering file types
    (the artifact itself); layer 3 = technical data beyond the cleared Payload Guide."""
    if not text:
        return []
    found = []
    # Layer 1 — genuine control MARKINGS (not bare topical mentions)
    for rx, label in _COMPILED:
        if rx.search(text) and label not in found:
            found.append(label)
    # Layer 2 — controlled artifacts (CAD / native engineering / analysis files)
    exts = []
    for m in CAD_RX.finditer(text):
        e = m.group(1).lower()
        if e not in exts:
            exts.append(e)
    if exts:
        found.append("controlled CAD/engineering file (" + ", ".join("." + e for e in exts[:6]) + ")")
    # Layer 3 — controlled technical data (beyond cleared Payload User's Guide)
    for rx, label in _TECHDATA_C:
        if rx.search(text):
            lbl = "controlled technical data (" + label + ")"
            if lbl not in found:
                found.append(lbl)
    return found


# --- Depth layer 4 (semantic): local-LLM classifier. Catches controlled technical data
# the keyword/artifact layers miss ("does this EXCEED the cleared Payload User's Guide?").
# Advisory net on top of the deterministic floor. Fail-OPEN (Ollama down -> no LLM hit) so
# the intake never jams; the deterministic layers 1-3 remain the reliable control.
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen3.6:35b-a3b"
_CLEARED = ("Exos's EXPORT-CLEARED Payload User's Guide covers ONLY these PUBLIC interface specs "
    "(NOT controlled): payload bay 25 in dia x 38-48 in; up to 135 kg to ~100 km; vibration/shock/"
    "g-load environment levels; ~2-day turnaround; 7 km keep-out; 28V power; vented or pressurized "
    "bay; general capability and marketing statements.")
_LLM_PROMPT = ("You are an ITAR/EAR export-control pre-screen for Exos Aerospace, a US-regulated launch company.\n"
    + _CLEARED + "\n\nCONTROLLED (exceeds the cleared guide) = internal engineering/design/performance a "
    "foreign person could use to build or improve the vehicle: engine internals & performance (Isp, chamber "
    "pressure, injector/turbopump/cooling design, propellant formulation), thrust/trajectory/delta-v/mass-"
    "fraction data, GNC or flight-software design/source or control-law parameters, composite layup/winding/"
    "resin process, structural design margins/allowables, or detailed CAD/drawing geometry.\n\n"
    "Decide if the CONTENT below contains controlled technical data that EXCEEDS the cleared guide. Ignore "
    "mere mentions of compliance, ITAR as a selling point, and the cleared interface specs above. Respond "
    "ONLY as JSON: {\"controlled\": true|false, \"category\": \"<short>\", \"reason\": \"<one sentence>\"}. "
    "If genuinely unsure, use controlled=true.\n\nCONTENT:\n")


def classify_llm(text, timeout=25, min_len=300):
    """Local-LLM judgement: does `text` contain controlled data beyond the cleared Payload Guide?
    Returns {"category","reason"} on a controlled verdict, else None. Fail-open on any error."""
    if not text or len(text) < min_len:
        return None
    try:
        payload = json.dumps({
            "model": LLM_MODEL, "prompt": _LLM_PROMPT + text[:6000],
            "stream": False, "format": "json", "think": False,
            "options": {"temperature": 0},
        }).encode()
        req = urllib.request.Request(OLLAMA_URL, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as f:
            resp = json.load(f)
        v = json.loads((resp.get("response") or "").strip())
        if isinstance(v, dict) and v.get("controlled") is True:
            return {"category": str(v.get("category", "controlled"))[:60],
                    "reason": str(v.get("reason", ""))[:160]}
    except Exception:
        return None
    return None


def deep_hits(text, use_llm=True):
    """Primary entry point: deterministic layers 1-3, then (if clean and use_llm) the LLM layer.
    Skips the LLM when the deterministic net already holds (already quarantining)."""
    hits = screen(text)
    if hits or not use_llm:
        return hits
    v = classify_llm(text)
    if v:
        hits.append("LLM technical-data review: " + v["category"]
                    + (" — " + v["reason"] if v["reason"] else ""))
    return hits


def attachment_names(msg):
    names = []
    try:
        for p in msg.walk():
            fn = p.get_filename()
            if fn:
                names.append(fn)
    except Exception:
        pass
    return names


def _already(message_id):
    if not message_id or not os.path.exists(QLOG):
        return False
    try:
        with open(QLOG) as f:
            for line in f:
                try:
                    if json.loads(line).get("message_id") == message_id:
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _alert(text):
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.15.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", JON_DISCORD, "-m", text],
                       capture_output=True, text=True, timeout=60, env=env)
    except Exception:
        pass


_ID_RE = re.compile(r'\b((?:HP|BD|FUND|OPP|PROG|P3|P|B|D|REG)-\d{1,5})\b')


def _ct(iso_utc):
    """Format a UTC ISO timestamp as Central time, labeled — for human-facing display."""
    from datetime import datetime, timezone
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.strptime((iso_utc or "")[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %H:%M") + " CT"
    except Exception:
        return (iso_utc or "")[:16].replace("T", " ") + " UTC"


def _create_hold_decision(message_id, sender, subject, hits, body=""):
    """Drop the hold into the ROUTER'S OWN Decisions matrix so they must adjudicate it.
    Records exactly WHICH email (sender/subject) and links any task/opportunity it references."""
    try:
        arr = json.load(open(DECISIONS_FILE))
    except Exception:
        arr = []
    dedupe = "xctl-" + (message_id or subject or "")
    if any(d.get("dedupeKey") == dedupe for d in arr):
        return
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    who = sender or "jquinn@exosaero.com"
    m = _ID_RE.search((subject or "") + " " + (body or ""))
    related = m.group(1) if m else ""
    arr.append({
        "id": "XCTL-" + hashlib.sha1(dedupe.encode()).hexdigest()[:6].upper(),
        "created": now, "updated": now,
        "source": "Export-control screen",
        "relatedItem": related,
        "title": "Export-control HOLD — " + (subject or "(no subject)")[:80],
        "question": ("An email you routed to Mission Control was HELD as potential export-controlled "
                     "content (flagged: " + ", ".join(hits) + "). Was it correctly held?"),
        "context": ("HELD EMAIL — From: " + (sender or "unknown") + " · Subject: " + (subject or "(none)")
                    + " · held " + _ct(now) + ".\n"
                    + ("Appears related to " + related + ". " if related else "")
                    + "The email itself was NOT brought into Mission Control — it stays in the intake "
                    "inbox (and in SharePoint if that is where it belongs). Review it in your email to "
                    "decide. If it is controlled it stays put; if it is a false positive, re-send a "
                    "cleared version or ask an admin to release it — controlled content is never auto-released."),
        "proposedAction": "Confirm whether the hold was correct.",
        "type": "yesno",
        "options": ["Yes — correctly held (keep it in SharePoint)", "No — false positive"],
        "priority": "high", "dedupeKey": dedupe,
        "status": "open", "answer": None, "note": "", "answeredAt": None,
        "assignedTo": who, "approver": who,
    })
    tmp = DECISIONS_FILE + ".tmp"
    json.dump(arr, open(tmp, "w"), indent=2)
    os.replace(tmp, DECISIONS_FILE)


def all_recipients_internal(recipients):
    """True only if there is at least one recipient AND every recipient is an internal
    Exos address (exosaero.com or a Jon/ops alias). Internal US-person-to-US-person
    exchange is not an export, so such mail is not held. Fail-safe: an empty or
    unparseable recipient list returns False, so the hold still applies.
    NOTE: assumes exosaero.com recipients are U.S. persons; a foreign-person employee
    would be a deemed-export handled by Exos's separate personnel controls, not here."""
    recips = [r for r in (recipients or []) if r]
    if not recips:
        return False
    return all(_is_self(r) for r in recips)


def quarantine_and_alert(message_id, sender, subject, hits, source, body="", recipients=None):
    """Hold the email: log it, put an adjudication Decision in the sender's matrix, alert Jon.
    Deduped by message-id. Returns True if newly held.
    Internal-only transfers are NOT held: when every recipient is an internal Exos
    address, the hold is skipped (US-person-to-US-person is not an export). Full
    screening still applies whenever any recipient is external/foreign, or when the
    recipient list is unknown."""
    if recipients is not None and all_recipients_internal(recipients):
        return False
    if _already(message_id):
        return False
    os.makedirs(os.path.dirname(QLOG), exist_ok=True)
    rec = {"message_id": message_id, "sender": sender, "subject": subject,
           "indicators": hits, "source": source,
           "held_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(QLOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    try:
        _create_hold_decision(message_id, sender, subject, hits, body)
    except Exception:
        pass
    _alert("🛑 EXPORT-CONTROL HOLD — an email routed to the Mission Control intake was NOT "
           "captured or acted on (tripped export-control indicators). The sender now has a "
           "Decision in their matrix to confirm whether the hold is valid.\n"
           f"From: {sender}\nSubject: {subject}\nFlagged: {', '.join(hits)}")
    return True


if __name__ == "__main__":
    import sys
    print(screen(sys.stdin.read()))
