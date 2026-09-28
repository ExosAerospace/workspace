#!/usr/bin/env python3
"""reconcile_sent_tasks.py — close ready-to-send MC tasks Jon has ALREADY sent.

The gap (Jon, 2026-08-10, "38 ready to sends, many already sent"): capture agents open a
"SEND: ..." task per outreach, but nothing closes it once Jon actually sends the email from
Outlook. sent-loop-closer.py already learns who Jon has emailed (logs/outreach-sent-registry.json,
built from his BCC'd Proton copies). This joins the two: for every OPEN capture-agent task, pull
the recipient email(s) out of its description/title and, if any is in the sent registry, close
the task (state=Done) with an audit note. That's the reconciliation that was missing.

Only touches source=capture-agent tasks (the ready-to-send queue). Never closes anything without
a positive recipient match in the registry. Dry-run by default; --apply writes + snapshots.
"""
import os, sys, json, re, urllib.request, urllib.parse
from datetime import datetime, timezone

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
REGISTRY = os.path.join(WS, "logs", "outreach-sent-registry.json")
DONE = {"Done", "Completed", "Closed", "Archived", "Cancelled"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
INTERNAL = re.compile(r"(exosaero\.com|jquinnexo@|@pm\.me|@proton\.me|noreply|no-reply)", re.I)

def _key():
    return json.load(open(SECRETS))["supabase_service_role_key"]

def q_all(select, extra=""):
    k = _key(); out = []; off = 0
    while True:
        p = f"{SB}/tasks?select={select}{extra}&order=id&offset={off}&limit=1000"
        req = urllib.request.Request(p, headers={"apikey": k, "Authorization": f"Bearer {k}"})
        c = json.load(urllib.request.urlopen(req, timeout=60)); out += c
        if len(c) < 1000: return out
        off += 1000

def patch(tid, fields):
    k = _key()
    req = urllib.request.Request(f"{SB}/tasks?id=eq.{tid}", data=json.dumps(fields).encode(),
        headers={"apikey": k, "Authorization": f"Bearer {k}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()

# Send-ready markers in a task TITLE. Tasks like "[READY to send - Laura Stowe]" or
# "[SUBMIT-READY] Decline to 5DCP" come from many sources, not just capture agents. Before
# 2026-09-28 only source=capture-agent was reconciled, and 10 already-sent tasks sat open for months.
READY_RE = re.compile(r"(ready[ _-]*to[ _-]*send|\[ready|submit-ready|^\s*send\s*[:—-]|call card)", re.I)
M365_CACHE = os.path.join(WS, "logs", "m365-sent-cache.json")
M365_TTL = 30 * 60  # Outlook Sent Items refresh at most every 30 min (this runs every 2 min)


def m365_sends():
    """recipient -> latest {sent_date, subject} from Jon's OUTLOOK Sent Items (Graph, headers only).
    This covers sends Jon didn't BCC to Proton. The BCC registry alone missed most of them."""
    import time
    cache = {}
    if os.path.exists(M365_CACHE):
        try: cache = json.load(open(M365_CACHE))
        except Exception: cache = {}
    if time.time() - cache.get("fetched", 0) < M365_TTL:
        return cache.get("sent", {})
    try:
        import importlib.util as _u
        spec = _u.spec_from_file_location("tett", os.path.join(WS, "scripts", "team_email_task_tracker.py"))
        tt = _u.module_from_spec(spec); spec.loader.exec_module(tt)
        tt.LOOKBACK = 185
        tok, graph = tt.gtoken()
        msgs = tt.folder_msgs(graph, tok, "jquinn@exosaero.com", "sentitems",
                              "toRecipients,ccRecipients,bccRecipients,sentDateTime,subject", "sentDateTime")
    except Exception as ex:
        print(f"  (m365 sent fetch failed, using cache: {ex})")
        return cache.get("sent", {})
    sent = {}
    for m in msgs:
        d = (m.get("sentDateTime") or "")[:16].replace("T", " ")
        for k in ("toRecipients", "ccRecipients", "bccRecipients"):
            for r in m.get(k) or []:
                a = (r.get("emailAddress", {}).get("address") or "").lower()
                if a and not INTERNAL.search(a):
                    cur = sent.get(a, {}).get("sent_dates", [])
                    sent[a] = {"sent_dates": sorted(set(cur + [d])), "subject": m.get("subject", "")}
    json.dump({"fetched": time.time(), "sent": sent}, open(M365_CACHE, "w"))
    return sent


def main():
    apply = "--apply" in sys.argv
    if not os.path.exists(REGISTRY):
        print("No sent registry yet — run sent-loop-closer.py first."); return
    reg = json.load(open(REGISTRY))
    # recipient -> list of send dates (+ a subject), merged from the Proton BCC registry and Outlook
    sent = {}
    for e, v in reg.items():
        e = e.split()[0].lower()
        if v.get("sent_date"):
            sent.setdefault(e, {"dates": [], "subject": v.get("subject", "")})["dates"].append(v["sent_date"][:16])
    for e, v in m365_sends().items():
        sent.setdefault(e, {"dates": [], "subject": v.get("subject", "")})["dates"] += v["sent_dates"]
        sent[e]["subject"] = v.get("subject") or sent[e]["subject"]

    tasks = q_all("id,title,description,state,source,category,created_at")
    cap = [t for t in tasks
           if (t.get("state") or "") not in DONE
           and (t.get("source") == "capture-agent" or READY_RE.search(t.get("title") or ""))]

    hits = []
    for t in cap:
        blob = f"{t.get('title','')}\n{t.get('description','')}"
        # prefer the explicit TO: line, else any external email in the block
        to_line = ""
        m = re.search(r"(?im)^\s*TO:\s*(.+)$", blob)
        if m: to_line = m.group(1)
        cand = EMAIL_RE.findall(to_line) or EMAIL_RE.findall(blob)
        for e in cand:
            el = e.lower()
            if INTERNAL.search(el):
                continue
            if el in sent:
                # only a send ON/AFTER the task was created counts — an older email to the same
                # person is a different conversation
                created = (t.get("created_at") or "")[:16].replace("T", " ")
                after = sorted(d for d in sent[el]["dates"] if d >= created)
                if after:
                    hits.append((t, el, {"sent_date": after[-1], "subject": sent[el]["subject"]})); break

    print(f"Open send-ready tasks (capture-agent + READY-titled): {len(cap)} | already-sent matches: {len(hits)}")
    for t, e, info in hits:
        print(f"  #{t['id']}  {(t.get('title') or '')[:60]}")
        print(f"         -> sent to {e} on {info.get('sent_date')}")

    if not apply:
        print("\nDRY RUN — re-run with --apply to close these as Done.")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    snap = [{"id": t["id"], "prev_state": t.get("state"), "matched": e} for t, e, _ in hits]
    sp = os.path.join(WS, "mission-control/data", f"reconcile-sent-snapshot-{stamp}.json")
    json.dump(snap, open(sp, "w"), indent=2)
    print(f"\nSnapshot: {sp}")
    ok = err = 0
    for t, e, info in hits:
        note = f"[auto-closed {datetime.now():%Y-%m-%d}] Already sent to {e} on {info.get('sent_date')} (sent-registry match)."
        newdesc = ((t.get("description") or "") + "\n\n" + note)[:8000]
        try:
            patch(t["id"], {"state": "Done", "description": newdesc}); ok += 1
        except Exception as ex:
            err += 1; print(f"  ERR {t['id']}: {ex}")
    print(f"Closed {ok} already-sent tasks ({err} errors).")

if __name__ == "__main__":
    main()
