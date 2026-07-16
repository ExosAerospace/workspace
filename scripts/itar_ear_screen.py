#!/usr/bin/env python3
"""
itar_ear_screen.py — backup export-control screen for the email intake.

BACKUP net, not the primary control: the employee's judgment (only route non-CUI/
non-ITAR/EAR email to the intake) is primary. This catches emails that slip through
by scanning subject + body + attachment names for explicit ITAR / EAR / CUI /
export-control indicators. On a hit the calling watcher HOLDS the email (does not
capture it to a task and does not run it as a command), quarantines it, and alerts.

Conservative by design toward false positives: a hit means "hold for human review,"
which is safe. Import and use:
    from itar_ear_screen import screen, attachment_names, quarantine_and_alert
    hits = screen(subject + "\\n" + body + "\\n" + " ".join(attachment_names(msg)))
    if hits:
        quarantine_and_alert(message_id, sender, subject, hits, source="tracker")
        # ...skip processing this email...
"""
import json, os, re, subprocess, time, hashlib

WS = "/Users/exomac/.openclaw/workspace"
QLOG = os.path.join(WS, "logs", "itar-ear-quarantine.jsonl")
DECISIONS_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON_DISCORD = "1501632195163590739"

# (regex, human label). Case-insensitive. Explicit export-control / controlled-info markers.
INDICATORS = [
    (r'\bITAR\b', 'ITAR'),
    (r'export[\s\-]{0,3}control(?:led)?', 'export control'),
    (r'\bEAR99\b', 'EAR99'),
    (r'\bECCN\b', 'ECCN'),
    (r'\bUSML\b', 'USML'),
    (r'\bDDTC\b', 'DDTC'),
    (r'\bdefense article', 'defense article'),
    (r'\bdefense service', 'defense service'),
    (r'\bdeemed export\b', 'deemed export'),
    (r'\bNOFORN\b', 'NOFORN'),
    (r'\b22\s*C\.?\s?F\.?\s?R\.?', '22 CFR (ITAR)'),
    (r'\b15\s*C\.?\s?F\.?\s?R\.?', '15 CFR (EAR)'),
    (r'commodity jurisdiction', 'commodity jurisdiction'),
    (r'technical assistance agreement', 'TAA'),
    (r'manufacturing license agreement', 'MLA'),
    (r'controlled unclassified information', 'CUI'),
    (r'(?<![A-Za-z])CUI(?![A-Za-z])', 'CUI'),
    (r'contains technical data.{0,60}(export|itar|controll)', 'technical-data export marking'),
    (r'export administration regulation', 'EAR'),
    (r'international traffic in arms', 'ITAR'),
]
_COMPILED = [(re.compile(p, re.I | re.S), label) for p, label in INDICATORS]


def screen(text):
    """Return a de-duplicated list of matched export-control indicator labels."""
    if not text:
        return []
    found = []
    for rx, label in _COMPILED:
        if rx.search(text) and label not in found:
            found.append(label)
    return found


def attachment_names(msg):
    names = []
    try:
        for p in msg.walk():
            fn = p.get_filename()
            if fn:
                names.append(fn)
    except Exception:
        pass
    return names


def _already(message_id):
    if not message_id or not os.path.exists(QLOG):
        return False
    try:
        with open(QLOG) as f:
            for line in f:
                try:
                    if json.loads(line).get("message_id") == message_id:
                        return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _alert(text):
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.14.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", JON_DISCORD, "-m", text],
                       capture_output=True, text=True, timeout=60, env=env)
    except Exception:
        pass


def _create_hold_decision(message_id, sender, subject, hits):
    """Drop the hold into the ROUTER'S OWN Decisions matrix so they must adjudicate it."""
    try:
        arr = json.load(open(DECISIONS_FILE))
    except Exception:
        arr = []
    dedupe = "xctl-" + (message_id or subject or "")
    if any(d.get("dedupeKey") == dedupe for d in arr):
        return
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    who = sender or "jquinn@exosaero.com"
    arr.append({
        "id": "XCTL-" + hashlib.sha1(dedupe.encode()).hexdigest()[:6].upper(),
        "created": now, "updated": now,
        "source": "Export-control screen",
        "title": "Export-control HOLD — " + (subject or "(no subject)")[:80],
        "question": ("An email you routed to Mission Control was HELD as potential export-controlled "
                     "content (flagged: " + ", ".join(hits) + "). Was it correctly held?"),
        "context": ("Nothing was captured or acted on. If it is controlled, it stays in SharePoint. "
                    "If this was a false positive, re-send a cleared version or ask an admin to "
                    "release it — controlled content is never auto-released."),
        "proposedAction": "Confirm whether the hold was correct.",
        "type": "yesno",
        "options": ["Yes — correctly held (keep it in SharePoint)", "No — false positive"],
        "priority": "high", "dedupeKey": dedupe,
        "status": "open", "answer": None, "note": "", "answeredAt": None,
        "assignedTo": who, "approver": who,
    })
    tmp = DECISIONS_FILE + ".tmp"
    json.dump(arr, open(tmp, "w"), indent=2)
    os.replace(tmp, DECISIONS_FILE)


def quarantine_and_alert(message_id, sender, subject, hits, source):
    """Hold the email: log it, put an adjudication Decision in the sender's matrix, alert Jon.
    Deduped by message-id. Returns True if newly held."""
    if _already(message_id):
        return False
    os.makedirs(os.path.dirname(QLOG), exist_ok=True)
    rec = {"message_id": message_id, "sender": sender, "subject": subject,
           "indicators": hits, "source": source,
           "held_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(QLOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    try:
        _create_hold_decision(message_id, sender, subject, hits)
    except Exception:
        pass
    _alert("🛑 EXPORT-CONTROL HOLD — an email routed to the Mission Control intake was NOT "
           "captured or acted on (tripped export-control indicators). The sender now has a "
           "Decision in their matrix to confirm whether the hold is valid.\n"
           f"From: {sender}\nSubject: {subject}\nFlagged: {', '.join(hits)}")
    return True


if __name__ == "__main__":
    import sys
    print(screen(sys.stdin.read()))
