#!/usr/bin/env python3
"""Build the Dubai fraud case record + recommended Exos actions memo (2026-10-01)."""
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = "/Users/exomac/.openclaw/workspace/drafts/Exos_Dubai_Fraud_Case_Record_Recommended_Actions_2026-10-01.docx"

d = Document()
st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)


def h(t, lvl=1):
    d.add_heading(t, level=lvl)


def p(t, bold=False, italic=False):
    para = d.add_paragraph()
    r = para.add_run(t); r.bold = bold; r.italic = italic
    return para


def b(t, lead=None, style="List Bullet"):
    para = d.add_paragraph(style=style)
    if lead:
        para.add_run(lead).bold = True
    para.add_run(t)
    return para


t = d.add_heading("Dubai Fraud Matter: Case Record & Recommended Exos Actions", 0)
p("Exos Aerospace Systems & Technologies, Inc. | Prepared by Exo for John Quinn | 1 October 2026", italic=True)
c = p("CONFIDENTIAL. Prepared for review with Counsel. Law-enforcement matter: nothing here is sent externally without John's go.", bold=True)
c.runs[0].font.color.rgb = RGBColor(0xB0, 0x00, 0x20)

h("1. Bottom line")
b("The FBI path is stalled at intake. No case agent has been assigned, and the Dallas number reaches the tip line. Stop waiting on Dallas alone. Escalate through congressional casework and open parallel federal referrals (USSS, HSI).")
b("Rob Cass's 9/30 plan mostly serves his own €755k commercial judgment. Exos benefits from two parts of it: (a) linking the proceedings to a criminal case, which keeps the 5-year limitation running and puts Exos's losses in scope, and (b) the asset intelligence. A U.S. residential asset would give us the U.S. hook the FBI needs.")
b("Exos should not fund legal fees or sign any engagement yet. First verify that Khalid Riad and Omar Al Sharif are licensed, and get a written, success-weighted engagement that Counsel has reviewed. The previous UAE solicitor took fees roughly equal to the only money recovered (€50k) and never froze the accounts.")

h("2. Record: new information received 30 Sep – 1 Oct 2026")
p("Source: Rob Cass (rob@irishsustainablehomes.com), 30 Sep 20:56, 'Re: UAE action: Call on next steps', recapping a call with solicitors. Cc: PLIM Swiss legal dept (legaldepartment@plimswiss.com), Mike O'Shea (mike@osheauk.com), John Quinn. Khalid Riad (kdlilaw@gmail.com) replied 1 Oct 02:35: 'I am ready for all legal supports.'")
h("Findings reported", 2)
b("Rob's group holds an enforceable Supreme Court commercial judgment against Aras / Beyond Infinity for €755k plus interest. The solicitor never enforced it and never froze accounts, although that work was paid for in 2021.")
b("Funds were moved out of the judgment-debtor accounts while the High Court cases were running: €700k to Emirates Islamic Bank and personal accounts, plus €1.3m across other victims. None came back. The only recovery was €50k, which matched the solicitor's fees.")
b("2021 strategy flaw: the solicitor filed a commercial costs claim (€755k) instead of a civil/criminal claim. That gave up the loan quantum (about €640m, Rob's figure), lost profits (about €210m), and personal claims against the directors.")
b("Criminal conduct Rob says was never charged: fake names to hide German criminal records, falsified loan and silent-partner quantums, a false Dubai Holdings association, no trade license to lend, falsified Hikma bank statements, false statements to officials, misuse of brokers, dissipation of assets to personal and related accounts, and defamation of victims on Telegram.")
b("Asset-flight indicators: Aras Group UAE assets are moving to individuals and family in DE, UK, Turkey, Brazil and Indonesia through shell fronts (UK retail, DE real-estate brokers, UAE solicitors and real-estate brokers) and a residential holding in the U.S.")
h("Proposed legal approach (all four tracks run at once)", 2)
b("Seek a travel ban against Ralf Jung / 'Frank Kahn' ('catch the kingpin'). The €10k asset-related cost is covered by Rob's Kuwaiti/UAE sponsor.", style="List Number")
b("Enforce the judgment to recover costs and fund the next steps.", style="List Number")
b("Review the earlier proceedings for errors so they can be reopened as civil or criminal cases.", style="List Number")
b("Link to other victims' criminal case, which preserves the 5-year statute of limitations and brings civil/criminal losses into scope.", style="List Number")
p("Proposed team: Khalid Riad leads, paid as a % of recovery. Omar Al Sharif appears in court, with payment phased toward recovery. Criminal-case cost proposal: an attachment to Rob's email, which did NOT come through with the forward. Rob is asking for a call on approach, plan and fees/financing across UK, DE, IRL and US, and whether 'Theo' will cover the initial legal costs.")

h("3. Exos position (unchanged)")
b("Victims: Exos Aerospace and its investors. USD 613,097.63 wired from Chase via BNY Mellon to Emirates Islamic Bank (UAE). 18 U.S.C. §§1343, 1956, 1962.")
b("U.S.: IC3 complaint #7c585d20…; voluntary interview with FBI Legat Dubai on 23 Jun 2026 (SSA David Minami, SSA Melissa). Dallas FO submission 1 Sep (re-addressed to SAC Rothrock 9/17 and 9/24). Follow-up/status letter drafted 9/24 and not sent. John (MC #3210): 'No field office assignment and phone number you gave me was basically a tip line.' Senator Cornyn casework letter appears to have gone out about 7 May. No response is logged.")
b("Foreign: two affirmed Dubai judgments (Case #207/2023/5263); Dubai Police complaint #225004184901; connected German conviction (27 Jul 2026); Irish Garda ECU MLA request to the UAE (30 Aug 2026).")
b("Witness intimidation: WhatsApp threats to the lead cooperating victim since about 11 Aug 2026.")

h("4. Recommended Exos actions (ranked)")
h("A. Break the FBI logjam (John; government, so John sends)", 2)
b(" Send a short status-only casework request to Sen. Cornyn and Sen. Cruz (state offices) and to John's U.S. Representative (Hunt County, TX: [confirm member ______]). Ask each office to make a congressional liaison inquiry to the FBI on referral status and case-agent assignment. This is the standard lever when a referral sits unassigned. Each office needs a signed Privacy Act release, which is a one-page form on its website. Exo will pre-fill the forms on request.", lead="1. Congressional casework (highest leverage, no cost).")
b(" File a supplemental IC3 report that cites the original complaint number and adds the new facts: asset dissipation, the U.S. residential holding, the travel-ban effort, ongoing intimidation, the German conviction, and the Garda MLA. It creates a dated federal record and costs nothing.", lead="2. Supplement IC3.")
b(" Refer the case to the U.S. Secret Service Dallas Field Office (financial and wire fraud) and to HSI Dallas (transnational money laundering). Both have jurisdiction over cross-border wire fraud and laundering through U.S. banks. Reuse the 9/1 letter with a new address block.", lead="3. Open parallel federal referrals.")
b(" Send the 9/24 status letter by certified mail to 1 Justice Way, Dallas, TX 75220 (return receipt). That gives a delivery record the congressional offices can cite. Also email a copy to Legat Dubai through U.S. Embassy Abu Dhabi, since SSA Minami already knows the case. Exo can find a usable Legat Dubai address if John doesn't have Minami's email.", lead="4. Certified-mail the 9/24 status letter.")
h("B. UAE legal track: participate selectively, fund nothing yet", 2)
b(" Support track 4 (criminal linkage). It does the most for Exos at the lowest cost: it keeps the limitation period running and puts Exos's USD 613k in the criminal file. Confirm whether Dubai Police complaint #225004184901 is Exos's own complaint or Rob's, and whether Exos is named in the linked case.", lead="5. Back the criminal linkage.")
b(" Before any power of attorney, fee, or engagement: (a) verify Khalid Riad and Omar Al Sharif in the Dubai Legal Affairs Department / UAE MOJ advocate registry (Khalid writes from a Gmail address, a red flag that needs explaining); (b) get the criminal-case cost proposal that was missing from the forward; (c) any agreement must be written, success-weighted, capped, limited to Exos's claim, signed directly with a licensed firm, and reviewed by Counsel. Fraud victims are a known target for follow-on 'recovery' schemes, so verify first.", lead="6. Vet before you commit.")
b(" The travel ban/asset step is funded by Rob's sponsor. Exos should contribute documents (judgments, wire records, IC3 number), not money. The question of whether 'Theo' funds the initial legal costs is for the other victims to settle. Exos should not step into that role.", lead="7. Contribute documents, not money.")
b(" Ask Rob in writing for the specifics on the U.S. residential asset (address, titled entity or person, state). A U.S. asset tied to the proceeds is the strongest single fact for getting FBI/USSS/HSI to open a case, and it could support U.S. civil forfeiture or a domestic recognition-and-attachment action.", lead="8. Get the U.S. asset details.")
h("C. Company protection", 2)
b(" Give Counsel a one-page brief. The loss and any contingent recovery may need disclosure in Series A / RTO diligence. Do not book recovery as an asset. Ask the CPA when a theft-loss deduction applies, since timing depends on whether there is a reasonable prospect of recovery.", lead="9. Counsel + investor disclosure.")
b(" Export and preserve the WhatsApp threats and Telegram defamation (screenshots plus exports with metadata). They support the obstruction and flight-risk argument in every jurisdiction.", lead="10. Preserve evidence.")
b(" Note: Mission Control's automated DD engine flagged Rob Cass FAIL (9/4) and Mike O'Shea CAUTION. Both are most likely name collisions with unrelated people, and Rob has been a known co-victim since April. This does not block cooperation. It is one more reason not to move Exos money on anyone's instruction without independent verification.", lead="11. CRM DD flags.")

h("5. Suggested holding reply (John to send if desired; fill the blank)")
p("To: Rob Cass; Cc: Khalid Riad, PLIM legal, Mike O'Shea", italic=True)
p("Rob, Khalid — thank you, this is a clear plan. Exos supports moving all four tracks, especially linking to the criminal case so the limitation period keeps running.\n\n"
  "Before Exos commits to any engagement or costs, please send: (1) the criminal-case cost proposal (it did not come through on my copy); (2) the UAE license / registration details for Khalid and for Omar Al Sharif; (3) how Exos's claim (USD 613,097.63, Dubai Police complaint #225004184901) would be included in the criminal filing; and (4) whatever detail you have on the U.S. residential asset. That last item matters for our U.S. law-enforcement track.\n\n"
  "I can join a call ______ (day/time CT).\n\nJohn")

h("6. Decisions for John")
b("Authorize Exo to draft the congressional casework requests + pre-filled privacy releases (Cornyn, Cruz, U.S. Rep).", style="List Bullet")
b("Authorize Exo to draft the USSS Dallas + HSI Dallas referral letters and the IC3 supplement.", style="List Bullet")
b("Send the holding reply to Rob as written, edited, or not at all.", style="List Bullet")
b("Whether to bring Counsel in now on the UAE engagement terms.", style="List Bullet")

d.save(OUT)
print(OUT)
