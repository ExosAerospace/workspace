#!/usr/bin/env python3
"""HTML twin of the v6 visual-first IDJ deck -> 16:9 PDF + PNG previews.
Mirrors scripts/build_idj_deck_pptx_v5.py geometry (inch*96 = px on a 1280x720 canvas)."""
import base64, os, subprocess
WS="/Users/exomac/.openclaw/workspace"; D=os.path.join(WS,"drafts")
STEM="Exos_JP_3min_InvestorPitch_IDJ_BRANDED_v6_2026-09-27"
def b64(p): return base64.b64encode(open(p,"rb").read()).decode()
logo=b64(os.path.join(D,"_exos_white_official.png"))
lockup=b64(os.path.join(D,"_spaceavailable_white.png"))
planet=b64(os.path.join(D,"_exos_planet_b.png"))
PX=96.0
def px(v): return round(v*PX,1)

def box(x,y,w,h,cls="",style="",html=""):
    return (f'<div class="{cls}" style="left:{px(x)}px;top:{px(y)}px;width:{px(w)}px;'
            f'height:{px(h)}px;{style}">{html}</div>')

CSS=f"""
<style>
@page {{ size:1280px 720px; margin:0; }}
*{{box-sizing:border-box;margin:0;padding:0;font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;}}
body{{background:#333;}}
.slide{{position:relative;width:1280px;height:720px;background:#0d0d0f;overflow:hidden;page-break-after:always;}}
.slide>div{{position:absolute;}}
.corner{{position:absolute;right:{px(1.433)}px;top:{px(0.42)}px;height:{px(0.32)}px;}}
.kick{{color:#F26A21;font-weight:700;font-size:12px;letter-spacing:.12em;}}
.stitle{{color:#fff;font-weight:700;font-size:30px;}}
.rule{{position:absolute;background:#F26A21;}}
.panel{{background:#17181c;border-radius:14px;}}
.panel2{{background:#1f2025;border-radius:12px;}}
.spine{{position:absolute;background:#F26A21;}}
.num{{color:#F26A21;font-weight:700;font-size:40px;line-height:.95;}}
.lbl{{color:#fff;font-weight:700;font-size:15.5px;line-height:1.05;}}
.sub{{color:#9a9aa1;font-size:12.5px;line-height:1.05;margin-top:6px;}}
.body{{color:#d2d2d7;font-size:12.5px;line-height:1.1;margin-top:6px;}}
.circle{{position:absolute;border-radius:50%;border:2px solid #F26A21;display:flex;align-items:center;justify-content:center;color:#F26A21;font-weight:700;}}
.chip{{background:#1f2025;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#d2d2d7;font-weight:700;font-size:12px;text-align:center;padding:0 8px;}}
.chipo{{border:1px solid #7a3612;}}
.pend{{color:#F26A21;font-weight:700;}}
.mut{{color:#9a9aa1;}}
.wht{{color:#fff;}}.gry{{color:#d2d2d7;}}.org{{color:#F26A21;}}
</style>
"""

def hero_bg():
    scrim="linear-gradient(180deg,rgba(0,0,0,.8) 0%,rgba(0,0,0,.55) 50%,rgba(0,0,0,.82) 100%)"
    return (f'<div style="left:0;top:0;width:1280px;height:720px;'
            f'background:{scrim},url(data:image/png;base64,{planet});'
            f'background-size:cover;background-position:center;"></div>'
            f'<img class="hlogo" style="position:absolute;left:{px(0.62)}px;top:{px(0.55)}px;height:{px(0.6)}px;" src="data:image/png;base64,{logo}">'
            f'<img style="position:absolute;left:{px(10.4)}px;top:{px(0.62)}px;width:{px(2.3)}px;" src="data:image/png;base64,{lockup}">')

def chrome(title,kick):
    h=f'<img class="corner" src="data:image/png;base64,{logo}">'
    h+=box(0.64,0.44,11,0.3,"kick","",kick.upper())
    h+=box(0.62,0.74,10.9,0.9,"stitle","",title)
    h+=f'<div class="rule" style="left:{px(0.66)}px;top:{px(1.52)}px;width:{px(1.15)}px;height:{px(0.055)}px;"></div>'
    return h

def stat(x,y,w,h,num,lbl,sub):
    return (box(x,y,w,h,"panel")+
            f'<div class="spine" style="left:{px(x)}px;top:{px(y)}px;width:{px(0.08)}px;height:{px(h)}px;"></div>'+
            box(x+0.32,y+0.30,w-0.5,1.0,"num","",num)+
            box(x+0.34,y+1.28,w-0.6,h-1.4,"","",
                f'<div class="lbl">{lbl}</div><div class="sub">{sub}</div>'))

def icard(x,y,w,h,glyph,title,body):
    return (box(x,y,w,h,"panel")+
            f'<div class="circle" style="left:{px(x+0.34)}px;top:{px(y+0.34)}px;width:{px(0.62)}px;height:{px(0.62)}px;font-size:22px;">{glyph}</div>'+
            box(x+0.32,y+1.15,w-0.62,h-1.25,"","",
                f'<div class="lbl">{title}</div><div class="body">{body}</div>'))

def quad(x,y,w,h,glyph,title,body):
    return (box(x,y,w,h,"panel")+
            f'<div class="circle" style="left:{px(x+0.3)}px;top:{px(y+0.3)}px;width:{px(0.54)}px;height:{px(0.54)}px;font-size:18px;">{glyph}</div>'+
            box(x+1.05,y+0.24,w-1.25,h-0.4,"","",
                f'<div class="lbl" style="font-size:15px;">{title}</div><div class="body" style="font-size:12px;">{body}</div>'))

def chip(x,y,w,text,org=False):
    return box(x,y,w,0.5,"chip"+(" chipo" if org else ""),"",text)

slides=[]

# SLIDE 1 hero
s=hero_bg()
s+=box(0.7,2.55,12,1.0,"","font-size:42px;font-weight:700;",
       '<span class="wht">Exos Aerospace&nbsp;&nbsp;</span><span class="org">—</span><span class="wht">&nbsp;&nbsp;Expanding to Japan</span>')
s+=box(0.72,3.66,12,0.6,"org","font-size:22px;font-weight:700;","A Partnership &amp; Investment Opportunity — Exos Aerospace Japan (K.K.)")
s+=box(0.72,4.55,12,0.9,"","",
       '<div class="gry" style="font-size:15px;">With appreciation to Innovation Dojo — Black Belt Venture Studio&nbsp;&nbsp;·&nbsp;&nbsp;8 October 2026</div>'
       '<div class="mut" style="font-size:14px;margin-top:5px;">Toshi Kumazawa (Japan BD)&nbsp;&nbsp;·&nbsp;&nbsp;John Quinn (Co-founder &amp; CEO)</div>')
s+=box(0.72,6.98,12,0.4,"org","font-size:9.5px;","v6 — John's inputs locked 27 Sep 2026; Toshi finalizes Japanese / keigo")
slides.append(s)

# SLIDE 2 who we are
s=chrome("Who we are","Proven · profitable · reusable")
tw=3.92;gap=0.31;x0=0.66;y=2.05;th=2.55
s+=stat(x0,y,tw,th,"3","of only 3 U.S. companies FAA-licensed for reusable launch operations","alongside SpaceX and Blue Origin")
s+=stat(x0+tw+gap,y,tw,th,"25+ yrs","hands-on reusable-vehicle heritage","predecessor: Armadillo Aerospace")
s+=stat(x0+2*(tw+gap),y,tw,th,"$1.49M","2025 revenue — profitable: EBITDA $254K (17% margin)","FY2025, accrual basis, unaudited")
s+=box(0.66,4.95,12,0.5,"gry","font-size:16px;font-weight:700;","A real operating company with flight heritage — not a concept.")
slides.append(s)

# SLIDE 3 tech
s=chrome("Proven, differentiated technology","What sets us apart")
cw=3.92;gap=0.31;x0=0.66;y=2.0;ch=3.55
s+=icard(x0,y,cw,ch,"▲","BLK3 reusable vehicle","Suborbital launch vehicle: out-of-autoclave carbon composite, low parts count — recovered and reflown.")
s+=icard(x0+cw+gap,y,cw,ch,"◆","TRL-9 Type-5 cryo tanks","Linerless composite cryogenic tanks (affiliate Scorpius / SSLC) — lighter and more robust than metal.")
s+=icard(x0+2*(cw+gap),y,cw,ch,"☾","Proven on the Moon","Scorpius Type-5 tanks flew as fuel &amp; LOX tanks aboard Intuitive Machines' Odysseus (2024) and Athena landers.")
slides.append(s)

# SLIDE 4 commitment
s=chrome("Our commitment to Japan","Built in Japan, together with Japan")
qw=5.95;qh=1.72;gx=0.66;gy=2.02;gp=0.28
s+=quad(gx,gy,qw,qh,"社","Exos Aerospace Japan (K.K.)","A local company, office, and team — opening in 2026.")
s+=quad(gx+qw+gp,gy,qw,qh,"↑","HOSPO wet-lease flights","BLK3 reusable suborbital flight services at Hokkaido Spaceport, with Exos as licensed operator.")
s+=quad(gx,gy+qh+gp,qw,qh,"⚙","Serve industry &amp; universities","BLK3 verification / flight-test platform, reusable engines, and SSLC Type-5 cryo tanks.")
s+=quad(gx+qw+gp,gy+qh+gp,qw,qh,"◇","Consulting &amp; collaboration","Long-term partnership — building space capability in Japan, together with Japan.")
slides.append(s)

# SLIDE 5 investment
s=chrome("The investment opportunity","Slide 5 · structured round · returns · exit")
ax,ay,aw,ah=0.66,1.95,3.55,3.05
s+=box(ax,ay,aw,ah,"panel")
s+=f'<div class="spine" style="left:{px(ax)}px;top:{px(ay)}px;width:{px(aw)}px;height:{px(0.09)}px;"></div>'
s+=box(ax+0.3,ay+0.28,aw-0.6,0.4,"mut","font-size:11px;font-weight:700;","JAPAN ROUND — VIA EXOS U.S.")
s+=box(ax+0.3,ay+0.66,aw-0.6,0.9,"num","","¥790M")
s+=box(ax+0.3,ay+1.5,aw-0.6,0.4,"org","font-size:12.5px;font-weight:700;",'≈ US$5.0M target&nbsp;&nbsp;(at ~¥157 / US$)')
s+=box(ax+0.3,ay+1.95,aw-0.6,1.0,"","",
       '<div class="gry" style="font-size:12.5px;line-height:1.1;">Invest through the Exos U.S. offering vehicle; proceeds fund the Japan K.K. build-out.</div>'
       '<div class="mut" style="font-size:12px;margin-top:6px;line-height:1.1;">Exos Aerospace Japan K.K. is a wholly-owned subsidiary of Exos U.S.</div>')
ux=4.5;uy=1.9
s+=box(ux,uy,8.1,0.35,"mut","font-size:11px;font-weight:700;","USE OF FUNDS")
uf=["Stand up Japan operations","Secure a wet-lease BLK3 for HOSPO","Open the Japan office (2026)","Build the local team"]
cwid=[3.55,3.95];ccols=[ux,ux+4.05]
for i,label in enumerate(uf):
    cx=ccols[i%2];cy=uy+0.38+(i//2)*0.6;s+=chip(cx,cy,cwid[i%2] if i%2 else cwid[0],label)
ty=3.55
s+=box(ux,ty,8.1,0.35,"mut","font-size:11px;font-weight:700;","PATH TO RETURNS — GROW, THEN EXIT")
steps=[("ROUND (now)","Fund Japan stand-up + first wet-lease flights"),
       ("SCALE","Recurring revenue: wet-lease flights · Type-5 tank &amp; engine sales · verification &amp; consulting"),
       ("EXIT",'Liquidity through an Exos U.S. event: public listing or acquisition. Horizon ~3+ yrs.')]
sw=2.55;sg=0.18
for i,(hd,bd) in enumerate(steps):
    x=ux+i*(sw+sg)
    s+=box(x,ty+0.38,sw,1.4,"panel2")
    s+=f'<div class="spine" style="left:{px(x)}px;top:{px(ty+0.38)}px;width:{px(sw)}px;height:{px(0.07)}px;"></div>'
    s+=box(x+0.2,ty+0.52,sw-0.35,0.4,"org","font-size:13px;font-weight:700;",hd)
    s+=box(x+0.2,ty+0.9,sw-0.35,0.82,"gry","font-size:10.5px;line-height:1.06;",bd)
    if i<2:
        s+=f'<div style="position:absolute;left:{px(x+sw)}px;top:{px(ty+0.9)}px;color:#F26A21;font-size:18px;font-weight:700;">&#10148;</div>'
by=5.55
s+=box(0.66,by,12.0,1.12,"panel")
s+=f'<div class="spine" style="left:{px(0.66)}px;top:{px(by)}px;width:{px(0.09)}px;height:{px(1.12)}px;"></div>'
s+=box(0.95,by+0.16,11.6,0.35,"","font-size:11.5px;",'<span class="org" style="font-weight:700;">ALSO ON THE TABLE — non-dilutive layers&nbsp;&nbsp;</span><span class="mut">(alongside equity, per IDJ)</span>')
s+=chip(0.95,by+0.55,3.6,"Payload pre-sales — reserve BLK3 flight capacity",True)
s+=chip(4.75,by+0.55,3.6,"Crowdfunding — community &amp; fan participation",True)
s+=chip(8.55,by+0.55,3.9,"Staged equity rounds — realistic financing",True)
s+=box(0.66,6.86,12,0.3,"","font-size:8.5px;color:#8a8f98;font-style:italic;","This presentation is not an offer to sell or a solicitation of an offer to buy securities. Any offering will be made only through definitive offering documents to eligible investors.")
slides.append(s)

# SLIDE 6 traction
s=chrome("Traction & the path forward","Real signal, on the ground")
mw=5.95;mh=1.72;gx=0.66;gy=2.02;gp=0.28
def mile(x,y,tag,title,body):
    return (box(x,y,mw,mh,"panel")+
            f'<div class="spine" style="left:{px(x)}px;top:{px(y)}px;width:{px(0.08)}px;height:{px(mh)}px;"></div>'+
            box(x+0.3,y+0.22,mw-0.5,0.3,"org","font-size:10.5px;font-weight:700;",tag)+
            box(x+0.3,y+0.52,mw-0.55,mh-0.6,"","",
                f'<div class="lbl" style="font-size:14px;">{title}</div><div class="body" style="font-size:11.5px;">{body}</div>'))
s+=mile(gx,gy,"DEMAND","LOI + inbound inquiry","Letter of intent for a fuel-tank order from a Japanese space-development company; an engine-specification inquiry as well.")
s+=mile(gx+mw+gp,gy,"PARTNER","HOSPO discussions underway","Collaboration talks in progress with Hokkaido Spaceport (HOSPO / Space Cotan).")
s+=mile(gx,gy+mh+gp,"IN-PERSON","CEO in Japan — October 2026","John Quinn will meet HOSPO, the LOI client, other space-development companies, and prospective investors.")
s+=mile(gx+mw+gp,gy+mh+gp,"LOCALIZE","JP production partners",'Seeking Japanese technical partners for licensed production of TRL-9 Type-5 tanks in Japan. BLK3-for-Japan production commences upon international approvals (incl. U.S. export), with potential reallocation of U.S. BLK3 assets to match the speed of those approvals.')
slides.append(s)

# SLIDE 7 thank you
s=hero_bg()
s+=box(0.7,2.55,12,1.0,"org","font-size:44px;font-weight:700;","Thank you")
items=["We are honored to explore this partnership with the Japanese space community",
       "Reusable space capability and lunar-proven tank technology — built in Japan, together with Japan",
       "We warmly invite investors and technical partners to build it with us — office opening 2026",
       "Contact: Toshi Kumazawa · toshihisa@exosaero.com  ·  John Quinn, Co-founder &amp; CEO"]
inner="".join(f'<div style="margin-top:{0 if i==0 else 10}px;color:#d2d2d7;font-size:17px;"><span class="org">▪&nbsp;&nbsp;</span>{t}</div>' for i,t in enumerate(items))
s+=box(0.72,3.7,12,2.4,"","",inner)
slides.append(s)

html="<html><head><meta charset='utf-8'>"+CSS+"</head><body>"+"".join(f'<div class="slide">{s}</div>' for s in slides)+"</body></html>"
hp=os.path.join(D,STEM+".html"); open(hp,"w",encoding="utf-8").write(html)
pdf=os.path.join(D,STEM+".pdf")
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([CH,"--headless","--disable-gpu","--no-pdf-header-footer",
                f"--print-to-pdf={pdf}",f"file://{hp}"],check=True,
               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print("HTML",hp); print("PDF",pdf,os.path.getsize(pdf))
