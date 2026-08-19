#!/usr/bin/env python3
"""
SAM.gov fit triage — the retrieve-then-READ model (per Jon, 2026-08-19).

Titles alone don't reveal fit (a "propulsion" hit was a scuba diver propulsion
vehicle). So: (1) retrieve candidates broadly by NAICS + title terms + ptype,
(2) DOWNLOAD each solicitation's full synopsis text, (3) judge fit on the CONTENT
with the local Ollama model against the Exos capability profile, (4) surface only
real fits with a one-line reason + deadline + POC, and escalate them to the report.

Usage: python3 scripts/sam_fit_triage.py [--days 200] [--limit 25] [--min-fit 3] [--escalate]
Deterministic, no cloud egress (SAM is public; judge runs on localhost Ollama).
"""
import os, sys, json, re, argparse, urllib.request, urllib.parse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exos_capability_gate import is_aligned, escalate, norm  # DENY backstop + report

SECRETS = "/Users/exomac/.openclaw/secrets.json"
SAM = "https://api.sam.gov/opportunities/v2/search"
OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen3.6:35b-a3b"
NAICS = ["336414", "541715", "541330"]  # space-vehicle mfg, R&D phys/eng, engineering svcs
TITLE_TERMS = ["reusable launch", "suborbital", "rotating detonation", "cryogenic",
               "propellant", "hypersonic", "responsive space", "launch services",
               "in-space", "flight test"]
PTYPE = "o,p,k,r"

PROFILE = ("Exos Aerospace capabilities: reusable SUBORBITAL launch + recovery (BLK3 PSRLV); "
           "payload flight-test / de-risk / hosted payload; Scorpius Type-5 linerless composite "
           "CRYOGENIC tanks + in-space refueling / cryogenic fluid management / propellant transfer; "
           "RDRE rotating-detonation propulsion (hosted / flight-tested, not self-developed); "
           "composite rocket-motor cases / structures. NOT a fit: building satellites/spacecraft buses, "
           "missiles/interceptors, ground facility equipment/valves, IT/software, marine or diver gear.")

def key():
    return json.load(open(SECRETS))["sam_api_key"]

def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
        return r.read()

def retrieve(k, days):
    today = datetime.date.today()
    frm = (today - datetime.timedelta(days=days)).strftime("%m/%d/%Y")
    to = today.strftime("%m/%d/%Y")
    params = ["&ncode=" + n for n in NAICS] + ["&title=" + urllib.parse.quote(t) for t in TITLE_TERMS]
    seen = {}
    for p in params:
        url = f"{SAM}?api_key={k}{p}&ptype={PTYPE}&postedFrom={frm}&postedTo={to}&limit=50"
        try:
            data = json.loads(get(url))
        except Exception:
            continue
        for o in (data.get("opportunitiesData") or []):
            dl = o.get("responseDeadLine")
            if not dl:
                continue
            try:
                if datetime.date.fromisoformat(dl[:10]) < today:
                    continue  # closed
            except Exception:
                continue
            nid = o.get("noticeId")
            if nid and nid not in seen:
                seen[nid] = o
    return list(seen.values())

def synopsis(o, k):
    d = o.get("description")
    if isinstance(d, str) and d.startswith("http"):
        try:
            raw = get(d + "&api_key=" + k, timeout=30)
            j = json.loads(raw)
            txt = j.get("description", "") if isinstance(j, dict) else raw.decode("utf8", "ignore")
        except Exception:
            txt = ""
    else:
        txt = d or ""
    txt = re.sub(r"<[^>]+>", " ", txt)          # strip HTML
    return re.sub(r"\s+", " ", txt).strip()

def judge(o, syn):
    prompt = (PROFILE + "\n\nSOLICITATION:\nTitle: " + (o.get("title") or "") +
              "\nNAICS: " + str(o.get("naicsCode")) + "  PSC: " + str(o.get("classificationCode")) +
              "\nSynopsis: " + syn[:2500] +
              "\n\nRate this solicitation's fit for Exos from 0 (irrelevant) to 5 (directly biddable core fit). "
              "Return ONLY JSON: {\"fit\": <int 0-5>, \"reason\": \"<one sentence>\"}")
    # qwen3.6 is a thinking model: with format=json it spends its output on the
    # reasoning channel and returns an empty response. think:false forces the JSON out.
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "format": "json",
                       "think": False, "options": {"temperature": 0}}).encode()
    try:
        req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read())
        out = json.loads(resp.get("response", "{}"))
        return int(out.get("fit", 0)), str(out.get("reason", ""))[:200]
    except Exception as e:
        return -1, f"judge error: {e}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=200)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--min-fit", type=int, default=3)
    ap.add_argument("--escalate", action="store_true")
    a = ap.parse_args()
    k = key()
    cands = retrieve(k, a.days)
    # deterministic pre-filter: drop obvious anti-patterns before spending judge calls,
    # but KEEP generic-title items (fit may be in the body) — that's the whole point.
    cands = [o for o in cands if not _hard_drop(o)]
    cands = cands[:a.limit]
    print(f"retrieved {len(cands)} open candidates (post pre-filter); reading + judging content...\n")
    scored = []
    for o in cands:
        syn = synopsis(o, k)
        fit, reason = judge(o, syn)
        scored.append((fit, o, reason, len(syn)))
    scored.sort(key=lambda x: x[0], reverse=True)
    fits = [s for s in scored if s[0] >= a.min_fit]
    for fit, o, reason, slen in scored:
        mark = "✅" if fit >= a.min_fit else "  "
        print(f"{mark} fit={fit} | {(o.get('title') or '')[:66]}")
        print(f"     due {(o.get('responseDeadLine') or '')[:10]} | {o.get('type')} | NAICS {o.get('naicsCode')} | synopsis {slen} chars")
        print(f"     {reason}")
    print(f"\n{len(fits)} of {len(scored)} judged a real fit (>= {a.min_fit}).")
    if a.escalate and fits:
        items = [{"title": o.get("title"), "due": (o.get("responseDeadLine") or "")[:10],
                  "link": o.get("uiLink"), "agency": o.get("fullParentPathName", "")} for _, o, _, _ in fits]
        n = escalate(items, source="sam_fit_triage")
        print(f"escalated {n} to the aligned-opportunities report.")

def _hard_drop(o):
    t = ((o.get("title") or "") + " " + str(o.get("classificationCode") or "")).lower()
    return any(x in t for x in ("diver propulsion", "lawn", "mower", "janitorial", "furniture",
                                "food service", "uniform", "landscaping"))

if __name__ == "__main__":
    main()
