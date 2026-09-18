#!/usr/bin/env python3
"""ITZ Operating Model infographic — Node, de-risk value, network, cadence, Artemis."""
W,H=1600,1150
INK="#0f1e2e";NAVY="#12395f";ORANGE="#e8791a";GREEN="#1f8a54"
PANEL="#eef3f8";LINE="#cbd6e2";MUTE="#5a6b7b";WHITE="#ffffff"
s=[]
def esc(t):return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def rect(x,y,w,h,fill,rx=14,stroke="none",sw=0):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def txt(x,y,t,size=22,fill=INK,weight="normal",anchor="start"):
    s.append(f'<text x="{x}" y="{y}" font-family="Helvetica, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(t)}</text>')
def arrow(x1,y,x2,label=None):
    s.append(f'<line x1="{x1}" y1="{y}" x2="{x2-13}" y2="{y}" stroke="{INK}" stroke-width="3"/>')
    s.append(f'<path d="M{x2-13} {y-8} L{x2} {y} L{x2-13} {y+8} Z" fill="{INK}"/>')
    if label: txt((x1+x2)/2,y-12,label,15,MUTE,"bold","middle")
def chip(x,y,t,size=17,fill="#dfe8f2",tc=NAVY,h=30):
    w=int(len(t)*size*0.60)+30
    rect(x,y,w,h,fill,rx=h//2);txt(x+w/2,y+h-10,t,size,tc,"bold","middle")
    return x+w+14

s.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
rect(0,0,W,H,WHITE,rx=0)
txt(60,58,"Exos International Trade Zone — Operating Model",34,INK,"bold")
txt(60,92,"A reusable suborbital test lane that de-risks hardware before orbit — packaged as a Node and repeated worldwide.",20,MUTE)

# BAND 1 — THE NODE
rect(60,115,1480,195,PANEL);rect(60,115,6,195,NAVY,rx=0)
txt(88,152,"1 · The Node — one repeatable unit",23,NAVY,"bold")
txt(88,178,"Wet-leased Exos vehicles + an ITZ container = a spaceport that flies international payloads.",18,INK)
gy=248
rect(430,gy-28,200,56,WHITE,rx=10,stroke=LINE,sw=2)
txt(530,gy-4,"Payloads",17,INK,"bold","middle");txt(530,gy+15,"from worldwide",15,MUTE,"normal","middle")
arrow(636,gy,712,"ITZ")
rect(716,gy-44,320,88,NAVY,rx=12);txt(876,gy-20,"NODE",18,WHITE,"bold","middle")
rect(736,gy-4,140,32,WHITE,rx=7);txt(806,gy+18,"2 wet-leased",13,NAVY,"bold","middle")
rect(884,gy-4,132,32,WHITE,rx=7);txt(950,gy+18,"ITZ container",13,NAVY,"bold","middle")
arrow(1042,gy,1118,None)
rect(1120,gy-28,210,56,WHITE,rx=10,stroke=LINE,sw=2)
txt(1225,gy-4,"Launches",17,INK,"bold","middle");txt(1225,gy+15,"+ research data",15,MUTE,"normal","middle")
txt(88,300,"On-ramp proven at home in Montana. First two U.S. launch sites — Spaceport America (New Mexico) + Montana Spaceport & Test Range — both need the ITZ for inbound international payloads.",15,MUTE)

# BAND 2 — DE-RISK VALUE
rect(60,330,1480,178,PANEL);rect(60,330,6,178,ORANGE,rx=0)
txt(88,368,"2 · Why customers come — de-risk before orbit",23,ORANGE,"bold")
txt(88,396,"Fly & qualify in a real flight environment (boost · high-g · vacuum · reentry · recovery), then get the hardware back to iterate:",17,INK)
cxp=88
for c in ["Avionics","Controls","Flight software","Sensors","Flight systems"]:
    cxp=chip(cxp,412,c)
# flow
fy2=470
rect(88,fy2-24,150,30,NAVY,rx=15);txt(163,fy2-3,"Suborbital test",14,WHITE,"bold","middle")
arrow(250,fy2-9,318,"qualify")
rect(322,fy2-24,140,30,WHITE,rx=15,stroke=LINE,sw=2);txt(392,fy2-3,"Orbital flight",14,INK,"bold","middle")
txt(500,fy2-3,"→  significant risk & cost reduction",19,ORANGE,"bold")
txt(1050,fy2-3,"the upstream qualification lane as allies",15,MUTE)
txt(1050,fy2+16,"build their own reusable orbital platforms",15,MUTE)

# BAND 3 — NETWORK calendar
cy=528;ch=306
rect(60,cy,1480,ch,PANEL);rect(60,cy,6,ch,GREEN,rx=0)
txt(88,cy+38,"3 · The Network — a launch every month of the year",23,GREEN,"bold")
months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
cellW=98;rowH=32
for j,m in enumerate(months):
    txt(330+j*cellW+cellW/2,cy+74,m,17,MUTE,"normal","middle")
rows=[("Spaceport America · US",NAVY,[0,3,6,9]),
      ("Montana Spaceport · US",NAVY,[1,4,7,10]),
      ("Japan · HOSPO",ORANGE,[2,5,8,11]),
      ("Italy + Nodes 5–12 (scale)","#8aa0b4",list(range(12)))]
ry0=cy+90
for r,(label,col,mset) in enumerate(rows):
    ry=ry0+r*(rowH+7)
    txt(88,ry+rowH-10,label,16,INK,"bold")
    for j in range(12):
        x=330+j*cellW
        if r==3: rect(x+3,ry,cellW-6,rowH,"#dbe4ee",rx=6)
        elif j in mset:
            rect(x+3,ry,cellW-6,rowH,col,rx=6);txt(x+cellW/2,ry+rowH-10,"launch",12,WHITE,"bold","middle")
        else: rect(x+3,ry,cellW-6,rowH,"#dde6ef",rx=6)
sy=ry0+4*(rowH+7)+2
txt(88,sy+19,"Coverage",15,GREEN,"bold")
for j in range(12):
    x=330+j*cellW;rect(x+3,sy,cellW-6,23,GREEN,rx=6);txt(x+cellW/2,sy+17,"✓",14,WHITE,"bold","middle")
txt(88,cy+ch-12,"Two U.S. Nodes + Japan already cover all twelve months · each Node ~4 campaigns/yr · scale to 6–12 Nodes",15,MUTE)

# BAND 4 — cadence + Artemis
py=852;ph=214
rect(60,py,720,ph,PANEL);rect(60,py,6,ph,ORANGE,rx=0)
txt(88,py+38,"4 · Cadence",23,ORANGE,"bold")
txt(88,py+66,"One-week campaign, every 3 months per Node. Flights/week scale up:",16,MUTE)
base=py+176
for i,v in enumerate([3,4,5,6]):
    x=88+i*64;hgt=v*18
    rect(x,base-hgt,48,hgt,ORANGE,rx=6);txt(x+24,base+22,str(v),18,INK,"bold","middle")
txt(88+3.7*64,base+22,"flights / week",15,MUTE)
txt(430,py+112,"Per campaign:",17,INK,"bold")
txt(430,py+140,"•  2 NASA flights",17,INK)
txt(430,py+166,"•  1 commercial  (higher value)",17,INK)
rect(820,py,720,ph,NAVY)
txt(848,py+40,"Payoff · Artemis Capability Testing",21,WHITE,"bold")
for i,b in enumerate(["A global, year-round, high-cadence suborbital network becomes",
                      "on-demand capability testing for Artemis — de-risking",
                      "hardware for the Moon and Mars, with a choice of",
                      "research Nodes worldwide to run each test."]):
    txt(848,py+76+i*26,b,17,"#d7e2ee")

fy=1080
rect(60,fy,1480,42,"#f3f6fa",rx=10,stroke=LINE,sw=1)
txt(80,fy+28,"Flywheel:  wet lease → U.S. rocket manufacturing → O&M revenue → local handover (MLA) → upgrade / next-gen sales → more Nodes → year-round cadence → Artemis.",16,INK,"bold")
txt(60,H-12,"Planning targets; cadence and export scope pending DDTC/BIS approvals. Exos = one of only three FAA-licensed reusable rocket launch providers in the U.S.",13,MUTE)
s.append("</svg>")
open("ITZ_Operating_Model_Infographic.svg","w").write("\n".join(s))
print("wrote svg")
