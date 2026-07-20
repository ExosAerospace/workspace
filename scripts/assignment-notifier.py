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
import json, os, re, time, subprocess, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY}
USERS = os.path.join(WS, "mission-control", "users.json")
STATE = os.path.join(WS, "logs", "assignment-notify-state.json")
LOG = os.path.join(WS, "logs", "assignment-notify.log")
MCURL = "http://192.168.1.216:8080"

EXCLUDE = {"jquinn@exosaero.com"}          # monitored directly; avoid inbox flooding
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
    url = (f"{SB}/tasks?select=id,title,description,state,priority,due_date,"
           f"category,owner,assigned_to,assigned_email&limit=5000")
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=60) as f:
        return json.load(f)


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
    active, sent = set(), 0
    for t in tasks:
        tid = str(t.get("id"))
        st = (t.get("state") or "").lower()
        email, name = resolve(t, by_email, by_name)
        if not email or email in EXCLUDE or st in ("done", "cancelled", "canceled"):
            continue
        active.add(tid)
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
    for tid in [k for k in state if k not in active]:   # prune un-assigned/closed
        del state[tid]
    json.dump(state, open(STATE, "w"))
    log(f"BASELINED {len(state)} assignments (no emails)." if baseline
        else f"run complete: sent={sent}")


if __name__ == "__main__":
    main()
