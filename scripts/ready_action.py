#!/usr/bin/env python3
"""
ready_action.py — the delivery primitive for Jon-gated actions.

Standing rule (feedback_send_or_mc_task_or_dead): a draft in a file is DEAD. When an
action is ready and gated on Jon, it must (a) land in his inbox as a ready-to-send, and
(b) open a Mission Control task. Never cite a file path.

deliver(...) does both, idempotently (keyed by `key` + content hash), so calling it every
cron cycle does not spam Jon or duplicate tasks. Import it, or run as CLI.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import os, sys, json, ssl, hashlib, smtplib, urllib.request, urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.join(WS, "logs", "ready-actions-dispatched.json")
LOG = os.path.join(WS, "logs", "ready-action.log")
# Sent registry (built by sent-loop-closer.py from Jon's BCC'd Proton copies): recipients he
# has ALREADY emailed from Outlook. A ready-to-send whose recipient is here is redundant —
# don't hand Jon a "ready to send" for mail he already sent ("many already sent" complaint).
SENT_REGISTRY = os.path.join(WS, "logs", "outreach-sent-registry.json")

# Email (Proton bridge, same as the other senders)
SMTP_HOST, SMTP_PORT = "127.0.0.1", 1025
SMTP_USER, SMTP_PASS = "jquinnexo@pm.me", "SPqYBivj98-jyF3RujLKxA"
JON = "jquinn@exosaero.com"

# ── Route deliverables to the RESPONSIBLE PARTY, not always Jon (Jon directive 2026-09-08) ──
# Map an owner name/alias to a work email. Sourced from the ERP employee table + explicit
# aliases (Lizi=Elizabeth Quinn, etc.). Unknown/blank/Jon -> Jon (safe fallback).
_TEAM_ALIASES = {
    "jon": JON, "john": JON, "john quinn": JON, "jquinn": JON, "jon+exo": JON, "exo": JON, "": JON,
    "lizi": "lquinn@exosaero.com", "liz": "lquinn@exosaero.com", "lizi quinn": "lquinn@exosaero.com",
    "elizabeth quinn": "lquinn@exosaero.com",
    "phil": "peaton@exosaero.com", "phil eaton": "peaton@exosaero.com", "phillip eaton": "peaton@exosaero.com",
    "steve": "snorsworthy@exosaero.com", "steve norsworthy": "snorsworthy@exosaero.com",
    "steven norsworthy": "snorsworthy@exosaero.com",
    "toshi": "toshihisa@exosaero.com", "toshihisa kumazawa": "toshihisa@exosaero.com",
    "kyle": "kballard@exosaero.com", "kyle ballard": "kballard@exosaero.com",
    "neil": "nmilburn@exosaero.com", "neil milburn": "nmilburn@exosaero.com",
}
_TEAM_CACHE = None
def resolve_owner_email(owner):
    """Owner name/alias -> work email. Unknown/blank/Jon -> Jon (safe fallback)."""
    o = str(owner or "").strip().lower()
    if o in _TEAM_ALIASES:
        return _TEAM_ALIASES[o]
    global _TEAM_CACHE
    if _TEAM_CACHE is None:
        _TEAM_CACHE = {}
        try:
            import sqlite3
            db = sqlite3.connect(os.path.expanduser("~/.openclaw/workspace/erp-foundation/mc.db"))
            for full, rj in db.execute("SELECT full_name, raw_json FROM employee WHERE employment_status='Active'"):
                try:
                    em = (json.loads(rj) or {}).get("email")
                except Exception:
                    em = None
                if full and em:
                    _TEAM_CACHE[full.strip().lower()] = em
            db.close()
        except Exception:
            pass
    if o in _TEAM_CACHE:
        return _TEAM_CACHE[o]
    first = o.split()[0] if o.split() else o
    hits = {em for nm, em in _TEAM_CACHE.items() if nm.split() and nm.split()[0] == first}
    return next(iter(hits)) if len(hits) == 1 else JON

# Supabase MC board
SB_URL = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
def _sb_key():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def _log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")


def _load_state():
    try: return json.load(open(STATE))
    except Exception: return {}

def _save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w"), indent=2)


def _sb(method, path, payload=None):
    key = _sb_key()
    h = {"apikey": key, "Authorization": "Bearer " + key,
         "Content-Type": "application/json", "Prefer": "return=representation"}
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(SB_URL + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
        body = r.read().decode()
        return json.loads(body) if body else []


def create_task(title, description, category="BD", priority=70, owner="Jon", source="capture-agent"):
    """Create an MC task, deduped by exact title. Returns task id or None."""
    try:
        q = f"tasks?title=eq.{urllib.parse.quote(title)}&select=id&limit=1"
        existing = _sb("GET", q)
        if isinstance(existing, list) and existing:
            return existing[0].get("id")
    except Exception as e:
        _log(f"task dedup check failed: {e}")
    task = {"title": title, "description": description, "state": "To Do",
            "category": category, "priority": priority, "owner": owner, "source": source}
    try:
        res = _sb("POST", "tasks", task)
        tid = res[0].get("id") if isinstance(res, list) and res else None
        _log(f"MC task created: {title} -> {tid}")
        return tid
    except Exception as e:
        _log(f"MC task create FAILED ({title}): {e}")
        return None


def email_ready(subject, body, to=JON):
    msg = MIMEMultipart()
    # Reply-To the responsible party so the thread stays with them (Jon oversight via cc-free default);
    # falls back to Jon when the recipient IS Jon.
    msg["From"] = f"Exo <{SMTP_USER}>"; msg["Reply-To"] = to or JON
    msg["To"] = to; msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo(); s.starttls(); s.ehlo(); s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, [to], msg.as_string())
    _log(f"emailed ready-to-send to {to}: {subject}")


import re as _re
# Volatile aging counters like "(36+ days READY)", "(12 days ready)", "(day 40)" bump every
# cron cycle. If they leak into the dedup hash, Jon gets re-nagged on the SAME ready-to-send
# every day it ages — exactly the "stop asking me to send this" complaint. Strip them before
# hashing so aging alone can NEVER re-deliver; only a real content change re-delivers.
_AGE_RE = _re.compile(r"\(\s*(?:day\s+\d+|\d+\+?\s*days?\b[^)]*)\)", _re.IGNORECASE)
# Bare (non-parenthesized) aging counters like "9 days", "8 days dark", "6 days since
# first ask", "12 days post-panel", "~2 wks post-approval" also bump every cron cycle and
# were leaking into the hash (parenthesized form above never caught them). Strip the
# numeric age token itself so only the count changing can NEVER re-deliver; the stable
# trailing words ("dark", "post-panel") are left intact and don't move between cycles.
_AGE_BARE_RE = _re.compile(r"~?\d+\+?\s*(?:days?|wks?|weeks?|hrs?|hours?|mos?|months?)\b", _re.IGNORECASE)
def _dedup_norm(*parts):
    s = "\n".join(p or "" for p in parts)
    s = _AGE_RE.sub("", s)
    s = _AGE_BARE_RE.sub("", s)
    return _re.sub(r"\s+", " ", s).strip()


# Meeting-duration guardrail (feedback_meeting_durations): calendar slots are ONLY 15/30/60 min.
# Any non-slot duration in outgoing ready-to-send copy is snapped to the nearest allowed slot so
# no "20 minutes"-style ask ever leaves, regardless of what a model wrote.
_DUR_MAP = {"10": "15", "20": "15", "25": "30", "40": "30", "45": "30", "50": "60", "90": "60"}
def scrub_durations(text):
    if not text:
        return text
    bad = "|".join(_DUR_MAP)
    # hyphenated adjective form first ("20-minute"/"20-min" -> "15-minute"), then the noun form
    text = _re.sub(r"\b(" + bad + r")-min(?:ute)?s?\b", lambda m: _DUR_MAP[m.group(1)] + "-minute", text)
    text = _re.sub(r"\b(" + bad + r")\s?min(?:ute)?s?\b", lambda m: _DUR_MAP[m.group(1)] + " minutes", text)
    return text


# Per-key cooldown (2026-08-10 flood fix). Content-hash dedup alone is defeated by variant
# churn: the SAME pursuit re-emails whenever a cron model rewords the copy (v1/v2/v3
# escalation series — the NIH-MG RFI went out ~5x this way, each reworded, each slipping the
# hash). Once a key has emailed Jon, it may NOT email again for COOLDOWN_DAYS regardless of
# how the copy changes. We deliberately do NOT store the new hash while suppressing, so after
# the window the latest copy goes out exactly once. Net: at most one email per key per window,
# always the freshest content. A brand-new key (no prev) is never gated. MC task is untouched.
COOLDOWN_DAYS = float(os.environ.get("READY_ACTION_COOLDOWN_DAYS", "4"))

_RA_EMAIL_RE = _re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RA_INTERNAL = _re.compile(r"(exosaero\.com|jquinnexo@|@pm\.me|@proton\.me|noreply|no-reply)", _re.I)
# Gov / manual-send ready-to-sends route TO Jon (to: jquinn@exosaero.com) and carry the REAL
# external recipient inside the body, under a "SEND TO:" header block ("To: andrew.nelson@...").
# Checking only the `to:` field matched Jon's own (internal) address, so the already-sent guard
# NEVER fired for these — they re-nagged forever no matter how many times Jon actually sent them
# (Nelson/Utah flood, 2026-08-26). Pull the true "To:" recipient out of the body so the registry
# match works for the manual-send class too.
_RA_BODY_TO_RE = _re.compile(r"^\s*to\s*:\s*(.+)$", _re.I | _re.M)

def _body_primary_recipients(body):
    """External 'To:' recipients declared inside a ready-to-send body's SEND TO block."""
    out = []
    if not body:
        return out
    for line in _RA_BODY_TO_RE.findall(body):
        for e in _RA_EMAIL_RE.findall(line):
            el = e.lower()
            if not _RA_INTERNAL.search(el):
                out.append(el)
    return out

def _already_sent_recipient(to_line, body=""):
    """Return the first real recipient Jon has already emailed, else None. Checks the `to:`
    field AND the body's SEND TO block (gov/manual-send items address Jon, recipient in body).
    Disabled by env READY_ACTION_SKIP_SENT=0."""
    if os.environ.get("READY_ACTION_SKIP_SENT", "1") == "0":
        return None
    try:
        reg = {k.lower() for k in json.load(open(SENT_REGISTRY)).keys()}
    except Exception:
        return None
    cands = [e.lower() for e in _RA_EMAIL_RE.findall(to_line or "")]
    cands += _body_primary_recipients(body)
    for el in cands:
        if not _RA_INTERNAL.search(el) and el in reg:
            return el
    return None


def _emailed_recently(prev):
    if not prev or not prev.get("emailed_at"):
        return False
    try:
        last = datetime.strptime(prev["emailed_at"], "%Y-%m-%d %H:%M")
    except Exception:
        return False
    return (datetime.now() - last) < timedelta(days=COOLDOWN_DAYS)


def deliver(key, subject, body, to_line="", cc_line="", task_title=None,
            category="BD", priority=75, do_email=True, do_mc=True, owner="Jon", to=None):
    """Idempotent: emails Jon the ready-to-send + opens an MC task. Re-running with the
    same key+content is a no-op. Changed content re-delivers, but at most once per
    COOLDOWN_DAYS per key (variant-churn guard). Returns a result dict. Aging day-counters
    are stripped before hashing so a stale item never re-nags on age."""
    subject = scrub_durations(subject); body = scrub_durations(body); task_title = scrub_durations(task_title)
    # Normalize versioned/escalation keys onto ONE pursuit key. Generators emit -v2/-v3/-v4
    # (firefly-clps v1..v4, ravee-...-val v1..v2, entx-...-nudge v1..v2) — each was a distinct
    # key, so each re-emailed AND opened a new MC task. Collapsing to the base means all versions
    # share one cooldown slot and REUSE the first version's task_id (no new task per version).
    key = _re.sub(r"(?:[-_]v\d+)+$", "", key)
    st = _load_state()
    h = hashlib.sha256(_dedup_norm(subject, body, to_line, task_title).encode()).hexdigest()[:16]
    prev = st.get(key)
    if prev and prev.get("hash") == h:
        return {"key": key, "skipped": True, "task_id": prev.get("task_id")}
    # Jon already sent this outreach from Outlook (registry match on recipient): don't hand him a
    # redundant ready-to-send, no matter how the copy is reworded. Checked on every call so a
    # versioned/escalation variant can't slip past. Toggle with READY_ACTION_SKIP_SENT=0.
    if do_email:
        already = _already_sent_recipient(to_line, body)
        if already:
            _log(f"skip ready-to-send ({key}); Jon already sent to {already}")
            st[key] = {"hash": h, "task_id": prev.get("task_id") if prev else None,
                       "emailed_at": prev.get("emailed_at") if prev else None,
                       "skipped_already_sent": already}
            _save_state(st)
            return {"key": key, "skipped": True, "reason": "already-sent", "recipient": already}
    # Content changed but we already emailed this key inside the cooldown window: suppress the
    # re-send (do NOT persist the new hash, so the latest copy still goes out once cooldown ends).
    if prev and do_email and _emailed_recently(prev):
        _log(f"cooldown-suppressed re-send ({key}); {COOLDOWN_DAYS}d window not elapsed")
        return {"key": key, "skipped": True, "reason": "cooldown", "task_id": prev.get("task_id")}

    # Route the ready-to-send to the RESPONSIBLE PARTY (task owner), not always Jon.
    # `to` override wins; otherwise resolve the owner to their work email; unknown/Jon -> Jon.
    recipient = to or resolve_owner_email(owner)

    # Compose the inbox email: recipients header block + the ready-to-send body
    hdr = ""
    if to_line: hdr += f"TO: {to_line}\n"
    if cc_line: hdr += f"CC: {cc_line}\n"
    hdr += f"SUBJECT: {subject}\n"
    inbox_subject = f"[READY TO SEND] {task_title or subject}"
    inbox_body = ("Ready-to-send below — you are the responsible owner. Copy/forward from your mail "
                  "(external / gov contacts send from you; loop Jon only if it needs his sign-off).\n\n"
                  + hdr + "\n" + body)

    emailed = False
    if do_email:
        try:
            email_ready(inbox_subject, inbox_body, to=recipient); emailed = True
        except Exception as e:
            _log(f"email FAILED ({key}): {e}")

    task_id = prev.get("task_id") if prev else None
    if do_mc and not task_id:
        desc = (f"Ready-to-send delivered to {recipient} {datetime.now():%Y-%m-%d %H:%M}.\n\n"
                + hdr + "\n" + body[:1500])
        task_id = create_task(task_title or subject, desc, category=category, priority=priority, owner=owner)

    st[key] = {"hash": h, "task_id": task_id, "emailed_at": f"{datetime.now():%Y-%m-%d %H:%M}"}
    _save_state(st)
    return {"key": key, "skipped": False, "emailed": emailed, "task_id": task_id}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--to", default="")
    ap.add_argument("--cc", default="")
    ap.add_argument("--task-title", default=None)
    ap.add_argument("--category", default="BD")
    ap.add_argument("--priority", type=int, default=75)
    ap.add_argument("--no-email", action="store_true")
    ap.add_argument("--no-mc", action="store_true")
    a = ap.parse_args()
    body = open(a.body_file, encoding="utf-8").read()
    out = deliver(a.key, a.subject, body, a.to, a.cc, a.task_title, a.category,
                  a.priority, do_email=not a.no_email, do_mc=not a.no_mc)
    print(json.dumps(out, indent=2))
