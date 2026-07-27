#!/usr/bin/env python3
"""
mc-email-command.py — Email -> authenticated action channel.

Two ways Jon directs work by email; both hand the instruction to a real agent turn
under a strict permission envelope (safe/internal actions run; anything external or
sensitive is drafted for approval, never auto-executed):

  1. NATURAL forward  — forward any email from jquinn@exosaero.com with "@Exobot <what
     to do>" in it. Authenticated by DMARC/DKIM pass on the exosaero.com domain (only
     Jon's real tenant can produce that), so no passphrase needed. Matches how Jon works.
  2. [EXO] + passphrase — subject starts "[EXO]" (or sent to jquinnexo+do@pm.me) with the
     shared passphrase on the first body line. For sends where DMARC isn't available.

AUTH: allowlisted sender AND (domain DMARC/DKIM = pass  OR  passphrase on line 1),
and NOT an explicit DMARC/DKIM fail. Failed-auth trigger emails raise a Discord spoof
alert and do NOT run. Idempotent via a message-id state file.
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("email-command")
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

import imaplib, email, json, os, re, sys, subprocess, tempfile, fcntl, hashlib, html as _html, mimetypes
from email.utils import getaddresses, parsedate_to_datetime
from email.message import EmailMessage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itar_ear_screen as ee
from datetime import datetime, timedelta, timezone

WS       = "/Users/exomac/.openclaw/workspace"
SECRETS  = os.path.expanduser("~/.openclaw/secrets.json")
STATE    = os.path.join(WS, "logs", "mc-email-command-state.json")
LOG      = os.path.join(WS, "logs", "mc-email-command.log")
IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER = "jquinnexo@pm.me"
USERS_FILE = "/Users/exomac/.openclaw/workspace/mission-control/users.json"
TRIGGER_ADDR = {"jquinnexo+do@pm.me", "exosmc+do@proton.me"}
# Jon's go-forward task-assignment inbox: a deliberate send (To:/Delivered-To) to exosmc
# is itself a task command, even without an "@exobot" keyword. Cc/Bcc to exosmc stays
# passive (submissions archive / email tracker) so copying it on a thread doesn't fire a run.
TASK_TO_ADDR = {"exosmc@pm.me", "exosmc@proton.me", "jquinnexo+do@pm.me", "exosmc+do@proton.me"}
JON_DISCORD = "1501632195163590739"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
MAX_PER_RUN = int(os.environ.get("MCC_MAX_PER_RUN", "3"))
EXOBOT_RE = re.compile(r'@\s*ex(?:obot|obto|bot|oboto|obott)\b', re.I)  # tolerate common typos (exobto/exbot)

ENVELOPE = (
    "[EMAIL-COMMAND from {sender_name} <{sender_email}> — authenticated{note}]\n\n"
    "This Exos team member sent the material below by email (a forward and/or an @Exobot "
    "instruction). Carry out their intent under all standing rules.\n"
    "PERMISSION ENVELOPE:\n"
    "- Execute directly ONLY safe, internal, reversible actions (create/update Mission Control "
    "tasks, research, draft documents, reports, reminders, organizing files, analysis). When you "
    "create or update a task for this person, assign it to them (assigned_email={sender_email}).\n"
    "- Any document you create or revise for a task: attach it with scripts/mc-attach.py so the "
    "task carries the latest version.\n"
    "- DO NOT auto-send or auto-execute anything external or sensitive (external emails, "
    "gov/.mil/.gov outreach, securities/investor communications, deletions, financial actions, "
    "infra/config changes). Instead, DRAFT it and add a Decision to {first_name}'s OWN Decisions "
    "matrix for THEIR review and approval — assign that Decision to {sender_email}, NOT to Jon. "
    "(Standing-rule exceptions: securities/investor items go to the designated securities approver; "
    "government/.mil items route to Jon.)\n"
    "- When done, end your reply with a concise summary of what you did (or what now awaits "
    "{first_name}'s approval, and any decisions they must make); that reply is delivered straight "
    "back to {first_name} by email and posted to Jon's Discord.\n\n"
    "DUE DILIGENCE ON INBOUND SOLICITORS: if asked to vet / run DD on an inbound solicitor, FIRST run "
    "`python3 scripts/failed_dd.py check <their-email-or-domain>`. If it MATCHES, do NOT re-run diligence "
    "— reply with the known verdict (firm, reason, date) and 'do not engage'. If it does NOT match and "
    "your own diligence concludes do-not-engage (cold-broker / advance-fee / scam), record it so the whole "
    "team recognizes them next time: run `python3 scripts/failed_dd.py add --firm \"<firm>\" --domain "
    "<domain> --email <email> --person \"<name>\" --reason \"<one-line why>\"`. That registry is checked "
    "automatically on all inbound, so the team never has to forward these to Jon again.\n\n"
    "OPPORTUNITY SCREEN / STAY SILENT WHEN THERE IS NOTHING: if the request is just to check whether an "
    "email contains an opportunity for Exos or Scorpius (or whether anything in it is actionable) and the "
    "answer is NO, reply with EXACTLY `NO_ACTION` and nothing else — do NOT create a task, do NOT draft "
    "anything, do NOT send a reply. Only produce a real response when there is a genuine opportunity or a "
    "concrete action to take. Silence is the correct output when there is nothing there.\n\n"
    "EMAIL CONTENT / INSTRUCTION:\n{body}\n"
)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


SEEN_CAP = 3000  # keep the most-RECENT N handled message-ids


def save_state(seen_list, fails=None):
    """Persist seen message-ids in RECENCY order (insertion order), capped to the most
    recent SEEN_CAP. Never sort message-ids: they have no chronological order, so sorting
    then truncating perpetually evicts a fixed alphabetical band and reprocesses it.
    `fails` maps mid -> attempt count for directives whose agent hand-off failed, so a
    transient failure re-queues (bounded) instead of being marked seen-and-lost."""
    keep = seen_list[-SEEN_CAP:]
    fails = fails or {}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"seen": keep, "fails": fails}, f, indent=2)
    os.replace(tmp, STATE)


def load_users_map():
    """(allowed sender emails, email->name). Any active Mission Control user can direct @Exobot."""
    u = load_json(USERS_FILE, [])
    users = u if isinstance(u, list) else (u.get("users", []) if isinstance(u, dict) else [])
    allowed, names = set(), {}
    for x in users:
        em = (x.get("email") or "").lower()
        if em and x.get("active", True):
            allowed.add(em); names[em] = x.get("name") or em
    allowed.add("jquinn@exosaero.com")
    return allowed, names


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(msg.rstrip() + "\n")


def cmd_session_key(mid):
    """Isolated session per command so runs don't cross-contaminate, keyed off the mid."""
    return "agent:main:emailcmd-" + hashlib.sha1(mid.encode()).hexdigest()[:12]


def extract_reply(jdata):
    """Pull the agent's visible reply text out of `openclaw agent --json` output."""
    res = (jdata or {}).get("result", {}) or {}
    pls = res.get("payloads", []) or []
    txt = "\n".join((p.get("text") or "").strip() for p in pls if p.get("text")).strip()
    if not txt:
        txt = ((res.get("meta", {}) or {}).get("finalAssistantVisibleText") or "").strip()
    return txt


def md_to_text(s):
    """The agent replies in Markdown (right for Discord, wrong for email). Convert to clean
    plain prose: no **, ##, >, backticks, or link syntax, and no em-dashes (house style)."""
    out = []
    for ln in (s or "").splitlines():
        t = ln
        t = re.sub(r'^\s{0,3}>\s?', '', t)                      # blockquote markers
        t = re.sub(r'^\s{0,3}#{1,6}\s+', '', t)                 # heading markers
        t = re.sub(r'^(\s*)[*+\-]\s+', r'\1- ', t)              # normalize bullets
        if re.match(r'^\s*([-*_])(\s*\1){2,}\s*$', t):          # horizontal rules -> drop
            continue
        t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)                  # bold
        t = re.sub(r'__(.+?)__', r'\1', t)                      # bold (underscore)
        t = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'\1', t)  # italic *
        t = re.sub(r'`([^`]+)`', r'\1', t)                      # inline code
        t = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 (\2)', t)      # links w/ url
        t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)          # other links
        out.append(t)
    txt = "\n".join(out)
    txt = txt.replace(' — ', ', ').replace('—', '-')           # em-dash -> comma/hyphen
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    return txt.strip()


# Document/artifact paths the agent produced, so replies carry the file in hand (not just a
# Mission Control task reference). Restricted to known workspace output folders + doc extensions.
_ATTACH_RE = re.compile(
    r'((?:drafts|mission-control/uploads|assets|reports|submissions-archive|out|exports)'
    r'/[\w./-]+?\.(?:docx|pdf|xlsx|xls|pptx|csv|txt|md|png|jpe?g))', re.I)

def _as_word(ap):
    """Jon/team work from Word, never .md/.txt. Convert a raw markdown/text artifact to a
    clean .docx and return that path; on any failure fall back to the original."""
    if not ap.lower().endswith((".md", ".txt")):
        return ap
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("md_to_docx", os.path.join(WS, "scripts", "md_to_docx.py"))
        mdx = importlib.util.module_from_spec(spec); spec.loader.exec_module(mdx)
        dst = os.path.splitext(ap)[0] + ".docx"
        out = mdx.convert(ap, dst)
        # Only accept a real .docx; never let a raw .md/.txt through.
        return out if out and out.lower().endswith(".docx") and os.path.isfile(out) else None
    except Exception as e:
        log(f"[email-reply] md->docx failed for {ap}: {e} (dropping, no raw .md attached)")
        return None


def collect_reply_attachments(*texts, cap=5, max_bytes=20 * 1024 * 1024):
    """Pull real, existing artifact files referenced in the agent's reply/instruction so the
    outbound email includes the actual document. Bounded by count and total size.
    Any .md/.txt artifact is converted to Word before attaching (standing: deliver .docx)."""
    out, total = [], 0
    for t in texts:
        for rel in _ATTACH_RE.findall(t or ""):
            ap = os.path.normpath(os.path.join(WS, rel.strip()))
            if not ap.startswith(WS) or not os.path.isfile(ap) or ap in out:
                continue
            ap = _as_word(ap)
            if not ap or not os.path.isfile(ap) or ap in out:
                continue
            sz = os.path.getsize(ap)
            if sz == 0 or sz > max_bytes or total + sz > max_bytes:
                continue
            out.append(ap); total += sz
            if len(out) >= cap:
                return out
    return out


def email_requester(to_addr, orig_subject, instruction, reply_text, attachments=None):
    """Reply by email to the authenticated requester who sent the @Exobot command, so they
    get closure (done, or decisions awaiting them) without watching Discord. Internal only:
    to_addr is always an allowlisted Mission Control user. Any document the agent produced is
    attached to THIS email so the recipient gets the file in hand, not just a task pointer."""
    subj = re.sub(r'^\s*((re|fwd?|fw)\s*:\s*)+', '', orig_subject or '', flags=re.I).strip() or "your request"
    instr1 = " ".join((instruction or "").split())[:220]
    m = EmailMessage()
    m["From"] = "Exo (Exos AI Assistant) <jquinnexo@pm.me>"
    m["To"] = to_addr
    m["Subject"] = f"Re: {subj}, Exo update"
    note = ("\nDocument attached to this email.\n" if attachments else "")
    m.set_content(
        f"You directed Exo by email:\n  \"{md_to_text(instr1)}\"\n\n"
        f"{md_to_text(reply_text)}\n{note}\n"
        f"- Exo (automated). Anything external or sensitive is drafted and held for your approval, "
        f"not sent. Forward another @Exobot instruction to continue.\n"
    )
    for ap in (attachments or []):
        try:
            with open(ap, "rb") as f:
                data = f.read()
            ctype = mimetypes.guess_type(ap)[0] or "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            m.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(ap))
        except Exception as e:
            log(f"[email-reply] attach failed {ap}: {e}")
    try:
        p = subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", to_addr],
                           input=m.as_bytes(), capture_output=True, timeout=60, env=sub_env())
        if p.returncode != 0:
            log(f"[email-reply] FAILED to {to_addr}: {p.stderr.decode(errors='replace')[:200]}")
            return False
        log(f"[email-reply] sent to {to_addr}")
        return True
    except Exception as e:
        log(f"[email-reply] error to {to_addr}: {e}")
        return False


def sub_env():
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.15.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    return env


def discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", JON_DISCORD, "-m", text],
                       capture_output=True, text=True, timeout=60, env=sub_env())
    except Exception as e:
        log(f"[discord] failed: {e}")


def imap_conn():
    pw = load_json(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if not pw:
        log("ERROR: protonmail_bridge_smtp_password not in secrets.json"); sys.exit(1)
    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
    m.login(EMAIL_USER, pw)
    return m


def _strip_html(h):
    h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    return re.sub(r'[ \t]+', ' ', _html.unescape(h))


def body_text(msg, cap=9000):
    """Prefer text/plain; fall back to stripped HTML (Outlook sends HTML-only)."""
    plain, htmls = [], []
    if msg.is_multipart():
        for p in msg.walk():
            ct = p.get_content_type()
            if ct == "text/plain":
                try: plain.append(p.get_payload(decode=True).decode(errors="replace"))
                except Exception: pass
            elif ct == "text/html":
                try: htmls.append(p.get_payload(decode=True).decode(errors="replace"))
                except Exception: pass
    else:
        try: plain.append(msg.get_payload(decode=True).decode(errors="replace"))
        except Exception: pass
    text = "\n".join(plain).strip()
    if not text and htmls:
        text = _strip_html("\n".join(htmls)).strip()
    return text[:cap]


def sender_authenticated(msg, sender_domain):
    """Cryptographic-grade check that the mail truly came from the sender's domain.
    Returns 'pass' (DMARC/DKIM pass, or domain-aligned SPF pass), 'fail' (explicit
    DMARC/DKIM fail), or 'none'."""
    ars = " ".join(msg.get_all("Authentication-Results", []) or []).lower()
    if not ars:
        return "none"
    if "dmarc=fail" in ars or "dkim=fail" in ars:
        return "fail"
    if "dmarc=pass" in ars or "dkim=pass" in ars or ("spf=pass" in ars and sender_domain in ars):
        return "pass"
    return "none"


def is_trigger(msg, subject, body):
    if subject.strip().startswith("[EXO]"):
        return True
    if EXOBOT_RE.search(body or ""):
        return True
    recips = set()
    for hk in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To"):
        for v in msg.get_all(hk, []):
            for _n, a in getaddresses([v]):
                if a:
                    recips.add(a.lower())
    if recips & TRIGGER_ADDR:
        return True
    # A deliberate send TO the task inbox (not merely Cc/Bcc) is a command on its own.
    to_recips = set()
    for hk in ("To", "Delivered-To", "X-Original-To", "Envelope-To"):
        for v in msg.get_all(hk, []):
            for _n, a in getaddresses([v]):
                if a:
                    to_recips.add(a.lower())
    return bool(to_recips & TASK_TO_ADDR)


def main():
    # Concurrency guard: an accepted trigger launches an agent run up to 600s, and launchd
    # fires this every 600s. Without a lock, overlapping runs read stale state and double-fire.
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    lockf = open(os.path.join(WS, "logs", "mc-email-command.lock"), "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("[skip] another instance already running — exiting")
        return

    secrets = load_json(SECRETS, {})
    passphrase = (secrets.get("mc_command_passphrase") or "").strip()
    allowed, names = load_users_map()

    state = load_json(STATE, {})
    seen_list = list(dict.fromkeys(state.get("seen", [])))  # preserve order, drop dupes
    seen = set(seen_list)
    fails = dict(state.get("fails", {}))  # mid -> failed agent-run attempts (bounded retry)
    MAX_TRIES = 3
    since = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%d-%b-%Y")

    m = imap_conn()
    m.select("INBOX", readonly=False)
    st, data = m.search(None, "SINCE", since)
    nums = data[0].split() if (st == "OK" and data and data[0]) else []
    processed = 0
    for num in nums[::-1]:
        if processed >= MAX_PER_RUN:
            break
        st, raw = m.fetch(num, "(RFC822)")
        if st != "OK" or not raw or not raw[0]:
            continue
        msg = email.message_from_bytes(raw[0][1])
        mid = (msg.get("Message-ID") or "").strip()
        subject = str(msg.get("Subject", "") or "")
        if not mid or mid in seen:
            continue
        body = body_text(msg)
        if not is_trigger(msg, subject, body):
            continue
        seen.add(mid)  # pre-commit so a concurrent run can't re-grab it mid-flight
        seen_list.append(mid)
        save_state(seen_list, fails)  # commit BEFORE the long agent run so an overlap can't re-grab it

        frm = [a.lower() for _n, a in getaddresses([msg.get("From", "")])]
        sender = frm[0] if frm else ""
        sender_domain = sender.split("@")[-1] if "@" in sender else ""

        # Backup export-control screen: HOLD (never run) anything tripping ITAR/EAR/CUI markers,
        # controlled CAD/engineering artifacts, technical data beyond the cleared guide, or the LLM layer.
        ee_hits = ee.deep_hits(subject + "\n" + body + "\n" + " ".join(ee.attachment_names(msg)))
        if ee_hits:
            _recips = []
            for _hk in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To"):
                for _v in msg.get_all(_hk, []):
                    for _n2, _a in getaddresses([_v]):
                        if _a:
                            _recips.append(_a.lower())
            ee.quarantine_and_alert(mid, sender, subject, ee_hits, "command", body, recipients=_recips)
            log(f"[held:export-control] mid={mid} subj={subject!r} hits={ee_hits}")
            processed += 1
            continue

        first_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        domain_auth = sender_authenticated(msg, sender_domain)
        passphrase_ok = bool(passphrase) and (first_line == passphrase)

        # ---- authenticate: allowlisted sender AND (DMARC/DKIM pass OR passphrase), and not an explicit fail
        reasons = []
        if sender not in allowed:
            reasons.append(f"sender {sender or '?'} is not a Mission Control user")
        if domain_auth == "fail":
            reasons.append("sender domain failed DMARC/DKIM (spoofed)")
        if domain_auth != "pass" and not passphrase_ok:
            reasons.append("unverified: needs a DMARC-passing exosaero.com send, or the passphrase on line 1")

        if reasons:
            log(f"[reject] mid={mid} subj={subject!r} reasons={reasons}")
            discord("⚠️ A Mission Control email-command was IGNORED (possible spoof).\n"
                    f"From: {sender or 'unknown'}\nSubject: {subject}\n"
                    f"Reason: {', '.join(reasons)}")
            processed += 1
            continue

        # ---- authenticated: build the instruction ----
        if passphrase_ok:
            out, dropped = [], False
            for ln in body.splitlines():
                if not dropped and ln.strip() == passphrase:
                    dropped = True
                    continue
                out.append(ln)
            instruction = "\n".join(out).strip()
        else:
            # @Exobot forward, DMARC-verified: pass the full body so the agent has the
            # forwarded content the directive refers to.
            instruction = body.strip()[:7000]
        if not instruction:
            discord(f"📧 Authenticated email-command had no instruction (subject: {subject}).")
            processed += 1
            continue

        note = " (DMARC-verified)" if domain_auth == "pass" else " (passphrase)"
        sender_name = names.get(sender, sender)
        first_name = sender_name.split()[0] if sender_name else sender
        prompt = ENVELOPE.format(note=note, body=instruction, sender_name=sender_name,
                                 sender_email=sender, first_name=first_name)
        log(f"[accept] mid={mid} subj={subject!r} auth={domain_auth} instr={instruction[:120]!r}")
        discord(f"📧 Authenticated email-command received{note} — handing to the agent now.\n"
                f"Subject: {subject}\nInstruction: {instruction[:280]}")
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
                tf.write(prompt)
                pf = tf.name
            r = subprocess.run([OPENCLAW, "agent",
                                "--session-key", cmd_session_key(mid),
                                "--message-file", pf, "--json"],
                               capture_output=True, text=True, timeout=600, env=sub_env())
            reply, ok = "", False
            try:
                jdata = json.loads(r.stdout)
                reply = extract_reply(jdata)
                ok = (r.returncode == 0) and (jdata.get("status") == "ok") and bool(reply)
            except Exception:
                ok = False
            if not ok:
                err = (r.stderr or r.stdout or "").strip()[-400:]
                tries = fails.get(mid, 0) + 1
                if tries < MAX_TRIES:
                    # re-queue: un-commit from seen so a later run retries instead of losing it
                    fails[mid] = tries
                    if mid in seen:
                        seen.discard(mid)
                        try: seen_list.remove(mid)
                        except ValueError: pass
                    save_state(seen_list, fails)
                    log(f"[agent] FAILED mid={mid} rc={r.returncode} (try {tries}/{MAX_TRIES}, re-queued): {err}")
                    discord(f"⚠️ Email-command hand-off failed (try {tries}/{MAX_TRIES}, will retry).\n"
                            f"Subject: {subject}\n{err[:300]}")
                else:
                    fails.pop(mid, None)
                    save_state(seen_list, fails)  # give up after MAX_TRIES; stays seen
                    log(f"[agent] FAILED mid={mid} rc={r.returncode} (gave up after {MAX_TRIES}): {err}")
                    discord(f"⛔ Email-command failed {MAX_TRIES}× — giving up (needs a look).\n"
                            f"Subject: {subject}\n{err[:300]}")
            else:
                fails.pop(mid, None)
                sender_name = names.get(sender, sender)
                # NO-OP: opportunity screen negative / nothing actionable -> stay fully silent.
                # No task, no reply, no Discord noise (per Jon: don't reply or add a task when nothing's there).
                if (reply or "").strip().upper().replace("*", "").replace("`", "").startswith("NO_ACTION"):
                    log(f"[agent] NO_ACTION mid={mid} — nothing actionable; silent (no task/reply/discord)")
                else:
                    atts = collect_reply_attachments(reply, instruction)
                    discord(f"✅ Email-command done for {sender_name} — {subject}\n\n{reply[:1500]}"
                            + (f"\n\n📎 attached: {', '.join(os.path.basename(a) for a in atts)}" if atts else ""))
                    # Only email the requester when there's an actual deliverable to hand over (a document).
                    # A summary-only reply is already posted to Discord above, so emailing it too just doubles
                    # the inbox — skip it. (When a document IS produced, the email carries it, in hand.)
                    if atts:
                        email_requester(sender, subject, instruction, reply, attachments=atts)
                        _how = f"discord+emailed; attached {len(atts)} file(s)"
                    else:
                        _how = "discord-only (summary; no redundant email)"
                    log(f"[agent] done rc=0 mid={mid}; {_how} {sender}")
        except Exception as e:
            log(f"[agent] run failed: {e}")
            discord(f"⚠️ Email-command received but the agent run errored: {e}")
        finally:
            try:
                os.unlink(pf)
            except Exception:
                pass
        processed += 1

    try:
        m.logout()
    except Exception:
        pass
    save_state(seen_list, fails)
    log(f"run complete: {processed} trigger email(s) handled")


if __name__ == "__main__":
    main()
