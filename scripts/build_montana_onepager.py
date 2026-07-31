#!/usr/bin/env python3
"""Exos Montana Program one-pager (11x17, 2 pages). Edit CONTENT + re-run.
v2 2026-06-28: large print-scale fonts, fills the full page, concise scannable copy.
Outputs PNGs + PDF (primary) + 11x17 docx (height-fit, no blank page)."""
import os, random
from PIL import Image, ImageDraw, ImageFont
random.seed(7)
W,H=2200,3400
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
    glow=Image.new("L",(W,H),0); gd=ImageDraw.Draw(glow); R=1500
    cx,cy=W*0.85,H*0.78
    for r in range(R,0,-6): gd.ellipse([cx-r,cy-r,cx+r,cy+r],fill=int(60*(1-r/R)))
    img.paste(Image.new("RGB",(W,H),ORANGE),(0,0),glow.point(lambda v:int(v*0.45)))
    d=ImageDraw.Draw(img)
    for _ in range(260):
        x,y=random.randint(0,W),random.randint(0,int(H*0.55)); b=random.randint(45,160)
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
def panel(d,box): rr(d,box,22,fill=PANEL,outline=PANEL_BD,wd=3)

def section(d,x,y,label):
    d.text((x,y),label,font=F('bold',60),fill=WHITE); d.line([(x,y+86),(x+340,y+86)],fill=GOLD,width=6); return y+130

def card(d,x,y,w,h,head,bullets):
    panel(d,[x,y,x+w,y+h]); pad=36
    yy=txt(d,x+pad,y+pad,head,F('bold',38),GOLD,mw=w-2*pad,lh=1.12)+14
    fb=F('reg',33)
    for b in bullets:
        d.ellipse([x+pad,yy+13,x+pad+11,yy+24],fill=GOLD)
        yy=txt(d,x+pad+30,yy,b,fb,GREY,mw=w-2*pad-30,lh=1.28,sp=6)+11
    return yy

def header(d,img,sub):
    d.text((60,72),"EXOS",font=F('black',58),fill=WHITE)
    d.text((250,80),"AEROSPACE",font=F('reg',50),fill=GOLD)
    d.text((W-60,94),sub,font=F('reg',30),fill=GREY,anchor="ra")
    d.line([(60,205),(W-60,205)],fill=PANEL_BD,width=3)

def footer(d,t):
    d.rectangle([0,H-130,W,H],fill=(7,14,30)); d.text((W//2,H-65),t,font=F('bold',32),fill=GREY,anchor="mm")

# ===================== PAGE 1 =====================
def page1():
    img=bg(); d=ImageDraw.Draw(img); M=60
    header(d,img,"PREPARED FOR MONTANA / TOWNSEND SITE VISIT   |   MAY 2026")
    d.text((M,270),"MONTANA AEROSPACE",font=F('black',104),fill=WHITE)
    d.text((M,392),"ECONOMIC DEVELOPMENT",font=F('black',84),fill=WHITE)
    d.text((M,492),"PROGRAM",font=F('black',84),fill=WHITE)
    d.text((M,608),"Precision Suborbital Launch   |   Workforce Development   |   Pathway to Polar Orbit",font=F('bold',40),fill=GOLD)
    txt(d,M,676,"A practical, near-term spaceport catalyst built around two reusable, FAA-licensed suborbital launch vehicles.",F('reg',38),GREY,mw=1360)
    # ASK card (wide; sits top-right, clears the title and the subtitle below it)
    aw,ah=600,340; ax=W-M-aw; ay=250
    rr(d,[ax,ay,ax+aw,ay+ah],26,fill=(15,28,52),outline=GOLD,wd=5)
    d.text((ax+aw//2,ay+28),"THE ASK",font=F('bold',38),fill=GOLD,anchor="ma")
    d.text((ax+aw//2,ay+80),"$6M",font=F('black',126),fill=WHITE,anchor="ma")
    txt(d,ax+44,ay+248,"Two BLK3 rockets  ·  licensing  ·  workforce  ·  Montana operations",F('reg',26),GREY,mw=aw-88,lh=1.25)
    # stat row
    stats=[("2 BLK3","reusable rockets"),("135 kg","payload / vehicle"),("100+ km","suborbital altitude"),("2-day","turnaround")]
    sy=900; gap=30; cw=(W-2*M-3*gap)//4
    for i,(big,small) in enumerate(stats):
        x=M+i*(cw+gap); rr(d,[x,sy,x+cw,sy+230],22,fill=LIGHT)
        d.text((x+cw//2,sy+44),big,font=F('black',72),fill=NAVY,anchor="ma")
        d.text((x+cw//2,sy+158),small,font=F('reg',32),fill=(64,76,94),anchor="ma")
    # strategic rationale
    y=section(d,M,1180,"STRATEGIC RATIONALE")
    cwc=(W-2*M-60)//2; hh=440
    card(d,M,y,cwc,hh,"THE OPPORTUNITY",
        ["Oklahoma invested $17M in a single horizontal-launch spaceport.",
         "Montana fields two FAA-licensed reusable rockets, 135 kg to 100+ km, at roughly one-third the cost.",
         "Near-term, proven, and commercially available today."])
    card(d,M+cwc+60,y,cwc,hh,"WHY THE LAUNCH VEHICLE IS CRITICAL",
        ["FAA launch-site licensing requires a specific vehicle.",
         "BLK3 flight data drives trajectory, risk, and environmental modeling.",
         "A vehicle on Day 1 compresses the licensing path by years.",
         "Flight heritage gives the FAA real data, not projections."])
    # program pillars
    y=section(d,M,1810,"PROGRAM PILLARS")
    pw=(W-2*M-2*40)//3; ph=760
    card(d,M,y,pw,ph,"LAUNCH OPERATIONS",
        ["Two BLK3 rockets for DoD, NASA, and commercial campaigns.",
         "Suborbital flights to 100+ km from Montana ranges.",
         "Two-day turnaround for rapid, repeatable access.",
         "FAA launch-site licensing for Montana."])
    card(d,M+pw+40,y,pw,ph,"EDUCATION = WORKFORCE,\nTODAY & TOMORROW",
        ["Builds the skilled workforce now and funds Montana's space future.",
         "Keeps young Montanans and talent in-state: MSU, Montana Tech, partners.",
         "Hands-on student integration: payload, avionics, ground, flight ops.",
         "Technician certificates and veteran-transition pathways."])
    card(d,M+2*(pw+40),y,pw,ph,"ORBITAL PATHWAY",
        ["Suborbital today seeds near-term polar and infrastructure.",
         "Active operations attract orbital launch startups.",
         "About $1M per flight at current NASA pricing.",
         "Polar-launch pipeline alongside Rocket Lab and Vandenberg."])
    # economic impact + why montana
    y=section(d,M,2760,"ECONOMIC IMPACT  +  WHY MONTANA")
    lw=600; ph2=350
    rr(d,[M,y,M+lw,y+ph2],22,fill=(15,28,52),outline=PANEL_BD,wd=3)
    d.text((M+lw//2,y+34),"50-75+",font=F('black',104),fill=GOLD,anchor="ma")
    d.text((M+lw//2,y+170),"direct jobs by Year 3",font=F('reg',34),fill=GREY,anchor="ma")
    d.text((M+lw//2,y+232),"$50M+ federal potential",font=F('bold',38),fill=WHITE,anchor="ma")
    d.text((M+lw//2,y+286),"3-5x economic multiplier",font=F('bold',38),fill=WHITE,anchor="ma")
    card(d,M+lw+60,y,W-2*M-lw-60,ph2,"WHY MONTANA",
        ["Geography: 45-48 deg N polar / SSO corridor, Kodiak to Vandenberg.",
         "Safety: clear airspace, low density; range-safety analysis underway.",
         "Infrastructure: AeroTec / MAGA, MSU smallsat, no state sales tax.",
         "International: SpacePort Australia discussions."])
    footer(d,"EXOS AEROSPACE    |    FAA-licensed reusable suborbital launch    |    Active USAF SBIR Phase II & NASA contracts    |    Profitable in 2025")
    return img

# ===================== PAGE 2 =====================
def page2():
    img=bg(); d=ImageDraw.Draw(img); M=60
    header(d,img,"PHASE PLAN   |   CONGRESSIONAL SUPPORT   |   Q&A")
    y=section(d,M,270,"HOW CONGRESS CAN HELP")
    cw=(W-2*M-40)//2
    cc=[("FAA LAUNCH-SITE LICENSING",["Endorsement accelerates FAA review for the Billings and Townsend sites."]),
        ("FEDERAL FUNDING",["Direct DoD / NASA contracts to Montana; $50M+ already in the STRATFI / SBIR / Phase III pipeline."]),
        ("GOLDEN DOME ALIGNMENT",["Montana launch as a strategic asset for space-based missile defense."]),
        ("WORKFORCE GRANTS",["NSF, NASA Space Grant, and DOL funding for aerospace workforce programs."])]
    for i,(h,b) in enumerate(cc):
        card(d,M+(i%2)*(cw+40),y+(i//2)*270,cw,240,h,b)
    y=section(d,M,1130,"$6M PROGRAM STRUCTURE")
    pw=(W-2*M-2*40)//3; ph=560
    card(d,M,y,pw,ph,"1   FOUNDATION\nMonths 1-6   ·   $2.5M",
        ["FAA site licensing initiated.","Ground test ops at AeroTec.","MSU / Montana Tech students onboarded.","10-15 jobs created."])
    card(d,M+pw+40,y,pw,ph,"2   FLIGHT OPS\nMonths 12-18   ·   $2.5M",
        ["Two BLK3 rockets operational.","First suborbital flights as the license matures.","DoD / NASA + international payloads.","25-40 jobs."])
    card(d,M+2*(pw+40),y,pw,ph,"3   OPERATIONS TURNOVER\nMonths 18-36   ·   $1.0M",
        ["Hand-off to the Montana Spaceport team, 100% revenue.","Pilot corridor qualification.","35-75+ jobs.","$50M+ federal pipeline established."])
    y=section(d,M,2010,"ANTICIPATED QUESTIONS & ANSWERS")
    qa=[("Is $6M enough?","Yes, the vehicles and FAA licenses already exist; funds cover Montana infrastructure, deployment, and workforce."),
        ("How does revenue work?","About $1M per flight at NASA pricing; Phase 3 shifts revenue to the Montana Spaceport team."),
        ("Why Montana for polar orbit?","High latitude offers SSO access between Kodiak and Vandenberg, with low population density."),
        ("Safety and environment?","FAA launch licensing and environmental review govern operations; vehicles are recovered and reused."),
        ("How does suborbital reach orbit?","Active operations draw orbital startups, airspace, and the infrastructure a polar capability builds on."),
        ("How does this compare?","Oklahoma spent $17M on one horizontal site; Montana fields two reusable vehicles for a fraction.")]
    cwq=(W-2*M-60)//2; col_y=[y,y]
    for i,(q,a) in enumerate(qa):
        c=i%2; x=M+c*(cwq+60); yy=col_y[c]
        yy=txt(d,x,yy,"Q   "+q,F('bold',38),WHITE,mw=cwq,lh=1.2)+6
        yy=txt(d,x+48,yy,a,F('reg',34),GREY,mw=cwq-48,lh=1.3)+40
        col_y[c]=yy
    yb=max(col_y)+10
    rr(d,[M,yb,W-M,yb+170],20,fill=(15,28,52),outline=GOLD,wd=4)
    txt(d,M+50,yb+40,"Montana can move to the front of the line: vehicle data on Day 1, operational flight heritage, workforce programs, and a polar-launch strategy aligned with national security needs.",F('bold',38),WHITE,mw=W-2*M-100,lh=1.32)
    footer(d,"www.exosaero.com    |    John Quinn, CEO    |    jquinn@exosaero.com    |    972-740-8355    |    Townsend Site Visit, May 2026")
    return img

os.makedirs("drafts",exist_ok=True)
p1=page1(); p2=page2()
p1.save("drafts/Exos_Montana_OnePager_p1.png"); p2.save("drafts/Exos_Montana_OnePager_p2.png")
p1.convert("RGB").save("drafts/Exos_Montana_OnePager.pdf",save_all=True,append_images=[p2.convert("RGB")],resolution=200.0)
from docx import Document; from docx.shared import Inches
doc=Document(); s=doc.sections[0]; s.page_width=Inches(11); s.page_height=Inches(17)
s.left_margin=s.right_margin=s.top_margin=s.bottom_margin=Inches(0)
doc.add_picture("drafts/Exos_Montana_OnePager_p1.png",height=Inches(16.95))
doc.add_page_break(); doc.add_picture("drafts/Exos_Montana_OnePager_p2.png",height=Inches(16.95))
doc.save("drafts/Exos_Montana_Program_One_Pager_REBUILD.docx")
print("BUILT v2")
