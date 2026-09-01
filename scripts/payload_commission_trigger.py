# -*- coding: utf-8 -*-
"""
payload_commission_trigger.py — fire a Mission Control commission-check task whenever
payload-contracted funds are RECEIVED against an EXECUTED + SIGNED Launch Services Agreement.

Jon's rule (2026-09-01): the receipt of payload-contract money is the trigger to cut a payload
sales commission check. It must fire even when NO commission salesperson is attributed (e.g. entX)
— in that case the task asks Jon to confirm attribution or waive; there is simply no check to cut
until an agent is attributed. This is the audit trigger that never lets a payload receipt slip past
the commission process.

Source of truth:
  - config/payload_lsa_contracts.json  -> which customers have an executed/signed payload LSA
  - QuickBooks (scripts/qb_client.py)  -> actual Payment records per customer (money in the door)
Idempotent: every QB Payment Id is processed once (state file + Supabase source-key dedupe).
Money never moves here — it only files an approval/decision task in Mission Control.

If an agent IS attributed (config attributed_agent set), this also invokes the commission tracker
(erp-foundation/record_payment.js) so the commission accrues + a payout task is filed per agreement.

Run:
  python3 scripts/payload_commission_trigger.py --dry                 # show what would fire, no writes
  python3 scripts/payload_commission_trigger.py --onboard entX Limited # one baseline task for funds already received, seed them seen
  python3 scripts/payload_commission_trigger.py                       # normal: 1 task per NEW payment (cron)
"""
import os, sys, json, subprocess, urllib.request, urllib.parse, urllib.error, datetime

WS = os.path.expanduser("~/.openclaw/workspace")
sys.path.insert(0, os.path.join(WS, "scripts"))
import qb_client as qb

CONFIG = os.path.join(WS, "config", "payload_lsa_contracts.json")
STATE = os.path.join(WS, "mission-control", "data", "payload_commission_state.json")
SEC = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
SB_KEY = SEC["supabase_service_role_key"]

DRY = "--dry" in sys.argv
ONBOARD = None
if "--onboard" in sys.argv:
    ONBOARD = " ".join(sys.argv[sys.argv.index("--onboard") + 1:]).strip()


def _money(n):
    return "${:,.0f}".format(float(n or 0))


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"seen_payment_ids": [], "onboarded_contracts": []}


def save_state(st):
    json.dump(st, open(STATE, "w"), indent=1)


def load_contracts():
    d = json.load(open(CONFIG))
    return [c for c in d.get("contracts", []) if c.get("lsa_executed")]


def qb_payments_for(customer_id):
    """All QB Payments for a customer, newest first. Each: Id, TxnDate, TotalAmt."""
    r = qb.query("SELECT Id, TxnDate, TotalAmt, CustomerRef FROM Payment "
                 "WHERE CustomerRef = '%s' ORDERBY TxnDate DESC MAXRESULTS 1000" % customer_id)
    pays = (r or {}).get("Payment", []) or []
    return [{"id": p["Id"], "date": p.get("TxnDate"), "amount": float(p.get("TotalAmt") or 0)}
            for p in pays]


def supabase_task_exists(source_key):
    """Dedupe backstop independent of the local state file."""
    try:
        url = SB + "/tasks?" + urllib.parse.urlencode({"source": "eq." + source_key, "select": "id"})
        req = urllib.request.Request(url, headers={"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return len(json.load(resp)) > 0
    except Exception:
        return False


def file_task(task, source_key):
    if supabase_task_exists(source_key):
        print("  (task already exists for %s — skip)" % source_key)
        return None
    body = json.dumps(task).encode()
    req = urllib.request.Request(SB + "/tasks", data=body, method="POST",
        headers={"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        j = json.load(resp)
    tid = j[0]["id"] if isinstance(j, list) and j else "?"
    print("  filed MC task #%s — %s" % (tid, task["title"]))
    return tid


def attribution_clause(c):
    agent = c.get("attributed_agent")
    if agent:
        return ("Commission agent **%s** is attributed to this contract — the commission tracker "
                "(erp-foundation/record_payment.js) accrues the commission per agreement and files a "
                "payout task. Approve + pay via QuickBooks." % agent)
    return ("NO commission sales agent is attributed to this contract, so there is no check to cut yet. "
            "ACTION: confirm attribution via `node erp-foundation/attribute.js --contract %s --agent-email <email>` "
            "(commission then accrues automatically), OR mark this waived. This task is the audit trigger that "
            "fires on every payload-contract receipt." % c.get("contract_id"))


def accrue_if_attributed(c, pay):
    """If an agent is attributed, run the commission tracker so it accrues + files the payout task."""
    if not c.get("attributed_agent") or DRY:
        return
    try:
        subprocess.run(["node", os.path.join(WS, "erp-foundation", "record_payment.js"),
                        "--contract", c["contract_id"], "--amount", str(pay["amount"]),
                        "--date", pay["date"], "--customer", c["qb_customer"]],
                       cwd=os.path.join(WS, "erp-foundation"), timeout=60, capture_output=True)
        print("  -> commission tracker accrued for %s" % c["attributed_agent"])
    except Exception as e:
        print("  record_payment.js failed:", e)


def make_task(c, pay, running, is_onboard=False):
    total = float(c.get("contract_total") or 0)
    pct = (" (%.0f%% of %s contract)" % (100.0 * running / total, _money(total))) if total else ""
    due = (datetime.date.fromisoformat(pay["date"]) + datetime.timedelta(days=30)).isoformat() \
        if pay.get("date") else datetime.date.today().isoformat()
    if is_onboard:
        source_key = "payload-commission-trigger:onboard:" + c["contract_id"]
        title = "Payload commission check (baseline) — %s: %s received to date" % (c["qb_customer"], _money(running))
        desc = ("Onboarding %s (%s) to the payload-commission trigger. Payload-contract funds RECEIVED to date "
                "against the EXECUTED/SIGNED LSA = %s%s (QuickBooks). %s Going forward, each NEW payment auto-files "
                "its own commission-check task." % (c["qb_customer"], c["contract_id"], _money(running), pct,
                                                    attribution_clause(c)))
    else:
        source_key = "payload-commission-trigger:qbpmt:" + pay["id"]
        title = "Payload commission check — %s: %s received%s" % (c["qb_customer"], _money(pay["amount"]),
                                                                  pct.strip() and " " + pct.strip() or "")
        desc = ("Payload-contract funds RECEIVED against the EXECUTED/SIGNED LSA (%s, %s). Payment %s on %s "
                "(QB Payment %s). Running total received %s%s. %s"
                % (c["contract_id"], c["qb_customer"], _money(pay["amount"]), pay.get("date"), pay["id"],
                   _money(running), pct, attribution_clause(c)))
    task = {"title": title, "description": desc, "category": "EXOS ADMIN", "priority": 80,
            "due_date": due + "T23:59:59Z", "owner": "Jon", "assigned_to": "Jon",
            "assigned_email": "jquinn@exosaero.com", "source": source_key, "state": "To Do"}
    return task, source_key


def main():
    st = load_state()
    seen = set(st.get("seen_payment_ids", []))
    contracts = load_contracts()
    if not contracts:
        print("no executed-LSA payload contracts in config"); return
    filed = 0
    for c in contracts:
        cid = c.get("qb_customer_id")
        pays = qb_payments_for(cid) if cid else []
        received = sorted([p for p in pays if p["amount"] > 0], key=lambda p: p.get("date") or "")
        total_recv = sum(p["amount"] for p in received)
        print("%s (%s): %d payment(s), %s received" % (c["qb_customer"], c["contract_id"], len(received), _money(total_recv)))

        onboarding = ONBOARD and ONBOARD.lower() in (c["qb_customer"].lower(), c["contract_id"].lower())
        if onboarding:
            task, sk = make_task(c, {"date": received[-1]["date"] if received else None}, total_recv, is_onboard=True)
            if DRY:
                print("  [dry] onboard task:", task["title"]); filed += 1
            else:
                if file_task(task, sk):
                    filed += 1
                for p in received:
                    seen.add(p["id"])
                if c["contract_id"] not in st.get("onboarded_contracts", []):
                    st.setdefault("onboarded_contracts", []).append(c["contract_id"])
            continue

        # normal mode: one task per NOT-yet-seen payment
        running = 0.0
        for p in received:
            running += p["amount"]
            if p["id"] in seen:
                continue
            task, sk = make_task(c, p, running)
            if DRY:
                print("  [dry] new payment %s %s -> %s" % (p["id"], _money(p["amount"]), task["title"]))
            else:
                file_task(task, sk)
                accrue_if_attributed(c, p)
                seen.add(p["id"])
            filed += 1

    if not DRY:
        st["seen_payment_ids"] = sorted(seen)
        save_state(st)
    print("done — %d task(s) %s" % (filed, "would fire (dry)" if DRY else "filed"))


if __name__ == "__main__":
    main()
