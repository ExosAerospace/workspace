#!/usr/bin/env python3
"""qb_invoice.py — QuickBooks invoices issued by Decision approval (nobody logs in to QB).

Jon 2026-10-01: approved QB WRITE access for invoicing; invoices go out by Decision review + approval.

Flow:
  prepare  → find/create the QB Customer, create the invoice in QB (UNSENT), pull QuickBooks' own PDF
             to drafts/invoices/, file an "EXO3: Approve & send invoice" Decision card (approver = Jon).
  watch    → (launchd, every few min) for each invoice card:
               "Approve & send"  → QuickBooks emails the invoice from its own mailer (PDF attached +
                                   "Review and pay" link, card/ACH via QB Payments) → payload-order
                                   milestone marked invoiced.
               "Cancel invoice"  → the unsent invoice is deleted from QB.
               "Hold"            → nothing; stays unsent.
             Also polls sent invoices: Balance == 0 in QB → milestone marked paid (+ payload-customer
             registry on M1, same as the MC button).

SAFETY: nothing is emailed to a customer without an answered "Approve & send" card. The only QB writes
are Customer create, Invoice create/delete(unsent only)/send. No payments, no journal entries.

Usage:
  qb_invoice.py prepare --order PO2C-2026-001 --milestone M1 [--terms "Net 30"] [--dry-run]
  qb_invoice.py prepare --customer "Acme" --email ap@acme.com --amount 1234.56 --desc "..." [--item "Test Services"]
  qb_invoice.py watch [--dry-run]
"""
import argparse, json, os, re, sys, urllib.request, urllib.parse, urllib.error, datetime, subprocess

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import qb_client as q

ORDERS = os.path.join(WS, "mission-control/data/payload-orders.json")
DECISIONS = os.path.join(WS, "mission-control/data/decisions.json")
STATE = os.path.join(WS, "mission-control/data/qb-invoices.json")
OUTDIR = os.path.join(WS, "drafts/invoices")
LOG = os.path.join(WS, "logs/qb-invoice.log")
TOKEN = os.path.join(WS, "mission-control/data/.decisions-token")
PAYLOAD_CUSTOMER = os.path.join(WS, "scripts/payload_customer.py")
JON = "jquinn@exosaero.com"
PCT = {"M1": 50, "M2": 40, "M3": 10}
MS_LABEL = {"M1": "slot reservation (50%)", "M2": "L-120 milestone (40%)", "M3": "post-flight data delivery (10%)"}
OPT_SEND, OPT_HOLD, OPT_CANCEL = "Approve & send", "Hold", "Cancel invoice"
# Internal program names that must never appear on a customer invoice (Jon 2026-10-01: "we do not want
# pathfinder on any invoice"). Checked at prepare AND re-checked against QB's live line text before send.
INVOICE_BANNED = ("pathfinder",)


def banned_terms(text):
    return [t for t in INVOICE_BANNED if t in (text or "").lower()]


def flight_text(mission_id, m):
    """Customer-facing flight line: 'Mission M6 (BLK3 S0)'. Mission id + vehicle/serial only — no internal names."""
    veh = " ".join(x for x in (m.get("vehicle"), m.get("vehicle_serial")) if x)
    return f"Mission {mission_id}" + (f" ({veh})" if veh else "")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(m):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{now()} {m}\n")
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


# ── QB REST (write) ──────────────────────────────────────────────────────────
def _api(method, path, body=None, accept="application/json", params=None, _retried=False):
    access, realm, env = q.get_access_token()
    p = {"minorversion": "73", **(params or {})}
    url = f"{q._base(env)}/v3/company/{realm}/{path}?" + urllib.parse.urlencode(p)
    data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
    hdr = {"Authorization": f"Bearer {access}", "Accept": accept}
    if body is not None:
        hdr["Content-Type"] = "application/json"
    elif method == "POST":
        hdr["Content-Type"] = "application/octet-stream"
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return raw if accept != "application/json" else json.loads(raw)
    except urllib.error.HTTPError as e:
        if e.code == 401 and not _retried:
            return _api(method, path, body, accept, params, _retried=True)
        raise RuntimeError(f"QB {method} {path} → {e.code}: {q._http_err_body(e)[:400]}") from e


def qesc(s):
    return str(s).replace("'", "\\'")


def find_or_create_customer(name, email, dry):
    r = q.query(f"select Id, DisplayName, PrimaryEmailAddr from Customer where DisplayName = '{qesc(name)}'")
    if r.get("Customer"):
        return r["Customer"][0]["Id"], False
    if dry:
        return "(new)", True
    body = {"DisplayName": name, "CompanyName": name}
    if email:
        body["PrimaryEmailAddr"] = {"Address": email}
    c = _api("POST", "customer", body)["Customer"]
    log(f"created QB customer {c['Id']} {name}")
    return c["Id"], True


def ref_by_name(entity, name):
    r = q.query(f"select Id, Name from {entity} where Name = '{qesc(name)}'")
    rows = r.get(entity) or []
    if not rows:
        raise SystemExit(f"QB {entity} '{name}' not found")
    return rows[0]["Id"]


def next_doc_number():
    """Books use custom txn numbers (0069, 0070, CLIN-…) — QB won't auto-number API invoices. Next = max numeric + 1."""
    r = q.query("select DocNumber from Invoice orderby MetaData.CreateTime desc maxresults 300")
    nums = [int(i["DocNumber"]) for i in r.get("Invoice", []) if str(i.get("DocNumber", "")).isdigit() and len(str(i["DocNumber"])) <= 5]
    return f"{(max(nums) + 1) if nums else 1:04d}"


def invoice_pdf(inv_id, doc):
    os.makedirs(OUTDIR, exist_ok=True)
    pdf = _api("GET", f"invoice/{inv_id}/pdf", accept="application/pdf")
    fn = os.path.join(OUTDIR, f"Exos_Invoice_{doc or inv_id}.pdf")
    open(fn, "wb").write(pdf)
    return fn


def write_cover_email(rec, contact_name=None):
    """Jon 2026-10-01: an invoice never goes out bare — it needs an intro email. Write the cover email
    next to the PDF (<pdf>_cover_email.txt); decision-send-watcher puts it at the top of the
    ready-to-send so Jon can paste it and attach the PDF. [____] marks anything Jon must fill."""
    first = (contact_name or "").split()[0] if contact_name else "[____]"
    due = (datetime.datetime.now() + datetime.timedelta(days=int(re.sub(r"\D", "", rec["terms"]) or 30))).strftime("%B %-d, %Y")
    ms = f"Milestone {rec['milestone']} on payload order {rec['order']}" if rec.get("order") else "the work described"
    txt = (f"To: {contact_name + ' ' if contact_name else ''}<{rec['email']}>\n"
           f"Subject: Exos Invoice #{rec['doc_number']} — {rec['customer']}\n"
           f"Attachment: {os.path.basename(rec['pdf'])}\n\n"
           f"Hi {first},\n\n"
           f"Attached is Exos Invoice #{rec['doc_number']} for ${rec['amount']:,.2f}, covering {ms}.\n\n"
           f"- Billed to: {rec['customer']}\n- Terms: {rec['terms']}, due {due}\n"
           f"- Payment: by wire. We'll send wire instructions separately; please confirm them with us by phone before sending funds.\n\n"
           f"[____ one line on what this payment unlocks / next step]\n\n"
           f"Thanks, and let me know if you have any questions.\n\nBest,\nJohn Quinn\nCofounder & CEO\n")
    fn = os.path.splitext(rec["pdf"])[0] + "_cover_email.txt"
    if not os.path.exists(fn):  # never clobber a hand-edited cover email
        open(fn, "w").write(txt)
    return fn


def file_decision(rec):
    tok = open(TOKEN).read().strip()
    rel_pdf = os.path.relpath(rec["pdf"], WS)
    ctx = (f"Customer: {rec['customer']} — invoice goes to {rec['email']}\n"
           f"Amount: ${rec['amount']:,.2f} · Terms: {rec['terms']} · QB invoice #{rec['doc_number']} (QB Id {rec['qb_id']})\n"
           f"Line: {rec['desc']}\n"
           f"Invoice PDF (exactly what the customer gets): {rel_pdf}\n"
           + (f"Cover email (intro that goes with the invoice): {rec['cover_email']}\n" if rec.get("cover_email") else "")
           + (f"Payload order: {rec['order']} {rec['milestone']}\n" if rec.get("order") else "")
           + (f"\n{rec['note']}\n" if rec.get("note") else "")
           + "\nOn Approve & send: QuickBooks emails it from its own mailer with the PDF and a 'Review and pay' "
             "link (card/ACH through QB Payments, so payment posts to QB automatically). Hold = stays unsent. "
             "Cancel invoice = deleted from QB (it was never sent).")
    body = {
        "source": "QB Invoicing (exo3)", "title": f"EXO3: Approve & send invoice — {rec['customer']} ${rec['amount']:,.0f}",
        "question": f"Send QuickBooks invoice #{rec['doc_number']} for ${rec['amount']:,.2f} to {rec['customer']} ({rec['email']})?",
        "context": ctx, "proposedAction": "Approve & send — QuickBooks emails the invoice + pay link; MC milestone marked invoiced.",
        "type": "choice", "options": [OPT_SEND, OPT_HOLD, OPT_CANCEL], "priority": "high",
        "relatedItem": rec.get("order") or "", "dedupeKey": f"qb-invoice:{rec['qb_id']}",
        "approver": JON, "assignedTo": JON, "agentClass": "qb-invoice",
    }
    req = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-Exo-Token": tok})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())["id"]


def attach_pdf_to_decision(rec):
    """Put the invoice PDF on the Decision card (uploads/_meta.json decision_id) so Jon reviews it
    right on /decisions.html — the related payload-order task docs (LSA etc.) appear alongside."""
    import shutil, time, uuid
    mc = os.path.join(WS, "mission-control")
    meta_path = os.path.join(mc, "uploads/_meta.json")
    meta = json.load(open(meta_path))
    f = os.path.basename(rec["pdf"])
    if any(m.get("decision_id") == rec["decision_id"] and m.get("filename", "").endswith(f) for m in meta):
        return
    stored = f"{int(time.time()*1000)}_{f}"
    shutil.copy2(rec["pdf"], os.path.join(mc, "uploads", stored))
    meta.append({"id": uuid.uuid4().hex[:16], "filename": f"Invoice #{rec['doc_number']} (exactly what the customer gets) — {f}",
                 "stored_name": stored, "size": os.path.getsize(os.path.join(mc, "uploads", stored)), "extension": ".pdf",
                 "task_id": None, "project_id": None, "decision_id": rec["decision_id"], "doc_key": f"qb-invoice-{rec['qb_id']}",
                 "version": 1, "current": True, "uploaded_by": "Exo", "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    tmp = meta_path + ".tmp"; json.dump(meta, open(tmp, "w"), indent=2); os.replace(tmp, meta_path)


# ── prepare ──────────────────────────────────────────────────────────────────
def prepare(a):
    st = jload(STATE, {"invoices": []})
    order = None
    if a.order:
        od = jload(ORDERS, {"orders": []})
        order = next((o for o in od["orders"] if o["id"] == a.order), None)
        if not order:
            raise SystemExit(f"order {a.order} not found")
        ms = a.milestone or "M1"
        if not all(c.get("clear") for c in order.get("csl") or []) or order.get("export", {}).get("status") in (None, "unscreened"):
            raise SystemExit("export + CSL screen must be complete before invoicing (same gate as MC)")
        if (order.get("milestones") or {}).get(ms, {}).get("invoiced_at"):
            raise SystemExit(f"{a.order} {ms} already invoiced")
        live = [r for r in st["invoices"] if r.get("order") == a.order and r.get("milestone") == ms and r["status"] in ("pending", "sent", "paid")]
        if live:
            raise SystemExit(f"{a.order} {ms} already has QB invoice {live[0]['doc_number']} ({live[0]['status']})")
        cv = float(order["contract_value"])
        amount = round(cv * PCT[ms] / 100, 2)
        customer, email = order["customer"], order.get("contact_email")
        if not order.get("mission"):
            raise SystemExit(f"{a.order} has no mission number (M5, M6, ...) — set it on the payload order first")
        mlabel = next((m for m in jload(os.path.join(WS, "mission-control/data/missions.json"), {}).get("missions", []) if m["id"] == order["mission"]), {})
        flight_txt = flight_text(order["mission"], mlabel)
        desc = (f"{order.get('payload_name') or customer + ' payload'} — {flight_txt} payload integration & flight. "
                f"Milestone {ms}: {MS_LABEL[ms]} of ${cv:,.0f} contract (payload order {order['id']}).")
        item = a.item or "Payload Sale"
    else:
        if not (a.customer and a.amount and a.desc):
            raise SystemExit("need --order, or --customer/--amount/--desc")
        customer, email, amount, desc, ms = a.customer, a.email, float(a.amount), a.desc, None
        item = a.item or "Contract Services"
    if not email:
        raise SystemExit("no customer billing email — QB can't send without one")

    if banned_terms(desc):
        raise SystemExit(f"invoice text contains internal term(s) {banned_terms(desc)} — not allowed on a customer invoice")
    terms = a.terms or "Net 30"
    if a.dry_run:
        cid, new = find_or_create_customer(customer, email, True)
        print(json.dumps({"doc_number": a.doc_number or next_doc_number(), "customer": customer, "qb_customer": cid, "new_customer": new, "email": email, "amount": amount,
                          "item": item, "terms": terms, "desc": desc}, indent=1))
        return
    cid, _ = find_or_create_customer(customer, email, False)
    inv = {
        "CustomerRef": {"value": cid},
        "Line": [{"DetailType": "SalesItemLineDetail", "Amount": amount, "Description": desc,
                  "SalesItemLineDetail": {"ItemRef": {"value": ref_by_name("Item", item)}, "Qty": 1, "UnitPrice": amount}}],
        "SalesTermRef": {"value": ref_by_name("Term", terms)},
        "BillEmail": {"Address": email},
        "AllowOnlineACHPayment": True, "AllowOnlineCreditCardPayment": True,
        "EmailStatus": "NotSet",
        "PrivateNote": f"Created by Exo via MC (qb_invoice.py); sends only on Decision approval. {order['id'] + ' ' + ms if order else ''}".strip(),
    }
    inv["DocNumber"] = a.doc_number or next_doc_number()
    created = _api("POST", "invoice", inv)["Invoice"]
    rec = {"qb_id": created["Id"], "doc_number": created.get("DocNumber") or created["Id"], "customer": customer,
           "email": email, "amount": amount, "terms": terms, "desc": desc, "order": order["id"] if order else None,
           "milestone": ms, "status": "pending", "created_at": now(), "note": a.note or ""}
    rec["pdf"] = invoice_pdf(rec["qb_id"], rec["doc_number"])
    rec["cover_email"] = os.path.relpath(write_cover_email(rec, (order or {}).get("contact_name")), WS)
    rec["decision_id"] = file_decision(rec)
    try:
        attach_pdf_to_decision(rec)
    except Exception as e:
        log(f"WARN could not attach invoice PDF to {rec['decision_id']}: {e}")
    st["invoices"].append(rec)
    jsave(STATE, st)
    if order:
        _order_log(order["id"], f"{ms} QB invoice drafted", f"#{rec['doc_number']} ${amount:,.2f} — awaiting {rec['decision_id']}",
                   lambda m: m.update({"qb_invoice_id": rec["qb_id"], "qb_doc_number": rec["doc_number"], "qb_status": "pending_approval"}), ms)
    log(f"prepared QB invoice {rec['doc_number']} (Id {rec['qb_id']}) {customer} ${amount:,.2f} → {rec['decision_id']}")


def _order_log(order_id, action, detail, mutate=None, ms=None):
    od = jload(ORDERS, None)
    if not od:
        return None
    o = next((x for x in od["orders"] if x["id"] == order_id), None)
    if not o:
        return None
    if mutate and ms:
        o.setdefault("milestones", {}).setdefault(ms, {})
        mutate(o["milestones"][ms])
    o.setdefault("history", []).append({"at": now(), "by": "Exo", "email": "exo@exosaero.com", "action": action, "detail": detail})
    jsave(ORDERS, od)
    return o


# ── watch ────────────────────────────────────────────────────────────────────
def watch(a):
    st = jload(STATE, {"invoices": []})
    decs = jload(DECISIONS, [])
    decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    byid = {d.get("id"): d for d in decs}
    changed = False
    today = datetime.date.today().isoformat()
    for r in st["invoices"]:
        if r["status"] == "pending":
            d = byid.get(r.get("decision_id")) or {}
            ans = (d.get("answer") or "").strip()
            if d.get("status") in (None, "open", "pending") or not ans:
                continue
            by, by_email = (d.get("answeredBy") or "").strip().lower(), (d.get("answeredByEmail") or "").strip().lower()
            if not (by or by_email) or by_email.startswith("exo@") or re.search(r"\b(exo|exobot|agent|cron|bot|resolver|triage)\b", by):
                log(f"skip {r['decision_id']}: answered by '{by or by_email}' — invoice actions need a human answer")
                continue
            if ans.lower().startswith("approve"):
                live = q.query(f"select * from Invoice where Id = '{r['qb_id']}'").get("Invoice") or [{}]
                bad = banned_terms(" ".join(str(l.get("Description") or "") for l in live[0].get("Line", [])) + " " + str(live[0].get("CustomerMemo", {}).get("value") or ""))
                if bad:
                    log(f"BLOCKED send of QB invoice {r['doc_number']}: line text contains {bad} — fix the invoice, then re-approve")
                    continue
                if a.dry_run:
                    print("WOULD SEND", r["doc_number"], r["email"]); continue
                res = _api("POST", f"invoice/{r['qb_id']}/send", params={"sendTo": r["email"]})["Invoice"]
                r.update(status="sent", sent_at=now(), approved_by=d.get("answeredBy") or "Jon", email_status=res.get("EmailStatus"))
                if r.get("order"):
                    def mut(m, r=r):
                        m.update(invoice_no=r["doc_number"], invoiced_at=today, invoiced_by="Exo (QB, approved " + r["decision_id"] + ")", qb_status="sent")
                    _order_log(r["order"], f"{r['milestone']} invoiced", f"QB #{r['doc_number']} emailed by QuickBooks to {r['email']} · approved {r['decision_id']}", mut, r["milestone"])
                log(f"SENT QB invoice {r['doc_number']} to {r['email']} (approved {r['decision_id']})")
                changed = True
            elif ans.lower().startswith("cancel"):
                if a.dry_run:
                    print("WOULD DELETE", r["doc_number"]); continue
                cur = q.query(f"select Id, SyncToken, EmailStatus from Invoice where Id = '{r['qb_id']}'").get("Invoice") or []
                if cur and cur[0].get("EmailStatus") != "EmailSent":
                    _api("POST", "invoice", {"Id": r["qb_id"], "SyncToken": cur[0]["SyncToken"]}, params={"operation": "delete"})
                r.update(status="cancelled", cancelled_at=now())
                if r.get("order"):
                    _order_log(r["order"], f"{r['milestone']} QB invoice cancelled", f"#{r['doc_number']} deleted unsent ({r['decision_id']})",
                               lambda m: [m.pop(k, None) for k in ("qb_invoice_id", "qb_doc_number", "qb_status")], r["milestone"])
                log(f"cancelled QB invoice {r['doc_number']} ({r['decision_id']})")
                changed = True
            # Hold → leave pending; Jon can re-answer the card later.
        elif r["status"] == "sent":
            cur = q.query(f"select Id, Balance, TotalAmt from Invoice where Id = '{r['qb_id']}'").get("Invoice") or []
            if not cur or float(cur[0].get("Balance", 1)) > 0:
                continue
            if a.dry_run:
                print("WOULD MARK PAID", r["doc_number"]); continue
            amt = float(cur[0]["TotalAmt"])
            r.update(status="paid", paid_at=now())
            if r.get("order"):
                def mut(m, amt=amt):
                    m.update(paid_at=today, amount_received=amt, recorded_by="Exo (QB payment sync)", qb_status="paid")
                o = _order_log(r["order"], f"{r['milestone']} paid", f"${amt:,.2f} · QB #{r['doc_number']} balance 0", mut, r["milestone"])
                if o and r["milestone"] == "M1" and os.path.exists(PAYLOAD_CUSTOMER):
                    args = ["/usr/bin/python3", PAYLOAD_CUSTOMER, "add", "--company", o["customer"],
                            "--payload-name", o.get("payload_name") or o["customer"] + " payload", "--mission", o.get("flight") or "BLK3",
                            "--flight-no", o.get("mission") or "", "--contract-id", o["id"], "--amount-paid", str(amt), "--paid-date", today,
                            "--notes", "M1 deposit via QB invoice " + r["doc_number"]]
                    if o.get("mass_kg"): args += ["--mass-kg", str(o["mass_kg"])]
                    if o.get("flight_date"): args += ["--flight-date", o["flight_date"]]
                    if o.get("contract_value"): args += ["--contract-value", str(o["contract_value"])]
                    subprocess.run(args, timeout=60)
            log(f"PAID QB invoice {r['doc_number']} ${amt:,.2f}")
            changed = True
    if changed:
        jsave(STATE, st)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepare")
    for f in ("order", "milestone", "customer", "email", "amount", "desc", "item", "terms", "note", "doc_number"):
        p.add_argument("--" + f.replace("_", "-"), dest=f)
    p.add_argument("--dry-run", action="store_true")
    w = sp.add_parser("watch")
    w.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    prepare(a) if a.cmd == "prepare" else watch(a)


if __name__ == "__main__":
    main()
