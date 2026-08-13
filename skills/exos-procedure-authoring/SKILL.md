---
name: "exos-procedure-authoring"
description: "Author any Exos procedure on the house template + Master List + Process Library via build_procedure.py"
---

# Exos Procedure Authoring (controlled)

Use this whenever anyone asks to create, add, or build a **procedure** for Exos (including procedures an employee requests as part of their work process, e.g. the Expense Report Submission Procedure).

**Never hand-write a procedure as freeform markdown.** Procedures are controlled documents and must be produced through the hard-wired generator so they are always (1) on the Exos-US house template, (2) added to the Procedures Master List, and (3) registered in the Mission Control Process Library.

## Steps

1. **Write a spec JSON** and save it to `process-library/_specs/<DOCNO>_<slug>.json`:
   ```json
   {
     "title": "…", "doc_no": "EXOS-<AREA>-00X-0", "area": "Administrative",
     "area_id": "11-administrative", "owner": "<role> / Exo", "rev": "0",
     "status": "Approved", "intl_release": "Yes", "reference_docs": "…",
     "remarks": "…", "objective": "<completes: 'The purpose of this procedure is to …'>",
     "overview": "…",
     "tasks": [ {"name": "Task 1 - …", "steps": ["…","…"]} ]
   }
   ```
   - `doc_no`: `EXOS-<AREA>-<seq>-<rev>` (e.g. `EXOS-ADM-002-0`). Areas map to the numbered process-library folders (11-administrative, 05-human-resources, etc.).
   - Tasks render as `Task N` headings with `_____ ` verify-checkbox steps, matching the house format. A Completion block (record in NetSuite + Exos Work Management System) is added automatically.

2. **Run the generator:**
   ```
   PYTHONPATH=/Users/Shared/exos-archive/pylibs python3 scripts/build_procedure.py process-library/_specs/<file>.json
   ```
   It: renders the `.docx` on the house template (SAFETY/ENVIRONMENTAL → OBJECTIVE → OVERVIEW → PROCEDURE tasks → Completion → controlled footer with doc-no/date/status) via `textutil` html→docx; appends the row to `process-library/01-quality-as9100/Exos_Aerospace_Procedures_Master_List.xlsx`; and registers it in `mission-control/data/process-register.json` + the embedded catalogue in `mission-control/process-library.html`.

3. **Verify:** `textutil -convert txt -stdout <docx>` shows the house sections; the Master List has the row; the Process Library lists it under its area. The doc is downloadable at `/process-library/<area_id>/<file>.docx` (session-gated).

4. **Commit** the generated `.docx`, the spec, the Master List xlsx, and the two registry files.

## References
- Template source: `process-library/01-quality-as9100/Exos-US-Procedure_Template.doc`
- Master List: `process-library/01-quality-as9100/Exos_Aerospace_Procedures_Master_List.xlsx`
- Generator: `scripts/build_procedure.py`
- Do NOT freeform. If the template or Master List format changes, update `build_procedure.py`, not individual docs.
