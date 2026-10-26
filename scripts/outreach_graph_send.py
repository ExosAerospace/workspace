#!/usr/bin/env python3
"""outreach_graph_send.py — one-click outreach from Jon's real mailbox (jquinn@exosaero.com).

Delegated Graph (GCC High) via the "Exos Outreach Sender" app, signed in by Jon himself
(D-7282193, 2026-10-26). No application permissions: it can only act as Jon.
Refresh token in ~/.openclaw/secrets.json (ms_outreach_refresh_token, rotated on every use).

  outreach_graph_send.py whoami
  outreach_graph_send.py send   <msg.json>   # sends now; copy lands in Jon's Sent Items
  outreach_graph_send.py draft  <msg.json>   # puts a fully formatted draft in Jon's Outlook Drafts
msg.json: {"to":[..], "cc":[..], "subject":"..", "html":"..body without signature.."}
Every message gets Jon's signature appended (Outlook does not add it to API-sent mail).
Callers must only run send/draft after Jon's per-email approval.
"""
import json, os, sys, urllib.request, urllib.parse, html

SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
LOGIN, G = "https://login.microsoftonline.us", "https://graph.microsoft.us"
BOOK = "https://outlook.office365.us/bookwithme/user/3d1b68ea7e5643f9b2e76624f9dfd95f%40exosaero.com?anonymous&ismsaljsauthenabled"
SIGNATURE = f"""<p style="margin-top:16px">John Quinn<br>Cofounder and CEO<br>Exos Aerospace Systems &amp; Technologies, Inc.<br>
Mob. +1-972-740-8355<br>Address: 299 FM 1903&nbsp; Greenville, TX 75402<br>Website: <a href="https://www.exosaero.com">www.exosaero.com</a><br>
Exos Aerospace Italia, Srl<br>C/o I3P Scpa<br>C.so Castelfidardo 30/A<br>10129 Torino</p>
<p>Check out our Youtube @ <a href="https://www.youtube.com/channel/UCh2dmwg4BVRAznfQgdhTm7w">https://www.youtube.com/channel/UCh2dmwg4BVRAznfQgdhTm7w</a></p>
<p><b>Leadership is changing.</b><br>Exos leaders are shifting from directing work to designing systems where humans and our AI can collaborate effectively.</p>
<p><a href="{BOOK}">Book time to meet with me</a></p>"""


def token():
    s = json.load(open(SECRETS))
    d = urllib.parse.urlencode({"client_id": s["ms_outreach_client_id"], "grant_type": "refresh_token",
                                "refresh_token": s["ms_outreach_refresh_token"],
                                "scope": f"{G}/Mail.Send {G}/Mail.ReadWrite {G}/User.Read offline_access"}).encode()
    t = json.loads(urllib.request.urlopen(f"{LOGIN}/{s['ms_graph_tenant_id']}/oauth2/v2.0/token", d, timeout=30).read())
    if t.get("refresh_token"):
        s = json.load(open(SECRETS)); s["ms_outreach_refresh_token"] = t["refresh_token"]
        tmp = SECRETS + ".tmp"; json.dump(s, open(tmp, "w"), indent=2); os.chmod(tmp, 0o600); os.replace(tmp, SECRETS)
    return t["access_token"]


def call(method, path, body=None):
    r = urllib.request.Request(G + "/v1.0" + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Authorization": "Bearer " + token(), "Content-Type": "application/json"}, method=method)
    b = urllib.request.urlopen(r, timeout=60).read()
    return json.loads(b) if b else {}


def message(m):
    rcpt = lambda xs: [{"emailAddress": {"address": a}} for a in (xs or [])]
    return {"subject": m["subject"], "body": {"contentType": "HTML", "content": m["html"] + SIGNATURE},
            "toRecipients": rcpt(m.get("to")), "ccRecipients": rcpt(m.get("cc"))}


def main():
    cmd = sys.argv[1]
    if cmd == "whoami":
        print(call("GET", "/me?$select=userPrincipalName,mail,displayName")); return
    m = json.load(open(sys.argv[2]))
    if cmd == "send":
        call("POST", "/me/sendMail", {"message": message(m), "saveToSentItems": True}); print("SENT", m["subject"])
    elif cmd == "draft":
        d = call("POST", "/me/messages", message(m)); print("DRAFT", d.get("webLink", d.get("id")))


if __name__ == "__main__":
    main()
