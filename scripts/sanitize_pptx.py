#!/usr/bin/env python3
"""
sanitize_pptx.py — make a PPTX open cleanly in Microsoft PowerPoint.

Fixes the two defect classes that pass python-pptx / macOS QuickLook / zip validation but make
PowerPoint say "found a problem with content" (and fail to repair). These slip in when decks are
script-assembled or merged from pasted slides. See memory: reference_pptx_wont_open_diagnostics.

  1. Broken SmartArt: a <p:graphicFrame> whose <dgm:relIds> point at non-diagram parts (or the
     ppt/diagrams/ parts are missing). The diagram is already flattened to native shapes, so the
     orphan graphicFrame is removed with no visual loss.
  2. PowerPoint-undecodable images: MPO (multi-frame "3D" JPEG) and TIFF. Re-encoded to baseline
     JPEG / PNG (TIFF->PNG with .rels + [Content_Types] fixups).

Usage:
  python3 scripts/sanitize_pptx.py IN.pptx OUT.pptx [--slim] [--check]
    --slim   also downscale images to <=1600px & recompress (for email/Discord delivery copies)
    --check  exit 2 (and print findings) if defects found; do not write OUT. For pipeline gating.

Exit codes: 0 clean/fixed, 2 defects found in --check mode, 1 error.
"""
import sys, os, re, io, zipfile, posixpath
from lxml import etree
from PIL import Image

DGM = 'http://schemas.openxmlformats.org/drawingml/2006/diagram'
P   = 'http://schemas.openxmlformats.org/presentationml/2006/main'
MAXDIM = 1600


def _broken_smartart(zin, slide):
    """A slide's SmartArt is BROKEN if its <dgm:relIds> pointers don't all resolve to existing
    ppt/diagrams/ parts (e.g. they point at images, or the diagram parts are missing). Valid
    SmartArt (pointers -> real diagram parts) is left untouched."""
    names = set(zin.namelist())
    d = zin.read(slide).decode('utf-8', 'ignore')
    m = re.search(r'<dgm:relIds[^>]*>', d)
    if not m:
        return False
    relbytes = zin.read(re.sub(r'(slide\d+\.xml)$', r'_rels/\1.rels', slide))
    rels = {r.get('Id'): (r.get('Type', ''), r.get('Target', ''))
            for r in etree.fromstring(relbytes)}
    for rid in re.findall(r'r:(?:dm|lo|qs|cs)="([^"]+)"', m.group(0)):
        typ, tgt = rels.get(rid, ('', ''))
        if 'diagram' not in typ.lower():
            return True  # pointer resolves to a non-diagram part (or missing) -> broken
        full = posixpath.normpath(posixpath.join('ppt/slides', tgt))
        if full not in names:
            return True  # diagram part missing
    return False


def analyze(zin):
    """Return (broken_smartart_slides, bad_images, has_diagrams) without modifying anything."""
    names = set(zin.namelist())
    has_diagrams = any(n.startswith('ppt/diagrams/') for n in names)
    smartart = []
    for n in names:
        if re.match(r'ppt/slides/slide\d+\.xml$', n) and b'dgm:relIds' in zin.read(n):
            if _broken_smartart(zin, n):
                smartart.append(n)
    bad_images = []
    for n in names:
        if n.startswith('ppt/media/') and n.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
            try:
                fmt = Image.open(io.BytesIO(zin.read(n))).format
            except Exception as e:
                bad_images.append((n, 'UNREADABLE:' + str(e)[:30])); continue
            if fmt not in ('JPEG', 'PNG'):
                bad_images.append((n, fmt))
    return smartart, bad_images, has_diagrams


def sanitize(src, out, slim=False):
    zin = zipfile.ZipFile(src)
    smartart, bad_images, _ = analyze(zin)
    rename = {}      # old media path -> new (tiff->png)
    newmedia = {}    # media path (possibly new name) -> bytes
    for n in zin.namelist():
        if not n.startswith('ppt/media/'):
            continue
        raw = zin.read(n); low = n.lower()
        if not low.endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
            newmedia[n] = raw; continue
        try:
            im = Image.open(io.BytesIO(raw)); im.seek(0); im.load()
        except Exception:
            newmedia[n] = raw; continue
        if slim and max(im.size) > MAXDIM:
            r = MAXDIM / max(im.size); im = im.resize((int(im.size[0]*r), int(im.size[1]*r)), Image.LANCZOS)
        buf = io.BytesIO()
        if low.endswith(('.tif', '.tiff')):
            if im.mode not in ('RGB', 'RGBA', 'L'): im = im.convert('RGB')
            im.save(buf, 'PNG', optimize=True)
            newn = re.sub(r'\.tiff?$', '.png', n); newmedia[newn] = buf.getvalue(); rename[n] = newn
        elif low.endswith('.png'):
            if im.mode == 'P': im = im.convert('RGBA')
            im.save(buf, 'PNG', optimize=True); newmedia[n] = buf.getvalue()
        else:
            if im.mode not in ('RGB', 'L'): im = im.convert('RGB')
            im.save(buf, 'JPEG', quality=(82 if slim else 90), optimize=True); newmedia[n] = buf.getvalue()

    patched_slides = {}
    for n in smartart:
        root = etree.fromstring(zin.read(n)); removed = 0
        for gf in list(root.iter('{%s}graphicFrame' % P)):
            if gf.find('.//{%s}relIds' % DGM) is not None:
                gf.getparent().remove(gf); removed += 1
        if removed:
            patched_slides[n] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

    zout = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        n = item.filename
        if n in rename:
            zout.writestr(rename[n], newmedia[rename[n]]); continue
        if n in newmedia:
            zout.writestr(n, newmedia[n]); continue
        if n in patched_slides:
            zout.writestr(item, patched_slides[n]); continue
        data = zin.read(n)
        if n.endswith('.rels') and rename:
            s = data.decode('utf-8')
            for old, new in rename.items():
                s = s.replace(posixpath.basename(old), posixpath.basename(new))
            data = s.encode('utf-8')
        if n == '[Content_Types].xml' and rename and 'Extension="png"' not in data.decode('utf-8', 'ignore'):
            s = data.decode('utf-8').replace('</Types>', '<Default Extension="png" ContentType="image/png"/></Types>')
            data = s.encode('utf-8')
        zout.writestr(item, data)
    zout.close()
    return patched_slides, rename, bad_images


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    src = a[0]
    slim = '--slim' in a
    check = '--check' in a
    zin = zipfile.ZipFile(src)
    smartart, bad_images, has_diagrams = analyze(zin)
    print(f"{os.path.basename(src)}: SmartArt-slides={smartart} bad-images={bad_images} diagrams-present={has_diagrams}")
    if check:
        if smartart or bad_images:
            print("DEFECTS FOUND — deck would fail in PowerPoint."); sys.exit(2)
        print("clean."); sys.exit(0)
    out = a[1]
    patched, rename, bad = sanitize(src, out, slim=slim)
    from pptx import Presentation
    n = len(Presentation(out).slides._sldIdLst)
    z = zipfile.ZipFile(out)
    assert z.testzip() is None
    print(f"fixed -> {out}  ({round(os.path.getsize(out)/1e6,1)}MB, {n} slides) "
          f"smartart_removed={list(patched)} tiff_png={rename} images_reencoded={len(bad)}")


if __name__ == '__main__':
    main()
