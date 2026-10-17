#!/usr/bin/env python3
"""Build SSLC Board notice: Director James Wertz's unauthorized unilateral cancellation of the Board-approved Exos Sales Commission Agreement."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_LINE_SPACING

OUT = "drafts/SSLC_Director_Violation_Notice_to_Board_2026-10-17_r3.docx"

d = Document()
# base style
st = d.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)
for s in d.sections:
    s.top_margin = Inches(1.0); s.bottom_margin = Inches(1.0)
    s.left_margin = Inches(1.0); s.right_margin = Inches(1.0)

NAVY = RGBColor(0x1F, 0x38, 0x64)

def para(text="", *, bold=False, italic=False, size=11, align=None, space_after=6, space_before=0, color=None):
    p = d.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    if align: p.alignment = align
    if text:
        r = p.add_run(text); r.bold = bold; r.italic = italic; r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    return p

def heading(num, text):
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(4)
    r = p.add_run(f"{num}.  {text}"); r.bold = True; r.font.size = Pt(11.5); r.font.color.rgb = NAVY
    return p

def kv(label, value):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(label + "  "); r.bold = True
    p.add_run(value)
    return p

def bullet(text, bold_lead=None):
    p = d.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(4)
    if bold_lead:
        r = p.add_run(bold_lead); r.bold = True
    p.add_run(text)
    return p

# ---- Title ----
t = para("NOTICE TO THE BOARD OF DIRECTORS", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2, color=NAVY)
para("Scorpius Space Launch Company (a California corporation)", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
para("Unauthorized Unilateral Action by a Director in Violation of the Corporation’s Bylaws",
     italic=True, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=10)

# divider
dp = d.add_paragraph(); dp.paragraph_format.space_after = Pt(8)
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
pPr = dp._p.get_or_add_pPr(); pbdr = OxmlElement('w:pBdr'); bottom = OxmlElement('w:bottom')
bottom.set(qn('w:val'),'single'); bottom.set(qn('w:sz'),'6'); bottom.set(qn('w:space'),'1'); bottom.set(qn('w:color'),'1F3864')
pbdr.append(bottom); pPr.append(pbdr)


def src(n, text):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    r = p.add_run(f"[{n}]  "); r.bold = True; r.font.size = Pt(9)
    r2 = p.add_run(text); r2.font.size = Pt(9)
    return p

# ---- Header block ----
kv("TO:", "The Board of Directors, Scorpius Space Launch Company —")
para("James Wertz (Chairman of the Board & Director); Markus Rufer (Chief Executive Officer & Director); Alice Wertz (Secretary, Chief Financial Officer & Director); Robert Conger (Director).", space_after=4)
kv("FROM:", "John Quinn, Director")
kv("DATE:", "October 17, 2026")
kv("RE:", "Purported unilateral cancellation of the Board-approved Exos sales commission arrangement — context for the Board and request for a Board vote")
kv("ATTACHMENT:", "A — Sales Commission Agreement between SSLC and Exos (unsigned draft dated October 6, 2026), for the Board’s review")
para("")

heading(1, "Summary")
para("At the Board’s recent meeting, Director James Wertz stated that he was cancelling the Company’s sales commission arrangement with Exos Aerospace Systems & Technologies, Inc. (“Exos”), under which Exos acts as SSLC’s sales representative for tank hardware in exchange for a commission. He said it could stand for the current PD Aerospace order only, and not going forward.")
para("No individual director has the authority to take that action. Under the Bylaws, the Company’s business is managed by the Board acting together; one director cannot cancel, suspend, or re-scope a contract the Board has approved. This notice gives every director the full context — what the Board approved, what the written agreement was for, what Exos has invested, and why 15% is a fair rate — so that the Board, not any one of us, decides the question by a vote.")

heading(2, "Background — the Board approved the arrangement")
para("The Board approved paying Exos a fifteen percent (15%) sales commission on SSLC tank-hardware sales, with price parity, at its meeting on or about May 23, 2026 (the “Board Approval”). [Secretary to confirm the meeting date and attach the minutes.] That approval is a corporate act of the Company.")
para("Exos is SSLC’s second-largest customer and its highest-producing sales channel, and Exos holds approximately eighteen percent (18%) of SSLC’s outstanding equity. The arrangement brings SSLC third-party tank-hardware revenue it would not otherwise reach.")

heading(3, "Why the written agreement was sent (Attachment A)")
para("Exos sent SSLC the unsigned Sales Commission Agreement attached as Attachment A to give the Board-approved arrangement a proper structure. Without a written agreement, the Board Approval exists only as a meeting decision and a working practice. That leaves real ambiguity about what products are covered, how a customer is credited to Exos, when a commission is earned and paid, how long the arrangement runs, and what happens if either side ends it. That ambiguity is exactly what produced the current dispute.")
para("The written agreement defines each of those points (covered Tank Hardware, Net Sales Price, customer registration, price parity, payment timing, audit, term and termination, and a post-termination tail) so that the arrangement runs under the Company’s normal corporate process: approved by the disinterested directors, recorded in the minute book, and changed only by the Board. It also records the Section 310 related-party approval with my abstention (Agreement § 11). It documents the Board Approval; it does not create it. It is attached so each director can review the actual terms rather than a description of them.")

heading(4, "Exos has fully funded the sales effort")
para("SSLC has not paid for any of the sales effort behind this channel. Exos has carried all of it:")
bullet(" Exos has spent more than $20,000 of its own money on sales activity directly related to SSLC, including business-development travel to Japan to present SSLC tank capabilities. [Exos to attach an itemized schedule.]", bold_lead="Direct sales investment. ")
bullet(" Exos is committed to an SSLC booth at a December 2026 event in Washington, D.C. SSLC has paid nothing toward it. [Exos to state the booth cost.]", bold_lead="December Washington, D.C. booth. ")
bullet(" Customers pay exactly what SSLC would charge them directly. SSLC pays a commission only on a closed sale, and only as the customer pays (Agreement §§ 4–6). If Exos produces no revenue, SSLC pays nothing.", bold_lead="No cost to SSLC unless Exos delivers. ")
para("Cutting the arrangement off now would let SSLC keep the benefit of an investment Exos made on SSLC’s behalf, with no recognition of it. That is not a fair or sound outcome for the Company, and it would damage SSLC’s standing with the customers Exos has introduced. Exos has already had to cancel a PD Aerospace tank meeting because it cannot commit to a customer on terms SSLC may withdraw.", space_before=4)

heading(5, "The 15% rate is in line with what an in-house sales function would cost")
para("The Board should weigh the commission against what SSLC would otherwise pay to generate the same sales:")
bullet(" The U.S. Bureau of Labor Statistics reports a median annual wage of $124,900 for sales engineers (May 2025) [1]. For full-time private-industry workers, wages are 68.5% of total employer compensation cost, with benefits the remaining 31.5% (June 2026) [2]. One in-house sales engineer therefore costs SSLC roughly $182,000 a year before travel, trade shows, or any sale closes.", bold_lead="Cost of a salaried seller. ")
bullet(" At 15%, Exos would have to bring SSLC more than $1.2 million of sales in a year before SSLC’s commission cost equaled the cost of one salaried sales engineer. Below that volume, the commission channel is cheaper. At any volume, SSLC pays only for revenue it actually receives.", bold_lead="Break-even. ")
bullet(" The Manufacturers’ Agents National Association’s member surveys put typical rep commissions at 7%–14% for end-user sales, and note that rates can exceed those ranges in unique circumstances [3]. MANA states its surveys date from 1999–2005 and that no newer data exists. Industry sources note that rates run higher for complex, low-volume, engineered products with long sales cycles [4]. Flight-qualified composite cryogenic tanks sold into new launch and spacecraft programs are that kind of product.", bold_lead="Independent-rep rates. ")
bullet(" A typical independent rep pays for its own selling costs out of its commission [5]. Here Exos does the same and more: it has funded SSLC-specific international travel and a dedicated SSLC trade-show presence, on top of the technical sales work.", bold_lead="What the 15% covers. ")

heading(6, "A tail provision protects the investment already made")
para("If the Board decides to end or change the arrangement, the Company should do so on a fair basis, not by cutting it off. Attachment A already provides a standard tail (Agreement § 7): after the agreement ends, SSLC continues to pay commission on all sales ordered before the end date and on orders from Exos-registered customers placed within twelve (12) months afterward. A tail like this is standard practice for sales-representative agreements. It means the party that funded the customer development is paid when that work turns into orders.")
para("I ask that any Board action on this arrangement include, at minimum: (i) that tail on Exos-registered customers; and (ii) reimbursement of Exos’s documented SSLC-specific sales investment, including the December Washington, D.C. booth, to the extent it has not been recovered through commissions.")

heading(7, "The Bylaws reserve this decision to the Board")
bullet(" — “all corporate powers shall be exercised by or under the direction of the board of directors.” Corporate power belongs to the Board as a body, not to any director.", bold_lead="Article III, Section 1 (Powers)")
bullet(" — an act of the Board is a decision “made by a majority of the directors present at a meeting duly held at which a quorum is present.” A statement by one director at a meeting is not an act of the Board.", bold_lead="Article III, Section 9 (Quorum / Vote)")
bullet(" — action without a meeting requires the written consent of “all members of the board.”", bold_lead="Article III, Section 13 (Action Without Meeting)")
bullet(" — the chairman presides at Board meetings and has only the other powers “assigned to such officer by the board of directors or prescribed by the bylaws.” Neither the Board nor the Bylaws has given the chair power to revoke a Board-approved agreement.", bold_lead="Article V, Section 6 (Chairman of the Board)")
bullet(" — even the president acts “subject to the control of the board of directors.”", bold_lead="Article V, Section 7 (President)")
bullet(" — no officer, agent, or employee may bind the Company by contract “unless so authorized or ratified by the board of directors.” Un-binding the Company from a contract the Board approved is equally a Board act.", bold_lead="Article VIII, Section 3 (Contracts)")
para("Because the arrangement is a Board-approved corporate obligation, the Board alone can modify or rescind it. The statement that it was “cancelled” has no effect. Until the Board votes otherwise, the arrangement remains in force, and Exos will continue to perform under it.", space_before=4)

heading(8, "A related financial matter for the Board")
para("My understanding is that the Company shipped approximately $5,000,000 of hardware after receiving only about half of the contract value, leaving on the order of $2,500,000 of SSLC investors’ value exposed. [Secretary/CFO to confirm the figures.] Extending credit or forgiving payment of that size is a Board matter. Like the commission decision, it should not be made by any one director or officer alone.")

heading(9, "Requested Board action")
para("I ask that the Board:")
bullet(" that no individual director or officer can cancel or re-scope the Board-approved Exos commission arrangement, and that it remains in force until the Board votes otherwise;", bold_lead="(a) Confirm ")
bullet(" Attachment A and decide, by vote at a duly held meeting, whether to approve it as the written form of the Board Approval;", bold_lead="(b) Review ")
bullet(" if the Board chooses to end or change the arrangement, that it do so with the tail and reimbursement described in Section 6;", bold_lead="(c) Provide, ")
bullet(" that no director or officer may terminate a Board-approved contract, or ship hardware ahead of payment, without prior Board authorization; and", bold_lead="(d) Confirm ")
bullet(" the Secretary/CFO to bring a written accounting of the hardware orders in Section 8 (contract value, invoiced, collected, and outstanding). Under Article V, Section 10, the books of account are open to inspection by any director, and I am exercising that right.", bold_lead="(e) Direct ")
para("I ask that a special meeting be called within five (5) business days to take up these items. Under Article III, Section 8 and California Corporations Code § 307(a)(1), a special meeting may be called by the chairman, the president, the secretary, or any two directors. If no meeting is called by Friday, October 23, 2026, I will join with another director to call one. Until the Board acts, please confirm in writing that no notice of termination has gone, or will go, to any customer or partner.", space_before=4)

heading(10, "Disclosure of interest")
para("I am CEO and a director of Exos, and Exos is the counterparty to this arrangement. This is an interested-director matter under Section 310 of the California Corporations Code. I have disclosed that interest and will abstain from the vote. That is exactly why this decision belongs to the disinterested directors acting together, and not to any one director.")

heading(11, "Reservation of rights")
para("Nothing in this notice waives any right of the Company, of Exos, or of me as a director or shareholder. I ask that this notice and Attachment A be entered in the Company’s minute book.")

para("")
para("Respectfully submitted,", space_after=18)
para("John Quinn", bold=True, space_after=0)
para("Director, Scorpius Space Launch Company", space_after=0, size=10.5)
para("CEO, Exos Aerospace Systems & Technologies, Inc.", space_after=12, size=10.5)

p = para("Sources", bold=True, size=10, space_before=10, space_after=2)
src(1, "U.S. Bureau of Labor Statistics, Occupational Outlook Handbook — Sales Engineers (median annual wage, May 2025): https://www.bls.gov/ooh/sales/sales-engineers.htm")
src(2, "U.S. Bureau of Labor Statistics, “Compensation costs for private industry workers averaged $46.89 per hour worked in June 2026,” The Economics Daily, Sept. 17, 2026: https://www.bls.gov/opub/ted/2026/compensation-costs-for-private-industry-workers-averaged-46-89-per-hour-worked-in-june-2026.htm")
src(3, "Manufacturers’ Agents National Association (MANA), “Step 3 — Create Fair and Balanced Written Agreements” (commission-rate survey ranges): https://www.manaonline.org/step-3-create-fair-and-balanced-written-agreements")
src(4, "Manufacturers-Representatives.com, “Sales Commission: Formulas, Rates, and Structure for Sales Reps”: https://www.manufacturers-representatives.com/article.cfm?ArticleNumber=7")
src(5, "RepHunter, “How are manufacturers representatives typically paid?”: https://www.rephunter.net/blog/how-are-manufacturers-representatives-typically-paid")

fp = para("DRAFT FOR JOHN QUINN’S REVIEW — not sent. Bracketed items need confirmation before issuance.",
          italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=14)
fp.runs[0].font.color.rgb = RGBColor(0x80,0x80,0x80)

d.save(OUT)
print("WROTE", OUT)
