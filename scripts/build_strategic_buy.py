#!/usr/bin/env python3
"""build_strategic_buy.py — Strategic Buy / competitive-RFQ package generator for Exos BOMs.

Turns the BLK3 + HVRR BOMs into a competitive sourcing workbook: parts are clustered into
commodity BUY GROUPS, identical parts are AGGREGATED across programs (buy once, more volume =
better price), and each group gets a 3-supplier quote-comparison grid (primary + the two qualified
backups from the dual/tri-source pass) so procurement can run one RFQ per group and award the
lowest qualified bid.

Usage: python3 scripts/build_strategic_buy.py            # combined BLK3+HVRR -> EXOS_Strategic_Buy_<date>.xlsx
"""
import openpyxl, os, re, collections, datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOMS = {"BLK3": "mission-control/uploads/1787343333564_BLK3_BOM_8-21-2026.xlsx",
        "HVRR": "mission-control/uploads/1787344060367_HVRR_BOM_8-21-2026.xlsx"}
OUT = os.path.join(WS, "mission-control", "uploads",
                   f"EXOS_Strategic_Buy_BLK3-HVRR_{datetime.date.today():%Y-%m-%d}.xlsx")

MERGE = {"pasternak":"Pasternack","pasterknack":"Pasternack","mouser`":"Mouser","morga newton":"Morgan Newton",
         "swaglok":"Swagelok","mcmaster":"McMaster-Carr","digi-key":"DigiKey","diamond sys":"Diamond Systems"}
def canon(v):
    if not v: return ""
    return MERGE.get(v.strip().lower(), v.strip())

# buy group -> (primary-vendor matchers, [3 recommended bidders])
GROUPS = [
 ("MRO · Fasteners · Raw Stock", ["mcmaster","msc","grainger","pipingnow","military fastner","metals","dix","radwell"],
     ["McMaster-Carr", "Grainger", "MSC Industrial"]),
 ("Electronic Components", ["digikey","mouser","arrow","heilind","allied electronics","pei-genesis","pei genisis"],
     ["DigiKey", "Mouser", "Newark (element14)"]),
 ("RF & Microwave", ["pasternack","shireen","fairview","l-com"],
     ["Pasternack", "Fairview Microwave", "L-com"]),
 ("Fluid Systems · Valves · Fittings · Regulators", ["swagelok","parker","gems","aqua environments","midwest hose","ratermann","chemiquip"],
     ["Swagelok", "Parker (Ham-Let)", "ASCO/Tescom (Emerson)"]),
 ("Composite Structures", ["scorpius","sslc","cdt","composite technology","jp composites","infinite composites"],
     ["Scorpius (affiliate)", "Infinite Composites Technologies", "Composite Technology Development (CTD)"]),
 ("Machining & Fabrication", ["avco","morgan newton","lee hardesty","ub corp","csr","sharpe","invest cast","desgnatronics"],
     ["Xometry", "Protolabs", "Incumbent shop (qualify)"]),
 ("Avionics · Sensors · GNSS", ["emcore","javad","teklab","diamond systems","navtechgps","byonics","business systems"],
     ["Incumbent (EMCORE/JAVAD)", "VectorNav / NovAtel", "SBG / Septentrio"]),
 ("Actuation & Motion", ["ultramotion"],
     ["Ultramotion", "Thomson (Regal Rexnord)", "Moog"]),
 ("Aircraft & Racing Hardware", ["aircraft spruce","summit racing"],
     ["Aircraft Spruce", "Wicks Aircraft", "Chief Aircraft / Jegs"]),
 ("Recovery · Textiles · Firesleeve", ["wamore","paragear","offray","bally ribbon","american firesleeve"],
     ["Incumbent (WAMORE/Airborne)", "Bally Ribbon / Murdock Webbing", "Techflex"]),
 ("Metals & Titanium", ["performance titanium","the trident company","trident metals"],
     ["TMS Titanium", "Titanium Industries", "Online Metals"]),
 ("Batteries & Hobby", ["rcbattery","hobbytown","hobby town"],
     ["RCBattery", "HobbyKing", "MaxAmps / Tower Hobbies"]),
]
def group_of(vendor):
    v = vendor.lower()
    for name, matchers, bidders in GROUPS:
        if any(m in v for m in matchers):
            return name, bidders
    return "Other · Misc / To-Categorize", ["(assign)", "(assign)", "(assign)"]

INTERNAL = re.compile(r'^(exos|machining|fabrication|welding|weld|assembly|assy|labor|in.?house|multiple|\?+|http|www\.)', re.I)

def load_lines():
    agg = collections.OrderedDict()  # key (group, vendor, vpn, desc) -> {qty, cost, ext, progs}
    for prog, rel in BOMS.items():
        wb = openpyxl.load_workbook(os.path.join(WS, rel), data_only=True)
        for sn in wb.sheetnames:
            if sn.lower().endswith("top level"): continue
            ws = wb[sn]; rows = [[c.value for c in r] for r in ws.iter_rows()]
            hdr = None
            for i, r in enumerate(rows):
                j = " ".join(str(x).strip().lower() if x else "" for x in r)
                if "vendor" in j and "description" in j: hdr = i; break
            if hdr is None: continue
            H = [str(x).strip().lower() if x else "" for x in rows[hdr]]
            def col(exact=None, part=None):
                for k, h in enumerate(H):
                    if exact and h == exact: return k
                    if part and part in h and h != "vendor p/n": return k
                return None
            c_ven = col(exact="vendor"); c_desc = col(part="description"); c_qty = col(part="quantity")
            c_vpn = col(part="vendor p/n") or col(exact="vendor p/n"); c_cost = col(part="cost ea")
            if c_ven is None: continue
            for r in rows[hdr+1:]:
                def g(c): return ("" if (c is None or c >= len(r) or r[c] is None) else str(r[c]).strip())
                ven = canon(g(c_ven)); desc = g(c_desc)
                if not ven or INTERNAL.match(ven) or not desc: continue
                try: qty = float(str(g(c_qty)).replace(",", "")) if g(c_qty) and g(c_qty).replace('.','').isdigit() else (1 if g(c_qty) else 0)
                except: qty = 0
                try: cost = float(str(g(c_cost)).replace(",", "")) if g(c_cost) else 0
                except: cost = 0
                grp, bidders = group_of(ven)
                key = (grp, ven, g(c_vpn), desc[:60])
                a = agg.setdefault(key, {"grp": grp, "bidders": bidders, "vendor": ven, "vpn": g(c_vpn),
                                         "desc": desc, "qty": 0, "cost": cost, "progs": set()})
                a["qty"] += qty; a["progs"].add(prog)
                if cost: a["cost"] = cost
    return list(agg.values())

# ---- styling ----
NAVY = "0b2a4a"; LT = "eef3f9"; RED = "c8102e"
HF = PatternFill("solid", fgColor=NAVY); HL = PatternFill("solid", fgColor=LT)
WHF = Font(bold=True, color="FFFFFF"); BF = Font(bold=True, color=NAVY)
THIN = Border(*[Side(style="thin", color="c9d2dd")] * 4)

def build():
    lines = load_lines()
    by_group = collections.defaultdict(list)
    for a in lines: by_group[a["grp"]].append(a)
    wb = openpyxl.Workbook()

    # ── Instructions ──
    ins = wb.active; ins.title = "Instructions"
    ins["A1"] = "EXOS AEROSPACE — Strategic Buy / Competitive RFQ Package"; ins["A1"].font = Font(bold=True, size=15, color=NAVY)
    ins["A2"] = f"BLK3 + HVRR BOMs · generated {datetime.date.today():%b %d, %Y}"; ins["A2"].font = Font(italic=True, color="606a78")
    steps = [
        "", "How to run the competitive buy:",
        "1. Each tab is a BUY GROUP (a commodity family). Identical parts are aggregated across BLK3 + HVRR — buy once, more volume, better price.",
        "2. Send the group's line list to the 3 qualified suppliers named at the top of each tab (primary + the two DIB-qualified backups).",
        "3. Enter each supplier's unit quote in its column. 'Low Quote', 'Award To', and 'Savings vs Baseline' auto-compute.",
        "4. Award to the lowest qualified bid. Confirm backups' supplier DD is GREEN before award (Gov/DIB Readiness Register).",
        "5. Baseline $ = current BOM cost. Savings roll up on the Summary tab.",
        "", "Only qualified (DD-cleared) suppliers should be solicited. Machining/fab and 'Other' groups need a buyer to confirm the alternate before RFQ.",
    ]
    for i, s in enumerate(steps, start=3):
        ins[f"A{i}"] = s
        if s.endswith(":"): ins[f"A{i}"].font = BF
    ins.column_dimensions["A"].width = 130

    # ── Summary ──
    su = wb.create_sheet("Buy Group Summary")
    su.append(["Buy Group", "Unique Parts", "Baseline Ext $", "Recommended Bidders (RFQ to)", "", ""])
    for c in range(1, 7): su.cell(1, c).fill = HF; su.cell(1, c).font = WHF
    tot = 0
    for grp, items in sorted(by_group.items(), key=lambda kv: -sum(i["qty"]*i["cost"] for i in kv[1])):
        base = sum(i["qty"] * i["cost"] for i in items); tot += base
        b = items[0]["bidders"]
        su.append([grp, len(items), round(base, 2), b[0], b[1], b[2]])
    su.append(["TOTAL", sum(len(v) for v in by_group.values()), round(tot, 2), "", "", ""])
    for c in range(1, 4): su.cell(su.max_row, c).font = BF
    for w, col in zip([44, 12, 16, 26, 26, 26], "ABCDEF"): su.column_dimensions[col].width = w

    # ── one tab per group ──
    HEAD = ["Item", "Qty (BLK3+HVRR)", "Programs", "Vendor P/N", "Description", "Baseline Vendor", "Baseline $ ea",
            "Baseline Ext $", "", "", "", "Low Quote", "Award To", "Savings vs Baseline"]
    for grp, items in sorted(by_group.items()):
        title = re.sub(r'[^A-Za-z0-9 ]', '', grp)[:28] or "Group"
        ws = wb.create_sheet(title)
        b = items[0]["bidders"]
        ws["A1"] = grp; ws["A1"].font = Font(bold=True, size=13, color=NAVY)
        ws["A2"] = "RFQ to (qualified suppliers):"; ws["A2"].font = BF
        ws["C2"] = f"1) {b[0]}    2) {b[1]}    3) {b[2]}"
        ws["A3"] = "RFQ issued:"; ws["C3"] = "____________"; ws["E3"] = "Quotes due:"; ws["G3"] = "____________"
        hdr = 5
        head = HEAD[:]
        head[8], head[9], head[10] = f"{b[0]} $ea", f"{b[1]} $ea", f"{b[2]} $ea"
        ws.append([]) ; ws.append([]) ; ws.append([]) ; ws.append([])  # pad to row 5
        for c, h in enumerate(head, start=1):
            cell = ws.cell(hdr, c, h); cell.fill = HF; cell.font = WHF; cell.alignment = Alignment(wrap_text=True, vertical="center")
        r = hdr + 1
        for it in sorted(items, key=lambda x: -(x["qty"] * x["cost"])):
            ws.cell(r, 1, r - hdr)
            ws.cell(r, 2, round(it["qty"], 2)); ws.cell(r, 3, "+".join(sorted(it["progs"])))
            ws.cell(r, 4, it["vpn"]); ws.cell(r, 5, it["desc"][:80]); ws.cell(r, 6, it["vendor"])
            ws.cell(r, 7, it["cost"]); ws.cell(r, 8, f"=B{r}*G{r}")
            # supplier quote cols I,J,K (9,10,11) left blank for entry
            ws.cell(r, 12, f'=IFERROR(MIN(I{r}:K{r}),"")')                    # Low Quote
            ws.cell(r, 13, f'=IFERROR(INDEX($I$%d:$K$%d,1,MATCH(L{r},I{r}:K{r},0)),"")' % (hdr+1, r) if False else "")  # award (manual)
            ws.cell(r, 14, f'=IF(L{r}="","",(G{r}-L{r})*B{r})')              # savings
            for c in range(1, 15): ws.cell(r, c).border = THIN
            r += 1
        # totals
        ws.cell(r, 6, "GROUP TOTAL").font = BF
        ws.cell(r, 8, f"=SUM(H{hdr+1}:H{r-1})").font = BF
        ws.cell(r, 14, f"=SUM(N{hdr+1}:N{r-1})").font = BF
        for w, col in zip([6, 12, 10, 20, 46, 18, 11, 13, 13, 13, 13, 11, 16, 15], "ABCDEFGHIJKLMN"):
            ws.column_dimensions[col].width = w
        ws.freeze_panes = f"A{hdr+1}"
    wb.save(OUT)
    return OUT, by_group, sum(sum(i["qty"]*i["cost"] for i in v) for v in by_group.values())

if __name__ == "__main__":
    out, groups, tot = build()
    print("wrote:", out)
    print(f"buy groups: {len(groups)} | unique aggregated parts: {sum(len(v) for v in groups.values())} | baseline spend: ${tot:,.0f}")
    for g, items in sorted(groups.items(), key=lambda kv:-sum(i['qty']*i['cost'] for i in kv[1])):
        print(f"  {g:46s} {len(items):4d} parts  ${sum(i['qty']*i['cost'] for i in items):>12,.0f}")
