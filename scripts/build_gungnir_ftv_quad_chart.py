#!/usr/bin/env python3
"""Project GUNGNIR — USAF TACFI quad chart (FTV refueling + storable RDRE) + DoD transition slide.

Built for the GS-15 buy-off (Harvazinski / Burr call, 2026-09-28). Output: .pptx (editable) in the
Gungnir TACFI meeting folder. Content lives in the CONTENT dict so edits don't touch layout code.
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR

OUT = 'projects/USAF/Gungnir_BLK3-RDRE/03_TACFI_Meeting_2026-09/Gungnir_FTV_Refueling_TACFI_QuadChart_2026-09-28.pptx'
IMG = 'assets/blk3_hover.png'
NAVY = RGBColor(0x1B, 0x3A, 0x5C); GRAY = RGBColor(0x40, 0x40, 0x40); DARK = RGBColor(0x1E, 0x1E, 0x1E)
LIGHT = RGBColor(0xE8, 0xEE, 0xF4); WHITE = RGBColor(0xFF, 0xFF, 0xFF); ACCENT = RGBColor(0xC8, 0x6A, 0x1E)

C = {
 'title': 'Exos Aerospace Systems & Technologies, Inc.  |  Project GUNGNIR',
 'subtitle': 'Refuel · Relight · Reuse — In-Space Refueling + Storable-Propellant RDRE Flight Demo for Fast Transfer Vehicles (FTV)',
 'tag': 'AF TACFI  |  SBIR Phase II FA9300-25-C-6022',
 'img_caption': 'BLK3 reusable VTVL vehicle — tethered hover test, Greenville TX',
 'conops': ['1  Hover', '2  Flight to 100 km+', '3  In-space: RDRE fire + restart\n    & µg propellant transfer', '4  Land · recover · refly'],
 'q1_tagline': 'Space logistics needs FTVs that can be refueled and re-maneuvered on orbit. Exos flies the refueling and propulsion hardware in space, recovers it, and flies it again.',
 'q2': [
  ('Objective', ['Fly a <b>non-cryogenic (storable) RDRE</b> on the reusable BLK3 vehicle: hover → flights to 100 km+ → <b>in-space ignition, restart and pulsing</b>.',
                 'In the same campaign, demonstrate <b>tank-to-tank transfer of storable propellant in microgravity</b>, the refueling function an FTV and depot need.']),
  ('Innovation', ['Recoverable, re-flyable <b>in-space</b> test of refueling + detonation propulsion. Vacuum ignition/restart and µg propellant feed and transfer cannot be reproduced on a ground stand.',
                  'Reusable = repeated in-space test points per campaign, not one expendable shot. Fast turnaround; pad + power/comms only.']),
  ('Operational Impact', ['Refuelable FTVs = <b>maneuver without regret</b> for USSF mobility & logistics. Higher-efficiency, compact propulsion + on-orbit resupply extends vehicle life.',
                          'Sustainment: refuel and service on orbit rather than dispose by reentry. Commercial stations become <b>refueling depots</b>.']),
  ('Deliverables', ['1 hover + 2 flights to 100 km+ with in-space RDRE firings and a µg transfer demo; flight dataset (thrust, Isp, restart, transfer mass/flow) + final report.']),
 ],
 'enduser': '<b>End User:</b> AFRL/RQRI (Edwards)  ·  <b>Customer:</b> AFRL — Dr. M. Harvazinski; J. Burr (RDRE lead)',
 'engine_note': 'Engine: government-furnished / candidate storable RDRE (GTL-built), selected by program trade study. Tanks: Type V composite heritage (Scorpius, flew on IM Odysseus & Athena).',
 'cost_hdr': ['$M', 'Year 1', 'Year 2', 'Total'],
 'cost_rows': [
  ['Dev: integration, storable feed + transfer module', '1.4', '0.3', '1.7'],
  ['Prototype: hover test', '0.6', '—', '0.6'],
  ['Test flights: in-space fire/restart + µg transfer', '—', '1.7', '1.7'],
  ['TACFI (SBIR/federal)', '1.0', '1.0', '2.0'],
  ['Match: Texas Space Commission (SEARF)*', '1.0', '1.0', '2.0'],
  ['Total', '2.0', '2.0', '4.0'],
 ],
 'milestones': 'M1 PDR (Q1) · M2 CDR (Q2) · M3 Hover (Q4) · M4 Flight 1: in-space RDRE fire (Q5) · M5 µg transfer demo (Q6) · M6 Flight 2: restart/pulse + final report (Q8)',
 'cost_note': '*TSC board meets 11 Dec 2026; match subject to board approval and TACFI selection. Year splits are planning estimates.',
 'q4_title': 'Success & Transition (DoD)',
 'q4': ['<b>Success:</b> in-space storable-RDRE ignition + restart and a µg propellant transfer, recovered and reflown, with a flight dataset delivered to AFRL.'],
 'transition_ladder': [],
 'cta': 'Focus: Space Mobility & Logistics / in-space propulsion',
 'footer': 'Distribution: non-proprietary summary. TACFI is subject to selection; nothing is awarded. Exos provides the reusable flight-test platform, integration and propellant-transfer hardware; RDRE hardware is government-furnished or selected by trade study.',
}


def tb(slide, x, y, w, h, paras, size=10, color=DARK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, bullets=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, t in enumerate(paras if isinstance(paras, list) else [paras]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        _runs(p, ('• ' if bullets else '') + t, size, color, bold)
        p.space_after = Pt(2)
    return box


def _runs(p, text, size, color, bold):
    """Minimal <b>…</b> markup → runs."""
    parts = text.replace('</b>', '<b>').split('<b>')
    for i, part in enumerate(parts):
        if not part: continue
        r = p.add_run(); r.text = part
        r.font.size = Pt(size); r.font.color.rgb = color; r.font.name = 'Arial'
        r.font.bold = bold or (i % 2 == 1)


def section(slide, x, y, w, h, heading, items, size=9):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = Inches(0.02)
    first = True
    for head, lines in heading if isinstance(heading, list) else [(heading, items)]:
        p = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
        _runs(p, head, size + 0.5, NAVY, True); p.space_before = Pt(3); p.space_after = Pt(1)
        for l in lines:
            q = tf.add_paragraph(); _runs(q, '• ' + l, size, DARK, False); q.space_after = Pt(1.5)
    return box


def rect(slide, x, y, w, h, fill, line=None):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None: s.line.fill.background()
    else: s.line.color.rgb = line
    s.shadow.inherit = False
    return s


def line(slide, x1, y1, x2, y2, w=1.25):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = NAVY; c.line.width = Pt(w)


def header(s, title, subtitle, tag):
    rect(s, 0, 0, 13.333, 0.95, NAVY)
    tb(s, 0.2, 0.05, 9.4, 0.4, title, 17, WHITE, True)
    tb(s, 0.2, 0.47, 10.4, 0.45, subtitle, 11, WHITE)
    tb(s, 9.6, 0.08, 3.55, 0.35, tag, 10, WHITE, True, PP_ALIGN.RIGHT)


def footer(s, text, n):
    tb(s, 0.2, 7.12, 11.9, 0.35, text, 7, GRAY)
    tb(s, 12.3, 7.12, 0.85, 0.3, str(n), 8, GRAY, align=PP_ALIGN.RIGHT)


def build():
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    # ---------------- Slide 1: QUAD CHART ----------------
    s = prs.slides.add_slide(blank)
    header(s, C['title'], C['subtitle'], C['tag'])
    tb(s, 9.6, 0.5, 3.55, 0.4, C['cta'], 8.5, WHITE, align=PP_ALIGN.RIGHT)
    MX, MY = 6.2, 3.95
    line(s, MX, 1.0, MX, 7.08); line(s, 0.1, MY, 13.23, MY)

    # Q1 — picture + ConOps
    s.shapes.add_picture(IMG, Inches(0.2), Inches(1.05), height=Inches(1.95))
    tb(s, 0.2, 3.0, 3.5, 0.22, C['img_caption'], 7, GRAY)
    cx = 3.75
    tb(s, cx, 1.05, 2.4, 0.25, 'Concept of Operations', 10, NAVY, True)
    for i, step in enumerate(C['conops']):
        b = rect(s, cx, 1.35 + i * 0.44, 2.35, 0.38, LIGHT if i != 2 else ACCENT)
        tb(s, cx + 0.02, 1.36 + i * 0.44, 2.33, 0.36, step, 8.5, DARK if i != 2 else WHITE, True, anchor=MSO_ANCHOR.MIDDLE)
    tb(s, 0.2, 3.22, 5.95, 0.7, C['q1_tagline'], 9.5, NAVY, True)

    # Q2 — description
    section(s, MX + 0.08, 1.0, 13.23 - MX - 0.1, 2.35, C['q2'], None, 8.6)
    tb(s, MX + 0.08, 3.36, 13.23 - MX - 0.1, 0.25, C['enduser'], 8.5)
    tb(s, MX + 0.08, 3.6, 13.23 - MX - 0.1, 0.34, C['engine_note'], 7.2, GRAY)

    # Q3 — cost & schedule
    tb(s, 0.2, 4.0, 5.9, 0.25, 'Integrated Cost and Schedule ($M)', 10.5, NAVY, True)
    rows = [C['cost_hdr']] + C['cost_rows']
    t = s.shapes.add_table(len(rows), 4, Inches(0.2), Inches(4.28), Inches(5.9), Inches(1.9)).table
    widths = [3.35, 0.85, 0.85, 0.85]
    for j, wv in enumerate(widths): t.columns[j].width = Inches(wv)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            cell = t.cell(i, j); cell.text = ''
            p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            _runs(p, v, 8, WHITE if i == 0 else DARK, i == 0 or i == len(rows) - 1)
            cell.margin_top = cell.margin_bottom = Inches(0.01)
            cell.fill.solid(); cell.fill.fore_color.rgb = NAVY if i == 0 else (LIGHT if i in (4, 5, 6) else WHITE)
    tb(s, 0.2, 6.22, 5.9, 0.5, '<b>Milestones:</b> ' + C['milestones'], 7.8)
    tb(s, 0.2, 6.75, 5.9, 0.32, C['cost_note'], 6.8, GRAY)

    # Q4 — success & transition
    tb(s, MX + 0.08, 4.0, 6.9, 0.25, C['q4_title'], 10.5, NAVY, True)
    tb(s, MX + 0.08, 4.27, 6.9, 0.5, C['q4'], 8.6)
    y = 4.78
    for k, (step, what, money) in enumerate(C['transition_ladder']):
        rect(s, MX + 0.1, y, 0.32, 0.4, NAVY)
        tb(s, MX + 0.1, y, 0.32, 0.4, str(k + 1), 11, WHITE, True, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
        tb(s, MX + 0.47, y - 0.02, 4.9, 0.46, f'<b>{step}</b> — {what}', 8.1)
        tb(s, MX + 5.4, y - 0.02, 1.65, 0.46, money, 8, NAVY, True, PP_ALIGN.RIGHT)
        y += 0.47
    footer(s, C['footer'], 1)

    # ---------------- Slide 2: DoD TRANSITION PATH (backup) ----------------
    if C.get('slide2'):
        s2 = prs.slides.add_slide(blank)
        header(s2, 'GUNGNIR — DoD Transition Path', C['slide2']['subtitle'], C['tag'])
        section(s2, 0.3, 1.1, 6.3, 5.9, C['slide2']['left'], None, 11)
        section(s2, 6.8, 1.1, 6.3, 5.9, C['slide2']['right'], None, 11)
        footer(s2, C['slide2'].get('footer', C['footer']), 2)

    prs.save(OUT); print('saved', OUT)


if __name__ == '__main__':
    import json, sys
    if len(sys.argv) > 1:  # optional JSON overrides (transition content from research)
        C.update(json.load(open(sys.argv[1])))
    build()
