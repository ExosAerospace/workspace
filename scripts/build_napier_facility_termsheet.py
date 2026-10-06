"""Napier Park — Milestone Draw Facility indicative term sheet (2-pager, Word on PRIMARY letterhead).
Built 2026-10-05 from the Lex Maldutis / Mike Chacos call transcript (MC task #1416).
Lex's ask: ask X, use of proceeds Y, schedule of deployment Z, security, why the money is good;
one facility with draws A/B/C tied to milestones; warrants 5-10% max; credit shop, not equity."""
import sys
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
sys.path.insert(0, "scripts")
from _letterhead_fix import apply_letterhead_fixes

LH = "assets/EXOS_Letterhead_Greenville_TX_address_PRIMARY.docx"
OUT = "drafts/Exos_Napier_Park_Milestone_Facility_TermSheet_DRAFT_2026-10-06_v3.docx"
ORANGE = RGBColor(0xF2, 0x6A, 0x21)
GREY = RGBColor(0x55, 0x55, 0x55)

doc = Document(LH)
for p in list(doc.paragraphs):
    p._element.getparent().remove(p._element)
apply_letterhead_fixes(doc)
for s in doc.sections:
    s.left_margin = s.right_margin = Inches(0.85)

st = doc.styles["Normal"]
st.font.name = "Calibri"; st.font.size = Pt(9.5)


def para(text="", bold=False, size=None, color=None, align=None, after=3, before=0, italic=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(before)
    if align: p.alignment = align
    if text:
        r = p.add_run(text); r.bold = bold; r.italic = italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    return p


def rich(parts, after=2, style=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(after)
    for t, b in parts:
        r = p.add_run(t); r.bold = b
    return p


def head(t):
    para(t.upper(), bold=True, size=10.5, color=ORANGE, before=5, after=2)


def bullet(parts):
    if isinstance(parts, str): parts = [(parts, False)]
    p = rich([("\u25aa  ", False)] + list(parts), after=1)
    p.runs[0].font.color.rgb = ORANGE
    p.paragraph_format.left_indent = Inches(0.22); p.paragraph_format.first_line_indent = Inches(-0.16)
    return p


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcolor)
    tcPr.append(sh)


def table(rows, widths, header_fill="222222"):
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    tblPr = t._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
        x = OxmlElement("w:" + e); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "BBBBBB")
        b.append(x)
    tblPr.append(b)
    t.autofit = False
    for j, w in enumerate(widths):
        t.columns[j].width = Inches(w)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.width = Inches(widths[j])
            c.text = ""
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            r = p.add_run(val); r.font.size = Pt(8.5)
            if i == 0:
                r.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); shade(c, header_fill)
            elif j == 0:
                r.bold = True
    return t


# ---------- Title ----------
para("INDICATIVE TERM SHEET — FOR DISCUSSION", bold=True, size=8.5, color=GREY, after=0)
para("Exos Aerospace — Senior Secured Milestone Draw Facility", bold=True, size=15, after=0)
para("Prepared for Alexander Maldutis, Napier Park Global Capital  ·  via Mike Chacos, Trade Vector  ·  October 2026",
     size=9, color=GREY, after=4)
rich([("Bottom line: ", True),
      ("one credit facility, drawn in tranches as milestones are hit — not an equity raise. "
       "Each draw is secured by a specific, identifiable asset (payload receivables, an awarded government contract, "
       "an acquired contract book) and repaid from that asset's cash. Tranche A is the only immediate need; "
       "B and C are drawn only if their triggering events occur.", False)], after=4)

# ---------- 1. The ask ----------
head("1. The ask (X)")
table([
    ["Tranche", "Amount", "Draw trigger / timing", "Use of proceeds (Y)", "Primary security", "Repayment source"],
    ["A — Flight 2 launch readiness", "$750K\n(up to $1.0M)",
     "At close — target before Oct 23, 2026",
     "Finish BLK3 critical design reviews + FAA Part 450 licensing; Flight 2 hardware",
     "Assignment of BLK3 Flight 2 payload receivables (135 kg bay); pledge of Flight 2 hardware",
     "Flight 2 payload deposits (50% at booking); full repayment by Mar 30, 2027"],
    ["B — Government-contract line", "Up to $2.0M",
     "Only on USAF TACFI award + Texas Space Commission match (vote Dec 11) — est. Jan–Mar 2027",
     "Balance-sheet backing required at TACFI contract execution; RDRE flight-test hardware",
     "Assignment of TACFI contract receivables + TSC grant proceeds",
     "Government milestone payments — no dependence on payload sales"],
    ["C — Acquisition working capital", "$350K–$750K\n(up to $1.5M)",
     "Only after Exos closes the Scorpius (SSLC) asset acquisition",
     "Working capital to deliver the acquired tank contract book (not the purchase price)",
     "Assignment of acquired contracts (~$5M firm 2027 tank orders) + acquired equipment / IP",
     "Customer progress payments on the tank contracts"],
    ["Total", "Up to $4.25M", "", "", "", ""],
], [1.15, 0.8, 1.25, 1.35, 1.35, 1.15])
para("Exos funds the Scorpius purchase price itself; Napier Park is asked only to finance working capital "
     "after the acquired balance sheet and contracts are in the collateral pool.",
     size=8.5, italic=True, color=GREY, before=2, after=2)

# ---------- 2. Schedule ----------
head("2. Schedule of deployment (Z)")
table([
    ["Date", "Event", "Facility impact"],
    ["Oct 6–8, 2026", "Term sheet to Napier Park; discussion Thu Oct 8", "Credit committee read; IOI if interested"],
    ["Oct 9 → 23, 2026", "Target close + draw of Tranche A", "Tranche A funds launch-readiness work"],
    ["Oct 10–19, 2026", "Japan: Innovation Dojo program + large Japanese space-company meeting", "Parallel capital track (see §5)"],
    ["By Oct 21, 2026", "USAF decision on submitting the TACFI package", "Tranche B becomes live or drops"],
    ["Oct 20–22, 2026", "New York: private-equity meetings; Napier Park in person Oct 21", "Target IOI → documentation"],
    ["Dec 11, 2026", "Texas Space Commission vote on $2M matching grant", "Tranche B sizing confirmed"],
    ["Jan–Mar 2027", "TACFI contract execution; SSLC acquisition close (target)", "Tranche B / Tranche C draws"],
    ["Mar–Apr 2027", "BLK3 Flight 2", "Tranche A fully repaid by Mar 30, 2027"],
], [1.15, 3.6, 2.3])

# ---------- 3. Security ----------
head("3. Security and why the money is good")
bullet([("Self-liquidating collateral per tranche. ", True),
        ("Every draw is tied to an asset that throws off the cash that repays it; nothing is drawn against a hope.", False)])
bullet([("Flight 2 payload receivables (A). ", True),
        ("135 kg bay at $7,500/kg = $1,012,500 gross if fully booked; Launch Services Agreement terms collect 50% at signing, "
         "40% at T-90 to T-120 days, 10% post-flight. A full bay produces ~$506K in deposits at signing. These are projected "
         "receivables, not yet booked.", False)])
bullet([("Proof the model collects. ", True),
        ("BLK3 Flight 1 customer entX: $820,000 contract, $410,000 received to date (QuickBooks). Flight 1 cash is "
         "committed to Flight 1 and is not pledged here.", False)])
bullet([("Government contract (B). ", True),
        ("$2M USAF TACFI plus $2M Texas Space Commission statutory match against SBIR Phase II contract FA9300-25-C-6022 "
         "(HVRR-RDRE). Tranche B exists only if the award is made.", False)])
bullet([("Acquired contract book (C). ", True),
        ("Scorpius builds composite cryogenic tanks for Intuitive Machines (lunar landers and orbital transfer vehicles). "
         "~$5M of firm 2027 orders (14–16 tanks); Exos targets a 20% EBITDA margin on that book. Exos already owns 18% of Scorpius.", False)])
bullet([("Not loan-to-own. ", True),
        ("Exos is asking for a credit facility it repays in cash. We recently repaid $500K of notes.", False)])

# ---------- 4. Indicative terms ----------
head("4. Indicative terms (Exos proposal, open to Napier Park's structure)")
table([
    ["Term", "Proposal"],
    ["Structure", "Senior secured delayed-draw facility; tranches B and C uncommitted until their triggers occur"],
    ["Pricing", "To be proposed by Napier Park"],
    ["Equity kicker (default-only warrants)", "Warrants are issued ONLY upon an uncured Event of Default under the facility; no warrants "
                      "are issued while Exos is current. Capped at 86,605 Exos common shares, about 0.69% of Exos fully diluted "
                      "(sized to 100% coverage of the $750K Tranche A: $750,000 / $8.66 per-share 409A fair market value after the "
                      "36.51% DLOM, Eqvista 03/31/26; strike $8.66). No further equity under any tranche. Common, not preferred: "
                      "no liquidation preference, board or voting rights"],
    ["Exos buyback (call) right", "If warrants are issued, Exos may repurchase all or part of the warrants, or any shares issued on "
                      "exercise, at any time, for cash equal to their value at the then-current 409A fair market value "
                      "(warrants: that FMV minus the $8.66 strike). Warrants not exercised by [JON: 5] years expire. Exos holds a "
                      "right of first refusal on any transfer. Purpose: Napier Park is a lender, not a long-term shareholder"],
    ["Cash sweep", "Tranche A: [JON: 50%] of Flight 2 payload deposits swept to Napier Park until repaid. B / C: dedicated collection accounts"],
    ["Maturity", "A: Mar 30, 2027.  B: on TACFI milestone receipts.  C: 12 months from draw"],
    ["Reporting", "Monthly booking / receivables report from Exos Mission Control; quarterly financials"],
], [1.3, 5.75])

# ---------- 5. Capital demand band ----------
head("5. Capital demand band and parallel tracks")
rich([("Demand scales with wins. ", True),
      ("If ~20% of the open DoD, NASA and Intuitive Machines pipeline converts, peak need is Tranche A plus the low end of C "
       "(~$1.1–1.5M). At ~75% (optimistic), B and the high end of C are both live (~$4.25M). More awards raise the need "
       "for working capital, and they also add collateral to secure it.", False)], after=3)
rich([("Parallel capital tracks (timing pressure). ", True),
      ("Oct 10–19: Japan (Innovation Dojo; Exos is a selected initiative; Japanese entity planned before year end; "
       "Japan-investor offering targeting ~¥790M / ~US$5M). Oct 20–22: New York private-equity meetings. Longer-dated: "
       "NASA Office of Strategic Capital loan process with Stifel. None of these is committed. A fast Napier Park IOI lets "
       "Tranche A close before the Japan trip outcome is known.", False)], after=3)
para("Contact: John Quinn, Cofounder & CEO · jquinn@exosaero.com · +1-972-740-8355", size=8.5, color=GREY, before=3, after=0)
para("Indicative and non-binding. Not an offer to sell securities. Projected figures are labeled as projections. "
     "Subject to definitive documentation, Exos board approval and counsel review.", size=7.5, italic=True, color=GREY, after=0)

doc.save(OUT)
print(OUT)
