#!/usr/bin/env python3
"""INTERNAL 1-2 page brief for Jon: Honda visit (Hokkaido, 13-15 Oct 2026). Companion to build_honda_partnership_deck.py."""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = "/Users/exomac/.openclaw/workspace/drafts/Honda/Exos_Honda_Visit_Summary_INTERNAL_2026-10-13.docx"
OR = RGBColor(0xF2, 0x6A, 0x21); GR = RGBColor(0x55, 0x55, 0x5c)
d = Document()
for s in d.sections:
    s.left_margin = s.right_margin = Inches(0.7); s.top_margin = s.bottom_margin = Inches(0.55)
st = d.styles["Normal"]; st.font.name = "Arial"; st.font.size = Pt(9.5)
st.paragraph_format.space_after = Pt(2); st.paragraph_format.space_before = Pt(0)

def P(text="", bold=False, size=None, color=None, after=2, italic=False):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(after)
    if text:
        r = p.add_run(text); r.bold = bold; r.italic = italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = color
    return p
def RUNS(parts, style=None, after=1):
    p = d.add_paragraph(style=style); p.paragraph_format.space_after = Pt(after)
    for t, b in parts:
        r = p.add_run(t); r.bold = b
    return p
def B(text, lead=None): return RUNS(([(lead + " ", True)] if lead else []) + [(text, False)], "List Bullet")
def H(text): P(text, True, 11, OR, after=1).paragraph_format.space_before = Pt(5)

P("DRAFT — INTERNAL / EXOS ONLY — NOT FOR HONDA — not sent", True, 8.5, OR, after=0)
P("Honda visit brief — Hokkaido, 13–15 October 2026", True, 15, after=0)
P("For: Jon Quinn (Cofounder & CEO, Empowered Official)  ·  Prepared 13 Oct 2026  ·  Companion deck: Exos_Honda_Partnership_Briefing_2026-10-13.pptx (12 slides, external)", size=8.5, color=GR, after=4)

H("Bottom line")
P("Three focus areas with Honda R&D: (1) a Hokkaido International Trade Zone at HOSPO with Honda as a co-located partner, supplier and customer; "
  "(2) evaluate/acquire Honda-built communications systems; (3) evaluate/acquire Honda-built flight termination systems (FTS). Structure: Honda provides hardware; "
  "Exos pays in kind with reusable flight services and TAA-gated reusable-rocket consulting, both sides valued on an agreed schedule at standard pricing (no free flights). "
  "Exos initiates the TAA. The deck is humble and question-led: we ask about their FTS and comms; we claim no knowledge of either.")

H("What Honda has publicly done (verified)")
B("17 Jun 2025, Honda R&D launch-and-landing test at Honda's own facility in Taiki Town, Hokkaido: 6.3 m long, 85 cm dia., 900 kg dry / 1,312 kg wet; reached 271.4 m; landed within 37 cm of target; 56.6 s flight. Combustion and hover tests since 2024. [1]")
B("Goal: technological capability for a suborbital launch by 2029. Still \"fundamental research\" with no commercialization decision. [1]")
B("The test vehicle carried \"a safety system to prevent deviation from a pre-defined flight corridor, speed and attitude conditions\". Safe distance was set per Japanese Cabinet Office guidelines (1 km restricted radius). This is our opening for the FTS questions. [1]")
B("Note: Honda's site is its own facility in Taiki, not HOSPO. SPACE COTAN took over HOSPO operations under a 15-year concession from 1 Oct 2026; LC1 operations are due by end of FY2026. [3]")

H("The three focus areas")
t = d.add_table(rows=1, cols=5); t.style = "Light Grid Accent 2"
hdr = ["Area", "Exos objective", "Honda's likely interest", "Path forward", "Risks / gates"]
for i, h in enumerate(hdr):
    c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8.5)
rows = [
 ("1. Hokkaido ITZ", "Container-as-Zone at HOSPO: all integration of US hardware by Exos/US contractor in a monitored container; temporary admission for vehicle (DSP-73 <4 yr + bonded storage) and payloads (Carnet/TIB). Honda as anchor tenant/partner.",
  "Taiki is Honda's test home; shared range, weather and logistics; a domestic route to reusable flight data before its own 2029 goal.",
  "Non-binding HOSPO/SPACE COTAN MOU (zero legal spend), aligned with the 15 Oct HOSPO working meeting → feasibility study → DDTC CJ + advisory opinion and Japan consultations when there is a contract → pilot.",
  "Concept only; no approval exists. DDTC appetite for a forward-based Cat IV vehicle. Export counsel deferred until a contract. No controlled data to SPACE COTAN/Honda before the TAA."),
 ("2. Comms", "Evaluate, then acquire, Honda telemetry/command/GNSS/antenna hardware for reusable vehicles, paid in kind.",
  "Real-flight, recovered-hardware data on Honda units; external validation of its avionics.",
  "Q&A (deck slide 11) → NDA → eval units → bench/ground test → hosted flights → supply agreement.",
  "Japan export: METI approval may be needed under FEFTA Art. 48(1) (goods) / 25(1) (technology) [8], TBC by Honda. US import classification TBC. Spectrum licensing in the US."),
 ("3. FTS", "Evaluate, then acquire, Honda FTS/flight-safety hardware, paid in kind.",
  "Path to US-range qualification for its own system; sales outside Honda.",
  "Q&A (slide 10) → design review against RCC 319 (current ed. 319-25, Jun 2025) [6] and FAA AC 450.143-1 [7] under the TAA → eval units → qualification → supply.",
  "Honda's system is built for a ~300 m hop in a 1 km keep-out. Qualification gap to RCC 319 could be large and costly. Helping Honda qualify = defense service, so TAA first. METI/US classification TBC."),
]
for row in rows:
    cells = t.add_row().cells
    for i, v in enumerate(row):
        cells[i].text = ""; r = cells[i].paragraphs[0].add_run(v); r.font.size = Pt(8); r.bold = (i == 0)
for row in t.rows:
    for i, w in enumerate([0.85, 1.75, 1.35, 1.75, 1.6]): row.cells[i].width = Inches(w)

H("Partnering structure: Honda hardware ↔ Exos in-kind reusable services")
B("Honda: FTS units, comms units, possibly test support at Taiki. Exos: reusable suborbital flight services, TAA-gated consulting, ITZ integration/ops. Both valued at standard pricing on a jointly agreed valuation schedule. The deck shows no prices and no $35K.")
B("Sequence: non-binding framework partnering agreement → definitive supply and services agreements. Start small (eval units ↔ hosted flights). Flight services from BLK3 (\"preparing for flight, early 2027\"). Never say \"on our BLK3 manifest\".")

H("The TAA, and how it ties to the $35K Phase 1 offer (MC #3704)")
B("22 CFR §124.1: DDTC must approve an agreement before Exos furnishes defense services (§120.32) to Honda, even using public-domain data [5]. Until then, exchanges stay non-technical/public-level. Exos may RECEIVE Honda data; Exos's sharing is what's controlled. EO = John Quinn; ITAR reviewer = Denise Shirey.")
B("Drafted offer: Phase 1 USD 35,000 fixed fee (50% on signature / 50% at DDTC submission). TAA submitted within 45 days of Honda inputs, ~90-day Phase 1. Counsel at cost with no markup on a prepaid estimate. Credited to Phase 2 if Honda signs within 6 months. Note: v3 (13 Oct, addressed to Sato-san, Honda R&D, Wako) is the latest version, not v2.")
RUNS([("[DECIDED 13 Oct, D-7282073: as recommended] Run the barter partnership ALONGSIDE, with ONE TAA. ", True),
      ("Keep the $35K Phase 1 as cash, since it funds real counsel and EO time and keeps the 45-day filing clock. Write the TAA scope broad enough to cover all three focus areas: reusable-rocket consulting, FTS/comms evaluation and integration, and ITZ test operations. Then the hardware-for-flights barter needs no second filing. Paper the barter in a separate non-binding framework agreement. Allow in-kind credit against Phase 2 and flights, never Phase 1. "
       "Why not fold the TAA into the barter: valuing barter takes weeks, which would delay the TAA, and it would replace committed cash with in-kind credit.", False)], "List Bullet")

H("Key asks of Honda")
for a in ["Honda's answers to the FTS and comms questions (deck slides 10–11), at a public level now and detail under NDA.",
          "Sign the $35K Phase 1 letter and a mutual NDA; name the Honda R&D entities/people, a single POC and the intended end use (all needed for the TAA).",
          "Interest in a framework partnering agreement (hardware ↔ in-kind flights) and in eval units.",
          "Permission to mention Honda's interest at the 15 Oct HOSPO/SPACE COTAN meeting, and willingness to join a Taiki ITZ MOU.",
          "Honda to confirm METI export treatment for its hardware/technology."]:
    B(a)

H("Talking points (partnership-first, humble)")
for a in ["Open with respect for their 37 cm landing and 2029 goal. \"We come to learn as much as to offer.\"",
          "Exos: FAA-licensed reusable suborbital operator (14 CFR Part 431, transitioning to Part 450) [4]. Payload recovery. BLK3 preparing for flight, early 2027.",
          "Complementary strengths: Honda engineering and manufacturing; Exos licensed reusable flight operations and US range experience.",
          "Compliance first: Exos files the TAA; until then we keep it public-level. This protects Honda too.",
          "Avoid: superlatives (only/first/fastest, \"one of three FAA-licensed\"); RDRE/propulsion-provider framing; vehicle tech data; prices in the room unless Honda asks about Phase 1."]:
    B(a)

H("Other [JON DECISION] items and risks")
B("[DECIDED 13 Oct, D-7282073] Denise Shirey is NOT named on the external deck; slide 8 shows the Empowered Official role only. The wet-lease/NCE vehicle model stays out of the Honda deck; the ITZ is presented at concept level only.")
B("Risks: Honda may see Exos as a competitor or be unwilling to sell hardware while still in research. Its FTS may be far from RCC 319, so in-kind value may exceed the hardware's worth. Barter valuation, tax and transfer pricing need review by counsel. Deemed-export exposure at Taiki if US data is shared. In-kind flights depend on the BLK3 schedule.")

H("Sources")
for s in ["[1] Honda Global, \"Honda Conducts Successful Launch and Landing Test of Experimental Reusable Rocket,\" 17 Jun 2025, global.honda/en/topics/2025/c_2025-06-17ceng.html",
          "[2] Honda R&D, \"SPACETIDE 2025: Honda's Challenge,\" 2025, global.honda/en/RandD/activity/rdtopics/spacetide2025",
          "[3] HOSPO, \"HOSPO Transitions to Concession Model; SPACE COTAN Begins Operation ... October 1,\" 2026, hokkaidospaceport.com/en/news/2306",
          "[4] Exos Aerospace, Capabilities, exosaero.com/capabilities (accessed Oct 2026)",
          "[5] 22 CFR §124.1, §120.32 (eCFR, current)",
          "[6] RCC 319-25, Flight Termination Systems Commonality Standard, Jun 2025, trmc.osd.mil",
          "[7] FAA AC 450.143-1, Federal Register, 14 May 2025, federalregister.gov/d/2025-08496",
          "[8] Hogan Lovells, \"Japan's New Chip Equipment Export Rules Take Effect,\" 2023 (FEFTA Arts. 48(1), 25(1)), hlc.com",
          "Internal: drafts/Honda/Exos_Honda_Consulting_TAA_Engagement_Letter_v3_35K_2026-10-13.docx; memory on the ITZ and Japan seed."]:
    P(s, size=7.5, color=GR, after=0)
d.save(OUT); print(OUT)
