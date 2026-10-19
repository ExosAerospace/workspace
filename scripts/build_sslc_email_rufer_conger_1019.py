#!/usr/bin/env python3
"""10/19 draft: John → Markus Rufer + Bob Conger explaining the ~$1.6M Microcosm swing before Tuesday's vote.
Figures: SSLC QuickBooks GL 1/1/2024–10/12/2026 + balance sheet 10/11/2026; Jim Wertz debt summary 8/31/2026;
share counts from the August 2024 SSLC register (872,489 shares)."""
from docx import Document
from docx.shared import Pt, Inches

OUT = "drafts/SSLC_Email_to_Rufer_Conger_Microcosm_Swing_2026-10-19.docx"
d = Document()
for s in d.sections:
    s.left_margin = s.right_margin = Inches(1)
d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)


def para(t, *, bold=False, italic=False, size=11, after=8):
    p = d.add_paragraph(); r = p.add_run(t); r.bold = bold; r.italic = italic; r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(after)


para("DRAFT — NOT SENT · for John Quinn’s review", italic=True, size=9)
for k, v in [("From:", "John Quinn <jquinn@exosaero.com>"),
             ("To:", "Markus Rufer <mrufer@smad.com>; Robert Conger <rconger@smad.com>"),
             ("Subject:", "Before Tuesday: how SSLC went from being owed $1.16M by Microcosm to owing it $451K")]:
    p = d.add_paragraph(); a = p.add_run(k + "  "); a.bold = True; p.add_run(v); p.paragraph_format.space_after = Pt(2)
para("—" * 40)

for t in [
    "Markus and Bob,",
    "I would like us to settle this amicably, inside the Board, and move on. Nothing here is meant as an attack on Jim or Alice; the goal "
    "is clean books that every shareholder can rely on, which any buyer, including Exos, will insist on anyway.",
    "Before Tuesday’s vote on fixing the related-party entries, I want you to have the full picture in one place. The short version: "
    "on SSLC’s own books, Microcosm has gone from owing SSLC about $1.16 million to being owed about $451,000. That is a turn of about "
    "$1.6 million in Microcosm’s favour, and every dollar of it comes out of what SSLC’s shareholders, including both of you, would "
    "receive in any sale. Here is how it adds up. Every figure is from SSLC’s QuickBooks, which you can now open yourselves in the SSLC "
    "Board Books page in Mission Control (login instructions emailed to each of you on October 19).",

    "1. What Microcosm owed SSLC: about $1.16 million",
    "a) Loans: $812,699. Between January 2019 and October 2025, SSLC lent Microcosm cash dozens of times, in amounts from $4,000 to "
    "$104,308. Until this year those loans were not recorded as a loan to Microcosm. They sat in account 1480, “Workman’s Comp "
    "Over/Under”, so they never appeared on SSLC’s balance sheet as money Microcosm owed.\n"
    "b) Microcosm’s share of the building: about $351,000. Until June 2024, SSLC and Microcosm split the Lomita Blvd rent and utilities "
    "50/50. From July 2024, SSLC has paid 100%, and Microcosm’s half was never charged back. Through August 2026 that is about $316,000 "
    "of rent and $35,000 of utilities. None of it is on the books.\n"
    "Together: $812,699 + about $351,000 = about $1.16 million owed to SSLC.",

    "2. What happened to it",
    "a) The loans were cancelled. On April 30, 2026, an entry moved the loans into a new account, 1481 Loan to Microcosm, and in the same "
    "entry netted them to zero against Microcosm’s own charges: $294,499 and $423,965 of “intercompany” and “pre-6/2025 reimbursable” "
    "balances (first booked at June 30, 2025), $61,290 for “Judy’s time” and a $32,946 “reimbursables” credit. Those four amounts add up to "
    "exactly $812,699. None of them has invoice-level support, and the Board never approved netting them.\n"
    "b) A payable was created. The same day, $426,687 of Microcosm bills was moved out of accounts payable into a new account, 2385 Due to "
    "Microcosm, which removed the invoice trail. Another $24,742 of 2026 Microcosm charges has been added since, so the balance on "
    "SSLC’s books at October 11 is $451,429. (Jim’s October 18 debt summary shows $447,900 as of August 31.)\n"
    "c) The building share was never booked, so it stays at zero.",

    "3. The result",
    "Before: Microcosm owed SSLC about $1.16 million.\n"
    "After: SSLC owes Microcosm $451,429.\n"
    "The turn: $1.16 million + $451,429 = about $1.6 million in Microcosm’s favour.",
    "My written findings to the Board show about $1.26 million. That is the same calculation without the building share, because the "
    "findings cover only entries actually posted in QuickBooks: $812,699 + $451,429 = $1,264,128. Adding the unbooked building share of "
    "about $351,000 gives the $1.6 million.",

    "4. What it means for each of us",
    "SSLC has 872,489 shares on the August 2024 register, so $1.6 million is about $1.85 a share. On that basis the turn costs Exos "
    "(18.06%) about $292,000, Markus (91,000 shares) about $168,000 and Bob (29,000 shares) about $54,000. It also matters because, as far "
    "as I know, Microcosm has had no revenue for at least two years. A company with no revenue could not have paid the “reimbursables” "
    "used to cancel SSLC’s loans unless the money came from SSLC or from its owners.",

    "5. What I am asking the Board to vote on Tuesday",
    "Motions 2, 3 and 4 were approved on October 13 and are not up for a vote again; Tuesday covers only their status. The new votes "
    "are six resolutions on the related-party entries, RP-1 to RP-6:",
    "RP-1: record that these are related-party transactions the disinterested directors never approved.\n"
    "RP-2: reverse the April 30 entries, so the $812,699 goes back on the books as owed by Microcosm until each offset is supported by "
    "invoices and approved.\n"
    "RP-3: book Microcosm’s half of the building, about $351,000, as a receivable, less any credits Microcosm can document.\n"
    "RP-4: no payments to Microcosm, the Bookstore or the Wertz family before closing without disinterested approval.\n"
    "RP-5: an independent CPA reviews every related-party entry since January 2024.\n"
    "RP-6: related-party entries are posted only with a disinterested director’s written approval.",
    "Some of Microcosm’s charges may turn out to be legitimate. The point of these motions is that SSLC should not give up $1.6 million "
    "until each one is supported and approved by directors who have no stake in Microcosm.",
    "Bob, I want to be direct about your vote. You are a Microcosm director and hold 150 of its 1,920 shares (7.81%). Under Corporations "
    "Code §310, that means your vote cannot be counted on any of these Microcosm items, including RP-1 to RP-6 and Motion 5. I ask that you "
    "disclose your Microcosm interest at the start of the meeting and abstain on those items, as Jim and Alice should. It is not a "
    "judgment on you; it is what keeps Tuesday’s votes from being challenged later. Markus, your 15 Microcosm shares (0.78%) are not a "
    "material interest; please disclose them, and your vote counts. The attached motions paper sets this out item by item.",
    "Two attachments are for your review before they go to the full Board: a one-page summary of the issue, and a short request "
    "that SSLC and A La Carte Solutions preserve the relevant records while the Board reviews them. The preservation request is "
    "routine and does not stop normal bookkeeping; please tell me if you would change anything in either.",
    "As the Board agreed on October 13, if you have issues with the deposit and billing correction, Paula Lessnick of BBSNV, "
    "Exos’s accounting firm, is available for a call. She works for Exos, so take her view as a second opinion rather than the "
    "independent review in RP-5. Just tell me and I will set it up.",
    "I am also happy to get on a call myself to walk through any of the entries.",
    "Regards,\nJohn",
    "John Quinn\nDirector, Scorpius Space Launch Company",
]:
    bold = t[:2] in ("1.", "2.", "3.", "4.", "5.") and len(t) < 80
    para(t, bold=bold)
para("Attachments: SSLC_RelatedParty_Case_Summary_2026-10-19.docx; SSLC_Records_Preservation_Request_2026-10-19.docx (draft for your review); SSLC_RelatedParty_Reclass_Findings_2026-10-19.docx; SSLC_Board_Motions_Voting_Eligibility_2026-10-19.docx", italic=True, size=9)
d.save(OUT); print(OUT)
