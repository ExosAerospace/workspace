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
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("email-command")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gt = _gis_transient(v); _gevent(_GRUN, "transient_skip" if _gt else "error", status="transient" if _gt else "error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import imaplib, email, json, os, re, sys, subprocess, tempfile, fcntl, hashlib, html as _html, mimetypes
from datetime import datetime, timezone
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
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
# LOG addresses: when an INTERNAL sender (Jon/team) copies any of these on ANY line (To/Cc/Bcc),
# it's a deliberate "log this to Mission Control" — process it just like exosmc, regardless of line.
# (Jon 2026-09-02: every email sent cc/bcc to his Proton should update tasks like exosmc does.)
LOG_ADDR = {"jquinnexo@pm.me", "jquinnexo@proton.me", "exosmc@pm.me", "exosmc@proton.me",
            "jquinnexo+do@pm.me", "exosmc+do@proton.me"}
JON_DISCORD = "1501632195163590739"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
MAX_PER_RUN = int(os.environ.get("MCC_MAX_PER_RUN", "3"))
# Matches @exo AND @exobot (+ common typos: exbot / exobto). Fires from the body regardless of line.
EXOBOT_RE = re.compile(r'@\s*ex(?:o(?:bot|bto|boto|bott)?|bot)\b', re.I)

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
    "- TO EMAIL A DOCUMENT BACK to the requester (send/attach/'get me' a file): put a line "
    "`ATTACH: <filename or path>` (one per file) anywhere in your reply — the file is looked up by "
    "name and attached to this reply email automatically. A bare filename works (e.g. "
    "`ATTACH: Exos_OSC_Part1_Concept_25M_2026-09-23.pdf`). Do NOT rely on prose like 'attached' — "
    "always emit an explicit ATTACH: line, and attach the exact format asked for (send the .pdf when "
    "they need the PDF). If unsure the file exists, say so rather than implying it was sent.\n"
    "- DO NOT auto-send or auto-execute anything external or sensitive (external emails, "
    "gov/.mil/.gov outreach, securities/investor communications, deletions, financial actions, "
    "infra/config changes). Instead, DRAFT it and add a Decision to {first_name}'s OWN Decisions "
    "matrix for THEIR review and approval — assign that Decision to {sender_email}, NOT to Jon. "
    "(Standing-rule exceptions: securities/investor items go to the designated securities approver; "
    "government/.mil items route to Jon.)\n"
    "- IMPORTANT: any Decision you create while handling THIS email-command must set its "
    "`source` to \"Exo (email command)\". Your reply below is emailed straight back to the requester "
    "with the deliverable attached, so a separate 'ready to send' email must NOT also go out — the "
    "email-command source tag is how the send-watcher knows to stay silent and avoid a duplicate email.\n"
    "- NO DUPLICATE FOR JON (Jon 2026-09-09): if the requester IS Jon (sender_email jquinn@exosaero.com "
    "or jquinnexo@pm.me) and your handling produces a Decision for HIM to make (a DD verdict, a go/no-go, "
    "or an approve-to-send), that Decision is the ONLY artifact he needs. Put the full substance IN the "
    "Decision (one-line verdict + the specific choice + any links), and begin your reply with the literal "
    "token [[DECISION_ONLY]] on its own first line. The channel then suppresses the duplicate email to Jon "
    "(he gets the Decision in Mission Control + a short Discord note) so he is not made to read the same "
    "thing twice. Do NOT restate the analysis as an emailed write-up. This applies ONLY to Jon and ONLY "
    "when a Decision is created — deliverables/attachments and all other requesters still get the email.\n"
    "- When done, end your reply with a concise summary of what you did (or what now awaits "
    "{first_name}'s approval, and any decisions they must make); that reply is delivered straight "
    "back to {first_name} by email and posted to Jon's Discord.\n\n"
    "DUE DILIGENCE ON INBOUND SOLICITORS: if asked to vet / run DD on an inbound solicitor, FIRST run "
    "`python3 scripts/failed_dd.py check <their-email-or-domain>`. If it MATCHES, do NOT re-run diligence "
    "— reply with the known verdict (firm, reason, date) and 'do not engage'. If it does NOT match and "
    "your own diligence concludes do-not-engage (cold-broker / advance-fee / scam), record it so the whole "
    "team recognizes them next time: run `python3 scripts/failed_dd.py add --firm \"<firm>\" --domain "
    "<domain> --email <email> --person \"<name>\" --reason \"<one-line why>\"`. That registry is checked "
    "automatically on all inbound, so the team never has to forward these to Jon again.\n"
    "- IF THE REQUESTER IS JON (Jon 2026-09-10): a DD verdict on something HE forwarded "
    "(pass / caution / FAIL / do-not-engage on a contact not in the CRM) is DECISION_ONLY. The Decision "
    "already gives him the status, so put the verdict IN the Decision and begin your reply with "
    "[[DECISION_ONLY]] on its own first line — do NOT also send him an email response. His words: "
    "\"you already send me a decision so I know the status - do not send me an email response too.\"\n\n"
    "- EMAIL-DRAFTING IS NOT A DECISION (Jon 2026-09-11): if {first_name} directs you to PREPARE / DRAFT / "
    "WRITE / 'put together' an email reply (or any outbound message), the drafted email ITSELF is the "
    "deliverable — return the full draft in your reply (and attach it as a .docx when it's long) so it "
    "lands in his inbox for review. Do NOT create a Decision block for an email-drafting request and do "
    "NOT use [[DECISION_ONLY]] for it — a draft is a drafting task, not a go/no-go. Where you need him to "
    "supply something you cannot fill (a figure, a name, a date, a choice), leave a CLEARLY-MARKED BLANK — "
    "a run of underscores like `______` or a `[____]` placeholder — so the gaps are obvious at a glance and "
    "he knows exactly what to add before sending. He will send it himself or reply 'send it'. His words: "
    "\"If I direct @exo to prepare an email reply it should never go to a decision block. If it has content "
    "I need to add the blank spaces will make that clear.\"\n\n"
    "ALWAYS LOG EVERY COMPANY DD IN MISSION CONTROL (so the whole team can see the DD is already done and "
    "nobody repeats it): after ANY due-diligence on a company — pass, caution, OR fail — run "
    "`python3 scripts/log_dd.py --firm \"<firm>\" --domain <domain> --person \"<name>\" --email <email> "
    "--verdict <pass|caution|fail> --requester \"{first_name}\" --summary \"<one-line verdict>\" "
    "--next \"<recommended next step>\"`. This writes a visible dossier at /dossier.html. Do this for every "
    "DD; when the verdict is do-not-engage, ALSO add the failed_dd.py registry entry above.\n\n"
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


def _clean_cut(text, limit=1600):
    """Trim text to <= limit at a clean boundary (paragraph > line > sentence > word) so a Discord
    notification never cuts mid-word like reply[:N] did. Returns (trimmed_text, was_truncated)."""
    text = text or ""
    if len(text) <= limit:
        return text, False
    cut = text[:limit]
    for sep in ("\n\n", "\n", ". ", " "):
        i = cut.rfind(sep)
        if i > limit * 0.5:
            return cut[:i].rstrip(), True
    return cut.rstrip(), True


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
    allowed.add("jquinnexo@pm.me")   # Jon's Proton / Exobot account (internal, trusted)
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
    Any .md/.txt artifact is converted to Word before attaching (standing: deliver .docx).

    Returns (attached_paths, missed) where `missed` is a list of (reference, reason) for any
    path the agent referenced like a deliverable but that could NOT be attached — so a drop is
    SURFACED, never silent (Jon 2026-09-10: a referenced-but-missing file must throw a warning)."""
    out, total, missed, seen = [], 0, [], set()
    for t in texts:
        for rel in _ATTACH_RE.findall(t or ""):
            rel = rel.strip()
            if rel in seen:
                continue
            seen.add(rel)
            ap = os.path.normpath(os.path.join(WS, rel))
            if not ap.startswith(WS):
                missed.append((rel, "invalid path")); continue
            if not os.path.isfile(ap):
                missed.append((rel, "file not found")); continue
            wp = _as_word(ap)
            if not wp or not os.path.isfile(wp):
                missed.append((rel, "conversion failed")); continue
            if wp in out:
                continue
            sz = os.path.getsize(wp)
            if sz == 0:
                missed.append((rel, "empty file")); continue
            if sz > max_bytes or total + sz > max_bytes:
                missed.append((rel, "too large (>20MB)")); continue
            out.append(wp); total += sz
            if len(out) >= cap:
                return out, missed
    return out, missed


# Robust attachment resolution: the agent may name a document loosely (a bare filename, or without a
# folder prefix). resolve_artifact() finds the real file by exact path, exact basename, or fuzzy name
# across the known artifact folders — so "ATTACH: Exos_OSC_Part1_Concept_25M_2026-09-23.pdf" works.
_ART_DIRS = ["drafts", "mission-control/uploads", "reports", "assets", "out", "exports",
             "data-room", "process-library", "submissions-archive", "media/inbound/email-command", ""]
_DIRECTIVE_RE = re.compile(r'(?im)^\s*ATTACH:\s*(.+?)\s*$')


def resolve_artifact(ref):
    ref = (ref or "").strip().strip('\'"`<>').strip()
    if not ref:
        return None
    cand = os.path.normpath(os.path.join(WS, ref))
    if cand.startswith(WS) and os.path.isfile(cand):
        return cand
    base = os.path.basename(ref)
    fuzzy = []
    for d in _ART_DIRS:
        root = os.path.join(WS, d)
        if not os.path.isdir(root):
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in ("node_modules", ".git", ".backups")]
            for f in files:
                if f == base:
                    return os.path.join(dirpath, f)
                if len(base) >= 6 and base.lower() in f.lower():
                    fuzzy.append(os.path.join(dirpath, f))
    if fuzzy:
        fuzzy.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return fuzzy[0]
    return None


def collect_attach_directives(*texts, cap=5, max_bytes=20 * 1024 * 1024, existing=None):
    """Attach files the agent explicitly requested via `ATTACH: <name-or-path>` lines, resolved by
    resolve_artifact() (bare filename or fuzzy name OK). Fails loud (missed list), never silent."""
    out, total, missed = [], 0, []
    have = set(existing or [])
    for t in texts:
        for ref in _DIRECTIVE_RE.findall(t or ""):
            ap = resolve_artifact(ref)
            if not ap:
                missed.append((ref, "not found")); continue
            wp = _as_word(ap)
            if not wp or not os.path.isfile(wp):
                missed.append((ref, "conversion failed")); continue
            if os.path.basename(wp) in have:
                continue
            sz = os.path.getsize(wp)
            if sz == 0 or sz > max_bytes or total + sz > max_bytes:
                missed.append((ref, "too large/empty")); continue
            out.append(wp); total += sz; have.add(os.path.basename(wp))
            if len(out) >= cap:
                return out, missed
    return out, missed


_UPLOADS_DIR = os.path.join(WS, "mission-control", "uploads")
_UPLOADS_META = os.path.join(_UPLOADS_DIR, "_meta.json")


def meta_att_ids():
    """Snapshot the set of attachment ids in the uploads registry (call before the agent runs)."""
    try:
        return {m.get("id") for m in json.load(open(_UPLOADS_META))}
    except Exception:
        return set()


def new_task_deliverables(before_ids, cap=5, max_bytes=20 * 1024 * 1024):
    """Files the agent attached to a task during THIS command (via mc-attach.py) — the current
    versions added since `before_ids` was snapshotted. This makes the @exo reply carry the actual
    deliverable even when the reply text never names the file path (root cause of the 2026-09-21
    AEDC agreement 'text-only reply' drop — Jon 2026-09-23)."""
    out, total = [], 0
    try:
        meta = json.load(open(_UPLOADS_META))
    except Exception:
        return out
    for m in meta:
        if m.get("id") in before_ids or not m.get("current", True) or not m.get("task_id"):
            continue
        sn = m.get("stored_name")
        p = os.path.join(_UPLOADS_DIR, sn) if sn else None
        if not (p and os.path.isfile(p)):
            continue
        sz = os.path.getsize(p)
        if sz == 0 or sz > max_bytes or total + sz > max_bytes:
            continue
        out.append(p); total += sz
        if len(out) >= cap:
            break
    return out


def _clean_subject(orig_subject):
    """Strip Re/Fw prefixes and collapse ALL whitespace (incl. embedded CR/LF from wrapped
    Outlook subjects) so the value is always a valid email header — a raw \\r\\n crashes
    EmailMessage and kills the whole reply. Covered by `--selftest`."""
    s = re.sub(r'^\s*((re|fwd?|fw)\s*:\s*)+', '', orig_subject or '', flags=re.I)
    return re.sub(r'\s+', ' ', s).strip() or "your request"


def email_requester(to_addr, orig_subject, instruction, reply_text, attachments=None):
    """Reply by email to the authenticated requester who sent the @Exobot command, so they
    get closure (done, or decisions awaiting them) without watching Discord. Internal only:
    to_addr is always an allowlisted Mission Control user. Any document the agent produced is
    attached to THIS email so the recipient gets the file in hand, not just a task pointer."""
    subj = _clean_subject(orig_subject)  # strips Re/Fw + collapses CR/LF so the header is always valid
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


def _chunk_text(s, limit=1800):
    """Split on line boundaries into <=limit-char parts (Discord hard-caps ~2000/msg; oversized
    sends were also timing out). A single overlong line is hard-split."""
    parts, cur = [], ""
    for line in (s or "").split("\n"):
        while len(line) > limit:
            if cur:
                parts.append(cur); cur = ""
            parts.append(line[:limit]); line = line[limit:]
        if len(cur) + len(line) + 1 > limit:
            parts.append(cur); cur = line
        else:
            cur = (cur + "\n" + line) if cur else line
    if cur:
        parts.append(cur)
    return parts or [""]


def discord(text):
    # Chunk to Discord's message limit and give each part a generous timeout — the old single
    # 60s send silently failed (timed out) on long email-command summaries (Jon 2026-09-10).
    parts = _chunk_text(text)
    for i, part in enumerate(parts):
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", JON_DISCORD, "-m", part],
                           capture_output=True, text=True, timeout=180, env=sub_env())
        except Exception as e:
            log(f"[discord] failed (part {i + 1}/{len(parts)}): {e}")


def imap_conn():
    pw = load_json(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if not pw:
        log("ERROR: protonmail_bridge_smtp_password not in secrets.json"); sys.exit(1)
    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
    m.login(EMAIL_USER, pw)
    return m


# ── Training certificates ([CERT]) — file per-employee + record completion ──
RR_FILE = os.path.join(WS, "mission-control/data/required-reading.json")
CERT_STORE = os.path.join(WS, "submissions-archive", "training-certificates")

def save_training_certs(msg, sender):
    """File any attachments from a [CERT] email into the per-employee training-record store."""
    d = os.path.join(CERT_STORE, re.sub(r'[^a-z0-9._@-]', '_', sender.lower()))
    os.makedirs(d, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    saved = []
    for part in msg.walk():
        fn = part.get_filename()
        if not fn:
            continue
        try:
            data = part.get_payload(decode=True)
            if not data:
                continue
            out = os.path.join(d, f"{stamp}_{re.sub(r'[^A-Za-z0-9._-]', '_', fn)[:120]}")
            with open(out, "wb") as f:
                f.write(data)
            saved.append(out)
        except Exception as e:
            log(f"[cert] attachment save failed: {e}")
    return saved

INBOUND_ATTACH_DIR = os.path.join(WS, "media", "inbound", "email-command")

def save_inbound_attachments(msg, mid, cap=10, max_bytes=25 * 1024 * 1024):
    """Extract the REAL attachments (Content-Disposition: attachment) from an inbound @exo command
    email and save them under media/inbound/email-command/<mid>/ so the agent can READ them (it has
    file tools) and re-attach any it needs. Skips inline images (signatures/logos). Returns saved
    absolute paths. Generalizes save_training_certs, which only handled [CERT] emails — before this,
    a general @exo command's attachments were never saved, so the agent referenced files it could
    never find ("the N documents attached to this email — not found")."""
    safe = re.sub(r'[^A-Za-z0-9]', '_', (mid or 'noid')).strip('_')[:60] or 'noid'
    d = os.path.join(INBOUND_ATTACH_DIR, safe)
    saved = []
    for part in msg.walk():
        try:
            if part.get_content_disposition() != 'attachment':
                continue
            fn = part.get_filename()
            if not fn:
                continue
            data = part.get_payload(decode=True)
            if not data or len(data) > max_bytes:
                continue
            os.makedirs(d, exist_ok=True)
            out = os.path.join(d, re.sub(r'[^A-Za-z0-9._-]', '_', fn)[:120] or 'attachment')
            with open(out, 'wb') as f:
                f.write(data)
            saved.append(out)
            if len(saved) >= cap:
                break
        except Exception as e:
            log(f"[inbound-attach] save failed: {e}")
    return saved

def record_training_completion(sender, sender_name, cert_paths, doc_id="cui-itar-annual"):
    """Record a certificate-based required-reading completion for the sender (resets the annual clock)."""
    try:
        rr = json.load(open(RR_FILE))
    except Exception as e:
        log(f"[cert] cannot read required-reading.json: {e}"); return False
    doc = next((x for x in rr.get("docs", []) if x.get("id") == doc_id), None)
    if not doc:
        log(f"[cert] doc {doc_id} not registered"); return False
    ver = doc.get("version")
    rr.setdefault("completions", [])
    rr["completions"] = [c for c in rr["completions"]
                         if not (c.get("user_email") == sender.lower() and c.get("doc_id") == doc_id and c.get("doc_version") == ver)]
    rr["completions"].append({
        "doc_id": doc_id, "doc_version": ver, "user_email": sender.lower(),
        "user_name": sender_name, "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "valid": True, "type": "certificate",
        "certificates": [os.path.relpath(p, WS) for p in cert_paths],
    })
    try:
        tmp = RR_FILE + ".tmp"
        json.dump(rr, open(tmp, "w"), indent=1)
        os.replace(tmp, RR_FILE)
        return True
    except Exception as e:
        log(f"[cert] write failed: {e}"); return False


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
    # Copying the shared command address exosmc anywhere (To/Cc/Bcc) is a deliberate "read this and
    # act" signal — Exo processes the FULL message + attachments (updates the matching task, files /
    # version-controls any [DOC]). John 2026-09-03: Cc/Bcc to exosmc is now ACTIVE, not passive.
    # (jquinnexo is Jon's personal inbox, NOT a team command channel — its content is only actioned
    # via @Exobot / [EXO]; plain mail there is status-tracked by the metadata layer, not content-read.)
    CMD_ANY = {"exosmc@pm.me", "exosmc@proton.me"}
    if recips & CMD_ANY:
        return True
    to_recips = set()
    for hk in ("To", "Delivered-To", "X-Original-To", "Envelope-To"):
        for v in msg.get_all(hk, []):
            for _n, a in getaddresses([v]):
                if a:
                    to_recips.add(a.lower())
    return bool(to_recips & TASK_TO_ADDR)
    # NOTE (Jon 2026-09-02): a Bcc'd sent-copy must NOT trigger an agent run / create a task. It
    # should MATCH an existing open task and log "email sent on <date>" for follow-up tracking. That
    # is handled by the dedicated sent-log processor (sent-loop-closer), NOT this command trigger.


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
        # Exception: internal-only mail (all recipients are @exosaero.com) is US-person-to-US-person
        # and is NOT an export — quarantine_and_alert returns False in that case. Only skip processing
        # when the hold was actually placed (returned True); allow internal mail through.
        # [CERT] training-certificate submissions are administrative completion records (not
        # controlled technical data) and are filed internally with no external release, so they
        # are exempt from the export-control hold.
        ee_hits = [] if subject.strip().upper().startswith("[CERT]") else ee.deep_hits(subject + "\n" + body + "\n" + " ".join(ee.attachment_names(msg)))
        if ee_hits:
            _recips = []
            for _hk in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To"):
                for _v in msg.get_all(_hk, []):
                    for _n2, _a in getaddresses([_v]):
                        if _a:
                            _recips.append(_a.lower())
            actually_held = ee.quarantine_and_alert(mid, sender, subject, ee_hits, "command", body, recipients=_recips)
            if actually_held:
                log(f"[held:export-control] mid={mid} subj={subject!r} hits={ee_hits}")
                processed += 1
                continue
            # Internal-only: screener flagged content but correctly exempted from hold.
            # Log the flag and continue processing normally.
            log(f"[export-control:internal-exempt] mid={mid} subj={subject!r} hits={ee_hits}")

        first_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
        domain_auth = sender_authenticated(msg, sender_domain)
        passphrase_ok = bool(passphrase) and (first_line == passphrase)

        # ---- authenticate: allowlisted sender AND (DMARC/DKIM pass OR passphrase), and not an explicit fail
        reasons = []
        if sender not in allowed:
            reasons.append(f"sender {sender or '?'} is not a Mission Control user")
        if domain_auth == "fail":
            reasons.append("sender domain failed DMARC/DKIM (spoofed)")
        # Jon's Proton / Exobot account (jquinnexo@pm.me) is internal & trusted: accept it without
        # an exosaero.com DMARC pass, but ONLY when there is no explicit DMARC/DKIM FAIL (an external
        # forgery of jquinnexo@pm.me gets dmarc=fail at Proton inbound and is still rejected above).
        TRUSTED_INTERNAL = {"jquinnexo@pm.me"}
        proton_trusted = sender in TRUSTED_INTERNAL and domain_auth != "fail"
        if domain_auth != "pass" and not passphrase_ok and not proton_trusted:
            reasons.append("unverified: needs a DMARC-passing exosaero.com send, or the passphrase on line 1")

        if reasons:
            log(f"[reject] mid={mid} subj={subject!r} reasons={reasons}")
            discord("⚠️ A Mission Control email-command was IGNORED (possible spoof).\n"
                    f"From: {sender or 'unknown'}\nSubject: {subject}\n"
                    f"Reason: {', '.join(reasons)}")
            processed += 1
            continue

        # ---- [CERT] training-certificate submission: file it + record completion (no agent turn) ----
        if subject.strip().upper().startswith("[CERT]"):
            certs = save_training_certs(msg, sender)
            sname = names.get(sender, sender)
            if not certs:
                email_requester(sender, subject, "certificate",
                    "We received your [CERT] email but found no certificate attached. Please reply with your training completion certificate attached (PDF or image).")
                discord(f"📄 [CERT] from {sname} had no attachment — asked them to resend.")
            else:
                ok_rec = record_training_completion(sender, sname, certs)
                fnames = ", ".join(os.path.basename(c) for c in certs)
                email_requester(sender, subject, "certificate",
                    f"Thank you. Your training certificate ({fnames}) has been filed and your annual CUI/ITAR training is recorded as complete for this year.")
                discord(f"📄✅ Training certificate filed for {sname} <{sender}>: {fnames}"
                        + ("" if ok_rec else " (⚠️ completion NOT recorded — check cui-itar-annual doc)"))
                log(f"[cert] mid={mid} filed {len(certs)} cert(s) for {sender} recorded={ok_rec}")
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
        # Save any real attachments on this command email so the agent can read/re-attach them
        # (previously only [CERT] did this → general commands lost their attachments, e.g. the
        # 4 BLK4-RDRE proposal docs the agent then couldn't find). Give the agent the saved paths.
        try:
            _inbound_atts = save_inbound_attachments(msg, mid)
        except Exception as _e:
            _inbound_atts = []; log(f"[inbound-attach] extraction error mid={mid}: {_e}")
        if _inbound_atts:
            _rels = [os.path.relpath(p, WS) for p in _inbound_atts]
            instruction = (instruction + "\n\n[The sender attached " + str(len(_rels)) +
                           " document(s) to this email; they are saved for you to read at these paths "
                           "(read them for full context, and use `ATTACH: <path>` for any you must include "
                           "in a reply):\n" + "\n".join("- " + r for r in _rels) + "]").strip()
            log(f"[inbound-attach] mid={mid} saved {len(_rels)} file(s): {_rels}")
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
        before_att_ids = meta_att_ids()  # snapshot so we can attach the deliverable the agent adds to a task
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
                    atts, missed_atts = collect_reply_attachments(reply, instruction)
                    _have = {os.path.basename(a) for a in atts}
                    # Explicit `ATTACH: <name-or-path>` directives (resolved by name/fuzzy) — this is
                    # the reliable way to email an EXISTING document (root cause of the OSC submittal
                    # 'no attachment' drops — Jon 2026-09-23; the agent named the file, no path).
                    _dir_atts, _dir_missed = collect_attach_directives(reply, instruction, existing=_have)
                    for _d in _dir_atts:
                        if len(atts) < 5:
                            atts.append(_d); _have.add(os.path.basename(_d))
                    missed_atts = (missed_atts or []) + (_dir_missed or [])
                    # Also attach any deliverable the agent added to a task this run (via mc-attach.py),
                    # even if the reply text didn't spell out the path — so "fill this out and return it"
                    # actually returns the file. Dedupe by basename against path-referenced attachments.
                    for _d in new_task_deliverables(before_att_ids):
                        if os.path.basename(_d) not in _have and len(atts) < 5:
                            atts.append(_d); _have.add(os.path.basename(_d))
                    # Surface referenced-but-missing attachments instead of dropping them silently
                    # (Jon 2026-09-10 root-cause: a described .xlsx that was never written just vanished).
                    _miss_note = ""
                    if missed_atts:
                        _mw = "; ".join(f"{os.path.basename(r)} ({why})" for r, why in missed_atts)
                        log(f"[email-reply] ⚠️ referenced attachment(s) NOT sent: {_mw}")
                        _miss_note = ("\n\n⚠️ Referenced but NOT attached (file missing/failed): " + _mw
                                      + "\n(The document was named but no valid file was found — it was not generated or the path is wrong.)")
                    # NO DUPLICATE FOR JON (Jon 2026-09-09): when HIS own @exo task produces a Decision for
                    # him to make (agent flags it with a leading [[DECISION_ONLY]] token), the Decision is the
                    # single artifact — do NOT also email him the write-up (it was filling his inbox and making
                    # him read the same thing twice). Team email-users (Phil/Lizi) and deliverable/attachment
                    # replies are unaffected: they still get the email.
                    _sender_l = (sender or "").lower()
                    _is_jon = _sender_l in ("jquinn@exosaero.com", "jquinnexo@pm.me",
                                            "jquinnexo+do@pm.me", "jquinnexo@proton.me")
                    _decision_only = bool(re.search(r"\[\[\s*decision[_ ]only\s*\]\]", reply or "", re.I))
                    reply = re.sub(r"\[\[\s*decision[_ ]only\s*\]\]", "", reply or "", flags=re.I).strip()
                    _summary, _cut = _clean_cut(reply, 1600)
                    if _is_jon and _decision_only:
                        # Decision is the sole artifact: Discord note only, no email to Jon.
                        discord(f"✅ Email-command done — {subject}\n\n{_summary}"
                                "\n\n🗳️ Decision created for your call in Mission Control — no duplicate email sent."
                                + _miss_note)
                        log(f"[agent] done rc=0 mid={mid}; decision-only, email-to-Jon suppressed {sender}")
                    else:
                        discord(f"✅ Email-command done for {sender_name} — {subject}\n\n{_summary}"
                                + ("\n\n📧 Full reply sent to your inbox — trimmed here to keep the channel clean." if _cut else "")
                                + (f"\n\n📎 attached: {', '.join(os.path.basename(a) for a in atts)}" if atts else "")
                                + _miss_note)
                        # ALWAYS reply to the requester on the channel THEY used (email). The Discord post above
                        # goes to Jon's ops channel, NOT the requester — so a summary-only answer would never reach
                        # them otherwise. (This silently dropped Phil's Grant Engine DD, 2026-08-18: rc=0 but the
                        # only delivery was "discord-only", which Phil, an email user, never saw.)
                        email_requester(sender, subject, instruction, reply, attachments=atts)
                        _how = (f"discord+emailed requester; attached {len(atts)} file(s)" if atts
                                else "discord+emailed requester (summary)")
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


def _selftest():
    """Regression eval for the two 2026-09-25 Dankanich-pipeline fixes (ExO3 Trusted-Evals):
       (a) a wrapped/CR-LF Outlook subject yields a VALID reply-Subject header (no crash);
       (b) inbound @exo attachments are extracted (real docs saved, inline images skipped).
    Exit 0 on pass, 1 on any failure. Run: python3 scripts/mc-email-command.py --selftest"""
    import shutil
    fails = []
    # (a) subject sanitization
    bad = 'Fw: [EXTERNAL] EXOS BLK4-RDRE NASA proposal (22.5-45k, annual\r\n spend, +BLK3 RHU) '
    try:
        subj = _clean_subject(bad)
        mm = EmailMessage(); mm["Subject"] = f"Re: {subj}, Exo update"
        hv = str(mm["Subject"])
        assert "\r" not in hv and "\n" not in hv, "CR/LF leaked into Subject header"
        assert "BLK4-RDRE" in hv, "subject content lost"
        print("PASS subject-sanitize:", hv)
    except Exception as e:
        fails.append(f"subject-sanitize: {e}")
    # (b) inbound attachment extraction
    try:
        m = EmailMessage(); m["Subject"] = "t"; m.set_content("body")
        m.add_attachment(b"%PDF-1.4 x", maintype="application", subtype="pdf", filename="Proposal_A.pdf")
        m.add_attachment(b"docxbytes", maintype="application",
                         subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                         filename="Proposal_B.docx")
        inl = EmailMessage(); inl.add_attachment(b"PNG", maintype="image", subtype="png",
                                                 filename="sig001.png", disposition="inline")
        m.attach(inl.get_payload()[0] if inl.is_multipart() else inl)
        saved = save_inbound_attachments(m, "SELFTEST_MID")
        base = [os.path.basename(p) for p in saved]
        assert "Proposal_A.pdf" in base and "Proposal_B.docx" in base, f"real attachments missing: {base}"
        assert not any("sig001" in b for b in base), f"inline image not skipped: {base}"
        print("PASS inbound-attachments:", base)
    except Exception as e:
        fails.append(f"inbound-attachments: {e}")
    finally:
        shutil.rmtree(os.path.join(INBOUND_ATTACH_DIR, "SELFTEST_MID"), ignore_errors=True)
    if fails:
        print("SELFTEST FAILED:")
        for f in fails:
            print("  -", f)
        return 1
    print("SELFTEST OK")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(_selftest())
    main()
