#!/usr/bin/env python3
"""SSLC board cover email r4: Exos objection to Wertz's cancellation; ask board to disregard and vote per Bylaws."""
from docx import Document
from docx.shared import Pt
OUT = "drafts/sslc_board_vote/SSLC_Board_Vote_Request_Exos_Sales_Agent_Agreement_2026-10-17_r4.docx"
L = """DRAFT, not sent. John sends from jquinn@exosaero.com.
To: Jim Wertz <jim@smad.com>; Alice Wertz <awertz@smad.com>; Bob Conger <rconger@smad.com>; Markus Rufer <mrufer@smad.com>
Cc: (none)
Subject: Exos objection to the cancellation of the sales agent agreement; request for a board vote
Attachments: (1) Notice to the Board of Directors, October 17, 2026; (2) Attachment A: Sales Commission Agreement (unsigned draft dated October 6, 2026)

Jim, Alice, Bob, Markus,

Exos formally objects to the action taken at our last board meeting, when Jim stated that he was cancelling the Exos sales agent agreement. He said it would stand for the PD Aerospace order only, and not going forward. The board approved that agreement. SSLC's Bylaws do not allow any one director to cancel it, and I ask the board to disregard the comment and act on the agreement by a vote, as the Bylaws require.

The cancellation violates the Bylaws in four ways:
• Article III, Section 1: "all corporate powers shall be exercised by or under the direction of the board of directors." The power belongs to the board as a body, not to one director.
• Article III, Section 9: an act of the board is a decision "made by a majority of the directors present at a meeting duly held at which a quorum is present." No motion was made and no vote was taken, so a statement at a meeting is not an act of the board.
• Article V, Section 6: the chairman presides and has only the powers "assigned to such officer by the board of directors or prescribed by the bylaws." Neither the board nor the Bylaws gives the chair power to revoke a board-approved agreement.
• Article VIII, Section 3: no officer or agent may bind the corporation by contract unless the board authorizes or ratifies it. Releasing the corporation from a contract the board approved is equally an act reserved to the board.

The cancellation therefore has no effect. The agreement stays in force until the board votes otherwise, and Exos will continue to perform under it.

The attached notice gives the board the full context:
• Why Exos sent the written agreement: to put the board-approved 15% arrangement into a defined structure under normal corporate process, and to remove the ambiguity that caused this dispute. The agreement is attached for your review.
• Exos has funded the entire sales effort: more than $20,000 of SSLC-specific sales spending to date, plus an SSLC booth at a December event in Washington, D.C. SSLC has paid nothing toward any of it. SSLC pays a commission only on closed sales, at the same price SSLC would charge directly.
• The 15% rate is supported by cost data: based on BLS figures, one in-house sales engineer costs about $182,000 a year fully loaded. Exos would have to deliver more than $1.2 million of sales a year before SSLC's commission cost matched that one hire.
• A tail provision: if the board decides to end or change the arrangement, it should honor the agreement's 12-month tail on Exos-registered customers and reimburse Exos's documented SSLC sales investment. That investment should not simply be cut off.

What I am asking the board to do:
1. Disregard the statement made at the last meeting as not an act of the board.
2. Hold a special board meeting within 5 business days to review the attached agreement and vote on moving forward with it. Under Bylaws Article III, Section 8 and California Corporations Code §307(a)(1), the chairman, the president, the secretary or any two directors may call that meeting. If none has been called by Friday, October 23, I will join with another director to call one.
3. Until the board votes, please confirm in writing that no notice of termination has gone, or will go, to any customer or partner.

Disclosure: as CEO of Exos I have a financial interest in this agreement. I have disclosed it, and I will abstain from the vote under Corporations Code §310. That is why this decision belongs to the disinterested directors acting together, and not to any one of us.

Regards,
John Quinn
Director, Scorpius Space Launch Company
CEO, Exos Aerospace Systems & Technologies, Inc."""
d = Document(); d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)
for line in L.split("\n"):
    p = d.add_paragraph(line); p.paragraph_format.space_after = Pt(4)
d.save(OUT); print("WROTE", OUT)
