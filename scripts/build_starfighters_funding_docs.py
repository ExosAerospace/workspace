#!/usr/bin/env python3
"""
Build Exos_Starfighters_Funding_Structure_Options_2026-10-06.docx  (internal)
     Exos_Starfighters_Proposal_DRAFT_2026-10-06.docx              (external IOI)
     Exos_Starfighters_MeetingBrief_Tim_2026-10-06.docx            (1-page brief)
All three on PRIMARY letterhead via python-docx.
Run: PYTHONNOUSERSITE=1 python3.12 scripts/build_starfighters_funding_docs.py
"""
import os, copy
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

WS     = os.path.expanduser("~/.openclaw/workspace")
LH     = os.path.join(WS, "assets", "EXOS_Letterhead_Greenville_TX_PRIMARY.docx")
DRAFTS = os.path.join(WS, "drafts")

NAVY  = RGBColor(0x0A, 0x3D, 0x7C)
DARK  = RGBColor(0x1A, 0x1A, 0x1A)
RED   = RGBColor(0xC0, 0x00, 0x00)
GRAY  = RGBColor(0x55, 0x55, 0x55)


# ── helpers ──────────────────────────────────────────────────────────────────

def new_doc():
    return Document(LH)


def h1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text.upper())
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = NAVY
    run.font.name = "Calibri"
    # underline rule
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single")
    bot.set(qn("w:sz"), "4")
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), "0A3D7C")
    pBdr.append(bot)
    pPr.append(pBdr)
    return p


def h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(2)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(11)
    run.font.color.rgb = NAVY
    run.font.name = "Calibri"
    return p


def body(doc, text, indent=0, bold=False, italic=False, color=None, size=10):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(3)
    if indent:
        p.paragraph_format.left_indent = Inches(indent * 0.25)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.name = "Calibri"
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color or DARK
    return p


def bullet(doc, text, level=1, bold_prefix=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after  = Pt(1)
    p.paragraph_format.left_indent  = Inches(0.25 * level)
    p.paragraph_format.first_line_indent = Inches(-0.18)
    rb = p.add_run("•  ")
    rb.font.size = Pt(10)
    rb.font.name = "Calibri"
    rb.font.color.rgb = NAVY
    if bold_prefix:
        r1 = p.add_run(bold_prefix + " ")
        r1.bold = True
        r1.font.size = Pt(10)
        r1.font.name = "Calibri"
        r1.font.color.rgb = DARK
    r2 = p.add_run(text)
    r2.font.size = Pt(10)
    r2.font.name = "Calibri"
    r2.font.color.rgb = DARK
    return p


def divider(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run("─" * 80)
    run.font.size = Pt(8)
    run.font.color.rgb = GRAY
    return p


def warning(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run("⚠  " + text)
    run.bold = True
    run.font.size = Pt(9)
    run.font.name = "Calibri"
    run.font.color.rgb = RED
    return p


def kv(doc, key, value, note=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after  = Pt(1)
    r1 = p.add_run(key + ":  ")
    r1.bold = True
    r1.font.size = Pt(10)
    r1.font.name = "Calibri"
    r1.font.color.rgb = NAVY
    r2 = p.add_run(value)
    r2.font.size = Pt(10)
    r2.font.name = "Calibri"
    r2.font.color.rgb = DARK
    if note:
        r3 = p.add_run("  [" + note + "]")
        r3.italic = True
        r3.font.size = Pt(9)
        r3.font.name = "Calibri"
        r3.font.color.rgb = GRAY
    return p


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 1 — INTERNAL FUNDING STRUCTURE OPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def build_internal():
    doc = new_doc()

    # Title block
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_before = Pt(6)
    r = tp.add_run("EXOS AEROSPACE — STARFIGHTERS SPACE (FJET)\nFUNDING STRUCTURE OPTIONS")
    r.bold = True; r.font.size = Pt(15); r.font.color.rgb = NAVY; r.font.name = "Calibri"

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sp.add_run("INTERNAL — FOR JON QUINN / COUNSEL REVIEW ONLY  |  October 6, 2026")
    r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GRAY; r.font.name = "Calibri"

    # ── SECTION 0: FJET SNAPSHOT ──────────────────────────────────────────────
    h1(doc, "0. Starfighters Space (FJET) — Current Facts")

    body(doc, "All figures from primary sources (SEC EDGAR, MarketBeat). Unverified items flagged.", italic=True, color=GRAY)

    kv(doc, "Exchange / Ticker",  "NYSE American: FJET  (listed December 2025)")
    kv(doc, "CEO",                "Tim Franta — salary raised to $350K/yr effective Sep 28, 2026",
       note="SEC 8-K Oct 2 2026  https://capedge.com/company/1947016/filings")
    kv(doc, "CFO",                "David Whitney — salary raised to $300K/yr effective Sep 28, 2026")
    kv(doc, "Share price (10/6/26)", "$1.62–$1.63  |  52-wk range $1.57–$31.50  (−86% YTD)",
       note="MarketBeat https://www.marketbeat.com/stocks/NYSEAMERICAN/FJET/chart")
    kv(doc, "Market cap (10/6/26)", "≈ $89.9M")
    kv(doc, "Shares outstanding",  "≈ 55M (current Yahoo Finance);  44.2M at March 31, 2026",
       note="Yahoo Finance key stats https://finance.yahoo.com/quote/FJET/key-statistics")
    kv(doc, "Float",               "37.33M shares  |  Insiders 26.6%  |  Institutions 18.9%")
    kv(doc, "Key institutional holders",
       "Citadel Advisors 5.43% (2.99M shs, Aug 24);  BlackRock 3.86% (2.12M shs, Jun 30)",
       note="Investing.com https://www.investing.com/equities/starfighters-space")
    kv(doc, "Last capital raise",
       "$17.5M Reg D 506(b) private placement, May 22/27, 2026 — 5.22M shares @ $3.35;  Cantor Fitzgerald placement agent",
       note="SEC Form D filed Jun 4 2026  https://www.sec.gov/cgi-bin/browse-edgar")
    kv(doc, "H1 2026 net loss",   "$15.7M  |  operating cash burn $10.1M",
       note="10-Q filed Aug 19 2026  https://www.sec.gov/Archives/edgar/data/1947016/000106299326004518/form10q.htm")
    kv(doc, "Cash at Mar 31, 2026", "$2.14M (cash + restricted)  |  Total assets $26.34M  |  Equity $22.43M",
       note="10-Q filed May 20 2026  https://www.sec.gov/Archives/edgar/data/1947016/000106299326002803/form10q.htm")
    kv(doc, "Aircraft deposit impairment",
       "$5.15M impaired in H1 2026 — program-cost indicator for STARLAUNCH buildout")
    kv(doc, "STARLAUNCH program",
       "STARLAUNCH 1 wind tunnel testing complete (Mach 0.85 / Mach 1.3, no adverse aero interactions, Jan 2026). "
       "Preparing next R&D phase. ILS partnership for mission design / range integration (Aug 2026).",
       note="SEC 8-K Jan 21 2026")
    kv(doc, "Blackstar Orbital partnership",
       "Technical Interchange Agreement for reusable hypersonic 'SpaceDrone' captive-carry flight tests; "
       "Q4 FY26 targeted",
       note="Finviz news Oct 1 2026  https://finviz.com/news/340916")
    kv(doc, "Auditor",
       "Changed to CBIZ CPAs P.C. effective July 22, 2026 — prior auditor departed",
       note="SEC 8-K Jul 2026")

    warning(doc, "FJET going-concern disclosures are active in its 10-Q. High stock-based comp ($4.5M H1), "
            "significant cash burn, and material weakness remediation ongoing. Any deal must account for "
            "FJET's own capital needs and NYSE American continued-listing requirements.")

    h2(doc, "Existing Exos–Starfighters Relationship")
    bullet(doc, "MOU under discussion (Task #1782 / 23 emails with Tim Franta as of Sep 28, 2026); "
           "draft covers teaming, BD, AEDC Velocity Alliance consortium (Exos prime / Starfighters sub).")
    bullet(doc, "Mutual NDA executed. AEDC Velocity Alliance RFWP roster submitted with Starfighters.")
    bullet(doc, "September 2026 investor update included AEDC/Starfighters teaming angle.")
    bullet(doc, "Historical: Exos–Starfighters discussion letter on file (Sep 11, 2026).")

    # ── SECTION 1: EXOS CONTEXT ───────────────────────────────────────────────
    h1(doc, "1. Exos Funding Context as of October 6, 2026")

    body(doc, "Active funding paths (running in parallel per project_rto_rollup_capital_path):")
    kv(doc, "A. Reg D Rule 504 offering",
       "Up to $25M staged at ≈$10M/yr. No public solicitation. Counsel-confirmed structure. "
       "Rule 504 rolls 12-month cap: $10M total (see https://www.sec.gov/smallbusiness/exemptofferings/rule504). "
       "Existing 504 sales + Capital Bridge consume some of this capacity — exact remaining headroom requires Counsel confirmation.")
    kv(doc, "B. Japan Reg S round",
       "EAI unit structure, offshore, separate from U.S. 504. K.K. wholly owned. Toshihisa Kumazawa leading BD.")
    kv(doc, "C. Ainigma RTO",
       "Series A worklist PAUSED pending Ainigma transaction resolving. Any RTO / reverse-merger deal with FJET "
       "MUST be reviewed against the Ainigma term sheet for exclusivity clauses before proceeding.")
    kv(doc, "D. Scorpius commission-only (NEW — tonight 10/6)",
       "ROFR expired. Commission-only arrangement at 15%, no acquisition obligation. "
       "D-7281978 covers SSLC Sales Commission Agreement. Exos retains 18% equity in Scorpius.")
    kv(doc, "Exos 409A valuation", "$169.7M  (as of March 31, 2026)")
    kv(doc, "Series A target",     "$10M–$25M  (D1–D4 figures locked Aug 13, 2026)")
    kv(doc, "BLK3 first flight",   "Early 2027 (FAA license March 2026; never cite a specific month externally)")

    warning(doc, "Before executing any structure involving an RTO / reverse merger / public shell, "
            "confirm with Counsel whether the Ainigma term sheet contains an exclusivity or no-shop provision "
            "that would restrict Exos from entering such a transaction. This is a go/no-go gate for Structures B and C below.")

    # ── SECTION 2: STRUCTURE A ────────────────────────────────────────────────
    h1(doc, "2. Structure A — Strategic Equity Investment by FJET in Exos")

    warning(doc, "RULE 504 CAPACITY ISSUE — READ BEFORE PROCEEDING: Rule 504 caps total raises at $10M "
            "per rolling 12-month period (SEC Rule 504: https://www.sec.gov/smallbusiness/exemptofferings/rule504). "
            "Exos's existing 504 sales and Capital Bridge already consume some of that capacity. A $5–$10M FJET "
            "check could consume all remaining 504 headroom and block other 504 sales for the rest of the window. "
            "FJET is also a public institutional company — not an existing-relationship individual — which creates "
            "additional considerations under the no-general-solicitation requirement. "
            "Two sub-options are set out below; Counsel must confirm the chosen path before proceeding.")

    h2(doc, "Concept")
    body(doc, "FJET deploys capital into Exos at Exos's current 409A valuation ($169.7M pre-money). FJET becomes "
         "a strategic minority investor. No change in Exos control or governance. The securities exemption "
         "for this investment depends on remaining 504 capacity (Sub-Option A1) or must move to a separate "
         "Rule 506(b) offering (Sub-Option A2).")

    h2(doc, "Sub-Option A1 — Size Within Remaining 504 Capacity")
    bullet(doc, "Counsel confirms the 12-month rolling balance available under the current 504 offering "
           "after accounting for all prior sales and Capital Bridge commitments. FJET's check is sized "
           "to stay within that balance (likely well under $5M; exact figure TBD).")
    bullet(doc, "Advantage: no new offering exemption needed; flows directly into the existing 504 offering.")
    bullet(doc, "Risk: may limit FJET's check size materially; does not protect the 504 window for "
           "other investors who have existing-relationship status.")

    h2(doc, "Sub-Option A2 — Separate Rule 506(b) Offering for FJET (Accredited Institutional Investor)")
    bullet(doc, "FJET qualifies as an 'accredited investor' under Rule 501(a) as an institutional entity. "
           "A separate Rule 506(b) offering accommodates any investment size — no $10M/yr cap — "
           "with no general solicitation, and allows up to 35 non-accredited investors (not applicable here).")
    bullet(doc, "Rule 152 integration analysis required: concurrent 504 and 506(b) offerings may be "
           "integrated as a single offering if the SEC deems them part of the same plan of financing. "
           "Rule 152 safe harbor (https://www.sec.gov/smallbusiness/exemptofferings/rule152) provides "
           "protection in certain circumstances — Counsel to confirm whether the 504 and 506(b) offerings "
           "can be structured to avoid integration. [COUNSEL TO CONFIRM]")
    bullet(doc, "If integration risk is manageable, A2 is the cleaner path: investment size $5M–$10M, "
           "506(b) filing, separate Form D for the 506(b) tranche.")
    bullet(doc, "Exos post-money: $175–$180M at $5–$10M;  FJET dilution at Exos: ≈2.9%–5.6% — minimal.")

    h2(doc, "FJET-side Considerations (both sub-options)")
    bullet(doc, "Investment treated as equity security on FJET's balance sheet. NYSE American Company Guide "
           "§712 shareholder approval required if FJET issues new shares to fund the investment and those "
           "shares exceed 20% of FJET outstanding. At $3.35/share, $10M = ≈2.99M new FJET shares ≈ 5.4% "
           "of 55M shares — well below 20%; board approval required, not shareholder vote.")
    bullet(doc, "MNPI: MOU already covers. FJET's public-company obligations require careful MNPI management.")
    bullet(doc, "No Ainigma exclusivity conflict expected (pure equity investment, not RTO/merger).")
    bullet(doc, "Cost to FJET: FJET cash burn ≈$10M/H1 — this likely requires FJET to conduct a new raise "
           "or use proceeds from a follow-on concurrent with this investment.")

    h2(doc, "Pros")
    bullet(doc, "Deepens AEDC Velocity Alliance teaming relationship; provides Exos capital toward BLK3 first flight")
    bullet(doc, "FJET gains strategic exposure to Exos reusable-rocket upside without full-integration risk")
    bullet(doc, "No dilution to Exos's public-listing optionality on any future path (RTO, IPO, SPAC)")
    bullet(doc, "Sub-Option A2 (506(b)) removes the 504 cap constraint and protects the 504 window "
           "for other existing-relationship investors — preferred if Rule 152 analysis is favorable")

    h2(doc, "Cons")
    bullet(doc, "FJET may not have $5–10M available given its cash position and burn rate")
    bullet(doc, "Minority stake does not materially re-rate FJET stock")
    bullet(doc, "Rule 152 integration analysis adds Counsel time before closing A2")
    bullet(doc, "May not satisfy Exos's full capital raise need as a standalone tranche")

    h2(doc, "Timeline estimate")
    body(doc, "Sub-Option A1: 4–8 weeks if 504 capacity exists. "
         "Sub-Option A2: 6–10 weeks (add time for Rule 152 analysis and 506(b) Form D). "
         "Most time-efficient of all four structures once the exemption path is confirmed by Counsel.")

    h2(doc, "Recommendation")
    body(doc, "Confirm with Counsel: (1) remaining 504 capacity and (2) Rule 152 integration analysis for "
         "a concurrent 506(b) tranche. Proceed with whichever sub-option Counsel approves. "
         "Propose this as the second track at the Tim meeting, with Structure C (JV/teaming) as Ask 1.",
         bold=True)

    divider(doc)

    # ── SECTION 3: STRUCTURE B ────────────────────────────────────────────────
    h1(doc, "3. Structure B — Stock-for-Stock Merger / Exos Becomes FJET Subsidiary")

    warning(doc, "AINIGMA CONFLICT CHECK REQUIRED BEFORE PROCEEDING. If Ainigma term sheet "
            "includes an exclusivity or no-shop for RTO / reverse merger / public-company combination, "
            "this structure may be blocked until Ainigma resolves. Confirm with Counsel first.")

    h2(doc, "Concept")
    body(doc, "Exos merges into Starfighters Space (or a newly formed FJET subsidiary). Exos shareholders "
         "receive FJET common stock at a negotiated exchange ratio based on relative valuations. "
         "Exos becomes an operating subsidiary. Result: Exos acquires public-company access without "
         "a separate IPO, SPAC, or third-party RTO process. This is a direct alternative to the Ainigma RTO.")

    h2(doc, "Economics")
    bullet(doc, "Exos 409A pre-money: $169.7M  |  FJET market cap at $1.63: ≈$89.9M")
    bullet(doc, "Combined enterprise value (illustrative): ≈$260M pre-synergies — FJET would need "
           "to accept a significant premium to Exos ($169.7M / $260M = 65% of combined going to Exos shareholders)")
    bullet(doc, "Exchange ratio illustrative: 1 Exos share → ≈ 1.89 FJET shares (at $169.7M Exos / $1.63 FJET price, "
           "assuming no control premium). Actual ratio subject to negotiation, independent fairness opinion, and "
           "audit of Exos financials")
    bullet(doc, "Dilution to current FJET shareholders: significant — roughly 2x share count unless structure "
           "includes a capital raise concurrently")
    bullet(doc, "Pro forma combined entity: Exos + FJET shareholders each own ≈40–65% depending on negotiated ratio")

    h2(doc, "Securities / Regulatory (most complex of all four structures)")
    bullet(doc, "FJET shareholder vote required: NYSE American §712 requires vote for issuances >20% of "
           "outstanding shares. A full merger almost certainly crosses 20%. Proxy / information statement required")
    bullet(doc, "SEC registration: S-4 registration statement required for stock-for-stock merger. "
           "SEC review period typically 60–90 days minimum. Audited Exos financials required (Exos currently private — "
           "PCAOB-compliant audits needed)")
    bullet(doc, "FJET's current NYSE American listing: FJET must maintain continued-listing standards throughout "
           "the transaction; going concern disclosures and sub-$1 stock risk are real issues at current price")
    bullet(doc, "FJET stock at $1.63: if price falls below $1.00 for 30 consecutive days NYSE American may "
           "initiate delisting proceedings — this is a timing risk that could disrupt or terminate a deal")
    bullet(doc, "Reg D / Reg S compatibility: existing Exos Reg D 504 offering and Japan Reg S round must be "
           "suspended or terminated at the time of the S-4 filing to avoid integration-of-offerings issues; "
           "Counsel must confirm timing")
    bullet(doc, "ITAR/EAR: any transfer of Exos assets or technical data to a public company (even as a sub) "
           "requires export-control review if foreign shareholders are involved (Citadel, BlackRock, any "
           "foreign institutional holders of FJET)")

    h2(doc, "Pros")
    bullet(doc, "Exos gains public-company capital markets access (at-the-market offerings, PIPE, registered "
           "direct) without a separate IPO timeline or SPAC fees")
    bullet(doc, "Eliminates need for the Ainigma RTO if executed instead")
    bullet(doc, "FJET gets Exos's FAA-licensed reusable launch, flight-test tech, and Scorpius relationship "
           "— could materially re-rate FJET stock")
    bullet(doc, "Combined entity is stronger for AEDC, Hermes AFRL, NASA on-ramp, and DoD prime teaming")

    h2(doc, "Cons")
    bullet(doc, "Highest complexity, longest timeline (6–18 months with S-4)")
    bullet(doc, "FJET's financial condition (going concern, material weakness) creates due-diligence and "
           "public-market risk for Exos shareholders")
    bullet(doc, "FJET stock decline risk (−86% YTD) means Exos shareholders could receive shares worth "
           "far less by close than at signing")
    bullet(doc, "Ainigma exclusivity may block this path entirely")
    bullet(doc, "Exos audited financials required — cost and time")

    h2(doc, "Timeline estimate")
    body(doc, "12–18 months minimum (PCAOB audit + S-4 filing + SEC review + FJET shareholder vote + closing). "
         "Only viable if Ainigma RTO is abandoned or resolved, and FJET listing remains stable.")

    h2(doc, "Recommendation")
    body(doc, "High-upside but high-risk. Not recommended as the primary path given Ainigma exclusivity "
         "uncertainty and FJET's financial condition. Explore only if Ainigma RTO fails and FJET stabilizes "
         "above $2.00.",
         bold=True)

    divider(doc)

    # ── SECTION 4: STRUCTURE C ────────────────────────────────────────────────
    h1(doc, "4. Structure C — JV / Teaming + Flight-Test Services Offtake")

    h2(doc, "Concept")
    body(doc, "Exos and Starfighters formalize a joint-venture or long-term teaming agreement that creates "
         "a combined supersonic-aircraft + suborbital-rocket flight-test capability ladder. Exos provides "
         "suborbital payload services (BLK3, above 85 km) and reusable composite structure qualification. "
         "FJET provides captive-carry supersonic flight test (above Mach 2) on its F-104 fleet. "
         "The combined test ladder covers atmospheric (FJET) through Kármán line (Exos). "
         "Structure includes a multi-year offtake commitment by each party to include the other on bid responses, "
         "plus warrants as an alignment mechanism.")

    h2(doc, "Economics")
    bullet(doc, "No direct cash investment required from either party at formation")
    bullet(doc, "Revenue share: negotiated per-contract split (illustrative: 70/30 to the platform provider "
           "on jointly won contracts)")
    bullet(doc, "Warrants: FJET receives Exos warrants (illustrative: 1.0%–2.0% of Exos fully diluted at "
           "$169.7M pre-money exercise price) upon execution; Exos may receive FJET warrants symmetrically. "
           "Aligns long-term incentives without up-front cash")
    bullet(doc, "Target combined contract wins: AEDC Velocity Alliance, AFRL hypersonic test, DoD "
           "captive-carry programs, NASA HASTE-equivalent — potential $5M–$50M in jointly addressable backlog")

    h2(doc, "Securities / Regulatory")
    bullet(doc, "Warrant issuance by Exos: fits inside Reg D 504 offering as a warrant component or as "
           "a separate Reg D 506(b) issuance to FJET (accredited investor). Annual cap must not be exceeded")
    bullet(doc, "FJET warrant issuance: requires FJET board approval; if >20% of outstanding, FJET "
           "shareholder vote. At illustrative 1–2% warrant size (0.55M–1.1M FJET shares), well below 20% — "
           "no vote required")
    bullet(doc, "JV entity (if formed): Delaware LLC or Texas LP; no SEC registration needed if no "
           "securities issued at the JV level")
    bullet(doc, "No Ainigma exclusivity conflict expected (teaming / JV is not an RTO / reverse merger)")

    h2(doc, "Pros")
    bullet(doc, "Lowest barrier to execution — can close in 30–60 days (teaming agreement + warrants + NDA already in place)")
    bullet(doc, "Directly supports AEDC Velocity Alliance and AFRL programs in near term")
    bullet(doc, "Creates a differentiated go-to-market: 'the only commercial test ladder from Mach 2 to the Kármán line'")
    bullet(doc, "Warrant upside for both parties aligns incentives without cash outlay")
    bullet(doc, "No regulatory complexity; doesn't touch Ainigma/RTO structures")

    h2(doc, "Cons")
    bullet(doc, "Does not directly solve Exos's capital raise need")
    bullet(doc, "Revenue realization depends on jointly winning contracts — indirect / longer-cycle")
    bullet(doc, "FJET's own financial pressure may limit their ability to invest in BD for joint pursuits")
    bullet(doc, "Warrant dilution to existing Exos and FJET shareholders, even if modest")

    h2(doc, "Timeline estimate")
    body(doc, "30–60 days from term sheet to signed agreement. RECOMMENDED as an immediate parallel track "
         "alongside Structure A.")

    h2(doc, "Recommendation")
    body(doc, "Best near-term strategic move. Execute JV/teaming agreement and warrant package in parallel "
         "with raising Structure A capital. Builds the combined test-ladder narrative for investors and "
         "government customers immediately.",
         bold=True)

    divider(doc)

    # ── SECTION 5: STRUCTURE D ────────────────────────────────────────────────
    h1(doc, "5. Structure D — Asset / Commercial Deal + Warrants")

    h2(doc, "Concept")
    body(doc, "Exos licenses specific capabilities (e.g., IPS composite structures, payload integration "
         "services, or BLK3 launch slots) to FJET on a fee-for-service basis, with FJET receiving "
         "Exos warrants as part of total consideration. Alternatively, FJET pays Exos a launch-slot "
         "prepayment/deposit (creating immediate non-dilutive cash) in exchange for launch-service credits "
         "and warrants.")

    h2(doc, "Economics")
    bullet(doc, "Prepayment scenario: FJET makes a $2M–$5M launch-slot prepayment / deposit credited "
           "against future Exos launch services. Exos receives immediate cash; FJET receives launch-service "
           "credits at published rates plus warrants.")
    bullet(doc, "License scenario: Exos earns royalties or milestone payments from FJET's use of "
           "composite-structure IP or suborbital integration services")
    bullet(doc, "Warrants: same structure as in Structure C — 0.5%–1.5% of Exos, exercise at 409A, "
           "vesting on launch milestones or JV revenue thresholds")

    h2(doc, "Securities / Regulatory")
    bullet(doc, "Launch-slot prepayment: commercial contract; no securities registration if treated as a "
           "prepaid service, not as a security")
    bullet(doc, "Warrants: same Reg D analysis as Structure C")
    bullet(doc, "IP license: standard commercial license; no securities issues")
    bullet(doc, "If prepayment + warrants are combined, Counsel should confirm whether the package "
           "constitutes a 'security' under the Howey test")

    h2(doc, "Pros")
    bullet(doc, "Can generate immediate non-dilutive cash for Exos (launch-slot prepayment path)")
    bullet(doc, "Low legal complexity; no S-4, no shareholder vote")
    bullet(doc, "Keeps future M&A / RTO optionality fully open")
    bullet(doc, "Concrete commercial milestone (BLK3 flight) aligns warrant vesting with value creation")

    h2(doc, "Cons")
    bullet(doc, "Cash amounts relatively small ($2M–$5M) — not sufficient standalone for BLK3 full program")
    bullet(doc, "FJET may not have cash available for a prepayment given current balance sheet")
    bullet(doc, "Warrant dilution without direct cash investment from FJET may feel imbalanced")

    h2(doc, "Timeline estimate")
    body(doc, "2–4 weeks for commercial agreement; warrant terms add 2–3 weeks for legal docs.")

    h2(doc, "Recommendation")
    body(doc, "Good supplemental structure to Layer onto Structure A or C, not a standalone. "
         "Particularly useful if FJET cannot commit $5M+ as an equity check but can prepay launch services.",
         bold=True)

    divider(doc)

    # ── SECTION 6: SIDE-BY-SIDE SUMMARY ───────────────────────────────────────
    h1(doc, "6. Summary Comparison")

    body(doc, "Structure A = Strategic Equity Investment  |  504 capacity check required; 506(b)/Rule 152 path preferred — Counsel must confirm")
    body(doc, "Structure B = Stock-for-Stock Merger       |  Highest strategic value; blocked by Ainigma risk and FJET condition")
    body(doc, "Structure C = JV / Teaming + Warrants      |  Best near-term move; execute immediately")
    body(doc, "Structure D = Asset Deal + Warrants        |  Supplemental; useful if FJET can't write an equity check")

    body(doc, "\nRecommended sequence: Execute Structure C (JV/teaming) immediately (Ask 1). "
         "Propose Structure A (equity investment) at Tim meeting — but ONLY after Counsel confirms "
         "the 504 capacity remaining and approves the Rule 506(b)/Rule 152 path (Ask 2). "
         "Add Structure D (prepayment) if FJET needs an easier entry point. "
         "Keep Structure B available as a 12–18 month strategic option if Ainigma resolves and FJET stabilizes.",
         bold=True)

    warning(doc, "NOTHING in this document has been reviewed by Counsel. All figures, structures, "
            "and timelines are internal analysis only. Do not share externally until Counsel review "
            "and Jon approval.")

    # Footer note
    fn = doc.add_paragraph()
    fn.paragraph_format.space_before = Pt(12)
    r = fn.add_run("Exos Aerospace Systems & Technologies, Inc.  |  299 FM 1903, Greenville, TX 75402  |  "
                   "jquinn@exosaero.com  |  (430) 966-4005  |  Proprietary — Internal Use Only")
    r.italic = True; r.font.size = Pt(8); r.font.color.rgb = GRAY; r.font.name = "Calibri"

    out = os.path.join(DRAFTS, "Exos_Starfighters_Funding_Structure_Options_2026-10-06.docx")
    doc.save(out)
    print(f"[OK] {out}")
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 2 — EXTERNAL PROPOSAL / IOI
# ═══════════════════════════════════════════════════════════════════════════════

def build_external():
    doc = new_doc()

    # DRAFT watermark header
    wp = doc.add_paragraph()
    wp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = wp.add_run("[ DRAFT — NON-BINDING — FOR DISCUSSION ONLY — REQUIRES COUNSEL REVIEW BEFORE TRANSMISSION ]")
    r.bold = True; r.font.size = Pt(9); r.font.color.rgb = RED; r.font.name = "Calibri"

    # Title block
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_before = Pt(6)
    r = tp.add_run("LETTER OF INTEREST\nStrategic Partnership and Investment Discussion\nExos Aerospace Systems & Technologies, Inc.\nand Starfighters Space, Inc. (NYSE American: FJET)")
    r.bold = True; r.font.size = Pt(13); r.font.color.rgb = NAVY; r.font.name = "Calibri"

    dp = doc.add_paragraph()
    dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = dp.add_run("October 6, 2026  |  DRAFT — Not for distribution")
    r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GRAY; r.font.name = "Calibri"

    body(doc, " ")

    body(doc, "Dear Tim,")
    body(doc, " ")
    body(doc, "Thank you for the relationship we have been building over the past months, including our mutual NDA, "
         "the MOU discussions, and the AEDC Velocity Alliance teaming work. I wanted to put forward a more "
         "structured set of ideas for how Exos and Starfighters can create value together as we head into "
         "late 2026 and 2027.", size=10)

    body(doc, "This letter is a non-binding expression of interest only. Nothing here constitutes a commitment, "
         "offer, or agreement. All terms discussed below are subject to definitive documentation, satisfactory "
         "due diligence, and approval by each company's board of directors. Exos will not proceed on any "
         "securities-related matter without review by our legal counsel. Starfighters' obligations as a "
         "public company are acknowledged, and we will manage this discussion in strict compliance with "
         "applicable securities laws, including material non-public information (MNPI) obligations.", italic=True, size=9, color=GRAY)

    body(doc, " ")

    h1(doc, "1. Why Exos and Starfighters")

    body(doc, 'Exos Aerospace Systems & Technologies, Inc. is a Texas-based reusable launch company and one of three FAA-licensed providers of vertical-takeoff reusable rockets with demonstrated recovery and reflight (FAA reusable launch vehicle operator license LRLO 18-109, renewed March 2026; faa.gov/data_research/commercial_space_data). Exos has flown commercial payloads since 2018 on its SARGE vehicle. Block 3 (BLK3), the enhanced successor to SARGE, is FAA-licensed for reusable suborbital flight (license issued March 2026), with the first commercial flight of BLK3, our latest FAA-licensed vehicle, planned for early 2027.')

    body(doc, "Starfighters operates what it describes as the world's largest fleet of commercial supersonic "
         "aircraft and is developing the STARLAUNCH air-launch program from Kennedy Space Center. "
         "STARLAUNCH 1 has completed wind tunnel testing (Mach 0.85 and 1.3, January 2026), and "
         "Starfighters has established partnerships with Blackstar Orbital for hypersonic captive-carry "
         "flight testing and with Integrated Launch Solutions for mission engineering and range integration.")

    body(doc, "Together, Exos and Starfighters offer a test-and-qualification capability ladder that no "
         "single company presently covers commercially: supersonic captive-carry flight test (above Mach 2, "
         "FJET) through reusable suborbital launch above 85 km (Exos BLK3). "
         "We believe this ladder addresses a validated, growing demand from DoD, NASA, and commercial customers "
         "for affordable, frequent flight-test access to supersonic and near-space environments.")

    body(doc, " ")

    h1(doc, "2. Proposed Areas for Discussion")

    body(doc, "We would like to explore three areas in our meeting:")

    h2(doc, "A. Joint Venture / Teaming Agreement with Warrants")
    body(doc, "Formalize the working relationship we have started via the MOU into a binding teaming "
         "agreement covering joint bid pursuit for government and commercial flight-test programs. "
         "The teaming structure would include a mutual non-circumvention provision, a revenue-sharing "
         "framework for jointly won contracts, and warrant instruments (to be structured in compliance "
         "with applicable securities laws) that align our long-term incentives. This path can close in "
         "30–60 days and directly supports our combined AEDC Velocity Alliance and AFRL pursuits.")

    h2(doc, "B. Strategic Equity Investment by Starfighters in Exos")
    body(doc, "We would welcome a discussion of a strategic equity investment by Starfighters in Exos, "
         "subject to applicable securities exemptions and Counsel review on both sides. "
         "Exos's most recent 409A independent valuation (March 31, 2026) provides "
         "a reference point for this discussion. A strategic investment would deepen the relationship, "
         "provide Starfighters strategic exposure to Exos's BLK3 flight cadence and reusable-launch "
         "upside, and accelerate our combined government program pursuit. We understand that any "
         "Starfighters investment decision would require FJET board approval and compliance with NYSE "
         "American rules.")

    h2(doc, "C. Launch-Service Commercial Arrangement")
    body(doc, "Exos would consider a launch-service prepayment or mission deposit structure that provides "
         "Starfighters with access to BLK3 launch slots at published service rates. This creates "
         "a concrete near-term commercial relationship and may be paired with the warrant structure "
         "described in Item A. Exos's BLK3 payload bay (135 kg, altitude >85 km, FAA-licensed) is "
         "complementary to STARLAUNCH's air-launch profile and may serve a different portion of "
         "customer payloads.")

    body(doc, " ")

    h1(doc, "3. What We Are Not Proposing")

    body(doc, "To be clear, this letter does not propose any acquisition of, or by, either party; "
         "and does not constitute an offer to purchase FJET shares or to sell Exos shares on any basis "
         "other than through a properly disclosed offering process with counsel engaged on both sides. "
         "All securities-related discussions are subject to applicable securities exemptions and Counsel review.",
         italic=True)

    body(doc, " ")

    h1(doc, "4. Our Commitment")

    body(doc, "Exos is committed to a relationship with Starfighters that creates durable value for both "
         "companies and their stakeholders. We approach this as a partnership between two mission-driven "
         "teams that believe the commercial aerospace test-infrastructure market is at an inflection point "
         "driven by defense modernization, the SpaceX IPO repricing of the sector, and generational "
         "demand for affordable, frequent flight qualification.")

    body(doc, "We look forward to a substantive conversation in late October and are happy to have our "
         "counsel coordinate with yours on any of the topics above.")

    body(doc, " ")
    body(doc, "Sincerely,", size=10)
    body(doc, " ")
    body(doc, " ")
    body(doc, "John Quinn\nCofounder & CEO\nExos Aerospace Systems & Technologies, Inc.\n"
         "299 FM 1903, Greenville, TX 75402\njquinn@exosaero.com  |  (430) 966-4005", size=10)

    body(doc, " ")

    # DRAFT footer
    fp = doc.add_paragraph()
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("DRAFT — NON-BINDING INDICATION OF INTEREST ONLY — REQUIRES COUNSEL REVIEW BEFORE TRANSMISSION\n"
                   "This document does not constitute a commitment, contract, or offer of securities. "
                   "Exos Aerospace Systems & Technologies, Inc.  |  Proprietary — Do Not Distribute")
    r.italic = True; r.font.size = Pt(8); r.font.color.rgb = RED; r.font.name = "Calibri"

    out = os.path.join(DRAFTS, "Exos_Starfighters_Proposal_DRAFT_2026-10-06.docx")
    doc.save(out)
    print(f"[OK] {out}")
    return out


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 3 — 1-PAGE MEETING BRIEF
# ═══════════════════════════════════════════════════════════════════════════════

def build_brief():
    doc = new_doc()

    # Title
    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tp.paragraph_format.space_before = Pt(4)
    r = tp.add_run("MEETING BRIEF — TIM FRANTA / STARFIGHTERS SPACE")
    r.bold = True; r.font.size = Pt(13); r.font.color.rgb = NAVY; r.font.name = "Calibri"

    sp = doc.add_paragraph()
    sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sp.add_run("Jon Quinn  |  Late October 2026  |  INTERNAL — NOT FOR DISTRIBUTION")
    r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GRAY; r.font.name = "Calibri"

    # ── WHO ────────────────────────────────────────────────────────────────────
    h1(doc, "Who You're Meeting")
    kv(doc, "Name",    "Tim Franta — CEO, Starfighters Space, Inc.")
    kv(doc, "Email",   "tfranta@starfightersspace.com")
    kv(doc, "Company", "NYSE American: FJET — Cape Canaveral, FL")
    kv(doc, "Context", "23+ emails; MOU under discussion (Task #1782); mutual NDA in place; "
       "AEDC Velocity Alliance co-teaming (Exos prime / Starfighters sub)")
    kv(doc, "FJET today",
       "Stock $1.62  |  Market cap ≈$90M  |  Down 86% from 52-week high of $31.50  |  "
       "Going concern disclosures active  |  Cash burn ≈$10M/H1  |  Changed auditors Jul 2026")

    # ── OBJECTIVE ─────────────────────────────────────────────────────────────
    h1(doc, "Meeting Objective")
    body(doc, "Advance Starfighters from a teaming partner to a capital and commercial partner. "
         "Confirm one concrete next step before leaving the room.")

    # ── ASK ───────────────────────────────────────────────────────────────────
    h1(doc, "Your Asks (Ranked)")
    bullet(doc, "JV / Teaming Agreement signed: formalize the MOU into a binding teaming agreement with "
           "revenue share + mutual warrants. 30–60 day close. Supports AEDC, AFRL, NASA pursuits jointly.",
           bold_prefix="Ask 1 (Priority):")
    bullet(doc, "Strategic equity investment in Exos: $5M–$10M at 409A valuation ($169.7M pre-money), "
           "subject to applicable securities exemptions and Counsel review (Exos's 504 capacity is limited; "
           "a separate accredited-investor offering may be required — Counsel to confirm). "
           "Requires FJET board approval. Tim takes it to the board. Timeline: 6–10 weeks once structure confirmed.",
           bold_prefix="Ask 2 (Secondary):")
    bullet(doc, "Launch-slot prepayment: $2M–$5M commercial deposit against future BLK3 flights, "
           "paired with warrants. Easiest entry if equity investment timeline is slow.",
           bold_prefix="Ask 3 (Fallback):")

    # ── WALK-AWAY ─────────────────────────────────────────────────────────────
    h1(doc, "Walk-Away Lines")
    bullet(doc, "No deal that doesn't have Ask 1 (teaming) as the minimum outcome.")
    bullet(doc, "No share price or structure that values Exos below the March 31, 2026 409A ($169.7M pre-money).")
    bullet(doc, "No merger, acquisition, or reverse-merger discussion until: (a) Ainigma term sheet "
           "exclusivity is cleared by Counsel, and (b) FJET stock is stable above $2.00.")
    bullet(doc, "Do not reference Scorpius acquisition, ROFR, or any Scorpius ownership change with Tim.")
    bullet(doc, "Do not commit to any specific BLK3 flight date — use 'early 2027.'")

    # ── QUESTIONS TO ASK ──────────────────────────────────────────────────────
    h1(doc, "Questions to Ask Tim")
    bullet(doc, "What is Starfighters' current capital runway and any active fundraise timing?")
    bullet(doc, "Is the FJET board aligned on making strategic investments vs. deploying all capital on "
           "STARLAUNCH ops?")
    bullet(doc, "What is FJET's priority customer: DoD captive-carry, commercial space, or orbital launch "
           "for STARLAUNCH 2?")
    bullet(doc, "What is Tim's personal view on the Blackstar Orbital partnership — competitive or synergistic "
           "with what Exos brings?")
    bullet(doc, "Has Cantor Fitzgerald (their May 2026 placement agent) discussed any follow-on raise?")
    bullet(doc, "Is the AEDC Velocity Alliance RFWP fully submitted with Exos on the roster?")

    # ── POSITIONING ────────────────────────────────────────────────────────────
    h1(doc, "Key Positioning Points")
    bullet(doc, "Exos = one of three FAA-licensed reusable rocket providers. BLK3 FAA-licensed (Mar 2026), "
           "first commercial flight early 2027. Flying since 2018 (SARGE/Armadillo lineage).")
    bullet(doc, "Exos + Starfighters = the only commercial test ladder from Mach 2 to 85+ km Kármán line. "
           "No single competitor covers this range.")
    bullet(doc, "SpaceX IPO repriced the sector — non-SpaceX space infrastructure is the buy, "
           "per market narrative FJET itself has used in press releases.")
    bullet(doc, "Exos BLK3 135 kg, >85 km, reusable — complements STARLAUNCH's air-launch profile for "
           "different payload classes and altitudes.")

    # Footer
    fn = doc.add_paragraph()
    fn.paragraph_format.space_before = Pt(10)
    r = fn.add_run("Prepared by Exos AI Desk  |  October 6, 2026  |  Internal use only — do not share")
    r.italic = True; r.font.size = Pt(8); r.font.color.rgb = GRAY; r.font.name = "Calibri"

    out = os.path.join(DRAFTS, "Exos_Starfighters_MeetingBrief_Tim_2026-10-06.docx")
    doc.save(out)
    print(f"[OK] {out}")
    return out


if __name__ == "__main__":
    p1 = build_internal()
    p2 = build_external()
    p3 = build_brief()
    print("\nAll three DOCX files written. Run build_starfighters_funding_pdfs.py for PDFs.")
