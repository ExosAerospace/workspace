# -*- coding: utf-8 -*-
"""
capstone_email_capture.py — turn UTD capstone students'/instructors' emails to the Proton mailbox
into Mission Control tasks so their questions never get lost. Exo monitors jquinnexo@pm.me; any
message FROM a capstone account (role=early_adopter, project="Payload Sales" in MC users) becomes
a task assigned to Lizi (capstone owner). Idempotent: dedupe by Message-ID. Run: [--dry]
"""
import imaplib, email, socket, json, os, sys, urllib.request, urllib.error
from email.header import decode_header
socket.setdefaulttimeout(60)
WS=os.path.expanduser("~/.openclaw/workspace")
H,P,U,PW='127.0.0.1',1143,'jquinnexo@pm.me',__import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
STATE=os.path.join(WS,"mission-control","data","capstone_email_seen.json")
USERS=os.path.join(WS,"mission-control","users.json")
SB="https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY=json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
SBH={"apikey":KEY,"Authorization":"Bearer "+KEY,"Content-Type":"application/json"}
LIZI="lquinn@exosaero.com"
DRY="--dry" in sys.argv

def dh(s):
    try: return ''.join(p.decode(e or 'utf-8','ignore') if isinstance(p,bytes) else p for p,e in decode_header(s or ''))
    except: return s or ''

def capstone_addrs():
    d=json.load(open(USERS)); u=d if isinstance(d,list) else d.get("users",[])
    return {(x.get("email") or "").lower(): x.get("name")
            for x in u if x.get("role")=="early_adopter" and (x.get("project") or "")=="Payload Sales"}

def make_task(sender_name, sender_email, subject, snippet):
    task={"title":f"Capstone Q — {sender_name}: {subject[:70]}",
          "state":"New","owner":"Lizi Quinn","assigned_to":"Lizi Quinn","assigned_email":LIZI,"priority":70,
          "category":"Capstone Support","source":"capstone-email",
          "description":f"Question from {sender_name} <{sender_email}> to the Proton mailbox re: the UTD payload capstone.\n\nSubject: {subject}\n\n{snippet[:600]}\n\n[Reply from the Proton mailbox. Auto-captured by Exo.]"}
    r=urllib.request.Request(SB+"/tasks",data=json.dumps(task).encode(),headers={**SBH,"Prefer":"return=representation"},method="POST")
    with urllib.request.urlopen(r,timeout=30) as x: return json.load(x)[0].get("id")

def main():
    seen=set(json.load(open(STATE))) if os.path.exists(STATE) else set()
    addrs=capstone_addrs()
    if not addrs: print("no capstone addresses found"); return
    m=imaplib.IMAP4(H,P)
    try: m.starttls()
    except Exception: pass
    m.login(U,PW)
    made=0; scanned=0
    for folder in ("INBOX",):
        st,_=m.select(f'"{folder}"',readonly=True)
        if st!="OK": continue
        _,data=m.search(None,"SINCE","28-Aug-2026")
        ids=(data[0].split() if data and data[0] else [])
        for i in ids:
            t,d=m.fetch(i,"(RFC822)")
            if t!="OK" or not d or not d[0]: continue
            msg=email.message_from_bytes(d[0][1])
            frm=dh(msg.get("From")); mid=msg.get("Message-ID") or f"{folder}:{i.decode()}"
            import re
            addr=(re.search(r"[\w.%+-]+@[\w.-]+", frm) or [None])
            addr=addr.group(0).lower() if hasattr(addr,"group") else None
            if not addr or addr not in addrs: continue
            scanned+=1
            if mid in seen: continue
            subj=dh(msg.get("Subject")) or "(no subject)"
            # skip our own outbound onboarding (from us) — we only want inbound FROM the student
            body=""
            for part in msg.walk():
                if part.get_content_type()=="text/plain":
                    try: body=part.get_payload(decode=True).decode(errors="ignore"); break
                    except: pass
            if DRY:
                print(f"  DRY would create task: {addrs[addr]} | {subj[:50]}"); made+=1; seen.add(mid); continue
            tid=make_task(addrs[addr], addr, subj, body)
            print(f"  + task {tid}: {addrs[addr]} | {subj[:50]}")
            seen.add(mid); made+=1
    try: m.logout()
    except: pass
    if not DRY: json.dump(sorted(seen),open(STATE,"w"),indent=0)
    print(f"{'DRY ' if DRY else ''}capstone emails: matched {scanned} from capstone accounts | new tasks {made}")

# ── OUTPUT eval (exo3 R5): `capstone_email_capture.py selftest` ─────────────
# Read-only: fixture run against a fake IMAP mailbox + fake task creator in a temp dir (no Bridge
# login, no Supabase write), then Supabase GET-only checks of the real tasks this job made.
def _selftest_fixture():
    import tempfile, shutil, types
    g=globals(); saved={k:g[k] for k in ("STATE","USERS","make_task","imaplib","DRY")}
    tmp=tempfile.mkdtemp(prefix="capemail-selftest-"); res=[]
    def raw(mid, frm, subj):
        return (f"Message-ID: <{mid}>\r\nFrom: {frm}\r\nSubject: {subj}\r\nContent-Type: text/plain\r\n\r\nhello").encode()
    box=[raw("m1@x","Stu Dent <stu@utdallas.edu>","Question 1"), raw("m2@x","Other <other@gmail.com>","Spam"),
         raw("m1@x","Stu Dent <stu@utdallas.edu>","Question 1")]   # same Message-ID delivered twice
    class FakeIMAP:
        def __init__(self,*a): pass
        def starttls(self): pass
        def login(self,*a): pass
        def select(self,*a,**k): return "OK",[b""]
        def search(self,*a): return "OK",[" ".join(str(i+1) for i in range(len(box))).encode()]
        def fetch(self,i,_): return "OK",[(b"",box[int(i)-1])]
        def logout(self): pass
    made=[]
    try:
        json.dump([{"email":"stu@utdallas.edu","name":"Stu Dent","role":"early_adopter","project":"Payload Sales"}],
                  open(os.path.join(tmp,"users.json"),"w"))
        g.update(STATE=os.path.join(tmp,"seen.json"), USERS=os.path.join(tmp,"users.json"), DRY=False,
                 imaplib=types.SimpleNamespace(IMAP4=FakeIMAP),
                 make_task=lambda n,a,sj,b: made.append((n,a,sj)) or len(made))
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            main(); main()
        res.append(("fixture: one task per Message-ID across duplicate delivery + re-run", len(made)==1))
        res.append(("fixture: non-capstone sender ignored", all(a=="stu@utdallas.edu" for _,a,_ in made)))
        res.append(("fixture: seen-state persisted", json.load(open(g["STATE"]))==["<m1@x>"]))
    finally:
        g.update(saved); shutil.rmtree(tmp,ignore_errors=True)
    return res

def _selftest_live():
    res=[]
    try:
        seen=json.load(open(STATE)) if os.path.exists(STATE) else []
        res.append((f"live: seen-state is a unique list ({len(seen)} ids)", isinstance(seen,list) and len(seen)==len(set(seen))))
    except Exception as e:
        res.append((f"live: seen-state unreadable {e}", False))
    try:
        r=urllib.request.Request(SB+"/tasks?select=id,title,description,assigned_email&source=eq.capstone-email&order=id",headers=SBH)
        with urllib.request.urlopen(r,timeout=30) as x: rows=json.load(x)
        c={}
        for t in rows: c.setdefault((t.get("title"),t.get("description")),[]).append(t["id"])
        dup=[v for v in c.values() if len(v)>1]
        res.append((f"live: no duplicate capstone-email tasks ({len(rows)} tasks)"+(f" -> {dup[:5]}" if dup else ""), not dup))
        bad=[t["id"] for t in rows if (t.get("assigned_email") or "").lower()!=LIZI]
        res.append(("live: every capstone-email task assigned to Lizi"+(f" -> {bad}" if bad else ""), not bad))
    except Exception as e:
        res.append((f"live: Supabase read error {e}", False))
    return res

def selftest():
    res=_selftest_fixture()+_selftest_live()
    for n,ok in res: print(("PASS " if ok else "FAIL ")+n)
    nf=sum(1 for _,ok in res if not ok)
    print(f"capstone_email_capture selftest: {'PASS' if not nf else 'FAIL'} ({len(res)-nf}/{len(res)})")
    return 0 if not nf else 1

if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="selftest": sys.exit(selftest())
    main()
