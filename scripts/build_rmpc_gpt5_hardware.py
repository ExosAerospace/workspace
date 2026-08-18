#!/usr/bin/env python3
"""
Take the 5 GPT-5 RMPC slides and add the two ACTUAL Type-5 hardware photos
(real linerless composite tanks + real iFEX cryo quick-disconnect coupling),
placed into each slide's emptiest region with a clean frame + small caption
matching the deck's dark style. Real hardware grounds the rendered tanks.

Outputs:
  drafts/rmpc_gpt5/gpt5_hw_p1..p5.png
  RMPC_GPT5_with_Real_Type5_Hardware.pdf
  drafts/Exos_RMPC_GPT5_Hardware.pptx
  /tmp/gpt5_hw_contact.png
"""
import os, glob
from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageFont

ROOT = "/Users/exomac/.openclaw/workspace"
STAGE = os.path.join(ROOT, "media/inbound/openclaw-staged-3641ae71-18fb-4443-99fc-b353649227a1")
OUT = os.path.join(ROOT, "drafts/rmpc_gpt5"); os.makedirs(OUT, exist_ok=True)

SLIDES = sorted(glob.glob(os.path.join(STAGE, "ChatGPT_Image_*")))
TANKS = os.path.join(STAGE, "Screenshot_2026-08-17_161343---35f85154-3f6d-4252-8114-d02f377482ce.png")  # real composite tanks
QD    = os.path.join(STAGE, "Screenshot_2026-08-17_161227---551031e9-10df-463a-9ea6-972ca9a9f9ed.png")  # real iFEX cryo QD

def font(sz):
    for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/Library/Fonts/Arial.ttf"]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, sz)
            except: pass
    return ImageFont.load_default()

def autocrop_black(im, thr=22):
    g = im.convert("L")
    bbox = g.point(lambda p: 255 if p > thr else 0).getbbox()
    return im.crop(bbox) if bbox else im

def framed(im, target_w, caption=None):
    im = im.convert("RGB")
    h = int(im.height * target_w / im.width)
    im = im.resize((target_w, h), Image.LANCZOS)
    im = ImageOps.expand(im, border=1, fill=(90, 100, 115))
    im = ImageOps.expand(im, border=4, fill=(232, 238, 245))   # white hairline frame
    if caption:
        cf = font(max(15, target_w // 22))
        d0 = ImageDraw.Draw(im)
        tw = d0.textlength(caption, font=cf); th = (cf.size + 8)
        bar = Image.new("RGB", (im.width, th), (10, 20, 38))
        bd = ImageDraw.Draw(bar)
        bd.text(((im.width - tw)//2, 4), caption, font=cf, fill=(210, 225, 245))
        stacked = Image.new("RGB", (im.width, im.height + th), (10, 20, 38))
        stacked.paste(im, (0, 0)); stacked.paste(bar, (0, im.height))
        im = ImageOps.expand(stacked, border=1, fill=(70, 85, 105))
    return im

def activity_map(img, gs=48):
    small = img.convert("L").resize((gs, gs), Image.BILINEAR)
    px = small.load()
    import statistics
    # local score = brightness + edge energy (diff to neighbors)
    score = [[0.0]*gs for _ in range(gs)]
    for y in range(gs):
        for x in range(gs):
            v = px[x, y]; e = 0
            if x+1 < gs: e += abs(px[x+1, y]-v)
            if y+1 < gs: e += abs(px[x, y+1]-v)
            score[y][x] = v*0.5 + e*2.0
    return score

def find_empty_box(img, bw, bh, ytop_frac=0.12, ybot_frac=0.93, prefer=None):
    W, H = img.size; gs = 48
    sc = activity_map(img, gs)
    cw = max(1, int(bw/W*gs)); ch = max(1, int(bh/H*gs))
    y0 = int(ytop_frac*gs); y1 = int(ybot_frac*gs) - ch
    best = None
    for gy in range(y0, max(y0+1, y1)):
        for gx in range(0, gs-cw):
            s = sum(sc[yy][xx] for yy in range(gy, gy+ch) for xx in range(gx, gx+cw))
            # bias toward preferred corner
            if prefer == "br": s -= (gx + gy)*0.0
            cand = (s, gx, gy)
            if best is None or cand[0] < best[0]: best = cand
    _, gx, gy = best
    return int(gx/gs*W), int(gy/gs*H)

def shadow_paste(page, tile, xy):
    x, y = xy; b = 14
    sh = Image.new("RGBA", (tile.width+4*b, tile.height+4*b), (0,0,0,0))
    sh.paste(Image.new("RGBA", tile.size, (0,0,0,150)), (2*b, 2*b))
    sh = sh.filter(ImageFilter.GaussianBlur(b))
    page.paste(sh, (x-2*b+8, y-2*b+10), sh)
    page.paste(tile, (x, y))

tanks_img = autocrop_black(Image.open(TANKS))
qd_img = autocrop_black(Image.open(QD))

# explicit placement (seen all 5 slides): (photo, x_frac, y_frac, w_frac, caption)
PLAN = {
    0: [(tanks_img, 0.720, 0.135, 0.250, "Actual Type-5 composite tanks"),
        (qd_img,    0.018, 0.130, 0.120, "iFEX cryo quick-disconnect")],
    2: [(tanks_img, 0.775, 0.815, 0.135, None)],   # into SUBORBITAL TANK TEST HERITAGE box
    4: [(tanks_img, 0.035, 0.195, 0.150, None)],   # into panel 1 "Suborbital tank test"
}

pages = []
for idx, sfile in enumerate(SLIDES):
    page = Image.open(sfile).convert("RGB")
    W, H = page.size
    for (photo, xf, yf, wfrac, cap) in PLAN.get(idx, []):
        tile = framed(photo, int(W*wfrac), caption=cap)
        shadow_paste(page, tile, (int(W*xf), int(H*yf)))
    out = os.path.join(OUT, f"gpt5_hw_p{idx+1}.png")
    page.save(out); pages.append(page)
    print(f"slide {idx+1}: added {len(PLAN.get(idx,[]))} real photo(s) -> {os.path.basename(out)}")

pdf = os.path.join(ROOT, "RMPC_GPT5_with_Real_Type5_Hardware.pdf")
pages[0].save(pdf, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
print("PDF ->", pdf)

try:
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    for i in range(len(pages)):
        s = prs.slides.add_slide(blank)
        s.shapes.add_picture(os.path.join(OUT, f"gpt5_hw_p{i+1}.png"), 0, 0,
                             width=prs.slide_width, height=prs.slide_height)
    pptx = os.path.join(ROOT, "drafts/Exos_RMPC_GPT5_Hardware.pptx")
    prs.save(pptx); print("PPTX ->", pptx)
except Exception as e:
    print("PPTX skipped:", e)

# contact sheet
th = [p.copy() for p in pages]
for t in th: t.thumbnail((560, 560))
cols=2; cw=max(t.width for t in th); ch=max(t.height for t in th)
rows=(len(th)+cols-1)//cols
cs=Image.new("RGB",(cols*cw+(cols+1)*8, rows*ch+(rows+1)*8),(16,16,20))
for i,t in enumerate(th):
    r,c=divmod(i,cols); cs.paste(t,(8+c*(cw+8),8+r*(ch+8)))
cs.save("/tmp/gpt5_hw_contact.png"); print("contact -> /tmp/gpt5_hw_contact.png")
