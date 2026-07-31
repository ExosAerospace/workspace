#!/usr/bin/env python3
"""Convert the EXOS Capabilities Statement PDF content into a formatted Word doc."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
GREY = RGBColor(0x40, 0x40, 0x40)

doc = Document()

# Base style
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(10.5)

for s in doc.sections:
    s.top_margin = Inches(0.6)
    s.bottom_margin = Inches(0.6)
    s.left_margin = Inches(0.7)
    s.right_margin = Inches(0.7)


def title(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(20)
    r.font.color.rgb = NAVY
    return p


def subtitle(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.size = Pt(11)
    r.font.color.rgb = GREY
    p.space_after = Pt(6)
    return p


def heading(text):
    p = doc.add_paragraph()
    p.space_before = Pt(10)
    p.space_after = Pt(2)
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = ACCENT
    # bottom border
    return p


def body(text):
    p = doc.add_paragraph(text)
    p.paragraph_format.space_after = Pt(4)
    return p


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.add_run(text)
    return p


def item(label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(label + " — ")
    r.bold = True
    r.font.color.rgb = NAVY
    p.add_run(text)
    return p


# Header
title("EXOS AEROSPACE")
subtitle("Capabilities Statement")

# Company Overview
heading("Company Overview")
body("EXOS Aerospace is an FAA-licensed reusable suborbital launch operator providing "
     "wet-leased flight test infrastructure for hypersonic, space, and defense applications.")
body("With modeling tools mature and wind tunnels saturated, repeatable access to flight "
     "testing is the primary constraint. EXOS delivers flight-proven reusable launch platforms "
     "that increase national test cadence, enable rapid iteration, and support payload recovery "
     "and operational learning.")

# Core Capabilities
heading("Core Capabilities")
bullet("Reusable suborbital launch vehicle operations")
bullet("Wet lease flight test services for hypersonic and space systems")
bullet("NASA and DoD mission execution and contract performance")
bullet("Type V linerless composite pressurized structures")
bullet("Fractional parts count architectures enabling repeatable reuse")
bullet("LOX/methane propulsion systems and cryogenic integrated structures")

# Operational Differentiators
heading("Operational Differentiators")
item("Cadence-Focused Infrastructure",
     "EXOS provides operational flight platforms designed for repeatability rather than "
     "one-off launches, enabling faster campaign iteration and reduced program risk.")
item("Wet Lease Integration Model",
     "EXOS operates and maintains the vehicle, reducing integration burden and accelerating "
     "timelines for government and commercial payload customers.")
item("Integrated Composite Structures",
     "Through its ownership position in Scorpius Space Launch Company, EXOS strengthens "
     "industrial depth in Type V composite pressurized structures and scalable manufacturing capability.")
item("RDRE-Aligned Flight Test Capability",
     "EXOS is under contract with the U.S. Department of Defense to develop the flight vehicle "
     "for RDRE engine flight demonstration, where repeatable operations, rapid turnaround, and "
     "practical test execution are critical.")

# Program Execution & Flight Heritage
heading("Program Execution & Flight Heritage")
bullet("Flew SARGE four times, demonstrating reusable suborbital launch operations and repeatable flight execution.")
bullet("Developed BLK3 from concept to hover in 12 months as part of USAF Phase II SBIR development "
       "of a Hypersonic Reusable Launch Vehicle (HRLV), validating integrated pressurized structures "
       "with a 25% size increase and 29% weight reduction.")
bullet("NASA contract performance and suborbital research mission support")
bullet("Northrop Grumman Lunar Lander Challenge - 1st place (Round 1), 2nd place (Round 2)")
bullet("Pioneering work in supersonic suborbital launch vehicles and modular vehicle architectures")
bullet("Reusable propulsion systems proven through hundreds of successful in-flight relights, "
       "enabling repeatable flight cadence")

# Company Data
heading("Company Data")
item("CAGE", "7EMY6")
item("DUNS / UEI", "07-987-4626")
item("PSC Codes", "1725, 1340, 2645, 1675, AR15")
item("NAICS Codes", "336414, 336415, 541715, 927110")

# Contact
heading("Contact")
item("John M. Quinn", "Co-Founder and CEO")
body("299 FM 1903, Greenville, TX 75402")
body("jquinn@exosaero.com")

out = "/Users/exomac/.openclaw/workspace/EXOS_Capabilities_Statement.docx"
doc.save(out)
print("Saved:", out)
print("Paragraphs:", len(doc.paragraphs))
