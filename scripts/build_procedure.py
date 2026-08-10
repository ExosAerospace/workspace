#!/usr/bin/env python3
"""build_procedure.py — HARD-WIRED procedure generator for Exos.

Every new procedure MUST be created through this script so it is always:
  1. Built on the Exos-US house Procedure Template format (SAFETY/ENVIRONMENTAL,
     OBJECTIVE, OVERVIEW, Tasks w/ verify-checkboxes, NetSuite + Exos WMS completion,
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


def build_docx(spec, out_docx):
    """Render the procedure in the house template format via HTML -> docx (textutil)."""
    today = spec.get("issued", datetime.date.today().strftime("%m/%d/%Y"))
    tasks_html = ""
    for t in spec.get("tasks", []):
        tasks_html += f"<h3>{esc(t.get('name'))}</h3>"
        for s in t.get("steps", []):
            tasks_html += f"<p style='margin:2px 0'>_____ {esc(s)}</p>"
    html = f"""<!doctype html><html><head><meta charset="utf-8"></head><body style="font-family:Arial,sans-serif;font-size:11pt;color:#000">
<table width="100%"><tr>
<td style="font-weight:bold">EXOS AEROSPACE SYSTEMS &amp; TECHNOLOGIES, INC.</td>
<td style="text-align:right">{esc(spec.get('doc_no'))}<br>DATE: {esc(today)}<br>STATUS: {esc(spec.get('status','PENDING APPROVAL')).upper()}</td>
</tr></table>
<h1 style="font-size:15pt;text-align:center">{esc(spec.get('title'))}</h1>
<p>EQUIPMENT / SYSTEM NO ___________ &nbsp; Date _________ &nbsp; Performed by _______________________</p>
<h2>SAFETY / ENVIRONMENTAL</h2>
<p>Verify that all personnel that will be involved with this activity are familiar with this procedure, any risks or hazards that may be encountered, possess the required safety equipment, and are familiar with the site safety and environmental policies.</p>
<h2>OBJECTIVE</h2>
<p>The purpose of this procedure is to {esc(spec.get('objective',''))}</p>
<h2>OVERVIEW</h2>
<p>{esc(spec.get('overview','It is necessary for the personnel involved in executing this procedure to possess a thorough working knowledge of the systems under their jurisdiction. Good communication between the personnel involved minimizes the potential for unforeseen problems. Any change in status or condition must be recognized, verified, and monitored by the Procedure lead or their direct report, and corrective action taken to resolve any abnormal conditions.'))}</p>
<h2>PROCEDURE</h2>
{tasks_html}
<h3>Completion</h3>
<p style="margin:2px 0">_____ Record completion of the activity in NetSuite.</p>
<p style="margin:2px 0">_____ Complete the job in the Exos Work Management System (Mission Control).</p>
<hr>
<p style="font-size:8pt;color:#555">This is a copy of the procedure. Valid for today's date only. Owner: {esc(spec.get('owner',''))} · Reference documents: {esc(spec.get('reference_docs','NA'))} · {esc(spec.get('doc_no'))} Rev {esc(spec.get('rev','0'))} · Process &amp; Procedure Control per EXOS-US-QMS-001.</p>
</body></html>"""
    tmp = out_docx + ".html"
    open(tmp, "w", encoding="utf-8").write(html)
    subprocess.run(["textutil", "-convert", "docx", "-output", out_docx, tmp], check=True)
    os.remove(tmp)


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
