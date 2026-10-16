#!/usr/bin/env python3.12
"""Hokkaido Space Summit / HOSPO trip briefing (Oct 13-15, 2026) — prioritized opportunities + Toshi task list. Editable .docx (no PDF)."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
OUT="drafts/Hokkaido_Trip_Briefing_Prioritized_Opportunities_2026-10-15_r2.docx"
NAVY=RGBColor(0x0A,0x3D,0x7C)
d=Document(); s=d.styles["Normal"]; s.font.name="Calibri"; s.font.size=Pt(10)
for sec in d.sections: sec.left_margin=sec.right_margin=Inches(0.8)
def h(t,size=12):
    p=d.add_paragraph(); r=p.add_run(t); r.bold=True; r.font.size=Pt(size); r.font.color.rgb=NAVY; p.paragraph_format.space_before=Pt(8)
def para(t,i=False,b=False):
    p=d.add_paragraph(); r=p.add_run(t); r.italic=i; r.bold=b; p.paragraph_format.space_after=Pt(4)
def bl(t,lead=None):
    p=d.add_paragraph(style="List Bullet")
    if lead: p.add_run(lead).bold=True
    p.add_run(t); p.paragraph_format.space_after=Pt(2)
def table(rows,widths):
    t=d.add_table(rows=len(rows),cols=len(rows[0])); t.style="Light Grid Accent 1"; t.autofit=False
    lay=OxmlElement("w:tblLayout"); lay.set(qn("w:type"),"fixed"); t._tbl.tblPr.append(lay)
    for gc,w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")),widths): gc.set(qn("w:w"),str(int(w*1440)))
    for ri,row in enumerate(rows):
        tr=t.rows[ri]._tr.get_or_add_trPr(); cs=OxmlElement("w:cantSplit"); tr.append(cs)
        if ri==0: hd=OxmlElement("w:tblHeader"); tr.append(hd)
        for ci,v in enumerate(row):
            c=t.cell(ri,ci); c.width=Inches(widths[ci]); c.text=""
            rr=c.paragraphs[0].add_run(str(v)); rr.font.size=Pt(8.5); rr.bold=(ri==0)
    d.add_paragraph()

t=d.add_paragraph(); r=t.add_run("Hokkaido Trip Briefing — Prioritized Opportunities"); r.bold=True; r.font.size=Pt(16); r.font.color.rgb=NAVY
para("Hokkaido Space Summit 2026 (Obihiro) + Hokkaido Spaceport (HOSPO, Taiki) events  |  Oct 13–15, 2026  |  INTERNAL — for John's review", i=True)

h("Bottom line")
para("Thirty-plus contacts across Japanese government, logistics, launch developers, trading houses, investors, media and three foreign spaceports. "
     "The highest-value outcomes: (1) NYK as our logistics partner plus a possible paid support contract on its JAXA-funded rocket-recovery program; "
     "(2) Innovative Space Carrier, our #1-ranked BLK3 vehicle-sales prospect, met in person; (3) a government support layer — the PM's Special Advisor for regional strategy, "
     "Hokkaido's Vice Governor and Taiki's mayor; (4) new tank and test-service openings with Axiom Space; (5) two foreign spaceports (SSC Sweden, Virginia) interested in BLK3. "
     "Everything below is in the CRM; denied-party screening was clean for every company screened.")

h("Rules that apply to every follow-up")
for x in ["Capability-level only — no technical data or drawings to any foreign party without export review (Empowered Official John Quinn, reviewer Denise Shirey); support/consulting work = TAA first.",
          "No pricing until John approves; BLK3 timing = \"early 2027\"; no Hokkaido launch date (\"exploring\").",
          "Government, politicians, investors and media = John only. No capital/Japan-entity talk with anyone outside counsel's process (Reg S / CFIUS / FEFTA).",
          "Toshi owns Japan commercial follow-ups (Japanese thank-you within a week, then the actions below)."]:
    bl(" "+x)

h("Tier 1 — act now (highest value; AstroX + Space One added by John 10/15)")
rows=[["#","Who","Opportunity","Next action","Owner"],
 ["1","NYK Line — Daisuke Suga (space BD), Satohiko Kodama (ocean eng.), Masahiro Morimoto (Hokkaido GM)","Designated logistics + consortium partner: ship BLK3/GSE TX→Japan, candidate TX→Sardinia. NYK leads JAXA SSF offshore reusable-rocket recovery project (w/ MHI, 2025–29) → paid Exos support contract (TAA). DD PASS. OPP-636.","Follow-up email sent 10/15 with booking link (meeting after next week). Toshi: request project-cargo contact + non-binding shipping estimate (dims/weights only). Exo: Honda-model Phase-1 support proposal draft.","John + Toshi"],
 ["2","Innovative Space Carrier — Kojiro Hatada, President & CEO","#1 BLK3 vehicle-sales target (fit 5/5; ¥3.2B equity 2026, MEXT SBIR Ph3 up to ¥5B, SSF). Their 100-km ASCA 1.1 risks the vehicle on a failed powered landing → Exos backup recovery kit.","Toshi: Japanese thank-you + propose call on recovery for ASCA test flights; capability deck only.","Toshi (John on call)"],
 ["3","AstroX — Shobu Oda, CEO (meeting 10/16)","Rockoon tests lose gondola/attitude-control hardware every flight → recovery + reflight value; BLK3 bridge flights for their customers (fit 4/5). DD caution (early stage), CSL clean.","Toshi: follow-up after 10/16 meeting + recovery capability call (MC #3810).","Toshi (John on call)"],
 ["4","Space One — Hidenori Yagi (BD Group) entry; Nobuhiro Sekino (VP) sponsor","KAIROS is 0-for-3 (Mar 2026 failure tied to the flight-termination system) → recover test hardware by drogue/parafoil + fly avionics/FTS on a recoverable Exos test flight before flight 4. Well funded (MEXT SBIR Ph3 up to ¥4.46B; MoD contracts). Fit 3/5.","Toshi: open contact via BD group or Space BD; ask for a call with John (MC #3811). Capability-level only (MoD programs).","Toshi (John on call)"],
 ["5","Gov't support layer — Hajime Sasaki (PM Special Advisor, Regional Future Strategy; LDP HoR), Tsuyoshi Mitsuhashi (Vice Governor of Hokkaido), Yutaka Kurokawa (Mayor of Taiki, HOSPO owner)","Policy cover for a Japan presence; Sasaki expressed support for tanks + payloads; regional revitalization / high-tech jobs is their agenda.","John: formal thank-you letters (Toshi translates); get emails for Mitsuhashi/Kurokawa via Space Cotan. No commitments.","John only"],
 ["6","Axiom Space — Koichi Wakata (astronaut, CTO Asia-Pacific), Janelle Ward (Strategic Engagements)","Station modules each carry propulsion; in-house 3D-printed thrusters; tank supplier not public → Scorpius composite tanks (Exos commission) + thruster test hosting / BLK3 flight qualification.","John: follow-up to Wakata/Ward asking who supplies propellant/pressurant tanks and where printed thrusters are qualified.","John"],
 ["7","SSC Space (Sweden) — Nils Forsblad, BD Director, Orbital Launch & Rocket Test","Jon: propose BLK3 for reuse with SSC (Esrange). Foreign-spaceport hosting/partnership.","John: follow-up proposing BLK3 reuse discussion; capability-level.","John"],
 ["8","Virginia Spaceport Authority — Ted Mercer (CEO, Maj Gen ret.), Kimberly West (EA)","U.S. spaceport (MARS, Wallops) — spaceport potential for BLK3; met on flight back.","John: schedule via Kimberly West.","John"]]
table(rows,[0.25,1.6,2.2,2.0,0.75])

h("Tier 2 — strong, develop over 30–60 days")
rows=[["#","Who","Opportunity","Next action","Owner"],
 ["9","Firefly Aerospace — Brett Stephens, Director, Commercial & International Launch","Intros requested to Firefly Japan dev team + U.S. Embassy Tokyo contacts; Firefly also has a HOSPO feasibility MOU.","Auto-check 10/21; reminder draft to John if not received.","John"],
 ["10","Space BD — Umeda (Organization Development)","Suborbital BLK3 as pre-ISS qualification/screening step in Space BD's microgravity offering.","Toshi: ask Umeda for intro to the microgravity utilization team.","Toshi"],
 ["11","Mitsui Bussan Aerospace — Gota Mishima, Sr. Mgr Space Business","Japan import/distribution channel (Scorpius tanks, BLK3 services).","Follow-up email ready on John's OK; Toshi then explores channel terms.","Toshi"],
 ["12","Andøya Spaceport (Norway) — Nicholas Borroz, BD Manager","New tenants beyond Isar need cryo propellant storage/handling → Scorpius tanks / Exos cryo; BLK3 hosting.","John: cryo + hosting follow-up.","John"],
 ["13","Swiss Business Hub / Embassy of Switzerland — Luca Saporita","Warm intros to ETH Zurich + EPFL (eSpace): BLK3 research flights; Scorpius tanks.","John/Lizi: request the two intros.","John / Lizi"],
 ["14","MJOLNIR SPACEWORKS — Ryota Kotabe (BD), Kazuho Sato (PR)","Sapporo hybrid-rocket developer (SSF rocket-parts selectee); test/recovery partner; local Hokkaido ally.","Toshi: thank-you + explore flight-test/recovery support.","Toshi"]]
table(rows,[0.25,1.6,2.2,2.0,0.75])

h("Tier 3 — relationship / hold")
rows=[["#","Who","Note","Owner"],
 ["15","SBI Investment — Yang Yang, Mgr CVC","Investor. Capital talks only via John + counsel (Reg S / CFIUS / FEFTA). DD PASS.","John only"],
 ["16","U.S. Space Forces–Japan — Lt Col Kaoru Elliott, Deputy Commander","Space Force–Japan partnership liaison; relationship only.","John only"],
 ["17","Media — NHK Sapporo (Luana Mosset), Asahi Shimbun Hokkaido (Kaori Ozawa); HBC on site","Interviews given 10/14 on regional revitalization; future quotes are John's call.","John"],
 ["18","Hibiki Seiki — Takuya Fukumura (machining, JIS Q 9100)","Japan-side machining source for later; no Exos technical data (export).","Toshi (low)"],
 ["19","AMORCE Inc. — Hideyuki Wada (CEO), Chihiro Nakamura (President)","Tanks/payload interest; company UNVERIFIED (DD caution) — verify registration first.","Toshi"],
 ["20","Sogo Kanri — Mr. Sasaki (Nagoya, building management)","Facilities only if the Japan entity needs space.","Toshi (low)"]]
table(rows,[0.25,2.3,3.15,1.1])

h("Mission Control tasks for Toshi (created 10/15 on John's approval, D-7282121) — parent #3807")
for x in ["#3808 NYK: thank-you, project-cargo contact, non-binding TX→Japan / TX→Sardinia estimate; schedule John's follow-up. Due 10/22.",
 "#3809 Innovative Space Carrier (Hatada): thank-you + recovery call with John. Due 10/22.",
 "#3810 AstroX (Oda): follow-up after the 10/16 meeting + recovery capability call. Due 10/22.",
 "#3811 Space One: open contact via BD group (Yagi) or Space BD; recovery + avionics/FTS flight-test call with John. Due 10/24.",
 "#3812 Government thank-yous: translate John's letters to Sasaki, Mitsuhashi, Kurokawa. Due 10/24.",
 "#3813 Space BD (Umeda): intro to microgravity utilization team. Due 10/24.",
 "#3814 Mitsui Bussan Aerospace (Mishima): distribution-channel interest after John's email. Due 10/29.",
 "#3796 MJOLNIR (Kotabe): composite cryo tank sales (existing task). Due 10/21.",
 "#3815 AMORCE: verify company registration before any engagement. Due 10/29.",
 "#3816 Hibiki Seiki + Sogo Kanri: courtesy thank-yous. Due 11/5."]:
    bl(" "+x)
para("Not for Toshi: government officials, Lt Col Elliott, SBI, media, Axiom, SSC, Virginia, Andøya, Swiss embassy, Firefly — John-owned (Lizi supports where noted).", i=True)

h("Context worth remembering")
for x in ["Space Cotan took over HOSPO operations Oct 1, 2026 under a concession from Taiki Town (https://hokkaidospaceport.com/en/news/2306).",
          "HOSPO advantages used in interviews: open ocean east and south, clear 'Tokachi-bare' weather, room to expand, vertical + runway operations.",
          "Interstellar Technologies (HOSPO anchor tenant): no new contact this trip; existing CRM name only (Lui Suzuki).",
          "Honda (separate track, MC #3704): lead = Exos recovery-on-anomaly; consulting TAA proposal model reused for NYK."]:
    bl(" "+x)
d.save(OUT); print("WROTE",OUT)
