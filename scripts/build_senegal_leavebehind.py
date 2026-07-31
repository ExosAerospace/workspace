#!/usr/bin/env python3
"""Senegal NCE leave-behind card, built ON the PRIMARY Exos letterhead (dark text on white)."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SRC="assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT="drafts/Exos_Senegal_NCE_LeaveBehind.docx"
NAVY=RGBColor(0x0b,0x1a,0x3a); GOLD=RGBColor(0xb8,0x86,0x1f); DARK=RGBColor(0x1a,0x1a,0x1a); GREY=RGBColor(0x44,0x44,0x44)

doc=Document(SRC)

def para(text="",size=11,bold=False,color=DARK,align=None,after=6,before=0,italic=False):
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(after); p.paragraph_format.space_before=Pt(before)
    if align: p.alignment=align
    r=p.add_run(text); r.font.size=Pt(size); r.font.bold=bold; r.font.italic=italic; r.font.color.rgb=color; r.font.name="Calibri"
    return p

def bullet(text,size=11):
    p=doc.add_paragraph(style=None); p.paragraph_format.left_indent=Inches(0.28); p.paragraph_format.space_after=Pt(5)
    r=p.add_run("▸  "); r.font.size=Pt(size); r.font.bold=True; r.font.color.rgb=GOLD; r.font.name="Calibri"
    r2=p.add_run(text); r2.font.size=Pt(size); r2.font.color.rgb=DARK; r2.font.name="Calibri"
    return p

# Title
para("NATIONAL CHARTER ENTERPRISE", size=17, bold=True, color=NAVY, after=1)
para("A Sovereign Path to Space for Senegal", size=13, bold=True, color=GOLD, after=8)
para("US-operated reusable launch, wet-leased to Senegal  ·  engineer training with ASES  ·  US export financing",
     size=10.5, italic=True, color=GREY, after=12)

# The offer
para("THE OFFER", size=11.5, bold=True, color=NAVY, after=4)
bullet("Base a US-operated, FAA-licensed reusable launch vehicle at Senegal's spaceport. Exos owns and flies the rocket; Senegal commands the missions — a wet lease, not a purchase.")
bullet("Train Senegalese engineers and students through a joint ASES–Exos program, building sovereign national capability.")
bullet("Gain real flight-test and launch capability without building a rocket program from the ground up.")
bullet("Structure the cost through US EXIM export financing, so Senegal gains the capability without carrying it alone.")

# Why it matters
para("WHY IT MATTERS", size=11.5, bold=True, color=NAVY, after=4, before=6)
para("Senegal becomes Africa's sovereign, US-aligned gateway to space — near-term, proven, and financed as a United States export.",
     size=11, color=DARK, after=12)

# The 30-second summary (highlighted)
para("IN BRIEF", size=11.5, bold=True, color=NAVY, after=4)
q=doc.add_paragraph(); q.paragraph_format.left_indent=Inches(0.2); q.paragraph_format.space_after=Pt(12)
qr=q.add_run("“Senegal can become Africa's sovereign gateway to space — without building a rocket program from scratch. "
    "Exos is one of only three FAA-licensed reusable rocket launch providers in the United States. Under a National Charter, "
    "we would base a US-operated reusable launch vehicle at your spaceport and train Senegalese engineers through ASES. "
    "And because it is a US export, EXIM financing can cover much of the cost — so Senegal gains real launch and flight-test "
    "capability without carrying it alone.”")
qr.font.size=Pt(11); qr.font.italic=True; qr.font.color.rgb=NAVY; qr.font.name="Calibri"

# The question
para("THE QUESTION", size=11.5, bold=True, color=NAVY, after=4)
para("Is Senegal prepared to make this its national space charter — and who on your side should we work with to structure it with US financing?",
     size=11.5, bold=True, color=DARK, after=14)

# Contact
c=doc.add_paragraph(); c.paragraph_format.space_before=Pt(4)
cr=c.add_run("John Quinn  ·  Cofounder & CEO  ·  Exos Aerospace  ·  jquinn@exosaero.com  ·  +1 972 740 8355  ·  www.exosaero.com")
cr.font.size=Pt(9.5); cr.font.color.rgb=GREY; cr.font.name="Calibri"

doc.save(OUT)
print("BUILT", OUT)
