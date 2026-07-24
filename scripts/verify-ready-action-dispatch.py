#!/usr/bin/env python3
"""
verify-ready-action-dispatch.py — spot-check that the READY-ACTION pipeline is working.

For each real READY-ACTION block found in the agent trackers, report whether it was
dispatched (emailed to Jon + MC task opened) per the dispatch state, and confirm the MC
task is live on the board. Prints a concise summary to relay to Jon.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import os, re, sys, json, glob, ssl, hashlib, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.join(WS, "logs", "ready-actions-dispatched.json")
TRACKER_DIRS = [os.path.join(WS, d) for d in ("capture", "captures", "tasks")]
BLOCK_RE = re.compile(r"<!--\s*READY-ACTION\s*(.*?)\s*END-READY-ACTION\s*-->", re.DOTALL)
SB_URL = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"


def parse_block(text):
    d, body, in_body = {}, [], False
    for line in text.splitlines():
        if in_body:
            body.append(line); continue
        m = re.match(r"^\s*(\w+)\s*:\s*(.*)$", line)
        if m and m.group(1).lower() in ("key", "task_title", "to", "cc", "subject", "category", "priority", "body"):
            k = m.group(1).lower()
            if k == "body":
                in_body = True
                if m.group(2).strip(): body.append(m.group(2))
            else:
                d[k] = m.group(2).strip()
    d["body"] = "\n".join(body).strip()
    return d


def real_blocks():
    out = []
    for d in TRACKER_DIRS:
        for path in glob.glob(os.path.join(d, "*.md")):
            try:
                txt = open(path, encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for raw in BLOCK_RE.findall(txt):
                b = parse_block(raw)
                if not b.get("key") or not b.get("subject") or not b.get("body"):
                    continue
                if "<" in b["key"] or "<" in b["subject"] or b["key"] in ("selftest-key", "example"):
                    continue
                b["_file"] = os.path.basename(path)
                out.append(b)
    return out


def task_live(task_id):
    if not task_id:
        return False
    try:
        key = json.load(open(SECRETS))["supabase_service_role_key"]
        req = urllib.request.Request(
            f"{SB_URL}tasks?id=eq.{task_id}&select=id,title,state",
            headers={"apikey": key, "Authorization": "Bearer " + key})
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
            arr = json.loads(r.read().decode())
            return bool(arr)
    except Exception:
        return None  # unknown


def build_report():
    """Return (report_text, noteworthy). noteworthy = there is real signal worth emailing."""
    try:
        state = json.load(open(STATE))
    except Exception:
        state = {}
    blocks = real_blocks()
    L = ["=== READY-ACTION dispatch verification ===",
         f"Real READY-ACTION blocks in trackers: {len(blocks)}",
         f"Dispatched keys on record: {len(state)}"]
    if not blocks and not state:
        L.append("\nNo agent has emitted a real READY-ACTION block yet. Pipeline idle (expected until the next agent run).")
        return "\n".join(L), False

    noteworthy = False  # stay silent on success (the delivery email already confirmed it); alert only on gaps below
    if blocks:
        L.append("\n--- Blocks found in trackers ---")
        for b in blocks:
            st = state.get(b["key"], {})
            tid = st.get("task_id")
            live = task_live(tid) if tid else False
            status = "DISPATCHED" if st else "PENDING (not yet dispatched)"
            if not st or (tid and live is False):
                noteworthy = True
            live_s = "task live" if live else ("task MISSING" if live is False else "task unknown")
            L.append(f"  [{status}] {b['key']}  ({b['_file']})  ->  task {tid} {('('+live_s+')') if tid else ''}")
            L.append(f"      subject: {b['subject'][:80]}")

    orphans = [k for k in state if k not in {b['key'] for b in blocks}]
    if orphans:
        L.append("\n--- Dispatched earlier (block since removed/edited) ---")
        for k in orphans:
            L.append(f"  {k} -> task {state[k].get('task_id')} (emailed {state[k].get('emailed_at')})")
    return "\n".join(L), noteworthy


def main():
    report, noteworthy = build_report()
    print(report)
    if "--email" in sys.argv and noteworthy:
        # Only email when the report actually changes, so this stays quiet once things are steady.
        stampf = os.path.join(WS, "logs", "verify-last-email.json")
        h = hashlib.sha256(report.encode()).hexdigest()[:16]
        try: last = json.load(open(stampf)).get("hash")
        except Exception: last = None
        if h != last:
            try:
                import ready_action
                ready_action.email_ready("[Pipeline health] READY-ACTION dispatch check", report)
                json.dump({"hash": h}, open(stampf, "w"))
                print("\n[emailed pipeline-health summary to Jon]")
            except Exception as e:
                print(f"\n[email failed: {e}]")


if __name__ == "__main__":
    main()
