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
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)

WS = os.path.expanduser("~/.openclaw/workspace")
sys.path.insert(0, os.path.join(WS, "scripts"))
OUT = os.path.join(WS, "mission-control", "data", "operational-finance.json")
BACKLOG_CFG = os.path.join(WS, "mission-control", "data", "finance-backlog.json")
PROGRAM_CFG = os.path.join(WS, "mission-control", "data", "program-spend.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
LOG = os.path.join(WS, "logs", "operational-finance-exo3.log")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"

CASH_ALERT   = float(os.environ.get("OPFIN_CASH_ALERT", "250000"))
RUNWAY_ALERT = float(os.environ.get("OPFIN_RUNWAY_ALERT", "6"))
BENEFITS_LOAD = float(os.environ.get("OPFIN_BENEFITS_LOAD", "1.28"))  # payroll tax/benefits load factor
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

def _query(q):
    import qb_client
    acc, realm, env = qb_client.get_access_token()
    base = qb_client._base(env)
    url = f"{base}/v3/company/{realm}/query?" + urllib.parse.urlencode({"query": q, "minorversion": "73"})
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {acc}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

# ---- booked-revenue backlog (contracted, expected to report) ----
def pull_backlog():
    """Blend live QuickBooks pieces (open A/R, entX remaining) with the contracted
    backlog config. Returns line items + roll-up split by stage."""
    try:
        cfg = json.load(open(BACKLOG_CFG))
    except Exception as e:
        logline(f"WARN backlog cfg: {e}"); return None
    items = []
    live = cfg.get("live", {})
    # Open A/R (booked, invoiced, not collected)
    try:
        ar = _report("AgedReceivables", {})
        ar_total = _summary_value(ar, "total") or 0.0
        o = live.get("open_ar", {})
        items.append({"name": o.get("name", "Open A/R"), "amount": round(ar_total, 2),
                      "stage": o.get("stage", "booked"), "expect_2026": round(ar_total, 2), "note": o.get("note", "")})
    except Exception as e:
        logline(f"WARN A/R: {e}")
    # entX remaining-to-invoice = contract_total - invoiced_to_date (live from QB)
    ex = live.get("entx")
    if ex:
        try:
            r = _query(f"select * from Invoice where CustomerRef='{ex['qb_customer_ref']}'")
            invs = r.get("QueryResponse", {}).get("Invoice", [])
            invoiced = sum(float(i.get("TotalAmt", 0)) for i in invs)
            remaining = float(ex["contract_total"]) - invoiced
            if remaining > 0:
                items.append({"name": ex["name"], "amount": round(remaining, 2), "stage": ex.get("stage", "booked"),
                              "expect_2026": None, "note": ex.get("note", "")})
        except Exception as e:
            logline(f"WARN entX: {e}")
    # static contracted items
    for s in cfg.get("static_backlog", []):
        items.append({"name": s["name"], "amount": float(s.get("amount", 0)), "stage": s.get("stage", "booked"),
                      "expect_2026": s.get("expect_2026"), "note": s.get("note", "")})
    booked = sum(i["amount"] for i in items if i["stage"] in ("booked", "funded", "committed"))
    pipeline = sum(i["amount"] for i in items if i["stage"] == "pipeline")
    expect_2026 = sum((i["expect_2026"] or 0) for i in items if i["stage"] in ("booked", "funded", "committed"))
    return {"items": items, "booked_total": round(booked, 2), "pipeline_total": round(pipeline, 2),
            "expect_2026_min": round(expect_2026, 2)}

# ---- wages & benefits (BambooHR = payroll/HR system of record) ----
def pull_payroll():
    import base64, re
    from collections import defaultdict
    try:
        s = json.load(open(SECRETS)); sub = s["bamboo_subdomain"]; key = s["bamboo_api_key"]
    except Exception as e:
        logline(f"WARN bamboo secrets: {e}"); return None
    def api(ep):
        url = f"https://api.bamboohr.com/api/gateway.php/{sub}/v1/{ep}"
        auth = base64.b64encode(f"{key}:x".encode()).decode()
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    try:
        emps = api("employees/directory").get("employees", [])
    except Exception as e:
        logline(f"WARN bamboo dir: {e}"); return None
    total = 0.0
    dept = defaultdict(float); dept_ct = defaultdict(int); headcount = 0
    for e in emps:
        try:
            info = api(f"employees/{e['id']}?fields=payRate,payType,department")
        except Exception:
            continue
        pr = info.get("payRate") or ""
        m = re.search(r"([\d,]+\.?\d*)", pr.replace("USD", ""))
        amt = float(m.group(1).replace(",", "")) if m else 0.0
        hourly = (info.get("payType", "").lower() == "hourly") or (0 < amt < 1000)
        annual = amt * 2080 if hourly else amt
        total += annual; headcount += 1
        dp = e.get("department") or info.get("department") or "Unassigned"
        dept[dp] += annual; dept_ct[dp] += 1
    return {"headcount": headcount, "annual_base": round(total, 2), "monthly_base": round(total / 12, 2),
            "monthly_loaded": round(total * BENEFITS_LOAD / 12, 2), "load_factor": BENEFITS_LOAD,
            "by_dept": {k: {"monthly": round(v / 12, 2), "people": dept_ct[k]} for k, v in dept.items()}}

# ---- program-spend KPIs (HVRR-RDRE / BLK3 / R&D) ----
def pull_program_spend(payroll):
    try:
        cfg = json.load(open(PROGRAM_CFG))
    except Exception as e:
        logline(f"WARN program cfg: {e}"); return None
    live_class = bool(cfg.get("qb_class_tracking_enabled"))
    by_dept = (payroll or {}).get("by_dept", {})
    progs = []
    for p in cfg.get("programs", []):
        labor = by_dept.get(p.get("dept_proxy", ""), {}).get("monthly")
        progs.append({"key": p["key"], "budget": p.get("budget"),
                      "labor_proxy_monthly": labor, "dept_proxy": p.get("dept_proxy")})
    return {"qb_class_tracking": live_class, "programs": progs,
            "enablement_note": cfg.get("enablement_note", "")}

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

def pulse_text(a, al, backlog=None, payroll=None, program=None):
    money = lambda x: f"${x:,.0f}"
    if a["burning"]:
        run = f"{a['runway_months']} months" if a["runway_months"] is not None else "n/a"
        burn = f"burning {money(abs(a['monthly_net']))}/mo"
    else:
        run = "profitable — building cash"
        burn = f"net +{money(a['monthly_net'])}/mo"
    head = "🔴 OPERATIONAL FINANCE — ALERT" if al else "🔵 OPERATIONAL FINANCE — expanded pulse"
    lines = [head, f"_as of {a['asof']} · source: QuickBooks + BambooHR (live)_", "",
        "*CASH & REALIZED (QB, trailing 90d)*",
        f"• Cash on hand: {money(a['cash'])}",
        f"• Trailing 90d: rev {money(a['trailing_income'])} · exp {money(a['trailing_expenses'])} · net {money(a['trailing_net'])}",
        f"• Burn/surplus: {burn} · Runway: {run}",
        f"• Annualized run-rate: net {money(a['annualized_net_runrate'])} (FY2025 baseline net +{money(BASE_FY2025['net_income'])})"]
    if backlog and backlog.get("items"):
        lines += ["", "*BOOKED REVENUE / BACKLOG (contracted, expected to report)*"]
        for it in backlog["items"]:
            tag = "" if it["stage"] in ("booked", "funded", "committed") else f" ({it['stage']})"
            lines.append(f"• {it['name']}: {money(it['amount'])}{tag}")
        lines.append(f"→ Booked/committed backlog ≈ {money(backlog['booked_total'])}"
                     + (f" · pipeline {money(backlog['pipeline_total'])}" if backlog.get("pipeline_total") else ""))
    if payroll:
        lines += ["", "*COST KPIs*",
            f"• Wages & benefits: {money(payroll['monthly_base'])}/mo base "
            f"({money(payroll['annual_base'])}/yr, {payroll['headcount']} staff) · "
            f"{money(payroll['monthly_loaded'])}/mo fully loaded (~{int((payroll['load_factor']-1)*100)}% load)"]
    if program:
        if program.get("qb_class_tracking"):
            for p in program["programs"]:
                sp = p.get("spend_monthly")
                lines.append(f"• {p['key']} spend: {money(sp)}/mo" if sp is not None else f"• {p['key']} spend: n/a")
        else:
            prox = [f"{p['key']}~{money(p['labor_proxy_monthly'])}/mo" for p in program["programs"]
                    if p.get("labor_proxy_monthly")]
            # dedupe identical proxy (same dept) into one line
            uniq = []
            for p in program["programs"]:
                if p.get("labor_proxy_monthly") and p["dept_proxy"] not in [u[0] for u in uniq]:
                    uniq.append((p["dept_proxy"], p["labor_proxy_monthly"]))
            if uniq:
                lines.append("• Program labor (live proxy, BambooHR dept): "
                             + " · ".join(f"{d} {money(v)}/mo" for d, v in uniq))
            lines.append("• HVRR-RDRE / BLK3 / R&D full spend: not class-tracked in QB yet "
                         "(enable QB classes to go live)")
    if al:
        lines += ["", "⚠️ " + "; ".join(al)]
    return "\n".join(lines)

def save_json(a, al, backlog=None, payroll=None, program=None):
    obj = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
           "metrics": a, "backlog": backlog, "payroll": payroll, "program_spend": program,
           "alerts": al, "thresholds": {"cash": CASH_ALERT, "runway_months": RUNWAY_ALERT}}
    tmp = OUT + ".tmp"; json.dump(obj, open(tmp, "w"), indent=2); os.replace(tmp, OUT)

def main():
    args = set(sys.argv[1:])
    if "--sample" in args:
        raw = sample(); backlog = payroll = program = None
    else:
        raw = pull_live()
        backlog = pull_backlog()
        payroll = pull_payroll()
        program = pull_program_spend(payroll)
    a = analyze(raw); al = alerts(a)
    if "--sample" not in args:
        save_json(a, al, backlog, payroll, program)
    txt = pulse_text(a, al, backlog, payroll, program)
    if "--pulse" in args:
        post_discord(txt); logline("pulse sent" + (" +alert" if al else ""))
    elif "--alerts-only" in args:
        if al: post_discord(txt); logline("alert sent: " + "; ".join(al))
        else: logline("no alert")
    print(txt)

if __name__ == "__main__":
    main()
