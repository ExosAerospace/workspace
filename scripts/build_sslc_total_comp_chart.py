#!/usr/bin/env python3
"""Build SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png
Stacked bar: funding at close + EAI equity + earn-outs (5yr tank + milestones + stock earn-out) + Y5 hold annotation.
John 10/9 update (17:35): FIXED $1.0M EAI equity (not 1.0%); ~0.589% of $169.7M 409A; stock earn-out 0.0/0.25/0.5%;
totals ①$4,360K ②$5,360K ③$6,310K/$7,885K/$9,460K. HIGH drops below $10M — not rebalanced per instruction.
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
# 10/9 UPDATE (17:35): FIXED $1.0M EAI units at 409A (~0.589% of $169.7M, Rule 504)
eai_equity    = [1_000_000, 0, 0, 0, 0]   # $1,000,000 fixed; committed at board acceptance; issued at financing close

# ── Earn-out data (negotiating terms — management assumptions) ────────────────
# Matches offer summary Section 1 table (reconciled 10/9).
# Tank earn-out: % of IM/SSLC tank revenue, cap $300K/yr, 5 yrs FY27-FY31
# LOW 3% → $150K/yr = $750K | BASE 5% → $250K/yr = $1,250K | HIGH at cap $300K/yr = $1,500K
tank_earnout = [250_000]*5   # BASE $1,250K
tank_high    = [300_000]*5   # HIGH $1,500K
tank_low     = [150_000]*5   # LOW  $750K

# Goal-based milestones (paid only if hit):
# M1 SSLC FY2026-27 rev >= $5.1M → $200K, pays FY28 (L/B/H)
# M2 Nebula/OTV production contract → $200K, FY28 (B/H)
# M3 SSLC annual rev >= $10M → $250K, FY29 (B/H)
# M4 SSLC annual rev >= $20M → $250K, FY31 (H)
# M5 BLK3 tank qualification → $200K, FY28 (H)
milestone_base = [0, 200_000+200_000, 250_000, 0, 0]          # $650K
milestone_high = [0, 200_000+200_000+200_000, 250_000, 0, 250_000]  # $1,100K
milestone_low  = [0, 200_000, 0, 0, 0]                          # $200K

# Stock earn-out (earn-out only, on top of ~0.59% EAI up-front, Rule 504) — realized FY29
# LOW: 0.0% × $200M = $0 | BASE: 0.25% × $250M = $625K | HIGH: 0.5% × $300M = $1,500K
# Total Exos equity to SSLC: ~0.59% / ~0.84% / ~1.09% (EAI + earn-out)
stock_base = [0, 0,   625_000, 0, 0]   # 0.25% × $250M
stock_high = [0, 0, 1_500_000, 0, 0]   # 0.5%  × $300M
stock_low  = [0, 0,         0, 0, 0]   # 0.0%  × $200M = $0

CLOSE_FIXED = sum(cash_at_close)+sum(sslc_costs)+sum(stake_credit)+sum(debts_paid)+sum(eai_equity)  # $4,860K (no WC; $1M EAI)
CLOSE_BASE  = CLOSE_FIXED + sum(wc_bridge)                                                           # $5,360K ≈ $5.36M (② = ① + $1M EAI)

# BASE stacked bar (WC bridge + EAI included; tank starts FY27)
base_annual = [a+b+c+d+e+f+g+h+i for a,b,c,d,e,f,g,h,i in
               zip(cash_at_close, sslc_costs, stake_credit, debts_paid,
                   wc_bridge, eai_equity, tank_earnout, milestone_base, stock_base)]
cumulative  = np.cumsum(base_annual)

total_base  = sum(base_annual)                                                          # ~$7,885K ≈ $7.89M
total_low   = CLOSE_BASE  + sum(tank_low) + sum(milestone_low) + sum(stock_low)        # ~$6,310K ≈ $6.31M
total_high  = CLOSE_BASE  + sum(tank_high) + sum(milestone_high) + sum(stock_high)     # ~$9,460K ≈ $9.46M [HIGH < $10M — not rebalanced per 10/9 instruction]

# ── Y5 hold values (Old-Model base case; FY31 EV = $101.6M × 16× = $1.626B)
# Total SSLC stake = ~0.589% EAI up-front (Rule 504; $1M fixed) + earn-out %
# Low: ~0.589%+0.0%=~0.589% | Base: ~0.589%+0.25%=~0.839% | High: ~0.589%+0.5%=~1.089%
# Post-dilution (~30%): low ~0.4125%, base ~0.5875%, high ~0.7625%
EAI_PCT       = 1_000_000 / 169_700_000    # ~0.5893% FD shares
Y5_EV_OLDMODEL = 101_610_000 * 16          # $1.626B
Y5_EV_AA       =  11_000_000 * 16          # $176M — below $250M listing value
DILUTION = 0.30
y5_low_stake  = EAI_PCT * (1 - DILUTION)                  # ~0.4125%
y5_base_stake = (EAI_PCT + 0.0025) * (1 - DILUTION)       # ~0.5875%
y5_high_stake = (EAI_PCT + 0.005) * (1 - DILUTION)        # ~0.7625%

y5_v12_base = Y5_EV_OLDMODEL * y5_base_stake   # ~$9.6M
y5_v12_low  = Y5_EV_OLDMODEL * y5_low_stake    # ~$6.7M
y5_v12_high = Y5_EV_OLDMODEL * y5_high_stake   # ~$12.4M

y5_aa_base  = Y5_EV_AA * y5_base_stake          # ~$1.0M (< $1.875M listing)
y5_aa_low   = Y5_EV_AA * y5_low_stake           # ~$0.7M
y5_aa_high  = Y5_EV_AA * y5_high_stake          # ~$1.3M

# ── Colors ────────────────────────────────────────────────────────────────────
C_CASH    = "#8A8A8A"
C_COSTS   = "#AAAAAA"
C_STAKE   = "#666666"
C_DEBTS   = "#B0B0B0"
C_WC      = "#D0D0D0"
C_EAI     = "#7B61FF"   # purple — EAI up-front equity
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
b_eai       = np.array([k(v) for v in eai_equity])
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
    (b_eai,       C_EAI,       "Exos EAI equity $1.0M fixed (~0.59%, Rule 504)"),
    (b_tank,      C_TANK,      "Tank earn-out (5%/yr × 5yr, capped $300K/yr)"),
    (b_milestone, C_MILESTONE, "Milestone earn-outs base (M1-M3, $650K)"),
    (b_stock,     C_STOCK,     "Stock earn-out base (0.25% FD @ $250M = $625K)"),
]:
    ax.bar(x, arr, W, bottom=bottom, color=color, linewidth=0, zorder=3)
    if arr.any():
        ax.bar(x, np.where(arr > 0, 2, 0), W, bottom=bottom,
               color=CHART_BG, linewidth=0, zorder=4)
    bottom += arr

# Stock earn-out range whisker at FY29
bar_top_before_stock_fy29 = k(sum([
    cash_at_close[2], sslc_costs[2], stake_credit[2],
    debts_paid[2], wc_bridge[2], eai_equity[2], tank_earnout[2], milestone_base[2]
]))
stock_ba_k = k(stock_base[2])
ax.errorbar(x[2], bar_top_before_stock_fy29 + stock_ba_k,
            yerr=[[stock_ba_k - k(stock_low[2])], [k(stock_high[2]) - stock_ba_k]],
            fmt='none', ecolor='#FFD700', elinewidth=1.5, capsize=6, capthick=1.5, zorder=5)
stock_hi_k = k(stock_high[2])
ax.annotate(f"Stock earn-out: L $0K / H ${stock_hi_k:.0f}K",
            xy=(x[2] + W/2 + 0.05, bar_top_before_stock_fy29 + stock_ba_k + 60),
            fontsize=7.5, color='#FFD700', va='bottom', ha='left')

# Bar top labels
for i, tot in enumerate(base_annual):
    if tot > 0:
        bar_top = k(sum([cash_at_close[i], sslc_costs[i], stake_credit[i],
                         debts_paid[i], wc_bridge[i], eai_equity[i],
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

ax.axhline(k(625_000), color='#FF9F60', linewidth=0.8, linestyle=':', alpha=0.6, zorder=2)
ax.text(4.6, k(625_000) + 20, "earn-out base $625K", fontsize=6.5, color='#FF9F60', va='bottom')

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
    mpatches.Patch(color=C_EAI,       label="Exos EAI equity $1.0M fixed (~0.59% at 409A, Rule 504)"),
    mpatches.Patch(color=C_TANK,      label="Tank earn-out ×5yr ($1.25Mbase/$1.5M high)"),
    mpatches.Patch(color=C_MILESTONE, label="Milestone earn-outs (M1-M5; $650Kbase/$1.1M high)"),
    mpatches.Patch(color=C_STOCK,     label="Stock earn-out 0.25% FD @ $250M ($625K base)"),
    plt.Line2D([0],[0], color=LINE_CUM, linewidth=2, marker='o', markersize=4, label=f"Cumulative BASE → ${total_base/1e6:.2f}M  |  HIGH ~${total_high/1e6:.1f}M  |  LOW ${total_low/1e6:.2f}M"),
    mlines.Line2D([0],[0], color=C_Y5_V12, linewidth=2, label="v12 Y5 hold (≠ realized; ~0.5875% post-dilution base)"),
    mlines.Line2D([0],[0], color=C_Y5_AA,  linewidth=2, label="AA Y5 hold (⚠ below listing @ $176M EV)"),
]
leg = ax.legend(handles=legend_patches, loc='upper right', framealpha=0.85,
                facecolor='#1A1A1A', edgecolor='#444444',
                fontsize=6.5, labelcolor=TEXT, ncol=2)

plt.tight_layout(rect=[0, 0.04, 1, 0.97])
fig.savefig(OUT, dpi=150, bbox_inches='tight', facecolor=BG)
plt.close()

print(f"Saved: {OUT}")
print(f"CLOSE FIXED: ${CLOSE_FIXED/1e6:.3f}M ($1M EAI, no WC)  |  CLOSE BASE ②: ${CLOSE_BASE/1e6:.3f}M (with WC+$1M EAI)")
print(f"5-yr BASE ③: ${total_base/1e6:.3f}M  (close $5.36M incl $1M EAI + tank $1.25M + milestones $650K + stock earn-out $625K)")
print(f"5-yr LOW ③:  ${total_low/1e6:.3f}M  (close $5.36M + tank $750K + milestone $200K + stock earn-out $0)")
print(f"5-yr HIGH ③: ${total_high/1e6:.3f}M  (close $5.36M + tank $1.5M + milestones $1.1M + stock earn-out $1.5M) [HIGH < $10M target — not rebalanced]")
print(f"Y5 v12 hold: L ${y5_v12_low/1e6:.2f}M / B ${y5_v12_base/1e6:.2f}M / H ${y5_v12_high/1e6:.2f}M (~0.4125/0.5875/0.7625% post-dilution)")
print(f"Y5 AA hold:  L ${y5_aa_low/1e6:.3f}M / B ${y5_aa_base/1e6:.3f}M / H ${y5_aa_high/1e6:.3f}M (BELOW listing value)")
