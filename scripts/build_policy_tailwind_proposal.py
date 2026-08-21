#!/usr/bin/env python3
"""Exos policy-tailwind brief on the PRIMARY letterhead (editable Word).
Run: PYTHONNOUSERSITE=1 python3.12 scripts/build_policy_tailwind_proposal.py
"""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

LH = "assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
OUT = "data-room/Exos_SeriesA/_CANONICAL/Exos_Policy_Tailwind_NSTP_2026-08-21.docx"
NAVY = RGBColor(0x0A,0x3D,0x7C); DARK = RGBColor(0x1A,0x1A,0x1A); GREY = RGBColor(0x55,0x55,0x55); WHITE=RGBColor(0xFF,0xFF,0xFF)
doc = Document(LH)

def _set(run,size,color=DARK,bold=False,italic=False,font="Calibri"):
    run.font.size=Pt(size); run.font.color.rgb=color; run.font.bold=bold; run.font.italic=italic; run.font.name=font
def title(t,size=17):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; _set(p.add_run(t),size,NAVY,bold=True); return p
def sub(t,size=10.5):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; _set(p.add_run(t),size,GREY,italic=True); return p
def h1(t):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(11); p.paragraph_format.space_after=Pt(3); _set(p.add_run(t),13,NAVY,bold=True); return p
def body(t,size=10.5,align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(6); p.alignment=align; _set(p.add_run(t),size,DARK); return p
def bullet(t,size=10.5):
    p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(0.25); p.paragraph_format.space_after=Pt(2); _set(p.add_run("•  "+t),size,DARK); return p
def note(t,size=8.5):
    p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(4); _set(p.add_run(t),size,GREY,italic=True); return p

def shade(cell,hexcolor):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd')
    shd.set(qn('w:val'),'clear'); shd.set(qn('w:fill'),hexcolor); tcPr.append(shd)
def borders(table):
    tblPr=table._tbl.tblPr; b=OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        e=OxmlElement(f'w:{edge}'); e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:space'),'0'); e.set(qn('w:color'),'BFBFBF'); b.append(e)
    tblPr.append(b)
def cell(c,t,size=9.5,color=DARK,bold=False):
    c.text=""; p=c.paragraphs[0]; p.paragraph_format.space_after=Pt(1); _set(p.add_run(t),size,color,bold=bold)

doc.add_paragraph()
title("Exos Aerospace × National Space Transportation Policy", 18)
sub("Alignment Brief — the “Golden Age of Space Transportation” policy and why it accrues to Exos")
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; _set(p.add_run("Proprietary — Unclassified   |   August 21, 2026   |   Series A data room"),9,GREY)

h1("The policy, in brief")
for t in [
 "Updated U.S. National Space Transportation Policy (August 2026), building on the 2025 “Enabling Competition in the Commercial Space Industry” executive order.",
 "Target: 1,000+ launches and reentries per year on U.S. soil by 2030 — roughly a tenfold expansion of today’s cadence.",
 "DOT/FAA to cut spaceport-construction red tape, streamline launch and reentry licensing at scale (further reworking Part 450), and stand up senior space roles; integrate space traffic with air traffic control.",
 "Enable launch within 48 hours of high-priority civil and national-security missions.",
 "Greater commercial involvement in Moon/Mars; stronger emphasis on exporting American capabilities; develop additional launch and reentry/landing sites.",
 "Implementation depends on existing law and Congressional funding — a multi-year tailwind, not an overnight reset.",
]: bullet(t)

h1("Why it accrues to Exos")
rows=[
 ("Policy pillar","Exos capability & proof point"),
 ("1,000 launches and reentries per year by 2030 — reentry is the underserved half",
  "Reusable and recoverable platform: every Exos flight is a launch and a reentry. Few operators compete on recoverable reentry at cadence — a defensible position on the policy’s hardest goal."),
 ("48-hour responsive launch for high-priority missions",
  "Project Karmen — USAF-funded demonstration of two flights in 48 hours on BLK3. A direct proof point."),
 ("Spaceport / reentry-site build-out; streamlined Part 450 portfolio licensing",
  "Minimal-infrastructure model (pad, power, and communications via a mobile command module) makes new sites inexpensive to stand up; portfolio licensing rewards cadence and multi-site operations (West Texas). One of only three FAA-licensed reusable rocket launch providers in the United States."),
 ("Commercial Moon/Mars",
  "Scorpius Type 5 linerless composite cryogenic tanks — flight-proven at TRL 9 as the fuel and liquid-oxygen tanks on the Intuitive Machines Odysseus (IM-1) and Athena (IM-2) lunar missions — and in-space cryogenic fluid management: enabling infrastructure for lunar and Mars logistics."),
 ("Export American capabilities",
  "International wet-lease and trade-zone posture (Japan, Australia): ITAR-compliant export of U.S. flight-test and launch services."),
]
tbl=doc.add_table(rows=len(rows),cols=2); tbl.autofit=True; borders(tbl)
tbl.columns[0].width=Inches(2.5); tbl.columns[1].width=Inches(4.3)
for i,(a,b) in enumerate(rows):
    if i==0:
        shade(tbl.rows[i].cells[0],"0A3D7C"); shade(tbl.rows[i].cells[1],"0A3D7C")
        cell(tbl.rows[i].cells[0],a,9.5,WHITE,bold=True); cell(tbl.rows[i].cells[1],b,9.5,WHITE,bold=True)
    else:
        cell(tbl.rows[i].cells[0],a,9.5,NAVY,bold=True); cell(tbl.rows[i].cells[1],b,9.5,DARK)

h1("Capital-strategy tie-in")
body("The policy is a federal demand-pull signal that strengthens Exos’s capital pathway: it reinforces the DPA Title III and Office of Strategic Capital cases (national-priority industrial base for reusable launch, reentry, and spaceports), supports the AEDC flight-test-range positioning, and provides a market-timing catalyst for the growth and listing narrative.")

h1("Investor headline")
p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(0.12); p.paragraph_format.space_after=Pt(6)
_set(p.add_run("A national policy targeting 1,000+ launches and reentries per year by 2030 sizes the market Exos is built to serve — reusable, recoverable, responsive flight — and points federal capital (Title III / OSC) at exactly the capability Exos provides."),10.5,NAVY,bold=True)

note("Directional; reflects public policy reporting as of August 21, 2026 and Exos program status. Exos has not to date performed direct RDRE hardware development. BLK3 received its FAA launch license in March 2026 and is preparing for flight; it has not flown commercially. Proprietary — Unclassified. Not investment advice.")

doc.save(OUT); print("BUILT", OUT)
