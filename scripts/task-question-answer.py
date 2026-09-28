#!/usr/bin/env python3
"""task-question-answer.py — the ACCOUNTABILITY loop for @Exobot task-note support requests.

The @Exobot note on a task is how the whole team gets support. Every request MUST get a substantive
response on the task, tracked to closure — questions AND directives.

task-note-command.py routes each @Exobot note to a triage task (source=task-note-command):
  - QUESTION  → tag 'needs-attention'
  - DIRECTIVE → tag 'needs-owner' (when routed to Exo) or assigned to a person
This resolver (launchd ~2 min) finds every OPEN Exo-owned request and, via an ISOLATED main-agent
turn, produces a substantive response:
  - question  → answer it
  - safe/internal directive → do it (gather/draft/prepare) and report
  - external/irreversible/needs-a-decision → prepare it + post exactly what's needed from John (Exos
    guardrail: no external sends without John's go)
It posts the response on the ORIGINAL task, marks the triage Done, and clears the 'awaiting-exo-answer'
flag when fully resolved (keeps it flagged/visible when the request now needs the user).

ACCOUNTABILITY BACKSTOP: any request open past SLA_MIN without a response → DM John once, so a
failure of this loop is never silent. Never posts to a chat channel except that escalation DM.
"""
import os, json, re, subprocess, tempfile, urllib.request, urllib.parse, hashlib, time
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
STATE = os.path.join(WS, "logs", "task-question-answer-state.json")
LOG = os.path.join(WS, "logs", "task-question-answer.log")
JON = "1501632195163590739"
MAX_TRIES = 3
SLA_MIN = 20            # a request open longer than this with no response → escalate to John


def log(m):
    try:
        with open(LOG, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception:
        pass


def sub_env():
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.21.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    return env


def supa(method, path, body=None):
    req = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode(); return json.loads(t) if t else []
    except Exception as e:
        log(f"WARN supa {method} {path[:60]}: {e}"); return None


def dm_jon(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", "user:" + JON, "-m", text],
                       capture_output=True, text=True, timeout=60, env=sub_env())
    except Exception as e:
        log(f"WARN dm_jon: {e}")


def extract_reply(jdata):
    res = (jdata or {}).get("result", {}) or {}
    pls = res.get("payloads", []) or []
    txt = "\n".join((p.get("text") or "").strip() for p in pls if p.get("text")).strip()
    if not txt:
        txt = ((res.get("meta", {}) or {}).get("finalAssistantVisibleText") or "").strip()
    return txt


def parse_request(desc):
    origid = None
    m = re.search(r"task #(\d+)", desc or "")
    if m:
        origid = m.group(1)
    rm = re.search(r"Directive:\s*(.*)", desc or "", re.S) or re.search(r"\):\s*(.*)", desc or "", re.S)
    req = (rm.group(1) if rm else desc or "").strip()
    req = re.sub(r"\.\s*(Exo to review.*|Exo to own.*)$", "", req).strip()
    return origid, req


def resolve(origid, request, ctx):
    prompt = (
        "You are Exo, resolving a support request a teammate posted with @Exobot on Mission Control "
        f"task #{origid}. Your job: get them an answer or get it done — never leave it unaddressed.\n\n"
        f"REQUEST (from the note): {request}\n\n"
        f"TASK #{origid}: {ctx.get('title','')}\n"
        f"TASK CONTEXT:\n{(ctx.get('description') or '')[:2500]}\n\n"
        "Handle it:\n"
        "1. QUESTION → answer clearly and correctly from the task/context (use Bash/curl against our "
        "Supabase or files if you need more). If you genuinely can't, state exactly what's missing and who can provide it.\n"
        "2. DIRECTIVE that is SAFE and INTERNAL (gather info, draft a doc, prepare/stage something, read data) "
        "→ actually DO it now with your tools, then report what you did and where it is.\n"
        "3. DIRECTIVE needing an EXTERNAL send, a spend, or anything irreversible/consequential → DO NOT execute "
        "it autonomously. Prepare it (draft/plan) and state exactly what you need from John to proceed. "
        "(Standing Exos guardrail: no external sends without John's go.)\n\n"
        "Then return ONLY a JSON object (no prose outside it):\n"
        '{"response":"<concise message to post on the task, <=1200 chars>","resolved":true|false}\n'
        "resolved=true only if the request is fully handled and needs nothing further from the user; "
        "false if it now needs John's decision/input. Do NOT post to the task yourself — just return the JSON."
    )
    pf = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
            tf.write(prompt); pf = tf.name
        skey = "agent:main:taskresolve-" + hashlib.sha1((origid + request).encode()).hexdigest()[:12]
        r = subprocess.run([OPENCLAW, "agent", "--session-key", skey, "--message-file", pf, "--json"],
                           capture_output=True, text=True, timeout=420, env=sub_env())
        raw = extract_reply(json.loads(r.stdout))
        m = re.search(r"\{.*\}", raw, re.S)
        obj = json.loads(m.group(0)) if m else {"response": raw, "resolved": False}
        resp = (obj.get("response") or "").strip()
        return resp, bool(obj.get("resolved")), r.returncode
    finally:
        if pf:
            try: os.unlink(pf)
            except Exception: pass


def sweep_stale_flags():
    """Self-heal: strip 'awaiting-exo-answer' from any task that is already Done or already has a
    posted '✅ Exo:' answer. Catches flags that leaked past the resolve loop (e.g. a transient
    Supabase failure on the clear PATCH, or an answer posted before this guard existed)."""
    tagged = supa("GET", "tasks?select=id,state,tags&tags=cs.%7Bawaiting-exo-answer%7D&limit=200") or []
    for t in tagged:
        tid = str(t.get("id"))
        answered = False
        if t.get("state") == "Done":
            answered = True
        else:
            notes = supa("GET", f"activities?select=body&subject=eq.task:{tid}"
                                f"&type=eq.task_note&order=created_at.desc&limit=10") or []
            answered = any(str(n.get("body") or "").lstrip().startswith("✅ Exo:") for n in notes)
        if answered:
            tags = [x for x in (t.get("tags") or []) if x != "awaiting-exo-answer"]
            supa("PATCH", f"tasks?id=eq.{tid}", {"tags": tags})
            log(f"sweep: cleared stale awaiting-exo-answer on task #{tid} (state={t.get('state')})")


def main():
    sweep_stale_flags()
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {"seen": [], "fails": {}, "escalated": []}
    seen = set(st.get("seen", [])); fails = st.get("fails", {}); escalated = set(st.get("escalated", []))

    # Recency window: resolve requests from the last 14 days (avoids replaying ancient backlog in one
    # burst; older stuck items can be swept deliberately).
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    rows = []
    for tag in ("needs-attention", "needs-owner"):
        q = (f"tasks?select=id,title,description,state,tags,source,created_at&source=eq.task-note-command"
             f"&state=neq.Done&tags=cs.%7B{tag}%7D&created_at=gte.{urllib.parse.quote(since)}"
             f"&order=id.desc&limit=50")
        rows += (supa("GET", q) or [])
    # de-dup by id
    byid = {}
    for t in rows:
        byid[str(t.get("id"))] = t
    rows = list(byid.values())
    if not rows:
        return

    now = datetime.now(timezone.utc)
    for t in rows:
        tid = str(t.get("id"))
        if tid in seen:
            continue
        origid, request = parse_request(t.get("description") or "")
        if not origid:
            seen.add(tid); continue
        orig = supa("GET", f"tasks?id=eq.{origid}&select=id,title,description") or []
        ctx = orig[0] if orig else {}
        try:
            resp, resolved, rc = resolve(origid, request, ctx)
        except Exception as e:
            resp, resolved, rc = "", False, -1
            log(f"resolve exception t{tid}: {e}")

        if not resp:
            n = fails.get(tid, 0) + 1; fails[tid] = n
            log(f"FAILED resolve triage {tid} (orig {origid}) try {n}/{MAX_TRIES} rc={rc}")
            # SLA backstop: if it's been failing/open too long, escalate to John (once)
            age_min = _age_min(t.get("created_at"), now)
            if (n >= MAX_TRIES or age_min >= SLA_MIN) and tid not in escalated:
                dm_jon(f"⚠️ @Exobot request needs you — I couldn't auto-resolve it. Task #{origid}: "
                       f"“{request[:140]}”. It's flagged at the top of Mission Control.")
                escalated.add(tid)
                if n >= MAX_TRIES:
                    seen.add(tid); fails.pop(tid, None)
            continue

        # Post the substantive response on the ORIGINAL task.
        supa("POST", "activities", {"type": "task_note", "subject": f"task:{origid}",
             "body": "✅ Exo: " + resp, "owner": "Exo", "status": "completed"})
        supa("PATCH", f"tasks?id=eq.{tid}", {"state": "Done"})
        # A substantive answer is posted → Exo is no longer the blocker, so ALWAYS clear the
        # "awaiting-exo-answer" chip. The chip means "Exo owes an answer"; once answered it is
        # misleading to keep it lit (even when the ball is now in John's court — that path is
        # surfaced via the dm_jon escalation below, not by leaving this flag on).
        cur = supa("GET", f"tasks?id=eq.{origid}&select=tags") or []
        if cur:
            tags = [x for x in (cur[0].get("tags") or []) if x != "awaiting-exo-answer"]
            supa("PATCH", f"tasks?id=eq.{origid}", {"tags": tags})
        # If it now needs John, keep it visible via a one-time DM (not a stale board chip).
        if not resolved and tid not in escalated:
            dm_jon(f"↩️ @Exobot answered task #{origid} but it now needs you — “{request[:140]}”. "
                   f"My reply is on the task.")
            escalated.add(tid)
        seen.add(tid); fails.pop(tid, None)
        log(f"resolved triage {tid} -> task #{origid} (resolved={resolved}, chip cleared)")

    st["seen"] = list(seen)[-3000:]; st["fails"] = fails; st["escalated"] = list(escalated)[-500:]
    json.dump(st, open(STATE, "w"))


def _age_min(created_iso, now):
    try:
        c = datetime.fromisoformat(str(created_iso).replace("Z", "+00:00"))
        if c.tzinfo is None:
            c = c.replace(tzinfo=timezone.utc)
        return (now - c).total_seconds() / 60.0
    except Exception:
        return 0.0


if __name__ == "__main__":
    main()
