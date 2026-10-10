#!/usr/bin/env python3
"""Builds the BLK3 Vehicle Sales-exo3 research program + agent spec (Jon 2026-10-10).
Usage: /usr/bin/python3 scripts/build_vehiclesales_exo3_program_2026-10-10.py [targets_json]
targets_json (optional): list of {company,country,status,funding,why,fit,source}
"""
import json, sys
from docx import Document
from docx.shared import Pt

OUT = "drafts/Exos_BLK3_VehicleSales_exo3_Program_v2_2026-10-10.docx"
targets = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else []

d = Document()
st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
H = lambda t, l=1: d.add_heading(t, level=l)
P = lambda t: d.add_paragraph(t)
B = lambda t: d.add_paragraph(t, style="List Bullet")

def table(head, rows):
    t = d.add_table(rows=1, cols=len(head)); t.style = "Light Grid Accent 1"
    for i, h in enumerate(head): t.rows[0].cells[i].text = h
    for r in rows:
        c = t.add_row().cells
        for i, v in enumerate(r): c[i].text = str(v)
    return t

d.add_heading("BLK3 Vehicle Sales-exo3: Research Program & Agent Design (v2)", 0)
P("Exos Aerospace Systems & Technologies, Inc. · Internal · Draft for CEO review · 2026-10-10 · Prepared by Exo for John Quinn, Cofounder & CEO · v2 adds the recovery-system scope, a 14-day launch plan, daily outreach cadence, 50 targets with due diligence and contacts, per-company pitch decks, and the MTP / Ainigma story tie-in (Jon, 10/10)")

H("1. The thesis")
P("Many launch startups have raised private capital and government awards to build a rocket but have not delivered a flying vehicle. "
  "Their investors and government customers need flight milestones. Exos can deliver both halves: a reusable rocket (BLK3) and a market "
  "(Exos's payload customer pipeline and flight operations). The offer is \"Vehicle + Market\": they get to flight years sooner on a licensed "
  "reusable platform; Exos gets vehicle revenue, fleet scale and new flight cadence that fills its own payload demand.")
P("What we can honestly say today: BLK3 is FAA-licensed (14 CFR §431, renewed March 13, 2026) and ground-tested, has not yet flown, and its first "
  "flight campaign is planned for early 2027. Its predecessor SARGE flew four times (2018–19). Public reference price: ~$5M vehicle, "
  "$1M per flight ($7,500/kg × 135 kg). BLK3 has fewer than 5,000 components (BLK3 BOM, 8/21/2026). Every sale is gated on BLK3's "
  "own flights: we sell delivery after demonstrated flight, never a flown record we don't have.")

H("2. Two scopes, one relationship")
P("Scope 1, VEHICLE: sell, white-label, lease or license BLK3 plus access to Exos's payload market, for companies that raised money for a rocket and haven't flown. "
  "Scope 2, RECOVERY: Exos's recovery system for every orbital launch company building a vehicle today. There is no reason to lose a vehicle on your first three or four "
  "tests before you have proven you can reach orbit. Recovering test articles preserves hardware, data and schedule, and it is the low-friction entry into a relationship "
  "that can grow into BLK3 test flights and vehicle purchases. Recovery is pitched at capability level (drogue/ballute plus guided parafoil with GPS tracking, developed for "
  "Exos's reusable SARGE/BLK3 vehicles); integration on another company's vehicle starts with a paid integration study. Confirm with Jon which recovery elements are flight-proven before any external claim.")
H("3. Offer structures to test")
table(["Structure", "What the buyer gets", "Why it works", "Main risk"], [
    ["A. Vehicle sale (US buyers)", "A BLK3 built to order, training, spares", "Fastest path to their own flights", "Buyer becomes a competitor; FAA license is theirs to obtain"],
    ["B. White-label / co-brand", "BLK3 flown in their livery under Exos's license and ops", "Milestone for their investors without a license gap", "Brand/IP terms; flight ops capacity"],
    ["C. Wet lease (dedicated tail)", "Exos-owned, Exos-operated BLK3 dedicated to their program", "No hardware export; mirrors the NCE wet-lease model", "Capital tied up in fleet"],
    ["D. Licensed build (Consortium)", "Rights to build BLK3 in their plant under Exos IP", "Uses their facility + funding; royalties to Exos", "IP protection, quality control"],
    ["E. Acquire / roll-up", "Exos acquires a stalled startup's team, awards and plant", "Fits the roll-up capital path (license the line you want, ~$5M)", "Liabilities; needs acquisition currency"],
])
P("Foreign buyers: default to Structure C (wet lease, Exos keeps custody and flight ops), as in the NCE program, because a complete rocket "
  "system export faces ITAR/MTCR presumption-of-denial. Every foreign lead goes through export review before any technical exchange.")

H("4. Research program (workstreams)")
ws = [
    ("W1 Market map", "Who raised money for a launch vehicle and hasn't flown? Funding, gov awards, slip history, people.",
     "Company releases, SEC Form D, SBIR.gov/USAspending, SAM.gov, SpaceNews/Payload/TechCrunch (2023+)", "Scored target list (fit 1–5) in CRM, tag vehicle-sales-target"),
    ("W2 Buyer economics", "What does each target owe its investors/government by when? What does a BLK3 buy them in months and dollars vs. their own program?",
     "Award milestones (USAspending), investor updates, public roadmaps", "Per-target value case"),
    ("W3 Offer & pricing", "Price and terms for A–E; support, spares, training; data/IP rights; exclusivity.",
     "Exos cost basis (internal only), comparable deals, counsel", "Term sheet templates per structure"),
    ("W4 Regulatory & export", "FAA license path when a vehicle changes hands; ITAR Cat IV / MTCR category for BLK3; CFIUS for foreign capital in buyers.",
     "eCFR (14 CFR 450, 22 CFR 121), DDTC guidance, counsel, export review by the Empowered Official (John Quinn) with ITAR reviewer Denise Shirey", "Go/no-go rules per buyer type and country"),
    ("W5 Capacity & supply", "How many BLK3s can Exos build per year? Lead time, BOM (<5,000 components), Consortium suppliers, MRP.",
     "MC MRP/BOM, Suppliers & POs module", "Build-slot schedule + price floor"),
    ("W6 Channels & signals", "Who influences the buyer: lead investors, gov PMs, primes. What signals intent (missed milestones, layoffs, test-flight RFIs)?",
     "News, job posts, SAM.gov RFIs, investor portfolios", "Warm-path map per target"),
    ("W7 Competitive response", "Who else could offer a vehicle or test flights (e.g. suborbital/hypersonic test providers)? How do we position?",
     "Public announcements, contract awards", "Positioning one-pager"),
]
table(["Workstream", "Key questions", "Sources", "Output"], ws)

H("5. The agent: VehicleSales-exo3")
P("A SENSE + INTERPRET agent. It finds and scores targets and prepares the outreach; it never sends, prices or commits. "
  "Every outreach, price or term goes to Jon as a Decision card.")
spec = [
    ["Purpose / MTP", "Find funded-but-unflown launch companies and prepare BLK3 \"Vehicle + Market\" outreach; serves MTP \"Make Every Space Vehicle Reusable\""],
    ["Stack layer", "SENSE + INTERPRET (DECIDE stays with Jon)"],
    ["Autonomy tier", "Recommend-only: writes CRM/MC records and drafts; no external send"],
    ["Human owner", "John Quinn (proposed; also Empowered Official for the export gate, with ITAR reviewer Denise Shirey)"],
    ["Permission envelope", "Read web + gov databases; write CRM contacts/opps (tag vehicle-sales-target) and MC task notes; drafts only to Jon's inbox; NO external email"],
    ["Memory boundary", "Workspace + CRM (Supabase) + MC; no CUI, no export-controlled technical data in drafts"],
    ["Escalation", "Decision card per outreach (\"Contact <company> about Structure X?\"); export flag → Empowered Official (John Quinn) / Denise Shirey"],
    ["Eval suite (output, not liveness)", "100% of claims in a target record carry a source URL; ≤10% of surfaced targets rejected by Jon as wrong-fit (rolling 30 days); no duplicate company records; weekly run completes"],
    ["Telemetry", "fleet_log correlation IDs → logs/fleet-events.jsonl; decision traces → logs/decision-traces.jsonl; log logs/vehiclesales-exo3.log"],
    ["Cadence", "Daily: prepare the next company's touch (dossier refresh + email draft + pitch deck) as a Decision card for Jon, one company per day until the full list is covered; daily signal scan (news / SAM.gov / award changes) re-ranks the queue; weekly re-check of funds availability"],
    ["Rollback", "Disable launchd job; CRM records tagged so they can be bulk-removed"],
]
table(["Property", "Specification"], spec)
P("Guardrails baked into the agent prompt: BLK3 not yet flown (early 2027); no free flights; no claims without a source; no ROFR; "
  "Exos is not a propulsion provider; foreign targets default to wet lease and are flagged for export review.")

H("6. 14-day launch plan (credible targets by day 14 at the latest)")
table(["Days", "Deliverable"], [
    ["1–3 (Oct 10–13)", "50 targets: 35 deepened + ~20 recovery-scope orbital developers; full due diligence, funds-availability check and decision-maker contacts for each; loaded to CRM as high priority"],
    ["3–5", "Per-company PowerPoint pitch generator live; first 5 decks built and reviewed; MTP and Ainigma-story slides locked"],
    ["5–7", "Export screen on every foreign target (Empowered Official John Quinn with ITAR reviewer Denise Shirey); jurisdiction-ruling (CJ) request scoped for BLK3; FAA license-path note"],
    ["7–10", "Offer one-pagers for Scope 1 (sale / white-label / wet lease) and Scope 2 (recovery integration study); pricing ranges for Jon's approval"],
    ["10–14", "Daily outreach starts: one company per day, priority A first, each as a ready-to-send Decision card (email + deck + dossier)"],
])
P("Outreach cadence: one company touched per day until all 50 are covered (about 10 weeks), then nurture follow-ups. Each touch is drafted by the agent and sent only after Jon approves the Decision card.")
P("Success metrics (first 90 days of outreach): 50/50 touched; 15 discovery calls; 5 recovery integration studies or LOIs; 1 vehicle LOI contingent on BLK3's early-2027 flights.")

H("7. MTP and Ainigma story")
B("MTP \"Make Every Space Vehicle Reusable\": the recovery scope is the MTP in its simplest form, applied to other people's rockets. Every pitch deck carries an MTP slide.")
B("Ainigma / RTO story: the program shows a repeatable commercial engine beyond Exos's own flights (recovery systems, vehicle sales, white-label flights) across a sourced pipeline of 50 funded launch developers. It also surfaces distressed developers as roll-up candidates for the stock-currency acquisition path. Counts and stages from this pipeline feed the RTO narrative only once they are real (Decision-approved touches, calls, LOIs).")

H("8. Priority in CRM and Mission Control")
P("Jon's direction: these contacts carry the highest value per contact with nurturing. Every target is loaded to the CRM with tag vehicle-sales-target, scope tag (vehicle / recovery / both), priority A/B/C from fit and funds availability, and is_high_priority = true for A and B. Mission Control's MC task #3684 tracks the program; the outreach queue is ordered A → B → C, and within a tier by funds availability (strong first), so money is there to buy.")

if targets:
    H("9. Target list")
    cols = ("company", "country", "scope", "vehicle_and_status", "funds_availability", "decision_maker", "priority")
    table(["Company", "Country", "Scope", "Vehicle / status", "Funds", "Decision maker", "Pri"],
          [[str(t.get(k, ""))[:180] for k in cols] for t in targets])

H("10. Decisions for Jon")
B("Approve the research program and the five offer structures to test (or strike some).")
B("Approve VehicleSales-exo3 to run in shadow mode (research + drafts only) with you as owner.")
B("Foreign targets: in scope via wet lease only, or US-only for now?")
B("Who owns the conversations once a target is qualified: you, or a named BD lead?")
B("Confirm which recovery-system elements are flight-proven (for the recovery pitch claims).")

d.save(OUT); print(OUT)
