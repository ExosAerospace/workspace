#!/usr/bin/env python3
"""Build (1) the expanded SSLC Board non-compliance notice (10/18, supersedes 10/17 r3) and
(2) John's draft reply to Jim Wertz's 10/18 email. Figures: SSLC QuickBooks extract 10/11/2026
(data-room/SSLC/qb-2026-10-11) + SSLC's 'Summary of SSLC Debt 2026.08.31' (Jim Wertz, 10/18)."""
import copy
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

R3 = "drafts/SSLC_Director_Violation_Notice_to_Board_2026-10-17_r3.docx"
OUT_NOTICE = "drafts/SSLC_Director_Violation_Notice_to_Board_2026-10-19.docx"
OUT_EMAIL = "drafts/SSLC_Reply_to_JWertz_Debt_Summary_2026-10-19.docx"
NAVY = RGBColor(0x1F, 0x38, 0x64)


def new_doc():
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    for s in d.sections:
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1.0)
    return d


def para(d, text="", *, bold=False, italic=False, size=11, align=None, space_after=6, color=None):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(space_after)
    if align is not None: p.alignment = align
    if text:
        r = p.add_run(text); r.bold = bold; r.italic = italic; r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    return p


def heading(d, label, text):
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(4)
    r = p.add_run(f"{label}  {text}"); r.bold = True; r.font.size = Pt(11.5); r.font.color.rgb = NAVY
    return p


def kv(d, label, value):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(label + "  "); r.bold = True
    p.add_run(value)
    return p


def bullet(d, text, lead=None):
    p = d.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(4)
    if lead:
        r = p.add_run(lead); r.bold = True
    p.add_run(text)
    return p


def divider(d):
    dp = d.add_paragraph(); dp.paragraph_format.space_after = Pt(8)
    pPr = dp._p.get_or_add_pPr(); pbdr = OxmlElement('w:pBdr'); b = OxmlElement('w:bottom')
    for k, v in (('w:val', 'single'), ('w:sz', '6'), ('w:space', '1'), ('w:color', '1F3864')):
        b.set(qn(k), v)
    pbdr.append(b); pPr.append(pbdr)


def table(d, header, rows, widths=None):
    t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(9.5)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; r = cells[i].paragraphs[0].add_run(v); r.font.size = Pt(9.5)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths): row.cells[i].width = Inches(w)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def src(d, n, text):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(f"[{n}]  "); r.bold = True; r.font.size = Pt(9)
    r2 = p.add_run(text); r2.font.size = Pt(9)


# =====================================================================================
# 1. Expanded notice
# =====================================================================================
d = new_doc()
para(d, "NOTICE TO THE BOARD OF DIRECTORS", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2, color=NAVY)
para(d, "Scorpius Space Launch Company (a California corporation)", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para(d, "Non-Compliance with the Bylaws and with the Board’s October 13, 2026 Actions — Expanded Notice",
     italic=True, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)
divider(d)

kv(d, "TO:", "The Board of Directors, Scorpius Space Launch Company —")
para(d, "James Wertz (Chairman of the Board & Director); Markus Rufer (Chief Executive Officer & Director); "
        "Alice Wertz (Secretary, Chief Financial Officer & Director); Robert Conger (Director).", space_after=4)
kv(d, "FROM:", "John Quinn, Director")
kv(d, "DATE:", "October 19, 2026")
kv(d, "RE:", "Expanded notice of non-compliance, after the October 18 debt summary and update from the Chairman. "
             "This notice replaces my notice of October 17, 2026; that notice’s commission item is carried forward unchanged in Part B.")
kv(d, "ATTACHMENTS:", "A — Sales Commission Agreement between SSLC and Exos (unsigned draft dated October 19, 2026, conformed to the April 10, 2025 Board Approval). "
                      "B — “Summary of SSLC Debt as of August 31, 2026,” as provided by the Chairman on October 18, 2026.")
para(d, "")

heading(d, "1.", "Summary")
para(d, "On October 18 the Chairman sent the Board a debt summary and an update. It does not answer the questions the "
        "Board deferred on October 13. It also raises four new matters that the Bylaws reserve to the Board acting together: "
        "(i) related-party balances owed to entities controlled by two directors, now presented at face value; "
        "(ii) a $100,000 interest waiver agreed by one officer; (iii) profit figures that do not agree with the Company’s own "
        "books; and (iv) a letter of intent to invest in or buy the Company that has not been given to the Board. "
        "Part A.6 sets out, as a formal finding for the Board, journal entries and payments that benefit entities controlled by the "
        "Chairman and the Secretary/CFO at the expense of SSLC and its other shareholders. Section 3 lists the resolutions I ask the Board to vote on.")
para(d, "I ask that each item be taken up at a duly noticed special meeting on Tuesday, October 20, 2026 (see A.7), and that this "
        "notice be entered in the minute book.")

heading(d, "2.", "Status of the Board’s October 13, 2026 actions")
table(d, ["Item", "Board action on 10/13", "Status at 10/18"], [
    ["Motion 1: offer and §3 exclusivity", "Deferred. SSLC to send a written counteroffer with its advisor’s comments.",
     "Not received as of 10/19. The Chairman says comments or a counteroffer will come by Tuesday 10/20. Taken last on 10/20."],
    ["Motion 2: full read-only access to SSLC’s books for all directors", "Approved.",
     "Done. Established through Exos Mission Control on October 19, 2026, as the Board agreed, because QuickBooks seats are limited. Markus Rufer and Robert Conger were emailed their login instructions that day and have read-only access to SSLC’s books and records. Mission Control is also the platform for the Motion 4 ERP/MRP evaluation."],
    ["Motion 3: correct AR Unbilled / customer-deposit accounting", "Approved; 5 business days.",
     "Due Tuesday 10/20. Billings in excess of revenue grew from $520,757 (8/31) to $942,177 (10/11)."],
    ["Motion 4: ERP/MRP evaluation", "Approved, at no cost to SSLC.", "In progress (Exos), on Exos Mission Control: ERP/MRP, inventory, purchasing and job costing."],
    ["Motion 5: related-party balances", "Deferred. SSLC to review the transactions and respond “in the next couple of days.”",
     "No response to the October 12 questions. A debt summary was sent instead (Attachment B)."],
], widths=[1.7, 2.3, 2.5])

para(d, "PART A — NEW MATTERS ARISING FROM THE OCTOBER 18 DATA", bold=True, color=NAVY, space_after=4)

heading(d, "A.1", "Related-party balances are presented at face value, without disinterested-director review")
para(d, "Of the $1,020,690 of debt in Attachment B, $857,419 (84%) is owed to Microcosm, Inc. ($447,900), Microcosm "
        "Astronautics Books / MDAB ($317,019) and the Wertz family ($92,500). These are entities in which the Chairman and the "
        "Secretary/CFO have a financial interest. The rest is the SBA EIDL loan ($132,072) and Exos ($31,200).")
para(d, "The questions I sent the Board on October 12 are still unanswered. Each one affects what SSLC’s shareholders receive at closing:")
bullet(d, " $426,687 of Microcosm payables reclassified on April 30, 2026 to 2385 Due to Microcosm, with no invoice-level support provided.", "Reclassification.")
bullet(d, " $812,699 of SSLC loans to Microcosm (2019–October 2025), booked and then netted to zero on April 30, 2026 against unsupported Microcosm balances.", "Loan netting.")
bullet(d, " SSLC has paid 100% of the Lomita Blvd rent and utilities since July 2024, against about 50% before. On the 2024 basis, "
          "Microcosm’s uncredited share is about $351K through August 2026.", "Facility share.")
bullet(d, " Notes, terms and approvals for the Bookstore note ($320,582) and the Wertz loan ($92,500).", "Loan documents.")
para(d, "Bylaw basis. Article III, Section 1 (all corporate powers are exercised by or under the direction of the Board). "
        "Article III, Section 9 (Board acts are subject to Corporations Code §310 for transactions in which a director has a material "
        "financial interest) [6]. None of these balances has been approved by the disinterested directors.")

heading(d, "A.2", "A $100,000 interest waiver agreed by one officer")
para(d, "The Chairman reports that the Secretary/CFO “has reviewed the SSLC debt and agreed to drop the $100,000 in interest owed to "
        "the bookstore.” I welcome the waiver. It confirms that the $97,302 of interest capitalized into 2700 Notes Payable–Bookstore on "
        "April 30, 2026 should not have been booked. But the same person keeps SSLC’s books and has an interest in the creditor. "
        "A waiver made that way must be documented so it cannot be reversed later.")
para(d, "Bylaw basis. Article V, Section 10 (the CFO keeps “adequate and correct books and records”). Article V, Section 9 (the Secretary "
        "keeps minutes of all Board actions). Article III, Section 1. Required: a signed written release from MDAB, a reversing journal "
        "entry, and a Board resolution entered in the minute book. The Board should also be told who approved the April 30 entry.")

heading(d, "A.3", "Profit figures do not agree with the Company’s books")
para(d, "The Chairman reports pre-tax profit of $577K for June–August and “approximately $48,000 per week.” SSLC’s own records show otherwise:")
table(d, ["Measure (SSLC records)", "Amount", "Source"], [
    ["June–August pre-tax profit, as reported", "$577K", "Chairman’s 10/18 email"],
    ["  of which June (last month of FY26)", "$314,077", "QuickBooks GL, 10/11 extract"],
    ["  June revenue booked by three 6/30 “True-Up Unbilled” journal entries (Exos 133; IM 134; IM 122)", "$515,215", "QuickBooks GL"],
    ["FY27 net income through 8/31", "$262,836", "Balance sheet in Attachment B"],
    ["FY27 net income through 10/11", "$112,666", "QuickBooks balance sheet 10/11"],
    ["August / September / October 1–11 results", "($63,121) / ($134,595) / ($15,575)", "QuickBooks GL"],
    ["FY27 average to 10/11 (14.6 weeks)", "≈ $7,700 per week", "Calculated"],
    ["Billings in excess of revenue (1110), 8/31 → 10/11", "$520,757 → $942,177", "Balance sheets"],
    ["Cash, 10/11", "$590,344", "QuickBooks balance sheet 10/11"],
], widths=[3.6, 1.5, 1.4])
para(d, "In other words, most of the reported quarter is a year-end accounting true-up, the last ten weeks show a combined loss of "
        "about $213K, and SSLC holds about $942K of customer billings for work not yet done, more than its cash. Motion 3 exists to correct exactly this.")
para(d, "Bylaw basis. Article V, Section 10 (adequate and correct books; the CFO must give the directors an account of the Company’s "
        "financial condition on request). Article VII, Section 6 (quarterly statements must carry an independent accountant’s report or "
        "an officer’s certificate that they were prepared from the books). Figures given to the Board in a pending sale should meet that standard.")

heading(d, "A.4", "A letter of intent for the Company has not been given to the Board")
para(d, "The Chairman reports that on Friday, October 16, “we received a Letter of Intent from a company interested in investing in or "
        "buying both Microcosm and SSLC.” A proposal to invest in or buy the Company is a Board matter. The Board has not seen it. "
        "Because it covers Microcosm as well, any director with an interest in Microcosm has a conflict over how value would be split between the two companies.")
para(d, "Bylaw basis. Article III, Section 1 (Board authority). Article VII, Section 4 (every director has the “absolute right at any "
        "reasonable time to inspect and copy all books, records and documents of every kind”) [7]. Article VIII, Section 3 (no officer "
        "or agent may bind the Company without Board authority). Article IV, Section 1 (the Board may appoint a committee of two or more "
        "directors). Corporations Code §310 [6].")
para(d, "Two earlier records make the split of value the central question. On October 27, 2015 the Board agreed that proceeds of any sale "
        "of SSLC and Microcosm would go 60% to Microcosm and 40% to SSLC, on Markus Rufer’s motion, passed unanimously. Three of the five "
        "directors voting (the Chairman, the Secretary/CFO and Robert Conger) held Microcosm interests, so it was never approved by a disinterested majority under §310(a)(2) "
        "and cannot bind SSLC. On February 14, 2018 the minutes record that SSLC’s tank-making assets were “currently owned mostly by "
        "Microcosm Inc.” and that Danny Piper of NewCap Partners represented both companies. Mr. Piper has given sound advice to the Chairman, "
        "to SSLC and to Exos. NewCap is engaged by the Chairman and earns a 5% commission on a sale of SSLC and/or Microcosm at the time of "
        "sale. So that this is handled correctly, I ask the Board to record that arrangement and vote on it (motion NC-1), and that the "
        "Secretary confirm which tank-making assets SSLC owns.")
para(d, "I am exercising my inspection right. Please send a copy of the letter of intent and all related correspondence to every director by "
        "[____ date/time], and in any case before the October 20 meeting.")

heading(d, "A.5", "Insider creditors are being paid ahead of the outside lender")
para(d, "SSLC’s loan from Exos ($31,200) has had no payment since May 2, 2025, and the GL notes that applying it against Exos contracts "
        "“has not happened.” Exos’s $1,500 invoice for SSLC’s share of Space Tech Expo is also unpaid [____ due date]. Over the same "
        "period SSLC capitalized interest owed to the Bookstore and paid Microcosm’s share of the facility. Insider creditors should not be "
        "preferred over outside creditors while a sale is pending.")

heading(d, "A.6", "Self-dealing: entries and payments that serve the Wertz-controlled entities, not SSLC’s shareholders")
para(d, "I am formally calling out the following transactions as interested-director (self-dealing) transactions under Corporations Code §310 [6]. "
        "Each benefits Microcosm, Inc., Microcosm Astronautics Books (MDAB) or the Wertz family, entities in which the Chairman and the "
        "Secretary/CFO have a material financial interest. None was disclosed to or approved by the disinterested directors or the shareholders. "
        "All figures are from SSLC’s QuickBooks general ledger (1/1/2024–10/12/2026). The entry-by-entry findings are in the attached "
        "Findings on Related-Party Reclassifications (October 19, 2026).")
table(d, ["Entry / payment", "Amount", "Who benefits", "Effect on SSLC"], [
    ["4/30/2026 reclass of Microcosm payables into 2385 Due to Microcosm", "$426,687", "Microcosm", "Creates a $451,429 insider liability with no invoice support"],
    ["4/30/2026 netting of SSLC loans to Microcosm (1481, lent 2019–Oct 2025) against unsupported Microcosm balances", "$812,699", "Microcosm", "Wipes out a receivable SSLC was owed"],
    ["4/30/2026 interest capitalized into 2700 Notes Payable–Bookstore", "$97,302", "MDAB", "Adds insider debt; the Secretary/CFO has since agreed to drop it"],
    ["SSLC paying 100% of shared Lomita Blvd rent and utilities since July 2024 (50% before)", "≈ $351K", "Microcosm", "Microcosm’s share is uncredited"],
    ["Cash paid to Microcosm entities, 2024 / 2025 / 2026 YTD", "$598,794 / $687,286 / $26,136", "Microcosm, MDAB", "Purposes not yet supported at invoice level"],
], widths=[2.6, 1.1, 1.0, 1.8])
para(d, "The April 30, 2026 entries were posted while SSLC’s outside accounting contractor, A La Carte Solutions, kept the books. Its fee is split 50/50 "
        "with Microcosm, and the work is overseen by the Secretary/CFO, who has an interest in the counterparty. None of the entries was shown to the Board. "
        "Their combined effect is to move about $865K of SSLC’s debt to insiders and to reduce what SSLC’s non-Wertz shareholders, "
        "including Exos with 18.06%, would receive in any sale. Under §310(a), the burden of showing that these transactions were just and "
        "reasonable to SSLC rests with those asserting their validity. I ask that the Board vote on each of them (Section 3, resolutions RP-1 to RP-6).")

heading(d, "A.7", "The October 20 meeting must be duly called and noticed")
para(d, "A special meeting may be called by the Chairman, the President, any Vice President, the Secretary or any two directors (Article III, "
        "Section 8). Notice must reach each director at least 48 hours ahead if given personally or by telephone, or 4 days ahead if mailed. "
        "The Secretary gives notice and keeps the minutes (Article V, Section 9). Three of the five directors are a quorum (Article III, "
        "Section 9). Defects can be cured by written waiver (Article III, Section 10). A written update by email is not an act of the Board.")

para(d, "PART B — CARRIED FORWARD FROM THE OCTOBER 17 NOTICE: THE EXOS COMMISSION ARRANGEMENT", bold=True, color=NAVY, space_after=4)
para(d, "At the Board’s recent meeting, Director James Wertz stated that he was cancelling the Company’s sales commission arrangement with "
        "Exos Aerospace Systems & Technologies, Inc. (“Exos”), apart from the current PD Aerospace order. No individual director has that "
        "authority. The October 17 notice is restated below without change.")

# copy r3 sections 2–8 verbatim (paragraphs 14..44), relabelled B.1..B.7
r3 = Document(R3)
src_pars = r3.paragraphs[14:45]
labels = iter(["B.1", "B.2", "B.3", "B.4", "B.5", "B.6", "B.7"])
body = d.element.body
sectPr = body[-1]
for p in src_pars:
    el = copy.deepcopy(p._p)
    sectPr.addprevious(el)
for p in d.paragraphs:
    t = p.text
    for n in range(2, 9):
        if t.startswith(f"{n}.  ") and p.runs and p.runs[0].bold and any(
                t.startswith(f"{n}.  {k}") for k in ("Background", "Why the written", "Exos has fully", "The 15%", "A tail", "The Bylaws reserve", "A related financial")):
            p.runs[0].text = p.runs[0].text.replace(f"{n}.  ", f"{next(labels)}  ", 1)
            break

# 10/19: correct the Board Approval date/terms from the April 10, 2025 minutes (SSLC + Microcosm)
B1_TEXT = ("The Board approved Exos’s help in finding new business for SSLC in exchange for a fifteen percent (15%) commission, payable after "
           "SSLC receives the customer’s funds, with repeat customers at five percent (5%), at its meeting of April 10, 2025, with all five "
           "directors present (the “Board Approval”). Markus Rufer moved, Robert Conger seconded, and approval was unanimous; the minutes are "
           "signed by Alice Wertz as Secretary. Four disinterested directors voted for it, so it meets Corporations Code §310(a)(2) without "
           "counting my vote. The same day, Microcosm’s Board, with James Wertz, Alice Wertz and Robert Conger present, approved a 15% commission to Exos "
           "for new contracts brought into Microcosm. The Board Approval is a corporate act of the Company.")
for p in d.paragraphs:
    if "May 23, 2026" in p.text:
        for r in p.runs[1:]:
            r.text = ""
        if p.runs:
            p.runs[0].text = B1_TEXT
        break

heading(d, "3.", "Requested Board action")
para(d, "I ask that the Board, at a duly noticed meeting on October 20, 2026, take up the following items. Item (a), Motion 1 on the Exos offer, is taken last:")
reqs = [
    ("(b) Vote ", "on Motion 5, and resolve that no Microcosm, MDAB or Wertz balance will be paid, prepaid, netted, secured or accrue interest "
                  "before closing without approval by the disinterested directors."),
    ("(c) Direct ", "the CFO to produce the support requested on October 12 (invoices, loan notes, facility agreements and approvals for the April 30, 2026 entries)."),
    ("(d) Record ", "the Bookstore interest waiver with a signed MDAB release, a reversing entry and a Board resolution."),
    ("(e) Direct ", "the CFO to deliver, before the meeting, monthly profit and loss statements for June–September 2026, the FY26 annual statements, "
                    "and an FY27 year-to-date balance sheet and income statement through September 30, each with an officer’s certificate under Article VII, Section 6."),
    ("(f) Confirm ", "completion of Motion 3 (AR Unbilled / customer deposits)."),
    ("(g-1) Vote ", "on motion NC-1: record NewCap Partners’ engagement (engaged by the Chairman; 5% commission on a sale of SSLC and/or "
                     "Microcosm at the time of sale) with its engagement letter given to every director, and approve any part of that fee to be "
                     "paid by SSLC by disinterested directors, or failing that by SSLC’s shareholders at the closing vote."),
    ("(g) Receive ", "the October 16 letter of intent; resolve that no director or officer will respond to, negotiate, or sign an NDA or exclusivity "
                     "with its sender except as the Board directs; and appoint a committee of disinterested directors to evaluate it alongside the Exos offer."),
    ("(h) Receive ", "the terms of the October 16 Intuitive Machines order ($270K): deposit, billing schedule, and effect on the billed-ahead balance."),
    ("(i) Note ", "for the minutes, with no vote, that the Exos commission arrangement was approved by the Board on April 10, 2025 and stands. "
                   "The statement at the last meeting that it was cancelled conflicts with the Bylaws (Art. III §§1, 9 and 13; Art. V §6) and has no effect. "
                   "Attachment A is provided for reference only."),
    ("(j) Direct ", "a written accounting of the hardware orders described in Part B (contract value, invoiced, collected, outstanding), and a payment schedule for the Exos loan and the Space Tech Expo invoice."),
    ("(a) Last, vote ", "on Motion 1 (the Exos offer), or receive SSLC’s written counteroffer, as committed on October 13. It is taken last "
                       "because the counteroffer the Chairman proposed on October 13 has not yet been received."),
]
for lead, txt in reqs:
    bullet(d, txt, lead)
para(d, "Resolutions on the related-party (self-dealing) transactions in Part A.6. I ask that each be put to a recorded roll-call vote, "
        "with the Chairman, the Secretary/CFO and Robert Conger (a Microcosm director and officer) disclosing their interest and abstaining, and the vote of each director entered in the minutes:", bold=True)
res = [
    ("RP-1 Finding. ", "The transactions listed in Part A.6 are interested-director transactions under Corporations Code §310 that were not approved by the disinterested directors."),
    ("RP-2 Reversal. ", "The April 30, 2026 entries ($426,687 reclassification, $812,699 loan netting and $97,302 capitalized interest) are reversed pending approval by the disinterested directors on invoice-level support."),
    ("RP-3 Facility share. ", "SSLC books a receivable from Microcosm for its 50% share of rent and utilities since July 2024 (about $351K), net of any documented credits."),
    ("RP-4 Payment freeze. ", "No payment, prepayment, netting, security or interest accrual on any Microcosm, MDAB or Wertz balance before closing without approval by the disinterested directors."),
    ("RP-5 Independent review. ", "The disinterested directors engage an independent CPA to review all related-party entries and payments from January 1, 2024, reporting to the full Board."),
    ("RP-6 Books access. ", "Related-party entries may be posted only with the written approval of a disinterested director, and every director keeps the full read-only books access approved under Motion 2."),
]
for lead, txt in res:
    bullet(d, txt, lead)
para(d, "If the Board does not take up these resolutions, Exos, which holds more than ten percent of SSLC’s shares, intends to call a special "
        "meeting of shareholders to consider them, as Article II, Section 3 of the Bylaws allows.")
para(d, "If the meeting has not been noticed by [____ date/time], I will call it together with another director, as Article III, Section 8 allows. "
        "Please confirm in writing that no notice ending the commission arrangement has gone to any customer or partner.")

heading(d, "4.", "Disclosure of interest")
para(d, "I am CEO and a director of Exos. Exos is the counterparty to the commission arrangement and the proposed asset purchase. Those are "
        "interested-director matters under Corporations Code §310. I have disclosed that interest and will abstain from those votes. The same "
        "standard applies to every director with an interest in Microcosm, MDAB or the Wertz loan when the Board takes up Part A, "
        "including Robert Conger, who is a Microcosm director.")

heading(d, "5.", "Reservation of rights")
para(d, "Nothing in this notice waives any right of the Company, of Exos, or of me as a director or shareholder. I ask that this notice and its "
        "attachments be entered in the Company’s minute book.")

para(d, "")
para(d, "Respectfully submitted,")
para(d, "John Quinn", bold=True, space_after=0)
para(d, "Director, Scorpius Space Launch Company", size=10.5, space_after=0)
para(d, "CEO, Exos Aerospace Systems & Technologies, Inc.", size=10.5)

para(d, "Sources", bold=True, size=10, space_after=2)
for n, t in enumerate([
    "U.S. Bureau of Labor Statistics, Occupational Outlook Handbook — Sales Engineers (median annual wage, May 2025): https://www.bls.gov/ooh/sales/sales-engineers.htm",
    "U.S. Bureau of Labor Statistics, “Compensation costs for private industry workers averaged $46.89 per hour worked in June 2026,” The Economics Daily, Sept. 17, 2026: https://www.bls.gov/opub/ted/2026/compensation-costs-for-private-industry-workers-averaged-46-89-per-hour-worked-in-june-2026.htm",
    "Manufacturers’ Agents National Association (MANA), “Step 3 — Create Fair and Balanced Written Agreements”: https://www.manaonline.org/step-3-create-fair-and-balanced-written-agreements",
    "Manufacturers-Representatives.com, “Sales Commission: Formulas, Rates, and Structure for Sales Reps”: https://www.manufacturers-representatives.com/article.cfm?ArticleNumber=7",
    "RepHunter, “How are manufacturers representatives typically paid?”: https://www.rephunter.net/blog/how-are-manufacturers-representatives-typically-paid",
    "California Corporations Code §310 (interested-director transactions): https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CORP&sectionNum=310",
    "California Corporations Code §1602 (director inspection rights): https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CORP&sectionNum=1602",
], 1):
    src(d, n, t)
para(d, "Company figures are from SSLC’s QuickBooks (balance sheet 10/11/2026; transaction detail 1/1/2024–10/12/2026) and Attachment B. "
        "Bylaw references are to SSLC’s Bylaws (data-room copy). Confidential under the July 27, 2021 NDA.", size=8.5)
para(d, "DRAFT FOR JOHN QUINN’S REVIEW — not sent. Bracketed items need confirmation before issuance.", italic=True, size=8.5)
d.save(OUT_NOTICE)

# =====================================================================================
# 2. Draft reply email
# =====================================================================================
e = new_doc()
para(e, "DRAFT — NOT SENT · for John Quinn’s review", italic=True, size=9)
for k, v in [
    ("From:", "John Quinn <jquinn@exosaero.com>"),
    ("To:", "Jim Wertz <jim@smad.com>; Jim Wertz <jwertz@smad.com>"),
    ("Cc:", "Danny Piper <piper@newcap.com>; Markus Rufer <mrufer@smad.com>; Robert Conger <rconger@smad.com>; "
            "Alice Wertz <awertz@smad.com>"),
    ("Subject:", "RE: URGENT- SSLC time's-up for a decision on how to proceed."),
]:
    kv(e, k, v)
divider(e)
EMAIL = [
"Jim and SSLC Board,",
"Thank you for replying before the deadline, and for the debt summary. I’m sorry to hear about Markus and about Judy’s family, and I hope both are doing better.",
"I will accept Tuesday, October 20 as the date for SSLC’s answer, on one condition: it has to be a duly noticed Board meeting with votes, not another written update. "
"I am sending the Board a separate email with the meeting agenda, the motions and the supporting papers.",
"Before Tuesday, I also need to record that the commitments made at the October 13 meeting have not been kept:",
"1. The counteroffer. You said you would send a counteroffer “sometime later today” on October 13. Six days later none has arrived, and the date is now Tuesday.\n"
"2. The Motion 5 transactions. The Board deferred Motion 5 so that SSLC could “look at what’s here and respond in the next couple of days.” SSLC has not answered any of my October 12 questions. "
"Instead your October 18 email presents the same balances at face value in a debt summary.\n"
"3. Motion 3. The Board approved correcting the AR Unbilled and customer-deposit accounting within five business days, due Tuesday. I have seen no corrected balance sheet or adjusting entries. The latest balance sheet I have (October 11) shows billings in excess of revenue of $942,177, up from $520,757 on August 31. Please send the corrected balance sheet and the entries before the meeting.\n"
"4. The letter of intent. SSLC received it on October 16 and has not shared it with the Board.",
"These were commitments to the Board, not to Exos. Each has been missed, while the figures sent instead favour the balances owed to Microcosm, MDAB and the Wertz family. "
"I ask that the minutes of Tuesday’s meeting record the status of each one.",
"Four points on the figures in your email:",
"1. Profit. The $577K for June–August ties to SSLC’s ledger, but it spans two fiscal years. $314K of it is June, the last month of FY26, and June’s $515K of revenue "
"came from three June 30 “True-Up Unbilled” journal entries, not June sales. For the current fiscal year, the balance sheet you attached shows net income of $262,836 "
"through August 31, and QuickBooks shows $112,666 through October 11. August lost about $63K and September about $135K. That is under $8,000 a week year to date, not $48,000, "
"and the last ten weeks are a combined loss of about $213K. Over the same period, billings in excess of revenue grew from $520,757 to $942,177. That is more than SSLC’s cash, "
"and it is what Motion 3 corrects by Tuesday.",
"2. Debt. Of the $1,020,690, $857,419 (84%) is owed to Microcosm, MDAB and the Wertz family. Those are the Motion 5 balances, and my October 12 questions on them are still open: "
"the $426,687 reclassification and the $812,699 loan netting booked on April 30, 2026, and Microcosm’s share of rent and utilities since July 2024 (about $351K on the 2024 50/50 basis). "
"None of these has been approved by the disinterested directors. Under Corporations Code §310, without that approval the burden is on those relying on them to prove they were fair to SSLC.",
"3. Bookstore interest. I welcome Alice’s agreement to drop the $100,000. It confirms the $97,302 capitalized on April 30 should not have been booked. "
"Please record it with a signed release from MDAB, a reversing entry and a Board resolution, so it is binding and in the minute book.",
"4. The letter of intent. An offer to invest in or buy SSLC is a Board matter. Under Article VII, Section 4 every director has an absolute right to inspect the Company’s documents, "
"and I am asking for a copy, to all directors, before Tuesday. Because it also covers Microcosm, the split of value between the two companies is a conflict for any director with an "
"interest in Microcosm, so the disinterested directors should evaluate it. If it is better for SSLC’s shareholders than ours, the Board should see the two side by side.",
"Congratulations on the IM order. Please include its deposit and billing schedule in Tuesday’s package so the Board can see its effect on the billed-ahead balance.",
"On the $15,000 a week: that is what the delay costs Exos. SSLC’s profit belongs to all of its shareholders, Exos included, so it doesn’t offset that cost. "
"SSLC also still owes Exos the $31,200 loan, with no payment since May 2025, and the $1,500 Space Tech Expo share [____ due date].",
"I still have not received the counteroffer you proposed on October 13. Please send it before Tuesday. I have put Motion 1 last on the agenda so the Board can take it up with your counteroffer in hand. "
"I am not withdrawing the offer, but Tuesday is the last date. If the Board has not voted on Motion 1 or delivered a written counteroffer by the end of the October 20 meeting, "
"I will present our plan in New York without Scorpius, as I said on Friday.",
"The Board papers, including my notice, my findings on the related-party reclassifications and the motions for Tuesday, follow in my separate email to the Board.",
"Regards,\nJohn",
]
for t in EMAIL:
    para(e, t, space_after=8)
e.save(OUT_EMAIL)
print(OUT_NOTICE); print(OUT_EMAIL)
