#!/usr/bin/env python3
"""build_procedure.py — HARD-WIRED procedure generator for Exos.

Every new procedure MUST be created through this script so it is always:
  1. Built on the Exos-US house Procedure Template format (SAFETY/ENVIRONMENTAL,
     OBJECTIVE, OVERVIEW, Tasks w/ verify-checkboxes, Exos WMS (Mission Control) completion,
     controlled footer with doc no / date / status).
  2. Added as a row to the Procedures Master List
     (process-library/01-quality-as9100/Exos_Aerospace_Procedures_Master_List.xlsx).
  3. Registered in the Mission Control Process Library (process-register.json + the
     embedded catalogue in process-library.html) so employees can access it.

Usage:  python3 scripts/build_procedure.py <spec.json>
Spec (JSON): { title, doc_no, area, area_id, owner, objective, overview,
               tasks:[{name, steps:[...]}], reference_docs, status, intl_release }
"""
import json, os, sys, subprocess, datetime

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PL = os.path.join(WS, "process-library")
MASTER = os.path.join(PL, "01-quality-as9100", "Exos_Aerospace_Procedures_Master_List.xlsx")
REG = os.path.join(WS, "mission-control", "data", "process-register.json")
REG_HTML = os.path.join(WS, "mission-control", "process-library.html")


def esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# Exos house palette (matched to the Series A deck / brand): deep navy + a red rule accent.
NAVY = RGBColor(0x0b, 0x2a, 0x4a)
DARK = RGBColor(0x1c, 0x1c, 0x1c)
GREY = RGBColor(0x60, 0x6a, 0x78)
RED  = RGBColor(0xc8, 0x10, 0x2e)
BODY_FONT = "Calibri"
HEAD_IMG = os.path.join(WS, "mission-control", "brand-assets", "exos-letterhead-header.png")
FOOT_IMG = os.path.join(WS, "mission-control", "brand-assets", "exos-letterhead-footer.png")


def _run(p, text, size=11, bold=False, italic=False, color=DARK, font=BODY_FONT, caps=False):
    r = p.add_run(text.upper() if caps else text)
    r.font.name = font; r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = color
    return r


def _bottom_rule(p, color="c8102e", size=6):
    """Thin colored rule under a heading paragraph — the branded section divider."""
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr"); b = OxmlElement("w:bottom")
    b.set(qn("w:val"), "single"); b.set(qn("w:sz"), str(size))
    b.set(qn("w:space"), "3"); b.set(qn("w:color"), color)
    pbdr.append(b); pPr.append(pbdr)


def _page_field(p):
    """Insert a live PAGE number field."""
    for txt, kind in [("begin", "w:fldCharType"), ("PAGE", None), ("end", "w:fldCharType")]:
        if kind:
            fld = OxmlElement("w:fldChar"); fld.set(qn(kind), txt)
            r = p.add_run(); r._r.append(fld)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = " PAGE "
            r = p.add_run(); r.font.size = Pt(8); r.font.color.rgb = GREY; r.font.name = BODY_FONT; r._r.append(it)


def build_docx(spec, out_docx):
    """Render the procedure on the Exos house template with letterhead branding and clean,
    consistent typography (python-docx)."""
    today = spec.get("issued", datetime.date.today().strftime("%m/%d/%Y"))
    doc = Document()

    # Base style + page geometry
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT; normal.font.size = Pt(10.5); normal.font.color.rgb = DARK
    normal.paragraph_format.space_after = Pt(6); normal.paragraph_format.line_spacing = 1.08
    sec = doc.sections[0]
    sec.top_margin = Inches(0.5); sec.bottom_margin = Inches(0.55)
    sec.left_margin = Inches(0.9); sec.right_margin = Inches(0.9)
    sec.header_distance = Inches(0.3); sec.footer_distance = Inches(0.25)

    # ── Letterhead HEADER (branding) ──
    hp = sec.header.paragraphs[0]; hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hp.paragraph_format.space_after = Pt(2)
    if os.path.exists(HEAD_IMG):
        hp.add_run().add_picture(HEAD_IMG, width=Inches(6.7))

    # ── Letterhead FOOTER (branding) + controlled-doc line + page number ──
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.space_after = Pt(0)
    ctl = (f"{spec.get('doc_no')} Rev {spec.get('rev','0')}  ·  Controlled copy — valid for today's date only  "
           f"·  Process & Procedure Control per EXOS-US-QMS-001  ·  Page ")
    _run(fp, ctl, size=8, color=GREY)
    _page_field(fp)
    if os.path.exists(FOOT_IMG):
        fimg = sec.footer.add_paragraph(); fimg.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fimg.paragraph_format.space_before = Pt(3); fimg.paragraph_format.space_after = Pt(0)
        fimg.add_run().add_picture(FOOT_IMG, width=Inches(6.7))

    # ── Document-control block (top-right) ──
    for i, (lbl, val) in enumerate([("DOC NO", spec.get("doc_no", "")),
                                     ("DATE", today),
                                     ("STATUS", str(spec.get("status", "PENDING APPROVAL")).upper())]):
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
        _run(p, f"{lbl}:  ", size=9, bold=True, color=NAVY)
        _run(p, str(val), size=9, color=DARK)

    # ── Title ──
    t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.paragraph_format.space_before = Pt(6); t.paragraph_format.space_after = Pt(2)
    _run(t, spec.get("title", ""), size=17, bold=True, color=NAVY)
    _bottom_rule(t, color="0b2a4a", size=8)

    # ── Sign-off line ──
    so = doc.add_paragraph(); so.paragraph_format.space_before = Pt(8); so.paragraph_format.space_after = Pt(10)
    _run(so, "Equipment / System No ", size=10, color=DARK)
    _run(so, "___________________", size=10, color=GREY)
    _run(so, "     Date ", size=10, color=DARK); _run(so, "_____________", size=10, color=GREY)
    _run(so, "     Performed by ", size=10, color=DARK); _run(so, "______________________________", size=10, color=GREY)

    def section(label):
        p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        _run(p, label, size=12, bold=True, color=NAVY, caps=True)
        _bottom_rule(p, color="c8102e", size=6)

    def body(text):
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(6)
        _run(p, text, size=10.5, color=DARK)

    def step(text):
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_after = Pt(3)
        _run(p, "☐  ", size=12, color=NAVY)   # ☐ ballot box
        _run(p, text, size=10.5, color=DARK)

    section("Safety / Environmental")
    body("Verify that all personnel who will be involved with this activity are familiar with this procedure, "
         "any risks or hazards that may be encountered, possess the required safety equipment, and are familiar "
         "with the site safety and environmental policies.")

    section("Objective")
    body("The purpose of this procedure is to " + str(spec.get("objective", "")).strip())

    section("Overview")
    body(str(spec.get("overview",
        "It is necessary for the personnel involved in executing this procedure to possess a thorough working "
        "knowledge of the systems under their jurisdiction. Good communication between the personnel involved "
        "minimizes the potential for unforeseen problems. Any change in status or condition must be recognized, "
        "verified, and monitored by the Procedure lead or their direct report, and corrective action taken to "
        "resolve any abnormal conditions.")))

    section("Procedure")
    for t in spec.get("tasks", []):
        tp = doc.add_paragraph(); tp.paragraph_format.space_before = Pt(7); tp.paragraph_format.space_after = Pt(3)
        tp.paragraph_format.keep_with_next = True
        _run(tp, str(t.get("name", "")), size=11, bold=True, color=NAVY)
        for s in t.get("steps", []):
            step(s)

    cp = doc.add_paragraph(); cp.paragraph_format.space_before = Pt(7); cp.paragraph_format.space_after = Pt(3)
    _run(cp, "Completion", size=11, bold=True, color=NAVY)
    step("Record completion of the activity in the Exos Work Management System (Mission Control).")

    # Owner / reference footer line (in-body, small)
    meta = doc.add_paragraph(); meta.paragraph_format.space_before = Pt(12)
    _run(meta, f"Owner: {spec.get('owner','')}   ·   Reference documents: {spec.get('reference_docs','NA')}",
         size=8.5, italic=True, color=GREY)

    doc.save(out_docx)


def update_master(spec):
    import openpyxl
    wb = openpyxl.load_workbook(MASTER)
    ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb.active
    # avoid dup by procedure number
    for r in ws.iter_rows(min_row=3):
        if r[1].value and str(r[1].value).strip() == str(spec.get("doc_no")).strip():
            ws.delete_rows(r[0].row, 1); break
    ws.append([spec.get("title"), spec.get("doc_no"), spec.get("rev", "0"),
               spec.get("reference_docs", "NA"),
               spec.get("issued", datetime.date.today().strftime("%b-%d-%Y")),
               spec.get("intl_release", "Yes"), spec.get("charters", ""),
               spec.get("status", "Approved")])
    wb.save(MASTER)


def register(spec, rel_docx):
    entry = {"area": spec.get("area"), "area_id": spec.get("area_id"),
             "procedure": spec.get("title"), "doc_no": spec.get("doc_no"),
             "rev": spec.get("rev", "0"), "status": spec.get("status", "Approved"),
             "intl_release": spec.get("intl_release", "Yes"), "ack_required": bool(spec.get("ack_required", False)),
             "owner": spec.get("owner", "Exo (Lizi advising)"), "remarks": spec.get("remarks", ""),
             "files": [rel_docx], "file_count": 1}
    # optional call-to-action button on the Process Library row (e.g. self-service page)
    if spec.get("apply_link"):
        entry["apply_link"] = spec["apply_link"]
        entry["apply_label"] = spec.get("apply_label", "Open →")

    def add(d):
        d["meta"]["updated"] = datetime.date.today().isoformat()
        if entry["area"] not in d["meta"]["areas"]:
            d["meta"]["areas"].append(entry["area"])
        d["register"] = [r for r in d["register"] if r.get("doc_no") != entry["doc_no"]]
        d["register"].append(entry)
    d = json.load(open(REG)); add(d); json.dump(d, open(REG, "w"), ensure_ascii=False, indent=1)
    html = open(REG_HTML, encoding="utf-8").read()
    sm = '<script id="data" type="application/json">'
    i = html.index(sm) + len(sm); j = html.index("</script>", i)
    blob = json.loads(html[i:j]); add(blob)
    open(REG_HTML, "w", encoding="utf-8").write(html[:i] + "\n" + json.dumps(blob, ensure_ascii=False, indent=1) + "\n" + html[j:])


def main():
    if len(sys.argv) < 2:
        print("usage: build_procedure.py <spec.json>"); sys.exit(1)
    spec = json.load(open(sys.argv[1]))
    for req in ("title", "doc_no", "area", "area_id"):
        if not spec.get(req): print(f"spec missing '{req}'"); sys.exit(1)
    folder = os.path.join(PL, spec["area_id"]); os.makedirs(folder, exist_ok=True)
    fname = spec["doc_no"].replace(" ", "_") + "_" + spec["title"].replace(" ", "_").replace("/", "-") + ".docx"
    out = os.path.join(folder, fname)
    build_docx(spec, out)
    update_master(spec)
    register(spec, f"{spec['area_id']}/{fname}")
    print(f"OK: built {fname}\n  - house template format (docx)\n  - added to Procedures Master List\n  - registered in Process Library ({spec['area']})")


if __name__ == "__main__":
    main()
