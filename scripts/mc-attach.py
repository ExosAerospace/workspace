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
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s or "document"


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
    title = a.title or fname
    if title.lower().endswith((".md", ".txt")):
        title = os.path.splitext(title)[0] + ".docx"
    ts = int(time.time() * 1000)
    stored = f"{ts}_{re.sub(r'[^A-Za-z0-9._-]', '_', fname)}"
    shutil.copy2(src, os.path.join(UPLOADS, stored))
    size = os.path.getsize(src)

    meta = load_meta()
    # supersede the current version of this doc on this task
    prev_ver = 0
    for m in meta:
        if str(m.get("task_id")) == str(a.task) and m.get("doc_key") == doc_key and m.get("current") is not False:
            m["current"] = False
            m["superseded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            prev_ver = max(prev_ver, int(m.get("version", 1)))
    version = prev_ver + 1

    rec = {
        "id": hashlib.sha1(f"{stored}{ts}".encode()).hexdigest()[:16],
        "filename": title,
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
    with open(META, "w") as f:
        json.dump(meta, f, indent=2)

    action = "attached (v1)" if version == 1 else f"revised (v{version}, prior archived)"
    print(f"{action}: '{rec['filename']}' -> task {a.task}")
    print(f"  url: /uploads/{stored}")
    print(f"  doc_key: {doc_key}")


if __name__ == "__main__":
    main()
