#!/usr/bin/python3
"""Build rev 2 of the DARPA NGHCM RFI response (DARPA-SN-26-93).

Per Jon's 10/6 instruction on D-7281960 / task #3444: add recovery, inspection and
72-hour reflight of BLK3 and its payloads; add Payload User Guide (July 2026) data,
figures and charts; add the suppressed-trajectory guardrail (not flown; capable).
Source PUG: mission-control/uploads/1790801413407_Exos_Payload_User_Guide_July_2026.pdf
"""
import copy, os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(W, "Exos_DARPA_NGHCM_RFI_Response_SN-26-93_2026-09-07.docx")
OUT = os.path.join(W, "Exos_DARPA_NGHCM_RFI_Response_SN-26-93_2026-10-06_rev2.docx")
FIG = os.path.join(W, "nghcm_figs")
NAVY = "#0a3d7c"

# ---------- generated charts ----------
def turnaround_chart(path):
    # Notional 72-h turnaround (design intent; PUG §2.6 + §4.5). Hours from landing.
    rows = [
        ("Landing, safing, \"Flight Secure\"", 0, 0.5),
        ("Payload removal & hand-back", 0.5, 1.5),
        ("Payload inspection / data pull", 1.0, 6),
        ("Vehicle physical inspection", 1.5, 8),
        ("Flight telemetry review", 2, 12),
        ("Install spare recovery set + charged He", 8, 20),
        ("Payload re-integration (if reflown)", 20, 26),
        ("Readiness review / range & FAA notice", 26, 40),
        ("Reflight launch window (07:00-12:00)", 46, 72),
    ]
    fig, ax = plt.subplots(figsize=(7.2, 3.3), dpi=200)
    for i, (lbl, a, b) in enumerate(rows):
        ax.barh(i, b - a, left=a, color=NAVY if i < len(rows) - 1 else "#c8102e", height=0.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 72)
    ax.set_xticks([0, 12, 24, 36, 48, 60, 72])
    ax.set_xlabel("Hours after landing", fontsize=8)
    ax.tick_params(axis="x", labelsize=7.5)
    ax.grid(axis="x", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("BLK3 notional reflight turnaround (design intent, 10-person launch team)",
                 fontsize=8.5, color="#1a1a1a")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def timeline_chart(path):
    # Mission event G-loads, PUG §2.3
    ev = [("Boost / MECO", 90, 3.8), ("Ballute peak", 330, 4.3),
          ("Main chute shock", 520, 6.8), ("Touch-down (max)", 1500, 7.0)]
    fig, ax = plt.subplots(figsize=(7.2, 2.4), dpi=200)
    ax.axvspan(130, 280, color="#e6eef8")
    ax.text(205, 7.4, "~150 s zero-G", ha="center", fontsize=7.5, color=NAVY)
    for lbl, t, g in ev:
        ax.vlines(t, 0, g, color=NAVY, linewidth=2)
        ax.plot(t, g, "o", color=NAVY, ms=4)
        ax.text(t, g + 0.25, f"{lbl}\nT+{t}s · {g} G", ha="center", fontsize=6.8)
    ax.set_xlim(0, 1600)
    ax.set_ylim(0, 9.5)
    ax.set_xlabel("Mission elapsed time (s)", fontsize=8)
    ax.set_ylabel("Peak load (G)", fontsize=8)
    ax.tick_params(labelsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


turnaround_chart(os.path.join(FIG, "gen_turnaround.png"))
timeline_chart(os.path.join(FIG, "gen_gloads.png"))

# ---------- document ----------
d = docx.Document(SRC)
P = d.paragraphs
H_T, B_T, BUL_T = P[6], P[7], P[11]          # heading / body / bullet templates
anchor = P[19]                                # "6. Export Control and Limitations"
body = anchor._p.getparent()


def _clone(tpl, text, bold_lead=None):
    el = copy.deepcopy(tpl._p)
    anchor._p.addprevious(el)
    p = docx.text.paragraph.Paragraph(el, anchor._parent)
    runs = p.runs
    for r in runs[1:]:
        r._r.getparent().remove(r._r)
    r0 = runs[0]
    if bold_lead:
        r0.text = bold_lead
        r0.bold = True
        r1 = p.add_run(text)
        r1.bold = False
        r1.font.size, r1.font.name = r0.font.size, r0.font.name
        r1.font.color.rgb = r0.font.color.rgb
    else:
        r0.text = text
    return p


def H(t):
    h = _clone(H_T, t)
    h.paragraph_format.keep_with_next = True
    return h
def B(t, lead=None): return _clone(B_T, t, lead)
def BUL(t, lead=None):
    return _clone(BUL_T, t, "•  " + lead) if lead else _clone(BUL_T, "•  " + t)


def fig(path, caption, width=6.3):
    p = _clone(B_T, "")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].add_picture(path, width=Inches(width))
    c = _clone(B_T, caption)
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.runs[0].italic = True
    c.runs[0].font.size = Pt(8.5)
    c.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def table(rows, widths=(2.2, 4.3)):
    tpl = d.tables[0]
    t = d.add_table(rows=0, cols=2)
    t.style = tpl.style
    for k, v in rows:
        cells = t.add_row().cells
        for c, txt, b in ((cells[0], k, True), (cells[1], v, False)):
            c.text = ""
            r = c.paragraphs[0].add_run(txt)
            r.bold = b
            r.font.size = Pt(9.5)
            r.font.name = "Calibri"
            r.font.color.rgb = RGBColor(0x1a, 0x1a, 0x1a)
    # copy borders/shading from the cover table if present
    tblPr_src = tpl._tbl.tblPr
    t._tbl.remove(t._tbl.tblPr)
    t._tbl.insert(0, copy.deepcopy(tblPr_src))
    for row in t.rows:
        for c, w in zip(row.cells, widths):
            c.width = Inches(w)
    anchor._p.addprevious(t._tbl)
    _clone(B_T, "")  # spacer


# ===== 6. Vehicle & environment data =====
H("6.  BLK3 Vehicle and Flight-Environment Data")
B("The data below are drawn from the Exos BLK3 Payload User Guide (July 2026, approved for public "
  "release). BLK3 is a single-stage, pressure-fed LOX/ethanol vehicle of carbon-fiber composite "
  "construction. It traces directly to a 2021 U.S. Air Force contract to build BLK3 as a concept "
  "ground-launched hypersonic test vehicle; its precursor, SARGE, flew four times from Spaceport America.")
table([
    ("Design reference mission", "135 kg payload to 100 km apogee (Spaceport America, NM)"),
    ("Heavy-payload mission", "Up to 200 kg to ~80 km (NASA Flight Opportunities class)"),
    ("Payload bay", "636 mm (25.04 in) ID × 1,219 mm (48 in); standard 20 in adapter plate"),
    ("Vehicle", "Single stage, pressure-fed LOX/ethanol; 635 mm (25 in) dia.; 10.82 m stack"),
    ("Boost / coast", "MECO ≈ T+90 s at 3.8 G; peak velocity ≈ 1,100 m/s"),
    ("Microgravity", "~150 s zero-G (T+130 to T+280 s), payload-mass dependent"),
    ("Peak loads", "Ballute 4.3 G; main-chute shock 6.8 G; touch-down ~7 G max"),
    ("Vibration", "Transonic ±1.5 G (1–5 Hz); remainder of boost ±0.5 G (10–50 Hz)"),
    ("Bay environment", "Sealed (double O-ring); ≥70 kPa; ≤60 °C absent payload heat loads"),
    ("Payload services", "5/12/24 VDC power; two 0–24 VDC event triggers (e.g., zero-G onset, apogee); "
                         "optional real-time downlink, external camera/antenna, viewport, vacuum bay, ejection"),
    ("Mission duration", "~20–25 min launch to touch-down; recovery within 25–30 min"),
])
fig(os.path.join(FIG, "img-004.png"),
    "Figure 1. Nominal BLK3 mission profile, altitude and velocity vs. time (PUG §2.3).")
fig(os.path.join(FIG, "img-005.png"),
    "Figure 2. BLK3 acceleration profile: MECO 3.8 G, ~150 s zero-G, ballute 4.3 G, main chute 6.8 G (PUG §2.3).")
fig(os.path.join(FIG, "img-006.png"),
    "Figure 3. Apogee vs. payload mass: 135 kg to 100 km design reference; 200 kg to ~80 km (PUG §2.3).", 5.8)
fig(os.path.join(FIG, "img-002.png"),
    "Figure 4. BLK3 vehicle stack, 10.82 m: recovery, payload, avionics, pressurization, tanks, propulsion (PUG §2).", 3.6)
fig(os.path.join(FIG, "img-008.png"),
    "Figure 5. Payload bay assembly and adapter-plate interface: 636 mm ID × 1,219 mm (PUG §3.1).", 5.6)

# ===== 7. Recovery, inspection, reflight =====
H("7.  Recovery, Inspection and 72-Hour Reflight")
B("For NGHCM T&E, the key differentiator is that both the vehicle and the test article come back. "
  "Hardware, instrumentation and on-board recorders are recovered intact for post-flight inspection, "
  "failure analysis, and reflight of the same article, so iterative test campaigns can run on "
  "one serial number instead of consuming a new article each time.")
BUL("A ballute deploys at the onset of milli-G to carry BLK3 through the supersonic regime. A ram-air "
    "parachute with an Autonomous Guidance Unit then glides the vehicle back to the recovery area near the "
    "pad and launch control.", "Two-stage guided recovery. ")
BUL("Nominal recovery is 25–30 minutes after launch. The vehicle is brought to \"Flight Secure\" and payloads are "
    "removed and returned to their owners on launch day. Providers who need urgent access can be stationed "
    "in the remote viewing area ~450 m from the pad.", "Same-day hands-on access. ")
BUL("BLK3 is designed and capable of reflight within 72 hours with a launch team of just 10 people. A second "
    "flight can be accommodated as early as two days after the first by installing a spare recovery system "
    "and pre-charged high-pressure helium. That leaves time for a full post-mission physical inspection and "
    "telemetry review between flights (PUG §2.6). This is a design capability. It has not yet been "
    "demonstrated on BLK3 in flight.", "Rapid turnaround. ")
BUL("Each flight returns the test article plus on-board data. Payload event triggers and optional real-time "
    "downlink support time-tagged correlation of article behavior to flight environment.",
    "Data return. ")
fig(os.path.join(FIG, "gen_turnaround.png"),
    "Figure 6. Notional post-landing turnaround to a reflight window within 72 hours (design intent; "
    "derived from PUG §2.6 and §4.5).")

# ===== 8. Launch ops / sites =====
H("8.  Launch Operations, Ranges and Deployability")
B("Exos launches from the Vertical Launch Area at Spaceport America (32°53′58″N, 106°55′48″W, "
  "1,400 m MSL) under an FAA AST launch license, with coordination among NMSA, White Sands Missile Range "
  "and the FAA. The primary Flight Hazard Area is a 6.5 km circle. GNC software terminates thrust if the "
  "vehicle would leave the FHA during boost. Launch control sits ~150 m from the tower. The windows are "
  "07:00–12:00 local, with 30 days' advance notice and a standard two-day window (day two = weather/"
  "technical scrub day).")
fig(os.path.join(FIG, "img-007.png"),
    "Figure 7. Spaceport America Vertical Launch Area: Exos launch pad, launch control and viewing area (PUG §2.4).")
B("The entire campaign deploys by road from Greenville, TX: launch control trailer, GSE crane truck, "
  "propellants and vehicle. It needs only a pad, power and communications. The scripted sequence runs "
  "from departure at L−4 days to a dry run and abort practice at L−1, a mandatory Mission Readiness Review, "
  "then launch day and a post-mission review with FAA AST and the spaceport.")
B("Exos has not flown suppressed (depressed) trajectories. Its SARGE flights "
  "and BLK3's licensed profile are near-vertical, recovered inside the launch-site FHA. Exos assesses that the vehicle is capable "
  "of more representative profiles, subject to FAA license modification and range approval. Options include: "
  "(a) commercial launch from Spaceport America with potential downrange landing on White Sands Missile Range; "
  "and (b) operations from ranges abroad, such as Australia, with the vehicle and test articles moved in Exos's "
  "secure shipping-container solution under a CRADA and with the required export authorizations. Exos would "
  "welcome DARPA's view on which profiles are of most T&E value.", "Trajectory guardrail. ")

# ===== 9. Payload integration =====
H("9.  Test-Article Integration Process")
B("Integration is managed under an Interface Control Document. Exos supplies the mounting plate (custom "
  "adapters need only hole pattern details). Exos also runs a Combined Systems Test at Greenville in "
  "simulated-flight mode to verify triggers, EMI compatibility and no adverse vehicle/payload interaction, "
  "and carries FAA AST payload review as part of the service. The BLK3 launch license already includes "
  "safety approval for a wide range of payloads. Controlled items are protected by protocol: unrestricted "
  "GPS unlock codes are installed at Exos and not kept with the vehicle, engine internals are covered, "
  "and high-resolution telemetry is restricted to Exos and FAA AST.")
fig(os.path.join(FIG, "img-009.png"),
    "Figure 8. Payload customer electrical interface: two 0–24 VDC triggers and switched customer power A/B (PUG §3).", 5.4)
fig(os.path.join(FIG, "gen_gloads.png"),
    "Figure 9. Design-load events a test article must survive across one BLK3 mission (PUG §2.3 data).")

# "add to" Jon's sentence in §2
for r in P[9].runs:
    if r.text.endswith("for inspection and reflight."):
        r.text = r.text[:-1] + ", designed and capable for reflight within 72 hours with a launch team of just 10."

# renumber Export section
for r in anchor.runs:
    if r.text.startswith("6."):
        r.text = r.text.replace("6.", "10.", 1)

# date refresh: cover/date line + amendment reference where the 9/7 date appears
for p in d.paragraphs:
    for r in p.runs:
        if "September 7, 2026" in r.text:
            r.text = r.text.replace("September 7, 2026", "October 6, 2026")

d.save(OUT)
print(OUT)
