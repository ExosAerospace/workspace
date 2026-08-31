#!/usr/bin/env python3
"""Summarize a grok_eval results dir into a model × category matrix (success/latency/size).

Usage:
    python3 score.py                 # newest results dir
    python3 score.py results/<ts>    # specific run

Manual/LLM-judge scoring TODO: hook Opus as an LLM judge over results/<ts>/<model>/<id>.txt
against eval_set.json rubrics. Not called by default (avoids spend).
"""
import os, sys, json, glob

HERE = os.path.dirname(os.path.abspath(__file__))

def latest():
    dirs = sorted(glob.glob(os.path.join(HERE, "results", "*")))
    return dirs[-1] if dirs else None

def main():
    rd = sys.argv[1] if len(sys.argv) > 1 else latest()
    if not rd or not os.path.isdir(rd):
        print("no results dir found"); return
    if not os.path.isabs(rd):
        rd = os.path.join(HERE, rd) if not rd.startswith(HERE) else rd
    summ = json.load(open(os.path.join(rd, "summary.json")))
    ev = {it["id"]: it for it in json.load(open(os.path.join(HERE, "eval_set.json")))["items"]}
    models = summ["models"]
    cats = sorted(set(it["category"] for it in ev.values()))
    print(f"\nRun: {summ['timestamp']}   models: {', '.join(models)}\n")
    # per-model rollup
    print(f"{'model':<16} {'ok':>5} {'avg_ms':>8} {'avg_chars':>10}")
    print("-" * 44)
    for m in models:
        rs = [r for r in summ["runs"] if r["model"] == m]
        ok = [r for r in rs if r.get("ok")]
        avg_ms = int(sum(r["latency_ms"] for r in ok) / len(ok)) if ok else 0
        avg_c = int(sum(r["chars"] for r in ok) / len(ok)) if ok else 0
        print(f"{m:<16} {len(ok):>3}/{len(rs):<2} {avg_ms:>8} {avg_c:>10}")
    print("\nOpen an answer:  results/<ts>/<model>/<item_id>.txt")
    print("Rubrics live in eval_set.json for side-by-side judging.\n")

if __name__ == "__main__":
    main()
