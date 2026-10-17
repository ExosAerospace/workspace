#!/usr/bin/env python3
"""Mission Control 'battle command station' look concepts (Jon 2026-10-15) — STATIC MOCKUPS ONLY, MC untouched.
One shared home-dashboard layout, four themes. Renders HTML + 1600x1000 PNG per concept via headless Chrome."""
import os, subprocess

OUT = os.path.dirname(os.path.abspath(__file__))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

TASKS = [("130", "Japan Seed Round: full package", "J. Quinn", "CRIT"),
         ("130", "GTL methane tank: Direct-to-Phase-II path", "J. Quinn", "CRIT"),
         ("127", "OSC loan: $15M ask + capital stack", "J. Quinn", "CRIT"),
         ("100", "OSP-4 On-Ramp submission (rolling focus)", "J. Quinn", "HIGH"),
         ("88", "BLK3 S0 hover campaign: test readiness", "P. Eaton", "HIGH"),
         ("75", "EXOS-FIN-004 intl payments: Wise setup", "K. Ballard", "MED")]
KPIS = [("OPEN DECISIONS", "7"), ("OVERDUE", "3"), ("ROLLING OPPS", "543"), ("PIPELINE", "$1.02B"), ("FLEET AGENTS", "268 / 0 FAIL")]
ALERTS = ["D-7282118 awaiting CEO: EXOS-FIN-004 approval", "Rolling focus: OSP-4 due 10/19", "M6 waivers: 1 of 2 wet-signed on file",
          "exo3 code audit: 70 gaps (D-7282081)", "SSLC board package r5 issued"]

THEMES = {
 "A_Imperial_Command_Bridge": dict(
   name="A · COMMAND BRIDGE", sub="gunmetal + red/amber, angled armor panels, scanlines",
   bg="#0b0d10", panel="#14181d", edge="#c0392b", accent="#ff4b3e", accent2="#ffb000", text="#e6e6e6", dim="#8a8f98",
   font="'Eurostile','Microgramma','Bank Gothic','Arial Narrow',sans-serif", grid="rgba(255,75,62,.06)",
   clip="polygon(14px 0,100% 0,100% calc(100% - 14px),calc(100% - 14px) 100%,0 100%,0 14px)", scan=True, glow="0 0 10px rgba(255,75,62,.35)"),
 "B_Holo_Tactical_Table": dict(
   name="B · HOLO TACTICAL", sub="deep navy + cyan hologram glow, radar sweep, wireframe grid",
   bg="#020a14", panel="rgba(8,30,52,.72)", edge="#1ec8ff", accent="#38e1ff", accent2="#7cffcb", text="#d8f6ff", dim="#5d8aa6",
   font="'Orbitron','Rajdhani','Avenir Next Condensed','Arial Narrow',sans-serif", grid="rgba(56,225,255,.08)",
   clip="none", scan=False, glow="0 0 14px rgba(56,225,255,.55)", radar=True),
 "C_Joint_Ops_Center": dict(
   name="C · JOINT OPS CENTER", sub="black + phosphor green, MIL-style status board, DEFCON-like readiness bar",
   bg="#000000", panel="#060c06", edge="#2bd24a", accent="#39ff6a", accent2="#ffd84a", text="#c9f7cf", dim="#4f8a57",
   font="'Menlo','SF Mono','Consolas',monospace", grid="rgba(57,255,106,.05)",
   clip="none", scan=True, glow="0 0 6px rgba(57,255,106,.45)", readiness=True),
 "D_Mission_Control_Ops": dict(
   name="D · MISSION OPS (MCC)", sub="charcoal + amber, clean flight-control consoles, big clocks, low glare",
   bg="#16181b", panel="#202327", edge="#3a3f45", accent="#ffb347", accent2="#5fd3a2", text="#eceff1", dim="#8b939b",
   font="'Inter','Helvetica Neue',Arial,sans-serif", grid="transparent",
   clip="none", scan=False, glow="none", clocks=True),
}


def bar_html(t):
    def bar(label, pct):
        return (f"<div class=br><span class=bl>{label}</span><span class=bt><span class=bf style='width:{pct}%'></span></span><span class=bp>{pct}%</span></div>")
    return bar


def html(t):
    bar = bar_html(t)
    rows = "".join(f"<tr><td class=sc>{s}</td><td>{n}</td><td class=dim>{o}</td><td><span class='pill p{p}'>{p}</span></td></tr>" for s, n, o, p in TASKS)
    kpis = "".join(f"<div class='kpi panel'><div class=kv>{v}</div><div class=kl>{k}</div></div>" for k, v in KPIS)
    ticker = "  ◆  ".join(ALERTS)
    radar = "<div class='radar panel'><div class=sweep></div><div class=blip style='top:30%;left:62%'></div><div class=blip style='top:58%;left:35%'></div></div><div class=kl style='text-align:center;margin-top:-6px'>OPPORTUNITY SCOPE · 543 ROLLING</div>" if t.get("radar") else ""
    ready = "<div class='ready panel'><span class=kl>READINESS</span>" + "".join(f"<span class='rl{' on' if i == 3 else ''}'>{i}</span>" for i in range(5, 0, -1)) + "<span class=dim style='margin-left:10px'>CON 3 · ELEVATED (BLK3 test window)</span></div>" if t.get("readiness") else ""
    clocks = "".join(f"<div class='clk panel'><div class=kv>{v}</div><div class=kl>{k}</div></div>" for k, v in [("CDT", "16:52:07"), ("UTC", "21:52:07"), ("JST", "06:52:07"), ("T- BLK3 S0", "early 2027")]) if t.get("clocks") else ""
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
*{{box-sizing:border-box}} body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{t['bg']};color:{t['text']};font-family:{t['font']};
 background-image:linear-gradient({t['grid']} 1px,transparent 1px),linear-gradient(90deg,{t['grid']} 1px,transparent 1px);background-size:40px 40px}}
.panel{{background:{t['panel']};border:1px solid {t['edge']};clip-path:{t['clip']};box-shadow:{t['glow']}}}
header{{display:flex;align-items:center;justify-content:space-between;padding:14px 24px;border-bottom:2px solid {t['edge']}}}
.brand{{font-size:26px;letter-spacing:.25em;color:{t['accent']};text-shadow:{t['glow']}}} .brand small{{display:block;font-size:11px;letter-spacing:.3em;color:{t['dim']}}}
.tag{{font-size:12px;letter-spacing:.2em;color:{t['accent2']}}}
.wrap{{padding:18px 24px;display:grid;grid-template-columns:2fr 1fr;gap:16px}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;grid-column:1/3}}
.kpi,.clk{{padding:14px 16px}} .kv{{font-size:30px;font-weight:700;color:{t['accent']};text-shadow:{t['glow']}}} .kl{{font-size:11px;letter-spacing:.2em;color:{t['dim']};margin-top:4px}}
.board{{padding:14px 16px}} h3{{margin:0 0 10px;font-size:13px;letter-spacing:.25em;color:{t['accent2']}}}
table{{width:100%;border-collapse:collapse;font-size:15px}} td{{padding:9px 8px;border-bottom:1px solid {t['edge']}33}}
.sc{{font-weight:800;color:{t['accent']};width:60px;font-size:18px}} .dim{{color:{t['dim']}}}
.pill{{font-size:11px;letter-spacing:.15em;padding:3px 8px;border:1px solid}} .pCRIT{{color:#ff5a5a;border-color:#ff5a5a}} .pHIGH{{color:{t['accent2']};border-color:{t['accent2']}}} .pMED{{color:{t['dim']};border-color:{t['dim']}}}
.side{{display:flex;flex-direction:column;gap:16px}} .dec{{padding:14px 16px;font-size:14px;line-height:1.6}}
.ticker{{position:absolute;bottom:0;left:0;right:0;padding:10px 24px;border-top:2px solid {t['edge']};color:{t['accent2']};font-size:14px;letter-spacing:.08em;white-space:nowrap;overflow:hidden;background:{t['bg']}}}
.radar{{height:230px;position:relative;border-radius:50%;width:230px;margin:0 auto;overflow:hidden;background:radial-gradient(circle,transparent 30%,{t['grid']} 31%,transparent 32%,transparent 60%,{t['grid']} 61%,transparent 62%),{t['panel']}}}
.sweep{{position:absolute;inset:0;background:conic-gradient(from 40deg,{t['accent']}66,transparent 25%)}} .blip{{position:absolute;width:9px;height:9px;border-radius:50%;background:{t['accent2']};box-shadow:0 0 10px {t['accent2']}}}
.ready{{grid-column:1/3;padding:10px 16px;display:flex;align-items:center;gap:8px}} .rl{{width:44px;text-align:center;padding:6px 0;border:1px solid {t['dim']};color:{t['dim']}}} .rl.on{{background:{t['accent2']};color:#000;border-color:{t['accent2']}}}
.clocks{{grid-column:1/3;display:grid;grid-template-columns:repeat(4,1fr);gap:12px}} .clk .kv{{font-variant-numeric:tabular-nums;font-size:34px}}
.scan:after{{content:'';position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0 1px,transparent 1px 3px)}}
.row3{{grid-column:1/3;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}} .bars{{padding:14px 16px}}
.br{{display:flex;align-items:center;gap:10px;margin:9px 0;font-size:13px}} .bl{{width:170px;color:{t['dim']}}} .bt{{flex:1;height:10px;border:1px solid {t['edge']}66}} .bf{{display:block;height:100%;background:{t['accent']};box-shadow:{t['glow']}}} .bp{{width:44px;text-align:right;color:{t['accent']}}}
.label{{position:absolute;top:58px;right:24px;font-size:12px;color:{t['dim']};letter-spacing:.15em;text-align:right}}
</style></head><body class="{'scan' if t['scan'] else ''}">
<header><div class=brand>EXOS MISSION CONTROL<small>OPERATIONS COMMAND · INTERNAL</small></div>
<div class=tag>{t['name']}</div><div class=tag>CDT 16:52 · UTC 21:52 · JST 06:52</div></header>
<div class=label>{t['sub']}</div>
<div class=wrap>
{('<div class=clocks>' + clocks + '</div>') if clocks else ''}
{ready}
<div class=kpis>{kpis}</div>
<div class='board panel'><h3>▸ PRIORITY TARGETS · MISSION SCORE</h3><table>{rows}</table></div>
<div class=side>{radar}<div class='dec panel'><h3>▸ DECISIONS AWAITING CEO</h3>D-7282118 · EXOS-FIN-004 intl payments<br>D-7282081 · exo3 code audit remediation<br>D-7282050 · Payload manual Rev5<br>D-7282042 · Minutes correction to Neil</div></div>
<div class=row3>
 <div class='panel bars'><h3>▸ AGENT FLEET HEALTH</h3>{bar("Capture agents",96)}{bar("Decision guards",100)}{bar("Finance / QB",92)}{bar("Payload order-to-cash",88)}{bar("exo3 code coverage",11)}</div>
 <div class='panel bars'><h3>▸ PIPELINE BY STAGE</h3>{bar("New · 623",100)}{bar("Draft · 38",40)}{bar("Active · 15",22)}{bar("Submitted · 6",12)}{bar("Awarded · 1",4)}</div>
 <div class='panel dec'><h3>▸ T-MINUS · NEXT 7 DAYS</h3>10/19 · OSP-4 on-ramp focus due<br>10/21 · Investor update + annual-meeting save-the-date<br>10/22 · BOREALIS/MSGC follow-up<br>10/23 · Innovation Dojo JPY 1M grant (5 pm JST)<br>Fri 16:05 · weekly rolling-submittal check</div>
</div>
</div>
<div class=ticker>⚠ ALERTS  ◆  {ticker}</div>
</body></html>"""


if __name__ == "__main__":
  for key, t in THEMES.items():
    hp = os.path.join(OUT, f"MC_Theme_{key}.html"); open(hp, "w").write(html(t))
    png = os.path.join(OUT, f"MC_Theme_{key}.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size=1600,1000", f"--screenshot={png}", "file://" + hp],
                   capture_output=True, timeout=60)
    print(png, os.path.exists(png))
