#!/usr/bin/env python3
"""backlog_grind_apply.py — deterministic guard + executor for the daily backlog grind (Jon 2026-10-04).

The grind cron (LLM) curates MERGE/CLOSE candidates. This script makes the result safe and Decision-based:

  propose --items-json FILE   (called by the grind cron)
      1. VERIFY each item at source (rules learned from real misses):
         - skip tasks no longer open, tagged no-merge/keep/canonical-merged, or already named in an
           OPEN Decision (e.g. PIEE #3250 sitting in D-7281902)
         - MERGE only same owner + same student-task (different assignees/scopes ≠ duplicate)
         - never CLOSE the only open instance of a recurring task → becomes REDATE (next cycle)
         - never CLOSE a "single canonical" consolidated item → becomes REDATE
      2. EXO-FIRST auto-apply the provably safe class (snapshot first): duplicate recurring instances
         (same title + same due), subtasks whose parent is Done/Cancelled.
      3. Everything else → ONE Decision card (ingest API) with a recommendation per item; plan saved to
         mission-control/data/backlog-grind-plan.json. Prints a one-line summary for Discord.

  apply                        (launchd com.exos.backlog-grind-apply, every 10 min)
      If the plan's Decision was answered by a HUMAN click: "Apply my recommendations" → execute every
      item except per-item overrides in the note ("hold 3 5" / "skip 3"); "Hold" → do nothing.
      Snapshot first; posts one result line to #exomac-system. Idempotent.
"""
import json, os, re, sys, subprocess, urllib.request, urllib.parse
from datetime import datetime, timezone, date, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
DEC_FILE = os.path.join(WS, "mission-control", "data", "decisions.json")
PLAN = os.path.join(WS, "mission-control", "data", "backlog-grind-plan.json")
LOG = os.path.join(WS, "logs", "backlog-grind-apply.log")
MC = "http://127.0.0.1:8080"
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
CHANNEL = "channel:1501636814849577050"
PROTECT = {"no-merge", "keep", "canonical-merged"}
OPEN = ("To Do", "In Progress", "Blocked")


def log(m):
    with open(LOG, "a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")


def sb_get(p):
    return json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/{p}", headers=H), timeout=60))


def sb_patch(tid, f):
    urllib.request.urlopen(urllib.request.Request(f"{SB}/tasks?id=eq.{tid}", data=json.dumps(f).encode(),
                           headers={**H, "Prefer": "return=minimal"}, method="PATCH"), timeout=30).read()


def decisions():
    d = json.load(open(DEC_FILE))
    return d if isinstance(d, list) else d.get("decisions", [])


def snapshot(rows, tag):
    st = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    json.dump(rows, open(os.path.join(WS, "mission-control", "data", f"backlog-grind-{tag}-snapshot-{st}.json"), "w"),
              indent=1, default=str)
    return st[:8]


def tagset(t):
    return set(t.get("tags") or [])


def is_recurring(t):
    return any(str(g).startswith("recur:") or str(g).startswith("recurring") for g in tagset(t))


def next_cycle(t):
    tg = " ".join(map(str, tagset(t))).upper()
    d0 = date.today()
    if "YEARLY" in tg: return (d0 + timedelta(days=365)).isoformat()
    if "WEEKLY" in tg: return (d0 + timedelta(days=7)).isoformat()
    m = re.search(r"INTERVAL=(\d+)", tg)
    if "DAILY" in tg and m: return (d0 + timedelta(days=int(m.group(1)))).isoformat()
    try:
        due = date.fromisoformat(str(t.get("due_date"))[:10])
        nxt = date(d0.year, d0.month, min(due.day, 28))          # next upcoming same-day-of-month
        if nxt <= d0:
            nxt = date(d0.year + (d0.month == 12), d0.month % 12 + 1, min(due.day, 28))
    except Exception:
        nxt = d0 + timedelta(days=30)
    return nxt.isoformat()


def stamp(t, line, extra_tags, state=None):
    f = {"description": (t.get("description") or "") + f"\n\n{line}",
         "tags": sorted(tagset(t) | set(extra_tags))}
    if state: f["state"] = state
    return f


def execute(item, T, d8, why_suffix):
    a, tid = item["action"], item["id"]
    t = T.get(tid)
    if not t or t.get("state") not in OPEN:
        return f"#{tid} skipped (no longer open)"
    if a == "merge":
        sb_patch(tid, stamp(t, f"[MERGED {d8} into #{item['canonical']} — backlog grind{why_suffix}.]",
                            [f"merged-dup:{item['canonical']}"], "Cancelled"))
        c = T.get(item["canonical"])
        if c:
            sb_patch(c["id"], {"tags": sorted(tagset(c) | {"canonical-merged"})})
        return f"#{tid}→#{item['canonical']} merged"
    if a == "close":
        sb_patch(tid, stamp(t, f"[CLOSED {d8} stale — {item.get('why','')}. Backlog grind{why_suffix}.]",
                            ["closed", "stale-closed"], "Cancelled"))
        return f"#{tid} closed"
    if a == "redate":
        f = stamp(t, f"[RE-DATED {d8} to {item['due']} — {item.get('why','')}. Backlog grind{why_suffix}.]", [])
        f["due_date"] = item["due"]
        sb_patch(tid, f)
        return f"#{tid} re-dated {item['due']}"
    return f"#{tid} unknown action"


def propose(items):
    ids = sorted({i["id"] for i in items} | {i["canonical"] for i in items if i.get("canonical")})
    T = {t["id"]: t for t in sb_get(f"tasks?select=*&id=in.({','.join(map(str, ids))})")} if ids else {}
    open_ctx = " ".join(f"{d.get('title','')} {d.get('context','')} {d.get('proposedAction','')}"
                        for d in decisions() if str(d.get("status")).lower() in ("open", "pending")
                        and d.get("dedupeKey") != f"backlog-grind-{date.today().isoformat()}")  # today's own card refreshes
    auto, ask, dropped = [], [], []
    for it in items:
        tid = it["id"]; t = T.get(tid)
        a = it.get("action")
        if not t or t.get("state") not in OPEN:
            dropped.append(f"#{tid}: not open"); continue
        if tagset(t) & PROTECT:
            dropped.append(f"#{tid}: tagged {sorted(tagset(t) & PROTECT)}"); continue
        if re.search(rf"#{tid}\b", open_ctx):
            dropped.append(f"#{tid}: already in an open Decision"); continue
        if a == "merge":
            c = T.get(it.get("canonical"))
            if not c or c.get("state") not in OPEN or tagset(c) & {"no-merge", "keep"}:
                dropped.append(f"#{tid}: canonical #{it.get('canonical')} not mergeable"); continue
            if (t.get("owner") or "").lower() != (c.get("owner") or "").lower():
                dropped.append(f"#{tid}: different owner than #{c['id']} (not a duplicate)"); continue
            st = lambda x: {g for g in tagset(x) if str(g).startswith("student-task:")}
            if st(t) != st(c):
                dropped.append(f"#{tid}: different student task than #{c['id']}"); continue
            if is_recurring(t) and t.get("title") == c.get("title") and \
               str(t.get("due_date"))[:10] == str(c.get("due_date"))[:10]:
                auto.append({**it, "why": "duplicate recurring instance (same title + due)"}); continue
            ask.append(it); continue
        if a == "close":
            if is_recurring(t):
                fam = sb_get("tasks?select=id,state&title=eq." + urllib.parse.quote(t.get("title") or ""))
                if not [x for x in fam if x["id"] != tid and x.get("state") in OPEN]:
                    ask.append({"action": "redate", "id": tid, "due": next_cycle(t),
                                "why": "only open instance of a recurring task — closing would end the recurrence",
                                "label": it.get("label", "")}); continue
            if re.search(r"single canonical", t.get("description") or "", re.I):
                ask.append({"action": "redate", "id": tid, "due": next_cycle(t),
                            "why": "consolidated canonical item — keep it, move to next cycle",
                            "label": it.get("label", "")}); continue
            pm = next((str(g)[7:] for g in tagset(t) if str(g).startswith("parent:")), None)
            if pm:
                par = sb_get(f"tasks?select=state&id=eq.{pm}")
                if par and par[0].get("state") in ("Done", "Cancelled"):
                    auto.append({**it, "why": f"parent #{pm} is {par[0]['state']}"}); continue
            ask.append(it); continue
        dropped.append(f"#{tid}: unknown action {a}")

    applied = []
    if auto:
        d8 = snapshot([T[i["id"]] for i in auto if i["id"] in T], "auto")
        for it in auto:
            applied.append(execute(it, T, d8, ", Exo-verified: " + it["why"]))
    did = None
    if ask:
        for n, it in enumerate(ask, 1):
            it["n"] = n
        def line(it):
            t = T.get(it["id"], {})
            who = t.get("owner") or "?"
            if it["action"] == "merge":
                return f"{it['n']}) MERGE #{it['id']} into #{it['canonical']} — {(t.get('title') or '')[:60]} ({who}). {it.get('why','')}"
            if it["action"] == "redate":
                return f"{it['n']}) KEEP + RE-DATE #{it['id']} to {it['due']} — {(t.get('title') or '')[:60]} ({who}). {it['why']}"
            return f"{it['n']}) CLOSE #{it['id']} — {(t.get('title') or '')[:60]} ({who}, due {str(t.get('due_date'))[:10]}). {it.get('why','')}"
        ctx = ("Backlog grind, verified at source. \"Apply my recommendations\" executes every item below; "
               "override per item in the note, e.g. \"hold 3 5\".\n\n" + "\n".join(line(i) for i in ask))
        if applied:
            ctx += "\n\nAlready applied (provably safe, snapshot kept): " + "; ".join(applied)
        if dropped:
            ctx += "\n\nFiltered out (not safe to propose): " + "; ".join(dropped)
        today = date.today().isoformat()
        body = {"title": f"Backlog grind {today}: {len(ask)} merge/close/re-date calls",
                "question": f"Apply the {len(ask)} backlog recommendations?", "type": "yesno",
                "options": ["Apply my recommendations", "Hold"], "priority": "normal",
                "source": "Exo (backlog grind)", "context": ctx,
                "proposedAction": "; ".join(f"{i['action']} #{i['id']}" for i in ask),
                "dedupeKey": f"backlog-grind-{today}"}
        tok = open(os.path.join(WS, "mission-control", "data", ".decisions-token")).read().strip()
        r = json.load(urllib.request.urlopen(urllib.request.Request(f"{MC}/api/decisions/ingest",
                      data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-exo-token": tok},
                      method="POST"), timeout=30))
        did = r.get("id")
        json.dump({"decision_id": did, "created": datetime.now(timezone.utc).isoformat(), "items": ask,
                   "executed": False}, open(PLAN, "w"), indent=1)
    log(f"propose: auto={applied} ask={len(ask)} dropped={dropped} decision={did}")
    parts = []
    if applied: parts.append(f"{len(applied)} safe cleanup(s) applied")
    if did: parts.append(f"{len(ask)} call(s) awaiting you → Decision {did}")
    print("Backlog grind: " + (" · ".join(parts) if parts else "NO_REPLY"))


def human_answered(d):
    if d.get("answeredByEmail"): return True
    try:
        u = json.load(open(os.path.join(WS, "mission-control", "users.json")))
        u = u if isinstance(u, list) else (u.get("users") or list(u.values()))
        names = {str(x.get("name", "")).strip().lower() for x in u if isinstance(x, dict)}
    except Exception:
        names = set()
    return str(d.get("answeredBy") or "").strip().lower() in names


def apply():
    try:
        plan = json.load(open(PLAN))
    except Exception:
        return
    if plan.get("executed") or not plan.get("decision_id"):
        return
    d = next((x for x in decisions() if x.get("id") == plan["decision_id"]), None)
    if not d or d.get("status") != "answered" or not human_answered(d):
        return
    ans = str(d.get("answer") or "").lower()
    note = str(d.get("note") or "").lower()
    held = {int(n) for m in re.finditer(r"\b(?:hold|skip|keep|no)\s+((?:#?\d+[\s,]*)+)", note)
            for n in re.findall(r"\d+", m.group(1))}
    res = []
    if ans.startswith("apply") or ans in ("yes", "approve", "approved"):
        items = [i for i in plan["items"] if i.get("n") not in held]
        ids = sorted({i["id"] for i in items} | {i["canonical"] for i in items if i.get("canonical")})
        T = {t["id"]: t for t in sb_get(f"tasks?select=*&id=in.({','.join(map(str, ids))})")} if ids else {}
        d8 = snapshot(list(T.values()), "commit")
        for it in items:
            res.append(execute(it, T, d8, f", Jon approved {plan['decision_id']}"))
    plan.update({"executed": True, "executed_at": datetime.now(timezone.utc).isoformat(), "result": res,
                 "held": sorted(held), "answer": d.get("answer")})
    json.dump(plan, open(PLAN, "w"), indent=1)
    log(f"apply {plan['decision_id']}: {res} held={sorted(held)}")
    if res:
        msg = (f"✅ Backlog grind {plan['decision_id']} applied: " + "; ".join(res) +
               (f" (held: {', '.join(map(str, sorted(held)))})" if held else ""))
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", CHANNEL, "-m", msg],
                       capture_output=True, timeout=60)


if __name__ == "__main__":
    import urllib.parse
    if len(sys.argv) > 1 and sys.argv[1] == "propose":
        src = sys.argv[sys.argv.index("--items-json") + 1]
        propose(json.load(open(src)) if src != "-" else json.load(sys.stdin))
    elif len(sys.argv) > 1 and sys.argv[1] == "apply":
        apply()
    else:
        print(__doc__)
