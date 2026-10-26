#!/usr/bin/env python3
"""Web-search failover: Tavily primary, Gemini (Google grounding) fallback.

Jon 2026-10-26: keep Tavily for its detailed search + references; fall back to
Google only when Tavily fails or we pass the $54/mo budget.

OpenClaw has no ordered fallback for an explicitly selected provider (and
auto-detect ranks Gemini ahead of Tavily), so this flips
tools.web.search.provider between "tavily" and "gemini".

Budget: Project plan $30 (4,000 credits) + pay-go at $0.008/credit, capped at
3,000 pay-go credits = $54 (https://www.tavily.com/pricing). Credits reset on
the 1st, so the switch back to Tavily happens on its own when usage resets.

Agents that call tavily_search/tavily_extract directly (research-web, the
Research Team and capture crons) get the same failover: while on Gemini, both
tools are added to the global tools.deny, so those agents use web_search,
which now routes to Gemini. They come back off the denylist when Tavily recovers.
Every job that allows tavily_* in toolsAllow also allows web_search.

Runs from launchd com.exos.search-failover every 10 min. Checking /usage costs
no credits.
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime

BUDGET_USD = 54.0
PLAN_USD = 30.0
PAYGO_PER_CREDIT = 0.008
HEADROOM_USD = 0.50          # switch slightly before the hard cap
FAIL_THRESHOLD = 2           # consecutive /usage failures before switching
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.expanduser("~/.openclaw/state/search-failover.json")
LOG = os.path.expanduser("~/.openclaw/logs/search-failover.log")


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")
    print(msg)


def load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {"fails": 0}


def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(s, open(STATE, "w"), indent=2)


def tavily_usage():
    key = json.load(open(SECRETS))["tavily_api_key"]
    req = urllib.request.Request("https://api.tavily.com/usage",
                                 headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def current_provider():
    out = subprocess.run(["openclaw", "config", "get", "tools.web.search.provider"],
                         capture_output=True, text=True, timeout=60)
    return out.stdout.strip().strip('"').splitlines()[-1] if out.stdout.strip() else ""


def set_provider(p):
    subprocess.run(["openclaw", "config", "set", "tools.web.search.provider", p],
                   check=True, capture_output=True, text=True, timeout=60)


TAVILY_TOOLS = ["tavily_search", "tavily_extract"]


def get_deny():
    out = subprocess.run(["openclaw", "config", "get", "tools.deny", "--json"],
                         capture_output=True, text=True, timeout=60)
    try:
        v = json.loads(out.stdout)
        return v if isinstance(v, list) else []
    except Exception:
        return []


def sync_deny(failover):
    cur = get_deny()
    new = ([x for x in cur if x not in TAVILY_TOOLS] + TAVILY_TOOLS) if failover \
        else [x for x in cur if x not in TAVILY_TOOLS]
    if sorted(new) == sorted(cur):
        return False
    if new:
        subprocess.run(["openclaw", "config", "set", "tools.deny", json.dumps(new), "--strict-json"],
                       check=True, capture_output=True, text=True, timeout=60)
    else:
        subprocess.run(["openclaw", "config", "unset", "tools.deny"],
                       check=True, capture_output=True, text=True, timeout=60)
    log(f"tools.deny -> {new}")
    return True


def main():
    s = load_state()
    want, reason = "tavily", "healthy"
    try:
        u = tavily_usage()
        acct = u["account"]
        paygo = acct.get("paygo_usage", 0)
        spend = PLAN_USD + paygo * PAYGO_PER_CREDIT
        remaining = u["key"]["limit"] - u["key"]["usage"]
        s.update(fails=0, spend_usd=round(spend, 2), credits_remaining=remaining,
                 checked=datetime.now().isoformat(timespec="seconds"))
        if spend >= BUDGET_USD - HEADROOM_USD or remaining <= 25:
            want, reason = "gemini", f"budget: ${spend:.2f}/${BUDGET_USD:.0f}, {remaining} credits left"
    except Exception as e:
        s["fails"] = s.get("fails", 0) + 1
        if s["fails"] >= FAIL_THRESHOLD:
            want, reason = "gemini", f"tavily failure x{s['fails']}: {e}"
        else:
            save_state(s)
            log(f"tavily check failed ({s['fails']}/{FAIL_THRESHOLD}): {e}")
            return
    cur = current_provider()
    if cur != want:
        set_provider(want)
        log(f"switched web_search {cur or '(unset)'} -> {want} ({reason})")
    sync_deny(want == "gemini")
    s["provider"] = want
    s["reason"] = reason
    save_state(s)
    if "--verbose" in sys.argv:
        print(json.dumps(s, indent=2))


if __name__ == "__main__":
    main()
