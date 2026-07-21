#!/usr/bin/env python3
"""
kimi_bd.py — Kimi K3 as a cheap, large-context "BD analyst tier" for NON-SENSITIVE data only.

Kimi K3 (Moonshot AI, China) is an open-frontier model: huge 1M-token context, strong agentic
coding, cheap. GREAT for business-development grunt work on PUBLIC / non-controlled data
(solicitation triage, investor/partner research, competitive intel, first-pass outreach copy).

HARD BOUNDARY (the whole point of this module): it is a Chinese-hosted API, so it must NEVER
see ITAR / EAR / CUI or proprietary Exos data. EVERY call passes through the export-control
screen (itar_ear_screen); on ANY hit the call is BLOCKED and nothing is sent. This is the
single chokepoint — BD code should import ask() from here, never call the API directly.

Stack fit: below Opus. Opus = interactive/sensitive/final; local Qwen = crons; Kimi K3 = wide,
cheap, non-sensitive BD research/drafting behind this gate. See model policy memory.

Usage:
    from kimi_bd import ask
    out = ask("Rank these solicitations for Exos fit", data=public_text, label="opp-triage")

Activate: add `moonshot_api_key` to ~/.openclaw/secrets.json (get one at platform.kimi.ai).
Self-test (proves the gate blocks controlled + passes clean, no key needed for the block path):
    python3 scripts/kimi_bd.py --self-test
"""
import json, os, re, sys, time, hashlib, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itar_ear_screen as ee

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
BLOCK_LOG = os.path.join(WS, "logs", "kimi-egress-blocked.jsonl")
AUDIT_LOG = os.path.join(WS, "logs", "kimi-bd.jsonl")
MODEL = "kimi-k3"


def _secret(*names, default=None):
    try:
        s = json.load(open(SECRETS))
    except Exception:
        s = {}
    for n in names:
        if s.get(n):
            return s[n]
    for n in names:
        if os.environ.get(n.upper()):
            return os.environ[n.upper()]
    return default


def _log(path, rec):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


class ExportControlBlocked(Exception):
    """Raised when content trips the export-control screen — the payload is NOT sent."""


def screen_or_block(text, label):
    """The gate. Returns the screened text if clean; raises ExportControlBlocked on any hit."""
    hits = ee.screen(text or "")
    if hits:
        cid = hashlib.sha1((label + text[:200]).encode()).hexdigest()[:10]
        _log(BLOCK_LOG, {"cid": cid, "label": label, "blocked": True,
                         "indicators": hits, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        raise ExportControlBlocked(
            f"BLOCKED — export-control indicators {hits}. Not sent to Kimi K3 (Chinese API). "
            "This tier is for public / non-CUI/ITAR/EAR data only.")
    return text


def ask(prompt, data="", label="bd", system=None, temperature=1, max_tokens=4000, timeout=180):
    """Ask Kimi K3 about NON-SENSITIVE material. Screens the full payload first; blocks on any
    export-control hit (raises ExportControlBlocked). Returns the model's text on success."""
    payload_text = (system or "") + "\n" + (prompt or "") + "\n" + (data or "")
    screen_or_block(payload_text, label)          # <-- hard gate; EVERYTHING that egresses is screened

    key = _secret("moonshot_api_key", "kimi_api_key")
    base = _secret("moonshot_base_url", default="https://api.moonshot.ai/v1")
    cid = hashlib.sha1((label + payload_text[:200] + str(time.time())).encode()).hexdigest()[:10]
    if not key:
        _log(AUDIT_LOG, {"cid": cid, "label": label, "gate": "passed", "sent": False,
                         "reason": "no moonshot_api_key set", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        raise RuntimeError("Gate passed but no API key. Add `moonshot_api_key` to ~/.openclaw/secrets.json "
                           "(get one at platform.kimi.ai) to activate the Kimi K3 BD tier.")

    body = {"model": MODEL, "temperature": (1 if MODEL.startswith("kimi-k3") else temperature),
            "max_tokens": max_tokens,
            "messages": ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": (prompt + ("\n\n" + data if data else ""))}]}
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key,
                                          "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    resp = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    out = resp["choices"][0]["message"]["content"]
    usage = resp.get("usage", {})
    _log(AUDIT_LOG, {"cid": cid, "label": label, "gate": "passed", "sent": True, "model": MODEL,
                     "tokens": usage, "ms": round((time.time() - t0) * 1000),
                     "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return out


def _self_test():
    print("=== kimi_bd gate self-test ===")
    controlled = ("Here is the ITAR-controlled RDRE injector CAD and USML Category IV "
                  "technical data with ECCN and the deemed export details.")
    try:
        ask(controlled, label="selftest-controlled")
        print("FAIL: controlled text was NOT blocked")
    except ExportControlBlocked as e:
        print("PASS: controlled text blocked ->", str(e)[:70])
    except RuntimeError as e:
        print("FAIL: reached API path on controlled text ->", e)

    clean = "Summarize these three public SAM.gov solicitation titles for Exos BD fit."
    try:
        out = ask(clean, label="selftest-clean")
        print("PASS: clean text sent, got", len(out), "chars back")
    except ExportControlBlocked:
        print("FAIL: clean BD text was wrongly blocked")
    except RuntimeError as e:
        print("PASS (gate): clean text passed the screen;", str(e)[:80])


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
    else:
        p = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
        data = sys.stdin.read() if not sys.stdin.isatty() else ""
        print(ask(p, data=data, label="cli"))
