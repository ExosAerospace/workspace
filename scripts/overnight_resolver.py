#!/usr/bin/env python3
"""
Overnight Resolver — launchd-backed (replaces the flaky agent-turn cron).

Why this exists: the old Overnight Resolver was an ISOLATED agent-turn cron whose prompt
told it to run `curl` against Supabase and the localhost decisions API — but its toolsAllow
had NO shell tool, and its sandbox BLOCKS private/internal IPs. So every night it failed to
fetch the board, flailed on web_search against the API URL, and cried wolf ("all automation
halted"). None of that was true; it just couldn't reach the data.

This version runs LOCALLY on exomac under launchd (com.exos.overnight-resolver, 23:00 CT), so
it can reach Supabase (public REST) with real HTTP and read the decisions store off local disk.
Deterministic: pull board + open decisions, build the top-15 working set, compute
STILL-BLOCKED / NEEDS-JON / RESOLVED buckets, apply the decisions fail-safe, and DM Jon a
morning summary. The model stays OUT of the critical path (reliability first), matching the
capture-action-dispatch lesson.

Scope (v1): analyze + surface + summarize. It does NOT autonomously mutate the board or post
new Decisions — those need judgment and are already covered by decision-triage + the morning
digest. A future v2 can add local-Ollama reasoning to auto-advance reversible items.

Run: python3 scripts/overnight_resolver.py [--dry-run]
"""
import os, sys, json, ssl, shutil, subprocess, urllib.request
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
DECISIONS_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
USAGE_LOG = os.path.join(WS, "memory", "overnight-usage-log.md")
LOG = os.path.join(WS, "logs", "overnight-resolver.log")
SB_URL = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
JON = "user:1501632195163590739"
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
DRY = "--dry-run" in sys.argv

LEVERAGE = ("series a", "sbir", "sttr", "tacfi", "stratfi", "darpa", "rofr", "scorpius",
            "osc", "opp-021", "nasa", "afrl", "entx", "rdre")


def logline(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"[{datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M %Z}] {msg}\n")
    except Exception:
        pass


def sb_key():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def sb_get(path):
    key = sb_key()
    req = urllib.request.Request(SB_URL + path, headers={"apikey": key, "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode())


def _subprocess_env():
    env = os.environ.copy()
    extra = [os.path.dirname(OPENCLAW), "/Users/exomac/.local/share/mise/shims",
             "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra + [env.get("PATH", "")])
    return env


def post_discord(text):
    if DRY:
        print("----- (dry-run) would DM Jon -----\n" + text + "\n----------------------------------")
        return True
    try:
        r = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", text],
                           capture_output=True, text=True, timeout=90, env=_subprocess_env())
        if r.returncode != 0:
            logline(f"WARN discord send rc={r.returncode}: {r.stderr[:200]}")
            return False
        return True
    except Exception as e:
        logline(f"WARN discord send failed: {e}")
        return False


def today():
    return datetime.now(timezone.utc).astimezone().date()


def parse_due(t):
    d = t.get("due_date")
    if not d:
        return None
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00")).date()
    except Exception:
        return None


def rank_key(t):
    due = parse_due(t)
    overdue = due is not None and due < today()
    days_to = (due - today()).days if due else 9999
    title = (t.get("title") or "").lower()
    lev = any(k in title for k in LEVERAGE)
    # sort: overdue first, then nearest due, then leverage, then priority desc
    return (0 if overdue else 1, days_to, 0 if lev else 1, -(t.get("priority") or 0))


def load_open_decisions():
    """Read decisions.json directly (local). Returns (list_or_None). None => fetch failed."""
    try:
        d = json.load(open(DECISIONS_FILE))
        arr = d if isinstance(d, list) else d.get("decisions", d.get("items", []))
        return [x for x in arr if (x.get("status") or "open") == "open"]
    except Exception as e:
        logline(f"decisions read failed: {e}")
        return None


def decision_for(task_id, open_decs):
    tid = str(task_id)
    for x in open_decs:
        if str(x.get("relatedItem") or "") == tid:
            return x
        blob = (str(x.get("title", "")) + str(x.get("question", "")) + str(x.get("dedupeKey", ""))).lower()
        if tid and tid.lower() in blob:
            return x
    return None


def main():
    d = today()
    try:
        tasks = sb_get("tasks?select=id,title,owner,state,priority,due_date,category,assigned_to,updated_at"
                       "&state=neq.Done&order=priority.desc&limit=400")
    except Exception as e:
        logline(f"FATAL board fetch failed: {e}")
        post_discord(f"🌙 **Overnight Resolver — {d}**\n\n⚠️ Board fetch from Supabase failed ({str(e)[:120]}). "
                     "No summary this run; the rest of the automation fleet is unaffected. Will retry tomorrow.")
        return

    tasks = [t for t in tasks if (t.get("state") or "") not in ("Done", "Cancelled")]
    # Working set: Blocked + overdue + due within 14 days + top In Progress, capped at 15.
    horizon = d + timedelta(days=14)
    ws = []
    for t in tasks:
        due = parse_due(t)
        if (t.get("state") == "Blocked" or (due and due <= horizon) or t.get("state") == "In Progress"):
            ws.append(t)
    ws.sort(key=rank_key)
    ws = ws[:15]

    open_decs = load_open_decisions()
    decisions_ok = open_decs is not None
    # Fail-safe: implausibly-few open decisions for a board this size => treat as failed fetch.
    if decisions_ok and len(open_decs) == 0 and len(tasks) > 50:
        logline("decisions fetch returned 0 for a large board — treating as unreliable (fail-safe)")
        decisions_ok = False

    # Blocked + needs-Jon are computed from the FULL board (not just the top-15) so they always
    # surface; the radar/Top-3 use the ranked working set. Each item appears in ONE bucket.
    claimed = set()
    blocked, needs_jon, advancing = [], [], []

    for t in sorted([x for x in tasks if x.get("state") == "Blocked"], key=rank_key):
        dec = decision_for(t["id"], open_decs) if decisions_ok else None
        blocked.append(f"[{t['id']}] {(t.get('title') or '')[:66]}"
                       + (f" — decision {dec.get('id')} open" if dec else " — no decision on file"))
        claimed.add(t["id"])

    for t in sorted(tasks, key=rank_key):
        if t["id"] in claimed:
            continue
        due = parse_due(t)
        overdue = due is not None and due < d
        dec = decision_for(t["id"], open_decs) if decisions_ok else None
        if dec:
            needs_jon.append(f"[{t['id']}] {(t.get('title') or '')[:58]} — decision {dec.get('id')} awaiting you")
            claimed.add(t["id"])
        elif overdue and not (t.get("assigned_to") or t.get("owner")):
            needs_jon.append(f"[{t['id']}] {(t.get('title') or '')[:58]} — OVERDUE, no owner (route it)")
            claimed.add(t["id"])

    for t in ws:
        if t["id"] in claimed:
            continue
        due = parse_due(t)
        overdue = due is not None and due < d
        tag = "OVERDUE" if overdue else (f"due {due}" if due else t.get("state"))
        advancing.append(f"[{t['id']}] {(t.get('title') or '')[:58]} — {tag}")

    top3 = [f"{i+1}. [{t['id']}] {(t.get('title') or '')[:64]}" for i, t in enumerate(ws[:3])]

    parts = [f"🌙 **Overnight Resolver — {d}**",
             f"Working set: top {len(ws)} of {len(tasks)} open items (ranked: overdue → nearest deadline → leverage).", ""]
    if needs_jon:
        parts.append("🗳️ **NEEDS JON:**")
        parts += [f"• {x}" for x in needs_jon[:8]]
        parts.append("")
    if blocked:
        parts.append("⛔ **STILL BLOCKED:**")
        parts += [f"• {x}" for x in blocked[:8]]
        parts.append("")
    if advancing:
        parts.append("🔎 **ON THE RADAR (due / in-progress):**")
        parts += [f"• {x}" for x in advancing[:8]]
        parts.append("")
    parts.append("**Top 3 for today:**")
    parts += top3
    if not decisions_ok:
        parts.append("")
        parts.append("_Note: decisions store was unreadable/implausible this run — escalation matching skipped (fail-safe). Board data above is good._")
    parts.append("")
    parts.append("_Analysis + surfacing only; no autonomous board changes. Full board: http://192.168.1.216:8080_")
    summary = "\n".join(parts)

    delivered = post_discord(summary)
    logline(f"run ok: ws={len(ws)} blocked={len(blocked)} needs_jon={len(needs_jon)} radar={len(advancing)} "
            f"decisions_ok={decisions_ok} delivered={delivered}{' (dry-run)' if DRY else ''}")
    try:
        with open(USAGE_LOG, "a") as f:
            f.write(f"| {d} | launchd-deterministic | {len(ws)} | 0 | {len(needs_jon)} | 0 |\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
