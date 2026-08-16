#!/usr/bin/env python3
"""Letterhead-matched PDF twin of the UTD x Exos Capstone MOU. Run: python3 scripts/build_utd_mou_pdf.py"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, ListFlowable, ListItem, Spacer
from reportlab.lib.enums import TA_LEFT

HDR = "/tmp/lh_media/word/media/image1.png"; FTR = "/tmp/lh_media/word/media/image2.png"
OUT = "drafts/UTD_Exos_Capstone_MOU.pdf"
PW, PH = letter
NAVY = HexColor("#0A3D7C"); DARK = HexColor("#1A1A1A")
hdr_h = PW * 542/2625; ftr_h = PW * 431/2625

def banners(c, d):
    c.drawImage(HDR, 0, PH - hdr_h, width=PW, height=hdr_h, mask='auto')
    c.drawImage(FTR, 0, 0, width=PW, height=ftr_h, mask='auto')

title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, spaceAfter=1, leading=18)
sub = ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=12, textColor=DARK, spaceAfter=9, leading=15)
h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=12, textColor=NAVY, spaceBefore=9, spaceAfter=2, leading=15)
body = ParagraphStyle("b", fontName="Helvetica", fontSize=10.5, textColor=DARK, spaceAfter=6, leading=14.5, alignment=TA_LEFT)
meta = ParagraphStyle("m", parent=body, spaceAfter=1)
note = ParagraphStyle("n", parent=body, fontName="Helvetica-Oblique", fontSize=9.5, spaceBefore=10)
bul = ParagraphStyle("bul", parent=body, leftIndent=12, spaceAfter=2)

def B(t): return Paragraph(t, body)
def L(items): return ListFlowable([ListItem(Paragraph(t, bul), value="•") for t in items], bulletType="bullet", start="•", leftIndent=10)

s = []
s += [Paragraph("Memorandum of Understanding", title),
      Paragraph("Exos &times; UT Dallas — “EXO3 Payload Capstone” (Fall 2026)", sub),
      Paragraph("<b>Parties:</b> Exos Aerospace Systems &amp; Technologies, Inc. (“Exos”) and The University of Texas at Dallas (“UTD”).", meta),
      Paragraph("<b>Exos lead:</b> Lizi Quinn (relationship owner + public-content approver); John Quinn, Cofounder &amp; CEO (sponsor, supportive).", meta),
      Paragraph("<b>UTD lead:</b> Edwin Van Der Vlist (capstone program administrator).", meta),
      Paragraph("<b>Status:</b> DRAFT for review — route to counsel before signature.", body)]

s += [Paragraph("1. Purpose", h),
      B("UTD provides a Fall 2026 marketing capstone team to act as Exos’s agency of record, marketing and filling the open ~135 kg on the BLK3 Flight 2 payload bay (early 2027, Spaceport America, NM; launch est. April 2027) under the SPACEavailable…™ campaign, directing Exos’s EXO3 AI agent fleet. Students are graded on real payload outcomes, not effort.")]
s += [Paragraph("2. Roles", h),
      L(["<b>Lizi Quinn (Exos)</b> — owns the UTD relationship and is the approval gate for anything that goes public (media, website, outreach naming Exos).",
         "<b>John Quinn (Exos)</b> — sponsor; supportive; engaged only for critical-impact decisions.",
         "<b>Exo (EXO3 agent)</b> — the operating engine; gates student design/build requests, generates code/creative in an isolated sandbox, and runs the scorecard.",
         "<b>Edwin Van Der Vlist (UTD)</b> — program administrator; uploads the roster; parallel rights with Jon + Lizi to see/manage student accounts; joint determiner (with Exos) of material contribution."])]
s += [Paragraph("3. Student access &amp; security", h),
      L(["Each student receives a scoped Mission Control login limited to the “Payload Sales” board + the progress tracker. No access to Exos CRM, financials, decisions, documents, or internal systems.",
         "Access is monitored: any attempt to exceed scope is logged and alerts Exos + Lizi.",
         "Restricted from students: Narravity and Napier Park (walled off).",
         "Design-request loop: students request builds; Exo generates in an isolated capstone sandbox (never Exos production); changes are reviewed and reversible; nothing executes on Exos systems."])]
s += [Paragraph("4. Timeline (15 weeks; Edwin sets the start date)", h),
      L(["<b>Weeks 1–2:</b> onboard, team sets its own space-themed name, lock the 10× baseline, define ICP/segments; Exos site visit (Greenville, TX, 3–4 hrs). Every student is handed a company Divvy card to hold through to the launch.",
         "<b>Week 3:</b> Challenge kickoff — AI-only vs Hybrid both live.",
         "<b>Weeks 4–15:</b> campaign build, outreach at scale, weekly pipeline gates, handoffs, 100 kg push, final presentation + playbook + Payload Sales Engineer selections. A live weekly-gate tracker shows progress to the team and Edwin."])]
s += [Paragraph("5. The Challenge", h),
      B("A controlled A/B on matched prospect cohorts: AI-only (fleet autonomous) vs Hybrid (students directing the fleet), same tools and approval gate, metrics pre-registered. It tests whether human-directed AI beats autonomous AI on real revenue.")]
s += [Paragraph("6. Grading &amp; metrics (weekly, real dollars)", h),
      L(["<b>Team outcomes:</b> qualified pipeline $, high-prob opportunities vs the 10× target, kg advanced/booked, funnel conversion; plus AI-effectiveness (leverage, reply rate, attribution, cost/opportunity).",
         "<b>Individual score (role-fair, /100):</b> primary-track impact 35, contribution-to-team-outcome 20, AI-leverage 15, consistency 15, instructor+peer assessment 15. Four equal tracks — Growth/Outreach, Web &amp; Pipeline Engineering, Creative/Content, Data/Analytics &amp; Ops — each scored in its own currency. Specializing to the website/pipeline build (or creative, or analytics) is a full, unpenalized path."])]
s += [Paragraph("7. Individual accountability", h),
      B("It is a team effort, but each person must materially contribute to earn rewards. Material contribution = individual score ≥ 60 in their track and affirmed by both Edwin and Exos.")]
s += [Paragraph("8. Reward ladder (two rungs; both gated per person)", h),
      L(["<b>75 kg booked → 1U payload reward</b> ($8,000 value; contents ≤ 1 kg): eligible members place a small item and decide its use — engraved dog tags/names, or flown-item/sticker sales for a university-approved team activity (their fundraiser, not Exos revenue), or both. All items flight-safe per the Payload User’s Guide, export-safe.",
         "<b>100 kg booked → launch trip</b> (BLK3 launch, Spaceport America, est. April 2027): eligible members travel. Exos provides a 15-passenger van, ~4-day trip, group lodging (men/women separate), and a Divvy virtual-card food budget (actual receipted expenses up to $55/person/day, food-only merchant controls, receipts in the Divvy app). Cards are issued at the kickoff and held to the launch; they activate only once the launch window is set and the student is booked.",
         "<b>Perfectly clear:</b> anyone who does not materially participate goes on no trip and places nothing in the 1U."])]
s += [Paragraph("9. Total Exos contribution", h),
      B("Approximately $16,100 in direct rewards for a successful project ($8,000 1U spaceflight + ~$8,100 launch trip), plus substantial in-kind value (EXO3 platform + agent-fleet access, Exo’s build time, brand assets/media, CEO + BD team time) and a contracted Payload Sales Engineer pathway for top performers.")]
s += [Paragraph("10. Payload Sales Engineer track", h),
      B("Top performers may earn a contracted Payload Sales Engineer position. Compensation = commission on the customer payload bookings they source, via Exos’s commission system — not tied to any capital raise. A hired student receives attribution credit carried forward for capstone-sourced opportunities, but commissions are payable only on future sales that close beyond the capstone.")]
s += [Paragraph("11. Intellectual property", h),
      B("Exos owns all capstone deliverables (site, copy, campaign assets, pipeline). UTD confirms its capstone terms do not conflict.")]
s += [Paragraph("12. Media", h),
      B("UTD is responsible for local and national media and audience-building around the “AI challenged by UTD” story. Any media naming Exos or its capabilities passes Exos (Lizi) review first — positioning rules apply (flying since 2018; one of only three FAA-licensed reusable rocket launch providers in the U.S.; never “first commercial flight”; no overstatement; export-safe).")]
s += [Paragraph("13. Sources &amp; attribution", h),
      B("Primary source: the Exos BLK3 Payload User’s Guide. Context: historical Exos + Armadillo Aerospace video. Any material used from Armadillo Aerospace must credit “Armadillo Aerospace” (Exos is Armadillo’s commercial successor).")]
s += [Paragraph("14. Compliance", h),
      L(["<b>Student data / FERPA:</b> minimal collection; Edwin uploads from the UTD side.",
         "<b>Export diligence:</b> the roster captures US-citizen / non-US status as a documentation step, not a disqualifier — the student scope is public/commercial marketing data only (no ITAR/CUI); non-US students participate fully.",
         "<b>Securities:</b> any public investor/offering language is counsel-gated, must fit the applicable Reg D exemption’s solicitation rules, and is authored by Exos + counsel only — never by students.",
         "<b>Hosting:</b> the SPACEavailable microsite is served at spaceavailable.exosaero.com (static, reviewed-before-deploy)."])]
s += [Paragraph("15. Term &amp; signatures", h),
      B("Effective on signature; runs the Fall 2026 semester. Either party may terminate for cause with written notice; student data handled per FERPA on termination."), Spacer(1, 10),
      Paragraph("<b>Exos Aerospace Systems &amp; Technologies, Inc.</b>", body),
      Paragraph("By: ____________________________&nbsp;&nbsp;&nbsp;Name: John Quinn&nbsp;&nbsp;&nbsp;Title: Cofounder &amp; CEO&nbsp;&nbsp;&nbsp;Date: __________", body),
      Spacer(1, 6),
      Paragraph("<b>The University of Texas at Dallas</b>", body),
      Paragraph("By: ____________________________&nbsp;&nbsp;&nbsp;Name: ____________________&nbsp;&nbsp;&nbsp;Title: __________&nbsp;&nbsp;&nbsp;Date: __________", body),
      Paragraph("DRAFT — route to counsel (compensation, IP, student data, media, launch-site liability) before signature.", note)]

SimpleDocTemplate(OUT, pagesize=letter, topMargin=1.9*inch, bottomMargin=1.5*inch, leftMargin=0.9*inch, rightMargin=0.9*inch)\
    .build(s, onFirstPage=banners, onLaterPages=banners)
print("saved", OUT)
