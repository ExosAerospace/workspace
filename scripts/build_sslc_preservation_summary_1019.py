#!/usr/bin/env python3
"""10/19 drafts for SSLC directors Markus Rufer + Bob Conger to review before Tuesday (amicable track):
(1) Records-preservation request to SSLC + A La Carte Solutions; (2) one-page case summary of the related-party balances.
Figures: SSLC QuickBooks GL 1/1/2024–10/12/2026 + balance sheet 10/11/2026; share counts from the August 2024 register."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

NAVY = RGBColor(0x1F, 0x2A, 0x44)
OUT_PRES = "drafts/SSLC_Records_Preservation_Request_2026-10-19.docx"
OUT_SUM = "drafts/SSLC_RelatedParty_Case_Summary_2026-10-19.docx"


def new_doc(margin=1.0, size=11):
    d = Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Inches(margin); s.top_margin = s.bottom_margin = Inches(0.7)
    d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(size)
    return d


def para(d, t, *, bold=False, italic=False, size=None, after=6, color=None, align=None):
    p = d.add_paragraph(); r = p.add_run(t); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    if color: r.font.color.rgb = color
    if align: p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    return p


def lead(d, label, text, size=None, after=3):
    p = d.add_paragraph(); a = p.add_run(label + " "); a.bold = True
    b = p.add_run(text)
    if size: a.font.size = b.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(after)


# ------------------------------------------------------------------ 1. Preservation request
d = new_doc()
para(d, "DRAFT — for review by Markus Rufer and Robert Conger before issue", italic=True, size=9)
para(d, "REQUEST TO PRESERVE COMPANY RECORDS", bold=True, size=14, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para(d, "Scorpius Space Launch Company (a California corporation)", align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
for k, v in [("TO:", "Alice Wertz, Secretary and Chief Financial Officer, Scorpius Space Launch Company; "
                     "A La Carte Solutions, SSLC’s accounting contractor [attention: ____ engagement lead]"),
             ("CC:", "The Board of Directors of Scorpius Space Launch Company"),
             ("FROM:", "John Quinn, Director"),
             ("DATE:", "October [__], 2026")]:
    lead(d, k, v)
para(d, "")
for t in [
    "The Board is reviewing SSLC’s related-party balances with Microcosm, Inc., Microcosm Astronautics Books (MDAB) and members of the "
    "Wertz family, including the entries dated June 30, 2025 and April 30, 2026. So that the review can be completed on a full and "
    "accurate record, I ask that all of the records below be kept exactly as they are, and not deleted, overwritten, re-dated or edited, "
    "until the Board confirms in writing that the review is finished.",
    "This is a routine step that protects every director and the Company. It is not an accusation against anyone, and it does not stop "
    "normal bookkeeping. New entries can be made as usual; existing ones should be corrected only by a new, dated adjusting entry, so "
    "that the history stays visible.",
]:
    para(d, t)
para(d, "Records to preserve (paper and electronic, including drafts and backups):", bold=True)
for t in [
    "1. The complete QuickBooks Online company file, including the audit log, attachments, and the history of every entry in accounts "
    "1430, 1435, 1480, 1481, 2000 (Microcosm and MDAB vendor records), 2385, 2700, 2701 and 2714, from January 1, 2019.",
    "2. Every invoice, bill, statement or support relied on for the June 30, 2025 entries (JE 25925 and 25926) and the April 30, 2026 "
    "entries (“Loan to Mic”, “Offset AP” and the three vendor credits).",
    "3. All loan agreements, notes, payment records and approvals for amounts lent by SSLC to Microcosm, and lent to SSLC by Microcosm, "
    "MDAB or the Wertz family.",
    "4. The Lomita Blvd lease, any facility or cost-sharing arrangement between SSLC and Microcosm, and rent and utility invoices from 2024.",
    "5. SSLC bank statements from January 1, 2024, and records of every payment to or from a Microcosm entity or the Wertz family.",
    "6. Emails, messages and notes between SSLC, Microcosm, MDAB and A La Carte Solutions about these balances or entries, including "
    "who requested each April 30, 2026 entry.",
    "7. Board and shareholder minutes, consents and the share register, and A La Carte Solutions’ engagement terms with SSLC and with Microcosm.",
]:
    para(d, t, after=3)
para(d, "")
para(d, "Please confirm by reply that these records are being kept. If anything listed has already been changed or deleted, please say "
        "what and when, so the Board has an accurate picture. Thank you for your help with this.")
para(d, "John Quinn\nDirector, Scorpius Space Launch Company")
d.save(OUT_PRES)

# ------------------------------------------------------------------ 2. One-page case summary
d = new_doc(margin=0.75, size=10)
para(d, "SSLC RELATED-PARTY BALANCES — ONE-PAGE SUMMARY", bold=True, size=13, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER, after=0)
para(d, "For the SSLC Board meeting of Tuesday, October 20, 2026 · prepared by John Quinn, Director · draft for Markus Rufer and Robert Conger",
     italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)

para(d, "The issue", bold=True, color=NAVY, after=2)
para(d, "On SSLC’s own books, Microcosm has gone from owing SSLC about $1.16 million to being owed $451,429, a turn of about "
        "$1.6 million in Microcosm’s favour. None of the entries that did this was approved by directors without a stake in Microcosm.", after=4)

para(d, "How it happened (SSLC QuickBooks)", bold=True, color=NAVY, after=2)
for label, t in [
    ("Loans, $812,699.", "SSLC lent Microcosm cash from 2019 to October 2025. The loans were carried in account 1480 “Workman’s Comp "
     "Over/Under”, not as a loan to Microcosm. On April 30, 2026 they were netted to zero against four Microcosm charges with no invoice "
     "support ($294,499, $423,965, $61,290 for “Judy’s time” and $32,946), which add up to exactly $812,699."),
    ("Payable, $451,429.", "The same day, $426,687 of Microcosm bills was moved out of accounts payable into a new account, 2385 Due to "
     "Microcosm, by a vendor credit, which removed the invoice trail. 2026 charges have since brought it to $451,429."),
    ("Building, about $351,000.", "SSLC paid 50% of the shared Lomita Blvd rent and utilities until June 2024 and 100% since. Microcosm’s "
     "half (about $316,000 rent and $35,000 utilities through August 2026) was never charged back."),
    ("Bookstore interest, $97,302.", "Accrued interest was added to the MDAB note principal. Alice has since agreed to drop it."),
]:
    lead(d, label, t, after=2)
para(d, "Booked entries alone: $812,699 + $451,429 = $1,264,128. Adding the unbooked building share gives about $1.6 million.", italic=True, after=4)

para(d, "Why it matters", bold=True, color=NAVY, after=2)
para(d, "About $1.85 per SSLC share (872,489 shares): roughly $292,000 for Exos (18.06%), $168,000 for Markus (91,000 shares) and $54,000 "
        "for Bob (29,000 shares). To my knowledge Microcosm has had no revenue for at least two years, so it could not have funded the "
        "“reimbursables” used to cancel SSLC’s loans unless the money came from SSLC or its owners.", after=4)

para(d, "The rule", bold=True, color=NAVY, after=2)
para(d, "A transaction between SSLC and a company in which a director has a material financial interest, or on whose board a director "
        "sits, stands only if disinterested directors or shareholders approve it after full disclosure, or if it is proven just and "
        "reasonable to SSLC (Corporations Code §310). Jim and Alice Wertz (about 71% of Microcosm between them) and Bob Conger (a "
        "Microcosm director with 7.81%) are interested; their votes on these items cannot be counted. Markus’s 15 Microcosm shares (0.78%) "
        "are not material. John Quinn has no interest in Microcosm.", after=4)

para(d, "The fix proposed for Tuesday", bold=True, color=NAVY, after=2)
para(d, "RP-1 record the finding · RP-2 reverse the April 30 entries pending invoice support · RP-3 book Microcosm’s building share as a "
        "receivable, net of documented credits · RP-4 no insider payments before closing without disinterested approval · RP-5 independent "
        "CPA review of every related-party entry since January 2024 · RP-6 related-party entries only with a disinterested director’s "
        "written approval. Some Microcosm charges may prove legitimate; these steps simply require that each be supported before SSLC "
        "gives up the money.", after=4)

para(d, "If it is not fixed", bold=True, color=NAVY, after=2)
para(d, "The aim is to settle this inside the Board. If the Board cannot, the Corporations Code gives shareholders further routes: a "
        "shareholders’ meeting (any holder of 10% may call one), a claim on SSLC’s behalf to undo the transactions (§800), and court "
        "removal of a director for gross abuse of authority (§304). Exos would much rather not use them.", after=4)

para(d, "Support available", bold=True, color=NAVY, after=2)
para(d, "Every figure can be checked in the SSLC Board Books page in Mission Control (general ledger and balance sheet). As the Board agreed, "
        "directors with issues on the deposit and billing correction can call Paula Lessnick of BBSNV, Exos’s accounting firm; she "
        "works for Exos, so her view is a second opinion and not the independent review in RP-5.", after=2)
para(d, "Not legal advice. Sources: SSLC QuickBooks GL 1/1/2024–10/12/2026 and balance sheet 10/11/2026; Microcosm stock distribution; "
        "Cal. Corp. Code §§304, 310, 800.", italic=True, size=8)
d.save(OUT_SUM)
print(OUT_PRES); print(OUT_SUM)
