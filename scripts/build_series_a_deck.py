#!/usr/bin/env python3
"""Build Exos Aerospace Series A Pitch Deck — May 2026"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

WORKSPACE = '/Users/exomac/.openclaw/workspace'
OUT = os.path.join(WORKSPACE, 'Exos_SeriesA_PitchDeck_May2026.pptx')
BG_IMG = os.path.join(WORKSPACE, 'assets/space-bg-dark-vivid.png')
LOGO_IMG = os.path.join(WORKSPACE, 'assets/exos-letterhead-logo.png')

# Colors
NAVY = RGBColor(0x0A, 0x1A, 0x3A)
DARK_BG = RGBColor(0x0B, 0x0E, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xCC, 0xCC, 0xCC)
MED_GRAY = RGBColor(0x99, 0x99, 0x99)
ACCENT_BLUE = RGBColor(0x00, 0x9E, 0xD9)
ACCENT_GOLD = RGBColor(0xFF, 0xB8, 0x00)
ACCENT_GREEN = RGBColor(0x00, 0xC8, 0x7A)
ACCENT_RED = RGBColor(0xFF, 0x4D, 0x4D)

# Slide dimensions (widescreen)
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H

# Use blank layout
blank_layout = prs.slide_layouts[6]


def add_bg(slide):
    """Add dark background rectangle."""
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), SLIDE_W, SLIDE_H
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = DARK_BG
    bg.line.fill.background()
    # Try to add image on top
    if os.path.exists(BG_IMG):
        try:
            pic = slide.shapes.add_picture(BG_IMG, Inches(0), Inches(0), SLIDE_W, SLIDE_H)
            # Make semi-transparent by adjusting - we'll just use it as-is
        except:
            pass


def add_footer(slide, text="PRIVATE & CONFIDENTIAL | NOT FOR DISTRIBUTION"):
    """Add footer bar."""
    footer = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.0), SLIDE_W, Inches(0.5)
    )
    footer.fill.solid()
    footer.fill.fore_color.rgb = RGBColor(0x05, 0x08, 0x12)
    footer.line.fill.background()
    tf = footer.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(9)
    run.font.color.rgb = MED_GRAY
    run.font.name = 'Calibri'


def add_accent_line(slide, left, top, width):
    """Add accent line."""
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Pt(3)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = ACCENT_BLUE
    line.line.fill.background()


def add_text_box(slide, left, top, width, height, text, font_size=14, bold=False,
                 color=WHITE, alignment=PP_ALIGN.LEFT, font_name='Calibri',
                 line_spacing=1.2, italic=False):
    """Add a text box with given properties."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = alignment
    p.space_after = Pt(4)
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font_name
    if italic:
        run.font.italic = True
    return txBox


def add_multi_text(slide, left, top, width, height, items, default_size=14,
                   default_color=WHITE):
    """Add text box with multiple formatted segments (list of dicts)."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        p.alignment = item.get('align', PP_ALIGN.LEFT)
        p.space_after = Pt(item.get('space_after', 4))
        p.space_before = Pt(item.get('space_before', 0))

        text = item.get('text', '')
        run = p.add_run()
        run.text = text
        run.font.size = Pt(item.get('size', default_size))
        run.font.bold = item.get('bold', False)
        run.font.color.rgb = item.get('color', default_color)
        run.font.name = item.get('font', 'Calibri')
        if item.get('italic'):
            run.font.italic = True

    return txBox


def add_card(slide, left, top, width, height, title, body, title_color=ACCENT_BLUE):
    """Add a card-like shape with title and body."""
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = RGBColor(0x12, 0x18, 0x2A)
    card.line.color.rgb = RGBColor(0x25, 0x35, 0x55)
    card.line.width = Pt(1)

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.15)
    tf.margin_right = Inches(0.15)
    tf.margin_top = Inches(0.1)

    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = title
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = title_color
    run.font.name = 'Calibri'

    p2 = tf.add_paragraph()
    p2.space_before = Pt(6)
    run2 = p2.add_run()
    run2.text = body
    run2.font.size = Pt(11)
    run2.font.color.rgb = LIGHT_GRAY
    run2.font.name = 'Calibri'


def make_table(slide, left, top, width, rows_data, col_widths=None):
    """Create a styled table."""
    n_rows = len(rows_data)
    n_cols = len(rows_data[0]) if rows_data else 2
    row_h = Inches(0.4)
    table_h = row_h * n_rows

    table_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, table_h)
    table = table_shape.table

    if col_widths:
        for i, w in enumerate(col_widths):
            table.columns[i].width = w

    for r_idx, row in enumerate(rows_data):
        for c_idx, cell_text in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.text = str(cell_text)

            # Style
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(11)
                    run.font.name = 'Calibri'
                    if r_idx == 0:
                        run.font.bold = True
                        run.font.color.rgb = ACCENT_BLUE
                    else:
                        run.font.color.rgb = WHITE

            # Cell fill
            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = RGBColor(0x0A, 0x14, 0x2A)
            elif r_idx % 2 == 0:
                cell.fill.fore_color.rgb = RGBColor(0x10, 0x16, 0x26)
            else:
                cell.fill.fore_color.rgb = RGBColor(0x0D, 0x12, 0x20)

    return table_shape


# ============================================================
# SLIDE 1 — COVER
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

# Logo
if os.path.exists(LOGO_IMG):
    try:
        slide.shapes.add_picture(LOGO_IMG, Inches(0.8), Inches(0.6), Inches(3.0))
    except:
        pass

add_text_box(slide, Inches(0.8), Inches(2.2), Inches(10), Inches(1.2),
             "EXOS AEROSPACE", font_size=48, bold=True, color=WHITE)

add_text_box(slide, Inches(0.8), Inches(3.4), Inches(10), Inches(0.8),
             "Reusable Flight Test Infrastructure for the Space & Defense Industrial Base",
             font_size=22, color=ACCENT_BLUE)

add_accent_line(slide, Inches(0.8), Inches(4.3), Inches(4))

add_multi_text(slide, Inches(0.8), Inches(4.6), Inches(10), Inches(2), [
    {'text': 'Licensed Reusable Launch  |  Lunar-Proven Technology  |  Profitable',
     'size': 16, 'color': LIGHT_GRAY, 'italic': True, 'space_after': 20},
    {'text': 'Raising: $10M Series A', 'size': 20, 'bold': True, 'color': ACCENT_GOLD,
     'space_after': 8},
    {'text': 'May 2026', 'size': 14, 'color': MED_GRAY},
])

add_footer(slide)

# ============================================================
# SLIDE 2 — THE FLIGHT TEST BOTTLENECK
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "THE FLIGHT TEST BOTTLENECK", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11), Inches(0.6),
             "Every orbital program needs flight truth before it commits. There is no substitute.",
             font_size=18, bold=True, color=ACCENT_BLUE)

# Problem cards
problems = [
    ("Wind tunnels are saturated", "18-24 month wait times at major facilities nationwide"),
    ("Computational modeling has limits", "Models diverge from reality at hypersonic and reentry regimes"),
    ("Custom test vehicle costs $50M+", "And takes 2-3 years before first flight"),
    ("Failed orbital launch destroys hardware", "No intact hardware = no post-flight analysis"),
]

for i, (title, body) in enumerate(problems):
    col = i % 2
    row = i // 2
    x = Inches(0.8) + col * Inches(5.8)
    y = Inches(2.4) + row * Inches(1.8)
    add_card(slide, x, y, Inches(5.4), Inches(1.5), title, body, ACCENT_RED)

add_text_box(slide, Inches(0.8), Inches(6.2), Inches(11), Inches(0.7),
             "The gap: Between simulation and orbital commitment, there is no affordable, rapid, repeatable flight test option.",
             font_size=16, bold=True, color=ACCENT_GOLD)

add_footer(slide)

# ============================================================
# SLIDE 3 — EXOS: THE DE-RISKING PLATFORM
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "EXOS: THE DE-RISKING PLATFORM", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

add_text_box(slide, Inches(0.8), Inches(1.5), Inches(11), Inches(0.6),
             "One of only three U.S.-licensed reusable suborbital launch companies \u2014 and the only one currently flying commercial test campaigns",
             font_size=15, bold=True, color=ACCENT_BLUE)

cards = [
    ("FLIGHT TEST AT A FRACTION OF THE COST",
     "Customers place avionics, flight controls, and subsystems in our BLK3 payload bay. "
     "BLK3 flies to space, executes reentry profiles, then recovers. "
     "Customers validate hardware survives \u2014 before risking an orbital vehicle.",
     ACCENT_GREEN),
    ("SILENT OPERATIONS",
     "All test operations conducted confidentially until the customer is ready to disclose. "
     "Failed tests never become public. Critical for companies with public investors, "
     "government stakeholders, or competitive exposure.",
     ACCENT_BLUE),
    ("INTACT HARDWARE RECOVERY",
     "Critical data can ONLY be obtained from examining recovered intact hardware \u2014 "
     "not from telemetry alone. Exos is the only suborbital platform designed to recover "
     "customer hardware fully intact after space-flight conditions.",
     ACCENT_GOLD),
]

for i, (title, body, color) in enumerate(cards):
    x = Inches(0.8) + i * Inches(3.9)
    add_card(slide, x, Inches(2.4), Inches(3.6), Inches(4.2), title, body, color)

add_footer(slide)

# ============================================================
# SLIDE 4 — THE BLK3 PLATFORM
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "THE BLK3 PLATFORM", font_size=32, bold=True, color=WHITE)
add_text_box(slide, Inches(0.8), Inches(1.1), Inches(11), Inches(0.4),
             "Precision Suborbital Reusable Launch Vehicle", font_size=16, color=ACCENT_BLUE)
add_accent_line(slide, Inches(0.8), Inches(1.6), Inches(3))

specs = [
    "\u2022  Suborbital flight profile reaching 100+ km altitude",
    "\u2022  LOX/ethanol propulsion system",
    "\u2022  Multiple flight test articles per mission",
    "\u2022  Vertical launch, parachute recovery, fully reusable",
    "\u2022  Integrated telemetry, tracking, and real-time data return",
    "\u2022  FAA-licensed operations from Spaceport America, NM",
    "\u2022  64+ channel DAQ at 1kHz+ sampling",
    "\u2022  Modular payload bay for diverse customer hardware",
]

add_multi_text(slide, Inches(0.8), Inches(1.9), Inches(5.5), Inches(4), [
    {'text': s, 'size': 13, 'color': LIGHT_GRAY, 'space_after': 6} for s in specs
])

# Customer progression on right
add_text_box(slide, Inches(7), Inches(1.9), Inches(5.5), Inches(0.5),
             "CUSTOMER PROGRAM PROGRESSION", font_size=15, bold=True, color=ACCENT_GOLD)

phases = [
    ("Phase 1", "Test avionics, GNC, flight controls via BLK3 suborbital flights"),
    ("Phase 2", "Iterate \u2014 fly repeatedly until all systems validated"),
    ("Phase 3", "Suborbital proof flight of customer's actual orbital-class vehicle using Exos-developed recovery systems"),
]

for i, (phase, desc) in enumerate(phases):
    y = Inches(2.6) + i * Inches(1.4)
    add_card(slide, Inches(7), y, Inches(5.5), Inches(1.2), phase, desc, ACCENT_BLUE)

add_text_box(slide, Inches(7), Inches(6.2), Inches(5.5), Inches(0.6),
             "The endgame: Customers graduate from testing subsystems to flying their own orbital vehicle suborbitally \u2014 recovering it intact \u2014 before committing to full orbital flight.",
             font_size=11, color=ACCENT_GOLD, bold=True)

add_footer(slide)

# ============================================================
# SLIDE 5 — COMPETITIVE MOAT
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "COMPETITIVE MOAT", font_size=32, bold=True, color=WHITE)
add_text_box(slide, Inches(0.8), Inches(1.1), Inches(11), Inches(0.4),
             "Why Exos Is Defensible", font_size=16, color=ACCENT_BLUE)
add_accent_line(slide, Inches(0.8), Inches(1.6), Inches(3))

moat_data = [
    ["Advantage", "Detail"],
    ["FAA Reusable Launch License", "One of only 3 companies in the U.S. Renewed March 2026. Multi-year, multi-site."],
    ["Only Active Commercial Operator", "The only licensed provider currently flying and offering wet-lease flight test services"],
    ["20+ Year Flight Heritage", "Armadillo Aerospace (2000) \u2192 Exos Aerospace (2014). X-Prize, Lunar Lander Challenge, BLK3"],
    ["Intact Hardware Recovery", "No other suborbital platform recovers customer hardware intact from space-flight conditions"],
    ["Silent Operations Model", "Confidential test campaigns \u2014 no other provider offers this systematically"],
    ["TRL-9 Lunar Tank Technology", "Scorpius Type 5 tanks flew on Odysseus and Athena lunar missions"],
    ["Active DoD Contracts", "USAF SBIR Phase II (FA9300-25-C-6022) \u2014 RDRE propulsion flight demo"],
    ["Dual Revenue Streams", "Launch services + tank manufacturing = diversified, not single-product"],
]

make_table(slide, Inches(0.8), Inches(1.9), Inches(11.5), moat_data,
           col_widths=[Inches(3.5), Inches(8.0)])

add_footer(slide)

# ============================================================
# SLIDE 6 — SCORPIUS ACQUISITION
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "STRATEGIC ACQUISITION: SCORPIUS TYPE 5 TANKS", font_size=28, bold=True, color=WHITE)
add_text_box(slide, Inches(0.8), Inches(1.1), Inches(11), Inches(0.4),
             "World's only TRL-9 cryogenic tank technology \u2014 deployed to the lunar surface",
             font_size=16, color=ACCENT_GOLD, bold=True)
add_accent_line(slide, Inches(0.8), Inches(1.6), Inches(3))

# Left: tank advantages
advantages = [
    "\u2022  ~50% mass reduction vs. metal tanks",
    "\u2022  All-composite, corrosion-resistant, export-approved",
    "\u2022  Room-temperature cure \u2014 no autoclaves required",
    "\u2022  Enables LOX-methane and advanced propellants",
    "\u2022  Proprietary trade secret manufacturing process",
]

add_multi_text(slide, Inches(0.8), Inches(1.9), Inches(5.5), Inches(3), [
    {'text': 'TANK ADVANTAGES', 'size': 14, 'bold': True, 'color': ACCENT_BLUE, 'space_after': 10},
] + [
    {'text': s, 'size': 12, 'color': LIGHT_GRAY, 'space_after': 6} for s in advantages
])

# Right: the arbitrage table
arb_data = [
    ["Metric", "Value"],
    ["Acquisition price", "$3.5M (incl. debt retirement)"],
    ["Conservative IP valuation", "$40\u201380M standalone"],
    ["Arbitrage multiple", "10\u201320x"],
    ["Key customer", "Intuitive Machines ($3.2B mkt cap)"],
    ["Additional targets", "SpaceX, NGC, NASA Artemis"],
    ["Terms", "$2.5M close + $1M milestone at 6 mo."],
    ["Current ownership", "Exos is existing 18% owner"],
]

make_table(slide, Inches(6.8), Inches(1.9), Inches(5.8), arb_data,
           col_widths=[Inches(2.3), Inches(3.5)])

add_text_box(slide, Inches(0.8), Inches(5.5), Inches(11.5), Inches(1.2),
             "Scorpius Type 5 composite-overwrapped cryogenic tanks served as fuel and LOX tanks on Intuitive Machines' "
             "Odysseus (IM-1) and Athena (IM-2) lunar missions \u2014 launched aboard SpaceX Falcon 9, funded by NASA CLPS.",
             font_size=12, color=LIGHT_GRAY)

add_footer(slide)

# ============================================================
# SLIDE 7 — MARKET SIZE & TRACTION
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "MARKET SIZE & TRACTION", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

mkt_data = [
    ["Market Segment", "Size by 2030", "Source"],
    ["Suborbital Flight Test Services", "$1.5\u20132.5B", "NSR, FAA AST, Bryce Tech"],
    ["Cryogenic Tank Production (Space)", "$2\u20134B", "In-space refueling + lunar demand"],
    ["Advanced Propulsion Systems", "$1\u20132B", "RDRE/detonation programs DoD/NASA"],
    ["Total Serviceable Market", "$4.5\u20138.5B", ""],
]

make_table(slide, Inches(0.8), Inches(1.5), Inches(11.5), mkt_data,
           col_widths=[Inches(4.5), Inches(2.5), Inches(4.5)])

add_text_box(slide, Inches(0.8), Inches(3.8), Inches(5), Inches(0.4),
             "CURRENT TRACTION", font_size=15, bold=True, color=ACCENT_GOLD)

traction = [
    "\u2022  Exos FY2025 Revenue: $1.55M (102% CAGR over 4 years)",
    "\u2022  Exos contract revenue Sept 2025 \u2013 July 2026: $1.9M",
    "\u2022  Scorpius revenue (pro forma): $3.1M for Sept 2025 \u2013 Sept 2026",
    "\u2022  Combined pro forma annual run-rate: ~$5M",
]

add_multi_text(slide, Inches(0.8), Inches(4.3), Inches(5.5), Inches(2.5), [
    {'text': t, 'size': 13, 'color': LIGHT_GRAY, 'space_after': 6} for t in traction
])

# Pipeline
add_text_box(slide, Inches(7), Inches(3.8), Inches(5), Inches(0.4),
             "GOVERNMENT PIPELINE", font_size=15, bold=True, color=ACCENT_GOLD)

pipeline = [
    "\u2022  USAF SBIR Phase II \u2014 HVRR-RDRE (FA9300-25-C-6022)",
    "\u2022  TACFI ($4M) \u2014 RDRE development ($2M DoD + $2M match)",
    "\u2022  STRATFI ($30M) \u2014 follow-on, RDRE operational engine",
    "\u2022  Active NASA relationships via Scorpius heritage",
]

add_multi_text(slide, Inches(7), Inches(4.3), Inches(5.5), Inches(2.5), [
    {'text': t, 'size': 13, 'color': LIGHT_GRAY, 'space_after': 6} for t in pipeline
])

add_text_box(slide, Inches(0.8), Inches(6.5), Inches(11), Inches(0.4),
             "Scorpius revenue shown pro forma pending acquisition close. Not yet consolidated Exos revenue.",
             font_size=10, color=MED_GRAY, italic=True)

add_footer(slide)

# ============================================================
# SLIDE 8 — REVENUE GROWTH: HISTORICAL
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "REVENUE GROWTH \u2014 HISTORICAL", font_size=32, bold=True, color=WHITE)
add_text_box(slide, Inches(0.8), Inches(1.1), Inches(11), Inches(0.4),
             "Consistently Doubling Revenue \u2014 102% CAGR", font_size=18, color=ACCENT_GREEN, bold=True)
add_accent_line(slide, Inches(0.8), Inches(1.6), Inches(3))

# Revenue bars (visual representation)
revenues = [
    ("2022", 0.19, "$0.19M"),
    ("2023", 0.31, "$0.31M"),
    ("2024", 0.63, "$0.63M"),
    ("2025", 1.55, "$1.55M"),
]

max_bar = 8.0  # max bar width in inches
max_rev = 1.55

for i, (year, val, label) in enumerate(revenues):
    y = Inches(2.2) + i * Inches(1.2)
    bar_w = Inches(val / max_rev * max_bar)

    # Year label
    add_text_box(slide, Inches(0.8), y, Inches(1.2), Inches(0.5),
                 year, font_size=20, bold=True, color=WHITE)

    # Bar
    bar = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.2), y + Pt(4), bar_w, Inches(0.4)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT_BLUE
    bar.line.fill.background()

    # Value label
    add_text_box(slide, Inches(2.4) + bar_w, y, Inches(2), Inches(0.5),
                 label, font_size=18, bold=True, color=ACCENT_GOLD)

# Profitability box
add_card(slide, Inches(7), Inches(5.0), Inches(5.5), Inches(1.6),
         "FIRST PROFITABLE YEAR \u2014 2025",
         "Revenue: $1.55M\nEBITDA: $0.26M (17% margin)\nNet Income: $0.20M\n\nFinancial figures subject to audit confirmation.",
         ACCENT_GREEN)

add_footer(slide)

# ============================================================
# SLIDE 9 — REVENUE SCALING: PROJECTED
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "REVENUE SCALING \u2014 PROJECTED", font_size=32, bold=True, color=WHITE)
add_text_box(slide, Inches(0.8), Inches(1.1), Inches(11), Inches(0.4),
             "Government backbone + commercial fleet scaling \u2014 ~140% CAGR",
             font_size=16, color=ACCENT_BLUE)
add_accent_line(slide, Inches(0.8), Inches(1.6), Inches(3))

rev_data = [
    ["Year", "BLK4 Commercial", "Scorpius", "TACFI/STRATFI", "Other Gov/Svc", "Combined", "YoY"],
    ["2025A", "\u2014", "\u2014", "\u2014", "$1.55M", "$1.55M", "146%"],
    ["2026E", "\u2014", "$2.65M", "$0.7M", "$1.1M", "$4.4M", "184%"],
    ["2027E", "\u2014", "$3.5M", "$2.7M", "\u2014", "$6.2M", "41%"],
    ["2028E", "$9.8M", "$7.0M", "$8.2M", "\u2014", "$25M", "303%"],
    ["2029E", "$31M", "$14M", "$10M", "\u2014", "$55M", "120%"],
    ["2030E", "$82M", "$28M", "$10M", "\u2014", "$120M", "118%"],
]

make_table(slide, Inches(0.8), Inches(1.9), Inches(11.5), rev_data,
           col_widths=[Inches(1.2), Inches(2.0), Inches(1.5), Inches(2.0),
                       Inches(1.8), Inches(1.5), Inches(1.5)])

# Unit economics
add_text_box(slide, Inches(0.8), Inches(5.2), Inches(5.5), Inches(0.4),
             "UNIT ECONOMICS", font_size=14, bold=True, color=ACCENT_GOLD)

units = [
    "\u2022  BLK4 vehicle sale: $6M/unit, 50%+ gross margin",
    "\u2022  BLK4 wet-lease flight: $3.75M/flight, 60%+ margin",
    "\u2022  Tank manufacturing: $200K\u2013$1M/unit, 45%+ margin",
    "\u2022  TACFI/STRATFI: 30% margin (70% COGS for gov't dev)",
]

add_multi_text(slide, Inches(0.8), Inches(5.6), Inches(5.5), Inches(2), [
    {'text': t, 'size': 12, 'color': LIGHT_GRAY, 'space_after': 4} for t in units
])

add_text_box(slide, Inches(0.8), Inches(6.8), Inches(11), Inches(0.3),
             "Forward-looking projections from March 2026. Actuals through February 2026. See disclaimers on final slide.",
             font_size=9, color=MED_GRAY, italic=True)

add_footer(slide)

# ============================================================
# SLIDE 10 — USE OF FUNDS
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "USE OF FUNDS & FINANCIAL PERFORMANCE", font_size=28, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

add_text_box(slide, Inches(0.8), Inches(1.4), Inches(11), Inches(0.4),
             "$10M raised \u2014 100% deployed, zero idle capital",
             font_size=18, color=ACCENT_GOLD, bold=True)

uof_data = [
    ["Allocation", "Amount", "Purpose"],
    ["Scorpius Acquisition", "$3.5M", "10\u201320x value on IP alone. Binding agreement."],
    ["RDRE Development (TACFI match)", "$2M", "Match for $4M TACFI. Unlocks $30M STRATFI."],
    ["BLK3 Vehicle Build", "$2.5M", "2nd vehicle. Dual-site ops. Doubles capacity."],
    ["Listing + Working Capital", "$2M", "Public listing costs + operational buffer."],
]

make_table(slide, Inches(0.8), Inches(2.0), Inches(11.5), uof_data,
           col_widths=[Inches(3.5), Inches(1.5), Inches(6.5)])

add_card(slide, Inches(0.8), Inches(4.2), Inches(11.5), Inches(0.8),
         "CAPITAL AMPLIFICATION",
         "$10M private capital unlocks $34M in government co-investment (TACFI + STRATFI) \u2014 a 3.4x multiplier on investor capital.",
         ACCENT_GREEN)

# Financial performance table
fin_data = [
    ["Metric", "CY2026", "CY2027", "CY2028", "CY2029", "CY2030"],
    ["Revenue", "$4.4M", "$6.2M", "$25M", "$55M", "$120M"],
    ["Gross Margin", "42%", "40%", "50%", "55%", "57%"],
    ["EBITDA", "$0.3M", "$0.4M", "$4M", "$14M", "$38M"],
    ["EBITDA Margin", "7%", "6%", "16%", "25%", "32%"],
    ["Net Income", "$0", "$0", "$2M", "$9M", "$28M"],
]

make_table(slide, Inches(0.8), Inches(5.3), Inches(11.5), fin_data,
           col_widths=[Inches(2.0), Inches(1.9), Inches(1.9), Inches(1.9), Inches(1.9), Inches(1.9)])

add_footer(slide)

# ============================================================
# SLIDE 11 — MANAGEMENT TEAM
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "MANAGEMENT TEAM", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

team = [
    ("JOHN QUINN \u2014 CEO & Co-Founder",
     "14.5-year U.S. Navy Submarine Service career\n"
     "$43M ROI in Six Sigma projects at FPL\n"
     "Company IP sale to Emerson Power\n"
     "Drives strategy, capital markets, government relations"),
    ("DAVID MITCHELL \u2014 President & Co-Founder",
     "4th-generation energy entrepreneur and investor\n"
     "Secured private funding enabling Exos to build commercial-grade reusable rockets\n"
     "Company sale to CITS\n"
     "Drives financing, corporate development, investor relations"),
    ("RUSSEL BLINK \u2014 CTO & Co-Founder",
     "BS EE, Michigan Technological University\n"
     "TI Defense \u2192 Long Range Systems (VP/Co-founder) \u2192 Armadillo Aerospace (VP Eng)\n"
     "Hundreds of engines, dozens of flying vehicles incl. NASA Lunar Landers"),
    ("NEIL MILBURN \u2014 COO & Co-Founder",
     "Chemical Engineering; co-founded Armadillo Aerospace (2000)\n"
     "Revolutionized CNG refueling at NASA launch facilities\n"
     "FAA liaison; company turnarounds and operational excellence"),
    ("KYLE BALLARD \u2014 CFO",
     "Financial operations, reporting, due diligence\n"
     "Leading SSLC financial analysis and public listing preparation"),
]

for i, (name, bio) in enumerate(team):
    col = i % 3
    row = i // 3
    x = Inches(0.8) + col * Inches(4.0)
    y = Inches(1.6) + row * Inches(2.8)
    add_card(slide, x, y, Inches(3.7), Inches(2.5), name, bio, ACCENT_BLUE)

add_footer(slide)

# ============================================================
# SLIDE 12 — OWNERSHIP & GOVERNANCE
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "OWNERSHIP & GOVERNANCE", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

own_data = [
    ["Shareholder", "Stake", "Role"],
    ["David Mitchell", "37%", "President, Co-founder"],
    ["John Quinn", "21%", "CEO, Co-founder"],
    ["EAI (accredited investors)", "37%", "Hundreds of investors, 10 years of private funding"],
    ["Incentive Stock Option Pool", "5%", "Key employee retention"],
]

make_table(slide, Inches(0.8), Inches(1.5), Inches(5.5), own_data,
           col_widths=[Inches(2.5), Inches(1.0), Inches(2.0)])

post_data = [
    ["Shareholder", "Post-Listing", "Status"],
    ["David Mitchell", "~33%", "Active management"],
    ["John Quinn", "~19%", "Active management"],
    ["EAI investors", "~33%", "NOW LIQUID \u2014 structured sell-down"],
    ["ESOP", "~4.5%", "Vesting"],
    ["New investors", "~11%", "Public market entry"],
]

make_table(slide, Inches(7), Inches(1.5), Inches(5.5), post_data,
           col_widths=[Inches(2.2), Inches(1.3), Inches(2.0)])

governance = [
    "\u2022  Mitchell + Quinn retain 56% effective control",
    "\u2022  EAI investors get first liquidity event in 10 years",
    "\u2022  Structured lock-up: 6\u201312 months, quarterly tranche sell-down",
    "\u2022  Delaware HoldCo structure for ITAR isolation",
    "\u2022  US subsidiary maintains all controlled technology and contracts",
]

add_multi_text(slide, Inches(0.8), Inches(4.8), Inches(11), Inches(2.5), [
    {'text': 'KEY GOVERNANCE', 'size': 14, 'bold': True, 'color': ACCENT_GOLD, 'space_after': 8},
] + [
    {'text': g, 'size': 12, 'color': LIGHT_GRAY, 'space_after': 4} for g in governance
])

add_footer(slide)

# ============================================================
# SLIDE 13 — CORPORATE STRUCTURE & LISTING
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "CORPORATE STRUCTURE & LISTING PATH", font_size=28, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

# Structure diagram using cards
add_card(slide, Inches(3.5), Inches(1.6), Inches(6), Inches(1.0),
         "EXOS AEROSPACE HOLDINGS (Delaware HoldCo)",
         "Public listing vehicle", ACCENT_GOLD)

add_card(slide, Inches(4), Inches(3.0), Inches(5.5), Inches(1.2),
         "EXOS AEROSPACE SYSTEMS & TECHNOLOGIES INC (Delaware)",
         "All ITAR-controlled operations | FAA license holder | Government contracts", ACCENT_BLUE)

add_card(slide, Inches(4.5), Inches(4.6), Inches(5), Inches(1.0),
         "SCORPIUS SPACE LAUNCH COMPANY INC",
         "Cryo tank IP, manufacturing, lunar heritage", ACCENT_GREEN)

# Listing options
add_text_box(slide, Inches(0.8), Inches(5.8), Inches(5.5), Inches(0.4),
             "LISTING VENUE UNDER EVALUATION", font_size=14, bold=True, color=ACCENT_GOLD)

venues = [
    "\u2022  Texas Stock Exchange (TXSE) \u2014 emerging U.S. small-cap exchange",
    "\u2022  Euronext Growth Dublin \u2014 EU defense capital, English-language",
    "\u2022  Reg A+ Tier 2 \u2192 NYSE American",
    "\u2022  OTCQB as interim stepping stone",
]

add_multi_text(slide, Inches(0.8), Inches(6.1), Inches(5.5), Inches(1.5), [
    {'text': v, 'size': 11, 'color': LIGHT_GRAY, 'space_after': 3} for v in venues
])

# Timeline
add_text_box(slide, Inches(7), Inches(5.8), Inches(5.5), Inches(0.4),
             "TIMELINE FROM INVESTMENT CLOSE", font_size=14, bold=True, color=ACCENT_GOLD)

timeline = [
    "\u2022  Aug\u2013Oct 2026: Capital deployed + Scorpius close",
    "\u2022  Nov 2026\u2013Jan 2027: Listing prep + regulatory",
    "\u2022  Q1\u2013Q2 2027: Admission to trading",
]

add_multi_text(slide, Inches(7), Inches(6.1), Inches(5.5), Inches(1.5), [
    {'text': t, 'size': 11, 'color': LIGHT_GRAY, 'space_after': 3} for t in timeline
])

add_footer(slide)

# ============================================================
# SLIDE 14 — COMPARABLE VALUATIONS
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "COMPARABLE VALUATIONS", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

comp_data = [
    ["Company", "Exchange", "Market Cap", "Revenue", "Multiple", "Notes"],
    ["Rocket Lab (RKLB)", "NASDAQ", "$12B", "$436M", "27x", "Orbital, M&A-driven"],
    ["Intuitive Machines (LUNR)", "NASDAQ", "$3.2B", "$227M", "14x", "Uses Scorpius tanks"],
    ["Spire Global (SPIR)", "NYSE", "$600M", "$110M", "5x", "Space data/analytics"],
    ["Mynaric (MYNA)", "NASDAQ", "$180M", "$40M", "4.5x", "Laser comms"],
    ["Virgin Galactic (SPCE)", "NYSE", "$320M", "$2M", "\u2014", "Suborbital tourism"],
]

make_table(slide, Inches(0.5), Inches(1.5), Inches(12.3), comp_data,
           col_widths=[Inches(2.5), Inches(1.5), Inches(1.8), Inches(1.5), Inches(1.5), Inches(3.5)])

add_card(slide, Inches(0.8), Inches(4.2), Inches(5.5), Inches(1.5),
         "EXOS VALUATION: $100\u2013150M ENTERPRISE VALUE",
         "4\u20136x 2028E combined revenue ($25M)\nIn line with peers when adjusted for growth rate\nCY2028 is first year of full commercial operations",
         ACCENT_GOLD)

add_card(slide, Inches(6.8), Inches(4.2), Inches(5.5), Inches(1.5),
         "WHY EXOS IS NOT VIRGIN GALACTIC",
         "\u2022 Sells to gov't/defense (contracted, recurring)\n"
         "\u2022 Already profitable \u2014 SPCE never has been\n"
         "\u2022 Owns irreplaceable IP (Scorpius + RDRE)\n"
         "\u2022 $34M gov't funding pipeline = revenue floor",
         ACCENT_GREEN)

add_footer(slide)

# ============================================================
# SLIDE 15 — WHY NOW? MARKET TIMING
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "WHY NOW? MARKET TIMING", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

catalysts = [
    ("SPACEX IPO (2026\u20132027)", ACCENT_BLUE,
     "The largest space sector event in history. Creates massive retail "
     "and institutional interest in anything space-adjacent. A publicly "
     "listed Exos captures investor allocation from those seeking "
     "diversified space exposure beyond SpaceX."),
    ("DEFENSE SPENDING SURGE", ACCENT_GOLD,
     "NATO nations committed to 2%+ GDP on defense. U.S. and allied "
     "governments actively seeking domestic defense/space capabilities. "
     "Exos provides flight test infrastructure that supports national "
     "security objectives."),
    ("IN-SPACE REFUELING MARKET", ACCENT_GREEN,
     "SpaceX Starship depot, NASA Artemis architecture, commercial space "
     "stations \u2014 all require cryogenic storage solutions. Scorpius is "
     "the only TRL 9 technology available commercially. Market timing is "
     "ideal for this acquisition."),
]

for i, (title, color, body) in enumerate(catalysts):
    x = Inches(0.8) + i * Inches(4.0)
    add_card(slide, x, Inches(1.6), Inches(3.7), Inches(5.0), title, body, color)

add_footer(slide)

# ============================================================
# SLIDE 16 — MILESTONES & HERITAGE
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "MILESTONES & HERITAGE", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

milestones = [
    ["Year", "Milestone"],
    ["2000", "Armadillo Aerospace founded by John Carmack"],
    ["2006", "Lunar Lander Challenge \u2014 1st Place"],
    ["2008\u20132009", "NASA Morpheus contract, Rocket Racing League"],
    ["2010", "STIG Rocket flies to 95km"],
    ["2014", "Exos Aerospace continues with new management"],
    ["2018\u20132019", "4 launches and 3 recoveries on 1st SARGE vehicle"],
    ["2023", "USAF SBIR Phase II \u2014 HVRR-RDRE contract awarded"],
    ["2025", "First profitable year ($1.55M revenue, 17% EBITDA)"],
    ["2026", "FAA license renewed; Scorpius acquisition; TACFI; $10M Series A"],
    ["2028", "BLK4 enters commercial service; STRATFI; dual-vehicle ops"],
    ["2030", "Target: $120M revenue, BLK4 fleet at scale"],
]

make_table(slide, Inches(0.8), Inches(1.5), Inches(11.5), milestones,
           col_widths=[Inches(2.0), Inches(9.5)])

add_text_box(slide, Inches(0.8), Inches(6.5), Inches(11), Inches(0.4),
             "Our competitive advantage is demonstrated by what our team has already done.",
             font_size=16, bold=True, color=ACCENT_GOLD)

add_footer(slide)

# ============================================================
# SLIDE 17 — RISK FACTORS
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "RISK FACTORS & MITIGATION", font_size=32, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

risk_data = [
    ["Risk", "Mitigation"],
    ["Regulatory (ITAR, FAA)", "15+ year compliance track record; ITAR counsel; HoldCo isolation"],
    ["Scorpius integration", "Exos is existing 18% owner; team/operations already familiar"],
    ["Technology (RDRE)", "SBIR Phase II funded; failure doesn't affect core business"],
    ["Market liquidity post-listing", "Market maker appointed; EAI sell-down provides volume"],
    ["Single customer dependency", "Diversified: DoD, NASA, 3 defense primes, commercial, university"],
    ["Key person risk", "D&O insurance; COO operational; 50+ years combined exec experience"],
    ["BLK4 timeline", "18\u201324 mo. development in projections; CY2026\u20132027 revenue not BLK4 dependent"],
]

make_table(slide, Inches(0.8), Inches(1.5), Inches(11.5), risk_data,
           col_widths=[Inches(3.5), Inches(8.0)])

add_footer(slide)

# ============================================================
# SLIDE 18 — THE ASK
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "THE ASK", font_size=40, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.3), Inches(3))

add_text_box(slide, Inches(0.8), Inches(1.6), Inches(11), Inches(0.5),
             "EXOS AEROSPACE \u2014 Licensed Reusable Launch | Lunar-Proven Technology | Profitable",
             font_size=16, color=ACCENT_BLUE, bold=True)

ask_data = [
    ["", ""],
    ["Raising", "$10M Series A"],
    ["Revenue Trajectory", "$4.4M (2026) \u2192 $6.2M \u2192 $25M \u2192 $55M \u2192 $120M (2030)"],
    ["Reusable Launch License", "One of only three U.S. companies"],
    ["TRL-9 Technology", "Scorpius fuel tanks operating on the Moon"],
    ["Gov't Co-Investment", "$34M TACFI/STRATFI pipeline \u2014 3.4x multiplier"],
    ["Profitability", "EBITDA-positive since 2025 \u2014 17% margin"],
]

make_table(slide, Inches(0.8), Inches(2.2), Inches(11.5), ask_data,
           col_widths=[Inches(3.5), Inches(8.0)])

# $10M enables
add_text_box(slide, Inches(0.8), Inches(5.0), Inches(5.5), Inches(0.4),
             "$10M ENABLES:", font_size=14, bold=True, color=ACCENT_GOLD)

enables = [
    "\u2022  Scorpius acquisition ($3.5M in negotiation)",
    "\u2022  TACFI match \u2192 unlocks $30M STRATFI",
    "\u2022  BLK4 commercial fleet development",
    "\u2022  Public listing (exchange TBD)",
]

add_multi_text(slide, Inches(0.8), Inches(5.4), Inches(5.5), Inches(1.5), [
    {'text': e, 'size': 12, 'color': LIGHT_GRAY, 'space_after': 3} for e in enables
])

# Next steps
add_text_box(slide, Inches(7), Inches(5.0), Inches(5.5), Inches(0.4),
             "NEXT STEPS:", font_size=14, bold=True, color=ACCENT_GOLD)

steps = [
    "1.  Review this materials package and financial model",
    "2.  Sign NDA for data room access",
    "3.  Management presentation (in person or virtual)",
    "4.  Confirm investment structure and timeline",
]

add_multi_text(slide, Inches(7), Inches(5.4), Inches(5.5), Inches(1.5), [
    {'text': s, 'size': 12, 'color': LIGHT_GRAY, 'space_after': 3} for s in steps
])

# Contact
add_card(slide, Inches(3.5), Inches(6.3), Inches(6), Inches(0.6),
         "John Quinn, CEO  |  jquinnexo@pm.me  |  Exos Aerospace Systems & Technologies, Inc.",
         "", ACCENT_BLUE)

add_footer(slide)

# ============================================================
# SLIDE 19 — DISCLAIMERS
# ============================================================
slide = prs.slides.add_slide(blank_layout)
add_bg(slide)

add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
             "IMPORTANT DISCLAIMERS", font_size=28, bold=True, color=WHITE)
add_accent_line(slide, Inches(0.8), Inches(1.2), Inches(3))

disclaimers = [
    {'text': 'PRIVATE & CONFIDENTIAL', 'size': 12, 'bold': True, 'color': ACCENT_BLUE, 'space_after': 4},
    {'text': 'This presentation is provided for informational purposes only to selected potential investors and does not '
             'constitute an offer to sell or a solicitation of an offer to buy any securities of Exos Aerospace Systems & '
             'Technologies, Inc. or any affiliated entity.',
     'size': 9, 'color': LIGHT_GRAY, 'space_after': 12},

    {'text': 'FORWARD-LOOKING STATEMENTS', 'size': 12, 'bold': True, 'color': ACCENT_BLUE, 'space_after': 4},
    {'text': 'This presentation contains forward-looking statements within the meaning of applicable securities laws. '
             'These statements involve known and unknown risks, uncertainties, and other factors that may cause actual results '
             'to differ materially. Forward-looking statements include projections of revenue, earnings, capital expenditures, '
             'market size, product development timelines, and business strategy. Risk factors include: delays in vehicle development; '
             'failure to close the Scorpius acquisition; loss of government contracts; regulatory changes; competition; inability to '
             'raise additional capital; technology risks; and general economic conditions.',
     'size': 9, 'color': LIGHT_GRAY, 'space_after': 12},

    {'text': 'NO ASSURANCE', 'size': 12, 'bold': True, 'color': ACCENT_BLUE, 'space_after': 4},
    {'text': 'There can be no assurance that any projections or forward-looking statements will be realized. Past performance '
             'is not indicative of future results. Investors should conduct their own due diligence.',
     'size': 9, 'color': LIGHT_GRAY, 'space_after': 12},

    {'text': 'EXPORT CONTROL NOTICE', 'size': 12, 'bold': True, 'color': ACCENT_BLUE, 'space_after': 4},
    {'text': 'Exos Aerospace maintains full compliance with ITAR and EAR. All controlled technical data and government '
             'contract work are performed exclusively by U.S. persons within U.S. facilities. This presentation does not '
             'contain controlled technical data. Any international structure maintains full compliance with appropriate isolation.',
     'size': 9, 'color': LIGHT_GRAY, 'space_after': 12},

    {'text': 'CONFIDENTIALITY', 'size': 12, 'bold': True, 'color': ACCENT_BLUE, 'space_after': 4},
    {'text': 'This presentation and its contents are strictly confidential. Recipients may not reproduce, distribute, or '
             'disclose without prior written consent. All financial figures are management estimates unless otherwise noted. '
             'Audited statements will be prepared in connection with the listing process.',
     'size': 9, 'color': LIGHT_GRAY, 'space_after': 8},

    {'text': 'Exos Aerospace Systems & Technologies, Inc. | Greenville, TX | May 2026',
     'size': 10, 'color': MED_GRAY, 'italic': True, 'space_after': 0},
]

add_multi_text(slide, Inches(0.8), Inches(1.5), Inches(11.5), Inches(5.5), disclaimers)

add_footer(slide)

# ============================================================
# SAVE
# ============================================================
prs.save(OUT)
print(f"Saved: {OUT}")
print(f"Slides: {len(prs.slides)}")
