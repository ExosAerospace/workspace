# -*- coding: utf-8 -*-
"""Shared content model for the Exos VSFB MDZ whitepaper (VSFBMDZCall).
Rendered by build_vsfb_mdz_docx.py (Word, letterhead) and build_vsfb_mdz_pdf.py (reportlab twin).
Markup: **bold**. Block types: title, sub, cover, h1, h2, p, b, decision, table, note, pb.
Outline mirrors Exhibit A ("White Paper Request Summary") of the call VERBATIM.
"""

DATE = "2026-10-14"
MARK = "Exos Proprietary — not for public release"
DIST = ("Exos Proprietary — Submitted for U.S. Government planning use under VSFBMDZCall §2.1; not for public release.")

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
 14: "Exos Aerospace, “Reusable Suborbital Flight Test Services” (EXOS at a Glance: FAA-licensed reusable suborbital launch operator; payload recovery for post-flight inspection), "
     "exosaero.com, accessed 12 Oct 2026.",
 15: "15 U.S.C. § 638(e)(4)(C) (SBIR “third phase” = work that “derives from, extends, or completes efforts made under prior funding "
     "agreements under the SBIR program”) and 15 U.S.C. § 638(r) (Phase III awards) — law.cornell.edu/uscode/text/15/638 (accessed 11 Oct 2026).",
 17: "Exos records: BLK3 reusable rocket design work performed under AFWERX SBIR Phase II FA8649-21-P-0838 (confirmed by Exos CEO, 11 Oct 2026).",
 16: "Exos SBIR Phase II award record, FA9300-25-C-6022, U.S. Space Force topic SF233-0019 (award documents on file at Exos).",
 13: "Exos Mission Control, Payloads-exo3 program record (program start 26 Jun 2026; seven-stage pipeline with human "
     "approval gate) and Exos payload and vehicle scheduling records — Exos internal system of record, available for "
     "Government review on request.",
 18: "Texas Secretary of State, Certificate of Fact (Status), Exos Aerospace Systems & Technologies, Inc., obtained via "
     "SOSDirect, October 2026 (Attachment 1).",
}

def D(text):
    return ("decision", text)

C = []
def add(*b): C.append(b)

VER = ""
LAUNCH = "planned, as early as Q2 2027, subject to launch site assignment, FAA licensing and range approvals"

# ------------------------------------------------------------------ COVER
add("title", "Whitepaper Response")
add("sub", "Vandenberg Space Force Base (VSFB) Call for Whitepapers for Mission Development Zone (MDZ) Outgrant")
add("sub", "Solicitation / Notice: VSFBMDZCall  ·  SLD 30/XPR  ·  Responses due 16 October 2026")
add("title2", "Exos MDZ Launch-Support Facility (land lease / outgrant)")
add("sub", "Ground facilities supporting planned Exos commercial launch operations at VSFB, with the MCMS-exo3 multi-user payload "
           "processing and logistics capability as added value for the spaceport")
add("spacer",)
add("cover", "**Submitted by:** Exos Aerospace Systems & Technologies, Inc.")
add("cover", "299 FM 1903, Greenville, TX 75402")
add("cover", "CAGE 7EMY6  ·  UEI CK24BPZGF854  ·  SAM.gov Active (All Awards) through 7 Oct 2027")
add("cover", "NAICS 336414 (primary) · 541715 · 541330  ·  Small Business")
add("cover", "**Point of contact:** John Quinn, Cofounder & Chief Executive Officer")
add("cover", "jquinn@exosaero.com  ·  +1 (972) 740-8355  ·  www.exosaero.com")
add("cover", "Submitted to: Ainsley Allen, SLD 30 — 232909MissionDevelopmentZoneMDZFacilityConstruct@groups.af.mil")
add("spacer",)
add("note", "Informational whitepaper submitted in response to a call that is not governed by the FAR and is not an RFI, RFP or "
            "RFQ (call §2.1). Exos acknowledges that the USSF may use the information in this submission for MDZ scoping and "
            "planning (call §2.1). Concepts herein are proposed and pre-decisional; nothing in this paper is an offer, a "
            "financing commitment or a rent proposal. Exos launch operations at VSFB are " + LAUNCH + "; Exos holds no VSFB "
            "launch site, launch license for VSFB, or VSFB manifest today.")
add("note", "**Attachments:** (1) Texas Secretary of State Certificate of Fact (Status); (2) Officer Certification of U.S. "
            "Ownership (51 U.S.C. § 50101(7)).")
add("note", "**Distribution:** " + DIST)
add("pb",)

# ------------------------------------------------------------------ EXEC SUMMARY
add("h1", "Executive Summary")
add("p", "Exos Aerospace requests consideration for an **MDZ land lease (outgrant under 10 U.S.C. § 2667) for the ground facilities "
         "that support Exos commercial launch operations at VSFB** [1][12]: vehicle and payload receiving, integration and "
         "processing, storage, spaceport logistics, and launch/mission operations and administrative/engineering offices. These match "
         "the uses the call lists for the MDZ — payload processing, spaceport logistics, commodity storage, launch and mission control, "
         "spacecraft integration and administrative/engineering spaces — and the call’s stated purpose of infrastructure for the "
         "“preparation, operation, and support of launch programs” [1].")
add("p", "Exos launch operations at VSFB are **" + LAUNCH + "**. The launch site itself has not been sited. As the call states, "
         "the MDZ is not a space launch complex [1]; Exos presents the MDZ as the support and processing base for a launch site to be "
         "assigned separately through SLD 30 and the FAA. Exos is an FAA-licensed reusable suborbital launch operator that flies "
         "today from Spaceport America, New Mexico [10]; it has not launched from Vandenberg. Its latest FAA-licensed vehicle, BLK3, "
         "is preparing for flight in early 2027.")
add("p", "**Added value for the spaceport.** As Exos operates on the leased site, it would develop **MCMS-exo3** (Mission Cargo "
         "Management System — exo3) into a multi-user, AI-managed payload processing and logistics capability and open it to other "
         "base users over time. MCMS-exo3 builds on the exo3 payload process in use today for Exos payload operations [13]; its "
         "extensions are proposed. It speaks directly to a documented need: Space Force officials told GAO that payload processing "
         "capacity is the greatest challenge facing DoD space launch, with an expected annual shortfall of up to two processing bays "
         "from FY2026 through FY2030, and that the Space Force lacks insight into commercial processing schedules [3]. SLD 30 "
         "supported 51 launches in 2024 and 77 total space launches, missile tests and aeronautical operations in 2025 [2].")
add("p", "**Why now.** Space Force officials have told GAO that payload processing capacity is the greatest challenge facing DoD "
         "space launch [3], and this MDZ call is SLD 30’s window to shape the response [1]. Exos asks SLD 30 to consider a direct "
         "award (7.2) so it can adopt an AI-native payload and range-integration process from an operator that runs exo3 today, "
         "ahead of Exos operations as early as Q2 2027, rather than waiting through a multi-year competitive cycle.")
add("p", "**Optional service offer.** Separately from the lease, Exos offers SLD 30 and MDZ tenants an optional **Exos Mission "
         "Control implementation for site and payload management services**, using the same Exos-built Mission Control software "
         "Exos uses today to schedule its own payloads and vehicles [13] (see 8.2).")
add("p", "**Phasing.** Phase 0 — MCMS-exo3 proven on Exos operations, now. Phase 1 — Exos launch-support facility on the lease, ready "
         "for operations as early as Q2 2027. Phase 2 — expansion to multi-user payload processing on MCMS-exo3, with an optional "
         "5-meter-class bay and hazardous processing cell, gated on financing and demand.")

# ------------------------------------------------------------------ 1.0
add("h1", "1.0 CORPORATE ADMINISTRATION")
add("h2", "1.1 Company legal name")
add("p", "Exos Aerospace Systems & Technologies, Inc. (dba Exos Aerospace) — CAGE 7EMY6, UEI CK24BPZGF854 [11].")
add("h2", "1.2 Company legal form of ownership")
add("p", "Texas corporation, founded and incorporated in 2015; EIN 47-3491152. Exos is organized under the laws of the State of "
         "Texas and is registered and active in SAM.gov (All Awards) through 7 October 2027 [11]. Exos is a Small Business under "
         "its primary NAICS 336414 and claims no other socio-economic designation.")
add("p", "**Eligibility as a United States commercial provider (51 U.S.C. § 50101(7)) [12].** Exos is a United States "
         "commercial provider as defined in 51 U.S.C. § 50101(7): a commercial provider organized under the laws of a State "
         "(Texas) that is more than 50 percent owned by United States nationals. Evidence of organization under Texas law: Texas Secretary of State "
         "Certificate of Fact (Status) (Attachment 1) [18]. Evidence of U.S. ownership: Officer Certification of "
         "U.S. Ownership signed by the Chief Executive Officer (Attachment 2).")
add("h2", "1.3 Company legal place of business (address)")
add("p", "299 FM 1903, Greenville, TX 75402 (headquarters: engineering, final assembly, ground test).")
add("h2", "1.4 Business address of company operating locations other than headquarters")
add("bl", ["**Spaceport America, New Mexico** — current launch and recovery operations site for Exos reusable suborbital flights [10]. "
           "Exos operations are not limited to Spaceport America; Exos evaluates additional launch and operating sites as its "
           "manifest grows.",
           "**Vandenberg SFB:** none today. The MDZ lease would add a West Coast launch-support location for Exos operations "
           + LAUNCH + ". Expansion of Exos’s presence at Vandenberg beyond the initial footprint is under consideration (see 5.1)."])
add("h2", "1.5 Primary & alternate points of contact")
add("table", [["Role", "Name / title", "Phone", "E-mail"],
              ["Primary", "John Quinn, Cofounder & Chief Executive Officer", "+1 (972) 740-8355", "jquinn@exosaero.com"],
              ["Alternate", "Lizi (Elizabeth) Quinn, Business Development", "—", "lquinn@exosaero.com"]],
        [1.0, 2.6, 1.3, 1.6])
add("h2", "1.6 Company history and relevant past performance")
add("p", "Exos was founded in 2015 to build reusable suborbital launch vehicles. Its team carries over 25 years of experience in the "
         "rocket and space industry, with deep Armadillo Aerospace and Exos heritage: hundreds of rocket engines and dozens of flying "
         "vehicles built. Exos is an FAA-licensed reusable suborbital launch operator providing flight-test services for space, "
         "defense, research and commercial payloads [10], with payload recovery for post-flight inspection, analysis "
         "and iteration [14]. Its latest FAA-licensed vehicle, BLK3, is preparing for flight in early 2027.")
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
add("p", "**Primary use: Exos launch-support base.** The leased MDZ site would be the ground support and processing base for Exos "
         "commercial launch operations at VSFB, " + LAUNCH + ". The launch pad itself is outside the MDZ and would be assigned "
         "separately; the MDZ site hosts everything that does not need to be at the pad. Exos’s reusable vertical-takeoff, "
         "vertical-landing approach needs little fixed infrastructure at the pad beyond power and communications, which keeps "
         "the support footprint compact.")
add("table", [["Function (call §1.3 wording)", "Exos activity on the MDZ site"],
              ["Spacecraft integration / payload processing", "Receive customer payloads; inspection, checkout and integration into Exos payload accommodations"],
              ["Preparation and support of launch programs (§3.1)", "Receive and prepare the reusable vehicle between flights; inspection, turnaround and storage"],
              ["Spaceport logistics / commodity storage", "Receiving, controlled storage and staging of vehicle hardware, GSE and spares; transport to the assigned launch site"],
              ["Launch and mission control", "Mission operations room for Exos launch campaigns (coordinated with Western Range)"],
              ["Administrative / engineering spaces", "Exos operations, engineering and customer offices"]],
        [2.4, 4.1])
add("p", "**Campaign flow.** Vehicle, GSE and payloads arrive by road (or through Vandenberg Airfield for payloads), are received "
         "and processed at the MDZ site, then move to the assigned launch site for the launch campaign. After landing, the reusable "
         "vehicle returns to the MDZ site for inspection and turnaround; payloads are handed back to their owners.")
add("p", "**Added value (brief; see 4.0, 7.2 and 8.0).** As it operates, Exos would develop the site’s processing and logistics into "
         "MCMS-exo3, a multi-user, AI-managed payload processing and logistics capability opened to other base users over time. "
         "Exos flies today under its FAA launch license (14 CFR Part 431, transitioning to Part 450) at Spaceport America [10]. "
         "Launching from a Government range adds range requirements such as flight termination system (FTS) requirements. "
         "Integrating exo3 with those range and FTS requirements is work Exos would perform under contract to SLD 30, creating "
         "an AI-native process that brings commercial and Defense requirements together in one easy-to-use process for range users. "
         "This is range-integration and process work only.")
add("p", "**Finance, design, construct, operate and maintain approach (call §1.2).** Exos would hold the outgrant and operate and "
         "maintain the facilities, with design and construction through a design-build contractor. Phase 1 launch-support "
         "facilities are scaled to Exos operations and phased with launch-site assignment; facility capital would come from Exos "
         "operating capital and/or a developer or financing partner under a build-to-suit or ground-lease structure. Phase 2 "
         "multi-user expansion is gated on anchor-customer demand and financing.")
add("h2", "2.2 Desired facility developments at the MDZ")
add("table", [["ID", "Facility", "Description", "Phase"],
              ["F0", "Exos Mission Control / MCMS-exo3 digital system of record", "Software in use on Exos operations (payload and vehicle scheduling); no MDZ construction needed", "0"],
              ["F1", "Vehicle & payload processing building", "High bay for vehicle receiving, inspection and turnaround; clean payload integration area", "1"],
              ["F2", "Logistics & storage", "Receiving, controlled storage of hardware, GSE and spares; staging and shipping", "1"],
              ["F3", "Operations & engineering building", "Launch/mission operations room, engineering and customer offices, Government office option (8.0)", "1"],
              ["F4", "Site works", "Heavy-haul access and transporter apron, parking, perimeter fence, access control, utility yard", "1"],
              ["F5", "Multi-user payload processing (MCMS-exo3)", "Additional cleanroom bays open to other base users; optional 5-m-class high bay", "2"],
              ["F6", "Hazardous processing cell (future option)", "Not part of this request; would need a separate hazardous parcel and explosives site plan", "2+"]],
        [0.4, 1.7, 3.5, 0.6])
add("p", "**Compatibility of the property (call §3.1).** The MDZ is a dedicated support zone on North VSFB within 5 miles of "
         "Vandenberg Airfield, with existing roads serving the numbered parcels [1]. Constraints that shape siting are building "
         "heights in the aircraft arrival corridor, the flood plain on Hazardous 50-acre Parcels 1–3, and lettered parcels without "
         "road access [1]. Exos prefers road-served parcels outside the approach-departure clearance surface (Exhibit B Fig. 4).")

# ------------------------------------------------------------------ 3.0
add("h1", "3.0 TARGETED PAYLOAD PROCESSING CAPABILITIES (Optional)")
add("p", "Phase 1 payload processing serves Exos launch customers. Phase 2 (MCMS-exo3 multi-user expansion) is where the call’s "
         "5-meter-class question applies. Values are **planning requirements** to be validated with users during final design.")
add("h2", "3.1 Facility specifications for 5-meter-class payloads and next-generation fairings")
add("table", [["Parameter", "Phase 1 (F1: Exos launch-support)", "Phase 2 option (F5: multi-user, 5-m class)"],
              ["Cleanroom class", "ISO 8 payload integration area", "ISO 8 high bay; ISO 7 integration cells"],
              ["Environmental control", "Temperature, humidity, particulate monitoring; ESD-safe floors", "Same, plus molecular-contamination monitoring"],
              ["Overhead crane hook height", "Sized to Exos vehicle and payload handling; set in final design within airfield height limits", "Sized to published 5-m-class fairing envelopes; set with users in final design"],
              ["Clear span / clear ceiling height", "Set in final design within airfield height limits (Exhibit B Fig. 4)", "Set with users in final design; parcel chosen outside the approach-departure surface"],
              ["Crane capacity", "Sized to Exos vehicle and GSE lift loads in final design", "Sized to 5-m-class payload and fairing lifts with users in final design"],
              ["Number of bays", "One vehicle processing high bay plus one payload integration area", "Additional multi-user bays; count set by demand and financing"]],
        [1.7, 2.4, 2.4])

add("h2", "3.2 Projected annual processing throughput")
add("table", [["Phase", "Projected annual processing throughput"],
              ["Phase 1 (F1: Exos launch-support)", "Exos launch campaigns per year, scaled to manifest once a launch site is assigned"],
              ["Phase 2 (F5: multi-user, MCMS-exo3)", "Multi-user processing campaigns per year as a range set by the final bay count, "
               "sized against the GAO-reported shortfall of up to two processing bays per year through FY2030 [3]"]],
        [2.3, 4.2])

# ------------------------------------------------------------------ 4.0
add("h1", "4.0 BENEFIT TO THE SPACEPORT ECOSYSTEM")
add("h2", "4.1 Benefit to VSFB, the commercial space industry and USSF national security objectives")
add("bl", [
 "**More launch providers, more assured access.** A reusable suborbital operator, " + LAUNCH + ", adds launch diversity at the "
 "Western Range with a compact, low-infrastructure support footprint that leaves pads and processing capacity for others.",
 "**Bonus: MCMS-exo3 multi-user payload processing and logistics.** As it operates, Exos would develop MCMS-exo3 on the leased "
 "site and open it to other base users over time — adding processing capacity where Space Force officials told GAO the "
 "shortfall is greatest (up to two bays per year through FY2030) [3], complementing SSC processing-capacity awards that "
 "target 2028–2029 [4][5]. MCMS-exo3 extensions are proposed.",
 "**One process for commercial and Defense range requirements.** Under contract to SLD 30, MCMS-exo3 would integrate range "
 "requirements, including flight termination system (FTS) requirements, with payload processing and logistics, giving every "
 "range user one AI-native process with human approval gates (range-integration and process work only).",
 "**Visibility the Government lacks.** GAO found the Space Force cannot see commercial payload processing schedules [3]. With "
 "customer consent, MCMS-exo3 could share bay schedules and readiness with SLD 30.",
 "**Accountability for high-value hardware.** A signed, append-only chain of custody (RFID/barcode scan and sensor logging at "
 "every handoff), a physical value ledger (declared/insured value re-attested at each transfer, linked to waivers of claims) and "
 "a brand and media value ledger, with AI anomaly detection, schedule-conflict prediction and compliance checks behind human "
 "approval gates. Export-control indicators go to Exos’s Empowered Official and are never auto-cleared.",
 "**Supports “launch on demand.”** The Spaceport of the Future program aims to remove operational bottlenecks and enable launch "
 "on demand [6]; scheduling across bays, cranes, crews and range calendars targets those bottlenecks.",
 "**Industrial base.** A U.S. small business operator broadens the Western Range supplier base and creates local technical jobs."])

# ------------------------------------------------------------------ 5.0
add("h1", "5.0 PARCEL SELECTION, UTILITY, & PERSONNEL REQUIREMENTS")
add("h2", "5.1 Acreage required and preferred conceptual footprints (MDZ Parcel Map, Exhibit B)")
add("p", "Siting logic: (1) a compact, road-served launch-support footprint for Phase 1; (2) contiguous expansion room for the Phase 2 "
         "multi-user build-out; (3) outside the approach-departure clearance surface and APZ 2 (Exhibit B Fig. 4) so a high bay is "
         "feasible; (4) avoid flood-plain Hazardous 50-acre Parcels 1–3 and lettered parcels without road access [1]; (5) no hazardous "
         "parcel is requested, because no propellant or ordnance is handled at the MDZ (see 6.2).")
add("table", [["Priority", "Area (Exhibit B)", "Parcel number(s)", "Use"],
              ["Preferred", "Non-Hazardous 5-acre plots, southern strip along Terra Rd / 13th St", "40, 41 (contiguous)", "Phase 1: F1–F4 launch support"],
              ["Expansion", "Adjacent Non-Hazardous 5-acre plots", "42, 43", "Phase 2: F5 multi-user"],
              ["Alternate", "Non-Hazardous 5-acre plots, southern strip", "26, 27, 28, 44", "Phase 1/2 alternate"],
              ["Hazardous", "None requested", "—", "No propellant/ordnance at the MDZ"]],
        [1.1, 2.6, 1.5, 1.3])
add("p", "**Acreage requested: approximately 20 acres as the initial (starter) footprint — Non-Hazardous 5-acre Plots 40–43.** "
         "Plots 40–41 host the Phase 1 launch-support facility and Plots 42–43 provide room to expand. The reference for Exos’s "
         "flight-operations footprint is Spaceport America, New Mexico, where Exos flies today under its FAA launch license "
         "(14 CFR Part 431, transitioning to Part 450) [10]. Expansion of Exos’s Vandenberg presence beyond this starter footprint is "
         "under consideration and would be raised with SLD 30 separately. No hazardous parcel is requested. No rent proposal is "
         "included, as none is requested by the call.")
add("h2", "5.2 Estimated peak and average daily on-site personnel (steady state)")
add("table", [["Category", "Average daily", "Peak (launch campaign)", "Shifts"],
              ["Exos operations, technicians, logistics, security", "Core Exos site team", "Core team plus Exos launch-campaign crew", "1 shift; extended during campaigns"],
              ["Customer payload teams", "Per scheduled campaign", "Per campaign, scheduled in Mission Control", "Per campaign"],
              ["Visitors / Government", "Occasional", "Launch-campaign reviews", "Day shift"]],
        [2.3, 1.2, 1.6, 1.4])
add("p", "Exos VSFB staffing is a deployment and hiring plan scaled to launch-campaign cadence once a launch site is assigned; "
         "numeric counts will be provided with final design and utility coordination.")
add("h2", "5.3 Estimated daily and peak requirements for power, water, road/traffic access and communications")
add("table", [["Utility", "Phase 1 requirement", "Notes"],
              ["Power", "Light-industrial service; daily and peak loads set in utility coordination with SLD 30", "Processing-area HVAC and shop loads; backup power for environmental control"],
              ["Water / sewer", "Domestic-scale demand; quantity set in utility coordination", "Domestic use; no process wastewater planned in Phase 1"],
              ["Road / traffic", "Heavy-haul access to Terra Rd / 13th St; transporter apron", "Vehicle moves to/from the assigned launch site scheduled with SLD 30"],
              ["Communications", "Commercial fiber, redundant path; base/range connections as authorized", "Range and mission-ops links per SLD 30 requirements"]],
        [1.2, 2.4, 2.9])

# ------------------------------------------------------------------ 6.0
add("h1", "6.0 IMPACTS AND SAFETY CONSIDERATIONS")
add("h2", "6.1 Operational CONOPS (material logistics and security boundaries)")
add("bl", [
 "**Inbound:** vehicle hardware, GSE and payloads arrive by road through base entry control (payloads may also arrive through "
 "Vandenberg Airfield [1]) and are escorted to F2 receiving. Shipments are pre-registered so gate, escort and receiving crews "
 "are scheduled ahead.",
 "**On site:** F2 receiving → F1 processing/integration → transporter apron (F4). Each move is a scanned, signed custody event.",
 "**To and from the launch site:** the vehicle and integrated payloads move to the separately assigned launch site under SLD 30 "
 "transport procedures; the reusable vehicle returns after landing for turnaround.",
 "**Security boundaries:** fenced perimeter with one controlled entry; nested zones — administrative/visitor (F3 front office), "
 "controlled processing (F1/F2, badge access, escorts), and customer-segregated payload areas. Export-controlled hardware and "
 "data are handled under ITAR/EAR procedures with decisions by Exos’s Empowered Official. Exos holds no facility security "
 "clearance; classified processing would be offered only under Government sponsorship and accreditation."])
add("h2", "6.2 Anticipated quantities and types of propellants, commodities, or hazardous chemicals")
add("p", "**No propellants or ordnance will be stored or handled on the MDZ parcels.** All propellant loading and any ordnance "
         "handling occur only at the separately assigned launch site. The MDZ site would hold only ordinary shop commodities: "
         "cleaning solvents in flammable cabinets, compressed inert gases (e.g., nitrogen, helium), lithium-ion batteries in "
         "customer payloads, and diesel for backup power, all in small, fire-code-compliant quantities.")
add("h2", "6.3 Anticipated explosive safety arcs and hazard areas (siting requirements)")
add("p", "With no explosives or propellants at the MDZ, **no explosive safety (quantity-distance) arcs are anticipated and no "
         "hazardous parcels are needed**; standard fire-code separation applies (call §2.4) [1]. Launch hazard areas belong to the "
         "separately assigned launch site. A Phase 2 hazardous payload-processing cell (F6) remains only a future option; it would "
         "require its own hazardous parcel and a separate explosives site plan under DoD explosives safety standards "
         "(DESR 6055.09 / DAFMAN 91-201) before any use.")
add("h2", "6.4 Mitigation alternatives for impacts on neighboring operations and transportation routes")
add("bl", [
 "Schedule vehicle and oversize moves in windows coordinated with SLD 30 and neighbors; MCMS-exo3 flags conflicts with range and "
 "road calendars before a move is approved.",
 "Keep building heights within airfield limits by choosing parcels outside the approach-departure surface (5.1).",
 "Avoid the flood plain and road-less parcels so no new road corridors are needed [1].",
 "No engine testing or launch activity at the MDZ; backup generator exercised on a set schedule.",
 "Stormwater, lighting and habitat measures as required by the base environmental review; Exos would support NEPA with site data."])
add("h2", "6.5 New construction or modifications required to existing VSFB infrastructure")
add("bl", [
 "Utility extensions (power, water, sewer, fiber) to the selected parcels; capacity upgrades if the base utility study requires.",
 "Driveway and turning-radius improvements at Terra Rd / 13th St for transporter access; no new public roads for the preferred parcels.",
 "Connection to base security and entry control as directed by SLD 30.",
 "No modifications to the airfield. Launch-site infrastructure is outside this MDZ request and depends on separate site assignment."])

# ------------------------------------------------------------------ 7.0
add("h1", "7.0 CONCEPTUAL PROJECT TIMELINE")
add("h2", "7.1 Notional schedule from initial site access to operational capability")
add("p", "Target: Phase 1 launch-support facilities ready to support Exos operations **as early as Q2 2027, subject to launch site "
         "assignment, FAA licensing and range approvals**. Durations are notional and measured from outgrant execution (M0); an "
         "interim (temporary or modular) facility may be needed to meet Q2 2027 if permanent construction runs longer.")
add("table", [["Phase / milestone", "Activity", "Notional timing"],
              ["Phase 0 (now)", "MCMS-exo3 custody, value ledger and gates proven on Exos operations; demonstration to SLD 30 stakeholders", "From submission"],
              ["In parallel", "Launch site assignment request, FAA license modification and range approvals (outside the MDZ)", "Starting on submission"],
              ["M0", "Outgrant executed; initial site access", "As agreed with SLD 30"],
              ["Design & site", "Surveys, environmental support, utility coordination; final design of F1–F4", "From M0"],
              ["Phase 1 build", "Site development and pre-engineered / modular construction of F1–F4; interim modular facility if needed", "Following final design"],
              ["Phase 1 activation", "Launch-support facility ready for Exos operations", "As early as Q2 2027 (subject to approvals)"],
              ["Phase 2 gate", "Multi-user MCMS-exo3 expansion; optional 5-m-class bay (hazardous cell only as a separate future option)", "On financing and demand"]],
        [1.4, 3.6, 1.5])


add("h2", "7.2 Requested award approach (supports operations as early as Q2 2027)")
add("p", "To make Q2 2027 achievable, Exos asks USSF/SLD 30 to consider **two separate instruments**, to the extent permitted by "
         "applicable authority:")
add("bl", ["**(1) The MDZ outgrant** under 10 U.S.C. § 2667 on its normal real-property path [12]. An outgrant is a real-property "
           "instrument, not a FAR procurement.",
           "**(2) A separate SBIR Phase III contract** for MCMS-exo3 range and FTS process integration, on the SBIR basis below [15]."])
add("p", "Exos does not assert that any particular award path is legally available; this is a request for the Government’s "
         "consideration.")
add("p", "**What SLD 30 would contract for.** Integration of exo3 with VSFB range requirements — including flight termination "
         "system (FTS) requirements that apply when launching from a Government range — into MCMS-exo3: one AI-native process that "
         "brings commercial and Defense requirements together for range users, with human approval gates. This is range-integration "
         "and process work only; it is not FTS hardware.")
add("p", "**SBIR basis.** Under the SBIR statute, a third phase covers work that “derives from, extends, or completes efforts made "
         "under prior funding agreements under the SBIR program,” and agencies may make Phase III awards to the firms that performed "
         "the prior work [15]. The exo3 / Mission Control payload process was built to support Exos’s reusable-rocket program [13].")
add("bl", ["**Primary basis — FA8649-21-P-0838**, AFWERX SBIR Phase II, “Prototype for a Mobile Low-Cost Ultra-Lightweight "
           "Hypersonic Reusable Launch Vehicle,” $750,000, March 2021 [8]. The BLK3 reusable rocket design work was performed under "
           "this award [17].",
           "**Supporting — FA9300-25-C-6022**, SBIR Phase II, Space Force topic SF233-0019: design, fabrication and hover test of the "
           "Exos HVRR (hover vehicle reusable rocket); USASpending description “Suborbital Hover Vehicle–Reusable Rocket,” "
           "$1,897,824, September 2025 [8][16]."])
add("p", "**Why a direct award now.** Space Force officials have told GAO that payload processing is the greatest challenge facing "
         "DoD space launch, with shortfalls expected through FY2030 [3], and this MDZ call is the window to address it at VSFB [1]. "
         "A direct award would let SLD 30 adopt an AI-native process from an operator that already runs exo3 today [13], and have it "
         "integrated with range requirements ahead of Exos operations as early as Q2 2027, rather than waiting through a "
         "multi-year competitive cycle.")

# ------------------------------------------------------------------ 8.0
add("h1", "8.0 ADDITIONAL ENHANCEMENTS")
add("h2", "8.1 Enhancements offered for Government consideration")
add("bl", [
 "**MCMS-exo3 multi-user payload processing and logistics.** Developed by Exos on the leased site as it operates and "
 "opened to other base users over time, adding processing capacity against the GAO-reported shortfall [3]. Built on the exo3 "
 "process in use today for Exos payload operations [13]: 01 Capture, 02 Qualify & Score, 03 Scope, 04 Quote, 05 Contract & "
 "Regulatory, 06 Approve & Close (human), 07 Handoff to Fly. Extensions (chain of custody, physical value and brand value ledgers, "
 "facility scheduling, AI layer with human gates) are proposed. The exo3 process has not been used at Vandenberg.",
 "**MCMS-exo3 range and FTS process integration under contract to SLD 30** (see 7.2): one AI-native process for "
 "commercial and Defense range requirements; range-integration and process work only.",
 "**Shared processing visibility for SLD 30:** customer-consented read access to MCMS-exo3 bay schedules and readiness [3].",
 "**MCMS-exo3 for other MDZ tenants:** one logistics picture across the zone.",
 "**Government-dedicated space:** office space in F3 and priority scheduling for DoW surge needs.",
 "**Phase 0 demonstration** of MCMS-exo3 to SLD 30 using Exos operations, limited in scope."])

add("h2", "8.2 Optional opportunity: Exos Mission Control implementation for site and payload management services")
add("p", "Separately from the outgrant, Exos offers USSF/SLD 30 the option to have Exos implement and operate **Exos Mission "
         "Control** — the Exos-built operations software Exos uses today to schedule its own payloads and vehicles and to run "
         "its seven-stage exo3 payload process with a human approval gate [13] — as a **site and payload management service** "
         "for the MDZ. The option is not a condition of the lease and would be scoped and priced separately under an instrument "
         "the Government chooses.")
add("table", [["Service area", "What Exos Mission Control would provide"],
              ["Site management", "Parcel and facility calendars, bay/crane/crew scheduling, access and escort scheduling, work orders and maintenance tracking across MDZ tenants"],
              ["Payload management", "Payload intake, readiness and processing schedules; signed chain of custody at each handoff; customer-segregated records"],
              ["Vehicle and range scheduling", "Vehicle moves, transporter and road windows, and launch-campaign milestones checked against range and base calendars before approval"],
              ["Government visibility", "Customer-consented, read-only view for SLD 30 of bay schedules and readiness across the zone [3]"],
              ["Controls", "Human approval gates on every commitment; export-control indicators routed to Exos’s Empowered Official, never auto-cleared"]],
        [1.7, 4.8])
add("p", "**Implementation path.** (1) Demonstration to SLD 30 on Exos’s own operations; (2) configuration for Exos’s MDZ site at "
         "Phase 1 activation; (3) optional extension to SLD 30 and other MDZ tenants. Hosting, data rights, cybersecurity "
         "authorization and any interface to Government systems would be defined with SLD 30 before use; Exos has not deployed "
         "Mission Control at Vandenberg or on Government networks.")

# ------------------------------------------------------------------ STATUS
add("h1", "Statement of Status (demonstrated vs. proposed)")
add("table", [["Item", "Status"],
              ["Exos launch operations at VSFB", "Planned, as early as Q2 2027, subject to launch site assignment, FAA licensing and range approvals; no VSFB launch site, license or manifest today"],
              ["Exos launch operations today", "FAA-licensed reusable suborbital operator from Spaceport America, NM [10]"],
              ["BLK3", "Latest FAA-licensed vehicle; preparing for flight, early 2027"],
              ["exo3 payload process (7 stages, human gate)", "In use today for Exos payload operations; not used at Vandenberg [13]"],
              ["Exos Mission Control (payload and vehicle scheduling)", "In use today on Exos operations; offered as an optional MDZ site and payload management service (8.2); not deployed at Vandenberg [13]"],
              ["MCMS-exo3 extensions and multi-user capability", "Proposed / in development"],
              ["MCMS-exo3 range / FTS process integration", "Proposed, for contract with SLD 30; process work only, not FTS hardware"],
              ["MDZ facilities F1–F6", "Proposed concept; no design, financing or Government commitment"],
              ["BLK4 / BLK4 Heavy orbital configuration", "Funded-future capability; not part of this MDZ request"],
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
 ("Call §1.2 / 51 U.S.C. § 50101(7)", "Respondent is a United States commercial provider", "1.2"),
 ("Exh. A 1.3", "Legal place of business", "1.3"),
 ("Exh. A 1.4", "Other operating locations", "1.4"),
 ("Exh. A 1.5", "Primary & alternate POCs", "1.5"),
 ("Exh. A 1.6", "Company history / relevant past performance", "1.6"),
 ("Exh. A 2.1 / Call §3.1", "Concept of operations; property compatibility", "2.1"),
 ("Call §1.3 / §1.4", "Use matches MDZ intended uses; MDZ not a launch complex", "2.1"),
 ("Call §1.2", "Approach to finance, design, construct, operate, maintain", "2.1"),
 ("Exh. A 2.2 / Call §3.1", "List and description of desired facility developments", "2.2"),
 ("Exh. A 3.1 / Call §3.2", "5-m-class facility specs: cleanroom class, hook height, clear span/ceiling", "3.1"),
 ("Exh. A 3.2 / Call §3.2", "Projected annual processing throughput", "3.2"),
 ("Exh. A 4.1 / Call §3.3", "Benefit to VSFB spaceport ecosystem, industry, USSF", "4.1"),
 ("Exh. A 5.1 / Call §3.4", "Acreage; preferred parcels by area and parcel number", "5.1"),
 ("Exh. B note", "Justification required if Hazardous 50-acre Parcels 1-3 requested (not requested)", "5.1"),
 ("Exh. A 5.2 / Call §3.4", "Peak and average daily personnel", "5.2"),
 ("Exh. A 5.3 / Call §3.4", "Power, water, road/traffic, communications", "5.3"),
 ("Exh. A 6.1 / Call §3.5", "Operational CONOPS, logistics, security boundaries", "6.1"),
 ("Exh. A 6.2 / Call §3.5", "Propellants, commodities, hazardous chemicals", "6.2"),
 ("Exh. A 6.3 / Call §2.4, §3.5", "Explosive safety arcs, QD, hazard areas", "6.3"),
 ("Exh. A 6.4 / Call §3.5", "Mitigation of impacts on neighbors and routes", "6.4"),
 ("Exh. A 6.5 / Call §3.5", "New construction / modifications to VSFB infrastructure", "6.5"),
 ("Exh. A 7.1 / Call §3.6", "Notional schedule: design, site development, construction, activation", "7.1"),
 ("Exos addition", "Requested award approach: MDZ outgrant + separate SBIR Phase III contract for MCMS-exo3 range/FTS integration (Counsel to confirm)", "7.2"),
 ("Exh. A 8.1", "Additional enhancements (Government use, launch infrastructure)", "8.1"),
 ("Exos addition (optional)", "Exos Mission Control implementation for site and payload management services", "8.2"),
 ("Exh. A 1.2 evidence", "Texas SOS Certificate of Fact (Status); Officer Certification of U.S. Ownership", "Attachments 1–2"),
 ("Call §4.2", "Maximum 30 pages", "Whole document"),
 ("Call §4.3", "MS Word or PDF; DoD SAFE delivery; separate receipt confirmation", "Submission checklist"),
]
add("h1", "Appendix A — Compliance Matrix")
add("p", "Maps every request in the call (Section 3 and Exhibit A) to this response. Page references are to the PDF version.")
add("table", [["Call reference", "Requirement", "Response section", "PDF page"]] +
    [[a, b, c, str(_PM.get(c, "—"))] for a, b, c in MATRIX], [1.6, 2.9, 1.2, 0.8])
add("h1", "Sources")
for k in sorted(SRC):
    add("src", "[%d] %s" % (k, SRC[k]))
