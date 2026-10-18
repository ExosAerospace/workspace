# -*- coding: utf-8 -*-
"""Shared content model for the Exos VSFB MDZ whitepaper (VSFBMDZCall).
Rendered by build_vsfb_mdz_docx.py (Word, letterhead) and build_vsfb_mdz_pdf.py (reportlab twin).
Markup: **bold**. Block types: title, sub, cover, h1, h2, p, b, decision, table, note, pb.
Outline mirrors Exhibit A ("White Paper Request Summary") of the call VERBATIM.
"""

DATE = "2026-10-15"
MARK = "Exos Proprietary — not for public release"
DIST = ("Exos Proprietary — Submitted for U.S. Government planning use under VSFBMDZCall \u00a72.1; not for public release.")

SRC = {
 1: "SAM.gov, “Vandenberg Space Force Base (VSFB) Call for Whitepapers for Mission Development Zone (MDZ) Outgrant,” "
    "Special Notice VSFBMDZCall, notice ID 053436c19dbd4979a19587b059158969, posted 30 Sep 2026 (due date extended to "
    "16 Oct 2026, 4:00 PM PT), with attachment 260901_RFI-VSFB_MDZ.pdf (SLD 30/XPR, 14 Aug 2026), Exhibits A and B.",
 2: "SLD 30 Public Affairs, “SLD 30 Celebrates 5th Anniversary,” May 2026 — vandenberg.spaceforce.mil/News/Article-Display/Article/4485076.",
 3: "U.S. Government Accountability Office, GAO-25-107228, “National Security Space Launch: Increased Commercial Use of "
    "Ranges Underscores Need for Improved Cost Recovery,” 2025 — files.gao.gov/reports/GAO-25-107228/index.html.",
 4: "Space Systems Command, “Space Systems Command Expands Space Vehicle Processing Capacity,” 7 Oct 2025 — "
    "ssc.spaceforce.mil/Newsroom/Article/4333969.",
 5: "Space Systems Command, “Space Force increases on-orbit warfighter capability support through expanded space vehicle "
    "processing” (All Points Logistics, $250M NSSL SV Processing CSO, Vandenberg capacity by 2029), 2026 — "
    "ssc.spaceforce.mil/Newsroom/Article/4558913.",
 6: "Military & Aerospace Electronics, “Space Force to outline its launch vision for the future at upcoming industry day,” "
    "29 Jun 2026 — militaryaerospace.com/home/article/55387166.",
 7: "Air & Space Forces Magazine, “Vandenberg Plans ‘Zone’ for New Launch Support Facilities,” 2026 — "
    "airandspaceforces.com/vandenberg-zone-new-launch-support-facilities-on-site-manufacturing.",
 8: "USASpending.gov, recipient Exos Aerospace Systems & Technologies, Inc. (UEI CK24BPZGF854), prime awards "
    "FA9300-25-C-6022, FA8649-21-P-0838, FA9300-24-P-6006, FA8649-20-P-0799 (retrieved 25 Sep 2026).",
 9: "Contract FA9300-26-C-6011, AFRL/RQ, effective 24 Sep 2026 (executed contract on file at Exos).",
 10: "Exos Aerospace, “Reusable Flight Test Infrastructure / Capabilities,” exosaero.com/capabilities (accessed Oct 2026).",
 11: "SAM.gov Entity Registration, Exos Aerospace Systems & Technologies, Inc., UEI CK24BPZGF854 / CAGE 7EMY6, "
     "status Active (All Awards), expiration 7 Oct 2027 (verified 11 Oct 2026).",
 12: "51 U.S.C. § 50101(7) (definition of “United States commercial provider”); 10 U.S.C. § 2667 (leases of non-excess property).",
 14: "Exos Aerospace, \u201cReusable Suborbital Flight Test Services,\u201d exosaero.com, accessed 12 Oct 2026.",
 15: "15 U.S.C. § 638(e)(4)(C) (SBIR “third phase” = work that “derives from, extends, or completes efforts made under prior funding "
     "agreements under the SBIR program”) and 15 U.S.C. § 638(r) (Phase III awards) — law.cornell.edu/uscode/text/15/638 (accessed 11 Oct 2026).",
 17: "Exos records: BLK3 reusable rocket design work performed under AFWERX SBIR Phase II FA8649-21-P-0838 (confirmed by Exos CEO, 11 Oct 2026).",
 16: "Exos SBIR Phase II award record, FA9300-25-C-6022, U.S. Space Force topic SF233-0019 (award documents on file at Exos).",
 13: "Exos Mission Control, Payloads-exo3 program record (program start 26 Jun 2026; seven-stage pipeline with human "
     "approval gate) and Exos payload and vehicle scheduling records — Exos internal system of record, available for "
     "Government review on request.",
 18: "Texas Secretary of State, Certificate of Fact (Status), Exos Aerospace Systems & Technologies, Inc., obtained via "
     "SOSDirect, October 2026 (Attachment 1).",
 19: "NOAA National Centers for Environmental Information, “Engineering Weather Data — KVBG (Vandenberg AFB / VSFB),” "
     "ICAO_KVBG_EWD_SI.pdf, 1988–2017 climatology — "
     "ncei.noaa.gov/pub/access/cebrequests/engineeringwx/ICAO_KVBG_EWD_SI.pdf (accessed Oct 2026). "
     "Prevailing surface wind directions at KVBG are west-northwest to west, consistent with onshore flow from the Pacific.",
 20: "Yakimenko, O.A., Dobrokhodov, S.N., and Kaminer, I.I., “On Estimation of Terminal Accuracy for Several Steerable "
     "Parafoil Systems,” AIAA Paper 2006-6793, AIAA Guidance, Navigation, and Control Conference, 2006 (older published data; "
     "accuracy varies by system and conditions; cited as a general reference for guided-parafoil CEP class).",
    21: "Fox News, \u201cTrump announces Montana \u2018super range\u2019 at midterm rally for Pentagon to test advanced war technology,\u201d 15 Oct 2026 \u2014 foxnews.com/politics/trump-announces-montana-super-range-midterm-rally-pentagon-test-advanced-war-technology.",
}

def D(text):
    return ("decision", text)

C = []
def add(*b): C.append(b)

VER = "_r12"
LAUNCH = ("targeted for Q2 2028, after BLK3 flight heritage (first flight planned early 2027 at Spaceport America) and subject to launch-site assignment, FAA licensing and range approvals")

# ------------------------------------------------------------------ COVER
add("title", "Whitepaper Response")
add("sub", "Vandenberg Space Force Base (VSFB) Call for Whitepapers for Mission Development Zone (MDZ) Outgrant")
add("sub", "Solicitation / Notice: VSFBMDZCall  \u00b7  SLD 30/XPR  \u00b7  Responses due 16 October 2026")
add("title2", "Exos Reusable-Vehicle Recovery & Turnaround Zone")
add("sub", "Option / reservation on MDZ parcels to establish a shared reusable-vehicle landing and turnaround zone "
           "on the Western Range, with MCMS-exo3 as the zone's coordination and scheduling system")
add("spacer",)
add("cover", "**Submitted by:** Exos Aerospace Systems & Technologies, Inc.")
add("cover", "299 FM 1903, Greenville, TX 75402")
add("cover", "CAGE 7EMY6  \u00b7  UEI CK24BPZGF854  \u00b7  SAM.gov Active (All Awards) through 7 Oct 2027")
add("cover", "NAICS 336414 (primary) \u00b7 541715 \u00b7 541330  \u00b7  Small Business")
add("cover", "**Point of contact:** John Quinn, Cofounder & Chief Executive Officer")
add("cover", "jquinn@exosaero.com  \u00b7  +1 (972) 740-8355  \u00b7  www.exosaero.com")
add("cover", "Submitted to: Ainsley Allen, SLD 30 — 232909MissionDevelopmentZoneMDZFacilityConstruct@groups.af.mil")
add("spacer",)
add("note", "Informational whitepaper submitted in response to a call that is not governed by the FAR and is not an RFI, RFP or "
            "RFQ (call \u00a72.1). Exos acknowledges that the USSF may use the information in this submission for MDZ scoping and "
            "planning (call \u00a72.1). Concepts herein are proposed and pre-decisional; nothing in this paper is an offer, a "
            "financing commitment or a rent proposal. Exos launch operations at VSFB are planned " + LAUNCH + "; Exos holds no VSFB "
            "launch site, launch license for VSFB, or VSFB manifest today.")
add("note", "**Attachments:** (1) Texas Secretary of State Certificate of Fact (Status); (2) Officer Certification of U.S. "
            "Ownership (51 U.S.C. \u00a7 50101(7)).")
add("note", "**Distribution:** " + DIST)
add("pb",)

# ------------------------------------------------------------------ EXEC SUMMARY
add("h1", "Executive Summary")
add("p", "Exos Aerospace's mission is **“Make Every Space Vehicle Reusable.”** Exos scopes this response to that mission. "
         "Exos asks SLD 30 to consider an **option / reservation (outgrant under 10 U.S.C. \u00a7 2667) on Hazardous 30-acre "
         "Plots 10 and 11** (Exhibit B) to establish the **Exos Reusable-Vehicle Recovery & Turnaround Zone** — a shared landing "
         "and recovery pad that any reusable vehicle or capsule on the Western Range can use, with operator consent. "
         "Exos is not requesting a launch complex; the MDZ is not a space launch complex [1]. The land request leads "
         "because this is a real-property call; the facilities ask is a modest, expeditionary footprint, not permanent construction.")
add("p", "**Why these parcels.** Plots 10 and 11 are along Beach Road, closest to the coast and outside the airfield "
         "approach-departure clearance surface and APZ 2 (Exhibit B Fig. 4) [1]. They provide the open landing field "
         "this concept requires. Alternates: Plot 1 (same hazardous strip), or Hazardous 50-acre Parcel 1 (flood-plain "
         "justification: an open landing field with no permanent structures is the only use proposed, making flooding "
         "a manageable risk rather than a disqualifier).")
add("p", "**Landing concept.** The reusable vehicle deploys its guided parafoil over the ocean, upwind of the coast. "
         "Vandenberg's prevailing surface winds are west-northwest to west (NOAA NCEI engineering weather data, KVBG, "
         "1988–2017 [19]), so the nominal glide path brings the vehicle across the coast and onto the recovery zone "
         "only when the canopy is nominal and the vehicle is safed (propellant vented, ordnance inert). Published "
         "guided-parafoil accuracy is approximately 100 m CEP (older published data, AIAA 2006-6793 [20]), which "
         "sets the size of the cleared dispersion area. Off-nominal descents land in the ocean with a flotation system "
         "and a standby recovery boat; no offshore catch structure is proposed.")
add("p", "**Live winds from Mission Control.** Before launch and before reentry/canopy deploy, Exos plans to fire "
         "rocket-launched radiosondes along the actual corridor to measure winds aloft in real time. These feed "
         "Mission Control's release-point computation and the go/no-go decision. Exos developed and tested this "
         "rocket-launched radiosonde and wrote the software that runs it; it is technology Exos has to augment local "
         "winds data. Over time the wind data shrinks the dispersion zone, and the radiosonde service "
         "can be offered to other Western Range users.")
add("p", "**Mission Control as the differentiator.** The zone's coordination system is MCMS-exo3 (Mission Control / "
         "exo3): scheduling across vehicles, crews, range and road calendars; signed chain of custody; range and FTS "
         "requirements in one process with human approval gates; the wind go/no-go; and a reusability ledger — "
         "turnaround status, inspection records, and reflight-readiness for every vehicle using the zone, with operator "
         "consent. Mission Control and the exo3 payload process are in use today on Exos operations [13]; their "
         "extensions to Vandenberg are proposed. **Phase 0 offer:** Exos will run a read-only Mission Control pilot "
         "for SLD 30 now, using Exos's Spaceport America operations as the live data source — no real property needed.")
add("p", "**Facilities.** Expeditionary and modular: a landing pad (~150 m\u00b2), containerized processing, a mobile "
         "Mission Control node, wind sensors, and perimeter — nothing permanent until a launch site is assigned.")
add("p", "**Future vision (funded-future / vision, not demonstrated).** Near term: BLK3 reusable suborbital, "
         "followed by BLK4 — a reusable replacement for Black Brant-class sounding rockets. Orbital: BLK4 Heavy "
         "(three BLK4 cores in parallel) is Exos's planned path to orbital launch, capital-dependent. Vandenberg is "
         "where that orbital future would fly, with reusable-stage recovery by propulsive landing on an offshore "
         "barge and/or return to this recovery zone. BLK3 has not flown; its first flight is planned early 2027 at "
         "Spaceport America.")

# ------------------------------------------------------------------ 1.0
add("h1", "1.0 CORPORATE ADMINISTRATION")
add("h2", "1.1 Company legal name")
add("p", "Exos Aerospace Systems & Technologies, Inc. (dba Exos Aerospace) — CAGE 7EMY6, UEI CK24BPZGF854 [11].")
add("h2", "1.2 Company legal form of ownership")
add("p", "Texas corporation, founded and incorporated in 2015; EIN 47-3491152. Exos is organized under the laws of the State of "
         "Texas and is registered and active in SAM.gov (All Awards) through 7 October 2027 [11]. Exos is a Small Business under "
         "its primary NAICS 336414 and claims no other socio-economic designation.")
add("p", "**Eligibility as a United States commercial provider (51 U.S.C. \u00a7 50101(7)) [12].** Exos is a United States "
         "commercial provider as defined in 51 U.S.C. \u00a7 50101(7): a commercial provider organized under the laws of a State "
         "(Texas) that is more than 50 percent owned by United States nationals. Evidence of organization under Texas law: Texas Secretary of State "
         "Certificate of Fact (Status) (Attachment 1) [18]. Evidence of U.S. ownership: Officer Certification of "
         "U.S. Ownership signed by the Chief Executive Officer (Attachment 2).")
add("h2", "1.3 Company legal place of business (address)")
add("p", "299 FM 1903, Greenville, TX 75402 (headquarters: engineering, final assembly, ground test).")
add("h2", "1.4 Business address of company operating locations other than headquarters")
add("bl", ["**Spaceport America, New Mexico** — current launch and recovery operations site for Exos reusable suborbital flights [10]. "
           "Exos operations are not limited to Spaceport America; Exos evaluates additional launch and operating sites as its "
           "manifest grows.",
           "**Vandenberg SFB:** none today. The MDZ outgrant option / reservation would establish the Exos Reusable-Vehicle Recovery & Turnaround Zone for planned Exos "
           "operations " + LAUNCH + ". Exos holds no VSFB launch site, launch license for VSFB, or VSFB manifest today."])
add("h2", "1.5 Primary & alternate points of contact")
add("table", [["Role", "Name / title", "Phone", "E-mail"],
              ["Primary", "John Quinn, Cofounder & Chief Executive Officer", "+1 (972) 740-8355", "jquinn@exosaero.com"],
              ["Alternate", "Lizi (Elizabeth) Quinn, Business Development", "—", "lquinn@exosaero.com"]],
        [1.0, 2.6, 1.3, 1.6])
add("h2", "1.6 Company history and relevant past performance")
add("p", "Exos was founded in 2015 to build reusable suborbital launch vehicles. Its team carries over 25 years of experience in the "
         "rocket and space industry, with deep Armadillo Aerospace and Exos heritage: hundreds of rocket engines and dozens of flying "
         "vehicles built. Exos is a reusable suborbital launch operator, holding an FAA Part 431 launch license that is transitioning to Part 450, providing flight-test services for space, "
         "defense, research and commercial payloads [10], with payload recovery for post-flight inspection, analysis "
         "and iteration [14]. Its next vehicle, BLK3, is preparing for first flight in early 2027, under the Part 450 transition.")
add("p", "**Relevance to the MDZ.** Exos runs the full launch-support lifecycle as an operator — vehicle and payload receiving, "
         "integration, launch operations, recovery and reflight — with a small ground footprint. Exos manages the payload side of "
         "that lifecycle today on exo3, an AI-managed payload process in Exos Mission Control with a seven-stage pipeline and a human "
         "approval-and-signature gate before any commitment [13].")
add("p", "**Verified Federal past performance [8][9]** (Department of the Air Force):")
add("table", [["Contract", "Value", "Start", "Scope (as titled)"],
              ["FA9300-25-C-6022", "$1,897,824", "Sep 2025", "SBIR Phase II — Suborbital Hover Vehicle–Reusable Rocket (flight vehicle and flight demonstration; in performance)"],
              ["FA8649-21-P-0838", "$750,000", "Mar 2021", "AFWERX SBIR Phase II — Prototype mobile low-cost reusable launch vehicle"],
              ["FA9300-24-P-6006", "$189,406", "Apr 2024", "SBIR Phase I — Evaluation & design of reusable hover vehicle test bed"],
              ["FA8649-20-P-0799", "$50,000", "Mar 2020", "AFWERX SBIR Phase I — Reusable launch vehicle"],
              ["FA9300-26-C-6011", "$293,063 (FFP)", "Sep 2026", "AFRL/RQ — Free-flight test program (newly executed)"]],
        [1.35, 1.05, 0.8, 3.3])
add("p", "**Leadership.** John Quinn, Cofounder & CEO (11 years building Exos; 14.5-year U.S. Navy Submarine Service veteran); "
         "Russel Blink, Cofounder & CTO (propulsion and vehicle engineering); Neil Milburn, Cofounder & COO (Armadillo Aerospace "
         "veteran; FAA liaison and program execution); David Mitchell, Cofounder & President (financing and investor relations); "
         "Kyle Ballard, CFO (financial reporting, controls and diligence).")

# ------------------------------------------------------------------ 2.0
add("h1", "2.0 PROPOSED OPERATIONS & FACILITIES")
add("h2", "2.1 Concept of operations")
add("p", "**Primary use: Exos Reusable-Vehicle Recovery & Turnaround Zone.** The leased MDZ parcels would serve as a shared "
         "landing and recovery zone for reusable vehicles and capsules on the Western Range — open to any operator with "
         "SLD 30 approval and operator consent. The zone supports Exos's mission: Make Every Space Vehicle Reusable. "
         "The launch pad itself is outside the MDZ and would be assigned separately; the MDZ site supports recovery, "
         "turnaround, and operations.")
add("p", "**Recovery landing concept.** The reusable vehicle deploys its guided parafoil over the Pacific Ocean, upwind "
         "of the coast. Vandenberg's prevailing surface winds are west-northwest to west (NOAA NCEI KVBG, 1988–2017 [19]). "
         "The vehicle crosses the coastline only when the canopy is nominal and the vehicle is safed (propellant vented, "
         "pyrotechnics inert). It glides overland to a ~150 m\u00b2 aim point inside the cleared dispersion area on the "
         "recovery zone. Published guided-parafoil accuracy is approximately 100 m CEP (older published data, AIAA "
         "2006-6793 [20]), which drives the size of the dispersion buffer. An off-nominal descent lands in the ocean; "
         "the vehicle carries a flotation system and a standby recovery boat is stationed offshore. No offshore catch "
         "structure is proposed.")
add("p", "**Wind go/no-go and live radiosonde measurements.** Exos plans to fire rocket-launched radiosondes along the "
         "actual flight corridor before launch and before the reentry/canopy-deploy decision to measure winds aloft in "
         "real time. The radiosonde data feeds Mission Control's release-point computation and the go/no-go decision "
         "for canopy deployment. Exos developed and tested this rocket-launched radiosonde and wrote the software that "
         "runs it; it is technology Exos has to augment local winds data. Radiosonde solid motors are "
         "ordnance: they fly from the assigned launch site or a hazardous parcel with an explosives site plan and range "
         "approval — not from the inert recovery zone. Over time, accumulated wind data shrinks the required dispersion "
         "zone; the radiosonde service can be offered to other Western Range users.")
add("p", "**MCMS-exo3 as the zone's coordination system.** Mission Control schedules operations across vehicles, "
         "crews, range and road calendars; carries signed chain of custody at every handoff; integrates range and FTS "
         "requirements in one process with human approval gates; hosts the wind go/no-go workflow; and maintains a "
         "reusability ledger — turnaround status, inspection records, and reflight-readiness for every vehicle using "
         "the zone, with operator consent. Mission Control and the exo3 payload process are in use today on Exos "
         "operations [13]. Their extensions to Vandenberg and to a multi-vehicle zone are proposed.")
add("p", "**Finance, design, construct, operate and maintain approach (call \u00a71.2).** Exos would hold the outgrant and "
         "operate and maintain the zone with a deliberately light footprint: the landing pad and dispersion area, wind "
         "sensors, a mobile Mission Control node and transportable turnaround shelters. Exos does not propose to build "
         "or finance cleanrooms, payload-processing bays or other capital-intensive facilities; that is not where Exos "
         "adds value. Exos's contribution is Mission Control facilities integration and management: scheduling, custody, "
         "range and safety coordination, and the reusability ledger across whatever facilities SLD 30 and other "
         "tenants build or already operate.")
add("table", [["Function (call \u00a71.3 wording)", "Exos activity at the Recovery & Turnaround Zone"],
              ["Spacecraft integration / payload processing", "Receive and inspect recovered vehicles and payloads post-landing; turnaround and reflight preparation"],
              ["Preparation and support of launch programs (\u00a73.1)", "Mission operations for recovery campaigns; coordination with Western Range for landing windows"],
              ["Spaceport logistics / commodity storage", "GSE staging and storage; transporter access for vehicle moves to/from the assigned launch site"],
              ["Launch and mission control", "Mission Control node for recovery, scheduling and go/no-go decisions (coordinated with SLD 30)"],
              ["Administrative / engineering spaces", "Exos operations and engineering support; no large administrative footprint planned initially"]],
        [2.4, 4.1])
add("h2", "2.2 Desired facility developments at the MDZ")
add("table", [["ID", "Facility", "Description", "Phase"],
              ["F0", "MCMS-exo3 — Mission Control digital system of record", "Software in use on Exos operations (payload and vehicle scheduling); no MDZ construction needed; Phase 0 read-only pilot offered to SLD 30 now", "0"],
              ["F1", "Recovery pad and dispersion area", "~150 m\u00b2 hardened aim point; cleared dispersion buffer; perimeter markings; no permanent structures within the dispersion area", "1 (expeditionary)"],
              ["F2", "Transportable turnaround shelter", "Rented/containerized shelter for post-landing inspection and turnaround; no permanent structure", "1 (expeditionary)"],
              ["F3", "Mobile Mission Control node", "Containerized mission operations capability for recovery campaigns and go/no-go decisions", "1 (expeditionary)"],
              ["F4", "Site works", "Wind sensors; transporter apron and access from Beach Rd; perimeter fence; access control; utility connections", "1 (expeditionary)"]],
        [0.4, 1.7, 3.5, 0.6])
add("p", "**Expeditionary first.** All Phase 1 facilities are modular and containerized. Permanent construction is gated "
         "on launch-site assignment. The recovery zone's open character — no permanent structures within the dispersion "
         "area — is a feature, not a limitation. It keeps the zone available for any reusable vehicle.")
add("p", "**Compatibility of the property (call \u00a73.1).** Hazardous 30-acre Plots 10 and 11 are along Beach Road, "
         "near the coast, outside the airfield approach-departure clearance surface and APZ 2 (Exhibit B Fig. 4) [1]. "
         "They are road-served and clear of the flood plain. The alternate, Hazardous 50-acre Parcel 1, is in the "
         "flood plain; Exos's justification: the proposed use is an open landing field with no permanent structures, "
         "making flooding a manageable operational risk rather than a siting conflict.")

# ------------------------------------------------------------------ 4.0
add("h1", "4.0 BENEFIT TO THE SPACEPORT ECOSYSTEM")
add("h2", "4.1 Benefit to VSFB, the commercial space industry and USSF national security objectives")
add("bl", [
 "**Shared reusable-vehicle infrastructure on the Western Range.** A dedicated recovery zone available to any "
 "reusable vehicle or capsule — not just Exos — advances the Western Range's position for the next generation of "
 "reusable launch. Any operator that can land a vehicle within the dispersion envelope can use the zone, with SLD 30 "
 "approval and operator consent.",
 "**Mission Control coordination across operators.** MCMS-exo3 gives SLD 30 a single scheduling and chain-of-custody "
 "system for the zone: who is landing, when, in what configuration, with what hazard profile. Range and FTS "
 "requirements are integrated into one process with human approval gates. This is the kind of operational visibility "
 "GAO found the Space Force currently lacks [3].",
 "**Wind data service for the Western Range.** Rocket-launched radiosondes along the recovery corridor generate "
 "winds-aloft data before each event. Over time this data can be offered to other range users — launch operators, "
 "range safety — as a weather service. Exos developed and tested the radiosonde and its software.",
 "**Reusability ledger.** A per-vehicle record of turnaround, inspection, anomaly, and reflight-readiness — with "
 "chain of custody and operator consent — is the accountability infrastructure reusable launch needs on a "
 "Government range.",
 "**Industrial base and MTP alignment.** A U.S. small-business operator advancing reusable launch diversifies the "
 "Western Range supplier base; the zone's shared nature multiplies that value.",
 "**Phase 0 pilot now.** Exos offers SLD 30 a read-only Mission Control view of Exos's Spaceport America "
 "operations today — no real property required — so SLD 30 can evaluate the system before any lease is executed."])

# ------------------------------------------------------------------ 5.0
add("h1", "5.0 PARCEL SELECTION, UTILITY, & PERSONNEL REQUIREMENTS")
add("h2", "5.1 Acreage required and preferred conceptual footprints (MDZ Parcel Map, Exhibit B)")
add("img", "drafts/VSFB_MDZ/Exos_MDZ_Parcel_Selection_Map_r4.png", "Parcel map. Exos parcel selection on the MDZ Parcel Map (Exhibit B, Fig. 2): preferred Hazardous 30-acre Plots 10 and 11 (green); alternates Plot 1 and Hazardous 50-acre Parcel 1 (amber). Annotation by Exos.")
add("p", "Siting logic for the Recovery & Turnaround Zone: (1) open field for landing and dispersion — no tall structures "
         "inside the dispersion area; (2) close to the coast to minimize overland flight distance after canopy deploy; "
         "(3) road access (Beach Rd) for vehicle transport and GSE; (4) outside the airfield approach-departure clearance "
         "surface and APZ 2 (Exhibit B Fig. 4) [1]; (5) hazardous parcel designation is appropriate — the vehicle lands "
         "safed and inert, but the reentry/landing hazard area requires hazardous-area coordination with SLD 30 range safety.")
add("table", [["Priority", "Area (Exhibit B)", "Parcel(s)", "Use / justification"],
              ["Preferred", "Hazardous 30-acre, Beach Rd / westernmost", "Plots 10 & 11 (contiguous)", "Primary recovery zone: coastal, road-served, outside airfield approach surfaces and APZ 2"],
              ["Alternate A", "Hazardous 30-acre, same strip", "Plot 1", "Same strip; alternate if Plots 10–11 unavailable"],
              ["Alternate B", "Hazardous 50-acre Parcel 1 (flood plain)", "Hazardous 50-acre Parcel 1", "Open landing field; no permanent structures — flood plain is a manageable operational risk for this use; justification provided per Exhibit B note"]],
        [1.1, 2.4, 1.7, 1.3])
add("p", "**Reservation / option requested, not immediate build obligation.** Exos requests an option or reservation on "
         "the preferred parcels (Plots 10 and 11) while Exos pursues launch-site assignment and FAA licensing. "
         "The ask is: hold these parcels for the Exos Reusable-Vehicle Recovery & Turnaround Zone. Exos will exercise "
         "the outgrant " + LAUNCH + ". No rent proposal is included, as none is "
         "requested by the call.")
add("p", "**Zone name and shared access.** The zone is named the **Exos Reusable-Vehicle Recovery & Turnaround Zone** "
         "and is offered as shared infrastructure for any reusable vehicle or capsule on the Western Range, with SLD 30 "
         "approval and operator consent. This is consistent with the call's intent to create infrastructure that serves "
         "the broader spaceport ecosystem.")
add("h2", "5.2 Estimated peak and average daily on-site personnel (steady state)")
add("table", [["Category", "Average daily", "Peak (recovery campaign)", "Shifts"],
              ["Exos operations, technicians, logistics, security", "Minimal standing crew; zone is not continuously staffed between campaigns", "Exos recovery crew deployed for landing window", "Campaign-driven; extended during recovery windows"],
              ["Other operators / payload teams", "Per scheduled recovery event", "Per event, coordinated in Mission Control", "Per event"],
              ["Visitors / Government", "Occasional", "Recovery-campaign reviews and range safety coordination", "Day shift"]],
        [2.3, 1.2, 1.6, 1.4])
add("p", "Exos VSFB staffing scales to recovery-campaign cadence once a launch site is assigned; numeric counts will "
         "be provided with final design and utility coordination.")
add("h2", "5.3 Estimated daily and peak requirements for power, water, road/traffic access and communications")
add("table", [["Utility", "Phase 1 requirement", "Notes"],
              ["Power", "Light service to support mobile Mission Control node, wind sensors, perimeter lighting and vehicle checkout; load set in utility coordination", "Backup power for Mission Control and environmental sensors"],
              ["Water / sewer", "Minimal domestic demand; set in utility coordination", "No process wastewater; domestic use for small crew during campaigns"],
              ["Road / traffic", "Heavy-haul access from Beach Rd; transporter apron for vehicle moves", "Vehicle moves to/from the assigned launch site scheduled with SLD 30"],
              ["Communications", "Commercial fiber or satellite link; range/mission-ops connections as authorized by SLD 30", "Range links and Mission Control data connections per SLD 30 requirements"]],
        [1.2, 2.4, 2.9])

# ------------------------------------------------------------------ 6.0
add("h1", "6.0 IMPACTS AND SAFETY CONSIDERATIONS")
add("h2", "6.1 Operational CONOPS (material logistics and security boundaries)")
add("bl", [
 "**Inbound (recovery operations):** no vehicle hardware arrives at the zone by road before a recovery event. "
 "The vehicle descends onto the zone under its guided parafoil. GSE, personnel and the mobile Mission Control "
 "node are pre-staged on the parcels before the landing window.",
 "**On site:** post-landing, the vehicle is inspected, safed (confirmed), and secured. A scanned, signed custody "
 "event records receipt by Exos. The vehicle is then moved by transporter to the assigned launch site or a "
 "processing facility for turnaround.",
 "**To and from the launch site:** vehicle moves to and from the separately assigned launch site under SLD 30 "
 "transport procedures.",
 "**Security boundaries:** perimeter fence with one controlled entry; the zone is secured during recovery windows "
 "and between events. Export-controlled hardware and data handled under ITAR/EAR procedures with decisions by "
 "Exos's Empowered Official. No classified processing."])
add("h2", "6.2 Anticipated quantities and types of propellants, commodities, or hazardous chemicals")
add("p", "**No propellants or ordnance are stored or handled on the recovery zone parcels.** The vehicle lands "
         "safed and inert: propellant tanks vented, pyrotechnics expended or inerted before canopy deployment. "
         "The zone would hold only ordinary field commodities: compressed inert gases (nitrogen, helium) for "
         "post-recovery procedures, lithium-ion batteries in payloads, and diesel for backup power — all in "
         "small, fire-code-compliant quantities. Radiosonde solid motors are ordnance and are handled only at "
         "the assigned launch site or a separately designated hazardous parcel with an explosives site plan and "
         "range approval; they are never handled at the recovery zone.")
add("h2", "6.3 Anticipated explosive safety arcs and hazard areas (siting requirements)")
add("p", "**Reentry/landing hazard area.** The recovery zone has a reentry and landing hazard area (the dispersion "
         "footprint for the guided-parafoil descent) that will be coordinated with SLD 30 range safety and FAA "
         "under Part 450 (or equivalent). This is not a quantity-distance (QD) arc — it is a flight-safety "
         "exclusion area for the landing window, cleared and then released. The vehicle lands safed and inert; "
         "there is no explosive safety arc from ordnance or propellant at the recovery zone itself.")
add("p", "**Off-nominal contingency.** An off-nominal descent (failed canopy) lands in the ocean; the vehicle "
         "carries a flotation system and a standby recovery boat is pre-positioned. Range safety procedures for "
         "the off-nominal case will be coordinated with SLD 30 and documented in the flight safety analysis under "
         "FAA Part 450.")
add("p", "**No QD arcs or hazardous-material siting** are anticipated at the recovery zone. The hazardous parcel "
         "designation is appropriate for range-safety coordination of the landing hazard area. A future explosion-hazard "
         "use at these parcels is not part of this request and would require a separate explosives site plan under "
         "DoD explosives safety standards (DESR 6055.09 / DAFMAN 91-201).")
add("h2", "6.4 Mitigation alternatives for impacts on neighboring operations and transportation routes")
add("bl", [
 "Landing windows are discrete, pre-coordinated events; Mission Control flags conflicts with range and road "
 "calendars before a window is approved.",
 "The dispersion area is cleared of personnel during the landing window and released immediately after landing "
 "and vehicle safeing confirmation.",
 "Off-nominal ocean landing contingency keeps risk away from the base during any vehicle anomaly.",
 "No engine testing or launch activity at the recovery zone; backup generator exercised on a set schedule.",
 "Stormwater, lighting and habitat measures as required by the base environmental review; Exos would support "
 "NEPA with site data."])
add("h2", "6.5 New construction or modifications required to existing VSFB infrastructure")
add("bl", [
 "Utility extensions (power, fiber, minimal water/sewer) to the selected parcels; light-service loads only.",
 "Transporter apron and turning-radius improvements at Beach Rd for vehicle moves; no new public roads.",
 "Connection to base security and entry control as directed by SLD 30.",
 "No modifications to the airfield. Launch-site infrastructure is outside this MDZ request and depends on "
 "separate launch-site assignment."])

# ------------------------------------------------------------------ 7.0
add("h1", "7.0 CONCEPTUAL PROJECT TIMELINE")
add("h2", "7.1 Notional schedule from initial site access to operational capability")
add("p", "**Exos requests a reservation / option on the preferred parcels now.** Build-out of Phase 1 expeditionary "
         "facilities is planned " + LAUNCH + ". Durations are notional and "
         "measured from outgrant execution (M0). No hard operations date is proposed at this stage.")
add("table", [["Phase / milestone", "Activity", "Notional timing"],
              ["Phase 0 (now)", "Read-only Mission Control pilot for SLD 30 using Exos Spaceport America operations; no real property needed", "From submission, on SLD 30 interest"],
              ["In parallel", "BLK3 first flight at Spaceport America; accumulate flight heritage; launch-site assignment request; FAA license modification and range approvals for VSFB (outside the MDZ)", "Starting on submission"],
              ["Reservation", "Option / reservation on Plots 10 & 11 (or alternate) executed by SLD 30", "As agreed with SLD 30"],
              ["M0", "Outgrant executed; initial site access", "After BLK3 flight heritage and launch-site assignment"],
              ["Site / expeditionary", "Site preparation; wind sensors; pad marking; containerized processing and Mission Control node deployed", "From M0; rapid standup — modular equipment"],
              ["Phase 1 activation", "Recovery zone operational for Exos recovery campaigns", "Target Q2 2028, subject to approvals"],
              ["Phase 2 gate", "Mission Control integration and management extended to additional operators and to facilities built by SLD 30 or others; no Exos-funded permanent construction; gated on demand and SLD 30 concurrence", "After Phase 1 track record"]],
        [1.4, 3.6, 1.5])

add("h2", "7.2 Requested award approach")
add("p", "The primary instrument Exos requests is the **MDZ outgrant (option / reservation)** under 10 U.S.C. \u00a7 2667 "
         "on its normal real-property path [12].")
add("p", "For Mission Control range-integration work, Exos asks SLD 30 to refer Exos to the appropriate Space Force / "
         "SSC contracting path; Exos does not specify the instrument.")

# ------------------------------------------------------------------ 8.0
add("h1", "8.0 ADDITIONAL ENHANCEMENTS")
add("h2", "8.1 Enhancements offered for Government consideration")
add("bl", [
 "**MCMS-exo3 zone coordination system.** Scheduling across vehicles, crews, range and road calendars; signed "
 "chain of custody; range and FTS requirements in one process with human approval gates; wind go/no-go workflow; "
 "reusability ledger for every vehicle using the zone, with operator consent. Built on Mission Control and the "
 "exo3 process in use today [13]. Extensions are proposed.",
 "**Phase 0 read-only Mission Control pilot for SLD 30.** Exos will configure a read-only view of Exos's "
 "Spaceport America operations for SLD 30 stakeholders — no real property required — to demonstrate the "
 "system before any lease is executed.",
 "**Winds-aloft data service.** Rocket-launched radiosonde data from recovery corridor flights, "
 "offered to other range users over time. Built on the radiosonde and software Exos developed and tested.",
 "**Shared zone access.** Any reusable vehicle or capsule on the Western Range can use the recovery zone, "
 "with SLD 30 approval and operator consent — multiplying the value of the infrastructure.",
 "**Government-dedicated coordination view.** Customer-consented, read-only SLD 30 access to zone scheduling "
 "and vehicle readiness status in Mission Control [3]."])

add("h2", "8.2 Optional opportunity: Exos Mission Control implementation for zone and payload management services")
add("p", "Separately from the outgrant, Exos offers USSF/SLD 30 the option to have Exos implement and operate **Exos Mission "
         "Control** — the Exos-built operations software Exos uses today to schedule its own payloads and vehicles and to run "
         "its seven-stage exo3 payload process with a human approval gate [13] — as a **zone and payload management service** "
         "for the MDZ. The option is not a condition of the lease and would be scoped and priced separately under an instrument "
         "the Government chooses.")
add("table", [["Service area", "What Exos Mission Control would provide"],
              ["Zone management", "Parcel and facility calendars; landing-window scheduling across operators; access and escort scheduling; work orders and maintenance tracking"],
              ["Vehicle and payload management", "Recovery records, turnaround status, inspection logs, and reflight-readiness per vehicle; signed chain of custody at each handoff"],
              ["Range and road scheduling", "Vehicle moves, transporter windows, and recovery milestones checked against range and base calendars before approval"],
              ["Wind go/no-go workflow", "Pre-recovery radiosonde data and Mission Control release-point computation; go/no-go decision record with human approval gate (planned capability)"],
              ["Government visibility", "Customer-consented, read-only view for SLD 30 of zone schedules and vehicle readiness [3]"],
              ["Controls", "Human approval gates on every commitment; export-control indicators routed to Exos's Empowered Official, never auto-cleared"]],
        [1.7, 4.8])
add("p", "**Implementation path.** (1) Phase 0 demonstration to SLD 30 on Exos's own operations, now; (2) "
         "configuration for the Exos recovery zone at Phase 1 activation; (3) optional extension to SLD 30 and "
         "other MDZ tenants. Mission Control and the exo3 process are in use today on Exos operations; they have "
         "not been deployed at Vandenberg or on Government networks. Hosting, data rights, cybersecurity authorization "
         "and any Government-network interface would be defined with SLD 30 before use.")
add("p", "**Origin: a range-coordination concept.** Exos developed Mission Control's range-coordination concept alongside its Montana Spaceport & Test Range work (program operating agreement, May 2026; development-stage, not a licensed site) to coordinate many users, vehicles and test events on one range under human approval gates. The same need applies to multi-user test ranges such as the Montana \u201csuper range\u201d for advanced weapons and technology testing that the President announced on 14 Oct 2026 [21], as well as to the Western Range. Exos has no role in that range today.")
add("p", "**Exos Mission Control today.** Figures 1–4 show Exos Mission Control tracking Exos rocket missions today: mission and flight-readiness gates, payload operations, logistics (ERP/MRP), and financial integration (screens captured 15 Oct 2026, 18:24 CDT; counts are live at capture time; customers anonymized). They illustrate the service offered above; none of it is deployed at Vandenberg.")
add("img", "drafts/mc_theme_concepts/whitepaper_ops/Exos_MissionControl_Fig1_Mission_Ops_Board.png")
add("img", "drafts/mc_theme_concepts/whitepaper_ops/Exos_MissionControl_Fig2_Payload_Operations.png")
add("img", "drafts/mc_theme_concepts/whitepaper_ops/Exos_MissionControl_Fig3_Logistics_ERP_MRP_Inventory.png")
add("img", "drafts/mc_theme_concepts/whitepaper_ops/Exos_MissionControl_Fig4_Financial_Systems_Integration.png")

# ------------------------------------------------------------------ 9.0
add("h1", "9.0 FUTURE VISION (Funded-Future / Vision — Not Demonstrated)")
add("p", "This section describes Exos's planned trajectory — capital-dependent and not yet demonstrated. "
         "Nothing in this section represents a current Exos capability or a commitment.")
add("h2", "9.1 Near-term: reusable sounding-rocket replacement (BLK4)")
add("p", "BLK3 is Exos's next vehicle, preparing for first flight in early 2027 at Spaceport "
         "America. Following BLK3, Exos is developing BLK4 as a reusable suborbital vehicle in the Black Brant "
         "class — a reusable replacement for expendable sounding rockets used for science, defense research, and "
         "atmospheric measurements. BLK4 at Vandenberg would use the Recovery & Turnaround Zone to support a "
         "rapid-turnaround, reusable sounding-rocket cadence on the Western Range. BLK4 is a planned program; "
         "it has not flown.")
add("h2", "9.2 Orbital future: BLK4 Heavy (capital-dependent vision)")
add("p", "Exos's planned path to orbital launch is BLK4 Heavy — three BLK4 cores in parallel — a configuration "
         "that is capital-dependent and not yet funded or under development. Vandenberg SFB is where Exos envisions "
         "that orbital future flying: a polar or sun-synchronous orbit capability on the Western Range. "
         "Recovery of reusable stages would be by propulsive landing on an offshore barge and/or return to "
         "the Recovery & Turnaround Zone. The recovery zone requested in this whitepaper is designed to support "
         "this long-term vision as well as the near-term guided-parafoil recovery concept.")
add("p", "Exos does not have an orbital vehicle. Exos has not flown BLK3. BLK4 Heavy is a funded-future concept. "
         "These items are presented to give SLD 30 context for why Vandenberg — and this specific coastal recovery "
         "zone — is the right long-term site for Exos's reusable launch program.")

# ------------------------------------------------------------------ STATUS
add("h1", "Statement of Status (demonstrated vs. proposed / planned)")
add("table", [["Item", "Status"],
              ["Exos launch operations at VSFB", "Planned — " + LAUNCH + "; no VSFB launch site, license or manifest today"],
              ["Exos launch operations today", "Reusable suborbital operator from Spaceport America, NM; FAA Part 431 launch license, transitioning to Part 450 [10]"],
              ["BLK3", "Next vehicle; preparing for first flight, early 2027 at Spaceport America, under the Part 450 transition; has not flown"],
              ["exo3 payload process (7 stages, human gate)", "In use today for Exos payload operations; not deployed at Vandenberg [13]"],
              ["Exos Mission Control (payload and vehicle scheduling)", "In use today on Exos operations; offered as optional zone and payload management service (8.2); not deployed at Vandenberg [13]"],
              ["MCMS-exo3 extensions and zone coordination features", "Proposed / in development"],
              ["MCMS-exo3 range / FTS process integration", "Proposed, for contract with SLD 30; process work only, not FTS hardware"],
              ["Recovery zone facilities F1–F4", "Proposed expeditionary concept; no design, financing or Government commitment"],
              ["Rocket-launched radiosonde wind measurement at VSFB", "Developed and tested by Exos (radiosonde + run software); augments local winds data; not yet operated at Vandenberg"],
              ["BLK4 reusable suborbital (Black Brant-class replacement)", "Planned program; not yet in development; has not flown"],
              ["BLK4 Heavy orbital configuration (three BLK4 cores)", "Funded-future vision; capital-dependent; not under development; no orbital vehicle exists"],
              ["Certifications", "Small Business. NIST SP 800-171 implemented; CMMC 2.0 self-assessment complete (via Atomus). AS9100 in implementation; no facility clearance"]],
        [2.6, 3.9])

# ---- Compliance matrix (page refs filled from the built PDF by build_vsfb_mdz_all.py)
import json as _json, os as _os
_PM = {}
_pmf = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "drafts", "VSFB_MDZ", "_pagemap.json")
if _os.path.exists(_pmf): _PM = _json.load(open(_pmf))
MATRIX = [
 ("Exh. A 1.1", "Company legal name", "1.1"),
 ("Exh. A 1.2", "Legal form of ownership + evidence of U.S. organization", "1.2"),
 ("Call \u00a71.2 / 51 U.S.C. \u00a7 50101(7)", "Respondent is a United States commercial provider", "1.2"),
 ("Exh. A 1.3", "Legal place of business", "1.3"),
 ("Exh. A 1.4", "Other operating locations", "1.4"),
 ("Exh. A 1.5", "Primary & alternate POCs", "1.5"),
 ("Exh. A 1.6", "Company history / relevant past performance", "1.6"),
 ("Exh. A 2.1 / Call \u00a73.1", "Concept of operations; property compatibility", "2.1"),
 ("Call \u00a71.3 / \u00a71.4", "Use matches MDZ intended uses; MDZ not a launch complex", "2.1"),
 ("Call \u00a71.2", "Approach to finance, design, construct, operate, maintain", "2.1"),
 ("Exh. A 2.2 / Call \u00a73.1", "List and description of desired facility developments (expeditionary/modular)", "2.2"),
 ("Exh. A 4.1 / Call \u00a73.3", "Benefit to VSFB spaceport ecosystem, industry, USSF", "4.1"),
 ("Exh. A 5.1 / Call \u00a73.4", "Parcels: Plots 10 & 11 (Hazardous 30-acre, Beach Rd); alternates: Plot 1, Hazardous 50-acre Parcel 1", "5.1"),
 ("Exh. B note", "Justification for Hazardous 50-acre Parcel 1 (alt): open landing field, no permanent structures", "5.1"),
 ("Exh. A 5.2 / Call \u00a73.4", "Peak and average daily personnel", "5.2"),
 ("Exh. A 5.3 / Call \u00a73.4", "Power, water, road/traffic, communications", "5.3"),
 ("Exh. A 6.1 / Call \u00a73.5", "Operational CONOPS, logistics, security boundaries", "6.1"),
 ("Exh. A 6.2 / Call \u00a73.5", "Hazardous materials: none at recovery zone; vehicle lands safed/inert", "6.2"),
 ("Exh. A 6.3 / Call \u00a72.4, \u00a73.5", "Hazard area: reentry/landing dispersion footprint; no QD arcs; coordinated with SLD 30 and FAA Part 450", "6.3"),
 ("Exh. A 6.4 / Call \u00a73.5", "Mitigation of impacts on neighbors and routes", "6.4"),
 ("Exh. A 6.5 / Call \u00a73.5", "New construction / modifications to VSFB infrastructure (light-service utilities only)", "6.5"),
 ("Exh. A 7.1 / Call \u00a73.6", "Schedule: reservation now; build-out after BLK3 flight heritage and launch-site assignment; target Q2 2028", "7.1"),
 ("Exos addition", "Award approach: MDZ outgrant option/reservation; referral to SSC contracting path for MC range-integration work", "7.2"),
 ("Exh. A 8.1", "Enhancements: Phase 0 MC pilot; winds-aloft service; shared zone access; reusability ledger", "8.1"),
 ("Exos addition (optional)", "Exos Mission Control for zone and payload management services", "8.2"),
 ("Exos addition", "Future vision: BLK4 sounding-rocket replacement; BLK4 Heavy orbital (funded-future/vision, not demonstrated)", "9.0"),
 ("Exh. A 1.2 evidence", "Texas SOS Certificate of Fact (Status); Officer Certification of U.S. Ownership", "Attachments 1–2"),
 ("Call \u00a74.2", "Maximum 30 pages", "Whole document"),
 ("Call \u00a74.3", "MS Word or PDF; DoD SAFE delivery; separate receipt confirmation", "Submission checklist"),
]
add("h1", "Appendix A — Compliance Matrix")
add("p", "Maps every request in the call (Section 3 and Exhibit A) to this response. Page references are to the PDF version.")
add("table", [["Call reference", "Requirement", "Response section", "PDF page"]] +
    [[a, b, c, str(_PM.get(c, "—"))] for a, b, c in MATRIX], [1.6, 2.9, 1.2, 0.8])
add("h1", "Sources")
for k in sorted(SRC):
    add("src", "[%d] %s" % (k, SRC[k]))
