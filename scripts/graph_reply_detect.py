#!/usr/bin/env python3
"""graph_reply_detect.py — close the awaiting-reply loop using M365 (metadata only).

Reads Jon's Inbox via Microsoft Graph with Mail.ReadBasic.All (headers ONLY — from + receivedDateTime,
never bodies), on the GCC High (.us) cloud. For each tracked contact in logs/sent-followup-log.json
that hasn't replied, if an inbound message from that contact arrived AFTER Jon's last send, mark it
replied — so the follow-up nudge only chases genuinely-unanswered threads.

Idempotent, read-only against M365. --dry-run prints, writes nothing.
"""
import json, os, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
LOG = os.path.join(WS, "logs", "sent-followup-log.json")
MAILBOX = "jquinn@exosaero.com"
LOOKBACK_DAYS = 60


def sec():
    return json.load(open(SECRETS))


def token(s):
    login = s.get("ms_graph_login_host", "login.microsoftonline.us")
    graph = s.get("ms_graph_api_host", "graph.microsoft.us")
    data = urllib.parse.urlencode({"client_id": s["ms_graph_client_id"], "client_secret": s["ms_graph_client_secret"],
        "scope": f"https://{graph}/.default", "grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(f"https://{login}/{s['ms_graph_tenant_id']}/oauth2/v2.0/token", data=data, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]


def main():
    dry = "--dry-run" in sys.argv
    s = sec()
    if not s.get("ms_graph_client_id"):
        print("ms_graph creds not configured"); return
    graph = s.get("ms_graph_api_host", "graph.microsoft.us")
    tok = token(s)
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # latest inbound datetime per sender (metadata only)
    qs = urllib.parse.urlencode({"$select": "from,receivedDateTime", "$top": "200",
                                 "$filter": f"receivedDateTime ge {since}"}, quote_via=urllib.parse.quote, safe="")
    url = f"https://{graph}/v1.0/users/{MAILBOX}/mailFolders/inbox/messages?{qs}"
    inbound = {}; pages = 0
    while url and pages < 30:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
        d = json.loads(urllib.request.urlopen(req, timeout=45).read())
        for m in d.get("value", []):
            a = ((m.get("from", {}) or {}).get("emailAddress", {}) or {}).get("address", "").lower()
            dt = m.get("receivedDateTime", "")
            if a and dt and dt > inbound.get(a, ""):
                inbound[a] = dt
        url = d.get("@odata.nextLink"); pages += 1
    print(f"scanned inbox headers: {sum(1 for _ in inbound)} distinct senders (last {LOOKBACK_DAYS}d)")

    doc = json.load(open(LOG)); contacts = doc.get("contacts", {})
    closed = 0
    for a, c in contacts.items():
        if c.get("replied") or c.get("cleared") or not c.get("last_sent"):
            continue
        rep = inbound.get(a.lower())
        if rep and rep > c["last_sent"]:
            if not dry:
                c["replied"] = True; c["last_reply"] = rep; c["reply_source"] = "m365"
            closed += 1
            if closed <= 12:
                print(f"  ✓ reply from {c.get('name', a)} on {rep[:10]} (was awaiting since {c['last_sent'][:10]})")
    print(f"{'[dry-run] would close' if dry else 'closed'} {closed} awaiting-reply loops via M365")
    if not dry and closed:
        tmp = LOG + ".tmp"; json.dump(doc, open(tmp, "w"), indent=2); os.replace(tmp, LOG)


if __name__ == "__main__":
    main()
