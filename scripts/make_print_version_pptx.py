#!/usr/bin/env python3
"""Make an ink-friendly print copy of a dark-theme deck: white background, dark text,
lightened panels, inverted white logos, full-bleed dark photos removed.
Usage: make_print_version_pptx.py IN.pptx OUT.pptx"""
import sys, io, colorsys
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from PIL import Image, ImageOps

def hls(hexs):
    r, g, b = (int(hexs[i:i+2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)

def tohex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, max(0, min(1, l)), s)
    return '%02X%02X%02X' % tuple(round(x * 255) for x in (r, g, b))

def fill_map(hexs):          # panels/boxes: dark -> light, keep hue
    h, l, s = hls(hexs)
    if l < 0.5:
        return tohex(h, 0.97 if s < 0.15 else 0.95, min(s, 0.5))
    return hexs

def text_map(hexs):          # text: light -> dark, keep hue
    h, l, s = hls(hexs)
    if l > 0.5:
        return tohex(h, (1 - l) if s < 0.15 else min(0.38, 1 - l), s)
    return hexs

def line_map(hexs):
    h, l, s = hls(hexs)
    return tohex(h, 1 - l, s) if s < 0.15 else text_map(hexs)

def recolor(el, fn):
    for c in el.iter(qn('a:srgbClr')):
        c.set('val', fn(c.get('val').upper()))

def main(src, dst):
    p = Presentation(src)
    seen = set()
    for s in p.slides:
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for sh in list(s.shapes):
            if sh.shape_type == 13:
                if sh.width > p.slide_width * 0.9:
                    sh._element.getparent().remove(sh._element)
                    continue
                part = sh.image.blob
                key = sh._element.blipFill.blip.rEmbed
                ip = s.part.related_part(key)
                if id(ip) in seen:
                    continue
                seen.add(id(ip))
                im = Image.open(io.BytesIO(ip.blob)).convert('RGBA')
                r, g, b, a = im.split()
                inv = ImageOps.invert(Image.merge('RGB', (r, g, b)))
                out = Image.merge('RGBA', (*inv.split(), a))
                buf = io.BytesIO(); out.save(buf, 'PNG')
                ip._blob = buf.getvalue()
                continue
            spPr = sh._element.find(qn('p:spPr'))
            if spPr is not None:
                for tag in ('a:solidFill', 'a:gradFill'):
                    f = spPr.find(qn(tag))
                    if f is not None:
                        recolor(f, fill_map)
                ln = spPr.find(qn('a:ln'))
                if ln is not None:
                    recolor(ln, line_map)
            if sh.has_text_frame:
                for para in sh.text_frame.paragraphs:
                    for r in para.runs:
                        rPr = r._r.find(qn('a:rPr'))
                        sf = rPr.find(qn('a:solidFill')) if rPr is not None else None
                        if sf is not None and sf.find(qn('a:srgbClr')) is not None:
                            recolor(sf, text_map)
                        else:
                            r.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    p.save(dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
