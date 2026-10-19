#!/usr/bin/env python3
"""SSLC Board motions for 10/20/2026 — plain-English description + voting eligibility per motion (John Quinn, director)."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = "drafts/SSLC_Board_Motions_Voting_Eligibility_2026-10-19.docx"
NAVY = RGBColor(0x1F, 0x2A, 0x44)
RED = RGBColor(0x9C, 0x1C, 0x1C)

d = Document()
for s in d.sections:
    s.left_margin = s.right_margin = Inches(1)
    s.top_margin = s.bottom_margin = Inches(0.9)
d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)


def para(text="", *, bold=False, italic=False, size=11, align=None, after=6, color=None):
    p = d.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic; r.font.size = Pt(size)
    if color: r.font.color.rgb = color
    if align: p.alignment = align
    p.paragraph_format.space_after = Pt(after); return p


def lead(label, text, color=None):
    p = d.add_paragraph(); a = p.add_run(label + "  "); a.bold = True
    if color: a.font.color.rgb = color
    p.add_run(text); p.paragraph_format.space_after = Pt(4); p.paragraph_format.left_indent = Inches(0.2)


def motion(num, title, what, cannot, why, math, ask):
    p = d.add_paragraph(); r = p.add_run(f"{num}  {title}"); r.bold = True; r.font.size = Pt(12); r.font.color.rgb = NAVY
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(4); p.paragraph_format.keep_with_next = True
    lead("What it means.", what)
    lead("Who cannot vote.", cannot, RED)
    lead("Why.", why)
    if math: lead("Vote needed.", math)
    lead("Motion.", ask)


para("SSLC BOARD — MOTIONS AND VOTING ELIGIBILITY", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY, after=2)
para("Special meeting of the Board of Directors, Tuesday, October 20, 2026", align=WD_ALIGN_PARAGRAPH.CENTER, after=2)
para("Prepared by John Quinn, Director · October 19, 2026", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)

p = d.add_paragraph(); r = p.add_run("The rules that decide who votes"); r.bold = True; r.font.size = Pt(12); r.font.color.rgb = NAVY
lead("Interested director.", "A director is “interested” in a transaction between SSLC and the director, or between SSLC and a company "
     "in which the director has a material financial interest. Corporations Code §310(a) [1].")
lead("Common director.", "A director who also sits on the board of the other company is a “common director.” For a transaction between "
     "SSLC and that company, the Board must approve it “by a vote sufficient without counting the vote of the common director,” or the "
     "shareholders must approve it (§310(b)(1)) [1]. A common directorship alone is not a material financial interest, but an officer’s "
     "salary or a shareholding in the other company can be.")
lead("How an interested transaction is approved.", "Either (1) the shareholders approve it after full disclosure, with the interested "
     "director’s shares not voting (§310(a)(1)); or (2) the Board approves it after full disclosure, in good faith, “by a vote sufficient "
     "without counting the vote of the interested director or directors,” and it is just and reasonable to SSLC (§310(a)(2)). Otherwise "
     "whoever relies on it must prove it was just and reasonable to SSLC (§310(a)(3)) [1].")
lead("Quorum.", "Interested directors still count toward the quorum (§310(c)) [1]. Three of the five directors are a quorum, and an act "
     "of the Board is a majority of the directors present at a meeting with a quorum (Bylaws Art. III §9).")
lead("Duty of loyalty.", "Every director must act in good faith and in the best interests of SSLC and its shareholders (§309(a)) [2]. "
     "Where §310 does not strictly take away a vote (for example, a corrective motion), a director with a personal stake should still "
     "abstain. If an interested director votes a corrective motion down, that vote is itself an interested act open to challenge.")
lead("Who is interested in what.", "The Microcosm directors present at its April 10, 2025 Board meeting were James Wertz (Chairman), "
     "Alice Wertz and Robert Conger (Microcosm minutes). Alice Wertz is Microcosm’s majority stockholder and CFO, and the Microcosm key "
     "personnel bios list Robert Conger as its Executive Vice President. So three of SSLC’s five directors sit on Microcosm’s Board. To my "
     "knowledge Microcosm has had no revenue to pay anyone for at least two years, so these conflicts arise from directorship and ownership, "
     "not salary; under §310(b) a common director’s vote does not count either way. On Microcosm, MDAB and Wertz matters, James Wertz, Alice Wertz "
     "and Robert Conger are all conflicted. John Quinn is interested in Exos matters (Exos is the buyer, the commission counterparty, a "
     "customer and a creditor). Markus Rufer is not a Microcosm director and, with Microcosm paying no one, draws no Microcosm pay. He holds "
     "15 of Microcosm’s 1,920 shares (0.78%). §310(a) applies only to a material financial interest, and 0.78% is not material. He should "
     "disclose the holding in the minutes before each Microcosm vote; with that disclosure his vote counts.")
lead("Who owns Microcosm.", "Of Microcosm’s 1,920 shares (Microcosm stock distribution): Alice Wertz 970 (50.52%), James Wertz 390 (20.31%), "
     "Cheryl Wertz 30 and Laura Koerner 30 (1.56% each), so the Wertz family holds about 74%. Robert Conger holds 150 (7.81%), a material "
     "financial interest as well as his directorship, so §310(a) applies to him, not only §310(b). Judy Masukawa, whose time Microcosm bills "
     "to SSLC, holds 35 (1.82%). Microcosm in turn holds 280,000 SSLC shares, so the Wertz family also controls that SSLC vote.")
lead("Vote math when all five attend.", "Majority of five present = 3. On Microcosm matters only John and Markus are free to vote: 2, one short. "
     "The Board therefore cannot validly approve any SSLC–Microcosm transaction (§310(a)(2), §310(b)(1)), and every such balance stays "
     "unapproved, with the burden of proving fairness on whoever relies on it (§310(a)(3)). On Exos matters John is out, and Markus + Robert "
     "= 2, so one Wertz vote is needed or the §310(a)(3) fairness route applies.")
lead("Why that matters.", "On corrective motions (RP-1 to RP-6) the three Microcosm directors could still outvote John and Markus 3–2. "
     "If they do, each of them is voting to protect a company they run, which §309(a) does not permit [2]. The minutes must record each "
     "director’s interest and vote. A block leaves the transactions unapproved and moves the question to SSLC’s shareholders (Bylaws Art. II §3).")

para("PART 1 — MOTIONS FROM OCTOBER 13 (Motions 2–4 were approved then and need no new vote; Motion 5 was deferred to this meeting; Motion 1 is taken last, in Part 4)", bold=True, color=NAVY, after=2)
motion("Motion 2.", "Read-only access to SSLC’s books for every director",
       "Approved October 13. Every director gets full read-only access to SSLC’s books so the Board can check the figures it is given. Because "
       "QuickBooks seats are limited, the Board agreed it would be provided through Exos Mission Control. Access was established through "
       "Mission Control on October 19, 2026: Markus Rufer and Robert Conger were each emailed their login instructions that day and can "
       "open SSLC’s general ledger, balance sheet and records directly. Mission Control is also the platform Exos is using for the Motion 4 "
       "ERP/MRP, inventory and purchasing evaluation, so the same access supports that review.",
       "No one. The access applies to all directors equally, and no director has a financial stake in it.", "§310 does not apply.",
       None, "No vote: approved October 13. Status only: done; access established through Mission Control and login emails sent October 19.")
motion("Motion 3.", "Correct the AR Unbilled / customer-deposit accounting",
       "Approved October 13, due October 20. SSLC bills about 40% at the start of each tank and does not close those billings against "
       "the final invoice. Billings in excess of revenue (1110) grew from $520,757 (8/31) to $942,177 (10/11), more than SSLC’s $590,344 "
       "of cash. The correction shows how much of the reported profit is real.",
       "No one on the motion as a whole. John should abstain on any adjustment to Exos’s own orders (for example, the 6/30 “True-Up "
       "Unbilled” entry on Exos order 133).",
       "Exos is a customer, so a change to an Exos balance is an interested matter for John under §310(a) [1].",
       None, "No vote: approved October 13. Status only: confirm completion, with the adjusting entries and the restated 1110 balance.")
motion("Motion 4.", "ERP / MRP system evaluation",
       "Approved October 13. Exos evaluates an ERP/MRP system for SSLC at no cost to SSLC, using Exos Mission Control (ERP/MRP, inventory, "
       "purchasing, job costing), the same system through which the Motion 2 books access was established. No status vote is needed.",
       "John Quinn, on any later decision to buy or license a system Exos recommends or supplies.",
       "A purchase or license involving Exos would be an interested transaction under §310(a) [1].",
       None, "No vote: approved October 13. Status only.")
motion("Motion 5.", "Related-party balances ($857,419 owed to Microcosm, MDAB and the Wertz family)",
       "Of SSLC’s $1,020,690 of debt, $857,419 (84%) is owed to companies or family members of two directors: Microcosm ($447,900), MDAB "
       "($317,019) and the Wertz family ($92,500). Most of it was created by bookkeeping, not borrowing. On April 30, 2026, $426,687 of "
       "Microcosm bills was moved out of accounts payable into a new “Due to Microcosm” account with no invoice trail. The same day, "
       "$812,699 that SSLC had lent Microcosm since 2019 was cancelled against Microcosm’s own unsupported “reimbursable” charges. Since "
       "July 2024, SSLC has paid 100% of the shared building’s rent and utilities without charging Microcosm its former 50% share, about "
       "$351K. Before these entries, Microcosm owed SSLC about $1.16M (loans plus facility share). After them, SSLC owes Microcosm about $448K.",
       "James Wertz, Alice Wertz and Robert Conger.",
       "Microcosm and MDAB are companies in which Jim and Alice have a material financial interest, and the Wertz loan is theirs directly. "
       "Robert Conger is a Microcosm director holding 7.81% of its shares (§310(a)–(b)) [1]. Approving "
       "these balances is an interested-director transaction under §310(a) [1]. It is valid only if approved by the disinterested directors "
       "“without counting the vote of the interested director or directors” (§310(a)(2)), or by shareholders with the interested directors’ "
       "shares not voting (§310(a)(1)). None of that has happened, so under §310(a)(3) the burden is on the Wertz side to prove the balances "
       "are just and reasonable to SSLC.",
       "John + Markus = 2 of the 3 needed. The Board cannot approve these balances; only SSLC’s shareholders can, with the interested "
       "directors’ shares not voting (§310(a)(1)).",
       "Do not accept the related-party balances as stated until invoice-level support is produced and the disinterested directors approve them.")

para("PART 2 — RESOLUTIONS ON THE SELF-DEALING ENTRIES (NOTICE PART A.6)", bold=True, color=NAVY, after=2)
para("For each of RP-1 to RP-6: James Wertz, Alice Wertz and Robert Conger should not vote. These resolutions concern transactions with "
     "Microcosm, MDAB and the Wertz family. Jim and Alice have a material financial interest (§310(a)), and Robert Conger is a Microcosm "
     "director and officer (§310(b)). The resolutions are corrective, not approvals, so their duty of loyalty under §309(a) requires them to "
     "abstain [1][2]. If all three abstain, John + Markus = 2 of the 3 present, a majority. If they vote them down 3–2, the minutes must record "
     "each interest, the transactions stay unapproved, and Exos takes the resolutions to a shareholders’ meeting.",
     italic=True)
motion("RP-1.", "Formal finding",
       "The Board records, as a matter of fact, that the April 30, 2026 entries, the unpaid facility share and the insider loan repayments "
       "are interested-director transactions that no disinterested director approved. This is the official call-out.",
       "James Wertz, Alice Wertz and Robert Conger.", "§310(a)–(b) [1]; §309(a) [2].", None,
       "Find that the transactions in Part A.6 are interested-director transactions not approved under §310.")
motion("RP-2.", "Reverse the April 30, 2026 entries",
       "Undo the $426,687 move into “Due to Microcosm”, the $812,699 loan netting and the $97,302 of interest added to the Bookstore note. "
       "The loan to Microcosm goes back on the books as money Microcosm owes SSLC until each offset is supported by invoices and approved.",
       "James Wertz, Alice Wertz and Robert Conger.", "§310(a)–(b) [1]. Offsetting also requires determinable amounts and an enforceable right of setoff "
       "(ASC 210-20-45-1) [3].", None, "Direct the reversal of the April 30, 2026 entries pending disinterested approval.")
motion("RP-3.", "Charge Microcosm its share of the building",
       "Book a receivable from Microcosm for 50% of rent and utilities since July 2024, about $351K (rent ~$316K, utilities ~$35K), "
       "net of any credits Microcosm can document.",
       "James Wertz, Alice Wertz and Robert Conger.", "§310(a)–(b) [1].", None, "Direct the CFO to book the Microcosm facility receivable.")
motion("RP-4.", "Freeze insider payments",
       "No payment, prepayment, netting, security or interest on any Microcosm, MDAB or Wertz balance before closing without disinterested "
       "approval. In 2026 SSLC repaid Microcosm $90,000 (5/26) and $64,150 (8/13) while the Exos loan received nothing.",
       "James Wertz, Alice Wertz and Robert Conger.", "§310(a)–(b) [1]; §309(a) [2].", None, "Adopt the freeze.")
motion("RP-5.", "Independent CPA review",
       "The disinterested directors hire an independent CPA to review every related-party entry and payment since January 1, 2024. "
       "SSLC’s current accounting contractor, A La Carte Solutions, has its fee split 50/50 with Microcosm, so it is not independent.",
       "James Wertz, Alice Wertz and Robert Conger.", "§310(a)–(b) [1]; §309(a) [2].", None,
       "Authorize Markus Rufer and John Quinn, the two directors who do not sit on Microcosm’s Board, to engage the CPA and receive its report for the full Board.")
motion("RP-6.", "Posting controls",
       "Related-party entries may be posted only with written approval from a disinterested director, and every director keeps the "
       "read-only access approved under Motion 2.",
       "James Wertz, Alice Wertz and Robert Conger.", "§310(a)–(b) [1].", None, "Adopt the posting control.")

para("PART 3 — OTHER ITEMS FROM THE OCTOBER 19 NOTICE", bold=True, color=NAVY, after=2)
motion("Item (d).", "Record the $100,000 Bookstore interest waiver",
       "Alice Wertz agreed to drop the $100,000 of interest SSLC owes the Bookstore (MDAB). It benefits SSLC, but it must be made binding: "
       "a signed release from MDAB, a reversing entry for the $97,302 capitalized on April 30, and a Board resolution in the minute book.",
       "James Wertz, Alice Wertz and Robert Conger.", "It is a transaction between SSLC and MDAB, a Wertz/Microcosm affiliate (§310(a)–(b)) [1].",
       "John + Markus = 2 of the 3 needed. Because the waiver only benefits SSLC, record it by a signed MDAB release and reversing entry, "
       "then have the shareholders ratify it with the other items.", "Accept the waiver and direct the release, reversing entry and resolution.")
motion("Item (g).", "The October 16 letter of intent for SSLC and Microcosm",
       "A third party has proposed to invest in or buy both SSLC and Microcosm. The Board has not seen it. Because it covers both companies, "
       "how the price is split between them decides what SSLC’s shareholders get. Two earlier records make that split the central issue. "
       "(1) On October 27, 2015 the Board, on Markus Rufer’s motion and with James Wertz, Alice Wertz and Robert Conger voting, agreed that proceeds of any sale of the two "
       "companies would be split 60% to Microcosm and 40% to SSLC. Only two of the five directors present (Markus Rufer and Jack Kulpa) had no "
       "Microcosm interest, so that agreement was never approved under §310(a)(2) and cannot bind SSLC now. (2) On February 14, 2018 the "
       "minutes record that SSLC’s tank-making assets were “currently owned mostly by Microcosm Inc.” and that Danny Piper of NewCap Partners "
       "represented both SSLC and Microcosm (NewCap’s 2014 engagement fee was also split 50/50 between them). Today NewCap works for "
       "James Wertz and earns a 5% commission on a sale of SSLC and/or Microcosm at the time of sale. Mr. Piper has given sound advice to "
       "Jim, to SSLC and to Exos; motion NC-1 records the arrangement so it is handled correctly.",
       "James Wertz, Alice Wertz and Robert Conger (Microcosm is part of the deal and they control it). John Quinn should also abstain, "
       "because Exos is a competing bidder.",
       "§310(a)–(b) [1] for the three Microcosm directors; §309(a) duty of loyalty [2] for John as a competing bidder. Bylaws Art. IV §1 "
       "lets the Board appoint a committee of two or more directors, so a committee needs two directors, and only Markus Rufer is free of both conflicts.",
       "Appointing the committee needs a resolution by a majority of the authorized number of directors, 3 of 5 (Bylaws Art. IV §1). "
       "Appointing a committee is not itself a transaction with any director, so all five may vote on that resolution after stating their "
       "interests. Only the evaluation itself excludes interested directors.",
       "Receive the LOI; resolve that the October 27, 2015 60/40 split does not bind SSLC; confirm in writing which tank-making assets SSLC owns; engage an independent "
       "financial adviser, reporting to Markus Rufer and to the full Board, to compare the LOI with the Exos offer and allocate value between "
       "SSLC and Microcosm; no director or officer may respond to, negotiate or sign an NDA or exclusivity with its sender except as the Board "
       "directs; any acceptance goes to SSLC’s shareholders, with interested directors’ shares not voting.")
motion("NC-1.", "NewCap Partners’ engagement",
       "Danny Piper of NewCap Partners has given sound advice to Jim, to SSLC and to Exos. NewCap is engaged by James Wertz and earns a 5% "
       "commission on a sale of SSLC and/or Microcosm at the time of sale. That arrangement has not been put before SSLC’s Board. Recording "
       "it now, with the engagement letter in the minute book, means everyone knows who engaged NewCap, how it is paid and which company "
       "bears the fee, and protects the sale from a later challenge.",
       "Part (a), recording the disclosure: no one; it is not a transaction. Part (b), approving any fee SSLC would pay: James Wertz (NewCap’s "
       "client) and Alice Wertz and Robert Conger (the fee also covers a sale of Microcosm), and John Quinn (Exos is the buyer whose purchase "
       "would trigger the fee).",
       "Part (b) is a transaction in which those directors have an interest (§310(a)–(b)) [1]. Markus Rufer is the only director with no "
       "interest in it.",
       "Part (a): simple majority of directors present. Part (b): one disinterested vote is not a Board majority, so the Board should record "
       "Markus’s view and refer the approval of any SSLC-paid fee to SSLC’s shareholders with the sale, interested directors’ shares not "
       "voting (§310(a)(1)).",
       "(a) Record that NewCap Partners is engaged by James Wertz and earns a 5% commission on a sale of SSLC and/or Microcosm at the time "
       "of sale, and enter its engagement letter (showing which company pays) in the minute book. (b) Any portion of that fee to be paid by "
       "SSLC is approved only by disinterested directors or by SSLC’s shareholders as part of the sale approval.")
motion("Item (i).", "The Exos 15% sales-commission arrangement",
       "At its April 10, 2025 meeting, with all five directors present, SSLC’s Board accepted an offer that Exos help find new business for "
       "a 15% commission, payable after SSLC receives the customer’s funds, with repeat customers at 5% and a shared contact list to avoid "
       "double payment. Markus Rufer moved, Robert Conger seconded, and approval was unanimous (minutes signed by Alice Wertz, Secretary). "
       "Microcosm’s Board (Jim, Alice and Bob) approved the same 15% commission for new contracts Exos brings to Microcosm that day, on "
       "Alice’s motion. James Wertz later said he was cancelling it. Only the Board can change a Board-approved arrangement (Bylaws Art. III §1, Art. VIII §3).",
       "John Quinn.", "Exos is the counterparty (§310(a)) [1]. The April 10, 2025 approval already meets §310(a)(2): four disinterested "
       "directors voted for it, more than the three needed without counting John.",
       "No new vote is needed for the arrangement to stand. Any change needs a Board vote: Markus + Robert = 2 of the 3 needed if all five "
       "attend, and John cannot vote.",
       "Confirm that the April 10, 2025 approval stands and that no single director or officer can cancel it; and vote on adopting the written "
       "agreement (Attachment A), conformed to the approved terms (15% new business, 5% repeat customers, paid on receipt of funds), with the "
       "12-month tail and reimbursement of Exos’s SSLC-specific sales costs.")
motion("Item (j).", "Exos loan and Space Tech Expo invoice payment schedule",
       "SSLC owes Exos $31,200 of loan principal plus interest, with no payment since May 2, 2025, and $1,500 for SSLC’s share of Space Tech Expo.",
       "John Quinn.", "Exos is the creditor (§310(a)) [1].", "Markus + Robert = 2 of the 3 needed if all five attend.",
       "Adopt a payment schedule for the Exos loan and the Space Tech Expo invoice.")
motion("Items (c), (e), (h) and (j, part 1).", "Directions to the CFO and information items",
       "(c) produce the October 12 support for the April 30 entries; (e) monthly P&L June–September 2026, FY26 statements and FY27 "
       "year-to-date statements with an officer’s certificate (Bylaws Art. VII §6); (h) terms of the $270K Intuitive Machines order; "
       "(j) an accounting of hardware orders (contract value, invoiced, collected, outstanding).",
       "No one on (e), (h) and (j). On (c), James Wertz, Alice Wertz and Robert Conger should abstain.",
       "(e), (h) and (j) are information duties owed to every director (Bylaws Art. V §10, Art. VII §4). Item (c) concerns the support for "
       "transactions in which the Microcosm directors are interested (§310(a)–(b), §309(a)) [1][2].",
       None, "Direct the CFO to deliver each item by a stated date.")

para("PART 4 — LAST ITEM: MOTION 1, THE EXOS OFFER (SSLC’s written counteroffer not yet received)", bold=True, color=NAVY, after=2)
motion("Motion 1.", "Exos offer, §3 exclusivity and right of first refusal",
       "Exos has offered to buy SSLC on the Heads of Terms circulated October 12. Motion 1 asks the Board to accept the offer, confirm "
       "exclusivity under §3 while the asset purchase agreement is negotiated, and grant Exos a six-month right of first refusal that "
       "extends automatically during negotiation. On October 13 the Board deferred it, and SSLC committed to a vote or a written "
       "counteroffer by October 20. It is the last item on the agenda because, as of October 19, John has not received the "
       "counteroffer the Chairman proposed on October 13.",
       "John Quinn.",
       "Exos is the buyer. John is CEO and a director of Exos, so this is an interested-director transaction under §310(a) [1]. "
       "James Wertz, Alice Wertz and Robert Conger are not parties to the Exos offer, but Microcosm has a stake in its terms (the sale exclusions "
       "Microcosm retains, discussed April 10, 2025) and in the competing October 16 letter of intent, which covers Microcosm too. Each should "
       "disclose that interest before voting.",
       "Markus + Robert = 2 of the 3 needed if all five attend. If the motion fails without a Wertz vote, Exos may rely on §310(a)(3) "
       "and the Eqvista fairness opinion.",
       "Approve the Exos offer, confirm §3 exclusivity, and grant the ROFR; or record SSLC’s written counteroffer.")
para("")
para("If the Board does not act on these items, Exos, which holds 18.06% of SSLC’s shares, intends to call a special meeting of "
     "shareholders under Bylaws Art. II §3 (10% threshold). At that meeting, on any approval of Microcosm, MDAB or Wertz transactions, "
     "the interested directors’ shares do not vote (§310(a)(1)) [1]. Whether Microcosm’s own 280,000 shares may vote on a Microcosm "
     "transaction, given that its majority holder is an interested director, is a question for Counsel.")
para("This is a summary for the Board’s use, not legal advice. Bracketed items need confirmation before issuance.", italic=True, size=9)
para("Sources", bold=True, after=2)
for s in ["[1]  California Corporations Code §310 (FindLaw, current through Jan. 1, 2026): https://codes.findlaw.com/ca/corporations-code/corp-sect-310",
          "[2]  California Corporations Code §309(a) (Loeb & Loeb, Corporation Law: California, 2024): https://www.loeb.com/-/media/files/pdfs/2024-pdfs/other/corporation-law-california-(95171209).pdf",
          "[3]  ASC 210-20-45-1, right of setoff (PwC Viewpoint): https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/financial_statement_/financial_statement___18_US/chapter_2_balance_sh_US/24_balance_sheet_off_US.html",
          "SSLC minutes February 11, 2013 – August 14, 2018 (incl. 10/27/2015 and 2/14/2018); Microcosm stock distribution; SSLC and Microcosm Board minutes of April 10, 2025; Microcosm key personnel bios; SSLC Bylaws (June 2000); SSLC QuickBooks (GL 1/1/2024–10/12/2026; balance sheet 10/11/2026); data-room copies."]:
    para(s, size=9, after=2)
para("DRAFT FOR JOHN QUINN’S REVIEW — not sent.", italic=True, size=9)
d.save(OUT); print(OUT)
