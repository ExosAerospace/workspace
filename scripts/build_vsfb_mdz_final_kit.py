#!/usr/bin/env python3
"""Final submission kit for VSFBMDZCall: Attachment 2 (Officer Certification of U.S. Ownership, PDF+DOCX for e-sign),
receipt-confirmation email draft, and SUBMIT/ folder with call-ready file names. Run: PYTHONNOUSERSITE=1 python3.12"""
import os, sys, shutil
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, "scripts")
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from exos_letterhead import stationery, MARGINS
from docx import Document
from docx.shared import Pt
D = "drafts/VSFB_MDZ/"; DATE = "2026-10-14"
TITLE = "Officer Certification of U.S. Ownership"
BODY = [
 "Re: Vandenberg Space Force Base Call for Whitepapers for Mission Development Zone (MDZ) Outgrant — VSFBMDZCall (SLD 30/XPR)",
 "I, John Quinn, Cofounder and Chief Executive Officer of Exos Aerospace Systems & Technologies, Inc. (“Exos”), "
 "CAGE 7EMY6, UEI CK24BPZGF854, certify on behalf of Exos that:",
 "1. Exos is a corporation organized and existing under the laws of the State of Texas, with its principal place of "
 "business at 299 FM 1903, Greenville, TX 75402 (see Attachment 1, Texas Secretary of State Certificate of Fact).",
 "2. More than 50 percent of the ownership interest in Exos is held by United States nationals.",
 "3. Exos is therefore a “United States commercial provider” as defined in 51 U.S.C. § 50101(7).",
 "This certification is provided for the Government’s planning use in connection with the whitepaper submitted by Exos "
 "in response to VSFBMDZCall.",
]
SIG = ["_______________________________", "John Quinn", "Cofounder & Chief Executive Officer",
       "Exos Aerospace Systems & Technologies, Inc.", "Date: ____________________"]
ss = getSampleStyleSheet()
h = ParagraphStyle("h", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=HexColor("#0A3D7C"), spaceAfter=10)
p = ParagraphStyle("p", parent=ss["Normal"], fontName="Helvetica", fontSize=10.5, leading=14.5, spaceAfter=8)
pdf = D + "Exos_US_Ownership_Certification_%s.pdf" % DATE
E = [Paragraph(TITLE, h)] + [Paragraph(t, p) for t in BODY] + [Spacer(1, 18)] + [Paragraph(t, p) for t in SIG]
SimpleDocTemplate(pdf, pagesize=letter, title=TITLE, author="Exos Aerospace Systems & Technologies, Inc.", **MARGINS).build(
    E, onFirstPage=lambda c, d: stationery(c, d, page_note="Attachment 2 — VSFBMDZCall"))
doc = Document("assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx")
for el in list(doc.element.body):
    if el.tag.endswith('}p') or el.tag.endswith('}tbl'): doc.element.body.remove(el)
r = doc.add_paragraph().add_run(TITLE); r.bold = True; r.font.size = Pt(14)
for t in BODY + [""] + SIG:
    doc.add_paragraph().add_run(t).font.size = Pt(10.5)
doc.save(D + "Exos_US_Ownership_Certification_%s.docx" % DATE)
# Receipt confirmation email draft (call §4.3 requires a separate email after DoD SAFE upload)
open(D + "VSFB_MDZ_Receipt_Confirmation_Email_%s.txt" % DATE, "w").write(
"""TO: 232909MissionDevelopmentZoneMDZFacilityConstruct@groups.af.mil
CC: lquinn@exosaero.com
FROM: jquinn@exosaero.com
SUBJECT: VSFBMDZCall — Exos Aerospace whitepaper uploaded via DoD SAFE — please confirm receipt

Ms. Allen,

Exos Aerospace Systems & Technologies, Inc. (CAGE 7EMY6) has uploaded its whitepaper in response to the VSFB Call for
Whitepapers for Mission Development Zone (MDZ) Outgrant (VSFBMDZCall) through DoD SAFE today. Files:

  1. Exos_Aerospace_VSFBMDZCall_Whitepaper_2026-10-15.pdf
  2. Exos_Aerospace_VSFBMDZCall_Whitepaper_2026-10-15.docx (editable copy of the same document)
  3. Exos_Aerospace_VSFBMDZCall_Att1_TX_SOS_Certificate_of_Fact.pdf
  4. Exos_Aerospace_VSFBMDZCall_Att2_US_Ownership_Certification.pdf

As section 4.3 of the call requires, please confirm that these files were received.

Exos would also welcome a viewing of the MDZ parcels (call §1.5) at SLD 30's convenience.

Respectfully,
John Quinn
Cofounder & Chief Executive Officer
Exos Aerospace Systems & Technologies, Inc.
jquinn@exosaero.com | +1 (972) 740-8355
""")
S = D + "SUBMIT/"
shutil.copy(D + "Exos_VSFB_MDZ_Whitepaper_%s.pdf" % DATE, S + "Exos_Aerospace_VSFBMDZCall_Whitepaper_2026-10-15.pdf")
shutil.copy(D + "Exos_VSFB_MDZ_Whitepaper_%s.docx" % DATE, S + "Exos_Aerospace_VSFBMDZCall_Whitepaper_2026-10-15.docx")
print("ok", pdf)
