#!/usr/bin/env python3
"""AFRL RDRE RFI (2449PS50) response white paper — on PRIMARY Exos letterhead."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SRC="assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT="drafts/Exos_AFRL_RDRE_RFI_Response.docx"
NAVY=RGBColor(0x0b,0x1a,0x3a); GOLD=RGBColor(0xb8,0x86,0x1f); DARK=RGBColor(0x1a,0x1a,0x1a); GREY=RGBColor(0x44,0x44,0x44); RED=RGBColor(0x8a,0x1a,0x1a)
doc=Document(SRC)

def para(text="",size=10.5,bold=False,color=DARK,after=6,before=0,italic=False,align=None):
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(after); p.paragraph_format.space_before=Pt(before)
    if align: p.alignment=align
    r=p.add_run(text); r.font.size=Pt(size); r.font.bold=bold; r.font.italic=italic; r.font.color.rgb=color; r.font.name="Calibri"
    return p
def head(text): para(text,size=11.5,bold=True,color=NAVY,after=3,before=8)
def bullet(text,size=10.5):
    p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(0.28); p.paragraph_format.space_after=Pt(4)
    r=p.add_run("▸  "); r.font.size=Pt(size); r.font.bold=True; r.font.color.rgb=GOLD; r.font.name="Calibri"
    r2=p.add_run(text); r2.font.size=Pt(size); r2.font.color.rgb=DARK; r2.font.name="Calibri"

# marking
para("DISTRIBUTION C  ·  PROPRIETARY  ·  UNCLASSIFIED", size=8.5, bold=True, color=RED, after=8, align=WD_ALIGN_PARAGRAPH.CENTER)
# title
para("Response to AFRL RFI 2449PS50 — Storable-Propellant RDRE / RBCC", size=15, bold=True, color=NAVY, after=1)
para("Reusable VTVL Flight-Test and Integration Platform for Storable-Propellant Rotating Detonation Rocket Engine Maturation",
     size=11, bold=True, color=GOLD, after=2)
para("Submitted under the AFRL Rocket Lab “Hermes” BAA (FA9300-20-S-0001)  ·  Response due 10 August 2026",
     size=9.5, italic=True, color=GREY, after=10)

head("1.  Respondent and Interest")
para("Exos Aerospace Systems & Technologies, Inc. (Greenville, TX) is one of only three FAA-licensed reusable rocket launch "
     "providers in the United States. Exos operates a reusable, vertical-takeoff / vertical-landing (VTVL) precision suborbital "
     "reusable launch vehicle (BLK3 PSRLV) with flight heritage dating to 2018. Exos welcomes the opportunity to support AFRL's "
     "objectives for a storable-propellant Rotating Detonation Rocket Engine (RDRE) and rocket-based combined-cycle (RBCC) "
     "propulsion system, and responds to RFI 2449PS50 as a reusable flight-test and integration provider.")

head("2.  Relevant Capability")
bullet("Reusable VTVL flight-test platform: FAA-licensed BLK3, powered ascent and powered landing, article recovery, and ~2-day turnaround — enabling high-cadence, low-cost-per-test flight campaigns.")
bullet("Propulsion integration: Exos integrates partner- or government-furnished propulsion onto a flight vehicle, including pressure-fed (regulated blowdown) architectures.")
bullet("Storable-compatible tankage and feed: Scorpius Space Launch Company Type-5 all-composite tanks — TRL-9 with lunar flight heritage as propellant containment — rated to 1250 psi MEOP and adaptable to storable-propellant pressure-fed systems, with wetted materials selected for propellant compatibility.")
bullet("Standing in the AFRL propulsion ecosystem: active USAF SBIR Phase II (FA9300-25-C-6022) under the Hermes program.")

head("3.  Proposed Contribution to a Storable-Propellant RDRE / RBCC Effort")
para("Exos does not develop rotating detonation engines. Exos's value to this effort is as the reusable flight-test and "
     "integration prime that matures a partner-furnished RDRE core in a real flight environment:", after=4)
bullet("Reusable flight-test bed: fly an RDRE / RBCC article on a recoverable VTVL vehicle, recover it intact for post-flight inspection, and re-fly — compressing the cost and schedule of RDRE flight qualification versus expendable approaches.")
bullet("Preferred RDRE hardware path (down-select): Exos's leading approach is to integrate Gloyer-Taylor Laboratories (GTL) fully-machined RDRE hardware (approximately 2,500 lbf-thrust class), with Exos as the flight-test / integration prime and GTL as the engine provider. A NASA MSFC RDRE license path remains an alternative under Exos's program trade study.")
bullet("Storable-propellant relevance: the GTL fully-machined RDRE can be configured for storable hypergolic bipropellants, with dinitrogen tetroxide / monomethylhydrazine (N2O4 / MMH) as the reference pair — the highest-performance storable hypergolic, with deep launch upper-stage and spacecraft heritage. Hypergolic ignition supports reliable, restartable detonation initiation without a separate ignition system, aligning directly with the RFI's storable-propellant focus and Exos's pressure-fed architecture.")

head("4.  In-Space Application Relevance")
para("A storable hypergolic RDRE is well suited to in-space propulsion. Ambient-storable propellants eliminate cryogenic "
     "boiloff and enable multi-year on-orbit storage; hypergolic ignition enables reliable, restartable, multi-burn operation "
     "without a separate ignition system; and RDRE pressure-gain combustion offers higher specific impulse than conventional "
     "storable engines, increasing delta-V for orbital transfer, maneuvering, and servicing. This aligns with emerging DoD "
     "in-space servicing, mobility, and logistics (SML) needs. Exos's contribution is a reusable suborbital flight-qualification "
     "pathway that matures the storable RDRE in a relevant flight environment to de-risk it for in-space and orbital-transfer-"
     "vehicle use, complemented by long-duration storable tankage via Scorpius Type-5.")

head("5.  Supporting Reference Data")
para("The technical viability of hypergolic space-storable rotating detonation rocket engines is supported by published, "
     "peer-reviewed research. UCLA (Spearrin Laboratory, Department of Mechanical & Aerospace Engineering) has conducted "
     "experimental RDRE research focused on hypergolic space-storable propellants and additively manufactured combustors, "
     "including hot-fire test campaigns and, in collaboration with AFRL, MHz-rate optical detonation diagnostics "
     "(A. P. Nair et al., AIAA Best Paper in Pressure Gain Combustion; A. P. Nair, Ph.D. dissertation, UCLA, 2022). Exos "
     "proposes to leverage this and related reference data to inform integration and flight-test planning for a "
     "storable-propellant RDRE.")

head("6.  Relevant Experience")
bullet("Reusable suborbital flight operations and recovery since 2018 (SARGE / BLK3).")
bullet("USAF SBIR Phase II propulsion work under the Hermes program (FA9300-25-C-6022).")
bullet("Scorpius Type-5 composite tanks flew as fuel and LOX containment on the Intuitive Machines Odysseus and Athena lunar missions.")

head("7.  Teaming Posture and Interest")
para("Exos offers itself as the reusable flight-test and integration prime for a storable-propellant RDRE / RBCC maturation "
     "effort and is prepared to team with AFRL, GTL, and additional performers. Exos requests to be considered as AFRL develops "
     "any follow-on solicitation, and is available for further technical exchange under appropriate distribution controls.")

head("8.  Point of Contact")
para("John Quinn  —  Cofounder & CEO  ·  Exos Aerospace Systems & Technologies, Inc.  ·  jquinn@exosaero.com  ·  +1 972 740 8355", size=10, color=GREY, after=2)
para("CAGE / UEI, business size, and Distribution-C eligibility statement to be inserted per the RFI submission template.", size=8.5, italic=True, color=GREY)

doc.save(OUT); print("BUILT", OUT)
