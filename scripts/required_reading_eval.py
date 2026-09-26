#!/usr/bin/env python3
"""
required_reading_eval.py — exo3 process eval for MC Required Reading.

Owner: Exo (MC platform). Checks every doc in mission-control/data/required-reading.json
the same way the server's /api/required-reading/content route will render it — under the
launchd PATH (no /opt/homebrew/bin), because that PATH gap is what broke all 24 PDFs (9/26).

Checks per doc:
  RENDER  — file exists, converter runs under launchd PATH, output has real text (>= MIN_WORDS)
  PATH    — how the item gets completed: tracked reader / page reader / GCC High (CUI) / certificate
  NEXT    — for a brand-new user with nothing complete, the "Next required reading →" button
            from this doc lands on a doc that has a tracked reader (never a CUI 403 or mailto)

Usage: python3 scripts/required_reading_eval.py [--json]
Exit 0 = all PASS; 1 = at least one FAIL. Report: logs/required-reading-eval.json
"""
import json, os, re, subprocess, sys, tempfile, datetime
from pathlib import Path

WS = Path("/Users/exomac/.openclaw/workspace")
RR = WS / "mission-control" / "data" / "required-reading.json"
LIB = WS / "process-library"
DOCX2HTML = WS / "scripts" / "docx2html.py"
REPORT = WS / "logs" / "required-reading-eval.json"
LAUNCHD_ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(Path.home())}
MIN_WORDS = 60
PAGE_READERS = ("/help.html", "/ai-tool-use-policy.html")  # pages with their own tracked RR bar
TRACKABLE = re.compile(r"^/(read\.html\?|help\.html|ai-tool-use-policy\.html)")


def pdftotext_bin():
    # Mirrors server.js resolution.
    for p in ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext"):
        if os.path.exists(p):
            return p
    return "pdftotext"


def words(html):
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"base64,[^\"']*", "", html)
    return len(re.sub(r"<[^>]+>", " ", html).split())


def render(doc):
    src = doc.get("file") or doc.get("url") or ""
    rel = src[len("/process-library/"):]
    if "08-security-cui" in rel:
        return "SKIP", "CUI — GCC High only (by design)"
    full = LIB / rel
    if not full.is_file():
        return "FAIL", f"file missing: {rel}"
    ext = full.suffix.lower()
    try:
        if ext == ".pdf":
            r = subprocess.run([pdftotext_bin(), "-layout", "-q", str(full), "-"], env=LAUNCHD_ENV,
                               capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return "FAIL", f"pdftotext exit {r.returncode}"
            n = len(r.stdout.split())
        elif ext in (".docx", ".doc"):
            out = Path(tempfile.mkstemp(suffix=".html")[1])
            cmd = (["/usr/bin/python3", str(DOCX2HTML), str(full), str(out)] if ext == ".docx"
                   else ["textutil", "-convert", "html", "-output", str(out), str(full)])
            r = subprocess.run(cmd, env=LAUNCHD_ENV, capture_output=True, text=True, timeout=90)
            if r.returncode != 0:
                return "FAIL", f"{cmd[0]} exit {r.returncode}: {r.stderr[:120]}"
            n = words(out.read_text(errors="ignore")); out.unlink(missing_ok=True)
        elif ext in (".png", ".jpg", ".jpeg", ".gif"):
            return "PASS", "image (rendered as <img>)"
        else:
            return "FAIL", f"no inline renderer for {ext}"
    except FileNotFoundError as e:
        return "FAIL", f"converter not found under launchd PATH: {e.filename}"
    except subprocess.TimeoutExpired:
        return "FAIL", "render timeout"
    if n < MIN_WORDS:
        return "FAIL", f"only {n} words rendered (scan/image-only or broken)"
    return "PASS", f"{n} words"


def completion_path(doc):
    url = doc.get("url", "")
    if doc.get("fulfillment") == "attestation":
        return "attestation (CUI read in GCC High)"
    if url.startswith("/read.html?"):
        return "tracked reader"
    if url.startswith(PAGE_READERS):
        return "page reader"
    if url.startswith("mailto:") or doc.get("fulfillment") == "certificate":
        return "certificate (email)"
    if "08-security-cui" in url:
        return "GCC High (no MC completion path)"
    return "UNKNOWN"


def next_target(docs, cur_id):
    # Mirrors read.html/help.html/ai-tool-use-policy.html setupNext() for a user with nothing done.
    cur = next((i for i, d in enumerate(docs) if d["id"] == cur_id), -1)
    n = len(docs)
    for k in range(1, n + 1):
        c = docs[(cur + k) % n]
        if c["id"] != cur_id and TRACKABLE.match(c.get("url", "")):
            return c
    return None


def main():
    docs = json.load(open(RR))["docs"]
    rows, fails = [], 0
    for d in docs:
        path = completion_path(d)
        if path in ("tracked reader",):
            rs, rd = render(d)
        elif path.startswith("attestation"):
            leak = bool(d.get("file")) or "08-security-cui" in d.get("url", "")
            rs, rd = ("FAIL", "CUI path exposed to MC") if leak else ("PASS", "no CUI content in MC")
        elif path == "page reader":
            rs, rd = ("PASS" if (WS / "mission-control" / d["url"].lstrip("/").split("?")[0]).exists() else "FAIL"), "static page"
        else:
            rs, rd = "SKIP", path
        nx = next_target(docs, d["id"]) if TRACKABLE.match(d.get("url", "")) else None
        ns = "N/A" if not TRACKABLE.match(d.get("url", "")) else ("PASS" if nx else "FAIL")
        status = "FAIL" if "FAIL" in (rs, ns) or path == "UNKNOWN" else "PASS"
        fails += status == "FAIL"
        rows.append({"id": d["id"], "title": d["title"], "audience": d.get("audience"), "completion_path": path,
                     "render": rs, "render_detail": rd, "next": ns, "next_to": nx["id"] if nx else None, "status": status})
    report = {"ran_at": datetime.datetime.now().isoformat(timespec="seconds"), "total": len(rows),
              "fail": fails, "no_mc_completion_path": [r["id"] for r in rows if r["completion_path"].startswith("GCC High")],
              "rows": rows}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        for r in rows:
            print(f"{r['status']:4} {r['id']:26} {r['completion_path']:32} render={r['render']:4} ({r['render_detail']}) next={r['next']}")
        print(f"\n{len(rows)} docs · {fails} FAIL · no MC completion path: {', '.join(report['no_mc_completion_path']) or 'none'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
