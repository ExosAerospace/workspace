#!/usr/bin/env python3
"""Gantt (ERP schedule) -> Task board sync (Phil Eaton 2026-10-22, MC #3824).

Every owned task on the BLK3 Gantt must show up in its owner's MC "My Tasks" / To Do list.
The ERP schedule (erp-foundation/mc.db, project tw-902146) is the source of truth for owner
and due date; the board card (Supabase `tasks`) is made to match.

Linking: each Gantt task is tied to one board card via the tag `sched:<erp-task-id>`.
First run links by exact title (active cards preferred); unmatched owned tasks get a new card.
Board cards already Done/Cancelled are never reopened (owner/date still follow the Gantt). They are
reported as conflicts so a human can say whether the work is really finished.

Idempotent. Usage: sched_board_sync.py [--apply] [--project tw-902146] [--json]
(dry-run by default). Called by server.js after every Schedule edit.
"""
import argparse, glob, importlib.util, json, os, sqlite3, subprocess, sys, urllib.parse

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("ERP_DB_PATH") or os.path.join(WS, "erp-foundation", "mc.db")
_spec = importlib.util.spec_from_file_location("tnc", os.path.join(WS, "scripts", "task-note-command.py"))
_tnc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tnc)
supa = _tnc.supa

# Gantt owner name -> (board owner display name, assigned_email). assigned_email drives "My Tasks".
PEOPLE = {
    "phillip eaton": ("Phil Eaton", "peaton@exosaero.com"),
    "phil eaton": ("Phil Eaton", "peaton@exosaero.com"),
    "steven norsworthy": ("Steve Norsworthy", "snorsworthy@exosaero.com"),
    "steve norsworthy": ("Steve Norsworthy", "snorsworthy@exosaero.com"),
    "russell blink": ("Russ Blink", "rblink@exosaero.com"),
    "russ blink": ("Russ Blink", "rblink@exosaero.com"),
    "neil milburn": ("Neil Milburn", "nmilburn@exosaero.com"),
    "victor castilleja": ("Victor Castilleja", "vcastilleja@exosaero.com"),
    "mike talley": ("Mike Talley", "mtalley@exosaero.com"),
    "john quinn": ("John Quinn", "jquinn@exosaero.com"),
}
CLOSED = {"done", "cancelled", "canceled", "archived", "rejected"}
GANTT_URL = "https://mc.exosaero.space/gantt.html"


def norm(s):
    return " ".join(str(s or "").lower().replace("—", "-").split())


def gantt_tasks(project):
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT t.id, t.title, t.owner, t.state, t.due_date, l.name AS list, "
        "json_extract(t.raw_json,'$.startDate') AS start_date, json_extract(t.raw_json,'$.seq') AS seq "
        "FROM task t LEFT JOIN task_list l ON l.id=t.task_list_id WHERE t.project_id=?", (project,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def erp_set_done(erp_id):
    """Audited ERP write through the DAL (same path as the Schedule page edit)."""
    js = ("const {openErp}=require(process.argv[1]);const e=openErp(process.argv[2],{actor:'sched-board-sync',agent:'sched-board-sync'});"
          "try{e.updateScheduleTask(process.argv[3],{state:'Done'});}finally{e.close();}")
    subprocess.run(["node", "-e", js, os.path.join(WS, "erp-foundation", "dal.js"), DB, erp_id], check=True, timeout=30)


def erp_remove(erp_id):
    """Cancelled on the board -> delete the Gantt task and drop it from every predecessor list (audited DAL)."""
    js = ("const {openErp}=require(process.argv[1]);const e=openErp(process.argv[2],{actor:'sched-board-sync',agent:'sched-board-sync'});"
          "try{const id=process.argv[3];for(const t of e.getProjectSchedule(process.argv[4]).tasks){const p=JSON.parse(t.predecessors_json||'[]');"
          "if(p.includes(id))e.updateScheduleTask(t.id,{predecessors:p.filter(x=>x!==id)});}e.deleteTask(id);}finally{e.close();}")
    subprocess.run(["node", "-e", js, os.path.join(WS, "erp-foundation", "dal.js"), DB, erp_id, "tw-902146"], check=True, timeout=30)


def recycled_sched_ids():
    """Gantt ids whose board card a person deleted (MC recycle bin) -> never recreate that card."""
    out = set()
    for f in glob.glob(os.path.join(WS, "mission-control", "data", "recycle-bin", "*.jsonl")):
        try:
            for line in open(f):
                if '"sched:' not in line: continue
                rec = (json.loads(line).get("record") or {})
                out.update(t[6:] for t in (rec.get("tags") or []) if str(t).startswith("sched:"))
        except Exception:
            pass
    return out


def due_iso(d):
    return (d or "")[:10] + "T23:59:59+00:00" if d else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--project", default="tw-902146")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    linked = {}
    for c in supa("GET", "tasks?select=id,title,owner,state,due_date,assigned_email,tags&tags=ov.{%s}" %
                  ",".join("sched:" + t["id"] for t in gantt_tasks(a.project))) or []:
        for tg in c.get("tags") or []:
            if tg.startswith("sched:"): linked[tg[6:]] = c
    report = {"updated": [], "created": [], "conflicts": [], "unowned": [], "removed": [], "unchanged": 0}
    deleted = recycled_sched_ids()

    for g in gantt_tasks(a.project):
        # Phil Eaton 10/22: a Cancelled task comes off the Gantt and stays closed. Same if its card was deleted.
        c0 = linked.get(g["id"])
        if norm(g["state"]) in {"cancelled", "canceled"}:            # cancelled on the Schedule page -> close the card too
            if a.apply and c0 and norm(c0["state"]) not in {"cancelled", "canceled"}: supa("PATCH", f"tasks?id=eq.{c0['id']}", {"state": "Cancelled"})
            if a.apply: erp_remove(g["id"])
            report["removed"].append({"card": c0["id"] if c0 else None, "title": g["title"], "why": "cancelled on schedule"}); continue
        if (c0 and norm(c0["state"]) in {"cancelled", "canceled"}) or (not c0 and g["id"] in deleted):
            if a.apply: erp_remove(g["id"])
            report["removed"].append({"card": c0["id"] if c0 else "(deleted)", "title": g["title"]}); continue
        person = PEOPLE.get(norm(g["owner"]))
        if not person:
            report["unowned"].append({"gantt": g["title"], "owner": g["owner"]}); continue
        owner, email = person
        gantt_closed = norm(g["state"]) in CLOSED
        card = linked.get(g["id"])
        if not card:
            q = "tasks?select=id,title,owner,state,due_date,assigned_email,tags&title=ilike." + urllib.parse.quote(g["title"].replace("*", ""))
            cands = [c for c in (supa("GET", q) or []) if norm(c["title"]) == norm(g["title"])]
            cands.sort(key=lambda c: (norm(c["state"]) in CLOSED, "teamwork" not in (c.get("tags") or [])))
            card = cands[0] if cands else None
        if card and card["state"] == "Done" and not gantt_closed:   # Done means done (Phil 10/22)
            # Work is marked Done on the person's Task board card -> mark the Gantt task Done.
            if a.apply: erp_set_done(g["id"])
            report["updated"].append({"card": card["id"], "title": g["title"], "changes": ["Gantt state → Done (card is Done)"]})
            gantt_closed = True
        if card and norm(card["state"]) in CLOSED and not gantt_closed:
            # Never reopen a closed card, but still carry the Gantt owner/date so the two never disagree.
            report["conflicts"].append({"card": card["id"], "title": g["title"], "board_state": card["state"], "gantt_owner": owner, "gantt_due": (g["due_date"] or "")[:10]})
        if not card:
            if gantt_closed: continue
            body = {"title": g["title"], "owner": owner, "assigned_email": email, "state": "To Do",
                    "due_date": due_iso(g["due_date"]), "category": "Blk3 Flight", "source": "blk3-schedule",
                    "tags": ["blk3-schedule", "Blk3 Flight", "sched:" + g["id"]],
                    "description": f"BLK3 schedule task ({g.get('list') or 'BLK3'}). Start {(g['start_date'] or '')[:10]}, due {(g['due_date'] or '')[:10]}.\n"
                                   f"Owner and dates come from the BLK3 Gantt: {GANTT_URL}\nChange dates/owner on the Schedule page; this card follows."}
            if a.apply:
                out = supa("POST", "tasks", body)
                body["id"] = out[0]["id"] if out else None
            report["created"].append({"card": body.get("id"), "title": g["title"], "owner": owner, "due": (g["due_date"] or "")[:10]})
            continue
        patch, why = {}, []
        if card.get("owner") != owner or (card.get("assigned_email") or "") != email:
            patch.update(owner=owner, assigned_email=email); why.append(f"owner {card.get('owner') or '—'} → {owner}")
        if (card.get("due_date") or "")[:10] != (g["due_date"] or "")[:10]:
            patch["due_date"] = due_iso(g["due_date"]); why.append(f"due {(card.get('due_date') or '—')[:10]} → {(g['due_date'] or '')[:10]}")
        if gantt_closed and norm(card["state"]) not in CLOSED:
            patch["state"] = "Done"; why.append("state → Done")
        tags = card.get("tags") or []
        if "sched:" + g["id"] not in tags:
            patch["tags"] = [t for t in tags if not t.startswith("sched:")] + ["sched:" + g["id"], "blk3-schedule"]
        if not patch:
            report["unchanged"] += 1; continue
        if a.apply:
            supa("PATCH", f"tasks?id=eq.{card['id']}", patch)
        if why:
            report["updated"].append({"card": card["id"], "title": g["title"], "changes": why})
        else:
            report["unchanged"] += 1

    if a.json:
        print(json.dumps(report, indent=1))
    else:
        print(f"{'APPLIED' if a.apply else 'DRY RUN'}: updated {len(report['updated'])}, created {len(report['created'])}, "
              f"conflicts {len(report['conflicts'])}, unowned {len(report['unowned'])}, removed {len(report['removed'])}, unchanged {report['unchanged']}")
        for k in ("updated", "created", "conflicts", "unowned", "removed"):
            for r in report[k]: print(" ", k, r)


if __name__ == "__main__":
    main()
