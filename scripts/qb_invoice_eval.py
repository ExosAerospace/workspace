#!/usr/bin/env python3
"""
qb_invoice_eval.py — exo3 process eval for QB invoicing (qb_invoice.py).

Owner: Exo (finance automation). Replays the 2026-10-01 failure: invoice #0071 (Scentience, M6) went to
the approval card reading "Mission M6 (BLK3 S0 Pathfinder)". Jon: M5 is the Pathfinder, not M6, and
"we do not want pathfinder on any invoice".

Checks:
  REPLAY   — the old #0071 line text is caught by banned_terms()
  FLIGHT   — flight_text() for every mission in missions.json carries no banned term
  LABELS   — no mission label contains a banned term (labels flow to payload orders / LSA e-sign text)
  ORDERS   — no payload order `flight` text contains a banned term
  LIVE     — every pending/sent invoice in qb-invoices.json: stored line text carries no banned term
  GATE     — watch() re-checks QB's live line text before sending (source check)

Usage: python3 scripts/qb_invoice_eval.py   Exit 0 = all PASS; 1 = at least one FAIL.
"""
import json, os, sys

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import qb_invoice as m

D = os.path.join(WS, "mission-control/data")
fails = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        fails.append(name)


old = ("Scentience OPU (olfaction sensor + compute) — Mission M6 (BLK3 S0 Pathfinder) payload integration & flight. "
       "Milestone M1: slot reservation (50%) of $8,000 contract (payload order PO2C-2026-001).")
check("REPLAY", m.banned_terms(old) == ["pathfinder"])

missions = json.load(open(os.path.join(D, "missions.json")))["missions"]
bad = [x["id"] for x in missions if m.banned_terms(m.flight_text(x["id"], x))]
check("FLIGHT", not bad, f"missions {bad}")
bad = [x["id"] for x in missions if m.banned_terms(x.get("label"))]
check("LABELS", not bad, f"missions {bad}")

orders = json.load(open(os.path.join(D, "payload-orders.json"))).get("orders", [])
bad = [o["id"] for o in orders if m.banned_terms(o.get("flight"))]
check("ORDERS", not bad, f"orders {bad}")

inv = json.load(open(os.path.join(D, "qb-invoices.json"))).get("invoices", [])
bad = [r["doc_number"] for r in inv if r.get("status") in ("pending", "sent") and m.banned_terms(r.get("desc"))]
check("LIVE", not bad, f"invoices {bad}")

src = open(os.path.join(WS, "scripts/qb_invoice.py")).read()
check("GATE", "BLOCKED send of QB invoice" in src and src.index("BLOCKED send") < src.index('f"invoice/{r[\'qb_id\']}/send"'))

sys.exit(1 if fails else 0)
