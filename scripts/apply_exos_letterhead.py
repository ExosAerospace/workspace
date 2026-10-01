#!/usr/bin/env python3
"""apply_exos_letterhead.py — put an EXISTING customer-facing .docx on Exos PRIMARY letterhead without
touching its body formatting.

Jon 2026-10-01: "All documents to customers should be on Exos letterhead - header and footer. Addendum
should be on their own page(s). The LSA needs to hold the formats of the original."

What it does (body XML is left as-is — fonts, numbering, tables, spacing all hold):
  1. Every section's default header/footer = the PRIMARY letterhead banners (copied from the template's
     own header/footer parts, images re-linked). First-page/even variants removed so EVERY page carries it.
  2. The document's existing footer text (e.g. "Launch and Payload Integration Service Agreement – Page N")
     is kept, left-aligned, above the footer banner.
  3. Top/bottom margins + header/footer distances set to the template's geometry so the body clears the
     banners. Left/right margins stay as the original.
  4. Every "ADDENDUM <X>" / "APPENDIX <X>" title starts on a new page (pageBreakBefore) unless it already
     follows a page break — so each addendum is on its own page(s), with no blank pages added.

Usage: apply_exos_letterhead.py IN.docx OUT.docx [--check]
  --check  verify only: exit 1 if any section lacks the letterhead or an addendum doesn't start a page.
"""
import copy, io, re, sys
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Emu

# NB: the template's real filename has a newline in it ("...Greenville TX\n address (PRIMARY).docx") — glob it.
TEMPLATE = next(iter(sorted(__import__("glob").glob("/Users/exomac/.openclaw/workspace/assets/EXOS Letterhead Greenville TX*(PRIMARY).docx"))), "")
R_EMBED = qn("r:embed")
ADDENDUM_RE = re.compile(r"^\s*(ADDENDUM|APPENDIX)\s+[A-Z0-9]+\b")
MARK = "exos-letterhead"  # docPr descr tag so --check can find our banners


def _template_parts():
    t = Document(TEMPLATE)
    s = t.sections[0]
    return s.header, s.footer, s


def _copy_story(src_story, dst_story, keep_paras=()):
    """Replace dst header/footer content with src's, re-linking images into dst's part."""
    dst = dst_story._element
    for child in list(dst):
        dst.remove(child)
    for p in keep_paras:
        dst.append(p)
    for el in src_story._element:
        new = copy.deepcopy(el)
        for blip in new.iter(qn("a:blip")):
            rid = blip.get(R_EMBED)
            blob = src_story.part.related_parts[rid].blob
            new_rid, _ = dst_story.part.get_or_add_image(io.BytesIO(blob))
            blip.set(R_EMBED, new_rid)
        for dp in new.iter(qn("wp:docPr")):
            dp.set("descr", MARK)
        dst.append(new)


def _starts_page(p):
    """True if paragraph p already begins a new page (pageBreakBefore, or preceded by a page break)."""
    if p.find(qn("w:pPr")) is not None and p.find(qn("w:pPr")).find(qn("w:pageBreakBefore")) is not None:
        return True
    prev = p.getprevious()
    while prev is not None and prev.tag in (qn("w:p"), qn("w:bookmarkStart"), qn("w:bookmarkEnd")):
        if prev.tag != qn("w:p"):
            prev = prev.getprevious(); continue
        if prev.find(qn("w:pPr")) is not None and prev.find(qn("w:pPr")).find(qn("w:sectPr")) is not None:
            return True  # section break (next page) ends the previous paragraph
        if any(b.get(qn("w:type")) == "page" for b in prev.iter(qn("w:br"))):
            return True
        if "".join(t.text or "" for t in prev.iter(qn("w:t"))).strip():
            return False
        prev = prev.getprevious()
    return prev is None  # first thing in the document


def _addendum_paras(doc):
    return [p for p in doc.paragraphs if ADDENDUM_RE.match(p.text) and p.text.strip().upper() == p.text.strip()]


def apply(inp, out):
    doc = Document(inp)
    th, tf, ts = _template_parts()
    for sec in doc.sections:
        sp = sec._sectPr
        # existing footer text (page label) — keep the paragraphs that carry text/fields
        # (w:t text only — a drawing's string() includes its position numbers; never re-keep a banner)
        keep = [copy.deepcopy(p) for p in sec.footer._element.findall(qn("w:p"))
                if not list(p.iter(qn("w:drawing"))) and
                ("".join(t.text or "" for t in p.iter(qn("w:t"))).strip() or list(p.iter(qn("w:fldSimple"))) or list(p.iter(qn("w:instrText"))))]
        for ref in list(sp.findall(qn("w:headerReference"))) + list(sp.findall(qn("w:footerReference"))):
            if ref.get(qn("w:type")) in ("first", "even"):
                sp.remove(ref)
        for tp in sp.findall(qn("w:titlePg")):
            sp.remove(tp)
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        _copy_story(th, sec.header)
        _copy_story(tf, sec.footer, keep_paras=keep)
        sec.top_margin, sec.bottom_margin = ts.top_margin, Emu(max(ts.bottom_margin, Emu(int(1.05 * 914400))))
        sec.header_distance, sec.footer_distance = ts.header_distance, ts.footer_distance
    for p in _addendum_paras(doc):
        if not _starts_page(p._p):
            p.paragraph_format.page_break_before = True
    doc.save(out)
    return check(out)


def check(path):
    doc = Document(path)
    probs = []
    for i, sec in enumerate(doc.sections):
        for name, story in (("header", sec.header), ("footer", sec.footer)):
            n = sum(dp.get("descr") == MARK for dp in story._element.iter(qn("wp:docPr")))
            if n != 1:
                probs.append(f"section {i}: {n} letterhead banners in {name} (want exactly 1)")
        if sec._sectPr.findall(qn("w:titlePg")):
            probs.append(f"section {i}: different first page (page 1 would lose the letterhead)")
    for p in _addendum_paras(doc):
        if not _starts_page(p._p):
            probs.append(f"'{p.text.strip()}' does not start a new page")
    return probs


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    probs = check(a[0]) if "--check" in sys.argv else apply(a[0], a[1])
    print("\n".join(probs) or "OK: letterhead on every section; every addendum starts its own page")
    sys.exit(1 if probs else 0)
