#!/usr/bin/env python3
"""Build SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png
Stacked bar: funding at close + earn-outs (5yr tank + milestones + stock) + Y5 hold annotation.
John 10/7 15:22–15:28 update: tank earn-out extended to 5yr; milestone earn-outs added; HIGH ≈ $10M target.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np

OUT = "/Users/exomac/.openclaw/workspace/drafts/SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png"

# ── Data ──────────────────────────────────────────────────────────────────────
# Funding at close (FY27 only) — identical across scenarios
cash_at_close = [2_510_000, 0, 0, 0, 0]
sslc_costs    = [   60_000, 0, 0, 0, 0]
stake_credit  = [  790_000, 0, 0, 0, 0]
debts_paid    = [  500_000, 0, 0, 0, 0]   # ~$500K TBV
wc_bridge     = [  500_000, 0, 0, 0, 0]   # BASE/HIGH; LOW = $0

# ── Earn-out data (negotiating terms — management assumptions) ────────────────
# Tank earn-out: 5% of SSLC/IM tank revenue per year, cap $250K/yr, 5yr FY27-FY31
# BASE: 5% × avg $4M/yr = $200K/yr × 5 = $1,000K
# HIGH: 5% × $5M/yr = $250K/yr (at cap) × 5 = $1,250K
# LOW: $0 (IM demand does not materialize)
tank_earnout = [200_000, 200_000, 200_000, 200_000, 200_000]  # BASE: $1,000K
tank_high    = [250_000, 250_000, 250_000, 250_000, 250_000]  # HIGH: $1,250K
tank_low     = [      0,       0,       0,       0,       0]  # LOW:  $0

# Goal-based milestones (year distributed for BASE chart):
# M1: FY27 $5M revenue on schedule  → $200K, pays FY28
# M2: Nebula/OTV production contract → $300K, pays FY29 (base est.)
# M3: SSLC annual rev ≥$10M          → $300K, pays FY29 (HIGH) / not hit (BASE)
# M4: SSLC annual rev ≥$20M          → $400K, pays FY31 (HIGH only)
# M5: BLK3 tank qual complete         → $150K, pays FY28
# BASE (M1+M2+M5): $650K   HIGH (all): $1,350K   LOW: $0
milestone_base = [0, 200_000+150_000,  300_000,       0,       0]  # $650K: M1+M5 FY28, M2 FY29
milestone_high = [0, 200_000+150_000,  300_000+300_000, 0, 400_000]  # $1,350K: all 5
milestone_low  = [0,               0,               0, 0,       0]  # $0

# Stock earn-out — realized FY29 (listed ~FY28, 12-mo lockup)
stock_base = [0, 0, 1_875_000, 0, 0]   # 0.75% × $250M
stock_high = [0, 0, 3_000_000, 0, 0]   # 1.0%  × $300M
stock_low  = [0, 0, 1_000_000, 0, 0]   # 0.5%  × $200M

CLOSE_FIXED = sum(cash_at_close)+sum(sslc_costs)+sum(stake_credit)+sum(debts_paid)  # $3,860K (no WC)
CLOSE_BASE  = CLOSE_FIXED + sum(wc_bridge)                                           # $4,360K

# BASE stacked bar (WC bridge included; tank starts FY27)
base_annual = [a+b+c+d+e+f+g+h for a,b,c,d,e,f,g,h in
               zip(cash_at_close, sslc_costs, stake_credit, debts_paid,
                   wc_bridge, tank_earnout, milestone_base, stock_base)]
cumulative  = np.cumsum(base_annual)

total_base  = sum(base_annual)                                                          # $7,885K
total_low   = CLOSE_FIXED + sum(tank_low) + sum(milestone_low) + sum(stock_low)        # $4,860K (no WC)
total_high  = CLOSE_BASE  + sum(tank_high) + sum(milestone_high) + sum(stock_high)     # $9,960K ≈$10M

# ── Y5 hold values (Old-Model base case; FY31 EV = $101.6M × 16× = $1.626B)
# Dilution: Series A $25M staged + RTO listing + option pool ≈ 30% flat dilution (mgmt assumption)
# Post-dilution stakes: low 0.5%→0.35%, base 0.75%→0.525%, high 1.0%→0.70%
Y5_EV_OLDMODEL = 101_610_000 * 16          # $1.626B
Y5_EV_AA       =  11_000_000 * 16          # $176M — below $250M listing value
DILUTION = 0.30
y5_low_stake  = 0.005 * (1 - DILUTION)    # 0.35%
y5_base_stake = 0.0075 * (1 - DILUTION)   # 0.525%
y5_high_stake = 0.010 * (1 - DILUTION)    # 0.70%

y5_v12_base = Y5_EV_OLDMODEL * y5_base_stake   # $8.54M
y5_v12_low  = Y5_EV_OLDMODEL * y5_low_stake    # $5.69M
y5_v12_high = Y5_EV_OLDMODEL * y5_high_stake   # $11.38M

y5_aa_base  = Y5_EV_AA * y5_base_stake          # $924K  (< $1.875M listing)
y5_aa_low   = Y5_EV_AA * y5_low_stake           # $616K
y5_aa_high  = Y5_EV_AA * y5_high_stake          # $1.23M

# ── Colors ────────────────────────────────────────────────────────────────────
C_CASH    = "#8A8A8A"
C_COSTS   = "#AAAAAA"
C_STAKE   = "#666666"
C_DEBTS   = "#B0B0B0"
C_WC      = "#D0D0D0"
C_TANK    = "#F26A21"
C_MILESTONE = "#5BA3E0"
C_STOCK   = "#FF9F60"
BG        = "#111111"
CHART_BG  = "#1A1A1A"
TEXT      = "#FFFFFF"
GRID      = "#2E2E2E"
LINE_CUM  = "#FFFFFF"
C_Y5_V12  = "#00D4FF"   # cyan for Y5 old-model
C_Y5_AA   = "#FFD700"   # gold for Y5 AA (warn: below listing)

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
fig.patch.set_facecolor(BG)
ax.set_facecolor(CHART_BG)

YEARS = ["FY27\n(Close)", "FY28", "FY29\n(RTO+1yr)", "FY30", "FY31"]
x = np.arange(len(YEARS))
W = 0.52

def k(v): return v / 1_000

b_cash      = np.array([k(v) for v in cash_at_close])
b_costs     = np.array([k(v) for v in sslc_costs])
b_stake     = np.array([k(v) for v in stake_credit])
b_debts     = np.array([k(v) for v in debts_paid])
b_wc        = np.array([k(v) for v in wc_bridge])
b_tank      = np.array([k(v) for v in tank_earnout])
b_milestone = np.array([k(v) for v in milestone_base])
b_stock     = np.array([k(v) for v in stock_base])

bottom = np.zeros(len(YEARS))
for arr, color, label in [
    (b_cash,      C_CASH,      "Cash at close"),
    (b_costs,     C_COSTS,     "SSLC closing costs"),
    (b_stake,     C_STAKE,     "Exos stake credit (non-cash)"),
    (b_debts,     C_DEBTS,     "SSLC debts at face ~$500K TBV"),
    (b_wc,        C_WC,        "WC bridge ($500K)"),
    (b_tank,      C_TANK,      "Tank earn-out (5%/yr × 5yr, capped $300K/yr)"),
    (b_milestone, C_MILESTONE, "Milestone earn-outs base (M1-M3, $650K)"),
    (b_stock,     C_STOCK,     "Stock earn-out base (0.75% FD @ $250M)"),
]:
    ax.bar(x, arr, W, bottom=bottom, color=color, linewidth=0, zorder=3)
    if arr.any():
        ax.bar(x, np.where(arr > 0, 2, 0), W, bottom=bottom,
               color=CHART_BG, linewidth=0, zorder=4)
    bottom += arr

# Stock earn-out range whisker at FY29
bar_top_before_stock_fy29 = k(sum([
    cash_at_close[2], sslc_costs[2], stake_credit[2],
    debts_paid[2], wc_bridge[2], tank_earnout[2], milestone_base[2]
]))
stock_ba_k = k(stock_base[2])
ax.errorbar(x[2], bar_top_before_stock_fy29 + stock_ba_k,
            yerr=[[stock_ba_k - k(stock_low[2])], [k(stock_high[2]) - stock_ba_k]],
            fmt='none', ecolor='#FFD700', elinewidth=1.5, capsize=6, capthick=1.5, zorder=5)
ax.annotate(f"Stock: L ${k(stock_low[2]):.0f}K / H ${k(stock_high[2]):.0f}K",
            xy=(x[2] + W/2 + 0.05, bar_top_before_stock_fy29 + stock_ba_k + 60),
            fontsize=7.5, color='#FFD700', va='bottom', ha='left')

# Bar top labels
for i, tot in enumerate(base_annual):
    if tot > 0:
        bar_top = k(sum([cash_at_close[i], sslc_costs[i], stake_credit[i],
                         debts_paid[i], wc_bridge[i],
                         tank_earnout[i], milestone_base[i], stock_base[i]]))
        ax.text(x[i], bar_top + 30, f"${tot/1e6:.2f}M",
                ha='center', va='bottom', fontsize=8.5, color=TEXT, fontweight='bold', zorder=6)

# Cumulative line
cum_k = [k(v) for v in cumulative]
ax.plot(x, cum_k, color=LINE_CUM, linewidth=2, marker='o', markersize=5, zorder=7)
ax.annotate(f"5-yr total\n${total_base/1e6:.2f}M base\n(L ${total_low/1e6:.2f}M / H ~${total_high/1e6:.1f}M)",
            xy=(x[-1], cum_k[-1]),
            xytext=(x[-1] + 0.32, cum_k[-1] - 500),
            fontsize=7.5, color=TEXT,
            arrowprops=dict(arrowstyle='->', color=TEXT, lw=1),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#222222', edgecolor='#555555', alpha=0.9))

# ── Y5 Hold Potential markers at FY31 (x[4]) ─────────────────────────────────
fy31_bar_top = k(base_annual[4])   # 0 (no earn-outs at FY31 in base)

y5_y_v12 = k(y5_v12_base)
y5_y_aa  = k(y5_aa_base)

# Old-Model Y5 marker — bracket above bar
ax.annotate("",
            xy=(x[4] - W*0.55, y5_y_v12),
            xytext=(x[4] - W*0.55, fy31_bar_top),
            arrowprops=dict(arrowstyle='<->', color=C_Y5_V12, lw=1.5))
ax.text(x[4] - W*0.55 - 0.08, (y5_y_v12 + fy31_bar_top)/2,
        f"v12 Y5\nhold\n${y5_v12_base/1e6:.1f}M\n(L${y5_v12_low/1e6:.1f} H${y5_v12_high/1e6:.1f})",
        ha='right', va='center', fontsize=7, color=C_Y5_V12,
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#111111', edgecolor=C_Y5_V12, alpha=0.9))

# AA Y5 marker — bracket
ax.annotate("",
            xy=(x[4] + W*0.55, y5_y_aa),
            xytext=(x[4] + W*0.55, fy31_bar_top),
            arrowprops=dict(arrowstyle='<->', color=C_Y5_AA, lw=1.5))
ax.text(x[4] + W*0.55 + 0.08, (y5_y_aa + fy31_bar_top)/2,
        f"AA Y5\nhold\n${y5_aa_base/1e6:.2f}M\n⚠ < listing",
        ha='left', va='center', fontsize=7, color=C_Y5_AA,
        bbox=dict(boxstyle='round,pad=0.25', facecolor='#111111', edgecolor=C_Y5_AA, alpha=0.9))

ax.axhline(k(1_875_000), color='#FF9F60', linewidth=0.8, linestyle=':', alpha=0.6, zorder=2)
ax.text(4.6, k(1_875_000) + 20, "at-listing base $1.875M", fontsize=6.5, color='#FF9F60', va='bottom')

# ── Axes ──────────────────────────────────────────────────────────────────────
ax.set_xticks(x)
ax.set_xticklabels(YEARS, color=TEXT, fontsize=9)
ax.set_ylabel("Value ($000s)", color=TEXT, fontsize=9)
ylim_top = max(k(y5_v12_high), max(cum_k)) * 1.30
ax.set_ylim(0, ylim_top)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}K"))
ax.tick_params(colors=TEXT, labelsize=8)
ax.spines[['top','right']].set_visible(False)
ax.spines['left'].set_color(GRID)
ax.spines['bottom'].set_color(GRID)
ax.yaxis.grid(True, color=GRID, linewidth=0.5, linestyle='--', zorder=0)
ax.set_axisbelow(True)

# ── Title ─────────────────────────────────────────────────────────────────────
fig.suptitle("SSLC Option B — Total Compensation to Shareholders (FY27–FY31)",
             color=TEXT, fontsize=12, fontweight='bold', y=0.98)
ax.set_title("Funding at close + earn-outs (realized) + Y5 hold potential (bracketed, not double-counted)",
             color='#AAAAAA', fontsize=8, pad=6)

fig.text(0.5, 0.01,
         r"negotiating terms — management assumptions | SSLC debt ~\$500K TBV unverified (per 10/2 QB pull) | "
         r"Stock earn-out: principals' lockup terms (modeled ~12 months) | "
         r"Y5 hold: dilution 30% flat (Series A \$25M + RTO + pool) — mgmt assumption",
         ha='center', fontsize=6.5, color='#888888', style='italic')

# ── Legend ────────────────────────────────────────────────────────────────────
legend_patches = [
    mpatches.Patch(color=C_CASH,      label="Cash at close ($2.51M)"),
    mpatches.Patch(color=C_COSTS,     label="SSLC closing costs ($60K)"),
    mpatches.Patch(color=C_STAKE,     label="Stake credit non-cash ($790K)"),
    mpatches.Patch(color=C_DEBTS,     label="SSLC debts at face ~$500K TBV"),
    mpatches.Patch(color=C_WC,        label="WC bridge ($500K)"),
    mpatches.Patch(color=C_TANK,      label=f"Tank earn-out 5%/yr ×5yr ($1.0M base / $1.25M high)"),
    mpatches.Patch(color=C_MILESTONE, label=f"Milestone earn-outs ($650K base / $1.35M high)"),
    mpatches.Patch(color=C_STOCK,     label="Stock earn-out 0.75% FD @ $250M ($1.875M base)"),
    plt.Line2D([0],[0], color=LINE_CUM, linewidth=2, marker='o', markersize=4, label=f"Cumulative BASE → ${total_base/1e6:.2f}M  |  HIGH ~${total_high/1e6:.1f}M  |  LOW ${total_low/1e6:.2f}M"),
    mlines.Line2D([0],[0], color=C_Y5_V12, linewidth=2, label="v12 Y5 hold (≠ realized; 0.525% post-dilution)"),
    mlines.Line2D([0],[0], color=C_Y5_AA,  linewidth=2, label="AA Y5 hold (⚠ below listing @ $176M EV)"),
]
leg = ax.legend(handles=legend_patches, loc='upper right', framealpha=0.85,
                facecolor='#1A1A1A', edgecolor='#444444',
                fontsize=6.5, labelcolor=TEXT, ncol=2)

plt.tight_layout(rect=[0, 0.04, 1, 0.97])
fig.savefig(OUT, dpi=150, bbox_inches='tight', facecolor=BG)
plt.close()

print(f"Saved: {OUT}")
print(f"CLOSE FIXED: ${CLOSE_FIXED/1e6:.3f}M (no WC)  |  CLOSE BASE: ${CLOSE_BASE/1e6:.3f}M (with WC)")
print(f"5-yr BASE:  ${total_base/1e6:.3f}M  (close $4.36M + tank $1.0M + milestones $650K + stock $1.875M)")
print(f"5-yr LOW:   ${total_low/1e6:.3f}M  (close $3.86M no WC + no earn-outs + stock min $1.0M)")
print(f"5-yr HIGH:  ${total_high/1e6:.3f}M  (close $4.36M + tank $1.25M + milestones $1.35M + stock $3.0M) ≈$10M")
print(f"Y5 v12 hold: L ${y5_v12_low/1e6:.2f}M / B ${y5_v12_base/1e6:.2f}M / H ${y5_v12_high/1e6:.2f}M (0.35/0.525/0.70% post-dilution)")
print(f"Y5 AA hold:  L ${y5_aa_low/1e6:.3f}M / B ${y5_aa_base/1e6:.3f}M / H ${y5_aa_high/1e6:.3f}M (BELOW listing value)")
