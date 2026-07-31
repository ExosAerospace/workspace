#!/usr/bin/env python3
"""Two Exos x Purdue partner-recruitment CONCEPT DECKS (16:9, branded).
Deck A: Embedded FBG Structural Health Monitoring (NASA SBIR AERO.4.S26B) -> Purdue CMSC / Dr. Dianyun Zhang.
Deck B: SACSS 40-100 km atmospheric contaminant sampling (NASA SBIR INSTALG.2.S26A) -> Purdue / Dr. Steven Collicott.
Facts verified vs memory: BLK3 <4g boost / ~7g peak transient shock (NOT 5-10g sustained); onboard computer/telemetry
stack records sensor channels (no standalone 64-ch DAQ); FBG SHM is PROPOSED not yet flown; one of only three
FAA-licensed reusable providers; Part 431 license 3/13/26 -> Part 450; Armadillo successor flying since 2018."""
import os, random
from PIL import Image, ImageDraw, ImageFont
random.seed(11)
W, H = 2560, 1440
NAVY=(9,20,42); GOLD=(232,170,60); ORANGE=(233,122,50); WHITE=(255,255,255)
LIGHT=(238,243,248); GREY=(205,216,230); PANEL=(19,40,70); PANEL_BD=(46,82,130)

def F(kind,size):
    paths={'reg':"/System/Library/Fonts/Supplemental/Arial.ttf",
           'bold':"/System/Library/Fonts/Supplemental/Arial Bold.ttf",
           'black':"/System/Library/Fonts/Supplemental/Arial Black.ttf"}
    p=paths[kind]
    if os.path.exists(p):
        try: return ImageFont.truetype(p,size)
        except: pass
    return ImageFont.truetype({'reg':"DejaVuSans.ttf",'bold':"DejaVuSans-Bold.ttf",'black':"DejaVuSans-Bold.ttf"}[kind],size)

def bg(hero=False):
    img=Image.new("RGB",(W,H),NAVY); d=ImageDraw.Draw(img)
    for y in range(H):
        t=y/H; d.line([(0,y),(W,y)],fill=(int(9+9*t),int(20+16*t),int(42+26*t)))
    glow=Image.new("L",(W,H),0); gd=ImageDraw.Draw(glow); R=1500
    cx,cy=(W*0.5,H*0.62) if hero else (W*0.88,H*0.85)
    for r in range(R,0,-6): gd.ellipse([cx-r,cy-r,cx+r,cy+r],fill=int((72 if hero else 55)*(1-r/R)))
    img.paste(Image.new("RGB",(W,H),ORANGE),(0,0),glow.point(lambda v:int(v*0.4)))
    d=ImageDraw.Draw(img)
    for _ in range(240):
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
def panel(d,box,bd=PANEL_BD): rr(d,box,20,fill=PANEL,outline=bd,wd=3)

M=90
def chrome(d,tag,pageno,total):
    d.text((M,60),"EXOS",font=F('black',48),fill=WHITE)
    d.text((M+210,68),"AEROSPACE",font=F('reg',40),fill=GOLD)
    d.text((W-M,80),tag,font=F('reg',26),fill=GREY,anchor="ra")
    d.line([(M,150),(W-M,150)],fill=PANEL_BD,width=3)
    d.rectangle([0,H-70,W,H],fill=(7,14,30))
    d.text((M,H-52),"EXOS AEROSPACE  x  PURDUE UNIVERSITY   |   Partnership Concept   |   Proprietary",font=F('reg',24),fill=GREY)
    d.text((W-M,H-52),f"{pageno} / {total}",font=F('bold',24),fill=GREY,anchor="ra")

def title_slide(title, sub, chips, tag):
    img=bg(hero=True); d=ImageDraw.Draw(img)
    d.text((M,90),"EXOS",font=F('black',60),fill=WHITE)
    d.text((M+265,102),"AEROSPACE",font=F('reg',52),fill=GOLD)
    d.text((W-M,120),tag,font=F('reg',28),fill=GREY,anchor="ra")
    d.line([(M,210),(W-M,210)],fill=PANEL_BD,width=3)
    d.text((M,150),"PARTNERSHIP CONCEPT  ·  EXOS  ×  PURDUE UNIVERSITY",font=F('bold',30),fill=GOLD) if False else None
    y=430
    y=txt(d,M,y,title,F('black',88),WHITE,mw=W-2*M,lh=1.12)+18
    y=txt(d,M,y,sub,F('bold',44),GOLD,mw=W-2*M,lh=1.22)+40
    # chips
    fx=F('reg',30); x=M
    for c in chips:
        w=d.textlength(c,font=fx)+56
        rr(d,[x,y,x+w,y+70],35,fill=(15,28,52),outline=PANEL_BD,wd=2)
        d.text((x+28,y+18),c,font=fx,fill=GREY); x+=w+22
    d.rectangle([0,H-70,W,H],fill=(7,14,30))
    d.text((M,H-52),"John Quinn, Cofounder & CEO   |   jquinn@exosaero.com   |   972-740-8355   |   www.exosaero.com",font=F('reg',24),fill=GREY)
    return img

def kicker(d,y,label):
    d.text((M,y),label,font=F('bold',34),fill=GOLD); d.line([(M,y+52),(M+230,y+52)],fill=GOLD,width=5); return y+96

def card(d,x,y,w,h,head,bullets,head_fill=GOLD,bh=34,bb=28):
    panel(d,[x,y,x+w,y+h]); pad=34
    yy=txt(d,x+pad,y+pad,head,F('bold',bh),head_fill,mw=w-2*pad,lh=1.12)+14
    fb=F('reg',bb)
    for b in bullets:
        d.ellipse([x+pad,yy+13,x+pad+11,yy+24],fill=GOLD)
        yy=txt(d,x+pad+30,yy,b,fb,GREY,mw=w-2*pad-30,lh=1.26,sp=6)+11
    return yy

def row(cards, top, height, heads_fill=None, gap=40, bh=34, bb=28):
    def _draw(d):
        n=len(cards); cw=(W-2*M-(n-1)*gap)//n
        for i,(h,b) in enumerate(cards):
            hf=(heads_fill[i] if isinstance(heads_fill,list) else (heads_fill or GOLD))
            card(d,M+i*(cw+gap),top,cw,height,h,b,head_fill=hf,bh=bh,bb=bb)
    return _draw

def content_slide(tag, pageno, total, title, kick, drawers, subtitle=None):
    img=bg(); d=ImageDraw.Draw(img); chrome(d,tag,pageno,total)
    y=txt(d,M,178,title,F('black',60),WHITE,mw=W-2*M,lh=1.08)+6
    if subtitle: y=txt(d,M,y+4,subtitle,F('reg',32),GREY,mw=W-2*M,lh=1.25)+6
    if kick: y=kicker(d,y+14,kick)
    for fn in drawers: fn(d)
    return img

def statrow(stats, top, h=170):
    def _draw(d):
        n=len(stats); gap=36; cw=(W-2*M-(n-1)*gap)//n
        for i,(big,small) in enumerate(stats):
            x=M+i*(cw+gap); rr(d,[x,top,x+cw,top+h],18,fill=LIGHT)
            d.text((x+cw//2,top+30),big,font=F('black',56),fill=NAVY,anchor="ma")
            d.text((x+cw//2,top+120),small,font=F('reg',26),fill=(64,76,94),anchor="ma")
    return _draw

def ctabar(text, top, h=150):
    def _draw(d):
        rr(d,[M,top,W-M,top+h],18,fill=(15,28,52),outline=GOLD,wd=4)
        txt(d,M+40,top+30,text,F('bold',36),WHITE,mw=W-2*M-80,lh=1.28)
    return _draw

def save_deck(slides, base):
    os.makedirs("drafts",exist_ok=True)
    pngs=[]
    for i,s in enumerate(slides,1):
        p=f"drafts/{base}_s{i}.png"; s.save(p); pngs.append(p)
    imgs=[Image.open(p).convert("RGB") for p in pngs]
    pdf=f"drafts/{base}.pdf"
    imgs[0].save(pdf,save_all=True,append_images=imgs[1:],resolution=200.0)
    # contact sheet for quick review
    return pdf, pngs

# ============================================================
# DECK A — FBG SHM  (Purdue CMSC / Dr. Dianyun Zhang)
# ============================================================
TAGA="EMBEDDED FBG SHM  |  NASA SBIR AERO.4.S26B"
a=[]
a.append(title_slide(
    "Flight-Validated Structural Health\nMonitoring for Reusable Composites",
    "Embedded fiber-optic (FBG) sensing on the BLK3 reusable launch vehicle and Scorpius lunar-heritage cryo tanks",
    ["NASA SBIR AERO.4.S26B","Exos Aerospace (prime)","Purdue CMSC — Dr. Dianyun Zhang","Letter of Commitment in hand"],
    "EMBEDDED FBG SHM  ·  PARTNERSHIP CONCEPT"))
a.append(content_slide(TAGA,2,6,"The Composite Data Gap","WHY THIS MATTERS",[
    row([("THE AVIATION PRECEDENT",
          ["Even the Boeing 787 (~50% composite) flies with NO embedded FBG real-time SHM.",
           "Certification leans on scheduled inspection, coupons, and damage-tolerance models built for metals."]),
         ("THE LAUNCH-VEHICLE GAP IS WIDER",
          ["Composite tanks, interstages, and COPVs see cryo-to-aero thermal shock and repeated pressure cycles.",
           "No statistical fleet exists — flight-validated composite aging data simply is not available."]),
         ("THE FAA / NASA NEED",
          ["FAA AST must license reusable composite structures flown dozens to hundreds of times.",
           "Ground coupons miss the coupled thermal-mechanical-vibration flight environment."])],
        330,760, bb=29)]))
a.append(content_slide(TAGA,3,6,"The Concept","PROPOSED INNOVATION",[
    statrow([("100+ pts","distributed FBG channels / fiber"),("grams","of fiber vs kg of cabling"),("EMI-immune","in an RF-dense vehicle"),("re-fly","same hardware, mission after mission")],330),
    row([("EMBEDDED FBG SHM ON A REUSABLE PLATFORM",
          ["Embed fiber-optic Bragg-grating sensors inside flight-critical carbon-composite structures on BLK3 and Scorpius Type-5 cryo tanks.",
           "Read internal strain and temperature the same airframe flies repeatedly — building the longitudinal aging dataset the FAA and NASA lack.",
           "Note: FBG SHM is a proposed development for BLK3, not yet flown — this program flight-validates it."]),
         ("CLOSING THE LOOP",
          ["BLK3 recovers intact every flight: correlate in-flight FBG data with post-flight inspection and coupon extraction.",
           "Interrogator integrates into the BLK3 onboard computer / telemetry stack — an incremental add, not clean-sheet avionics.",
           "Room-temperature-cure Scorpius layup avoids the autoclave heat that damages embedded fibers."])],
        540,540,bb=28)]))
a.append(content_slide(TAGA,4,6,"Why This Team","THE UNIQUE COMBINATION",[
    row([("EXOS — THE FLIGHT PLATFORM",
          ["One of only three FAA-licensed reusable rocket launch providers in the US (Part 431 issued 3/13/26; Part 450 transition underway).",
           "BLK3 PSRLV: 100+ km, <4g boost with ~7g peak transient shock, 2-3 day turnaround, intact parachute recovery.",
           "Commercial successor to Armadillo Aerospace — flying reusable suborbital since 2018."]),
         ("SCORPIUS — LUNAR-HERITAGE TANKS",
          ["Only TRL-9 Type-5 composite cryo tanks demonstrated on the lunar surface (Intuitive Machines IM-1 Odysseus, IM-2 Athena).",
           "Room-temperature-cure process embeds fiber without autoclave damage."]),
         ("PURDUE CMSC — DR. DIANYUN ZHANG",
          ["LUNA OFDR interrogation — the same principle as NASA's FOSS technology named in the topic.",
           "ASTM composite testing (D3039 / D6641 / D2344) + research-scale automated fiber placement (AFP)."])],
        330,780,bb=27)]))
a.append(content_slide(TAGA,5,6,"Division of Work","HOW THE PARTNERSHIP RUNS",[
    row([("EXOS — PRIME (Phase I)",
          ["FBG sensor architecture + interrogator trade study for the flight environment.",
           "Fabricate instrumented composite panels and a subscale Scorpius tank article.",
           "Cryo, pressure, and vibration ground tests to BLK3 flight spectra.",
           "Phase II flight-integration preliminary design + test plan."]),
         ("PURDUE — SUBAWARD (Dr. Zhang)",
          ["ASTM testing of FBG-embedded coupons vs uninstrumented controls.",
           "FBG calibration: static, cryo-to-elevated temperature, dynamic frequency response.",
           "LUNA OFDR correlation to validate accuracy and align to NASA FOSS.",
           "Embedding-process consulting; possible AFP subscale-tank fabrication.",
           "Phase II: flight-data analysis + predictive damage models."])],
        330,700,heads_fill=[GOLD,ORANGE],bb=28)]))
a.append(content_slide(TAGA,6,6,"The Path Forward","WHERE WE ARE, WHAT WE ASK",[
    row([("IN HAND",
          ["Purdue Letter of Commitment (Dr. Zhang, 5/20/26).",
           "Full technical narrative + work plan drafted.",
           "Exos flight platform, DAQ path, and Scorpius manufacturing ready."]),
         ("THE VEHICLES",
          ["NASA SBIR AERO.4.S26B — Phase I flight-measurement technologies.",
           "Adjacent pull-through: Navy ONR / NAVAIR fiber-optic SHM flight test.",
           "Phase II: 6+ instrumented BLK3 flights -> composite aging database."]),
         ("THE ASK OF PURDUE",
          ["Confirm the Phase I scope and subaward roles above.",
           "Lock a joint Phase II vision (flight-data analysis + damage models).",
           "30-minute working call to align on schedule and next submission."])],
        330,560,bb=27),
    ctabar("Exos + Purdue CMSC can build the flight-validated composite SHM dataset the FAA and NASA do not have. Let's lock the team.",930)]))
pdfA,_=save_deck(a,"Exos_Purdue_FBG_SHM_Concept_Deck")
print("BUILT A:",pdfA)

# ============================================================
# DECK B — SACSS  (Purdue / Dr. Steven Collicott)
# ============================================================
TAGB="SACSS 40-100 km SAMPLING  |  NASA SBIR INSTALG.2.S26A"
b=[]
b.append(title_slide(
    "SACSS — Closing the 40-100 km\nIn-Situ Atmospheric Sampling Gap",
    "Reusable, multi-altitude physical sample return of reentry-derived particulate on the BLK3 platform",
    ["NASA SBIR INSTALG.2.S26A","Exos Aerospace (prime)","Purdue — Dr. Steven Collicott","Letter of Support in hand"],
    "SACSS  ·  PARTNERSHIP CONCEPT"))
b.append(content_slide(TAGB,2,6,"The Problem NOAA & NASA Already Own","A MEASUREMENT BLIND SPOT",[
    statrow([("~17 t","Al2O3 injected (2022)"),("~360 t/yr","projected at full deployment"),("12,000+","reentries / yr by ~2040"),("96 km","lithium plume already detected")],330),
    row([("REENTRY METAL INJECTION IS ACCELERATING",
          ["Mega-constellation reentries deposit alumina and metals into the mesosphere and stratosphere.",
           "Documented effects on Earth's radiation budget: mesospheric heating, polar-vortex shift, ozone catalysis."]),
         ("THE MANDATE HAS NO REACH",
          ["Congress directed NOAA (2020) to observe and monitor stratospheric conditions (ERB Initiative).",
           "But the injection/ablation zone is 40-100 km — today assessed on modeling alone, with no in-situ physical samples."])],
        540,540,bb=29)]))
b.append(content_slide(TAGB,3,6,"The Gap Is the Wedge","MEASUREMENT REACH TODAY",[
    row([("AIRCRAFT (SABRE WB-57)",["Ceiling ~19 km.","Samples only what has already settled."]),
         ("BALLOONS",["~35-40 km.","Marginal lower edge of the zone."]),
         ("SOUNDING ROCKETS",["Reach 100+ km.","$1-5M/flight, single-shot, no reuse."]),
         ("SATELLITE / LIDAR",["Column or single-species only.","Cannot return a physical sample."])],
        330,420,bb=28),
    ctabar("Result: almost no systematic in-situ sampling exists for 40-100 km. SACSS is the only path to altitude-resolved, composition-grade physical samples in the gap.",800)]))
b.append(content_slide(TAGB,4,6,"The Capability","SACSS ON A REUSABLE PLATFORM",[
    statrow([("40-100 km","three sampling bands"),("ascent + descent","chambers open & seal"),("~$250K","per flight incl. lab analysis"),("~8 / yr","target monitoring cadence")],330),
    row([("MULTI-ALTITUDE PHYSICAL SAMPLE RETURN",
          ["Multi-stage sampler opens and seals chambers at 40-60, 60-80, 80-100 km on both ascent and descent.",
           "Parachute recovery returns intact samples for mass spec, electron microscopy, and isotopic composition.",
           "One of only three FAA-licensed reusable providers — repeatable campaigns at a fraction of sounding-rocket cost."]),
         ("COMPLEMENTS, NOT DUPLICATES",
          ["SACSS samples the source region; SABRE samples the settled stratosphere — together they close the column.",
           "Delivers the ground-truth to validate ERB/CSL aerosol radiative-forcing models.",
           "Data formatted to align with NOAA CSL and NASA science pipelines."])],
        540,540,bb=28)]))
b.append(content_slide(TAGB,5,6,"Why This Team","PLATFORM x DEEP SUBORBITAL SCIENCE",[
    row([("EXOS — PRIME FLIGHT & SAMPLING",
          ["BLK3 PSRLV to 100+ km with intact recovery; sampler integration, flight ops, and campaign cadence.",
           "Part 431 license issued 3/13/26 (Part 450 transition underway); Armadillo successor flying since 2018.",
           "Exos primes the flight and sampling capability end to end."]),
         ("PURDUE — DR. STEVEN COLLICOTT",
          ["One of the most flight-experienced suborbital scientists in the US: 12 experiments on New Shepard, plus Virgin Galactic, Pluto — flying with Exos and predecessor Armadillo since 2009.",
           "Member of the all-Purdue Purdue 1 research flight crew (2027)."]),
         ("PURDUE — THE SCIENCE ROLE",
          ["Atmospheric sampling methodology, substrate selection, and sample-preservation protocols.",
           "EM-EDX (SEM/EDX) and ICP-MS trace-metal analysis requirements for Phase II.",
           "Phase II flight-data analysis and publication."])],
        330,780,bb=26)]))
b.append(content_slide(TAGB,6,6,"The Path Forward","WHERE WE ARE, WHAT WE ASK",[
    row([("IN HAND",
          ["Purdue Letter of Support (Dr. Collicott).",
           "SACSS concept, sampler architecture, and cost model drafted.",
           "NASA INSTALG.2.S26A Phase I proposal package staged."]),
         ("THE VEHICLES",
          ["NASA SBIR INSTALG.2.S26A — Suborbital Instruments & Sensor Systems.",
           "NOAA CPO ERB / AC4 competition (science-led, Exos + Purdue Co-PI).",
           "NOAA SBIR Phase I — ~80% reuse of the NASA package."]),
         ("THE ASK OF PURDUE",
          ["Confirm the Co-PI / science role and Phase II analysis scope.",
           "Align on the NOAA ERB/AC4 LOI window (next cycle).",
           "30-minute working call to sequence the submissions."])],
        330,560,bb=27),
    ctabar("Exos + Purdue can give NOAA and NASA the first altitude-resolved, composition-grade samples from 40-100 km. Let's lock the team.",930)]))
pdfB,_=save_deck(b,"Exos_Purdue_SACSS_Concept_Deck")
print("BUILT B:",pdfB)
