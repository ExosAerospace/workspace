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
import imaplib, email, json, os, re, sys, subprocess, tempfile, fcntl, hashlib, html as _html
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
JON_DISCORD = "1501632195163590739"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
MAX_PER_RUN = int(os.environ.get("MCC_MAX_PER_RUN", "3"))
EXOBOT_RE = re.compile(r'@\s*exobot\b', re.I)

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
    "EMAIL CONTENT / INSTRUCTION:\n{body}\n"
)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


SEEN_CAP = 3000  # keep the most-RECENT N handled message-ids


def save_state(seen_list):
    """Persist seen message-ids in RECENCY order (insertion order), capped to the most
    recent SEEN_CAP. Never sort message-ids: they have no chronological order, so sorting
    then truncating perpetually evicts a fixed alphabetical band and reprocesses it."""
    keep = seen_list[-SEEN_CAP:]
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"seen": keep}, f, indent=2)
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


def email_requester(to_addr, orig_subject, instruction, reply_text):
    """Reply by email to the authenticated requester who sent the @Exobot command, so they
    get closure (done, or decisions awaiting them) without watching Discord. Internal only:
    to_addr is always an allowlisted Mission Control user."""
    subj = re.sub(r'^\s*((re|fwd?|fw)\s*:\s*)+', '', orig_subject or '', flags=re.I).strip() or "your request"
    instr1 = " ".join((instruction or "").split())[:220]
    m = EmailMessage()
    m["From"] = "Exo (Exos AI Assistant) <jquinnexo@pm.me>"
    m["To"] = to_addr
    m["Subject"] = f"Re: {subj}, Exo update"
    m.set_content(
        f"You directed Exo by email:\n  \"{md_to_text(instr1)}\"\n\n"
        f"{md_to_text(reply_text)}\n\n"
        f"- Exo (automated). Anything external or sensitive is drafted and held for your approval, "
        f"not sent. Forward another @Exobot instruction to continue.\n"
    )
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
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.14.0/bin:"
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
    return bool(recips & TRIGGER_ADDR)


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
        seen.add(mid)  # a trigger email is handled exactly once, pass or fail
        seen_list.append(mid)
        save_state(seen_list)  # commit BEFORE the long agent run so an overlap can't re-grab it

        frm = [a.lower() for _n, a in getaddresses([msg.get("From", "")])]
        sender = frm[0] if frm else ""
        sender_domain = sender.split("@")[-1] if "@" in sender else ""

        # Backup export-control screen: HOLD (never run) anything tripping ITAR/EAR/CUI markers,
        # controlled CAD/engineering artifacts, technical data beyond the cleared guide, or the LLM layer.
        ee_hits = ee.deep_hits(subject + "\n" + body + "\n" + " ".join(ee.attachment_names(msg)))
        if ee_hits:
            ee.quarantine_and_alert(mid, sender, subject, ee_hits, "command", body)
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
                log(f"[agent] FAILED mid={mid} rc={r.returncode}: {err}")
                discord(f"⚠️ Email-command accepted but the agent hand-off FAILED.\n"
                        f"Subject: {subject}\n{err[:300]}")
            else:
                sender_name = names.get(sender, sender)
                discord(f"✅ Email-command done for {sender_name} — {subject}\n\n{reply[:1500]}")
                email_requester(sender, subject, instruction, reply)
                log(f"[agent] done rc=0 mid={mid}; discord+emailed {sender}")
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
    save_state(seen_list)
    log(f"run complete: {processed} trigger email(s) handled")


if __name__ == "__main__":
    main()
