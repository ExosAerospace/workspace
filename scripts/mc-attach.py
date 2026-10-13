#!/usr/bin/env python3
"""
mc-attach.py — attach a document to a Mission Control task, with versioning.

Standing behavior for Exo: whenever a document is created or revised for a task,
call this so the task always carries the LATEST version, and prior versions are
archived (never lost). The board/API surfaces the current version; history stays
available.

  Attach (or revise) a doc on a task:
    mc-attach.py --task <task_id> --file <path> [--doc-key <key>] [--by "Exo"] [--title "..."]

Revision logic: a document's identity on a task is its --doc-key (defaults to a
slug of the filename). Attaching a new file with the same (task_id, doc_key) marks
the previous current version archived and bumps the version number; the new file
becomes current.
"""
import argparse, json, os, re, shutil, sys, time, hashlib

MC = "/Users/exomac/.openclaw/workspace/mission-control"
UPLOADS = os.path.join(MC, "uploads")
META = os.path.join(UPLOADS, "_meta.json")


def slug(s):
    """Canonical document key: strip trailing version/date/draft tokens in ANY
    order so every revision of a doc maps to the SAME key (and thus chains as
    versions). A version number must be separator-led (e.g. _v0.1, -3), so
    embedded names like BLK3/RDRE are never mangled."""
    s = os.path.splitext(os.path.basename(s))[0].lower()
    prev = None
    while prev != s:                                     # peel trailing tokens, any order
        prev = s
        s = re.sub(r'[\s_.\-]+v?\d+(\.\d+)*$', '', s)    # trailing version: _v0.1, -v2, _3 (BLK3-safe)
        s = re.sub(r'[\s_.\-]*\(?\d{4}-\d{2}-\d{2}\)?$', '', s)  # trailing ISO date (opt parens)
        s = re.sub(r'[\s_.\-]+draft$', '', s)            # trailing 'draft'
        s = re.sub(r'[\s_.\-]*\(\d+\)$', '', s)          # browser duplicate: "name (1)"
        s = re.sub(r'[\s_.\-]+copy$', '', s)             # trailing 'copy'
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s or "document"


_TOK = re.compile(r'(^|[\s_.\-])((r|rev|v)\s?\d+(\.\d+)*|rev|final|draft|updated|latest|copy|clean)(?=$|[\s_.\-])')

def family(name):
    """Document family = filename stem with dates / r# / rev# / v# / FINAL / DRAFT / '(1)' stripped, plus the
    extension. SAME rule as mission-control/lib/doc-families.js. Every iteration of a document on a task maps to
    one family, whatever doc_key or name Exo used (Jon 10/13: 'Exo names all the files ... fix it')."""
    b = re.sub(r'^\d{10,}_', '', os.path.basename(name or ""))
    stem, ext = os.path.splitext(b)
    s = stem.lower()
    s = re.sub(r'---[0-9a-f-]{20,}$', '', s)
    s = re.sub(r'\(?\d{4}-\d{2}-\d{2}\)?', ' ', s)
    s = re.sub(r'\(\d+\)', ' ', s)
    prev = None
    while prev != s:
        prev = s
        s = _TOK.sub(' ', s)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return (s or 'document') + ext.lower()

def doc_date(name):
    """Last ISO date embedded in a filename (e.g. _2026-10-05), or None."""
    d = re.findall(r'(\d{4}-\d{2}-\d{2})', os.path.basename(name or ""))
    return d[-1] if d else None


def load_meta():
    try:
        with open(META) as f:
            return json.load(f)
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--doc-key", default=None)
    ap.add_argument("--by", default="Exo")
    ap.add_argument("--title", default=None)
    ap.add_argument("--allow-older", action="store_true",
                    help="permit an OLDER-dated file to become current (deliberate rollback only)")
    a = ap.parse_args()

    if not os.path.isfile(a.file):
        print(f"ERROR: file not found: {a.file}"); sys.exit(1)
    os.makedirs(UPLOADS, exist_ok=True)

    fname = os.path.basename(a.file)
    ext = os.path.splitext(fname)[1].lower()
    doc_key = a.doc_key or slug(fname)
    # Standing rule: task attachments are Word, never raw .md/.txt — convert before storing.
    src = a.file
    if ext in (".md", ".txt"):
        try:
            import tempfile, importlib.util
            _sp = importlib.util.spec_from_file_location("md_to_docx",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "md_to_docx.py"))
            _mdx = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_mdx)
            src = _mdx.convert(a.file, os.path.join(tempfile.mkdtemp(), os.path.splitext(fname)[0] + ".docx"))
            fname = os.path.basename(src); ext = ".docx"
            # non-silent: announce the conversion so a spreadsheet-intended .md is never quietly turned to Word
            print(f"NOTE: converted {os.path.basename(a.file)} (.md/.txt) -> .docx before attaching. "
                  f"If this was meant to be a spreadsheet, attach a real .xlsx instead.")
        except Exception as e:
            print("md->docx failed, storing original:", str(e)[:70]); src = a.file
    title = a.title or ""
    if title.lower().endswith((".md", ".txt")):
        title = os.path.splitext(title)[0] + ".docx"
    meta = load_meta()
    on_task = [m for m in meta if str(m.get("task_id")) == str(a.task)]
    # 1) identical content already current anywhere on the task -> no new copy (stops 26x re-uploads)
    src_hash0 = hashlib.sha256(open(src, "rb").read()).hexdigest()
    for m in on_task:
        if m.get("current") is False:
            continue
        try:
            if hashlib.sha256(open(os.path.join(UPLOADS, m["stored_name"]), "rb").read()).hexdigest() == src_hash0:
                print(f"unchanged: identical file is already current on task {a.task} as '{m.get('filename')}' (doc_key {m.get('doc_key')})")
                return
        except Exception:
            pass
    # 2) same document family already on the task -> chain to ITS doc_key, never invent a new key/name
    fam = family(fname)
    fam_hits = [m for m in on_task if m.get("current") is not False and m.get("doc_key")
                and family(m.get("stored_name") or m.get("filename")) == fam]
    if fam_hits:
        keep = max(fam_hits, key=lambda m: m.get("uploaded_at") or "")["doc_key"]
        if keep != doc_key:
            print(f"NOTE: '{fname}' is an iteration of an existing document on task {a.task}; "
                  f"chaining to doc_key '{keep}' (ignored '{doc_key}').")
            doc_key = keep
    # Stale-version guard (Jon 10/7 "how do we not send an outdated one?"): an older copy must
    # never supersede a newer one. On #2488 a re-attach of the 09-22 HyCAT file demoted the 10-05
    # revision, so the board's "current" — the copy that gets sent — was the outdated one.
    same = [m for m in meta if str(m.get("task_id")) == str(a.task) and m.get("doc_key") == doc_key]
    src_hash = hashlib.sha256(open(src, "rb").read()).hexdigest()
    for m in same:
        if m.get("current") is False:
            continue
        try:
            if hashlib.sha256(open(os.path.join(UPLOADS, m["stored_name"]), "rb").read()).hexdigest() == src_hash:
                print(f"unchanged: '{fname}' is already the current v{m.get('version', 1)} on task {a.task}")
                return
        except Exception:
            pass
    new_d = doc_date(fname)
    newer = [m for m in same if new_d and doc_date(m.get("stored_name")) and doc_date(m.get("stored_name")) > new_d]
    if newer and not a.allow_older:
        n = max(newer, key=lambda m: doc_date(m.get("stored_name")))
        print(f"REFUSED (stale): '{fname}' ({new_d}) is older than '{n.get('filename')}' "
              f"({doc_date(n.get('stored_name'))}) already on task {a.task}. Not superseding the newer "
              f"version. Use --allow-older only for a deliberate rollback.")
        sys.exit(3)

    ts = int(time.time() * 1000)
    stored = f"{ts}_{re.sub(r'[^A-Za-z0-9._-]', '_', fname)}"
    shutil.copy2(src, os.path.join(UPLOADS, stored))
    size = os.path.getsize(src)
    # supersede the current version of this doc on this task
    prev_ver = 0
    for m in meta:
        if str(m.get("task_id")) == str(a.task) and m.get("current") is not False and (
                m.get("doc_key") == doc_key or family(m.get("stored_name") or m.get("filename")) == fam):
            m["current"] = False
            m["superseded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            prev_ver = max(prev_ver, int(m.get("version", 1)))
    version = prev_ver + 1

    rec = {
        "id": hashlib.sha1(f"{stored}{ts}".encode()).hexdigest()[:16],
        "filename": fname,
        **({"title": title} if title and title != fname else {}),
        "stored_name": stored,
        "size": size,
        "extension": ext,
        "task_id": str(a.task),
        "project_id": None,
        "decision_id": None,
        "doc_key": doc_key,
        "version": version,
        "current": True,
        "uploaded_by": a.by,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    meta.append(rec)
    tmp = META + f".tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(meta, f, indent=2)
    os.replace(tmp, META)  # atomic: never leave a truncated _meta.json

    action = "attached (v1)" if version == 1 else f"revised (v{version}, prior archived)"
    print(f"{action}: '{rec['filename']}' -> task {a.task}")
    print(f"  url: /uploads/{stored}")
    print(f"  doc_key: {doc_key}")


if __name__ == "__main__":
    main()
