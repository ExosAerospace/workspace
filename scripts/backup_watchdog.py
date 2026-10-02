#!/usr/bin/env python3
"""
backup_watchdog.py — watches the DR backup-health sentinel and enforces the safety policy.

Runs hourly (launchd). If the last successful Studio->Mini backup is stale/missing or a
pause is already set:
  1. Sets the backup-health PAUSE flag  -> risky/state-mutating crons no-op (via backup_health_gate).
  2. Notifies Jon (Discord DM + #exomac-system) and emails him — DEDUPED (one alert per
     outage, then at most one reminder / 24h), so it never spams.
When health returns, it clears the pause and sends a single recovery note.

Also (2026-10-02, Jon): alerts on
  - checksum FAIL — the last post-backup content-hash verify (dr_verify.py) found a mismatch;
  - "Mini link down" — the Mini doesn't answer over the DR ssh link (two probes ~20s apart).
    Typical cause: the Mini rebooted after a power loss and is sitting FileVault-locked.
    Alert-only (no pause): the Studio's data is fine, but the DR copy and failover are not.
Each condition is deduped separately (one alert per outage, a reminder every 24h, one recovery).

Usage: python3 scripts/backup_watchdog.py [--force-alert] [--dry-run] [--selftest]
"""
import os, sys, json, time, subprocess
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import backup_health_gate as gate
import dr_verify

CFG = json.load(open(os.path.join(WS, "config", "dr-backup.json")))
STATE_DIR = gate.STATE_DIR
ALERT_MARK = os.path.join(STATE_DIR, "backup-watchdog-lastalert.json")
LOG = os.path.join(WS, "logs", "backup-watchdog.log")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
REMINDER_EVERY_H = 24

def logline(s):
    os.makedirs(os.path.join(WS, "logs"), exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat()} {s}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def _openclaw_send(target, text):
    if not os.path.exists(OPENCLAW):
        logline(f"WARN openclaw not at {OPENCLAW}; skip discord to {target}"); return
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", target, "-m", text], timeout=60, check=False)
    except Exception as e:
        logline(f"WARN discord send to {target} failed: {e}")

DRY_RUN = "--dry-run" in sys.argv[1:] or "--selftest" in sys.argv[1:]
SENT = []   # what would have been sent (dry-run / selftest)

def notify(text):
    if DRY_RUN:
        SENT.append(text); logline(f"[dry-run] would notify: {text[:160]}"); return
    _openclaw_send(CFG.get("alert_discord_dm_target", "user:1501632195163590739"), text)
    sysch = CFG.get("alert_discord_system_channel")
    if sysch:
        _openclaw_send(sysch, text)
    # email via msmtp (best-effort)
    to = CFG.get("alert_email_to", "jquinn@exosaero.com")
    try:
        msg = f"To: {to}\nSubject: [Exos DR] backup-health alert\n\n{text}\n"
        subprocess.run(["msmtp", to], input=msg.encode(), timeout=60, check=False)
    except Exception as e:
        logline(f"WARN email alert failed: {e}")

def load_mark():
    try: return json.load(open(ALERT_MARK))
    except Exception: return {}

def save_mark(d):
    if DRY_RUN:
        return
    os.makedirs(STATE_DIR, exist_ok=True)
    json.dump(d, open(ALERT_MARK, "w"), indent=2)

def _fleet(status, detail):
    try:
        import fleet_log
        fleet_log.event("backup-watchdog", "govern", "check", detail={"summary": detail[:300]},
                        owner="John Quinn", outcome=status, level="warn" if status != "ok" else "info")
    except Exception:
        pass

def check_side(key, bad, reason, mark, now, alert_text, recover_text):
    """Deduped alert/recover state machine for one side-condition (link / checksum)."""
    m = mark.get(key, {})
    if not bad:
        if m.get("state") == "alerted":
            notify(recover_text)
            mark[key] = {"state": "healthy", "since": now}
            logline(f"{key}: recovered")
        return
    if m.get("state") != "alerted" or (now - m.get("last_alert_epoch", 0)) > REMINDER_EVERY_H * 3600:
        notify(alert_text)
        mark[key] = {"state": "alerted", "last_alert_epoch": now, "reason": reason}
        logline(f"{key}: ALERTED — {reason}")
    else:
        logline(f"{key}: still bad ({reason}); alert suppressed (deduped)")

def side_checks(mark, now, probe=None, verify_state=None):
    probe = probe or dr_verify.link_up
    ok, why = probe()
    if not ok:
        time.sleep(0 if DRY_RUN else 20)
        ok, why = probe()
    check_side("link", not ok, why, mark, now,
               f"🔴 Exos DR: Mini link DOWN — the Studio can't reach the Mini (mini-dr) over the DR link ({why}).\n"
               f"Likely cause: the Mini rebooted after a power loss and is FileVault-locked. Fix: someone at Lizi's "
               f"unlocks the Mini (log in as exomac). Until then: no DR copies, no hot-state sync, no automatic failover.",
               "✅ Exos DR: Mini link is back up — DR copies and failover standby resumed.")
    vs = verify_state if verify_state is not None else dr_verify.read_state()
    vbad = bool(vs) and not vs.get("ok", True)
    check_side("checksum", vbad, f"mismatched: {(vs or {}).get('mismatched')}", mark, now,
               f"🔴 Exos DR: checksum verify FAILED on the Mini mirror — critical files differ from the Studio: "
               f"{(vs or {}).get('mismatched')}. The DR sentinel was NOT refreshed. Check logs/dr-backup.log.",
               "✅ Exos DR: checksum verify passing again.")
    return ok, vbad

def main():
    if "--selftest" in sys.argv[1:]:
        return selftest()
    force = "--force-alert" in sys.argv[1:]
    ok, reason = gate.is_healthy()
    mark = load_mark()
    now = time.time()
    link_ok, vbad = side_checks(mark, now)
    _fleet("ok" if (ok and link_ok and not vbad) else "alert",
           f"backup={'ok' if ok else reason}; link={'up' if link_ok else 'DOWN'}; checksum={'FAIL' if vbad else 'ok'}")

    if ok and not force:
        # recovered?
        if mark.get("state") == "alerted":
            if not DRY_RUN:
                gate.clear_pause()
            notify("✅ Exos DR backup RECOVERED — Studio→Mini backup is healthy again; "
                   "paused Studio-only tasks have auto-resumed.")
            mark.update({"state": "healthy", "since": now}); save_mark(mark)
            logline("recovered: pause cleared, resume note sent")
        else:
            logline(f"healthy — {reason}")
            save_mark(mark)
        return

    # NOT healthy -> enforce pause + alert (deduped)
    if not DRY_RUN:
        gate.set_pause(f"watchdog: {reason}")
    last = mark.get("last_alert_epoch", 0)
    already = mark.get("state") == "alerted"
    due_reminder = (now - last) > REMINDER_EVERY_H * 3600
    if force or (not already) or due_reminder:
        notify(f"🔴 Exos DR backup NOT HEALTHY — {reason}\n"
               f"Action taken: Studio-only / state-mutating tasks are PAUSED until a good backup lands "
               f"(read-only jobs keep running). They auto-resume on the next successful backup.\n"
               f"Check: `python3 scripts/backup_health_gate.py --status` and the last DR backup run "
               f"(`logs/dr-backup.log`).")
        mark.update({"state": "alerted", "last_alert_epoch": now, "reason": reason}); save_mark(mark)
        logline(f"ALERTED + PAUSED — {reason}")
    else:
        save_mark(mark)
        logline(f"still unhealthy ({reason}); alert suppressed (deduped, next reminder in "
                f"{REMINDER_EVERY_H}h)")

def selftest():
    """Replays the link-down / checksum-fail / recovery paths with fake probes. Sends nothing."""
    results = []
    def case(name, cond):
        results.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name)
    mark = {}; t = 1_000_000.0
    down = lambda: (False, "ssh rc=255 Connection timed out")
    up = lambda: (True, "link up")
    SENT.clear(); side_checks(mark, t, probe=down, verify_state={"ok": True})
    case("Mini locked/unreachable -> one 'link DOWN' alert", len(SENT) == 1 and "link DOWN" in SENT[0])
    SENT.clear(); side_checks(mark, t + 3600, probe=down, verify_state={"ok": True})
    case("still down 1h later -> deduped (no 2nd alert)", len(SENT) == 0)
    SENT.clear(); side_checks(mark, t + 25 * 3600, probe=down, verify_state={"ok": True})
    case("still down after 24h -> one reminder", len(SENT) == 1)
    SENT.clear(); side_checks(mark, t + 26 * 3600, probe=up, verify_state={"ok": True})
    case("link back -> one recovery note", len(SENT) == 1 and "back up" in SENT[0])
    flaky = iter([(False, "blip"), (True, "link up")])
    SENT.clear(); side_checks(mark, t + 27 * 3600, probe=lambda: next(flaky), verify_state={"ok": True})
    case("single failed probe then OK -> no alert (2-probe rule)", len(SENT) == 0)
    SENT.clear(); side_checks(mark, t + 28 * 3600, probe=up, verify_state={"ok": False, "mismatched": ["openclaw-config/secrets.json"]})
    case("checksum mismatch -> one checksum alert", len(SENT) == 1 and "checksum" in SENT[0])
    SENT.clear(); side_checks(mark, t + 29 * 3600, probe=up, verify_state={"ok": True})
    case("checksum ok again -> recovery note", len(SENT) == 1)
    n = sum(ok for _, ok in results)
    print(f"selftest {n}/{len(results)}")
    sys.exit(0 if n == len(results) else 1)

if __name__ == "__main__":
    main()
