#!/usr/bin/env python3
"""
legacy_triage_decisions.py — feed Jon the stale legacy backlog 25/day as Mission Control Decisions,
with Exo's recommendation on each (Jon 2026-09-09).

Pool = old email-taskified tasks (source "Email to jquinn@…", state To Do, created < 2026-08-01)
that are NOT the active action pile (awaiting-john), In Progress, guarded, or already triaged.

Each run:
  PHASE A — if the previous batch Decision is ANSWERED, execute it:
     "Apply my recommendations"  -> CLOSE=cancel, KEEP=leave (tag legacy-kept), PROMOTE=tag awaiting-john.
        Per-ID overrides in the note: e.g.  keep 123 456 / close 789 / promote 555
     "Skip this batch"           -> leave the 25 out of the queue (tag legacy-triage-skipped), do nothing.
  PHASE B — if there is NO open (unanswered) triage batch, create the next batch of 25 as ONE Decision
     via POST /api/decisions/ingest (dedupeKey legacy-triage-batch-N). Only ONE open batch at a time,
     so unanswered batches never pile up ("25 a day" cadence, self-throttling).

Run:  python3 scripts/legacy_triage_decisions.py [--dry-run]
Scheduled daily via launchd com.exos.legacy-triage.
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

WS = os.path.expanduser("~/.openclaw/workspace")
DEC_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
TOKEN = open(os.path.join(WS, "mission-control", "data", ".decisions-token")).read().strip()
MC = "http://127.0.0.1:8080"
STATE = os.path.join(WS, "logs", "legacy-triage-state.json")
DRY = "--dry-run" in sys.argv
BATCH_SIZE = 25
CUTOFF = "2026-08-01"

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
def _sbkey():
    return json.load(open(os.path.expanduser("~/.openclaw/secrets.json"))).get("supabase_service_role_key")
SBH = {"apikey": _sbkey(), "Authorization": "Bearer " + _sbkey()}

def sb_page(path):
    out, off = [], 0
    while True:
        r = urllib.request.Request(f"{SB}{path}&limit=1000&offset={off}", headers=SBH)
        pg = json.load(urllib.request.urlopen(r, timeout=40)); out += pg
        if len(pg) < 1000: return out
        off += 1000

def sb_patch(tid, body):
    if DRY:
        print(f"    [dry] patch #{tid} {body}"); return
    r = urllib.request.Request(SB + f"tasks?id=eq.{tid}", data=json.dumps(body).encode(),
        headers={**SBH, "Content-Type": "application/json", "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(r, timeout=30)

def load_json(p, d):
    try: return json.load(open(p))
    except Exception: return d

def save_state(st):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(st, open(STATE, "w"), indent=1)

def ingest_decision(payload):
    if DRY:
        print(f"    [dry] would POST decision: {payload['dedupeKey']}"); return {"id": "D-DRY"}
    r = urllib.request.Request(MC + "/api/decisions/ingest", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-exo-token": TOKEN}, method="POST")
    return json.load(urllib.request.urlopen(r, timeout=30))

GUARD_TAGS = ("awaiting-john", "legacy-triage-queued", "legacy-triaged", "legacy-kept",
              "legacy-triage-skipped", "legacy-noise-closed-20260909")
LIVING = re.compile(r"\bdeck\b|series a|teaser|capability statement|one[- ]?pager|template|\bNDA\b|\bMNDA\b|"
                    r"\bMOU\b|\bLOI\b|spacewerx|on-orbit|financial model|data ?room|quad chart|pricing|"
                    r"payload user guide|\bSOP\b|procedure|price list", re.I)
PROMOTE = re.compile(r"ready to send|ready-to-send|\[READY|submit-ready|\bsign\b|\bsubmit\b|approve", re.I)

def recommend(title):
    t = title or ""
    if PROMOTE.search(t): return "PROMOTE", "looks action-ready — belongs in your queue"
    if LIVING.search(t):  return "KEEP", "living asset — likely still in use"
    return "CLOSE", "stale pre-Aug, untouched, not in your action pile"

def is_guarded(tags):
    tl = [str(x).lower() for x in (tags or [])]
    return any(g.lower() in tl for g in GUARD_TAGS) or any(str(x).startswith("pin:") for x in (tags or []))

def pool(tasks):
    out = []
    for t in tasks:
        if not (t.get("source") or "").startswith("Email to jquinn"): continue
        if t.get("state") != "To Do": continue
        if (t.get("created_at") or "")[:10] >= CUTOFF: continue
        if is_guarded(t.get("tags")): continue
        out.append(t)
    out.sort(key=lambda x: x.get("created_at") or "")
    return out

def parse_overrides(note):
    ov = {}
    for kw, rec in (("keep", "KEEP"), ("close", "CLOSE"), ("promote", "PROMOTE")):
        for m in re.finditer(kw + r"[:\s]+((?:#?\d+[,\s]*)+)", note or "", re.I):
            for i in re.findall(r"\d+", m.group(1)):
                ov[int(i)] = rec
    return ov

def human_answered(d):
    if d.get("answeredByEmail"):
        return True
    users = load_json(os.path.join(WS, "mission-control", "users.json"), [])
    names = {str(u.get("name", "")).strip().lower() for u in users if u.get("name")}
    return str(d.get("answeredBy") or "").strip().lower() in names


def apply_batch(batch, decision):
    ans = (decision.get("answer") or "").lower()
    if "skip" in ans:
        for it in batch["items"]:
            r = urllib.request.Request(f"{SB}tasks?id=eq.{it['id']}&select=tags", headers=SBH)
            tags = (json.load(urllib.request.urlopen(r, timeout=30)) or [{}])[0].get("tags") or []
            sb_patch(it["id"], {"tags": list(dict.fromkeys(list(tags) + ["legacy-triage-skipped"]))})
        print(f"  batch {batch['n']}: SKIP — {len(batch['items'])} left out of queue")
        return
    ov = parse_overrides(decision.get("note"))
    counts = {"CLOSE": 0, "KEEP": 0, "PROMOTE": 0}
    for it in batch["items"]:
        rec = ov.get(it["id"], it["rec"])
        r = urllib.request.Request(f"{SB}tasks?id=eq.{it['id']}&select=tags,state", headers=SBH)
        row = (json.load(urllib.request.urlopen(r, timeout=30)) or [{}])[0]
        tags = list(row.get("tags") or [])
        if rec == "CLOSE":
            sb_patch(it["id"], {"state": "Cancelled", "tags": list(dict.fromkeys(tags + ["legacy-triaged", "legacy-triaged-closed"]))})
        elif rec == "PROMOTE":
            sb_patch(it["id"], {"tags": list(dict.fromkeys(tags + ["legacy-triaged", "awaiting-john"]))})
        else:  # KEEP
            sb_patch(it["id"], {"tags": list(dict.fromkeys(tags + ["legacy-triaged", "legacy-kept"]))})
        counts[rec] += 1
    print(f"  batch {batch['n']}: applied — {counts}")

def main():
    decs = load_json(DEC_FILE, [])
    decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    dbykey = {d.get("dedupeKey"): d for d in decs if d.get("dedupeKey")}
    st = load_json(STATE, {"batches": []})

    # PHASE A — execute any answered, not-yet-executed batch
    open_batch = False
    for b in st["batches"]:
        d = dbykey.get(b["key"])
        if not d:
            continue
        # exo3 sign-off gate: execute only on a HUMAN click in MC (answeredByEmail is stamped only by
        # a logged-in session, or answeredBy is an MC user) — never on an auto/token/agent answer.
        answered = d.get("status") == "answered" and human_answered(d)
        if b.get("executed"):
            continue
        if answered:
            apply_batch(b, d)
            if not DRY:
                b["executed"] = True
        else:
            open_batch = True   # still waiting on Jon
    if not DRY:
        save_state(st)

    # PHASE B — only add a new batch if none is outstanding
    if open_batch:
        print("An open triage batch is still awaiting Jon — not creating a new one."); return

    tasks = sb_page("tasks?select=id,title,state,source,tags,created_at&order=id")
    queued_ids = {i for b in st["batches"] for i in [x["id"] for x in b["items"]]}
    remaining = [t for t in pool(tasks) if t["id"] not in queued_ids]
    if not remaining:
        print("Legacy triage complete — pool is empty. Nothing to queue."); return

    n = len(st["batches"]) + 1
    key = f"legacy-triage-batch-{n}"
    chunk = remaining[:BATCH_SIZE]
    items, lines = [], []
    for t in chunk:
        rec, why = recommend(t.get("title"))
        items.append({"id": t["id"], "rec": rec})
        lines.append(f"#{t['id']} — {(t.get('title') or '')[:70]} → {rec} ({why})")
    # tag the chunk so it's not re-picked
    for t in chunk:
        tags = list(dict.fromkeys(list(t.get("tags") or []) + ["legacy-triage-queued", f"batch:{key}"]))
        sb_patch(t["id"], {"tags": tags})

    nclose = sum(1 for i in items if i["rec"] == "CLOSE")
    payload = {
        "source": "Exo (legacy triage)",
        "title": f"Legacy backlog triage — Batch {n} ({len(chunk)} items, {len(remaining)-len(chunk)} left after)",
        "question": ("Clear these stale pre-August tasks off your board. My recommendation is on each line "
                     f"({nclose} CLOSE, {sum(1 for i in items if i['rec']=='KEEP')} KEEP, "
                     f"{sum(1 for i in items if i['rec']=='PROMOTE')} PROMOTE). Answer 'Apply' to execute, "
                     "and add any per-item exceptions in the note (e.g. 'keep 123 456, promote 789')."),
        "context": "\n".join(lines),
        "proposedAction": ("On Apply: CLOSE = cancel the task, KEEP = stays on the board, PROMOTE = added to your "
                           "action queue (awaiting-john). Per-ID note overrides win. 'Skip' leaves all 25 untouched."),
        "type": "yesno",
        "options": ["Apply my recommendations", "Skip this batch"],
        "priority": "low",
        "dedupeKey": key,
    }
    res = ingest_decision(payload)
    st["batches"].append({"key": key, "n": n, "decision_id": res.get("id"),
                          "items": items, "executed": False,
                          "created": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    if not DRY:
        save_state(st)
    print(f"Created triage Batch {n} ({res.get('id')}): {len(chunk)} items ({nclose} recommend CLOSE). "
          f"{len(remaining)-len(chunk)} remain in pool.")

if __name__ == "__main__":
    main()
