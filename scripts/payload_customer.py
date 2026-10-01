#!/usr/bin/env python3
"""
payload_customer.py — record a paid payload against a customer and flag them a
FORMER/ACTIVE payload customer in the CRM.

Exo runs this any time a customer PAYS for a payload. It writes directly to
mission-control/data/payload-customers.json (the registry Mission Control joins onto
CRM/company rows for the green "Payload Customer" badge and true customer metrics).
No server required — the MC server reads this file live on every request.

Each payload entry captures the high-level CONTRACT + PAYLOAD detail and the
SIGNED-CONTRACT reference so we can report true customer metrics (who paid, how many
payloads, total contract $ vs paid $).

Examples:
  # log a paid payload
  python3 scripts/payload_customer.py add \
      --company "Acme Space" \
      --payload-name "AstroSensor-1" --mission "BLK3 / SARGE Mar-2027" \
      --flight-date 2027-03 --mass-kg 8 \
      --contract-id "PSA-2026-014" --contract-value 60000 --amount-paid 30000 \
      --paid-date 2026-09-04 --signed-contract "data-room/contracts/AcmeSpace_PSA_signed.pdf" \
      --signed-date 2026-08-20 --notes "50% deposit received; balance on integration"

  # show the registry + metrics (feeds UTD Capstone customer reporting)
  python3 scripts/payload_customer.py list
"""
import argparse
import datetime
import json
import os
import re
import sys

WS = "/Users/exomac/.openclaw/workspace"
REG = os.path.join(WS, "mission-control", "data", "payload-customers.json")


def norm(s):
    """Match the server's _mndaNorm: lowercase, strip non-alphanumeric."""
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower())


def base(s):
    """norm() minus corporate suffixes, so 'Scentience' matches 'Scentience, Inc.'."""
    return re.sub(r"(incorporated|inc|llc|ltd|limited|corp|corporation|co|gmbh|bv|sa|srl|plc)$", "", norm(s)) or norm(s)


def find_key(reg, company):
    k = norm(company)
    if k in reg:
        return k
    b = base(company)
    hits = [x for x, r in reg.items() if base(r.get("company") or x) == b]
    return hits[0] if len(hits) == 1 else k


def load():
    try:
        with open(REG) as f:
            return json.load(f)
    except Exception:
        return {}


def save(reg):
    os.makedirs(os.path.dirname(REG), exist_ok=True)
    tmp = REG + ".tmp"
    with open(tmp, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, REG)


def recompute(rec):
    pls = rec.get("payloads") or []
    rec["is_payload_customer"] = len(pls) > 0
    rec["payload_count"] = len(pls)
    rec["flights"] = sorted({p["flight_no"] for p in pls if p.get("flight_no")})   # mission numbers flown/booked
    rec["total_contract_value_usd"] = sum(float(p.get("contract_value_usd") or 0) for p in pls)
    rec["total_paid_usd"] = sum(float(p.get("amount_paid_usd") or 0) for p in pls)
    paid = sorted([p.get("paid_date") for p in pls if p.get("paid_date")])
    rec["customer_since"] = (paid[0] if paid else rec.get("customer_since")) or None
    rec["last_payload_date"] = (paid[-1] if paid else rec.get("last_payload_date")) or None
    return rec


def cmd_add(a):
    today = datetime.date.today().isoformat()
    reg = load()
    if not norm(a.company):
        sys.exit("ERROR: --company is required")
    key = find_key(reg, a.company)
    rec = reg.get(key) or {"company": a.company, "payloads": [], "created": today}
    rec["company"] = rec.get("company") or a.company
    payload = {
        "payload_name": a.payload_name,
        "mission": a.mission,
        "flight_no": (a.flight_no or "").upper() or None,   # mission number, e.g. M6 (Jon 2026-10-01)
        "flight_date": a.flight_date,
        "mass_kg": a.mass_kg,
        "contract_id": a.contract_id,
        "contract_value_usd": a.contract_value,
        "amount_paid_usd": a.amount_paid,
        "paid_date": a.paid_date or today,
        "signed_contract_ref": a.signed_contract,
        "signed_date": a.signed_date,
        "notes": a.notes,
        "logged": today,
        "logged_by": "Exo",
    }
    payload = {k: v for k, v in payload.items() if v is not None and v != ""}
    # Same mission (or same contract) already on file as an unpaid placeholder → fill it in, don't duplicate.
    slot = next((p for p in rec.get("payloads", []) if not float(p.get("amount_paid_usd") or 0) and (
        (payload.get("flight_no") and p.get("flight_no") == payload["flight_no"]) or
        (payload.get("contract_id") and p.get("contract_id") == payload["contract_id"]))), None)
    if slot is not None:
        slot.update(payload)
    else:
        rec.setdefault("payloads", []).append(payload)
    recompute(rec)
    rec["updated"] = today
    reg[key] = rec
    save(reg)
    print(f"✓ Logged payload for {rec['company']} — now a payload customer "
          f"({rec['payload_count']} payload(s), ${rec['total_paid_usd']:,.0f} paid / "
          f"${rec['total_contract_value_usd']:,.0f} contracted).")
    if not a.signed_contract:
        print("  ⚠ No --signed-contract reference captured. Add the signed contract for true metrics.")


def cmd_list(a):
    reg = load()
    recs = [r for r in reg.values() if r.get("is_payload_customer")]
    recs.sort(key=lambda r: r.get("customer_since") or "")
    tot_c = sum(r.get("total_contract_value_usd", 0) for r in recs)
    tot_p = sum(r.get("total_paid_usd", 0) for r in recs)
    tot_pl = sum(r.get("payload_count", 0) for r in recs)
    print(f"PAYLOAD CUSTOMERS: {len(recs)} | payloads: {tot_pl} | "
          f"repeat: {sum(1 for r in recs if r.get('payload_count',0)>1)} | "
          f"contracted ${tot_c:,.0f} | paid ${tot_p:,.0f}")
    for r in recs:
        signed = sum(1 for p in r.get("payloads", []) if p.get("signed_contract_ref"))
        print(f"  • {r['company']:32} since {(r.get('customer_since') or '?'):10} "
              f"{r.get('payload_count',0)} payload(s) {','.join(r.get('flights') or []) or '—':8} "
              f"${r.get('total_paid_usd',0):,.0f}/${r.get('total_contract_value_usd',0):,.0f}  "
              f"signed:{signed}/{r.get('payload_count',0)}")


def main():
    ap = argparse.ArgumentParser(description="Record paid payloads / flag payload customers.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = sub.add_parser("add", help="log a paid payload for a customer")
    add.add_argument("--company", required=True)
    add.add_argument("--payload-name", dest="payload_name")
    add.add_argument("--mission")
    add.add_argument("--flight-no", dest="flight_no", help="mission number, e.g. M5 / M6")
    add.add_argument("--flight-date", dest="flight_date")
    add.add_argument("--mass-kg", dest="mass_kg")
    add.add_argument("--contract-id", dest="contract_id")
    add.add_argument("--contract-value", dest="contract_value", type=float)
    add.add_argument("--amount-paid", dest="amount_paid", type=float)
    add.add_argument("--paid-date", dest="paid_date")
    add.add_argument("--signed-contract", dest="signed_contract",
                     help="path/ref to the SIGNED contract (data-room path or e-sign envelope id)")
    add.add_argument("--signed-date", dest="signed_date")
    add.add_argument("--notes")
    add.set_defaults(func=cmd_add)
    lst = sub.add_parser("list", help="print registry + customer metrics")
    lst.set_defaults(func=cmd_list)
    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
