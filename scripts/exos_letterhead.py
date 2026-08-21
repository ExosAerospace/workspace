"""Exos letterhead — SINGLE SOURCE OF TRUTH for stationery placement.

Every Exos PDF twin MUST import from here instead of hand-placing the banner.
Geometry is measured from assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx and
locked; do NOT re-tune per document (that drift is the bug we keep re-fixing).

Header logo: 3.15in wide x ~0.65in tall, top-left (~0.13in from left, ~0.10in from top).
Footer logo: 3.745in wide x ~0.615in tall, bottom-left.

Usage (reportlab):
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from exos_letterhead import stationery, MARGINS
    doc = SimpleDocTemplate(OUT, pagesize=letter, **MARGINS)
    doc.build(E, onFirstPage=stationery, onLaterPages=stationery)

Banners live in-repo at assets/letterhead_media/ (NOT /tmp — /tmp vanishes and
is why builds kept coming out wrong).
"""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER_IMG = os.path.join(_ROOT, "assets", "letterhead_media", "header.png")   # 2625x542
FOOTER_IMG = os.path.join(_ROOT, "assets", "letterhead_media", "footer.png")   # 2625x431
GREY = HexColor("#555555")
PW, PH = letter

# ---- LOCKED geometry (inches) — measured from the PRIMARY letterhead .docx ----
_HDR_W, _HDR_NATIVE = 3.15, (2625, 542)     # extent cx=2880360 EMU = 3.15in
_FTR_W, _FTR_NATIVE = 3.745, (2625, 431)    # extent cx=3425190 EMU = 3.745in
_HDR_LEFT, _HDR_TOP = 0.13, 0.10            # insets from page edges
_FTR_LEFT, _FTR_BOTTOM = 0.13, 0.30
def _h(native, w): return w * (native[1] / native[0])   # height locked to native aspect
_HDR_H = _h(_HDR_NATIVE, _HDR_W)
_FTR_H = _h(_FTR_NATIVE, _FTR_W)

# Text-frame margins that clear the stationery. Header logo bottom sits at
# ~0.10+0.65=0.75in; footer logo top at ~0.30+0.615=0.915in. These margins clear both.
MARGINS = dict(leftMargin=1.0*inch, rightMargin=1.0*inch,
               topMargin=1.15*inch, bottomMargin=1.05*inch)

def stationery(canvas, doc, page_note="Proprietary — Unclassified"):
    """reportlab onPage callback: draws the locked header + footer logos + page number."""
    if os.path.exists(HEADER_IMG):
        canvas.drawImage(HEADER_IMG, _HDR_LEFT*inch, PH-_HDR_TOP*inch-_HDR_H*inch,
                         width=_HDR_W*inch, height=_HDR_H*inch, mask='auto')
    if os.path.exists(FOOTER_IMG):
        canvas.drawImage(FOOTER_IMG, _FTR_LEFT*inch, _FTR_BOTTOM*inch,
                         width=_FTR_W*inch, height=_FTR_H*inch, mask='auto')
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(GREY)
    canvas.drawRightString(PW-0.75*inch, 0.35*inch, "%s   |   Page %d" % (page_note, doc.page))

# Back-compat alias
deco = stationery
