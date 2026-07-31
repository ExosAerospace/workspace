#!/usr/bin/env python3
"""Render the $500K Note Offering one-pager to a letterhead PDF (reportlab), matching house style."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, ListFlowable, ListItem, Table, TableStyle)
from reportlab.platypus.flowables import HRFlowable
from PIL import Image as PILImage

OUT = 'drafts/Exos_500K_Note_Offering_OnePager.pdf'
LOGO = 'assets/exos-letterhead-logo-tight.png'
FOOTER = 'assets/exos-letterhead-footer-tight.png'
NAVY = HexColor('#1B3A5C'); GRAY = HexColor('#404040'); DARK = HexColor('#222222')
PAGE_W, PAGE_H = letter
LEFT = RIGHT = 0.9*inch; TOP_GAP = 0.0*inch; TOP_MARGIN = 1.2*inch; BOT_MARGIN = 1.05*inch
LOGO_H = 0.75*inch; LOGO_W = LOGO_H*PILImage.open(LOGO).size[0]/PILImage.open(LOGO).size[1]
FOOT_H = 0.75*inch; FOOT_W = FOOT_H*PILImage.open(FOOTER).size[0]/PILImage.open(FOOTER).size[1]

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.drawImage(LOGO, LEFT, PAGE_H-TOP_GAP-LOGO_H, width=LOGO_W, height=LOGO_H, mask='auto', preserveAspectRatio=True)
    canvas.drawImage(FOOTER, PAGE_W-RIGHT-FOOT_W, 0.0*inch, width=FOOT_W, height=FOOT_H, mask='auto', preserveAspectRatio=True)
    canvas.restoreState()

ss = getSampleStyleSheet()
body = ParagraphStyle('body', parent=ss['Normal'], fontName='Helvetica', fontSize=9.5, leading=13, textColor=DARK, spaceAfter=5)
h1 = ParagraphStyle('h1', parent=body, fontName='Helvetica-Bold', fontSize=12, textColor=NAVY, spaceBefore=11, spaceAfter=5)
title = ParagraphStyle('title', parent=body, fontName='Helvetica-Bold', fontSize=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=3)
sub = ParagraphStyle('sub', parent=body, fontName='Helvetica-Bold', fontSize=11.5, textColor=GRAY, alignment=TA_CENTER, spaceAfter=3)
meta = ParagraphStyle('meta', parent=body, fontName='Helvetica-Oblique', fontSize=8.5, textColor=GRAY, alignment=TA_CENTER, spaceAfter=8)
disc = ParagraphStyle('disc', parent=body, fontName='Helvetica-Oblique', fontSize=7.5, textColor=GRAY, leading=9, spaceBefore=10)

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def B(s): return Paragraph(esc(s).replace('**','') if False else esc(s), body)

flow = []
flow.append(Paragraph('EXOS AEROSPACE SYSTEMS &amp; TECHNOLOGIES, INC.', title))
flow.append(Paragraph('$500,000 Note Offering', sub))
flow.append(Paragraph('8% Annual Interest&nbsp;&nbsp;|&nbsp;&nbsp;5-Year Term&nbsp;&nbsp;|&nbsp;&nbsp;Consistent with Prior Exos Note Rounds', sub))
flow.append(Paragraph('CONFIDENTIAL — for existing and accredited investors&nbsp;&nbsp;|&nbsp;&nbsp;299 FM 1903, Greenville, TX 75402&nbsp;&nbsp;|&nbsp;&nbsp;June 2026', meta))
flow.append(HRFlowable(width='100%', thickness=0.75, color=NAVY, spaceAfter=8))

# Terms table
rows = [
 ['Instrument', 'Promissory notes (same structure as prior Exos rounds)'],
 ['Total raise', 'Up to $500,000'],
 ['Interest', '8% per annum'],
 ['Term', '5 years'],
 ['Increments', '$25,000 lots, consistent with prior Exos note rounds'],
 ['Target close', '30 days'],
]
tbl = Table([[Paragraph(f'<b>{esc(k)}</b>', body), Paragraph(esc(v), body)] for k,v in rows],
            colWidths=[1.5*inch, 5.1*inch])
tbl.setStyle(TableStyle([
 ('BACKGROUND',(0,0),(0,-1), HexColor('#EEF2F6')),
 ('LINEBELOW',(0,0),(-1,-1),0.4, HexColor('#C9D3DD')),
 ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
 ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
 ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
]))
flow.append(tbl)

flow.append(Paragraph('Use of Proceeds — straight to a value inflection', h1))
flow.append(Paragraph('Proceeds complete execution of Exos&rsquo;s <b>first BLK3 suborbital flight</b> (entX / Project Lazarus &mdash; launch services agreement executed, $840K customer-funded) and advance the <b>second flight</b>. <b>Two successful flights above 85 km open the NASA Flight Opportunities on-ramp &mdash; a recurring ~$1M-per-flight NASA revenue line</b> &mdash; and set up a targeted <b>3-day reflight that would establish a new industry reusability record</b>. This is the near-term catalyst ahead of the Series A.', body))

flow.append(Paragraph('Why Exos, Why Now', h1))
bl = [
 'One of only 3 U.S.-licensed reusable suborbital providers — FAA launch license secured (March 2026) on the BLK3 PSRLV.',
 'entX flight booked ($840K customer commitment); a second BLK3 flight in active sales (~$1M).',
 'NASA Flight Opportunities on-ramp opens recurring per-flight revenue once two >85 km flights are flown.',
 'RDRE next-generation propulsion under an active USAF SBIR Phase II.',
 'Scorpius Space Launch Co. arbitrage — Exos holds 18% + a right of first refusal at a 2021 valuation basis on the only TRL-9 Type-V cryogenic tank technology flight-proven on the lunar surface (IM-1, IM-2). Upon securing committed funding, the ROFR becomes exclusive to Exos and its financier.',
 'A Series A (up to $25M) follows; note holders bridge ahead of it.',
]
flow.append(ListFlowable([ListItem(Paragraph(esc(b), body), leftIndent=12, value='•') for b in bl], bulletType='bullet', leftIndent=10))

flow.append(Paragraph('Contact', h1))
flow.append(Paragraph('<b>David Mitchell</b>, President &nbsp;&middot;&nbsp; Exos Aerospace Systems &amp; Technologies, Inc.<br/>299 FM 1903, Greenville, TX 75402 &nbsp;&middot;&nbsp; www.exosaero.com', body))

flow.append(Paragraph('Confidential. This summary is provided for discussion with existing and accredited investors only and is not an offer to sell, or a solicitation of an offer to buy, any security in any jurisdiction where such would be unlawful. Any investment will be made solely pursuant to definitive note documents. Forward-looking statements reflect current projections and assumptions; past performance does not guarantee future results.', disc))

frame = Frame(LEFT, BOT_MARGIN, PAGE_W-LEFT-RIGHT, PAGE_H-TOP_MARGIN-BOT_MARGIN, id='f', showBoundary=0)
doc = BaseDocTemplate(OUT, pagesize=letter, leftMargin=LEFT, rightMargin=RIGHT, topMargin=TOP_MARGIN, bottomMargin=BOT_MARGIN)
doc.addPageTemplates([PageTemplate(id='lh', frames=[frame], onPage=header_footer)])
doc.build(flow)
print('BUILT', OUT)
