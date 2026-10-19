#!/usr/bin/env python3
"""10/19 SSLC email drafts: (1) Paula Lessnick (BBSNV) — read-in + acquisition close readiness; (2) SSLC Board — information + motions for 10/20."""
from docx import Document
from docx.shared import Pt, Inches

OUT_PAULA = "drafts/SSLC_Email_to_PLessnick_Motions2-4_2026-10-19.docx"
OUT_BOARD = "drafts/SSLC_Email_to_Board_Meeting_Motions_2026-10-19.docx"


def new_doc():
    d = Document()
    for s in d.sections:
        s.left_margin = s.right_margin = Inches(1)
    d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)
    return d


def para(d, t, *, bold=False, italic=False, size=11, after=8):
    p = d.add_paragraph(); r = p.add_run(t); r.bold = bold; r.italic = italic; r.font.size = Pt(size)
    p.paragraph_format.space_after = Pt(after)


def header(d, rows):
    para(d, "DRAFT — NOT SENT · for John Quinn’s review", italic=True, size=9)
    for k, v in rows:
        p = d.add_paragraph(); a = p.add_run(k + "  "); a.bold = True; p.add_run(v); p.paragraph_format.space_after = Pt(2)
    para(d, "—" * 40, after=8)


# ---------------------------------------------------------------- 1. Paula Lessnick
# r10/19 05:33 (Jon): read-in only. The SSLC Board agreed to call Paula only if it has issues; prepare her to help and to
# capture everything in Exos's books if the acquisition closes.
d = new_doc()
header(d, [
    ("From:", "John Quinn <jquinn@exosaero.com>"),
    ("To:", "Paula Lessnick <paula.lessnick@bbsnv.com>"),
    ("Subject:", "Scorpius (SSLC): background, a possible call from its directors, and getting ready for the acquisition"),
])
for t in [
    "Paula,",
    "I want to bring you up to speed on Scorpius Space Launch Company (SSLC), where I am a director and Exos holds 18.06% of the shares, "
    "and ask you to be ready to help in two ways. Nothing is needed from you this week.",
    "Where things stand",
    "1. Exos has offered to buy SSLC’s assets. The SSLC Board takes up the offer at a special meeting on Tuesday, October 20. Nothing is "
    "agreed yet.\n"
    "2. On October 13 the SSLC Board approved three items. All directors get read-only access to SSLC’s books, and that is done: it was "
    "set up through Exos Mission Control on October 19. SSLC’s bookkeeper, A La Carte Solutions, is correcting how SSLC books customer "
    "deposits and progress billings, due October 20. And Exos is running an ERP/MRP evaluation for SSLC at no cost to SSLC.\n"
    "3. The Board is also reviewing some related-party entries in SSLC’s books. That is SSLC’s matter, and SSLC is handling it.",
    "1. Standby for SSLC’s directors",
    "The Board agreed that it would call you only if it has issues with the deposit and billing correction. If that happens, I will let "
    "you know first, and the directors know you are Exos’s accountant, so your view would be a second opinion, not an independent "
    "review. Please don’t prepare anything in advance.",
    "2. Getting ready to capture everything if the acquisition closes",
    "If the deal closes, I want everything in Exos’s books from day one, with nothing left to reconstruct later. When you can, ideally "
    "before the end of the month, please send me a short close-readiness checklist covering:\n"
    "a) How Exos should account for the purchase (asset acquisition or business combination) and how the price is allocated across "
    "inventory and work in process, equipment, IP and customer contracts.\n"
    "b) Customer deposits and progress billings on open orders that Exos would take on, and how they carry over.\n"
    "c) The deferred parts of the price: the earn-out and the Exos units issued at close.\n"
    "d) What we need from SSLC at close: the QuickBooks file, open orders with the deposit schedule by customer, the fixed-asset "
    "register, inventory counts, and anything else you would want.\n"
    "e) The opening entries in Exos’s QuickBooks.",
    "Item d) matters most now: I want those deliverables written into the deal documents, so tell me early if anything should be added.",
    "BBSNV’s time on this is for Exos’s account. SSLC information is confidential, and I will share SSLC’s books with you only as the "
    "SSLC Board authorizes or as part of the deal.",
    "Thank you,\nJohn",
    "John Quinn\nCEO, Exos Aerospace Systems & Technologies, Inc.\nDirector, Scorpius Space Launch Company",
]:
    para(d, t, bold=t in ("Where things stand", "1. Standby for SSLC’s directors",
                          "2. Getting ready to capture everything if the acquisition closes"))
d.save(OUT_PAULA)

# ---------------------------------------------------------------- 2. SSLC Board
d = new_doc()
header(d, [
    ("From:", "John Quinn <jquinn@exosaero.com>"),
    ("To:", "Jim Wertz <jim@smad.com>; Jim Wertz <jwertz@smad.com>; Alice Wertz <awertz@smad.com>; Markus Rufer <mrufer@smad.com>; "
            "Robert Conger <rconger@smad.com>"),
    ("Subject:", "SSLC Board: notice, agenda and motions for the special meeting on Tuesday, October 20"),
    ("Attachments:", "SSLC_Director_Violation_Notice_to_Board_2026-10-19.docx; SSLC_RelatedParty_Reclass_Findings_2026-10-19.docx; "
                     "SSLC_Board_Motions_Voting_Eligibility_2026-10-19.docx"),
])
for t in [
    "Directors,",
    "Please find attached the papers for Tuesday’s meeting. Alice, as Secretary, please send notice under Article III, Section 8 by [____ day/time] "
    "for a special meeting on Tuesday, October 20 at [____] PT by Teams, and enter this email and its attachments in the minute book. If notice "
    "has not gone out by then, I will call the meeting with a second director, as Section 8 allows.",
    "Attachments:\n"
    "1. Notice to the Board (October 19), setting out each item under the Bylaws.\n"
    "2. Findings on the related-party reclassifications: the April 30, 2026 entries, what they did to SSLC’s balance sheet, and why they do not "
    "meet basic accounting standards.\n"
    "3. Motions and voting eligibility: a plain-English description of each motion, which directors cannot vote, and the rule that says so.",
    "Agenda and motions",
    "1. Motion 1: the Exos offer, §3 exclusivity and right of first refusal, or SSLC’s written counteroffer (vote). I am interested and will abstain.\n"
    "2. Motions 2–4, approved October 13: status. Motion 2 is done: access was established through Mission Control on October 19, and Markus and Bob "
    "were each emailed their login instructions that day for read-only access to SSLC’s books and records. Motion 3, the corrected AR "
    "Unbilled and customer-deposit accounting, due Tuesday. A La Carte is making the correction; as agreed, the Board will call Paula "
    "Lessnick of BBSNV, Exos’s accountant, only if it has issues. Motion 4, the ERP/MRP evaluation, is in progress at Exos’s cost on the same Mission Control platform.\n"
    "3. Motion 5: the related-party balances owed to Microcosm, MDAB and the Wertz family ($857,419 of $1,020,690) (vote).\n"
    "4. New resolutions RP-1 to RP-6 on the self-dealing entries: a formal finding; reversal of the April 30, 2026 entries; a receivable for "
    "Microcosm’s share of the building; a freeze on insider payments; an independent CPA review; and posting controls (roll-call votes).\n"
    "5. The Bookstore interest waiver: signed MDAB release, reversing entry and resolution.\n"
    "6. The October 16 letter of intent for SSLC and Microcosm: receive it; resolve that the October 27, 2015 60/40 split does not bind SSLC; "
    "written confirmation of which tank-making assets SSLC owns; "
    "independent financial adviser.\n"
    "6a. Motion NC-1, NewCap Partners: Danny has given sound advice to Jim, SSLC and Exos. So that it is handled correctly, record that "
    "NewCap is engaged by Jim and earns 5% on a sale of SSLC and/or Microcosm, put the engagement letter in the minute book, and have any "
    "SSLC-paid part of the fee approved by disinterested directors or by shareholders with the sale.\n"
    "7. The Exos commission: confirm the Board’s April 10, 2025 approval (15% on new business, 5% on repeat customers, paid on receipt of funds) "
    "stands, and vote on the written agreement. I am interested and will abstain.\n"
    "8. Payment schedule for the Exos loan and the Space Tech Expo invoice. I am interested and will abstain.\n"
    "9. Information items: monthly statements June–September 2026 with an officer’s certificate; terms of the Intuitive Machines order; an "
    "accounting of hardware orders.",
    "Who cannot vote. Under Corporations Code §310, a director with a material financial interest in a transaction, or who sits on the other "
    "company’s board, cannot have their vote counted toward approving it. On Microcosm, MDAB and Wertz items, that is Jim, Alice and Bob: all "
    "three are Microcosm directors, and Microcosm’s stock distribution shows Alice with 50.52%, Jim 20.31% and Bob 7.81%. Markus holds 0.78% of "
    "Microcosm, which is not material; he should disclose it, and his vote counts. On Exos items, that is me. The attached motions paper sets "
    "this out item by item. I ask that each director state their interests at the start of the meeting and that the minutes record each "
    "director’s vote.",
    "If the Board does not take up these items on Tuesday, Exos, which holds 18.06% of SSLC’s shares, intends to call a special meeting of "
    "shareholders under Article II, Section 3.",
    "Regards,\nJohn",
    "John Quinn\nDirector, Scorpius Space Launch Company",
]:
    para(d, t)
d.save(OUT_BOARD)
print(OUT_PAULA); print(OUT_BOARD)
