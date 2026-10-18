#!/usr/bin/env python3
"""decision-note-router.py — route Decisions-note directions (plain text, auto-assigned).

When yes/no doesn't fit, a user writes a PLAIN-TEXT direction in the decision NOTE and submits.
This watcher (launchd, ~2 min) reads decisions.json and acts on notes it hasn't seen before:

  * "#123 done" / "#123 have Lizi take it" / "#123 <text>"  -> UPDATE task #123 (done / reassign / note)
  * any other DIRECTIVE note ("order a new release servo", "renew the FAA license", "have Neil
    handle the fin resize")  -> create a task, AUTO-ASSIGNED to the right owner. The writer does
    NOT need to know who handles it — we resolve the owner: explicit name -> domain map -> local
    model judgment (Exo) -> fall back to an Exo triage task so nothing is ever lost.

No Discord mentions. Yes/No and "Not my decision" are untouched. Baseline-safe (first run records
current note hashes and does nothing).
"""
import json, os, re, hashlib, urllib.request
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
DECISIONS = os.path.join(WS, "mission-control", "data", "decisions.json")
ROSTER = os.path.join(WS, "mission-control", "data", "routing-roster.json")
STATE = os.path.join(WS, "logs", "decision-note-router-state.json")
LOG = os.path.join(WS, "logs", "decision-note-router.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
OLLAMA = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "gemma4:e4b"      # small + fast; the classification is a simple pick-from-list
_model_calls = [0]
MAX_MODEL_CALLS = 4              # bound per-run runtime; excess unresolved notes -> Exo triage
ACTION = re.compile(r"\b(handle|take care of|manage|order|buy|purchase|procure|source|renew|prepare|"
                    r"draft|send|fix|schedule|call|contact|reach\s?out|follow\s?up|investigate|"
                    r"resolve|create|build|arrange|coordinate|set\s?up|research|file|submit|pay|book|"
                    r"have\s+\w+|analy[sz]e|evaluate|assess|review|model|compare|calculate|estimate|"
                    r"quantify|rework|revise|redo|update|explain|summari[sz]e|recommend)\b", re.I)
# High-confidence domain -> owner email (fast path before the model).
DOMAIN = [
    (r"expense|invoice|reimburs|payment|payroll|budget|accounting|quickbooks|finance|\bap\b", "kballard@exosaero.com"),
    (r"machin|fabricat|production|work order|shop\b|tooling|composite layup|manufactur", "peaton@exosaero.com"),
    (r"avionics|sensor|electronics|wiring|instrumentation|daq|test bench|flight software", "snorsworthy@exosaero.com"),
    (r"schedule|timeline|teamwork|gantt|milestone|turnaround", "peaton@exosaero.com"),
    (r"software|mission control|website|web app|dashboard|\bbug\b|database|server|\bit\b|login", "exo@exosaero.com"),
    (r"sales|customer|investor|outreach|marketing|payload sale|\blead\b|crm|business develop", "lquinn@exosaero.com"),
    (r"japan|hospo|space cotan|kumazawa", "toshihisa@exosaero.com"),
    # export control -> Empowered Official John Quinn (reviewer Denise Shirey); NOT Neil (Jon 2026-10-10)
    (r"export|itar|\bear\b|ddtc|deemed export", "jquinn@exosaero.com"),
    (r"licens|compliance|cmmc|cui", "nmilburn@exosaero.com"),
    (r"contract|legal|agreement|\bnda\b|mnda|counsel|terms sheet|term sheet", "jquinn@exosaero.com"),
    (r"facilit|crane|generator|building|site\b|maintenance", "peaton@exosaero.com"),
]


try:
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import drop_tombstone_exo3 as _tomb
except Exception:
    _tomb = None


def _fl_event(did, action):
    try:
        import fleet_log
        fleet_log.event("decision-note-router", "govern", action, detail={"decision": did}, owner="John Quinn")
    except Exception:
        pass


def logline(m):
    try:
        with open(LOG, "a") as f: f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception: pass


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def supa(method, path, body=None):
    req = urllib.request.Request(SUPA + "/" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            t = r.read().decode(); return json.loads(t) if t else []
    except Exception as e:
        logline(f"WARN supa {method}: {e}"); return None


def mktask(t):
    d = supa("POST", "tasks", t); return d[0]["id"] if d else None


def explicit_name(note, roster):
    m = re.search(r"\bhave\s+([A-Za-z]+)\b", note, re.I)
    cand = m.group(1).lower() if m else None
    for p in roster:
        if cand and p["first"].lower() == cand: return p
    for p in roster:  # any full/first name + an action verb
        if (p["name"].lower() in note.lower() or re.search(rf"\b{re.escape(p['first'])}\b", note, re.I)) and ACTION.search(note):
            return p
    return None


def domain_owner(note, by_email):
    for pat, em in DOMAIN:
        if re.search(pat, note, re.I): return by_email.get(em)
    return None


def ollama_owner(note, roster, by_email):
    if _model_calls[0] >= MAX_MODEL_CALLS: return None
    _model_calls[0] += 1
    team = "\n".join(f"- {p['name']} <{p['email']}> — {p['title']} ({p['dept']})" for p in roster)
    prompt = (f"You route Exos Aerospace action items to the single best owner. Team:\n{team}\n\n"
              f"Action item: \"{note}\"\n\nReply with ONLY the owner's email from the list, or the word "
              f"unsure. No other text.")
    # ExO3 #3: prepend the confirmed MTP-as-protocol so owner-routing ladders to Exos's MTP +
    # hard constraints + decision-priority (config/mtp-protocol.json).
    try:
        import os as _os, sys as _sys
        _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        import mtp as _mtp
        prompt = _mtp.protocol_prompt() + "\n\n" + prompt
    except Exception:
        pass
    try:
        req = urllib.request.Request(OLLAMA, method="POST",
            data=json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                             "options": {"temperature": 0}}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode()).get("response", "")
        m = re.search(r"[a-z0-9._%+-]+@exosaero\.com", resp, re.I)
        if m and m.group(0).lower() in by_email: return by_email[m.group(0).lower()]
    except Exception as e:
        logline(f"WARN ollama: {e}")
    return None


def main():
    decs = load(DECISIONS, [])
    decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    roster = load(ROSTER, [])
    by_email = {p["email"].lower(): p for p in roster}
    state = load(STATE, None)

    def h(s): return hashlib.sha1((s or "").encode()).hexdigest()[:16]

    if state is None:  # BASELINE (hash the SAME way as processing — stripped)
        state = {d["id"]: h((d.get("note") or "").strip()) for d in decs if (d.get("note") or "").strip()}
        json.dump(state, open(STATE, "w"), indent=0)
        logline(f"baseline {len(state)}"); print("baseline"); return

    acted = 0
    for d in decs:
        note = (d.get("note") or "").strip()
        if not note: continue
        nh = h(note)
        if state.get(d["id"]) == nh: continue
        title = d.get("title") or d.get("question") or d["id"]
        # GOVERN (John 10/18): task #3600 was spawned from a note that was ONLY Exo's own bracket
        # annotations ("[pulled back…] [Exo 10/8: Dropped…]"). Judge the human's words only, and a
        # drop/close note never becomes new work — it is a kill, not a directive.
        human = _tomb.human_text(note) if _tomb else note
        if not human:
            state[d["id"]] = nh; continue
        drop = bool(_tomb and _tomb.DROP_RE.search(human) and not _tomb.CONDITIONAL_RE.search(human))

        tid = re.search(r"#(\d{2,})", human)
        if tid:                                          # UPDATE an existing task
            taskid, low, did = tid.group(1), human.lower(), []
            owner = explicit_name(human, roster)
            if owner and re.search(r"reassign|assign to|have\s|hand", low):
                supa("PATCH", f"tasks?id=eq.{taskid}", {"owner": owner["name"], "assigned_email": owner["email"]}); did.append(f"reassign->{owner['name']}")
            if drop:
                supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "Cancelled"}); did.append("Cancelled")
            elif re.search(r"\b(done|closed?|complete[d]?|resolved?)\b", low):
                supa("PATCH", f"tasks?id=eq.{taskid}", {"state": "Done"}); did.append("Done")
            supa("POST", "activities", {"type": "task_note", "subject": f"task:{taskid}",
                 "body": f"[from decision {d['id']}] {note}", "owner": "Decisions note", "status": "completed"}); did.append("note")
            logline(f"{d['id']}: #{taskid} {did}"); state[d["id"]] = nh; acted += 1; continue

        # An explicit "📝 Instruction" answer is ALWAYS a directive (a missing verb once dropped
        # Jon's D-7281837 "Analyze it on the basis of..." note silently, 2026-09-26).
        instr = "instruction" in str(d.get("answer") or "").lower()
        if drop and not instr:                           # "drop this" kills; never spawns a task
            logline(f"{d['id']}: drop note — no task spawned"); _fl_event(d["id"], "drop_no_spawn")
            state[d["id"]] = nh; continue
        if not instr and not ACTION.search(human):       # plain comment, not a directive
            state[d["id"]] = nh; continue

        # Exo-authored decisions: follow-up direction on Exo's own analysis comes back to Exo,
        # not to a domain owner (e.g. an investor-dilution ask must not land on finance/AP).
        exo_src = str(d.get("source") or "").lower().startswith("exo")
        # EXO-FIRST / SUBTASK-FIRST (Jon 2026-10-03): only an EXPLICITLY named person gets the work.
        # Otherwise Exo does it (task-question-answer.py works these) and hands off only a genuine human
        # step. If the decision is about an existing task, the routed item is a SUBTASK of that task.
        named = explicit_name(human, roster)
        guess = None if (named or exo_src) else (domain_owner(human, by_email) or ollama_owner(human, roster, by_email))
        rel = next((str(d.get(k)) for k in ("relatedTaskId", "spawned_task", "taskId", "relatedTask", "related_task")
                    if re.fullmatch(r"\d{2,}", str(d.get(k) or "").lstrip("#"))), None)
        rel = rel.lstrip("#") if rel else None
        sub = ["subtask", f"parent:{rel}"] if rel else []
        if named:
            mktask({"title": f"{note[:70]}", "owner": named["name"], "assigned_email": named["email"],
                    "assigned_to": named["name"], "state": "To Do", "priority": 72, "category": "Decision",
                    "source": "decision-note-router", "tags": ["decision-routed"] + sub,
                    "description": f"Auto-routed from decision {d['id']} ({title}). Direction: {note}"})
            logline(f"{d['id']}: routed -> {named['email']}{' sub of #'+rel if rel else ''}")
        else:
            hint = f" Suggested human owner if it truly needs one: {guess['name']} <{guess['email']}>." if guess else ""
            mktask({"title": f"[Exo doing] {note[:62]}", "owner": "Exo", "assigned_email": "exo@exosaero.com",
                    "state": "To Do", "priority": 74, "category": "Decision", "source": "decision-note-router",
                    "tags": ["decision-routed", "needs-owner", "exo-first"] + sub,
                    "description": (f"From decision {d['id']} ({title}){' about task #'+rel if rel else ''}. "
                                    f"Direction: {note}. Exo to do it itself.{hint}")})
            logline(f"{d['id']}: routed -> EXO-first{' sub of #'+rel if rel else ''} (guess={guess and guess['email']})")
        state[d["id"]] = nh; acted += 1
    json.dump(state, open(STATE, "w"), indent=0)
    print(f"routed {acted}")


main()
