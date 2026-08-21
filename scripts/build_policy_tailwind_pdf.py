#!/usr/bin/env python3
"""Letterhead-matched PDF twin of the Exos policy-tailwind brief. Run: python3 scripts/build_policy_tailwind_pdf.py"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exos_letterhead import stationery, MARGINS   # LOCKED letterhead placement
OUT="data-room/Exos_SeriesA/_CANONICAL/Exos_Policy_Tailwind_NSTP_2026-08-21.pdf"
NAVY=HexColor("#0A3D7C"); DARK=HexColor("#1A1A1A"); GREY=HexColor("#555555")
PW,PH=letter
ss=getSampleStyleSheet()
title=ParagraphStyle("t",parent=ss["Title"],fontSize=18,textColor=NAVY,alignment=TA_CENTER,leading=21,spaceAfter=2)
sub=ParagraphStyle("s",parent=ss["Normal"],fontSize=10.5,textColor=GREY,alignment=TA_CENTER,leading=13,spaceAfter=1)
meta=ParagraphStyle("m",parent=ss["Normal"],fontSize=9,textColor=GREY,alignment=TA_CENTER,spaceAfter=3)
h1=ParagraphStyle("h1",parent=ss["Heading1"],fontSize=12.5,textColor=NAVY,spaceBefore=10,spaceAfter=3,leading=14)
body=ParagraphStyle("b",parent=ss["Normal"],fontSize=10.5,textColor=DARK,alignment=TA_JUSTIFY,leading=13.8,spaceAfter=6)
bullet=ParagraphStyle("bu",parent=body,leftIndent=16,bulletIndent=4,spaceAfter=3)
head=ParagraphStyle("hd",parent=body,textColor=NAVY,fontName="Helvetica-Bold",spaceAfter=4)
note=ParagraphStyle("n",parent=body,fontSize=8.5,textColor=GREY,alignment=TA_JUSTIFY,spaceAfter=3)
cellL=ParagraphStyle("cl",parent=ss["Normal"],fontSize=9,textColor=NAVY,fontName="Helvetica-Bold",leading=11)
cellR=ParagraphStyle("cr",parent=ss["Normal"],fontSize=9,textColor=DARK,leading=11.5)
cellH=ParagraphStyle("ch",parent=ss["Normal"],fontSize=9,textColor=HexColor("#FFFFFF"),fontName="Helvetica-Bold",leading=11)
E=[]
def P(t,st=body): E.append(Paragraph(t,st))
def B(t): E.append(Paragraph("•&nbsp;&nbsp;"+t,bullet))
doc=SimpleDocTemplate(OUT,pagesize=letter,**MARGINS)

P("Exos Aerospace &times; National Space Transportation Policy",title)
P("Alignment Brief — the &ldquo;Golden Age of Space Transportation&rdquo; policy and why it accrues to Exos",sub)
P("Proprietary — Unclassified&nbsp;&nbsp;|&nbsp;&nbsp;August 21, 2026&nbsp;&nbsp;|&nbsp;&nbsp;Series A data room",meta)

P("The policy, in brief",h1)
for t in [
 "Updated U.S. National Space Transportation Policy (August 2026), building on the 2025 &ldquo;Enabling Competition in the Commercial Space Industry&rdquo; executive order.",
 "Target: <b>1,000+ launches and reentries per year</b> on U.S. soil by 2030 — roughly a tenfold expansion of today&rsquo;s cadence.",
 "DOT/FAA to cut spaceport-construction red tape, streamline launch and reentry licensing at scale (further reworking Part 450), and stand up senior space roles; integrate space traffic with air traffic control.",
 "Enable <b>launch within 48 hours</b> of high-priority civil and national-security missions.",
 "Greater commercial involvement in Moon/Mars; stronger emphasis on exporting American capabilities; develop additional launch and reentry/landing sites.",
 "Implementation depends on existing law and Congressional funding — a multi-year tailwind, not an overnight reset.",
]: B(t)

P("Why it accrues to Exos",h1)
rows=[
 [Paragraph("Policy pillar",cellH),Paragraph("Exos capability &amp; proof point",cellH)],
 [Paragraph("1,000 launches and reentries by 2030 — reentry is the underserved half",cellL),
  Paragraph("Reusable and recoverable: every Exos flight is a launch and a reentry. Few operators compete on recoverable reentry at cadence — a defensible position on the policy&rsquo;s hardest goal.",cellR)],
 [Paragraph("48-hour responsive launch",cellL),
  Paragraph("Project Karmen — USAF-funded demonstration of two flights in 48 hours on BLK3. A direct proof point.",cellR)],
 [Paragraph("Spaceport / reentry-site build-out; streamlined Part 450 portfolio licensing",cellL),
  Paragraph("Minimal-infrastructure model (pad, power, communications via a mobile command module) makes new sites inexpensive to stand up; portfolio licensing rewards cadence and multi-site operations (West Texas). One of only three FAA-licensed reusable rocket launch providers in the United States.",cellR)],
 [Paragraph("Commercial Moon/Mars",cellL),
  Paragraph("Scorpius Type 5 linerless composite cryogenic tanks — flight-proven at TRL 9 as the fuel and liquid-oxygen tanks on the Intuitive Machines Odysseus (IM-1) and Athena (IM-2) lunar missions — and in-space cryogenic fluid management: enabling infrastructure for lunar and Mars logistics.",cellR)],
 [Paragraph("Export American capabilities",cellL),
  Paragraph("International wet-lease and trade-zone posture (Japan, Australia): ITAR-compliant export of U.S. flight-test and launch services.",cellR)],
]
tbl=Table(rows,colWidths=[2.3*inch,4.4*inch])
tbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.5,HexColor("#BFBFBF")),("VALIGN",(0,0),(-1,-1),"TOP"),
    ("BACKGROUND",(0,0),(-1,0),NAVY),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[HexColor("#FFFFFF"),HexColor("#F2F5F8")])]))
E.append(tbl); E.append(Spacer(1,0.08*inch))

P("Capital-strategy tie-in",h1)
P("The policy is a <b>federal demand-pull signal</b> that strengthens Exos&rsquo;s capital pathway: it reinforces the DPA Title III and Office of Strategic Capital cases (national-priority industrial base for reusable launch, reentry, and spaceports), supports the AEDC flight-test-range positioning, and provides a market-timing catalyst for the growth and listing narrative.")

P("Investor headline",h1)
P("A national policy targeting 1,000+ launches and reentries per year by 2030 sizes the market Exos is built to serve — reusable, recoverable, responsive flight — and points federal capital (Title III / OSC) at exactly the capability Exos provides.",head)

P("Directional; reflects public policy reporting as of August 21, 2026 and Exos program status. Exos has not to date performed direct RDRE hardware development. BLK3 received its FAA launch license in March 2026 and is preparing for flight; it has not flown commercially. Proprietary — Unclassified. Not investment advice.",note)

doc.build(E,onFirstPage=stationery,onLaterPages=stationery)
print("BUILT",OUT)
