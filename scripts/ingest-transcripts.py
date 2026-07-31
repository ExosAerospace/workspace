#!/usr/bin/env python3
"""
ingest-transcripts.py — turn a call transcript into CRM / dossier / action-item updates.

INPUTS (two ways, both automatic):
  1. Drop a file in transcripts/inbox/  (.docx, .txt, .md)
  2. Email it to your Proton with [TRANSCRIPT] in the subject (attachment or body)

For each new transcript it:
  - extracts the text and archives it to transcripts/<date>_<slug>.txt
  - runs the LOCAL model (Ollama) to extract a structured summary: participants,
    key points, action items, the relationship it maps to, and a PROPOSED status +
    next step
  - appends the result to mission-control/data/transcripts.json (viewable log)
  - DMs Jon a summary + proposed updates for one-tap confirmation

SAFETY GATE: it does NOT silently rewrite a dossier's status. Status/next-step
changes are PROPOSED to Jon; a human (or Exo on confirmation) applies them by editing
config/relationships.json. Contacts with emails flow in via the normal capture job.
Fail-soft: if Ollama is down, it still archives + DMs the raw transcript flagged for
manual processing.
"""
import imaplib, email, json, os, re, glob, shutil, subprocess, urllib.request
from datetime import datetime, timezone
from email.header import decode_header

WS = "/Users/exomac/.openclaw/workspace"
INBOX_DIR = os.path.join(WS, "transcripts", "inbox")
DONE_DIR = os.path.join(WS, "transcripts", "processed")
ARCHIVE = os.path.join(WS, "transcripts")
OUT = os.path.join(WS, "mission-control", "data", "transcripts.json")
STATE = os.path.join(WS, "logs", "transcript-ingest-state.json")
LOG = os.path.join(WS, "logs", "transcript-ingest.log")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen3.6:35b-a3b"
DM_TARGET = "user:1501632195163590739"
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"


def now():
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def logline(m):
    try:
        open(LOG, "a").write(f"[{now()}] {m}\n")
    except Exception:
        pass


def load_json(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def save_json(p, o):
    tmp = p + ".tmp"
    json.dump(o, open(tmp, "w"), indent=2, ensure_ascii=False)
    os.replace(tmp, p)


def dec(s):
    if not s:
        return ""
    out = ""
    for t, e in decode_header(s):
        out += t.decode(e or "utf-8", "ignore") if isinstance(t, bytes) else t
    return out


def docx_text(path):
    import zipfile
    z = zipfile.ZipFile(path)
    xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    txt = re.sub(r"<[^>]+>", "", xml)
    for a, b in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"')]:
        txt = txt.replace(a, b)
    return re.sub(r"[ \t]+", " ", txt).strip()


def extract_text(path):
    low = path.lower()
    if low.endswith(".docx"):
        return docx_text(path)
    if low.endswith((".txt", ".md")):
        return open(path, encoding="utf-8", errors="ignore").read()
    return ""


def slug(s):
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")[:50] or "transcript"


def post_dm(text):
    env = os.environ.copy()
    env["PATH"] = ":".join([os.path.dirname(OPENCLAW),
                            "/Users/exomac/.local/share/mise/shims",
                            "/opt/homebrew/bin", "/usr/local/bin", env.get("PATH", "")])
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DM_TARGET, "-m", text],
                       capture_output=True, text=True, timeout=60, env=env)
    except Exception as e:
        logline(f"DM failed: {e}")


def ollama_extract(text):
    prompt = (
        "You are a CRM analyst. From this call/meeting transcript, return STRICT JSON with keys: "
        "title (short), summary (3-4 sentences), participants (array of {name, org, role, email}), "
        "key_points (array of strings), action_items (array of {owner, task}), "
        "relationship (the company/person this maps to), proposed_status (one line), "
        "proposed_next_step (one line), flags (array of strings: legal/securities/conflict/ITAR or data to confirm). "
        "Only output JSON.\n\nTRANSCRIPT:\n" + text[:14000])
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "format": "json", "think": False,
                       "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.loads(r.read().decode())
    resp = (data.get("response") or data.get("thinking") or "").strip()
    resp = re.sub(r"<think>.*?</think>", "", resp, flags=re.S).strip()
    return json.loads(resp)


def collect():
    """Return list of (name, text, cleanup_fn)."""
    items = []
    # 1) watched folder
    for path in sorted(glob.glob(os.path.join(INBOX_DIR, "*"))):
        if os.path.isfile(path):
            try:
                txt = extract_text(path)
            except Exception as e:
                logline(f"extract failed {path}: {e}")
                txt = ""
            if txt.strip():
                items.append((os.path.basename(path), txt, ("file", path)))
    # 2) tagged email
    state = load_json(STATE, {})
    seen = set(state.get("email_uids", []))
    pw = load_json(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if pw:
        try:
            m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT); m.starttls(); m.login(EMAIL_USER, pw)
            m.select("INBOX")
            typ, data = m.uid("search", None, "SINCE", "01-Jun-2026", "SUBJECT", '"[TRANSCRIPT]"')
            for u in (data[0].split() if data and data[0] else []):
                uid = u.decode()
                if uid in seen:
                    continue
                typ, d = m.uid("fetch", u, "(RFC822)")
                if not d or not d[0]:
                    continue
                msg = email.message_from_bytes(d[0][1])
                subj = dec(msg["Subject"])
                txt = ""
                for part in msg.walk():
                    fn = part.get_filename()
                    if fn and fn.lower().endswith((".docx", ".txt", ".md")):
                        tmp = os.path.join(INBOX_DIR, dec(fn))
                        open(tmp, "wb").write(part.get_payload(decode=True))
                        try:
                            txt = extract_text(tmp)
                        finally:
                            try: os.remove(tmp)
                            except Exception: pass
                        break
                if not txt:
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            txt = part.get_payload(decode=True).decode("utf-8", "ignore"); break
                if txt.strip():
                    items.append((subj, txt, ("email", uid)))
                seen.add(uid)
            m.logout()
        except Exception as e:
            logline(f"email scan failed: {e}")
    state["email_uids"] = sorted(seen)
    save_json(STATE, state)
    return items


def main():
    items = collect()
    if not items:
        logline("no new transcripts")
        return
    log = load_json(OUT, {"generated_display": "", "transcripts": []})
    for name, text, (origin, ref) in items:
        date = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        arch = os.path.join(ARCHIVE, f"{date}_{slug(name)}.txt")
        try:
            open(arch, "w").write(text)
        except Exception:
            pass
        extracted, ok = None, True
        try:
            extracted = ollama_extract(text)
        except Exception as e:
            ok = False
            logline(f"ollama extract failed for {name}: {e}")
        rec = {"ingested": now(), "source": origin, "name": name,
               "archive": os.path.relpath(arch, WS), "auto_extract_ok": ok,
               "extracted": extracted}
        log["transcripts"].insert(0, rec)
        # build DM
        if ok and extracted:
            ai = extracted.get("action_items", [])
            ai_txt = "\n".join(f"  • [{(a.get('owner') or '?')}] {a.get('task','')}" for a in ai[:8]) or "  (none)"
            parts = ", ".join(p.get("name", "") for p in extracted.get("participants", []) if p.get("name"))
            flags = extracted.get("flags", [])
            fl = ("\n⚠ " + "\n⚠ ".join(flags)) if flags else ""
            dm = (f"\U0001F4DD **Transcript ingested: {extracted.get('title', name)}**\n"
                  f"Relationship: {extracted.get('relationship','?')} | Participants: {parts}\n\n"
                  f"{extracted.get('summary','')}\n\n"
                  f"**Proposed status:** {extracted.get('proposed_status','')}\n"
                  f"**Proposed next step:** {extracted.get('proposed_next_step','')}\n"
                  f"**Action items:**\n{ai_txt}{fl}\n\n"
                  f"_Proposed only — reply to confirm and I'll apply it to the dossier._")
        else:
            dm = (f"\U0001F4DD **Transcript received: {name}** (auto-extract unavailable — archived at "
                  f"{os.path.relpath(arch, WS)}). Ask me to process it.")
        post_dm(dm)
        logline(f"ingested {name} (extract_ok={ok})")
        # cleanup source
        if origin == "file":
            try:
                shutil.move(ref, os.path.join(DONE_DIR, os.path.basename(ref)))
            except Exception:
                pass
    log["generated_display"] = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    save_json(OUT, log)
    logline(f"run complete: {len(items)} transcript(s)")


if __name__ == "__main__":
    main()
