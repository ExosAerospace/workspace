#!/usr/bin/env python3
"""expense-workflow.py — advance expense reports through the workflow.

Reads the ledger (mission-control/data/expense-reports.json):
  - state 'submitted': when the manager's approval task is Done -> create payment task(s)
    for the role holders in expense-roles.json, move to 'approved'.
  - state 'approved': when all payment tasks are Done -> 'paid'.

Deterministic (model out of the loop). Runs on a launchd timer. --apply to write (default dry-run).
"""
import json, os, sys, urllib.request

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(WS, "mission-control", "data", "expense-reports.json")
ROLES = os.path.join(WS, "mission-control", "data", "expense-roles.json")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
APPLY = "--apply" in sys.argv
DONE = {"done", "complete", "completed", "approved", "paid"}


def jpy_note(e):
    """Yen reimbursement (Jon 2026-10-15): payment task tells Finance to pay in JPY on the international rail
    (EXOS-FIN-004), not a USD ACH. Empty string for USD reports."""
    if e.get("pay_currency") != "JPY":
        return ""
    fx = e.get("pay_fx") or {}
    return (f" PAY IN JPY: ¥{int(e.get('pay_amount_jpy') or 0):,}" + (f" (H.10 ¥{fx.get('rate')}/$ {fx.get('date')})" if fx else "")
            + " via the international JPY rail per EXOS-FIN-004 International Contractor & Expense Payments; record the actual JPY sent + USD debited.")


def _selftest():
    assert jpy_note({"pay_currency": "USD"}) == "", "USD report -> no JPY instruction"
    n = jpy_note({"pay_currency": "JPY", "pay_amount_jpy": 15834, "pay_fx": {"rate": 158.34, "date": "2026-10-09"}})
    assert "¥15,834" in n and "158.34" in n and "EXOS-FIN-004" in n, "JPY report -> yen amount, rate and procedure on the payment task"
    assert "¥0" in jpy_note({"pay_currency": "JPY"}), "missing amount still flags JPY payment"
    print("expense-workflow selftest: 3/3 pass")


def sreq(method, path, body=None):
    req = urllib.request.Request(
        SUPA + "/" + path, method=method,
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"},
        data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        t = r.read().decode()
        return json.loads(t) if t else []


def task_state(tid):
    try:
        d = sreq("GET", f"tasks?id=eq.{tid}&select=id,state")
        return (d[0]["state"] if d else "") or ""
    except Exception:
        return ""


def main():
    try: led = json.load(open(LEDGER))
    except Exception: led = []
    try: approvers = json.load(open(ROLES)).get("payment_approvers", [])
    except Exception: approvers = []
    changed = 0
    for e in led:
        st = e.get("state")
        if st == "submitted" and e.get("approval_task_id"):
            if task_state(e["approval_task_id"]).lower() in DONE:
                print(f"{e['id']}: manager approved -> payment tasks for {[a.get('role') for a in approvers]}")
                if APPLY:
                    ptids = []
                    _amt = (f"${float(e['amount']):,.2f}" if isinstance(e.get('amount'), (int, float)) else f"${e.get('amount', '?')}")
                    _sub = (e.get('submitter_email') or '').lower()
                    _jpy = jpy_note(e)
                    for ap in approvers:
                        # Segregation of duties: never route the payment task to the person who submitted it.
                        if (ap.get('email') or '').lower() == _sub:
                            print(f"  skip payer {ap.get('email')} (is the submitter of {e['id']})"); continue
                        task = {
                            "title": f"Pay expense report — {e.get('submitter_name')} ({_amt}{' / ¥' + format(int(e.get('pay_amount_jpy') or 0), ',') + ' JPY' if _jpy else ''})",
                            "owner": ap.get("role"), "assigned_email": ap.get("email"), "assigned_to": ap.get("role"),
                            "state": "To Do", "priority": 80, "category": "Expense",
                            "source": "expense-workflow", "tags": ["expense-payment"],
                            "description": (f"APPROVED expense from {e.get('submitter_name')} ({e.get('submitter_email')}). "
                                            f"Amount {_amt} · Purpose: {e.get('purpose','—')}. File: {e.get('file')}. "
                                            f"Manager {e.get('manager_name')} approved. Action for your role ({ap.get('role')}): process payment.{_jpy} Ref {e['id']}."),
                        }
                        created = sreq("POST", "tasks", task)
                        if created: ptids.append(created[0]["id"])
                    e["payment_task_id"] = ptids
                    e["state"] = "approved"
                    changed += 1
        elif st == "approved" and e.get("payment_task_id"):
            ids = e["payment_task_id"] if isinstance(e["payment_task_id"], list) else [e["payment_task_id"]]
            if ids and all(task_state(t).lower() in DONE for t in ids):
                print(f"{e['id']}: payment complete -> paid")
                if APPLY:
                    e["state"] = "paid"
                    changed += 1
    if APPLY and changed:
        json.dump(led, open(LEDGER, "w"), indent=2)
    print(f"{'applied' if APPLY else 'dry-run'}: {changed} change(s)")


if "--selftest" in sys.argv:
    _selftest()
else:
    main()
