#!/usr/bin/env python3
"""esign_stamp.py — put e-signatures ON the document's signature lines (not just on a trailing certificate).

Jon 2026-10-01 (Lesiw LSA, envelope 76caeac89582): "the signatures at the bottom of the page is invalid. Fix it
again - this time fully." The executed copy showed the Acceptance block's "______  Date: ____" lines blank, with the
signatures only in a certificate tacked on after the document — it reads as an unsigned contract.

Two parts:
  find_slots(pdf)  — pdftotext -bbox: every signature blank ("____" run, ≥8) and its "Date: ____" partner on the same
                     row, labelled by the printed name on the line below (e.g. "Matt Lesiw", "John Quinn, Cofounder…").
                     Emitted into the page-image HTML as hidden <div class="esign-line-slot" …> markers (fractions of
                     the page, so they hold at any render DPI). Used by lsa_esign_render.py; docusign.html makes the
                     same markers from pdf.js for uploaded PDFs.
  stamp (stdin JSON) — burns each signed signer's signature image onto its line and the signing date (US Central) onto
                     its Date line, directly into the page JPEGs (email clients strip CSS overlays), and writes the
                     executed PDF: the stamped pages + a Signature Certificate (audit trail) page.

CLI:
  esign_stamp.py slots PDF                 → JSON list of slots
  esign_stamp.py stamp < {html, signers, id, title, completedAt, pdf_out}
                                           → JSON {html, pdf, placed:[signer names], slots}
"""
import base64, html as htmlmod, io, json, re, subprocess, sys
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

PDFTOTEXT = "/opt/homebrew/bin/pdftotext"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
CT = ZoneInfo("America/Chicago")
BLANK = re.compile(r"_{8,}")
SLOT_RE = re.compile(r'<div class="esign-line-slot"([^>]*)></div>')


# ── slot detection ────────────────────────────────────────────────────────────
def find_slots(pdf):
    out = subprocess.run([PDFTOTEXT, "-bbox", pdf, "-"], capture_output=True, text=True, timeout=120).stdout
    slots = []
    for pno, (pw, ph, body) in enumerate(re.findall(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', out, re.S), 1):
        pw, ph = float(pw), float(ph)
        words = [dict(x0=float(a), y0=float(b), x1=float(c), y1=float(d), t=htmlmod.unescape(t))
                 for a, b, c, d, t in re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', body)]
        rows = []
        for w in words:
            if not BLANK.search(w["t"]):
                continue
            h = w["y1"] - w["y0"]
            same = [o for o in words if o is not w and abs((o["y0"] + o["y1"]) / 2 - (w["y0"] + w["y1"]) / 2) < h * 0.5]
            left = sorted([o for o in same if o["x1"] <= w["x0"] + 1], key=lambda o: o["x1"])
            prev = left[-1]["t"] if left else ""
            if re.match(r"^date:?$", prev.strip(), re.I):
                rows.append(dict(kind="date", w=w))
                continue
            # a signature blank starts its line (or follows a short "By:"/"Signature:" lead-in), not mid-sentence
            if left and not re.match(r"^(by|signature|signed|sign|name)\s*:?$", prev.strip(), re.I):
                continue
            # the printed name under this line only — stop at the next blank on the row (two-column signature blocks)
            nxt = [o["x0"] for o in same if o["x0"] >= w["x1"] - 1 and BLANK.search(o["t"])]
            right = min([w["x1"] + 320] + [x - 2 for x in nxt])
            below = [o for o in words if w["y1"] - 1 < o["y0"] < w["y1"] + h * 1.9 and o["x1"] > w["x0"] - 4 and o["x0"] < right]
            label = " ".join(o["t"] for o in sorted(below, key=lambda o: o["x0"])).strip()
            # clear space above the line (the signature must not run into the text block above it)
            above = [o["y1"] for o in words if o["y1"] <= w["y0"] + 0.5 and o["y1"] > w["y0"] - h * 6 and o["x1"] > w["x0"] - 4 and o["x0"] < w["x1"] + 4]
            rows.append(dict(kind="sig", w=w, label=label, top=max(above) if above else w["y0"] - h * 3))
        sigs = [r for r in rows if r["kind"] == "sig"]
        for r in rows:
            w = r["w"]
            box = [round(w["x0"] / pw, 5), round(w["y0"] / ph, 5), round(w["x1"] / pw, 5), round(w["y1"] / ph, 5)]
            s = dict(page=pno, kind=r["kind"], box=box)
            if r["kind"] == "sig":
                s["label"], s["top"] = r["label"], round(r["top"] / ph, 5)
            else:  # pair the date blank with the signature blank on the same row
                mate = [g for g in sigs if abs(g["w"]["y0"] - w["y0"]) < 3]
                if not mate:
                    continue
                s["label"] = mate[0]["label"]
            slots.append(s)
    return slots


def slots_html(slots):
    return "".join(
        f'<div class="esign-line-slot" data-page="{s["page"]}" data-kind="{s["kind"]}" '
        f'data-label="{htmlmod.escape(s.get("label", ""), quote=True)}" data-box="{",".join(map(str, s["box"]))}"'
        + (f' data-top="{s["top"]}"' if "top" in s else "") + '></div>'
        for s in slots)


def parse_slots(html):
    out = []
    for attrs in SLOT_RE.findall(html):
        a = dict(re.findall(r'data-([a-z]+)="([^"]*)"', attrs))
        out.append(dict(page=int(a["page"]), kind=a["kind"], label=htmlmod.unescape(a.get("label", "")),
                        box=[float(v) for v in a["box"].split(",")], top=float(a["top"]) if a.get("top") else None))
    return out


# ── signer ↔ slot matching ────────────────────────────────────────────────────
def is_exos(s):
    return bool(re.search(r"@exosaero\.com$", s.get("email") or "", re.I) or re.search(r"\bquinn\b", s.get("name") or "", re.I))


def match(label, signers):
    lab = label.lower()
    for s in signers:
        if (s.get("name") or "").lower() and s["name"].lower() in lab:
            return s
    for s in signers:
        last = (s.get("name") or "").split()[-1:] or [""]
        if len(last[0]) > 2 and re.search(r"\b" + re.escape(last[0].lower()) + r"\b", lab):
            return s
    if re.search(r"\bexos\b", lab):
        ex = [s for s in signers if is_exos(s)]
        return ex[0] if len(ex) == 1 else None
    return None


def assign(slots, signers):
    """slot index → signer. Name match first; leftover signature lines map to leftover signers top-to-bottom only when
    the counts agree exactly (counterparty first, Exos last — the envelope's signing order)."""
    sig_idx = [i for i, s in enumerate(slots) if s["kind"] == "sig"]
    got = {i: match(slots[i]["label"], signers) for i in sig_idx}
    used = {id(v) for v in got.values() if v}
    free_slots = sorted([i for i in sig_idx if not got[i]], key=lambda i: (slots[i]["page"], slots[i]["box"][1]))
    free_signers = [s for s in signers if id(s) not in used]
    if free_slots and len(free_slots) == len(free_signers):
        for i, s in zip(free_slots, free_signers):
            got[i] = s
    res = {i: s for i, s in got.items() if s}
    for i, s in enumerate(slots):  # dates follow their row's signature line
        if s["kind"] == "date":
            mate = [j for j in sig_idx if slots[j]["page"] == s["page"] and abs(slots[j]["box"][1] - s["box"][1]) < 0.006]
            if mate and mate[0] in res:
                res[i] = res[mate[0]]
    return res


# ── stamping ──────────────────────────────────────────────────────────────────
def sig_image(data_url):
    im = Image.open(io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))).convert("RGBA")
    # trim to the ink: alpha channel, or non-white pixels when the PNG is opaque
    a = im.getchannel("A")
    bbox = a.point(lambda v: 255 if v > 20 else 0).getbbox()
    if bbox == (0, 0, im.width, im.height) or bbox is None:
        g = im.convert("L").point(lambda v: 255 if v < 200 else 0)
        bbox = g.getbbox() or bbox
    return im.crop(bbox) if bbox else im


def signed_date(s):
    return datetime.fromisoformat(s["signedAt"].replace("Z", "+00:00")).astimezone(CT).strftime("%Y-%m-%d")


def stamp_page(img, page_slots, who):
    W, H = img.size
    d = ImageDraw.Draw(img)
    for i, s in page_slots:
        signer = who.get(i)
        if not signer or not signer.get("signatureData"):
            continue
        x0, y0, x1, y1 = s["box"][0] * W, s["box"][1] * H, s["box"][2] * W, s["box"][3] * H
        lh = y1 - y0
        base = y0 + lh * 0.78  # the underscore rule sits near the bottom of its word box
        if s["kind"] == "sig":
            sig = sig_image(signer["signatureData"])
            bottom = base + lh * 0.12  # ink just crosses the rule, like a wet signature, clear of the printed name below
            top = s["top"] * H + lh * 0.12 if s.get("top") is not None else bottom - lh * 3.2
            bh, bw = min(lh * 3.2, bottom - top), (x1 - x0) * 0.96
            k = min(bh / sig.height, bw / sig.width)
            sig = sig.resize((max(1, int(sig.width * k)), max(1, int(sig.height * k))), Image.LANCZOS)
            img.paste(sig, (int(x0 + 4), int(bottom - sig.height)), sig)
        else:
            f = ImageFont.truetype(FONT, max(9, int(lh * 0.95)))
            d.text((x0 + 4, base - lh * 0.15), signed_date(signer), font=f, fill=(20, 32, 70), anchor="ls")


def certificate_page(env, W, H):
    page = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(page)
    u = W / 8.5  # px per inch
    f_h, f_b, f_s = ImageFont.truetype(FONT, int(u * 0.22)), ImageFont.truetype(FONT, int(u * 0.13)), ImageFont.truetype(FONT, int(u * 0.11))
    y = u * 0.9
    d.text((u, y), "Signature Certificate", font=f_h, fill=(10, 22, 40)); y += u * 0.4
    d.text((u, y), env.get("title", ""), font=f_b, fill=(60, 60, 60)); y += u * 0.35
    d.line((u, y, W - u, y), fill=(10, 22, 40), width=max(1, int(u * 0.02))); y += u * 0.25
    for s in env["signers"]:
        if not s.get("signed"):
            continue
        sig = sig_image(s["signatureData"])
        k = min(u * 0.6 / sig.height, u * 3.0 / sig.width)
        sig = sig.resize((max(1, int(sig.width * k)), max(1, int(sig.height * k))), Image.LANCZOS)
        page.paste(sig, (int(u), int(y)), sig); y += sig.height + u * 0.08
        d.text((u, y), f'{s["name"]}' + (f' — {s["role"]}' if s.get("role") else ""), font=f_b, fill=(20, 20, 20)); y += u * 0.2
        d.text((u, y), f'Signed electronically: {s["signedAt"]} · IP: {s.get("ip") or "n/a"} · Method: {s.get("signatureType") or "typed"}',
               font=f_s, fill=(90, 90, 90)); y += u * 0.4
    y += u * 0.1
    for line in ["Executed electronically by the parties under the U.S. E-SIGN Act (15 U.S.C. §7001 et seq.) and the Uniform",
                 "Electronic Transactions Act (UETA). Each signature above is also applied on the document's signature lines.",
                 f'Envelope ID: {env.get("id", "")} · Completed: {env.get("completedAt") or ""}']:
        d.text((u, y), line, font=f_s, fill=(90, 90, 90)); y += u * 0.18
    return page


def stamp(env):
    html = env["html"]
    slots = parse_slots(html)
    signed = [s for s in env["signers"] if s.get("signed") and s.get("signatureData")]
    who = assign(slots, signed)
    # page number = count of pdf-page containers so far; a page that docusign.html cut at "Sincerely" holds several
    # image slices and carries no line slots, so only single-image pages are stamped / go into the executed PDF
    img_re = re.compile(r'src="data:image/(?:jpeg|png);base64,([A-Za-z0-9+/=]+)"')
    found = [(html.count('class="pdf-page"', 0, m.start()), m) for m in img_re.finditer(html)]
    per_page = {}
    for pno, _ in found:
        per_page[pno] = per_page.get(pno, 0) + 1
    pages, stamped = [], {}
    for pno, m in found:
        if per_page[pno] != 1:
            continue
        im = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGB")
        page_slots = [(i, s) for i, s in enumerate(slots) if s["page"] == pno]
        if page_slots:
            stamp_page(im, page_slots, who)
            buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
            stamped[m.start()] = 'src="data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode() + '"'
        pages.append(im)
    out_html = img_re.sub(lambda m: stamped.get(m.start(), m.group(0)), html)
    placed = sorted({who[i]["name"] for i, s in enumerate(slots) if s["kind"] == "sig" and i in who})
    pdf = None
    if env.get("pdf_out") and pages and len(pages) == len(found) and all(s.get("signed") for s in env["signers"]):
        cert = certificate_page(env, *pages[0].size)
        pages[0].save(env["pdf_out"], "PDF", resolution=pages[0].size[0] / 8.5, save_all=True, append_images=pages[1:] + [cert])
        pdf = env["pdf_out"]
    return dict(html=out_html, pdf=pdf, placed=placed, slots=len(slots))


if __name__ == "__main__":
    if sys.argv[1:2] == ["slots"]:
        print(json.dumps(find_slots(sys.argv[2]), indent=1))
    elif sys.argv[1:2] == ["stamp"]:
        print(json.dumps(stamp(json.load(sys.stdin))))
    else:
        raise SystemExit(__doc__)
