#!/usr/bin/env python3
"""Exos Mission Control — white-paper screens in the selected 'Joint Ops Center' (C) look (Jon 2026-10-15, for the
VSFB MDZ whitepaper). Counts are LIVE from MC data at render time (/tmp/mc_live_metrics.json). Content is
EXTERNAL-SAFE: no investor/deal/personal/CUI items — work items are public-program or generic examples.
Renders 1920x1080 @2x PNG per screen via headless Chrome."""
import json, os, subprocess, datetime

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitepaper")
os.makedirs(OUT, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
M = json.load(open("/tmp/mc_live_metrics.json"))
NOW = datetime.datetime.now()
STAMP = NOW.strftime("%d %b %Y %H:%M CDT").upper()
st = dict(M["opps_by_status"])

CSS = """
*{box-sizing:border-box} body{margin:0;width:1920px;height:HPX;position:relative;overflow:hidden;background:#16181b;color:#eceff1;font-family:'Menlo','SF Mono',monospace;
 background-image:linear-gradient(rgba(255,179,71,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,179,71,.035) 1px,transparent 1px);background-size:40px 40px}
body:after{content:'';position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.06) 0 1px,transparent 1px 3px)}
.p{background:#202327;border:1px solid #3a3f45;box-shadow:none;padding:16px 18px}
header{display:flex;justify-content:space-between;align-items:center;padding:16px 28px;border-bottom:2px solid #3a3f45}
.brand{font-size:30px;letter-spacing:.3em;color:#ffb347;text-shadow:none} .brand small{display:block;font-size:12px;letter-spacing:.3em;color:#8b939b;margin-top:4px}
.y{color:#5fd3a2} .d{color:#8b939b} .g{color:#ffb347} .r{color:#ff5a5a}
h3{margin:0 0 12px;font-size:14px;letter-spacing:.28em;color:#5fd3a2}
.kv{font-size:40px;font-weight:700;color:#ffb347;text-shadow:none} .kl{font-size:12px;letter-spacing:.22em;color:#8b939b;margin-top:6px}
.grid{display:grid;gap:18px;padding:20px 28px}
table{width:100%;border-collapse:collapse;font-size:16px} td{padding:10px 8px;border-bottom:1px solid rgba(139,147,155,.22)}
.pill{font-size:11px;letter-spacing:.15em;padding:3px 8px;border:1px solid}
.foot{position:absolute;bottom:0;left:0;right:0;padding:10px 28px;border-top:2px solid #3a3f45;font-size:13px;color:#8b939b;display:flex;justify-content:space-between;background:#16181b}
.flow{display:flex;align-items:stretch;gap:0}
.stage{flex:1;text-align:center} .arrow{width:46px;display:flex;align-items:center;justify-content:center;color:#5fd3a2;font-size:30px}
.br{display:flex;align-items:center;gap:12px;margin:10px 0;font-size:14px} .bl{width:230px;color:#8b939b} .bt{flex:1;height:12px;border:1px solid rgba(139,147,155,.35)} .bf{display:block;height:100%;background:#ffb347;box-shadow:none} .bp{width:70px;text-align:right;color:#ffb347}
"""


def page(title, body, caption):
    return f"""<!doctype html><html><head><meta charset=utf-8><style>{CSS}</style></head><body>
<header><div class=brand>EXOS MISSION CONTROL<small>AI-NATIVE OPERATIONS COMMAND · {title}</small></div>
<div class=y style='letter-spacing:.2em'>LIVE · {STAMP}</div></header>{body}
<div class=foot><span>{caption}</span><span>Exos Aerospace Systems &amp; Technologies, Inc. · CAGE 7EMY6</span></div></body></html>"""


def kpi(v, k):
    return f"<div class=p><div class=kv>{v}</div><div class=kl>{k}</div></div>"


def bar(label, val, mx, txt=None):
    pct = max(2, round(100 * val / mx)) if mx else 0
    return f"<div class=br><span class=bl>{label}</span><span class=bt><span class=bf style='width:{pct}%'></span></span><span class=bp>{txt or val}</span></div>"


S = {}
# 1 — Command dashboard
rows = [("100", "OSP-4 On-Ramp submission (rolling focus)", "CEO", "HIGH"),
        ("95", "BLK3 S0 hover campaign: test readiness review", "Ops", "HIGH"),
        ("92", "VSFB MDZ whitepaper: final compliance check", "BD", "HIGH"),
        ("88", "FAA Part 450 license transition package", "Regulatory", "HIGH"),
        ("80", "University microgravity payload: integration plan", "Payload", "MED"),
        ("75", "AFRL BAA white paper: reusable flight-test platform", "BD", "MED")]
tr = "".join(f"<tr><td class=g style='font-size:20px;font-weight:800;width:70px'>{s}</td><td>{n}</td><td class=d>{o}</td><td><span class=pill style='color:{'#5fd3a2' if p=='HIGH' else '#8b939b'}'>{p}</span></td></tr>" for s, n, o, p in rows)
S["1_Command_Dashboard"] = page("COMMAND DASHBOARD", f"""
<div class=grid style='grid-template-columns:repeat(6,1fr)'>{kpi(M['tasks_open'],'OPEN WORK ITEMS')}{kpi(M['tasks_done_7d'],'CLOSED · LAST 7 DAYS')}{kpi(M['decisions_open'],'DECISIONS AWAITING HUMAN')}{kpi(M['opps'],'OPPORTUNITIES CAPTURED')}{kpi(M['agents'],'REGISTERED AI AGENTS')}{kpi(f"{M['fleet_events_7d']:,}",'AGENT EVENTS · 7 DAYS')}</div>
<div class=grid style='grid-template-columns:2fr 1fr;padding-top:0'>
 <div class=p><h3>▸ PRIORITY TARGETS · RANKED BY MISSION SCORE</h3><table>{tr}</table></div>
 <div class=p><h3>▸ HOW WORK IS RANKED</h3><div style='font-size:15px;line-height:1.75'>Every work item is scored 0–100+ on<br><span class=g>strategic fit</span> · <span class=g>contract value</span> · <span class=g>deadline urgency</span><br>· <span class=g>live signals</span> · <span class=g>aging</span>.<br><br>Overdue critical items escalate<br>above 100 and pin to the top.<br><br><span class=y>Humans set direction;<br>agents keep the board honest.</span></div></div>
</div>""", "Fig. 1 — Command dashboard: live work board ranked by Mission Score (counts live at render time)")

# 2 — Capture pipeline
S["2_Capture_Pipeline"] = page("OPPORTUNITY CAPTURE PIPELINE", f"""
<div class=grid><div class='p flow'>
 <div class=stage><h3>SENSE</h3><div class=kv>DAILY</div><div class=kl>SAM.GOV · SBIR/STTR · BAAs<br>EMAIL · CRM · NEWS</div></div><div class=arrow>▶</div>
 <div class=stage><h3>CAPTURE</h3><div class=kv>{M['opps']}</div><div class=kl>OPPORTUNITIES LOGGED</div></div><div class=arrow>▶</div>
 <div class=stage><h3>RANK</h3><div class=kv>{M['rolling']}</div><div class=kl>ROLLING · RANKED BY<br>MAX CONTRACT VALUE</div></div><div class=arrow>▶</div>
 <div class=stage><h3>DECIDE</h3><div class=kv>{M['decisions_answered_30d']}</div><div class=kl>HUMAN DECISIONS · 30 DAYS</div></div><div class=arrow>▶</div>
 <div class=stage><h3>SUBMIT</h3><div class=kv>1/WK</div><div class=kl>FOCUS SUBMITTAL TARGET<br>VERIFIED EVERY FRIDAY</div></div>
</div></div>
<div class=grid style='grid-template-columns:1fr 1fr;padding-top:0'>
 <div class=p><h3>▸ PIPELINE BY STAGE (LIVE)</h3>{bar('New / screening',st.get('NEW',0),st.get('NEW',1))}{bar('Drafting',st.get('DRAFT',0),st.get('NEW',1))}{bar('Active pursuit',st.get('ACTIVE',0),st.get('NEW',1))}{bar('Outreach sent',st.get('OUTREACH',0),st.get('NEW',1))}{bar('Submitted',st.get('SUBMITTED',0),st.get('NEW',1))}</div>
 <div class=p><h3>▸ GATES BUILT INTO THE PIPELINE</h3><div style='font-size:15px;line-height:1.8'>
 <span class=g>✔</span> Bid requirements verified verbatim first: unmet = automatic no-bid<br>
 <span class=g>✔</span> Denied-party (CSL/OFAC) screen before any outreach<br>
 <span class=g>✔</span> ITAR/EAR screen with a human Empowered Official<br>
 <span class=g>✔</span> No outbound outreach, invoice or submittal without a human approval click<br>
 <span class=g>✔</span> One focus task (priority 120, ≤5 days) on the highest-value rolling opportunity</div></div>
</div>""", "Fig. 2 — Opportunity capture: AI agents sense and rank; humans decide; one submittal closes every week")

# 3 — Recursive self-improvement / governance
v = dict(M["ledger_verdicts"])
S["3_Self_Improving_Governance"] = page("RECURSIVE SELF-IMPROVEMENT · exo3 GOVERNANCE", f"""
<div class=grid style='grid-template-columns:repeat(5,1fr)'>{kpi(M['agents'],'AGENTS IN REGISTRY<br>EACH WITH A NAMED HUMAN OWNER')}{kpi(M['agents_with_selftest'],'WITH FAILURE-REPLAY<br>OUTPUT TESTS')}{kpi(M['ledger'],'IMPROVEMENTS LOGGED<br>AS HYPOTHESES')}{kpi(f"{M['fleet_events_7d']:,}",'TRACED AGENT EVENTS<br>LAST 7 DAYS')}{kpi(M['fleet_agents_7d'],'AGENTS ACTIVE<br>LAST 7 DAYS')}</div>
<div class=grid style='grid-template-columns:1.2fr 1fr;padding-top:0'>
 <div class=p><h3>▸ THE IMPROVEMENT LOOP</h3><div style='font-size:16px;line-height:2'>
 <span class=y>1 DETECT</span>  hourly evals · commit gate · weekly code audit<br>
 <span class=y>2 FIX</span>  failure fixes ship with a test that replays the failure; a weekly code audit flags any that don't<br>
 <span class=y>3 MEASURE</span>  each fix is logged as a hypothesis with a baseline<br>
 <span class=y>4 VERDICT</span>  weekly review: improved · no change · regressed<br>
 <span class=y>5 GOVERN</span>  owner + permission envelope + escalation for every agent</div></div>
 <div class=p><h3>▸ IMPROVEMENT LEDGER VERDICTS (LIVE)</h3>{bar('Measuring',v.get('measuring',0),M['ledger'])}{bar('Improved',v.get('IMPROVED',0),M['ledger'])}{bar('No change',v.get('NO CHANGE',0),M['ledger'])}{bar('Regressed → rework',v.get('REGRESSED',0),M['ledger'])}
 <div class=d style='font-size:13px;margin-top:12px'>Regressions are surfaced, not hidden: they go back into the loop.</div></div>
</div>""", "Fig. 3 — Recursive self-improvement: every agent has a named owner; activity is traced; fixes are measured")

# 4 — Human-in-the-loop decisions
dec = [("FAA payload approval: confirm wet-signed cross-waiver on file", "Payload Ops", "HUMAN CONFIRM"),
       ("Approve procedure: international contractor payments", "CEO", "APPROVE"),
       ("Approve weekly exo3 code-audit remediation plan", "CEO", "APPROVE"),
       ("Approve & send customer invoice (QuickBooks)", "CEO", "APPROVE & SEND"),
       ("Rolling-opportunity focus: confirm submittal strategy", "CEO", "DECIDE")]
dr = "".join(f"<tr><td>{a}</td><td class=d>{b}</td><td><span class=pill style='color:#5fd3a2'>{c}</span></td></tr>" for a, b, c in dec)
S["4_Human_In_The_Loop"] = page("HUMAN-IN-THE-LOOP DECISIONS", f"""
<div class=grid style='grid-template-columns:repeat(4,1fr)'>{kpi(f"{M['decisions_total']:,}",'DECISIONS ON RECORD')}{kpi(M['decisions_answered_30d'],'DECIDED · LAST 30 DAYS')}{kpi(M['decisions_open'],'AWAITING A HUMAN NOW')}{kpi('EVERY','OUTBOUND COMMITMENT<br>GATED BY A HUMAN CLICK')}</div>
<div class=grid style='grid-template-columns:2fr 1fr;padding-top:0'>
 <div class=p><h3>▸ DECISION QUEUE (EXAMPLES)</h3><table>{dr}</table></div>
 <div class=p><h3>▸ DESIGN RULES</h3><div style='font-size:15px;line-height:1.8'>Agents prepare; <span class=g>humans decide</span>.<br>Agent answers are proposals only:<br>a card closes on a human click.<br><br>Every card carries its documents,<br>a recommendation and the trace<br>of what the agent did and why.</div></div>
</div>""", "Fig. 4 — Human-in-the-loop: agents do the work, accountable people make every outbound commitment")

for name, h in S.items():
    H = {"1_Command_Dashboard": 600, "2_Capture_Pipeline": 560, "3_Self_Improving_Governance": 560, "4_Human_In_The_Loop": 560}[name]
    h = h.replace("HPX", f"{H}px")
    hp = os.path.join(OUT, f"Exos_MissionControl_{name}.html"); open(hp, "w").write(h)
    png = os.path.join(OUT, f"Exos_MissionControl_{name}.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size=1920,{H}", f"--screenshot={png}", "file://" + hp], capture_output=True, timeout=90)
    print(png, os.path.exists(png))
