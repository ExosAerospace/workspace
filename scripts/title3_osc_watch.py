#!/usr/bin/env python3
"""
title3_osc_watch.py — deterministic watcher for two non-dilutive capital windows
for the Scorpius cryo-tank line + RDRE-enabled reusable vehicle (see MC task 2287):

  1. DPA Title III FOA FA8650-19-S-5010 (AFRL/RXKM) posting a NEW Call / status change
  2. OSC Credit Program NOFO dropping (cto.mil/osc/credit-program)

Detects via: grants.gov Search2 API (opp status/close-date change or new matching opp),
a SAM.gov keyword sweep, and text-hash change on the two program pages. Baselines on the
first run (no alert), then alerts on any change. Alert = Discord post to #series-a + email.

State: data/title3_osc_watch_state.json   Reads: ~/.openclaw/secrets.json (sam_api_key)
"""
# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent, is_transient as _gis_transient
    _GRUN = _gnew_run("title3-osc-watch")
    _gevent(_GRUN, "start")
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gt = _gis_transient(v); _gevent(_GRUN, "transient_skip" if _gt else "error", status="transient" if _gt else "error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import json, os, re, sys, hashlib, subprocess, urllib.parse, urllib.request, shutil
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from datetime import datetime, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
STATE = os.path.join(WS, "data", "title3_osc_watch_state.json")
TO = "jquinn@exosaero.com"
DISCORD_CHANNEL = "channel:1501636728711282741"   # #series-a
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"

SAM_API = "https://api.sam.gov/opportunities/v2/search"
GRANTS_API = "https://api.grants.gov/v1/api/search2"
TITLE3_NUMBER = "FA8650-19-S-5010"
GRANTS_KEYWORD = "Defense Production Act Title III"
SAM_TERMS = ["Defense Production Act Title III", "DPA Title III"]
PAGES = {
    "OSC Credit Program (cto.mil)": "https://www.cto.mil/osc/credit-program/",
}
NOFO_KWS = ("nofo", "notice of funding", "apply now", "application", "open", "submit", "solicitation")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept": "text/html,application/json"}

def load(p, d):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return d

def key():
    return load(SECRETS, {}).get("sam_api_key")

def fetch_text(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode("utf-8", "ignore")
    txt = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip().lower()
    return txt

def _grants_post(payload):
    req = urllib.request.Request(GRANTS_API, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        d = json.loads(r.read().decode())
    return (d.get("data", {}) or {}).get("oppHits", []) or []

def grants_search():
    """Merge an exact opp-number lookup with a keyword sweep, incl. closed status so we
    already track FA8650-19-S-5010 (currently suspended) and catch its flip to a new Call."""
    merged = {}
    for payload in ({"oppNum": TITLE3_NUMBER, "oppStatuses": "forecasted|posted|closed|archived", "rows": 25},
                    {"keyword": GRANTS_KEYWORD, "oppStatuses": "forecasted|posted|closed", "rows": 100}):
        try:
            for h in _grants_post(payload):
                num = (h.get("number") or "").strip()
                if num: merged[num] = h
        except Exception as e:
            print("  grants query failed:", e)
    # keep only opps actually relevant to DPA Title III (kills generic keyword noise)
    out = []
    for num, h in merged.items():
        title = (h.get("title") or "").lower()
        if "fa8650" in num.lower() or "defense production act title iii" in title or "dpa title iii" in title:
            out.append(h)
    return out

def sam_query(k, title):
    today = datetime.now()
    params = {"api_key": k, "title": title,
              "postedFrom": (today - timedelta(days=120)).strftime("%m/%d/%Y"),
              "postedTo": today.strftime("%m/%d/%Y"), "ptype": "o,p,r,k", "limit": "50"}
    req = urllib.request.Request(SAM_API + "?" + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode()).get("opportunitiesData", []) or []

def discord(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                        "--target", DISCORD_CHANNEL, "-m", text],
                       capture_output=True, timeout=60)
    except Exception as e:
        print("discord post failed:", e)

def email(subject, body):
    msg = f"From: jquinnexo@pm.me\nTo: {TO}\nSubject: {subject}\n\n{body}\n"
    try:
        subprocess.run(["msmtp", "-a", "protonmail", TO], input=msg.encode(),
                       capture_output=True, timeout=60)
    except Exception as e:
        print("email failed:", e)

def main():
    st = load(STATE, {})
    first = not st
    grants_state = st.get("grants", {})
    pages_state = st.get("pages", {})
    sam_seen = set(st.get("sam_seen", []))
    alerts = []

    # 1) grants.gov — FA8650-19-S-5010 status/close-date change or new matching opp
    try:
        hits = grants_search()
        new_grants = {}
        for h in hits:
            num = (h.get("number") or "").strip()
            if not num: continue
            sig = {"status": h.get("oppStatus", ""), "close": h.get("closeDate", ""),
                   "title": h.get("title", ""), "id": h.get("id", "")}
            new_grants[num] = sig
            prev = grants_state.get(num)
            is_t3 = TITLE3_NUMBER.lower() in num.lower()
            if prev is None and not first:
                alerts.append(f"NEW grants.gov opportunity matching DPA Title III: {num} — "
                              f"{sig['title']} [status {sig['status']}, closes {sig['close'] or 'n/a'}]")
            elif prev and (prev.get("status") != sig["status"] or prev.get("close") != sig["close"]):
                flag = " ← FA8650-19-S-5010 (the standing Title III FOA)" if is_t3 else ""
                alerts.append(f"grants.gov CHANGE on {num}{flag}: status {prev.get('status')}→{sig['status']}, "
                              f"close {prev.get('close') or 'n/a'}→{sig['close'] or 'n/a'} "
                              f"(a status flip / new close date often signals a new Call)")
        grants_state = new_grants
    except Exception as e:
        print("grants.gov check failed (skipped, no alert):", e)

    # 2) SAM.gov keyword sweep (in case a Call posts as its own notice)
    k = key()
    if k:
        found = {}
        for term in SAM_TERMS:
            try:
                for n in sam_query(k, term):
                    nid = n.get("noticeId") or n.get("solicitationNumber") or n.get("title")
                    if nid: found[nid] = n
            except Exception as e:
                print(f"  SAM query failed '{term}':", e)
        for nid, n in found.items():
            if nid not in sam_seen and not first:
                alerts.append(f"NEW SAM.gov notice: {n.get('title','(no title)')} "
                              f"[{n.get('type','')}, posted {n.get('postedDate','')}, "
                              f"sol# {n.get('solicitationNumber','n/a')}] {n.get('uiLink','')}")
            sam_seen.add(nid)

    # 3) program-page text-hash change detection
    for name, url in PAGES.items():
        try:
            txt = fetch_text(url)
            h = hashlib.sha256(txt.encode()).hexdigest()[:16]
            prev = pages_state.get(url, {})
            if prev and prev.get("hash") != h and not first:
                kws = [w for w in NOFO_KWS if w in txt]
                alerts.append(f"PAGE CHANGED — {name}: {url}\n"
                              f"    funding keywords present: {', '.join(kws) if kws else 'none'} "
                              f"(check for a new Call / NOFO)")
            pages_state[url] = {"hash": h}
        except Exception as e:
            print(f"page fetch failed ({name}), skipped:", e)

    # persist
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"grants": grants_state, "pages": pages_state,
               "sam_seen": sorted(sam_seen), "last_run": datetime.now().isoformat()},
              open(STATE, "w"), indent=2)

    if first:
        print(f"First run — baselined {len(grants_state)} grants opps, {len(pages_state)} pages, "
              f"{len(sam_seen)} SAM notices. No alert.")
        return 0
    if not alerts:
        print("No change. Both windows still closed/unchanged."); return 0

    header = ("🟡 **DPA Title III / OSC capital-window watch — CHANGE DETECTED**\n"
              "For the Scorpius cryo-tank line + RDRE reusable-vehicle brief (MC task 2287). "
              "The letterhead capability brief is staged and ready to finalize.\n\n")
    body = header + "\n".join(f"• {a}" for a in alerts) + (
        "\n\nNext: confirm it's a real Call/NOFO, finalize the brief + white paper, "
        "line up the DoD champion, and send via Jon (.mil routes through Jon).")
    discord(body)
    # email() removed 2026-09-10 (Jon: watcher digests -> Discord only, not inbox); discord(body) above handles it
    print(f"ALERT sent ({len(alerts)} change(s)).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
