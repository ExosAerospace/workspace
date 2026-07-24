#!/usr/bin/env python3
"""
mc-email-tracker.py — Email -> Mission Control tracker.

Watches the Proton Bridge INBOX + Sent folders and attaches relevant emails to
the matching Mission Control task / decision / opportunity. Trigger convention:
MC users CC jquinnexo@pm.me on their mail (lands in Proton); Jon sends from pm.me.

Tasks are indexed from the LIVE Supabase board (integer ids), not the stale legacy
tasks.json. When an email strong-matches a board task, its DOCUMENT attachments are
pulled onto that task via mc-attach.py (versioned) so reviewers can open the deliverable
from the task card. Export-controlled mail is screened out (itar_ear_screen) before any
capture, so controlled attachments never land in Mission Control.

Read-only on email. Never sends. Only APPENDS to local stores. Idempotent.

Safe-write rules:
- tasks.json / opportunities.json are REGENERATED from markdown -> do NOT write them.
  Email activity for those items lives in the side-store email-activity.json, which
  the dashboard joins at render time.
- decisions.json is a live store -> high-confidence matches are annotated in place
  (each decision gets an `email_activity` array).

Usage: python3 mc-email-tracker.py [--since-days N]   (default 2; backfill uses 14)
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import imaplib, email, json, os, re, sys, argparse, urllib.request, subprocess, tempfile
from email.utils import getaddresses, parsedate_to_datetime
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itar_ear_screen as ee

WS        = "/Users/exomac/.openclaw/workspace"
DATA      = os.path.join(WS, "mission-control", "data")
SECRETS   = "/Users/exomac/.openclaw/secrets.json"
ACT_FILE  = os.path.join(DATA, "email-activity.json")
DEC_FILE  = os.path.join(DATA, "decisions.json")
STATE     = os.path.join(WS, "logs", "mc-email-tracker-state.json")
SELF_ADDRS = {"jquinnexo@pm.me", "jquinn@exosaero.com", "exosmc@proton.me", "exosmc@pm.me"}
# Internal domains are too broad to match on (every teammate shares them) — address
# matching uses EXTERNAL counterparts only. Internal mail still attaches via an
# explicit MC/decision id in the subject/body.
INTERNAL_DOMAINS = {"exosaero.com", "pm.me"}
SUPA_URL = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
MC_ATTACH = os.path.join(WS, "scripts", "mc-attach.py")
# Only real deliverable documents get pulled onto a task — not inline images / signatures.
DOC_EXTS = (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls")

IMAP_HOST, IMAP_PORT = "127.0.0.1", 1143
EMAIL_USER = "jquinnexo@pm.me"
SENT_FOLDERS = ["Sent", "INBOX.Sent", "Sent Messages", "Sent Items"]
USERS_FILE = "/Users/exomac/.openclaw/workspace/mission-control/users.json"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma4:e4b"   # light model — matcher runs every 20 min; 35B pin OOMs the 48GB box
HEAVY_MODEL = "qwen3.6:35b-a3b"   # escalation only: second opinion on AMBIGUOUS matches
HEAVY_CAP = 6                     # max heavy escalations per run (bounds the 27GB transient load)
LLM_CAP = 60          # max model calls per run (bounds cost on big backfills)
ATTACH_CONF = 0.70    # >= this -> auto-attach
SUGGEST_CONF = 0.45   # >= this (but < attach) -> suggest for review, do not attach
RESOLVE_CONF = 0.85   # auto-advancing a decision is consequential -> higher bar than attach

ADDR_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Plus-addressed intake: exosmc+<TASKID>@pm.me (or jquinnexo+<TASKID>@pm.me).
# The task id rides in the delivery address — deterministic, no sender lookup.
PLUS_RE = re.compile(r"^(?:exosmc|jquinnexo)\+([A-Za-z0-9.\-]+)@(?:pm|proton)\.me$", re.I)
STOP = {"with","this","that","from","exos","capital","mission","control","payload",
        "follow","review","status","update","email","draft","aerospace","series",
        "decision","contract","program","week","data","need","send","call","meeting"}


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def arr(obj, *keys):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in keys:
            if isinstance(obj.get(k), list):
                return obj[k]
    return []


def is_send_decision(d):
    """A 'Send X to Y?' gate whose ACTION is executed by sending an email.
    These can auto-resolve when the send is detected. Approval gates ('secure
    approval', 'approve …') are deliberate human acts and are NEVER auto-resolved."""
    t = (d.get("title") or "").strip().lower()
    q = (d.get("question") or "").strip().lower()
    if "approval" in t or "approval" in q or "approve" in q:
        return False
    return t.startswith("send:") or q.startswith("send this") or q.startswith("send the")


def supa_tasks():
    """Live board tasks (integer ids). Falls back to legacy tasks.json if Supabase is down,
    so the watcher never dies on a network blip."""
    try:
        k = json.load(open(SECRETS))["supabase_service_role_key"]
        req = urllib.request.Request(
            SUPA_URL + "tasks?select=id,title,description,owner,state,source&limit=5000",
            headers={"apikey": k, "Authorization": "Bearer " + k})
        rows = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return [r for r in rows if r.get("source") != "mc-board-legacy"]
    except Exception as e:
        print(f"supa_tasks fallback to tasks.json ({e})")
        return arr(load_json(os.path.join(DATA, "tasks.json"), []), "tasks")


def save_task_attachments(msg, task_id, sender):
    """Pull document attachments off this email onto the matched task via mc-attach.py
    (reuses its versioning/supersede so re-sent docs archive the prior version). Controlled
    content is already screened out upstream. The per-message state guard means each email
    is processed once, so this never double-attaches from re-scanning. Returns count saved."""
    try:
        parts = list(msg.walk())
    except Exception:
        return 0
    saved = 0
    for p in parts:
        fn = p.get_filename()
        if not fn or not fn.lower().endswith(DOC_EXTS):
            continue
        try:
            data = p.get_payload(decode=True)
        except Exception:
            data = None
        if not data:
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(fn)) or "attachment"
        tmpd = tempfile.mkdtemp()
        tmpf = os.path.join(tmpd, safe)
        try:
            with open(tmpf, "wb") as f:
                f.write(data)
            r = subprocess.run(
                ["python3", MC_ATTACH, "--task", str(task_id), "--file", tmpf,
                 "--by", "email-tracker", "--title", os.path.basename(fn)],
                capture_output=True, text=True, cwd=WS, timeout=60)
            if r.returncode == 0:
                saved += 1
            else:
                print(f"  attach-fail task {task_id} <- {fn}: {(r.stderr or r.stdout)[:80]}")
        except Exception as e:
            print(f"  attach-error task {task_id} <- {fn}: {e}")
        finally:
            try:
                os.remove(tmpf); os.rmdir(tmpd)
            except Exception:
                pass
    return saved


def build_index():
    """Return list of {id, type, emails:set, tokens:set} for all MC items.
    Tasks come from the LIVE Supabase board (integer ids), not the stale legacy tasks.json."""
    idx = []
    tasks = supa_tasks()
    opps  = arr(load_json(os.path.join(DATA, "opportunities.json"), []), "opportunities")
    decs  = arr(load_json(DEC_FILE, []), "decisions")
    def add(it, typ, *fields):
        iid = it.get("id")
        if not iid:
            return
        iid = str(iid)
        text = " ".join(str(it.get(f, "") or "") for f in fields)
        emails = set(a.lower() for a in ADDR_RE.findall(text))
        emails = {a for a in emails if a.split("@")[-1] not in INTERNAL_DOMAINS}
        title = str(it.get("title", "") or "")
        tokens = set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'&.-]{3,}", text)
                     if w.lower() not in STOP)
        owner = str(it.get("owner", "") or it.get("answeredBy", "") or "").lower()
        status = str(it.get("state", it.get("status", "")) or "")
        summary = re.sub(r"\s+", " ", (title + " — " + text)).strip()[:240]
        idx.append({"id": iid, "type": typ, "emails": emails, "tokens": tokens,
                    "owner": owner, "status": status, "title": title, "summary": summary})
    for t in tasks: add(t, "task", "title", "description")
    for o in opps:  add(o, "opportunity", "title", "description", "next_action")
    for d in decs:  add(d, "decision", "title", "question", "context", "proposedAction", "relatedItem")
    return idx


def load_users():
    """email(lower) -> set of lowercase name tokens, for owner/sender priors."""
    out = {}
    for u in load_json(USERS_FILE, []):
        em = (u.get("email") or "").lower()
        nm = (u.get("name") or "")
        toks = {w.lower() for w in re.findall(r"[A-Za-z]{2,}", nm)}
        if em:
            out[em] = toks
    return out


def prefilter(counterparts, subj_tokens, sender_toks, idx, cap=12):
    """Cheap pre-rank so the model only sees a short, relevant candidate list.
    Signals: shared external address (strong), owner == sender (prior), topic overlap."""
    scored = []
    for it in idx:
        s = 0
        if it["emails"] & counterparts:
            s += 6
        if sender_toks and any(t in it["owner"] for t in sender_toks):
            s += 3
        s += len(it["tokens"] & subj_tokens)
        if it.get("status", "").lower() in ("done", "closed", "answered", "complete"):
            s -= 1
        if s > 0:
            scored.append((s, it))
    scored.sort(key=lambda x: -x[0])
    return [it for _s, it in scored[:cap]]


def ollama_match(ctx, candidates, model=OLLAMA_MODEL, keep_alive=None):
    """Ask a local model which ONE item the email is about, or none. Returns dict.
    keep_alive lets the heavy escalation model unload promptly after use."""
    lines = "\n".join(f'- {c["id"]} [{c["type"]}]: {c["summary"]}' for c in candidates)
    prompt = (
        "You attach an internal work email to the ONE Mission Control item it is about, "
        "or NONE if unclear. Use the sender, recipients, subject and snippet — not guesswork.\n\n"
        f'EMAIL\nfrom: {ctx["from"]}\nto: {", ".join(ctx["to"])}\nsubject: {ctx["subject"]}\n'
        f'snippet: {ctx["snippet"]}\n\nCANDIDATES\n{lines}\n\n'
        'Reply ONLY JSON: {"id":"<exact candidate id or empty>","confidence":0.0-1.0,"reason":"<short>"}. '
        "Pick an id only if the email is clearly about that item; otherwise id empty."
    )
    payload = {"model": model, "format": "json", "stream": False,
               "messages": [{"role": "user", "content": prompt}]}
    if keep_alive:
        payload["keep_alive"] = keep_alive
    body = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    return json.loads(d["message"]["content"])


def imap_conn():
    pw = load_json(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if not pw:
        print("ERROR: protonmail_bridge_smtp_password not in secrets.json"); sys.exit(1)
    m = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
    m.login(EMAIL_USER, pw)
    return m


def fetch_index(m, folder, since_str, direction):
    """Light: return [(folder, num, message_id, direction)] using header-only fetch,
    so we never pull hundreds of full bodies in one shot (that gets the run killed)."""
    try:
        st, _ = m.select(folder, readonly=True)
        if st != "OK":
            return []
    except Exception:
        return []
    try:
        st, data = m.search(None, "SINCE", since_str)
    except Exception:
        return []
    if st != "OK" or not data or not data[0]:
        return []
    out = []
    for num in data[0].split():
        try:
            st, raw = m.fetch(num, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
            mid = ""
            if st == "OK" and raw and raw[0]:
                h = raw[0][1].decode(errors="replace")
                mm = re.search(r"(?i)message-id:\s*(<[^>]+>)", h)
                if mm:
                    mid = mm.group(1).strip()
            out.append((folder, num, mid, direction))
        except Exception:
            continue
    return out


def _strip_html(h):
    import html as _h
    h = re.sub(r'(?is)<(script|style).*?</\1>', ' ', h)
    h = re.sub(r'(?s)<[^>]+>', ' ', h)
    return re.sub(r'\s+', ' ', _h.unescape(h))


def body_text(msg, cap=6000):
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
    text = " ".join(plain).strip()
    if not text and htmls:
        text = _strip_html(" ".join(htmls)).strip()
    return text[:cap]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-days", type=int, default=2)
    ap.add_argument("--max-llm", type=int, default=LLM_CAP)
    ap.add_argument("--max-msgs", type=int, default=40)   # bound work per run (resumable via state)
    args = ap.parse_args()
    since = (datetime.now(timezone.utc) - timedelta(days=args.since_days))
    since_str = since.strftime("%d-%b-%Y")

    idx = build_index()
    known_ids = {it["id"] for it in idx}
    supa_task_ids = {it["id"] for it in idx if it["type"] == "task"}
    # Inline-id matching only on PREFIX-NUM style ids (HP-004, FUND-012, OPP-032). Bare
    # integer Supabase task ids are deliberately excluded — matching "122" inside an email
    # body would false-attach. Integer tasks match via address / token / LLM instead.
    inline_ids = {i for i in known_ids if re.match(r"^[A-Za-z]{1,6}-\w", i)}
    id_pat = re.compile(r"\b(" + "|".join(re.escape(i) for i in sorted(inline_ids, key=len, reverse=True)) + r")\b") if inline_ids else None

    state = set(load_json(STATE, []))
    activity = load_json(ACT_FILE, [])
    act_by_id = {r.get("message_id"): r for r in activity if r.get("message_id")}

    m = imap_conn()
    index = fetch_index(m, "INBOX", since_str, "received")
    for fol in SENT_FOLDERS:
        s = fetch_index(m, fol, since_str, "sent")
        if s:
            index += s
            break

    scanned = 0
    new_high = {}   # item_id -> count
    saved_docs = 0  # email attachments pulled onto tasks
    auto_resolved = []   # decision ids flipped open -> answered by a detected send
    users = load_users()
    llm_calls = 0
    heavy_calls = 0
    suggested_ct = 0
    dec_store = load_json(DEC_FILE, [])
    dec_list = arr(dec_store, "decisions")
    dec_by_id = {d.get("id"): d for d in dec_list}

    def flush():
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        with open(ACT_FILE, "w") as f:
            json.dump(sorted(act_by_id.values(), key=lambda r: r.get("date", ""), reverse=True), f, indent=2)
        with open(STATE, "w") as f:
            json.dump(sorted(state), f)
        with open(DEC_FILE, "w") as f:
            json.dump(dec_store, f, indent=2)

    # Process only unprocessed messages, BOUNDED per run, fetching each body lazily, and
    # CHECKPOINT every few — so a kill never loses progress and the next run resumes.
    todo = [t for t in index if t[2] and t[2] not in state][:args.max_msgs]
    cur_folder = None
    FLUSH_EVERY = 8

    for fol, num, mid, direction in todo:
        if mid in state:
            continue
        try:
            if cur_folder != fol:
                m.select(fol, readonly=True); cur_folder = fol
            st, raw = m.fetch(num, "(RFC822)")
            if st != "OK" or not raw or not raw[0]:
                continue
            msg = email.message_from_bytes(raw[0][1])
        except Exception:
            continue
        scanned += 1
        state.add(mid)
        frm = [a.lower() for _, a in getaddresses([msg.get("From", "")])]
        to  = [a.lower() for _, a in getaddresses([msg.get("To", "")])]
        cc  = [a.lower() for _, a in getaddresses([msg.get("Cc", "")])]
        subject = str(msg.get("Subject", "") or "")
        if any(a in SELF_ADDRS for a in frm):
            direction = "sent"
        try:
            dt = parsedate_to_datetime(msg.get("Date"))
            date_iso = dt.astimezone(timezone.utc).isoformat()
        except Exception:
            date_iso = ""
        counterparts = {a for a in (frm + to + cc) if a and a not in SELF_ADDRS and a.split("@")[-1] not in INTERNAL_DOMAINS}
        blob = subject + "\n" + body_text(msg)

        # Backup export-control screen: HOLD (never capture/attach) anything tripping ITAR/EAR/CUI
        # markers, controlled CAD/engineering artifacts, technical data beyond the cleared guide, or LLM.
        ee_hits = ee.deep_hits(blob + "\n" + " ".join(ee.attachment_names(msg)))
        if ee_hits:
            ee.quarantine_and_alert(mid, (frm[0] if frm else ""), subject, ee_hits, "tracker", blob)
            continue

        # Deterministic, sender-independent routing: BCC exosmc+<TASKID>@pm.me puts the
        # task id in the delivery address itself. BCC lands in Delivered-To/X-Original-To
        # on the bridge, so scan all recipient headers.
        plus_tags = set()
        for hk in ("To", "Cc", "Delivered-To", "X-Original-To", "Envelope-To", "X-Original-Cc"):
            for v in msg.get_all(hk, []):
                for _n, a in getaddresses([v]):
                    mm = PLUS_RE.match((a or "").strip())
                    if mm:
                        plus_tags.add(mm.group(1).upper())

        strong = set()
        basis = []
        for tag in plus_tags:
            if tag in known_ids:
                strong.add(tag); basis.append("plus-tag:" + tag)
        if id_pat:
            for mt in id_pat.findall(blob):
                strong.add(mt); basis.append("id:" + mt)
        for it in idx:
            if it["emails"] & counterparts:
                strong.add(it["id"])
                hit = next(iter(it["emails"] & counterparts))
                basis.append("addr:" + hit)
        method = "deterministic" if strong else None
        suggested = None
        conf_num = None
        reason = None

        # Sender + content semantic match (NO task ids needed) when there's no exact hit.
        # The local model reads who sent it, who it's to, the subject and snippet, and the
        # short candidate list, then picks the one item it's about — or none.
        if not strong and llm_calls < args.max_llm:
            sender_addr = frm[0] if frm else ""
            sender_toks = users.get(sender_addr, set())
            subj_tokens = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'&.-]{3,}", subject)
                           if w.lower() not in STOP}
            cands = prefilter(counterparts, subj_tokens, sender_toks, idx, 12)
            if cands:
                llm_calls += 1
                try:
                    ctx = {"from": sender_addr, "to": (to + cc)[:5], "subject": subject,
                           "snippet": body_text(msg, 1200)}
                    r = ollama_match(ctx, cands)
                    cid = (r.get("id") or "").strip()
                    try:
                        conf_num = float(r.get("confidence") or 0)
                    except Exception:
                        conf_num = 0.0
                    reason = (r.get("reason") or "")[:140]
                    if cid in known_ids and conf_num >= ATTACH_CONF:
                        strong = {cid}; basis = [f"llm:{conf_num:.2f}"]; method = "llm"
                    elif cid in known_ids and conf_num >= SUGGEST_CONF:
                        suggested = cid; method = "llm-suggest"
                except Exception:
                    pass

                # Ambiguous light result -> second opinion from the heavy 35B (rare; unloads after).
                if (not strong) and (conf_num is not None) and SUGGEST_CONF <= conf_num < ATTACH_CONF and heavy_calls < HEAVY_CAP:
                    heavy_calls += 1
                    try:
                        r2 = ollama_match(ctx, cands, HEAVY_MODEL, keep_alive="30s")
                        cid2 = (r2.get("id") or "").strip()
                        c2 = float(r2.get("confidence") or 0)
                        re2 = (r2.get("reason") or "")[:140]
                        if cid2 in known_ids and c2 >= ATTACH_CONF:
                            strong = {cid2}; basis = [f"llm35b:{c2:.2f}"]; method = "llm-escalated"
                            conf_num = c2; reason = re2; suggested = None
                        elif cid2 in known_ids and c2 >= SUGGEST_CONF:
                            suggested = cid2; method = "llm35b-suggest"; conf_num = c2; reason = re2
                        else:
                            suggested = None   # heavy model says no clear match -> drop the weak suggestion
                    except Exception:
                        pass

        if not strong and not suggested:
            continue

        rec = {
            "message_id": mid, "date": date_iso, "direction": direction,
            "from": frm[0] if frm else "", "to": to, "cc": cc, "subject": subject,
            "matched_item": (sorted(strong)[0] if strong else None),
            "matched_items": sorted(strong),
            "suggested_item": suggested,
            "method": method,
            "confidence": ("high" if method == "deterministic" else (round(conf_num, 2) if conf_num is not None else None)),
            "reason": reason,
            "basis": sorted(set(basis)),
        }
        act_by_id[mid] = rec
        if suggested and not strong:
            suggested_ct += 1

        # Proof Exo actually SAW this sent email with us on it: it came from our own Sent
        # mailbox, or an intake/self address is in the recipients (cc/bcc/delivered-to).
        # Required before any decision can auto-flip to "Sent" — it never flips on a send
        # we were not copied on / did not observe.
        recips = set(to) | set(cc)
        for hk in ("Delivered-To", "X-Original-To", "Envelope-To", "Bcc", "X-Original-Cc"):
            for v in msg.get_all(hk, []):
                for _n, a in getaddresses([v]):
                    if a:
                        recips.add(a.lower())
        exo_on_email = (fol in SENT_FOLDERS) or any(a in SELF_ADDRS for a in recips)

        for iid in strong:
            new_high[iid] = new_high.get(iid, 0) + 1
            # Pull any document attachments onto the matched board task (integer ids only).
            if iid in supa_task_ids:
                saved_docs += save_task_attachments(msg, iid, rec["from"])
            d = dec_by_id.get(iid)
            if d is not None:
                ea = d.setdefault("email_activity", [])
                if not any(e.get("message_id") == mid for e in ea):
                    ea.append({"message_id": mid, "date": date_iso, "direction": direction,
                               "from": rec["from"], "to": to, "subject": subject,
                               "basis": rec["basis"]})
                # Auto-advance ONLY send-type gates, ONLY on a real outbound send, ONLY when
                # still open, and ONLY on a strong signal (deterministic addr/id match, or a
                # high-confidence llm match). Records a fact ("Sent"); never grants approval.
                det = method == "deterministic" and any(b.startswith(("addr:", "plus-tag:", "id:")) for b in rec["basis"])
                strong_enough = det or (conf_num is not None and conf_num >= RESOLVE_CONF)
                if (direction == "sent" and exo_on_email and strong_enough
                        and str(d.get("status", "")).lower() == "open"
                        and is_send_decision(d)):
                    d["status"] = "answered"
                    d["answer"] = "Sent"
                    d["answeredAt"] = date_iso
                    d["answeredBy"] = "email-tracker"
                    d["updated"] = date_iso
                    d["note"] = ((d.get("note", "") or "").strip()
                                 + f" Auto-resolved: outreach detected as sent {date_iso[:10]} "
                                   f"(to {', '.join(to[:3])}; msg {mid}).").strip()
                    auto_resolved.append(iid)

        if scanned % FLUSH_EVERY == 0:   # checkpoint so a kill never loses progress
            flush()

    try:
        m.logout()
    except Exception:
        pass
    flush()

    print(f"scanned {scanned} new messages | auto-attached: {sum(new_high.values())} across {len(new_high)} items "
          f"| docs saved to tasks: {saved_docs} | suggested(review): {suggested_ct} "
          f"| light calls: {llm_calls} | 35b escalations: {heavy_calls}")
    for iid, n in sorted(new_high.items(), key=lambda x: -x[1]):
        print(f"  {iid} <- {n} email(s)")
    if auto_resolved:
        print(f"auto-resolved send-decisions: {', '.join(sorted(set(auto_resolved)))}")


if __name__ == "__main__":
    main()
