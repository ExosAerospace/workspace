#!/usr/bin/env python3
"""Build REV1 of the 10/3 FNEX FINAL letter with the memo's top-5 fixes as Word tracked changes.

Source: drafts/Exos_FNEX_Response_to_9-29_Markup_FINAL_2026-10-03.docx (unchanged)
Fixes:  drafts/Exos_FNEX_PIPE_Scenarios_and_License_Path_2026-10-04.docx, section 3, gaps 1-5
"""
import copy, sys
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = "drafts/Exos_FNEX_Response_to_9-29_Markup_FINAL_2026-10-03.docx"
OUT = sys.argv[1] if len(sys.argv) > 1 else "drafts/Exos_FNEX_Response_to_9-29_Markup_REV1_TRACKED_2026-10-04.docx"
AUTHOR, DATE = "Exo", "2026-10-04T12:30:00Z"
_id = [9000]


def nid():
    _id[0] += 1
    return str(_id[0])


def mark(tag):
    el = OxmlElement(tag)
    el.set(qn("w:id"), nid()); el.set(qn("w:author"), AUTHOR); el.set(qn("w:date"), DATE)
    return el


def text_runs(p):
    return [r for r in p._p.iter(qn("w:r")) if r.find(qn("w:t")) is not None]


def mk_run(rpr, text):
    r = OxmlElement("w:r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = OxmlElement("w:t"); t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve"); t.text = text
    r.append(t)
    return r


def ins_wrap(run):
    w = mark("w:ins"); w.append(run); return w


def del_run(r):
    """Wrap an existing run in w:del, converting w:t -> w:delText."""
    for t in r.findall(qn("w:t")):
        t.tag = qn("w:delText")
    w = mark("w:del")
    r.addprevious(w); w.append(r)
    return w


def replace(p, old, new):
    """Tracked replace of `old` (must sit inside one run) with `new`."""
    for r in text_runs(p):
        t = r.find(qn("w:t"))
        if old in t.text:
            before, after = t.text.split(old, 1)
            rpr = r.find(qn("w:rPr"))
            anchor = r
            if before:
                b = mk_run(rpr, before); anchor.addprevious(b)
            d = mk_run(rpr, old); anchor.addprevious(d); del_run(d)
            if new:
                dw = d.getparent()
                dw.addnext(ins_wrap(mk_run(rpr, new)))
            if after:
                t.text = after
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            else:
                anchor.getparent().remove(anchor)
            return
    raise SystemExit(f"not found in single run: {old!r}")


def replace_body(p, new, keep_first=0):
    """Delete all text runs after the first `keep_first` and insert `new` at the end."""
    runs = text_runs(p)
    rpr = runs[-1].find(qn("w:rPr"))
    last = None
    for r in runs[keep_first:]:
        last = del_run(r)
    last.addnext(ins_wrap(mk_run(rpr, new)))


def delete_para(p):
    for r in text_runs(p):
        del_run(r)
    ppr = p._p.get_or_add_pPr()
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr"); ppr.append(rpr)
    rpr.append(mark("w:del"))


def new_para_after(anchor_p, template_p, segments):
    """Insert a fully tracked-inserted paragraph after anchor_p, styled like template_p.
    segments: list of (template_run_index, text)."""
    tp = template_p._p
    np_ = OxmlElement("w:p")
    ppr = copy.deepcopy(tp.find(qn("w:pPr")))
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr"); ppr.append(rpr)
    rpr.append(mark("w:ins"))
    np_.append(ppr)
    truns = text_runs(template_p)
    for idx, txt in segments:
        rr = truns[idx].find(qn("w:rPr"))
        rr = copy.deepcopy(rr) if rr is not None else None
        if rr is not None:
            for x in rr.findall(qn("w:lastRenderedPageBreak")):
                rr.remove(x)
        np_.append(ins_wrap(mk_run(rr, txt)))
    anchor_p._p.addnext(np_)
    from docx.text.paragraph import Paragraph
    return Paragraph(np_, anchor_p._parent)


doc = Document(SRC)
P = doc.paragraphs
assert P[0].text == "October 3, 2026" and P[48].text.startswith("Still open") and P[64].text.startswith("Attachment")
HEAD, BUL, CLAUSE = P[9], P[10], P[65]

# Date: left blank for Jon (Counsel review first)
replace(P[0], "3", "__")

# Opening paragraph: flag what is new
last = text_runs(P[8])[-1]
last.addnext(ins_wrap(mk_run(last.find(qn("w:rPr")),
    " Sections 10 to 13 and the revised section 7 are new since my October 3 letter. They cover the PIPE note, a $10 million floor at closing, when fees are earned, the note's conversion price, and the listing; proposed language is added to the attachment.")))

# Fix 4 (part): §1 second cash tranche trigger
replace(P[11], "half once $40 million has been raised",
        "half only if FNEX-placed financings after Closing total $40 million within 12 months, as set out in section 13")

# Fix 5: §7 heading + body
replace_body(P[32], "7.  Listing: name the shell and the listing standard, and make Nasdaq approval a condition of Closing")
replace_body(P[33], "Please name the Target and confirm in writing the listing standard the combined company will meet. The one-year seasoning period and the $4 price held for 30 of 60 trading days that I described on October 3 apply to a merger with an OTC or unlisted shell. If the Target is already listed on Nasdaq, the combined company must instead meet the full initial listing standards at Closing. Either way, at a $2.00 merger price, how will the stock reach and hold the required price? A deep PIPE discount works against that, which is another reason for the 30% cap. Nasdaq approval of the combined company's listing should be a condition of Closing.", keep_first=1)
p = new_para_after(P[33], BUL, [(0, "•  "), (1, "Why: a merger that closes into a stock that cannot list, or is suspended, leaves the PIPE investors and Exos holders with no market. Nasdaq now has discretion to deny listings by small companies, including based on the advisors involved, and companies that fall below a $5 million market value face immediate delisting with no automatic stay.")])

# Fixes 1-4: new sections 10-13, inserted before "Still open"
sections = [
    ("10.  The PIPE note: held in escrow until Closing, never repayable debt", [
        "Your model funds the approximately $15 million PIPE as a note about three months before Closing, but no document defines its issuer, maturity, security, or what happens if the merger does not close. A note that does not convert has to be repaid with interest, which would leave Exos in debt on a deal that failed.",
        "The PIPE proceeds are held in escrow until Closing. If Closing has not occurred by the Outside Date, the proceeds are returned to the investors or, at Exos's option, convert into Exos common stock. No principal, interest or redemption amount is ever payable in cash, and the note is unsecured. Please attach the note terms to the agreement as an exhibit.",
        "Why: the PIPE is meant to be equity that funds Exos at the merger. If it funds early and the merger fails, it must not become a debt Exos has to repay. This restores the position in our September 26 letter.",
    ]),
    ("11.  $10 million net to Exos at Closing", [
        "Exos needs $10 million net at Closing to proceed. Today that is a model output, not a term: the $15 million minimum raise conditions your fee but does not protect Exos. At $12 million the model leaves Exos about $8.3 million.",
        "Net Closing Cash of at least $10 million is a condition of Closing that only Exos can waive. If the PIPE comes in short, the cash fee due at Closing is deferred first, then the placement fee, to the next financing. That lowers the PIPE needed to clear $10 million to about $11.9 million.",
        "Why: the $10 million is the reason for the transaction. A closing that delivers less would leave Exos underfunded while the fees are paid in full.",
    ]),
    ("12.  Fees earned only at Closing", [
        "This moves from our open items into the agreement. No cash fee, placement fee, fee shares or expenses are earned or payable unless Closing occurs, and \"Closing\" means consummation of the merger with the Target: not signing of the merger agreement, and not funding of the PIPE note.",
        "Why: the September 29 text still triggers the cash fee on signing, and the placement fee clause says \"at Closing\" without defining it. If the note funds and the merger then fails, no fee should have been earned.",
    ]),
    ("13.  The note's conversion price and the $40 million trigger", [
        "In the model the note converts at 20% below the price of the first post-merger raise. If that raise never happens, the note never converts; if it is priced low, dilution grows (at $1.00, about 19 million note shares instead of 7.65 million). The note should convert at Closing at the merger price less the agreed discount, within the 30% cap in section 5, and not be adjusted by any later financing.",
        "The second 0.5% cash fee is due on \"an aggregate of $40MM\", which is not defined. It should be due only if FNEX-placed financings after Closing total at least $40 million within 12 months, not counting the PIPE or capital Exos raises itself.",
        "Why: the board needs to know the cap table when it approves the merger, and a fee should be tied to money FNEX actually places.",
    ]),
]
anchor = P[47]
for head, bullets in sections:
    anchor = new_para_after(anchor, HEAD, [(0, head)])
    for b in bullets:
        anchor = new_para_after(anchor, BUL, [(0, "•  "), (1, b)])

# Fix 3: the "Still open" fees-at-closing bullet is now section 12
assert P[49].text.startswith("Fees earned and payable at closing") or "Fees earned and payable at closing" in P[49].text
delete_para(P[49])

# Attachment: new clauses after the last clause
clauses = [
    "PIPE Note; Escrow. The PIPE is issued on the terms of Exhibit A. All PIPE proceeds are held in escrow until Closing. If Closing has not occurred by the Outside Date, the proceeds are returned to the investors or, at the Company's option, convert into Company common stock at $[____] per share. No principal, interest or redemption amount is ever payable by the Company in cash, and the PIPE is unsecured.",
    "Net Closing Cash. It is a condition to Closing, waivable only by the Company, that Net Closing Cash is at least $10,000,000. \"Net Closing Cash\" means PIPE proceeds released to the Company at Closing less all Fees, the Placement Fee, expenses and Transaction costs paid at Closing. To the extent of any shortfall, payment of the Cash Fee, and then of the Placement Fee, is deferred to the Company's next financing.",
    "Fees Earned Only at Closing. No Fee, Placement Fee, Fee shares or expenses are earned or payable unless Closing occurs. \"Closing\" means consummation of the merger of the Company with the Target. Neither signing of a definitive agreement nor funding of the PIPE is Closing.",
    "PIPE Conversion; Second Cash Fee. The PIPE converts at Closing at the merger price per share less the agreed discount, subject to the PIPE Pricing cap, and is not adjusted by any later financing. The second one-half percent (0.5%) of the Cash Fee is payable only if, within twelve (12) months after Closing, financings placed by FNEX after Closing total at least $40,000,000, excluding the PIPE and any capital raised by the Company from other sources.",
    "Target and Listing. Before execution of any definitive agreement, FNEX shall name the Target and confirm in writing the listing standard under which the combined company will meet Nasdaq initial listing requirements at Closing. Approval of the combined company's listing by Nasdaq is a condition to Closing.",
]
anchor = P[76]
for c in clauses:
    anchor = new_para_after(anchor, CLAUSE, [(0, c)])

# Keep tracking on for further edits
st = doc.settings.element
if st.find(qn("w:trackRevisions")) is None:
    tr = OxmlElement("w:trackRevisions")
    ps = st.find(qn("w:proofState"))
    (ps.addnext(tr) if ps is not None else st.insert(1, tr))

doc.save(OUT)
print("saved", OUT)
