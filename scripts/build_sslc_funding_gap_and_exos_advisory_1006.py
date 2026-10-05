#!/usr/bin/env python3
"""build_sslc_funding_gap_and_exos_advisory_1006.py — MC task #2414 (@Exobot request, 2026-10-05).

Two deliverables for Tuesday 2026-10-06:
  A. SSLC_Board_Briefing_Standalone_Funding_Gap_2026-10-06  — SSLC-board-facing: why the standalone plan fails
     without new cash, how much is needed, and answers to every question raised at the 10/2 SSLC board meeting
     (transcript: mission-control/uploads/1791215046286_sslc_board_mtg__1_.docx). Companion to
     SSLC_Board_Package_2026-10-06. No distressed/bankruptcy-purchase content (internal only).
  B. Exos_Board_Advisory_SSLC_ROFR_and_Control_Options_2026-10-06 — Exos-board-only: options to win the ROFR and
     the non-consensual ("hostile") paths, with legal constraints. Builds on research/fnex_rd_2026-10-03/B_*.md.

Numbers: SSLC QuickBooks pulled 10/2 + SSLC FY26 management report (8/21) + Annual_Projection_summaries.xlsx,
as already tabulated in SSLC_Board_Package_2026-10-06.docx.
"""
import os, subprocess
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

WS = "/Users/exomac/.openclaw/workspace"
D = os.path.join(WS, "drafts")
NAVY = RGBColor(0x1F, 0x3A, 0x68)
RED = RGBColor(0x9B, 0x1C, 0x1C)

LEG = "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CORP&sectionNum="
LII = "https://www.law.cornell.edu/uscode/text/"


class Doc:
    def __init__(self):
        self.d = Document()
        self.d.styles["Normal"].font.name = "Calibri"; self.d.styles["Normal"].font.size = Pt(10.5)

    def para(self, text="", bold=False, size=None, color=None, italic=False, space=4, indent=None):
        p = self.d.add_paragraph(); p.paragraph_format.space_after = Pt(space)
        if indent: p.paragraph_format.left_indent = Inches(indent)
        if text:
            r = p.add_run(text); r.bold = bold; r.italic = italic
            if size: r.font.size = Pt(size)
            if color: r.font.color.rgb = color
        return p

    def head(self, text):
        p = self.para(text, bold=True, size=12.5, color=NAVY, space=3); p.paragraph_format.keep_with_next = True

    def sub(self, text):
        p = self.para(text, bold=True, size=11, space=2); p.paragraph_format.keep_with_next = True

    def bullet(self, lead, body="", indent=0.25):
        p = self.para(space=2, indent=indent); p.add_run("•  ")
        if lead:
            r = p.add_run(lead); r.bold = True
        p.add_run(body)

    def qa(self, who, q, a):
        p = self.para(space=1); r = p.add_run(f"{who}: "); r.bold = True; r2 = p.add_run(q); r2.italic = True
        p.paragraph_format.keep_with_next = True
        self.para(a, space=5, indent=0.2)

    def table(self, rows, widths, bold_last=False):
        t = self.d.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
        for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 1440)))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                c = t.cell(i, j); c.width = Inches(widths[j]); c.text = ""
                r = c.paragraphs[0].add_run(str(val)); r.font.size = Pt(9.5)
                if i == 0 or (bold_last and i == len(rows) - 1): r.bold = True
        self.para(space=3)

    def save(self, name):
        raw = os.path.join(D, f"_{name}_raw.docx"); out = os.path.join(D, name + ".docx")
        self.d.save(raw)
        subprocess.run(["/usr/bin/python3", os.path.join(WS, "scripts/apply_exos_letterhead.py"), raw, out], check=True)
        os.remove(raw)
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", D, out], check=True,
                       capture_output=True)
        return out


# ============================================================================ A. SSLC board briefing
A = Doc()
A.para("SCORPIUS SPACE LAUNCH COMPANY — THE STANDALONE PLAN AND THE CASH IT NEEDS", bold=True, size=15, color=NAVY, space=1)
A.para("Briefing for the SSLC Board of Directors · Special Meeting, Tuesday, October 6, 2026 · 2:00 PM Pacific", size=10, space=1)
A.para("Prepared by Exos Aerospace Systems & Technologies, Inc. for the SSLC directors and SSLC counsel. Confidential. "
       "Companion to the October 6 Board Decision Package. Figures are from SSLC's own QuickBooks (pulled October 2, 2026), "
       "SSLC's FY26 management report (August 21, 2026) and SSLC's Annual_Projection_summaries workbook. "
       "John Quinn abstains from every vote (Cal. Corp. Code §310: " + LEG + "310).", italic=True, size=9, space=8)

A.head("1. Bottom line")
A.para("Everyone at Friday's meeting agreed Scorpius has real value: firm Intuitive Machines demand, better pricing, "
       "steadier payment terms. The problem is not the technology or the team. It is cash. On SSLC's own numbers, the "
       "standalone plan cannot be carried out with the money SSLC has, and no source for the difference has been identified.", space=4)
A.bullet("Cash runs out around mid-December 2026. ", "Liquid resources of $475,226 cover about 2.5 months at the Q1 cost "
         "rate of ~$186,500 a month.")
A.bullet("$297,000 to $721,000 more is needed just to finish work SSLC has already billed or been paid for ", "($984,062 of "
         "prepaid work: $864,062 billed ahead of performance plus $120,000 of deposits).")
A.bullet("Up to ~$1.5M more is needed by June 2027 ", "if revenue runs at 75% of projection and costs track FY26.")
A.bullet("The growth plan is unfunded on top of that: ", "the five people hired in the last 100 days, at least two more, a "
         "formal quality function, offline winding stands, a 5-axis winder and the automation steps in the September 30 IM "
         "briefing.")
A.bullet("$1,027,783 of loans and notes are outstanding ", "(not the $710K cited from March 31), and SSLC's equity is "
         "−$1,403,075. No lender we know of will fund the gap on that balance sheet.")
A.para("The question for the board is not whether Scorpius is valuable. It is: where does the cash come from, how much, "
       "and by when? Section 6 lists what a credible answer must cover.", bold=True, space=6)

A.head("2. What the board told us on October 2, and what each point costs in cash")
A.table([
    ["Said on October 2", "By", "Cash consequence"],
    ["\"$7.4M was optimistic … really, really close to $5 million for next year\" is firm", "Markus",
     "Revenue plan down ~32%, while the cost base is being built for growth. The 75% case below already assumes "
     "~$524K/month of revenue, more than twice Q1's ~$238K/month."],
    ["Hired 5 people in the last 100 days; 2 more needed; no formal quality management function yet", "Markus / John",
     "Fixed payroll rises before the new tank revenue arrives. None of it is in the cash on hand."],
    ["Two more containers, tank carts, motorized offline stands so the winder only winds; batch-building PMDs and "
     "inventory", "Markus", "Capital spending and inventory build ahead of revenue — \"these are also financial commitments\"."],
    ["Government now buys in batches: tank sets for 2030 missions may have to start in early 2028", "Markus",
     "More work-in-process carried for longer. Working capital need grows with the backlog."],
    ["One delivered tank was destroyed when the customer's transport frame failed; a replacement is needed", "Markus",
     "Unplanned production slot inside an already-full schedule."],
    ["IM pays on a fixed calendar schedule; net-15 restored", "Markus",
     "Helps timing, but $864,062 has already been billed ahead of the work. That cash has come in; the cost of the work "
     "has not yet been spent."],
    ["No federal budget; Space Force / Golden Dome cannot start new work", "Bob",
     "No new non-IM orders near term. IM concentration (73% of FY26 revenue) stays high exactly when cash is tightest."],
    ["Margins are up — about 35%", "Bob / John",
     "Good, and Q1 shows it. But Q1 costs still ran 78.5% of revenue and September recorded a gross loss of $32,542 "
     "with no revenue booked."],
    ["Lease more equipment against firm orders", "Bob",
     "A lessor underwrites the lessee. With equity of −$1.40M and an FY26 operating loss of $415,963, expect personal "
     "guarantees or large deposits."],
    ["Debt was $710K at March 31", "Jim", "Loans and notes are $1,027,783 at October 2; total liabilities $1,275,622."],
], [2.35, 0.75, 3.4])

A.head("3. The cash math, on SSLC's own numbers")
A.sub("3a. Can SSLC finish the work it has already been paid for?")
A.table([
    ["Item", "Amount"],
    ["Cash (10/2)", "$198,419"],
    ["Plus billed receivables, if all collected", "+$343,306"],
    ["Less payables and accrued wages due now", "−$66,499"],
    ["Liquid resources", "$475,226"],
    ["Cost to deliver $984,062 of prepaid work at the FY27 Q1 cost ratio (78.5%)", "$772,291"],
    ["Cost to deliver it at the FY26 cost ratio (121.6%)", "$1,196,718"],
    ["Additional cash needed just to finish paid-for work", "≈ $297,000 to $721,000"],
], [4.8, 1.7], bold_last=True)
A.sub("3b. Can SSLC operate through June 2027 at 75% of projection?")
A.table([
    ["", "At FY27 Q1 cost ratio", "At FY26 cost ratio"],
    ["Revenue at 75% of the $6,285K projected for Oct–Jun", "$4,713,750", "$4,713,750"],
    ["Less revenue on work already paid for (no new cash)", "−$984,062", "−$984,062"],
    ["New cash revenue", "$3,729,688", "$3,729,688"],
    ["Operating costs", "−$3,699,350", "−$5,732,390"],
    ["Plus liquid resources today", "+$475,226", "+$475,226"],
    ["Ending cash, June 2027 (before debt service and capital spending)", "≈ $505,600", "≈ −$1,527,500"],
], [3.5, 1.5, 1.5], bold_last=True)
A.para("SSLC has historically delivered 50–72% of projection (FY26 ≈ 50%; FY27 Q1 ≈ 72% of the $987K contracted for "
       "July–September). The best case above needs 75% and Q1 margins every month for nine months, and still ends with only "
       "about two to three months of costs in the bank, before debt service and before any growth spending.", space=4)
A.sub("3c. Total outside cash the standalone plan needs")
A.table([
    ["Need", "Amount", "Timing"],
    ["Finish prepaid work", "$297K – $721K", "Before mid-December 2026"],
    ["Operate through June 2027 at 75% of plan", "$0 – ~$1.53M", "Through June 2027"],
    ["Growth: hires, quality function, stands, 5-axis winder, automation (IM briefing 9/30)", "Not quantified by SSLC; unfunded",
     "2026–2027"],
    ["Existing loans and notes ($451K Microcosm, $321K Bookstore note, $132K EIDL, $92.5K Wertz, $31.2K Exos)",
     "$1,027,783", "Service/repay"],
], [3.4, 1.6, 1.5])
A.para("Planning range: roughly $0.3M of new cash by December, and $1.5M or more by mid-2027 once growth spending is "
       "included, before any debt is repaid. SSLC management should put its own figure on the growth line; Exos will "
       "gladly use it.", space=6)

A.head("4. Why outside money is hard to raise on these numbers")
A.bullet("Negative equity: ", "−$1,403,075 at October 2. A lender sees a liability, not collateral. Fixed assets "
         "($544,157 of tooling and test stands) are almost fully depreciated.")
A.bullet("The FY26 operating loss was $415,963. ", "Net loss was only −$77,683 because of a one-time $287,247 Employee "
         "Retention Credit that will not recur.")
A.bullet("Track record against projection: ", "50–72%. Lenders and investors now discount projections to contracted "
         "work only. That is why the 11 investors Exos spoke with valued SSLC's standalone books as a liability.")
A.bullet("Customer concentration: ", "IM was 73% of FY26 revenue; Exos was 23.6%. Remove Exos and SSLC's revenue base is "
         "one customer.")
A.bullet("Even growing companies with clean books are being turned down. ", "Exos, which has doubled revenue each of the "
         "past four years, cannot get an SBA-guaranteed loan for lack of three years of consistent financials.")
A.bullet("New equity at today's book value ", "would come at a steep discount and dilute every current holder.")

A.head("5. What happens if the cash runs short before a source arrives")
A.bullet("Deliveries slip on the 14 IM tanks in flow ", "(Operations Briefing, September 30). The 6–8 IM tanks expected "
         "within 6–8 weeks and the 4 more for next year depend on on-time delivery of these.")
A.bullet("IM has alternatives. ", "Other suppliers are already winning lunar-lander tank work. A customer that has prepaid "
         "$864,062 of work will protect itself first.")
A.bullet("Key people leave first. ", "The five new hires and the experienced technicians are the asset.")
A.bullet("Creditors' interests move to the front. ", "SSLC is balance-sheet insolvent today. SSLC counsel should advise the "
         "board on directors' obligations in that position (e.g., Berg & Berg Enterprises v. Boyle, 178 Cal.App.4th 1020 "
         "(2009): https://law.justia.com/cases/california/court-of-appeal/2009/h032785.html).")

A.head("6. What a credible standalone plan must answer")
A.para("Exos would genuinely welcome a plan that answers these. If there is one, the license still helps SSLC (surge "
       "capacity, 15% commission, Exos as a funded customer). If there is not, the sale is the plan.", space=3)
for q in ["Where does the $297K–$721K to finish the work already paid for come from, and by what date before mid-December?",
          "If revenue runs at 75% of projection and costs track FY26, where does up to $1.5M come from by June 2027?",
          "Will Intuitive Machines prepay more or fund capacity? Is that in writing, and on what terms?",
          "Will the Wertz/Microcosm side lend more or convert the $543,929 it is owed into equity?",
          "How are the hires, quality function, offline stands, 5-axis winder and automation funded, and what do they cost?",
          "What is the plan for the 14 IM tanks in flow if cash runs short before any of these sources arrive?",
          "What does each shareholder receive under the standalone plan, and when?"]:
    A.bullet("", q)

A.head("7. Every question raised on October 2, answered")
A.qa("Jim", "Is the projection going up, or is the $7.4M the number?",
     "Markus answered it: about $5M for 2027 is firm, the $7.4M was optimistic. Exos's view matches: about $3.0M is "
     "booked, ~$4.5M with the expected IM tanks, ~$5.1M with pipeline. The cash math above uses SSLC's own projection at 75%.")
A.qa("Markus", "Is the license tied to the deal? If the deal fails, does Exos still own a license?",
     "It is a license, not ownership; SSLC keeps the IP. It is effective on signing because the financing requires a "
     "present right. To meet the \"only if SSLC fails\" concern, Exos will accept a covenant not to manufacture itself "
     "except (i) U.S. Government work SSLC declines or cannot schedule, (ii) SSLC missing an Exos PO date or spec, (iii) "
     "SSLC ceasing tank operations, or (iv) SSLC-requested surge. Present grant, conditional exercise.")
A.qa("Jim", "How much is Exos paying for the license?",
     "Exos cancels its loan to SSLC with all accrued interest (about $38,158), SSLC earns 15% on surge work Exos performs "
     "for it, and Exos keeps buying from SSLC at customer price parity. See Package §6 for the Vaya comparison.")
A.qa("Bob", "SSLC licensed before; why not a license that only springs on bankruptcy?",
     "A license triggered by bankruptcy is generally unenforceable against the bankruptcy estate (11 U.S.C. §365(e)(1): "
     + LII + "11/365). A license granted before any filing is protected (§365(n)). A springing license fails exactly "
     "when it is needed, so the financing cannot rely on it. The conditional-exercise covenant above gives the same "
     "practical protection to SSLC.")
A.qa("Jim", "Why does Exos need to build tanks instead of buying them?",
     "Exos will keep buying from SSLC; that is the point of the conditional-exercise covenant. The financing requires that "
     "Exos can build its vehicles if SSLC cannot deliver. Markus confirmed the capacity issue himself: three BLK3 vehicles "
     "in ~4 months would not fit SSLC's IM schedule today.")
A.qa("Jim", "Would IM become second fiddle?",
     "No. Exos adds capacity at its own site rather than using SSLC's winder. SSLC can also send IM overflow to Exos and "
     "earn 15%.")
A.qa("Bob", "The price is the 2021 amount even though SSLC has grown.",
     "The term-sheet price is non-binding. The final price will be set on current financials through the independent "
     "Eqvista fairness opinion and comes back to this board and to the shareholders. If SSLC's growth is real, that process "
     "captures it. Exos is also open to part of the price being paid in Exos-Scorpius stock or tied to IM deliveries, so "
     "holders share in the upside they believe in.")
A.qa("Bob", "What actually comes out to the stockholders?",
     "On October 2 figures, about $1.04M distributable to the holders of the other 82% after all debts are paid at face "
     "(including Microcosm and the Wertz note), with $1.0M paid at escrow release (Package §3). Under the standalone plan, "
     "the answer today is nothing until the funding gap above is closed.")
A.qa("Jim", "Your investors are saying Scorpius has no value.",
     "They value SSLC's standalone books, which show −$1.40M equity and an operating loss. The value appears inside a "
     "funded combined company, which is why the listing is planned as Exos + Scorpius. Exos's position is the same as "
     "the board's: the technology and team are valuable. This briefing is about funding, not value.")
A.qa("Bob", "If Exos proceeds without SSLC, what does that do to Exos?",
     "Exos must qualify a different tank solution for the next BLK3 build, which takes Exos's 23.6% of SSLC revenue and "
     "its BLK3/BLK4 growth elsewhere. That outcome is worse for both companies. It is why Exos is asking for the license.")
A.qa("Bob", "Does Exos have the government contracts for these vehicles?",
     "The three BLK3 vehicles are funded from Exos's financing, not a single contract. Demand includes NASA Flight "
     "Opportunities eligibility, Exos Aerospace Japan and Exos Aerospace Italia. Exos is also performing a $1.9M Air Force "
     "contract with a $300K extension recently received.")
A.qa("Jim", "Can we take a week?",
     "John leaves for Japan on Thursday, October 8 for three weeks. If the board needs more time on the ROFR and the sale, "
     "Exos asks that it vote on the license (Resolution 1) on Tuesday so the financing can proceed, and take up the rest "
     "on the board's schedule. Exos will designate an officer to sign while John travels.")
A.para("Prepared by Exos for discussion. Not legal advice; SSLC directors should rely on SSLC counsel.", italic=True,
       size=8.5, space=2)
outA = A.save("SSLC_Board_Briefing_Standalone_Funding_Gap_2026-10-06")


# ============================================================================ B. Exos board advisory
B = Doc()
B.para("ADVISORY TO THE EXOS BOARD OF DIRECTORS", bold=True, size=15, color=NAVY, space=1)
B.para("SSLC: getting to the ROFR, and the non-consensual options · Board meeting, October 6, 2026", size=10.5, space=1)
B.para("CONFIDENTIAL — Exos board only. Do not forward to SSLC or its directors. Strategic analysis, not legal advice; "
       "items marked [Counsel] need M&A counsel before any action. Prepared by Exo for John Quinn, Cofounder & CEO.",
       italic=True, size=9, color=RED, space=8)

B.head("1. Bottom line")
B.bullet("SSLC's standalone plan fails without new cash. ", "On its own books SSLC runs out of liquid resources around "
         "mid-December 2026, needs $0.3–0.7M just to finish $984K of prepaid work, and up to ~$1.5M more by June 2027, "
         "with its growth plan unfunded and $1.03M of loans outstanding. No source has been identified.")
B.bullet("The SSLC board is reluctant, not opposed. ", "Jim: \"unlikely to get there… but maybe there exists some "
         "compromise.\" Markus accepts a license conditioned on SSLC failure. Bob offered a springing license and objects "
         "to the 2021 price. Nobody would DocuSign on October 2; they re-meet Tuesday 2:00 PM PT with counsel (Danny).")
B.bullet("A true hostile takeover is not available. ", "SSLC is a private California corporation; the Wertz family holds "
         "a majority (~60% per our records, confirm against the stock ledger). Exos cannot buy control without them.")
B.bullet("Exos's real leverage is cash timing. ", "SSLC's December cash cliff arrives before any other funding source. "
         "The value-preserving move is a consensual deal offered before that cliff, with a distress-ready fallback "
         "prepared quietly with counsel.")
B.bullet("Recommendation: ", "Path C — present license now, ROFR as an option, acquisition gated, and a pre-cliff "
         "secured bridge as the bridge-to-yes. Do not authorize any adversarial action on October 6.")

B.head("2. Where we stand after October 2")
B.table([
    ["Item", "Status"],
    ["SSLC board", "Jim Wertz (chair), Markus Rufer, Bob, John Quinn (abstains). Alice Wertz attends. Counsel: Danny."],
    ["Asks of SSLC", "R1 manufacturing license (key) · R2 endorse asset transaction · R3 ROFR reinstatement 6 months + "
                     "auto-extend during APA · R4 acknowledgment / 120-day no-shop · R5 conduct to closing"],
    ["Votes needed", "John abstains, so 2 of 3 disinterested directors (Jim, Markus, Bob). Markus and Bob have signaled "
                     "conditional license support."],
    ["Sale of substantially all assets", "Also needs shareholder approval (Cal. Corp. Code §1001: " + LEG + "1001). "
                                         "Wertz decides that vote alone."],
    ["Timing", "SSLC board Tue 10/6 2:00 PM PT · documents Wed 10/7 · John departs Thu 10/8 for ~3 weeks (Japan, then "
               "NYC investors) · SSLC cash cliff ~mid-December · ROFR (if granted) ~April 2027"],
], [1.8, 4.7])

B.head("3. Leverage map")
B.table([
    ["Exos holds", "SSLC's pressure points"],
    ["18% shareholder: inspection rights, can call a special meeting, cumulative voting", "Cash: ~2.5 months of runway"],
    ["Largest non-IM customer (23.6% of FY26 revenue) and funded BLK3 work", "IM = 73% of revenue; IM has prepaid $864K"],
    ["Exclusive 15% sales agent; the ~$800K Japan order rides on Exos", "No new government orders under the CR (Bob)"],
    ["Creditor: $31.2K loan + interest", "$543,929 owed to Wertz/Microcosm that they want repaid"],
    ["A financing (PIPE) that can pay all SSLC debts at face", "Growth plan (hires, winder, automation) unfunded"],
    ["A credible alternative: second-source / licensed tank cell", "He-tank 4,400-psi proof failures on Exos's funded article"],
], [3.25, 3.25])

B.head("4. Consensual options to win the ROFR (ranked)")
B.bullet("1. Unbundle — license first. ", "Vote R1 alone on Tuesday; it is what the financing needs. Offer "
         "\"present grant, conditional exercise\" (Exos manufactures only for USG work SSLC declines, missed Exos POs, "
         "SSLC ceasing operations, or SSLC-requested surge) plus a documentation escrow. This gives Markus and Bob the "
         "substance of their springing license while keeping a present right protected under 11 U.S.C. §365(n) (" + LII +
         "11/365).")
B.bullet("2. Bridge the price gap without raising cash price. ", "Let the Eqvista fairness opinion reset price on current "
         "financials, and offer part of consideration as (a) Exos-Scorpius stock after the listing or (b) an earn-out "
         "tied to IM tank deliveries and FY27 actuals. Answers Bob's \"not much to stockholders\" and Jim's \"Scorpius has "
         "value\": if they are right about growth, they are paid for it.")
B.bullet("3. Make the controlling holder whole. ", "Microcosm ($451K) and the Wertz note ($92.5K) paid at face at closing "
         "(already in R5), plus a capped 6–12-month Microcosm transition-services agreement with a hard sunset. This is "
         "Wertz's personal path to yes.")
B.bullet("4. Solve their December problem — the strongest lever. ", "Offer, subject to financing and disinterested SSLC "
         "approval, a secured working-capital bridge or a prepaid BLK3 tank PO sized to the prepaid-work gap "
         "($300–700K), secured on IP and tooling and credited against the APA price, in exchange for the ROFR and the "
         "no-shop. It turns Exos from the party asking into the party rescuing, and gives Exos secured-creditor standing "
         "(credit-bid rights under §363(k)) if SSLC fails anyway. [Counsel: insider lending to an insolvent company; "
         "EIDL lien priority.]")
B.bullet("5. People. ", "Defined roles for Markus (operations), Bob (government BD) and a board or advisory seat for Jim "
         "in Exos-Scorpius. Retention offers to Morey and the lead technicians at signing.")
B.bullet("6. Bring IM inside the tent (with SSLC's consent). ", "IM wants supply assurance. A combined, funded company "
         "with twice the capacity is IM's best outcome. IM's view can move Wertz. Do not contact IM about SSLC without "
         "SSLC's consent (interference risk).")
B.bullet("7. Fix the travel bottleneck. ", "Authorize a designated Exos officer to sign while John is away so Jim's "
         "\"take a week\" does not become a three-week stall.")

B.head("5. Non-consensual (\"hostile\") options — what is actually available")
B.table([
    ["Option", "Feasibility", "Notes"],
    ["Buy shares directly from non-Wertz holders / tender", "Low",
     "Cannot reach control without Wertz. Transfer restrictions or holder ROFRs in SSLC bylaws/agreements may block it. "
     "Any tender offer is subject to anti-fraud rules (15 U.S.C. §78n(e): " + LII + "15/78n)."],
    ["Shareholder governance pressure (18%)", "Available",
     "Inspect books and records (§1601: " + LEG + "1601); call a special meeting at ≥10% (§600(d): " + LEG + "600); "
     "cumulative voting for a director (§708: " + LEG + "708); scrutiny of related-party Microcosm fees (§310). Pressure, "
     "not control."],
    ["Buy SSLC debt", "Low–Medium",
     "$543,929 is insider debt (won't sell). Identify the holder of the $321K Bookstore note; if third-party, a discounted "
     "purchase gives a creditor seat. The $132K EIDL likely carries an SBA blanket lien — run a CA SOS UCC search first."],
    ["Distressed purchase (bankruptcy §363 sale or assignment for benefit of creditors)", "Medium, if SSLC fails",
     "Assets bought free and clear (11 U.S.C. §363(f): " + LII + "11/363). But: the ROFR generally will not bind a "
     "trustee; IM is the natural competing bidder or DIP lender; insider bids get heightened scrutiny; the team and IM "
     "contracts may scatter. Least value-preserving route."],
    ["Build around SSLC (BATNA)", "High",
     "Second-source or licensed tank cell for BLK3. Capex ~$0.8–1.5M manual, ~$3M automated; 9–18 months to a qualified "
     "tank. Credible alternative strengthens every consensual option."],
], [1.7, 0.95, 3.85])
B.sub("Constraints the board must respect [Counsel]")
B.bullet("John's duties as an SSLC director. ", "He owes SSLC loyalty and confidentiality. He cannot use SSLC board "
         "information to plan an adversarial move against SSLC. If the Exos board ever elects a distressed or adversarial "
         "path, John should first recuse formally or resign the SSLC seat, and Exos should act only on information it "
         "holds as shareholder, customer or creditor, through independent counsel.")
B.bullet("The license could be challenged if SSLC fails within a year. ", "An insolvent SSLC granting a perpetual license "
         "to an insider for cancellation of a ~$38K antecedent debt invites insider-preference (11 U.S.C. §547: " + LII +
         "11/547) and fraudulent-transfer (§548) claims. John accepted this on 10/2. Counsel should look at adding "
         "contemporaneous new value (e.g., the Exos-funded He-tank completion work or a PO commitment) and extending "
         "the Eqvista opinion to cover the license.")
B.bullet("One valuation story. ", "The SSLC-facing documents say standalone value is low; investor materials show "
         "\"OWN $20–40M.\" Both will be discoverable in an RTO proxy. Use one line everywhere: standalone SSLC is worth "
         "little; value arises inside a funded combined company.")
B.bullet("No pressure tactics. ", "The funding-gap briefing to SSLC is factual and uses SSLC's own numbers. Keep it that "
         "way. Nothing about distressed purchase goes outside this board.")

B.head("6. Recommended decision path")
B.table([
    ["Outcome on Tue 10/6", "Exos response"],
    ["Present license granted (as drafted or with conditional-exercise covenant)",
     "Proceed with PIPE/RTO on an Exos-only use of proceeds plus a ~$3–4M tank-capacity reserve. Pursue the ROFR/APA "
     "only when gates pass: IM written consent to assignment and ≥6 2027 IM tanks contracted; key-staff retention "
     "signed; trailing-two-quarter revenue ≥75% of contracted plan; net cash price ≤ ~$2.6M supported by fairness opinion."],
    ["License + ROFR granted", "As above, plus begin APA drafting with M&A counsel; offer the pre-cliff secured bridge."],
    ["Only a springing license offered", "Do not treat it as meeting the financing requirement. Counter with conditional "
     "exercise. If refused, remove Scorpius from the PIPE story and start the BLK3 second-source plan."],
    ["Nothing granted", "Exos-only raise; keep the 18%; second-source plan; prepare the distress scenario with counsel "
                        "and John walled off from SSLC deliberations."],
    ["Any path — by ~Nov 20", "If IM has not committed to fund or prepay SSLC's gap, take the secured-bridge offer through "
                              "SSLC's disinterested directors before the December cliff."],
], [2.2, 4.3])

B.head("7. Resolutions proposed for the Exos board (October 6)")
for i, r in enumerate([
    "Authorize the CEO to continue the consensual license-first path and to accept a \"present grant, conditional "
    "exercise\" license with documentation escrow.",
    "Authorize negotiation of price consideration that includes post-listing stock and/or an IM-delivery earn-out, "
    "within the range supported by the Eqvista fairness opinion. [Board to set ceiling.]",
    "Authorize management to offer SSLC, conditioned on financing and disinterested SSLC approval, a secured "
    "working-capital bridge or prepaid PO of up to $[board to set] credited against the APA price.",
    "Direct management and M&A counsel to prepare contingency analysis: SSLC governing documents and transfer "
    "restrictions, CA SOS UCC lien search, holder of the Bookstore note, and a distressed-acquisition playbook. No "
    "adversarial action without a further board vote.",
    "Direct qualification of a BLK3 second-source tank path.",
    "Designate [officer] to sign SSLC-related documents while the CEO travels October 8–~29.",
], 1):
    B.bullet(f"R{i}. ", r)
B.para("Not authorized today: any tender offer, debt purchase, or distressed-acquisition step.", bold=True, space=6)
B.para("Sources: SSLC QuickBooks (10/2), SSLC FY26 management report (8/21), SSLC Annual_Projection_summaries.xlsx, "
       "SSLC board meeting record (10/2/2026), SSLC Board Decision Package and Funding-Gap Briefing (10/6), Exos "
       "research note B (10/3). Legal references linked inline; confirm with counsel.", italic=True, size=8.5, space=2)
outB = B.save("Exos_Board_Advisory_SSLC_ROFR_and_Control_Options_2026-10-06")
print(outA); print(outB)
