#!/usr/bin/env python3
"""Nebex deal structure (Jon 2026-10-21 11:13 DM): $5M BLK3 wet lease (Nebex funds, NOT equity) to test Exos reentry
systems as the precursor to the orbital first-flight multi-mission engagement, leveraged through AEDC Velocity (Exos prime).
Also rebuilds the AEDC on-ramp brief as r2 with the equity ask replaced by the wet lease.
import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches

WS = "/Users/exomac/.openclaw/workspace"
D = datetime.date.today().strftime("%Y-%m-%d")
NAVY = RGBColor(0x0A, 0x16, 0x28)


def new(title, subtitle):
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(1); s.top_margin = s.bottom_margin = Inches(0.9)
    st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    p = doc.add_paragraph(); r = p.add_run(title); r.bold = True; r.font.size = Pt(16); r.font.color.rgb = NAVY
    p = doc.add_paragraph(); r = p.add_run(subtitle); r.italic = True; r.font.size = Pt(9.5); r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
    return doc


def h(doc, t):
    p = doc.add_paragraph(); r = p.add_run(t); r.bold = True; r.font.size = Pt(12); r.font.color.rgb = NAVY
    p.paragraph_format.space_before = Pt(10)


def para(doc, t, italic=False):
    p = doc.add_paragraph(); r = p.add_run(t); r.italic = italic; return p


def bullets(doc, items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        if isinstance(it, tuple):
            r = p.add_run(it[0]); r.bold = True; p.add_run(" " + it[1])
        else:
            p.add_run(it)


def table(doc, head, rows):
    t = doc.add_table(rows=1, cols=len(head)); t.style = "Light Grid Accent 1"
    for i, c in enumerate(head):
        t.rows[0].cells[i].text = c
        for r in t.rows[0].cells[i].paragraphs[0].runs: r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, c in enumerate(row): cells[i].text = c
    doc.add_paragraph()


def sources(doc, items):
    h(doc, "Sources")
    for t, u in items:
        p = doc.add_paragraph(style="List Number"); p.add_run(t + " — "); r = p.add_run(u); r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x99)


SRC = [
    ("Arnold AFB, 'AEDC Velocity Alliance advances modernization for future test needs'", "https://www.arnold.af.mil/News/Article-Display/Article/4574989/aedc-velocity-alliance-advances-modernization-for-future-test-needs"),
    ("Aerospace Testing International, AEDC establishes test modernization consortium", "https://www.aerospacetestinginternational.com/news/arnold-engineering-development-complex-establishes-test-modernization-consortium.html"),
    ("BBC Future, 'What are the odds of a successful space launch?' (2023)", "https://www.bbc.com/future/article/20230518-what-are-the-odds-of-a-successful-space-launch"),
    ("C4ISRNET, Varda lands third capsule with AFRL hypersonic data (May 2025)", "https://www.c4isrnet.com/space/2025/05/14/varda-lands-third-space-capsule-carrying-key-hypersonic-flight-data"),
]

# ============================================================ 1. Deal structure
doc = new("Nebex Deal Structure: BLK3 Wet Lease → AEDC Velocity → Orbital Multi-Mission",
          f"Exos Aerospace · INTERNAL · Prepared by Exo for John Quinn · {datetime.date.today():%B %d, %Y} · "
          "Counterparty: Nebex (Tejpaul Bhatia, CEO) · MC #3926")

h(doc, "Bottom line")
para(doc, "Nebex funds a $5M BLK3 wet lease. That is a service contract, not an equity investment. Exos uses the leased BLK3 "
     "flights to test its reentry systems (reentry body and ejectable black box) on suborbital flights. That work qualifies the "
     "same hardware for the orbital first flights Nebex wants to buy. Exos brings the BLK3 flight-test data into AEDC Velocity as "
     "prime, with Nebex as its named launch-access partner. The orbital side is set up as a single multi-mission engagement, so "
     "follow-on flights can use different launch providers and revenue arrives evenly.")

h(doc, "Tej's comments: what they tell us to do")
table(doc, ["What Tej said (10/21)", "Guidance for the structure"], [
    ["The $5M figure didn't faze him.", "Hold $5M as the wet-lease price. Don't discount it to close; any concession goes into scope (more flights or data), not price."],
    ["He can fund the wet lease, not an equity investment.", "Drop the $5M strategic investment from every Nebex document and conversation. No equity, warrants or Rule 504 papers tied to this deal. The lease stands on its own."],
    ["Flights 2–5 can be with different providers under a multi-mission engagement.", "Write the orbital piece as ONE multi-mission engagement (flight 1 plus flights 2–5), with each mission free to name its own provider. Exos stays the integrator across all of them."],
    ["Multi-mission is 'probably a better path'; it evens out revenue.", "Price the engagement as a level per-mission fee across the five missions, not one first-flight discount followed by full-price follow-ons. That smooths cash for both sides."],
    ["(Earlier) He wants a discounted first-flight bay in exchange for follow-on bookings.", "Flight 1 carries the outcome-proof Maiden Flight Data Package, so it earns money even if the rocket fails. Nearly one in two first flights of a new rocket goes wrong [3]."],
])

h(doc, "The three-layer architecture")
para(doc, "Layer 1: Commercial. BLK3 Wet Lease & O&M Agreement (Nebex = Client)")
bullets(doc, [
    ("Vehicle:", "the BLK3 wet-lease template already on #3926 (from Copernic r5), with Appendix I (Orbital First-Flight Precursor Program) as the operative scope."),
    ("Price:", "$5,000,000 for a dedicated BLK3 reentry test campaign. Number of flights: [CONFIRM: Phil, how many flights $5M covers]."),
    ("Proposed payment milestones:", "[50% at signing / 40% at L-120 / 10% after flight data delivery]. This mirrors the Exos standard payload terms; negotiable."),
    ("What flies:", "Exos reentry systems. (a) Reentry body: separation, thermal protection, telemetry during descent, recovery. (b) Ejectable crash-survivable black box: ascent environment (vibration, shock, acoustics, thermal). Suborbital reentry conditions are below orbital speeds, so BLK3 proves the systems and the data chain, not Mach 25 heating. Test envelope: [CONFIRM: Phil]."),
    ("Data rights:", "Exos keeps the reentry-system design IP. Nebex gets a licence to the flight results for marketing the orbital engagement. Government data rights follow each AEDC project. [NEGOTIATE]"),
    ("Timing:", "BLK3 first flights are planned for early 2027. Describe BLK3 as operating under its 14 CFR Part 431 licence, transitioning to Part 450. Never say bare 'licensed'."),
])
para(doc, "Layer 2: Government. AEDC Velocity Alliance (Exos = prime)")
bullets(doc, [
    ("Why it fits:", "AEDC Velocity is an Other Transaction consortium run by AEDC with the Air Force Test Center under 10 U.S.C. §4022, supporting a multibillion-dollar test-modernization portfolio [1][2]. Exos is a member and pitches flight test as the low-cost complement to ground test. Reentry data from BLK3 can be checked against AEDC's tunnels."),
    ("How the lease feeds it:", "The Nebex-funded flights are already paid for, so Exos can offer AEDC project announcements (POAs) flight-test data on those flights at low marginal cost. That makes Exos's bids sharper. Hypersonic reentry data has a proven DoD buyer: AFRL is paying Varda to fly reentry capsules as hypersonic testbeds [4]."),
    ("Nebex's role:", "named launch-access partner (firm-fixed-price sub) on the orbital pieces of POAs Exos bids as prime. This only happens after the compliance gate below. Whether a partner with compliance still pending can be named on a POA is not yet confirmed in the RFWP."),
    ("Keep separate:", "The wet lease is never conditioned on, or credited against, AEDC awards. A tie reads as pay-to-play. Exos is a member; projects are bid individually, nothing is 'awarded'."),
])
para(doc, "Layer 3: Orbital. Multi-mission engagement (Nebex buys, Exos integrates)")
bullets(doc, [
    ("Shape:", "one engagement covering five missions. Flight 1 is the orbital maiden-flight bay at a discount; flights 2–5 can each use a different provider."),
    ("Exos content:", "the BLK3-qualified reentry body and black box fly as the Maiden Flight Data Package on flight 1, paying on any outcome. Exos fills and resells remaining slices; no free slots."),
    ("Revenue:", "level per-mission fee across the five missions. Exos integration revenue recurs on every mission, regardless of provider."),
    ("Phase 2:", "Loft Orbital as a hosting/government-channel option. See the Loft fit assessment on #3926."),
])

h(doc, "Money flow")
table(doc, ["From → To", "What", "Basis"], [
    ["Nebex → Exos", "$5M BLK3 wet lease (reentry test campaign)", "Wet Lease & O&M Agreement + Appendix I"],
    ["AEDC (via POA) → Exos", "Flight-test data / test services", "Velocity project award, bid individually; Exos prime"],
    ["Exos → Nebex", "Launch-access FFP sub share on POAs that include orbital access", "Teaming agreement after compliance gate"],
    ["Nebex → orbital providers", "Bay purchases on flights 1–5", "Nebex's multi-mission engagement"],
    ["Nebex → Exos", "Per-mission integration fee, flights 1–5", "Multi-mission integration agreement [to draft]"],
])

h(doc, "Gate (unchanged; nothing moves until it clears)")
bullets(doc, [
    "CSL/OFAC and SAM exclusions screening: CLEAN on 10/21 (Tej, Nebex, Anand Subramanian, Manlio Di Stefano).",
    "ExoSign due-diligence and background-check authorization: SENT 10/21 (env e1018b1c5b05), awaiting signature.",
    "Mutual NDA, then the wet lease, then the teaming agreement.",
    "Empowered Official export review before ANY reentry-system data is shared. This is a foreign-influence flag: co-founder Manlio Di Stefano is a former Italian Vice Minister of Foreign Affairs.",
    "Exos supports Nebex's SAM/CAGE, JCP (DD 2345) and CMMC only if all screening stays clean. SAM shows 'Nebex Solutions, LLC' as INACTIVE (UEI JHD6JZGB2HJ7, CAGE 7YE79); it's not yet confirmed to be the same company.",
])

h(doc, "Next conversation with Tej: 30-second version")
para(doc, "\"Here's how we'd put it together. Your $5 million funds a BLK3 wet lease: dedicated flights where we test our reentry "
     "body and black box before they go up on an orbital first flight. Those same flights give the Air Force flight-test data "
     "through AEDC Velocity, where Exos is a member and you'd come in as our launch-access partner. Then we wrap your orbital "
     "flights into one multi-mission engagement, any provider, level pricing per mission. Next step is the due-diligence form "
     "and an NDA.\"", italic=True)

h(doc, "Keep out of the conversation")
bullets(doc, [
    "Any equity, investment or 'strategic investment' language. That track is dead for Nebex.",
    "'$2.6B', member count, POA mechanics (members-only Industry Day material). Say 'multibillion-dollar'.",
    "'Awarded' or 'contract won' for Velocity.",
    "BLK3 Mach or reentry-temperature numbers until Phil confirms the envelope.",
    "'On our BLK3 manifest'. There is no manifest yet.",
])

h(doc, "What changes on #3926")
bullets(doc, [
    "AEDC Velocity On-Ramp Brief → r2 (attached): $5M strategic investment replaced by the $5M wet lease; script updated.",
    "BLK3 wet-lease template + Appendix I: still valid as-is. Its clause that no investment is required now matches the deal exactly. Populate with Nebex details and the $5M reentry scope once the MNDA is signed.",
    "Rule 504 / David Mitchell review: not needed for Nebex.",
])
sources(doc, SRC)
f1 = f"{WS}/drafts/Nebex_Deal_Structure_{D}.docx"; doc.save(f1)

# ============================================================ 2. AEDC brief r2
doc = new("AEDC Velocity Alliance — Partner On-Ramp Brief",
          f"Exos Aerospace · INTERNAL · Prepared by Exo for John Quinn · {datetime.date.today():%B %d, %Y} · r2 · "
          "Prospect: Nebex (Tejpaul Bhatia) · r2 change: the $5M is a BLK3 wet lease Nebex funds, not an equity investment (Tej, 10/21)")
h(doc, "Construct")
bullets(doc, [
    ("Vehicle:", "AEDC Velocity Alliance, an Other Transaction consortium run by AEDC with the Air Force Test Center under 10 U.S.C. §4022 and §2808a, supporting a multibillion-dollar portfolio of test-infrastructure projects [1][2]. Exos is an active member (Opportunity 2 membership effective 30 Sep 2026). Work arrives as individual project announcements (POAs) on AcqBot."),
    ("Fit:", "Exos's Velocity positioning is flight test as a low-cost complement to ground test. The reentry body gives AEDC flight data to check against its tunnels; the black box gives ascent-environment data."),
    ("Precursor:", "Nebex funds a $5M BLK3 wet lease. Its flights test the Exos reentry systems ahead of the orbital first flight. Those already-funded flights let Exos offer Velocity POAs flight data at low marginal cost."),
    ("Structure:", "Exos is prime and integrator (reentry body, black box, recovery, payload integration, DoD interface). Nebex is a firm-fixed-price sub supplying launch access under a multi-mission engagement (flight-1 bay plus flights 2–5, any provider). Exos keeps a substitution right so one maiden-flight failure doesn't sink a Velocity deliverable."),
    ("Paths in:", "(1) Named partner under Exos on a POA Exos bids as prime. This is the fastest route and the one we recommend. (2) Nebex's own membership later; the Request for Whitepapers stays open to new applicants through 30 Sep 2032 (FA9101-26-9-Velocity_Alliance)."),
])
h(doc, "Gate and compliance support (Jon 10/21 06:39)")
para(doc, "Exos supports Nebex toward Velocity requirements ONLY if OFAC / restricted-party screening is clean.")
bullets(doc, [
    ("Step 1:", "Tej signs the ExoSign Partner Due Diligence Intake & Background Check Authorization (sent 10/21, env e1018b1c5b05)."),
    ("Step 2:", "OFAC, Consolidated Screening List and SAM.gov exclusions on him, Nebex and listed owners and officers. First pass on 10/21 was CLEAN. Any later match stops everything and goes to John only."),
    ("Step 3 if clean:", "background report and company diligence (registry, litigation, media, beneficial ownership)."),
    ("Step 4 if all clean, Exos assists:", "SAM.gov registration (UEI + CAGE); JCP certification (DD Form 2345); CMMC Level 2 self-assessment in SPRS; mutual NDA, then the wet lease, then the teaming agreement; Empowered Official export review before any reentry or vehicle data is shared."),
    ("Interim:", "Exos bids as prime and names Nebex as partner. Whether a partner with compliance still pending can be named on a POA is not yet confirmed; check the RFWP before relying on it."),
    ("Cost logic:", "Exos's compliance support and integration work are priced into the wet-lease service. There is no investment ask."),
])
h(doc, "30-second introduction script")
para(doc, "\"Here's how we'd put it together. Your $5 million funds a BLK3 wet lease: dedicated flights where we test our reentry "
     "body and black box before they go up on an orbital first flight. Those same flights give the Air Force flight-test data "
     "through AEDC Velocity, a contract vehicle for a multibillion-dollar test modernization program that's open through 2032. "
     "Exos is a member, and you'd come in as our launch-access partner. Then we wrap your orbital flights into one multi-mission "
     "engagement. Next step is the due-diligence form and an NDA.\"", italic=True)
h(doc, "Keep out of the conversation")
bullets(doc, [
    "Any equity or investment ask. Tej funds the lease, not equity (10/21).",
    "\"$2.6B\". It was briefed at the members-only Industry Day and isn't in any public source. Say \"multibillion-dollar\".",
    "Member count (82) and POA mechanics, which come from member-only notices.",
    "\"Awarded\" or \"contract won\". Exos is a member; projects are bid individually.",
    "Conditioning the lease on Velocity awards. Keep them independent; a tie reads as pay-to-play to DoD.",
    "BLK3: say \"first flights planned for early 2027\"; never bare \"licensed\".",
])
sources(doc, SRC[:2])
f2 = f"{WS}/drafts/AEDC_Velocity_OnRamp_Brief_{D}_r2.docx"; doc.save(f2)
print(f1); print(f2)
