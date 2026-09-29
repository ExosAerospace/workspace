#!/usr/bin/env python3
"""
decision-send-watcher.py — closes the "send it to me" loop on the Decisions inbox.

When Jon answers a decision with a SEND intent (e.g. title "Send drafted response...",
answer "Yes — send", or a note/answer like "send it to me"), this emails the linked
DRAFT to Jon (jquinn@exosaero.com) so he actually receives it instead of the request
silently dying in a comment.

SAFETY: recipient is ALWAYS jquinn@exosaero.com (internal, Jon himself). This NEVER
sends to any external party — it is the drafts-route-to-Jon pattern, automated.

Modes:
  --baseline : mark all currently-triggerable answered decisions as processed, send nothing
               (run once at install so history isn't blasted out).
  --dry-run  : print what WOULD be sent, change nothing.
  (default)  : send any NEW send-requests to Jon, record state. Runs on launchd every ~8 min.
Deterministic, fail-soft, idempotent (dedupe by decision id + updated timestamp).
"""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("decision-send")
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

import json, os, re, sys, subprocess, mimetypes
from email.message import EmailMessage

WS   = "/Users/exomac/.openclaw/workspace"
DEC  = os.path.join(WS, "mission-control", "data", "decisions.json")
MCMD = os.path.join(WS, "exos-mission-control.md")
STATE= os.path.join(WS, "logs", "decision-send-state.json")
LOG  = os.path.join(WS, "logs", "decision-send-watcher.log")
TO   = "jquinn@exosaero.com"          # ALWAYS Jon; never external
FROM = "jquinnexo@pm.me"
# A finished deliverable is ONLY ever one of these. We NEVER attach code/build scripts (.py/.js/.sh),
# data (.json/.csv/.log), or notebooks — attaching those is what filled Jon's inbox with useless files.
DELIVERABLE_EXT = (".docx", ".pdf", ".pptx", ".xlsx")
FILE_RX = re.compile(r"((?:drafts|captures|tasks|submissions-archive)/[\w./\- ]+?\.(?:docx|pdf|md|txt|pptx|xlsx))", re.I)
SEND_RX = re.compile(r"\b(re-?send|send it|send me|send to me|send the draft|email me|for me to send|send drafted|send response)\b", re.I)
# Jon 2026-07-31: a decision whose ONLY action is "deliver this draft to your inbox to send" is
# redundant — delivering to Jon's own inbox is NOT an external send (he still sends it himself), so
# it should fire IMMEDIATELY on OPEN, not wait for him to approve delivering it to himself.
DELIVER_TO_JON = re.compile(r"deliver .{0,30}?(your|to your) inbox|for you to send|to your inbox to send|"
                            r"on\s+yes[, ].{0,40}?deliver|i deliver the draft|ready.{0,15}?for you to send", re.I)

def log(m):
    from datetime import datetime, timezone
    ts=datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    with open(LOG,"a") as f: f.write(f"[{ts}] {m}\n")

def load_json(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def decisions():
    d = load_json(DEC, [])
    return d if isinstance(d,list) else d.get("decisions", d.get("items", []))

# Jon 2026-08-31: an email-command (@exobot / [EXO]) already gets a full reply — with the
# deliverable ATTACHED — sent straight back to the requester by mc-email-command.py. If the agent
# also spun up a "send/deliver" Decision during that same run, this watcher would email a SECOND,
# redundant "[Ready to send — from you]" copy. Suppress that: one email-command → one reply. The
# Decision still lives on the board, so answering it there later still delivers the draft normally.
# D-7281739 fix #4: canonicalize the source tag to ONE recognizer. The tag had 60+ hand-typed
# variants ("email cmd", "emailcmd", "e-mail command", "email_command", "exo (email command)") and
# the old strict regex let several slip through → a redundant second email. Match any e-mail +
# command/cmd form, with or without separators, so no variant escapes suppression.
EMAIL_CMD_SOURCE_RX = re.compile(r"e[\-\s]?mail[\s\-_]?(?:command|cmd)", re.I)
def from_email_command(it):
    # check both the canonical source field and any legacy origin/basis fields
    blob = " ".join(str(it.get(k, "") or "") for k in ("source", "origin", "channel", "via"))
    return bool(EMAIL_CMD_SOURCE_RX.search(blob))

def is_send_request(it):
    if str(it.get("status","")).lower() != "answered": return False
    if from_email_command(it): return False  # already delivered via the email-command reply
    ans = str(it.get("answer","")); note = str(it.get("note",""))
    title = str(it.get("title",""))
    # affirmative?
    affirmative = ans.strip().lower().startswith("yes") or "approve" in ans.lower()
    # explicit send phrasing anywhere, OR (affirmative AND the decision is a "send X" request)
    text = " ".join([title, ans, note, str(it.get("proposedAction",""))])
    if SEND_RX.search(ans) or SEND_RX.search(note): return True
    if affirmative and re.search(r"^\s*send\b", title, re.I): return True
    if affirmative and re.search(r"\bfor you to send\b|\bready.*to send\b", str(it.get("proposedAction","")), re.I): return True
    return False

def _plausible(path, it):
    """resolved filename must share a significant token with the decision title/relatedItem."""
    fn = os.path.basename(path).lower()
    stop = {"send","draft","drafted","response","email","the","to","for","me","review",
            "outreach","followup","plan","this","week","capital","exos","nasa","john","jon",
            "form","submit","ready","overdue","days","day","sent","build","final"}
    toks = {w.lower() for w in re.findall(r"[A-Za-z]{4,}",
            f"{it.get('title','')} {it.get('relatedItem','')}") if w.lower() not in stop}
    return any(t in fn for t in toks)

def resolve_draft(it):
    # 1) explicit file path in any field
    for k in ("proposedAction","context","note","answer","title","question"):
        m = FILE_RX.search(str(it.get(k,"")))
        if m:
            p = os.path.join(WS, m.group(1).strip())
            if os.path.exists(p): return p
    # 2) relatedItem -> look it up in the MC board for a drafts/ reference
    #    (guarded: the resolved filename must plausibly relate to the decision, else skip)
    rel = str(it.get("relatedItem","")).strip()
    if rel and os.path.exists(MCMD):
        md = open(MCMD, encoding="utf-8", errors="ignore").read()
        idx = md.find(rel)
        if idx != -1:
            block = md[idx: idx+600]           # tight window: stay inside this item
            m = FILE_RX.search(block)
            if m:
                p = os.path.join(WS, m.group(1).strip())
                if os.path.exists(p) and _plausible(p, it): return p
    # 3) fuzzy: significant title words -> best matching file in drafts/
    stop = {"send","draft","drafted","response","email","the","to","for","me","review","a","of","and",
            "form","submit","ready","overdue","days","day","sent","build","final","plan","this",
            "letter","support","phase","task","your","signature"}
    # Fuzzy on title + relatedItem + dedupeKey — the title alone (e.g. "…8 days overdue, ready for
    # your signature") often lacks the subject tokens that name the file; relatedItem/dedupeKey carry them.
    hay = f"{it.get('title','')} {it.get('relatedItem','')} {str(it.get('dedupeKey','')).replace('-',' ')}"
    words = list(dict.fromkeys(w.lower() for w in re.findall(r"[A-Za-z]{3,}", hay) if w.lower() not in stop))
    if words:
        scored=[]
        for root in ("drafts","captures"):
            d=os.path.join(WS,root)
            if not os.path.isdir(d): continue
            for fn in os.listdir(d):
                # only ever consider finished deliverables — never build scripts / code / data files
                if not fn.lower().endswith(DELIVERABLE_EXT): continue
                s=sum(1 for w in words if w in fn.lower())
                if s>0: scored.append((s, os.path.join(d,fn)))
        # Strong match = >=3 distinct significant tokens shared with the filename. When several files
        # tie at the top score (e.g. versioned/duplicate drafts), the newest-modified wins the tiebreak
        # instead of the item being HELD forever on an unbreakable tie.
        scored.sort(key=lambda x:(x[0], os.path.getmtime(x[1])), reverse=True)
        if scored and scored[0][0] >= 3:
            return scored[0][1]
    return None

def recipient(it):
    """Deliver the ready draft to the decision OWNER's own inbox — they send it from there.
    SAFETY: internal exosaero.com only; anything else falls back to Jon. NEVER external."""
    a = str(it.get("assignedTo") or "").strip().lower()
    return a if a.endswith("@exosaero.com") else "jquinn@exosaero.com"


def send(it, draft):
    to = recipient(it)
    # Standing rule: deliver Word, never a raw .md/.txt — convert before attaching.
    att = draft
    if draft and draft.lower().endswith((".md", ".txt")):
        try:
            import tempfile, importlib.util
            spec = importlib.util.spec_from_file_location("md_to_docx", os.path.join(WS, "scripts", "md_to_docx.py"))
            mdx = importlib.util.module_from_spec(spec); spec.loader.exec_module(mdx)
            dst = os.path.join(tempfile.mkdtemp(), os.path.splitext(os.path.basename(draft))[0] + ".docx")
            att = mdx.convert(draft, dst)
        except Exception as e:
            # NEVER fall back to a raw .md/.txt — Jon works from Word only. Drop the attachment
            # instead and let the note point him at the source path.
            print("md->docx failed, dropping attachment (no raw .md):", str(e)[:80]); att = None
    # Belt-and-suspenders: attach ONLY a finished deliverable. Anything else (raw .md/.txt, or a
    # build script / code / data file that slipped through resolution) is dropped, not emailed.
    if att and not att.lower().endswith(DELIVERABLE_EXT):
        att = None
    m=EmailMessage(); m["From"]=FROM; m["To"]=to
    title=it.get("title","(decision)")
    m["Subject"]=f"[Ready to send — from you] {title}"
    ctx=(f"You authorized decision {it.get('id')} ({title}) with: {it.get('answer','')}.\n"
         f"Related: {it.get('relatedItem','')}\n\n"
         f"This is the ready message. SEND IT FROM YOUR OWN EMAIL to the intended recipient. "
         f"It was delivered here to you, and was NOT sent to the outside party by the system.\n\n"
         f"{('Attached: '+os.path.basename(att)+'  (verify it matches before you send)') if att else ('NOTE: draft could not be delivered as Word (conversion issue). Source: '+os.path.basename(draft)+' — reply and I will resend as .docx.') if draft else 'NOTE: I could not confidently locate a draft file for this — decision context only. Point me at the file if needed.'}\n\n"
         f"Context: {it.get('context','')[:800]}\n\n(auto-delivered by decision-send-watcher to YOUR inbox only, never external.)")
    m.set_content(ctx)
    if att:
        ct,_=mimetypes.guess_type(att); ct=ct or "application/octet-stream"; mt,st=ct.split("/",1)
        with open(att,"rb") as f: m.add_attachment(f.read(),maintype=mt,subtype=st,filename=os.path.basename(att))
    p=subprocess.run(["msmtp","-a","protonmail",to],input=bytes(m),capture_output=True,timeout=60)
    return p.returncode==0, (p.stderr.decode()[:200] if p.returncode else "")

def is_deliver_to_jon(it):
    """OPEN decision whose only action is handing Jon the draft to send from his own inbox."""
    if str(it.get("status","") or "open").lower() != "open":
        return False
    if from_email_command(it): return False  # email-command reply already delivered it (no 2nd email)
    blob = " ".join(str(it.get(k,"")) for k in ("proposedAction","question","context"))
    return bool(DELIVER_TO_JON.search(blob))


# A proposedAction that DESCRIBES the delivery action rather than BEING the draft — auto-delivering
# these produces a content-free email (Jon 2026-08-02). Recognize and skip them unless a real draft
# file is attached.
META_ACTION = re.compile(r"^\s*(approve send\b|on yes[,;: ]|on approval\b|exo delivers\b|exo drafts\b|"
                         r"jon forwards\b|jon,?\s+per\b|verify\b|forward (all|the) |deliver the drafted\b)", re.I)


def has_deliverable_content(it, draft):
    """True only if there's something REAL to deliver: a resolved draft file, or a proposedAction
    that is an actual draft body (addressed + substantial) — not a meta-instruction / multi-doc pointer."""
    # A resolved draft only counts if send() can actually ATTACH it: a finished deliverable
    # (docx/pdf/pptx/xlsx) or a convertible source (.md/.txt). A code/data path (.py/.json/.csv/.log)
    # would be dropped by send()'s attachment guard, leaving an empty "[Ready to send]" shell — the
    # exact fill-my-inbox failure. So those do NOT count as deliverable content.
    if draft and draft.lower().endswith(DELIVERABLE_EXT + (".md", ".txt")):
        return True
    pa = (it.get("proposedAction") or "").strip()
    if not pa or META_ACTION.search(pa):
        return False
    if re.search(r"exo delivers each|exo drafts a|delivers?\s+(?:each|the)\s+letter|each letter to your inbox", pa, re.I):
        return False
    # A proposedAction that instructs delivering a draft to someone to send (e.g. "deliver the
    # drafted email to nmilburn@… to send") is a routing instruction, not the draft itself. Without
    # a resolved draft file there is nothing to deliver — skip rather than send an empty email.
    if re.search(r"\bdeliver\b.{0,80}?\bto send\b", pa, re.I):
        return False
    return len(pa) >= 200  # a genuine inline draft body, not a one-line instruction


def close_decision(did, note):
    """exo3 sign-off gate: after auto-delivering the draft, PROPOSE the close — the card stays OPEN
    with proposedAnswer until a human confirms it in MC (Decisions → ✓ Confirm). Never self-answers."""
    raw = load_json(DEC, [])
    arr = raw if isinstance(raw, list) else raw.get("decisions", [])
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for d in arr:
        if str(d.get("id")) == str(did) and str(d.get("status") or "open").lower() == "open":
            d["proposedAnswer"] = "Done — draft delivered to owner's inbox"
            d["auto_proposed"] = {"by": "decision-send-watcher", "at": now, "basis": note}
            d["note"] = (d.get("note") or "") + f" [{note}; awaiting human confirm]"; d["updated"] = now
    tmp = DEC + f".tmp.{os.getpid()}"  # per-process temp: avoid concurrent-writer race on shared .tmp
    with open(tmp, "w") as f:
        json.dump(arr if isinstance(raw, list) else {**raw, "decisions": arr}, f, indent=2)
    os.replace(tmp, DEC)


def auto_deliver(it, draft):
    """Email the ready draft to the decision OWNER's own inbox (they send it) — internal only.
    Routes to assignedTo per the decisions-route-to-assignee rule; falls back to Jon only when the
    owner is not an internal exosaero.com address. NEVER external."""
    to = recipient(it)
    m = EmailMessage(); m["From"] = FROM; m["To"] = to
    title = it.get("title", "(draft)")
    m["Subject"] = f"[Ready to send — from you] {title}"
    body = (f"This draft is ready to send from your own email (it was NOT sent externally by the system — "
            f"you review it and hit send yourself).\n\n"
            f"{it.get('proposedAction','')}\n\n"
            f"{('Attached: '+os.path.basename(draft)) if draft and draft.lower().endswith(DELIVERABLE_EXT) else ''}\n"
            f"(auto-delivered to your inbox from your pending Decisions — internal only, never external.)")
    m.set_content(body)
    if draft and draft.lower().endswith(DELIVERABLE_EXT) and os.path.exists(draft):
        ct, _ = mimetypes.guess_type(draft); ct = ct or "application/octet-stream"; mt, st = ct.split("/", 1)
        with open(draft, "rb") as f: m.add_attachment(f.read(), maintype=mt, subtype=st, filename=os.path.basename(draft))
    p = subprocess.run(["msmtp", "-a", "protonmail", to], input=bytes(m), capture_output=True, timeout=60)
    return p.returncode == 0, (p.stderr.decode()[:200] if p.returncode else "")


def main():
    mode = sys.argv[1] if len(sys.argv)>1 else ""
    st = load_json(STATE, {}); done = st.setdefault("processed", {})   # id -> updated
    awaiting = st.setdefault("awaiting_draft", {})                       # id -> updated (held, no draft yet)
    # NEW: auto-deliver OPEN "deliver-to-Jon draft" decisions immediately + close them (no approval
    # hop for things Jon requested). Delivery is internal (his inbox); he still sends externally.
    for it in [d for d in decisions() if is_deliver_to_jon(d)]:
        did = str(it.get("id")); key = "autodel-" + did
        if done.get(key):
            continue
        if mode == "--dry-run":
            print(f"AUTO-DELIVER {did} | {(it.get('title') or '')[:60]}"); continue
        if mode == "--baseline":
            done[key] = "1"; continue
        draft = resolve_draft(it)
        if not has_deliverable_content(it, draft):
            # meta-instruction / multi-doc with no attachable draft — do NOT send an empty email.
            # Leave the decision OPEN for proper handling; mark processed so we don't recheck endlessly.
            done[key] = "skip-nocontent"
            log(f"SKIP auto-deliver (no attachable draft; meta/multi-doc): {did} '{it.get('title')}'")
            continue
        ok, err = auto_deliver(it, draft)
        if ok:
            close_decision(did, "auto-delivered on request; no approval needed")
            done[key] = "1"
            log(f"AUTO-DELIVERED to Jon; close proposed (awaiting human confirm): {did} '{it.get('title')}'")
        else:
            log(f"AUTO-DELIVER FAILED {did}: {err}")
    triggerable = [it for it in decisions() if is_send_request(it)]
    for it in triggerable:
        did=str(it.get("id")); upd=str(it.get("updated") or it.get("answeredAt") or "")
        key=did
        already = done.get(key)==upd
        draft=resolve_draft(it)
        if mode=="--dry-run":
            print(f"{did} | {it.get('title')[:60]} | draft={draft or 'NONE'} | already={already}")
            continue
        if mode=="--baseline":
            done[key]=upd; continue
        if already: continue
        # Root-cause fix (Jon 2026-08-17 "nothing here to work with / fill-my-inbox"): NEVER email a
        # "[Ready to send]" with no actual deliverable. If no draft resolves and there's no genuine
        # inline body, HOLD — do not send an empty context-only email. Leave it unprocessed so it
        # self-heals the instant a draft exists; log once so the log doesn't churn every 8 min.
        if not has_deliverable_content(it, draft):
            if awaiting.get(key) != upd:
                awaiting[key]=upd
                log(f"HOLD send (no attachable draft — would be empty, NOT emailing): {did} '{it.get('title')}'")
            continue
        awaiting.pop(key, None)
        ok,err = send(it, draft)
        if ok:
            done[key]=upd
            log(f"SENT to {recipient(it)}: {did} '{it.get('title')}' draft={os.path.basename(draft) if draft else 'none'}")
        else:
            log(f"FAILED {did}: {err}")
    if mode!="--dry-run":
        with open(STATE,"w") as f: json.dump(st,f,indent=2)
    if mode=="--baseline":
        log(f"BASELINE set: {len(triggerable)} send-requests marked processed (no emails sent).")

if __name__=="__main__":
    main()
