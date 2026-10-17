#!/usr/bin/env python3
"""Mission Control MILITARY HUD look concepts (Jon 2026-10-16) — STATIC MOCKUPS ONLY, MC untouched.
Same home-dashboard content as build.py (10/15 concepts); four HUD symbology styles.
Renders HTML + 1600x1000 PNG per concept via headless Chrome into ./hud/."""
import os, subprocess
from build import TASKS, KPIS, ALERTS, CHROME

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hud")
os.makedirs(OUT, exist_ok=True)

THEMES = {
 "1_Fighter_HUD_Green": dict(
   name="1 · FIGHTER HUD", sub="F-16/F-35 style: phosphor green vector lines on black, no fills, heading tape, target brackets",
   bg="#000805", fg="#3dff7a", fg2="#3dff7a", warn="#ffd23d", crit="#ff4040", dim="#1f8f45", fill="transparent",
   glow="0 0 4px #3dff7a, 0 0 10px rgba(61,255,122,.45)", font="'Menlo','SF Mono',monospace", ladder=True, tape=True),
 "2_Apache_MFD_Amber": dict(
   name="2 · COCKPIT MFD", sub="Apache/F-15E multifunction display: amber on black, bezel button labels on every panel",
   bg="#050302", fg="#ffb000", fg2="#ffd27a", warn="#ffffff", crit="#ff4a2a", dim="#8a5f12", fill="rgba(255,176,0,.035)",
   glow="0 0 5px rgba(255,176,0,.55)", font="'Menlo','SF Mono',monospace", bezel=True),
 "3_Helmet_HMD_Cyan": dict(
   name="3 · HELMET DISPLAY (HMD)", sub="JHMCS/F-35 helmet: cyan-white symbology over dark glass, reticle, range rings",
   bg="radial-gradient(ellipse at 50% 45%,#0b1d2b 0%,#03080d 70%)", fg="#7fe9ff", fg2="#e9fbff", warn="#ffd23d", crit="#ff5470",
   dim="#3d7d93", fill="rgba(127,233,255,.04)", glow="0 0 6px rgba(127,233,255,.6)", font="'Avenir Next Condensed','Arial Narrow',sans-serif",
   reticle=True, tape=True),
 "4_Night_Ops_Red": dict(
   name="4 · NIGHT OPS", sub="low-light red symbology (keeps night vision), dimmest of the four, for 24/7 wall display",
   bg="#060000", fg="#ff3b30", fg2="#ff8a80", warn="#ffb3ab", crit="#ffffff", dim="#7a1a15", fill="rgba(255,59,48,.03)",
   glow="0 0 4px rgba(255,59,48,.5)", font="'Menlo','SF Mono',monospace", ladder=True),
}


def html(t):
    rows = "".join(
        f"<tr><td class=sc>{s}</td><td>{('<span class=tgt>' + n + '</span>') if i == 0 else n}</td><td class=dim>{o}</td>"
        f"<td><span class='pill p{p}'>{p}</span></td></tr>" for i, (s, n, o, p) in enumerate(TASKS))
    kpis = "".join(f"<div class='kpi box'><div class=kv>{v}</div><div class=kl>{k}</div></div>" for k, v in KPIS)
    def bar(label, pct):
        return (f"<div class=br><span class=bl>{label}</span><span class=bt>"
                + "".join(f"<i class='{'on' if j < pct // 10 else ''}'></i>" for j in range(10))
                + f"</span><span class=bp>{pct:03d}</span></div>")
    tape = ""
    if t.get("tape"):
        ticks = "".join(f"<span class=tk>{h:03d}</span>" for h in range(330, 360, 5)) + "".join(f"<span class=tk>{h:03d}</span>" for h in range(0, 35, 5))
        tape = f"<div class=tape><div class=tks>{ticks}</div><div class=caret>▼ 012</div></div>"
    ladder = ""
    if t.get("ladder"):
        ladder = "<div class=ladder>" + "".join(f"<div class=rung><span>{v}</span><b></b><b></b><span>{v}</span></div>" for v in (10, 5, -5, -10)) + "</div>"
    reticle = "<div class=reticle><div class=ring></div><div class='ring r2'></div><div class=pip>+</div><div class=rlab>543 OPPS · 6 HOT</div></div>" if t.get("reticle") else ""
    bez = (lambda labels: "<div class=bez>" + "".join(f"<span>{x}</span>" for x in labels) + "</div>") if t.get("bezel") else (lambda labels: "")
    ticker = "  ◆  ".join(ALERTS)
    side_sym = reticle or ladder
    return f"""<!doctype html><html><head><meta charset=utf-8><style>
*{{box-sizing:border-box}}
body{{margin:0;width:1600px;height:1000px;overflow:hidden;background:{t['bg']};color:{t['fg']};font-family:{t['font']};letter-spacing:.06em;text-shadow:{t['glow']}}}
.box{{position:relative;background:{t['fill']};border:1px solid {t['dim']};padding:14px 16px}}
.box:before,.box:after{{content:'';position:absolute;width:14px;height:14px;border:2px solid {t['fg']};box-shadow:{t['glow']}}}
.box:before{{top:-2px;left:-2px;border-right:0;border-bottom:0}} .box:after{{bottom:-2px;right:-2px;border-left:0;border-top:0}}
header{{display:flex;align-items:center;justify-content:space-between;padding:12px 24px;border-bottom:1px solid {t['dim']}}}
.brand{{font-size:24px;letter-spacing:.3em;color:{t['fg2']}}} .brand small{{display:block;font-size:11px;letter-spacing:.3em;color:{t['dim']};text-shadow:none}}
.tag{{font-size:12px;letter-spacing:.22em}}
.tape{{position:relative;height:38px;margin:0 24px;border-bottom:1px solid {t['dim']};overflow:hidden}}
.tks{{display:flex;justify-content:space-between;padding:4px 120px 0;font-size:12px;color:{t['dim']}}} .tk{{border-left:1px solid {t['fg']};padding-left:4px;height:16px}}
.caret{{position:absolute;left:50%;transform:translateX(-50%);bottom:0;font-size:13px;color:{t['fg2']};border:1px solid {t['fg']};padding:0 6px;background:#000}}
.wrap{{padding:14px 24px;display:grid;grid-template-columns:2fr 1fr;gap:16px}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;grid-column:1/3}}
.kv{{font-size:30px;color:{t['fg2']};font-variant-numeric:tabular-nums}} .kl{{font-size:11px;letter-spacing:.22em;color:{t['dim']};text-shadow:none;margin-top:3px}}
h3{{margin:0 0 10px;font-size:13px;letter-spacing:.28em;font-weight:400;color:{t['fg2']}}}
table{{width:100%;border-collapse:collapse;font-size:15px}} td{{padding:8px;border-bottom:1px dashed {t['dim']}}}
.sc{{color:{t['fg2']};width:60px;font-size:18px}} .dim{{color:{t['dim']};text-shadow:none}}
.tgt{{outline:1px solid {t['warn']};outline-offset:4px;color:{t['warn']}}}
.pill{{font-size:11px;letter-spacing:.18em;padding:2px 7px;border:1px solid}} .pCRIT{{color:{t['crit']};border-color:{t['crit']}}} .pHIGH{{color:{t['warn']};border-color:{t['warn']}}} .pMED{{color:{t['dim']};border-color:{t['dim']}}}
.side{{display:flex;flex-direction:column;gap:16px}} .dec{{font-size:14px;line-height:1.7}}
.row3{{grid-column:1/3;display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}}
.br{{display:flex;align-items:center;gap:10px;margin:8px 0;font-size:13px}} .bl{{width:170px;color:{t['dim']};text-shadow:none}}
.bt{{flex:1;display:flex;gap:3px}} .bt i{{flex:1;height:10px;border:1px solid {t['dim']}}} .bt i.on{{background:{t['fg']};border-color:{t['fg']};box-shadow:{t['glow']}}} .bp{{width:36px;text-align:right}}
.ladder{{height:210px;display:flex;flex-direction:column;justify-content:space-around;padding:0 10px}}
.rung{{display:flex;align-items:center;gap:8px;font-size:12px}} .rung b{{flex:1;height:0;border-top:2px solid {t['fg']}}} .rung:nth-child(n+3) b{{border-top-style:dashed}}
.reticle{{position:relative;height:230px}} .ring{{position:absolute;left:50%;top:50%;width:200px;height:200px;margin:-100px;border:1px solid {t['fg']};border-radius:50%}}
.r2{{width:110px;height:110px;margin:-55px;border-style:dashed}} .pip{{position:absolute;left:50%;top:50%;transform:translate(-50%,-55%);font-size:28px;color:{t['fg2']}}}
.rlab{{position:absolute;bottom:0;width:100%;text-align:center;font-size:11px;letter-spacing:.22em}}
.bez{{display:flex;justify-content:space-between;margin:-6px -6px 8px;font-size:10px;letter-spacing:.15em}} .bez span{{border:1px solid {t['dim']};padding:1px 6px;color:{t['fg2']}}}
.ticker{{position:absolute;bottom:0;left:0;right:0;padding:9px 24px;border-top:1px solid {t['dim']};color:{t['warn']};font-size:14px;white-space:nowrap;overflow:hidden}}
.label{{position:absolute;top:56px;right:24px;font-size:11px;color:{t['dim']};text-shadow:none;letter-spacing:.12em}}
</style></head><body>
<header><div class=brand>EXOS MISSION CONTROL<small>OPERATIONS COMMAND · INTERNAL</small></div>
<div class=tag>{t['name']}</div><div class=tag>CDT 21:58 · UTC 02:58 · JST 11:58</div></header>
<div class=label>{t['sub']}</div>
{tape}
<div class=wrap>
<div class=kpis>{kpis}</div>
<div class=box>{bez(['TGT','SORT','OWNR','FLTR','BACK'])}<h3>▸ PRIORITY TARGETS · MISSION SCORE</h3><table>{rows}</table></div>
<div class=side>{('<div class=box>' + side_sym + '</div>') if side_sym else ''}<div class='box dec'>{bez(['DEC','APRV','HOLD'])}<h3>▸ DECISIONS AWAITING CEO</h3>D-7282118 · EXOS-FIN-004 intl payments<br>D-7282081 · exo3 code audit remediation<br>D-7282050 · Payload manual Rev5<br>D-7282042 · Minutes correction to Neil</div></div>
<div class=row3>
 <div class=box>{bez(['FLT','HLTH','LOG'])}<h3>▸ AGENT FLEET HEALTH</h3>{bar("Capture agents",96)}{bar("Decision guards",100)}{bar("Finance / QB",92)}{bar("Payload order-to-cash",88)}{bar("exo3 code coverage",11)}</div>
 <div class=box>{bez(['PIPE','STG','$'])}<h3>▸ PIPELINE BY STAGE</h3>{bar("New · 623",100)}{bar("Draft · 38",40)}{bar("Active · 15",22)}{bar("Submitted · 6",12)}{bar("Awarded · 1",4)}</div>
 <div class='box dec'>{bez(['T-','CAL','WK'])}<h3>▸ T-MINUS · NEXT 7 DAYS</h3>10/19 · OSP-4 on-ramp focus due<br>10/21 · Investor update + annual-meeting save-the-date<br>10/22 · BOREALIS/MSGC follow-up<br>10/23 · Innovation Dojo JPY 1M grant (5 pm JST)<br>10/26 · FAA-2026-9736 RFI comment deadline</div>
</div>
</div>
<div class=ticker>⚠ MASTER CAUTION  ◆  {ticker}</div>
</body></html>"""


for key, t in THEMES.items():
    hp = os.path.join(OUT, f"MC_HUD_{key}.html"); open(hp, "w").write(html(t))
    png = os.path.join(OUT, f"MC_HUD_{key}.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1600,1000",
                    f"--screenshot={png}", "file://" + hp], capture_output=True, timeout=60)
    print(png, os.path.exists(png))
