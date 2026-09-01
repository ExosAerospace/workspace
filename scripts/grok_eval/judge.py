#!/usr/bin/env python3
"""judge.py — LLM-judged quality scoring for the model eval (4-way + local).

For each eval item, sends ALL models' answers to a judge model (Opus 4.8) together and scores each
on three dimensions (1-5): technical ACCURACY, DESIGN depth/usefulness, GROUNDING (no hallucination).
Judging per-item (not per-answer) is cheaper and gives a true head-to-head. Aggregates per model
overall and per category, writes a markdown report, and prints a summary.

Usage: python3 judge.py [results_dir ...]
  No args → auto: scan results/*/ and take the newest answer per (model,item).
"""
import os, sys, json, glob, re, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")

def secret(n, d=None):
    try: return json.load(open(SECRETS)).get(n, d)
    except Exception: return d

def gather(dirs):
    """model -> item_id -> answer text (newest dir wins)."""
    if not dirs:
        dirs = sorted(glob.glob(os.path.join(HERE, "results", "*")))
    data = {}
    for d in dirs:
        if not os.path.isdir(d): continue
        for mdir in glob.glob(os.path.join(d, "*")):
            if not os.path.isdir(mdir): continue
            model = os.path.basename(mdir)
            for f in glob.glob(os.path.join(mdir, "*.txt")):
                iid = os.path.basename(f)[:-4]
                try: txt = open(f).read()
                except Exception: continue
                if txt.strip():
                    data.setdefault(model, {})[iid] = txt  # later dirs overwrite (sorted asc)
    return data

def opus_judge(prompt):
    key = secret("anthropic_default_key_main") or secret("anthropic_default_key_coding")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages",
        data=json.dumps({"model": "claude-opus-4-8", "max_tokens": 2000,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Content-Type": "application/json", "x-api-key": key, "anthropic-version": "2023-06-01"},
        method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(r.read())
    return "".join(b.get("text", "") for b in out.get("content", []) if b.get("type") == "text")

def main():
    dirs = sys.argv[1:]
    data = gather(dirs)
    models = sorted(data.keys())
    if not models:
        print("no results found"); return
    ev = {it["id"]: it for it in json.load(open(os.path.join(HERE, "eval_set.json")))["items"]}
    scores = {m: [] for m in models}   # list of dicts {accuracy,design,grounding,category}
    report = ["# Model Eval — LLM-Judged (Opus 4.8 judge)",
              f"_{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_  ·  models: {', '.join(models)}\n"]
    for iid, it in ev.items():
        answers = {m: data[m].get(iid) for m in models if data.get(m, {}).get(iid)}
        if not answers: continue
        rubric = "; ".join(it.get("rubric", []))
        blocks = "\n\n".join(f"### MODEL: {m}\n{answers[m][:3500]}" for m in answers)
        jp = (f"You are a strict aerospace/controls domain judge. Score each model's answer to the "
              f"prompt below on three axes, integers 1-5 (5=best):\n"
              f"- accuracy: technical correctness, no factual/engineering errors\n"
              f"- design: depth and usefulness for real early-design/trade-study work\n"
              f"- grounding: stays factual, no hallucinated specifics/citations\n\n"
              f"PROMPT: {it['prompt']}\n\nRUBRIC (what a strong answer contains): {rubric}\n\n"
              f"ANSWERS:\n{blocks}\n\n"
              f"Return ONLY a JSON array, one object per model, each: "
              f'{{"model":"...","accuracy":N,"design":N,"grounding":N,"note":"<=15 words, flag any inaccuracy"}}. '
              f"No prose outside the JSON.")
        try:
            raw = opus_judge(jp)
            m = re.search(r"\[.*\]", raw, re.S)
            arr = json.loads(m.group(0)) if m else []
        except Exception as e:
            report.append(f"- judge error on {iid}: {e}"); continue
        report.append(f"\n## {iid} ({it['category']})")
        for o in arr:
            mdl = o.get("model")
            if mdl not in scores:
                # tolerate judge renaming; match by substring
                mdl = next((x for x in models if x in str(o.get("model","")) or str(o.get("model","")) in x), None)
            if not mdl: continue
            rec = {"accuracy": o.get("accuracy",0), "design": o.get("design",0),
                   "grounding": o.get("grounding",0), "category": it["category"]}
            scores[mdl].append(rec)
            report.append(f"- **{mdl}**: acc {rec['accuracy']} / design {rec['design']} / ground {rec['grounding']} — {o.get('note','')}")

    # aggregates
    report.append("\n\n# Aggregate (avg across items)\n")
    report.append("| Model | Accuracy | Design | Grounding | Composite |")
    report.append("|---|---|---|---|---|")
    summary = []
    for m in models:
        rs = scores[m]
        if not rs: continue
        a = sum(r["accuracy"] for r in rs)/len(rs); d = sum(r["design"] for r in rs)/len(rs); g = sum(r["grounding"] for r in rs)/len(rs)
        comp = (a+d+g)/3
        report.append(f"| {m} | {a:.2f} | {d:.2f} | {g:.2f} | **{comp:.2f}** |")
        summary.append((m, a, d, g, comp))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outp = os.path.join(HERE, "results", f"judge-report-{ts}.md")
    open(outp, "w").write("\n".join(report))
    summary.sort(key=lambda x: -x[4])
    print(f"\nJUDGED SCORES (composite desc) — report: {outp}\n")
    print(f"{'model':<18}{'acc':>6}{'design':>8}{'ground':>8}{'comp':>8}")
    for m,a,d,g,c in summary:
        print(f"{m:<18}{a:>6.2f}{d:>8.2f}{g:>8.2f}{c:>8.2f}")

if __name__ == "__main__":
    main()
