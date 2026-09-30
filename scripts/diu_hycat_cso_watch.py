#!/usr/bin/env python3
"""
diu_hycat_cso_watch.py — deterministic watcher for a DIU HyCAT / hypersonic-test CSO
(MC task #2488, BD-032). Replaces the weekly LLM cron ad2b3471 (Jon 2026-09-30:
"set a watcher to alert the moment a HyCAT CSO opens").

  1. diu.mil/work-with-us/open-solicitations (server-rendered HTML) — parse every
     /work-with-us/submit-solution/PROJxxxxx card (portfolio, title, closing date).
     For each NEW card, fetch its page and keyword-score it for HyCAT fit.
  2. SAM.gov keyword sweep ("HyCAT", "High-Cadence Airborne Testing") in case DIU
     posts a notice there.

Relevant new item → Discord DM to Jon. Unrelated new DIU openings (C-UAS, ISR, ...) are
logged to state only — no noise. Baselines silently on first run.

State: data/diu_hycat_cso_watch_state.json   Reads: ~/.openclaw/secrets.json (sam_api_key)
"""
import json, os, re, sys, html, shutil, subprocess, urllib.parse, urllib.request
from datetime import datetime, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.join(WS, "data", "diu_hycat_cso_watch_state.json")
DISCORD_TARGET = "user:1501632195163590739"   # Jon DM
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"

BASE = "https://www.diu.mil"
OPEN_PAGE = BASE + "/work-with-us/open-solicitations"
SAM_API = "https://api.sam.gov/opportunities/v2/search"
SAM_TERMS = ["HyCAT", "High-Cadence Airborne Testing"]
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

# strong = alert on its own; weak = alert only if 2+ hit
STRONG = ("hycat", "high-cadence airborne test", "hypersonic", "suborbital", "sounding rocket",
          "reusable launch", "flight test", "flight-test", "test bed", "testbed", "rocket")
WEAK = ("reusable", "launch", "high-cadence", "high cadence", "re-entry", "reentry",
        "thermal protection", "propulsion", "missile defense", "boost", "space access")


def load(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "ignore")


def text_of(raw):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", t)).strip()


def parse_cards(raw):
    cards = {}
    for m in re.finditer(r'<a href="(/work-with-us/submit-solution/(PROJ\w+))"[^>]*class="opportunity"[^>]*>(.*?)</a>',
                         raw, re.S):
        path, pid, inner = m.groups()
        h6 = re.search(r"<h6[^>]*>(.*?)</h6>", inner, re.S)
        ps = [text_of(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", inner, re.S)]
        closing = next((p for p in ps if p.lower().startswith("closing")), "")
        title = next((p for p in ps if not p.lower().startswith("closing")), "(untitled)")
        cards[pid] = {"portfolio": text_of(h6.group(1)) if h6 else "", "title": title,
                      "closing": closing.replace("Closing:", "").strip(), "url": BASE + path}
    counts = {text_of(h): text_of(c) for h, c in
              re.findall(r'<h4[^>]*>(Pathways through[^<]*)</h4>\s*<div class="pill[^"]*"[^>]*>([^<]*)</div>', raw)}
    return cards, counts


def score(text):
    t = text.lower()
    s = [k for k in STRONG if k in t]
    w = [k for k in WEAK if k in t]
    return (bool(s) or len(w) >= 2), s + w


def sam_sweep(k):
    today = datetime.now()
    found = {}
    for term in SAM_TERMS:
        params = {"api_key": k, "title": term, "postedFrom": (today - timedelta(days=60)).strftime("%m/%d/%Y"),
                  "postedTo": today.strftime("%m/%d/%Y"), "limit": "50"}
        try:
            req = urllib.request.Request(SAM_API + "?" + urllib.parse.urlencode(params), headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                for n in json.loads(r.read().decode()).get("opportunitiesData", []) or []:
                    nid = n.get("noticeId") or n.get("solicitationNumber")
                    if nid: found[nid] = n
        except Exception as e:
            print(f"  SAM query failed '{term}':", e)
    return found


def discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD_TARGET, "-m", text], capture_output=True, timeout=60)
    except Exception as e:
        print("discord post failed:", e)


def main():
    st = load(STATE, {})
    first = not st
    seen = st.get("diu_seen", {})
    sam_seen = set(st.get("sam_seen", []))
    alerts, logged = [], []

    try:
        raw = get(OPEN_PAGE)
        cards, counts = parse_cards(raw)
        if not cards and "submit-solution" in raw:
            print("WARN: page has submit-solution links but parser found none — markup changed?")
        for pid, c in cards.items():
            if pid in seen:
                continue
            try:
                detail = text_of(get(c["url"]))
            except Exception as e:
                detail = ""
                print(f"  detail fetch failed {pid}:", e)
            hit, kws = score(" ".join([c["portfolio"], c["title"], detail]))
            c.update({"first_seen": datetime.now().isoformat(timespec="minutes"), "relevant": hit, "kws": kws})
            seen[pid] = c
            if first:
                continue
            line = (f"**{c['title']}** ({c['portfolio']}) — closes {c['closing'] or 'n/a'} "
                    f"(per DIU portal, subject to change)\n  {c['url']}")
            (alerts if hit else logged).append(line + (f"\n  matched: {', '.join(kws[:6])}" if hit else ""))
        st["last_counts"] = counts
    except Exception as e:
        print("DIU page fetch failed (skipped, no alert):", e)

    k = load(SECRETS, {}).get("sam_api_key")
    if k:
        for nid, n in sam_sweep(k).items():
            if nid not in sam_seen and not first:
                alerts.append(f"SAM.gov: **{n.get('title','(no title)')}** [{n.get('type','')}, "
                              f"posted {n.get('postedDate','')}, sol# {n.get('solicitationNumber','n/a')}, "
                              f"due {n.get('responseDeadLine') or 'n/a'}]\n  {n.get('uiLink','')}")
            sam_seen.add(nid)

    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    st.update({"diu_seen": seen, "sam_seen": sorted(sam_seen), "last_run": datetime.now().isoformat()})
    json.dump(st, open(STATE, "w"), indent=2)

    if first:
        print(f"First run — baselined {len(seen)} DIU cards, {len(sam_seen)} SAM notices. No alert.")
        return 0
    for l in logged:
        print("new DIU opening, not HyCAT-relevant (no alert):", l.splitlines()[0])
    if not alerts:
        print("No new HyCAT-relevant opening."); return 0

    body = ("🔴 **DIU HyCAT / hypersonic-test opening detected** (MC #2488, BD-032)\n\n"
            + "\n".join(f"• {a}" for a in alerts)
            + "\n\nBD-032 strategy + capability statement are pre-staged. Say the word and I draft the "
              "CSO solution brief + compliance map for your review (you submit — .mil routes through you).")
    discord(body)
    print(f"ALERT sent ({len(alerts)} item(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
