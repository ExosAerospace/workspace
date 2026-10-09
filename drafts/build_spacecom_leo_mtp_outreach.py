#!/usr/bin/env python3
"""Build the SpaceCom 'LEO and Beyond' MTP outreach pack (.docx) for Jon.
Source: SpaceCom Second Stage Sector Spotlight 'LEO and Beyond: In-Space Infrastructure' (Oct 2026).
Each draft = recipient on top line, Subject, letter (Jon's ready-to-send format). Outlook appends signature."""
import json, sys
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = sys.argv[1]
DATA = json.load(open(sys.argv[2]))

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)

h = doc.add_heading("MTP Outreach Pack — SpaceCom “LEO and Beyond” Sector Spotlight", 0)
doc.add_paragraph("Prepared for John Quinn · 2026-10-09 · DRAFTS — nothing has been sent")
doc.add_paragraph(DATA["intro"])

doc.add_heading("Target screen (MTP: Make Every Space Vehicle Reusable)", 1)
t = doc.add_table(rows=1, cols=5); t.style = "Light Grid Accent 1"
for i, c in enumerate(["#", "Company / contact", "MTP fit", "Relationship", "Send path"]):
    t.rows[0].cells[i].text = c
for i, d in enumerate(DATA["drafts"], 1):
    r = t.add_row().cells
    r[0].text = str(i); r[1].text = f'{d["company"]} — {d["person"]}'
    r[2].text = d["fit"]; r[3].text = d["rel"]; r[4].text = d["path"]

doc.add_heading("Screened out", 2)
for x in DATA["excluded"]:
    doc.add_paragraph(x, style="List Bullet")

doc.add_heading("Claims used in the drafts, with sources", 2)
for x in DATA["claims"]:
    doc.add_paragraph(x, style="List Bullet")

for i, d in enumerate(DATA["drafts"], 1):
    doc.add_page_break()
    doc.add_heading(f'{i}. {d["company"]} — {d["person"]}', 1)
    p = doc.add_paragraph(); run = p.add_run("Note for John: " + d["note"]); run.italic = True
    run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    doc.add_paragraph(d["to"])
    doc.add_paragraph("Subject: " + d["subject"])
    for para in d["body"].strip().split("\n\n"):
        doc.add_paragraph(para.strip())
doc.save(OUT)
print("wrote", OUT)
