#!/usr/bin/env python3
"""NYK x Exos — Sea Recovery & Sea Launch Strategy (internal, for Jon). Ranked options:
dry-pool drone-ship recovery, shore reentry/landing first-launch proof, ocean-as-flame-trench
offshore launch vessel, and supporting plays. Plain editable .docx (internal; not letterhead)."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches

OUT = "drafts/nyk/NYK_Sea_Recovery_and_Launch_Strategy_2026-10-18.docx"
NAVY = RGBColor(0x0B, 0x2A, 0x4A)

d = Document()
st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
for s in d.sections:
    s.left_margin = s.right_margin = Inches(0.9)


def H(t, lvl=1):
    p = d.add_paragraph(); r = p.add_run(t); r.bold = True
    r.font.size = Pt(15 if lvl == 0 else 12.5 if lvl == 1 else 11); r.font.color.rgb = NAVY
    p.paragraph_format.space_before = Pt(10 if lvl else 0); p.paragraph_format.space_after = Pt(4)


def P(t, bold_lead=None, italic=False, size=None):
    p = d.add_paragraph(); p.paragraph_format.space_after = Pt(5)
    if bold_lead:
        p.add_run(bold_lead).bold = True
    r = p.add_run(t); r.italic = italic
    if size: r.font.size = Pt(size)


def B(t, bold_lead=None):
    p = d.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(2)
    if bold_lead:
        p.add_run(bold_lead).bold = True
    p.add_run(t)


def table(rows, widths):
    t = d.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Light Grid Accent 1"
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j); c.text = ""; c.width = Inches(widths[j])
            r = c.paragraphs[0].add_run(val); r.font.size = Pt(9); r.bold = i == 0
    d.add_paragraph().paragraph_format.space_after = Pt(2)


S = {
    "ssf": "https://www.nyk.com/english/news/2025/20250422_01.html",
    "aip": "https://www.nyk.com/english/news/2025/20250724_02.html",
    "osaka": "https://www.nyk.com/english/news/2026/20260701_01.html",
    "classnk": "https://www.classnk.or.jp/hp/pdf/research/rd/2024/09_e06.pdf",
    "hospo": "https://hokkaidospaceport.com/",
    "honda": "https://global.honda/en/topics/2025/c_2025-06-17ceng.html",
    "roi": "https://rocketlabcorp.com/updates/rocket-lab-reveals-ocean-platform-for-neutron-rocket-landings-at-sea",
    "bollinger": "https://www.bollingershipyards.com/news/rocket-lab-selects-bollinger-shipyards-to-support-modification-of-neutron-landing-platform",
    "rl_salt": "https://spaceflightnow.com/2020/11/05/rocket-lab-to-attempt-booster-recovery-on-next-mission",
    "seagate_abs": "https://seagatespace.com/abs-approves-seagate-spaces-modular-offshore-launch-platform",
    "seagate_ff": "https://spacenews.com/seagate-space-signs-mou-with-firefly-aerospace-to-collaborate-on-offshore-launch-infrastructure-for-alpha",
    "seagate_oce": "https://spacenews.com/seagate-space-and-oceaneering-join-forces-to-build-the-future-of-offshore-launch-infrastructure",
    "spacex_rigs": "https://spacenews.com/spacex-drops-plans-to-covert-oil-rigs-into-launch-platforms",
    "cz_sea": "https://www.space.com/china-building-ship-rocket-launches-at-sea",
    "odyssey": "https://www.satellitetoday.com/finance/2007/02/12/sea-launch-assesses-damage-to-launch-platform",
    "faa": "https://www.faa.gov/data_research/commercial_space_data/licenses",
}

H("NYK × Exos — Sea Recovery and Sea Launch Strategy", 0)
P("Six ranked options, from highest strategic potential to lowest, with execution sequence, proof plan and "
  "export gates. INTERNAL — for Jon. Not for NYK distribution in this form. Prepared 2026-10-18 for the "
  "Oct 28, 2026 8:00 AM JST NYK meeting (Tue Oct 27, 6:00 PM CDT). MC #3808.", italic=True, size=9.5)

H("1. Bottom line")
B(" Lead with the drone-ship ‘dry pool’ — BLK3 recovered into a contained water basin on an NYK vessel, never "
  "touching seawater. It is the option NYK cannot get from anyone else, it plugs directly into NYK’s funded "
  "JAXA SSF recovery-vessel program, and Exos owns the vehicle side of the interface.", "Recommendation.")
B(" BLK3 first launch from Hokkaido Spaceport (HOSPO), reentry, and recovery on the shore. Low risk, it makes "
  "Exos the first live vehicle NYK touches, and it is the gating proof for every sea option.", "Prove it first:")
B(" NYK designs a modified barge / twin-hull vessel that launches over open water and uses the ocean as the "
  "flame trench. Largest long-run value (orbital, BLK4 Heavy plus third-party launchers), longest horizon. "
  "Pitch it as the Phase 3 vision on the same hull family, not a near-term ask.", "Big swing:")
B(" File a provisional patent on the dry-pool recovery and open-water flame-duct concepts BEFORE any "
  "design-level disclosure to NYK, and keep Oct 28 at capability level until the TAA is approved.",
  "Protect the IP first:")

H("2. What NYK already has (why this fits)")
B(f" NYK leads, with MHI, a JAXA Space Strategy Fund project for an offshore reusable-rocket recovery vessel: "
  f"capture at sea, securing and residual-propellant discharge, a landing deck for jet blast and impact, remote "
  f"operation, and a prototype vessel with sea trials. Source: {S['ssf']}", "Funded recovery program.")
B(f" ClassNK Approval in Principle for the concept, July 2025 ({S['aip']}); University of Osaka joint research "
  f"on vessel motion from July 2026 ({S['osaka']}).", "Progress.")
B(f" A 2024 ClassNK study notes the seas around Japan are rougher than off Florida, so barge-style recovery "
  f"that works for SpaceX may not transfer; a large, sea-kindly ship is needed. Source: {S['classnk']}",
  "Japan-specific problem.")
B(" NYK has a vessel program but, as far as we can find, no flying vehicle committed to it. Exos has a "
  "reusable vehicle and needs a sea-recovery partner. That gap is the whole strategy.", "The gap.")

H("3. Ranked options")
table([
    ["Rank", "Option", "Strategic value", "Exos $ potential", "Time to first proof", "Exos control", "Key risk"],
    ["1", "Dry-pool drone-ship recovery (BLK3) — world-first", "Very high", "High", "~18–30 mo",
     "High (vehicle side + IP)", "Novel; sea-state dispersion into a small target"],
    ["2", "Ocean-as-flame-trench launch vessel (BLK4 Heavy + third parties)", "Very high (long run)",
     "Very high", "4–6+ yrs", "Medium", "Capital; BLK4 Heavy not yet funded"],
    ["3", "Recovery-as-a-Service JV for Japanese launchers", "High", "Medium–high (recurring)", "~3 yrs",
     "Medium", "Needs #1 or #4 proof first"],
    ["4", "HOSPO first launch: reentry + shore landing (BLK3)", "High (gating proof)", "Medium", "~12–18 mo",
     "High", "ITAR license timing; site approvals"],
    ["5", "BLK3 mobile sea launch from NYK vessel", "Medium", "Medium", "~3 yrs", "Medium",
     "Platform motion; range/licensing at sea"],
    ["6", "NYK as exclusive space-logistics carrier (TX→Japan, Italy)", "Medium", "Low (cost saver)",
     "Next shipment", "High", "ITAR license per shipment"],
], [0.4, 1.7, 0.9, 0.9, 0.8, 0.9, 1.3])
P("Ranking = strategic potential (uniqueness × value × fit with NYK’s funded program). Execution order is "
  "different: see Section 5. Time-to-proof figures are Exos planning estimates, not commitments, and assume "
  "BLK3 first flight in early 2027 at Spaceport America.", italic=True, size=9)

H("Option 1 — Dry-pool drone-ship recovery (BLK3): be first", 2)
P("Concept: BLK3 returns under its drogue + main canopy and descends into a contained, fresh-water (or "
  "foam/cushion) basin carried on an uncrewed NYK vessel — or slung between a small group of drone ships. "
  "The basin absorbs the landing, the vehicle never contacts seawater, and the vessel safes and secures it "
  "remotely.")
B(" Seawater is what drives refurbishment cost in water recovery; Rocket Lab built its helicopter-catch "
  f"program specifically to keep Electron out of salt water ({S['rl_salt']}, 2020 — still its stated "
  "rationale). A basin gives water-landing softness without the salt.", "Why it matters.")
B(" Lands squarely on NYK’s SSF scope items: fixed-point capture, securing, residual-propellant discharge, "
  "remote ops. NYK gets its first real vehicle; Exos gets a recovery mode no U.S. competitor has.",
  "Fit with NYK.")
B(" Variants to put in the study: (a) on-deck basin on one large, sea-kindly hull (answers the ClassNK "
  "rough-sea point); (b) 4–6 drone ships holding an inflatable-boom ‘pool’ (~150 m) — the concept already "
  "floated with Honda on 10/13, but note a boom pool alone is still seawater unless it carries a liner or "
  "bladder; (c) net/airbag catch deck as a fallback.", "Variants.")
B(" We found no public record of a launch vehicle recovered into a water basin on a vessel. Treat ‘world "
  "first’ as unverified until a patent / prior-art search confirms it — do not use the phrase externally yet.",
  "‘First’ claim.")
B(" Landing dispersion under canopy vs. basin size; vessel motion; wind at descent. Phase 1 study must size "
  "the basin against BLK3 dispersion data before anyone promises a date.", "Hard part.")
B(" Payload return in minutes is already an Exos strength; a dry recovery keeps it true at sea.",
  "Payload angle.")

H("Option 2 — Ocean as the flame trench: an NYK launch vessel for orbital", 2)
P("Concept: NYK modifies a barge, semi-submersible or twin-hull vessel so the launch mount sits over open "
  "water. The plume goes straight down into the sea — no concrete flame trench, no deflector to rebuild, "
  "and an unlimited deluge supply pumped from the ocean. The same hull family can later carry the recovery "
  "basin from Option 1, so one fleet launches and recovers.")
P("Design changes we would ask NYK to study (engineering hypotheses, not validated):", bold_lead=None)
B(" Twin-hull (catamaran) or open-stern ‘moon pool’ layout with the mount bridging the gap, so exhaust exits "
  "between hulls instead of hitting the deck.", "Open-water flame duct.")
B(" Ballast down to a stable, semi-submerged launch draft for liftoff (the way the Odyssey platform worked), "
  "then de-ballast for transit.", "Launch draft.")
B(" Ocean-fed water deluge for acoustic suppression; blast shielding and thermal protection for deck "
  "equipment (Rocket Lab is fitting both on its barge — "
  f"{S['bollinger']}).", "Acoustics & heat.")
B(" Plume-driven spray and steam, acoustic reflection off the water, liftoff loads on a moving deck, and "
  "salt spray on the vehicle before launch.", "Risks to test.")
P("Evidence the market is moving this way:", bold_lead=None)
B(f" Seagate Space’s uncrewed semi-submersible launch platform received the first ABS Approval in Principle "
  f"under ABS’s new offshore-spaceport requirements ({S['seagate_abs']}); MOU with Firefly for Alpha "
  f"(Apr 6, 2026: {S['seagate_ff']}); MOU with Oceaneering, first missions targeted as early as 2027 "
  f"({S['seagate_oce']}).", "U.S.:")
B(f" China flies orbital rockets from converted barges in the Yellow Sea and is building a dedicated "
  f"launch ship ({S['cz_sea']}).", "China:")
B(f" SpaceX dropped its plan to convert two oil rigs into Starship platforms ({S['spacex_rigs']}) — "
  f"proof this is hard at super-heavy scale and a reason to start at BLK3/BLK4 scale.", "Cautionary:")
B(f" Sea Launch’s Odyssey lost its flame deflector in a 2007 launch failure ({S['odyssey']}, historical) — "
  f"the open-water duct removes that single point of failure.", "Historical:")
B(" BLK4 Heavy (three BLK4 cores) is Exos’s planned, capital-gated orbital path — never present it as "
  "built or funded. The pitch to NYK: a vessel class that serves Japan’s orbital launchers too, with Exos as "
  "launch operator / anchor tenant.", "Exos framing.")
B(" Japan is short on launch sites; a vessel that launches from open ocean adds sites, inclinations and "
  "range flexibility without new coastline. (Our inference — validate with NYK and JAXA on Oct 28.)",
  "Why Japan cares.")

H("Option 3 — Recovery-as-a-Service JV for Japanese launchers", 2)
P(f"NYK owns and runs the vessels; Exos supplies the operator procedures, vehicle-interface standards, "
  f"recovery-on-anomaly (drogue + canopy) hardware and safing know-how. Customers: JAXA’s reusable program and "
  f"Japanese developers such as Honda, which flew and landed a reusable test rocket at Taiki in June 2025 "
  f"({S['honda']}). Recurring revenue per recovery. Needs Option 1 or 4 as proof first. Requires a TAA, and "
  f"must not cut across the Honda track (Honda uses its own landing-ship arrangement).")

H("Option 4 — HOSPO first launch: reentry and shore landing (the proof)", 2)
P(f"NYK ships BLK3 and its GSE Texas → Hokkaido; BLK3 flies from HOSPO, Taiki, on the Pacific coast "
  f"({S['hospo']}), reenters and lands under canopy on shore or in the near-shore zone. NYK’s team runs "
  f"securing, safing and remote-operation steps on a real vehicle. Outcome: Exos is the first vehicle NYK "
  f"recovers, NYK gets procedure data for SSF, and both get a public milestone in Japan.")
B(" Early 2027 first campaign is at Spaceport America; a Japan campaign follows after that and after export "
  "licensing. Pick the window in the Phase 1 study, not on Oct 28.", "Timing guardrail.")
B(" Proves end to end: ocean shipping, Japan site ops, reentry, recovery and safing — every building block "
  "of Options 1–3.", "What it buys.")

H("Option 5 — BLK3 mobile sea launch", 2)
P(f"Launch BLK3 itself from an NYK vessel — responsive launches for hypersonic and defense test work, and "
  f"access to new trajectories. Seagate positions its Firefly platform for exactly these missions "
  f"({S['seagate_ff']}). Smaller prize than Option 2 but a useful stepping stone onto the same hull. "
  f"FAA licensing and range safety at sea need separate work.")

H("Option 6 — NYK as exclusive space-logistics carrier", 2)
P("NYK as preferred ocean carrier for BLK3/GSE to Japan and, later, the Sardinia option (internal). Saves "
  "cost and builds the relationship; each shipment needs its own ITAR license. Already in motion (OPP-636).")

H("4. Strategic logic — why lead with #1, prove with #4, sell #2")
B(" #1 is the only option where Exos holds something NYK cannot buy elsewhere — a flying vehicle plus a "
  "recovery mode designed around it.", "Uniqueness.")
B(" #4 converts talk into a dated, low-risk event and makes Exos ‘first’ in fact, not in slides.", "Proof.")
B(" #2 is the long-run platform: one NYK hull family that launches (ocean flame trench) and recovers "
  "(dry pool). It turns NYK from a vessel supplier into a launch-infrastructure owner, with Exos as operator.",
  "Platform.")
B(" #3, #5, #6 monetize the same assets and keep NYK engaged between flight campaigns.", "Fill-in.")

H("5. Execution sequence")
table([
    ["Step", "What", "Gate / owner", "Target"],
    ["0", "Provisional patent: dry-pool recovery + open-water flame-duct vessel", "Exos / Counsel",
     "Before design-level disclosure"],
    ["1", "Oct 28 meeting: capability-level only; ask NYK’s first-vehicle plans; float #1, #4 and #2 vision",
     "Jon", "Oct 28 JST"],
    ["2", "MNDA → Strategic Engagement Agreement + down payment (per 10/18 proposal)", "NYK / Exos", "[__]"],
    ["3", "TAA filed (defense services to NYK); per-shipment export licenses", "EO John Quinn / Denise Shirey",
     "File right after SEA"],
    ["4", "Phase 1 joint study: basin sizing vs. BLK3 dispersion; shore-landing campaign plan; vessel "
     "flame-duct concept", "Joint", "Starts on TAA approval"],
    ["5", "HOSPO first launch + shore recovery (Option 4)", "Exos + NYK + HOSPO", "After 2027 SA campaign"],
    ["6", "Dry-pool sea recovery demo (Option 1)", "Exos + NYK", "After step 5"],
    ["7", "Launch-vessel concept + funding path (Option 2), tied to BLK4 Heavy capital", "Joint", "Phase 3"],
], [0.4, 3.4, 1.5, 1.4])

H("6. Guardrails")
B(" BLK3 has not flown commercially; Exos holds a §431 license (renewed 3/13/26) and is transitioning to "
  f"Part 450 ({S['faa']}). Never say ‘FAA-licensed BLK3’ bare.", "Claims.")
B(" BLK4 / BLK4 Heavy are in development and capital-gated — describe as the planned orbital path.",
  "Orbital.")
B(" No technical data, drawings or design-level detail to NYK until the TAA is approved; every shipment is "
  "its own license. Export owner = EO John Quinn, reviewer Denise Shirey.", "Export.")
B(" Japan materials stay on the Japan track; Sardinia stays internal; nothing here goes to SBI/650.",
  "Tracks.")
B(" No free flights — the first recovery is a paid, reserved position.", "Commercial.")

H("7. Questions to ask NYK on Oct 28")
for q in ["Which vehicles is the SSF recovery vessel being designed around, and is any flying vehicle committed?",
          "Is the hull sized for rough Japanese seas (per ClassNK) — and could it carry an on-deck basin?",
          "Would NYK consider a vessel that also launches — and has NYK or MHI studied an open-water flame duct?",
          "Prototype vessel and sea-trial dates: can a shore or near-vessel recovery fit before them?",
          "Can a U.S. operator join under SSF, or must this be a separate NYK agreement?"]:
    B(" " + q)

d.save(OUT)
print(OUT)
