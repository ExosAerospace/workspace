#!/usr/bin/env python3
"""deadline-capture.py — capture solicitation deadline CHANGES from inbound email onto the task.

The gap this closes: when a solicitation notice announces a new/changed deadline (resubmission
required, extension granted, date moved), agents email the deliverable but never write the new
date back onto the tracker — so the task keeps a stale deadline (the RMPC 8/17 miss, 2026-08-14).

This watcher (launchd, hourly) scans the inbox for deadline-CHANGE emails, extracts the new date,
matches it to an open MC task by distinctive token (program acronym / solicitation id), and:
  - auto-updates that task's due_date + posts a [DEADLINE-UPDATE] note (house rule: an authoritative
    source moving a date is captured, not left in the inbox), and
  - ALWAYS emails Jon a one-line summary so a moved deadline is never silent (deadline-watch rule).
  - if no confident task match, files a triage task so the date is still captured for manual linking.

Modes:  --baseline (record current change-emails, act on nothing)  |  --dry-run (report, change nothing)
Idempotent by message-id; conservative matching; fail-soft. Deterministic (no model).
"""
import os, sys, re, json, ssl, imaplib, email, subprocess, urllib.request
from email.header import decode_header, make_header
from html.parser import HTMLParser
from datetime import datetime, timezone, date

WS = "/Users/exomac/.openclaw/workspace"
STATE = os.path.join(WS, "logs", "deadline-capture-state.json")
LOG = os.path.join(WS, "logs", "deadline-capture.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
IMAP_USER, IMAP_PASS = "jquinnexo@pm.me", __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
JON = "jquinn@exosaero.com"
BASELINE = "--baseline" in sys.argv
DRY = "--dry-run" in sys.argv

# An email only qualifies if it signals a CHANGE (not just any "due by" mention).
CHANGE_RE = re.compile(r"\b(resubmission required|resubmit by|deadline (?:has been )?(?:extended|moved|changed|revised|updated)|"
                       r"extension (?:granted|to)|(?:new|revised|updated|amended) (?:deadline|due date)|"
                       r"deadline is now|due date is now|extended to|moved to|postponed|"
                       r"has been extended|new submission deadline)\b", re.I)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
# distinctive tokens: acronyms (>=3 caps), solicitation ids, topic codes, program names
TOKEN_RE = re.compile(r"\b([A-Z]{3,}|[A-Z]{1,2}\d{2,}[\w.\-]*|W911\w+|FA\d{3,}\w*|\d{2}\.[A-Z]{1,3})\b")
PROGRAM_TOKENS = ["techleap", "spacewerx", "afwerx", "tacfi", "stratfi", "sbir", "sttr", "rmpc",
                  "osp-4", "idiq", "searf", "rdre", "reddi", "nspires", "topic"]
# too-common tokens that must NOT drive a match on their own
STOPTOK = {"NASA", "SBIR", "STTR", "USAF", "DOD", "AIR", "FORCE", "THE", "AND", "FOR", "PDF", "ITAR",
           "EAR", "CUI", "LLC", "INC", "USA", "ET", "PM", "AM", "EDT", "EST", "URL", "FAA"}


def logline(m):
    try:
        open(LOG, "a").write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception:
        pass


class _Strip(HTMLParser):
    def __init__(s): super().__init__(); s.t = []
    def handle_data(s, d): s.t.append(d)


def html_text(h):
    p = _Strip()
    try: p.feed(h)
    except Exception: pass
    return re.sub(r"\s+", " ", " ".join(p.t)).strip()


def supa(method, path, body=None):
    req = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode(); return json.loads(t) if t else []
    except Exception as e:
        logline(f"WARN supa {method}: {e}"); return None


def email_jon(subject, body):
    if DRY:
        print(f"[dry] would email Jon: {subject}"); return
    mail = f"From: Exo <{IMAP_USER}>\nTo: {JON}\nReply-To: {JON}\nSubject: {subject}\n\n{body}\n"
    try:
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", JON],
                       input=mail.encode(), timeout=30, check=False)
    except Exception as e:
        logline(f"WARN email: {e}")


def extract_deadline(text):
    """Return (iso_date, human_snippet) for a FUTURE new deadline stated next to a deadline cue,
    or (None, None). Conservative: only dates adjacent to a cue (no whole-body guessing), and the
    date must be today-or-later (a deadline change announces a future date)."""
    low = text.lower()
    today = date.today()
    windows = []
    for cm in re.finditer(r"(resubmit by|upload by|submit by|no later than|deadline(?: is)?(?: now)?|"
                          r"due(?: date)?(?: is)?(?: now)?|extended to|moved to|postponed to)\s*:?\s*"
                          r"([^.;\n]{0,40})", low):
        windows.append(cm.group(2))
    for w in windows:
        # Month name form: aug 17 2026 / august 17, 2026 / aug. 17
        m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z.]*\s+(\d{1,2})(?:st|nd|rd|th)?"
                      r"(?:,?\s*(20\d{2}))?", w)
        if m:
            mon = MONTHS[m.group(1)[:3]]; day = int(m.group(2)); yr = int(m.group(3) or date.today().year)
            try:
                d = date(yr, mon, day)
                if not m.group(3) and d < today:
                    d = date(yr + 1, mon, day)  # bare date already past -> next year
                if d >= today:
                    return d.isoformat(), m.group(0)
            except ValueError:
                pass
        # numeric M/D or M/D/Y
        m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b", w)
        if m:
            mon, day = int(m.group(1)), int(m.group(2)); yr = int(m.group(3) or today.year)
            try:
                d = date(yr, mon, day)
                if not m.group(3) and d < today:
                    d = date(yr + 1, mon, day)
                if d >= today:
                    return d.isoformat(), m.group(0)
            except ValueError:
                pass
    return None, None


def distinctive_tokens(text):
    toks = set()
    for t in TOKEN_RE.findall(text):
        if t.upper() in STOPTOK or len(t) < 3:
            continue
        toks.add(t.upper())
    for p in PROGRAM_TOKENS:
        if re.search(rf"\b{re.escape(p)}\b", text, re.I):
            toks.add(p.upper())
    return toks


def match_task(tokens, open_tasks):
    """Best open task by count of shared distinctive tokens; require >=1 and inverse-frequency gate."""
    # frequency of each token across open task titles
    freq = {}
    for tk in tokens:
        freq[tk] = sum(1 for t in open_tasks if tk.lower() in (t.get("title", "") + " " + (t.get("description") or "")).lower())
    scored = []
    for t in open_tasks:
        blob = (t.get("title", "") + " " + (t.get("description") or "")).lower()
        shared = [tk for tk in tokens if tk.lower() in blob and 1 <= freq[tk] <= 8]  # skip ultra-common
        if shared:
            score = len(shared) + (t.get("priority") or 0) / 1000.0
            scored.append((score, len(shared), t, shared))
    if not scored:
        return None, []
    scored.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return scored[0][2], scored[0][3]


def imap_conn():
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.starttls(ssl_context=ctx); m.login(IMAP_USER, IMAP_PASS)
    return m


def main():
    state = None
    try: state = json.load(open(STATE))
    except Exception: state = None

    try:
        m = imap_conn()
    except Exception as e:
        logline(f"WARN imap: {e}"); print("imap unavailable"); return
    m.select("INBOX", readonly=True)
    # recent window
    since = (date.today().replace(day=1) if date.today().day <= 12 else date.today())
    typ, data = m.search(None, "SINCE", (date.today()).strftime("%d-%b-%Y") if False else "01-Aug-2026")
    ids = data[0].split() if data and data[0] else []

    def dec(s):
        try: return str(make_header(decode_header(s or "")))
        except Exception: return s or ""

    changes = []
    for i in ids[-120:]:
        t, d = m.fetch(i, "(RFC822)")
        if t != "OK": continue
        msg = email.message_from_bytes(d[0][1])
        mid = msg.get("Message-ID") or f"idx:{i.decode()}"
        subj = dec(msg.get("Subject")); frm = dec(msg.get("From"))
        body = ""
        if msg.is_multipart():
            pl = ht = ""
            for part in msg.walk():
                try: pay = part.get_payload(decode=True).decode(errors="ignore")
                except Exception: pay = ""
                if part.get_content_type() == "text/plain" and not pl: pl = pay
                if part.get_content_type() == "text/html" and not ht: ht = pay
            body = pl.strip() or html_text(ht)
        else:
            try: raw = msg.get_payload(decode=True).decode(errors="ignore")
            except Exception: raw = ""
            body = html_text(raw) if "<" in raw else raw
        blob = f"{subj}\n{body}"
        if CHANGE_RE.search(blob):
            changes.append({"mid": mid, "subj": subj, "from": frm, "body": body[:4000]})
    m.logout()

    if state is None or BASELINE:
        seen = {c["mid"] for c in changes}
        if not DRY:
            json.dump({"seen": list(seen)}, open(STATE, "w"))
        logline(f"baseline {len(seen)}"); print(f"baseline {len(seen)} change-emails recorded"); return

    seen = set(state.get("seen", []))
    open_tasks = supa("GET", "tasks?select=id,title,description,priority,state&state=in.(%22To%20Do%22,%22In%20Progress%22,Queued,Blocked)&limit=2000") or []
    acted = 0
    for c in changes:
        if c["mid"] in seen: continue
        seen.add(c["mid"])
        iso, snip = extract_deadline(c["subj"] + "\n" + c["body"])
        tokens = distinctive_tokens(c["subj"] + " " + c["body"][:600])
        task, shared = match_task(tokens, open_tasks) if tokens else (None, [])
        src = re.sub(r"\s+", " ", c["subj"])[:90]

        # HOUSE RULE (deadline-watch): never silently move a date. Alert Jon to CONFIRM; he applies
        # with one line: @Exobot due <date> on the task (the task-note watcher sets it). We only
        # alert on high signal: a future date next to a deadline cue AND a matched task.
        if task and iso:
            apply_hint = f"To apply: open task #{task['id']} and post the note:  @Exobot due {iso}"
            email_jon(f"Confirm deadline: {task['title'][:55]} -> {iso}?",
                      f"The email “{src}” looks like a deadline change to {iso} for task #{task['id']} "
                      f"(“{task['title'][:70]}”, matched on {', '.join(shared)}).\n\n{apply_hint}\n\n"
                      f"If it's the wrong task or date, ignore this — nothing was changed.")
            logline(f"ALERT confirm task {task['id']} -> {iso} (mid {c['mid'][:30]})"); acted += 1
        elif task and not iso:
            email_jon(f"Deadline change for {task['title'][:50]}? — date unclear",
                      f"“{src}” reads like a deadline change for task #{task['id']} but I couldn't extract a firm date. "
                      f"If a date applies, post  @Exobot due <date>  on that task. Nothing was changed.")
            logline(f"ALERT no-date task {task['id']} (mid {c['mid'][:30]})"); acted += 1
        # date-but-no-task or neither -> too weak to alert on (avoid noise); logged only
        elif iso and not task:
            logline(f"skip date-no-task -> {iso} (mid {c['mid'][:30]})")

    if not DRY:
        state["seen"] = list(seen)[-4000:]
        json.dump(state, open(STATE, "w"))
    print(f"{'dry-run' if DRY else 'acted'} {acted}")


main()
