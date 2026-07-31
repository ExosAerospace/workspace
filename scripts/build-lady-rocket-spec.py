#!/usr/bin/env python3
"""Build the Lady Rocket Reusable Signature spec sheet as a clean
single-section letterhead .docx (full-width reflowed body)."""
import re
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from PIL import Image as PILImage

import sys
SRC = sys.argv[1]
OUT = sys.argv[2]
T_CLUB = sys.argv[3]
T_SUB = sys.argv[4]
T_HERO = sys.argv[5]
T_TAG = sys.argv[6]
LOGO = 'assets/exos-letterhead-logo-tight.png'
FOOTER = 'assets/exos-letterhead-footer-tight.png'

GOLD = RGBColor(0xB8, 0x86, 0x0B)   # luxury gold accent
NAVY = RGBColor(0x1B, 0x3A, 0x5C)
GRAY = RGBColor(0x40, 0x40, 0x40)
DARK = RGBColor(0x22, 0x22, 0x22)

raw = open(SRC).read().split('\n')
n = len(raw)

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.5); sec.page_height = Inches(11)
sec.left_margin = Inches(1.0); sec.right_margin = Inches(0.5)
sec.top_margin = Inches(1.5); sec.bottom_margin = Inches(1.1)
sec.header_distance = Inches(0.01); sec.footer_distance = Inches(0.01)

nf = doc.styles['Normal'].font
nf.name = 'Calibri'; nf.size = Pt(10.5)
doc.styles['Normal'].paragraph_format.space_after = Pt(4)

usable_w = sec.page_width - sec.left_margin - sec.right_margin

# Header logo: tight-cropped, sized to a clean ~3.0" width, left-aligned, zero padding
hp = sec.header.paragraphs[0]
hp.paragraph_format.space_before = Pt(0); hp.paragraph_format.space_after = Pt(0)
hp.add_run().add_picture(LOGO, height=Inches(0.75))
fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
fp.paragraph_format.space_before = Pt(0); fp.paragraph_format.space_after = Pt(0)
fp.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
fp.paragraph_format.line_spacing = Pt(54)  # 0.75in, kills baseline descent below footer image
fr = fp.add_run(); fr.font.size = Pt(1)
fr.add_picture(FOOTER, height=Inches(0.75))

def add(text='', bold=False, size=None, align=None, italic=False, color=DARK,
        before=None, after=None):
    p = doc.add_paragraph()
    if text:
        r = p.add_run(text)
        r.bold = bold; r.italic = italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    if align is not None: p.alignment = align
    if before is not None: p.paragraph_format.space_before = Pt(before)
    if after is not None: p.paragraph_format.space_after = Pt(after)
    return p

# Section headings we recognize (ALLCAPS lines)
def is_section(s):
    return bool(re.match(r'^[A-Z][A-Z0-9 ™&·\-]{3,}$', s)) and len(s) <= 40

i = 0
# Title block (first 3 lines are the title cluster)
add(T_CLUB, bold=True, size=16,
    align=WD_ALIGN_PARAGRAPH.CENTER, color=GOLD, after=2)
add(T_SUB, size=11,
    align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, after=8)
add(T_HERO, bold=True, size=20,
    align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY, after=2)
add(T_TAG, italic=True, size=12,
    align=WD_ALIGN_PARAGRAPH.CENTER, color=GRAY, after=4)
add('Powered by Exos Aerospace · In collaboration with Copernic Space',
    size=9, align=WD_ALIGN_PARAGRAPH.CENTER, color=GOLD, after=6)

# Skip source title cluster: advance to first '---'
while i < n and raw[i].strip() != '---':
    i += 1
i += 1  # past first ---

buf = []
def flush():
    if buf:
        add(' '.join(buf), after=6); buf.clear()

def h_section(t):
    add(t, bold=True, size=12.5, color=NAVY, before=10, after=4)

while i < n:
    line = raw[i]
    s = line.strip()
    if s == '---':
        flush(); i += 1; continue
    if not s:
        flush(); i += 1; continue
    if is_section(s):
        flush(); h_section(s); i += 1; continue
    # "Label. Rest of sentence." feature bullets in the receive section
    m = re.match(r'^([A-Z][A-Za-z ™]{2,40})\.\s+(.*)$', s)
    if m and m.group(1).isupper() is False and m.group(1)[0].isupper():
        # treat as a labeled feature line if label is Title Case and <= 5 words
        label = m.group(1)
        if len(label.split()) <= 5 and label[0].isupper():
            flush()
            p = doc.add_paragraph()
            r = p.add_run(label + '. '); r.bold = True; r.font.color.rgb = GOLD
            r2 = p.add_run(m.group(2)); r2.font.color.rgb = DARK
            p.paragraph_format.space_after = Pt(5)
            p.paragraph_format.left_indent = Inches(0.2)
            i += 1; continue
    # closing fine print
    if s.startswith('Note:'):
        flush(); add(s, italic=True, size=8.5, color=GRAY, before=8); i += 1; continue
    buf.append(s)
    i += 1
flush()

doc.save(OUT)
print('WROTE', OUT)
