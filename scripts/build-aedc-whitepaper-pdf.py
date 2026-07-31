#!/usr/bin/env python3
"""Render the AEDC Velocity Alliance whitepaper to a letterhead PDF via reportlab."""
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, ListFlowable, ListItem, Image)
from reportlab.platypus.flowables import HRFlowable
from PIL import Image as PILImage

SRC = 'drafts/aedc-velocity-alliance-whitepaper.md'
OUT = 'Exos_AEDC_Velocity_Alliance_Whitepaper.pdf'
LOGO = 'assets/exos-letterhead-logo-tight.png'
FOOTER = 'assets/exos-letterhead-footer-tight.png'

NAVY = HexColor('#1B3A5C')
GRAY = HexColor('#404040')
DARK = HexColor('#222222')

PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.9 * inch
TOP_GAP = 0.0 * inch      # small, even top gap before the logo
TOP_MARGIN = 1.25 * inch   # space for logo band
BOT_MARGIN = 1.1 * inch    # space for footer graphic

def img_dims(path, target_w):
    im = PILImage.open(path); w, h = im.size
    return target_w, target_w * h / w

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
    canvas.drawRightString(PAGE_W - RIGHT, 0.0*inch + FOOT_H + 4,
                           f'Page {doc.page}')
    canvas.restoreState()

ss = getSampleStyleSheet()
body = ParagraphStyle('body', parent=ss['Normal'], fontName='Helvetica',
                      fontSize=9.5, leading=13, textColor=DARK, spaceAfter=5)
kv = ParagraphStyle('kv', parent=body, fontName='Courier', fontSize=9, leading=12,
                    spaceAfter=1)
h1 = ParagraphStyle('h1', parent=body, fontName='Helvetica-Bold', fontSize=12.5,
                    textColor=NAVY, spaceBefore=12, spaceAfter=5)
h2 = ParagraphStyle('h2', parent=body, fontName='Helvetica-Bold', fontSize=10.5,
                    textColor=NAVY, spaceBefore=8, spaceAfter=3)
h3 = ParagraphStyle('h3', parent=body, fontName='Helvetica-Bold', fontSize=9.5,
                    textColor=GRAY, spaceBefore=6, spaceAfter=2)
title = ParagraphStyle('title', parent=body, fontName='Helvetica-Bold',
                       fontSize=15, textColor=NAVY, alignment=TA_CENTER, spaceAfter=3)
sub = ParagraphStyle('sub', parent=body, fontName='Helvetica-Bold', fontSize=12,
                     textColor=GRAY, alignment=TA_CENTER, spaceAfter=3)
subi = ParagraphStyle('subi', parent=body, fontName='Helvetica-Oblique',
                      fontSize=10, alignment=TA_CENTER, spaceAfter=2)
meta = ParagraphStyle('meta', parent=body, fontName='Helvetica', fontSize=8.5,
                      textColor=GRAY, alignment=TA_CENTER, spaceAfter=8)

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

raw = open(SRC).read().split('\n')
n = len(raw)
SEP = lambda s: set(s.strip()) <= {'=', '-', ' '} and len(s.strip()) > 3

flow = []
flow.append(Paragraph('EXOS AEROSPACE SYSTEMS &amp; TECHNOLOGIES, INC.', title))
flow.append(Paragraph('AEDC Velocity Alliance — Whitepaper Submission', sub))
flow.append(Paragraph('Onboarding Opportunity 1', subi))
flow.append(Paragraph('Solicitation FA9101-26-9-Velocity_Alliance&nbsp;&nbsp;|&nbsp;&nbsp;'
                      '10 U.S.C. § 4022&nbsp;&nbsp;|&nbsp;&nbsp;May 31, 2026', meta))
flow.append(HRFlowable(width='100%', thickness=0.75, color=NAVY, spaceAfter=8))

i = 0
while i < n and 'RESPONDENT INFORMATION' not in raw[i]:
    i += 1
i += 1
if i < n and SEP(raw[i]): i += 1

bullets = []
def flush_bullets():
    global bullets
    if bullets:
        flow.append(ListFlowable(
            [ListItem(Paragraph(esc(b), body), leftIndent=14, value='•') for b in bullets],
            bulletType='bullet', start='•', leftIndent=12))
        bullets = []

def render_until(stop):
    global i
    while i < n and not stop(raw[i]):
        line = raw[i]
        if SEP(line): i += 1; continue
        s = line.strip()
        if not s: flush_bullets(); i += 1; continue
        m1 = re.match(r'^(\d+\.0)\s+(.*)$', s)
        m2 = re.match(r'^(\d+\.\d+)\s+(.*)$', s)
        if s.startswith('- '):
            bullets.append(s[2:]); i += 1; continue
        flush_bullets()
        if m1:
            flow.append(Paragraph(esc(f'{m1.group(1)}  {m1.group(2).title()}'), h1))
        elif m2:
            flow.append(Paragraph(esc(f'{m2.group(1)}  {m2.group(2).title()}'), h2))
        elif re.match(r'^[A-Z0-9][A-Z0-9 /,&()§.\-]{4,}$', s):
            flow.append(Paragraph(esc(s.title()), h3))
        elif re.match(r'^[A-Za-z()/ ]+:\s{2,}\S', s) or re.match(r'^[A-Za-z ]+:$', s):
            flow.append(Paragraph(esc(s), kv))
        else:
            flow.append(Paragraph(esc(s), body))
        i += 1

render_until(lambda l: 'EXECUTIVE SUMMARY' in l)
i += 1
if i < n and SEP(raw[i]): i += 1
flush_bullets()
flow.append(Paragraph('Executive Summary', h1))
render_until(lambda l: 'END OF WHITEPAPER' in l or '--- END' in l)
flush_bullets()

doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=LEFT, rightMargin=RIGHT,
                      topMargin=TOP_MARGIN, bottomMargin=BOT_MARGIN, title='Exos AEDC Velocity Alliance Whitepaper')
frame = Frame(LEFT, BOT_MARGIN, PAGE_W-LEFT-RIGHT, PAGE_H-TOP_MARGIN-BOT_MARGIN, id='body')
doc.addPageTemplates([PageTemplate(id='lh', frames=[frame], onPage=header_footer)])
doc.build(flow)
print('WROTE', OUT)
