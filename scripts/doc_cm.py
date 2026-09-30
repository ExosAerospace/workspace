#!/usr/bin/env python3
"""
doc_cm.py — Controlled-document configuration management (CM) register + drift check.
exo3 r2 (r2-controlled-docs), audit theme 7 (Process Library NON-COMPLIANT; RTO data room PARTIAL).

What it does
  register  mission-control/data/cm-register.json — one row per controlled doc:
            cm_id (current doc_no), proposed_cm_id (scheme below, pending Jon), rev, owner,
            status, path, sha256, size, git_tracked, controlled_marking, and the APPROVED
            baseline {sha256, by, decision_id, at}. Sources: process-register.json rows
            (their `files`) + the RTO data-room manifest and every file it lists.
  check     re-hashes every row. A file whose sha256 != approved sha256 is an UNAPPROVED
            CHANGE (FAIL). Missing file = FAIL. Data-room: manifest hash change, a manifest
            doc with no lock row, or an extra file dropped in mission-control/dataroom/ = FAIL.
            Unregistered files in process-library area dirs / register files not in git = WARN.
            On a NEW FAIL set it files ONE deduped Decision card to Jon (dedupeKey
            cm-drift:<digest>) — AI proposes, a human confirms. fleet_log event every run.
  accept    `--accept-answered`: for drift cards Jon ANSWERED "Approve…" (status answered,
            i.e. a human session — token answers are only proposals since e13a807), re-baseline
            exactly the sha256s listed on that card. Nothing else ever moves a baseline.
  approve   `approve <path> --decision D-x`: re-baseline one doc, only if D-x is answered by a
            human with an approving answer. Used by Exo's CM step after Jon approves a revision.

Deterministic guards (not prompt text)
  * baseline only moves with a human-answered decision id recorded on the row.
  * controlled-marking scan (CUI banner / ITAR / export-control / distribution statement):
    marked files are registered HASH-ONLY with controlled_marking=true; `gitsafe` lists them so
    they are never committed; the drift card calls them out. Content is never copied or logged.
  * the data-room lock is the approved sha256 of the manifest + each served file; MC serving
    side can consult `dataroom_lock_ok()` / cm-register.json.

Usage
  python3 scripts/doc_cm.py build [--baseline-basis TEXT]   # (re)build register; keeps approvals
  python3 scripts/doc_cm.py check [--no-alert] [--json]
  python3 scripts/doc_cm.py check --accept-answered
  python3 scripts/doc_cm.py approve <path> --decision D-123
  python3 scripts/doc_cm.py gitsafe                          # untracked register files safe to commit
  python3 scripts/doc_cm.py scan <path>...                   # marking scan, names/reasons only
  python3 scripts/doc_cm.py --selftest
"""
import datetime, hashlib, json, os, re, subprocess, sys, tempfile, urllib.request, zipfile
from pathlib import Path

WS = Path("/Users/exomac/.openclaw/workspace")
sys.path.insert(0, str(WS / "scripts"))
try:
    from fleet_log import event as _fleet_event, new_corr
except Exception:  # logging must never break the check
    _fleet_event = None
    def new_corr():
        import uuid; return uuid.uuid4().hex[:16]

AGENT = "com.exos.doc-cm-drift"
PL = WS / "process-library"
PROC_REG = WS / "mission-control/data/process-register.json"
DR_MANIFEST = WS / "mission-control/data/dataroom-manifest.json"
DR_DIR = WS / "mission-control/dataroom"
CM_REG = WS / "mission-control/data/cm-register.json"
DECISIONS = WS / "mission-control/data/decisions.json"
STATE = WS / "state/doc-cm-state.json"
TOKEN = WS / "mission-control/data/.decisions-token"
INGEST = "http://127.0.0.1:8080/api/decisions/ingest"
SKIP_DIRS = {"_inbox", "_held", "_specs"}

# Proposed CM numbering scheme (PENDING Jon decision — never auto-applied to documents):
#   EXOS-<AREA>-<NNN>-<REV>   e.g. EXOS-GRN-001-0 (already used by build_procedure.py docs)
AREA_CODES = {
    "01-quality-as9100": "QMS", "02-ground-operations": "GRN", "03-payload": "PAY",
    "04-procurement": "PUR", "05-human-resources": "HR", "06-safety-ehs": "SAF",
    "07-hr-compliance-training": "HRC", "08-security-cui": "SEC", "09-records-schedules": "REC",
    "10-culture": "CUL", "11-administrative": "ADM", "11-manufacturing-build": "BLD",
    "12-finance-accounting": "FIN", "13-manufacturing": "MFG", "99-reference": "REF",
    "cmmc-2.0": "CMMC", "dataroom": "DR",
}
SCHEME_RE = re.compile(r"^EXOS-[A-Z]{2,4}-\d{3}-\d+$")

# Banner-style markings only (policy text that merely discusses CUI is not a banner).
MARKINGS = [
    ("CUI banner", re.compile(r"\bCUI\s*//\s*[A-Z]", re.I)),
    ("CUI designation block", re.compile(r"Controlled\s+by\s*:.{0,80}CUI\s+Category", re.I | re.S)),
    ("ITAR warning statement", re.compile(r"(contains?|includes?)\s+technical\s+data\s+whose\s+export\s+is\s+restricted", re.I)),
    ("ITAR-controlled marking", re.compile(r"\bITAR[\s-]+CONTROLLED\b(?!\s+(data|information)\s+(must|shall|is\s+not|may\s+not))", re.I)),
    ("Export-controlled marking", re.compile(r"\bEXPORT[\s-]+CONTROLLED\s*(-|:|//|—)", re.I)),
    ("Distribution statement B-F", re.compile(r"DISTRIBUTION\s+STATEMENT\s+[B-F]\b", re.I)),
    ("USML category citation", re.compile(r"\bUSML\s+Cat(egory)?\.?\s+[IVX]+\b", re.I)),
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(WS))


def fleet(action, detail, outcome=None, level="info", corr=None):
    if _fleet_event:
        try:
            return _fleet_event(AGENT, "govern", action, corr=corr, detail=detail,
                                owner="John Quinn", outcome=outcome, level=level)
        except Exception:
            pass
    return corr


def atomic_write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def load_json(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


# ---------------------------------------------------------------- marking scan
def extract_text(p):
    p = Path(p)
    ext = p.suffix.lower()
    try:
        if ext in (".docx", ".pptx", ".xlsx", ".docm") or p.name.endswith(".docx.prebrand-20260821") or ".docx.prebrand" in p.name:
            out = []
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    if n.endswith(".xml") and ("word/" in n or "ppt/slides/" in n or "sharedStrings" in n
                                                or "header" in n or "footer" in n):
                        out.append(re.sub(r"<[^>]+>", " ", z.read(n).decode("utf8", "ignore")))
            return " ".join(out)
        if ext == ".pdf":
            r = subprocess.run(["pdftotext", "-q", str(p), "-"], capture_output=True, timeout=60)
            return r.stdout.decode("utf8", "ignore")
        if ext in (".doc", ".rtf"):
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(p)], capture_output=True, timeout=60)
            return r.stdout.decode("utf8", "ignore")
        if ext in (".md", ".txt", ".json", ".csv", ".tbl", ".prb"):
            return p.read_text(errors="ignore")[:5_000_000]
    except Exception:
        return ""
    return ""


def scan_markings(p, text=None):
    text = extract_text(p) if text is None else text
    text = re.sub(r"\s+", " ", text)
    return sorted({name for name, rx in MARKINGS if rx.search(text)})


# ---------------------------------------------------------------- decisions
def decisions_by_id():
    d = load_json(DECISIONS, [])
    L = d if isinstance(d, list) else d.get("decisions", [])
    return {x.get("id"): x for x in L if isinstance(x, dict)}


APPROVE_RX = re.compile(r"^\s*(approve|keep|yes|accept)", re.I)


def human_approved(dec):
    """A decision counts only if a HUMAN answered it with an approving option.
    Token (agent) answers stay status=open with proposedAnswer since e13a807."""
    return bool(dec) and dec.get("status") == "answered" and bool(APPROVE_RX.match(str(dec.get("answer") or "")))


def ingest_decision(payload):
    tok = TOKEN.read_text().strip()
    req = urllib.request.Request(INGEST, data=json.dumps(payload).encode(), method="POST",
                                 headers={"x-exo-token": tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode() or "{}")


# ---------------------------------------------------------------- build
def git_tracked_set():
    r = subprocess.run(["git", "-C", str(WS), "ls-files", "-z", "process-library", "mission-control/dataroom",
                        "mission-control/data/dataroom-manifest.json"], capture_output=True)
    return set(x for x in r.stdout.decode().split("\0") if x)


def proposed_id(area_id, doc_no, rev, taken):
    if doc_no and SCHEME_RE.match(doc_no):
        return doc_no
    code = AREA_CODES.get(area_id, "GEN")
    m = re.search(r"(\d{3})", doc_no or "")
    n = int(m.group(1)) if m else 1
    r = re.sub(r"[^0-9]", "", str(rev)) if str(rev).isdigit() else "0"
    while True:
        cid = f"EXOS-{code}-{n:03d}-{r or '0'}"
        if cid not in taken:
            taken.add(cid)
            return cid
        n += 1


def build(basis):
    old = {r["path"]: r for r in load_json(CM_REG, {}).get("docs", [])}
    tracked = git_tracked_set()
    pr = load_json(PROC_REG, {}).get("register", [])
    docs, taken = [], set(r.get("doc_no") for r in pr if SCHEME_RE.match(str(r.get("doc_no") or "")))
    ts = now()

    def row(path, meta):
        p = WS / path
        prev = old.get(path, {})
        h = sha256(p) if p.exists() else None
        marks = prev.get("controlled_marking") if prev.get("sha256") == h and "controlled_marking" in prev else (
            scan_markings(p) if p.exists() else [])
        r = dict(meta, path=path, sha256=h, size=p.stat().st_size if p.exists() else None,
                 git_tracked=path in tracked, controlled_marking=marks)
        r["approved"] = prev.get("approved") or {
            "sha256": h, "by": "baseline (r2-controlled-docs)", "decision_id": None, "at": ts, "basis": basis}
        r["history"] = prev.get("history", [])
        return r

    for x in pr:
        for f in x.get("files") or []:
            path = f"process-library/{f}"
            docs.append(row(path, {
                "set": "process-library", "cm_id": x.get("doc_no"),
                "proposed_cm_id": proposed_id(x.get("area_id"), x.get("doc_no"), x.get("rev"), taken),
                "title": x.get("procedure"), "rev": x.get("rev"), "owner": x.get("owner"),
                "status": x.get("status"), "area_id": x.get("area_id")}))
    man = load_json(DR_MANIFEST, {})
    docs.append(row(rel(DR_MANIFEST), {"set": "dataroom", "cm_id": "DR-MANIFEST", "proposed_cm_id": "EXOS-DR-000-0",
                                       "title": "RTO data-room manifest (what is disclosed)", "rev": None,
                                       "owner": "John Quinn", "status": "Locked", "area_id": "dataroom"}))
    for i, d in enumerate(man.get("docs", []), 1):
        docs.append(row(f"mission-control/dataroom/{d.get('file')}", {
            "set": "dataroom", "cm_id": f"DR-{d.get('id')}", "proposed_cm_id": f"EXOS-DR-{i:03d}-0",
            "title": d.get("title"), "rev": None, "owner": "John Quinn", "status": "Locked (disclosed)",
            "area_id": "dataroom"}))
    reg = {
        "_doc": "Controlled-document CM register (exo3 r2, r2-controlled-docs). Built by scripts/doc_cm.py; "
                "approved.sha256 is the only accepted content — it moves only with a human-answered decision id. "
                "Content of marked (CUI/ITAR) files is never stored here — hash + marking names only.",
        "generated": ts,
        "numbering_scheme": {"proposed": "EXOS-<AREA>-<NNN>-<REV>", "status": "pending Jon approval",
                             "area_codes": AREA_CODES},
        "docs": docs,
    }
    atomic_write(CM_REG, reg)
    fleet("cm_register_build", {"docs": len(docs), "marked": sum(1 for d in docs if d["controlled_marking"]),
                                "untracked": sum(1 for d in docs if not d["git_tracked"])}, outcome="ok")
    return reg


# ---------------------------------------------------------------- check
def check(reg, alert=True, accept_answered=False, decisions=None):
    decisions = decisions_by_id() if decisions is None else decisions
    state = load_json(STATE, {})
    ts = now()
    fails, warns, accepted = [], [], []
    docs = reg.get("docs", [])
    by_path = {d["path"]: d for d in docs}

    # human-confirmed acceptance of earlier drift cards
    if accept_answered:
        for did, card in (state.get("cards") or {}).items():
            dec = decisions.get(did)
            if card.get("accepted") or not human_approved(dec):
                continue
            for path, h in card.get("items", {}).items():
                d = by_path.get(path)
                if not d and h and path.startswith("mission-control/dataroom/"):
                    d = {"set": "dataroom", "cm_id": "DR-" + Path(path).stem, "proposed_cm_id": None,
                         "title": Path(path).name, "rev": None, "owner": "John Quinn", "status": "Locked (disclosed)",
                         "area_id": "dataroom", "path": path, "sha256": h, "size": None, "git_tracked": False,
                         "controlled_marking": scan_markings(WS / path) if (WS / path).exists() else [],
                         "approved": {"sha256": None}, "history": []}
                    docs.append(d); by_path[path] = d
                if d and h:
                    d.setdefault("history", []).append(dict(d["approved"]))
                    d["approved"] = {"sha256": h, "by": dec.get("answeredBy") or "human",
                                     "decision_id": did, "at": ts, "basis": "drift card answered: " + str(dec.get("answer"))[:80]}
                    accepted.append(path)
            card["accepted"] = ts

    for d in docs:
        p = WS / d["path"]
        if not p.exists():
            fails.append({"path": d["path"], "why": "missing", "set": d["set"], "sha256": None})
            continue
        h = sha256(p)
        d["sha256"], d["size"] = h, p.stat().st_size
        if h != (d.get("approved") or {}).get("sha256"):
            fails.append({"path": d["path"], "why": "changed without approval", "set": d["set"], "sha256": h,
                          "cm_id": d.get("cm_id")})
    # data-room: every manifest doc must be locked; no stray files in the served dir
    man = load_json(DR_MANIFEST, {})
    for x in man.get("docs", []):
        path = f"mission-control/dataroom/{x.get('file')}"
        if path not in by_path:
            fails.append({"path": path, "why": "added to data-room manifest without approval", "set": "dataroom",
                          "sha256": sha256(WS / path) if (WS / path).exists() else None})
    if DR_DIR.exists():
        for f in sorted(DR_DIR.iterdir()):
            path = rel(f)
            if f.is_file() and not f.name.startswith(".") and path not in by_path:
                fails.append({"path": path, "why": "unlisted file in data-room folder", "set": "dataroom",
                              "sha256": sha256(f)})
    # data-room filesystem lock (chmod a-w on manifest + files, dir 0500): loosened -> WARN
    for d in docs:
        p = WS / d["path"]
        if d["set"] == "dataroom" and p.exists() and p.stat().st_mode & 0o222:
            warns.append({"path": d["path"], "why": "data-room lock off (file is writable)"})
    if DR_DIR.exists() and DR_DIR.stat().st_mode & 0o222:
        warns.append({"path": rel(DR_DIR), "why": "data-room lock off (folder is writable)"})
    # process-library hygiene (WARN only)
    for d in docs:
        if d["set"] == "process-library" and not d.get("git_tracked") and not d.get("controlled_marking"):
            warns.append({"path": d["path"], "why": "not in git"})
    for root, dirs, files in os.walk(PL):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in files:
            path = rel(Path(root) / f)
            if not f.startswith(".") and path not in by_path and ".prebrand" not in f and not f.endswith(".json"):
                warns.append({"path": path, "why": "unregistered file in controlled library"})

    marked = [d["path"] for d in docs if d.get("controlled_marking")]
    digest = hashlib.sha256(json.dumps(sorted((f["path"], f["sha256"] or "") for f in fails)).encode()).hexdigest()[:12]
    corr = new_corr()
    filed = None
    if fails and alert and digest != state.get("last_fail_digest"):
        filed = file_drift_card(fails, digest, corr)
        if filed:
            state.setdefault("cards", {})[filed] = {"digest": digest, "filed": ts,
                                                    "items": {f["path"]: f["sha256"] for f in fails if f["sha256"]}}
            state["last_fail_digest"] = digest
    elif not fails:
        state["last_fail_digest"] = None
    res = {"ts": ts, "status": "FAIL" if fails else ("WARN" if warns else "OK"), "docs": len(docs),
           "fails": fails, "warns": len(warns), "warn_items": warns[:50], "marked": marked,
           "accepted": accepted, "drift_decision": filed, "corr": corr}
    state.update({"last_run": ts, "last_status": res["status"], "last_fail_count": len(fails), "last_warn_count": len(warns)})
    fleet("cm_drift_check", {"docs": len(docs), "fail": len(fails), "warn": len(warns), "marked": len(marked),
                             "accepted": len(accepted), "decision": filed,
                             "fail_paths": [f["path"] for f in fails][:20]},
          outcome=res["status"], level="error" if fails else ("warn" if warns else "info"), corr=corr)
    return res, state


def file_drift_card(fails, digest, corr):
    dr = [f for f in fails if f["set"] == "dataroom"]
    lines = [f"- {f['path']} — {f['why']}" + (f" (sha256 {f['sha256'][:12]})" if f.get("sha256") else "") for f in fails[:25]]
    payload = {
        "title": "EXO3: Controlled document changed without approval" + (" — DATA ROOM" if dr else ""),
        "question": f"{len(fails)} controlled document(s) changed since their last approved revision — approve these exact versions, or have them reverted?",
        "context": "The nightly CM drift check (scripts/doc_cm.py) found content that does not match the approved "
                   "sha256 in mission-control/data/cm-register.json:\n" + "\n".join(lines) +
                   ("\n(+ more — see state/doc-cm-state.json)" if len(fails) > 25 else "") +
                   "\n\nIf you approve, only these exact file versions become the approved revision (next check run). "
                   "If you choose revert, Exo restores the last approved version from git (untracked files: from the "
                   "asset backup) and reports back. Nothing is changed until you answer.",
        "proposedAction": "Approve if you or the owner made these edits on purpose; otherwise revert.",
        "type": "choice",
        "options": ["Approve these versions", "Revert to last approved", "Hold — ask the owner"],
        "priority": "high" if dr else "med",
        "dedupeKey": f"cm-drift:{digest}",
        "source": "exo3-doc-cm",
        "agentClass": "GOVERN",
        "assignedTo": "jquinn@exosaero.com",
        "approver": "John Quinn",
        "relatedItem": "cm-register",
        "correlationId": corr,
    }
    try:
        r = ingest_decision(payload)
        return r.get("id") or (r.get("decision") or {}).get("id")
    except Exception as e:
        fleet("cm_drift_alert_failed", {"error": str(e)[:200]}, outcome="error", level="error", corr=corr)
        return None


# ---------------------------------------------------------------- approve / gitsafe
def approve(reg, path, did, decisions=None):
    decisions = decisions_by_id() if decisions is None else decisions
    dec = decisions.get(did)
    if not human_approved(dec):
        raise SystemExit(f"REFUSED: {did} is not answered-approve by a human (status={dec and dec.get('status')}, "
                         f"answer={dec and dec.get('answer')!r}). Baselines move only on a human answer.")
    d = next((x for x in reg["docs"] if x["path"] == path), None)
    if not d:
        raise SystemExit(f"not in register: {path} (run build first)")
    h = sha256(WS / path)
    d.setdefault("history", []).append(dict(d["approved"]))
    d["approved"] = {"sha256": h, "by": dec.get("answeredBy") or "human", "decision_id": did, "at": now(),
                     "basis": "approve " + str(dec.get("answer"))[:80]}
    fleet("cm_approve", {"path": path, "decision": did, "sha256": h[:12]}, outcome="ok")
    return d


def gitsafe(reg):
    return [d["path"] for d in reg["docs"] if not d["git_tracked"] and not d["controlled_marking"]
            and (WS / d["path"]).exists()]


# ---------------------------------------------------------------- selftest
def selftest():
    global WS, PL, PROC_REG, DR_MANIFEST, DR_DIR, CM_REG, STATE, _fleet_event
    import shutil
    ok, n = 0, 0
    saved = (WS, PL, PROC_REG, DR_MANIFEST, DR_DIR, CM_REG, STATE, _fleet_event)
    tmp = Path(tempfile.mkdtemp(prefix="doccm-st-")).resolve()
    real_card = globals()["file_drift_card"]
    try:
        WS = tmp; PL = tmp / "process-library"; PROC_REG = tmp / "mission-control/data/process-register.json"
        DR_MANIFEST = tmp / "mission-control/data/dataroom-manifest.json"; DR_DIR = tmp / "mission-control/dataroom"
        CM_REG = tmp / "mission-control/data/cm-register.json"; STATE = tmp / "state/doc-cm-state.json"
        _fleet_event = None
        (PL / "02-ground-operations").mkdir(parents=True); DR_DIR.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(tmp)])
        (PL / "02-ground-operations/GRN-001.txt").write_text("crane procedure rev 0")
        (PL / "02-ground-operations/marked.txt").write_text("CUI//SP-EXPT  trajectory tables")
        (DR_DIR / "deck.txt").write_text("deck v1")
        atomic_write(PROC_REG, {"register": [
            {"area_id": "02-ground-operations", "doc_no": "GRN-001", "rev": "0", "procedure": "Crane",
             "owner": "Steve", "status": "Approved", "files": ["02-ground-operations/GRN-001.txt"]},
            {"area_id": "02-ground-operations", "doc_no": "EXOS-GRN-002-0", "rev": "0", "procedure": "Marked",
             "owner": "Steve", "status": "Draft", "files": ["02-ground-operations/marked.txt"]}]})
        atomic_write(DR_MANIFEST, {"docs": [{"id": "deck", "file": "deck.txt", "title": "Deck"}]})
        filed = []
        globals()["file_drift_card"] = lambda fails, digest, corr: (filed.append(digest), f"D-T{len(filed)}")[1]

        def t(name, cond):
            nonlocal ok, n
            n += 1; ok += bool(cond); print(("PASS " if cond else "FAIL ") + name)

        reg = build("selftest")
        t("register rows = 2 docs + manifest + 1 dataroom file", len(reg["docs"]) == 4)
        t("proposed id keeps scheme-conformant doc_no", any(d["proposed_cm_id"] == "EXOS-GRN-002-0" for d in reg["docs"]))
        t("legacy doc_no GRN-001 gets EXOS-GRN-001-0 proposal", any(d["proposed_cm_id"] == "EXOS-GRN-001-0" for d in reg["docs"]))
        t("CUI banner file flagged controlled_marking", any(d["controlled_marking"] for d in reg["docs"] if d["path"].endswith("marked.txt")))
        t("marked file excluded from gitsafe", all(not p.endswith("marked.txt") for p in gitsafe(reg)))
        res, st = check(reg, alert=True, decisions={}); atomic_write(STATE, st)
        t("clean baseline -> no FAIL", res["status"] != "FAIL" and not filed)
        # replay the audit gap: an edit with no approval
        (PL / "02-ground-operations/GRN-001.txt").write_text("crane procedure EDITED")
        res, st = check(reg, alert=True, decisions={}); atomic_write(STATE, st)
        t("unapproved edit -> FAIL + one decision card", res["status"] == "FAIL" and len(filed) == 1)
        res, st = check(reg, alert=True, decisions={}); atomic_write(STATE, st)
        t("same drift again -> deduped (no second card)", len(filed) == 1)
        # data-room: add a doc to the manifest + drop an unlisted file
        atomic_write(DR_MANIFEST, {"docs": [{"id": "deck", "file": "deck.txt"}, {"id": "x", "file": "new.txt"}]})
        (DR_DIR / "new.txt").write_text("409A")
        res, st = check(reg, alert=True, decisions={}); atomic_write(STATE, st)
        whys = {f["why"] for f in res["fails"]}
        t("data-room manifest edit + new doc -> FAIL", "added to data-room manifest without approval" in whys
          and any(f["path"].endswith("dataroom-manifest.json") for f in res["fails"]))
        t("new drift set -> new card", len(filed) == 2)
        # agent (token) answer is only a proposal -> must NOT move baseline
        prop = {"D-T2": {"id": "D-T2", "status": "open", "proposedAnswer": "Approve these versions"}}
        res, st = check(reg, alert=False, accept_answered=True, decisions=prop); atomic_write(STATE, st)
        t("agent-proposed answer does not re-baseline", not res["accepted"] and res["status"] == "FAIL")
        try:
            approve(reg, "process-library/02-ground-operations/GRN-001.txt", "D-T2", decisions=prop); t("approve refuses non-human", False)
        except SystemExit:
            t("approve refuses non-human", True)
        hum = {"D-T2": {"id": "D-T2", "status": "answered", "answer": "Approve these versions", "answeredBy": "Jon"}}
        res, st = check(reg, alert=False, accept_answered=True, decisions=hum); atomic_write(STATE, st)
        t("human-answered approve re-baselines exactly the listed files (incl. new data-room doc)", len(res["accepted"]) == 3)
        for f in [DR_MANIFEST, DR_DIR / "deck.txt", DR_DIR / "new.txt"]:
            os.chmod(f, 0o400)
        os.chmod(DR_DIR, 0o500)
        res2, _ = check(reg, alert=False, decisions=hum)
        t("locked data room -> no lock-off warning", not any("lock off" in w["why"] for w in res2["warn_items"]))
        os.chmod(DR_DIR, 0o700)
        t("after human approval the same content is clean", res2["status"] != "FAIL")
        os.chmod(DR_MANIFEST, 0o600); (DR_DIR / "new.txt").unlink(); atomic_write(DR_MANIFEST, {"docs": [{"id": "deck", "file": "deck.txt"}]})
        atomic_write(STATE, st)
        rej = {"D-T9": {"id": "D-T9", "status": "answered", "answer": "Revert to last approved"}}
        try:
            approve(reg, "process-library/02-ground-operations/GRN-001.txt", "D-T9", decisions=rej); t("approve refuses 'Revert' answer", False)
        except SystemExit:
            t("approve refuses 'Revert' answer", True)
    finally:
        WS, PL, PROC_REG, DR_MANIFEST, DR_DIR, CM_REG, STATE, _fleet_event = saved
        globals()["file_drift_card"] = real_card
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"doc_cm selftest {ok}/{n}")
    fleet("selftest", {"pass": ok, "total": n}, outcome="ok" if ok == n else "fail")
    return ok == n


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    if argv[0] == "--selftest":
        return 0 if selftest() else 1
    cmd = argv[0]
    if cmd == "build":
        basis = argv[argv.index("--baseline-basis") + 1] if "--baseline-basis" in argv else "baseline"
        reg = build(basis)
        print(f"register: {len(reg['docs'])} docs -> {rel(CM_REG)}")
        return 0
    if cmd == "scan":
        for p in argv[1:]:
            print(f"{p}\t{', '.join(scan_markings(p)) or '-'}")
        return 0
    reg = load_json(CM_REG, None)
    if not reg:
        print("no register — run build first"); return 2
    if cmd == "check":
        res, state = check(reg, alert="--no-alert" not in argv, accept_answered="--accept-answered" in argv)
        atomic_write(CM_REG, reg)
        atomic_write(STATE, state)
        if "--json" in argv:
            print(json.dumps(res, indent=1))
        else:
            print(f"{res['status']}: {res['docs']} docs, {len(res['fails'])} fail, {res['warns']} warn, "
                  f"{len(res['marked'])} marked, accepted {len(res['accepted'])}, card {res['drift_decision']}")
            for f in res["fails"]:
                print(f"  FAIL {f['path']} — {f['why']}")
        return 0  # drift is reported via decision + fleet_log, not as a crash
    if cmd == "approve":
        d = approve(reg, argv[1], argv[argv.index("--decision") + 1])
        atomic_write(CM_REG, reg)
        print(f"approved {d['path']} @ {d['approved']['sha256'][:12]} ({d['approved']['decision_id']})")
        return 0
    if cmd == "gitsafe":
        print("\n".join(gitsafe(reg)))
        return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
