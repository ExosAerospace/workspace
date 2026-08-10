#!/usr/bin/env python3
"""decision-note-router.py — route Decisions-note escalations.

When yes/no doesn't fit, a user writes an instruction in a decision's NOTE field. This watcher
(launchd, every ~2 min) reads decisions.json and acts on notes it hasn't seen before:

  1. EXPLICIT Discord mention  (<@&roleId> role or <@userId> user)  -> ping that mention in the
     #exomac-system channel with the ask, AND create a tracked task.
  2. PLAIN instruction  ("have Neil handle X", "Lizi to follow up")  -> resolve the name to an
     owner via the roster, create a task assigned to them.  NO Discord ping.

Yes/no and the "Not my decision" reassign flow are untouched — this only rides on the note field.
Baseline-safe: first run records current note hashes and does nothing (no historical spam).
"""
import json, os, re, sys, hashlib, subprocess, shutil, urllib.request
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
USERS = os.path.join(WS, "mission-control", "users.json")
STATE = os.path.join(WS, "logs", "decision-note-router-state.json")
LOG = os.path.join(WS, "logs", "decision-note-router.log")
DISCORD_CHANNEL = "channel:1501636814849577050"  # #exomac-system
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
MENTION_RE = re.compile(r"<@[&!]?\d+>")
VERBS = r"(handle|take|own|manage|review|approve|do|follow\s?up|prepare|draft|send|fix|schedule|call|contact|reach out)"


def logline(m):
    try:
        with open(LOG, "a") as f: f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception: pass


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def roster():
    u = load(USERS, [])
    u = u if isinstance(u, list) else u.get("users", [])
    first, full = {}, {}
    for x in u:
        nm, em = (x.get("name") or "").strip(), (x.get("email") or "").strip()
        if not em: continue
        if nm:
            full[nm.lower()] = (nm, em)
            first[nm.split()[0].lower()] = (nm, em)
    return first, full


def post_discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD_CHANNEL, "-m", text],
                       capture_output=True, text=True, timeout=60)
        return True
    except Exception as e:
        logline(f"WARN discord: {e}"); return False


def mktask(task):
    body = json.dumps(task).encode()
    req = urllib.request.Request(SUPA + "/tasks", method="POST", data=body,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode() or "[]"); return d[0]["id"] if d else None
    except Exception as e:
        logline(f"WARN task: {e}"); return None


def resolve_name(note, first, full):
    m = re.search(r"\bhave\s+([A-Za-z]+)\b", note, re.I)
    cand = m.group(1).lower() if m else None
    if cand and cand in first: return first[cand]
    for key, val in full.items():   # full-name mention + a verb
        if key in note.lower() and re.search(VERBS, note, re.I): return val
    for fn, val in first.items():    # first-name + a verb
        if re.search(rf"\b{re.escape(fn)}\b", note, re.I) and re.search(VERBS, note, re.I): return val
    return None


def main():
    now = datetime.now(timezone.utc).isoformat()
    decs = load(DECISIONS, [])
    decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    state = load(STATE, None)
    first, full = roster()

    def h(s): return hashlib.sha1((s or "").encode()).hexdigest()[:16]

    if state is None:  # BASELINE — record, act on nothing
        state = {d["id"]: h(d.get("note")) for d in decs if d.get("note")}
        json.dump(state, open(STATE, "w"), indent=0)
        logline(f"baseline: recorded {len(state)} note hashes, no actions"); print("baseline"); return

    acted = 0
    for d in decs:
        note = (d.get("note") or "").strip()
        if not note: continue
        nh = h(note)
        if state.get(d["id"]) == nh: continue           # unchanged note already handled
        title = d.get("title") or d.get("question") or d["id"]
        mentions = MENTION_RE.findall(note)
        if mentions:                                     # (1) explicit mention -> ping + task
            txt = (" ".join(mentions) + f" — decision **{d['id']}**: {title}\n> {note}\n"
                   "(routed from a Decisions note — yes/no didn't fit)")
            post_discord(txt)
            owner = resolve_name(note, first, full)
            mktask({"title": f"Decision action: {title[:70]}", "owner": owner[0] if owner else "Team",
                    "assigned_email": owner[1] if owner else None, "assigned_to": owner[0] if owner else None,
                    "state": "To Do", "priority": 75, "category": "Decision", "source": "decision-note-router",
                    "tags": ["decision-routed"],
                    "description": f"From decision {d['id']} ({title}). Note: {note}. Discord mention pinged: {' '.join(mentions)}."})
            logline(f"{d['id']}: mention route -> {mentions}")
            acted += 1
        else:                                            # (2) plain instruction -> task, no ping
            owner = resolve_name(note, first, full)
            if not owner:
                state[d["id"]] = nh; continue            # nothing to route; mark seen
            mktask({"title": f"Decision action: {title[:70]}", "owner": owner[0], "assigned_email": owner[1],
                    "assigned_to": owner[0], "state": "To Do", "priority": 72, "category": "Decision",
                    "source": "decision-note-router", "tags": ["decision-routed"],
                    "description": f"From decision {d['id']} ({title}). Instruction: {note}."})
            logline(f"{d['id']}: plain route -> {owner[1]}")
            acted += 1
        state[d["id"]] = nh
    json.dump(state, open(STATE, "w"), indent=0)
    print(f"routed {acted}")


main()
