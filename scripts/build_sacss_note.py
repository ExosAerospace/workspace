#!/usr/bin/env python3
"""Build the branded SACSS Cluster-II co-measurement note (HTML -> PDF via Chrome)."""
import base64, os, subprocess

ROOT = "/Users/exomac/.openclaw/workspace"
def b64(path):
    with open(os.path.join(ROOT, path), "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "jpeg" if ext in ("jpg","jpeg") else ext
    return f"data:image/{mime};base64,{data}"

LOGO   = b64("ExosLogo_navy.png")
LIMB   = b64("media/blk3-footage/SARGE_earth_limb.jpg")
CANOPY = b64("media/blk3-footage/SARGE_rocket_under_canopy.jpg")
HOVER  = b64("assets/blk3_hover.png")

html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
@page{{size:Letter;margin:0.55in 0.7in}}
*{{box-sizing:border-box}}
body{{font-family:"Helvetica Neue",Arial,sans-serif;color:#14202e;font-size:10.3px;line-height:1.45;margin:0}}
.brandbar{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #c8102e;padding-bottom:7px;margin-bottom:9px}}
.brandbar .lockup{{display:flex;align-items:center;gap:10px}}
.brandbar img.logo{{height:38px}}
.wordmark{{font-weight:800;letter-spacing:1.5px;color:#0b2a4a;font-size:15px;line-height:1}}
.wordmark small{{display:block;font-weight:600;letter-spacing:.6px;color:#c8102e;font-size:7.6px;margin-top:2px}}
.docref{{text-align:right;font-size:8px;color:#5a6675;line-height:1.35}}
h1{{font-size:16px;margin:2px 0 1px;color:#0b2a4a;letter-spacing:.2px}}
.sub{{font-size:10px;color:#39485a;margin:0 0 8px;font-weight:600}}
h2{{font-size:11px;color:#0b2a4a;border-bottom:1.4px solid #d7dee7;padding-bottom:2px;margin:12px 0 5px;text-transform:uppercase;letter-spacing:.5px}}
p{{margin:0 0 6px}}
ul{{margin:0 0 6px;padding-left:15px}} li{{margin:0 0 3px}}
.hdrbox{{border:1px solid #cdd6e0;background:#f5f8fb;border-left:3px solid #0b2a4a;padding:7px 10px;font-size:8.9px;margin:0 0 10px;line-height:1.5}}
.hdrbox b{{color:#0b2a4a}}
.stats{{display:flex;gap:6px;margin:2px 0 10px}}
.stat{{flex:1;border:1px solid #cdd6e0;border-top:3px solid #c8102e;border-radius:2px;padding:6px 4px;text-align:center;background:#fbfcfd}}
.stat .n{{font-size:14px;font-weight:800;color:#0b2a4a;line-height:1.1}}
.stat .l{{font-size:7px;color:#5a6675;text-transform:uppercase;letter-spacing:.4px;margin-top:2px}}
.figrow{{display:flex;gap:9px;margin:6px 0 9px}}
.fig{{flex:1;border:1px solid #cdd6e0;border-radius:2px;overflow:hidden;background:#0b2a4a}}
.fig img{{width:100%;height:104px;object-fit:cover;display:block}}
.fig .cap{{font-size:7.6px;color:#e9eef4;background:#0b2a4a;padding:4px 6px;line-height:1.35}}
.fig .cap b{{color:#fff}}
.hero{{width:100%;height:150px;object-fit:cover;display:block;border-radius:2px}}
.herocap{{font-size:7.8px;color:#5a6675;margin:3px 0 2px;font-style:italic}}
.key{{background:#eef6ee;border:1px solid #bcd6bc;border-left:3px solid #2e7d32;padding:6px 9px;font-size:9.4px;margin:5px 0 6px}}
.foot{{margin-top:11px;border-top:1px solid #cdd6e0;padding-top:6px;font-size:7.6px;color:#5a6675;line-height:1.45}}
.tag{{color:#c8102e;font-weight:700}}
</style></head><body>

<div class="brandbar">
  <div class="lockup">
    <img class="logo" src="{LOGO}">
    <div class="wordmark">EXOS AEROSPACE<small>SYSTEMS &amp; TECHNOLOGIES, INC.</small></div>
  </div>
  <div class="docref">CONCEPT NOTE &middot; 24 JULY 2026<br>Companion to the AIRL Working Group Whitepaper<br>ESSC/ESF, June 2026 &middot; Zenodo 20831147</div>
</div>

<h1>SACSS &mdash; Suborbital Atmospheric Contaminant Sampling System</h1>
<div class="sub">The in-situ, physical-sample-return leg of targeted-reentry co-measurement</div>

<div class="hdrbox">
<b>Submitting Organization:</b> Exos Aerospace Systems &amp; Technologies, Inc., 299 FM 1903, Greenville, TX 75402 &nbsp;|&nbsp; <b>CAGE:</b> 7EMY6 &nbsp;|&nbsp; <b>UEI:</b> CK24BPZGF854<br>
<b>Business POC:</b> John Quinn, Cofounder &amp; CEO (jquinn@exosaero.com, 972-740-8355) &nbsp;|&nbsp; <b>Platform:</b> BLK3 PSRLV, one of only three FAA-licensed reusable launch-and-recovery vehicles in the United States
</div>

<img class="hero" src="{LIMB}">
<div class="herocap">Onboard imagery from an Exos suborbital flight above the cloud deck &mdash; the vehicle routinely transits the 40&ndash;100 km injection and ablation zone that aircraft and balloons cannot reach.</div>

<h2>Why now &mdash; a scheduled, known-composition reentry</h2>
<p>ESA is about to close its 24-year Cluster mission with a <b>rare twin targeted reentry</b> of its last two satellites, <b>Samba and Tango</b>, expected roughly 24 hours apart around <b>1 September 2026</b> over a remote stretch of the South Pacific, with an airborne observation campaign already committed. Because these are <i>targeted</i> reentries, the time, location, and vehicle composition are known in advance &mdash; exactly the controlled natural laboratory the AIRL whitepaper points to for measuring how spaceflight is loading the upper atmosphere with aluminium, copper, and lithium.</p>

<h2>The measurement gap the Cluster campaign makes concrete</h2>
<div class="figrow">
  <div class="fig"><img src="{CANOPY}"><div class="cap"><b>Guided recovery.</b> BLK3 returns under a steerable parafoil, bringing sealed sample chambers back intact for laboratory-grade composition work.</div></div>
  <div class="fig"><img src="{HOVER}"><div class="cap"><b>Reusable, recoverable vehicle.</b> The FAA-licensed BLK3 PSRLV flies and is recovered repeatedly, enabling a monitoring cadence rather than a single shot.</div></div>
</div>
<p>An airborne campaign captures a reentry <b>remotely</b> &mdash; spectroscopy, imaging, optical signatures from below. What no campaign to date captures is an <b>in-situ, altitude-resolved physical sample</b> returned intact for laboratory analysis. Aircraft (NOAA's SABRE WB-57) top out near 19 km; balloons near 35&ndash;40 km; satellites and lidar see a column, not a specimen. The community models radiative forcing and ablation chemistry largely without ground-truth material from the zone itself &mdash; the exact gap the whitepaper flags as urgent, and the gap SACSS is designed to close.</p>

<h2>What SACSS adds</h2>
<div class="stats">
  <div class="stat"><div class="n">40&ndash;100</div><div class="l">km sampling band</div></div>
  <div class="stat"><div class="n">3</div><div class="l">altitude bands</div></div>
  <div class="stat"><div class="n">2&times;</div><div class="l">ascent + descent</div></div>
  <div class="stat"><div class="n">~$250K</div><div class="l">per flight, incl. lab</div></div>
  <div class="stat"><div class="n">~8</div><div class="l">flights / year target</div></div>
</div>
<ul>
<li>Multi-stage sampler opens and seals collection chambers across three bands (40&ndash;60, 60&ndash;80, 80&ndash;100 km) on <b>ascent and descent</b>, and returns <b>intact physical samples</b> for mass spectrometry, electron microscopy, and isotopic/chemical composition.</li>
<li>Reusable cadence at a fraction of a single-shot sounding rocket ($1&ndash;5M), on a vehicle that is already FAA-licensed and flown-and-recovered.</li>
<li>Complements, does not duplicate, airborne and space-based observation: SACSS supplies the one data type they structurally cannot &mdash; a composition-grade specimen from the injection and ablation altitude.</li>
</ul>

<div class="key"><b>The co-measurement thesis:</b> the Cluster II twin reentry is not a one-off &mdash; it is the template for a recurring class of event, accelerating toward an estimated 12,000+ reentries per year by roughly 2040. Each one pairs <b>remote observation</b> (the ESA / airborne model) with <b>physical-sample return</b> (the SACSS model) into a single, complete measurement: the coordinated campaign the AIRL whitepaper calls for.</div>

<h2>Where a conversation could go</h2>
<ul>
<li>Walk the NOAA CSL / ERB team through the SACSS concept and the composition data it returns.</li>
<li>Map how a physical-sampling platform slots alongside airborne campaigns like ESA's for future targeted reentries.</li>
<li>If U.S. and European coordination is forming around the AIRL recommendations, design a U.S. physical-sampling capability in from the start rather than bolt it on later. Exos maintains a European footprint through Exos Aerospace Italia (Torino / I3P), a latent bridge to the ESSC-led side of AIRL.</li>
</ul>

<div class="foot">Forward-looking: BLK3 holds an FAA reusable-launch license and has not yet flown a commercial SACSS payload. SACSS performance figures (altitude bands, per-flight cost, cadence) are design targets pending flight demonstration. SACSS is positioned as the in-situ, physical-sample-return leg of the measurement campaign the AIRL whitepaper calls for; it is not claimed that the whitepaper endorses Exos, nor that SACSS will sample the Samba/Tango reentries. Sources: ESA Cluster reentry program (Salsa 2024, Rumba 2025, Samba/Tango ~Sept 2026); AIRL Working Group whitepaper (Zenodo 20831147); NOAA Earth's Radiation Budget Initiative (2020 congressional mandate). Exos Aerospace Systems &amp; Technologies, Inc. &mdash; CAGE 7EMY6 &mdash; UEI CK24BPZGF854.</div>

</body></html>"""

out_html = os.path.join(ROOT, "drafts/SACSS_CoMeasurement_Note_ClusterII_2026-07-24.html")
with open(out_html, "w") as f:
    f.write(html)

out_pdf = os.path.join(ROOT, "drafts/SACSS_CoMeasurement_Note_ClusterII_2026-07-24.pdf")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
    f"--print-to-pdf={out_pdf}", "--no-pdf-header-footer", "--print-to-pdf-no-header",
    "file://" + out_html], check=True,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
print("PDF:", out_pdf, os.path.getsize(out_pdf), "bytes")
