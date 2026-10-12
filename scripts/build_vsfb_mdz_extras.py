#!/usr/bin/env python3
"""Compliance matrix .xlsx + Submission checklist .docx for VSFB MDZ. Run with PYTHONNOUSERSITE=1 python3.12."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vsfb_mdz_content as K
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
D = "drafts/VSFB_MDZ/"
wb = Workbook(); ws = wb.active; ws.title = "Compliance Matrix"
ws.append(["Exos VSFB MDZ Whitepaper — Compliance Matrix (VSFBMDZCall) — " + K.MARK]); ws["A1"].font = Font(bold=True, size=12, color="0A3D7C")
ws.append(["Call reference", "Requirement", "Response section", "PDF page", "Status", "Open item"])
openmap = {"1.2": "Counsel: confirm wording; attach TX SOS cert + officer statement", "1.5": "Confirm Lizi title", "2.1": "Kyle: financing wording check",
           "3.1": "Russell/ENG: crane, height, span, bays", "5.1": "", "5.2": "Phil/Neil: personnel counts",
           "5.3": "ENG: utility loads", "6.2": "ENG: commodity quantities", "7.2": "Counsel: two-instrument award section", "7.1": "Phil/Neil: durations; Q2 2027 realism"}
thin = Side(style="thin", color="9AA5B1")
for a, b, c in K.MATRIX:
    ws.append([a, b, c, str(K._PM.get(c, "—")), "Addressed — placeholder open" if c in openmap else "Addressed", openmap.get(c, "")])
for cell in ws[2]: cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="0A3D7C")
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical="top"); c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
    if row[5].value and row[0].row > 2:
        for c in row: c.fill = PatternFill("solid", fgColor="FFF4CC")
for col, w in zip("ABCDEF", [26, 60, 20, 12, 26, 34]): ws.column_dimensions[col].width = w
ws.freeze_panes = "A3"
wb.save(D + "Exos_VSFB_MDZ_Compliance_Matrix_%s%s.xlsx" % (K.DATE, K.VER))

# ---------------- Checklist docx
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
doc = Document("assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx")
for el in list(doc.element.body):
    if el.tag.endswith('}p') or el.tag.endswith('}tbl'): doc.element.body.remove(el)
NAVY = RGBColor(0x0A,0x3D,0x7C); DARK = RGBColor(0x1A,0x1A,0x1A); RED = RGBColor(0x9A,0x1B,0x1B)
def P(t, size=10.5, color=DARK, bold=False, after=4, indent=None):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(after)
    if indent: p.paragraph_format.left_indent = Inches(indent)
    for part in re.split(r"(\*\*.+?\*\*)", t):
        if not part: continue
        b = part.startswith("**"); r = p.add_run(part[2:-2] if b else part)
        r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold or b; r.font.name = "Calibri"
    return p
P("VSFB MDZ Whitepaper — Submission Checklist", 16, NAVY, True, 2)
P(K.MARK + " · prepared " + K.DATE + " · nothing has been sent or submitted", 9, RED, True, 10)
P("Key facts", 12.5, NAVY, True)
for t in ["**Notice:** VSFB Call for Whitepapers for Mission Development Zone (MDZ) Outgrant — **VSFBMDZCall** (SAM.gov notice 053436c19dbd4979a19587b059158969; Special Notice; SLD 30/XPR).",
          "**Deadline:** must be **received by Friday 16 October 2026, 4:00 PM PT** (SAM.gov response date, amended from 2 Oct 2026). Target internal sign-off by **Wed 14 Oct** so the DoD SAFE link request has time to come back.",
          "**POC:** Ainsley Allen — 232909MissionDevelopmentZoneMDZFacilityConstruct@groups.af.mil (no phone listed).",
          "**Format:** MS Word or PDF, compatible with DoD IT systems; **max 30 pages** (current draft: %s). DoD SAFE file limit 8 GB." % K._PM.get("Whole document", "—"),
          "**Questions deadline:** none stated in the call. Questions and site-viewing requests go to the POC e-mail; a site visit does **not** extend the deadline (call §1.5).",
          "Not FAR-governed; not an RFI/RFP/RFQ; no Government funding for responses; USSF may use submitted content for planning (call §2.1–2.3)."]:
    P("•  " + t, indent=0.2)
P("DoD SAFE submission steps (call §4.3)", 12.5, NAVY, True)
P("**STATUS: DoD SAFE link requested 2026-10-11 16:15 CDT from jquinnexo@pm.me, reply-to and link to jquinn@exosaero.com, cc lquinn@exosaero.com; confirm receipt by separate email after upload.**", 10.5, RED, after=6)
for i, t in enumerate([
  "Jon resolves every [JON DECISION] / [ENG REVIEW] item in the whitepaper and approves the final text (Exos internal review).",
  "Remove all DRAFT markings and yellow decision boxes; rebuild Word + PDF (scripts/build_vsfb_mdz_all.py); confirm ≤30 pages and letterhead on every page.",
  "E-mail 232909MissionDevelopmentZoneMDZFacilityConstruct@groups.af.mil from jquinn@exosaero.com requesting a DoD SAFE drop-off link for the VSFBMDZCall whitepaper (subject: “VSFBMDZCall — DoD SAFE link request — Exos Aerospace”).",
  "Open the link at https://safe.apps.mil (it expires; use it promptly). Enter sender name and e-mail; upload the final PDF (and Word version if desired). Add a short description: “Exos Aerospace whitepaper — VSFBMDZCall”.",
  "Note: DoD SAFE e-mails the recipient automatically; separately **send a confirmation e-mail** to the POC listing the file names and asking for receipt confirmation (call §4.3 requires confirmation via a separate e-mail).",
  "Save the DoD SAFE confirmation, the link-request e-mail and the receipt confirmation to the opportunity record in Mission Control.",
  "Optional: request an MDZ property viewing (call §1.5) in the same e-mail thread."], 1):
    P("%d.  %s" % (i, t), indent=0.2)
P("File naming (final)", 12.5, NAVY, True)
for t in ["Exos_Aerospace_VSFBMDZCall_Whitepaper_2026-10-16.pdf  (primary submission)",
          "Exos_Aerospace_VSFBMDZCall_Whitepaper_2026-10-16.docx  (optional editable copy)",
          "Optional attachments if Jon approves: Exos_TX_SOS_Certificate_of_Fact.pdf; Exos_US_Ownership_Certification.pdf"]:
    P("•  " + t, indent=0.2)
P("Open Jon decisions (recommendation in bold)", 12.5, NAVY, True)
decs = [
 ("DECIDED 10/11 15:50", "Proceed; primary use = Exos launch-support land lease (launch planned, as early as Q2 2027, not yet sited); MCMS-exo3 = added value."),
 ("DECIDED 10/11 16:11", "U.S. ownership (>50% U.S. nationals) stated; TX SOS cert + officer statement to attach. No propellant/ordnance at MDZ. Direct-award request."),
 ("DECIDED 10/11 16:25", "BLK3 design work = AFWERX SBIR Phase II FA8649-21-P-0838 (primary basis); FA9300-25-C-6022 HVRR supporting."),
 ("DECIDED 10/11 16:25", "Acreage = Plots 40–43 (≈20 ac) as the starter footprint; Spaceport America as flight-ops reference; MCMS-exo3 range/FTS integration as the SLD 30 contract deliverable."),
 ("DECIDED 10/11 16:25", "Partners: option (a) — all partner references removed from the whitepaper."),
 ("OPEN — Lizi Quinn title", "Not on file in memory; supply title for §1.5."),
 ("OPEN — Counsel review", "Ownership wording (§1.2) and the direct-award section (§7.2)."),
 ("OPEN — Engineering numbers", "Crane, heights/span, bays, utilities, personnel, commodity quantities — engineer-sourced ranges or “TBD in final design.”"),
 ("OPEN — SARGE 2018–19 source", "Pre-2023 source for SARGE payload heritage [14]: keep, or drop the clause under the 2023+ rule."),
 ("DECIDED 10/12 17:45 (D-7282063)", "As recommended, with overrides: marking = Exos Proprietary (not CUI); locations not limited to Spaceport America + VSFB expansion under consideration; award = outgrant + separate SBIR Phase III; throughput scaled to manifest / bay-count range; financing = operating capital and/or build-to-suit/ground lease, no figures; Gov office space + priority scheduling + limited Phase 0 demo — no-cost language removed."),
]
t = doc.add_table(rows=1, cols=3)
from docx.oxml.ns import qn; from docx.oxml import OxmlElement
b = OxmlElement('w:tblBorders')
for e in ('top','left','bottom','right','insideH','insideV'):
    x = OxmlElement('w:'+e); x.set(qn('w:val'),'single'); x.set(qn('w:sz'),'4'); x.set(qn('w:color'),'9AA5B1'); b.append(x)
t._tbl.tblPr.append(b)
for j, h in enumerate(["#", "Decision", "Recommendation / options"]):
    c = t.rows[0].cells[j]; r = c.paragraphs[0].add_run(h); r.font.bold = True; r.font.size = Pt(9.5)
for i, (a, rec) in enumerate(decs, 1):
    cells = t.add_row().cells
    for c, v in zip(cells, [str(i), a, rec]):
        for part in re.split(r"(\*\*.+?\*\*)", v):
            if not part: continue
            bb = part.startswith("**"); r = c.paragraphs[0].add_run(part[2:-2] if bb else part); r.font.size = Pt(9.5); r.font.bold = bb
for row in t.rows:
    for c, w in zip(row.cells, [0.35, 2.1, 4.05]): c.width = Inches(w)
P("", after=4)
P("Eligibility / risk notes", 12.5, NAVY, True)
for x in ["U.S. commercial provider: Jon confirmed the cap table (>50% U.S. nationals); attach TX SOS certificate + officer statement; Counsel confirms wording.",
          "Direct-award request: an outgrant is a real-property instrument, not a FAR procurement; the paper only asks USSF to consider it to the extent permitted — Counsel to confirm.",
          "License wording: Exos holds a current FAA launch license under 14 CFR Part 431 and is transitioning to Part 450; a VSFB launch would need its own licensing — the paper says “FAA launch license (14 CFR Part 431, transitioning to Part 450)”.",
          
          "Q2 2027 depends on separate launch-site assignment, FAA license modification and range approvals, plus outgrant execution within months — the draft conditions every reference to it.",
          "Scale realism: a 5-m-class high bay is a major capital project; kept as a Phase 2 option gated on financing and demand.",
          "Exos has not launched from Vandenberg and holds no VSFB launch site, license or manifest; the MDZ is not a launch complex — stated plainly.",
          "SARGE flight-heritage citation [14] relies on 2018–2019 primary sources (pre-2023); keep, or drop the clause if the 2023+ source rule is applied strictly."]:
    P("•  " + x, indent=0.2)
doc.save(D + "Exos_VSFB_MDZ_Submission_Checklist_%s%s.docx" % (K.DATE, K.VER)); print("ok")
