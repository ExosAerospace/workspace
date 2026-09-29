#!/usr/bin/env python3
"""
assignment-notifier.py — UNIVERSAL task-assignment email notifier.

Emails the assigned owner when a Mission Control task is assigned or reassigned,
REGARDLESS of how the assignment was made: the web app, the email auto-capture,
cron agents, scripts, or direct database writes. Closes the gap where only
app/API (server.js) assignments notified — backend/DB assignments were silent.

Deterministic launchd poller (same pattern as the other watchers). Dedup via a
state file so nobody is emailed twice for the same assignment.

BASELINE: on first run (no state file) it records every current assignment
WITHOUT emailing (no inbox blast), then emails only on assignment CHANGES after.

Jon (jquinn@exosaero.com) is excluded by default — he monitors the board directly
and the auto-capture assigns him many tasks. Remove from EXCLUDE to notify him too.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, os, re, time, subprocess, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}
USERS = os.path.join(WS, "mission-control", "users.json")
STATE = os.path.join(WS, "logs", "assignment-notify-state.json")
# D-7281739 fix #3: mc-email-command handling writes {tid: requester_email} here for tasks it
# creates/assigns to the requester during a run. Those already got the email-command reply, so the
# notifier must NOT also email the same person 5 min later. Seeded silently as already-notified.
SUPPRESS = os.path.join(WS, "logs", "assignment-notify-suppress.json")
LOG = os.path.join(WS, "logs", "assignment-notify.log")
MCURL = "http://192.168.143.216:8080"

EXCLUDE = {"jquinn@exosaero.com",          # monitored directly; avoid inbox flooding
           "exo@exosaero.com"}             # Exo AI = in-system agent, no deliverable mailbox;
                                           # this GCC High addr rejects the pm.me sender (550 5.4.1)
                                           # and only produces MAILER-DAEMON bounce loops. It IS a
                                           # valid-looking email so resolve() returns it, bypassing
                                           # the SKIP_OWNERS owner-string check — exclude by address.
SKIP_OWNERS = {"", "system", "exo", "exomac", "both", "unassigned", "none", "team"}
EMAIL_RX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def log(m):
    try:
        open(LOG, "a").write(f"[{time.strftime('%Y-%m-%d %H:%M:%S %Z')}] {m}\n")
    except Exception:
        pass


def load_json(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def build_user_index():
    d = load_json(USERS, [])
    us = d if isinstance(d, list) else (d.get("users") or list(d.values()))
    by_email, by_name = {}, {}
    for u in us:
        if not isinstance(u, dict):
            continue
        if u.get("email"):
            by_email[u["email"].strip().lower()] = u
        if u.get("name"):
            by_name[u["name"].strip().lower()] = u
    return by_email, by_name


def resolve(task, by_email, by_name):
    """Return (email, display_name) for the current assignee, or (None, None)."""
    # UTD capstone tasks are created in batches (dozens at once) and the students get
    # ONE consolidated prompter email from Exo instead. Per-task mail flooded them
    # (38 emails on 2026-09-27) and linked a LAN-only MC address they can't reach.
    if (task.get("source") or "").startswith("exo-capstone"):
        return None, None
    ae = (task.get("assigned_email") or "").strip().lower()
    owner = (task.get("owner") or "").strip()
    if ae and EMAIL_RX.match(ae):
        u = by_email.get(ae)
        return ae, (u.get("name") if u else (owner or ae))
    o = owner.lower()
    if o in SKIP_OWNERS:
        return None, None
    if o in ("jon", "john quinn"):
        u = by_email.get("jquinn@exosaero.com")
    else:
        u = by_email.get(o) or by_name.get(o)
    if u and u.get("email") and u.get("active") is not False:
        return u["email"].strip().lower(), u.get("name") or owner
    return None, None


def fetch_tasks():
    # PostgREST caps every response at 1000 rows regardless of limit=, so page with
    # offset until a short page. Without this, tasks beyond the first 1000 (high ids,
    # newly created) are invisible and their assignees never get notified.
    sel = ("select=id,title,description,state,priority,due_date,"
           "category,owner,assigned_to,assigned_email,source&order=id&limit=1000")
    out, off = [], 0
    while True:
        req = urllib.request.Request(f"{SB}/tasks?{sel}&offset={off}", headers=H)
        with urllib.request.urlopen(req, timeout=60) as f:
            page = json.load(f)
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def send(to, name, task):
    title = task.get("title") or "Untitled task"
    due = str(task.get("due_date"))[:10] if task.get("due_date") else "None"
    prio = task.get("priority") if task.get("priority") is not None else "—"
    body = (f"You have been assigned a task in Exos Mission Control.\n\n"
            f"Task:        {title}\n"
            f"Owner:       {name} <{to}>\n"
            f"Status:      {task.get('state') or 'To Do'}\n"
            f"Priority:    {prio}\n"
            f"Category:    {task.get('category') or '—'}\n"
            f"Due:         {due}\n\n"
            f"Details:\n{task.get('description') or '(no description provided)'}\n\n"
            f"Open Mission Control: {MCURL}/")
    msg = (f"From: jquinnexo@pm.me\r\nTo: {to}\r\n"
           f"Subject: [Mission Control] Task assigned to you: {title[:80]}\r\n\r\n"
           + body.replace("\n", "\r\n"))
    p = subprocess.run(["msmtp", "-a", "protonmail", to],
                       input=msg.encode(), capture_output=True, timeout=60)
    return p.returncode == 0, (p.stderr.decode()[:200] if p.returncode else "")


def main():
    by_email, by_name = build_user_index()
    try:
        tasks = fetch_tasks()
    except Exception as e:
        log(f"fetch failed: {e}")
        return
    state = load_json(STATE, None)
    baseline = state is None
    if baseline:
        state = {}
    suppress = load_json(SUPPRESS, {}) or {}   # {tid: email} seeded by mc-email-command handling
    # present_tids/terminal_tids drive pruning. A task that is fetched but merely FAILS to resolve
    # this run (transient users.json read, key hiccup) stays "present" and is NOT pruned — that is
    # the fix for the prune-then-re-add re-send loop (D-7281739 #4).
    present_tids, terminal_tids = set(), set()
    active, sent = set(), 0
    for t in tasks:
        tid = str(t.get("id"))
        present_tids.add(tid)
        st = (t.get("state") or "").lower()
        if st in ("done", "cancelled", "canceled"):
            terminal_tids.add(tid)
            continue
        email, name = resolve(t, by_email, by_name)
        if not email or email in EXCLUDE:
            continue
        active.add(tid)
        # D-7281739 fix #3: task assigned to this person during an email-command run already got the
        # reply — seed state as already-notified (no second email), then drop the suppress entry.
        if suppress.get(tid) == email and state.get(tid) != email:
            state[tid] = email
            log(f"suppressed (email-command reply already sent) {email} -> task {tid}")
            continue
        if state.get(tid) == email:
            continue                      # already notified for this assignee
        if baseline:
            state[tid] = email            # record silently, no email
            continue
        ok, err = send(email, name or email, t)
        if ok:
            state[tid] = email
            sent += 1
            log(f"notified {email} -> task {tid}: {str(t.get('title'))[:50]}")
        else:
            log(f"SEND FAIL {email} task {tid}: {err}")
    # Prune ONLY genuinely-gone tasks (no longer present) or terminal (done/cancelled). Never prune a
    # still-present task just because it didn't resolve this run — that was the re-send bug.
    for tid in [k for k in state if (k in terminal_tids) or (k not in present_tids)]:
        del state[tid]
    json.dump(state, open(STATE, "w"))
    # consume suppress entries whose task is now recorded (or gone) so the file stays small
    if suppress:
        remaining = {tid: em for tid, em in suppress.items()
                     if tid not in state and tid in present_tids}
        try:
            json.dump(remaining, open(SUPPRESS, "w"))
        except Exception:
            pass
    log(f"BASELINED {len(state)} assignments (no emails)." if baseline
        else f"run complete: sent={sent}")


if __name__ == "__main__":
    main()
