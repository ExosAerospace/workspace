#!/usr/bin/env python3
"""Series A Strategic deck rev-2026-10-16 (Jon 10/16 22:00: "Series A deck updates to what QuickBooks shows").
QB P&L accrual (pulled 10/16): 2022 $187,842 · 2023 $308,003 · 2024 $623,791 · 2025 $1,493,964; 2025 NOI $253,535 (17.0%); NI $190,855.
Also: license wording per Jon 10/15 (Part 431 → Part 450; hover test campaign completed), drop unsourced "World's only"."""
from pptx import Presentation
WS="/Users/exomac/.openclaw/workspace"; C=f"{WS}/data-room/Exos_SeriesA/_CANONICAL"
SRC=f"{C}/Exos_SeriesA_StrategicDeck_2026-09-06_CURRENT_rev-2026-10-10.pptx"
OUT=f"{C}/Exos_SeriesA_StrategicDeck_2026-09-06_CURRENT_rev-2026-10-16.pptx"
EXACT={"$1.55M":"$1.49M","102%":"100%","4-yr revenue CAGR":"3-yr revenue CAGR (2022–25)",
       "2025 EBITDA margin (first profit)":"2025 operating margin (first profit)","$0.63M":"$0.62M","$1.55M ✓ profit":"$1.49M ✓ profit"}
SUB=[("$0.63M","$0.62M"),("$1.55M","$1.49M"),
     ("a profitable, licensed, reusable hardware operator","a profitable reusable hardware operator under an FAA Part 431 launch license (transitioning to Part 450)"),
     ("BLK3 — one of only three FAA-licensed reusable rocket launch providers in the U.S.","Exos — one of only three FAA-licensed reusable rocket launch providers in the U.S. (Part 431, transitioning to Part 450). BLK3:"),
     ("Licensed and hover-demonstrated;","Hover test campaign completed;"),
     ("Reusable, recoverable, licensed.","Reusable and recoverable."),
     ("World's only TRL-9 linerless","TRL-9 linerless"),
     ("Financial figures are management-prepared estimates","Historical figures per QuickBooks (accrual, unaudited); projections are management-prepared estimates")]
p=Presentation(SRC); log=[]
def fix_para(para):
    t=para.text
    if t.strip() in EXACT and para.runs:
        new=t.replace(t.strip(),EXACT[t.strip()]); para.runs[0].text=new
        for r in para.runs[1:]: r.text=""
        log.append((t,new)); return
    new=t
    for a,b in SUB: new=new.replace(a,b)
    if new!=t and para.runs:
        # replace within single run if possible, else collapse text into the run holding the match
        done=False
        for r in para.runs:
            rt=r.text
            for a,b in SUB: rt=rt.replace(a,b)
            if rt!=r.text: r.text=rt; done=True
        if not done or para.text!=new:
            para.runs[0].text=new
            for r in para.runs[1:]: r.text=""
        log.append((t,para.text))
def walk(shapes):
    for sh in shapes:
        if sh.shape_type==6: walk(sh.shapes); continue
        if sh.has_text_frame:
            for para in sh.text_frame.paragraphs: fix_para(para)
        if getattr(sh,"has_table",False) and sh.has_table:
            for row in sh.table.rows:
                for c in row.cells:
                    for para in c.text_frame.paragraphs: fix_para(para)
for s in p.slides: walk(s.shapes)
p.save(OUT)
for a,b in log: print("-",a[:110],"\n  →",b[:150])
