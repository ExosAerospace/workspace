#!/usr/bin/env python3
"""
mail_bridge_guard.py — deterministic exo3 guard for the Proton Bridge login path (r2-launchd-residuals, 2026-09-30).

Root cause it guards (9/28-9/29): after the Mini->Studio cutover the Studio's Bridge has its own password
(~/.config/exos/bridge-studio.pw, used by msmtp), but ~/.openclaw/secrets.json
protonmail_bridge_smtp_password still held the Mini's value. Every IMAP/SMTP script (27 use imaplib)
got Bridge "no such user"; the burst of failed logins then tripped Bridge's limiter, so the rest got
"too many login attempts". Fixed by syncing secrets.json at ~07:40 CDT 9/29 — errors stopped that minute
with no schedule change, so parallel polling is an amplifier, not the cause.

Read-only. Never logs in, never edits a secret, never prints a secret value (hashes compared in memory).
Wired into agent_eval.py (hourly) as the "mail-bridge" checks; also runnable by hand.

Checks
  1. PASSWORD DRIFT (FAIL): SHA-256(secrets.json protonmail_bridge_smtp_password) !=
     SHA-256(bridge-studio.pw). Skipped (OK) on a box without bridge-studio.pw (the Mini).
  2. AUTH STORM (FAIL): in the last 2h of logs/runs/*.jsonl, >= 3 runs across >= 2 labels whose
     stderr tail carries a Bridge auth error ("no such user" / "too many login attempts" /
     "Invalid login" / AUTHENTICATIONFAILED). One job failing once is a blip (survey-ingest 04:05 9/29).

Remedy is a human step (sync the value, then restart MC once, which reads it at startup) — see memory
reference_bridge_password_studio. This guard only raises it.

Usage:
  mail_bridge_guard.py             # print findings, exit 1 on any FAIL
  mail_bridge_guard.py --selftest  # fixtures only (replays the 9/29 state)
"""
import datetime, glob, hashlib, json, os, sys

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STUDIO_PW = os.path.expanduser("~/.config/exos/bridge-studio.pw")
RUNS = os.path.join(WS, "logs", "runs")
SECRET_KEY = "protonmail_bridge_smtp_password"
AUTH_ERRORS = ("no such user", "too many login attempts", "invalid login", "authenticationfailed")
STORM_WINDOW_S = 2 * 3600
STORM_MIN_RUNS, STORM_MIN_LABELS = 3, 2
LABEL = "mail-bridge"


def _h(v):
    return hashlib.sha256((v or "").strip().encode()).hexdigest()


def pw_drift(secrets_path=SECRETS, studio_path=STUDIO_PW):
    """None if in sync / not applicable, else a reason string (names only)."""
    if not os.path.exists(studio_path):
        return None
    try:
        s = json.load(open(secrets_path)).get(SECRET_KEY)
    except Exception as e:
        return f"secrets.json unreadable ({type(e).__name__})"
    if not s:
        return f"secrets.json has no {SECRET_KEY}"
    if _h(s) != _h(open(studio_path).read()):
        return (f"secrets.json {SECRET_KEY} != ~/.config/exos/bridge-studio.pw — every IMAP/SMTP job will get "
                "Bridge 'no such user' then 'too many login attempts'; sync the value, restart MC once")
    return None


def _ts(s):
    try:
        return datetime.datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def auth_storm(records, now):
    """records: iterable of run_logged dicts. Returns (n_runs, sorted labels) or None."""
    hits = []
    for r in records:
        t = _ts(r.get("start") or r.get("end") or "")
        if t is None or now - t > STORM_WINDOW_S:
            continue
        tail = " ".join(r.get("stderr_tail") or []).lower()
        if any(e in tail for e in AUTH_ERRORS):
            hits.append(r.get("label", "?"))
    labels = sorted(set(hits))
    if len(hits) >= STORM_MIN_RUNS and len(labels) >= STORM_MIN_LABELS:
        return len(hits), labels
    return None


def recent_runs(now):
    out = []
    for d in {datetime.date.fromtimestamp(now), datetime.date.fromtimestamp(now - STORM_WINDOW_S)}:
        f = os.path.join(RUNS, f"{d.isoformat()}.jsonl")
        if not os.path.exists(f):
            continue
        for line in open(f, errors="replace"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def check(now=None):
    """[(label, status, why)] — same shape as cron_hygiene.check(); empty list = all OK."""
    now = now or datetime.datetime.now().timestamp()
    found = []
    why = pw_drift()
    if why:
        found.append((LABEL, "FAIL", "password drift: " + why))
    storm = auth_storm(recent_runs(now), now)
    if storm:
        n, labels = storm
        found.append((LABEL, "FAIL", f"Bridge auth storm: {n} runs / {len(labels)} jobs in 2h ({', '.join(labels[:6])})"))
    return found


def selftest():
    import tempfile
    n = 0
    with tempfile.TemporaryDirectory() as td:
        sp, pp = os.path.join(td, "secrets.json"), os.path.join(td, "bridge-studio.pw")
        json.dump({SECRET_KEY: "fixture-studio-value"}, open(sp, "w"))
        assert pw_drift(sp, pp) is None; n += 1                     # no studio file (Mini) -> n/a
        open(pp, "w").write("fixture-studio-value\n")
        assert pw_drift(sp, pp) is None; n += 1                     # in sync (trailing newline ignored)
        json.dump({SECRET_KEY: "fixture-mini-value"}, open(sp, "w"))
        r = pw_drift(sp, pp)
        assert r and "fixture" not in r; n += 2                     # 9/29 replay: drift FAILs, value never echoed
        json.dump({}, open(sp, "w"))
        assert "no " + SECRET_KEY in pw_drift(sp, pp); n += 1
    now = datetime.datetime(2026, 9, 29, 7, 40).astimezone().timestamp()
    iso = lambda m: datetime.datetime.fromtimestamp(now - m * 60).astimezone().isoformat(timespec="seconds")
    storm = [  # replay of logs/runs/2026-09-29.jsonl 07:00-07:36
        {"label": "com.exos.forwarded-mail-watch", "start": iso(9), "stderr_tail": ["imaplib.error: b'no such user'"]},
        {"label": "com.exos.doc-manager", "start": iso(5), "stderr_tail": ["imaplib.error: b'too many login attempts'"]},
        {"label": "com.exos.capstone-email-capture", "start": iso(6), "stderr_tail": ["imaplib.error: b'no such user'"]},
    ]
    s = auth_storm(storm, now)
    assert s and s[0] == 3 and len(s[1]) == 3; n += 1
    assert auth_storm(storm[:1], now) is None; n += 1                # single blip (survey-ingest 04:05)
    assert auth_storm([dict(r, label=".".join(["com", "exos", "fixture-loop"])) for r in storm], now) is None; n += 1  # one job looping
    assert auth_storm([dict(r, start=iso(200)) for r in storm], now) is None; n += 1      # outside window
    assert auth_storm([dict(r, stderr_tail=["Traceback", "KeyError"]) for r in storm], now) is None; n += 1
    assert isinstance(check(), list); n += 1
    print(f"mail_bridge_guard selftest: {n}/{n} pass")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    found = check()
    if not found:
        print("mail_bridge_guard: OK (bridge password in sync, no auth storm in 2h)")
        return 0
    for label, status, why in found:
        print(f"{status}: {label} — {why}")
    return 1 if any(s == "FAIL" for _, s, _ in found) else 0


if __name__ == "__main__":
    sys.exit(main())
