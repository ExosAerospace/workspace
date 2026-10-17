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

Offering invoices (watches etc.) are prepared by scripts/invoice_command_exo3.py ('@Exobot invoice <product>'
email command) through prepare() with qty/unit_price/offering set; watch() then moves the offering ledger
entry Invoiced / Cancelled (unit released) / Paid via invoice_command_exo3.ledger_mark().
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
MS_LABEL = {"M1": "slot reservation (50%)", "M2": "L-120 milestone (40%)", "M3": "post-flight data delivery (10%)",
            "INK": "$1 documentation invoice for an in-kind payment"}
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


PHONE_RE = re.compile(r"\+?1?[\s.\-]?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")


def bill_block(customer, email, phone, address):
    """Task #3418 (10/5): every invoice must show the customer's address, phone AND email. QB's invoice PDF
    prints BillAddr only (not the customer's phone/email), so put all of them in BillAddr as free-form lines (max 5)."""
    addr = [s.strip() for s in re.split(r"\n|;", address or "") if s.strip()]
    if len(addr) > 2:   # name + 2 address lines + phone + email = 5 lines, which is QB's limit
        addr = [addr[0], ", ".join(addr[1:])]
    lines = [customer] + addr + [f"Phone: {phone}", f"Email: {email}"]
    return {f"Line{i + 1}": l[:500] for i, l in enumerate(lines[:5])}


def contact_gaps(bill_addr, email):
    """What's missing from an invoice's billing block, as a list of words (empty = OK to send)."""
    lines = [str(v) for k, v in (bill_addr or {}).items() if k.startswith("Line") and v]
    gaps = []
    if not email:
        gaps.append("email")
    if not any(PHONE_RE.search(l) for l in lines):
        gaps.append("phone")
    if not any(re.search(r"\d", l) and not l.startswith(("Phone:", "Email:")) for l in lines[1:]) and not (bill_addr or {}).get("City"):
        gaps.append("address")
    return gaps


def customer_contact(cid):
    """(phone, address) already on the QB customer record, if any."""
    c = (q.query(f"select * from Customer where Id = '{cid}'").get("Customer") or [{}])[0]
    phone = (c.get("PrimaryPhone") or {}).get("FreeFormNumber") or (c.get("Mobile") or {}).get("FreeFormNumber")
    b = c.get("BillAddr") or {}
    parts = [b.get(k) for k in ("Line1", "Line2", "Line3") if b.get(k)]
    cityline = " ".join(x for x in [(b.get("City") or "") + ("," if b.get("City") else ""), b.get("CountrySubDivisionCode"), b.get("PostalCode")] if x)
    if cityline.strip(" ,"):
        parts.append(cityline.strip())
    return phone, "; ".join(parts) or None


def update_customer_contact(cid, phone, address):
    c = (q.query(f"select * from Customer where Id = '{cid}'").get("Customer") or [{}])[0]
    body = {"Id": cid, "SyncToken": c["SyncToken"], "sparse": True}
    if phone:
        body["PrimaryPhone"] = {"FreeFormNumber": phone}
    if address:
        parts = [s.strip() for s in re.split(r"\n|;", address) if s.strip()]
        body["BillAddr"] = {f"Line{i + 1}": p for i, p in enumerate(parts[:4])}
    _api("POST", "customer", body)


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
    if "receipt" in (rec.get("terms") or "").lower():
        due = "upon receipt"
    else:
        due = (datetime.datetime.now() + datetime.timedelta(days=int(re.sub(r"\D", "", rec["terms"]) or 30))).strftime("%B %-d, %Y")
    ms = f"Milestone {rec['milestone']} on payload order {rec['order']}" if rec.get("order") else (
        rec["desc"].rstrip(".") if rec.get("offering") else "the work described")
    pay = ("online by card or bank transfer (ACH) through the 'Review and pay' link in the QuickBooks invoice email."
           if rec.get("offering") else
           "by wire. We'll send wire instructions separately; please confirm them with us by phone before sending funds.")
    txt = (f"To: {contact_name + ' ' if contact_name else ''}<{rec['email']}>\n"
           f"Subject: Exos Invoice #{rec['doc_number']} — {rec['customer']}\n"
           f"Attachment: {os.path.basename(rec['pdf'])}\n\n"
           f"Hi {first},\n\n"
           f"Attached is Exos Invoice #{rec['doc_number']} for ${rec['amount']:,.2f}, covering {ms}.\n\n"
           f"- Billed to: {rec['customer']}\n- Terms: {rec['terms']}" + ("" if due == "upon receipt" else f", due {due}") + "\n"
           f"- Payment: {pay}\n\n"
           f"[____ one line on what this payment unlocks / next step]\n\n"
           f"Thanks, and let me know if you have any questions.\n\nBest,\nJohn Quinn\nCofounder & CEO\n")
    fn = os.path.splitext(rec["pdf"])[0] + "_cover_email.txt"
    if not os.path.exists(fn):  # never clobber a hand-edited cover email
        open(fn, "w").write(txt)
    return fn


def _invoice_cards(decs, qb_id):
    """Every Approve & send card ever filed for one QB invoice (base dedupeKey plus any :suffix re-files)."""
    k = f"qb-invoice:{qb_id}"
    return [d for d in decs if (d.get("dedupeKey") or "") == k or (d.get("dedupeKey") or "").startswith(k + ":")]


def _is_action(ans):
    return (ans or "").strip().lower().startswith(("approve", "hold", "cancel"))


def file_decision(rec, dedupe_suffix="", preface=""):
    # One open card per invoice (#3774: a second hand-filed card for #0075 made Jon answer twice). If one is
    # already open, or Jon already answered one with Approve/Hold/Cancel, reuse it instead of filing another.
    decs = jload(DECISIONS, [])
    decs = decs if isinstance(decs, list) else decs.get("decisions", [])
    for d in sorted(_invoice_cards(decs, rec["qb_id"]), key=lambda d: d.get("created") or "", reverse=True):
        if d.get("status") in (None, "open", "pending") or (d.get("status") == "answered" and _is_action(d.get("answer"))):
            log(f"not filing a new card for QB invoice {rec['doc_number']}: {d.get('id')} already covers it")
            return d.get("id")
    tok = open(TOKEN).read().strip()
    rel_pdf = os.path.relpath(rec["pdf"], WS)
    ctx = ((preface + "\n\n" if preface else "") +
           f"Customer: {rec['customer']} — invoice goes to {rec['email']}\n"
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
        "relatedItem": rec.get("order") or ((rec.get("offering") or {}).get("entry_id") or ""), "dedupeKey": f"qb-invoice:{rec['qb_id']}{dedupe_suffix}",
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
def crm_phone(email):
    """Phone from ANY CRM contact record with this email. The CRM holds several auto-captured
    records per person and only one may carry the phone (10/12: Kordel's number sat on 1 of 7
    'kordel@scentience.ai' records while invoice #0071 was blocked for 'missing phone')."""
    try:
        import urllib.parse
        sec = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
        k = sec["supabase_service_role_key"]
        u = ("https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/contacts?select=phone,updated_at"
             f"&email=ilike.{urllib.parse.quote(email or '')}&phone=not.is.null&order=updated_at.desc.nullslast&limit=1")
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=20).read())
        return (r[0].get("phone") or "").strip() or None if r else None
    except Exception:
        return None


def crm_address(email):
    """Billing address from the CRM for this email, same idea as crm_phone(). contacts has no address column, so
    payload_questionnaire.py writes a structured 'Billing address: street; city, ST zip [source]' notes line on
    every record for the email; fall back to the linked company's address column."""
    try:
        import urllib.parse
        k = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
        h = {"apikey": k, "Authorization": "Bearer " + k}
        base = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
        rows = json.loads(urllib.request.urlopen(urllib.request.Request(
            base + f"contacts?select=notes,company_id,updated_at&email=ilike.{urllib.parse.quote(email or '')}"
                   "&order=updated_at.desc.nullslast&limit=20", headers=h), timeout=20).read())
        for r in rows:
            m = re.search(r"^Billing address:\s*(.+?)\s*(?:\[[^\]]*\])?\s*$", r.get("notes") or "", re.I | re.M)
            if m:
                return m.group(1).strip()
        for cid in {r["company_id"] for r in rows if r.get("company_id")}:
            co = json.loads(urllib.request.urlopen(urllib.request.Request(
                base + f"companies?select=address&id=eq.{cid}", headers=h), timeout=20).read())
            a = ((co or [{}])[0].get("address") or "").strip()
            if re.search(r"\d", a):
                return a
    except Exception:
        return None
    return None


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
        ik = order.get("in_kind")
        if ik and ms != "INK":
            raise SystemExit(f"{a.order} is paid in kind — only the $1 INK documentation invoice applies")
        if ms == "INK" and not ik:
            raise SystemExit(f"{a.order} is not an in-kind order")
        amount = 1.00 if ms == "INK" else round(cv * PCT[ms] / 100, 2)
        customer, email = order["customer"], order.get("contact_email")
        if not order.get("mission"):
            raise SystemExit(f"{a.order} has no mission number (M5, M6, ...) — set it on the payload order first")
        mlabel = next((m for m in jload(os.path.join(WS, "mission-control/data/missions.json"), {}).get("missions", []) if m["id"] == order["mission"]), {})
        flight_txt = flight_text(order["mission"], mlabel)
        if ms == "INK":
            iv = float(ik.get("value") or cv)
            desc = (f"{order.get('payload_name') or customer + ' payload'} — {flight_txt} payload integration & flight. "
                    f"Paid in kind: {ik.get('description')} (value ${iv:,.0f}, matching the standard price). "
                    f"$1.00 documentation invoice (payload order {order['id']}).")
        else:
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
    phone = getattr(a, "phone", None) or (order or {}).get("contact_phone") or crm_phone(email)
    address = getattr(a, "address", None) or (order or {}).get("billing_address") or crm_address(email)

    if banned_terms(desc):
        raise SystemExit(f"invoice text contains internal term(s) {banned_terms(desc)} — not allowed on a customer invoice")
    terms = a.terms or "Net 30"
    qty = int(getattr(a, "qty", None) or 1)
    unit = round(float(getattr(a, "unit_price", None) or amount / qty), 2)
    if abs(round(qty * unit, 2) - amount) > 0.005:
        raise SystemExit(f"qty x unit price ({qty} x {unit}) != amount {amount}")
    offering = getattr(a, "offering", None)
    if a.dry_run:
        cid, new = find_or_create_customer(customer, email, True)
        if not new:
            p0, a0 = customer_contact(cid)
            phone, address = phone or p0, address or a0
        gaps = contact_gaps(bill_block(customer, email, phone, address) if address else {"Line1": customer, "Line2": f"Phone: {phone}" if phone else ""}, email)
        if gaps:
            raise SystemExit(f"invoice must carry the customer's address, phone and email — missing: {', '.join(gaps)} (task #3418)")
        out = {"doc_number": a.doc_number or next_doc_number(), "customer": customer, "qb_customer": cid, "new_customer": new, "email": email, "amount": amount,
               "qty": qty, "unit_price": unit, "item": item, "item_id": ref_by_name("Item", item), "terms": terms,
               "terms_id": ref_by_name("Term", terms), "desc": desc, "dry_run": True}
        print(json.dumps(out, indent=1))
        return out
    found = q.query(f"select Id from Customer where DisplayName = '{qesc(customer)}'").get("Customer")
    if found:
        p0, a0 = customer_contact(found[0]["Id"])
        phone, address = phone or p0, address or a0
    gaps = contact_gaps(bill_block(customer, email, phone, address) if address else {"Line1": customer, "Line2": f"Phone: {phone}" if phone else ""}, email)
    if gaps:   # checked BEFORE creating anything in QB
        raise SystemExit(f"invoice must carry the customer's address, phone and email — missing: {', '.join(gaps)} (task #3418)")
    cid, _ = find_or_create_customer(customer, email, False)
    update_customer_contact(cid, phone, address)
    inv = {
        "BillAddr": bill_block(customer, email, phone, address),
        "CustomerRef": {"value": cid},
        "Line": [{"DetailType": "SalesItemLineDetail", "Amount": amount, "Description": desc,
                  "SalesItemLineDetail": {"ItemRef": {"value": ref_by_name("Item", item)}, "Qty": qty, "UnitPrice": unit}}],
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
    if offering:
        rec["offering"] = dict(offering, qty=qty, unit_price=unit)
    rec["pdf"] = invoice_pdf(rec["qb_id"], rec["doc_number"])
    rec["cover_email"] = os.path.relpath(write_cover_email(rec, (order or {}).get("contact_name") or (customer if offering else None)), WS)
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
    return rec


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
def _offering_mark(r, status):
    """Move the offering-ledger entry (watch pre-orders etc.) — never let a ledger hiccup break invoicing."""
    if not r.get("offering"):
        return
    try:
        import invoice_command_exo3
        invoice_command_exo3.ledger_mark(r, status)
    except Exception as e:
        log(f"WARN offering ledger update failed for #{r.get('doc_number')} -> {status}: {e}")

# ── auto-draft the next milestone (Jon 10/16: "if I click Done, what handles the next steps — invoice etc?") ──
M2_LEAD_DAYS = 7   # draft M2 a week before L-120 so the Approve & send card is waiting when it falls due


def auto_prepare_due(a):
    """Draft the M2 (40%, L-120) QB invoice for every executed payload order once it is within M2_LEAD_DAYS of
    L-120. Same gates as a hand-run `prepare` (CSL/export, mission no., billing block) and the same output: an
    UNSENT QB invoice + an "Approve & send" Decision for Jon. Nothing reaches the customer without his answer.
    One attempt per order/milestone per day so a blocked draft (e.g. missing billing phone) logs once, not every 5 min."""
    od = jload(ORDERS, {"orders": []})
    st = jload(STATE, {"invoices": []})
    today = datetime.date.today()
    tried = st.setdefault("auto_prepare", {})
    for o in od.get("orders", []):
        if o.get("in_kind") or not o.get("flight_date") or o.get("status") in ("cancelled", "closed"):
            continue
        ms = o.get("milestones") or {}
        if not (ms.get("M1") or {}).get("paid_at") or (ms.get("M2") or {}).get("invoiced_at"):
            continue
        due = datetime.date.fromisoformat(o["flight_date"][:10]) - datetime.timedelta(days=120)
        if today < due - datetime.timedelta(days=M2_LEAD_DAYS):
            continue
        if any(r.get("order") == o["id"] and r.get("milestone") == "M2" and r["status"] in ("pending", "sent", "paid") for r in st["invoices"]):
            continue
        key = f"{o['id']}:M2"
        if tried.get(key) == today.isoformat():
            continue
        tried[key] = today.isoformat(); jsave(STATE, st)
        if a.dry_run:
            print("WOULD DRAFT M2", o["id"], "L-120", due.isoformat()); continue
        ns = argparse.Namespace(order=o["id"], milestone="M2", customer=None, email=None, phone=None, address=None, amount=None,
                                desc=None, item=None, terms=None, note=f"auto-drafted: L-120 = {due.isoformat()}", doc_number=None, dry_run=False)
        try:
            prepare(ns)
            st = jload(STATE, {"invoices": []})   # prepare() saved its own record
            _fleet("m2_autodraft", {"order": o["id"], "l120": due.isoformat()}, "drafted")
        except SystemExit as e:
            log(f"auto-draft M2 for {o['id']} blocked: {e}")
            _order_log(o["id"], "M2 auto-draft blocked", str(e))
            _fleet("m2_autodraft", {"order": o["id"], "l120": due.isoformat(), "blocker": str(e)}, "blocked")


def _fleet(action, detail, outcome):
    """exo3 telemetry → logs/fleet-events.jsonl."""
    if os.environ.get("QBI_SELFTEST"):
        return
    try:
        import fleet_log
        fleet_log.event("qb-invoice-watch", "orchestrate", action, detail=detail, owner="John Quinn", outcome=outcome)
    except Exception:
        pass


def selftest():
    """Failure replay (Jon 10/16, Scentience): clicking Done on M1 left nobody to raise the M2 (40%, L-120)
    invoice. auto_prepare_due must draft M2 once, inside the 7-day lead, for paid-M1 orders only — never in-kind,
    cancelled, already-invoiced or early orders, and only one attempt per order per day. prepare() is stubbed:
    no QB call, no Decision, no live data touched."""
    import tempfile
    global ORDERS, STATE, LOG, prepare
    os.environ["QBI_SELFTEST"] = "1"
    t = tempfile.mkdtemp()
    ORDERS, STATE, LOG = (os.path.join(t, n) for n in ("orders.json", "state.json", "log"))
    today = datetime.date.today()
    fd = lambda days_to_l120: (today + datetime.timedelta(days=120 + days_to_l120)).isoformat()
    paid = {"M1": {"paid_at": "2026-10-01"}}
    orders = [
        {"id": "due", "flight_date": fd(5), "milestones": paid},
        {"id": "early", "flight_date": fd(30), "milestones": paid},
        {"id": "m1-unpaid", "flight_date": fd(5), "milestones": {}},
        {"id": "in-kind", "in_kind": True, "flight_date": fd(5), "milestones": paid},
        {"id": "cancelled", "status": "cancelled", "flight_date": fd(5), "milestones": paid},
        {"id": "m2-done", "flight_date": fd(5), "milestones": dict(paid, M2={"invoiced_at": "2026-10-10"})},
        {"id": "overdue", "flight_date": fd(-3), "milestones": paid},
    ]
    json.dump({"orders": orders}, open(ORDERS, "w")); json.dump({"invoices": []}, open(STATE, "w"))
    calls = []
    def fake_prepare(ns):
        calls.append((ns.order, ns.milestone))
        st = jload(STATE, {"invoices": []})
        st["invoices"].append({"order": ns.order, "milestone": ns.milestone, "status": "pending"}); jsave(STATE, st)
    prepare = fake_prepare
    a = argparse.Namespace(dry_run=False)
    auto_prepare_due(a)
    first = sorted(calls)
    auto_prepare_due(a)   # second watch tick (5 min later) must not draft again
    checks = {
        "paid-M1 order inside 7-day lead drafted as M2": ("due", "M2") in first,
        "overdue L-120 order drafted": ("overdue", "M2") in first,
        "early / unpaid / in-kind / cancelled / already-invoiced skipped": len(first) == 2,
        "second tick does not re-draft": len(calls) == 2,
    }
    bad = [k for k, v in checks.items() if not v]
    print(f"qb_invoice selftest: {len(checks) - len(bad)}/{len(checks)} pass" + (f" FAIL {bad}" if bad else ""))
    return 1 if bad else 0


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
            if not _is_action(d.get("answer")):
                # #3774: the record can point at a card answered with an instruction while Jon approved a sibling
                # card for the same invoice. Act on the latest Approve/Hold/Cancel card instead (it still sends only once).
                acted = sorted((x for x in _invoice_cards(decs, r["qb_id"]) if x.get("status") == "answered" and _is_action(x.get("answer"))),
                               key=lambda x: x.get("answeredAt") or "")
                if acted:
                    d = acted[-1]
                    if r.get("decision_id") != d.get("id"):
                        r.setdefault("history", []).append({"at": now(), "event": f"decision {r.get('decision_id')} -> {d.get('id')} (answered {d.get('answer')})"})
                        r["decision_id"] = d.get("id"); changed = True
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
                gaps = contact_gaps(live[0].get("BillAddr"), (live[0].get("BillEmail") or {}).get("Address"))
                if gaps:
                    log(f"BLOCKED send of QB invoice {r['doc_number']}: billing block missing {', '.join(gaps)} (task #3418) — "
                        f"run `qb_invoice.py contact --qb-id {r['qb_id']} --phone ... --address ...`; the approval stands and it sends on the next watch")
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
                _offering_mark(r, "Invoiced")
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
                _offering_mark(r, "Cancelled")
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
                if o and r["milestone"] in ("M1", "INK") and os.path.exists(PAYLOAD_CUSTOMER):
                    args = ["/usr/bin/python3", PAYLOAD_CUSTOMER, "add", "--company", o["customer"],
                            "--payload-name", o.get("payload_name") or o["customer"] + " payload", "--mission", o.get("flight") or "BLK3",
                            "--flight-no", o.get("mission") or "", "--contract-id", o["id"], "--amount-paid", str(amt), "--paid-date", today,
                            "--notes", "M1 deposit via QB invoice " + r["doc_number"]]
                    if o.get("mass_kg"): args += ["--mass-kg", str(o["mass_kg"])]
                    if o.get("flight_date"): args += ["--flight-date", o["flight_date"]]
                    if o.get("contract_value"): args += ["--contract-value", str(o["contract_value"])]
                    subprocess.run(args, timeout=60)
            log(f"PAID QB invoice {r['doc_number']} ${amt:,.2f}")
            _offering_mark(r, "Paid")
            changed = True
    if changed:
        jsave(STATE, st)
    auto_prepare_due(a)


def contact(a):
    """Add/fix the customer's phone + address on an UNSENT invoice (and its QB customer), then refresh the PDF
    that Jon reviews on the Decision. Task #3418."""
    inv = (q.query(f"select * from Invoice where Id = '{a.qb_id}'").get("Invoice") or [None])[0]
    if not inv:
        raise SystemExit(f"QB invoice Id {a.qb_id} not found")
    if inv.get("EmailStatus") == "EmailSent":
        raise SystemExit(f"invoice {inv.get('DocNumber')} was already sent; not editing it")
    cid, name = inv["CustomerRef"]["value"], inv["CustomerRef"].get("name")
    email = (inv.get("BillEmail") or {}).get("Address")
    p0, a0 = customer_contact(cid)
    phone, address = a.phone or p0, a.address or a0
    block = bill_block(name, email, phone, address) if address else {"Line1": name, "Line2": f"Phone: {phone}" if phone else "", "Line3": f"Email: {email}"}
    if a.dry_run:
        print(json.dumps({"BillAddr": block, "gaps": contact_gaps(block, email)}, indent=1)); return
    update_customer_contact(cid, a.phone, a.address)
    _api("POST", "invoice", {"Id": inv["Id"], "SyncToken": inv["SyncToken"], "sparse": True, "BillAddr": {k: v for k, v in block.items() if v}})
    st = jload(STATE, {"invoices": []})
    rec = next((r for r in st["invoices"] if r["qb_id"] == str(a.qb_id)), None)
    if rec:
        pdf = invoice_pdf(rec["qb_id"], rec["doc_number"])
        meta_path = os.path.join(WS, "mission-control/uploads/_meta.json")
        meta = json.load(open(meta_path))
        for m in meta:   # refresh the copy on the Decision card in place
            if m.get("decision_id") == rec.get("decision_id") and m.get("doc_key") == f"qb-invoice-{rec['qb_id']}":
                import shutil
                shutil.copy2(pdf, os.path.join(WS, "mission-control/uploads", m["stored_name"]))
                m["size"] = os.path.getsize(pdf)
        tmp = meta_path + ".tmp"; json.dump(meta, open(tmp, "w"), indent=2); os.replace(tmp, meta_path)
    gaps = contact_gaps(block, email)
    # Jon answered the original card with an instruction (not Approve/Hold/Cancel): watch() never acts on
    # that, so once the billing block is complete, re-file a fresh Approve & send card for this invoice.
    if rec and not gaps and rec.get("status") == "pending":
        decs = jload(DECISIONS, [])
        decs = decs if isinstance(decs, list) else decs.get("decisions", [])
        d = next((x for x in decs if x.get("id") == rec.get("decision_id")), {})
        ans = (d.get("answer") or "").strip().lower()
        if d.get("status") == "answered" and not ans.startswith(("approve", "hold", "cancel")):
            n = len(rec.get("history", [])) + 2
            rec["decision_id"] = file_decision(rec, dedupe_suffix=f":r{n}", preface=(
                f"RE-FILED: per your note on {d.get('id')}, the invoice now shows the customer's address, phone and email "
                f"(see the PDF). Ready to approve."))
            rec.setdefault("history", []).append({"at": now(), "event": f"re-filed after {d.get('id')} instruction (contact block)"})
            jsave(STATE, st)
            attach_pdf_to_decision(rec)
            log(f"re-filed Approve & send card {rec['decision_id']} for QB invoice {rec['doc_number']} (was {d.get('id')})")
    log(f"contact updated on QB invoice {inv.get('DocNumber')} (Id {inv['Id']}); still missing: {gaps or 'nothing'}")
    print(json.dumps({"doc": inv.get("DocNumber"), "BillAddr": block, "missing": gaps}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prepare")
    for f in ("order", "milestone", "customer", "email", "phone", "address", "amount", "desc", "item", "terms", "note", "doc_number"):
        p.add_argument("--" + f.replace("_", "-"), dest=f)
    p.add_argument("--dry-run", action="store_true")
    w = sp.add_parser("watch")
    w.add_argument("--dry-run", action="store_true")
    c = sp.add_parser("contact", help="add/fix customer phone + address on an unsent invoice")
    c.add_argument("--qb-id", required=True)
    c.add_argument("--phone")
    c.add_argument("--address", help="street; city, ST zip  (';' or newline separates lines)")
    c.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    {"prepare": prepare, "watch": watch, "contact": contact}[a.cmd](a)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    main()
