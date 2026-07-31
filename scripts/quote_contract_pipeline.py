#!/usr/bin/env python3
"""
PROG-002 — AI Mission Desk: Quote & Contract pipeline.
For a qualified payload opportunity, this auto-drafts (1) the mission scope + a priced quote
from the published rate card, (2) a contract/term-sheet draft (from the BLK3 bailment & operating
lease template) plus the FAA authorization note, and (3) routes the whole package into the
Decisions matrix for Jon's one-click approval. Human touch = relationship + signature only.

Pricing/contract are DRAFTS for review — the Decision gates before anything is sent, and the
contract/FAA package is template-based (counsel confirms before execution).

Run:  python3 scripts/quote_contract_pipeline.py --customer "Acme" --kg 25 --altitude 90 \
          --mission "microgravity materials test" [--post]
"""
import os, sys, json, argparse, datetime, urllib.request

WS = os.path.expanduser("~/.openclaw/workspace")
RATE = os.path.join(WS, "pricing", "rate-card.json")
DECISIONS_API = "http://localhost:8080/api/decisions/ingest"
CONTRACT_TEMPLATE = "Attachment_B_BLK3_Bailment_and_Operating_Lease_TermSheet.docx"
# During the PROG-002 test phase the drafted package routes to Phil to check the work and
# update the documents — NOT to Jon's decision box. Change this to hand review to someone else.
REVIEWER_EMAIL = "peaton@exosaero.com"
REVIEWER_NAME = "Phil Eaton"


def _token():
    try:
        return open(os.path.join(WS, "mission-control", "data", ".decisions-token")).read().strip()
    except Exception:
        return "33bad1599d6fdc99af6c10026cdab10c46c5a7bbcbbff18b"  # fallback (matches decisions crons)


def quote(kg):
    rc = json.load(open(RATE))
    per_kg = rc["custom"]["mass_based"]["price_per_kg"]
    # Small payloads (<=6 kg) fit the cubesat/BRIC rate card — far cheaper than a Quarter bay.
    if kg <= 6:
        cs = sorted(rc["cubesat_bric_tiers"], key=lambda t: (t["max_kg"], t["price"]))
        fit = next((t for t in cs if kg <= t["max_kg"]), None)
        if fit:
            return {"tier": f"CubeSat/BRIC {fit['name']}", "price": fit["price"], "per_kg_price": kg * per_kg,
                    "note": f"Published {fit['name']} cubesat rate; standard fractional bay available if more volume is needed."}
    tiers = sorted(rc["standard_payload_tiers"], key=lambda t: t["max_kg"])
    fit = next((t for t in tiers if kg <= t["max_kg"]), None)
    if not fit:
        return {"tier": "Exceeds single-flight capacity (>135 kg)", "price": None, "per_kg_price": kg * per_kg,
                "note": "Payload exceeds the 135 kg full bay — scope as multi-flight or custom."}
    return {"tier": fit["name"], "price": fit["price"], "per_kg_price": kg * per_kg,
            "note": f"Published {fit['name']} rate; custom per-kg alternative ${kg*per_kg:,.0f} (${per_kg:,}/kg)."}


def build_package(customer, kg, altitude, mission, q):
    price_line = f"${q['price']:,.0f}" if q["price"] else "custom (see note)"
    md = f"""# BLK3 Mission Scope, Quote & Contract Package — {customer}

**Prepared:** {datetime.date.today():%B %d, %Y}  ·  **Vehicle:** Exos BLK3 PSRLV (reusable, FAA-licensed suborbital)  ·  **DRAFT for approval**

## 1. Mission Scope
- **Customer:** {customer}
- **Payload:** {kg} kg — {mission}
- **Target apogee:** ~{altitude} km (suborbital)
- **Service:** flight, recovery, and payload return; 2–3 day turnaround; recover-and-refly capable.
- **Assumptions:** standard integration; no ITAR/CUI technical data exchanged outside the export-control process.

## 2. Quote (from published rate card)
- **Tier:** {q['tier']}
- **Price:** {price_line}
- {q['note']}
- Not a final price; discounts apply for payloads over 20 kg and multi-flight commitments.

## 3. Contract / Term Sheet
- Basis: **BLK3 Bailment & Operating Lease Term Sheet** ({CONTRACT_TEMPLATE}) — to be tailored to this customer and payload.
- Key terms to confirm: payment schedule, integration milestones, recovery/return, reciprocal waiver of claims, IP/data rights.

## 4. FAA / Authorization Note
- Flight under Exos's active FAA authorization from Spaceport America, NM. Confirm mission profile within licensed envelope; reciprocal waiver of claims per 14 CFR 440; no new exemption required for standard payloads.

## 5. Next step
On approval, Exo delivers the tailored quote + term sheet to your inbox to send; you own the relationship and signature.
"""
    out = os.path.join(WS, "drafts", f"Quote_Package_{customer.replace(' ','_')}.md")
    open(out, "w").write(md)
    return out, price_line


def post_decision(customer, kg, price_line, pkg_path):
    body = {"source": "AI Mission Desk (PROG-002)",
            "title": f"Review drafted quote + package for {customer} ({kg} kg, {price_line})",
            "question": f"Does the auto-drafted BLK3 mission scope, quote ({price_line}), and contract/FAA package for {customer} look right?",
            "context": f"Auto-drafted by the Quote & Contract pipeline. Package: {os.path.basename(pkg_path)}. {REVIEWER_NAME}: check the numbers/scope, correct the term sheet + FAA note, and update the documents as needed.",
            "proposedAction": f"{REVIEWER_NAME} reviews and updates the drafted documents. On 'Looks good', it advances to Jon for the go-live call. On 'Needs work', note what to fix.",
            "type": "choice", "options": ["Looks good", "Needs work"], "priority": "high",
            "assignedTo": REVIEWER_EMAIL, "approver": REVIEWER_NAME,
            "dedupeKey": f"quote-{customer.lower().replace(' ','-')}"}
    req = urllib.request.Request(DECISIONS_API, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Exo-Token": _token()})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--customer", required=True); ap.add_argument("--kg", type=float, required=True)
    ap.add_argument("--altitude", type=float, default=90); ap.add_argument("--mission", default="suborbital payload flight")
    ap.add_argument("--post", action="store_true")
    a = ap.parse_args()
    q = quote(a.kg)
    pkg, price_line = build_package(a.customer, a.kg, a.altitude, a.mission, q)
    print(f"Quote: {a.customer} · {a.kg} kg · {q['tier']} · {price_line}")
    print(f"Package: {pkg}")
    if a.post:
        print("Decision posted (status", post_decision(a.customer, a.kg, price_line, pkg), f") — routed to {REVIEWER_NAME} for review")
    else:
        print("(dry-run — add --post to route into Decisions for approval)")


if __name__ == "__main__":
    main()
