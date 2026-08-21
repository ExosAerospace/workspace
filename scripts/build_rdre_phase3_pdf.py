#!/usr/bin/env python3
"""Letterhead-matched PDF twin of the RDRE Phase III proposal (reliable; no soffice)."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
                                PageBreak, Table, TableStyle)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exos_letterhead import stationery, MARGINS   # LOCKED letterhead placement — do not hand-place banners
OUT = "drafts/Exos_RDRE_Phase3_BLK4Heavy_Proposal.pdf"
NAVY = HexColor("#0A3D7C"); DARK = HexColor("#1A1A1A"); GREY = HexColor("#555555")
PW, PH = letter

ss = getSampleStyleSheet()
title = ParagraphStyle("t", parent=ss["Title"], fontSize=19, textColor=NAVY, alignment=TA_CENTER, leading=22, spaceAfter=2)
title2 = ParagraphStyle("t2", parent=ss["Title"], fontSize=14, textColor=NAVY, alignment=TA_CENTER, leading=17, spaceAfter=2)
sub = ParagraphStyle("s", parent=ss["Normal"], fontSize=10.5, textColor=GREY, alignment=TA_CENTER, leading=13, spaceAfter=2)
cov = ParagraphStyle("cov", parent=ss["Normal"], fontSize=10.5, textColor=DARK, alignment=TA_CENTER, leading=15, spaceAfter=1)
covb = ParagraphStyle("covb", parent=cov, fontName="Helvetica-Bold")
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=13, textColor=NAVY, spaceBefore=11, spaceAfter=3, leading=15)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, textColor=NAVY, spaceBefore=7, spaceAfter=2, leading=13)
body = ParagraphStyle("b", parent=ss["Normal"], fontSize=10.5, textColor=DARK, alignment=TA_JUSTIFY, leading=13.8, spaceAfter=6)
bullet = ParagraphStyle("bu", parent=body, leftIndent=16, bulletIndent=4, spaceAfter=3)
note = ParagraphStyle("n", parent=body, fontSize=9, textColor=GREY, spaceAfter=4)
mile = ParagraphStyle("m", parent=body, leftIndent=16, spaceAfter=3)

E = []
def P(t, st=body): E.append(Paragraph(t, st))
def B(t): E.append(Paragraph("•&nbsp;&nbsp;" + t, bullet))

doc = SimpleDocTemplate(OUT, pagesize=letter, **MARGINS)

# ---- COVER ----
P("SBIR Phase III Proposal", title)
P("Reusable RDRE Orbital Access via BLK4 Heavy", title2)
P("Project Hermes Phase III — Rotating Detonation Rocket Engine to Reusable Orbit", sub)
E.append(Spacer(1, 0.12*inch))
P("Total Proposed Value: $60,000,000&nbsp;&nbsp;|&nbsp;&nbsp;Period of Performance: 36 Months", covb)
E.append(Spacer(1, 0.12*inch))
P("Prepared for: U.S. Space Force / Air Force Research Laboratory (AFRL) — SpaceWERX", covb)
P("Phase III Basis: SBIR Phase II Contract FA9300-25-C-6022 (Project Hermes, HVRR-RDRE)", cov)
P("Authority: 15 U.S.C. &sect; 638(r) — SBIR/STTR Phase III (sole-source, no dollar ceiling)", cov)
E.append(Spacer(1, 0.1*inch))
P("Submitted by: Exos Aerospace Systems &amp; Technologies, Inc.", covb)
P("299 FM 1903, Greenville, TX 75402", cov)
P("Point of Contact: John Quinn, Cofounder &amp; Chief Executive Officer", cov)
P("jquinn@exosaero.com&nbsp;&nbsp;|&nbsp;&nbsp;+1 (972) 740-8355&nbsp;&nbsp;|&nbsp;&nbsp;www.exosaero.com", cov)
E.append(Spacer(1, 0.15*inch))
P("Proprietary — Unclassified. Contains Exos Aerospace business-sensitive and pre-decisional planning data. "
  "Not for public release. Cost and technical approach are proposal-stage estimates.", note)
E.append(PageBreak())

# ---- 1 ----
P("1. Executive Summary", h1)
P("The next decade of national power will be decided in the physical world. The re-industrialization of space — "
  "responsive orbital access, on-orbit logistics, and assured launch — is a multi-trillion-dollar contest, and the "
  "United States needs launch providers that are reusable, capital-efficient, and domestically sovereign. Exos "
  "Aerospace proposes a $60,000,000 SBIR Phase III effort to mature Rotating Detonation Rocket Engine (RDRE) "
  "propulsion from our active Air Force Phase II into an integrated, reusable orbital launch capability: the BLK4 Heavy.")
P("This Phase III derives directly from and extends Exos&rsquo;s active DoD SBIR Phase II, contract "
  "FA9300-25-C-6022 (Project Hermes, HVRR-RDRE). Under 15 U.S.C. &sect; 638(r), that Phase II establishes "
  "sole-source Phase III authority with no dollar ceiling, allowing any federal component to fund the work that "
  "carries the technology to application. The application we propose is a reusable RDRE-powered heavy configuration "
  "that closes the gap between Exos&rsquo;s proven reusable suborbital heritage and responsive orbital access.")
P("$60M does not build a clean-sheet orbital rocket, and it does not need to. Exos already holds the expensive, "
  "flight-proven pieces: a reusable vehicle with propulsive landing and autonomous abort, flight-proven Scorpius "
  "Type 5 linerless composite cryogenic tankage with lunar heritage, and a minimal-infrastructure operating model. "
  "This program funds the bridge — RDRE propulsion maturation and the BLK4 Heavy airframe — to a demonstrated "
  "reusable RDRE orbital pathfinder, not an operational fleet.")

# ---- 2 ----
P("2. Phase III Basis and Eligibility", h1)
P("Exos is the awardee of active DoD SBIR Phase II contract FA9300-25-C-6022 (Project Hermes), an Air Force effort "
  "in high-speed and RDRE-relevant propulsion. SBIR Phase III authority provides that work which &ldquo;derives from, "
  "extends, or completes&rdquo; a prior SBIR effort may be awarded sole-source, by any federal agency or DoD "
  "component, with no dollar ceiling and no requirement for further competition.")
B("Derivation: this effort extends the Hermes RDRE propulsion line from component and high-speed work into an "
  "integrated, reusable orbital launch application.")
B("Contract vehicle: sole-source SBIR Phase III, prime customer U.S. Space Force / AFRL / SpaceWERX; NASA Marshall "
  "Space Flight Center is an available secondary Phase III path given shared RDRE interest.")
B("No competition required and no ceiling; the Government preserves SBIR data rights while accelerating a domestic "
  "reusable-launch capability.")

# ---- 3 ----
P("3. Strategic Context and Demand", h1)
P("The demand signal is unambiguous. The Space Force has tripled the NSSL Phase 3 Lane 1 ceiling to $17B, with a "
  "total program ceiling near $30B, and projects national launch operations rising from roughly 214 in 2026 to over "
  "500 by 2036. Tactically responsive and assured orbital access are stated priorities. RDRE is a leap-ahead "
  "propulsion cycle — higher theoretical efficiency in a compact, potentially lower-cost engine — and the nation "
  "that fields it first on a reusable vehicle changes the launch cost curve.")
P("Exos is positioned to deliver that capability capital-efficiently. As one of only three FAA-licensed reusable "
  "rocket launch providers in the United States, and operating as an AI-native, lean organization, Exos pursues in "
  "tens of millions what legacy programs pursue in hundreds of millions.")

# ---- 4 ----
P("4. Technical Approach", h1)
P("4.1 RDRE Propulsion Maturation — Structured Trade-Study Down-Select", h2)
P("Exos has not performed direct RDRE hardware development to date; this Phase III funds that maturation through a "
  "disciplined, competed trade-study down-select rather than a pre-committed path. Three candidate approaches will "
  "be evaluated against cost, schedule, performance, manufacturability, and defense-industrial-base sovereignty, "
  "with a Government down-select gate before any vehicle-level commitment:")
B("A GTL-style fully-machined RDRE fabrication approach. Exos does not own this technology; it is evaluated as one "
  "candidate to be licensed or partnered.")
B("A NASA Marshall Space Flight Center RDRE technology license, leveraging Government-developed RDRE heritage.")
B("A hybrid path combining both — for example a domestic fully-machined build informed by NASA MSFC design heritage.")
P("Exos&rsquo;s working preference, subject to and to be confirmed by the trade, is the domestic fully-machined "
  "(GTL-style) path on U.S. defense-industrial-base and supply-chain-integrity grounds — keeping the engine build "
  "sovereign, controllable, and free of licensing dependencies. Final partner and build-path selection is determined "
  "by the trade results and Government direction; all three options remain open at proposal stage.")
P("The down-select is followed by injector and combustor subscale hot-fire, then full-scale hot-fire, gating "
  "vehicle integration on demonstrated engine performance.")
P("4.2 BLK4 Heavy Configuration", h2)
P("BLK4 Heavy is Exos&rsquo;s proposed next-generation reusable heavy vehicle. It is not yet built; this program "
  "designs, fabricates, and demonstrates the first article, leveraging assets Exos already holds:")
B("Reusable heritage from BLK3: propulsive landing, GPS/INS-guided instantaneous-impact-point autonomous abort, and "
  "2&ndash;3 day turnaround — a reuse operating model already demonstrated at suborbital scale.")
B("Scorpius Type 5 linerless composite cryogenic tankage — flight-proven at TRL 9 as the fuel and liquid-oxygen "
  "tanks on the Intuitive Machines Odysseus (IM-1) and Athena (IM-2) lunar missions. Exos owns 18% of Scorpius with "
  "a right of first refusal on the balance.")
B("Integrated Pressurized Structures: using the composite tank as a load-bearing primary structure to cut dry mass "
  "— the differentiator that makes a reusable heavy vehicle close on a $60M budget.")
B("Minimal-infrastructure operations: pad, power, and communications plus a mobile command module, reducing the "
  "fixed-infrastructure cost that burdens conventional orbital programs.")
P("4.3 Reusable-to-Orbit Progression", h2)
P("The path is incremental and flight-proven at each step: RDRE ground hot-fire, then a suborbital RDRE flight "
  "demonstration on Exos&rsquo;s proven reusable platform, then BLK4 Heavy assembly and a reusable RDRE orbital "
  "pathfinder attempt. Each gate retires risk before the next commitment, and reuse is validated at suborbital scale "
  "before it is asked to perform at orbital scale.")

# ---- 5 ----
P("5. Program Plan and Milestones (36 Months)", h1)
for m, t in [
    ("Months 0&ndash;6", "RDRE trade study and Government down-select gate; BLK4 Heavy system requirements review; Type 5 tank requirements definition with Scorpius."),
    ("Months 6&ndash;12", "RDRE injector/combustor subscale hot-fire; BLK4 Heavy preliminary and critical design; Type 5 first-article fabrication start."),
    ("Months 12&ndash;18", "Full-scale RDRE hot-fire campaign; BLK4 Heavy structures and tank integration."),
    ("Months 18&ndash;24", "Integrated propulsion-and-vehicle ground test; suborbital RDRE flight demonstration on reusable platform."),
    ("Months 24&ndash;30", "BLK4 Heavy assembly; propulsive-return reusability demonstration; FAA Part 450 orbital licensing progression."),
    ("Months 30&ndash;36", "Reusable RDRE orbital pathfinder flight demonstration; transition and sustainment package to the Government customer."),
]:
    P("<b>%s:</b> %s" % (m, t), mile)

# ---- 6 ----
P("6. Cost Summary ($60,000,000)", h1)
data = [
    ["RDRE propulsion: trade study, down-select, hardware and hot-fire test", "$18.0M"],
    ["BLK4 Heavy airframe, structures, and Scorpius Type 5 tankage (first article)", "$16.0M"],
    ["Reusability and GN&C: propulsive return, avionics, autonomous-abort scale-up", "$8.0M"],
    ["Integration, GSE, and ground/launch infrastructure", "$6.0M"],
    ["Flight test and orbital pathfinder demonstration", "$8.0M"],
    ["Program management, FAA Part 450 licensing, systems engineering, reserve", "$4.0M"],
    ["Total", "$60.0M"],
]
tbl = Table(data, colWidths=[5.4*inch, 1.1*inch])
tbl.setStyle(TableStyle([
    ("FONTSIZE",(0,0),(-1,-1),9.5), ("TEXTCOLOR",(0,0),(-1,-1),DARK),
    ("GRID",(0,0),(-1,-1),0.5,HexColor("#BFBFBF")),
    ("ALIGN",(1,0),(1,-1),"RIGHT"), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ("LEFTPADDING",(0,0),(-1,-1),6),
    ("BACKGROUND",(0,-1),(-1,-1),HexColor("#EEF2F8")),
    ("TEXTCOLOR",(0,-1),(-1,-1),NAVY), ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
]))
E.append(tbl); E.append(Spacer(1, 0.08*inch))
P("Cost is scoped to a demonstrated reusable RDRE orbital pathfinder that leverages existing Exos and Scorpius "
  "assets; it is not scoped to an operational orbital fleet, which would follow as a separate production effort.", note)

# ---- 7 ----
P("7. Why Exos", h1)
B("Reusable flight heritage since 2018 through the SARGE and Armadillo lineage; BLK3 received its FAA launch license "
  "in March 2026 and is preparing for flight. One of only three FAA-licensed reusable rocket launch providers in the United States.")
B("Flight-proven Scorpius Type 5 cryogenic tankage with lunar heritage (IM-1, IM-2) — a de-risked, domestic "
  "structural and propellant-storage foundation few can match.")
B("Capital efficiency: an AI-native, lean operating model that pursues in tens of millions what legacy programs pursue in hundreds of millions.")
B("Minimal-infrastructure, mobile operations that lower the cost and expand the geography of responsive launch.")

# ---- 8 ----
P("8. Key Risks and Mitigations", h1)
B("RDRE maturity: mitigated by a competed trade-study down-select and gated hot-fire campaign before any "
  "vehicle-level commitment; Exos does not assume an unproven engine into the vehicle.")
B("First reusable orbital flight: mitigated by incremental build-up on proven suborbital reuse, including a suborbital RDRE demonstration before the orbital attempt.")
B("Licensing: FAA Part 450 transition is already underway; early and continuous FAA AST engagement is budgeted.")
B("Cost and schedule: milestone-gated funding and maximum reuse of existing flight-proven assets compress both.")

# ---- 9 ----
P("9. Management, Teaming, and Transition", h1)
P("Exos Aerospace is the prime and integrator. Scorpius Space Launch Company (Exos owns 18% with a right of first "
  "refusal) provides Type 5 composite cryogenic tankage. The RDRE technology partner and build path — domestic "
  "GTL-style, NASA Marshall via license, or a hybrid — remain TBD, to be fixed by the Section 4.1 trade, with "
  "Exos&rsquo;s working preference the sovereign domestic build path for DIB integrity. The program delivers to the "
  "Government a demonstrated reusable RDRE orbital pathfinder, an engine down-select and test record, and a "
  "transition path to a follow-on production and operational capability, with SBIR data rights preserved.")
E.append(HRFlowable(width="100%", thickness=0.5, color=GREY, spaceBefore=6, spaceAfter=6))
P("This proposal is submitted for Government planning and negotiation purposes. Technical maturity, cost, and "
  "schedule are proposal-stage estimates subject to the trade-study down-select and Government direction. Exos "
  "Aerospace has not to date performed direct RDRE hardware development; the RDRE approach and any third-party "
  "technology are to be selected and licensed under this effort.", note)

doc.build(E, onFirstPage=stationery, onLaterPages=stationery)
print("BUILT", OUT)
