#!/usr/bin/env python3
"""Branded Exos Capabilities Statement - single full page, print-readable, real hardware imagery."""
import base64, os, subprocess
ROOT="/Users/exomac/.openclaw/workspace"
def b64(p):
    d=base64.b64encode(open(os.path.join(ROOT,p),"rb").read()).decode()
    e=os.path.splitext(p)[1].lstrip(".").lower(); m="jpeg" if e in("jpg","jpeg") else e
    return f"data:image/{m};base64,{d}"
LOGO=b64("ExosLogo_navy.png"); ASCENT=b64("media/blk3-footage/SARGE_ascent.jpg")
SEP=b64("media/blk3-footage/SARGE_separation_moneyshot.jpg")
CANOPY=b64("media/blk3-footage/SARGE_rocket_under_canopy.jpg")
HOVER=b64("assets/blk3_hover.png")

html=f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
@page{{size:Letter;margin:0.4in 0.6in}}
*{{box-sizing:border-box}}
body{{font-family:"Helvetica Neue",Arial,sans-serif;color:#14202e;font-size:10.2px;line-height:1.27;margin:0}}
.brandbar{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #c8102e;padding-bottom:6px;margin-bottom:8px}}
.lockup{{display:flex;align-items:center;gap:11px}}
.lockup img{{height:44px}}
.wordmark{{font-weight:800;letter-spacing:1.6px;color:#0b2a4a;font-size:17px;line-height:1}}
.wordmark small{{display:block;font-weight:600;letter-spacing:.6px;color:#c8102e;font-size:8.4px;margin-top:2px}}
.docref{{text-align:right;font-size:10px;color:#5a6675;font-weight:700;letter-spacing:1.2px;text-transform:uppercase}}
.hero{{position:relative;border-radius:3px;overflow:hidden;margin:0 0 9px}}
.hero img{{width:100%;height:104px;object-fit:cover;display:block}}
.hero .ov{{position:absolute;left:0;bottom:0;right:0;background:linear-gradient(transparent,rgba(11,42,74,.86));color:#fff;padding:18px 16px 10px}}
.hero .ov h1{{margin:0;font-size:20px;letter-spacing:.3px}}
.hero .ov p{{margin:3px 0 0;font-size:11px;color:#dce6f0;font-weight:600}}
h2{{font-size:11.5px;color:#0b2a4a;border-bottom:1.5px solid #d7dee7;padding-bottom:2px;margin:6px 0 3px;text-transform:uppercase;letter-spacing:.6px}}
p{{margin:0 0 4px}}
ul{{margin:0 0 4px;padding-left:16px}} li{{margin:0 0 2.5px}}
.two{{display:flex;gap:18px}} .two .col{{flex:1}}
.stats{{display:flex;gap:6px;margin:2px 0 6px}}
.stat{{flex:1;border:1px solid #cdd6e0;border-top:3px solid #c8102e;border-radius:3px;padding:6px 4px;text-align:center;background:#fbfcfd}}
.stat .n{{font-size:19px;font-weight:800;color:#0b2a4a;line-height:1.05}}
.stat .l{{font-size:8px;color:#5a6675;text-transform:uppercase;letter-spacing:.4px;margin-top:3px}}
.figrow{{display:flex;gap:9px;margin:4px 0 6px}}
.fig{{flex:1;border:1px solid #cdd6e0;border-radius:3px;overflow:hidden;background:#0b2a4a}}
.fig img{{width:100%;height:76px;object-fit:cover;display:block}}
.fig .cap{{font-size:8.6px;color:#e9eef4;background:#0b2a4a;padding:5px 7px;line-height:1.4}}
.fig .cap b{{color:#fff}}
.databand{{border:1px solid #cdd6e0;background:#f5f8fb;border-left:4px solid #0b2a4a;padding:7px 11px;font-size:9.4px;margin:6px 0 0;line-height:1.5}}
.databand b{{color:#0b2a4a}}
.diff b{{color:#0b2a4a}}
.foot{{margin-top:6px;border-top:1px solid #cdd6e0;padding-top:5px;font-size:8.1px;color:#5a6675;line-height:1.4}}
</style></head><body>

<div class="brandbar">
  <div class="lockup"><img src="{LOGO}"><div class="wordmark">EXOS AEROSPACE<small>SYSTEMS &amp; TECHNOLOGIES, INC.</small></div></div>
  <div class="docref">Capabilities Statement</div>
</div>

<div class="hero"><img src="{ASCENT}"><div class="ov">
  <h1>Reusable Suborbital Flight-Test Infrastructure</h1>
  <p>One of only three FAA-licensed reusable launch-and-recovery providers in the United States</p>
</div></div>

<div class="stats">
  <div class="stat"><div class="n">1 of 3</div><div class="l">FAA-licensed reusable providers (US)</div></div>
  <div class="stat"><div class="n">4</div><div class="l">SARGE flights flown</div></div>
  <div class="stat"><div class="n">12 mo</div><div class="l">BLK3 concept to hover</div></div>
  <div class="stat"><div class="n">&minus;29%</div><div class="l">structure weight, +25% size</div></div>
  <div class="stat"><div class="n">100s</div><div class="l">successful in-flight relights</div></div>
</div>

<h2>Company Overview</h2>
<p>Exos Aerospace is an FAA-licensed reusable suborbital launch operator providing wet-lease flight-test infrastructure for space and defense applications. Exos delivers flight-proven reusable launch platforms that increase national test cadence, enable rapid iteration, and support payload recovery and operational learning.</p>

<h2>Core Capabilities</h2>
<div class="two"><div class="col"><ul>
<li>Reusable suborbital launch vehicle operations</li>
<li>Wet-lease flight-test services for space and defense systems</li>
<li>NASA and DoD mission execution and contract performance</li>
</ul></div><div class="col"><ul>
<li>Type V linerless composite pressurized structures</li>
<li>Fractional parts-count architectures enabling repeatable reuse</li>
<li>LOX/methane propulsion integration and cryogenic Type V pressurized structures</li>
</ul></div></div>

<div class="figrow">
  <div class="fig"><img src="{SEP}"><div class="cap"><b>Flight heritage.</b> Onboard view of a suborbital mission above the atmosphere &mdash; four SARGE flights of demonstrated reusable operations.</div></div>
  <div class="fig"><img src="{CANOPY}"><div class="cap"><b>Recovery &amp; reuse.</b> Guided-parafoil recovery returns the vehicle and payload intact for rapid turnaround.</div></div>
  <div class="fig"><img src="{HOVER}"><div class="cap"><b>Integrated &amp; test-ready.</b> BLK3 PSRLV vertical for integrated test &mdash; concept to powered hover in 12 months.</div></div>
</div>

<h2>Operational Differentiators</h2>
<p class="diff"><b>Cadence-focused infrastructure.</b> Operational flight platforms designed for repeatability rather than one-off launches, enabling faster campaign iteration and reduced program risk.</p>
<p class="diff"><b>Wet-lease integration model.</b> Exos operates and maintains the vehicle, reducing integration burden and accelerating timelines for government and commercial payload customers.</p>
<p class="diff"><b>Integrated composite structures.</b> Through its ownership position in Scorpius Space Launch Company, Exos strengthens industrial depth in Type V composite pressurized structures and scalable manufacturing capability.</p>
<p class="diff"><b>RDRE-aligned flight-test capability.</b> Exos is under contract with the U.S. Department of Defense to develop the flight vehicle for flight demonstration of a government-furnished LOX/methane Rotating Detonation Rocket Engine (RDRE), where repeatable operations, rapid turnaround, and practical test execution are critical.</p>

<h2>Program Execution &amp; Flight Heritage</h2>
<div class="two"><div class="col"><ul>
<li>Flew SARGE four times, demonstrating reusable suborbital launch operations and repeatable flight execution.</li>
<li>Developed BLK3 from concept to hover in 12 months under a USAF Phase II SBIR, validating integrated pressurized structures with a 25% size increase and 29% weight reduction.</li>
<li>NASA contract performance and suborbital research mission support.</li>
</ul></div><div class="col"><ul>
<li>Northrop Grumman Lunar Lander Challenge &mdash; 1st place (Round 1), 2nd place (Round 2).</li>
<li>Pioneering work in supersonic suborbital launch vehicles and modular vehicle architectures.</li>
<li>Propulsion heritage spanning hundreds of engines (including LOX/methane) and more than a dozen flying vehicles, with hundreds of successful in-flight relights.</li>
</ul></div></div>

<div class="databand">
<b>CAGE:</b> 7EMY6 &nbsp;|&nbsp; <b>UEI:</b> CK24BPZGF854 &nbsp;|&nbsp; <b>PSC:</b> 1725, 1340, 2645, 1675, AR15 &nbsp;|&nbsp; <b>NAICS:</b> 336414, 336415, 541715, 927110<br>
<b>Contact:</b> John M. Quinn, Cofounder &amp; CEO &nbsp;&middot;&nbsp; 299 FM 1903, Greenville, TX 75402 &nbsp;&middot;&nbsp; jquinn@exosaero.com &nbsp;&middot;&nbsp; 972-740-8355 &nbsp;&middot;&nbsp; www.exosaero.com
</div>

<div class="foot">Exos Aerospace Systems &amp; Technologies, Inc. SARGE flew four suborbital missions; BLK3 holds an FAA reusable-launch license and has demonstrated powered hover, and has not yet flown a commercial mission. The RDRE flight vehicle is under DoD contract; the RDRE itself is government-furnished. Type V composite structures are developed with affiliate Scorpius Space Launch Company (Exos holds an ownership position). CAGE 7EMY6 &mdash; UEI CK24BPZGF854.</div>

</body></html>"""
oh=os.path.join(ROOT,"drafts/EXOS_Capabilities_Statement_1PAGE.html"); open(oh,"w").write(html)
op=os.path.join(ROOT,"drafts/EXOS_Capabilities_Statement_1PAGE.pdf")
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome","--headless=new",
  "--disable-gpu","--no-sandbox",f"--print-to-pdf={op}","--no-pdf-header-footer","file://"+oh],
  check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
import re
c=re.findall(rb'/Count\s+\d+',open(op,'rb').read())
print("PDF:",op,os.path.getsize(op),"bytes  Count:",c[:1])
