#!/usr/bin/env python3
"""
Combine the 5 NASA TechLeap RMPC concept pages into one visual set, each grounded
with a REAL Exos/Scorpius hardware photo composited into the page's emptiest corner.
TEXT-FREE by design (prior RMPC visual was rejected for labels/callouts) — images only.

Outputs:
  drafts/rmpc_combined/rmpc_c1..c5.png   (composited pages)
  RMPC_Visual_Representation_COMBINED.pdf (5-page submission-grade visual)
  drafts/Exos_RMPC_Visual_Combined.pptx   (editable, one full-bleed slide per page)
  /tmp/rmpc_combined_contact.png          (review contact sheet)
"""
import os
from PIL import Image, ImageFilter, ImageOps

ROOT = "/Users/exomac/.openclaw/workspace"
OUTDIR = os.path.join(ROOT, "drafts/rmpc_combined")
os.makedirs(OUTDIR, exist_ok=True)

# (concept page, real hardware inset, corner, orientation)
#  corners: tl, tr, bl, br
PLAN = [
    ("rmpc_p1.png", "drafts/hw_timeline_imgs/s18_6.png",                 "bl", "portrait"),   # on-orbit refuel <- Type-5 tank on the Moon (flight-proven)
    ("rmpc_p2.png", "assets/navy-deck/cryo_tanks.png",                   "tl", "land"),       # Type-5 module   <- real 3-tank VTVL hardware
    ("rmpc_p3.png", "drafts/hw_timeline_imgs/s18_4.png",                 "bl", "portrait"),   # cryo QD couple  <- BLK3 reusable vehicle, vertical
    ("rmpc_p4.png", "assets/navy-deck/blk3_hangar.jpeg",                 "tl", "land"),       # tank-to-tank    <- BLK3 real vehicle in hangar (human scale)
    ("rmpc_p5.png", "assets/navy-deck/vtvl_hover.png",                   "tr", "land"),       # ground cryo-fill<- reusable VTVL hover (fuel it -> fly it)
]

MARGIN = 30
BORDER = 5           # white hairline frame
SHADOW_BLUR = 14
SHADOW_OFF = (10, 12)

def framed(inset, target_w=None, target_h=None):
    im = inset.convert("RGB")
    if target_h:
        w = int(im.width * target_h / im.height); im = im.resize((w, target_h), Image.LANCZOS)
    else:
        h = int(im.height * target_w / im.width); im = im.resize((target_w, h), Image.LANCZOS)
    # white frame
    im = ImageOps.expand(im, border=BORDER, fill=(255, 255, 255))
    # subtle inner line
    im = ImageOps.expand(im, border=1, fill=(120, 130, 140))
    return im

def paste_with_shadow(page, tile, xy):
    x, y = xy
    # shadow
    sh = Image.new("RGBA", (tile.width + 4*SHADOW_BLUR, tile.height + 4*SHADOW_BLUR), (0, 0, 0, 0))
    blk = Image.new("RGBA", (tile.width, tile.height), (0, 0, 0, 150))
    sh.paste(blk, (2*SHADOW_BLUR, 2*SHADOW_BLUR))
    sh = sh.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))
    page.paste(sh, (x - 2*SHADOW_BLUR + SHADOW_OFF[0], y - 2*SHADOW_BLUR + SHADOW_OFF[1]), sh)
    page.paste(tile, (x, y))

def corner_xy(corner, W, H, tw, th):
    if corner == "tl": return (MARGIN, MARGIN)
    if corner == "tr": return (W - tw - MARGIN, MARGIN)
    if corner == "bl": return (MARGIN, H - th - MARGIN)
    return (W - tw - MARGIN, H - th - MARGIN)

pages = []
for pfile, ifile, corner, orient in PLAN:
    page = Image.open(os.path.join(ROOT, pfile)).convert("RGB")
    W, H = page.size
    inset = Image.open(os.path.join(ROOT, ifile))
    if orient == "portrait":
        tile = framed(inset, target_h=int(H * 0.46))
    else:
        tile = framed(inset, target_w=int(W * 0.28))
    xy = corner_xy(corner, W, H, tile.width, tile.height)
    paste_with_shadow(page, tile, xy)
    out = os.path.join(OUTDIR, "rmpc_c%s.png" % pfile[6])
    page.save(out, "PNG")
    pages.append(page)
    print("composited", os.path.basename(out), "inset:", os.path.basename(ifile), "@", corner)

# ---- multi-page PDF ----
pdf = os.path.join(ROOT, "RMPC_Visual_Representation_COMBINED.pdf")
pages[0].save(pdf, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
print("PDF ->", pdf)

# ---- editable PPTX (full-bleed image per slide, 16:9) ----
try:
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    for i in range(1, 6):
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(os.path.join(OUTDIR, "rmpc_c%d.png" % i), 0, 0,
                             width=prs.slide_width, height=prs.slide_height)
    pptx = os.path.join(ROOT, "drafts/Exos_RMPC_Visual_Combined.pptx")
    prs.save(pptx); print("PPTX ->", pptx)
except Exception as e:
    print("PPTX skipped:", e)

# ---- review contact sheet ----
cs_cols, cs_w = 2, 700
thumbs = [p.copy() for p in pages]
for t in thumbs: t.thumbnail((cs_w, cs_w))
rows = (len(thumbs) + cs_cols - 1)//cs_cols
cw = max(t.width for t in thumbs); ch = max(t.height for t in thumbs)
sheet = Image.new("RGB", (cs_cols*cw + (cs_cols+1)*10, rows*ch + (rows+1)*10), (18, 18, 22))
for i, t in enumerate(thumbs):
    r, c = divmod(i, cs_cols)
    sheet.paste(t, (10 + c*(cw+10), 10 + r*(ch+10)))
sheet.save("/tmp/rmpc_combined_contact.png")
print("contact -> /tmp/rmpc_combined_contact.png")
