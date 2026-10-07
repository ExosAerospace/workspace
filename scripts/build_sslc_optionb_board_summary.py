#!/usr/bin/env python3
"""Build Exos_SSLC_OptionB_Offer_Summary_2026-10-07.docx + .pdf on Exos PRIMARY letterhead.
2-page board-ready summary of the SSLC Option B acquisition offer.
Jon Quinn, CEO — INTERNAL / DRAFT — negotiating terms
"""
import os, sys, subprocess, shutil
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

WS   = "/Users/exomac/.openclaw/workspace"
TMPL = os.path.join(WS, "assets", "EXOS_Letterhead_Greenville_TX_PRIMARY.docx")
RAW  = os.path.join(WS, "drafts", "_sslc_optionb_raw.docx")
OUT  = os.path.join(WS, "drafts", "Exos_SSLC_OptionB_Offer_Summary_2026-10-07.docx")
PDF  = os.path.join(WS, "drafts", "Exos_SSLC_OptionB_Offer_Summary_2026-10-07.pdf")

NAVY  = RGBColor(0x1F, 0x3A, 0x68)
BLUE  = RGBColor(0x2E, 0x75, 0xB6)
BLACK = RGBColor(0x0,  0x0,  0x0)
RED   = RGBColor(0xC0, 0x00, 0x00)

shutil.copy(TMPL, RAW)
doc = Document(RAW)
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(10)

# --- helpers -----------------------------------------------------------------
def add_para(text="", bold=False, size=None, color=None, italic=False,
             space_after=4, space_before=0, indent=None, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after  = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    if indent:
        p.paragraph_format.left_indent = Inches(indent)
    if align:
        p.alignment = align
    if text:
        r = p.add_run(text)
        r.bold   = bold
        r.italic = italic
        if size:  r.font.size      = Pt(size)
        if color: r.font.color.rgb = color
    return p

def head1(text, space_before=6):
    p = add_para(text, bold=True, size=12, color=NAVY,
                 space_after=3, space_before=space_before)
    p.paragraph_format.keep_with_next = True

def head2(text):
    p = add_para(text, bold=True, size=10.5, color=BLUE, space_after=2, space_before=4)
    p.paragraph_format.keep_with_next = True

def body(text, indent=None):
    add_para(text, size=10, space_after=3, indent=indent)

def bullet(lead, rest="", indent=0.2):
    p = add_para(space_after=2, indent=indent)
    p.add_run("•  ")
    if lead:
        r = p.add_run(lead); r.bold = True
    if rest:
        p.add_run(rest)

def note(text):
    add_para(text, size=9, italic=True, color=RGBColor(0x60,0x60,0x60), space_after=2)

def add_table(rows_data, col_widths, header_bg=True):
    t = doc.add_table(rows=len(rows_data), cols=len(rows_data[0]))
    try:
        t.style = "Table Grid"
    except Exception:
        try:
            t.style = "TableNormal"
        except Exception:
            pass
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), col_widths):
        gc.set(qn("w:w"), str(int(w * 1440)))
    for i, row in enumerate(rows_data):
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.width = Inches(col_widths[j])
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(str(val) if val is not None else "")
            r.font.size = Pt(9)
            if i == 0 and header_bg:
                r.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                from docx.oxml import OxmlElement
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "1F3A68")
                tcPr.append(shd)
            elif j == 0 and i > 0:
                r.font.size = Pt(9)
    add_para(space_after=4)
    return t

# --- remove template leading empties ----------------------------------------
body_el = doc.element.body
for child in list(body_el):
    if child.tag == qn("w:p"):
        has_text = any((t.text or "").strip() for t in child.findall(".//" + qn("w:t")))
        has_gfx  = child.findall(".//" + qn("w:drawing")) or child.findall(".//" + qn("w:pict"))
        if not has_text and not has_gfx:
            body_el.remove(child)
        else:
            break

# =============================================================================
# PAGE 1
# =============================================================================
add_para("INTERNAL — DRAFT — NEGOTIATING TERMS — CEO eyes only",
         size=8, italic=True, color=RGBColor(0x80,0x00,0x00), space_after=2)

add_para("EXOS AEROSPACE — SSLC OPTION B ACQUISITION OFFER",
         bold=True, size=14, color=NAVY, space_after=2, space_before=4,
         align=WD_ALIGN_PARAGRAPH.CENTER)
add_para("Board Decision Summary · October 7, 2026",
         size=10, italic=True, color=BLUE, space_after=6,
         align=WD_ALIGN_PARAGRAPH.CENTER)

# --- Executive Summary -------------------------------------------------------
head1("EXECUTIVE SUMMARY", space_before=4)
body("Jon Quinn (CEO) has directed Exos to proceed with Option B: invoke §3 exclusivity of the "
     "May 2025 Asset Acquisition Agreement at the 2025 board-approved price, with an earn-out "
     "tied to Intuitive Machines (IM) tank deliveries and/or listed Exos stock post-RTO. Scorpius "
     "Space Launch Company (SSLC) debts are paid at face value at close, providing Jim Wertz's "
     "personal path to yes. This is separate from the ROFR the board declined; it proceeds on "
     "the signed, board-approved §3 exclusivity trigger.")

head1("DEAL TERMS (Option B)", space_before=6)
terms = [
    ["Component",                           "Amount",           "Notes"],
    ["Base acquisition price",              "$3,360,000",       "§3 / §1 price; cash + stake credit"],
    ["  Cash at close",                     "$2,510,000",       "Exos cash; from Series A first close"],
    ["  SSLC costs",                        "$60,000",          "Seller's costs (§3)"],
    ["  Exos stake credit (18%)",           "($790,000)",       "Non-cash; existing 18% equity at 2021 basis"],
    ["5% escrow holdback (§7, 12 mo.)",     "$168,000",         "Released at 12-month anniversary"],
    ["SSLC debts assumed at face",          "~$500K (TBV)",     "Microcosm/Wertz notes + AP — to verify in SSLC QB"],
    ["Earn-out i: IM tank revenue",         "5% of rev, $300K cap/yr, 3 yrs", "Low/Base/High: $450K / $750K / $900K"],
    ["Earn-out ii: Exos stock post-RTO",    "0.5% of FD shares, 12-mo lockup", "Low/Base/High: $600K / $1.25M / $2.1M"],
    ["TOTAL CONSIDERATION (Base, combined)","$5,860,000",       "Low: $4.91M | Base: $5.86M | High: $6.86M"],
]
add_table(terms, [2.2, 1.8, 2.7])
note("TBV = to be verified in SSLC QuickBooks (QB session expired 10/7; must verify before signing).")

# --- Financial Summary -------------------------------------------------------
head1("1-YEAR AND 5-YEAR HEADLINE NUMBERS (Exos + SSLC Consolidated)", space_before=4)
note("All figures management assumptions. Exos standalone from v15 commission-only baseline. SSLC FY27 "
     "IM tanks $5M confirmed by Markus Rufer (10/2). Post-acquisition: 15% commission eliminated as intercompany.")

fin = [
    ["Metric",                       "FY27 (Year 1)",  "FY31 (Year 5)",  "Notes"],
    ["SSLC Revenue",                 "$5,500,000",     "$16,500,000",    "IM tanks $5M firm + $0.5M other FY27"],
    ["Exos Standalone Revenue",      "$2,600,000",     "$16,000,000",    "v15 baseline excl. SSLC commission"],
    ["Net Consolidated Revenue",     "$7,600,000",     "$31,600,000",    "After intercompany elimination ($500K FY27)"],
    ["SSLC EBITDA",                  "+$1,240,000",    "+$6,015,000",    "Positive from close; accretive to Exos"],
    ["Exos Standalone EBITDA",       "−$4,000,000",    "+$5,000,000",    "BLK3 investment phase FY27; improving FY28+"],
    ["Consolidated EBITDA",          "−$2,760,000",    "+$11,015,000",   "Exos development costs dominate FY27"],
    ["v15 Benchmark SSLC revenue",   "$900,000",       "$21,000,000",    "Old acquisition model; Option B FY27 ×6.1×"],
    ["Cash need at close",           "$3,010,000",     "—",              "Acquisition $2.51M + WC bridge $0.5M"],
    ["Series A first close",         "$10,000,000",    "—",              "Covers acquisition, WC bridge, and Exos ops"],
    ["Net remaining for Exos ops",   "$6,990,000",     "—",              "After SSLC cash deployment"],
]
add_table(fin, [2.2, 1.5, 1.5, 1.5])

# =============================================================================
# PAGE 2
# =============================================================================
doc.add_page_break()

head1("EARN-OUT OPTIONS (Two Variants; Combined Recommended)", space_before=4)
eo = [
    ["",              "Earn-Out i: IM Tank Revenue",      "Earn-Out ii: Exos Stock",         "Combined"],
    ["Structure",     "% of SSLC IM hardware revenue",    "Exos common stock at listing",    "Both i + ii"],
    ["Mechanics",     "5% annual, $300K cap, 3-year term","0.5% of FD shares; 12-mo lockup", "Each on own schedule"],
    ["Low",           "$450,000",                          "$600,000",                        "$1,050,000"],
    ["Base",          "$750,000",                          "$1,250,000",                      "$2,000,000"],
    ["High",          "$900,000",                          "$2,100,000",                      "$3,000,000"],
    ["Dilution",      "None",                              "~0.5% of FD shares",              "~0.5% — non-material"],
    ["Rationale",     "Rewards SSLC sellers for IM growth they enabled", "Aligns SSLC sellers with Exos upside post-RTO", "Best protection for all parties"],
]
add_table(eo, [1.3, 1.9, 1.9, 1.6])

head1("RISKS AND MITIGATIONS", space_before=6)

head2("§3 Trigger Gap")
bullet("Risk: ", "FNEX/Ainigma is an advisor/broker-dealer, not itself an 'investor or lender'. SSLC counsel (Danny) may challenge the trigger.")
bullet("Mitigation: ", "Attach countersigned FNEX agreement + investor/sponsor use-of-proceeds letter naming the SSLC asset purchase. [Confirm D-7281974 is countersigned.]")

head2("He-Tank Dispute (MC #3056)")
bullet("Risk: ", "Rev3 GHe tank fails at 4,400 psi proof; Morey questions it as a flight article. Exos faces ~$175K to take to flight.")
bullet("Mitigation: ", "Plan B: qualified COPV ≤$250K (Jon cap), $0.3M gap. Resolves cleanly post-acquisition as intercompany — the legal dispute disappears. Decision D-7281994.")

head2("SSLC Cash Risk")
bullet("Risk: ", "SSLC cash at QB date: $198K. Needs $0.3–0.7M to finish $984K in prepaid work. Risk of distress before close.")
bullet("Mitigation: ", "Option C (held): prepaid BLK3 tank PO $300–700K as bridge. OR close quickly before cash depletes.")

head2("Related-Party / Governance")
bullet("Jon Quinn: ", "on both boards. Jon recuses from SSLC board vote; sends as Exos CEO only. Eqvista fairness opinion: engaged 8/14/2026; agreement still unsigned (held ~1 month).")
bullet("Disinterested directors: ", "Markus Rufer and Bob approve on SSLC side; Jon abstains.")

head2("Timing")
bullet("Exclusivity window: ", "90 days from ~Oct 8 = ~Jan 6, 2027. RTO close ~Mar 2027. Request extension proactively under the 'not unreasonably withhold' clause.")
bullet("Jon in Japan: ", "Oct 8 – Oct 29. Named Exos officer signs while away. Reply-by date to Jim/board to be confirmed.")

head1("ASKS — Board Decision Points", space_before=6)

asks = [
    ["#", "Ask",                                                          "Owner",          "Timing"],
    ["1", "DECIDED 10/7: Option B (A+B), Counsel deferred while negotiating","Jon (CEO)",       "Done"],
    ["2", "Confirm earn-out variant: tank-only, stock-only, or combined?","Jon (CEO)",       "Today 10/7"],
    ["3", "Confirm FNEX agreement is countersigned (D-7281974)?",         "Jon",             "Before send"],
    ["4", "Obtain investor use-of-proceeds letter naming SSLC purchase?","Jon + FNEX",      "Before send"],
    ["5", "Name Exos officer to sign while Jon is in Japan?",            "Jon (CEO)",       "Today 10/7"],
    ["6", "Set reply-by date to Jim Wertz?",                             "Jon (CEO)",       "Today 10/7"],
    ["7", "Verify SSLC liabilities in QB before signing?",              "Exo / Jon",       "Before sign"],
]
add_table(asks, [0.3, 2.8, 1.4, 1.2])

add_para("Model file: drafts/EXOS_SSLC_OptionB_Acquisition_Model_2026-10-07.xlsx — all formulas, recalculates on input changes.",
         size=8, italic=True, color=RGBColor(0x50,0x50,0x50), space_after=2)
add_para("Draft message to Wertz/board: see SSLC_Exclusivity_Rescue_Options_and_Draft_Message_2026-10-07_DRAFT_v2.docx.",
         size=8, italic=True, color=RGBColor(0x50,0x50,0x50), space_after=2)
add_para("Decision card for Jon's approval is on Mission Control under task #3544.",
         size=8, italic=True, color=RGBColor(0x50,0x50,0x50), space_after=6)

# =============================================================================
# PAGE 3 — Total Compensation Chart
# =============================================================================
doc.add_page_break()

head1("TOTAL COMPENSATION — 5-YEAR VIEW (FY27–FY31)", space_before=4)
note("Stacked bar: funding delivered at close + forward potential (earn-outs). Base scenario shown; "
     "stock earn-out whiskers show low/high range. "
     "negotiating terms — management assumptions; SSLC debt unverified.")

# Embed chart image
CHART_PNG = os.path.join(WS, "drafts", "SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png")
if os.path.exists(CHART_PNG):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run()
    run.add_picture(CHART_PNG, width=Inches(6.2))
else:
    add_para("[Chart not yet generated — run scripts/build_sslc_total_comp_chart.py first]",
             italic=True, color=RED, size=9)

head2("5-Year Total Compensation Summary")
comp_table = [
    ["Scenario",       "Funding Delivered\n(at close, FY27)", "Forward Potential\n(earn-outs, 3-yr)",  "5-Yr Total",    "Notes"],
    ["Base",           "$4,360,000",                           "$2,000,000",                             "$6,360,000",    "Tank $750K + Stock $1.25M"],
    ["Low",            "$4,360,000",                           "$1,050,000",                             "$5,410,000",    "Tank $450K + Stock $600K"],
    ["High",           "$4,360,000",                           "$3,000,000",                             "$7,360,000",    "Tank $900K (capped) + Stock $2.1M"],
    ["Model 'Total\nConsideration'\n(base; excl. WC bridge)", "$3,860,000", "$2,000,000",               "$5,860,000",    "Deal Structure sheet; WC bridge excluded from consideration"],
]
add_table(comp_table, [1.2, 1.6, 1.6, 1.3, 1.75])
note("'Funding delivered' includes: cash at close $2.51M + SSLC costs $60K + Exos stake credit (non-cash) $790K + "
     "SSLC debts paid at face ~$500K (TBV) + WC bridge $500K. "
     "Model 'Total Consideration' row follows the Deal Structure sheet definition (excl. WC bridge).")

add_para("Chart file: drafts/SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png",
         size=8, italic=True, color=RGBColor(0x50,0x50,0x50), space_after=2)
add_para("Total Compensation sheet in the model xlsx has formulas linked to Assumptions.",
         size=8, italic=True, color=RGBColor(0x50,0x50,0x50), space_after=4)

# --- apply letterhead fixes --------------------------------------------------
sys.path.insert(0, os.path.join(WS, "scripts"))
from _letterhead_fix import apply_letterhead_fixes
apply_letterhead_fixes(doc)

doc.save(OUT)
print(f"Saved DOCX: {OUT}")

# --- PDF ---
try:
    result = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir",
         os.path.join(WS, "drafts"), OUT],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0 and os.path.exists(PDF):
        print(f"Saved PDF: {PDF}")
    else:
        print("PDF conversion failed:", result.stderr[:200])
except Exception as e:
    print(f"PDF conversion error: {e}")
