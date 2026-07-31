#!/usr/bin/env python3
"""Combine the three Lady Rocket feature tiers into one luxury portfolio PDF
(cover page + Tier 1/2/3) on Exos letterhead via reportlab."""
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, PageBreak)
from reportlab.platypus.flowables import HRFlowable
from PIL import Image as PILImage

OUT = 'Lady_Rocket_Founding_Feature_Portfolio.pdf'
LOGO = 'assets/exos-letterhead-logo-tight.png'
FOOTER = 'assets/exos-letterhead-footer-tight.png'

GOLD = HexColor('#B8860B')
NAVY = HexColor('#1B3A5C')
GRAY = HexColor('#404040')
DARK = HexColor('#222222')

PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.9 * inch
TOP_GAP = 0.0 * inch          # small, even top gap before the logo
TOP_MARGIN = 1.6 * inch
BOT_MARGIN = 1.1 * inch

def img_dims(path, w):
    im = PILImage.open(path); iw, ih = im.size
    return w, w * ih / iw

LOGO_H = 0.75 * inch
LOGO_W = LOGO_H * PILImage.open(LOGO).size[0] / PILImage.open(LOGO).size[1]
FOOT_H = 0.75 * inch
FOOT_W = FOOT_H * PILImage.open(FOOTER).size[0] / PILImage.open(FOOTER).size[1]

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.drawImage(LOGO, LEFT, PAGE_H - TOP_GAP - LOGO_H, width=LOGO_W,
                     height=LOGO_H, mask='auto', preserveAspectRatio=True)
    canvas.drawImage(FOOTER, PAGE_W - RIGHT - FOOT_W, 0.0*inch, width=FOOT_W, height=FOOT_H,
                     mask='auto', preserveAspectRatio=True)
    canvas.setFont('Helvetica', 7.5); canvas.setFillColor(GRAY)
    canvas.drawCentredString(PAGE_W/2, 0.0*inch + FOOT_H + 4,
                             'Lady Rocket Exclusive Rocket Club  ·  Powered by Exos Aerospace  ·  In collaboration with Copernic Space')
    canvas.restoreState()

ss = getSampleStyleSheet()
body = ParagraphStyle('b', parent=ss['Normal'], fontName='Helvetica', fontSize=8.2,
                      leading=10.5, textColor=DARK, spaceAfter=2.5)
feat = ParagraphStyle('f', parent=body, leftIndent=12, spaceAfter=2.5)
h_sec = ParagraphStyle('h', parent=body, fontName='Helvetica-Bold', fontSize=10,
                       textColor=NAVY, spaceBefore=4.5, spaceAfter=2)
club = ParagraphStyle('club', parent=body, fontName='Helvetica-Bold', fontSize=15,
                      textColor=GOLD, alignment=TA_CENTER, spaceAfter=3)
sub = ParagraphStyle('sub', parent=body, fontSize=10, textColor=GRAY,
                     alignment=TA_CENTER, spaceAfter=5)
hero = ParagraphStyle('hero', parent=body, fontName='Helvetica-Bold', fontSize=17,
                      textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
tag = ParagraphStyle('tag', parent=body, fontName='Helvetica-Oblique', fontSize=10.5,
                     textColor=GRAY, alignment=TA_CENTER, spaceAfter=3)
pw = ParagraphStyle('pw', parent=body, fontSize=8.5, textColor=GOLD,
                    alignment=TA_CENTER, spaceAfter=4)
fine = ParagraphStyle('fine', parent=body, fontName='Helvetica-Oblique',
                      fontSize=7.3, leading=9, textColor=GRAY, spaceBefore=4)
# cover styles
cv_title = ParagraphStyle('cvt', parent=body, fontName='Helvetica-Bold', fontSize=26,
                          textColor=NAVY, alignment=TA_CENTER, spaceAfter=6, leading=30)
cv_gold = ParagraphStyle('cvg', parent=body, fontName='Helvetica-Bold', fontSize=15,
                         textColor=GOLD, alignment=TA_CENTER, spaceAfter=4)
cv_it = ParagraphStyle('cvi', parent=body, fontName='Helvetica-Oblique', fontSize=12,
                       textColor=GRAY, alignment=TA_CENTER, spaceAfter=14, leading=17)
cv_tier = ParagraphStyle('cvtr', parent=body, fontSize=11.5, textColor=DARK,
                         alignment=TA_CENTER, spaceAfter=10, leading=16)

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def is_section(s):
    return bool(re.match(r'^[A-Z][A-Z0-9 ™&·\-]{3,}$', s)) and len(s) <= 40

def render_tier(flow, path):
    raw = open(path).read().split('\n')
    n = len(raw)
    # title cluster
    club_txt = raw[0].strip()
    sub_txt = raw[1].strip()
    i = 0
    while i < n and raw[i].strip() != '---':
        i += 1
    # hero/tagline/powered sit between line 2 and the first ---
    mid = [x.strip() for x in raw[2:i] if x.strip()]
    hero_txt = mid[0] if mid else ''
    tag_txt = mid[1] if len(mid) > 1 else ''
    pw_txt = mid[2] if len(mid) > 2 else ''
    flow.append(Paragraph(esc(club_txt), club))
    flow.append(Paragraph(esc(sub_txt), sub))
    flow.append(Paragraph(esc(hero_txt), hero))
    if tag_txt: flow.append(Paragraph(esc(tag_txt), tag))
    if pw_txt: flow.append(Paragraph(esc(pw_txt), pw))
    flow.append(HRFlowable(width='100%', thickness=0.75, color=GOLD, spaceBefore=1, spaceAfter=5))
    i += 1
    buf = []
    def flush():
        if buf:
            flow.append(Paragraph(esc(' '.join(buf)), body)); buf.clear()
    while i < n:
        s = raw[i].strip()
        if s == '---' or not s:
            flush(); i += 1; continue
        if is_section(s):
            flush(); flow.append(Paragraph(esc(s), h_sec)); i += 1; continue
        m = re.match(r'^([A-Z][A-Za-z ™]{2,40})\.\s+(.*)$', s)
        if m and len(m.group(1).split()) <= 5 and not m.group(1).isupper():
            flush()
            flow.append(Paragraph(f'<font color="#B8860B"><b>{esc(m.group(1))}.</b></font> {esc(m.group(2))}', feat))
            i += 1; continue
        if s.startswith('Note:'):
            flush(); flow.append(Paragraph(esc(s), fine)); i += 1; continue
        buf.append(s)
        i += 1
    flush()

flow = []
# COVER
flow.append(Spacer(1, 0.6*inch))
flow.append(Paragraph('LADY ROCKET', cv_gold))
flow.append(Paragraph('Founding Applicant<br/>Feature Portfolio', cv_title))
flow.append(Paragraph('The world&#8217;s most exclusive private rocket community', cv_it))
flow.append(HRFlowable(width='55%', thickness=1, color=GOLD, spaceAfter=16))
flow.append(Paragraph('Three privileges reserved for the twenty.', tag))
flow.append(Spacer(1, 0.15*inch))
flow.append(Paragraph('<b>I &#8212; The Reusable Signature&#8482;</b> &#8212; Your mark, flown and returned, accumulating flight heritage. Ownership.', cv_tier))
flow.append(Paragraph('<b>II &#8212; The Flown Artifact Vault&#8482;</b> &#8212; Personal objects flown and returned with certified provenance. Renewable luxury.', cv_tier))
flow.append(Paragraph('<b>III &#8212; The Lunar Legacy Capsule&#8482;</b> &#8212; A reserved opportunity toward the Moon, built on real lunar heritage. Legacy.', cv_tier))
flow.append(Spacer(1, 0.3*inch))
flow.append(Paragraph('Powered by Exos Aerospace  ·  In collaboration with Copernic Space', pw))
flow.append(PageBreak())

for p in ['drafts/lady-rocket-reusable-signature-spec.md',
          'drafts/lady-rocket-flown-artifact-vault.md',
          'drafts/lady-rocket-lunar-legacy-capsule.md']:
    render_tier(flow, p)
    flow.append(PageBreak())

doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=LEFT, rightMargin=RIGHT,
                      topMargin=TOP_MARGIN, bottomMargin=BOT_MARGIN,
                      title='Lady Rocket Founding Applicant Feature Portfolio')
frame = Frame(LEFT, BOT_MARGIN, PAGE_W-LEFT-RIGHT, PAGE_H-TOP_MARGIN-BOT_MARGIN, id='b')
doc.addPageTemplates([PageTemplate(id='lh', frames=[frame], onPage=header_footer)])
doc.build(flow)
print('WROTE', OUT)
