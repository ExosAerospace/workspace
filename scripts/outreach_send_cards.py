#!/usr/bin/env python3
"""outreach_send_cards.py — Send-now cards for gov/investor email from jquinn@exosaero.com (D-7282193).

  post <card.json>   create a Decision card: [Send now] [Put in my Outlook Drafts] [Hold]
  run                (launchd com.exos.outreach-send-cards, every 120s) act on answered cards:
                     Send now -> outreach_graph_send.py send; Drafts -> ... draft; Hold -> nothing.
                     A note on the card ("note: ...") is NOT auto-merged; Exo revises and re-posts.
Each card is acted on exactly once (state/outreach-send-cards.json). Only Jon's per-card answer sends.
"""
import json, os, sys, subprocess, urllib.request, html, re
WS = "/Users/exomac/.openclaw/workspace"
CARDS = os.path.join(WS, "drafts", "outreach_cards")
STATE = os.path.join(WS, "state", "outreach-send-cards.json")
DEC = os.path.join(WS, "mission-control", "data", "decisions.json")
SEND = [sys.executable, os.path.join(WS, "scripts", "outreach_graph_send.py")]
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
               "proposedAction": "Send now = goes out from your mailbox immediately (in Sent Items). Outlook Drafts = formatted draft in your Drafts folder. Hold = nothing sent; add a note and Exo revises.",
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
        p = subprocess.run(SEND + [mode, s["card"]], capture_output=True, text=True, timeout=120)
        s["done"] = (mode + ": " + p.stdout.strip()) if p.returncode == 0 else None
        s["last_error"] = None if p.returncode == 0 else p.stderr[-400:]
        print(key, mode, p.returncode, p.stdout.strip() or p.stderr[-200:])
    json.dump(st, open(STATE, "w"), indent=1)


if __name__ == "__main__":
    post(sys.argv[2]) if sys.argv[1] == "post" else run()
