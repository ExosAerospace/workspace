---
name: "exos-letterhead-proposal-doc"
description: "Build Exos external/gov proposals on PRIMARY letterhead as editable Word + letterhead-matched PDF, with integrity guardrails."
---

# Exos Letterhead Proposal / Document Builder

Build any Exos external-facing document (gov proposal, teaming brief, formal letter) as BOTH an editable Word file on the PRIMARY letterhead AND a letterhead-matched PDF twin. Deliver both as attachments for in-chat review before anything is sent.

## When to use
Any request to "prepare/draft/build a proposal, brief, white paper, or formal letter" that Exos will send externally or to the government.

## Toolchain facts (learned, reliable)
- **Letterhead:** `assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx` (PRIMARY; dark text on white).
- **Editable Word:** run `PYTHONNOUSERSITE=1 python3.12` with `python-docx`. (The `PYTHONNOUSERSITE=1` flag is REQUIRED — the user-site `lxml` is broken and throws `getargspec/getfullargspec` ImportError otherwise.) Open the letterhead with `Document(LH)` and append content so the header/footer are preserved.
- **The letterhead template has NO built-in `Table Grid` style** — `table.style="Table Grid"` raises KeyError. Add borders manually via XML (`w:tblBorders`).
- **Headings:** navy `RGBColor(0x0A,0x3D,0x7C)`, body dark `0x1A1A1A`, Calibri, dark-on-white.
- **PDF twin:** DO NOT use LibreOffice `soffice --convert-to pdf` — it hangs on this host. Instead:
  1. Extract the letterhead banners: `unzip -o letterhead.docx "word/media/*"` → `image1.png` (header, ~2625x542) and `image2.png` (footer, ~2625x431).
  2. Build the PDF with **reportlab under plain `python3`** (NOT `PYTHONNOUSERSITE=1` — reportlab lives in user-site). Draw the banners full-width via an `onPage` callback (header top, footer bottom); set `topMargin~1.7in`, `bottomMargin~1.35in` so text clears the banners.
- **Verify before delivering:** `pdfinfo` for page count; `pdftotext | grep` for key phrases (contract numbers, dollar figures, the guardrail sentences) to confirm no corruption/overlap. Avoid trying to view images (context image limits).
- **Deliver with `MEDIA:<abs path>` lines** (Jon can't open file paths) — never just cite a path.

## Integrity guardrails to bake into EVERY Exos external doc
- Never overstate: state plainly what Exos has NOT done or does NOT own (e.g., "Exos has not performed direct RDRE development"; "Exos does not own the GTL technology"). Frame undecided paths as trade-study down-selects, not owned/decided.
- Flight heritage reframe: flying since 2018 (SARGE/Armadillo lineage); BLK3 FAA-licensed (Mar 2026) but NOT flown commercially — "preparing for flight," never "first commercial flight."
- Standing line: "one of only three FAA-licensed reusable rocket launch providers in the United States."
- Verified heritage only: Scorpius Type 5 flew as fuel + LOX tanks on Intuitive Machines Odysseus (IM-1) and Athena (IM-2). Don't claim cryo transfer was demonstrated.
- Hedge unprovable absolutes ("none we're aware of", not "world's only").
- Mark own trade-secret material "Proprietary — Unclassified" (don't self-designate CUI).
- Full legal address on formal docs: 299 FM 1903, Greenville, TX 75402. POC John Quinn, Cofounder & CEO, jquinn@exosaero.com.
- Dark text on white; build ON the PRIMARY letterhead.

## Procedure
1. Draft the content with the guardrails above; get section structure right for the audience (exec summary, basis/eligibility, approach, plan, cost table, risks, management).
2. Write a `scripts/build_*_proposal.py` (python-docx on the letterhead) → editable Word in `drafts/`.
3. Write a `scripts/build_*_pdf.py` (reportlab + extracted banners) → letterhead-matched PDF in `drafts/`.
4. Verify page count + key-phrase integrity via `pdfinfo`/`pdftotext`.
5. Deliver BOTH via `MEDIA:` lines with a tight summary; state it's a review copy — nothing sends until reviewed (and, for gov, until Jon + the contracting officer walk it).

## Reference implementations
- `scripts/build_rdre_phase3_proposal.py` (Word) and `scripts/build_rdre_phase3_pdf.py` (PDF) — the RDRE Phase III proposal.
