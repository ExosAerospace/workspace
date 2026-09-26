#!/usr/bin/env python3
"""
forwarded_mail_watch.py — near-real-time watcher over Jon's forwarded M365 inbound.

Runs every few minutes (launchd com.exos.forwarded-mail-watch). Uses forwarded_mail.scan()
to find mail Jon forwards from Outlook to Proton, dedups against state, keeps a rolling feed
the capture agents read (so they always have the latest), and posts ONE concise Discord line
to #series-a for each NEW high-signal forward (gov approvals, PI/counterparty replies). First
run baselines silently. Quiet 23:00-08:00 CT for alerts (feed still updates).
"""
import json, os, re, sys, subprocess, shutil, urllib.request, difflib
from datetime import datetime
sys.path.insert(0, os.path.join("/Users/exomac/.openclaw/workspace", "scripts"))
import forwarded_mail as fm

WS = "/Users/exomac/.openclaw/workspace"
SEEN = os.path.join(WS, "logs", "forwarded-mail-seen.json")
FEED = os.path.join(WS, "mission-control", "data", "forwarded-inbound.json")
DISCORD = "channel:1501636728711282741"  # #series-a
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
# high-signal = worth a ping (gov / PI / active-pursuit); everything else just updates the feed
HIGH = re.compile(r"nih\.gov|\.gov\b|\.mil\b|purdue\.edu|uw\.edu|noaa|nasa|era ?commons|"
                  r"institution registration|approv|kelly|park|collicott|teasley|murphy|"
                  r"subaward|solicitation|award|contract", re.I)

def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


# --- Forwards UPDATE an active task; they never create one (Jon 2026-09-09). A forward whose
# subject closely matches an OPEN task gets appended to that task as a dated note. No confident
# match => nothing created (it still lives in the inbound feed above). Idempotent: each forward is
# processed once (guarded by the SEEN set in main). ---
_SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
def _sb_key():
    try: return json.load(open(os.path.expanduser("~/.openclaw/secrets.json"))).get("supabase_service_role_key")
    except Exception: return None
def _norm(s):
    s = s or ""
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'^\s*(re|fw|fwd)\s*:\s*', '', s, flags=re.I)
        s = re.sub(r'^\s*\[[^\]]*\]\s*', '', s)
    s = re.sub(r'[^a-z0-9 ]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()
def _open_tasks(K):
    H = {"apikey": K, "Authorization": "Bearer " + K}
    out, off = [], 0
    while True:
        r = urllib.request.Request(f"{_SB}tasks?select=id,title,description,state,tags&limit=1000&offset={off}", headers=H)
        pg = json.load(urllib.request.urlopen(r, timeout=30)); out += pg
        if len(pg) < 1000: break
        off += 1000
    return [t for t in out if (t.get("state") or "").lower() in ("to do", "in progress")]
def _patch(K, tid, body):
    H = {"apikey": K, "Authorization": "Bearer " + K, "Content-Type": "application/json", "Prefer": "return=minimal"}
    urllib.request.urlopen(urllib.request.Request(_SB + f"tasks?id=eq.{tid}", data=json.dumps(body).encode(),
                                                  headers=H, method="PATCH"), timeout=30)
def fwd_update_tasks(new_forwards):
    K = _sb_key()
    if not K: return
    dry = "--dry-run" in sys.argv
    normed = [(t, _norm(t.get("title"))) for t in _open_tasks(K)]
    for r in new_forwards:
        fsubj = _norm(r.get("subject"))
        if len(fsubj) < 12:
            continue
        best, bestr = None, 0.0
        for t, nt in normed:
            if len(nt) < 12: continue
            ratio = difflib.SequenceMatcher(None, fsubj, nt).ratio()
            if ratio > bestr: bestr, best = ratio, t
        if best and bestr >= 0.72:
            note = (f"\n\n[fwd update {datetime.utcnow():%Y-%m-%d}] Jon forwarded "
                    f"\"{(r.get('subject') or '')[:120]}\" from {r.get('forwarded_from','?')} — "
                    f"{(r.get('snippet') or '')[:200]}")
            if dry:
                print(f"  [dry] fwd '{(r.get('subject') or '')[:40]}' -> #{best['id']} (r={bestr:.2f})"); continue
            desc = ((best.get("description") or "") + note)[:6000]
            tags = list(dict.fromkeys(list(best.get("tags") or []) + ["fwd-updated"]))
            _patch(K, best["id"], {"description": desc, "tags": tags,
                                   "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"})
            print(f"  fwd matched #{best['id']} (r={bestr:.2f}) — appended update, NO new task")
        else:
            print(f"  fwd '{(r.get('subject') or '')[:40]}' — no active-task match (r={bestr:.2f}); feed only, no task")

def quiet_hours():
    try:
        h = int(subprocess.run(["date", "+%H"], capture_output=True, text=True).stdout.strip())
        return h >= 23 or h < 8
    except Exception:
        return False

def main():
    rows = fm.scan(since_days=3)
    seen = set(load(SEEN, []))
    first = not seen
    new = [r for r in rows if r["id"] not in seen]
    for r in rows:
        seen.add(r["id"])
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    json.dump(sorted(seen)[-4000:], open(SEEN, "w"))
    # rolling feed (latest 50) — always current for the capture agents
    os.makedirs(os.path.dirname(FEED), exist_ok=True)
    json.dump({"updated": datetime.utcnow().isoformat(timespec="seconds") + "Z",
               "items": rows[:50]}, open(FEED, "w"), indent=2)
    print(f"forwarded-mail-watch: {len(rows)} forwards in window, {len(new)} new"
          + (" (first run — baselined, no alert)" if first else ""))
    # A new forward updates a matching ACTIVE task instead of spawning one (never creates).
    if not first and new:
        try:
            fwd_update_tasks(new)
        except Exception as e:
            print("fwd->task update failed:", e)
    if first or not new:
        return
    hot = [r for r in new if HIGH.search(r["subject"] + " " + r["forwarded_from"] + " " + r["snippet"])]
    if not hot or quiet_hours():
        return
    lines = ["📥 **Caught your forward(s)** — now in the inbound feed:"]
    for r in hot[:6]:
        who = r["forwarded_from"] if "@" in r["forwarded_from"] else "unparsed sender"
        lines.append(f"• **{who}** — {r['subject'][:70]}\n    “{r['snippet'][:130]}”")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD, "-m", "\n".join(lines)], capture_output=True, timeout=60)
    except Exception as e:
        print("alert failed:", e)

if __name__ == "__main__":
    main()
