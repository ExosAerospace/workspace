#!/usr/bin/env python3
"""
DOC MANAGER — Exobot as the (NON-CUI) document manager.

Ingests non-CUI documents (contracts, letters, notes, procedures) into a searchable local library
so Exobot can find them ("the last Jim Wertz contract", "the Scorpius $60K note"). EVERY document is
run through the ITAR/EAR/CUI screen first — anything that trips it is quarantined, never indexed, and
flagged for human review. Full-text search via SQLite FTS5. 100% local.

Lanes:
  • Folder:  drop files in doc-library/inbox/  → --inbox ingests them
  • Email:   forward to exosmc@proton.me with subject starting [DOC] → --email ingests attachments
  • CLI:     ingest <path>  |  search "<query>"

Run:  python3 scripts/doc_manager.py search "Jim Wertz contract"
      python3 scripts/doc_manager.py ingest ~/some/contract.pdf --tags scorpius,contract
      python3 scripts/doc_manager.py --inbox
      python3 scripts/doc_manager.py --email          # scan Proton [DOC] lane
"""
import os, sys, re, json, sqlite3, hashlib, shutil, subprocess, datetime, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from itar_ear_screen import screen  # CUI/ITAR gate — [] means clean

WS = os.path.expanduser("~/.openclaw/workspace")
LIB = os.path.join(WS, "doc-library")
FILES = os.path.join(LIB, "files")
INBOX = os.path.join(LIB, "inbox")
QUAR = os.path.join(LIB, "quarantine")
DB = os.path.join(LIB, "index.db")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
TEXT_EXT = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"}


def _db():
    for d in (FILES, INBOX, QUAR):
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5("
              "doc_id UNINDEXED, filename, tags, source, added UNINDEXED, path UNINDEXED, sha UNINDEXED, body)")
    return c


def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            return subprocess.run(["pdftotext", "-q", path, "-"], capture_output=True, text=True, timeout=60).stdout
        if ext in (".docx", ".doc", ".rtf"):
            return subprocess.run(["textutil", "-convert", "txt", "-stdout", path], capture_output=True, text=True, timeout=60).stdout
        if ext in (".txt", ".md"):
            return open(path, errors="replace").read()
    except Exception as e:
        print(f"  (text extract failed for {os.path.basename(path)}: {e})")
    return ""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(path, tags="", source="cli"):
    if not os.path.isfile(path):
        print(f"  not a file: {path}"); return None
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path)
    sha = sha256(path)
    c = _db()
    if c.execute("SELECT 1 FROM docs WHERE sha=?", (sha,)).fetchone():
        print(f"  already indexed: {name}"); c.close(); return "dup"
    text = extract_text(path) if ext in TEXT_EXT else ""
    hits = screen(text + " " + name)
    if hits:
        # Do NOT copy controlled files (no proliferation) — log the original path + reason for
        # human review, leave the file where it is. It never enters the searchable index.
        with open(os.path.join(QUAR, "quarantine-log.jsonl"), "a") as q:
            q.write(json.dumps({"file": name, "path": os.path.abspath(path), "reason": hits[:5],
                                "ts": datetime.datetime.now().isoformat(timespec="seconds")}) + "\n")
        print(f"  ⛔ QUARANTINED (controlled content: {', '.join(hits[:3])}): {name} — logged, NOT indexed")
        c.close(); return "quarantined"
    doc_id = sha[:12]
    dest = os.path.join(FILES, f"{doc_id}_{name}")
    shutil.copy2(path, dest)
    c.execute("INSERT INTO docs (doc_id,filename,tags,source,added,path,sha,body) VALUES (?,?,?,?,?,?,?,?)",
              (doc_id, name, tags, source, datetime.datetime.now().isoformat(timespec="seconds"), dest, sha, text[:500000]))
    c.commit(); c.close()
    print(f"  ✓ indexed: {name}  [{doc_id}]{'  tags='+tags if tags else ''}  ({len(text)} chars)")
    return doc_id


def search(query, limit=10):
    c = _db()
    # sanitize to a safe FTS query (bare terms OR'd) to avoid syntax errors on punctuation
    terms = re.findall(r"[A-Za-z0-9$]+", query)
    if not terms:
        print("  (empty query)"); c.close(); return
    fts = " OR ".join(terms)
    try:
        rows = c.execute(
            "SELECT doc_id, filename, tags, source, added, path, snippet(docs,7,'» ',' «','…',12) "
            "FROM docs WHERE docs MATCH ? ORDER BY rank LIMIT ?", (fts, limit)).fetchall()
    except sqlite3.OperationalError as e:
        print(f"  search error: {e}"); c.close(); return
    c.close()
    if not rows:
        print(f'  no documents match "{query}".'); return
    print(f'{len(rows)} match(es) for "{query}":')
    for r in rows:
        print(f"  📄 {r[1]}  [{r[0]}]{'  ('+r[2]+')' if r[2] else ''}  · {r[4][:10]} · {r[3]}")
        print(f"     …{r[6].strip()}…")
        print(f"     {r[5]}")


def process_inbox():
    files = [os.path.join(INBOX, f) for f in os.listdir(INBOX) if os.path.isfile(os.path.join(INBOX, f)) and not f.startswith(".")]
    if not files:
        print("inbox empty"); return
    print(f"processing {len(files)} file(s) from {INBOX}:")
    for f in files:
        r = ingest(f, source="inbox")
        if r and r != "dup":
            os.remove(f)  # consumed (copy is in files/ or quarantine/)


def process_email():
    import imaplib, email
    from email.utils import getaddresses
    pw = json.load(open(SECRETS)).get("protonmail_bridge_smtp_password")
    if not pw:
        print("no proton bridge password"); return
    state_p = os.path.join(LIB, ".email-state.json")
    seen = set(json.load(open(state_p)).get("seen", []) if os.path.exists(state_p) else [])
    m = imaplib.IMAP4("127.0.0.1", 1143); m.login("jquinnexo@pm.me", pw); m.select("INBOX")
    since = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%d-%b-%Y")
    _s, data = m.search(None, "SINCE", since)
    got = 0
    for num in (data[0].split() if data and data[0] else []):
        _s, d = m.fetch(num, "(RFC822)")
        if not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        mid = msg.get("Message-ID", "").strip()
        subj = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
        if not mid or mid in seen or not re.match(r"^\s*(re:|fw:|fwd:)?\s*\[doc\]", subj, re.I):
            continue
        seen.add(mid)
        tags = ",".join(re.findall(r"#(\w+)", subj))
        for part in msg.walk():
            fn = part.get_filename()
            if fn and os.path.splitext(fn)[1].lower() in TEXT_EXT | {".xlsx", ".pptx"}:
                tmp = os.path.join(INBOX, str(email.header.make_header(email.header.decode_header(fn))))
                try:
                    open(tmp, "wb").write(part.get_payload(decode=True))
                    if ingest(tmp, tags=tags, source="email") not in (None,) and os.path.exists(tmp):
                        os.remove(tmp)
                    got += 1
                except Exception as e:
                    print(f"  attach {fn} failed: {e}")
    m.logout()
    json.dump({"seen": list(seen)[-3000:]}, open(state_p, "w"))
    print(f"email lane: ingested {got} attachment(s) from [DOC] mail")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", choices=["ingest", "search"], help="ingest <path> | search <query>")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--tags", default="")
    ap.add_argument("--inbox", action="store_true")
    ap.add_argument("--email", action="store_true")
    a = ap.parse_args()
    if a.inbox:
        process_inbox()
    elif a.email:
        process_email()
    elif a.cmd == "ingest" and a.arg:
        ingest(os.path.expanduser(a.arg), tags=a.tags)
    elif a.cmd == "search" and a.arg:
        search(a.arg)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
