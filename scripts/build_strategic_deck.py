#!/usr/bin/env python3
"""Exos — Strategic Capital deck (institutional / Starfighters / Title III / OSC).
Timeline-story arc, cut down from the Series-A + Navy-Commission decks.
Figures-of-record enforced: $169.7M valuation only; $1M/flight; rapid reuse PROPOSED (not demonstrated);
management-prepared financials; no 'currently flying commercially'."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

NAVY=RGBColor(0x0B,0x2A,0x4A); RED=RGBColor(0xC8,0x10,0x2E); INK=RGBColor(0x14,0x20,0x2E)
GRAY=RGBColor(0x5A,0x66,0x75); LIGHT=RGBColor(0xF5,0xF8,0xFB); WHITE=RGBColor(0xFF,0xFF,0xFF)
CARD=RGBColor(0xE1,0xE8,0xF0)
ROOT="/Users/exomac/.openclaw/workspace"
prs=Presentation(); prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)
BLANK=prs.slide_layouts[6]
W=prs.slide_width; H=prs.slide_height

def box(sl,x,y,w,h,fill=None,line=None,lw=1.0):
    sp=sl.shapes.add_shape(MSO_SHAPE.RECTANGLE,x,y,w,h)
    sp.shadow.inherit=False
    if fill is None: sp.fill.background()
    else: sp.fill.solid(); sp.fill.fore_color.rgb=fill
    if line is None: sp.line.fill.background()
    else: sp.line.color.rgb=line; sp.line.width=Pt(lw)
    return sp

def txt(sl,x,y,w,h,runs,align=PP_ALIGN.LEFT,anchor=MSO_ANCHOR.TOP,sp_after=4):
    tb=sl.shapes.add_textbox(x,y,w,h); tf=tb.text_frame; tf.word_wrap=True
    tf.vertical_anchor=anchor
    for i,(t,sz,color,bold) in enumerate(runs):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.alignment=align; p.space_after=Pt(sp_after); p.space_before=Pt(0)
        r=p.add_run(); r.text=t; f=r.font
        f.size=Pt(sz); f.bold=bold; f.color.rgb=color; f.name="Helvetica Neue"
    return tb

def header(sl,kicker,title):
    box(sl,0,0,W,Inches(1.15),fill=NAVY)
    box(sl,0,Inches(1.15),W,Pt(3),fill=RED)
    txt(sl,Inches(0.55),Inches(0.16),Inches(12.2),Inches(0.35),[(kicker,12,RED,True)])
    txt(sl,Inches(0.55),Inches(0.44),Inches(12.2),Inches(0.66),[(title,25,WHITE,True)])

def bullets(sl,x,y,w,items,sz=14,gap=7,head=None):
    tb=sl.shapes.add_textbox(x,y,w,Inches(5)); tf=tb.text_frame; tf.word_wrap=True
    first=True
    if head:
        p=tf.paragraphs[0]; r=p.add_run(); r.text=head; r.font.size=Pt(12); r.font.bold=True
        r.font.color.rgb=RED; r.font.name="Helvetica Neue"; p.space_after=Pt(6); first=False
    for it in items:
        p=tf.paragraphs[0] if first else tf.add_paragraph(); first=False
        p.space_after=Pt(gap)
        r=p.add_run(); r.text="▸  "; r.font.size=Pt(sz); r.font.color.rgb=RED; r.font.bold=True; r.font.name="Helvetica Neue"
        parts=it.split("**")
        for j,seg in enumerate(parts):
            if not seg: continue
            rr=p.add_run(); rr.text=seg; rr.font.size=Pt(sz); rr.font.color.rgb=INK
            rr.font.bold=(j%2==1); rr.font.name="Helvetica Neue"
    return tb

def statrow(sl,y,stats):
    n=len(stats); gap=Inches(0.18); m=Inches(0.55)
    tw=W-2*m-(n-1)*gap; cw=int(tw/n)
    for i,(num,lab) in enumerate(stats):
        x=m+i*(cw+gap)
        box(sl,x,y,cw,Inches(1.15),fill=LIGHT,line=CARD,lw=1)
        box(sl,x,y,cw,Pt(3),fill=RED)
        txt(sl,x,y+Inches(0.16),cw,Inches(0.5),[(num,22,NAVY,True)],align=PP_ALIGN.CENTER)
        txt(sl,x,y+Inches(0.66),cw,Inches(0.42),[(lab,9.5,GRAY,False)],align=PP_ALIGN.CENTER)

def footer(sl,note="Exos Aerospace Systems & Technologies, Inc. — Private & Confidential. Financial figures are management-prepared estimates; supporting materials in the data room."):
    txt(sl,Inches(0.55),Inches(7.02),Inches(12.2),Inches(0.4),[(note,7.5,GRAY,False)])

def add_img_fit(sl,path,cx,cardw,top,zoneh):
    from PIL import Image
    iw,ih=Image.open(path).size; ar=iw/ih
    maxw=cardw-Inches(0.28); w=maxw; h=int(w/ar)
    if h>zoneh: h=zoneh; w=int(h*ar)
    left=cx+(cardw-w)//2
    sl.shapes.add_picture(path,left,top,width=w,height=h)

def slide(): return prs.slides.add_slide(BLANK)

# ---------- 1. TITLE ----------
s=slide(); box(s,0,0,W,H,fill=NAVY); box(s,0,Inches(4.9),W,Pt(4),fill=RED)
logo=os.path.join(ROOT,"ExosLogo_transparent.png")
if os.path.exists(logo): s.shapes.add_picture(logo,Inches(0.55),Inches(0.5),height=Inches(0.95))
txt(s,Inches(0.6),Inches(2.15),Inches(12),Inches(1.4),[("EXOS AEROSPACE",44,WHITE,True),("AI-Native Industrial Power for the Space & Defense Industrial Base",20,RGBColor(0xDC,0xE6,0xF0),True)])
txt(s,Inches(0.6),Inches(5.15),Inches(12),Inches(1.4),[
 ("Reusable flight-test platform  ·  TRL-9 lunar-proven composites  ·  the consortium that re-industrializes space & defense",13,RGBColor(0xB9,0xC6,0xD6),False),
 ("Profitable (2025)  ·  Raising $10M first close (tranched to $25M)  ·  August 2026",13,WHITE,True),
 ("John Quinn, Cofounder & CEO  ·  jquinn@exosaero.com  ·  www.exosaero.com   |   PRIVATE & CONFIDENTIAL",10,GRAY,False)])

# ---------- 2. THE MOMENT ----------
s=slide(); header(s,"WHY NOW","Three waves converge — and Exos sits at the intersection")
cols=[("THE $20T PHYSICAL WORLD","AI conquered software; the physical world is next. Almost no one can apply AI to real flight hardware. Exos already does."),
      ("THE INDUSTRIAL-BASE IMPERATIVE","Congress and DoD are re-industrializing for surge to 2045. Capital is moving to dual-use hardware and dormant capacity — Exos's exact lane."),
      ("THE CAPITAL WAVE","The SpaceX IPO and record defense spending are pulling institutional capital into space-defense hardware. The window to enter at this basis is now.")]
m=Inches(0.55); gap=Inches(0.3); cw=int((W-2*m-2*gap)/3)
for i,(h,b) in enumerate(cols):
    x=m+i*(cw+gap); box(s,x,Inches(1.6),cw,Inches(4.4),fill=LIGHT,line=CARD,lw=1); box(s,x,Inches(1.6),cw,Pt(3),fill=RED)
    txt(s,x+Inches(0.22),Inches(1.85),cw-Inches(0.44),Inches(0.8),[(h,14,NAVY,True)])
    txt(s,x+Inches(0.22),Inches(2.7),cw-Inches(0.44),Inches(3),[(b,13,INK,False)])
txt(s,Inches(0.55),Inches(6.25),Inches(12.2),Inches(0.7),[("Exos is the rare asset that is all three at once: a profitable, licensed, reusable hardware operator, running AI-native, holding lunar-proven IP.",13,NAVY,True)],align=PP_ALIGN.CENTER)
footer(s)

# ---------- FOUR CORE ASSETS ----------
s=slide(); header(s,"FOUR CORE ASSETS","Three technical assets, compounded by a fourth")
assets=[("1 · SCORPIUS TYPE-5 CRYO IP + ROFR","TRL-9 linerless composite cryogenic tanks, flight-proven on Intuitive Machines' IM-1 and IM-2. Exos holds 18% plus a right of first refusal at the 2021 basis — strategic valuation arbitrage."),
        ("2 · REUSABLE SUBORBITAL PLATFORM","BLK3 — one of only three FAA-licensed reusable rocket launch providers in the U.S. Recoverable, high-cadence, minimal fixed infrastructure."),
        ("3 · RDRE / ADVANCED PROPULSION","Active USAF SBIR Phase II on a government-furnished RDRE, opening a sole-source Phase III path with no dollar ceiling. Reusable-RDRE roadmap."),
        ("4 · AI-DEPLOYED OPERATING PLATFORM","Mission Control plus a governed agent fleet run BD, capture, compliance, and operations. A compounding, owned decision-and-audit-trail asset — capital-efficient and ITAR/CUI-safe.")]
mA=Inches(0.55); gapA=Inches(0.3); cwA=int((W-2*mA-gapA)/2); chA=Inches(2.15); y0A=Inches(1.55); vgapA=Inches(0.22)
for i,(h,b) in enumerate(assets):
    r,c=divmod(i,2); x=mA+c*(cwA+gapA); y=y0A+r*(chA+vgapA)
    accent = NAVY if i==3 else RED
    box(s,x,y,cwA,chA,fill=LIGHT,line=CARD,lw=1); box(s,x,y,cwA,Pt(3),fill=accent)
    txt(s,x+Inches(0.22),y+Inches(0.16),cwA-Inches(0.44),Inches(0.5),[(h,14,NAVY,True)])
    txt(s,x+Inches(0.22),y+Inches(0.72),cwA-Inches(0.44),chA-Inches(0.86),[(b,12.5,INK,False)])
txt(s,Inches(0.55),Inches(6.35),Inches(12.2),Inches(0.6),[("Assets 1–3 are the hardware and IP; #4 is the operating system that compounds them — management-characterized, a moat, not a separate line item. Single valuation of record: $169.7M.",12,NAVY,True)],align=PP_ALIGN.CENTER)
footer(s)

# ---------- 3. TIMELINE STORY ----------
s=slide(); header(s,"THE STORY","25 years of reusable rockets — to a profitable, lunar-proven inflection point")
tl=[("2000","Armadillo Aerospace — reusable VTVL rockets; 100+ engines built"),
    ("2014","John Quinn buys out the program → Exos Aerospace"),
    ("2018–19","SARGE: 4 flights in 14 months, guided-canopy recovery — capital-efficient reuse"),
    ("2021","Carbon-composite pivot; Scorpius arbitrage struck (18% + ROFR at 2021 basis)"),
    ("2024–25","Scorpius Type-5 cryo tanks fly to the Moon — IM-1 Odysseus & IM-2 Athena (TRL-9)"),
    ("2025","First profitable year; 1 of 3 FAA-licensed reusable providers; AI-native ops live"),
    ("2026 →","Series A: exercise the Scorpius ROFR + stand up the industrial-base consortium")]
y=Inches(1.75); rowh=Inches(0.66)
for i,(yr,ev) in enumerate(tl):
    yy=y+i*rowh
    box(s,Inches(0.55),yy+Inches(0.05),Inches(1.5),Inches(0.5),fill=NAVY)
    txt(s,Inches(0.55),yy+Inches(0.12),Inches(1.5),Inches(0.4),[(yr,13,WHITE,True)],align=PP_ALIGN.CENTER)
    box(s,Inches(2.15),yy+Inches(0.05),Inches(10.6),Inches(0.5),fill=LIGHT,line=CARD,lw=0.75)
    txt(s,Inches(2.35),yy+Inches(0.13),Inches(10.3),Inches(0.4),[(ev,12.5,INK,False)])
footer(s)

# ---------- 3b. HARDWARE HISTORY — VERBATIM COPY OF ORIGINAL SLIDE 18 (inserted post-build) ----------
# (the authentic rich hardware-history slide is copied wholesale from the Series-A deck at the end)

# ---------- 4. THE PLATFORM ----------
s=slide(); header(s,"THE PLATFORM","BLK3 — a reusable de-risk engine for the whole orbital industry")
bullets(s,Inches(0.55),Inches(1.55),Inches(7.0),[
 "**One of only three FAA-licensed reusable** launch-and-recovery providers in the U.S. (Part 431 → Part 450).",
 "**De-risk orbital programs on a proven ~$5M vehicle** instead of losing $50–100M rockets on first flight — industry loses 4–7 to reach orbit; Exos can help cut that to 2–5.",
 "Customers place avionics, sensors, controls, and recovery in the BLK3 bay; **hardware comes back, not just telemetry.**",
 "**$1M per flight** (135 kg @ $7,500/kg); designed for rapid reuse (a 2-flight / 48-hour turnaround is proposed under Project KARMEN, not yet demonstrated).",
 "Licensed and hover-demonstrated; **first commercial flight targeted early 2027.**"],sz=13.5,gap=9)
box(s,Inches(7.9),Inches(1.55),Inches(4.85),Inches(4.55),fill=LIGHT,line=CARD,lw=1); box(s,Inches(7.9),Inches(1.55),Pt(3),Inches(4.55),fill=RED)
img=os.path.join(ROOT,"assets/blk3_hover.png")
if os.path.exists(img): s.shapes.add_picture(img,Inches(8.05),Inches(1.75),width=Inches(4.55))
txt(s,Inches(8.05),Inches(4.65),Inches(4.55),Inches(1.3),[("BLK3 PSRLV — vertical for integrated test at Caddo Mills. Reusable, recoverable, licensed.",10.5,GRAY,False)])
footer(s)

# ---------- 5. SCORPIUS ROFR ----------
s=slide(); header(s,"THE CROWN JEWEL","Scorpius ROFR — strategic arbitrage, not a generic acquisition")
statrow(s,Inches(1.7),[("PAY  $3.4M","exercise price (frozen 2021 basis)"),("OWN  $20–40M","TRL-9 lunar-flown Type-5 IP"),("6–12×","value vs. exercise price"),("2×","flown to the Moon (IM-1 / IM-2)")])
bullets(s,Inches(0.55),Inches(3.15),Inches(12.2),[
 "**World's only TRL-9 linerless (Type-5) cryogenic composite tank technology**, flown as fuel & LOX tanks on Intuitive Machines' Odysseus (2024) and Athena (2025).",
 "**~50% mass reduction** vs. metal; room-temperature-cure resin (no microcracking through 150 cycles); qualified to fuel on a Falcon 9 on the pad; export-approved variant.",
 "Exos holds **18% + a right of first refusal at the 2021 basis** — the value gap is defined upside with a defined downside.",
 "Enables in-space refueling and long-duration cryo storage — the tankage a commercial space economy is built on."],sz=13.5,gap=9)
txt(s,Inches(0.55),Inches(6.35),Inches(12.2),Inches(0.5),[("Arbitrage figures are Exos's own valuation, independent of the $169.7M 409A equity value.",9.5,GRAY,False)])
footer(s)

# ---------- 6. AI-NATIVE ----------
s=slide(); header(s,"THE MULTIPLIER","AI-native operations — 5× output, and the way we commercialize dormant tech")
bullets(s,Inches(0.55),Inches(1.55),Inches(7.0),[
 "**Mission Control** — an in-house, AI-native operating system (ExO 3.0). Ran a 12-person team to **~5× output in 9 months.**",
 "AI-driven DFARS/CFR compliance (caught same-day regulatory changes on a live contract); CMMC L1 → L2; DoD data walled off from commercial AI.",
 "**This is how the consortium ships:** the AI stack drops into acquired sub-50-person firms and makes them AI-native overnight — the commercialization engine dormant DoD tech never had.",
 "The physical-AI proof point institutional capital is looking for — AI applied where it is hardest, real flight hardware."],sz=13.5,gap=10)
statrow(s,Inches(5.35),[("5×","output, 12-person team, 9 mo"),("$180M","AI-built pipeline value"),("96%","decisions cleared in-system"),("1,240","tasks orchestrated")])
footer(s)

# ---------- 7. INDUSTRIAL-BASE THESIS ----------
s=slide(); header(s,"THE THESIS","Activate America's dormant industrial capacity")
bullets(s,Inches(0.55),Inches(1.55),Inches(6.1),[
 "**Stranded capital is real:** Virgin Orbit ($1B+ → Ch.11), Astra ($500M), ABL ($461M) — enormous capacity built, then idled.",
 "**~10 partner firms** (CTD, GTL, Goodman, Firefly, Via Space) sit at **5–20% utilization**, holding **$1B+ of DoD-funded tech, <5% commercialized.**",
 "Exos is the **prime integrator** that knits them into one skunk-works — surging tanks, SRM cases, missile & Navy structures with **no new CapEx.**",
 "The same model transfers beyond space: advanced mfg, critical materials, energy, maritime, munitions."],sz=13.5,gap=9,head="THE PROBLEM & THE ENGINE")
box(s,Inches(7.0),Inches(1.55),Inches(5.75),Inches(4.55),fill=LIGHT,line=CARD,lw=1); box(s,Inches(7.0),Inches(1.55),Pt(3),Inches(4.55),fill=RED)
txt(s,Inches(7.22),Inches(1.72),Inches(5.4),Inches(0.5),[("SAME PLANT, UP TO 3× OUTPUT",13,NAVY,True)])
bullets(s,Inches(7.22),Inches(2.25),Inches(5.35),[
 "Idle winders & machines put to work at ~$150/hr — **10× manufacturing overnight.**",
 "Humanoids + Mission Control fill 2nd/3rd shifts the labor market can't — fixed cost amortized across up to 3× output.",
 "Partner IP advances the Exos tech stack — continuous improvement, not one-off buys."],sz=12.5,gap=8)
footer(s)

# ---------- 8. GOVERNMENT VALIDATION ----------
s=slide(); header(s,"VALIDATION","The government has already validated the platform — and under-resourced it")
box(s,Inches(0.55),Inches(1.6),Inches(12.2),Inches(1.7),fill=LIGHT,line=CARD,lw=1); box(s,Inches(0.55),Inches(1.6),Pt(3),Inches(1.7),fill=RED)
txt(s,Inches(0.8),Inches(1.78),Inches(11.7),Inches(0.5),[("PROJECT KARMEN — USSF SBIR SF254-D1002 (Direct-to-Phase-II)",15,NAVY,True)])
txt(s,Inches(0.8),Inches(2.28),Inches(11.7),Inches(1.0),[("A reusable suborbital platform to empirically qualify cargo, supplies & equipment under real spacelift conditions — a proposed 2-flight / 48-hour rapid-turnaround demonstration (not yet demonstrated). Competitively selected, then funded at ~1/10th of its validated $3M scope. A reissue at the proposed scope funds the next commercial launches and stands the pilot up in months.",12.5,INK,False)])
bullets(s,Inches(0.55),Inches(3.5),Inches(12.2),[
 "**$10M unlocks ~$34M** in government co-investment (TACFI + STRATFI) — a 3.4× capital multiplier. **Non-dilutive upside, milestone-gated — not counted in the base case.**",
 "**$180M AI-built pipeline;** Commission on the Future of the Navy toured Exos (Aug 2026) and is weighing the consortium/ITZ model for its report.",
 "**Secure International Trade Zone** (DHS-CRADA containers) bridges the foreign carbon fiber and cryo tankage the U.S. can't source — a national supply-chain-resilience tool."],sz=13.5,gap=10)
footer(s)

# ---------- 9. THE CAPITAL MECHANISM (Title III / OSC) ----------
s=slide(); header(s,"THE MECHANISM","A pilot fund built on DoD's own playbook — where strategic capital plugs in")
bullets(s,Inches(0.55),Inches(1.55),Inches(6.1),[
 "**$50M pilot fund, deployed in 12–18 months** — activation capital for dormant capacity, steered by insiders, run by pros.",
 "Mirrors mechanisms DoD already uses: **DPA Title III** (direct industrial-base investment), the **Office of Strategic Capital** (loans / loan guarantees), and **OTA consortia** (NSTXL / SpaceWERX).",
 "**Cost-share where viable; the fund fills the gap where it isn't** — a blanket 50% match kills small vendors.",
 "**OTA + firm-fixed-price** is the home for this: weeks-to-award, outcome-based, non-dilutive alongside the equity."],sz=13.5,gap=9,head="FOR TITLE III / OSC / STRATEGIC CAPITAL")
box(s,Inches(7.0),Inches(1.55),Inches(5.75),Inches(4.55),fill=NAVY); box(s,Inches(7.0),Inches(1.55),Pt(3),Inches(4.55),fill=RED)
txt(s,Inches(7.25),Inches(1.78),Inches(5.3),Inches(0.5),[("THE THREE WAYS TO PARTICIPATE",14,WHITE,True)])
bullets_dark=[("1  Institutional equity","Series A at a $169.7M 409A basis; TXSE listing path; SpaceX-IPO tailwind."),
 ("2  Strategic / Starfighters","JV / co-development on flight-test + reusable spacelift; shared cadence and range access."),
 ("3  Title III / OSC / OTA","Non-dilutive industrial-base capital into the consortium + KARMEN reissue.")]
yy=Inches(2.35)
for h,b in bullets_dark:
    txt(s,Inches(7.25),yy,Inches(5.3),Inches(0.4),[(h,13,RGBColor(0xFF,0xC9,0xC9),True)])
    txt(s,Inches(7.25),yy+Inches(0.32),Inches(5.3),Inches(0.7),[(b,11.5,WHITE,False)])
    yy=yy+Inches(1.12)
footer(s)

# ---------- 10. THE NUMBERS ----------
s=slide(); header(s,"THE NUMBERS","Profitable today, a government-backed path to ~$120M")
statrow(s,Inches(1.7),[("$1.55M","FY2025 revenue"),("102%","4-yr revenue CAGR"),("17%","2025 EBITDA margin (first profit)"),("~$5M","combined pro-forma run-rate")])
bullets(s,Inches(0.55),Inches(3.15),Inches(7.0),[
 "**History:** $0.19M (2022) → $0.31M → $0.63M → **$1.55M (2025), first profitable year.**",
 "**Projection:** **~$120M by Y5 on a contracted backbone** (conservative Cash Flow case); TACFI/STRATFI/entX-expansion sit in a separate **upside** layer, not the base.",
 "**Unit economics:** BLK4 sale $6M (50%+ GM); wet-lease flight $3.75M (60%+); tanks $200K–$1M (45%+).",
 "**Valuation: $169.7M** independent 409A equity value (Eqvista 3/31/26; $8.66/share; DLOM 36.51%) — comps cross-check 4–6× 2028E revenue."],sz=13,gap=9)
box(s,Inches(7.9),Inches(3.15),Inches(4.85),Inches(3.0),fill=LIGHT,line=CARD,lw=1); box(s,Inches(7.9),Inches(3.15),Pt(3),Inches(3.0),fill=RED)
txt(s,Inches(8.12),Inches(3.32),Inches(4.4),Inches(0.5),[("WHERE WE'VE BEEN → WHERE WE'RE GOING",12,NAVY,True)])
yrs=[("2022","$0.19M"),("2023","$0.31M"),("2024","$0.63M"),("2025","$1.55M ✓ profit"),("Y5","~$120M")]
yy=Inches(3.85)
for yr,v in yrs:
    txt(s,Inches(8.12),yy,Inches(1.2),Inches(0.35),[(yr,12,GRAY,True)])
    txt(s,Inches(9.5),yy,Inches(3.0),Inches(0.35),[(v,12.5,NAVY,True)])
    yy=yy+Inches(0.44)
footer(s)

# ---------- 11. USE OF FUNDS / ASK ----------
s=slide(); header(s,"THE ASK","$10M first close — 100% deployed, unlocking a 3.4× government multiplier")
bullets(s,Inches(0.55),Inches(1.55),Inches(7.0),[
 "**$10M first close (tranched to $25M):**",
 "   • Scorpius ROFR — **$3.4M** (the arbitrage)",
 "   • RDRE / TACFI match — unlocks ~**$30M STRATFI**",
 "   • BLK3/BLK4 vehicle build + working capital, Part 450, contingency",
 "**$10M unlocks ~$34M** in government co-investment — a **3.4× multiplier (non-dilutive upside).**",
 "**Listing path:** Texas Stock Exchange (TXSE), dated/conditioned, ~18–24 months.",
 "All common stock; founders retain ~56% control; EAI investors' first liquidity window in the raise."],sz=13,gap=8)
box(s,Inches(7.9),Inches(1.55),Inches(4.85),Inches(4.55),fill=NAVY); box(s,Inches(7.9),Inches(1.55),Pt(3),Inches(4.55),fill=RED)
txt(s,Inches(8.12),Inches(1.8),Inches(4.4),Inches(0.5),[("WHAT $10M ENABLES",15,WHITE,True)])
bullets2=["Exercise the Scorpius ROFR — lock the 6–12× arbitrage","Stand up the industrial-base consortium","Advance the RDRE flight-test program","Put idle partner capacity to work — no new CapEx","Bridge to the Title III / OSC non-dilutive layer"]
tb=s.shapes.add_textbox(Inches(8.12),Inches(2.4),Inches(4.4),Inches(3.5)); tf=tb.text_frame; tf.word_wrap=True
for i,b in enumerate(bullets2):
    p=tf.paragraphs[0] if i==0 else tf.add_paragraph(); p.space_after=Pt(11)
    r=p.add_run(); r.text="▸  "; r.font.size=Pt(13); r.font.color.rgb=RGBColor(0xFF,0xC9,0xC9); r.font.bold=True
    rr=p.add_run(); rr.text=b; rr.font.size=Pt(12.5); rr.font.color.rgb=WHITE; rr.font.name="Helvetica Neue"
footer(s)

# ---------- 12. CLOSE ----------
s=slide(); box(s,0,0,W,H,fill=NAVY); box(s,0,Inches(3.7),W,Pt(4),fill=RED)
txt(s,Inches(0.7),Inches(2.3),Inches(12),Inches(1.6),[("De-risk the impossible.",40,WHITE,True),("Deliver the mass that builds humanity's future in space.",22,RGBColor(0xDC,0xE6,0xF0),True)])
txt(s,Inches(0.7),Inches(4.2),Inches(12),Inches(1.2),[
 ("John Quinn, Cofounder & CEO",15,WHITE,True),
 ("jquinn@exosaero.com  ·  +1-972-740-8355  ·  www.exosaero.com",12,RGBColor(0xB9,0xC6,0xD6),False),
 ("PRIVATE & CONFIDENTIAL — not an offer to sell or a solicitation of securities. Financial figures are management-prepared estimates.",9,GRAY,False)])

# ---------- RESTORE the authentic hardware-history slide (verbatim copy of source slide 18) ----------
import copy
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn, nsdecls
RELNS="{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

def force_black_history(slide):
    """The copied hardware-history slide gets its black look from the ORIGINAL
    deck's theme (bg1->dk1=black, tx1->lt1=white). In this deck bg1->white, so it
    rendered white-on-white. Make the slide theme-independent: explicit black bg,
    a color-map override, and inherited (white) text pinned to explicit white so
    it's correct in PowerPoint AND any previewer."""
    sld=slide._element
    cSld=sld.find(qn('p:cSld'))
    old=cSld.find(qn('p:bg'))
    if old is not None: cSld.remove(old)
    cSld.insert(0, parse_xml('<p:bg %s><p:bgPr><a:solidFill><a:srgbClr val="000000"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>' % nsdecls('p','a')))
    ov=sld.find(qn('p:clrMapOvr'))
    if ov is not None: sld.remove(ov)
    sld.append(parse_xml('<p:clrMapOvr %s><a:overrideClrMapping bg1="dk1" tx1="lt1" bg2="dk2" tx2="lt2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/></p:clrMapOvr>' % nsdecls('p','a')))
    for shp in slide.shapes:
        if not shp.has_text_frame: continue
        for para in shp.text_frame.paragraphs:
            for run in para.runs:
                if run.font.color is not None and run.font.color.type is None:
                    run.font.color.rgb=RGBColor(0xFF,0xFF,0xFF)
def copy_slide_verbatim(src_slide, dst_prs, layout, insert_at):
    dst=dst_prs.slides.add_slide(layout)
    for ph in list(dst.shapes):           # strip default placeholders
        ph._element.getparent().remove(ph._element)
    idmap={}                               # copy image (and other) parts, remap rIds
    for rId,rel in src_slide.part.rels.items():
        if "image" in rel.reltype:
            try: idmap[rId]=dst.part.relate_to(rel.target_part, rel.reltype)
            except Exception: pass
    for shp in src_slide.shapes:           # deep-copy every shape verbatim
        el=copy.deepcopy(shp._element)
        for node in el.iter():
            for attr in (RELNS+"embed", RELNS+"link"):
                v=node.get(attr)
                if v in idmap: node.set(attr, idmap[v])
        dst.shapes._spTree.append(el)
    # move the new (last) slide into position `insert_at`
    sld=dst_prs.slides._sldIdLst; items=list(sld)
    sld.remove(items[-1]); sld.insert(insert_at, items[-1])
    return dst

try:
    src=Presentation(os.path.join(ROOT,"mission-control/uploads/Exos_SeriesA_PitchDeck_June2026_TXSE_FULL.pptx"))
    src18=list(src.slides)[17]            # original hardware-history slide
    hist=copy_slide_verbatim(src18, prs, BLANK, 3)   # place as slide 4 (0-based index 3)
    force_black_history(hist)                          # lock the original black bg + white text
    print("restored original slide 18 verbatim at position 4 (black bg + white text locked)")
except Exception as e:
    print("SLIDE-COPY FAILED:", e)

out=os.path.join(ROOT,"drafts/Exos_Strategic_Capital_Deck_2026-08-13.pptx")
prs.save(out); print("SAVED",out,"slides:",len(list(prs.slides)))
