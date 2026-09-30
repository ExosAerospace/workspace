#!/usr/bin/env python3
"""
build_fly_from_montana_onepager.py — one-page "Fly with Exos → Fly from Montana" sheet for
Edgar (Montana Spaceport) to use with Montana institutions and companies. MC task #3287.

Outputs (drafts/):  Fly_with_Exos_Fly_from_Montana_OnePager.docx  (editable, PRIMARY letterhead)
                    Fly_with_Exos_Fly_from_Montana_OnePager.pdf   (HTML twin → headless Chrome,
                                                                   same letterhead banners)
Edit COPY below and re-run. Claim rules applied: heritage-first framing (SARGE 2018, BLK3 =
latest FAA-licensed vehicle, not yet flown — no "first flight" framing); Montana spaceport =
PLANNED; public list price only ($7,500/kg); no free/in-kind slots; no "one of three" claim.
"""
import os, shutil, subprocess, tempfile, zipfile
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

WS = "/Users/exomac/.openclaw/workspace"
LH = os.path.join(WS, "assets", "EXOS_Letterhead_Greenville_TX_address_PRIMARY.docx")
OUT = os.path.join(WS, "drafts", "Fly_with_Exos_Fly_from_Montana_OnePager")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ORANGE = "F26A21"
GREY = "3A3A3A"

TITLE = "Fly with Exos → Fly from Montana"
SUB = "Reusable suborbital flight for Montana researchers and companies — starting in 2027."
LEAD = ("Put your payload on BLK3 in 2027 from Exos's current launch site. When the Montana spaceport "
        "is licensed and operating, Montana customers get first-flight priority from home. Exos has flown "
        "commercial payloads since 2018 on SARGE; BLK3 is its enhanced successor and Exos's latest "
        "FAA-licensed launch vehicle.")
SECTIONS = [
    ("The offer", [
        "Fly on BLK3 in 2027 from Exos's current launch site.",
        "First-flight priority from Montana once the Montana spaceport, planned with the Montana Spaceport, is licensed and operating.",
        "One team from first call to recovered hardware: payload integration, flight and recovery.",
    ]),
    ("What BLK3 gives your payload", [
        "Up to ~135 kg payload bay on a reusable suborbital vehicle.",
        "Hardware comes back: BLK3 is built to be recovered and reflown, and your payload returns for post-flight inspection.",
        "A real flight environment (launch loads, vibration, altitude and a microgravity coast) plus flight data to support TRL advancement.",
        "Confidential operations for sensitive research and test articles.",
    ]),
    ("Who it's for", [
        "University space labs and student teams moving up from CubeSats, balloons and sounding rockets.",
        "Photonics, sensor and instrument companies qualifying hardware before orbit.",
        "Defense and government test programs: EO/IR, electronics, radiation-tolerant computing.",
        "Tribal colleges and STEM programs flying sponsored student payloads.",
    ]),
    ("How to fund a slot", [
        "NASA Flight Opportunities (TechFlights) and the NASA TechRise Student Challenge.",
        "Montana Space Grant Consortium and NASA EPSCoR (Montana).",
        "SBIR/STTR (NASA, DoD) with Exos as the flight provider.",
        "State, industry and alumni sponsors co-funding research and student payloads.",
    ]),
]
PRICE = "Published list rate: $7,500 per kg. Every quote is sized to your payload — contact us for pricing."
NEXT = ("Next step: talk to the Montana Spaceport (Edgar · edgar@montanaspaceport.com). He introduces you to the "
        "Exos payload team, who scope your payload, flight profile and funding path.")
FINE = ("The Montana spaceport is planned and in development; it is not yet licensed or operating. BLK3 flight dates "
        "depend on vehicle readiness and FAA licensing. exosaero.com")


# ── Word ──────────────────────────────────────────────────────────────────────────────────────
def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_)
    tcPr.append(shd)


def para(container, text="", size=9.5, bold=False, color=GREY, after=2, before=0, italic=False):
    p = container.add_paragraph()
    p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.05
    if text:
        r = p.add_run(text); r.font.size = Pt(size); r.bold = bold; r.italic = italic
        r.font.color.rgb = RGBColor.from_string(color); r.font.name = "Arial"
    return p


def bullet(container, text):
    p = container.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Inches(0.14); pf.first_line_indent = Inches(-0.14); pf.space_after = Pt(2); pf.line_spacing = 1.05
    r = p.add_run("■  "); r.font.size = Pt(6.5); r.font.color.rgb = RGBColor.from_string(ORANGE)
    r = p.add_run(text); r.font.size = Pt(9.5); r.font.name = "Arial"; r.font.color.rgb = RGBColor.from_string(GREY)


def build_docx(path):
    doc = Document(LH)
    body = doc.element.body
    for el in list(body):
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    for s in doc.sections:     # reference_letterhead_margins: logo on page 1, clear the banners
        s.top_margin = Inches(1.7); s.bottom_margin = Inches(1.5)
        s.left_margin = Inches(1.0); s.right_margin = Inches(0.75)
        s.different_first_page_header_footer = False
        sp = s._sectPr
        for ref in list(sp.findall(qn("w:headerReference"))) + list(sp.findall(qn("w:footerReference"))):
            if ref.get(qn("w:type")) == "first":
                sp.remove(ref)
        for tp in list(sp.findall(qn("w:titlePg"))):
            sp.remove(tp)
    para(doc, TITLE, size=20, bold=True, color="111111", after=1)
    para(doc, SUB, size=10.5, color=ORANGE, bold=True, after=5)
    para(doc, LEAD, size=9.5, after=6)
    t = doc.add_table(rows=2, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    for i, (head, items) in enumerate(SECTIONS):
        c = t.cell(i // 2, i % 2); c.width = Inches(3.35)
        c.paragraphs[0].text = ""
        r = c.paragraphs[0].add_run(head.upper()); r.bold = True; r.font.size = Pt(10); r.font.name = "Arial"
        r.font.color.rgb = RGBColor.from_string(ORANGE)
        c.paragraphs[0].paragraph_format.space_after = Pt(3)
        for it in items:
            bullet(c, it)
    for row in t.rows:
        for c in row.cells:
            c.width = Inches(3.35)
    band = doc.add_table(rows=1, cols=1).cell(0, 0)
    shade(band, "1A1A1A")
    band.paragraphs[0].text = ""
    r = band.paragraphs[0].add_run(PRICE); r.font.size = Pt(9.5); r.bold = True; r.font.name = "Arial"; r.font.color.rgb = RGBColor.from_string("FFFFFF")
    band.paragraphs[0].paragraph_format.space_before = Pt(3); band.paragraphs[0].paragraph_format.space_after = Pt(2)
    p = band.add_paragraph(); r = p.add_run(NEXT); r.font.size = Pt(9.5); r.font.name = "Arial"; r.font.color.rgb = RGBColor.from_string(ORANGE); r.bold = True
    p.paragraph_format.space_after = Pt(3)
    para(doc, FINE, size=7.5, color="777777", before=5, italic=True)
    doc.core_properties.title = TITLE; doc.core_properties.author = "Exos Aerospace"
    doc.save(path)


# ── PDF twin (HTML → Chrome), same banners + margins as the Word letterhead ─────────────────
def build_pdf(path, tmp):
    with zipfile.ZipFile(LH) as z:
        for n in ("word/media/image1.png", "word/media/image2.png"):
            open(os.path.join(tmp, os.path.basename(n)), "wb").write(z.read(n))
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    cells = "".join(f'<div class="cell"><h3>{esc(h)}</h3><ul>{"".join(f"<li>{esc(i)}</li>" for i in items)}</ul></div>'
                    for h, items in SECTIONS)
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: 8.5in 11in; margin: 0 }}
body {{ margin:0; font-family: Arial, Helvetica, sans-serif; color:#{GREY}; }}
.page {{ position:relative; width:8.5in; height:11in; overflow:hidden; }}
.hdr {{ position:absolute; top:0; left:0.01in; width:6.5in; height:1.34in; }}
.ftr {{ position:absolute; bottom:0.05in; left:1.39in; width:7.1in; height:1.16in; }}
.body {{ position:absolute; top:1.7in; left:1.0in; right:0.75in; bottom:1.5in; }}
h1 {{ font-size:20pt; margin:0 0 1pt; color:#111; }}
.sub {{ font-size:10.5pt; color:#{ORANGE}; font-weight:bold; margin:0 0 5pt; }}
p {{ font-size:9.5pt; line-height:1.3; margin:0 0 6pt; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; column-gap:0.2in; row-gap:4pt; }}
h3 {{ font-size:10pt; color:#{ORANGE}; text-transform:uppercase; margin:0 0 3pt; }}
ul {{ list-style:none; padding:0; margin:0 0 4pt; }}
li {{ font-size:9.5pt; line-height:1.3; padding-left:0.14in; text-indent:-0.14in; margin-bottom:2pt; }}
li:before {{ content:"■"; color:#{ORANGE}; font-size:6.5pt; padding-right:0.07in; vertical-align:1px; }}
.band {{ background:#1A1A1A; padding:5pt 8pt; margin-top:4pt; }}
.band .p {{ color:#fff; font-weight:bold; font-size:9.5pt; margin:0 0 3pt; }}
.band .n {{ color:#{ORANGE}; font-weight:bold; font-size:9.5pt; margin:0; line-height:1.3; }}
.fine {{ font-size:7.5pt; color:#777; font-style:italic; margin-top:5pt; }}
</style></head><body><div class="page">
<img class="hdr" src="image1.png"><img class="ftr" src="image2.png">
<div class="body"><h1>{esc(TITLE)}</h1><div class="sub">{esc(SUB)}</div><p>{esc(LEAD)}</p>
<div class="grid">{cells}</div>
<div class="band"><div class="p">{esc(PRICE)}</div><div class="n">{esc(NEXT)}</div></div>
<div class="fine">{esc(FINE)}</div></div></div></body></html>"""
    hp = os.path.join(tmp, "onepager.html")
    open(hp, "w").write(html)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--print-to-pdf={path}", "--no-pdf-header-footer",
                    "file://" + hp], check=True, capture_output=True, timeout=90)
    return hp


if __name__ == "__main__":
    tmp = tempfile.mkdtemp(prefix="flymt-")
    build_docx(OUT + ".docx")
    build_pdf(OUT + ".pdf", tmp)
    shutil.copy(os.path.join(tmp, "onepager.html"), "/tmp/flymt_onepager.html")
    print("wrote", OUT + ".docx", OUT + ".pdf")
