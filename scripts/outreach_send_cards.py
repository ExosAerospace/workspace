#!/usr/bin/env python3
"""outreach_send_cards.py — Send-now cards for gov/investor email from jquinn@exosaero.com (D-7282193).

  post <card.json>   create a Decision card: [Send now] [Put in my Outlook Drafts] [Hold]
  run                (launchd com.exos.outreach-send-cards, every 120s) act on answered cards:
                     Send now -> outreach_graph_send.py send; Drafts -> ... draft; Hold -> nothing.
                     Send now / Drafts WITH a note -> Exo is woken to apply the note to the card, then runs
                     `finish <key>` which sends/drafts the revised email (Jon 10/26: "send them once I have added
                     my comments in"). Hold with a note -> Exo revises and re-posts.
Each card is acted on exactly once (state/outreach-send-cards.json). Only Jon's per-card answer sends.
"""
import json, os, sys, subprocess, urllib.request, html, re, shutil
WS = "/Users/exomac/.openclaw/workspace"
CARDS = os.path.join(WS, "drafts", "outreach_cards")
STATE = os.path.join(WS, "state", "outreach-send-cards.json")
DEC = os.path.join(WS, "mission-control", "data", "decisions.json")
SEND = [sys.executable, os.path.join(WS, "scripts", "outreach_graph_send.py")]
REVISER = "agent:main:discord:channel:1501636814849577050"  # #exomac-system applies Jon's card notes
LOGF = "/Users/exomac/.openclaw/logs/outreach-send-cards.log"
OPTS = ["Send now", "Put in my Outlook Drafts", "Hold"]


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def post(path):
    c = json.load(open(path)); key = "outreach-card-" + os.path.basename(path)[:-5]
    text = re.sub(r"<[^>]+>", "\n", c["html"].replace("</p>", "\n")); text = html.unescape(re.sub(r"\n{3,}", "\n\n", text)).strip()
    payload = {"source": "Exo (one-click send)", "title": f"Send: {c['subject']} → {', '.join(c['to'])}",
               "question": (f"To: {', '.join(c['to'])}\nCc: {', '.join(c.get('cc') or []) or '—'}\nSubject: {c['subject']}\n"
                            f"From: jquinn@exosaero.com (your full signature is added)\n\n{text}"),
               "context": f"MC task #{c.get('task')} · {c.get('audience')} · draft {path}",
               "proposedAction": "Add any edits in the note, then pick Send now: Exo applies your edits and it goes out from your mailbox right away (in Sent Items). No note = sends exactly as shown. Outlook Drafts = formatted draft in your Drafts folder. Hold = nothing sent; add a note and Exo revises.",
               "type": "choice", "options": OPTS, "priority": "high", "dedupeKey": key}
    if c.get("attachments"):  # attached file is the document (ingest requires a location for signature-flavored text)
        payload["documentLocation"] = c.get("document_url") or c["attachments"][0]
        payload["question"] += "\n\nAttached: " + ", ".join(os.path.basename(a) for a in c["attachments"])
    tok = open(os.path.join(WS, "mission-control", "data", ".decisions-token")).read().strip()
    r = urllib.request.Request("http://127.0.0.1:8080/api/decisions/ingest", data=json.dumps(payload).encode(),
                               headers={"Content-Type": "application/json", "x-exo-token": tok}, method="POST")
    d = json.loads(urllib.request.urlopen(r, timeout=30).read())
    st = load(STATE, {}); st[key] = {"card": path, "decision": d["id"], "done": None}
    os.makedirs(os.path.dirname(STATE), exist_ok=True); json.dump(st, open(STATE, "w"), indent=1)
    print("POSTED", d["id"], key)


def run():
    st = load(STATE, {}); decs = load(DEC, []); decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    by = {d.get("id"): d for d in decs}
    for key, s in st.items():
        if s.get("done"): continue
        d = by.get(s["decision"]) or {}
        a = str(d.get("answer") or "")
        mode = "send" if a.startswith("Send now") else "draft" if a.startswith("Put in my Outlook") else None
        if a.startswith("Hold"): s["done"] = "held"; continue
        if not mode: continue
        note = str(d.get("note") or "").strip()
        if note:
            if s.get("revising") == d.get("answeredAt"): continue
            s["revising"], s["mode"] = d.get("answeredAt"), mode
            wake(f"{d['id']} answered '{a}' WITH EDITS from Jon. Apply them, then {mode} it.\nJon's note: {note}\n"
                 f"Card file: {os.path.join(WS, s['card'])} (edit its \"html\" body and, only if the note asks, to/cc/subject/"
                 f"attachments; keep Jon's voice, change nothing else). Then run: python3 scripts/outreach_send_cards.py finish {key}\n"
                 "If the note cannot be applied safely (ambiguous, asks for facts you cannot verify), do NOT finish: re-post a "
                 "revised card with `post` and tell Jon why in one line.")
            print(key, "revise-then-" + mode); continue
        p = subprocess.run(SEND + [mode, s["card"]], capture_output=True, text=True, timeout=120)
        s["done"] = (mode + ": " + p.stdout.strip()) if p.returncode == 0 else None
        s["last_error"] = None if p.returncode == 0 else p.stderr[-400:]
        print(key, mode, p.returncode, p.stdout.strip() or p.stderr[-200:])
    json.dump(st, open(STATE, "w"), indent=1)


def wake(text):
    oc = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"
    subprocess.Popen([oc, "agent", "--session-key", REVISER, "-m", text], stdout=open(LOGF, "a"),
                     stderr=subprocess.STDOUT, start_new_session=True, cwd=WS)


def finish(key):  # called by Exo after applying Jon's note: send/draft the revised card exactly once
    st = load(STATE, {}); s = st[key]
    if s.get("done"): print("already", s["done"]); return
    p = subprocess.run(SEND + [s["mode"], s["card"]], capture_output=True, text=True, timeout=120, cwd=WS)
    s["done"] = (s["mode"] + " (revised): " + p.stdout.strip()) if p.returncode == 0 else None
    s["last_error"] = None if p.returncode == 0 else p.stderr[-400:]
    json.dump(st, open(STATE, "w"), indent=1); print(s["done"] or "FAILED " + p.stderr[-300:])
    sys.exit(0 if p.returncode == 0 else 1)


if __name__ == "__main__":
    {"post": lambda: post(sys.argv[2]), "finish": lambda: finish(sys.argv[2])}.get(sys.argv[1], run)()
