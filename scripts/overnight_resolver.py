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
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
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
APPLY = "--apply" in sys.argv  # v2: actually mutate the board (auto-close + false-overdue fix)

OLLAMA = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma4:e4b"  # reasoning target is exos-glimmer (installed/running) but its raw /api/generate leaks agentic-channel tokens; keep gemma until Glimmer chat-template is tuned
AUTO_CAP = 12                 # hard cap on autonomous board changes per run
NO_DEADLINE_MARKERS = ("no firm deadline", "rolling", "open call", "open-call", "confirm-with-organizer",
                       "no hard deadline", "no set deadline", "deadline tbd", "rolling deadline")
# NEVER auto-close/cancel/retouch these (active per Jon directive).
PROTECTED = ("osc", "opp-021")

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


def sb_patch(task_id, payload):
    key = sb_key()
    data = json.dumps(payload).encode()
    req = urllib.request.Request(SB_URL + f"tasks?id=eq.{task_id}", data=data, method="PATCH",
                                 headers={"apikey": key, "Authorization": "Bearer " + key,
                                          "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
        b = r.read().decode()
        return json.loads(b) if b else []


def ollama(prompt):
    """Best-effort local judgment. Returns text or None (degrade gracefully if Ollama is down)."""
    try:
        data = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(OLLAMA, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode()).get("response", "").strip()
    except Exception as e:
        logline(f"ollama unavailable: {e}")
        return None


def load_answered_recent(days=7):
    """Answered decisions from the last `days` (for auto-close of their linked tasks)."""
    try:
        d = json.load(open(DECISIONS_FILE))
        arr = d if isinstance(d, list) else d.get("decisions", d.get("items", []))
    except Exception:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for x in arr:
        if (x.get("status") or "") != "answered":
            continue
        ts = x.get("answeredAt") or x.get("updated") or ""
        try:
            if datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff:
                out.append(x)
        except Exception:
            out.append(x)  # no/odd timestamp -> include (better to consider than skip)
    return out


def _protected(t):
    blob = (str(t.get("title", "")) + " " + str(t.get("category", "")) + " " + str(t.get("id", ""))).lower()
    return any(p in blob for p in PROTECTED)


def auto_resolve(tasks, answered, apply):
    """v2 (conservative): (1) close/cancel tasks whose linked ANSWERED decision clearly means
    done/declined (LLM-gated); (2) fix false-overdue tasks that DECLARE no hard deadline
    (deterministic). Returns (resolved_lines, resolved_ids). Respects PROTECTED + AUTO_CAP."""
    resolved, ids = [], set()
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    by_id = {str(t["id"]): t for t in tasks}

    # (1) Answered-decision -> close linked task (the entX/TruSight pattern). LLM classifies.
    for dec in answered:
        if len(ids) >= AUTO_CAP:
            break
        tid = str(dec.get("relatedItem") or "")
        if tid not in by_id:
            # try to find a task id embedded in the decision title/dedupeKey
            blob = (str(dec.get("title", "")) + str(dec.get("dedupeKey", "")))
            tid = next((k for k in by_id if k and (" " + k + " ") in (" " + blob + " ")), "")
        t = by_id.get(tid)
        if not t or t.get("state") in ("Done", "Cancelled") or _protected(t):
            continue
        verdict = ollama(
            "Decide the state of a TASK given the answer to its decision. Be very strict.\n"
            f"TASK: {t.get('title','')}\n"
            f"DECISION: {dec.get('title','') or dec.get('question','')}\n"
            f"ANSWER: {dec.get('answer','')}\nNOTE: {dec.get('note','')}\n\n"
            "Rules:\n"
            "- DONE only if the answer states the work is ALREADY FINISHED/sent/issued/received/resolved.\n"
            "- CANCELLED only if the answer DECLINES it (no / stand down / pass / do not do it).\n"
            "- LEAVE for everything else. CRITICAL: an approval or go-ahead to START or PROCEED "
            "(e.g. 'yes, draft it', 'go', 'approve & release', 'ready — submit now', 'yes send it') "
            "is NOT completion — that is LEAVE, because the work still has to happen.\n"
            "Reply with ONE word: DONE, CANCELLED, or LEAVE.")
        v = (verdict or "").strip().upper()
        v = "DONE" if v.startswith("DONE") else "CANCELLED" if v.startswith("CANCEL") else "LEAVE"
        if v == "LEAVE" or verdict is None:
            continue
        note = f" [AUTO-{v} {now[:10]} by overnight-resolver: linked decision {dec.get('id')} answered '{str(dec.get('answer',''))[:40]}'. Reversible — flip state if wrong.]"
        if apply:
            try:
                sb_patch(t["id"], {"state": v.title(), "completed_at": now,
                                   "description": (t.get("description") or "") + note})
            except Exception as e:
                logline(f"auto-close PATCH failed for {t['id']}: {e}"); continue
        resolved.append(f"[{t['id']}] {(t.get('title') or '')[:56]} → {v} (decision {dec.get('id')} answered)")
        ids.add(str(t["id"]))

    # (2) False-overdue fix: task is overdue but its OWN description says there is no hard deadline.
    d0 = today()
    for t in tasks:
        if len(ids) >= AUTO_CAP:
            break
        if str(t["id"]) in ids or _protected(t):
            continue
        due = parse_due(t)
        if not (due and due < d0):
            continue
        desc = (t.get("description") or "").lower()
        if any(m in desc for m in NO_DEADLINE_MARKERS):
            newdue = (d0 + timedelta(days=30)).isoformat() + "T23:59:59+00:00"
            note = f" [AUTO-DATEFIX {d0} by overnight-resolver: was false-overdue (description declares no hard deadline); internal due bumped +30d. Reversible.]"
            if apply:
                try:
                    sb_patch(t["id"], {"due_date": newdue, "description": (t.get("description") or "") + note})
                except Exception as e:
                    logline(f"date-fix PATCH failed for {t['id']}: {e}"); continue
            resolved.append(f"[{t['id']}] {(t.get('title') or '')[:56]} → due bumped +30d (was false-overdue, no hard deadline)")
            ids.add(str(t["id"]))

    return resolved, ids


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


def held_sync(tasks, open_decs, resolved_ids, apply):
    """D-7281672 (approved 2026-08-24): tasks with an open linked decision get parked at
    state=Held with a decision-link note, so the nightly digest stops re-listing them
    individually (noise reduction). If the linked decision closes and the task wasn't
    already resolved to Done/Cancelled by auto_resolve, revert it to Blocked so it
    re-enters normal flow instead of sitting in Held forever."""
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    newly_held, reverted = [], []
    for t in tasks:
        tid = str(t["id"])
        if tid in resolved_ids or _protected(t):
            continue
        state = t.get("state") or ""
        dec = decision_for(t["id"], open_decs)
        if dec and state != "Held":
            note = f" [HELD {now[:10]} by overnight-resolver: linked to open Decision {dec.get('id')}; awaiting Jon. Reversible — auto-reopens when decision closes.]"
            if apply:
                try:
                    sb_patch(t["id"], {"state": "Held", "description": (t.get("description") or "") + note})
                except Exception as e:
                    logline(f"held-set PATCH failed for {tid}: {e}"); continue
            t["state"] = "Held"
            newly_held.append(f"[{tid}] {(t.get('title') or '')[:56]} → HELD (decision {dec.get('id')})")
        elif state == "Held" and not dec:
            note = f" [UNHELD {now[:10]} by overnight-resolver: linked decision closed; reopened to To Do.]"
            if apply:
                try:
                    sb_patch(t["id"], {"state": "To Do", "description": (t.get("description") or "") + note})
                except Exception as e:
                    logline(f"held-revert PATCH failed for {tid}: {e}"); continue
            t["state"] = "To Do"
            reverted.append(f"[{tid}] {(t.get('title') or '')[:56]} → To Do (decision closed)")
    return newly_held, reverted


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

    # v2 — autonomous reversible resolution (auto-close on answered decisions + false-overdue fix).
    answered = load_answered_recent() if decisions_ok else []
    resolved, resolved_ids = auto_resolve(tasks, answered, APPLY)
    if resolved_ids:
        tasks = [t for t in tasks if str(t["id"]) not in resolved_ids]
        ws = [t for t in ws if str(t["id"]) not in resolved_ids]

    # D-7281672: park decision-linked tasks at Held (mutates `tasks` in place) + auto-reopen
    # ones whose decision closed. Runs against the full board, not just the top-15.
    newly_held, reverted_held = held_sync(tasks, open_decs, resolved_ids, APPLY) if decisions_ok else ([], [])

    # Blocked + needs-Jon are computed from the FULL board (not just the top-15) so they always
    # surface; the radar/Top-3 use the ranked working set. Each item appears in ONE bucket.
    claimed = set()
    blocked, needs_jon, advancing = [], [], []

    for t in sorted([x for x in tasks if x.get("state") == "Blocked"], key=rank_key):
        dec = decision_for(t["id"], open_decs) if decisions_ok else None
        blocked.append(f"[{t['id']}] {(t.get('title') or '')[:66]}"
                       + (f" — decision {dec.get('id')} open" if dec else " — no decision on file"))
        claimed.add(t["id"])

    held_count = 0
    for t in sorted(tasks, key=rank_key):
        if t["id"] in claimed:
            continue
        due = parse_due(t)
        overdue = due is not None and due < d
        dec = decision_for(t["id"], open_decs) if decisions_ok else None
        if dec and t.get("state") == "Held" and f"[{t['id']}]" not in "".join(newly_held):
            # Already parked on a prior run — don't re-list it every night (D-7281672 noise fix).
            held_count += 1
            claimed.add(t["id"])
        elif dec:
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
    if resolved:
        parts.append(f"✅ **RESOLVED/ADVANCED{'' if APPLY else ' (proposed — not applied)'}:**")
        parts += [f"• {x}" for x in resolved[:AUTO_CAP]]
        parts.append("")
    if needs_jon:
        parts.append("🗳️ **NEEDS JON:**")
        parts += [f"• {x}" for x in needs_jon[:8]]
        parts.append("")
    if newly_held or reverted_held or held_count:
        parts.append("🔒 **HELD (decision open, parked off nightly list):**")
        parts += [f"• NEW: {x}" for x in newly_held[:8]]
        parts += [f"• REOPENED: {x}" for x in reverted_held[:8]]
        if held_count:
            parts.append(f"• {held_count} other item(s) already held — see MC for details")
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
    mode = "auto-resolve on" if APPLY else "surface-only"
    parts.append(f"_v2 {mode}: reversible auto-close + false-overdue fixes; one-way doors always escalated. Full board: http://192.168.1.216:8080_")
    summary = "\n".join(parts)

    delivered = post_discord(summary)
    logline(f"run ok: ws={len(ws)} resolved={len(resolved)} blocked={len(blocked)} needs_jon={len(needs_jon)} "
            f"held_new={len(newly_held)} held_reopened={len(reverted_held)} held_existing={held_count} "
            f"radar={len(advancing)} decisions_ok={decisions_ok} apply={APPLY} delivered={delivered}{' (dry-run)' if DRY else ''}")
    try:
        with open(USAGE_LOG, "a") as f:
            f.write(f"| {d} | launchd+ollama | {len(ws)} | {len(resolved)} | {len(needs_jon)} | 0 |\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
