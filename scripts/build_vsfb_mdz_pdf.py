#!/usr/bin/env python3
"""Letterhead-matched PDF twin of the Exos VSFB MDZ whitepaper (reportlab; no soffice).
Run: python3 scripts/build_vsfb_mdz_pdf.py
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from exos_letterhead import stationery, MARGINS
import vsfb_mdz_content as K

OUT = "drafts/VSFB_MDZ/Exos_VSFB_MDZ_Whitepaper_%s%s.pdf" % (K.DATE, K.VER)
NAVY = HexColor("#0A3D7C"); DARK = HexColor("#1A1A1A"); GREY = HexColor("#555555")
RED = HexColor("#9A1B1B"); YEL = HexColor("#FFF4CC"); GOLD = HexColor("#C9A227"); LINE = HexColor("#9AA5B1")
ss = getSampleStyleSheet()
def S(n, **kw):
    kw.setdefault("fontName", "Helvetica"); kw.setdefault("textColor", DARK)
    return ParagraphStyle(n, parent=ss["Normal"], **kw)
st = {
 "title": S("t", fontSize=20, leading=24, alignment=TA_CENTER, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=6),
 "title2": S("t2", fontSize=14.5, leading=18, alignment=TA_CENTER, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4),
 "sub": S("s", fontSize=10.5, leading=13.5, alignment=TA_CENTER, textColor=GREY, fontName="Helvetica-Oblique", spaceAfter=3),
 "cover": S("c", fontSize=10.5, leading=14, alignment=TA_CENTER, spaceAfter=1),
 "note": S("n", fontSize=8.5, leading=11, textColor=GREY, fontName="Helvetica-Oblique", spaceAfter=6),
 "h1": S("h1", fontSize=13, leading=16, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4, keepWithNext=1),
 "h2": S("h2", fontSize=11, leading=13.5, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=7, spaceAfter=3, keepWithNext=1),
 "p": S("p", fontSize=10, leading=13.2, alignment=TA_JUSTIFY, spaceAfter=5),
 "bl": S("b", fontSize=10, leading=13, leftIndent=16, bulletIndent=4, spaceAfter=3),
 "src": S("src", fontSize=8, leading=10.2, spaceAfter=2),
 "cell": S("cell", fontSize=8.6, leading=10.6),
 "cellh": S("cellh", fontSize=8.6, leading=10.6, textColor=white, fontName="Helvetica-Bold"),
 "dec": S("dec", fontSize=9, leading=11.5, textColor=RED),
}
def md(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)

E = []
for blk in K.C:
    k = blk[0]
    if k in ("title", "title2", "sub", "cover", "note", "h1", "h2", "p", "src"):
        E.append(Paragraph(md(blk[1]), st[k]))
    elif k == "spacer": E.append(Spacer(1, 0.18*inch))
    elif k == "bl":
        for b in blk[1]: E.append(Paragraph(md(b), st["bl"], bulletText="•"))
    elif k == "pb": E.append(PageBreak())
    elif k == "table":
        rows, w = blk[1], blk[2]; scale = 6.5 / sum(w)
        data = [[Paragraph(md(c), st["cellh"] if i == 0 else st["cell"]) for c in r] for i, r in enumerate(rows)]
        t = Table(data, colWidths=[x*scale*inch for x in w], repeatRows=1)
        sty = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("BACKGROUND", (0, 0), (-1, 0), NAVY),
               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        for i, r in enumerate(rows[1:], 1):
            for j, c in enumerate(r):
                if "[JON" in c or "[ENG" in c or "[PLANNING" in c: sty.append(("BACKGROUND", (j, i), (j, i), YEL))
        t.setStyle(TableStyle(sty)); E.append(t); E.append(Spacer(1, 6))
    elif k == "decision":
        t = Table([[Paragraph(md(blk[1]), st["dec"])]], colWidths=[6.5*inch])
        t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.8, GOLD), ("BACKGROUND", (0, 0), (-1, -1), YEL),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        E.append(t); E.append(Spacer(1, 6))

def page(c, d):
    stationery(c, d, page_note="Exos Proprietary — Unclassified")
    c.saveState(); c.setFont("Helvetica-Bold", 8); c.setFillColor(RED)
    c.drawRightString(letter[0]-0.75*inch, letter[1]-0.45*inch, K.MARK + "  ·  VSFBMDZCall")
    c.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=letter, title="Exos Aerospace — VSFBMDZCall Whitepaper",
                        author="Exos Aerospace Systems & Technologies, Inc.", **MARGINS)
doc.build(E, onFirstPage=page, onLaterPages=page)
print("wrote", OUT)
