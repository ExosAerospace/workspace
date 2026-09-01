#!/usr/bin/env python3
"""task-question-answer.py — answer @Exobot QUESTION notes on tasks, SILENTLY.

task-note-command.py routes a question (@Exobot <question> posted on a task) to an Exo triage
task (source=task-note-command, tag 'needs-attention'). This dispatcher finds those unanswered
triage tasks, uses an ISOLATED agent turn (openclaw agent --session-key … --json) to compose a
grounded answer, posts the answer as an Update on the ORIGINAL task, and closes the triage task.

Runs via launchd (~2 min). If there are NO pending question tasks it exits immediately and NEVER
writes to any chat channel (the earlier main-session cron polluted the channel on idle firings —
this replaces it). Idempotent via a seen-set with a retry cap.
"""
import json, os, re, subprocess, tempfile, urllib.request, hashlib
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"
STATE = os.path.join(WS, "logs", "task-question-answer-state.json")
LOG = os.path.join(WS, "logs", "task-question-answer.log")
MAX_TRIES = 3


def log(m):
    try:
        with open(LOG, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception:
        pass


def sub_env():
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.15.0/bin:"
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


def extract_reply(jdata):
    res = (jdata or {}).get("result", {}) or {}
    pls = res.get("payloads", []) or []
    txt = "\n".join((p.get("text") or "").strip() for p in pls if p.get("text")).strip()
    if not txt:
        txt = ((res.get("meta", {}) or {}).get("finalAssistantVisibleText") or "").strip()
    return txt


def main():
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {"seen": [], "fails": {}}
    seen = set(st.get("seen", [])); fails = st.get("fails", {})

    # Pending @Exobot QUESTION triage tasks (branch-5 of task-note-command: tag 'needs-attention').
    q = ("tasks?select=id,title,description,state,tags,source&source=eq.task-note-command"
         "&state=neq.Done&tags=cs.%7Bneeds-attention%7D&order=id.desc&limit=50")
    rows = supa("GET", q) or []
    if not rows:
        return  # nothing to do — SILENT, never touches any channel

    for t in rows:
        tid = str(t.get("id"))
        if tid in seen:
            continue
        desc = t.get("description") or ""
        m = re.search(r"task #(\d+)", desc)
        if not m:
            seen.add(tid); continue
        origid = m.group(1)
        qm = re.search(r"\):\s*(.*?)(?:\.\s*Exo to review.*)?$", desc, re.S)
        question = (qm.group(1) if qm else desc).strip()

        orig = supa("GET", f"tasks?id=eq.{origid}&select=id,title,description") or []
        ctx = orig[0] if orig else {}
        prompt = (
            "You are Exo, answering a question a teammate asked on a Mission Control task. "
            "Give a CONCISE, grounded answer (2-6 sentences). If you cannot answer confidently from "
            "the context, say what's missing and who to ask — do NOT invent facts.\n\n"
            f"QUESTION: {question}\n\n"
            f"TASK #{origid}: {ctx.get('title','')}\n"
            f"TASK CONTEXT:\n{(ctx.get('description') or '')[:2500]}\n\n"
            "Output ONLY the answer text, no preamble."
        )
        pf = None
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
                tf.write(prompt); pf = tf.name
            skey = "agent:main:taskqa-" + hashlib.sha1((tid + origid).encode()).hexdigest()[:12]
            r = subprocess.run([OPENCLAW, "agent", "--session-key", skey,
                                "--message-file", pf, "--json"],
                               capture_output=True, text=True, timeout=300, env=sub_env())
            ans = ""
            try:
                ans = extract_reply(json.loads(r.stdout))
            except Exception:
                ans = ""
        finally:
            if pf:
                try: os.unlink(pf)
                except Exception: pass

        if not ans:
            n = fails.get(tid, 0) + 1; fails[tid] = n
            log(f"FAILED task {tid} (orig {origid}) try {n}/{MAX_TRIES} rc={getattr(r,'returncode','?')}")
            if n >= MAX_TRIES:
                seen.add(tid); fails.pop(tid, None); log(f"gave up task {tid}")
            continue

        supa("POST", "activities", {"type": "task_note", "subject": f"task:{origid}",
             "body": "✅ Exo (answering the question): " + ans, "owner": "Exo", "status": "completed"})
        supa("PATCH", f"tasks?id=eq.{tid}", {"state": "Done"})
        # Clear the visible 'awaiting-exo-answer' flag on the ORIGINAL task now that it's answered.
        try:
            cur = supa("GET", f"tasks?id=eq.{origid}&select=tags") or []
            if cur:
                tags = [t for t in (cur[0].get("tags") or []) if t != "awaiting-exo-answer"]
                supa("PATCH", f"tasks?id=eq.{origid}", {"tags": tags})
        except Exception as e:
            log(f"WARN clear flag on {origid}: {e}")
        seen.add(tid); fails.pop(tid, None)
        log(f"answered task {tid} -> posted on #{origid}")

    st["seen"] = list(seen)[-2000:]; st["fails"] = fails
    json.dump(st, open(STATE, "w"))


if __name__ == "__main__":
    main()
