#!/usr/bin/env python3
"""
Capstone access monitor (Build A) — watches for privilege-escalation probing by sandboxed
UTD student (early_adopter) accounts. The MC server (mission-control/server.js `auditDeny`)
logs every DENIED sandbox request to logs/capstone-access-audit.jsonl; this launchd job
(com.exos.capstone-access-monitor, ~10 min) scans new entries and emails Lizi (owner) + Jon
when it sees escalation signals. Deterministic; offset-tracked so it never re-alerts.

Run: python3 scripts/capstone_access_monitor.py
"""
import os, json, subprocess

WS = "/Users/exomac/.openclaw/workspace"
AUDIT = os.path.join(WS, "logs", "capstone-access-audit.jsonl")
STATE = os.path.join(WS, "logs", "capstone-monitor-state.json")
LOG = os.path.join(WS, "logs", "capstone-access-monitor.log")
LIZI = "lquinn@exosaero.com"
JON = "jquinn@exosaero.com"
FROM = "jquinnexo@pm.me"  # Proton Bridge-authorized sender

# High-sensitivity targets a student should never touch — hitting these = escalation attempt.
HIGH_PATHS = ("/api/deals", "/api/crm", "/api/decisions", "/api/admin", "/api/commissions",
              "/api/exosops", "/api/templates", "/uploads/", "/backup/", "/viewpdf/", "/api/users")
PROBE_THRESHOLD = 8  # >= this many denials from one user in a batch = probing


def logline(m):
    try:
        with open(LOG, "a") as f:
            from datetime import datetime, timezone
            f.write(f"[{datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M %Z}] {m}\n")
    except Exception:
        pass


def load_offset():
    try:
        return json.load(open(STATE)).get("offset", 0)
    except Exception:
        return 0


def save_offset(o):
    try:
        json.dump({"offset": o}, open(STATE, "w"))
    except Exception:
        pass


def email_alert(subject, body):
    msg = (f"From: Exos Security <{FROM}>\nTo: {LIZI}\nCc: {JON}\n"
           f"Reply-To: {JON}\nSubject: {subject}\n\n{body}")
    p = subprocess.run(["msmtp", "-a", "default", LIZI, JON], input=msg.encode(), capture_output=True)
    logline(f"alert emailed rc={p.returncode} {p.stderr.decode()[:150]}")


def main():
    if not os.path.exists(AUDIT):
        return
    size = os.path.getsize(AUDIT)
    off = load_offset()
    if off > size:  # file rotated/truncated
        off = 0
    if off == size:
        return
    with open(AUDIT) as f:
        f.seek(off)
        new = f.read()
        save_offset(f.tell())

    events = []
    for line in new.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        # This monitor is ONLY for UTD capstone (early_adopter) students. The shared audit log
        # (mission-control/server.js auditDeny) also records dd_reviewer denials — those are the
        # external RTO due-diligence data-room sandbox working as designed (default-deny; its own
        # audit trail is logs/dd-activity.log). Do NOT mislabel a dd_reviewer as a "student probing."
        if (ev.get("role") or "") != "early_adopter":
            continue
        events.append(ev)
    if not events:
        return

    # Aggregate by user; find escalation signals.
    by_user = {}
    for e in events:
        by_user.setdefault(e.get("email") or e.get("userId") or "unknown", []).append(e)

    alerts = []
    for user, evs in by_user.items():
        high = [e for e in evs if any(h in (e.get("url") or "") for h in HIGH_PATHS)]
        traversal = [e for e in evs if ".." in (e.get("url") or "")]
        probing = len(evs) >= PROBE_THRESHOLD
        if high or traversal or probing:
            reasons = []
            if high: reasons.append(f"{len(high)} hit(s) on restricted endpoints")
            if traversal: reasons.append(f"{len(traversal)} path-traversal attempt(s)")
            if probing: reasons.append(f"{len(evs)} total denials (probing)")
            sample = "\n".join(f"    {e.get('ts','')} {e.get('method','')} {e.get('url','')} [{e.get('reason','')}] ip={e.get('ip','')}"
                               for e in (high + traversal + evs)[:12])
            alerts.append(f"USER: {user}\n  Signals: {', '.join(reasons)}\n  Recent denied requests:\n{sample}")

    logline(f"scanned {len(events)} new denial(s); {len(alerts)} user(s) flagged")
    if alerts:
        body = ("Heads up — one or more UTD capstone (early_adopter) accounts tried to reach data "
                "beyond their 'Payload Sales' sandbox. The server BLOCKED every attempt (this is a "
                "detection alert, not a breach). Review, and suspend the account if it looks intentional.\n\n"
                + "\n\n".join(alerts)
                + "\n\nBoard: http://192.168.1.216:8080  ·  To suspend: set the user's active=false in Mission Control admin.")
        email_alert(f"⚠️ Capstone access alert — {len(alerts)} student account(s) probing", body)


if __name__ == "__main__":
    main()
