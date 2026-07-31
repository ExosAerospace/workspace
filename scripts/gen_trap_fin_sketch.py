#!/usr/bin/env python3
"""Trapezoidal fin scaling sketch for Neil Milburn.
100% fin solid black; nested 90/80/70/60% dotted, color-coded, scaled about the
root leading-edge (mounting) corner which is held fixed. Dimensions in mm.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 100% fin geometry (mm). Root chord/base=500, span=300, tip chord=200.
# Fixed corner A = root leading edge at origin. Drawn with body (root chord)
# horizontal along the top; span points downward.
A = (0.0, 0.0)      # root leading edge  (FIXED CORNER)
B = (500.0, 0.0)    # root trailing edge
C = (150.0, 300.0)  # tip leading edge   (150mm sweep)
D = (350.0, 300.0)  # tip trailing edge  -> tip chord = 200

def fin_pts(s):
    """Uniform scale about A=(0,0) by factor s."""
    return [(p[0]*s, p[1]*s) for p in (A, B, D, C, A)]

scales = [
    (1.00, "black",     "-",  3.0, "100%  root 500 / span 300 / tip 200"),
    (0.90, "#1f77b4",  ":",  1.8, "90%   root 450 / span 270"),
    (0.80, "#2ca02c",  ":",  1.8, "80%   root 400 / span 240"),
    (0.70, "#ff7f0e",  ":",  1.8, "70%   root 350 / span 210"),
    (0.60, "#d62728",  ":",  1.8, "60%   root 300 / span 180"),
]

fig, ax = plt.subplots(figsize=(9, 7))

# body / mounting line reference along the root chord
ax.plot([-40, 540], [0, 0], color="0.55", lw=1.0, zorder=1)
ax.text(540, -12, "body / mounting line", color="0.45", fontsize=8, ha="right", va="top")

for s, color, ls, lw, _ in scales:
    xs = [p[0] for p in fin_pts(s)]
    ys = [p[1] for p in fin_pts(s)]
    ax.plot(xs, ys, color=color, linestyle=ls, lw=lw, zorder=3,
            dash_capstyle="round")

# mark the fixed mounting corner
ax.plot(*A, marker="o", color="black", ms=7, zorder=5)
ax.annotate("fixed mounting corner\n(root leading edge)", xy=A, xytext=(70, -55),
            fontsize=8.5, ha="left", va="top", color="black",
            arrowprops=dict(arrowstyle="->", color="black", lw=1))

# key dimensions on the 100% fin
ax.annotate("", xy=(0, 0), xytext=(500, 0),
            arrowprops=dict(arrowstyle="<->", color="black", lw=0.9))
ax.text(250, 10, "root chord 500 mm", ha="center", va="bottom", fontsize=9)
ax.annotate("", xy=(500, 0), xytext=(350, 300),
            arrowprops=dict(arrowstyle="<->", color="0.35", lw=0.8))
ax.text(150, 300, "  span 300 mm", ha="left", va="center", fontsize=9, rotation=0)
ax.annotate("", xy=(150, 300), xytext=(350, 300),
            arrowprops=dict(arrowstyle="<->", color="black", lw=0.9))
ax.text(250, 312, "tip chord 200 mm", ha="center", va="top", fontsize=9)

legend_lines = [Line2D([0], [0], color=c, linestyle=(ls if s != 1.0 else "-"),
                       lw=(3 if s == 1.0 else 1.8))
                for s, c, ls, lw, lbl in scales]
legend_labels = [lbl for *_, lbl in scales]
ax.legend(legend_lines, legend_labels, loc="lower right", fontsize=8.5,
          title="Scale (about fixed corner)", title_fontsize=9, framealpha=0.95)

ax.set_title("Trapezoidal Fin — Uniform Scaling Study (base + span)", fontsize=13)
ax.set_xlabel("mm"); ax.set_ylabel("mm (span)")
ax.set_aspect("equal")
ax.grid(True, color="0.9", lw=0.5)
ax.invert_yaxis()  # span downward as drawn
ax.set_xlim(-60, 560); ax.set_ylim(340, -80)

out = "/Users/exomac/.openclaw/workspace/Trapezoidal_Fin_Scaling_Sketch.png"
fig.tight_layout()
fig.savefig(out, dpi=170)
print(out)
