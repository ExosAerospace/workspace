#!/usr/bin/env python3
"""
mc-doc-reconcile.py — attach prepared documents to the Mission Control tasks they belong to.

The problem it fixes: tasks whose title implies a deliverable ("READY TO SEND ...",
"DRAFT — ...", "RFI Response ...") were created (often from email capture) without the
actual document linked, so reviewers on the board have nothing to open. The auto-attach
rule (scripts/mc-attach.py at doc-creation time) only covers docs the agent makes going
forward; this reconciler sweeps the whole board and links workspace files to any task
that is missing its deliverable.

Keyed to the LIVE Supabase board (integer task ids) — NOT the stale legacy tasks.json.
Conservative matcher: high-overlap matches auto-attach; medium matches must also share a
distinctive term; everything weaker is skipped (its doc likely lives only in an email body
and was never saved as a file). Idempotent: only touches tasks with no attachment yet.

Run: python3 scripts/mc-doc-reconcile.py [--dry-run]
Scheduled daily via launchd com.exos.mc-doc-reconcile.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, os, re, subprocess, sys, time, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
META = os.path.join(WS, "mission-control", "uploads", "_meta.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
LOG = os.path.join(WS, "logs", "mc-doc-reconcile.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
DRY = "--dry-run" in sys.argv

MARKERS = re.compile(r'READY TO SEND|SUBMIT-READY|DRAFT|whitepaper|white paper|letter|'
                     r'proposal|memo|one[\s-]?page|dossier|agenda|deck|package|FORWARD|'
                     r'RFI|response|capability statement|\bNDA\b|\bMNDA\b|template|'
                     r'policy|policies|procedure|agreement|\bSOP\b|checklist|brief|'
                     r'statement|plan|report|summary|guide|playbook', re.I)
STOP = set("the a an of to for re fw and or in on at with from draft final v1 v2 v3 v4 v5 v6 "
           "ready send submit review response letter memo package full version latest exos "
           "aerospace update".split())
GENERIC = set("response draft review send forward one page state legislature congressional "
              "federal support outreach follow followup email meeting call".split())


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def supa_tasks():
    k = json.load(open(SECRETS))["supabase_service_role_key"]
    req = urllib.request.Request(SUPA + "tasks?select=id,title,state,source&limit=5000",
                                 headers={"apikey": k, "Authorization": "Bearer " + k})
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            if i == 3:
                raise
            time.sleep(2)


def tok(s):
    s = re.sub(r'\.[a-z0-9]+$', '', s.lower())
    s = re.sub(r'^(fw|re)\s*:\s*', '', s)
    s = re.sub(r'\[[^\]]*\]', '', s)
    return set(w for w in re.split(r'[^a-z0-9]+', s) if len(w) > 2 and w not in STOP)


def workspace_files():
    files = []
    for root, _, fs in os.walk(WS):
        if any(s in root for s in ("/.git", "/node_modules", "/mission-control", "/logs",
                                    "/memory", "/.openclaw")):
            continue
        for f in fs:
            if not f.lower().endswith((".md", ".docx", ".pdf", ".html", ".xlsx", ".pptx")):
                continue
            if f.startswith("2017-contacts"):
                continue
            files.append(os.path.join(root, f))
    return [(f, tok(os.path.basename(f))) for f in files]


def main():
    tasks = supa_tasks()
    visible = [t for t in tasks if t.get("source") != "mc-board-legacy"]
    meta = json.load(open(META)) if os.path.exists(META) else []
    attached = set(str(r.get("task_id")) for r in meta)
    filetok = workspace_files()
    missing = [t for t in visible if str(t.get("id")) not in attached
               and MARKERS.search(t.get("title") or "")]

    hi = med = skip = 0
    for t in missing:
        tt = tok(t.get("title") or "")
        if len(tt) < 2:
            continue
        best = None; bs = 0; bf = None
        for f, ft in filetok:
            if not ft:
                continue
            rec = len(tt & ft) / len(tt)
            if rec > bs:
                bs = rec; best = f; bf = ft
        conf = None
        if bs >= 0.6:
            conf = "high"
        elif bs >= 0.4:
            shared = tt & bf
            prec = len(shared) / len(bf) if bf else 0
            distinctive = [w for w in shared if len(w) >= 5 and w not in GENERIC]
            if distinctive and prec >= 0.3:
                conf = "med"
        if not conf:
            skip += 1
            continue
        if DRY:
            log(f"[dry] would attach #{t['id']} ({conf}) <- {os.path.basename(best)}")
        else:
            r = subprocess.run(["python3", os.path.join(WS, "scripts", "mc-attach.py"),
                                "--task", str(t["id"]), "--file", best,
                                "--by", "Exo (auto-reconcile)", "--title", os.path.basename(best)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                log(f"FAIL #{t['id']}: {(r.stderr or r.stdout)[:100]}")
                continue
            log(f"attached #{t['id']} ({conf}) <- {os.path.basename(best)}")
        hi += conf == "high"; med += conf == "med"
    log(f"reconcile done | attached high:{hi} med:{med} | skipped(no file):{skip} "
        f"| candidates:{len(missing)}{' [DRY-RUN]' if DRY else ''}")


if __name__ == "__main__":
    main()
