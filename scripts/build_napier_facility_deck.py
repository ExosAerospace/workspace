"""Napier Park — Milestone Draw Facility deck (v2 10/6: + MC BLK3 Deal Flow, Series A, RTO; aligned to Jon's Term Sheet R1) (16:9 PPTX, Exos black/orange brand).
Companion to scripts/build_napier_facility_termsheet.py (MC task #1416, 2026-10-05).
Slide 1 embeds the Napier Park cut video (IDJ intro v4 + Japan track card + outro v4);
the closing slide embeds the IDJ outro v4."""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

OUT = "drafts/Exos_Napier_Park_Milestone_Facility_Deck_DRAFT_2026-10-06_v5.pptx"
import re, sys; sys.path.insert(0, "scripts"); from blk3_pipeline_stats import R as PIPE  # live MC BLK3 Deal Flow math (blk3-deal-flow.html)
VID = "drafts/Exos_NapierPark_Japan_Potential_Video_2026-10-05.mp4"
OUTRO = "/tmp/np/outro_small.mp4"
LOGO = "drafts/_exos_white_official.png"
BLACK = RGBColor(0, 0, 0); WHITE = RGBColor(255, 255, 255); OR = RGBColor(0xF2, 0x6A, 0x21)
LG = RGBColor(0xCC, 0xCC, 0xCC); DG = RGBColor(0x26, 0x26, 0x26); MG = RGBColor(0x88, 0x88, 0x88)

prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BL = prs.slide_layouts[6]


def slide(kicker=None, title=None):
    s = prs.slides.add_slide(BL)
    s.background.fill.solid(); s.background.fill.fore_color.rgb = BLACK
    s.shapes.add_picture(LOGO, Inches(11.6), Inches(0.35), height=Inches(0.5))
    if kicker: text(s, kicker.upper(), 0.7, 0.45, 9, 0.4, 14, OR, bold=True)
    if title:
        text(s, title, 0.7, 0.85, 11, 0.9, 34, WHITE, bold=True)
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.75), Inches(1.6), Inches(0.06))
        r.fill.solid(); r.fill.fore_color.rgb = OR; r.line.fill.background()
    text(s, "Exos Aerospace  ·  Indicative, for discussion  ·  Not an offer of securities", 0.7, 7.0, 9, 0.3, 9, MG)
    return s


def text(s, t, x, y, w, h, size, color, bold=False):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame; tf.word_wrap = True
    lines = t if isinstance(t, list) else [t]
    for i, l in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run(); r.text = l; r.font.size = Pt(size); r.font.color.rgb = color; r.font.bold = bold
    return tb


def bullets(s, items, x, y, w, size=18, gap=10):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(5)); tf = tb.text_frame; tf.word_wrap = True
    for i, it in enumerate(items):
        head, body = it if isinstance(it, tuple) else (None, it)
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.space_after = Pt(gap)
        r = p.add_run(); r.text = "▪  "; r.font.color.rgb = OR; r.font.size = Pt(size)
        if head:
            r = p.add_run(); r.text = head + "  "; r.font.bold = True; r.font.color.rgb = WHITE; r.font.size = Pt(size)
        r = p.add_run(); r.text = body; r.font.color.rgb = LG; r.font.size = Pt(size)


def table(s, rows, x, y, widths, size=12, rowh=0.5):
    shp = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(sum(widths)), Inches(rowh * len(rows)))
    t = shp.table
    for j, w in enumerate(widths): t.columns[j].width = Inches(w)
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = t.cell(i, j); c.fill.solid(); c.fill.fore_color.rgb = OR if i == 0 else (DG if i % 2 else BLACK)
            c.text = ""; p = c.text_frame.paragraphs[0]; r = p.add_run(); r.text = v
            r.font.size = Pt(size); r.font.color.rgb = WHITE; r.font.bold = (i == 0 or j == 0)
    return t


def kpi(s, x, y, w, num, lbl, note=None, col=None):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(1.5))
    r.fill.solid(); r.fill.fore_color.rgb = DG; r.line.fill.background()
    b = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.07), Inches(1.5))
    b.fill.solid(); b.fill.fore_color.rgb = col or OR; b.line.fill.background()
    text(s, num, x + 0.2, y + 0.12, w - 0.3, 0.6, 26, WHITE, bold=True)
    text(s, lbl.upper(), x + 0.2, y + 0.68, w - 0.3, 0.35, 11, LG, bold=True)
    if note: text(s, note, x + 0.2, y + 1.0, w - 0.3, 0.45, 10, MG)


M = lambda n: f"${n/1e6:.2f}M" if n >= 1e6 else f"${n/1e3:,.0f}K"

# 1 — Title + Napier Park cut video
s = slide()
text(s, "PREPARED FOR NAPIER PARK GLOBAL CAPITAL", 0.7, 0.6, 9, 0.4, 14, OR, bold=True)
text(s, ["Senior Secured", "Milestone Draw Facility"], 0.7, 1.1, 5.6, 2, 36, WHITE, bold=True)
text(s, ["One facility. Three tranches.", "Each draw secured by the asset that repays it."], 0.7, 3.0, 5.4, 1, 18, LG)
text(s, "John Quinn, Cofounder & CEO  ·  October 2026", 0.7, 4.3, 5.4, 0.4, 14, MG)
s.shapes.add_movie(VID, Inches(6.3), Inches(1.3), Inches(6.4), Inches(3.6), poster_frame_image="/tmp/np/video_poster.png", mime_type="video/mp4")
text(s, "▶ 43 s: BLK3 flown & recovered, the Japan track, and the ask", 6.3, 5.0, 6.4, 0.4, 11, MG)

# 2 — The ask
s = slide("The ask", "Up to $4.25M, drawn only as milestones are hit")
table(s, [
    ["Tranche", "Amount", "Draw trigger", "Use of proceeds", "Security", "Repaid from"],
    ["A  Flight 2 launch readiness", "$750K (up to $1.0M)", "At close; target before Oct 23, 2026", "Finish CDRs + FAA Part 450; Flight 2 hardware", "Flight 2 payload receivables (135 kg bay); Flight 2 hardware", "Payload deposits; repaid by Mar 30, 2027"],
    ["B  Government-contract line", "Up to $2.0M", "Only on USAF TACFI award + TSC match (est. Jan–Mar 2027)", "Balance-sheet backing at TACFI execution; RDRE flight hardware", "TACFI receivables + TSC grant proceeds", "Government milestone payments"],
    ["C  Acquisition working capital", "$350K–$750K (up to $1.5M)", "Only after the Scorpius asset acquisition closes", "Deliver acquired tank contracts (not the purchase price)", "Acquired contracts (~$5M firm 2027) + equipment / IP", "Customer progress payments"],
], 0.7, 2.1, [2.2, 1.6, 2.2, 2.2, 2.2, 1.6], size=12, rowh=1.0)
text(s, "Tranche A is the only immediate need. B and C are uncommitted until their triggers occur. Exos funds the Scorpius purchase price itself.", 0.7, 6.3, 12, 0.5, 13, LG)

# 3 — Schedule of deployment
s = slide("Schedule of deployment", "What happens when, and what it unlocks")
table(s, [
    ["Date", "Event", "Facility impact"],
    ["Oct 6–8, 2026", "Term sheet to Napier Park; call Thu Oct 8", "Credit read; IOI if interested"],
    ["Oct 9 → 23", "Target close + draw of Tranche A", "Launch-readiness work funded"],
    ["Oct 10–19", "Japan: Innovation Dojo + major Japanese space company", "Parallel capital track"],
    ["By Oct 21", "USAF decision on submitting TACFI package", "Tranche B live or drops"],
    ["Oct 20–22", "New York PE meetings; Napier Park in person Oct 21", "Target IOI → documents"],
    ["Dec 11, 2026", "Texas Space Commission vote, $2M match", "Tranche B sized"],
    ["Jan–Mar 2027", "TACFI contract execution; Scorpius acquisition close (target)", "Tranche B / C draws"],
    ["Mar–Apr 2027", "BLK3 Flight 2", "Tranche A repaid by Mar 30, 2027"],
], 0.7, 2.1, [2.0, 6.2, 3.8], size=13, rowh=0.52)

# 4 — Security
s = slide("Security", "Why the money is good")
bullets(s, [
    ("Flight 2 receivables (A).", f"135 kg × $7,500/kg = $1,012,500 gross if fully booked. Terms: 50% at signing, 40% at T-90 to T-120, 10% post-flight. Booked to date: {len(PIPE['orders'])} orders, {PIPE['kg']:g} kg; the rest is pipeline (next slides)."),
    ("It collects today.", "Flight 1 customer entX: $820,000 contract, $410,000 received (QuickBooks). Flight 1 cash stays with Flight 1."),
    ("Government contract (B).", "$2M USAF TACFI + $2M Texas Space Commission statutory match on SBIR Phase II FA9300-25-C-6022. No award, no draw."),
    ("Acquired contract book (C).", "Scorpius tanks for Intuitive Machines landers and orbital transfer vehicles: ~$5M firm 2027 orders (14–16 tanks). Exos already owns 18%."),
    ("Credit, not loan-to-own.", "Exos repays in cash; recently retired ~$600K of notes. Default-only equity backing: warrants on up to 86,605 common shares (~0.69%) issue only on an Event of Default, covering 100% of Tranche A; Exos buyback right."),
], 0.7, 2.1, 12, size=17, gap=12)

# 4b — BLK3 Deal Flow (live Mission Control, Oct 6, 2026)
st = PIPE["stages"]
s = slide("BLK3 deal flow  ·  Exos Mission Control, Oct 6, 2026", "What backs Tranche A: booked payloads and pipeline")
kpi(s, 0.7, 2.1, 2.9, M(PIPE["pipe"]), "BLK3 pipeline value", "estimated, unweighted; incl. booked")
kpi(s, 3.75, 2.1, 2.9, M(PIPE["weighted"]), "Stage-weighted value", "booked + pipeline × stage odds")
kpi(s, 6.8, 2.1, 2.9, M(PIPE["booked"]), "Booked contract value", f"entX Flight 1 $820K + {len(PIPE['orders'])} Flight 2 orders", RGBColor(0xE8, 0xB0, 0x30))
kpi(s, 9.85, 2.1, 2.8, str(PIPE["n"]), "Prospects to close", f"{st['active']} active · {st['outreach']} outreach · {st['ready'] + st['early']} ready/researching", RGBColor(0x3D, 0xB8, 0x6B))
table(s, [
    ["Booked", "Payload", "Flight", "Contract", "Status"],
    ["entX Limited", "RHU demonstration (Mission 0)", "BLK3 Flight 1 · Q1 2027", "$820,000", "$410,000 received (QuickBooks); Flight 1 only, not pledged"],
] + [[c.split(" DBA ")[-1] if re.search(r"LLC|Inc|Ltd|DBA", c) else "Private customer", n.split(" — ")[0][:40], "BLK3 Flight 2 · early 2027", f"${v:,.0f}", f"Booked · {kg:g} kg"] for c, n, kg, v in PIPE["orders"]],
    0.7, 3.85, [2.4, 3.0, 2.3, 1.3, 3.0], size=11, rowh=0.38)
text(s, ["Flight 2 bay: " + f"{PIPE['kg']:g} of 135 kg booked ({max(1, round(PIPE['kg'] / 1.35))}%). Full bay = $1,012,500 per flight.",
         "Pipeline values are estimates sized off the published rate card by segment, not booked revenue. Stage odds: active 50% · outreach 20% · ready 10% · researching 5%."],
     0.7, 5.6, 12, 0.9, 12, LG)

# 4c — Pipeline detail
s = slide("BLK3 deal flow  ·  pipeline detail", f"{PIPE['n']} prospects, {M(PIPE['unbooked'])} unbooked, sized off the rate card")
cd = CategoryChartData(); cd.categories = ["Active", "Outreach sent", "Ready / draft", "Researching"]
cd.add_series("Est. value ($M)", tuple(round(PIPE["by_stage_usd"][k] / 1e6, 2) for k in ("active", "outreach", "ready", "early")))
ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.7), Inches(2.1), Inches(5.6), Inches(4.2), cd).chart
ch.has_legend = False; ch.plots[0].has_data_labels = True
dl = ch.plots[0].data_labels; dl.number_format = '"$"0.00"M"'; dl.number_format_is_linked = False; dl.font.color.rgb = WHITE; dl.font.size = Pt(12)
ch.series[0].format.fill.solid(); ch.series[0].format.fill.fore_color.rgb = OR
ch.category_axis.tick_labels.font.color.rgb = LG; ch.category_axis.tick_labels.font.size = Pt(12)
ch.value_axis.visible = False; ch.value_axis.has_major_gridlines = False
text(s, [f"Prospects by stage: {st['active']} · {st['outreach']} · {st['ready']} · {st['early']}"], 0.7, 6.35, 5.6, 0.4, 11, MG)
bt = PIPE["by_tier"]; order = [("Quarter bay", "$255K"), ("6U", "$45K"), ("3U", "$22.5K"), ("1U", "$7.5K")]
table(s, [["Likely slot (rate card)", "Prospects", "Est. value"]] +
      [[f"{t}  ({p})", str(bt.get(t, (0, 0))[0]), M(bt.get(t, (0, 0))[1])] for t, p in order if t in bt],
      6.7, 2.1, [2.9, 1.3, 1.8], size=12, rowh=0.42)
bullets(s, [
    ("Active now:", "a DoD hypersonic-test prime, a commercial space-station builder, NASA's Flight Opportunities program office, and a university cryogenic-fluids team."),
    ("Coverage:", f"stage-weighted unbooked pipeline ≈ {M(PIPE['weighted'] - PIPE['booked'])} vs. a $1.01M Flight 2 bay."),
    ("Engine:", "daily payload-sales pipeline in Mission Control; monthly booking report to Napier Park."),
], 6.7, 4.4, 6.0, size=13, gap=8)

# 5 — Demand band
s = slide("Capital demand band", "Need scales with wins, and so does collateral")
cd = CategoryChartData(); cd.categories = ["~20% pipeline conversion", "~75% conversion (optimistic)"]
cd.add_series("Tranche A", (0.75, 0.75)); cd.add_series("Tranche B", (0, 2.0)); cd.add_series("Tranche C", (0.35, 1.5))
ch = s.shapes.add_chart(XL_CHART_TYPE.BAR_STACKED, Inches(0.7), Inches(2.1), Inches(7.4), Inches(4.4), cd).chart
ch.has_legend = True; ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False
ch.legend.font.color.rgb = LG; ch.legend.font.size = Pt(12)
for ser, col in zip(ch.series, [OR, RGBColor(0x99, 0x99, 0x99), RGBColor(0x55, 0x55, 0x55)]):
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = col
ch.category_axis.tick_labels.font.color.rgb = LG; ch.category_axis.tick_labels.font.size = Pt(12)
ch.value_axis.tick_labels.font.color.rgb = LG; ch.value_axis.tick_labels.font.size = Pt(11)
ch.value_axis.has_major_gridlines = False; ch.value_axis.tick_labels.number_format = '"$"0.0"M"'; ch.value_axis.tick_labels.number_format_is_linked = False
bullets(s, [
    ("~20%:", "Tranche A + low end of C ≈ $1.1–1.5M peak."),
    ("~75%:", "A + B + high end of C ≈ $4.25M peak."),
    ("Pipeline:", "open DoD, NASA and Intuitive Machines opportunities."),
    ("Every award", "that adds need also adds an assignable contract."),
], 8.5, 2.3, 4.3, size=15, gap=14)

# 6a — Capital stack: every path in parallel
s = slide("Capital stack  ·  all paths run in parallel", "Where the facility sits in the capital stack")
table(s, [
    ["Source", "Size", "Status (Oct 6, 2026)", "Role for Napier Park"],
    ["Napier Park facility", "Up to $4.25M", "Term sheet R1; call Thu Oct 8", "Bridge to Flight 2; milestone-secured"],
    ["Flight 2 payload sales", "$1.01M per full bay", f"{len(PIPE['orders'])} booked; {PIPE['n']} prospects in pipeline", "Primary repayment of Tranche A"],
    ["USAF TACFI + TSC match", "$2M + $2M", "USAF package decision by Oct 21; TSC vote Dec 11", "Trigger and repayment for Tranche B"],
    ["RTO + PIPE (Nasdaq)", "~$15M PIPE, ≥$10M net", "Advisory terms agreed by Exos Oct 6; shell not yet named", "Takeout / refinancing source; not relied on"],
    ["Series A (Rule 504)", "$10M first close → $25M", "504 open (~$167K in); institutional round sequenced behind RTO", "Equity cushion beneath the facility"],
    ["Japan offering (Reg S)", "~¥790M (~US$5M)", "Innovation Dojo Oct 10–19; contingent on investor", "Parallel equity; offshore, separate"],
    ["NASA OSC loan (Stifel)", "~$15M", "Longer-dated origination", "Long-term manufacturing debt"],
], 0.7, 2.1, [2.6, 2.1, 4.0, 3.3], size=12, rowh=0.52)
text(s, "None of the equity or loan tracks is committed. Tranche A is sized to be repaid from Flight 2 receivables without any of them.", 0.7, 6.4, 12, 0.4, 13, LG)

# 6b — Series A detail
s = slide("Series A  ·  in more detail", "Private growth round, staged to stay inside Rule 504")
table(s, [
    ["Item", "Figure of record"],
    ["Raise", "$10M first close, tranched to $25M (staged ~$10M per 12 months under Rule 504 of Reg D)"],
    ["Valuation reference", "$169.7M equity (independent 409A, Mar 31, 2026; Eqvista)"],
    ["Use of funds", "First close: Scorpius ROFR (~$3.4M) + RDRE / TACFI match + BLK3 build. BLK4 in the $25M expansion"],
    ["Raised to date", "~$167K in the current 504 offering (Exos subscription ledger)"],
    ["Investor pipeline", "57 institutional / family-office targets tracked in Exos CRM; ~17 engaged (meetings, NDA, diligence)"],
    ["Sequencing", "New institutional outreach held while the RTO runs (since Sep 28); warm conversations continue"],
    ["Listing path", "TXSE-primary listing as the conditioned destination; RTO is the faster route to Nasdaq"],
], 0.7, 2.1, [2.6, 9.4], size=13, rowh=0.55)
text(s, "Indicative only. Not an offer to sell securities. Figures are Exos management figures.", 0.7, 6.6, 12, 0.3, 11, MG)

# 6c — RTO detail
s = slide("RTO  ·  in more detail", "Reverse merger into a Nasdaq-listed shell, with a PIPE")
table(s, [
    ["Item", "Term (Exos board copy, Oct 6, 2026)"],
    ["Advisor", "FNEX Capital, LLC (FINRA-registered broker-dealer); exclusive, flat 6-month term"],
    ["Structure", "Exos merges into a Nasdaq-listed shell; shell to be named before the definitive agreement"],
    ["Merger value", "~$350M merger enterprise value; merger price floor $2.50/share unless Exos agrees"],
    ["PIPE", "~$15M convertible note, escrowed to Closing; converts at the merger price; never repayable in cash"],
    ["Net cash to Exos", "≥$10M net at Closing is a closing condition (est. ~$11.7M on a $15M PIPE)"],
    ["Status", "Exos agreed the advisory terms Oct 6; Exos and Scorpius boards reviewed Oct 6; Counsel review before signing"],
    ["Open items", "Shell identity and listing standard; 6 remaining agreement details; definitive merger documents"],
], 0.7, 2.0, [2.6, 9.4], size=12, rowh=0.5)
text(s, "For Napier Park: a closed RTO adds a takeout source and public acquisition currency (Scorpius). The facility does not depend on it. Confidential; not committed.", 0.7, 6.45, 12, 0.5, 13, LG)

# 6 — Japan track
s = slide("Parallel capital  ·  Oct 10–22, 2026", "The Japan track and New York")
bullets(s, [
    ("Innovation Dojo Japan:", "Exos is a selected initiative in the program."),
    ("Exos Aerospace Japan K.K.:", "wholly owned subsidiary planned before year-end."),
    ("Japan-investor offering:", "targeting ~¥790M (~US$5M), separate offshore offering."),
    ("Strategic:", "meeting a multi-billion-dollar Japanese space company on de-risking its reusable rocket programs."),
    ("New York, Oct 20–22:", "private-equity meetings; Napier Park in person Oct 21."),
    ("Longer-dated:", "NASA Office of Strategic Capital loan process with Stifel."),
    ("Why it matters to Napier Park:", "a fast IOI closes Tranche A before these outcomes are known. None of these tracks is committed."),
], 0.7, 2.1, 12, size=16, gap=10)

# 7 — Indicative terms + next steps
s = slide("Indicative terms", "Our proposal, open to Napier Park's structure")
table(s, [
    ["Term", "Proposal"],
    ["Structure", "Senior secured delayed-draw facility; B and C uncommitted until triggered"],
    ["Pricing", "To be proposed by Napier Park"],
    ["Equity backing (default-only)", "Warrants issued ONLY on an uncured Event of Default; none while Exos is current. Capped at 86,605 Exos common shares (~0.69% fully diluted) = 100% coverage of the $750K Tranche A ($750,000 / $8.66 per-share 409A FMV after the proposed 36.51% DLOM, Eqvista 03/31/26). Common: no liquidation preference, board or voting rights"],
    ["Exos buyback right", "If issued, Exos may repurchase warrants / exercised shares at then-current 409A FMV at any time (warrants: FMV minus $8.66 strike); unexercised warrants expire 5 years after issue; Exos ROFR on transfers"],
    ["Cash sweep", "A: 50% of Flight 2 payload collections to a lender-controlled account until repaid (full bay sweeps ~$456K pre-flight); balance bullet Mar 30, 2027; B / C: dedicated collection accounts"],
    ["Maturity", "A: Mar 30, 2027  ·  B: on TACFI milestone receipts  ·  C: 12 months from draw"],
    ["Reporting", "Monthly booking / receivables report; quarterly financials"],
    ["Next step", "Discuss Thu Oct 8 → IOI → Tranche A close before Oct 23"],
], 0.7, 2.1, [2.4, 9.6], size=12, rowh=0.52)

# 8 — Close + outro video
s = slide()
text(s, "LET'S BUILD IT TOGETHER", 0.7, 0.6, 9, 0.4, 14, OR, bold=True)
text(s, ["Close Tranche A", "before Oct 23."], 0.7, 1.1, 5.6, 2, 36, WHITE, bold=True)
text(s, ["John Quinn, Cofounder & CEO", "jquinn@exosaero.com  ·  +1-972-740-8355", "www.exosaero.com"], 0.7, 3.2, 5.4, 1.4, 16, LG)
s.shapes.add_movie(OUTRO, Inches(6.3), Inches(1.3), Inches(6.4), Inches(3.6), poster_frame_image="/tmp/np/outro_poster.png", mime_type="video/mp4")

prs.save(OUT)
print(OUT)
