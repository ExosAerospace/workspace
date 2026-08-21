#!/usr/bin/env python3
"""bom_dual_source.py — DIB supply-chain dual/tri-sourcing for the BLK3 & HVRR BOMs.

For each purchased line, add a qualified SECONDARY and TERTIARY backup supplier (commodity lines
inherit their distributor's equivalents; critical/specialized parts get targeted aerospace-grade
alternates). Writes two new columns into every detail sheet of each BOM, and emits the unique list
of NEW backup suppliers to load into the CRM + run through supplier DD.

Usage: python3 scripts/bom_dual_source.py         (updates BOM copies in mission-control/uploads, writes /tmp/new_suppliers.txt)
"""
import openpyxl, json, os, re, collections
from openpyxl.styles import Font, PatternFill

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOMS = {
    "BLK3": "mission-control/uploads/1787343333564_BLK3_BOM_8-21-2026.xlsx",
    "HVRR": "mission-control/uploads/1787344060367_HVRR_BOM_8-21-2026.xlsx",
}
# normalize the vendor-spelling drift so every line maps
MERGE = {
    "pasternak": "Pasternack", "pasterknack": "Pasternack", "pasternack": "Pasternack",
    "mouser`": "Mouser", "mouser": "Mouser", "morga newton": "Morgan Newton", "morgan newton": "Morgan Newton",
    "swaglok": "Swagelok", "swagelok": "Swagelok", "swagelock - texas valve and fitting": "Swagelok - Texas Valve and Fitting",
    "swagelok - texas valve and fitting": "Swagelok - Texas Valve and Fitting",
    "pei genisis": "PEI-Genesis", "pei-genesis": "PEI-Genesis", "hobby town": "HobbyTown", "hobbytown": "HobbyTown",
    "trident metals": "The Trident Company", "the trident company": "The Trident Company",
    "diamond sys": "Diamond Systems", "diamond systems": "Diamond Systems", "mcmaster": "McMaster-Carr",
    "mcmaster-carr": "McMaster-Carr", "digi-key": "DigiKey", "digikey": "DigiKey",
    "ratermann at www.rmiorder.com": "Ratermann (RMI)", "ratermann (rmi)": "Ratermann (RMI)",
    "scorpius": "Scorpius (affiliate)", "sslc": "SSLC (affiliate)",
}
# secondary / tertiary backups. [secondary, tertiary, confidence]
BK = {
    # ---- electronics distributors (drop-in equivalents) ----
    "DigiKey": ["Mouser", "Newark (element14)", "high"],
    "Mouser": ["DigiKey", "Newark (element14)", "high"],
    "ARROW": ["Avnet", "Future Electronics", "high"],
    "Heilind": ["Mouser", "DigiKey", "high"],
    "Allied Electronics": ["Newark (element14)", "RS Components", "high"],
    "PEI-Genesis": ["Mouser", "Powell Electronics", "high"],
    "Business Systems Connections": ["CDW", "Insight Enterprises", "low"],
    # ---- industrial / MRO distributors ----
    "McMaster-Carr": ["Grainger", "MSC Industrial", "high"],
    "MSC": ["Grainger", "Fastenal", "high"],
    "Radwell": ["Grainger", "Newark (element14)", "med"],
    "PIPINGNOW": ["McMaster-Carr", "Grainger", "high"],
    # ---- metals ----
    "Dix Metals": ["Online Metals", "Metal Supermarkets", "med"],
    "Metals (Bralco/Castle/Supermarket)": ["Online Metals", "TW Metals", "high"],
    "The Trident Company": ["Online Metals", "Metal Supermarkets", "med"],
    "Performance Titanium Group": ["TMS Titanium", "Titanium Industries", "high"],
    # ---- fasteners / hardware ----
    "Military Fastners": ["Aircraft Spruce", "Wicks Aircraft", "high"],
    "Aircraft Spruce": ["Wicks Aircraft Supply", "Chief Aircraft", "high"],
    # ---- fluid systems / valves / fittings / regulators ----
    "Swagelok": ["Parker (Ham-Let)", "Ideal Vacuum", "high"],
    "Swagelok - Texas Valve and Fitting": ["Parker (Ham-Let)", "Ideal Vacuum", "high"],
    "Parker": ["Swagelok", "Eaton Aerospace", "high"],
    "Gems Predyne": ["Parker (Skinner)", "ASCO (Emerson)", "med"],
    "Aqua Environments": ["TESCOM (Emerson)", "GO Regulator (Circor)", "med"],
    "Ratermann (RMI)": ["Airgas", "Harris Products", "med"],
    "MIDWEST HOSE & SPECIALTY, INC": ["Parker Hose Products", "Gates Aerospace", "med"],
    "Chemiquipproducts.com": ["Peter Paul Electronics", "ASCO (Emerson)", "low"],
    "AVCO": ["Xometry", "Protolabs", "low"],
    # ---- RF / microwave / GPS ----
    "Pasternack": ["Fairview Microwave", "L-com", "high"],
    "www.shireeninc.com": ["Pasternack", "L-com", "med"],
    "NavtechGPS": ["Tallysman", "Harxon", "med"],
    # ---- racing / auto (AN fittings, nitrous, plumbing) ----
    "Summit Racing": ["Jegs", "Pegasus Auto Racing", "high"],
    # ---- recovery / parachute / webbing / firesleeve ----
    "WAMORE": ["Airborne Systems", "Roberts Research Lab (Vertigo)", "med"],
    "Paragear": ["Rock Sky Market", "Para Gear alt (Aerostar)", "med"],
    "Offray": ["Bally Ribbon Mills", "Murdock Webbing", "high"],
    "Bally Ribbon Mills": ["Murdock Webbing", "Offray", "high"],
    "American Firesleeve": ["Techflex", "Aero-Flite (Firesleeve.com)", "med"],
    # ---- sensors / IMU / GNSS / avionics ----
    "EMCORE": ["VectorNav Technologies", "SBG Systems (Honeywell)", "high"],
    "JAVAD": ["NovAtel (Hexagon)", "Septentrio", "high"],
    "Teklab": ["Gems Sensors", "TE Connectivity", "med"],
    "Byonics": ["Argent Data Systems", "BigRedBee", "high"],
    # ---- rugged computing / I/O ----
    "Diamond Systems": ["WinSystems", "VersaLogic", "high"],
    # ---- actuation / motion ----
    "Ultramotion": ["Thomson (Regal Rexnord)", "Moog", "high"],
    # ---- precision gears / mechanical ----
    "Desgnatronics Inc.": ["SDP/SI (Stock Drive Products)", "Boston Gear", "med"],
    # ---- castings / composites / machining / fab ----
    "Invest Cast": ["Signicast (Form Technologies)", "Aristo Cast", "med"],
    "Morgan Newton": ["Screaming Circuits (Milwaukee Elec)", "Advanced Assembly", "low"],
    "Lee Hardesty": ["Xometry", "Protolabs", "low"],
    "JP Composites": ["Rock West Composites", "CST Composites", "med"],
    "Sharpe Products": ["Xometry", "Protolabs", "med"],
    "UB Corp": ["Xometry", "Protolabs", "low"],
    "CSR": ["Xometry", "Protolabs", "low"],
    # ---- batteries / hobby / misc ----
    "RCBattery": ["HobbyKing", "MaxAmps", "high"],
    "HobbyTown": ["Tower Hobbies", "Amazon Business", "high"],
    # ---- affiliates (related-party; alternates listed for supply-chain resilience only) ----
    "Scorpius (affiliate)": ["Infinite Composites Technologies", "Composite Technology Development (CTD)", "affiliate"],
    "SSLC (affiliate)": ["Infinite Composites Technologies", "ARDE Inc.", "affiliate"],
}


def canon(v):
    if not v:
        return ""
    return MERGE.get(v.strip().lower(), v.strip())


def main():
    new_suppliers = collections.Counter()
    HDR_FILL = PatternFill("solid", fgColor="0b2a4a")
    for prog, rel in BOMS.items():
        f = os.path.join(WS, rel)
        wb = openpyxl.load_workbook(f)
        touched = 0
        for sn in wb.sheetnames:
            if sn.lower().endswith("top level"):
                continue
            ws = wb[sn]
            # locate header row + Vendor column
            hdr_row = ven_col = None
            for r in range(1, min(ws.max_row, 6) + 1):
                vals = [str(ws.cell(r, c).value).strip().lower() if ws.cell(r, c).value else "" for c in range(1, ws.max_column + 1)]
                if "vendor" in vals and "description" in vals:
                    hdr_row = r
                    ven_col = vals.index("vendor") + 1
                    break
            if not hdr_row:
                continue
            # insert two columns right after Vendor
            ws.insert_cols(ven_col + 1, 2)
            ws.cell(hdr_row, ven_col + 1, "Secondary Supplier")
            ws.cell(hdr_row, ven_col + 2, "Tertiary Supplier")
            for cc in (ven_col + 1, ven_col + 2):
                ws.cell(hdr_row, cc).font = Font(bold=True, color="FFFFFF")
                ws.cell(hdr_row, cc).fill = HDR_FILL
            # fill each line
            for r in range(hdr_row + 1, ws.max_row + 1):
                raw = ws.cell(r, ven_col).value
                v = canon(raw)
                if not v or v not in BK:
                    continue
                sec, ter = BK[v][0], BK[v][1]
                ws.cell(r, ven_col + 1, sec)
                ws.cell(r, ven_col + 2, ter)
                touched += 1
                new_suppliers[sec] += 1
                new_suppliers[ter] += 1
        wb.save(f)
        print(f"{prog}: wrote Secondary/Tertiary on {touched} lines -> {rel}")
    # emit unique NEW backup suppliers (for CRM + DD), skip affiliates already known
    uniq = sorted(new_suppliers)
    open("/tmp/new_suppliers.txt", "w").write("\n".join(uniq))
    print(f"\nunique NEW backup suppliers to add to CRM + DD: {len(uniq)}")
    for s in uniq:
        print("  ", s, f"({new_suppliers[s]} lines)")


if __name__ == "__main__":
    main()
