#!/usr/bin/env python3
"""
TASK ATTACHMENT RECONCILER — makes "Attached: <file>" in a task body mean a real 📎 on the card.

Many tasks are created from emails/deliverables whose description says a file is attached, but the
file was never registered to the task in Mission Control's uploads system (so no paperclip shows).
This scans open tasks that reference an attachment, resolves the named file on disk, and attaches it
via mc-attach.py. SAFE: it only attaches when the body names an explicit filename (.pptx/.docx/.pdf/
.xlsx/…) that resolves to exactly ONE file in the workspace — it never guesses from prose. Anything
it can't resolve confidently is logged, not attached. Idempotent (skips tasks already linked).

Run:  python3 scripts/task-attachment-reconciler.py           # dry-run (show what it would attach)
      python3 scripts/task-attachment-reconciler.py --apply
      python3 scripts/task-attachment-reconciler.py --selftest  # replay network-failure handling
"""
import os, re, sys, json, time, socket, subprocess, urllib.request, urllib.error

WS = os.path.expanduser("~/.openclaw/workspace")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
K = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
META = os.path.join(WS, "mission-control", "uploads", "_meta.json")
MC_ATTACH = os.path.join(WS, "scripts", "mc-attach.py")
LOG = os.path.join(WS, "logs", "task-attach-reconciler.jsonl")
APPLY = "--apply" in sys.argv
EXTS = r"pptx|docx|pdf|xlsx|xls|csv|pptx|key|png|jpg|jpeg"
FNAME_RE = re.compile(r"([A-Za-z0-9][\w\-.()& ]{2,120}\.(?:%s))" % EXTS, re.I)
SKIP_DIRS = {".git", "node_modules", ".chunks", "uploads", "media", "process-library",
             "__pycache__", ".openclaw-cli-images", "submissions-archive"}
ATTACHABLE = re.compile(r"attach(ed|ment)\b", re.I)


NET_ERRORS = (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError)
RETRY_DELAYS = (5, 15, 45)


def fetch_json(req, opener=urllib.request.urlopen, sleep=time.sleep):
    """GET with retry/backoff on transient network errors (DNS blips, connect timeouts)."""
    for i, delay in enumerate(RETRY_DELAYS + (None,)):
        try:
            return json.load(opener(req, timeout=30))
        except urllib.error.HTTPError:
            raise  # a real HTTP error (auth/schema) is not transient
        except NET_ERRORS:
            if delay is None:
                raise
            sleep(delay)


def sb_tasks():
    out, off = [], 0
    while True:
        r = urllib.request.Request(f"{SB}tasks?select=id,title,description,state&order=id&limit=1000&offset={off}",
                                   headers={"apikey": K, "Authorization": "Bearer " + K})
        pg = fetch_json(r)
        out += pg
        if len(pg) < 1000:
            return out
        off += 1000


def linked_task_ids():
    try:
        m = json.load(open(META))
    except Exception:
        return set()
    items = m.values() if isinstance(m, dict) else m
    return set(str(e.get("task_id")) for e in items if isinstance(e, dict) and e.get("task_id"))


def build_file_index():
    """basename(lower) -> [absolute paths], across the workspace minus heavy/staging dirs."""
    idx = {}
    for root, dirs, files in os.walk(WS):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if "." in f and f.rsplit(".", 1)[1].lower() in EXTS.split("|"):
                idx.setdefault(f.lower(), []).append(os.path.join(root, f))
    return idx


def resolve(fname, idx):
    """Return the single matching path, or None if zero/ambiguous."""
    paths = idx.get(fname.lower())
    if not paths:
        # try a looser match: same stem, ignoring surrounding spaces
        return None
    uniq = sorted(set(paths))
    if len(uniq) == 1:
        return uniq[0]
    # ambiguous basename in multiple locations -> pick only if they're the same size (true dup)
    sizes = {os.path.getsize(p) for p in uniq}
    if len(sizes) == 1:
        return max(uniq, key=os.path.getmtime)  # identical dupes -> newest
    return None  # genuinely ambiguous -> skip, do not guess


def selftest():
    calls = []
    def flaky(req, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise urllib.error.URLError(socket.timeout("timed out"))
        import io
        return io.BytesIO(b"[]")
    assert fetch_json("x", opener=flaky, sleep=lambda s: None) == [] and len(calls) == 3
    def dead(req, timeout):
        raise urllib.error.URLError("nodename nor servname provided")
    try:
        fetch_json("x", opener=dead, sleep=lambda s: None)
        raise AssertionError("expected URLError after retries")
    except urllib.error.URLError:
        pass
    def http401(req, timeout):
        raise urllib.error.HTTPError("x", 401, "Unauthorized", {}, None)
    try:
        fetch_json("x", opener=http401, sleep=lambda s: None)
        raise AssertionError("expected HTTPError to propagate")
    except urllib.error.HTTPError:
        pass
    print("selftest OK")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    try:
        tasks = sb_tasks()
    except urllib.error.HTTPError:
        raise
    except NET_ERRORS as e:
        # Supabase unreachable after retries: nothing was changed and the job is idempotent,
        # so skip this cycle cleanly; the next StartInterval run (30 min) picks it up.
        print(f"SKIP: Supabase unreachable after {len(RETRY_DELAYS)} retries ({e}); will retry next run")
        return
    linked = linked_task_ids()
    idx = build_file_index()
    attached, unresolved = [], []
    for t in tasks:
        tid = str(t["id"])
        desc = t.get("description") or ""
        if (t.get("state") or "").lower() in ("done", "cancelled", "canceled"):
            continue
        if not ATTACHABLE.search(desc) or tid in linked:
            continue
        names = list(dict.fromkeys(FNAME_RE.findall(desc)))  # explicit filenames only
        if not names:
            unresolved.append((tid, (t.get("title") or "")[:55], "prose-only (no filename in body)"))
            continue
        hit = next(((n, resolve(n, idx)) for n in names if resolve(n, idx)), None)
        if not hit:
            unresolved.append((tid, (t.get("title") or "")[:55], f"named {names[0]} but not found on disk"))
            continue
        fname, path = hit
        print(f"  #{tid}  ←  {os.path.basename(path)}")
        attached.append((tid, path, (t.get("title") or "")[:55]))
        if APPLY:
            try:
                subprocess.run(["python3", MC_ATTACH, "--task", tid, "--file", path, "--by", "Exo (reconciler)"],
                               cwd=WS, timeout=60, capture_output=True, check=True)
                os.makedirs(os.path.dirname(LOG), exist_ok=True)
                open(LOG, "a").write(json.dumps({"task": tid, "file": os.path.basename(path)}) + "\n")
            except Exception as e:
                print(f"    attach failed: {e}")

    print(f"\n{'ATTACHED' if APPLY else 'WOULD ATTACH'}: {len(attached)}  |  unresolved (logged, not touched): {len(unresolved)}")
    if unresolved and not APPLY:
        print("Unresolved (need manual attach or prose-only):")
        for tid, title, why in unresolved[:20]:
            print(f"   #{tid} {title} — {why}")
        if len(unresolved) > 20:
            print(f"   …+{len(unresolved)-20} more")


if __name__ == "__main__":
    main()
