"""Rebuild Copernic's Oct 8 redline (v5/v6 PDF) as clean paragraphs with Copernic's
changes ACCEPTED: blue (0x1653a0) = inserted text kept, red (0xa32222) = deleted text
dropped, grey (0x555555) = page furniture dropped.

Needs PyMuPDF (fitz). Returns a list of dicts:
  {"page": n, "text": str ("\n" = line break), "font": "serif"|"sans", "size": pt,
   "bold": bool, "table_row": [cells] | None}
"""
import re
import fitz

SRC = "/Users/exomac/.openclaw/workspace/drafts/Copernic_Proposed_Redline_v6_2026-10-08.pdf"
BLUE, RED, GREY = 0x1653A0, 0xA32222, 0x555555
TERMINAL = tuple('.:;)!?"”')


def _is_furniture(spans, text):
    t = text.strip()
    if not t:
        return True
    if t == "Copernic proposed redline v5":
        return True
    if re.fullmatch(r"\d{2,4}", t):          # page number like "1339"
        return True
    if all(round(s["size"]) <= 8 for s in spans) and "redline" in t.lower():
        return True
    return False


def paragraphs(src=SRC, start_page=3):
    doc = fitz.open(src)
    out = []
    for pno in range(start_page - 1, len(doc)):
        page = doc[pno]
        first_on_page = True
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0:
                continue
            lines = []
            for ln in b["lines"]:
                spans = [s for s in ln["spans"] if s["color"] != GREY]
                kept = [s for s in spans if s["color"] != RED]
                lines.append((ln["bbox"], spans, "".join(s["text"] for s in kept)))
            allspans = [s for _, sp, _ in lines for s in sp]
            raw = "".join(t for _, _, t in lines)
            if _is_furniture(allspans, raw):
                continue
            # join lines: short line (< 65% of block width) => hard break
            widths = [bb[2] - bb[0] for bb, _, t in lines if t.strip()]
            maxw = max(widths) if widths else 1
            text = ""
            nonempty = [(bb, t) for bb, _, t in lines if t.strip()]
            for i, (bb, t) in enumerate(nonempty):
                t = t.rstrip()
                if i == 0:
                    text = t
                    continue
                prev_bb = nonempty[i - 1][0]
                short = (prev_bb[2] - prev_bb[0]) < 0.65 * maxw
                if short:
                    text += "\n" + t.lstrip()
                elif text.endswith("-") and not text.endswith(" -"):
                    text += t.lstrip()
                else:
                    text += " " + t.lstrip()
            text = re.sub(r"[ \t]+", " ", text).strip()
            text = re.sub(r"(\w)- (\w)", r"\1-\2", text)
            # numbered list items run together inside one block -> line breaks
            text = re.sub(r" (?=[2-9]\. [A-Z][A-Za-z]+(?: (?:and )?[A-Z][A-Za-z]+)*:)", "\n", text)
            fonts = [s for s in allspans if s["color"] != RED and s["text"].strip()]
            if not fonts:
                continue
            f0 = fonts[0]
            para = {
                "page": pno + 1,
                "text": text,
                "font": "serif" if "Serif" in f0["font"] else "sans",
                "size": round(f0["size"]),
                "bold": bool(f0["flags"] & 16) or "Bold" in f0["font"],
                "table_row": None,
            }
            if text.startswith("|"):
                cells = [c.strip() for c in text.replace("\n", " ").strip("|").split("|")]
                if all(re.fullmatch(r"-+", c) for c in cells):
                    continue
                para["table_row"] = cells
            # continuation across a page break (or orphan line)
            if out and not para["table_row"] and not out[-1]["table_row"]:
                prev = out[-1]
                cont = text[:1].islower() or (
                    first_on_page is False and prev["text"][-1:].islower()
                    and prev["text"].count(" ") > 12 and "\n" not in text
                )
                if text[:1].islower() and not prev["text"].endswith(TERMINAL):
                    cont = True
                if cont and prev["font"] == para["font"]:
                    prev["text"] += " " + text
                    first_on_page = False
                    continue
            para["new_page"] = first_on_page
            first_on_page = False
            out.append(para)
    return out


if __name__ == "__main__":
    for i, p in enumerate(paragraphs()):
        flag = "T" if p["table_row"] else ("B" if p["bold"] else "-")
        print(i, p["page"], p["font"][0], p["size"], flag, "|", p["text"][:150].replace("\n", " / "))
