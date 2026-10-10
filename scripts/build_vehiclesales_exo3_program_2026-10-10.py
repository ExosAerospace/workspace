#!/usr/bin/env python3
"""Builds the BLK3 Vehicle Sales-exo3 research program + agent spec (Jon 2026-10-10).
Usage: /usr/bin/python3 scripts/build_vehiclesales_exo3_program_2026-10-10.py [targets_json]
targets_json (optional): list of {company,country,status,funding,why,fit,source}
"""
import json, sys
from docx import Document
from docx.shared import Pt

OUT = "drafts/Exos_BLK3_VehicleSales_exo3_Program_2026-10-10.docx"
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

d.add_heading("BLK3 Vehicle Sales-exo3: Research Program & Agent Design", 0)
P("Exos Aerospace Systems & Technologies, Inc. · Internal · Draft for CEO review · 2026-10-10 · Prepared by Exo for John Quinn, Cofounder & CEO")

H("1. The thesis")
P("Many launch startups have raised private capital and government awards to build a rocket but have not delivered a flying vehicle. "
  "Their investors and government customers need flight milestones. Exos can deliver both halves: a reusable rocket (BLK3) and a market "
  "(Exos's payload customer pipeline and flight operations). The offer is \"Vehicle + Market\": they get to flight years sooner on a licensed "
  "reusable platform; Exos gets vehicle revenue, fleet scale and new flight cadence that fills its own payload demand.")
P("What we can honestly say today: BLK3 is FAA-licensed (14 CFR §431, renewed March 13, 2026) and ground-tested, has not yet flown, and its first "
  "flight campaign is planned for early 2027. Its predecessor SARGE flew four times (2018–19). Public reference price: ~$5M vehicle, "
  "$1M per flight ($7,500/kg × 135 kg). BLK3 has fewer than 5,000 components (BLK3 BOM, 8/21/2026). Every sale is gated on BLK3's "
  "own flights: we sell delivery after demonstrated flight, never a flown record we don't have.")

H("2. Offer structures to test")
table(["Structure", "What the buyer gets", "Why it works", "Main risk"], [
    ["A. Vehicle sale (US buyers)", "A BLK3 built to order, training, spares", "Fastest path to their own flights", "Buyer becomes a competitor; FAA license is theirs to obtain"],
    ["B. White-label / co-brand", "BLK3 flown in their livery under Exos's license and ops", "Milestone for their investors without a license gap", "Brand/IP terms; flight ops capacity"],
    ["C. Wet lease (dedicated tail)", "Exos-owned, Exos-operated BLK3 dedicated to their program", "No hardware export; mirrors the NCE wet-lease model", "Capital tied up in fleet"],
    ["D. Licensed build (Consortium)", "Rights to build BLK3 in their plant under Exos IP", "Uses their facility + funding; royalties to Exos", "IP protection, quality control"],
    ["E. Acquire / roll-up", "Exos acquires a stalled startup's team, awards and plant", "Fits the roll-up capital path (license the line you want, ~$5M)", "Liabilities; needs acquisition currency"],
])
P("Foreign buyers: default to Structure C (wet lease, Exos keeps custody and flight ops), as in the NCE program, because a complete rocket "
  "system export faces ITAR/MTCR presumption-of-denial. Every foreign lead goes through export review before any technical exchange.")

H("3. Research program (workstreams)")
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

H("4. The agent: VehicleSales-exo3")
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
    ["Cadence", "Weekly full sweep (Mon) + daily signal scan (news / SAM.gov / award changes)"],
    ["Rollback", "Disable launchd job; CRM records tagged so they can be bulk-removed"],
]
table(["Property", "Specification"], spec)
P("Guardrails baked into the agent prompt: BLK3 not yet flown (early 2027); no free flights; no claims without a source; no ROFR; "
  "Exos is not a propulsion provider; foreign targets default to wet lease and are flagged for export review.")

H("5. 30 / 60 / 90 days")
B("Days 1–30: W1 market map complete and loaded into CRM; W4 export/FAA rules drafted with counsel and the export reviewer (Denise Shirey); agent runs in shadow mode (reports only).")
B("Days 31–60: W2 value cases for the top 10; W3 term-sheet templates for A–C; first 5 outreach Decisions to Jon.")
B("Days 61–90: first discovery calls; W5 build-slot schedule tied to BLK3's early-2027 flights; go/no-go on Structure D/E with the roll-up path.")
P("Success metrics: 10 qualified conversations, 3 term-sheet discussions, 1 signed LOI contingent on BLK3 flight by end of Q1 2027.")

if targets:
    H("6. First target list (from today's research)")
    table(["Company", "Country", "Status", "Funding", "Why BLK3 helps", "Fit", "Source"],
          [[t.get(k, "") for k in ("company", "country", "status", "funding", "why", "fit", "source")] for t in targets])

H("7. Decisions for Jon")
B("Approve the research program and the five offer structures to test (or strike some).")
B("Approve VehicleSales-exo3 to run in shadow mode (research + drafts only) with you as owner.")
B("Foreign targets: in scope via wet lease only, or US-only for now?")
B("Who owns the conversations once a target is qualified: you, or a named BD lead?")

d.save(OUT); print(OUT)
