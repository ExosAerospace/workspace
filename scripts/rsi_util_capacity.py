#!/usr/bin/env python3
"""
rsi_util_capacity.py — utilization + capacity-forecast module for the weekly RSI loop.

The utilization-sharing recursive self-improvement loop, reporting arm. Reads the
host-utilization samples (util_metrics.py) and produces, per machine:
  - 7-day utilization stats (avg/peak CPU%, mem%, disk headroom, Ollama activity)
  - an under/healthy/hot verdict (idle capacity is a flagged inefficiency, per Jon)
  - a demand forecast: linear trend on daily-avg load -> days until capacity threshold
  - a PROVISION-AHEAD recommendation when the crossing lands inside hardware lead-time
It folds in a lab-efficiency multiplier (config/capacity-forecast.json): new lab
capabilities (e.g. MLX-LM ~1.3x, better quant) raise EFFECTIVE capacity, pushing the
pre-order date right — so capability gains directly defer capex.

Importable by weekly-rsi.py: returns {"title","lines","issues"}. Also standalone:
  python3 scripts/rsi_util_capacity.py            # print the report section
  python3 scripts/rsi_util_capacity.py --provision-check   # exit 0=ok, 3=pre-order recommended
No LLM. Deterministic. Read-only.
"""
import os, sys, json, time
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
SRC = os.path.join(WS, "mission-control", "data", "host-utilization.jsonl")
CFG = os.path.join(WS, "config", "capacity-forecast.json")

DEFAULTS = {
    "cpu_hot_pct": 75.0,          # 7-day avg peak CPU above this = capacity pressure
    "cpu_idle_pct": 25.0,         # avg CPU below this = under-utilized (inefficiency flag)
    "mem_hot_pct": 80.0,
    "lead_time_days": 21,         # Apple ship (~10-14d) + setup buffer; pre-order if crossing <= this
    "min_history_days": 10,       # forecast needs at least this much history
    "efficiency_multiplier": 1.0, # >1.0 = lab capability gains add effective capacity
    "efficiency_note": "1.0 baseline; bump when a lab capability lands (e.g. MLX-LM ~1.3x, new quant)."
}

def _cfg():
    c = dict(DEFAULTS)
    try: c.update(json.load(open(CFG)))
    except Exception: pass
    return c

def _load():
    try:
        return [json.loads(l) for l in open(SRC).read().splitlines() if l.strip()]
    except FileNotFoundError:
        return []

def _daily_avg(rows, key_fn):
    """avg of key_fn per calendar day -> [(day, avg), ...] sorted."""
    buckets = {}
    for r in rows:
        v = key_fn(r)
        if v is None: continue
        day = r["ts"][:10]
        buckets.setdefault(day, []).append(v)
    return sorted((d, sum(vs)/len(vs)) for d, vs in buckets.items())

def _lin_forecast(series, threshold):
    """series=[(day,val)]; simple least-squares slope; days until val hits threshold."""
    if len(series) < 3: return None, None
    xs = list(range(len(series))); ys = [v for _, v in series]
    n = len(xs); sx=sum(xs); sy=sum(ys); sxx=sum(x*x for x in xs); sxy=sum(x*y for x,y in zip(xs,ys))
    denom = (n*sxx - sx*sx)
    if denom == 0: return None, None
    slope = (n*sxy - sx*sy)/denom
    intercept = (sy - slope*sx)/n
    cur = slope*(n-1)+intercept
    if slope <= 0: return slope, None            # flat/declining -> no crossing
    days = (threshold - cur)/slope
    return slope, (days if days > 0 else 0)

def build():
    c = _cfg(); rows = _load()
    lines = []; issues = []
    if not rows:
        return {"title": "🖥️ Machine utilization & capacity forecast",
                "lines": ["No utilization samples yet — util_metrics.py collector not producing data."],
                "issues": ["utilization collector has no data"]}

    hosts = sorted({r["host"] for r in rows})
    now = time.time()
    horizon = now - 7*86400
    recent = [r for r in rows if r.get("epoch", 0) >= horizon]
    eff = c["efficiency_multiplier"]

    lines.append(f"Hosts reporting: {', '.join(hosts)}  |  efficiency multiplier: {eff}x")
    provision = False

    for h in hosts:
        hr = [r for r in recent if r["host"] == h]
        allh = [r for r in rows if r["host"] == h]
        if not hr:
            issues.append(f"{h}: no samples in last 7d (collector stopped?)")
            lines.append(f"• {h}: ⚠️ no samples in the last 7 days — collector may be down.")
            continue
        cpu_vals = [r["cpu"].get("load1_pct_of_cores") for r in hr if r["cpu"].get("load1_pct_of_cores") is not None]
        mem_vals = [r["mem"].get("used_pct") for r in hr if r["mem"].get("used_pct") is not None]
        role = hr[-1].get("role", "?")
        # effective load = observed / efficiency (more efficient capability -> lower effective load)
        cpu_avg = (sum(cpu_vals)/len(cpu_vals))/eff if cpu_vals else None
        cpu_peak = (max(cpu_vals))/eff if cpu_vals else None
        mem_avg = sum(mem_vals)/len(mem_vals) if mem_vals else None
        disk_free = hr[-1]["disk"].get("root_free_gb")
        gpu_vals = [r.get("gpu",{}).get("active_pct") for r in hr
                    if r.get("gpu",{}).get("sampled") and r.get("gpu",{}).get("active_pct") is not None]
        gpu_str = f", GPU avg {sum(gpu_vals)/len(gpu_vals):.0f}%" if gpu_vals else ""
        gpu_armed_recent = any(r.get("gpu_armed") for r in hr)
        if gpu_armed_recent and not gpu_vals:
            gpu_str = ", GPU armed (awaiting sudo helper)"

        verdict = "healthy"
        if cpu_avg is not None and cpu_avg < c["cpu_idle_pct"]:
            verdict = "UNDER-UTILIZED (idle capacity — candidate for more shared load)"
            issues.append(f"{h}: under-utilized (avg CPU {cpu_avg:.0f}% eff) — push more shared work here")
        if (cpu_peak is not None and cpu_peak > c["cpu_hot_pct"]) or (mem_avg is not None and mem_avg > c["mem_hot_pct"]):
            verdict = "HOT (capacity pressure)"
            issues.append(f"{h}: hot — peak CPU {cpu_peak:.0f}% / mem {mem_avg:.0f}% eff")

        lines.append(f"• {h} [{role}]: CPU avg {cpu_avg:.0f}% / peak {cpu_peak:.0f}% (eff), "
                     f"mem avg {mem_avg:.0f}%{gpu_str}, disk free {disk_free}GB → {verdict}"
                     if cpu_avg is not None else f"• {h}: (insufficient CPU samples)")

        # forecast on daily-avg CPU
        series = _daily_avg(allh, lambda r: r["cpu"].get("load1_pct_of_cores"))
        series = [(d, v/eff) for d, v in series]
        hist_days = len(series)
        if hist_days < c["min_history_days"]:
            lines.append(f"    forecast: insufficient history ({hist_days}d of ~{c['min_history_days']}d needed) — "
                         f"available after ~{c['min_history_days']-hist_days} more days of collection.")
            continue
        slope, days_to_hot = _lin_forecast(series, c["cpu_hot_pct"])
        if days_to_hot is None:
            lines.append(f"    forecast: load flat/declining ({slope:+.2f}%/day) — capacity adequate.")
        else:
            lines.append(f"    forecast: load rising {slope:+.2f}%/day → hits {c['cpu_hot_pct']:.0f}% in ~{days_to_hot:.0f} days.")
            if days_to_hot <= c["lead_time_days"]:
                provision = True
                issues.append(f"{h}: PROVISION-AHEAD — capacity crossing in ~{days_to_hot:.0f}d (< {c['lead_time_days']}d lead time)")
                lines.append(f"    🛒 PRE-ORDER RECOMMENDED: crossing lands inside hardware lead-time "
                             f"({c['lead_time_days']}d). Raise a hardware pre-order Decision now.")

    if not provision:
        lines.append("Provision status: ✅ capacity adequate within lead-time; re-evaluate next week.")
    lines.append("Efficiency lever: " + c["efficiency_note"])
    return {"title": "🖥️ Machine utilization & capacity forecast", "lines": lines,
            "issues": issues, "_provision": provision}

if __name__ == "__main__":
    r = build()
    if "--provision-check" in sys.argv[1:]:
        print("PROVISION-AHEAD recommended" if r.get("_provision") else "capacity OK")
        sys.exit(3 if r.get("_provision") else 0)
    print("##", r["title"])
    for l in r["lines"]: print(l)
    if r["issues"]:
        print("\nISSUES:")
        for i in r["issues"]: print(" -", i)
