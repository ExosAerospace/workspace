# Operational-Finance-exo3 — Governance

**Purpose.** A standing, always-on founder finance pulse: cash on hand, burn/surplus, runway,
and profitability vs. plan — read live from QuickBooks and delivered to Jon. Replaces the need
for an external "AI CFO" (e.g. Frank) by building the same value on infrastructure Exos already
owns, with **no financial data leaving the machine**.

**System of record.** QuickBooks Online (production). This engine is **read-only** — it never
writes to QB and never duplicates the ledger. Source reports: BalanceSheet (cash) + ProfitAndLoss
(trailing 90d income/expense/net).

**Determinism (matches Supplier-Diligence-exo3).** Every number comes straight from QuickBooks
reports. **No model sits in the number path.** The pulse text is templated, not generated.

**Metrics.** cash on hand; trailing-90d revenue/expenses/net; monthly burn or surplus; runway
months (cash ÷ monthly burn, only when burning); annualized net run-rate vs. the FY2025 actual
baseline (net +$187,861, EBITDA $296,022 — Form 1120).

**Delivery & schedule (launchd).**
- `com.exos.opfinance-pulse`  — Mondays 07:30 CT — DMs Jon the weekly pulse (`--pulse`).
- `com.exos.opfinance-alerts` — daily 07:00 CT — sends **only** on a threshold breach (`--alerts-only`).

**Thresholds (env-overridable).** OPFIN_CASH_ALERT (default $250k), OPFIN_RUNWAY_ALERT (6 months).
Breach of either — or a trailing run-rate that turns to a loss vs. the FY2025 baseline — fires an alert.

**Output.** `mission-control/data/operational-finance.json` (for Mission Control surfacing).
**Files.** `scripts/operational_finance_exo3.py`, `scripts/qb_client.py` (shared QB client),
plists in `config/launchd/`. Run modes: `--pulse`, `--now` (print, no send), `--alerts-only`, `--sample`.

**Scope note.** Exos-only today (Exos QuickBooks realm). Scorpius runs on separate books; once the
acquisition closes / Scorpius QB access lands, add its realm to give a true combined runway picture.
