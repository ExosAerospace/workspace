#!/usr/bin/env python3
"""Build SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png
Stacked bar chart: total value to SSLC shareholders/stakeholders, FY27-FY31.
Exos brand: black/grey base, orange (#F26A21) accent.
Follows dataviz skill: form → color → marks → render.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = "/Users/exomac/.openclaw/workspace/drafts/SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png"

# ── Data (from Assumptions sheet; base scenario) ─────────────────────────────
# Earn-out i: tank revenue 5% × $5M = $250K/yr (< $300K cap) × 3 yrs
# Earn-out ii: 0.5% × $250M = $1.25M at listing; 12-mo lockup → realized FY29
# Stock earn-out range: low 0.3%×$200M=$600K | high 0.7%×$300M=$2.1M

YEARS = ["FY27\n(Close)", "FY28", "FY29\n(RTO+1yr)", "FY30", "FY31"]

# Funding delivered — all hit in FY27 at close
cash_at_close    = [2_510_000, 0, 0, 0, 0]
sslc_costs       = [   60_000, 0, 0, 0, 0]
stake_credit     = [  790_000, 0, 0, 0, 0]
debts_paid       = [  500_000, 0, 0, 0, 0]
wc_bridge        = [  500_000, 0, 0, 0, 0]

# Forward potential — tank earn-out FY27-FY29 (base $250K/yr)
tank_earnout = [250_000, 250_000, 250_000, 0, 0]

# Stock earn-out scenarios — all realized FY29 (listed FY28, 12-mo lockup)
stock_base = [0, 0, 1_250_000, 0, 0]
stock_low  = [0, 0,   600_000, 0, 0]
stock_high = [0, 0, 2_100_000, 0, 0]

# Tank earn-out by scenario (for total reporting only; chart shows base bars)
tank_low  = [150_000, 150_000, 150_000, 0, 0]   # 3%×$5M = $150K < cap
tank_high = [300_000, 300_000, 300_000, 0, 0]   # 7%×$5M = $350K → capped $300K

# Cumulative for base
base_annual = [a+b+c+d+e+f+g for a,b,c,d,e,f,g in
               zip(cash_at_close, sslc_costs, stake_credit, debts_paid,
                   wc_bridge, tank_earnout, stock_base)]
cumulative  = np.cumsum(base_annual)

FUNDING_TOTAL = sum(cash_at_close) + sum(sslc_costs) + sum(stake_credit) + sum(debts_paid) + sum(wc_bridge)

# Totals for annotation (low = all-low; base = all-base; high = all-high)
total_base  = sum(base_annual)
total_low   = FUNDING_TOTAL + sum(tank_low)  + sum(stock_low)
total_high  = FUNDING_TOTAL + sum(tank_high) + sum(stock_high)

# ── Color palette (Exos brand) ────────────────────────────────────────────────
# Funding: greyscale family (neutral = committed at close)
C_CASH   = "#8A8A8A"   # cash at close — medium grey
C_COSTS  = "#AAAAAA"   # SSLC closing costs — light grey
C_STAKE  = "#666666"   # stake credit — dark grey
C_DEBTS  = "#B0B0B0"   # debts paid — lighter grey
C_WC     = "#D0D0D0"   # WC bridge — lightest grey
# Forward potential: Exos orange family
C_TANK   = "#F26A21"   # tank earn-out — Exos orange
C_STOCK  = "#FF9F60"   # stock earn-out — lighter orange
# Structural
BG       = "#111111"
CHART_BG = "#1A1A1A"
TEXT     = "#FFFFFF"
GRID     = "#2E2E2E"
LINE_CUM = "#FFFFFF"

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5))
fig.patch.set_facecolor(BG)
ax.set_facecolor(CHART_BG)

x = np.arange(len(YEARS))
W = 0.52  # bar width

def k(v): return v / 1_000

# Stack funding components (FY27 only) — draw bottom to top
b_cash  = np.array([k(v) for v in cash_at_close])
b_costs = np.array([k(v) for v in sslc_costs])
b_stake = np.array([k(v) for v in stake_credit])
b_debts = np.array([k(v) for v in debts_paid])
b_wc    = np.array([k(v) for v in wc_bridge])
b_tank  = np.array([k(v) for v in tank_earnout])
b_stock = np.array([k(v) for v in stock_base])

bars = []
bottom = np.zeros(len(YEARS))

for arr, color, label in [
    (b_cash,  C_CASH,  "Cash at close"),
    (b_costs, C_COSTS, "SSLC closing costs"),
    (b_stake, C_STAKE, "Exos stake credit (non-cash)"),
    (b_debts, C_DEBTS, "SSLC debts paid at face (TBV)"),
    (b_wc,    C_WC,    "Working-capital bridge"),
    (b_tank,  C_TANK,  "Tank earn-out (5%/yr, capped)"),
    (b_stock, C_STOCK, "Stock earn-out base (0.5% FD @ $250M)"),
]:
    bar = ax.bar(x, arr, W, bottom=bottom, color=color, label=label,
                 linewidth=0, zorder=3)
    # 2px surface gap between segments
    if arr.any():
        ax.bar(x, np.where(arr > 0, 2, 0), W, bottom=bottom,
               color=CHART_BG, linewidth=0, zorder=4)
    bottom += arr
    bars.append(bar)

# Stock earn-out range whiskers (low/high) at FY29 (index 2)
stock_lo_k = k(stock_low[2])
stock_hi_k = k(stock_high[2])
stock_ba_k = k(stock_base[2])
# whisker center = mid of stock base in FY29
bar_top_before_stock = k(sum([cash_at_close[2], sslc_costs[2], stake_credit[2],
                               debts_paid[2], wc_bridge[2], tank_earnout[2]]))
mid_stock = bar_top_before_stock + stock_ba_k / 2

ax.errorbar(x[2], bar_top_before_stock + stock_ba_k,
            yerr=[[stock_ba_k - stock_lo_k], [stock_hi_k - stock_ba_k]],
            fmt='none', ecolor='#FFD700', elinewidth=1.5, capsize=6,
            capthick=1.5, zorder=5)
ax.annotate(f"Stock: L ${k(stock_low[2]):.0f}K / H ${k(stock_high[2]):.0f}K",
            xy=(x[2] + W/2 + 0.05, bar_top_before_stock + stock_ba_k + 60),
            fontsize=7.5, color='#FFD700', va='bottom', ha='left')

# Bar value labels — top of each year's total bar
for i, (tot, cum) in enumerate(zip([k(v) for v in base_annual], [k(v) for v in cumulative])):
    if tot > 0:
        ax.text(x[i], k(sum([cash_at_close[i], sslc_costs[i], stake_credit[i],
                              debts_paid[i], wc_bridge[i], tank_earnout[i], stock_base[i]])) + 30,
                f"${tot/1000:.1f}M", ha='center', va='bottom', fontsize=8.5,
                color=TEXT, fontweight='bold', zorder=6)

# ── Cumulative line ───────────────────────────────────────────────────────────
cum_k = [k(v) for v in cumulative]
ax.plot(x, cum_k, color=LINE_CUM, linewidth=2, marker='o', markersize=5,
        zorder=7, label='Cumulative total')
# Label final cumulative point
ax.annotate(f"5-yr total\n${total_base/1e6:.2f}M base\n(L ${total_low/1e6:.2f}M / H ${total_high/1e6:.2f}M)",
            xy=(x[-1], cum_k[-1]),
            xytext=(x[-1] + 0.35, cum_k[-1] - 300),
            fontsize=8, color=TEXT,
            arrowprops=dict(arrowstyle='->', color=TEXT, lw=1),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#222222',
                      edgecolor='#555555', alpha=0.9))

# ── Axes formatting ───────────────────────────────────────────────────────────
ax.set_xticks(x)
ax.set_xticklabels(YEARS, color=TEXT, fontsize=9)
ax.set_ylabel("Value ($000s)", color=TEXT, fontsize=9)
ax.set_ylim(0, max(cum_k) * 1.22)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}K"))
ax.tick_params(colors=TEXT, labelsize=8)
ax.spines[['top','right']].set_visible(False)
ax.spines['left'].set_color(GRID)
ax.spines['bottom'].set_color(GRID)
ax.yaxis.grid(True, color=GRID, linewidth=0.5, linestyle='--', zorder=0)
ax.set_axisbelow(True)

# ── Title & disclaimer ────────────────────────────────────────────────────────
fig.suptitle("SSLC Option B — Total Compensation to Shareholders (FY27–FY31)",
             color=TEXT, fontsize=12, fontweight='bold', y=0.98)
ax.set_title("Funding delivered at close + forward potential (earn-outs); base scenario",
             color='#AAAAAA', fontsize=8.5, pad=6)

# Footnote
fig.text(0.5, 0.01,
         "negotiating terms — management assumptions; SSLC debt unverified | "
         "Stock earn-out: low $0.6M / base $1.25M / high $2.1M (whiskers FY29)",
         ha='center', fontsize=7, color='#888888', style='italic')

# ── Legend ────────────────────────────────────────────────────────────────────
legend_patches = [
    mpatches.Patch(color=C_CASH,  label="Cash at close ($2.51M)"),
    mpatches.Patch(color=C_COSTS, label="SSLC closing costs ($60K)"),
    mpatches.Patch(color=C_STAKE, label="Stake credit non-cash ($790K)"),
    mpatches.Patch(color=C_DEBTS, label="SSLC debts at face ~$500K TBV"),
    mpatches.Patch(color=C_WC,    label="WC bridge ($500K)"),
    mpatches.Patch(color=C_TANK,  label="Tank earn-out 5%/yr ×3 ($750K base)"),
    mpatches.Patch(color=C_STOCK, label="Stock earn-out 0.5% FD ($1.25M base)"),
    plt.Line2D([0],[0], color=LINE_CUM, linewidth=2, marker='o',
               markersize=4, label="Cumulative total"),
]
leg = ax.legend(handles=legend_patches, loc='upper right', framealpha=0.85,
                facecolor='#1A1A1A', edgecolor='#444444',
                fontsize=7.5, labelcolor=TEXT, ncol=2)

plt.tight_layout(rect=[0, 0.04, 1, 0.97])
fig.savefig(OUT, dpi=150, bbox_inches='tight', facecolor=BG)
plt.close()
print(f"Saved: {OUT}")
print(f"5-yr BASE:  funding ${FUNDING_TOTAL/1e6:.3f}M | forward ${(sum(tank_earnout)+sum(stock_base))/1e6:.3f}M | total ${total_base/1e6:.3f}M")
print(f"5-yr LOW:   funding ${FUNDING_TOTAL/1e6:.3f}M | forward ${(sum(tank_low)+sum(stock_low))/1e6:.3f}M | total ${total_low/1e6:.3f}M")
print(f"5-yr HIGH:  funding ${FUNDING_TOTAL/1e6:.3f}M | forward ${(sum(tank_high)+sum(stock_high))/1e6:.3f}M | total ${total_high/1e6:.3f}M")
