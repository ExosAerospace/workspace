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
        save_offset(0)  # persist the reset, else lines appended later are read from the stale offset
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
        # Skip throwaway accounts minted by automated sandbox self-tests (e.g.
        # montana_partner_access.py --selftest --live) — they probe on purpose to prove the block.
        if (ev.get("email") or "").lower().endswith("@exos-selftest.invalid"):
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
                + "\n\nBoard: http://192.168.143.216:8080  ·  To suspend: set the user's active=false in Mission Control admin.")
        email_alert(f"⚠️ Capstone access alert — {len(alerts)} student account(s) probing", body)


# ── OUTPUT eval (exo3 R5): `capstone_access_monitor.py selftest` ────────────
# Read-only: fixture audit log in a temp dir with msmtp faked (nothing is sent), then read-only
# checks of the real offset state + alert log.
INTERNAL_RECIPIENTS = {LIZI, JON}


def _selftest_fixture():
    import tempfile, shutil, types
    g = globals()
    saved = {k: g[k] for k in ("AUDIT", "STATE", "LOG", "subprocess")}
    tmp = tempfile.mkdtemp(prefix="capmon-selftest-")
    sends, res = [], []
    try:
        g.update(AUDIT=os.path.join(tmp, "audit.jsonl"), STATE=os.path.join(tmp, "state.json"),
                 LOG=os.path.join(tmp, "log.txt"),
                 subprocess=types.SimpleNamespace(run=lambda argv, **k: sends.append((argv, k.get("input")))
                                                  or types.SimpleNamespace(returncode=0, stderr=b"")))
        ev = lambda email, url, role="early_adopter": json.dumps({"email": email, "url": url, "role": role}) + "\n"
        with open(g["AUDIT"], "w") as f:
            f.write(ev("rev@dd.com", "/api/deals", role="dd_reviewer"))          # not a student
            f.write(ev("bot@exos-selftest.invalid", "/api/crm"))                  # sandbox self-test account
            f.write(ev("ok@utdallas.edu", "/api/tasks"))                          # 1 harmless denial
        main()
        res.append(("fixture: dd_reviewer / self-test / single harmless denial -> no alert", not sends))
        with open(g["AUDIT"], "a") as f:
            f.write(ev("probe@utdallas.edu", "/api/decisions"))
            f.write(ev("trav@utdallas.edu", "/files/../secrets.json"))
        main()
        res.append(("fixture: restricted endpoint + traversal -> exactly one alert", len(sends) == 1))
        body = (sends[0][1] or b"").decode() if sends else ""
        res.append(("fixture: alert names both flagged users only",
                    "probe@utdallas.edu" in body and "trav@utdallas.edu" in body and "ok@utdallas.edu" not in body))
        rcpts = set(sends[0][0][3:]) if sends else set()
        res.append(("fixture: alert recipients internal only", rcpts == INTERNAL_RECIPIENTS))
        main()
        res.append(("fixture: re-run on same offset -> no re-alert", len(sends) == 1))
        open(g["AUDIT"], "w").close()           # rotation/truncation, then new denials arrive
        main()
        with open(g["AUDIT"], "a") as f:
            for _ in range(PROBE_THRESHOLD):
                f.write(ev("p2@utdallas.edu", "/api/tasks"))
        main()
        res.append(("fixture: truncated log rescanned; >= threshold denials = probing alert", len(sends) == 2))
    finally:
        g.update(saved)
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def _selftest_live():
    import re, time
    res = []
    try:
        off = load_offset()
        size = os.path.getsize(AUDIT) if os.path.exists(AUDIT) else 0
        res.append((f"live: offset {off} <= audit size {size} (scanner keeping up)", 0 <= off <= size))
    except Exception as e:
        res.append((f"live: offset check error {e}", False))
    try:
        cutoff = time.time() - 7 * 86400
        bad = []
        if os.path.exists(LOG):
            for line in open(LOG, errors="replace"):
                m = re.match(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", line)
                if not m or "alert emailed rc=" not in line:
                    continue
                if time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M")) < cutoff:
                    continue
                if "alert emailed rc=0" not in line:
                    bad.append(line.strip()[:120])
        res.append(("live: every alert email in 7d delivered (msmtp rc=0)" + (f" -> {bad[:3]}" if bad else ""), not bad))
    except Exception as e:
        res.append((f"live: alert-log check error {e}", False))
    return res


def selftest():
    res = _selftest_fixture() + _selftest_live()
    for n, ok in res:
        print(("PASS " if ok else "FAIL ") + n)
    nf = sum(1 for _, ok in res if not ok)
    print(f"capstone_access_monitor selftest: {'PASS' if not nf else 'FAIL'} ({len(res) - nf}/{len(res)})")
    return 0 if not nf else 1


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    main()
