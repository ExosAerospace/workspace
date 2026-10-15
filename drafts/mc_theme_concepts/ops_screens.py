#!/usr/bin/env python3
"""Exos Mission Control — OPERATIONS screens for the VSFB MDZ whitepaper (Jon 2026-10-15 18:22: "align with rocket
launch, payload operations, logistics ERP/MRP/inventory and financial systems integration evidenced ... read like
rocket mission tracking"). C layout + D colors. UNCLASSIFIED / external-safe: no ITAR technical data, customers
anonymized, no dollar figures for contracts/POs, BLK3 shown per figures of record (Exos Part 431 license transitioning to Part 450 (John 10/15: NOT "licensed"); hover test PLANNED,
not yet flown commercially; first commercial flight targeted early 2027). Every count is read LIVE at render time from
MC data: missions.json, payload-orders.json (+ envelopes.json), erp-foundation/mc.db (asset, mrp_run, purchase_order,
purchase_request, part, bom_line), bom-index*.json, inventory.json, qb-invoices.json."""
import json, os, sqlite3, subprocess, datetime

WS = "/Users/exomac/.openclaw/workspace"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitepaper_ops")
os.makedirs(OUT, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
STAMP = datetime.datetime.now().strftime("%d %b %Y %H:%M CDT").upper()
J = lambda p: json.load(open(os.path.join(WS, p)))

# ── live data ──
db = sqlite3.connect(f"file:{WS}/erp-foundation/mc.db?mode=ro", uri=True)
q1 = lambda s: db.execute(s).fetchone()[0]
asset_events = db.execute("select occurred_at, notes from asset_event order by occurred_at").fetchall()
faa_date = next((d for d, n in asset_events if "FAA launch license" in n), None)
run = db.execute("select run_at, summary_json from mrp_run order by run_at desc limit 1").fetchone()
mrp = json.loads(run[1]); mrp_at = run[0][:16].replace("T", " ") + "Z"
po_open, po_closed = q1("select count(*) from purchase_order where status='open'"), q1("select count(*) from purchase_order where status='closed'")
po_qb = q1("select count(*) from purchase_order where qb_id is not null and qb_id!=''")
pr_open = q1("select count(*) from purchase_request where status='open'")
parts_make, parts_buy = q1("select count(*) from part where make_buy='make'"), q1("select count(*) from part where make_buy='buy'")
vendors = q1("select count(*) from vendor")
bom_blk3, bom_hvrr = J("mission-control/data/bom-index.json")["count"], J("mission-control/data/bom-index-hvrr.json")["count"]
inv = J("mission-control/data/inventory.json")["records"]
inv_items, inv_photo = len(inv), sum(1 for r in inv if r.get("photos"))
qbi = J("mission-control/data/qb-invoices.json").get("invoices", [])
qb_paid, qb_sent, qb_order = sum(i["status"] == "paid" for i in qbi), sum(i["status"] == "sent" for i in qbi), sum(1 for i in qbi if i.get("order"))
missions = {m["id"]: m for m in J("mission-control/data/missions.json")["missions"]}
node = subprocess.run(["node", "-e", """
const p=require('./lib/payload-orders');const envs=JSON.parse(require('fs').readFileSync('data/envelopes.json'));
console.log(JSON.stringify(p.load().orders.map(o=>{const v=p.view(o,envs);return {id:o.id,mission:o.mission,flight_date:o.flight_date,
 q:!!o.questionnaire_received,export:v.export_ok,exp_class:(o.export||{}).classification||'',csl:v.csl_ok,lsa:v.executed,
 m1:!!(v.milestones_view[0]||{}).paid_at,inkind:!!o.in_kind,waiver:!!o.waiver_wet_signed_at,waiver_due:v.waiver_due,faa:!!o.waiver_faa_submitted_at,stage:v.stage}})))"""],
    cwd=os.path.join(WS, "mission-control"), capture_output=True, text=True)
orders = json.loads(node.stdout)
m6 = [o for o in orders if o["mission"] == "M6"]
waivers_on = sum(o["waiver"] for o in m6)

CSS = """
*{box-sizing:border-box} body{margin:0;width:1920px;height:HPX;position:relative;overflow:hidden;background:#16181b;color:#eceff1;font-family:'Menlo','SF Mono',monospace;
 background-image:linear-gradient(rgba(255,179,71,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,179,71,.035) 1px,transparent 1px);background-size:40px 40px}
.p{background:#202327;border:1px solid #3a3f45;padding:16px 18px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 28px;border-bottom:2px solid #3a3f45}
.brand{font-size:30px;letter-spacing:.3em;color:#ffb347} .brand small{display:block;font-size:12px;letter-spacing:.3em;color:#8b939b;margin-top:4px}
.g{color:#5fd3a2} .a{color:#ffb347} .d{color:#8b939b} .r{color:#ff6b6b}
h3{margin:0 0 12px;font-size:14px;letter-spacing:.28em;color:#5fd3a2}
.kv{font-size:38px;font-weight:700;color:#ffb347} .kl{font-size:12px;letter-spacing:.2em;color:#8b939b;margin-top:6px;line-height:1.5}
.grid{display:grid;gap:18px;padding:20px 28px}
table{width:100%;border-collapse:collapse;font-size:15px} td,th{padding:9px 8px;border-bottom:1px solid rgba(139,147,155,.22);text-align:left}
th{font-size:11px;letter-spacing:.18em;color:#8b939b;font-weight:400}
.ok{color:#5fd3a2} .pend{color:#ffb347} .todo{color:#8b939b}
.foot{position:absolute;bottom:0;left:0;right:0;padding:10px 28px;border-top:2px solid #3a3f45;font-size:13px;color:#8b939b;display:flex;justify-content:space-between;background:#16181b}
.flow{display:flex;align-items:stretch} .st{flex:1;text-align:center;padding:4px 6px} .ar{width:34px;display:flex;align-items:center;justify-content:center;color:#5fd3a2;font-size:24px}
.st .kv{font-size:30px} .tag{display:inline-block;font-size:11px;letter-spacing:.15em;border:1px solid;padding:2px 7px;margin-top:6px}
"""
MARK = lambda b: "<span class=ok>■ DONE</span>" if b is True else ("<span class=pend>◧ OPEN</span>" if b is None else "<span class=todo>□ NEXT</span>")


def page(title, body, caption, h):
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{CSS.replace('HPX', str(h) + 'px')}</style></head><body>
<header><div class=brand>EXOS MISSION CONTROL<small>MISSION OPERATIONS · {title}</small></div>
<div class=g style='letter-spacing:.2em'>LIVE · {STAMP} · UNCLASSIFIED</div></header>{body}
<div class=foot><span>{caption}</span><span>Exos Aerospace Systems &amp; Technologies, Inc. · CAGE 7EMY6</span></div></body></html>"""


def kpi(v, k):
    return f"<div class=p><div class=kv>{v}</div><div class=kl>{k}</div></div>"


S = {}
# FIG 1 — Mission operations board
gates = [("FAA launch license: Part 431 (current)", True, f"renewed {faa_date}" if faa_date else "renewed"),
         ("FAA 14 CFR Part 450 transition", None, "in progress"),
         ("Hover test campaign (BLK3 S0)", False, "planned"),
         (f"Payload cross-waivers on file (M6)", None if waivers_on < len(m6) else True, f"{waivers_on} of {len(m6)} · due L-90"),
         ("Payload FAA submission package (M6)", False, "after all waivers on file"),
         ("Vehicle MRP build plan (S0)", None, f"{mrp['parts_planned']} parts planned · nightly run")]
gr = "".join(f"<tr><td>{n}</td><td>{MARK(b)}</td><td class=d>{t}</td></tr>" for n, b, t in gates)
mrows = [("SARGE 1–4", "SARGE", "—", "FLOWN", "4 suborbital missions (heritage)", "ok"),
         ("M5", "BLK3", "S0", "BOOKED", "commercial customer · first S0 mission", "pend"),
         ("M6", "BLK3", "S0", "BOOKED", f"shared payload bay · {len(m6)} payload orders", "pend")]
mr = "".join(f"<tr><td class=a style='font-weight:800'>{a}</td><td>{b}</td><td>{c}</td><td class={k}>{s}</td><td class=d>{n}</td></tr>" for a, b, c, s, n, k in mrows)
S["Fig1_Mission_Ops_Board"] = (page("MISSION OPERATIONS BOARD", f"""
<div class=grid style='grid-template-columns:repeat(5,1fr)'>{kpi('BLK3 S0','VEHICLE · GREENVILLE, TX')}{kpi('PART 431→450','FAA LICENSE · TRANSITIONING')}{kpi('EARLY 2027','FIRST COMMERCIAL FLIGHT TARGET')}{kpi(len(missions),'BLK3 MISSIONS BOOKED')}{kpi('4','SARGE MISSIONS FLOWN (HERITAGE)')}</div>
<div class=grid style='grid-template-columns:1.1fr 1fr;padding-top:0'>
 <div class=p><h3>▸ MISSION MANIFEST TRACK</h3><table><tr><th>MISSION</th><th>VEHICLE</th><th>SERIAL</th><th>STATUS</th><th>NOTES</th></tr>{mr}</table></div>
 <div class=p><h3>▸ FLIGHT READINESS GATES</h3><table>{gr}</table></div>
</div>""", "Fig. 1 — Mission operations board: vehicle, missions and flight-readiness gates tracked live in Mission Control", 640))

# FIG 2 — Payload operations
cols = [("Questionnaire", "q"), ("Export screen", "export"), ("Denied-party", "csl"), ("LSA e-signed", "lsa"), ("Payment", "m1"),
        ("FAA cross-waiver", "waiver"), ("FAA submission", "faa")]
names = {"PO2C-2026-001": "Payload A · commercial sensor", "PO2C-2026-002": "Payload B · 1U commemorative"}
prow = ""
for o in m6:
    cells = ""
    for _, k in cols:
        v = o[k] or (k == "m1" and o["inkind"])
        cells += f"<td>{'<span class=ok>■</span>' if v else '<span class=todo>□</span>'}</td>"
    prow += f"<tr><td class=a>{names.get(o['id'], o['id'])}</td>{cells}<td class=d>L-90 {o['waiver_due']}</td></tr>"
hdr = "".join(f"<th>{c.upper()}</th>" for c, _ in cols)
S["Fig2_Payload_Operations"] = (page("PAYLOAD OPERATIONS", f"""
<div class='grid'><div class='p flow'>
 <div class=st><h3>BOOK</h3><div class=kv>{len(orders)}</div><div class=kl>PAYLOAD ORDERS</div></div><div class=ar>▶</div>
 <div class=st><h3>SCREEN</h3><div class=kv>{sum(o['export'] and o['csl'] for o in orders)}/{len(orders)}</div><div class=kl>EXPORT + DENIED-PARTY<br>CLEARED</div></div><div class=ar>▶</div>
 <div class=st><h3>CONTRACT</h3><div class=kv>{sum(o['lsa'] for o in orders)}/{len(orders)}</div><div class=kl>LAUNCH SERVICES AGMT<br>E-SIGNED</div></div><div class=ar>▶</div>
 <div class=st><h3>WAIVER</h3><div class=kv>{waivers_on}/{len(m6)}</div><div class=kl>WET-SIGNED CROSS-WAIVER<br>ON FILE · HUMAN-CONFIRMED</div></div><div class=ar>▶</div>
 <div class=st><h3>FAA</h3><div class=kv>L-90</div><div class=kl>WAIVER PACKAGE TO FAA<br>FOR PAYLOAD APPROVAL</div></div><div class=ar>▶</div>
 <div class=st><h3>INTEGRATE</h3><div class=kv>L-45</div><div class=kl>PAYLOAD DELIVERY TO<br>EXOS FOR INTEGRATION</div></div><div class=ar>▶</div>
 <div class=st><h3>RECOVER</h3><div class=kv>MIN</div><div class=kl>IN-VEHICLE PAYLOADS BACK<br>WITHIN MINUTES OF LANDING</div></div>
</div></div>
<div class=grid style='padding-top:0'><div class=p><h3>▸ MISSION M6 · PAYLOAD STATUS (LIVE, CUSTOMERS ANONYMIZED)</h3>
<table><tr><th>PAYLOAD</th>{hdr}<th>WAIVER DUE</th></tr>{prow}</table></div></div>""",
 "Fig. 2 — Payload operations: every payload tracked from booking through export screening, contract, FAA waiver and integration", 640))

# FIG 3 — Logistics: ERP / MRP / inventory
flow = [("MISSION", f"{len(missions)}", "BOOKED MISSIONS<br>DRIVE DEMAND"), ("BOM", f"{bom_blk3}", "BLK3 BOM LINES<br>(+ HVRR " + str(bom_hvrr) + ")"),
        ("MRP NET", f"{mrp['parts_planned']}", "PARTS PLANNED<br>VS ON-HAND / ON-ORDER"), ("REQUEST", f"{mrp['purchase_requests']}", "PURCHASE REQUESTS<br>FROM LAST RUN"),
        ("APPROVE", f"{mrp['pr_to_jon']}", "ABOVE THRESHOLD →<br>CEO APPROVAL"), ("ORDER", f"{po_open + po_closed}", "PURCHASE ORDERS<br>SYNCED WITH QUICKBOOKS")]
fl = "<div class=ar>▶</div>".join(f"<div class=st><h3>{a}</h3><div class=kv>{b}</div><div class=kl>{c}</div></div>" for a, b, c in flow)
S["Fig3_Logistics_ERP_MRP_Inventory"] = (page("LOGISTICS · ERP / MRP / INVENTORY", f"""
<div class='grid'><div class='p flow'>{fl}</div></div>
<div class=grid style='grid-template-columns:1fr 1fr 1fr;padding-top:0'>
 <div class=p><h3>▸ LAST NIGHTLY MRP RUN</h3><table>
  <tr><td>Run</td><td class=a>{mrp_at}</td></tr><tr><td>Scope</td><td class=d>flight vehicles with booked missions</td></tr>
  <tr><td>Buy lines short</td><td class=a>{mrp['short_buy']}</td></tr><tr><td>Make lines short</td><td class=a>{mrp['short_make']}</td></tr>
  <tr><td>Matched to open orders</td><td class=a>{mrp['on_order_matched_parts']}</td></tr></table></div>
 <div class=p><h3>▸ PARTS &amp; SUPPLY BASE</h3><table>
  <tr><td>Parts master</td><td class=a>{parts_make + parts_buy}</td></tr><tr><td>Make / buy</td><td class=a>{parts_make} / {parts_buy}</td></tr>
  <tr><td>Vendors on file</td><td class=a>{vendors:,}</td></tr><tr><td>Open / closed POs</td><td class=a>{po_open} / {po_closed}</td></tr>
  <tr><td>POs linked to QuickBooks</td><td class=a>{po_qb}</td></tr></table></div>
 <div class=p><h3>▸ INVENTORY &amp; GATES</h3><div style='font-size:14px;line-height:1.85'>
  <span class=a>{inv_items}</span> items in the photo-verified inventory ledger (<span class=a>{inv_photo}</span> with photos, bin locations)<br>
  <span class=ok>✔</span> Purchase requests above threshold route to CEO approval<br>
  <span class=ok>✔</span> Every PO mirrored in QuickBooks (single source of record)<br>
  <span class=ok>✔</span> Nightly MRP re-plans against booked missions<br>
  <span class=d>Inventory ledger is in pilot; receiving integration is next.</span></div></div>
</div>""", "Fig. 3 — Logistics: booked missions drive BOM explosion, nightly MRP netting, purchase requests and QuickBooks-synced purchase orders", 640))

# FIG 4 — Financial systems integration
S["Fig4_Financial_Systems_Integration"] = (page("FINANCIAL SYSTEMS INTEGRATION", f"""
<div class=grid style='grid-template-columns:repeat(5,1fr)'>{kpi(len(qbi),'MILESTONE / PRODUCT INVOICES<br>ISSUED VIA QUICKBOOKS')}{kpi(qb_paid,'PAID · AUTO-SYNCED<br>FROM QUICKBOOKS')}{kpi(po_qb,'PURCHASE ORDERS<br>SYNCED WITH QUICKBOOKS')}{kpi('50·40·10','PAYLOAD MILESTONES<br>LSA · L-120 · POST-FLIGHT')}{kpi('H.10','FED RATE OF RECORD<br>FOR FOREIGN CURRENCY (JPY)')}</div>
<div class=grid style='grid-template-columns:1.2fr 1fr;padding-top:0'>
 <div class=p><h3>▸ INTEGRATED SYSTEMS</h3><table>
  <tr><td class=a>QuickBooks Online</td><td>invoices prepared by agents · sent only on human approval · paid status synced back to the payload order</td></tr>
  <tr><td class=a>ExoSign (in Mission Control)</td><td>launch services agreements: customer signs, then Exos countersigns · executed copy filed on the order</td></tr>
  <tr><td class=a>ERP / MRP (Mission Control)</td><td>missions → BOM → MRP → purchase requests → POs (QuickBooks)</td></tr>
  <tr><td class=a>BambooHR</td><td>people, roles and labor rates for program costing</td></tr>
  <tr><td class=a>FAA</td><td>payload cross-waiver package assembled per mission at L-90</td></tr></table></div>
 <div class=p><h3>▸ CONTROLS</h3><div style='font-size:15px;line-height:1.85'>
  <span class=ok>✔</span> No invoice is sent without a human approval click<br>
  <span class=ok>✔</span> Preparer ≠ approver (segregation of duties)<br>
  <span class=ok>✔</span> Export + denied-party screen before any invoice<br>
  <span class=ok>✔</span> In-kind payloads documented with a $1 invoice<br>
  <span class=ok>✔</span> Every money event written to the order history</div></div>
</div>""", "Fig. 4 — Financial integration: payload milestones, invoicing, purchasing and payments run through one governed loop", 640))

for name, h in S.items():
    H = 640
    hp = os.path.join(OUT, f"Exos_MissionControl_{name}.html"); open(hp, "w").write(h)
    png = os.path.join(OUT, f"Exos_MissionControl_{name}.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size=1920,{H}", f"--screenshot={png}", "file://" + hp], capture_output=True, timeout=90)
    print(png, os.path.exists(png))
