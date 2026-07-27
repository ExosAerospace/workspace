#!/usr/bin/env python3
"""
Priority Inbox Watcher
======================
Polls the Proton Bridge INBOX (every ~10 min via launchd) and DMs Jon on Discord
the moment a NEW email arrives from a watched domain/sender OR carrying the [EXO]
subject tag. Fixes the gap where the 4x/day opportunity scanner silently drops
forwarded relationship emails (e.g. Cerberus).

Design notes:
- UID-based dedupe; first run establishes a baseline (no backlog blast).
- Never silently drops: every hit is appended to logs/priority-inbox-hits.jsonl
  BEFORE the Discord send, so a failed DM still leaves a durable record.
- Fail-quiet: never crash-loops launchd; errors go to the log and exit 0.
- Config (watchlist, tag, DM target) lives in config/priority-watcher.json.
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("priority-inbox")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gevent(_GRUN, "error", status="error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import imaplib, email, json, os, sys, shutil, subprocess, re
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr

WORKSPACE = "/Users/exomac/.openclaw/workspace"
CONFIG    = os.path.join(WORKSPACE, "config", "priority-watcher.json")
STATE     = os.path.join(WORKSPACE, "logs", "priority-watcher-state.json")
HITS      = os.path.join(WORKSPACE, "logs", "priority-inbox-hits.jsonl")
LOG       = os.path.join(WORKSPACE, "logs", "priority-watcher.log")
SECRETS   = os.path.expanduser("~/.openclaw/secrets.json")

IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER = "jquinnexo@pm.me"

OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"


def now_iso():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def logline(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"[{now_iso()}] {msg}\n")
    except Exception:
        pass


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_state(state):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE)


def get_imap_password():
    sec = load_json(SECRETS, {})
    pw = sec.get("protonmail_bridge_smtp_password")
    if not pw:
        logline("ERROR: no protonmail_bridge_smtp_password in secrets.json")
        sys.exit(0)
    return pw


def dec(s):
    if not s:
        return ""
    out = ""
    for t, enc in decode_header(s):
        out += t.decode(enc or "utf-8", "ignore") if isinstance(t, bytes) else t
    return out


def _subprocess_env():
    # launchd gives a minimal PATH; `openclaw` is a node script and needs `node`
    # discoverable. Prepend the node/openclaw bin dir (and mise shims) explicitly.
    env = os.environ.copy()
    extra = [os.path.dirname(OPENCLAW),
             "/Users/exomac/.local/share/mise/shims",
             "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra + [env.get("PATH", "")])
    return env


def post_discord(target, text, log_only=False):
    if log_only:
        return False
    try:
        r = subprocess.run(
            [OPENCLAW, "message", "send", "--channel", "discord",
             "--target", target, "-m", text],
            capture_output=True, text=True, timeout=60, env=_subprocess_env(),
        )
        if r.returncode != 0:
            logline(f"WARN: discord send rc={r.returncode}: {r.stderr[:200]}")
            return False
        return True
    except Exception as e:
        logline(f"WARN: discord send failed: {e}")
        return False


def body_snippet(msg, limit=400):
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    txt = part.get_payload(decode=True).decode("utf-8", "ignore")
                    break
            else:
                txt = ""
        else:
            txt = msg.get_payload(decode=True).decode("utf-8", "ignore")
    except Exception:
        txt = ""
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]


def match_reason(sender_addr, subject, cfg):
    s = sender_addr.lower()
    subj = (subject or "").lower()
    tag = cfg.get("subject_tag", "[EXO]").lower()
    if tag and tag in subj:
        return f"subject tag {cfg.get('subject_tag')}"
    for d in cfg.get("watch_domains", []):
        if d.lower() in s:
            return f"watched domain {d}"
    for snd in cfg.get("watch_senders", []):
        if snd.lower() in s:
            return f"watched sender {snd}"
    return None


def main():
    cfg = load_json(CONFIG, {})
    if not cfg:
        logline("ERROR: config missing/unreadable; aborting")
        sys.exit(0)
    pw = get_imap_password()
    state = load_json(STATE, {})
    last_uid = int(state.get("last_uid", 0))
    first_run = "last_uid" not in state

    try:
        m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
        m.starttls()
        m.login(EMAIL_USER, pw)
        m.select("INBOX")
    except Exception as e:
        logline(f"ERROR: IMAP connect/login failed: {e}")
        sys.exit(0)

    # Pull UIDs greater than last seen.
    typ, data = m.uid("search", None, f"UID {last_uid + 1}:*")
    uids = [int(x) for x in data[0].split()] if data and data[0] else []
    # UID n:* always returns at least the highest UID even if <= last_uid; filter.
    uids = [u for u in uids if u > last_uid]

    target = cfg.get("dm_target", "user:1501632195163590739")
    alerts = 0
    max_uid = last_uid

    for uid in sorted(uids):
        max_uid = max(max_uid, uid)
        typ, d = m.uid("fetch", str(uid), "(RFC822)")
        if not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        subject = dec(msg["Subject"])
        from_raw = dec(msg.get("From", ""))
        _, sender_addr = parseaddr(from_raw)
        date_hdr = dec(msg.get("Date", ""))

        reason = match_reason(sender_addr, subject, cfg)
        if not reason:
            continue

        # On first run, baseline only: record but do not alert on backlog.
        if first_run:
            logline(f"baseline (no alert) uid={uid} from={sender_addr} subj={subject[:60]!r}")
            continue

        snippet = body_snippet(msg)
        hit = {
            "ts": now_iso(), "uid": uid, "reason": reason,
            "from": from_raw, "sender": sender_addr,
            "subject": subject, "date": date_hdr, "snippet": snippet,
        }
        # Durable record FIRST (no-loss), then notify.
        try:
            with open(HITS, "a") as f:
                f.write(json.dumps(hit) + "\n")
        except Exception as e:
            logline(f"WARN: could not write hit log: {e}")

        text = (
            f"\U0001F4E5 **Priority email** ({reason})\n"
            f"**From:** {from_raw}\n"
            f"**Subject:** {subject}\n"
            f"**Date:** {date_hdr}\n\n"
            f"{snippet}\n\n"
            f"_Flagged by priority-inbox-watcher. Reply here to action it._"
        )
        ok = post_discord(target, text)
        logline(f"ALERT uid={uid} reason={reason!r} from={sender_addr} dm={'ok' if ok else 'FAILED-logged'}")
        alerts += 1

    state["last_uid"] = max_uid
    state["last_run"] = now_iso()
    save_state(state)
    try:
        m.logout()
    except Exception:
        pass

    if first_run:
        logline(f"first run: baseline set last_uid={max_uid}; future arrivals will alert")
    else:
        logline(f"run complete: {len(uids)} new, {alerts} alert(s)")


if __name__ == "__main__":
    main()
