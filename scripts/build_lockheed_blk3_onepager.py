#!/usr/bin/env python3
"""Exos BLK3 full-payload SALES one-pager targeted at Lockheed Martin.
Single letter page (8.5x11). Branded navy/gold/orange. Outputs PNG + PDF + docx.
Payload-sale sheet (NOT an investor ask). Facts verified against memory."""
import os, random
from PIL import Image, ImageDraw, ImageFont
random.seed(7)
W, H = 2125, 2750
NAVY=(9,20,42); GOLD=(232,170,60); ORANGE=(233,122,50); WHITE=(255,255,255)
LIGHT=(238,243,248); GREY=(202,214,228); PANEL=(19,40,70); PANEL_BD=(46,82,130)

def F(kind,size):
    paths={'reg':"/System/Library/Fonts/Supplemental/Arial.ttf",
           'bold':"/System/Library/Fonts/Supplemental/Arial Bold.ttf",
           'black':"/System/Library/Fonts/Supplemental/Arial Black.ttf"}
    p=paths[kind]
    if os.path.exists(p):
        try: return ImageFont.truetype(p,size)
        except: pass
    return ImageFont.truetype({'reg':"DejaVuSans.ttf",'bold':"DejaVuSans-Bold.ttf",'black':"DejaVuSans-Bold.ttf"}[kind],size)

def bg():
    img=Image.new("RGB",(W,H),NAVY); d=ImageDraw.Draw(img)
    for y in range(H):
        t=y/H; d.line([(0,y),(W,y)],fill=(int(9+9*t),int(20+16*t),int(42+26*t)))
    glow=Image.new("L",(W,H),0); gd=ImageDraw.Draw(glow); R=1300
    cx,cy=W*0.85,H*0.82
    for r in range(R,0,-6): gd.ellipse([cx-r,cy-r,cx+r,cy+r],fill=int(60*(1-r/R)))
    img.paste(Image.new("RGB",(W,H),ORANGE),(0,0),glow.point(lambda v:int(v*0.42)))
    d=ImageDraw.Draw(img)
    for _ in range(220):
        x,y=random.randint(0,W),random.randint(0,int(H*0.5)); b=random.randint(45,160)
        d.ellipse([x,y,x+2,y+2],fill=(b,b+8,b+22))
    return img

def wrap(d,s,f,mw):
    out=[]
    for para in s.split("\n"):
        ln=""
        for w in para.split():
            t=(ln+" "+w).strip()
            if d.textlength(t,font=f)<=mw: ln=t
            else: out.append(ln); ln=w
        out.append(ln)
    return out

def txt(d,x,y,s,f,fill,mw=None,lh=1.3,sp=0,anchor=None):
    if mw is None:
        d.text((x,y),s,font=f,fill=fill,anchor=anchor); return y+int(f.size*lh)
    yy=y
    for ln in wrap(d,s,f,mw): d.text((x,yy),ln,font=f,fill=fill); yy+=int(f.size*lh)+sp
    return yy

def rr(d,box,r,fill=None,outline=None,wd=3): d.rounded_rectangle(box,radius=r,fill=fill,outline=outline,width=wd)
def panel(d,box): rr(d,box,20,fill=PANEL,outline=PANEL_BD,wd=3)

def section(d,x,y,label):
    d.text((x,y),label,font=F('bold',50),fill=WHITE); d.line([(x,y+72),(x+300,y+72)],fill=GOLD,width=5); return y+112

def card(d,x,y,w,h,head,bullets,head_fill=GOLD):
    panel(d,[x,y,x+w,y+h]); pad=32
    yy=txt(d,x+pad,y+pad,head,F('bold',34),head_fill,mw=w-2*pad,lh=1.12)+12
    fb=F('reg',30)
    for b in bullets:
        d.ellipse([x+pad,yy+12,x+pad+10,yy+22],fill=GOLD)
        yy=txt(d,x+pad+28,yy,b,fb,GREY,mw=w-2*pad-28,lh=1.26,sp=5)+10
    return yy

def build():
    img=bg(); d=ImageDraw.Draw(img); M=55
    # header
    d.text((M,58),"EXOS",font=F('black',52),fill=WHITE)
    d.text((M+230,66),"AEROSPACE",font=F('reg',44),fill=GOLD)
    d.text((W-M,80),"PREPARED FOR LOCKHEED MARTIN  |  JULY 2026",font=F('reg',26),fill=GREY,anchor="ra")
    d.line([(M,168),(W-M,168)],fill=PANEL_BD,width=3)
    # title
    d.text((M,208),"FULL BLK3 PAYLOAD",font=F('black',96),fill=WHITE)
    d.text((M,320),"DEDICATED SUBORBITAL FLIGHT",font=F('black',66),fill=WHITE)
    d.text((M,410),"Reserve the follow-on flight  ·  Late Q1 / early Q2 2027",font=F('bold',34),fill=GOLD)
    txt(d,M,470,"A dedicated, FAA-licensed reusable suborbital flight: ~135 kg to 100+ km, 2-3 day turnaround, at a fraction of legacy flight-test cost.",F('reg',32),GREY,mw=1330,lh=1.3)
    # offer box top-right
    aw,ah=560,300; ax=W-M-aw; ay=205
    rr(d,[ax,ay,ax+aw,ay+ah],22,fill=(15,28,52),outline=GOLD,wd=5)
    d.text((ax+aw//2,ay+26),"THE SLOT",font=F('bold',34),fill=GOLD,anchor="ma")
    d.text((ax+aw//2,ay+74),"T + 3 DAYS",font=F('black',72),fill=WHITE,anchor="ma")
    txt(d,ax+40,ay+178,"Full BLK3 payload · follow-on flight · booking now",F('reg',27),GREY,mw=aw-80,lh=1.28,anchor=None)
    d.text((ax+aw//2,ay+ah-42),"SPACEavailable...™",font=F('bold',30),fill=GOLD,anchor="ma")
    # stat row
    stats=[("135 kg","payload / flight"),("100+ km","suborbital altitude"),("2-3 day","turnaround"),("< 4g","boost, ~7g max shock")]
    sy=600; gap=26; cw=(W-2*M-3*gap)//4
    for i,(big,small) in enumerate(stats):
        x=M+i*(cw+gap); rr(d,[x,sy,x+cw,sy+200],20,fill=LIGHT)
        d.text((x+cw//2,sy+40),big,font=F('black',60),fill=NAVY,anchor="ma")
        d.text((x+cw//2,sy+140),small,font=F('reg',27),fill=(64,76,94),anchor="ma")
    # two-flight campaign
    y=section(d,M,858,"THE TWO-FLIGHT CAMPAIGN")
    cwc=(W-2*M-46)//2; hh=470
    card(d,M,y,cwc,hh,"FLIGHT 1 - FULLY MANIFESTED",
        ["First fully-manifested BLK3 flight carries a Radioactive Heating Unit (RHU) payload.",
         "Demonstrates handling of sensitive, regulated, nuclear-class hardware end to end.",
         "Late Q1 / early Q2 2027 from Spaceport America, New Mexico.",
         "Same airframe recovered and reflown for Flight 2."])
    card(d,M+cwc+46,y,cwc,hh,"FLIGHT 2 - YOURS TO BOOK",
        ["Same vehicle, reflown in 3 days: proven reusable cadence, not a paper claim.",
         "Full 135 kg dedicated payload volume - reserve the entire manifest for Lockheed hardware.",
         "Schedule-certain slot behind an already-manifested lead flight.",
         "SPACEavailable...™ - booking now."],head_fill=ORANGE)
    # why exos
    y=section(d,M,y+hh+52,"WHY EXOS")
    hh2=440
    card(d,M,y,cwc,hh2,"LICENSED & PROVEN",
        ["FAA Part 431 Reusable Launch Vehicle license issued March 13, 2026; transition to Part 450 underway.",
         "One of only three FAA-licensed reusable rocket launch providers in the US.",
         "Veteran-led; commercial successor to Armadillo Aerospace, flying reusable suborbital since 2018."])
    card(d,M+cwc+46,y,cwc,hh2,"BUILT FOR RAPID QUALIFICATION",
        ["Benign ride: <4g boost, ~7g peak transient shock, minutes of microgravity and space exposure.",
         "2-3 day turnaround enables back-to-back qualification campaigns.",
         "Recover, inspect, refly - relaunch at roughly 1% of vehicle cost."])
    # fit for lockheed - wide bar
    y=section(d,M,y+hh2+52,"THE FIT FOR LOCKHEED MARTIN")
    fh=250
    panel(d,[M,y,W-M,y+fh]); pad=32
    cols=[("Rapid, low-cost qualification","De-risk sensitive space hardware on a real flight before orbital or deep-space commitment."),
          ("Nuclear-class heritage","RHU flight experience relevant to RTG, deep-space power, and defense payload programs."),
          ("Schedule-certain access","A dedicated slot with a US-licensed reusable provider, on a near-term, repeatable cadence.")]
    cwf=(W-2*M-2*pad-2*30)//3
    for i,(h,b) in enumerate(cols):
        x=M+pad+i*(cwf+30)
        yy=txt(d,x,y+pad,h,F('bold',30),GOLD,mw=cwf,lh=1.15)+8
        txt(d,x,yy,b,F('reg',27),GREY,mw=cwf,lh=1.26)
    # CTA bar
    yb=y+fh+40
    rr(d,[M,yb,W-M,yb+150],20,fill=(15,28,52),outline=GOLD,wd=4)
    txt(d,M+44,yb+34,"Reserve the follow-on BLK3 flight - full 135 kg payload, late Q1 / early Q2 2027. SPACEavailable...™",F('bold',36),WHITE,mw=W-2*M-88,lh=1.28)
    # footer
    d.rectangle([0,H-110,W,H],fill=(7,14,30))
    d.text((W//2,H-58),"www.exosaero.com     |     John Quinn, CEO     |     jquinn@exosaero.com     |     972-740-8355",font=F('bold',30),fill=GREY,anchor="mm")
    return img

os.makedirs("drafts",exist_ok=True)
img=build()
png="drafts/Exos_Lockheed_BLK3_Payload_OnePager.png"
pdf="drafts/Exos_Lockheed_BLK3_Payload_OnePager.pdf"
docx="drafts/Exos_Lockheed_BLK3_Payload_OnePager.docx"
img.save(png)
img.convert("RGB").save(pdf,resolution=250.0)
from docx import Document; from docx.shared import Inches
doc=Document(); s=doc.sections[0]; s.page_width=Inches(8.5); s.page_height=Inches(11)
s.left_margin=s.right_margin=s.top_margin=s.bottom_margin=Inches(0)
doc.add_picture(png,height=Inches(11.0))
doc.save(docx)
print("BUILT", png)
