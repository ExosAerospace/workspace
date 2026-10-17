#!/usr/bin/env python3
"""qb_je_approval.py — QuickBooks journal entries posted by Decision approval (qb-je-approval-exo3).

Exo stages balanced journal entries; Kyle (or Jon) gets one "EXO3: Approve & post journal entries" card.
Nothing touches the books until a HUMAN answers Approve & post. Hold = stays staged. Reject = dropped.

  qb_je_approval.py stage --batch <json>   # validate + store a batch, file the Decision (approver Kyle)
  qb_je_approval.py watch                  # post approved batches (chained in com.exos.qb-invoice-watch, 300s)
  qb_je_approval.py --selftest             # exo3 eval (offline: no QB call, no Decision)

Batch JSON: {"id","title","why","approver_email","task", "entries":[{"date","doc","memo",
             "lines":[{"acct_id","acct","dr"|"cr","desc"}]}]}
Jon 2026-10-17: "record the information in QB for Kyle to just approve" (Round 7 note payoffs, #3853).
"""
import argparse, datetime, json, os, re, sys, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
STATE = os.path.join(WS, "mission-control/data/qb-je-batches.json")
DECISIONS = os.path.join(WS, "mission-control/data/decisions.json")
TOKEN = os.path.join(WS, "mission-control/data/.decisions-token")
LOG = os.path.join(WS, "logs/qb-je-approval.log")
AGENT, OWNER = "qb-je-approval-exo3", "John Quinn"
OPT_POST, OPT_HOLD, OPT_REJECT = "Approve & post", "Hold", "Reject"
HUMAN_APPROVERS = ("kballard@exosaero.com", "jquinn@exosaero.com")


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG, "a").write(f"{now()} {m}\n")
    print(m)


def jload(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def jsave(p, d):
    tmp = p + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def fleet(action, detail, outcome=None, level="info"):
    try:
        from fleet_log import event
        event(AGENT, "orchestrate", action, detail=detail, owner=OWNER, outcome=outcome, level=level)
    except Exception:
        pass


def validate(batch):
    """Every entry balances to the cent, has lines on real account ids, and a date. Returns list of errors."""
    errs = []
    if not batch.get("entries"):
        errs.append("no entries")
    for i, e in enumerate(batch.get("entries", [])):
        dr = round(sum(float(l.get("dr", 0)) for l in e.get("lines", [])), 2)
        cr = round(sum(float(l.get("cr", 0)) for l in e.get("lines", [])), 2)
        if dr != cr or dr <= 0:
            errs.append(f"entry {i} ({e.get('doc')}) unbalanced: dr {dr} cr {cr}")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", e.get("date", "")):
            errs.append(f"entry {i} bad date")
        for l in e.get("lines", []):
            if not str(l.get("acct_id", "")).isdigit():
                errs.append(f"entry {i} line without QB account id: {l}")
            if bool(l.get("dr")) == bool(l.get("cr")):
                errs.append(f"entry {i} line must be exactly one of dr/cr: {l}")
    return errs


def to_qb(e, batch_id):
    lines = []
    for l in e["lines"]:
        amt = float(l.get("dr") or l.get("cr"))
        lines.append({"DetailType": "JournalEntryLineDetail", "Amount": round(amt, 2),
                      "Description": l.get("desc") or e.get("memo", ""),
                      "JournalEntryLineDetail": {"PostingType": "Debit" if l.get("dr") else "Credit",
                                                 "AccountRef": {"value": str(l["acct_id"])}}})
    return {"TxnDate": e["date"], "DocNumber": e["doc"][:21], "Line": lines,
            "PrivateNote": f"{e.get('memo', '')} | Posted by Exo on Decision approval (batch {batch_id})"[:4000]}


def file_decision(batch):
    tok = open(TOKEN).read().strip()
    rows = []
    for e in batch["entries"]:
        rows.append(f"\n{e['doc']} · {e['date']} · {e.get('memo', '')}")
        for l in e["lines"]:
            side = f"Dr {float(l['dr']):>12,.2f}" if l.get("dr") else f"   Cr {float(l['cr']):>12,.2f}"
            rows.append(f"   {side}  {l['acct']}" + (f" — {l['desc']}" if l.get("desc") else ""))
    ctx = (batch.get("why", "") + "\n\nJOURNAL ENTRIES (balanced; nothing is in QuickBooks yet):" + "\n".join(rows)
           + ("\n\n" + batch["notes"] if batch.get("notes") else "")
           + f"\n\nOn Approve & post: Exo posts exactly these entries to QuickBooks (DocNumbers above) and notes the "
             f"QB ids on task #{batch.get('task', '')}. Hold = stays staged. Reject = discarded, nothing posted. "
             "Need a change? Answer with the change as an instruction and Exo restages.")
    body = {"source": "QB Journal Entries (exo3)", "title": f"EXO3: Approve & post journal entries — {batch['title']}",
            "question": f"Post these {len(batch['entries'])} journal entries to QuickBooks?",
            "context": ctx, "proposedAction": "Approve & post — Exo posts the entries to QuickBooks.",
            "type": "choice", "options": [OPT_POST, OPT_HOLD, OPT_REJECT], "priority": "high",
            "relatedItem": str(batch.get("task", "")), "dedupeKey": f"qb-je:{batch['id']}",
            "approver": batch["approver_email"], "assignedTo": batch["approver_email"], "agentClass": "qb-je"}
    req = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-Exo-Token": tok})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())["id"]


def stage(a):
    batch = json.load(open(a.batch))
    errs = validate(batch)
    if errs:
        log("REFUSED stage: " + "; ".join(errs)); fleet("stage_refused", {"batch": batch.get("id"), "errs": errs}, "refused", "warn")
        return 2
    st = jload(STATE, {"batches": []})
    if any(b["id"] == batch["id"] for b in st["batches"]):
        log(f"batch {batch['id']} already staged"); return 0
    batch.update(status="pending", staged_at=now(), decision_id=file_decision(batch))
    st["batches"].append(batch); jsave(STATE, st)
    log(f"staged {batch['id']} ({len(batch['entries'])} JEs) -> {batch['decision_id']}")
    fleet("staged", {"batch": batch["id"], "decision": batch["decision_id"], "entries": len(batch["entries"])}, "ok")
    return 0


def human(d):
    by, em = (d.get("answeredBy") or "").strip().lower(), (d.get("answeredByEmail") or "").strip().lower()
    if not (by or em) or em.startswith("exo@") or re.search(r"\b(exo|exobot|agent|cron|bot|resolver|triage)\b", by):
        return False
    return (em in HUMAN_APPROVERS) or bool(re.search(r"\b(kyle|ballard|john|jon|quinn)\b", by))


def decide(batch, d):
    """Pure decision logic (selftested): returns 'post' | 'hold' | 'reject' | 'wait' | 'skip_nonhuman'."""
    ans = (d.get("answer") or "").strip().lower()
    if d.get("status") in (None, "open", "pending") or not ans:
        return "wait"
    if not human(d):
        return "skip_nonhuman"
    if ans.startswith("approve"):
        return "post"
    if ans.startswith("reject"):
        return "reject"
    return "hold"


def watch(a):
    st = jload(STATE, {"batches": []})
    if not any(b["status"] == "pending" for b in st["batches"]):
        return 0
    from qb_invoice import _api
    decs = jload(DECISIONS, [])
    decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    byid = {d.get("id"): d for d in decs}
    for b in st["batches"]:
        if b["status"] != "pending":
            continue
        d = byid.get(b["decision_id"]) or {}
        act = decide(b, d)
        if act in ("wait", "hold"):
            continue
        if act == "skip_nonhuman":
            log(f"skip {b['decision_id']}: needs a human answer"); continue
        if act == "reject":
            b.update(status="rejected", closed_at=now()); log(f"REJECTED {b['id']}"); fleet("rejected", {"batch": b["id"]}, "ok")
            continue
        if validate(b):
            b.update(status="error", error="failed re-validation"); continue
        posted = b.setdefault("posted", {})
        try:
            for e in b["entries"]:
                if e["doc"] in posted:
                    continue  # idempotent across ticks
                r = _api("POST", "journalentry", to_qb(e, b["id"]))
                posted[e["doc"]] = r["JournalEntry"]["Id"]
                jsave(STATE, st)
            b.update(status="posted", closed_at=now(), approved_by=d.get("answeredBy") or d.get("answeredByEmail"))
            log(f"POSTED {b['id']}: {posted}")
            fleet("posted", {"batch": b["id"], "qb_ids": posted, "by": b["approved_by"]}, "ok")
        except Exception as ex:
            b["error"] = str(ex)[:400]; log(f"ERROR posting {b['id']}: {ex}")
            fleet("post_failed", {"batch": b["id"], "err": str(ex)[:200]}, "error", "warn")
    jsave(STATE, st)
    return 0


def selftest():
    ok = 0
    def t(c, label):
        nonlocal ok
        if not c:
            print("FAIL:", label); sys.exit(1)
        ok += 1
    good = {"id": "t", "title": "t", "approver_email": "kballard@exosaero.com", "entries": [
        {"date": "2026-03-02", "doc": "T1", "memo": "m", "lines": [{"acct_id": "333", "acct": "N", "dr": 50000},
                                                                  {"acct_id": "203", "acct": "P", "cr": 1.25},
                                                                  {"acct_id": "209", "acct": "C", "cr": 49998.75}]}]}
    t(validate(good) == [], "balanced batch validates")
    bad = json.loads(json.dumps(good)); bad["entries"][0]["lines"][2]["cr"] = 49998.0
    t(any("unbalanced" in x for x in validate(bad)), "unbalanced batch refused")
    noid = json.loads(json.dumps(good)); noid["entries"][0]["lines"][0]["acct_id"] = "Notes"
    t(any("account id" in x for x in validate(noid)), "line without QB account id refused")
    both = json.loads(json.dumps(good)); both["entries"][0]["lines"][0]["cr"] = 5
    t(any("exactly one" in x for x in validate(both)), "line with both dr and cr refused")
    q = to_qb(good["entries"][0], "t")
    t(q["Line"][0]["JournalEntryLineDetail"]["PostingType"] == "Debit" and q["Line"][1]["JournalEntryLineDetail"]["PostingType"] == "Credit", "QB payload sides")
    t(decide(good, {"status": "open"}) == "wait", "open card waits")
    t(decide(good, {"status": "answered", "answer": "Approve & post", "answeredBy": "Exo resolver"}) == "skip_nonhuman", "agent answer never posts")
    t(decide(good, {"status": "answered", "answer": "Approve & post", "answeredByEmail": "kballard@exosaero.com"}) == "post", "Kyle approve posts")
    t(decide(good, {"status": "answered", "answer": "Approve & post", "answeredBy": "Random Person"}) == "skip_nonhuman", "non-approver answer never posts")
    t(decide(good, {"status": "answered", "answer": "Hold", "answeredBy": "Kyle Ballard"}) == "hold", "hold stays staged")
    t(decide(good, {"status": "answered", "answer": "Reject", "answeredBy": "John Quinn"}) == "reject", "reject drops")
    t(decide(good, {"status": "answered", "answer": "use 3/31 date instead", "answeredBy": "Kyle Ballard"}) == "hold", "instruction = hold for restage")
    print(f"qb_je_approval selftest: {ok}/{ok} pass")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest(); sys.exit(0)
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd")
    s = sp.add_parser("stage"); s.add_argument("--batch", required=True)
    sp.add_parser("watch")
    a = ap.parse_args()
    sys.exit(stage(a) if a.cmd == "stage" else watch(a) if a.cmd == "watch" else ap.print_help())
