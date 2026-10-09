#!/usr/bin/env python3
"""SSLC acquisition rescue: invoke 2025 Asset Acquisition Agreement §3 exclusivity trigger. INTERNAL options memo + draft message (task #3544)."""
from docx import Document
from docx.shared import Pt
OUT="drafts/SSLC_Exclusivity_Rescue_Options_and_Draft_Message_2026-10-07_DRAFT_v2.docx"
d=Document(); s=d.styles['Normal']; s.font.name='Calibri'; s.font.size=Pt(10.5)
H=lambda t,l=1:d.add_heading(t,l); P=lambda t:d.add_paragraph(t); B=lambda t:d.add_paragraph(t,style='List Bullet')
H("SSLC Acquisition Rescue — Exclusivity Trigger: Options + Draft Message",0)
P("INTERNAL — Exos CEO only. DRAFT, not sent. Prepared by Exo for John Quinn, 2026-10-07 (MC #3544). Negotiation-stage terms — not a final offer.")
H("1. The lever you already hold")
P("The executed Asset Acquisition Agreement (signed John Quinn and James Wertz, May 13, 2025; SSLC board approved May 2, 2025) §3 says: Buyer holds non-exclusive rights to acquire the assets \"until Seller assigns exclusivity once Buyer has entered into an agreement with an investor or lender capable of financing the transaction. Once the Seller grants exclusivity, the Buyer will have exclusivity for 90 days to secure funding and close… The Seller will not unreasonably withhold an exclusivity extension as long as the Buyer and their financing source are working in good faith towards a closing.\" §6: closing within 90 days of exclusivity. Price: $3.36M total commitment ($2.51M cash + $60K seller costs; Exos's ~$790K 2021 capital is the balance).")
P("This is separate from the ROFR the board declined. It is a board-approved, signed acquisition path with its own trigger, and the trigger is the thing you now have.")
H("2. Ainigma structure as it bears on the trigger")
B("FNEX/Ainigma = exclusive RTO advisor + placement agent: RTO into a pre-funded NASDAQ shell, $15M pre-RTO convertible note, PIPE min $15M with $10M net to Exos, $250M min MEV, 7% placement on FNEX-placed PIPE.")
B("Weak point: FNEX is an advisor/broker-dealer, not itself the 'investor or lender'. SSLC counsel (Danny) will say an advisory mandate is not a financing agreement. Strengthen by attaching the executed FNEX agreement PLUS a written indication from the note/PIPE investor or the shell sponsor naming the SSLC asset purchase as an approved use of proceeds. [Confirm the FNEX agreement is countersigned; D-7281974 sent it 10/6.]")
B("Investors' stated condition (your 10/2 SSLC remarks): Scorpius stays OUT of the RTO perimeter and Exos must hold a perpetual manufacturing license. So the acquisition is funded from Exos-only proceeds after closing, as a bolt-on, not consolidated into the RTO story.")
B("Timing gap: 90 days of exclusivity from ~10/8 ends ~1/6/2027; the RTO is ~4–5 months. You need the §3 'not unreasonably withhold an extension' clause, so lead with good-faith progress.")
H("3. Options (ranked)")
H("Option A — Invoke §3 exclusivity at the 2025 price (RECOMMENDED lead)",2)
B("Send notice: Exos has entered into an exclusive financing agreement; request SSLC assign 90-day exclusivity under §3, with extensions while financing works in good faith.")
B("Price = the 2025 board-approved $3.36M commitment (cash-free/debt-free). Pro: contractual, already approved, sidesteps the ROFR vote. Con: Bob already objects to the old price; the trigger argument depends on the financing evidence.")
H("Option B — A + price bridge (best odds with Jim/Bob)",2)
B("Same notice, but offer consideration of $2.51M cash at close + earn-outs (IM tank revenue, revenue milestones, listed Exos stock post-RTO). Answers Jim ('Scorpius has value') without raising the cash the investors fund. Insider debt (Microcosm/Wertz) paid at face at close = Wertz's personal path to yes.")
B("EAI units (up-front equity component). 1.0% of EAI units (~$1.7M at 409A) issued at financing close as part of Exos's Rule 504 Reg D offering, at the 409A value. These are restricted securities bearing a legend — not freely tradeable at issuance. See lockup detail below.")
H("Option B — EAI Unit Lockup & Liquidity",3)
B("Restricted securities. The EAI units are issued under Rule 504, Regulation D and bear a restrictive legend. Rule 504 reference: https://www.sec.gov/resources-small-businesses/exempt-offerings/exemption-limited-offerings-not-exceeding-10-million-rule-504-regulation-d")
B("Lockup mirrors Exos principals. Same lockup terms as Exos principals under the RTO documents.")
B("Rule 144 resale (17 CFR 230.144(d); https://www.ecfr.gov/current/title-17/chapter-II/part-230/section-230.144). Holding period: 6 months if issuer is SEC reporting; 1 year if not. Exos is not currently reporting. The 6-month clock runs only AFTER the RTO makes the successor entity reporting.")
B("RTO structure: preferred at close. Per the Ainigma/FNEX RTO structure, founders receive unregistered non-voting preferred at RTO close — converts to common and becomes liquid only after (i) a post-close shareholder vote (proxy ~30 days post-close) and (ii) effective resale registration (S-1/S-3). [Sources: Ainigma_RTO_Board_Brief_2026-09-04.md:16; Ainigma_RTO_Anticipated_Board_Questions_2026-09-08.md:36,44.] EAI units follow this same path.")
B("Liquidity timeline (all dates targeted, not assured): Board acceptance (D+0, committed) → Financing close, units issued (targeted Q1 FY27; 1-yr Rule 144 clock starts) → Targeted RTO close (~6 months post-financing) → Conversion vote + resale registration effective (~30–90 days post-RTO) → Rule 144 eligibility: 6-month path after reporting status; 1-year path if non-reporting at issuance date.")
H("Option B — Projected Post-RTO Value (Projection, Not a Promise)",3)
B("CAUTIONARY STATEMENT: Forward-looking projection based on management assumptions (RTO completion, listing valuation, ~30% dilution). Not a guarantee or promise of value; actual results may differ materially. The RTO may not close. SEC Rule 10b-5 (17 CFR 240.10b-5; https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.10b-5) antifraud rules apply. Projections must have a reasonable basis.")
B("1.0% up-front EAI alone — pre-dil at RTO listing: Low $200M → $2.00M; Base $250M → $2.50M; High $300M → $3.00M. Post-dilution (~30%): Low $1.40M / Base $1.75M / High $2.10M. Versus 409A issuance value: ~$1.70M. Plus earn-out stock: 0.0% / +$424K / +$848K additional at listing.")
H("Option C — A/B + pre-cliff working-capital bridge (strongest lever)",2)
B("Offer, subject to financing and disinterested-director approval, a secured bridge or prepaid BLK3 tank PO of $300–700K from pre-RTO note proceeds, credited against the price, in exchange for exclusivity now. Turns Exos into the rescuer. Use only SSLC's own disclosed numbers.")
H("Option D — Fallback, run in parallel regardless",2)
B("Commission-only (15% Sales Commission Agreement, D-7281978) + 18% equity + manufacturing license. Keep it moving so a 'no' on exclusivity doesn't cost you the commission paper.")
H("4. Guardrails")
B("You sit on SSLC's board: recuse from SSLC's vote; send as Exos CEO; base the ask on the signed contract, not SSLC board deliberations. No distress/bankruptcy language anywhere.")
B("Don't lead with the He-tank PO 395 default (due 9/24/2025, still leaking) — keep the customer hat in reserve.")
B("One valuation story: standalone SSLC value is modest; value is created inside a funded Exos.")
B("You leave for Japan 10/8: either send today or name an Exos officer to sign while away.")
H("5. Draft message — to Jim Wertz, cc SSLC board (Options A+B; C held for the follow-up)")
for t in [
"Subject: Exos — Exclusivity under our May 2025 Asset Acquisition Agreement",
"Jim, Markus, Bob,",
"Thank you for the time on the license and ROFR. I understand the board's decision on the ROFR and I'm not asking you to revisit it.",
"I'm writing about our separate Asset Acquisition Agreement, which the SSLC board approved on May 2, 2025 and we both signed on May 13, 2025. Section 3 provides that SSLC assigns Exos exclusivity once Exos has entered into an agreement with a financing source capable of funding the transaction, with 90 days to fund and close and extensions not unreasonably withheld while we work in good faith.",
"Exos has now entered into an exclusive financing agreement with Ainigma Capital / FNEX Capital for our go-public transaction and PIPE. The acquisition of SSLC's assets is an approved use of proceeds. [Attach: executed FNEX agreement summary + investor/use-of-proceeds letter.]",
"Under Section 3, I'm asking SSLC to confirm Exos's 90-day exclusivity, starting on the date of your confirmation.",
"On value, I heard Jim's point that Scorpius has more value today than in 2021. We'll honor the cash terms in the 2025 Agreement and we're open to adding consideration tied to SSLC's own growth — an earn-out on IM tank deliveries and/or Exos stock after listing — so stockholders share in the upside. SSLC's debts, including the Microcosm and Wertz notes, would be paid at face at closing.",
"I'm in Japan for the next three weeks. [Exos officer] can sign for Exos while I'm away, and I'm available by phone. I'll recuse from SSLC's deliberations on this. Could the board confirm exclusivity by [date]?",
"Best regards,", "John Quinn", "Cofounder & CEO, Exos Aerospace Systems & Technologies, Inc."]:
    P(t)
H("6. What I need from you")
B("Go/no-go: Option A, A+B (recommended), or A+B+C.")
B("Confirm FNEX agreement is countersigned and whether an investor/sponsor use-of-proceeds letter is obtainable this week.")
B("Name the Exos officer who signs while you're in Japan; confirm reply-by date.")
d.save(OUT); print(OUT)
