#!/usr/bin/env python3
"""lsa_esign_render.py — make the customer-facing, format-true version of an uploaded LSA (Word) for e-sign.

Jon 2026-10-01: "All documents to customers should be on Exos letterhead - header and footer. Addendum should be
on their own page(s). The LSA needs to hold the formats of the original."

Why: the MC e-sign envelope used the mammoth HTML of the .docx (docx2html.py), which drops headers/footers,
page breaks and most layout. The customer would have signed a re-flowed copy that doesn't look like the LSA.

Steps:
  1. apply_exos_letterhead.py → <base>_LETTERHEAD.docx (body untouched; addenda start on their own page)
  2. LibreOffice → <base>_LETTERHEAD.pdf (exact page layout)
  3. pdftoppm → page images → <base>_PAGES.html (same "pdf-rendered" page-image format docusign.html uses for
     uploaded PDFs, so /sign and the executed copy show the real pages), plus hidden esign-line-slot markers for
     every "____" signature/date line so the server stamps each signature onto its line (esign_stamp.py; Jon 10/1)

Usage: lsa_esign_render.py IN.docx  → prints JSON {letterhead_docx, pdf, pages_html, pages}
Exit 1 if the letterhead check fails or the PDF can't be produced.
"""
import base64, glob, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import esign_stamp  # signature-line slots: signatures land ON the lines, not only on a trailing certificate

WS = "/Users/exomac/.openclaw/workspace"
SOFFICE = "/opt/homebrew/bin/soffice"
PDFTOPPM = "/opt/homebrew/bin/pdftoppm"
DPI = "110"


def main(inp):
    base = inp[:-5] if inp.lower().endswith(".docx") else inp
    lh_docx, pdf, pages_html = base + "_LETTERHEAD.docx", base + "_LETTERHEAD.pdf", base + "_PAGES.html"
    r = subprocess.run([sys.executable, os.path.join(WS, "scripts/apply_exos_letterhead.py"), inp, lh_docx], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("letterhead check failed: " + (r.stdout + r.stderr).strip())
    with tempfile.TemporaryDirectory() as tmp:
        # private LibreOffice profile so a concurrent soffice (or a stale lock) can't block the conversion
        subprocess.run([SOFFICE, f"-env:UserInstallation=file://{tmp}/lo", "--headless", "--convert-to", "pdf", "--outdir", tmp, lh_docx],
                       capture_output=True, timeout=240)
        out = os.path.join(tmp, os.path.basename(lh_docx)[:-5] + ".pdf")
        if not os.path.exists(out):
            raise SystemExit("PDF conversion failed")
        os.replace(out, pdf)
        subprocess.run([PDFTOPPM, "-r", DPI, "-jpeg", "-jpegopt", "quality=82", pdf, os.path.join(tmp, "p")], check=True, timeout=240)
        imgs = sorted(glob.glob(os.path.join(tmp, "p-*.jpg")))
        pages = "".join(
            f'<div class="pdf-page" style="margin:0 auto 16px;max-width:720px;">'
            f'<img src="data:image/jpeg;base64,{base64.b64encode(open(f, "rb").read()).decode()}" alt="Page {i}" '
            f'style="width:100%;height:auto;display:block;border:1px solid #ddd;border-radius:4px;"></div>'
            for i, f in enumerate(imgs, 1))
    slots = esign_stamp.find_slots(pdf)
    open(pages_html, "w").write(f'<div class="pdf-rendered" data-pdf="1" data-pages="{len(imgs)}">{pages}{esign_stamp.slots_html(slots)}</div>')
    print(json.dumps({"letterhead_docx": lh_docx, "pdf": pdf, "pages_html": pages_html, "pages": len(imgs),
                      "signature_lines": sum(1 for x in slots if x["kind"] == "sig")}))


if __name__ == "__main__":
    main(sys.argv[1])
