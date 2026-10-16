#!/usr/bin/env python3
"""team_email_task_tracker.py — team-wide sent/reply → task tracking via M365 (metadata only).

For each active @exosaero.com employee, reads their Sent Items + Inbox via Microsoft Graph
(Mail.ReadBasic.All, GCC High .us, headers ONLY — recipients/sender/date/subject, never bodies).
Matches each outbound to a task the SAME employee owns (high-confidence: contact org/name in the
task title), annotates "📤 sent … / ⏳ awaiting reply", and closes the loop when a reply arrives.
No Bcc habit needed — it reads the mailbox directly.

GOVERNANCE: only run team-wide AFTER the staff notice is out. Test safely with:
    python3 team_email_task_tracker.py --only jquinn@exosaero.com --dry-run
Full team (all @exosaero active users): python3 team_email_task_tracker.py   (writes; gated by --go)
"""
import json, os, sys, re, time, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
USERS = os.path.join(WS, "mission-control", "users.json")
LOG = os.path.join(WS, "logs", "team-followup-log.json")
MARK = os.path.join(WS, "logs", "team-followup-annotated.json")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
SKEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
SBH = {"apikey": SKEY, "Authorization": "Bearer " + SKEY, "Content-Type": "application/json", "Prefer": "return=representation"}
LOOKBACK = 45
EMAILRE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
COMMON = {"gmail", "outlook", "hotmail", "yahoo", "proton", "pm", "me", "icloud", "aol", "exosaero"}


def sb(method, path, body=None):
    r = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None, headers=SBH)
    try:
        with urllib.request.urlopen(r, timeout=40) as x:
            t = x.read().decode(); return json.loads(t) if t else []
    except Exception:
        return None


def gtoken():
    s = json.load(open(SECRETS))
    login = s.get("ms_graph_login_host", "login.microsoftonline.us")
    graph = s.get("ms_graph_api_host", "graph.microsoft.us")
    data = urllib.parse.urlencode({"client_id": s["ms_graph_client_id"], "client_secret": s["ms_graph_client_secret"],
        "scope": f"https://{graph}/.default", "grant_type": "client_credentials"}).encode()
    tok = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://{login}/{s['ms_graph_tenant_id']}/oauth2/v2.0/token", data=data, method="POST"), timeout=30).read())["access_token"]
    return tok, graph


def _fetch(url, tok):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=45).read()


def gget(url, tok, fetch=None, tries=3):
    # Graph occasionally returns a truncated/garbled body (JSONDecodeError) or drops the
    # connection; retry those. HTTPError (4xx/5xx) propagates to the per-mailbox handler.
    fetch = fetch or _fetch
    for i in range(tries):
        try:
            return json.loads(fetch(url, tok))
        except urllib.error.HTTPError:
            raise
        except (ValueError, urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if i == tries - 1: raise
            time.sleep(2 * (i + 1))


def folder_msgs(graph, tok, mbx, folder, select, since_field):
    since = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK)).strftime("%Y-%m-%dT%H:%M:%SZ")
    qs = urllib.parse.urlencode({"$select": select, "$top": "200", "$filter": f"{since_field} ge {since}"},
                                quote_via=urllib.parse.quote, safe="")
    url = f"https://{graph}/v1.0/users/{mbx}/mailFolders/{folder}/messages?{qs}"
    out = []; pages = 0
    while url and pages < 20:
        d = gget(url, tok); out += d.get("value", []); url = d.get("@odata.nextLink"); pages += 1
    return out


def org(addr):
    b = addr.split("@")[-1].split(".")[0].lower()
    return "" if b in COMMON else b


def names(addr):
    return [t for t in re.split(r"[._+\-]", addr.split("@")[0].lower()) if len(t) >= 3]


def selftest():
    # replays 2026-10-16 failure: truncated Graph JSON page → JSONDecodeError killed the whole run
    calls = []
    def flaky(url, tok):
        calls.append(1)
        return b'{"value": [{"a": 1} {"b"' if len(calls) == 1 else b'{"value": [{"a": 1}]}'
    real_sleep = time.sleep; time.sleep = lambda s: None
    try:
        assert gget("u", "t", fetch=flaky) == {"value": [{"a": 1}]} and len(calls) == 2
        try:
            gget("u", "t", fetch=lambda u, t: b'{"bad"'); assert False, "should raise"
        except ValueError:
            pass
    finally:
        time.sleep = real_sleep
    print("selftest OK")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    dry = "--dry-run" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1].lower() if "--only" in sys.argv else None
    go = "--go" in sys.argv

    u = json.load(open(USERS)); users = u if isinstance(u, list) else u.get("users", [])
    emps = [(x.get("name"), (x.get("email") or "").lower()) for x in users
            if (x.get("email") or "").lower().endswith("@exosaero.com") and x.get("active") is not False]
    if only:
        emps = [e for e in emps if e[1] == only]
    elif not go and not dry:
        print("Refusing team-wide run without --go (governance: send the staff notice first). Use --only <email> --dry-run to test.")
        return
    if not emps:
        print("no matching employees"); return

    # tasks grouped by owner-name → email index from that owner's tasks
    tasks = []; off = 0
    while True:
        c = sb("GET", f"tasks?select=id,title,description,state,owner&order=id.asc&limit=1000&offset={off}") or []
        tasks += c
        if len(c) < 1000: break
        off += 1000
    by_owner = {}
    for t in tasks:
        ow = (t.get("owner") or "").lower()
        by_owner.setdefault(ow, []).append(t)

    tok, graph = gtoken()
    log = {}
    try: log = json.load(open(LOG))
    except Exception: log = {}
    marks = {}
    try: marks = json.load(open(MARK))
    except Exception: marks = {}

    for name, mbx in emps:
        try:
            sent = folder_msgs(graph, tok, mbx, "sentitems", "toRecipients,sentDateTime,subject", "sentDateTime")
            inbox = folder_msgs(graph, tok, mbx, "inbox", "from,receivedDateTime", "receivedDateTime")
        except urllib.error.HTTPError as e:
            print(f"  {mbx}: Graph {e.code} — skipping"); continue
        except (ValueError, urllib.error.URLError, OSError) as e:
            print(f"  {mbx}: Graph read failed after retries ({type(e).__name__}: {str(e)[:120]}) — skipping"); continue
        inbound = {}
        for m in inbox:
            a = ((m.get("from", {}) or {}).get("emailAddress", {}) or {}).get("address", "").lower()
            dt = m.get("receivedDateTime", "")
            if a and dt > inbound.get(a, ""): inbound[a] = dt
        # this employee's tasks + email index
        mytasks = by_owner.get((name or "").lower(), [])
        eidx = {}
        for t in mytasks:
            for e in set(EMAILRE.findall((t.get("title", "") + " " + (t.get("description") or "")).lower())):
                eidx.setdefault(e, []).append(t)
        contacts = {}
        annos = 0
        for m in sent:
            subj = (m.get("subject") or "")[:120]
            dt = m.get("sentDateTime", "")
            for rc in (m.get("toRecipients") or []):
                a = ((rc.get("emailAddress", {}) or {}).get("address", "") or "").lower()
                if not a or a.endswith("@exosaero.com"): continue
                c = contacts.setdefault(a, {"last_sent": "", "subj": "", "task_id": None, "replied": False})
                if dt > c["last_sent"]: c["last_sent"], c["subj"] = dt, subj
                # high-conf task match among THIS employee's tasks
                if not c["task_id"]:
                    for t in eidx.get(a, []):
                        title = (t.get("title") or "").lower()
                        if (org(a) and org(a) in title) or any(n in title for n in names(a)):
                            c["task_id"] = t["id"]; break
        # reply detection
        for a, c in contacts.items():
            r = inbound.get(a)
            if r and c["last_sent"] and r > c["last_sent"]:
                c["replied"] = True
        # annotate high-conf tasks (idempotent)
        if not dry:
            for a, c in contacts.items():
                if not c["task_id"] or not c["last_sent"]: continue
                key = f"{c['task_id']}|{a}|{c['last_sent'][:10]}"
                if marks.get(key): continue
                sb("POST", "activities", {"type": "task_note", "subject": f"task:{c['task_id']}",
                   "body": f"📤 {name} emailed {a} on {c['last_sent'][:10]} — {c['subj']}" + ("" if c['replied'] else "  ·  ⏳ awaiting reply"),
                   "owner": "Exo", "status": "completed"})
                marks[key] = True; annos += 1
            log[mbx] = {"name": name, "contacts": contacts, "updated": datetime.now(timezone.utc).isoformat()}
        aw = sum(1 for c in contacts.values() if c["last_sent"] and not c["replied"])
        matched = sum(1 for c in contacts.values() if c["task_id"])
        print(f"  {mbx}: {len(sent)} sent / {len(contacts)} contacts · matched-to-own-task {matched} · awaiting {aw} · annotations {'(dry)' if dry else annos}")

    if not dry:
        json.dump(log, open(LOG, "w"), indent=2); json.dump(marks, open(MARK, "w"), indent=2)
    print("done" + (" [dry-run — nothing written]" if dry else ""))


if __name__ == "__main__":
    main()
