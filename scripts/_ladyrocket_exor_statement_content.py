"""Shared content: Exos Manufacturer & Operator Statement — Lady Rocket Program (Italy).
Prepared 2026-10-11 (v2: Jon corrections — customer wet lease, 12-mo build, Italian partners engaged, NDA in place) for John Quinn (email command, Eva Blaisdell 'Exor fund Italy').
Consistent with: executed Wet Lease O&M Agreement (eff. 2024-08-01, term to 2030-12-31),
2023 Sales & Commercialization Agent Agreement, Appendix G (authority/no-solicitation),
10/1 vehicle-options letter (v4), Aug-26 Leonardo term sheet guardrails (Sec 5/6).
INTERNAL-ONLY items deliberately excluded: two-vehicle $10.0M total.
"""

TITLE = "Manufacturer & Operator Statement — Lady Rocket Program (Italy)"
SUBTITLE = ("Exos Aerospace Systems & Technologies, Inc.  ·  Prepared for Copernic Space Corporation "
            "(“Copernic” / “Lady Rocket”)  ·  NON-BINDING  ·  October 2026")

INTRO = ("Copernic has asked Exos to document its role as vehicle manufacturer and launch operator for the "
         "Lady Rocket program, for use in Copernic’s materials for prospective program investors and Italian "
         "industrial partners (including Exor N.V.). This statement describes Exos’s commitments as they "
         "stand under the agreements now in place between Copernic and Exos. It does not change those "
         "agreements, and where it differs from them, the agreements govern.")

# (heading, [paragraphs or ("bullets", [..]) or ("table", header, rows)])
SECTIONS = [
    ("1.  Agreements in Place", [
        ("bullets", [
            "Wet Lease Operation and Maintenance Agreement (BLK3 Rocket Project) between Copernic Space "
            "Corporation (Client) and Exos (Owner/Operator). Effective August 1, 2024; term through "
            "December 31, 2030. This is the governing agreement for the program.",
            "Sales and Commercialization Agent Agreement (2023). Under it, Copernic is Exos’s commissioned "
            "agent for payload sales on Exos-owned vehicles.",
            "Mutual Non-Disclosure Agreement between Copernic and Exos, in place.",
            "Wet-lease appendices, vehicle-option terms and a Launch Services Agreement covering ordered "
            "vehicles are in negotiation and have not yet been executed. The commercial terms in Section 3 "
            "are Exos’s stated terms in that negotiation. They become binding only when a definitive "
            "agreement is signed and a deposit is received.",
        ]),
    ]),
    ("2.  The Vehicle — Exos BLK3", [
        "BLK3 is Exos’s Precision Suborbital Reusable Launch Vehicle. It is FAA-licensed and reusable, with a "
        "135 kg payload bay, a target apogee of about 100 km, and clean-burning LOX/ethanol propulsion. BLK3 "
        "has not yet flown commercially. Commercial flight service is targeted for early 2027. Exos and its "
        "predecessor programs have flown reusable suborbital vehicles since 2018.",
    ]),
    ("3.  Exos Manufacturing Commitment and Program Economics", [
        "For each vehicle Copernic orders, Exos will build the vehicle and then operate it under the Wet Lease. "
        "Exos performs configuration, final vehicle assembly, ground and flight test, and recovery in "
        "Greenville, Texas. Its raw carbon-composite tank and tube structures are made by Scorpius Space "
        "Launch Company in Torrance, California. Exos starts a build only on a signed order and deposit.",
        ("table", ["Item", "Exos term"], [
            ["Dedicated BLK3 vehicle", "$5.0M per ordered vehicle. Under the recommended option, Exos carries "
             "the loss risk on each vehicle’s first (“Pathfinder”) flight."],
            ["Payment milestones (per vehicle)", "50% on order · 25% at half-build · 10% when tested and "
             "ready for flight · 15% at the Pathfinder flight"],
            ["Flight operations", "$100,000 per flight, plus an Annual Operating Fee set each year in line "
             "with Exos’s annual operating budget"],
            ["Range, site, mobilization, logistics", "Passed through at actual cost at any site. Not "
             "included in the vehicle price or the per-flight fee."],
            ["Payload capacity (reference)", "$7,500/kg (about $1.01M for a full 135 kg bay)"],
            ["Launch liability insurance", "Carried by Exos as the licensed operator, as the launch license "
             "requires"],
            ["Vehicle (hull) insurance after the Pathfinder flight", "Optional, at Copernic’s election and "
             "cost. Copernic carries the loss risk after the Pathfinder flight."],
        ]),
        "Payload, branded-cargo, sponsorship and asset-participation revenue on Copernic’s vehicles belongs "
        "to Copernic, and so does the commercial risk. Exos makes no representation about Copernic’s pricing "
        "to its customers or investors, about mission revenue, or about the value of any tokenized or "
        "certified cargo.",
    ]),
    ("4.  Production Responsibilities", [
        ("table", ["Party", "Responsibility"], [
            ["Exos Aerospace (U.S.)", "Vehicle design, manufacture, integration and test; FAA licensing and "
             "launch operations; flight safety; launch liability insurance; sole control of the vehicle and "
             "its technical data."],
            ["Copernic Space / Lady Rocket", "Program origination and capital; the Lady Rocket brand and "
             "livery design; branded cargo, sponsorships and customer contracts; cargo certification, "
             "registration and tokenization, all on Copernic’s own account; optional hull insurance after "
             "the Pathfinder flight."],
            ["Italian industrial partner (not yet contracted)", "Work outside export control, such as ground "
             "facilities, cargo and payload processing, livery and finishing, sponsor and cultural "
             "programming, and development of local suppliers for items that are not controlled. Any "
             "assembly, testing or supply of controlled vehicle items happens only after the U.S. "
             "Government authorizations described in Section 6."],
        ]),
        "Exos has engaged with Avio, T4i, SITAEL and Leonardo on potential participation in the program. No "
        "contracts have been signed with any of them. Any such participation needs a separate definitive "
        "agreement with Exos.",
    ]),
    ("5.  Schedule and Brand Rights", [
        "Schedule. Each vehicle follows the same milestones: order and deposit, then build start, "
        "half-build, test and flight readiness, and the Pathfinder flight. Build duration is "
        "estimated at 12 months from order and deposit, to be confirmed at the time of order. Firm delivery "
        "dates are set in the definitive agreement when a vehicle is ordered. BLK3 commercial service is targeted for early 2027.",
        "Brand rights. The Lady Rocket brand, including its F1-inspired livery line, belongs to Copernic. "
        "Exos will apply Lady Rocket livery to vehicles Copernic orders. Exos remains identified as "
        "manufacturer and operator (“BLK3 by Exos Aerospace”) and keeps all rights to its name, marks, "
        "vehicle design and technology. This statement may be included in Copernic’s materials as written. "
        "Any other use of Exos’s name, marks or imagery, including AI-generated renderings, requires an "
        "approved brand-use addendum.",
    ]),
    ("6.  Italy — Assembly and Sardinia Launch Pathway", [
        "The BLK3 vehicle and its technical data are subject to U.S. export controls (ITAR/EAR). The "
        "following all require prior U.S. Government authorization, which Exos arranges (DDTC/BIS, "
        "including a Technical Assistance Agreement where it applies):",
        ("bullets", [
            "Italian assembly, testing or supply of controlled items",
            "Access by any foreign person to the vehicle or to controlled data",
            "Any launch from Sardinia or another non-U.S. site",
        ]),
        "A Sardinia launch also requires the applicable Italian authorizations. Exos stays the licensed "
        "operator and controller of the vehicle at all times.",
        "Exos Aerospace Italia, Srl (Torino) is an Exos affiliate and is not currently operating. Any role "
        "it takes in the program is Exos’s decision and is subject to the authorizations above.",
        "A Sardinia launch program is at the letter-of-intent stage. It is not a committed capability.",
    ]),
    ("7.  Nature of the Relationship", [
        "Copernic is an Exos customer. The program is a customer wet lease: Copernic orders and pays for "
        "dedicated BLK3 vehicles, and Exos builds and operates them under the Wet Lease. It is not a "
        "financing of Exos, and Exos is not a party to, sponsor of, or co-investor in any capital Copernic "
        "raises for its own program. No equity, ownership or control of Exos Aerospace Systems & "
        "Technologies, Inc. or Exos Aerospace Italia, Srl is offered or implied. Copernic is not authorized "
        "to bind Exos on vehicle price, quantity or schedule.",
    ]),
    ("8.  Status", [
        "This statement is non-binding. Exos’s commitments become binding only under a signed definitive "
        "agreement with a deposit received, and, for any Italian or foreign element, the authorizations in "
        "Section 6. Contact: John Quinn, Cofounder and CEO, jquinn@exosaero.com.",
    ]),
]

SIGNER = ["Exos Aerospace Systems & Technologies, Inc.", "", "_______________________________________",
          "John Quinn", "Cofounder and Chief Executive Officer",
          "299 FM 1903, Greenville, TX 75402", "Date: ______________________"]
