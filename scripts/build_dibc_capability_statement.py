#!/usr/bin/env python3
"""Build the Exos DIBC membership 'Business & Capabilities' statement (HTML -> PDF, Chrome headless).
Public-releasable: NO CUI / proprietary. Current brand (black/grey base + orange accent, black logo)."""
import base64, os, subprocess, time

WS = "/Users/exomac/.openclaw/workspace"
LOGO = os.path.join(WS, "drafts/_exos_black_official.png")
OUT_HTML = os.path.join(WS, "drafts/Exos_DIBC_Business_Capabilities_Statement_2026-09-27.html")
OUT_PDF = os.path.join(WS, "drafts/Exos_DIBC_Business_Capabilities_Statement_2026-09-27.pdf")
ORANGE = "#F26A21"

logo_b64 = base64.b64encode(open(LOGO, "rb").read()).decode()

HTML = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><style>
@page{{size:Letter;margin:0.5in 0.62in}}
*{{box-sizing:border-box}}
body{{font-family:"Helvetica Neue",Arial,sans-serif;color:#1a1a1a;font-size:10.3px;line-height:1.34;margin:0}}
.bar{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid {ORANGE};padding-bottom:8px;margin-bottom:9px}}
.bar img{{height:40px}}
.docref{{text-align:right;font-size:9px;color:#555;font-weight:700;letter-spacing:1.1px;text-transform:uppercase}}
h1{{font-size:16px;letter-spacing:.3px;color:#111;margin:0 0 2px}}
.sub{{font-size:9.2px;color:#555;font-weight:600;margin:0 0 8px}}
.ids{{background:#111;color:#fff;font-size:8.6px;letter-spacing:.3px;padding:5px 9px;border-radius:3px;margin:0 0 10px}}
.ids b{{color:{ORANGE}}}
h2{{font-size:10.6px;color:#111;border-bottom:1.4px solid #d7d7d7;padding-bottom:2px;margin:9px 0 4px;text-transform:uppercase;letter-spacing:.7px}}
h2 span{{color:{ORANGE}}}
p{{margin:0 0 4px}} ul{{margin:0 0 4px;padding-left:15px}} li{{margin:0 0 2.6px}}
.stats{{display:flex;gap:7px;margin:2px 0 8px}}
.stat{{flex:1;border:1px solid #d0d0d0;border-top:3px solid {ORANGE};border-radius:3px;padding:6px 5px;text-align:center;background:#fafafa}}
.stat .n{{font-size:15px;font-weight:800;color:#111;line-height:1.05}}
.stat .l{{font-size:7.4px;color:#555;text-transform:uppercase;letter-spacing:.3px;margin-top:3px}}
.two{{display:flex;gap:16px}} .two .col{{flex:1}}
table{{width:100%;border-collapse:collapse;margin:1px 0 4px}}
td,th{{border:1px solid #d0d0d0;padding:3px 6px;font-size:9px;vertical-align:top;text-align:left}}
th{{background:#111;color:#fff;text-transform:uppercase;letter-spacing:.4px;font-size:8.2px}}
.note{{font-size:8px;color:#666;font-style:italic;margin-top:2px}}
.foot{{border-top:2px solid {ORANGE};margin-top:10px;padding-top:6px;font-size:8.4px;color:#444;display:flex;justify-content:space-between}}
.rel{{background:#fff3ea;border:1px solid {ORANGE};border-radius:3px;padding:5px 8px;font-size:8.4px;color:#7a3b12;margin:8px 0 0}}
</style></head><body>

<div class="bar">
  <img src="data:image/png;base64,{logo_b64}" alt="Exos Aerospace">
  <div class="docref">DIBC Membership<br>Business &amp; Capabilities</div>
</div>

<h1>Exos Aerospace Systems &amp; Technologies, Inc.</h1>
<p class="sub">Business &amp; Capabilities Statement for the Defense Industrial Base Consortium (DIBC) &middot; September 2026</p>

<div class="ids">
<b>CAGE</b> 7EMY6 &nbsp;|&nbsp; <b>UEI</b> CK24BPZGF854 &nbsp;|&nbsp; <b>SBC</b> 001156963 &nbsp;|&nbsp;
<b>NAICS</b> 336414 (Guided Missile &amp; Space Vehicle Mfg), 541715 (R&amp;D) &nbsp;|&nbsp;
U.S.-owned &nbsp;|&nbsp; ITAR-registered &nbsp;|&nbsp; CMMC 2.0 Level 2 &nbsp;|&nbsp; SAM active
</div>

<div class="stats">
  <div class="stat"><div class="n">2018</div><div class="l">Flying reusable since (SARGE&rarr;BLK3)</div></div>
  <div class="stat"><div class="n">TRL&nbsp;9</div><div class="l">Lunar-flown Type-5 composite tanks</div></div>
  <div class="stat"><div class="n">1 of 3</div><div class="l">FAA-licensed reusable VTVL, U.S.</div></div>
  <div class="stat"><div class="n">2</div><div class="l">Lunar missions supplied (Odysseus, Athena)</div></div>
</div>

<h2><span>1.</span> Business Description</h2>
<p>Exos Aerospace is a U.S.-owned aerospace manufacturer and FAA-licensed reusable-launch operator headquartered in Greenville, Texas. Exos operates the Precision Suborbital Reusable Launch Vehicle (PSRLV) &ldquo;BLK3&rdquo; platform and is one of only three U.S. companies FAA-licensed to operate a vertical-takeoff reusable rocket with demonstrated recovery and reflight (with SpaceX and Blue Origin). Exos reached profitability in 2025. Through its 18% ownership of, and right of first refusal over, Scorpius Space Launch Company, Exos brings TRL-9 linerless (Type-5) composite pressure-vessel manufacturing &mdash; the same capability class the defense industrial base needs for domestic composite solid-rocket-motor (SRM) cases and missile structures. Exos pairs this with an AI-native production and program-management layer that compresses cost and cycle time across engineering, quality, and supply chain.</p>

<h2><span>2.</span> Relevance to the DIBC Mission</h2>
<p>Exos directly supports DIBC critical subsectors &mdash; <b>composites &amp; advanced materials, solid rocket motors / missile structures, propulsion, and resilient domestic supply chain</b>. Qualified domestic supply of filament-wound composite SRM cases is constrained; Exos/Scorpius offers U.S.-owned, domestically produced, flight-qualified linerless composite manufacturing with a room-temperature-cure resin that shows no microcracking in test &mdash; expanding surge-capable, multi-source capacity of exactly the type the DIBC and OSD Industrial Base Policy are funding.</p>

<h2><span>3.</span> Applicable Experience &amp; Core Capabilities</h2>
<div class="two"><div class="col"><ul>
<li><b>Linerless (Type-5) composite manufacturing</b> &mdash; all-composite, mandrel-wound pressure vessels; directly transferable to SRM cases and missile bodies.</li>
<li><b>Room-temperature-cure resin</b> &mdash; reduces large-autoclave dependence, cost, and cycle time; no microcracking observed in test.</li>
<li><b>Filament winding &amp; large composite structures</b> &mdash; production tooling and mandrels across geometries.</li>
</ul></div><div class="col"><ul>
<li><b>Reusable VTVL flight operations</b> &mdash; recovery, refurbishment, and reflight; minimal launch infrastructure (pad + power/comms).</li>
<li><b>Propulsion test hosting</b> &mdash; reusable flight test-bed for advanced-propulsion evaluation &amp; validation (RDRE) under an active USAF SBIR Phase II.</li>
<li><b>Domestic, export-compliant</b> &mdash; U.S.-owned; ITAR-registered; CMMC 2.0 Level 2; NDE / first-article qualification discipline.</li>
</ul></div></div>

<h2><span>4.</span> Government Contracts &amp; Authorizations</h2>
<table>
<tr><th>Instrument</th><th>Number / Reference</th><th>Scope</th></tr>
<tr><td>USAF AFRL SBIR Phase II ($1.90M, 2025)</td><td>FA9300-25-C-6022</td><td>Suborbital Hover Vehicle &ndash; Reusable Rocket (HVRR): reusable test-bed to evaluate &amp; validate an RDRE for DoD hypersonic test objectives (active).</td></tr>
<tr><td>USAF SBIR Phase I ($189K, 2024)</td><td>FA9300-24-P-6006</td><td>Evaluation &amp; design of the EXOS hover vehicle to validate an RDRE for DoD TRSA / hypersonic test-bed objectives (completed; led to Phase II).</td></tr>
<tr><td>USAF AFWERX SBIR Phase II ($750K, 2021)</td><td>FA8649-21-P-0838</td><td>Prototype mobile, low-cost, ultra-lightweight hypersonic reusable launch vehicle.</td></tr>
<tr><td>USAF AFWERX SBIR Phase I ($50K, 2020)</td><td>FA8649-20-P-0799</td><td>Reusable launch vehicle.</td></tr>
<tr><td>SBIR Phase III sole-source eligibility</td><td>15 U.S.C. &sect; 638(r), under FA9300-25-C-6022</td><td>Sole-source Phase III authority for any federal agency for work within that Phase II scope &mdash; no J&amp;A, no ceiling.</td></tr>
<tr><td>FAA Reusable Launch Vehicle License</td><td>Issued March 2026</td><td>Commercial authority to operate the reusable BLK3 suborbital vehicle.</td></tr>
<tr><td>AFRL Letter of Support (TACFI)</td><td>Received May 28, 2026</td><td>AFRL endorsement of the reusable-launch / RDRE test effort.</td></tr>
</table>
<p class="note">Contract numbers shown are Government-awarded, obligated USAF SBIR awards (verified via USASpending.gov, UEI CK24BPZGF854; ~$2.89M total). No CUI or proprietary contract detail is included.</p>

<h2><span>5.</span> Previous Technical Accomplishments</h2>
<ul>
<li><b>TRL-9 lunar flight heritage (composites):</b> Scorpius linerless Type-5 tanks flew as the fuel and LOX tanks on Intuitive Machines&rsquo; <b>Odysseus</b> and <b>Athena</b> lunar landers &mdash; flight-critical pressurized composite structures proven in space.</li>
<li><b>Reusable suborbital flight since 2018:</b> demonstrated recovery and reflight of a vertical-takeoff rocket (SARGE, evolved into the BLK3 platform); rapid-turnaround reusability, including a USAF-funded multi-flight rapid-reuse demonstration.</li>
<li><b>First contracted commercial launch:</b> payload flight manifested from Spaceport America, New Mexico (early 2027).</li>
<li><b>Advanced-propulsion test hosting:</b> RDRE evaluation &amp; validation on the reusable test-bed under FA9300-25-C-6022.</li>
</ul>

<h2><span>6.</span> Key Personnel &mdash; Relevant Technical Background</h2>
<ul>
<li><b>John Quinn &mdash; CEO &amp; Co-Founder:</b> 11 years building Exos to profitability; 14.5-year U.S. Navy Submarine Service; leads strategy, capital, and government relations.</li>
<li><b>Russel Blink &mdash; CTO &amp; Co-Founder:</b> Exos&rsquo;s technical bench &mdash; has built hundreds of rocket engines and dozens of flying vehicles; anchors propulsion and vehicle engineering.</li>
<li><b>Neil Milburn &mdash; COO &amp; Co-Founder:</b> longtime Armadillo Aerospace veteran; FAA liaison; operational execution and program turnarounds.</li>
<li><b>David Mitchell &mdash; President &amp; Co-Founder:</b> secured the private capital that built Exos&rsquo;s reusable rockets; leads financing and investor relations.</li>
<li><b>Kyle Ballard &mdash; CFO:</b> financial accuracy, controls, and diligence; leads public-listing readiness.</li>
</ul>

<h2><span>7.</span> Exceptional / Unique Capabilities</h2>
<ul>
<li>One of only <b>three U.S. companies</b> FAA-licensed to operate a vertical-takeoff reusable rocket with demonstrated recovery and reflight.</li>
<li><b>TRL-9, lunar-flown linerless (Type-5) composite pressure-vessel</b> manufacturing &mdash; a capability the domestic SRM-case base largely lacks.</li>
<li><b>Room-temperature-cure resin</b> with no microcracking in test &mdash; lower cost/cycle-time path for large composite structures.</li>
<li><b>AI-native production layer</b> (Mission Control) driving speed and traceability across engineering, quality, and supply chain.</li>
<li><b>Minimal-infrastructure launch</b> (pad + power/comms) and a reusable, recoverable T&amp;E test-bed for flight qualification.</li>
</ul>

<div class="rel">This document contains <b>no Controlled Unclassified Information (CUI) or proprietary information</b> and is releasable to the DIBC membership.</div>

<div class="foot">
  <div><b>Point of Contact:</b> John Quinn, Cofounder &amp; CEO &middot; jquinn@exosaero.com &middot; www.exosaero.com</div>
  <div>299 FM 1903, Greenville, TX 75402</div>
</div>

</body></html>"""

open(OUT_HTML, "w").write(HTML)
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={OUT_PDF}", "file://" + OUT_HTML],
               capture_output=True, timeout=90)
time.sleep(1)
print("PDF:", OUT_PDF, os.path.getsize(OUT_PDF) if os.path.exists(OUT_PDF) else "FAILED")
