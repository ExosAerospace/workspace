# Paying Japan-Based Contractors in JPY: Research Notes

Prepared 2026-10-15 for Jon (CEO), Exos Aerospace. These are internal working notes and not tax or legal advice. Have the CPA confirm the compliance section before the first payment.

Assumptions: Exos is a US company. It uses BambooHR (HR plus US payroll), QuickBooks Online (QBO) and BILL Spend & Expense (Divvy cards). The contractors are individuals or entities resident in Japan who perform the work in Japan.

---

## 1. Recommendation

**Primary rail: Wise Business. Pay contractor invoices in JPY to the contractor's domestic (zengin) Japanese bank account.**
- Wise charges a one-time **$31 setup fee** and converts at the **mid-market rate**. Its send fees **start at 0.23% and vary by currency** ([Wise Business pricing](https://wise.com/us/pricing/business)). Couldn't verify the exact USD to JPY percentage because the live calculator is JS-rendered. Get a quote in-app before the first payment.
- For JPY sent to a domestic Japanese bank and branch code, funds usually arrive about **1 working day after Wise receives and converts them**, and conversion can take up to 2 working days. Wise also says domestic accounts are "faster and cheaper" than sending by Swift ([Wise JPY guide](https://wise.com/help/articles/2932156/guide-to-jpy-transfers)). The per-transfer limit is 150M JPY for senders outside Japan (same source).
- It syncs with QBO. Bills paid in Wise are marked paid in QBO and fees are posted to Bank Charges. **QBO Multicurrency must be on** for this ([Wise help: connect QuickBooks](https://wise.com/help/articles/2978059/connect-your-wise-account-with-quickbooks)).
- **Trade-off to decide first:** Intuit says QuickBooks Bill Pay is **not compatible with Multicurrency**, and **once Multicurrency is on, it can't be turned off** ([Intuit Multicurrency article](https://quickbooks.intuit.com/learn-support/en-us/help-article/multicurrency/learn-multicurrency-quickbooks-online/L5krkKQi8_US_en_US)). If Exos uses QBO Bill Pay for US vendors today, the CPA needs to sign off before Multicurrency is enabled.
- Wise has no contract or tax-form tooling. Exos keeps the W-8BEN, contract and screening records itself (see the checklist in section 5).

**Backup: BambooHR Contractor Management, powered by Remote.** Use this if Exos wants contracts, invoice approval and payment inside BambooHR, or if the number of contractors grows.
- It is a paid add-on announced June 29, 2026. BambooHR says it covers hiring and paying contractors in **200+ countries**, generating **country-specific contracts with IP and invention-assignment terms**, and paying **"in their preferred currencies"** ([BambooHR press release](https://www.bamboohr.com/about-bamboohr/press-release/bamboohr-contractor-management-remote)).
- BambooHR does not publish an add-on price. Couldn't verify it; ask for a demo or quote. Standalone Remote Contractor Management is **$29 per contractor per month** and includes "compliance screening, expenses, and 1099-NEC generation" ([Remote pricing](https://remote.com/pricing)).
- Remote's FX is the "Remote FX rate," which "reflects risks… Remote's costs, and market benchmarks". That means there is a spread over mid-market ([Remote pricing FAQ](https://remote.com/en-ie/pricing)).

BILL AP is also a reasonable alternative because Exos already uses BILL through Divvy, and BILL syncs with QBO. FX wires and Local Transfers are free, but BILL's exchange rate includes a markup and AP seats cost money. See the comparison table.

---

## 2. BambooHR: what it does itself vs. what partners do

| Capability | BambooHR itself | Via partner |
|---|---|---|
| Core payroll | **US-only.** "BambooHR Payroll is designed to pay US-based employees and includes US federal, state, and local tax filing" ([BambooHR Payroll FAQ](https://www.bamboohr.com/platform/payroll)) | n/a |
| Pay international **contractors** in local currency (e.g. JPY) | Yes, but only through the **Contractor Management add-on, which is powered by Remote**. It is embedded in BambooHR, and Remote handles the payment and compliance engine ([press release, 2026-06-29](https://www.bamboohr.com/about-bamboohr/press-release/bamboohr-contractor-management-remote); [Marketplace listing](https://www.bamboohr.com/integrations/listings/bamboohr-global-employment)) | Remote, Deel and others through Marketplace integrations |
| International **employees** without an entity | BambooHR Employer of Record, **powered by Remote**, 90+ countries ([Marketplace listing](https://www.bamboohr.com/integrations/listings/bamboohr-global-employment)) | Deel EOR, Remote EOR, etc. |
| Local payroll where you have an entity | On-platform Xero Payroll integration for **UK, AU and NZ only** ([press release, Dec 2025](https://www.bamboohr.com/about-bamboohr/press-release/xero-payroll-integrations)). **Japan is not listed.** | "Local Payroll Bridge" plus partners: Remote, Deel, Papaya, Blue Marble, Oyster, Pay Captain, Payroll Harmony, Worklinks ([Global Employment page](https://www.bamboohr.com/platform/global-employment)); Multiplier ([listing](https://www.bamboohr.com/integrations/listings/multiplier)) |
| Deel integration | Data sync only | Deel Global Payroll and EOR. Payroll data flows from BambooHR to Deel and paystubs flow back ([Deel listing](https://www.bamboohr.com/integrations/listings/deel); [Deel help](https://help.letsdeel.com/hc/en-gb/articles/11206270029969-How-To-Integrate-BambooHR-for-Global-Payroll)) |
| Papaya integration | Data sync only (HR and PTO, pay rate plus currency) | Papaya runs the payroll ([Papaya connector](https://www.papayaglobal.com/connectors/bamboohr)) |

**Bottom line:** BambooHR Payroll cannot pay anyone in Japan or pay in JPY. The only BambooHR-branded way to pay a Japan contractor in JPY is the Contractor Management add-on, and Remote runs it. Every other option is a third-party partner, and BambooHR only syncs data with it.

---

## 3. Comparison table: paying a Japan contractor in JPY

| Rail | Fixed cost | Per-payment fee | FX | Pays JPY to Japanese bank? | Speed | Compliance features | QBO fit |
|---|---|---|---|---|---|---|---|
| **Wise Business** | $31 one-time ([pricing](https://wise.com/us/pricing/business)) | From 0.23% and varies by currency; exact USD to JPY couldn't verify ([pricing](https://wise.com/us/pricing/business)) | Mid-market, no markup (same source) | **Yes, domestic (bank and branch code).** Swift is also possible but slower and may lose correspondent fees ([JPY guide](https://wise.com/help/articles/2932156/guide-to-jpy-transfers)) | About 1 working day after conversion; conversion up to 2 working days (same) | None (no contracts or W-8 collection) | Bill-pay sync; needs Multicurrency ([help](https://wise.com/help/articles/2978059/connect-your-wise-account-with-quickbooks)) |
| **QBO Bill Pay** | Included with QBO | n/a | n/a | **No.** Intuit staff say Bill Pay "does not offer the option to pay international vendors" ([QB Community, Intuit staff](https://quickbooks.intuit.com/community/payments-3/paying-an-international-vendor-in-us-18482)), and it is not compatible with Multicurrency ([Intuit](https://quickbooks.intuit.com/learn-support/en-us/help-article/multicurrency/learn-multicurrency-quickbooks-online/L5krkKQi8_US_en_US)) | n/a | n/a | n/a |
| **BILL AP (bill.com)** | AP plans start at **$49/user/month** ([BILL blog](https://www.bill.com/blog/credit-cards-are-fees-eating-away-your-profit)) | International FX wire or Local Transfer: **free (exchange rate applies)**. USD wire: $19.99 ([BILL pricing](https://www.bill.com/pricing)) | BILL rate = "base rate + markup" ([BILL help snippet](https://help.bill.com/direct/s/article/000004057)). Couldn't verify the markup size | Local-currency payments in 130+ countries ([BILL Intl Payments](https://www.bill.com/product/international-payments)). Couldn't verify JPY or Japan on the country list because the help page would not load | Local Transfer is "up to 4 days faster than wire… often same business day" (same) | 1099 e-filing, approvals. No foreign-contractor contract tooling found | Native QBO sync (same) |
| **Remote Contractor Mgmt** (standalone, or embedded in BambooHR) | **$29/contractor/month**; Plus $99; Contractor of Record $325 ([Remote pricing](https://remote.com/pricing)) | Included | "Remote FX rate" includes costs and risk, so a spread ([FAQ](https://remote.com/en-ie/pricing)) | Pays contractors in local currency in 190+ countries (same) | Couldn't verify | Localized contracts, compliance screening, expenses, invoice approval; Plus adds $100K indemnity (same) | Couldn't verify a native QBO sync |
| **Deel Contractor** | **$49/contractor/month**; Contractor of Record $325 ([Deel pricing](https://www.deel.com/pricing)) | Contractor-side withdrawal fees vary by method. Local bank transfer is "no cost to the contractor," 1–5 business days ([Deel blog](https://www.deel.com/blog/contractor-payment-withdrawal-options-on-deel)) | FX applies when the withdrawal currency differs from the contract currency ([Deel help](https://help.letsdeel.com/hc/en-gb/articles/14391381019537-About-Withdrawal-Fees-and-Withdrawal-Minimums)). Couldn't verify the markup | Payments in 120+ currencies ([pricing](https://www.deel.com/pricing)). Couldn't verify JPY local payout specifically | 1–5 business days for local bank transfer | Contracts, tax-form collection, classification ([pricing](https://www.deel.com/pricing)) | BambooHR integration exists ([listing](https://www.bamboohr.com/integrations/listings/deel)) |
| **Payoneer** | Couldn't verify (the official fee page returned 404) | Payoneer's own blog says "to a bank account (not Payoneer): up to 3%" ([Payoneer blog](https://www.payoneer.com/resources/how-to-reduce-payoneer-costs-tips-and-strategies)) | Currency conversion "0.5% to 3.5%" (same) | Holds JPY balances; pays suppliers in local currency in 190+ countries ([Payoneer](https://www.payoneer.com/wholesale-and-trade)) | Couldn't verify | Minimal for this use | Couldn't verify |
| **Bank SWIFT wire** | n/a | Average outgoing international wire fee at the top 10 US banks is **about $38** (FDIC data as cited by BILL) ([BILL](https://www.bill.com/product/global-expense-management)). Deel puts SWIFT at $15–50+ plus intermediary fees ([Deel glossary](https://www.deel.com/glossary/local-bank-transfer)) | Bank FX spread, usually undisclosed | Yes (Swift/BIC), but intermediary banks may deduct fees | "Often 3–5 days" ([Wise blog](https://wise.com/us/blog/wise-vs-international-bank-transfers), vendor source) | None | Manual |
| **Divvy / BILL Spend & Expense** | $0/user/month ([BILL pricing FAQ](https://www.bill.com/pricing)) | n/a | "Competitive exchange rates" ([BILL S&E Intl](https://www.bill.com/product/global-expense-management)) | Reimbursements are in local currency and ERP sync is in USD (same). BILL also claims "global reimbursements in 70+ countries in employees' local currency" ([BILL blog](https://bill.com/blog/create-employee-reimbursement-plan)). Couldn't verify that **non-employee contractors** in Japan qualify; this likely needs the International add-on or demo | Couldn't verify | Receipt capture, approvals | Syncs in USD |

---

## 4. Expense reimbursement for foreign contractors

**Recommended practice**
1. **Put reimbursable expenses in the contract.** Require pre-approval and **itemized receipts in JPY**, billed as separate line items on the contractor's monthly invoice.
2. **Pay reimbursements with the invoice, in JPY, on the same rail** (Wise). There is then one transfer, one FX event, and one bill in QBO with a "Reimbursable expense" line separate from "Services". The IRS does not mandate this. It is the cleanest operational practice because the contractor gets back exactly the yen spent and Exos carries the FX.
   - Don't use Divvy reimbursement for non-employee contractors until BILL confirms that contractors in Japan are supported. Couldn't verify this.
3. **Use the rate actually paid.** Book the USD cost at the Wise conversion rate on the payment date and keep the Wise receipt. The IRS requires translating foreign-currency items "using the exchange rate prevailing when you receive, pay, or accrue the item" ([IRS: Foreign currency and exchange rates](https://www.irs.gov/individuals/international-taxpayers/foreign-currency-and-currency-exchange-rates)). The IRS "has no official exchange rate" and "generally… accepts any posted exchange rate that is used consistently" ([IRS: Yearly average rates](https://www.irs.gov/individuals/international-taxpayers/yearly-average-currency-exchange-rates)).
4. **Pick one documented benchmark** for policy checks, accruals, or when there is no actual conversion:
   - **Federal Reserve H.10** gives daily noon buying rates and includes JPY ([H.10 current](https://www.federalreserve.gov/releases/h10/current)). This is the most defensible daily public source.
   - **Treasury Reporting Rates of Exchange** are quarterly and meant for government reporting ([Treasury Fiscal Data](https://fiscaldata.treasury.gov/datasets/treasury-reporting-rates-exchange)). They are fine for budgeting but too coarse for transaction-date conversion.
   - **IRS yearly average rates**: JPY was 151.353 in 2024 and 149.632 in 2025 ([IRS](https://www.irs.gov/individuals/international-taxpayers/yearly-average-currency-exchange-rates)). Use these only for annual estimates.
   - OANDA is commercially acceptable under the IRS consistency standard. The IRS page lists "external resources," but couldn't verify that OANDA is named there. Prefer H.10 for a government source.
5. **Policy line to adopt:** "Foreign-currency expenses are recorded at the actual conversion rate of the payment; if not yet paid, at the Federal Reserve H.10 rate for the transaction date (or prior business day)."

---

## 5. Compliance checklist (per contractor, before the first payment)

- [ ] **Form W-8BEN (individual) or W-8BEN-E (entity) on file.** The W-8BEN goes to the payer "if you are a foreign person… whether or not you are claiming a reduced rate of, or exemption from, withholding" ([IRS: About W-8BEN](https://www.irs.gov/forms-pubs/about-form-w-8-ben)). W-8BEN-E documents a foreign entity's chapter 3 and 4 status ([IRS: About W-8BEN-E](https://www.irs.gov/forms-pubs/about-form-w-8-ben-e)). Without valid documentation the payer must generally **presume a US person** ([IRS TE/GE deck](https://www.irs.gov/pub/irs-tege/withholding_and_reporting_of_income_tax_on_non-wage.pdf)). Flag any W-8 that shows a US address, because Pub 515 treats it as unreliable ([Pub 515](https://www.irs.gov/publications/p515)).
- [ ] **Confirm where the work is performed.** "The place where the services are performed determines the source of the income, regardless of where the contract was made, the place of payment, or the residence of the payer" ([IRS Pub 515](https://www.irs.gov/publications/p515)).
  - **All work done in Japan:** the income is foreign-source. There is no US withholding and no Form 1042-S, because 1042-S covers *US-source* income ([1042-S instructions](https://www.irs.gov/instructions/i1042s)). There is also **no 1099-NEC**; the IRS instructions say "use Form 1042-S… for payments to nonresident aliens" ([1099-MISC/NEC instructions](https://www.irs.gov/instructions/i1099mec)).
  - **Any work done in the US** (for example, a trip to Greenville): that portion is US-source and must be allocated by days ([Pub 515](https://www.irs.gov/publications/p515)). Withhold **30% unless a treaty exemption is documented**, and report on **Form 1042-S / 1042** "even if the entire amount… is exempt under a tax treaty" ([IRS: NRA withholding page](https://www.irs.gov/individuals/international-taxpayers/federal-income-tax-withholding-and-reporting-on-other-kinds-of-us-source-income-paid-to-nonresident-aliens)).
- [ ] **US–Japan treaty.** A Japan resident's independent-contractor income for work in the US falls under **Article 7 (Business Profits)**. It is exempt from US tax unless the contractor has a US permanent establishment ([IRS Pub 901](https://www.irs.gov/publications/p901)). Individuals claim this on **Form 8233** for US-performed services ([IRS NRA page](https://www.irs.gov/individuals/international-taxpayers/federal-income-tax-withholding-and-reporting-on-other-kinds-of-us-source-income-paid-to-nonresident-aliens)). Only relevant if work happens in the US.
- [ ] **OFAC sanctions screening.** Screen the contractor name, any entity, and bank-account holder name in the [OFAC Sanctions List Search](https://ofac.treasury.gov/sanctions-list-search-tool), which covers the SDN and Non-SDN consolidated lists. Also screen against the **Consolidated Screening List** of Commerce, State and Treasury export lists ([OFAC: CSL reference](https://ofac.treasury.gov/additional-ofac-resources/other-non-treasury-sanctions-related-resources)). Save dated screenshots. Exos already runs CSL screening; reuse that workflow.
- [ ] **Export control (Exos-specific).** If a Japan contractor will receive ITAR or EAR technical data, the Empowered Official must clear it before work starts. Paying them is separate from export-authorizing them.
- [ ] **Contract** with IP/invention assignment, an independent-contractor clause, a JPY rate, the expense policy (section 4), and a work-location clause (Japan only unless pre-approved).
- [ ] **QBO setup:** decide on Multicurrency (irreversible, and it breaks QBO Bill Pay), then create a JPY vendor per contractor.
- [ ] **Out of scope, couldn't verify:** Japanese-side obligations such as consumption tax or invoice-system registration, and Japanese worker-misclassification risk. Remote Contractor Management Plus or Contractor of Record covers this if needed.

---

## 6. Full source list

**BambooHR / partners**
- https://www.bamboohr.com/platform/payroll (US-only FAQ)
- https://www.bamboohr.com/about-bamboohr/press-release/bamboohr-contractor-management-remote (2026-06-29)
- https://www.bamboohr.com/integrations/listings/bamboohr-global-employment
- https://www.bamboohr.com/platform/global-employment
- https://www.bamboohr.com/about-bamboohr/press-release/xero-payroll-integrations (2025-12-04)
- https://www.bamboohr.com/integrations/listings/remote
- https://www.bamboohr.com/integrations/listings/deel
- https://www.bamboohr.com/integrations/listings/multiplier
- https://help.letsdeel.com/hc/en-gb/articles/11206270029969-How-To-Integrate-BambooHR-for-Global-Payroll
- https://www.papayaglobal.com/connectors/bamboohr

**Payment rails**
- https://wise.com/us/pricing/business
- https://wise.com/help/articles/2932156/guide-to-jpy-transfers
- https://wise.com/help/articles/2978059/connect-your-wise-account-with-quickbooks
- https://wise.com/us/blog/wise-vs-international-bank-transfers
- https://quickbooks.intuit.com/learn-support/en-us/help-article/multicurrency/learn-multicurrency-quickbooks-online/L5krkKQi8_US_en_US
- https://quickbooks.intuit.com/community/payments-3/paying-an-international-vendor-in-us-18482
- https://www.bill.com/pricing
- https://www.bill.com/product/international-payments
- https://help.bill.com/direct/s/article/000004057
- https://help.bill.com/direct/s/article/360007172671 (country list; couldn't load)
- https://www.bill.com/product/global-expense-management
- https://bill.com/blog/create-employee-reimbursement-plan
- https://www.bill.com/blog/credit-cards-are-fees-eating-away-your-profit
- https://remote.com/pricing
- https://remote.com/en-ie/pricing
- https://www.deel.com/pricing
- https://www.deel.com/blog/contractor-payment-withdrawal-options-on-deel
- https://help.letsdeel.com/hc/en-gb/articles/14391381019537-About-Withdrawal-Fees-and-Withdrawal-Minimums
- https://www.deel.com/glossary/local-bank-transfer
- https://www.payoneer.com/wholesale-and-trade
- https://www.payoneer.com/resources/how-to-reduce-payoneer-costs-tips-and-strategies

**IRS / Treasury / Fed**
- https://www.irs.gov/forms-pubs/about-form-w-8-ben
- https://www.irs.gov/forms-pubs/about-form-w-8-ben-e
- https://www.irs.gov/publications/p515
- https://www.irs.gov/instructions/i1042s
- https://www.irs.gov/instructions/i1099mec
- https://www.irs.gov/individuals/international-taxpayers/federal-income-tax-withholding-and-reporting-on-other-kinds-of-us-source-income-paid-to-nonresident-aliens
- https://www.irs.gov/publications/p901
- https://www.irs.gov/pub/irs-tege/withholding_and_reporting_of_income_tax_on_non-wage.pdf
- https://www.irs.gov/individuals/international-taxpayers/foreign-currency-and-currency-exchange-rates
- https://www.irs.gov/individuals/international-taxpayers/yearly-average-currency-exchange-rates
- https://www.federalreserve.gov/releases/h10/current
- https://fiscaldata.treasury.gov/datasets/treasury-reporting-rates-exchange
- https://ofac.treasury.gov/sanctions-list-search-tool
- https://ofac.treasury.gov/additional-ofac-resources/other-non-treasury-sanctions-related-resources
