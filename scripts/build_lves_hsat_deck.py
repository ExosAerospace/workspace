#!/usr/bin/env python3
"""Build the AIAA LVES TC short deck for HSAT 2026 (Midland, Nov 11-13).

Content sources: drafts/LVES_Round1_Survey_Summary_Report_2026-10-04.docx (survey data),
Starfighters Space HSAT 2026 announcement, highspeedflight.com (event/portal scope).
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION

OUT = "/Users/exomac/.openclaw/workspace/drafts/AIAA_LVES_TC_HSAT2026_Brief_DRAFT_2026-10-08.pptx"

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
BLUE = RGBColor(0x1F, 0x5F, 0xA8)
SKY = RGBColor(0x8F, 0xB8, 0xE8)
ORANGE = RGBColor(0xE0, 0x7A, 0x1F)
GREY = RGBColor(0x5A, 0x64, 0x70)
LIGHT = RGBColor(0xF2, 0xF5, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W = prs.slide_width


def box(slide, x, y, w, h, fill=None, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1)
    s.shadow.inherit = False
    return s


def text(slide, x, y, w, h, runs, size=18, color=NAVY, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=6):
    """runs: str or list of paragraphs; each paragraph str or (str, dict(overrides))."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    paras = runs if isinstance(runs, list) else [runs]
    for i, p in enumerate(paras):
        t, o = (p, {}) if isinstance(p, str) else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = o.get("align", align)
        para.space_after = Pt(o.get("spacing", spacing))
        r = para.add_run(); r.text = t
        r.font.size = Pt(o.get("size", size)); r.font.bold = o.get("bold", bold)
        r.font.color.rgb = o.get("color", color); r.font.name = "Calibri"
    return tb


def header(slide, title, kicker=None):
    box(slide, 0, 0, W, Inches(0.12), fill=BLUE)
    if kicker:
        text(slide, Inches(0.6), Inches(0.35), Inches(12), Inches(0.4), kicker.upper(),
             size=12, color=ORANGE, bold=True)
    text(slide, Inches(0.6), Inches(0.65), Inches(12.2), Inches(0.9), title, size=30, bold=True)
    footer(slide)


def footer(slide):
    text(slide, Inches(0.6), Inches(7.0), Inches(9), Inches(0.35),
         "AIAA Launch Vehicles and Entry Systems (LVES) Technical Committee  ·  HSAT 2026, Midland, TX",
         size=10, color=GREY)
    text(slide, Inches(10.2), Inches(7.0), Inches(2.5), Inches(0.35),
         "DRAFT — for Chair review", size=10, color=ORANGE, bold=True, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, title, body, accent=BLUE, body_size=15):
    box(slide, x, y, w, h, fill=LIGHT)
    box(slide, x, y, Inches(0.08), h, fill=accent)
    text(slide, x + Inches(0.25), y + Inches(0.15), w - Inches(0.4), Inches(0.5), title,
         size=18, bold=True, color=accent)
    text(slide, x + Inches(0.25), y + Inches(0.65), w - Inches(0.4), h - Inches(0.75),
         body, size=body_size, color=NAVY, spacing=5)


def notes(slide, s):
    slide.notes_slide.notes_text_frame.text = s


# 1 — Title
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, W, prs.slide_height, fill=NAVY)
box(s, Inches(0.6), Inches(2.2), Inches(1.2), Inches(0.08), fill=ORANGE)
text(s, Inches(0.6), Inches(1.4), Inches(12), Inches(0.6), "AIAA TECHNICAL COMMITTEE BRIEF",
     size=14, color=SKY, bold=True)
text(s, Inches(0.6), Inches(2.45), Inches(12), Inches(1.9),
     ["Reusable Launch & Entry:", "Where High-Speed Flight Meets Space Access"],
     size=40, color=WHITE, bold=True, spacing=2)
text(s, Inches(0.6), Inches(4.35), Inches(12), Inches(0.6),
     "AIAA Launch Vehicles and Entry Systems (LVES) Technical Committee",
     size=22, color=SKY)
text(s, Inches(0.6), Inches(5.5), Inches(12), Inches(1.0),
     ["9th High Speed Aerospace Transportation Workshop (HSAT 2026)",
      "Midland International Air & Space Port, TX  ·  November 11–13, 2026",
      ("Presenter: ______________________ (John Vinson, Vice Chair  |  John Quinn, Member)",
       {"color": ORANGE, "size": 14})],
     size=16, color=WHITE, spacing=3)
notes(s, "Open: thank InterFlight Global / High Speed Flight and Starfighters Space (host). "
         "Purpose of this short brief: introduce the new AIAA LVES TC to the HSAT community, show "
         "where our scope and the high-speed-flight community overlap, and invite participation "
         "ahead of a fuller HSAT track in 2027. ~10 minutes.")

# 2 — Who we are
s = prs.slides.add_slide(BLANK)
header(s, "A new AIAA committee for reusable launch and entry", "Who we are")
box(s, Inches(0.6), Inches(1.75), Inches(12.1), Inches(1.55), fill=NAVY)
text(s, Inches(0.9), Inches(1.85), Inches(11.6), Inches(1.4),
     "“A non-competitive forum to advance safe, reliable, cost-effective and reusable launch and "
     "entry systems across the full mission cycle — ascent through entry and recovery — by exchanging "
     "technical information, producing roadmaps and lessons learned, informing policy and regulation, "
     "and engaging the next-generation workforce.”",
     size=18, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
text(s, Inches(0.9), Inches(3.3), Inches(11), Inches(0.4),
     "Draft Purpose statement, synthesized from Round 1 member survey", size=11, color=GREY)
card(s, Inches(0.6), Inches(3.9), Inches(3.9), Inches(2.85), "Leadership",
     ["Ritesh Ghimire — Chair", "John Vinson — Vice Chair",
      "Members across commercial launch, academia (U.S. + international), FFRDCs, and senior practitioners"])
card(s, Inches(4.7), Inches(3.9), Inches(3.9), Inches(2.85), "Where we are",
     ["Round 1 member survey complete (13 respondents)", "Draft charter in assembly",
      "Round 2 ranking pass to settle remaining boundaries"], accent=ORANGE)
card(s, Inches(8.8), Inches(3.9), Inches(3.9), Inches(2.85), "How we work",
     ["Quarterly meetings (member preference)", "Subcommittees with real deliverables",
      "Standard 3-year term, annual roster review"], accent=BLUE)
notes(s, "LVES is in stand-up. The Purpose statement is the survey synthesis, still draft pending "
         "Chair and member confirmation. Emphasize: non-competitive forum, systems-level, reusability.")

# 3 — Scope: full regime
s = prs.slides.add_slide(BLANK)
header(s, "Scope: the full launch-and-entry flight regime", "What we cover")
phases = [("Ascent", "Boosters & upper stages"), ("Hypersonic", "Rocket-powered high speed"),
          ("Space access", "Orbital / near-space operations"), ("Entry", "Aerothermal & rarefied regimes"),
          ("Recovery", "Descent, landing, turnaround")]
pw, gap, y = Inches(2.3), Inches(0.15), Inches(1.85)
for i, (h, sub) in enumerate(phases):
    x = Inches(0.6) + i * (pw + gap)
    shp = s.shapes.add_shape(MSO_SHAPE.CHEVRON if i else MSO_SHAPE.PENTAGON, x, y, pw, Inches(0.75))
    shp.fill.solid(); shp.fill.fore_color.rgb = BLUE if i % 2 == 0 else NAVY
    shp.line.fill.background(); shp.shadow.inherit = False
    tf = shp.text_frame; tf.clear(); tf.word_wrap = False
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = h; r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = WHITE
    text(s, x, y + Inches(0.8), pw, Inches(0.4), sub, size=12, color=GREY, align=PP_ALIGN.CENTER)
text(s, Inches(0.6), Inches(3.15), Inches(12.1), Inches(0.5),
     "Characterized by physical flow regime — Mach (continuum), Knudsen (rarefied / near-space), "
     "enthalpy (entry) — not capped at a single Mach number.", size=14, color=GREY)
card(s, Inches(0.6), Inches(3.8), Inches(3.9), Inches(2.95), "LVES owns (core)",
     ["Reusable boosters / first stages", "Reusable upper stages", "Entry, descent & recovery systems"])
card(s, Inches(4.7), Inches(3.8), Inches(3.9), Inches(2.95), "Interface with other TCs",
     ["Hypersonic suborbital rockets", "Rocket-powered hypersonic aircraft",
      "Operability, reliability & safety", "Airbreathing hypersonics (Round 2)"], accent=ORANGE)
card(s, Inches(8.8), Inches(3.8), Inches(3.9), Inches(2.95), "Boundary rule",
     ["Discipline TCs own the components.",
      "LVES owns how they integrate into reusable launch & entry systems — and the operational, "
      "safety and regulatory implications."], accent=NAVY)
notes(s, "The interface column is exactly where HSAT lives: rocket-powered high-speed vehicles, "
         "operability and safety. We don't want to duplicate HyTASP or propulsion TCs — we want to "
         "be the system-integration and reusability home that connects to them.")

# 4 — What members said (chart)
s = prs.slides.add_slide(BLANK)
header(s, "What members told us: reusability is the center of gravity", "Round 1 survey")
cd = CategoryChartData()
cats = ["Reusable upper stages", "Reusable boosters / first stages", "Entry, descent & recovery",
        "In-space servicing / logistics", "Airbreathing hypersonics", "Expendable upper stages",
        "Hypersonic suborbital rockets", "Operability / reliability / safety"]
vals = [51, 51, 37, 25, 16, 13, 11, 10]
cd.categories = list(reversed(cats)); cd.add_series("Weighted score", list(reversed(vals)))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.7), Inches(7.6),
                        Inches(5.1), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = False
pl = ch.plots[0]; pl.gap_width = 45; pl.has_data_labels = True
pl.data_labels.font.size = Pt(12); pl.data_labels.font.color.rgb = NAVY
pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
ser = pl.series[0]
for i, pt in enumerate(ser.points):
    pt.format.fill.solid()
    pt.format.fill.fore_color.rgb = BLUE if i >= len(vals) - 3 else SKY
ch.category_axis.tick_labels.font.size = Pt(12); ch.category_axis.tick_labels.font.color.rgb = NAVY
ch.category_axis.format.line.color.rgb = SKY
ch.value_axis.visible = False; ch.value_axis.has_major_gridlines = False
text(s, Inches(0.6), Inches(6.65), Inches(7.6), Inches(0.35),
     "Weighted scope ranking (rank 1 = 5 pts … rank 5 = 1 pt), 13 respondents", size=10, color=GREY)
card(s, Inches(8.5), Inches(1.7), Inches(4.2), Inches(2.75), "Top deliverables (votes)",
     ["Tech roadmap (launch/entry + reusable upper stage) — 12", "STEM / university engagement — 11",
      "Sessions at SciTech / AVIATION / ASCEND — 10", "Lessons learned: operability & safety — 8",
      "Policy / regulatory input — 7"], body_size=12)
card(s, Inches(8.5), Inches(4.6), Inches(4.2), Inches(2.2), "Who's missing",
     ["Government labs (AFRL, NASA centers)", "Commercial recovery / rapid-turnaround operators",
      "Aerothermal & reusable-TPS specialists", "Range & safety; early-career members"],
     accent=ORANGE, body_size=12)
notes(s, "Data: LVES Round 1 Member Survey Summary Report (Oct 4, 2026; 16 submissions, 13 unique "
         "respondents). Note the 'who's missing' list — several of those communities are in this room.")

# 5 — Why HSAT
s = prs.slides.add_slide(BLANK)
header(s, "Why LVES and the HSAT community belong in the same room", "Shared problems")
text(s, Inches(0.6), Inches(1.6), Inches(12.1), Inches(0.6),
     "High Speed Flight covers atmospheric and exo-atmospheric vehicles at Mach 0.9 and above — "
     "the same physics and operational problems reusable launch and entry systems face.",
     size=16, color=GREY)
items = [
    ("Aerothermal & TPS", "Long-life, reusable thermal protection for repeated high-enthalpy exposure."),
    ("Rapid turnaround", "Aircraft-like inspection, maintenance and reflight cadence."),
    ("Operability & safety", "Reliability data and lessons learned across many flights, not one."),
    ("Regulation", "FAA Part 450 for launch/reentry; FAA rulemaking for civil supersonic flight in the NAS."),
    ("Spaceports & airspace", "Integrating high-speed and space operations with conventional traffic."),
    ("Workforce", "Training the engineers who will design, certify and fly reusable vehicles."),
]
cw, chh = Inches(3.95), Inches(2.1)
for i, (t, b) in enumerate(items):
    x = Inches(0.6) + (i % 3) * (cw + Inches(0.12))
    y = Inches(2.4) + (i // 3) * (chh + Inches(0.2))
    card(s, x, y, cw, chh, t, b, accent=BLUE if i % 2 == 0 else ORANGE, body_size=15)
notes(s, "This is the bridge slide. Point-to-point high-speed transport and reusable space access "
         "converge on the same hard problems. HSAT 2026 agenda includes discussion of the FAA's "
         "rulemaking for civil supersonic flight in the NAS (per host announcement); LVES members "
         "flagged Part 450 as a policy priority.")

# 6 — Proposed collaboration
s = prs.slides.add_slide(BLANK)
header(s, "Proposed collaboration: LVES × HSAT", "What we'd like to build")
rows = [
    ("1", "HSAT 2027 track", "An LVES-organized session on reusable launch & entry at the next HSAT "
                             "— planned with the lead time this year's schedule did not allow."),
    ("2", "Roadmap input", "Invite HSAT practitioners to review the LVES launch/entry + reusable-upper-"
                           "stage technology roadmap — especially TPS, turnaround and operability."),
    ("3", "Lessons-learned exchange", "Shared, openly publishable operability and safety lessons from "
                                      "flight-test and high-speed operations."),
    ("4", "Regulatory dialogue", "A common, technically grounded voice on Part 450 and high-speed "
                                 "flight integration in the NAS."),
    ("5", "Recruiting & STEM", "Bring gov labs, operators, TPS specialists and students into LVES; "
                               "connect HSAT universities to LVES STEM work."),
]
y = Inches(1.75)
for n, t, b in rows:
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.6), y + Inches(0.08), Inches(0.6), Inches(0.6))
    c.fill.solid(); c.fill.fore_color.rgb = ORANGE; c.line.fill.background(); c.shadow.inherit = False
    tf = c.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = n; r.font.size = Pt(18); r.font.bold = True; r.font.color.rgb = WHITE
    text(s, Inches(1.45), y, Inches(3.2), Inches(0.8), t, size=19, bold=True, color=NAVY,
         anchor=MSO_ANCHOR.MIDDLE)
    text(s, Inches(4.7), y, Inches(8.0), Inches(0.8), b, size=15, color=GREY, anchor=MSO_ANCHOR.MIDDLE)
    y += Inches(1.0)
notes(s, "Be concrete and modest: LVES is new, so the ask is a 2027 track plus open channels now. "
         "Everything shared through LVES should be openly publishable (non-competitive forum).")

# 7 — Join us
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, W, prs.slide_height, fill=NAVY)
text(s, Inches(0.6), Inches(1.0), Inches(12), Inches(0.5), "GET INVOLVED", size=14, color=ORANGE, bold=True)
text(s, Inches(0.6), Inches(1.5), Inches(12), Inches(1.0),
     "Help shape a new AIAA committee from the start", size=36, color=WHITE, bold=True)
text(s, Inches(0.6), Inches(2.8), Inches(7.2), Inches(3.2),
     ["Join LVES as an AIAA member — subcommittees forming now:",
      ("•  Roadmap & Standards", {"color": SKY}),
      ("•  Reusable Upper Stages / In-Space Logistics", {"color": SKY}),
      ("•  STEM & Workforce", {"color": SKY}),
      "Bring a 2027 HSAT session idea or a roadmap reviewer.",
      "Especially welcome: gov labs, operators, TPS/aerothermal, range & safety, early-career."],
     size=18, color=WHITE, spacing=8)
box(s, Inches(8.3), Inches(2.8), Inches(4.4), Inches(2.9), fill=BLUE)
text(s, Inches(8.55), Inches(2.95), Inches(4.0), Inches(2.7),
     [("Contacts", {"bold": True, "size": 20}),
      "Ritesh Ghimire — Chair", "John Vinson — Vice Chair", "John Quinn — Member",
      ("Email: ______________________", {"color": ORANGE, "size": 15})],
     size=17, color=WHITE, spacing=8)
text(s, Inches(0.6), Inches(6.9), Inches(12), Inches(0.4),
     "AIAA Launch Vehicles and Entry Systems Technical Committee  ·  DRAFT — for Chair review",
     size=10, color=SKY)
notes(s, "Close with the ask. Fill the contact line with whichever address the Chair prefers "
         "for public distribution before presenting.")

# 8 — Sources (backup)
s = prs.slides.add_slide(BLANK)
header(s, "Sources", "Backup")
text(s, Inches(0.6), Inches(1.7), Inches(12.1), Inches(4.8),
     ["LVES Round 1 Member Survey — Summary Report, Oct 4, 2026 (16 submissions, 13 unique respondents). "
      "Internal committee document.",
      "Starfighters Space, “Starfighters Space Hosts HSAT 2026 in Midland” (company announcement): "
      "https://www.linkedin.com/posts/starfighters-space_we-are-excited-to-announce-that-starfighters-"
      "activity-7492666518086971392-aVaL",
      "High Speed Flight portal (scope: atmospheric and exo-atmospheric vehicles, Mach 0.90+): "
      "https://www.highspeedflight.com/",
      "FAA, 14 CFR Part 450 — Launch and Reentry Licensing Requirements: "
      "https://www.ecfr.gov/current/title-14/chapter-III/subchapter-C/part-450"],
     size=14, color=NAVY, spacing=14)
footer(s)

prs.save(OUT)
print(OUT)
