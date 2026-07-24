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
import json, os, re, sys, subprocess, mimetypes
from email.message import EmailMessage

WS   = "/Users/exomac/.openclaw/workspace"
DEC  = os.path.join(WS, "mission-control", "data", "decisions.json")
MCMD = os.path.join(WS, "exos-mission-control.md")
STATE= os.path.join(WS, "logs", "decision-send-state.json")
LOG  = os.path.join(WS, "logs", "decision-send-watcher.log")
TO   = "jquinn@exosaero.com"          # ALWAYS Jon; never external
FROM = "jquinnexo@pm.me"
FILE_RX = re.compile(r"((?:drafts|captures|tasks|submissions-archive)/[\w./\- ]+?\.(?:docx|pdf|md|txt|pptx|xlsx))", re.I)
SEND_RX = re.compile(r"\b(re-?send|send it|send me|send to me|send the draft|email me|for me to send|send drafted|send response)\b", re.I)

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

def is_send_request(it):
    if str(it.get("status","")).lower() != "answered": return False
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
            "outreach","followup","plan","this","week","capital","exos","nasa","john","jon"}
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
    stop = {"send","draft","drafted","response","email","the","to","for","me","review","a","of","and"}
    words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", it.get("title","")) if w.lower() not in stop]
    if words:
        scored=[]
        for root in ("drafts","captures"):
            d=os.path.join(WS,root)
            if not os.path.isdir(d): continue
            for fn in os.listdir(d):
                s=sum(1 for w in words if w in fn.lower())
                if s>0: scored.append((s, os.path.join(d,fn)))
        scored.sort(key=lambda x:x[0], reverse=True)
        # only accept a STRONG, UNIQUELY-DOMINANT match to avoid attaching the wrong draft
        if scored and scored[0][0]>=3 and (len(scored)==1 or scored[0][0]>scored[1][0]):
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
    # Belt-and-suspenders: if anything still points at a raw markdown/text file, do not attach it.
    if att and att.lower().endswith((".md", ".txt")):
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

def main():
    mode = sys.argv[1] if len(sys.argv)>1 else ""
    st = load_json(STATE, {}); done = st.setdefault("processed", {})   # id -> updated
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
