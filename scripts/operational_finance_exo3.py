#!/usr/bin/env python3
"""Operational-Finance-exo3 — standing founder finance pulse (cash / burn / runway).

exo3 process (AI-managed program; see project_exo3_program_naming). QuickBooks is the
system of record; this NEVER writes to QB and NEVER duplicates the ledger — it reads the
live BalanceSheet + ProfitAndLoss and turns them into the one thing a founder needs on a
standing basis: how much cash, how fast it moves, and how many months of runway remain —
reconciled against the plan (Exos closed FY2025 profitable).

Deterministic: the numbers come straight from QuickBooks reports. No model sits in the
number path (matches the Supplier-Diligence-exo3 governance — see project_supplier_dd_exo3).

Delivery:
  --pulse        compute + DM Jon the weekly founder pulse (and any threshold alert)
  --now          compute + print the pulse locally (no send)
  --alerts-only  send ONLY if a cash/runway threshold is breached (for a daily light check)
  --sample       run against built-in demo numbers (no QuickBooks needed)

Thresholds (env-overridable): OPFIN_CASH_ALERT (default $250k), OPFIN_RUNWAY_ALERT (6 mo).
Writes mission-control/data/operational-finance.json for Mission Control surfacing.
"""
import os, sys, json, subprocess, datetime, urllib.request, urllib.parse

WS = os.path.expanduser("~/.openclaw/workspace")
sys.path.insert(0, os.path.join(WS, "scripts"))
OUT = os.path.join(WS, "mission-control", "data", "operational-finance.json")
LOG = os.path.join(WS, "logs", "operational-finance-exo3.log")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"

CASH_ALERT   = float(os.environ.get("OPFIN_CASH_ALERT", "250000"))
RUNWAY_ALERT = float(os.environ.get("OPFIN_RUNWAY_ALERT", "6"))
# Plan baseline: Exos FY2025 actuals (Form 1120) — the profitability line we defend against.
BASE_FY2025 = {"revenue": 1493961.0, "ebitda": 296022.0, "net_income": 187861.0}

def logline(m):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f: f.write(f"[{ts}] {m}\n")
    except Exception: pass

def _subprocess_env():
    env = dict(os.environ)
    extra = ["/Users/exomac/.local/share/mise/installs/node/24.14.0/bin",
             "/Users/exomac/.local/share/mise/shims", "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra + [env.get("PATH", "")])
    return env

def post_discord(text):
    try:
        r = subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", JON, "-m", text],
                           capture_output=True, text=True, timeout=60, env=_subprocess_env())
        if r.returncode != 0:
            logline(f"WARN discord rc={r.returncode}: {r.stderr[:200]}"); return False
        return True
    except Exception as e:
        logline(f"WARN discord send failed: {e}"); return False

# ---- QuickBooks reports (read-only) ----
def _report(name, params):
    import qb_client
    acc, realm, env = qb_client.get_access_token()
    base = qb_client._base(env)
    q = dict(params); q["minorversion"] = "73"
    url = f"{base}/v3/company/{realm}/reports/{name}?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {acc}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def _walk(rows):
    """Yield every Row dict recursively from a QB report Rows tree."""
    if not rows: return
    lst = rows.get("Row", []) if isinstance(rows, dict) else rows
    for row in lst:
        yield row
        if row.get("Rows"):
            yield from _walk(row["Rows"])

def _summary_value(report, *label_substrs):
    """Find a Summary/row whose first cell contains any label substring; return its last numeric cell."""
    subs = [s.lower() for s in label_substrs]
    best = None
    for row in _walk(report.get("Rows", {})):
        cells = (row.get("Summary") or row).get("ColData") if row.get("Summary") else row.get("ColData")
        if not cells: continue
        label = (cells[0].get("value") or "").lower()
        if any(s in label for s in subs):
            for c in reversed(cells):
                v = (c.get("value") or "").replace(",", "").replace("$", "")
                try:
                    best = float(v); break
                except ValueError:
                    continue
    return best

def pull_live():
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=90)).isoformat()
    bs = _report("BalanceSheet", {"as_of": today.isoformat()})
    pl = _report("ProfitAndLoss", {"start_date": start, "end_date": today.isoformat()})
    cash = _summary_value(bs, "total bank accounts", "bank accounts", "total cash")
    if cash is None:
        cash = _summary_value(bs, "total current assets") or 0.0
    income = _summary_value(pl, "total income") or 0.0
    expenses = _summary_value(pl, "total expenses") or 0.0
    net = _summary_value(pl, "net income")
    if net is None: net = income - expenses
    return {"cash": cash, "window_days": 90, "income": income, "expenses": expenses, "net": net}

def sample():
    return {"cash": 812000.0, "window_days": 90, "income": 470000.0, "expenses": 405000.0, "net": 65000.0}

# ---- analysis (pure math) ----
def analyze(raw):
    days = raw["window_days"] or 90
    monthly_net = raw["net"] / (days / 30.4)
    burning = monthly_net < 0
    if burning:
        runway = raw["cash"] / abs(monthly_net) if monthly_net else None
    else:
        runway = None  # profitable / cash-building
    annualized_net = raw["net"] * (365.0 / days)
    return {
        "cash": round(raw["cash"], 2),
        "trailing_days": days,
        "trailing_income": round(raw["income"], 2),
        "trailing_expenses": round(raw["expenses"], 2),
        "trailing_net": round(raw["net"], 2),
        "monthly_net": round(monthly_net, 2),
        "burning": burning,
        "runway_months": round(runway, 1) if runway is not None else None,
        "annualized_net_runrate": round(annualized_net, 2),
        "vs_plan_profitable": annualized_net >= 0,
        "plan_baseline_net": BASE_FY2025["net_income"],
        "asof": datetime.date.today().isoformat(),
    }

def alerts(a):
    out = []
    if a["cash"] < CASH_ALERT:
        out.append(f"CASH below ${CASH_ALERT:,.0f} threshold (now ${a['cash']:,.0f})")
    if a["runway_months"] is not None and a["runway_months"] < RUNWAY_ALERT:
        out.append(f"RUNWAY below {RUNWAY_ALERT:.0f} mo (now {a['runway_months']} mo)")
    if not a["vs_plan_profitable"]:
        out.append(f"Trailing run-rate turned to a LOSS (annualized ${a['annualized_net_runrate']:,.0f}) vs FY2025 net +${BASE_FY2025['net_income']:,.0f}")
    return out

def pulse_text(a, al):
    money = lambda x: f"${x:,.0f}"
    if a["burning"]:
        run = f"{a['runway_months']} months" if a["runway_months"] is not None else "n/a"
        burn = f"burning {money(abs(a['monthly_net']))}/mo"
    else:
        run = "profitable — building cash"
        burn = f"net +{money(a['monthly_net'])}/mo"
    head = "🔴 OPERATIONAL FINANCE — ALERT" if al else "🟢 OPERATIONAL FINANCE — weekly pulse"
    lines = [head, f"_as of {a['asof']} · source: QuickBooks (live)_", "",
        f"• Cash on hand: {money(a['cash'])}",
        f"• Trailing 90d: rev {money(a['trailing_income'])} · exp {money(a['trailing_expenses'])} · net {money(a['trailing_net'])}",
        f"• Burn/surplus: {burn}",
        f"• Runway: {run}",
        f"• Annualized run-rate: net {money(a['annualized_net_runrate'])} (FY2025 baseline net +{money(BASE_FY2025['net_income'])})"]
    if al:
        lines += ["", "⚠️ " + "; ".join(al)]
    return "\n".join(lines)

def save_json(a, al):
    obj = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "metrics": a, "alerts": al, "thresholds": {"cash": CASH_ALERT, "runway_months": RUNWAY_ALERT}}
    tmp = OUT + ".tmp"; json.dump(obj, open(tmp, "w"), indent=2); os.replace(tmp, OUT)

def main():
    args = set(sys.argv[1:])
    raw = sample() if "--sample" in args else pull_live()
    a = analyze(raw); al = alerts(a)
    if "--sample" not in args:
        save_json(a, al)
    txt = pulse_text(a, al)
    if "--pulse" in args:
        post_discord(txt); logline("pulse sent" + (" +alert" if al else ""))
    elif "--alerts-only" in args:
        if al: post_discord(txt); logline("alert sent: " + "; ".join(al))
        else: logline("no alert")
    print(txt)

if __name__ == "__main__":
    main()
