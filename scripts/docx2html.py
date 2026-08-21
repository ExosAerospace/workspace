#!/usr/bin/env python3
"""docx2html.py <in.docx> <out.html>

Convert a .docx to a self-contained HTML with images EMBEDDED as base64 data URIs, wrapped in a
print-friendly stylesheet. Used by Mission Control's inline docx preview: server.js renders this
HTML to PDF with headless Chrome. Replaces macOS `textutil`, which silently drops all embedded
images (letterhead banners, diagrams, photos) from the preview.

Runs on the system python (/usr/bin/python3) where `mammoth` is installed.
"""
import sys

CSS = """
@page { size: Letter; margin: 0.6in; }
* { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: Calibri, 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1c1c1c;
       line-height: 1.3; margin: 0; }
p { margin: 3pt 0; }
img { max-width: 100%; height: auto; display: block; margin: 4pt auto; }
h1 { font-size: 17pt; color: #0b2a4a; margin: 8pt 0 3pt; }
h2 { font-size: 13pt; color: #0b2a4a; margin: 8pt 0 3pt; }
h3 { font-size: 11.5pt; color: #0b2a4a; margin: 6pt 0 2pt; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
td, th { border: 1px solid #c9d2dd; padding: 4px 7px; vertical-align: top; font-size: 10.5pt; }
th { background: #eef3f9; }
ul, ol { margin: 3pt 0 3pt 18pt; }
a { color: #0b57d0; }
""".strip()


def main():
    if len(sys.argv) < 3:
        print("usage: docx2html.py <in.docx> <out.html>", file=sys.stderr); sys.exit(2)
    src, out = sys.argv[1], sys.argv[2]
    import mammoth
    with open(src, "rb") as f:
        # mammoth embeds images inline as base64 data URIs by default (its default image handler),
        # so the resulting HTML is fully self-contained.
        result = mammoth.convert_to_html(f)
    body = result.value or ""
    html = ("<!doctype html><html><head><meta charset='utf-8'><style>" + CSS +
            "</style></head><body>" + body + "</body></html>")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()
