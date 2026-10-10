#!/usr/bin/python3
"""
decision_docs_guard_exo3.py — every open Decision card carries the documents its text references.

Jon 10/10 (core principle): a Decision card must carry the documents Jon needs to review so he
never has to chase them. D-7282043 (flight-test ladder strategy) said "Strategy memo:
drafts/Exos_Strategy_FlightTestLadder_..._2026-10-10.docx (emailed)" but had NO documents pinned.
Root cause: ingesters mention drafts/ paths in text without attaching them.

What it does (GOVERN guardrail, launchd com.exos.decision-docs-guard-exo3, every 5 min):
  For every OPEN decision (status open/pending/delegated) in mission-control/data/decisions.json
  (read-only) that has no docKeys and no current decision-linked uploads (or whose docs were placed
  by this guard and the referenced set has since changed):
    1. extract referenced document paths from title/question/context/proposedAction
       (drafts/…, capture/…, data-room/…, absolute/~ workspace paths, quoted paths, and bare
       filenames that exist in drafts/); .docx/.pdf/.xlsx/.pptx. A same-stem .pdf sibling is added
       as the review companion (doc key "<key>__pdf").
    2. attach them:
       - decision with a task id (docTask / numeric relatedItem / "task #N") AND a dedupeKey:
         scripts/mc-attach.py --task <id> --doc-key <key>, then re-ingest via /api/decisions/ingest
         with the SAME dedupeKey, all existing fields, docKeys + docTask.
       - otherwise: copy into mission-control/uploads with a _meta.json entry carrying decision_id
         (read → modify → tmp → os.replace, re-read immediately before writing), and pin docKeys via
         ingest when the card has a dedupeKey.
    .md files are never attached (logged as "referenced but .md"). A referenced file that does not
    exist is logged and ONE note line per decision goes to #exomac-system.
  Idempotent: logs/decision-docs-guard-state.json keeps the attached signature per decision.

Library use (born-with-docs at the source): governance/route.py escalate_and_file() and
opportunity_processor._ingest_decision() call ensure_docs(dedupe_key=…) right after ingest.

  /usr/bin/python3 scripts/decision_docs_guard_exo3.py run [--dry-run] [--id D-…]
  /usr/bin/python3 scripts/decision_docs_guard_exo3.py --selftest
"""
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, tempfile, time, uuid
import urllib.request

AGENT_ID = "decision-docs-guard-exo3"
GUARD_BY = "decision-docs-guard-exo3"
WS = "/Users/exomac/.openclaw/workspace"
SCRIPTS = os.path.join(WS, "scripts")
SYS_CHANNEL = "channel:1501636814849577050"   # #exomac-system (never Jon's DM)
OPEN_STATUSES = ("open", "pending", "delegated")
DOC_EXTS = (".docx", ".pdf", ".xlsx", ".pptx")
REF_EXTS = DOC_EXTS + (".md",)
ROOT_PREFIXES = ("drafts/", "capture/", "data-room/")
TEXT_FIELDS = ("title", "question", "context", "proposedAction")
# Roles for which pinning a doc on a card assigned to them GRANTS external access (server.js
# ddReviewerDecisionDocAllowed). New external doc exposure is Jon's call — never automatic.
EXTERNAL_DOC_ROLES = ("dd_reviewer", "montana_partner")


class Paths:
    def __init__(self, ws=WS):
        self.ws = ws
        self.mc = os.path.join(ws, "mission-control")
        self.decisions = os.path.join(self.mc, "data", "decisions.json")
        self.uploads = os.path.join(self.mc, "uploads")
        self.meta = os.path.join(self.uploads, "_meta.json")
        self.token = os.path.join(self.mc, "data", ".decisions-token")
        self.state = os.path.join(ws, "logs", "decision-docs-guard-state.json")
        self.log = os.path.join(ws, "logs", "decision-docs-guard-exo3.log")
        self.users = os.path.join(self.mc, "users.json")


P = Paths()


def iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg, paths=None):
    paths = paths or P
    try:
        if TEST:
            raise RuntimeError("selftest: stdout only")
        os.makedirs(os.path.dirname(paths.log), exist_ok=True)
        with open(paths.log, "a") as f:
            f.write(f"{iso()} {msg}\n")
    except Exception:
        pass
    print(msg)


TEST = False


def trace(action, detail, outcome=None, level="info"):
    if TEST:
        return None
    try:
        sys.path.insert(0, SCRIPTS)
        import fleet_log
        return fleet_log.event(AGENT_ID, "govern", action, detail=detail, owner="John Quinn",
                               outcome=outcome, level=level)
    except Exception:
        return None


def _slug_fn():
    try:
        spec = importlib.util.spec_from_file_location("mc_attach", os.path.join(SCRIPTS, "mc-attach.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.slug
    except Exception:
        return lambda s: re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(s))[0].lower()).strip("-") or "document"


_mc_slug = _slug_fn()


def slug(path):
    """Stable doc key: filename minus trailing date/draft tokens (so dated revisions chain as versions),
    but numeric ids are kept (mc-attach's slug turns OPP_PAY-6680_… into a colliding "opp-pay")."""
    s = os.path.splitext(os.path.basename(path))[0].lower()
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r"[\s_.\-]*\(?\d{4}-\d{2}-\d{2}\)?$", "", s)
        s = re.sub(r"[\s_.\-]+(draft|copy)$", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or _mc_slug(path)


def load_json(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def write_json_atomic(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = f"{p}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, p)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ───────────────────────────── extraction ─────────────────────────────
_EXT_RE = r"\.(?:docx|pdf|xlsx|pptx|md)"
_QUOTED = re.compile(r"[`\"]([^`\"\n]{1,300}?" + _EXT_RE + r")[`\"]", re.I)
_TOKEN = re.compile(r"(?<![\w./~-])((?:~|/)?[\w.~/-]*?[\w()-]+" + _EXT_RE + r")(?![\w])", re.I)


def extract_refs(text):
    """Referenced path strings as (ref, quoted) pairs (order-preserving, de-duplicated).
    Quoted refs may contain spaces; they only count when the file exists."""
    out, seen = [], set()
    for rx, quoted in ((_QUOTED, True), (_TOKEN, False)):
        for m in rx.finditer(text or ""):
            s = m.group(1).strip().rstrip(".,;:)")
            if quoted and " " not in s:
                continue          # the token pass catches space-free paths
            if s and s not in seen:
                seen.add(s); out.append((s, quoted))
    return out


def resolve_ref(ref, ws):
    """Map a referenced string to an absolute path inside the workspace (or None if unresolvable).
    Returns (abs_path_or_candidate, kind) kind ∈ {'path','bare'}."""
    r = ref.strip()
    if r.startswith("~/"):
        r = os.path.expanduser(r)
    if r.startswith("/"):
        return os.path.normpath(r), "path"
    rel = r[2:] if r.startswith("./") else r
    if rel.startswith("workspace/"):
        rel = rel[len("workspace/"):]
    if rel.startswith(ROOT_PREFIXES) or "/" in rel:
        return os.path.normpath(os.path.join(ws, rel)), "path"
    return os.path.join(ws, "drafts", rel), "bare"


def collect_docs(decision, ws):
    """→ dict(docs=[{path,key,role}], md=[…], missing=[…], outside=[…])."""
    text = "\n".join(str(decision.get(k) or "") for k in TEXT_FIELDS)
    md, missing, outside, files = [], [], [], []
    wsr = os.path.realpath(ws)
    for ref, quoted in extract_refs(text):
        path, kind = resolve_ref(ref, ws)
        if quoted and not os.path.isfile(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        real = os.path.realpath(path)
        if not (real == wsr or real.startswith(wsr + os.sep)) or os.sep + "mission-control" + os.sep + "uploads" + os.sep in real:
            outside.append(ref); continue
        if ext == ".md":
            md.append(ref); continue
        if ext not in DOC_EXTS:
            continue
        if not os.path.isfile(path):
            if kind == "bare":
                continue          # bare names only count when they exist in drafts/
            missing.append(ref); continue
        if path not in files:
            files.append(path)
    # group by stem: primary (office) + same-stem .pdf companion
    groups = {}
    for p in files:
        groups.setdefault(os.path.splitext(p)[0], set()).add(p)
    docs = []
    for stem in sorted(groups, key=lambda s: min(files.index(p) for p in groups[s])):
        members = groups[stem]
        office = [p for p in members if not p.lower().endswith(".pdf")]
        pdf = stem + ".pdf" if os.path.isfile(stem + ".pdf") else None
        for o in sorted(office):
            key = slug(o)
            if len(office) > 1:
                key = f"{key}-{os.path.splitext(o)[1].lstrip('.').lower()}"
            docs.append({"path": o, "key": key, "role": "doc"})
            if pdf:
                docs.append({"path": pdf, "key": key + "__pdf", "role": "pdf"})
        if not office and pdf:
            docs.append({"path": pdf, "key": slug(pdf), "role": "doc"})
    # de-dup by key (two office files sharing a pdf create one companion per key, that is fine)
    seen, uniq = set(), []
    for d in docs:
        if d["key"] not in seen:
            seen.add(d["key"]); uniq.append(d)
    return {"docs": uniq, "md": md, "missing": missing, "outside": outside}


# ───────────────────────────── eligibility ─────────────────────────────
def decision_task_id(d):
    for v in (d.get("docTask"),):
        if v is not None and str(v).strip():
            m = re.findall(r"\d+", str(v))
            if len(m) == 1:
                return m[0]
    ri = str(d.get("relatedItem") if d.get("relatedItem") is not None else "").strip()
    if re.fullmatch(r"#?\d+", ri):
        return ri.lstrip("#")
    ids = set(re.findall(r"task\s*#?\s*(\d+)", ri, re.I))
    for v in (d.get("taskId"), d.get("relatedTaskId"), d.get("related_task"), d.get("relatedTask")):
        m = re.search(r"(\d+)", str(v if v is not None else ""))
        if m:
            ids.add(m.group(1))
    return ids.pop() if len(ids) == 1 else None


def doc_keys(d):
    v = d.get("docKeys")
    if not isinstance(v, list):
        return []
    return [str(k).strip() for k in v if str(k or "").strip()]


def external_roles(users):
    """email/name (lower) → role, for roles where a pinned doc becomes externally visible."""
    out = {}
    rows = users.get("users", users) if isinstance(users, dict) else users
    rows = rows.values() if isinstance(rows, dict) else (rows or [])
    for u in rows:
        if isinstance(u, dict) and u.get("role") in EXTERNAL_DOC_ROLES:
            for k in (u.get("email"), u.get("name")):
                if k:
                    out[str(k).strip().lower()] = u["role"]
    return out


def eligibility(d, meta, state, ext=None):
    """→ (eligible: bool, reason)."""
    st = d.get("status") or "open"
    if st not in OPEN_STATUSES:
        return False, "not-open"
    for who in (d.get("assignedTo"), d.get("approver")):
        w = str(who or "").strip().lower()
        if w and ext and (w in ext or any(e in w for e in ext if "@" in e)):
            return False, "external-assignee"
    did = str(d.get("id"))
    mine = (state.get("decisions") or {}).get(did) or {}
    keys = doc_keys(d)
    if keys:
        if len(keys) == 1 and keys[0].lower() == "none":
            return False, "docKeys-none"
        if mine.get("docKeys") and sorted(mine["docKeys"]) == sorted(keys):
            return True, "guard-owned-pin"
        return False, "pinned"
    linked = [m for m in meta if str(m.get("decision_id")) == did and m.get("current") is not False]
    if any(m.get("uploaded_by") != GUARD_BY for m in linked):
        return False, "decision-linked"
    return True, ("guard-owned-linked" if linked else "no-docs")


def plan_decision(d, meta, state, ws, ext=None):
    ok, why = eligibility(d, meta, state, ext)
    if not ok:
        return {"id": d.get("id"), "skip": why}
    c = collect_docs(d, ws)
    sig = sorted([os.path.relpath(x["path"], ws), x["key"], sha256(x["path"])] for x in c["docs"])
    mine = (state.get("decisions") or {}).get(str(d.get("id"))) or {}
    task = decision_task_id(d) if d.get("dedupeKey") else None
    out = {"id": d.get("id"), "reason": why, "task": task, "dedupeKey": d.get("dedupeKey") or "",
           "docs": c["docs"], "md": c["md"], "missing": c["missing"], "outside": c["outside"], "sig": sig,
           "mode": "task" if task else "decision"}
    if not c["docs"]:
        out["skip"] = "no-attachable-refs"
    elif mine.get("sig") == sig and why != "no-docs":
        out["skip"] = "unchanged"
    return out


# ───────────────────────────── actions ─────────────────────────────
def mc_attach(task, path, key, title=None):
    cmd = ["/usr/bin/python3", os.path.join(SCRIPTS, "mc-attach.py"), "--task", str(task), "--file", path,
           "--doc-key", key, "--by", GUARD_BY]
    if title:
        cmd += ["--title", title]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def link_uploads(did, docs, paths=None):
    """Decision-linked uploads, written safely: copy files first, then re-read _meta immediately
    before the write, merge our records, tmp → os.replace."""
    paths = paths or P
    staged = []
    for x in docs:
        fn = os.path.basename(x["path"])
        h = sha256(x["path"])
        stored = f"{int(time.time() * 1000)}_{re.sub(r'[^A-Za-z0-9._-]', '_', fn)}"
        staged.append((x, fn, h, stored))
        time.sleep(0.002)
    meta = load_json(paths.meta, None)
    if not isinstance(meta, list):
        raise RuntimeError("uploads/_meta.json unreadable — refusing to write")
    results, new, copies = [], [], []
    for x, fn, h, stored in staged:
        cur = [m for m in meta if str(m.get("decision_id")) == str(did) and m.get("doc_key") == x["key"]
               and m.get("current") is not False]
        same = False
        for m in cur:
            try:
                same = same or sha256(os.path.join(paths.uploads, m["stored_name"])) == h
            except Exception:
                pass
        if same:
            results.append(f"unchanged {x['key']}"); continue
        copies.append((x["path"], stored))
        prev = max([int(m.get("version", 1)) for m in meta if str(m.get("decision_id")) == str(did)
                    and m.get("doc_key") == x["key"]] or [0])
        new.append({"id": uuid.uuid4().hex[:16], "filename": fn, "stored_name": stored,
                    "size": os.path.getsize(x["path"]), "extension": os.path.splitext(fn)[1].lower(),
                    "task_id": None, "project_id": None, "decision_id": str(did), "doc_key": x["key"],
                    "version": prev + 1, "current": True, "uploaded_by": GUARD_BY, "uploaded_at": iso(),
                    "source_path": os.path.relpath(x["path"], paths.ws)})
        results.append(f"linked {x['key']} v{prev + 1}")
    if not new:
        return results
    for src, stored in copies:
        shutil.copy2(src, os.path.join(paths.uploads, stored))
    # re-read immediately before writing so a concurrent writer's records are never clobbered
    meta = load_json(paths.meta, None)
    if not isinstance(meta, list):
        raise RuntimeError("uploads/_meta.json unreadable at write time — refusing to write")
    keys = {r["doc_key"] for r in new}
    for m in meta:
        if str(m.get("decision_id")) == str(did) and m.get("doc_key") in keys and m.get("current") is not False:
            m["current"] = False
            m["superseded_at"] = iso()
    meta.extend(new)
    write_json_atomic(paths.meta, meta)
    return results


def ingest_pin(d, keys, task, paths=None):
    """Re-ingest with the SAME dedupeKey, every existing field, + docKeys (+ docTask)."""
    paths = paths or P
    body = {k: d.get(k) for k in ("title", "question", "context", "proposedAction", "type", "options",
                                  "priority", "relatedItem", "source", "agentClass", "correlationId",
                                  "approver", "assignedTo", "docLegend") if d.get(k) is not None}
    body["dedupeKey"] = d["dedupeKey"]
    body["docKeys"] = keys
    if task:
        body["docTask"] = str(task)
    tok = open(paths.token).read().strip()
    req = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-Exo-Token": tok})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read().decode() or "{}")
    if res.get("deduped") or str(res.get("id")) != str(d.get("id")):
        raise RuntimeError(f"ingest did not update {d.get('id')} in place (got {res.get('id')} deduped={res.get('deduped')})")
    return res


def notify_missing(did, title, missing):
    text = (f"[decision-docs-guard] {did} \"{(title or '')[:80]}\" references document(s) that do not exist: "
            + ", ".join(missing[:5]) + (" …" if len(missing) > 5 else "") + " — card has no docs for them.")
    try:
        sys.path.insert(0, SCRIPTS)
        from deliver import deliver
        deliver(text, target=SYS_CHANNEL, source=AGENT_ID)
        return True
    except Exception as e:
        log(f"  ! notify failed: {e}")
        return False


def execute(pl, d, state, paths=None, dry=False):
    paths = paths or P
    did = str(pl["id"])
    ds = state.setdefault("decisions", {}).setdefault(did, {})
    refs_note = {"md": pl.get("md") or [], "missing": pl.get("missing") or [], "outside": pl.get("outside") or []}
    if dry or ds.get("refs_note") != refs_note:      # log reference problems once per change, not every 5 min
        if refs_note["md"]:
            log(f"  {did}: referenced but .md (not attached): {', '.join(refs_note['md'])}")
        if refs_note["outside"]:
            log(f"  {did}: referenced outside workspace (ignored): {', '.join(refs_note['outside'])}")
        if refs_note["missing"]:
            log(f"  {did}: MISSING referenced file(s): {', '.join(refs_note['missing'])}")
        if not dry:
            ds["refs_note"] = refs_note
    if pl.get("missing"):
        if not dry and sorted(pl["missing"]) != sorted(ds.get("notified_missing") or []):
            if notify_missing(did, d.get("title"), pl["missing"]):
                ds["notified_missing"] = sorted(pl["missing"])
    if pl.get("skip"):
        return None
    names = [f"{os.path.relpath(x['path'], paths.ws)} [{x['key']}]" for x in pl["docs"]]
    log(f"  {did}: {'WOULD attach' if dry else 'attach'} via {pl['mode']}"
        f"{' #' + pl['task'] if pl['task'] else ''}: {'; '.join(names)}")
    if dry:
        return "dry"
    keys = [x["key"] for x in pl["docs"]]
    if pl["mode"] == "task":
        # pdf companions first so the office original is the newest upload on the task
        for x in sorted(pl["docs"], key=lambda x: 0 if x["role"] == "pdf" else 1):
            rc, out = mc_attach(pl["task"], x["path"], x["key"])
            if rc == 3:
                log(f"    {x['key']}: mc-attach refused older file (a newer revision is current; pin follows it)")
            elif rc != 0:
                raise RuntimeError(f"mc-attach failed rc={rc}: {out[-200:]}")
            else:
                log(f"    {out.splitlines()[0] if out else 'ok'}")
    else:
        for r in link_uploads(did, sorted(pl["docs"], key=lambda x: 0 if x["role"] == "pdf" else 1), paths):
            log(f"    {r}")
    if pl.get("dedupeKey"):
        ingest_pin(d, keys, pl["task"], paths)
        log(f"    re-ingested {did} docKeys={keys}{' docTask=' + pl['task'] if pl['task'] else ''}")
        ds["docKeys"] = keys
    ds.update({"sig": pl["sig"], "mode": pl["mode"], "task": pl["task"], "at": iso(),
               "files": [os.path.relpath(x["path"], paths.ws) for x in pl["docs"]]})
    trace("decision_docs_attached", {"decision": did, "mode": pl["mode"], "task": pl["task"], "docKeys": keys,
                                     "missing": pl.get("missing"), "md": pl.get("md")}, outcome="attached")
    return "attached"


def run(dry=False, only=None, dedupe_key=None, paths=None, quiet_skips=True):
    paths = paths or P
    decisions = load_json(paths.decisions, [])
    meta = load_json(paths.meta, [])
    state = load_json(paths.state, {"decisions": {}})
    ext = external_roles(load_json(paths.users, []))
    summary = {"attached": [], "would": [], "errors": [], "missing": [], "skipped": 0}
    for d in decisions:
        if only and str(d.get("id")) != only:
            continue
        if dedupe_key and d.get("dedupeKey") != dedupe_key:
            continue
        if (d.get("status") or "open") not in OPEN_STATUSES:
            continue
        try:
            pl = plan_decision(d, meta, state, paths.ws, ext)
            if pl.get("skip") == "external-assignee":
                ds = state.setdefault("decisions", {}).setdefault(str(d.get("id")), {})
                if dry or not ds.get("external_logged"):
                    log(f"  {d.get('id')}: skip (assignee/approver is an external doc-gated role; "
                        f"exposing documents to them is Jon's call)")
                    if not dry:
                        ds["external_logged"] = iso()
                summary["skipped"] += 1
                continue
            if pl.get("skip") and pl["skip"] in ("not-open", "pinned", "docKeys-none", "decision-linked"):
                summary["skipped"] += 1
                if only or not quiet_skips:
                    log(f"  {d.get('id')}: skip ({pl['skip']})")
                continue
            if pl.get("missing"):
                summary["missing"].append((d.get("id"), pl["missing"]))
            res = execute(pl, d, state, paths, dry=dry)
            if res == "attached":
                summary["attached"].append((d.get("id"), [x["key"] for x in pl["docs"]]))
                meta = load_json(paths.meta, meta)
            elif res == "dry":
                summary["would"].append((d.get("id"), [os.path.relpath(x["path"], paths.ws) for x in pl["docs"]]))
            else:
                summary["skipped"] += 1
        except Exception as e:
            summary["errors"].append((d.get("id"), str(e)[:200]))
            log(f"  ! {d.get('id')}: {e}")
            trace("decision_docs_error", {"decision": d.get("id"), "error": str(e)[:300]}, outcome="error", level="error")
    if not dry:
        state["last_run"] = iso()
        write_json_atomic(paths.state, state)
    return summary


def ensure_docs(dedupe_key=None, decision_id=None):
    """Library hook for ingest helpers: attach referenced docs to a just-ingested card. Never raises."""
    try:
        if not (dedupe_key or decision_id):
            return None
        return run(only=decision_id, dedupe_key=dedupe_key)
    except Exception as e:
        try:
            log(f"  ! ensure_docs({dedupe_key or decision_id}) failed: {e}")
        except Exception:
            pass
        return None


# ───────────────────────────── selftest (eval) ─────────────────────────────
def selftest():
    global TEST
    TEST = True
    fails = []

    def check(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            fails.append(name)

    tmp = tempfile.mkdtemp(prefix="ddg-selftest-")
    tp = Paths(tmp)
    os.makedirs(os.path.join(tmp, "drafts")); os.makedirs(tp.uploads); os.makedirs(os.path.dirname(tp.decisions))
    os.makedirs(os.path.join(tmp, "logs"))
    memo = os.path.join(tmp, "drafts", "Exos_Strategy_FlightTestLadder_2026-10-10.docx")
    for p, b in ((memo, b"docx"), (memo[:-5] + ".pdf", b"pdf"), (os.path.join(tmp, "drafts", "Bare_Name.xlsx"), b"x"),
                 (os.path.join(tmp, "drafts", "note.md"), b"md")):
        open(p, "wb").write(b)
    write_json_atomic(tp.meta, [{"id": "x", "decision_id": "D-2", "current": True, "uploaded_by": "Exo",
                                 "stored_name": "a", "doc_key": "k"}])
    # 1) failure replay: D-7282043-shaped card, docs in text only, task-linked
    d1 = {"id": "D-1", "status": "open", "relatedItem": "1782", "dedupeKey": "k1",
          "context": "Strategy memo: drafts/Exos_Strategy_FlightTestLadder_2026-10-10.docx (emailed). See also "
                     "Bare_Name.xlsx and drafts/note.md and drafts/Gone_2026-01-01.pdf"}
    meta = load_json(tp.meta, [])
    pl = plan_decision(d1, meta, {}, tmp)
    keys = [x["key"] for x in pl["docs"]]
    check("replay D-7282043: memo docx extracted", any(x["path"] == memo for x in pl["docs"]))
    check("same-stem pdf added as __pdf companion", any(k.endswith("__pdf") for k in keys))
    check("bare filename in drafts/ resolved", any(x["path"].endswith("Bare_Name.xlsx") for x in pl["docs"]))
    check(".md never attached, listed", pl["md"] == ["drafts/note.md"] and not any(x["path"].endswith(".md") for x in pl["docs"]))
    check("missing file reported", pl["missing"] == ["drafts/Gone_2026-01-01.pdf"])
    check("task mode via numeric relatedItem", pl["mode"] == "task" and pl["task"] == "1782")
    # 2) skips
    check("pinned card left as-is", plan_decision(dict(d1, id="D-9", docKeys=["a"]), meta, {}, tmp).get("skip") == "pinned")
    check("docKeys ['none'] respected", plan_decision(dict(d1, docKeys=["none"]), meta, {}, tmp).get("skip") == "docKeys-none")
    check("human decision-linked upload wins", plan_decision(dict(d1, id="D-2"), meta, {}, tmp).get("skip") == "decision-linked")
    check("answered card ignored", plan_decision(dict(d1, status="answered"), meta, {}, tmp).get("skip") == "not-open")
    check("empty docKeys [] treated as unpinned", not plan_decision(dict(d1, docKeys=[]), meta, {}, tmp).get("skip"))
    # 3) decision-linked path + safe _meta write + idempotency
    d3 = {"id": "D-3", "status": "delegated", "relatedItem": "Some opp", "context": f"draft at {memo}"}
    pl3 = plan_decision(d3, meta, {}, tmp)
    check("no task → decision-linked mode", pl3["mode"] == "decision" and not pl3.get("skip"))
    state = {"decisions": {}}
    execute(pl3, d3, state, tp)
    meta = load_json(tp.meta, [])
    mine = [m for m in meta if m.get("decision_id") == "D-3"]
    check("decision-linked uploads written with decision_id", len(mine) == 2 and all(m["uploaded_by"] == GUARD_BY for m in mine))
    check("pre-existing _meta records preserved", any(m.get("id") == "x" for m in meta))
    check("files copied into uploads", all(os.path.isfile(os.path.join(tp.uploads, m["stored_name"])) for m in mine))
    check("re-plan is idempotent (unchanged)", plan_decision(d3, meta, state, tmp).get("skip") == "unchanged")
    open(memo, "wb").write(b"docx v2")
    pl3b = plan_decision(d3, meta, state, tmp)
    check("changed referenced file → refresh", not pl3b.get("skip") and pl3b["reason"] == "guard-owned-linked")
    execute(pl3b, d3, state, tp)
    meta = load_json(tp.meta, [])
    cur = [m for m in meta if m.get("decision_id") == "D-3" and m.get("current") is not False]
    check("refresh supersedes guard's old version", len(cur) == 2 and any(m["version"] == 2 for m in cur))
    # 4) guard-owned pin recognized on later runs
    st = {"decisions": {"D-1": {"docKeys": ["a", "a__pdf"], "sig": []}}}
    check("guard-owned pin re-evaluated", plan_decision(dict(d1, docKeys=["a", "a__pdf"]), [], st, tmp).get("reason") == "guard-owned-pin")
    # 5) external doc-gated assignee (dd_reviewer) is never auto-exposed
    ext = external_roles([{"email": "rev@ainigma.example", "role": "dd_reviewer"}, {"email": "s@utd.example", "role": "early_adopter"}])
    check("dd_reviewer assignee skipped", plan_decision(dict(d1, assignedTo="rev@ainigma.example"), [], {}, tmp, ext).get("skip") == "external-assignee")
    check("early_adopter assignee (no doc access) still served", not plan_decision(dict(d1, assignedTo="s@utd.example"), [], {}, tmp, ext).get("skip"))
    # 6) path containment
    out = collect_docs({"context": "/etc/passwd.pdf and ../../x.docx"}, tmp)
    check("paths outside workspace ignored", not out["docs"])
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'OK' if not fails else 'FAILED'}: {len(fails)} failure(s)")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="run", choices=["run"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--id")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    s = run(dry=a.dry_run, only=a.id, quiet_skips=not a.id)
    log(f"{'DRY-RUN ' if a.dry_run else ''}done: attached={len(s['attached'])} would={len(s['would'])} "
        f"missing={len(s['missing'])} errors={len(s['errors'])} skipped={s['skipped']}")
    sys.exit(1 if s["errors"] else 0)


if __name__ == "__main__":
    main()
