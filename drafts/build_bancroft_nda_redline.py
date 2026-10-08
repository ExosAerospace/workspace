#!/usr/bin/env python3
"""Exos tracked-changes redline of Bancroft Capital's Mutual NDA/Non-Circ (their 9/25/26 form).
Edits are <w:ins>/<w:del> on Bancroft's own docx so they see exactly what Exos changed.
Input: unpacked+run-merged dir (argv[1]); edits word/document.xml in place."""
import re, sys
from xml.sax.saxutils import escape
D = sys.argv[1] + "/word/document.xml"
x = open(D, encoding="utf-8").read()
AUTH, DATE = "Exos Aerospace", "2026-10-08T07:00:00Z"
nid = [9000]
def _id():
    nid[0] += 1; return nid[0]
def wt(s, tag="w:t"):
    return f'<{tag} xml:space="preserve">{escape(s)}</{tag}>'

def edit(old, new, anchor=None, before=""):
    """Replace `old` with `new` (tracked). If old=="" insert `new` right after `anchor`
    (or right before `before`). Text must sit inside a single <w:t> of one run."""
    global x
    key = old or anchor or before
    k = escape(key)
    pos = x.find(k)
    assert pos >= 0 and x.find(k, pos + 1) < 0, f"not unique/found: {key[:60]}"
    rs = x.rfind("<w:r>", 0, pos); rs2 = x.rfind("<w:r ", 0, pos); rs = max(rs, rs2)
    re_ = x.find("</w:r>", pos) + len("</w:r>")
    run = x[rs:re_]
    m = re.match(r"(<w:r(?: [^>]*)?>)(<w:rPr>.*?</w:rPr>)?(.*)</w:r>$", run, re.S)
    ropen, rpr, body = m.group(1), m.group(2) or "", m.group(3)
    tm = next((t for t in re.finditer(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', body) if k in t.group(1)), None)
    assert tm, f"key spans runs: {key[:60]}"
    txt = tm.group(1); i = txt.find(k)
    pre_b, post_b = body[:tm.start()], body[tm.end():]
    if old:
        a, b = txt[:i], txt[i + len(k):]
    elif anchor:
        a, b = txt[:i + len(k)], txt[i + len(k):]
    else:
        a, b = txt[:i], txt[i:]
    from xml.sax.saxutils import unescape as ue
    out = ""
    if pre_b or a: out += f"{ropen}{rpr}{pre_b}{wt(ue(a)) if a else ''}</w:r>"
    if old: out += f'<w:del w:id="{_id()}" w:author="{AUTH}" w:date="{DATE}"><w:r>{rpr}{wt(old, "w:delText")}</w:r></w:del>'
    if new: out += f'<w:ins w:id="{_id()}" w:author="{AUTH}" w:date="{DATE}"><w:r>{rpr}{wt(new)}</w:r></w:ins>'
    if b or post_b: out += f"<w:r>{rpr}{wt(ue(b)) if b else ''}{post_b}</w:r>"
    x = x[:rs] + out + x[re_:]

# Preamble: punctuation, date, correct legal entity
edit("(the “Agreement) September 25, 2026 is made", "(the “Agreement”), dated as of September 25, 2026, is made")
edit(" an Exos Aerospace and affiliates (“Exos”).", " and Exos Aerospace Systems & Technologies, Inc., a Texas corporation (together with its Affiliates, “Exos”).")
# 1(c): cover oral/unmarked disclosures and pre-signing disclosures
edit("information designated in writing as confidential information about",
     "information, whether disclosed before, on or after the date of this Agreement, that is marked or identified as confidential or that a reasonable person would understand to be confidential given its nature and the circumstances of disclosure, including information about")
edit("by Disclosing Party after the date of this Agreement.", "by Disclosing Party before, on or after the date of this Agreement.")
# 2: export control
edit("", "  Each Party acknowledges that Exos’s Confidential Information may include technical data subject to the International Traffic in Arms Regulations (22 C.F.R. Parts 120-130) or the Export Administration Regulations (15 C.F.R. Parts 730-774).  Exos will not disclose export-controlled technical data under this Agreement without first identifying it as such in writing, and Recipient shall not export, re-export or release any such information to any foreign person or destination except in compliance with applicable U.S. export control laws.",
     anchor="shall notify Disclosing Party immediately.")
# 3: non-circumvention carve-outs + 12-month limit
edit("", "  Notwithstanding the foregoing, the restrictions in this Section 3: (a) apply only to investors, financing sources or project sponsors that the introducing Party identifies to the other Party in writing (e-mail sufficient), within ten (10) business days after the introduction, as having been introduced under this Agreement (each, an “Introduced Party”); (b) shall not apply to any person with whom the other Party or its Affiliates had a relationship or discussions prior to the introduction, as evidenced by written records, or who contacts that Party independently and without use of the introducing Party’s Confidential Information; (c) shall not restrict Exos’s ordinary-course dealings with its existing investors, customers, suppliers, strategic partners, or any governmental authority; and (d) shall expire twelve (12) months after the date of this Agreement.",
     anchor="through its confidential relationship with the other Party hereto.")
# 4: no engagement / no fee
edit("Expenses.", "Expenses; No Engagement or Fees.")
edit("", "  This Agreement does not constitute an engagement of Bancroft or its Affiliates by Exos as placement agent, financial advisor, broker, finder or underwriter.  No fee, commission, success fee or other compensation shall be payable by Exos to Bancroft or its Affiliates in connection with any Transaction, introduction or financing unless set forth in a separate written engagement agreement signed by an authorized officer of Exos.",
     anchor="pertaining to this Agreement.")
# 6: independent development exception
edit("; or (e) disclosure is required", "; (e) disclosure is required")
edit("", "; or (f) the information is independently developed by or for Recipient without use of or reference to the Confidential Information",
     before=".  If disclosure is required under the foregoing item (e)")
# 18: trade-secret survival
edit("", "; provided, however, that Recipient’s obligations with respect to any Confidential Information that constitutes a trade secret under applicable law shall survive for so long as such information remains a trade secret",
     anchor="two (2) years from the date of this Agreement")
# Signature page
edit("Signature page to Mutual Confidentiality Agreement", "Signature page to Mutual Non-Disclosure and Non-Circumvention Agreement")
edit("EXOS AEROSPACE", "EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC.")
# Fill Exos signatory (Name / Title) as tracked insertions in the Exos block
eb = x.find("EXOS AEROSPACE SYSTEMS")
def ins_after(marker, text):
    global x
    i = x.find(marker, eb); assert i > 0, marker
    i = x.find("</w:r>", i) + len("</w:r>")
    x = x[:i] + f'<w:ins w:id="{_id()}" w:author="{AUTH}" w:date="{DATE}"><w:r><w:rPr><w:bCs/><w:u w:val="single"/></w:rPr>{wt("John Quinn" if text=="n" else "Cofounder and CEO")}</w:r></w:ins>' + x[i:]
ins_after('>Name: </w:t>', "n")
ins_after('>Title:  </w:t>', "t")
# Layout: their Exos block runs Name and Title together on one line. Break after the name,
# drop the underline filler tabs, and pull Title back one tab so it aligns with Name.
T = '<w:t xml:space="preserve">John Quinn</w:t></w:r></w:ins>'
i = x.find(T, eb); assert i > 0
x = x[:i] + '<w:t xml:space="preserve">John Quinn</w:t><w:br/></w:r></w:ins>' + x[i + len(T):]
U = '<w:r><w:rPr><w:bCs/><w:u w:val="single"/></w:rPr>' + '<w:tab/>' * 7 + '</w:r>'
i = x.find(U, eb); assert i > 0
x = x[:i] + f'<w:del w:id="{_id()}" w:author="{AUTH}" w:date="{DATE}">' + U + '</w:del>' + x[i + len(U):]
TR = '<w:r><w:rPr><w:bCs/></w:rPr>' + '<w:tab/>' * 6 + '<w:t xml:space="preserve">Title:  </w:t></w:r>'
i = x.find(TR, eb); assert i > 0
x = x[:i] + (f'<w:del w:id="{_id()}" w:author="{AUTH}" w:date="{DATE}"><w:r><w:rPr><w:bCs/></w:rPr><w:tab/></w:r></w:del>'
             '<w:r><w:rPr><w:bCs/></w:rPr>' + '<w:tab/>' * 5 + '<w:t xml:space="preserve">Title:  </w:t></w:r>') + x[i + len(TR):]
TU = '<w:r><w:rPr><w:bCs/><w:u w:val="single"/></w:rPr>' + '<w:tab/>' * 5 + '<w:t xml:space="preserve">  </w:t><w:tab/><w:tab/></w:r>'
i = x.find(TU, eb); assert i > 0
x = x[:i] + f'<w:del w:id="{_id()}" w:author="{AUTH}" w:date="{DATE}">' + TU.replace('<w:t xml:space="preserve">  </w:t>', '<w:delText xml:space="preserve">  </w:delText>') + '</w:del>' + x[i + len(TU):]
# Company name on two lines under the tab stop
N = '<w:t xml:space="preserve">EXOS AEROSPACE SYSTEMS &amp; TECHNOLOGIES, INC.</w:t>'
assert x.count(N) == 1
x = x.replace(N, '<w:t xml:space="preserve">EXOS AEROSPACE SYSTEMS &amp;</w:t><w:br/><w:tab/><w:t xml:space="preserve">TECHNOLOGIES, INC.</w:t>')
open(D, "w", encoding="utf-8").write(x)
print("redline applied")
