#!/usr/bin/env python3
"""
Build letterhead-matched PDFs for the three Starfighters documents.
Requires reportlab in user-site (run under plain python3, NOT PYTHONNOUSERSITE=1).
Run: python3 scripts/build_starfighters_funding_pdfs.py
"""
import os, subprocess, textwrap
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
                                 KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import Image as RLImage

WS     = os.path.expanduser("~/.openclaw/workspace")
LH_DOCX= os.path.join(WS, "assets", "EXOS_Letterhead_Greenville_TX_PRIMARY.docx")
DRAFTS = os.path.join(WS, "drafts")
MEDIA  = "/tmp/fjet_lh_media"

NAVY = colors.HexColor("#0A3D7C")
DARK = colors.HexColor("#1A1A1A")
RED  = colors.HexColor("#C00000")
GRAY = colors.HexColor("#555555")


def extract_banners():
    os.makedirs(MEDIA, exist_ok=True)
    subprocess.run(["unzip", "-o", LH_DOCX, "word/media/*", "-d", MEDIA], capture_output=True)
    media_dir = os.path.join(MEDIA, "word", "media")
    imgs = sorted(os.listdir(media_dir)) if os.path.exists(media_dir) else []
    header = footer = None
    if len(imgs) >= 2:
        header = os.path.join(media_dir, imgs[0])  # image1.png
        footer = os.path.join(media_dir, imgs[1])  # image2.png
    elif len(imgs) == 1:
        header = os.path.join(media_dir, imgs[0])
    return header, footer


def make_on_page(header_path, footer_path, pw, ph):
    def on_page(canvas, doc):
        canvas.saveState()
        if header_path and os.path.exists(header_path):
            canvas.drawImage(header_path, 0, ph - 1.4*inch, width=pw, height=1.4*inch,
                             preserveAspectRatio=False, mask="auto")
        if footer_path and os.path.exists(footer_path):
            canvas.drawImage(footer_path, 0, 0, width=pw, height=1.2*inch,
                             preserveAspectRatio=False, mask="auto")
        canvas.restoreState()
    return on_page


def styles():
    ss = getSampleStyleSheet()

    def add(name, **kw):
        s = ParagraphStyle(name, **kw)
        ss.add(s)
        return s

    add("H1", fontName="Helvetica-Bold", fontSize=11, textColor=NAVY,
        spaceBefore=12, spaceAfter=4, alignment=TA_LEFT,
        textTransform="uppercase")
    add("H2", fontName="Helvetica-Bold", fontSize=10, textColor=NAVY,
        spaceBefore=6, spaceAfter=2, alignment=TA_LEFT)
    add("Body", fontName="Helvetica", fontSize=9.5, textColor=DARK,
        spaceBefore=2, spaceAfter=3, leading=13, alignment=TA_JUSTIFY)
    add("BodyItalic", fontName="Helvetica-Oblique", fontSize=9, textColor=GRAY,
        spaceBefore=2, spaceAfter=3, leading=12)
    add("BulletItem", fontName="Helvetica", fontSize=9.5, textColor=DARK,
        spaceBefore=1, spaceAfter=1, leading=13,
        leftIndent=14, firstLineIndent=0, bulletIndent=4)
    add("KV", fontName="Helvetica", fontSize=9, textColor=DARK,
        spaceBefore=1, spaceAfter=2, leading=12)
    add("Warning", fontName="Helvetica-Bold", fontSize=9, textColor=RED,
        spaceBefore=4, spaceAfter=4, borderColor=RED, borderWidth=0.5,
        borderPadding=4)
    add("DocTitle", fontName="Helvetica-Bold", fontSize=14, textColor=NAVY,
        spaceBefore=6, spaceAfter=4, alignment=TA_CENTER)
    add("Subtitle", fontName="Helvetica-Oblique", fontSize=9, textColor=GRAY,
        spaceBefore=2, spaceAfter=6, alignment=TA_CENTER)
    add("DraftBanner", fontName="Helvetica-Bold", fontSize=9, textColor=RED,
        spaceBefore=4, spaceAfter=4, alignment=TA_CENTER)
    add("Footer", fontName="Helvetica-Oblique", fontSize=7.5, textColor=GRAY,
        spaceBefore=10, spaceAfter=2, alignment=TA_CENTER)
    return ss


def hr(ss):
    return HRFlowable(width="100%", thickness=0.5, color=NAVY, spaceAfter=4, spaceBefore=4)


def build_pdf(filename, story_fn):
    ss = styles()
    header_path, footer_path = extract_banners()
    pw, ph = letter
    outpath = os.path.join(DRAFTS, filename)

    doc = SimpleDocTemplate(
        outpath,
        pagesize=letter,
        topMargin=1.55*inch,
        bottomMargin=1.35*inch,
        leftMargin=0.85*inch,
        rightMargin=0.85*inch,
    )
    on_page = make_on_page(header_path, footer_path, pw, ph)
    story = story_fn(ss)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"[OK PDF] {outpath}")
    return outpath


# ─── STORY BUILDERS ──────────────────────────────────────────────────────────

def story_internal(ss):
    s = []

    def h1(t):
        s.append(Paragraph(t, ss["H1"]))
        s.append(hr(ss))

    def h2(t):
        s.append(Paragraph(t, ss["H2"]))

    def body(t, italic=False, bold=False, red=False):
        st = "BodyItalic" if italic else "Body"
        txt = t
        if bold:
            txt = f"<b>{t}</b>"
        if red:
            s.append(Paragraph(f'<font color="#C00000"><b>⚠  {t}</b></font>', ss["Body"]))
        else:
            s.append(Paragraph(txt, ss[st]))

    def warn(t):
        s.append(Paragraph(f'<font color="#C00000"><b>⚠  {t}</b></font>', ss["Warning"]))

    def bl(t, prefix=None):
        txt = f"• <b>{prefix}</b> {t}" if prefix else f"• {t}"
        s.append(Paragraph(txt, ss["BulletItem"]))

    def kv(k, v, note=None):
        note_txt = f'  <i><font color="#555555">[{note}]</font></i>' if note else ""
        s.append(Paragraph(f'<b><font color="#0A3D7C">{k}:</font></b>  {v}{note_txt}', ss["KV"]))

    # Title
    s.append(Paragraph("EXOS AEROSPACE — STARFIGHTERS SPACE (FJET)<br/>FUNDING STRUCTURE OPTIONS", ss["DocTitle"]))
    s.append(Paragraph("INTERNAL — FOR JON QUINN / COUNSEL REVIEW ONLY  |  October 6, 2026", ss["Subtitle"]))
    s.append(Spacer(1, 6))

    # Section 0
    h1("0. Starfighters Space (FJET) — Current Facts")
    body("All figures from primary sources (SEC EDGAR, MarketBeat). Unverified items flagged.", italic=True)
    kv("Exchange / Ticker", "NYSE American: FJET  (listed December 2025)")
    kv("CEO", "Tim Franta — salary raised to $350K/yr effective Sep 28, 2026",
       note="SEC 8-K Oct 2 2026")
    kv("CFO", "David Whitney — salary raised to $300K/yr effective Sep 28, 2026")
    kv("Share price (10/6/26)", "$1.62–$1.63  |  52-wk range $1.57–$31.50  (−86% YTD)",
       note="MarketBeat https://www.marketbeat.com/stocks/NYSEAMERICAN/FJET/chart")
    kv("Market cap (10/6/26)", "≈ $89.9M")
    kv("Shares outstanding", "≈ 55M (current);  44.2M at March 31, 2026",
       note="Yahoo Finance https://finance.yahoo.com/quote/FJET/key-statistics")
    kv("Float", "37.33M shares  |  Insiders 26.6%  |  Institutions 18.9%")
    kv("Institutional holders",
       "Citadel Advisors 5.43%;  BlackRock 3.86%",
       note="Investing.com https://www.investing.com/equities/starfighters-space")
    kv("Last capital raise",
       "$17.5M Reg D 506(b) private placement, May 27, 2026 — 5.22M shares @ $3.35;  Cantor Fitzgerald agent",
       note="SEC Form D Jun 4 2026  https://capedge.com/company/1947016/filings")
    kv("H1 2026 net loss", "$15.7M  |  operating cash burn $10.1M",
       note="10-Q filed Aug 19 2026 https://www.sec.gov/Archives/edgar/data/1947016/000106299326004518/form10q.htm")
    kv("Cash at Mar 31, 2026", "$2.14M (cash + restricted)  |  Total assets $26.34M  |  Equity $22.43M",
       note="10-Q filed May 20 2026 https://www.sec.gov/Archives/edgar/data/1947016/000106299326002803/form10q.htm")
    kv("STARLAUNCH status",
       "Wind tunnel testing complete Jan 2026 (Mach 0.85 / 1.3). Blackstar Orbital hypersonic partnership.",
       note="SEC 8-K Jan 21 2026")
    kv("Auditor", "Changed to CBIZ CPAs P.C. effective July 22, 2026",
       note="SEC 8-K Jul 2026")
    warn("FJET going-concern disclosures active. Material weakness remediation ongoing. "
         "High stock-based comp ($4.5M H1). Any deal must account for FJET's capital needs "
         "and NYSE American continued-listing requirements.")

    h2("Existing Exos–Starfighters Relationship")
    bl("MOU under discussion (Task #1782 / 23 emails with Tim Franta, Sep 28 2026).")
    bl("Mutual NDA executed. AEDC Velocity Alliance RFWP roster submitted (Exos prime / FJET sub).")

    # Section 1
    h1("1. Exos Funding Context — October 6, 2026")
    kv("A. Reg D Rule 504", "Up to $25M staged ≈$10M/yr. No public solicitation. Counsel-confirmed structure. "
       "Rule 504 rolls 12-month cap: $10M total. Existing 504 sales + Capital Bridge consume some capacity — "
       "exact remaining headroom requires Counsel confirmation. "
       "See https://www.sec.gov/smallbusiness/exemptofferings/rule504")
    kv("B. Japan Reg S", "EAI units, offshore, separate from U.S. 504. K.K. wholly owned.")
    kv("C. Ainigma RTO", "Series A worklist PAUSED pending Ainigma resolution.")
    kv("D. Scorpius commission-only (NEW 10/6)", "ROFR expired. 15% commission. D-7281978 SSLC agreement.")
    kv("Exos 409A valuation", "$169.7M  (March 31, 2026)")
    kv("Series A target", "$10M–$25M  (D1–D4 locked Aug 13, 2026)")
    kv("BLK3 first flight", "Early 2027  (FAA-licensed March 2026)")
    warn("Before executing any RTO / reverse-merger structure: confirm with Counsel whether "
         "Ainigma term sheet contains exclusivity that would block Structures B. This is a go/no-go gate.")

    # Section 2
    h1("2. Structure A — Strategic Equity Investment by FJET in Exos")
    warn("RULE 504 CAPACITY ISSUE: Rule 504 caps total raises at $10M per rolling 12 months "
         "(https://www.sec.gov/smallbusiness/exemptofferings/rule504). Existing 504 sales + Capital Bridge "
         "already consume some capacity. A $5–$10M FJET check could exhaust the remaining window. "
         "Two sub-options below — Counsel must confirm path before proceeding.")
    body("FJET deploys capital into Exos at Exos's 409A valuation ($169.7M pre-money). "
         "No change in Exos control. Exemption path depends on remaining 504 capacity.", bold=True)
    h2("Sub-Option A1 — Size Within Remaining 504 Capacity")
    bl("Counsel confirms rolling balance available in 504 offering; FJET check sized to stay within that balance (likely well under $5M; TBD).")
    bl("Flows directly into existing 504 offering; no new exemption needed. Risk: may severely limit FJET check size.")
    h2("Sub-Option A2 — Separate Rule 506(b) Offering for FJET (Preferred if Rule 152 analysis is favorable)")
    bl("FJET qualifies as accredited institutional investor under Rule 501(a). 506(b) has no $10M cap — "
       "accommodates $5M–$10M without consuming 504 window.")
    bl("Rule 152 integration analysis required: concurrent 504 + 506(b) may be integrated by SEC. "
       "See https://www.sec.gov/smallbusiness/exemptofferings/rule152  [COUNSEL TO CONFIRM]")
    bl("If approved: investment $5M–$10M; Exos post-money $175–$180M; FJET dilution ≈2.9%–5.6%; separate Form D filed for 506(b) tranche.")
    bl("FJET-side: no shareholder vote at this size (<20% of FJET outstanding); FJET board approval required.")
    bl("No Ainigma exclusivity conflict expected (pure equity, not RTO/merger).")
    body("TIMELINE: A1: 4–8 weeks if 504 capacity exists. A2: 6–10 weeks (add Rule 152 analysis). "
         "Confirm exemption path with Counsel BEFORE raising at Tim meeting.", italic=True)

    # Section 3
    h1("3. Structure B — Stock-for-Stock Merger (Exos as FJET Subsidiary)")
    warn("AINIGMA CONFLICT CHECK REQUIRED. Confirm with Counsel before discussing with Tim.")
    body("Exos merges into FJET (or FJET sub). Exos shareholders receive FJET stock. Exos acquires "
         "public-company access without a separate IPO.")
    bl("Exchange ratio illustrative: $169.7M Exos / $1.63 FJET = ≈1.89 FJET shares per Exos share")
    bl("Requires: S-4 registration, PCAOB-audited Exos financials, FJET shareholder vote (>20% NYSE Am. §712)")
    bl("FJET going-concern and sub-$2 stock are material risks to deal completion")
    bl("Timeline: 12–18 months minimum")
    body("RECOMMENDATION: Only viable if Ainigma RTO fails and FJET stabilizes above $2.00.", italic=True)

    # Section 4
    h1("4. Structure C — JV / Teaming + Warrants  [RECOMMENDED IMMEDIATE TRACK]")
    body("Formalize the MOU into a binding teaming agreement: combined Mach 2+ (FJET) through 85 km "
         "(Exos BLK3) test ladder. Revenue share on jointly won contracts. Mutual warrants for long-term alignment.")
    bl("No direct cash investment at formation")
    bl("FJET receives Exos warrants (≈1–2% fully diluted at $169.7M exercise price)")
    bl("Targets: AEDC Velocity Alliance, AFRL hypersonic, DoD captive-carry, NASA on-ramp")
    bl("No Ainigma conflict. No FJET shareholder vote at warrant size <20%")
    body("TIMELINE: 30–60 days.  EXECUTE IN PARALLEL WITH STRUCTURE A.", italic=True)

    # Section 5
    h1("5. Structure D — Launch-Service Prepayment + Warrants  [Supplemental]")
    body("FJET makes a $2M–$5M launch-slot deposit against future BLK3 missions at published rates, "
         "paired with Exos warrants. Non-dilutive cash for Exos without equity issuance paperwork.")
    bl("Fastest path to non-dilutive cash if FJET has liquidity")
    bl("Counsel must confirm prepayment + warrant package structure under Howey test")
    body("TIMELINE: 2–4 weeks.  Layer onto Structure C or A.", italic=True)

    # Section 6
    h1("6. Summary & Recommendation")
    bl("Execute Structure C (JV/teaming) immediately — 30–60 day close", prefix="Now:")
    bl("Structure A (equity): Counsel must confirm 504 capacity + Rule 152 analysis BEFORE raising at Tim meeting. "
       "Once approved: 6–10 weeks to close.", prefix="Gate:")
    bl("Add Structure D (prepayment) if FJET can't write equity check", prefix="If needed:")
    bl("Keep Structure B for after Ainigma resolves and FJET stabilizes", prefix="12–18 mo:")
    warn("NOTHING in this document reviewed by Counsel. Do not share externally. "
         "Structure A requires Counsel sign-off on securities path before it is raised with FJET.")

    s.append(Paragraph(
        "Exos Aerospace Systems & Technologies, Inc.  |  299 FM 1903, Greenville, TX 75402  |  "
        "jquinn@exosaero.com  |  Proprietary — Internal Use Only",
        ss["Footer"]))

    return s


def story_external(ss):
    s = []

    def h1(t):
        s.append(Paragraph(t, ss["H1"]))
        s.append(hr(ss))

    def h2(t):
        s.append(Paragraph(t, ss["H2"]))

    def body(t, italic=False, bold=False):
        st = "BodyItalic" if italic else "Body"
        txt = f"<b>{t}</b>" if bold else t
        s.append(Paragraph(txt, ss[st]))

    # DRAFT banner
    s.append(Paragraph(
        "[ DRAFT — NON-BINDING — FOR DISCUSSION ONLY — REQUIRES COUNSEL REVIEW BEFORE TRANSMISSION ]",
        ss["DraftBanner"]))

    s.append(Paragraph(
        "LETTER OF INTEREST<br/>Strategic Partnership and Investment Discussion<br/>"
        "Exos Aerospace Systems &amp; Technologies, Inc.<br/>"
        "and Starfighters Space, Inc. (NYSE American: FJET)",
        ss["DocTitle"]))
    s.append(Paragraph("October 6, 2026  |  DRAFT — Not for distribution", ss["Subtitle"]))
    s.append(Spacer(1, 6))

    body("Dear Tim,")
    s.append(Spacer(1, 4))
    body("Thank you for the relationship we have been building over the past months, including our mutual NDA, "
         "the MOU discussions, and the AEDC Velocity Alliance teaming work. I wanted to put forward a more "
         "structured set of ideas for how Exos and Starfighters can create value together as we head into "
         "late 2026 and 2027.")
    body("This letter is a non-binding expression of interest only. Nothing here constitutes a commitment, "
         "offer, or agreement. All terms discussed below are subject to definitive documentation, satisfactory "
         "due diligence, and approval by each company's board of directors. Exos will not proceed on any "
         "securities-related matter without review by our legal counsel. Starfighters' obligations as a "
         "public company are acknowledged, and we will manage this discussion in strict compliance with "
         "applicable securities laws, including material non-public information (MNPI) obligations.", italic=True)

    h1("1. Why Exos and Starfighters")
    body('Exos Aerospace Systems & Technologies, Inc. is a Texas-based reusable launch company. Exos has flown commercial payloads since 2018 on its SARGE vehicle. Block 3 (BLK3), the enhanced successor to SARGE, is FAA-licensed for reusable suborbital flight (license issued March 2026), with the first commercial flight of BLK3, our latest FAA-licensed vehicle, planned for early 2027.')
    body("Starfighters operates a commercial fleet of supersonic aircraft and is developing the STARLAUNCH "
         "air-launch program from Kennedy Space Center. STARLAUNCH 1 has completed wind tunnel testing "
         "(Mach 0.85 and 1.3, January 2026), and Starfighters has established partnerships with Blackstar "
         "Orbital for hypersonic captive-carry flight testing and with Integrated Launch Solutions for "
         "mission engineering and range integration.")
    body("Together, Exos and Starfighters offer a test-and-qualification capability ladder that covers "
         "supersonic captive-carry flight test (above Mach 2, FJET) through reusable suborbital launch "
         "above 85 km (Exos BLK3). We believe this ladder addresses a validated, growing demand from DoD, "
         "NASA, and commercial customers for affordable, frequent flight-test access to supersonic and "
         "near-space environments.")

    h1("2. Proposed Areas for Discussion")

    h2("A. Joint Venture / Teaming Agreement with Warrants")
    body("Formalize our working relationship into a binding teaming agreement covering joint bid pursuit "
         "for government and commercial flight-test programs. The teaming structure would include a mutual "
         "non-circumvention provision, a revenue-sharing framework for jointly won contracts, and warrant "
         "instruments (to be structured in compliance with applicable securities laws) that align our long-term "
         "incentives. This path can close in 30–60 days and directly supports our combined AEDC Velocity "
         "Alliance and AFRL pursuits.")

    h2("B. Strategic Equity Investment by Starfighters in Exos")
    body("We would welcome a discussion of a strategic equity investment by Starfighters in Exos, "
         "subject to applicable securities exemptions and Counsel review on both sides. "
         "Exos's most recent 409A independent valuation (March 31, 2026) provides a reference point for this "
         "discussion. A strategic investment would deepen the relationship, provide Starfighters strategic "
         "exposure to Exos's BLK3 flight cadence and reusable-launch upside, and accelerate our combined "
         "government program pursuit. We understand that any Starfighters investment decision would require "
         "FJET board approval and compliance with NYSE American rules.")

    h2("C. Launch-Service Commercial Arrangement")
    body("Exos would consider a launch-service prepayment or mission deposit structure that provides "
         "Starfighters with access to BLK3 launch slots at published service rates. This creates a concrete "
         "near-term commercial relationship and may be paired with the warrant structure described in Item A. "
         "Exos's BLK3 payload bay (135 kg, altitude above 85 km, FAA-licensed) is complementary to "
         "STARLAUNCH's air-launch profile and may serve a different portion of customer payloads.")

    h1("3. What We Are Not Proposing")
    body("To be clear, this letter does not propose any acquisition of, or by, either party; "
         "and does not constitute an offer to purchase FJET shares or to sell Exos shares on any basis "
         "other than through a properly disclosed offering process with counsel engaged on both sides. "
         "All securities-related discussions are subject to applicable securities exemptions and Counsel review.",
         italic=True)

    h1("4. Our Commitment")
    body("Exos is committed to a relationship with Starfighters that creates durable value for both "
         "companies and their stakeholders. We approach this as a partnership between two mission-driven "
         "teams that believe the commercial aerospace test-infrastructure market is at an inflection point "
         "driven by defense modernization and generational demand for affordable, frequent flight qualification.")
    body("We look forward to a substantive conversation in late October and are happy to have our counsel "
         "coordinate with yours on any of the topics above.")

    s.append(Spacer(1, 10))
    body("Sincerely,")
    s.append(Spacer(1, 20))
    body("John Quinn<br/>Cofounder &amp; CEO<br/>Exos Aerospace Systems &amp; Technologies, Inc.<br/>"
         "299 FM 1903, Greenville, TX 75402<br/>jquinn@exosaero.com  |  (430) 966-4005")

    s.append(Spacer(1, 12))
    s.append(Paragraph(
        "DRAFT — NON-BINDING INDICATION OF INTEREST ONLY — REQUIRES COUNSEL REVIEW BEFORE TRANSMISSION<br/>"
        "This document does not constitute a commitment, contract, or offer of securities.<br/>"
        "Exos Aerospace Systems &amp; Technologies, Inc.  |  Proprietary — Do Not Distribute",
        ss["DraftBanner"]))
    return s


def story_brief(ss):
    s = []

    def h1(t):
        s.append(Paragraph(t, ss["H1"]))
        s.append(hr(ss))

    def body(t, italic=False, bold=False):
        st = "BodyItalic" if italic else "Body"
        txt = f"<b>{t}</b>" if bold else t
        s.append(Paragraph(txt, ss[st]))

    def bl(t, prefix=None):
        txt = f"• <b>{prefix}</b> {t}" if prefix else f"• {t}"
        s.append(Paragraph(txt, ss["BulletItem"]))

    def kv(k, v):
        s.append(Paragraph(f'<b><font color="#0A3D7C">{k}:</font></b>  {v}', ss["KV"]))

    s.append(Paragraph("MEETING BRIEF — TIM FRANTA / STARFIGHTERS SPACE", ss["DocTitle"]))
    s.append(Paragraph(
        "Jon Quinn  |  Late October 2026  |  INTERNAL — NOT FOR DISTRIBUTION",
        ss["Subtitle"]))
    s.append(Spacer(1, 4))

    h1("Who You're Meeting")
    kv("Name", "Tim Franta — CEO, Starfighters Space, Inc.")
    kv("Email", "tfranta@starfightersspace.com")
    kv("Company", "NYSE American: FJET — Cape Canaveral, FL")
    kv("Context", "23+ emails; MOU under discussion (Task #1782); mutual NDA in place; AEDC Velocity Alliance co-teaming")
    kv("FJET today", "Stock $1.62  |  Market cap ≈$90M  |  Down 86% from 52-wk high $31.50  |  Going concern active  |  Cash burn ≈$10M/H1")

    h1("Meeting Objective")
    body("Advance Starfighters from teaming partner to capital and commercial partner. "
         "Confirm one concrete next step before leaving the room.")

    h1("Your Asks (Ranked)")
    bl("JV / Teaming Agreement signed: formalize MOU into binding agreement — revenue share + mutual warrants. "
       "30–60 day close. Supports AEDC, AFRL, NASA pursuits jointly.",
       prefix="Ask 1 (Priority):")
    bl("Strategic equity investment in Exos: $5M–$10M at 409A valuation ($169.7M pre-money), subject to "
       "applicable securities exemptions and Counsel review (504 capacity limited; separate accredited-investor "
       "offering may be required — Counsel to confirm before raising). FJET board approval required. "
       "Timeline: 6–10 weeks once structure confirmed.",
       prefix="Ask 2 (Secondary):")
    bl("Launch-slot prepayment: $2M–$5M commercial deposit against future BLK3 flights, with warrants. "
       "Easiest entry if equity timeline is slow.",
       prefix="Ask 3 (Fallback):")

    h1("Walk-Away Lines")
    bl("No deal that doesn't include Ask 1 (teaming) as the minimum outcome.")
    bl("No valuation of Exos below the March 31, 2026 409A ($169.7M pre-money).")
    bl("No merger / acquisition / reverse-merger discussion until Ainigma exclusivity cleared by Counsel "
       "AND FJET stock is stable above $2.00.")
    bl("Do not reference Scorpius acquisition, ROFR, or any Scorpius ownership change.")
    bl("Do not commit to a specific BLK3 flight date — use 'early 2027.'")

    h1("Questions to Ask Tim")
    bl("What is Starfighters' current capital runway and any active fundraise timing?")
    bl("Is the FJET board aligned on strategic investments vs. deploying all capital on STARLAUNCH ops?")
    bl("What is FJET's priority customer: DoD captive-carry, commercial space, or orbital launch?")
    bl("What is Tim's view on the Blackstar Orbital partnership vs. what Exos brings?")
    bl("Has Cantor Fitzgerald (May 2026 placement agent) discussed any follow-on raise?")
    bl("Is the AEDC Velocity Alliance RFWP fully submitted with Exos on the roster?")

    h1("Key Positioning Points")
    bl("Exos = one of three FAA-licensed reusable rocket providers. BLK3 FAA-licensed (Mar 2026), first commercial flight early 2027.")
    bl("Exos + Starfighters = commercial test ladder from Mach 2 to 85+ km. No single competitor covers this range.")
    bl("SpaceX IPO repriced the sector — non-SpaceX space infrastructure is the buy, per same narrative FJET uses.")
    bl("BLK3: 135 kg, above 85 km, reusable — complements STARLAUNCH for different payload classes and altitudes.")

    s.append(Paragraph(
        "Prepared by Exos AI Desk  |  October 6, 2026  |  Internal use only — do not share",
        ss["Footer"]))
    return s


if __name__ == "__main__":
    p1 = build_pdf("Exos_Starfighters_Funding_Structure_Options_2026-10-06.pdf", story_internal)
    p2 = build_pdf("Exos_Starfighters_Proposal_DRAFT_2026-10-06.pdf", story_external)
    p3 = build_pdf("Exos_Starfighters_MeetingBrief_Tim_2026-10-06.pdf", story_brief)
    print("\nAll three PDFs written.")
