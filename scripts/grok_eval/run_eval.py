#!/usr/bin/env python3
"""Exos model-eval harness — Grok 4.6/4.7 vs our model mix on NON-CONTROLLED, BLK3-adjacent tasks.

HARD RULE: this harness runs ONLY on non-controlled/public content. The runner aborts if any
eval item has controlled != false. Never add ITAR/CUI/BLK3-vehicle data to eval_set.json.

Local Ollama models run by default (free). Cloud models are each gated behind a flag and OFF by
default so no spend happens without an explicit request:
    python3 run_eval.py                 # local only (qwen3.6 + gemma4)
    python3 run_eval.py --grok          # + Grok 4.6 (needs xai_api_key in ~/.openclaw/secrets.json)
    python3 run_eval.py --opus --kimi   # + Opus 4.8 and Kimi K3
    python3 run_eval.py --only grok      # ONLY Grok (skip local)
    python3 run_eval.py --grok-model grok-4.7   # after 4.7 GA

Secrets: ~/.openclaw/secrets.json  (xai_api_key, anthropic_default_key_main, moonshot_api_key)
Results: results/<UTC-timestamp>/<model>/<item_id>.txt  +  results/<ts>/summary.json
"""
import os, sys, json, time, urllib.request, urllib.error, subprocess, tempfile, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
OLLAMA = "http://localhost:11434"
LOCAL_MODELS = ["qwen3.6:35b-a3b", "gemma4:e4b"]
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.15.0/bin/openclaw"

def _oc_env():
    env = dict(os.environ)
    env["PATH"] = ("/Users/exomac/.local/share/mise/installs/node/24.15.0/bin:"
                   "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    return env

def secret(name, default=None):
    try:
        return json.load(open(SECRETS)).get(name, default)
    except Exception:
        return default

def _post(url, body, headers, timeout):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read().decode())
    return out, int((time.time() - t0) * 1000)

# ── model callers: each returns (text, latency_ms, usage_dict_or_None) ──
def call_ollama(model, prompt, timeout=300):
    out, ms = _post(f"{OLLAMA}/api/chat",
                    {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
                    {"Content-Type": "application/json"}, timeout)
    return out.get("message", {}).get("content", ""), ms, None

def call_opus(prompt, timeout=240):
    # The raw anthropic key in secrets is not valid for the Messages API (MC routes via the CLI),
    # so run Opus through `openclaw agent` in an ISOLATED session (never posts to any channel).
    pf = None
    t0 = time.time()
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tf:
            tf.write(prompt); pf = tf.name
        skey = "agent:main:evalopus-" + hashlib.sha1(prompt.encode()).hexdigest()[:12]
        r = subprocess.run([OPENCLAW, "agent", "--model", "anthropic/claude-opus-4-8",
                            "--session-key", skey, "--message-file", pf, "--json"],
                           capture_output=True, text=True, timeout=timeout, env=_oc_env())
        j = json.loads(r.stdout)
        res = (j or {}).get("result", {}) or {}
        txt = "\n".join((p.get("text") or "") for p in res.get("payloads", []) if p.get("text")).strip()
        if not txt:
            txt = ((res.get("meta", {}) or {}).get("finalAssistantVisibleText") or "").strip()
        if not txt:
            raise RuntimeError("empty opus reply rc=%s %s" % (r.returncode, (r.stderr or '')[:120]))
        return txt, int((time.time() - t0) * 1000), None
    finally:
        if pf:
            try: os.unlink(pf)
            except Exception: pass

def _openai_compat(base, key, model, prompt, timeout, fallback_model=None, temperature=0.3):
    try:
        out, ms = _post(base.rstrip("/") + "/chat/completions",
                        {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature},
                        {"Content-Type": "application/json", "Authorization": "Bearer " + key}, timeout)
    except urllib.error.HTTPError as e:
        if e.code in (404, 400) and fallback_model:
            out, ms = _post(base.rstrip("/") + "/chat/completions",
                            {"model": fallback_model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature},
                            {"Content-Type": "application/json", "Authorization": "Bearer " + key}, timeout)
        else:
            raise
    txt = out.get("choices", [{}])[0].get("message", {}).get("content", "")
    return txt, ms, out.get("usage")

def call_grok(prompt, model="grok-4.6", timeout=120):
    key = secret("xai_api_key") or os.environ.get("XAI_API_KEY")
    if not key:
        raise RuntimeError("pending key: xai_api_key")
    return _openai_compat("https://api.x.ai/v1", key, model, prompt, timeout,
                          fallback_model=("grok-4-6" if model == "grok-4.6" else None))

def call_kimi(prompt, timeout=120):
    key = secret("moonshot_api_key") or secret("kimi_api_key")
    if not key:
        raise RuntimeError("pending key: moonshot_api_key")
    base = secret("moonshot_base_url", "https://api.moonshot.ai/v1")
    model = os.environ.get("KIMI_MODEL") or secret("kimi_eval_model", "kimi-k3")
    # kimi-k3 rejects any temperature != 1 ("only 1 is allowed for this model")
    return _openai_compat(base, key, model, prompt, timeout, temperature=1)

def main():
    argv = sys.argv[1:]
    grok_model = "grok-4.6"
    if "--grok-model" in argv:
        grok_model = argv[argv.index("--grok-model") + 1]
    only = argv[argv.index("--only") + 1] if "--only" in argv else None

    # Build the model roster
    roster = []  # (label, callable)
    if not only and "--no-local" not in argv:
        for m in LOCAL_MODELS:
            roster.append((m, (lambda p, mm=m: call_ollama(mm, p))))
    if "--opus" in argv or only == "opus":
        roster.append(("opus-4.8", lambda p: call_opus(p)))
    if "--kimi" in argv or only == "kimi":
        roster.append(("kimi-k3", lambda p: call_kimi(p)))
    if "--grok" in argv or only == "grok":
        roster.append((grok_model, lambda p: call_grok(p, model=grok_model)))
    if only in LOCAL_MODELS:
        roster = [(only, (lambda p, mm=only: call_ollama(mm, p)))]

    ev = json.load(open(os.path.join(HERE, "eval_set.json")))
    items = ev["items"]
    bad = [it["id"] for it in items if it.get("controlled") is not False]
    if bad:
        print(f"ABORT: non-controlled guardrail — these items are not marked controlled:false: {bad}")
        sys.exit(2)

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = os.path.join(HERE, "results", ts)
    os.makedirs(outdir, exist_ok=True)
    summary = {"timestamp": ts, "models": [r[0] for r in roster], "runs": []}
    print(f"eval: {len(items)} items × {len(roster)} models -> {outdir}")

    for label, fn in roster:
        mdir = os.path.join(outdir, label.replace("/", "_").replace(":", "_"))
        os.makedirs(mdir, exist_ok=True)
        for it in items:
            rec = {"model": label, "item": it["id"], "category": it["category"]}
            try:
                txt, ms, usage = fn(it["prompt"])
                open(os.path.join(mdir, it["id"] + ".txt"), "w").write(txt)
                rec.update({"ok": True, "latency_ms": ms, "chars": len(txt), "usage": usage})
                print(f"  [{label}] {it['id']} ok {ms}ms {len(txt)}c")
            except Exception as e:
                rec.update({"ok": False, "error": str(e)[:200]})
                print(f"  [{label}] {it['id']} FAIL {str(e)[:120]}")
            summary["runs"].append(rec)
        json.dump(summary, open(os.path.join(outdir, "summary.json"), "w"), indent=2)

    ok = sum(1 for r in summary["runs"] if r.get("ok"))
    print(f"done: {ok}/{len(summary['runs'])} runs ok -> {os.path.join(outdir,'summary.json')}")

if __name__ == "__main__":
    main()
