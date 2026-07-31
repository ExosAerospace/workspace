#!/usr/bin/env python3
"""Render the AEDC Velocity Alliance whitepaper into the Exos letterhead template."""
import re
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SRC = 'drafts/aedc-velocity-alliance-whitepaper.md'
OUT = 'Exos_AEDC_Velocity_Alliance_Whitepaper.docx'
NAVY = RGBColor(0x1B, 0x3A, 0x5C)
GRAY = RGBColor(0x40, 0x40, 0x40)
DARK = RGBColor(0x22, 0x22, 0x22)

raw = open(SRC).read().split('\n')

doc = Document('assets/exos-letterhead-template.docx')
# normalize base font
nf = doc.styles['Normal'].font
nf.name = 'Calibri'; nf.size = Pt(10.5)
doc.styles['Normal'].paragraph_format.space_after = Pt(4)

# clear empty template body paragraphs
for p in list(doc.paragraphs):
    p._element.getparent().remove(p._element)

def add(text='', bold=False, size=None, align=None, italic=False, color=DARK,
        before=None, after=None, bullet=False):
    p = doc.add_paragraph()
    if bullet:
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.first_line_indent = Inches(-0.15)
        text = '•  ' + text
    if text:
        r = p.add_run(text)
        r.bold = bold; r.italic = italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    if align is not None: p.alignment = align
    if before is not None: p.paragraph_format.space_before = Pt(before)
    if after is not None: p.paragraph_format.space_after = Pt(after)
    return p

def h1(t): add(t, bold=True, size=13, color=NAVY, before=12, after=5)
def h2(t): add(t, bold=True, size=11, color=NAVY, before=8, after=3)
def h3(t): add(t, bold=True, size=10.5, color=GRAY, before=6, after=2)

n = len(raw)
SEP = lambda s: set(s.strip()) <= {'=', '-', ' '} and len(s.strip()) > 3

# --- Title block ---
add('EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC.', bold=True, size=15,
    align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY, after=2)
add('AEDC Velocity Alliance — Whitepaper Submission', bold=True, size=12.5,
    align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, after=2)
add('Onboarding Opportunity 1', size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
    italic=True, after=2)
add('Solicitation FA9101-26-9-Velocity_Alliance   |   10 U.S.C. § 4022   |   June 9, 2026 (Revised)',
    size=9, align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, after=8)

i = 0
while i < n and 'RESPONDENT INFORMATION' not in raw[i]:
    i += 1
i += 1
if i < n and SEP(raw[i]): i += 1

def render_until(stop_pred):
    global i
    buf = []
    def flush():
        if buf:
            add(' '.join(buf)); buf.clear()
    while i < n and not stop_pred(raw[i]):
        line = raw[i]
        if SEP(line): i += 1; continue
        s = line.strip()
        if not s:
            flush(); i += 1; continue
        m1 = re.match(r'^(\d+\.0)\s+(.*)$', s)
        m2 = re.match(r'^(\d+\.\d+)\s+(.*)$', s)
        if m1:
            flush(); h1(f'{m1.group(1)}  {m1.group(2).title()}')
        elif m2:
            flush(); h2(f'{m2.group(1)}  {m2.group(2).title()}')
        elif s.startswith('- '):
            flush(); add(s[2:], bullet=True, after=2)
        elif re.match(r'^[A-Z0-9][A-Z0-9 /,&()§.\-]{4,}$', s):
            flush(); h3(s.title())
        elif re.match(r'^[A-Za-z()/. ]{2,30}:\s{2,}\S', s) or re.match(r'^[A-Za-z ]+:$', s):
            flush(); add(s)
        elif line.startswith('    '):
            flush(); add(s)
        else:
            buf.append(s)
        i += 1
    flush()

# Respondent block + Agreements officer
render_until(lambda l: 'EXECUTIVE SUMMARY' in l)
i += 1
if i < n and SEP(raw[i]): i += 1
h1('Executive Summary')
render_until(lambda l: 'END OF WHITEPAPER' in l or '--- END' in l)

doc.save(OUT)
print('WROTE', OUT)
