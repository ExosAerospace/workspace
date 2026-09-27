#!/usr/bin/env python3
"""
capstone_capture.py — Exo as the UTD Team Atlas "prompter" + experiment recorder.

Jon (2026-09-27): students work in short 15-20 min MC sessions WITH Exo; Exo learns
from their inputs/decisions and captures the result of every experiment.

Every ~10 min (launchd com.exos.capstone-capture):
  - reads new notes + state changes on UTD students' tasks (Supabase `activities`)
  - appends each to mission-control/data/capstone-experiments.jsonl (the dataset:
    contact checks, fit scores, AI-error lists, corrected drafts, checklist edits…)
  - replies on the task as Exo: note → "captured"; session moved to Done →
    milestone count + the student's next session
  - a student QUESTION becomes an Exo triage task tagged utd-question (answer must be
    program-safe: students are sandboxed early_adopters under NDA, public info only)

Deterministic, idempotent (state file tracks seen activity ids). Student notes are
excluded from task-note-command.py, so this is their only automation path.
"""
import os, re, json, subprocess, urllib.request, urllib.parse
from email.message import EmailMessage
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
DATA = os.path.join(WS, "mission-control/data/capstone-experiments.jsonl")
STATE = os.path.join(WS, "logs/capstone-capture-state.json")
LOG = os.path.join(WS, "logs/capstone-capture.log")
SINCE_DEFAULT = "2026-09-27T16:00:00+00:00"  # go-live; nothing earlier is replayed


def log(m):
    with open(LOG, "a") as f:
        f.write(f"[{datetime.now().astimezone():%Y-%m-%d %H:%M %Z}] {m}\n")


def supa(method, path, body=None):
    req = urllib.request.Request(SB + "/" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                                          "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read().decode()
        return json.loads(t) if t else []


def students():
    u = json.load(open(os.path.join(WS, "mission-control/users.json")))
    u = u if isinstance(u, list) else (u.get("users") or list(u.values()))
    return {x["name"].strip().lower(): x["name"] for x in u
            if isinstance(x, dict) and x.get("role") == "early_adopter" and x.get("name")}


def reply(tid, msg):
    supa("POST", "activities", {"type": "task_note", "subject": f"task:{tid}", "body": msg,
                                "owner": "Exo", "status": "completed"})


def fmt_due(d):
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%a %-m/%-d")
    except Exception:
        return ""


def main():
    st = {"since": SINCE_DEFAULT, "seen": [], "n": 0}
    if os.path.exists(STATE):
        st.update(json.load(open(STATE)))
    seen = set(st["seen"])
    who = students()
    tasks = supa("GET", "tasks?select=id,title,state,owner,due_date,source,tags&assigned_email=ilike.*utdallas*")
    by_id = {t["id"]: t for t in tasks}
    subj = ",".join(f"task:{i}" for i in by_id)
    q = (f"activities?select=id,type,subject,body,owner,created_at&type=in.(task_note,task_update)"
         f"&created_at=gt.{urllib.parse.quote(st['since'])}&subject=in.({urllib.parse.quote(subj)})&order=created_at")
    acts = supa("GET", q)
    captured = 0
    for a in acts:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        author = (a.get("owner") or "").strip()
        if author.lower() not in who:
            continue  # Exo / staff / automation
        tid = int(a["subject"].split(":")[1])
        t = by_id.get(tid, {})
        tags = t.get("tags") or []
        body = a.get("body") or ""
        is_done = a["type"] == "task_update" and re.search(r"State: .*→ Done", body)
        if a["type"] == "task_update" and not is_done and "State:" not in body:
            continue
        st["n"] += 1
        rec = {"n": st["n"], "ts": a["created_at"], "student": who[author.lower()], "task_id": tid,
               "task": t.get("title"), "kind": "done" if is_done else ("state" if a["type"] == "task_update" else "note"),
               "session": next((x[8:] for x in tags if x.startswith("session:")), None),
               "lead": next((x[5:] for x in tags if x.startswith("lead:")), None), "body": body}
        with open(DATA, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        captured += 1

        if rec["kind"] == "note":
            if "?" in body:
                nid = supa("POST", "tasks", {
                    "title": f"[UTD question] {author}: {body.strip()[:60]} (task #{tid})",
                    "owner": "Exo", "assigned_email": "exo@exosaero.com", "state": "To Do", "priority": 85,
                    "category": "Task", "source": "capstone-capture", "tags": ["utd-question", "needs-attention"],
                    "description": (f"UTD capstone student {author} asked on task #{tid} ({t.get('title')}):\n\n{body}\n\n"
                                    "ANSWER ON TASK #%s as Exo. The student is a sandboxed early_adopter under NDA: "
                                    "answer only with public / program information (PUG facts, process, their tasks). "
                                    "No pricing, customers, financials, CUI/ITAR, or other internal data. "
                                    "If unsure, route to Lizi." % tid)})
                reply(tid, f"✅ Exo: captured (data point #{rec['n']}). I saw your question and will answer it here, "
                           f"usually within a few hours (ref #{nid[0]['id'] if nid else '?'}).")
            else:
                reply(tid, f"✅ Exo: captured as data point #{rec['n']} for Team Atlas's human-vs-AI experiment. "
                           "Thanks! When you're done, drag this task to Done.")
        elif rec["kind"] == "done" and "15-min" in tags:
            mine = [x for x in tasks if (x.get("owner") or "").lower() == author.lower() and "15-min" in (x.get("tags") or [])]
            done = sum(1 for x in mine if x["state"] == "Done" or x["id"] == tid)
            nxt = sorted([x for x in mine if x["state"] != "Done" and x["id"] != tid], key=lambda x: x.get("due_date") or "")
            msg = f"🎯 Exo: session complete. You've closed {done} of {len(mine)} this week."
            msg += (f" Next up: #{nxt[0]['id']} {nxt[0]['title']} (due {fmt_due(nxt[0].get('due_date') or '')})."
                    if nxt else " That's all of your sessions for the week. Great work!")
            reply(tid, msg)
    if acts:
        st["since"] = acts[-1]["created_at"]
    st["seen"] = list(seen)[-3000:]
    json.dump(st, open(STATE, "w"))
    if captured:
        log(f"captured {captured} (total {st['n']})")


OUTBOX = os.path.join(WS, "mission-control/data/capstone-outbox.json")


def process_outbox():
    """Send staged student emails ONLY after Lizi answers their Decision Yes (Jon 9/27:
    Lizi releases, Exo sends directly as the team's prompter). No → cancelled."""
    if not os.path.exists(OUTBOX):
        return
    ob = json.load(open(OUTBOX))
    pend = [x for x in ob if x.get("status") == "pending"]
    if not pend:
        return
    tok = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
    req = urllib.request.Request("http://localhost:8080/api/decisions", headers={"X-Exo-Token": tok})
    decs = json.load(urllib.request.urlopen(req, timeout=20))
    for item in pend:
        d = next((z for z in decs if z.get("dedupeKey") == item["decision_dedupe"]), None)
        if not d or d.get("status") != "answered":
            continue
        ans = (d.get("answer") or "").strip().lower()
        if not ans.startswith("yes"):
            item["status"] = "cancelled"; item["decision_answer"] = d.get("answer")
            log(f"outbox {item['key']} cancelled: {d.get('answer')}"); continue
        sent = []
        for e in item["emails"]:
            m = EmailMessage()
            m["From"] = "Exo (Exos Mission Control) <jquinnexo@pm.me>"
            m["To"] = e["to"]; m["Cc"] = item["cc"]; m["Reply-To"] = item["reply_to"]
            m["Subject"] = e["subject"]; m.set_content(e["body"])
            p = subprocess.run(["msmtp", "-a", "protonmail", e["to"], item["cc"]], input=m.as_bytes(), capture_output=True)
            ok = p.returncode == 0
            sent.append({"to": e["to"], "ok": ok, "err": p.stderr.decode()[:120]})
            log(f"outbox {item['key']} -> {e['to']} ok={ok}")
        item["status"] = "sent" if all(x["ok"] for x in sent) else "partial"
        item["sent"] = sent; item["sent_at"] = datetime.now(timezone.utc).isoformat()
    json.dump(ob, open(OUTBOX, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
    try:
        process_outbox()
    except Exception as e:
        log(f"outbox error: {e}")
