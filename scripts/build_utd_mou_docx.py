#!/usr/bin/env python3
"""Build the UTD x Exos Capstone MOU on the PRIMARY letterhead.
Run: PYTHONNOUSERSITE=1 python3.12 scripts/build_utd_mou_docx.py"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

LH = "assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT = "drafts/UTD_Exos_Capstone_MOU.docx"
NAVY = RGBColor(0x0A, 0x3D, 0x7C); DARK = RGBColor(0x1A, 0x1A, 0x1A)
doc = Document(LH)

def run(p, t, size=11, bold=False, color=DARK, italic=False):
    r = p.add_run(t); r.font.name = "Calibri"; r.font.size = Pt(size)
    r.bold = bold; r.italic = italic; r.font.color.rgb = color; return r

def title(t, size=15):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(1); run(p, t, size, True, NAVY); return p
def sub(t):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(8); run(p, t, 12, True, DARK); return p
def h(t):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(9); p.paragraph_format.space_after = Pt(2); run(p, t, 12, True, NAVY); return p
def body(segs, after=6):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(after)
    for s, b in segs: run(p, s, 11, b, DARK)
    return p
def bullet(segs):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.28); p.paragraph_format.space_after = Pt(2)
    run(p, "•  ", 11, False, DARK)
    for s, b in (segs if isinstance(segs, list) else [(segs, False)]): run(p, s, 11, b, DARK)
    return p

title("Memorandum of Understanding")
sub("Exos × UT Dallas — “EXO3 Payload Capstone” (Fall 2026)")
body([("Parties: ", True), ("Exos Aerospace Systems & Technologies, Inc. (“Exos”) and The University of Texas at Dallas (“UTD”).", False)], after=1)
body([("Exos lead: ", True), ("Lizi Quinn (relationship owner + public-content approver); John Quinn, Cofounder & CEO (sponsor, supportive).", False)], after=1)
body([("UTD lead: ", True), ("Edwin Van Der Vlist (capstone program administrator).", False)], after=1)
body([("Status: ", True), ("DRAFT for review — route to counsel before signature.", False)], after=8)

h("1. Purpose")
body([("UTD provides a Fall 2026 marketing capstone team to act as Exos’s agency of record, marketing and filling the open ~135 kg on the BLK3 Flight 2 payload bay (early 2027, Spaceport America, NM; launch est. April 2027) under the SPACEavailable…™ campaign, directing Exos’s EXO3 AI agent fleet. Students are graded on real payload outcomes, not effort.", False)])

h("2. Roles")
bullet([("Lizi Quinn (Exos) ", True), ("— owns the UTD relationship and is the approval gate for anything that goes public (media, website, outreach naming Exos).", False)])
bullet([("John Quinn (Exos) ", True), ("— sponsor; supportive; engaged only for critical-impact decisions.", False)])
bullet([("Exo (EXO3 agent) ", True), ("— the operating engine; gates student design/build requests, generates code/creative in an isolated sandbox, and runs the scorecard.", False)])
bullet([("Edwin Van Der Vlist (UTD) ", True), ("— program administrator; uploads the roster; parallel rights with Jon + Lizi to see/manage student accounts; joint determiner (with Exos) of material contribution.", False)])

h("3. Student access & security")
bullet([("Each student receives a scoped Mission Control login limited to the “Payload Sales” board + the progress tracker. No access to Exos CRM, financials, decisions, documents, or internal systems.", False)])
bullet([("Access is monitored: any attempt to exceed scope is logged and alerts Exos + Lizi.", False)])
bullet([("Restricted from students: Narravity and Napier Park (walled off).", False)])
bullet([("Design-request loop: students request builds; Exo generates in an isolated capstone sandbox (never Exos production); changes are reviewed and reversible; nothing executes on Exos systems.", False)])

h("4. Timeline (15 weeks; Edwin sets the start date)")
bullet([("Weeks 1–2: ", True), ("onboard, team sets its own space-themed name, lock the 10× baseline, define ICP/segments; Exos site visit (Greenville, TX, 3–4 hrs — Jon/Lizi + BD team address the team + facility tour). Every student is handed a company Divvy card to hold through to the launch.", False)])
bullet([("Week 3: ", True), ("Challenge kickoff — AI-only vs Hybrid both live.", False)])
bullet([("Weeks 4–15: ", True), ("campaign build, outreach at scale, weekly pipeline gates, handoffs, 100 kg push, final presentation + playbook + Payload Sales Engineer selections. A live weekly-gate tracker shows progress to the team and Edwin.", False)])

h("5. The Challenge")
body([("A controlled A/B on matched prospect cohorts: AI-only (fleet autonomous) vs Hybrid (students directing the fleet), same tools and approval gate, metrics pre-registered. It tests whether human-directed AI beats autonomous AI on real revenue.", False)])

h("6. Grading & metrics (weekly, real dollars)")
bullet([("Team outcomes: ", True), ("qualified pipeline $, high-prob opportunities vs the 10× target, kg advanced/booked, funnel conversion; plus AI-effectiveness (leverage, reply rate, attribution, cost/opportunity).", False)])
bullet([("Individual score (role-fair, /100): ", True), ("primary-track impact 35, contribution-to-team-outcome 20, AI-leverage 15, consistency 15, instructor+peer assessment 15. Four equal tracks — Growth/Outreach, Web & Pipeline Engineering, Creative/Content, Data/Analytics & Ops — each scored in its own currency. Specializing to the website/pipeline build (or creative, or analytics) is a full, unpenalized path.", False)])

h("7. Individual accountability")
body([("It is a team effort, but each person must materially contribute to earn rewards. Material contribution = individual score ≥ 60 in their track and affirmed by both Edwin and Exos.", False)])

h("8. Reward ladder (two rungs; both gated per person)")
bullet([("75 kg booked → 1U payload reward ", True), ("($8,000 value; contents ≤ 1 kg): eligible members place a small item and decide its use — engraved dog tags/names, or flown-item/sticker sales for a university-approved team activity (their fundraiser, not Exos revenue), or both. All items flight-safe per the Payload User’s Guide, export-safe.", False)])
bullet([("100 kg booked → launch trip ", True), ("(BLK3 launch, Spaceport America, est. April 2027): eligible members travel. Exos provides a 15-passenger van, ~4-day trip, group lodging (men/women separate), and a Divvy virtual-card food budget (actual receipted expenses up to $55/person/day, food-only merchant controls, receipts submitted in the Divvy app). Cards are issued at the kickoff and held to the launch; they activate only once the launch window is set and the student is booked.", False)])
bullet([("Perfectly clear: ", True), ("anyone who does not materially participate goes on no trip and places nothing in the 1U.", False)])

h("9. Total Exos contribution")
body([("Approximately $16,100 in direct rewards for a successful project ($8,000 1U spaceflight + ~$8,100 launch trip), plus substantial in-kind value (EXO3 platform + agent-fleet access, Exo’s build time, brand assets/media, CEO + BD team time) and a contracted Payload Sales Engineer pathway for top performers.", False)])

h("10. Payload Sales Engineer track")
body([("Top performers may earn a contracted Payload Sales Engineer position. Compensation = commission on the customer payload bookings they source, via Exos’s commission system — not tied to any capital raise. A hired student receives attribution credit carried forward for capstone-sourced opportunities, but commissions are payable only on future sales that close beyond the capstone.", False)])

h("11. Intellectual property")
body([("Exos owns all capstone deliverables (site, copy, campaign assets, pipeline). UTD confirms its capstone terms do not conflict.", False)])

h("12. Media")
body([("UTD is responsible for local and national media and audience-building around the “AI challenged by UTD” story. Any media naming Exos or its capabilities passes Exos (Lizi) review first — positioning rules apply (flying since 2018; one of only three FAA-licensed reusable rocket launch providers in the U.S.; never “first commercial flight”; no overstatement; export-safe).", False)])

h("13. Sources & attribution")
body([("Primary source: the Exos BLK3 Payload User’s Guide. Context: historical Exos + Armadillo Aerospace video. Any material used from Armadillo Aerospace must credit “Armadillo Aerospace” (Exos is Armadillo’s commercial successor).", False)])

h("14. Compliance")
bullet([("Student data / FERPA: ", True), ("minimal collection; Edwin uploads from the UTD side.", False)])
bullet([("Export diligence: ", True), ("the roster captures US-citizen / non-US status as a documentation step, not a disqualifier — the student scope is public/commercial marketing data only (no ITAR/CUI); non-US students participate fully.", False)])
bullet([("Securities: ", True), ("any public investor/offering language is counsel-gated, must fit the applicable Reg D exemption’s solicitation rules, and is authored by Exos + counsel only — never by students.", False)])
bullet([("Hosting: ", True), ("the SPACEavailable microsite is served at spaceavailable.exosaero.com (static, reviewed-before-deploy).", False)])

h("15. Term & signatures")
body([("Effective on signature; runs the Fall 2026 semester. Either party may terminate for cause with written notice; student data handled per FERPA on termination.", False)], after=14)

sg = doc.add_paragraph(); run(sg, "Exos Aerospace Systems & Technologies, Inc.", 11, True, DARK)
p = doc.add_paragraph(); run(p, "By: ____________________________   Name: John Quinn   Title: Cofounder & CEO   Date: __________", 11)
doc.add_paragraph()
p = doc.add_paragraph(); run(p, "The University of Texas at Dallas", 11, True, DARK)
p = doc.add_paragraph(); run(p, "By: ____________________________   Name: ____________________   Title: __________   Date: __________", 11)
p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10)
run(p, "DRAFT — route to counsel (compensation, IP, student data, media, launch-site liability) before signature.", 9.5, False, DARK, italic=True)

doc.save(OUT); print("saved", OUT)
