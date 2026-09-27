#!/usr/bin/env python3
"""IDJ 3-min investor deck v6 (16:9, editable) — VISUAL-FIRST rebuild per Innovation Dojo feedback.
IDJ 2026-09-24: (1) visuals > text; (2) Slide 5 must show raise amount, investor returns
(profit growth + exit), structured rounds, and alternatives (payload pre-sale / crowdfunding).
Exos brand: black/grey base + orange (#F26A21) accent, planet backdrop, white logo, SPACEavailable lockup.
Orange [ ] brackets = pending John inputs (securities figures / exit line — John + counsel to confirm)."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches as I, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

WS="/Users/exomac/.openclaw/workspace"
OUT=os.path.join(WS,"drafts","Exos_JP_3min_InvestorPitch_IDJ_BRANDED_v6_2026-09-27.pptx")
LOGO=os.path.join(WS,"drafts","_exos_white_official.png")
LOCKUP=os.path.join(WS,"drafts","_spaceavailable_white.png")
PLANET=os.path.join(WS,"drafts","_exos_planet_b.png")

BG=RGBColor(0x0d,0x0d,0x0f); PANEL=RGBColor(0x17,0x18,0x1c); PANEL2=RGBColor(0x1f,0x20,0x25)
ORANGE=RGBColor(0xF2,0x6A,0x21); ORANGED=RGBColor(0x7a,0x36,0x12)
WHITE=RGBColor(0xFF,0xFF,0xFF); GREY=RGBColor(0xD2,0xD2,0xD7); MUTE=RGBColor(0x9a,0x9a,0xa1)

# --- darkened planet hero backdrop (baked once) ---
TBG=os.path.join(WS,"drafts","_exos_slide_bg.png")
W,H=2000,1125
im=Image.open(PLANET).convert("RGB"); iw,ih=im.size; sc=max(W/iw,H/ih)
im=im.resize((int(iw*sc),int(ih*sc))); iw,ih=im.size
im=im.crop(((iw-W)//2,(ih-H)//2,(iw-W)//2+W,(ih-H)//2+H))
scrim=Image.new("L",(1,H))
for y in range(H):
    t=y/(H-1); a=0.86-0.18*min(t/0.5,1) if t<0.5 else 0.68+0.20*((t-0.5)/0.5)
    scrim.putpixel((0,y),int(a*255))
scrim=scrim.resize((W,H))
Image.composite(Image.new("RGB",(W,H),(0,0,0)),im,scrim).save(TBG)

p=Presentation(); p.slide_width=I(13.333); p.slide_height=I(7.5); BL=p.slide_layouts[6]
def slide(): return p.slides.add_slide(BL)

def _noshadow(sh): sh.shadow.inherit=False
def rect(s,x,y,w,h,fill,line=None,lw=1.0,rounded=False):
    shp=MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    sh=s.shapes.add_shape(shp,I(x),I(y),I(w),I(h))
    if rounded:
        try: sh.adjustments[0]=0.06
        except Exception: pass
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb=fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb=line; sh.line.width=Pt(lw)
    _noshadow(sh); return sh
def circle(s,x,y,d,fill,line=None,lw=1.5):
    sh=s.shapes.add_shape(MSO_SHAPE.OVAL,I(x),I(y),I(d),I(d))
    if fill is None: sh.fill.background()
    else: sh.fill.solid(); sh.fill.fore_color.rgb=fill
    if line is None: sh.line.fill.background()
    else: sh.line.color.rgb=line; sh.line.width=Pt(lw)
    _noshadow(sh); return sh
def tb(s,x,y,w,h,anchor=MSO_ANCHOR.TOP):
    b=s.shapes.add_textbox(I(x),I(y),I(w),I(h)); tf=b.text_frame; tf.word_wrap=True; tf.vertical_anchor=anchor
    for m in ('margin_left','margin_right','margin_top','margin_bottom'): setattr(tf,m,0)
    return tf
def para(tf,runs,size,color,bold=False,first=False,sp=1.0,before=0,align=PP_ALIGN.LEFT):
    pr=tf.paragraphs[0] if first else tf.add_paragraph()
    pr.alignment=align; pr.line_spacing=sp; pr.space_before=Pt(before); pr.space_after=Pt(0)
    if isinstance(runs,str): runs=[(runs,color,bold)]
    for txt,c,b in runs:
        r=pr.add_run(); r.text=txt; f=r.font; f.size=Pt(size); f.bold=b; f.color.rgb=c; f.name="Arial"
    return pr
def kicker(s,x,y,text):
    t=tb(s,x,y,11,0.3); para(t,text.upper(),12,ORANGE,True,first=True)
def chrome(s,title,kick=None):
    rect(s,0,0,13.333,7.5,BG); s.shapes.add_picture(LOGO,I(11.9),I(0.42),height=I(0.32))
    yt=0.52
    if kick: kicker(s,0.64,0.44,kick); yt=0.74
    t=tb(s,0.62,yt,10.9,0.9); para(t,title,30,WHITE,True,first=True)
    rect(s,0.66,yt+0.78,1.15,0.055,ORANGE)
def herobg(s):
    rect(s,0,0,13.333,7.5,BG); s.shapes.add_picture(TBG,I(0),I(0),I(13.333),I(7.5))
    s.shapes.add_picture(LOGO,I(0.62),I(0.55),height=I(0.6)); s.shapes.add_picture(LOCKUP,I(10.4),I(0.62),width=I(2.3))

def stat_tile(s,x,y,w,h,num,label,sub=None):
    rect(s,x,y,w,h,PANEL,rounded=True); rect(s,x,y,0.08,h,ORANGE)  # orange spine
    t=tb(s,x+0.32,y+0.30,w-0.5,1.0); para(t,num,40,ORANGE,True,first=True,sp=0.95)
    t=tb(s,x+0.34,y+1.28,w-0.6,h-1.4)
    para(t,label,15.5,WHITE,True,first=True,sp=1.05)
    if sub: para(t,sub,12.5,MUTE,False,before=6,sp=1.05)

def icon_card(s,x,y,w,h,glyph,title,body):
    rect(s,x,y,w,h,PANEL,rounded=True)
    circle(s,x+0.34,y+0.34,0.62,None,ORANGE,2.0)
    g=tb(s,x+0.34,y+0.34,0.62,0.62,MSO_ANCHOR.MIDDLE); para(g,glyph,22,ORANGE,True,first=True,align=PP_ALIGN.CENTER)
    t=tb(s,x+0.32,y+1.15,w-0.62,h-1.25)
    para(t,title,15.5,WHITE,True,first=True,sp=1.03)
    para(t,body,12.5,GREY,False,before=6,sp=1.08)

def chip(s,x,y,w,text,fill=PANEL2,fg=GREY,line=None):
    rect(s,x,y,w,0.5,fill,line=line,rounded=True)
    t=tb(s,x+0.15,y,w-0.3,0.5,MSO_ANCHOR.MIDDLE); para(t,text,12,fg,True,first=True,align=PP_ALIGN.CENTER,sp=1.0)

# ============================================================ SLIDE 1 — HERO
s=slide(); herobg(s)
t=tb(s,0.7,2.55,12,1.0); para(t,[("Exos Aerospace  ",WHITE,True),("—",ORANGE,True),("  Expanding to Japan",WHITE,True)],42,WHITE,True,first=True)
t=tb(s,0.72,3.66,12,0.6); para(t,"A Partnership & Investment Opportunity — Exos Aerospace Japan (K.K.)",22,ORANGE,True,first=True)
t=tb(s,0.72,4.55,12,0.9)
para(t,"With appreciation to Innovation Dojo — Black Belt Venture Studio   ·   8 October 2026",15,GREY,False,first=True)
para(t,"Toshi Kumazawa (Japan BD)   ·   John Quinn (Co-founder & CEO)",14,MUTE,False,before=5)
t=tb(s,0.72,6.98,12,0.4); para(t,"v6 — John's inputs locked 27 Sep 2026; Toshi finalizes Japanese / keigo",9.5,ORANGE,False,first=True)

# ============================================================ SLIDE 2 — WHO WE ARE (stat tiles)
s=slide(); chrome(s,"Who we are",kick="Proven · profitable · reusable")
tw=3.92; gap=0.31; x0=0.66; y=2.05; th=2.55
stat_tile(s,x0,y,tw,th,"3","of only 3 U.S. companies FAA-licensed for reusable launch operations","alongside SpaceX and Blue Origin")
stat_tile(s,x0+tw+gap,y,tw,th,"25+ yrs","hands-on reusable-vehicle heritage","predecessor: Armadillo Aerospace")
stat_tile(s,x0+2*(tw+gap),y,tw,th,"$1.49M","2025 revenue — profitable: EBITDA $254K (17% margin)","FY2025, accrual basis, unaudited")
t=tb(s,0.66,4.95,12,0.5); para(t,"A real operating company with flight heritage — not a concept.",16,GREY,True,first=True)

# ============================================================ SLIDE 3 — TECHNOLOGY (icon cards)
s=slide(); chrome(s,"Proven, differentiated technology",kick="What sets us apart")
cw=3.92; gap=0.31; x0=0.66; y=2.0; ch=3.55
icon_card(s,x0,y,cw,ch,"▲","BLK3 reusable vehicle","Suborbital launch vehicle: out-of-autoclave carbon composite, low parts count — recovered and reflown.")
icon_card(s,x0+cw+gap,y,cw,ch,"◆","TRL-9 Type-5 cryo tanks","Linerless composite cryogenic tanks (affiliate Scorpius / SSLC) — lighter and more robust than metal.")
icon_card(s,x0+2*(cw+gap),y,cw,ch,"☾","Proven on the Moon","Scorpius Type-5 tanks flew as fuel & LOX tanks aboard Intuitive Machines' Odysseus (2024) and Athena landers.")

# ============================================================ SLIDE 4 — COMMITMENT TO JAPAN (quadrants)
s=slide(); chrome(s,"Our commitment to Japan",kick="Built in Japan, together with Japan")
qw=5.95; qh=1.72; gx=0.66; gy=2.02; gp=0.28
def quad(x,y,glyph,title,body):
    rect(s,x,y,qw,qh,PANEL,rounded=True)
    circle(s,x+0.3,y+0.3,0.54,None,ORANGE,2.0)
    g=tb(s,x+0.3,y+0.3,0.54,0.54,MSO_ANCHOR.MIDDLE); para(g,glyph,18,ORANGE,True,first=True,align=PP_ALIGN.CENTER)
    t=tb(s,x+1.05,y+0.24,qw-1.25,qh-0.4)
    para(t,title,15,WHITE,True,first=True,sp=1.0); para(t,body,12,GREY,False,before=5,sp=1.05)
quad(gx,gy,"社","Exos Aerospace Japan (K.K.)","A local company, office, and team — opening in 2026.")
quad(gx+qw+gp,gy,"↑","HOSPO wet-lease flights","BLK3 reusable suborbital flight services at Hokkaido Spaceport, with Exos as licensed operator.")
quad(gx,gy+qh+gp,"⚙","Serve industry & universities","BLK3 verification / flight-test platform, reusable engines, and SSLC Type-5 cryo tanks.")
quad(gx+qw+gp,gy+qh+gp,"◇","Consulting & collaboration","Long-term partnership — building space capability in Japan, together with Japan.")

# ============================================================ SLIDE 5 — INVESTMENT OPPORTUNITY (the redesign)
s=slide(); chrome(s,"The investment opportunity",kick="Slide 5 · structured round · returns · exit")
# LEFT — the ask
ax,ay,aw,ah=0.66,1.95,3.55,3.05
rect(s,ax,ay,aw,ah,PANEL,rounded=True); rect(s,ax,ay,aw,0.09,ORANGE)
t=tb(s,ax+0.3,ay+0.28,aw-0.6,0.4); para(t,"JAPAN ROUND — REG S, VIA EAI LLC",11,MUTE,True,first=True)
t=tb(s,ax+0.3,ay+0.66,aw-0.6,0.9); para(t,[("¥790M",ORANGE,True)],38,ORANGE,True,first=True,sp=0.95)
t=tb(s,ax+0.3,ay+1.5,aw-0.6,0.4); para(t,"≈ US$5.0M target  (at ~¥157 / US$)",12.5,ORANGE,True,first=True)
t=tb(s,ax+0.3,ay+1.95,aw-0.6,1.0)
para(t,"Purchase units in Exos Aerospace Investments, LLC (EAI); EAI units mirror Exos U.S. shares, and proceeds fund the wholly-owned Japan K.K.",12.5,GREY,False,first=True,sp=1.1)
para(t,"Offshore Regulation S offering — separate from the Exos U.S. domestic offering.",12,MUTE,False,before=6,sp=1.1)
# RIGHT TOP — use of funds chips
ux=4.5; uy=1.9
t=tb(s,ux,uy,8.1,0.35); para(t,"USE OF FUNDS",11,MUTE,True,first=True)
uf=["Stand up Japan operations","Secure a wet-lease BLK3 for HOSPO","Open the Japan office (2026)","Build the local team"]
cwid=[3.55,3.95]; ccols=[ux,ux+4.05]
for i,label in enumerate(uf):
    cx=ccols[i%2]; cy=uy+0.38+(i//2)*0.6; chip(s,cx,cy,cwid[i%2] if i%2 else cwid[0],label)
# RIGHT MID — round / return / exit timeline
ty=3.55
t=tb(s,ux,ty,8.1,0.35); para(t,"PATH TO RETURNS — GROW, THEN EXIT",11,MUTE,True,first=True)
steps=[("ROUND (now)","Fund Japan stand-up + first wet-lease flights"),
       ("SCALE","Recurring revenue: wet-lease flights · Type-5 tank & engine sales · verification & consulting"),
       ("EXIT","Liquidity through an Exos U.S. event (public listing or acquisition), realized via EAI LLC. Horizon ~3+ yrs.")]
sw=2.55; sg=0.18; sx=ux
for i,(hd,bd) in enumerate(steps):
    x=sx+i*(sw+sg)
    rect(s,x,ty+0.38,sw,1.4,PANEL2,rounded=True); rect(s,x,ty+0.38,sw,0.07,ORANGE)
    tt=tb(s,x+0.2,ty+0.52,sw-0.35,0.4); para(tt,hd,13,ORANGE,True,first=True)
    bt=tb(s,x+0.2,ty+0.9,sw-0.35,0.82); para(bt,bd,10.5,GREY,False,first=True,sp=1.06)
    if i<2:
        ar=s.shapes.add_shape(MSO_SHAPE.CHEVRON,I(x+sw+0.0),I(ty+0.9),I(sg+0.04),I(0.3))
        ar.fill.solid(); ar.fill.fore_color.rgb=ORANGE; ar.line.fill.background(); _noshadow(ar)
# BOTTOM — alternatives strip (IDJ suggestion)
by=5.55
rect(s,0.66,by,12.0,1.12,PANEL,rounded=True); rect(s,0.66,by,0.09,1.12,ORANGE)
t=tb(s,0.95,by+0.16,11.6,0.35); para(t,[("ALSO ON THE TABLE — non-dilutive layers  ",ORANGE,True),("(alongside equity, per IDJ)",MUTE,False)],11.5,ORANGE,True,first=True)
chip(s,0.95,by+0.55,3.6,"Payload pre-sales — reserve BLK3 flight capacity",PANEL2,GREY,ORANGED)
chip(s,4.75,by+0.55,3.6,"Crowdfunding — community & fan participation",PANEL2,GREY,ORANGED)
chip(s,8.55,by+0.55,3.9,"Staged equity rounds — realistic financing",PANEL2,GREY,ORANGED)
t=tb(s,0.66,6.72,12,0.45); para(t,"Not an offer to sell or a solicitation of an offer to buy securities. Units of Exos Aerospace Investments, LLC are offered only to non-U.S. persons in offshore transactions under Regulation S, separate from any U.S. offering, and only through definitive offering documents. Not registered under the U.S. Securities Act; may not be offered or sold in the U.S. or to U.S. persons absent registration or an exemption.",8.5,MUTE,False,first=True)

# ============================================================ SLIDE 6 — TRACTION (milestone tiles)
s=slide(); chrome(s,"Traction & the path forward",kick="Real signal, on the ground")
mw=5.95; mh=1.72; gx=0.66; gy=2.02; gp=0.28
def milestone(x,y,tag,title,body):
    rect(s,x,y,mw,mh,PANEL,rounded=True); rect(s,x,y,0.08,mh,ORANGE)
    tt=tb(s,x+0.3,y+0.22,mw-0.5,0.3); para(tt,tag,10.5,ORANGE,True,first=True)
    b=tb(s,x+0.3,y+0.52,mw-0.55,mh-0.6)
    para(b,title,14,WHITE,True,first=True,sp=1.0); para(b,body,11.5,GREY,False,before=4,sp=1.06)
milestone(gx,gy,"DEMAND","LOI + inbound inquiry","Letter of intent for a fuel-tank order from a Japanese space-development company; an engine-specification inquiry as well.")
milestone(gx+mw+gp,gy,"PARTNER","HOSPO discussions underway","Collaboration talks in progress with Hokkaido Spaceport (HOSPO / Space Cotan).")
milestone(gx,gy+mh+gp,"IN-PERSON","CEO in Japan — October 2026","John Quinn will meet HOSPO, the LOI client, other space-development companies, and prospective investors.")
milestone(gx+mw+gp,gy+mh+gp,"LOCALIZE","JP production partners","Seeking Japanese technical partners for licensed production of TRL-9 Type-5 tanks in Japan. BLK3-for-Japan production commences upon international approvals (incl. U.S. export), with potential reallocation of U.S. BLK3 assets to match the speed of those approvals.")

# ============================================================ SLIDE 7 — THANK YOU
s=slide(); herobg(s)
t=tb(s,0.7,2.55,12,1.0); para(t,"Thank you",44,ORANGE,True,first=True)
t=tb(s,0.72,3.7,12,2.2)
para(t,[("▪  ",ORANGE,True),("We are honored to explore this partnership with the Japanese space community",GREY,False)],17,GREY,first=True)
para(t,[("▪  ",ORANGE,True),("Reusable space capability and lunar-proven tank technology — built in Japan, together with Japan",GREY,False)],17,GREY,before=10)
para(t,[("▪  ",ORANGE,True),("We warmly invite investors and technical partners to build it with us — office opening 2026",GREY,False)],17,GREY,before=10)
para(t,[("▪  ",ORANGE,True),("Contact: Toshi Kumazawa · toshihisa@exosaero.com  ·  John Quinn, Co-founder & CEO",GREY,False)],17,GREY,before=10)

p.save(OUT); print("SAVED",OUT,os.path.getsize(OUT))
