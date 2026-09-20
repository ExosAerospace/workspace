#!/usr/bin/env python3
"""Nightly watch: detect attachments in mission-control/uploads/_meta.json whose task_id no longer
matches any live task (orphaned = "dropped" from the user's view). REPORT-ONLY — it never repairs
(repair/reconciliation is a separate, human-reviewed pass). DMs Jon only when NEW orphans appear so
this can't silently accumulate again. Root cause + fixes diagnosed 2026-09-20.

Run: python3 orphaned_attachment_watch.py [--now]   (--now prints locally and always reports)
"""
import os, sys, json, shutil, subprocess, datetime, urllib.request

WS = os.path.expanduser("~/.openclaw/workspace")
META = os.path.join(WS, "mission-control", "uploads", "_meta.json")
STATE = os.path.join(WS, "logs", "orphaned-attachment-watch-state.json")
LOG = os.path.join(WS, "logs", "orphaned-attachment-watch.log")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
JON = "1501632195163590739"


def logline(m):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f: f.write(f"[{ts}] {m}\n")
    except Exception: pass


def live_task_ids():
    key = json.load(open(SECRETS))["supabase_service_role_key"]
    ids, off = set(), 0
    while True:
        url = f"{SB}/tasks?select=id&limit=1000&offset={off}"
        req = urllib.request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=45) as r:
            batch = json.load(r)
        if not batch: break
        ids.update(str(x["id"]) for x in batch); off += 1000
        if len(batch) < 1000: break
    return ids


def find_orphans():
    meta = json.load(open(META))
    live = live_task_ids()
    orphans = [m for m in meta
               if m.get("task_id") and str(m.get("task_id")) not in live
               and m.get("current", True)]
    return orphans, len(meta)


def post_discord(text):
    ocw = shutil.which("openclaw")
    for cand in ([ocw] if ocw else []) + [
        "/Users/exomac/.local/share/mise/installs/node/lts/bin/openclaw",
        "/Users/exomac/.local/share/mise/installs/node/lts-krypton/bin/openclaw"]:
        if cand and os.path.exists(cand):
            try:
                env = dict(os.environ)
                env["PATH"] = os.path.dirname(cand) + ":/opt/homebrew/bin:/usr/local/bin:" + env.get("PATH", "")
                r = subprocess.run([cand, "message", "send", "--channel", "discord", "--target", JON, "-m", text],
                                   capture_output=True, text=True, timeout=60, env=env)
                if r.returncode == 0:
                    return True
            except Exception as e:
                logline(f"discord send failed via {cand}: {e}")
    return False


def main():
    now = "--now" in sys.argv
    try:
        orphans, total = find_orphans()
    except Exception as e:
        logline(f"scan error: {e}")
        if now: print("scan error:", e)
        return
    ids = sorted({str(m["task_id"]) for m in orphans})
    try:
        prev = json.load(open(STATE)).get("orphan_task_ids", [])
    except Exception:
        prev = []
    new_ids = [i for i in ids if i not in prev]
    json.dump({"generated": datetime.datetime.now().isoformat(timespec="seconds"),
               "orphan_count": len(orphans), "orphan_task_ids": ids, "total_attachments": total},
              open(STATE, "w"), indent=2)
    logline(f"{len(orphans)} orphaned attachment(s) across {len(ids)} task_ids; {len(new_ids)} new")
    if now or new_ids:
        sample = "\n".join(f"• task {m['task_id']} — {m.get('filename','?')[:48]}" for m in orphans[:10])
        msg = (f"📎 **Orphaned attachments watch** — {len(orphans)} doc(s) point at {len(ids)} missing/retired task_id(s)"
               + (f"; **{len(new_ids)} NEW**" if new_ids else "") + ".\n" + sample
               + ("\n…" if len(orphans) > 10 else "")
               + "\nRepair is a separate reviewed pass (map old→current task, then repoint).")
        if now:
            print(msg)
        if new_ids:
            post_discord(msg)


if __name__ == "__main__":
    main()
