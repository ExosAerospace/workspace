#!/usr/bin/env python3
"""
payload_pipeline_to_opps.py — Bridge the BLK3 Payload Sales pipeline into MC Opportunities.

The sourcing engine enriches qualified payload BUYERS into
tasks/blk3-payload-sales-pipeline.md (POC, segment, fit, status, next action),
but those warm prospects never reached mission-control/data/opportunities.json,
so the Opportunity Processor never priced them. This deterministic bridge closes
that gap:

  pipeline.md  →  PAY-#### blocks in opportunities-tracker.md  →  generator  →  opportunities.json  →  processor prices off rate card

Idempotent: rewrites a single managed section (between AUTO markers) every run,
so daily runs update in place instead of piling up duplicates. Skips any prospect
already represented by a non-PAY opportunity (e.g. SwRI lives as BD-024/025).

Usage: payload_pipeline_to_opps.py [--dry-run]
"""
import os, re, sys, json, hashlib, subprocess, argparse

WORKSPACE = "/Users/exomac/.openclaw/workspace"
PIPELINE  = os.path.join(WORKSPACE, "tasks/blk3-payload-sales-pipeline.md")
OPP_MD    = os.path.join(WORKSPACE, "opportunities-tracker.md")
OPP_JSON  = os.path.join(WORKSPACE, "mission-control/data/opportunities.json")
GENERATOR = os.path.join(WORKSPACE, "scripts/dashboard-data-generator.py")

BEGIN = "<!-- PAYLOAD-PIPELINE-AUTO:BEGIN (managed by payload_pipeline_to_opps.py) -->"
END   = "<!-- PAYLOAD-PIPELINE-AUTO:END -->"

# Full-bay list anchor for scoring/display; the processor computes the real quote
# off pricing/rate-card.json. List price only — no discount baked in.
DEFAULT_VALUE = "$1,012,500 (full-bay list; final quote priced off rate card)"
DUE = "BLK3 Flight 2 — early 2027"
OPP_TYPE = "Payload Sale (BLK3 early 2027)"

# Statuses in the pipeline that mean the prospect is dead/lost — don't stage them.
DEAD = ("CLOSED", "LOST", "PASS", "DEAD", "DROPPED")


def norm_key(name):
    """1-2 word dedupe/skip key. Generic leads ('space') keep two words; everything
    else collapses to its brand token (afrl, swri, purdue, redwire, spacetango)."""
    base = re.split(r"[(/—–,-]", name)[0]          # cut at ( / — – , -
    words = re.sub(r"[^a-z0-9 ]", "", base.lower()).split()
    if not words:
        return name.lower().strip()
    if words[0] in ("space", "texas", "new", "los", "san"):
        return " ".join(words[:2])
    return words[0]


def pay_id(key):
    n = int(hashlib.md5(key.encode()).hexdigest(), 16) % 9000 + 1000
    return f"PAY-{n}"


def field(body, label):
    m = re.search(rf"\*\*{re.escape(label)}:?\*\*\s*([^\n]+)", body, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def clean(s):
    # collapse links/markdown emphasis to plain text, trim
    s = re.sub(r"\*+", "", s).replace("`", "").strip()
    return re.sub(r"\s+", " ", s)


def parse_enriched(md):
    """The numbered '#### N. Name' enrichment blocks."""
    out = []
    # split into chunks headed by '#### N. Name'
    parts = re.split(r"^####\s+\d+\.\s*(.+?)\s*$", md, flags=re.MULTILINE)
    # parts = [pre, name1, body1, name2, body2, ...]
    for i in range(1, len(parts) - 1, 2):
        name = clean(parts[i])
        body = parts[i + 1]
        # stop body at the next section divider so we don't bleed into drafts
        body = re.split(r"\n## |\n### ", body)[0]
        out.append({
            "name": name,
            "segment": clean(field(body, "Segment")),
            "poc": clean(field(body, "POC").split("\n")[0]),
            "why": clean(field(body, "Why BLK3 fits") or field(body, "Why fit")),
            "status": clean(field(body, "Status")) or "RESEARCHING",
            "next": clean(field(body, "Next action")),
        })
    return out


def parse_hot_table(md):
    """The HOT table at the top: Prospect | Segment | Why fit | POC | Status | Next action."""
    out = []
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6:
            continue
        if cells[0].lower() in ("prospect", "") or set(cells[0]) <= set("-: "):
            continue
        out.append({
            "name": clean(cells[0]),
            "segment": clean(cells[1]),
            "why": clean(cells[2]),
            "poc": clean(cells[3]),
            "status": clean(cells[4]) or "READY",
            "next": clean(cells[5]),
        })
    return out


def render_block(oid, p):
    desc = f"Payload buyer sourced from BLK3 Payload Sales pipeline. {p['why']}".strip()
    return (
        f"\n### {oid} | {p['name']}\n"
        f"**Status:** {p['status'][:60]} — payload buyer (auto-bridged from pipeline)\n"
        f"**Type:** {OPP_TYPE}\n"
        f"**Segment:** {p['segment']}\n"
        f"**Value:** {DEFAULT_VALUE}\n"
        f"**Due:** {DUE}\n"
        f"**POC:** {p['poc']}\n"
        f"**Why fit:** {p['why']}\n"
        f"**Next action:** {p['next'] or 'Price off rate card; stage tailored outreach for Jon to approve.'}\n"
        f"**Source:** tasks/blk3-payload-sales-pipeline.md\n"
        f"_desc: {desc[:200]}_\n"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    md = open(PIPELINE).read()
    prospects = parse_enriched(md) + parse_hot_table(md)

    # Existing non-PAY opps that are ALREADY payload opps → skip those orgs only.
    # (We match on payload opps so a buyer isn't dropped just because the org also
    # appears under an unrelated angle, e.g. Purdue's GNC/flight-software BD item.)
    existing = []
    try:
        for o in json.load(open(OPP_JSON)).get("opportunities", []):
            if str(o.get("id", "")).startswith("PAY-"):
                continue
            blob = (str(o.get("title", "")) + " " + str(o.get("type", ""))).lower()
            if "payload" in blob:
                existing.append(blob)
    except Exception:
        pass

    staged, seen, ids = [], set(), set()
    for p in prospects:
        if not p["name"]:
            continue
        if any(d in p["status"].upper() for d in DEAD):
            continue
        key = norm_key(p["name"])
        if key in seen:
            continue                                   # de-dupe within pipeline
        if any(key in t for t in existing):
            continue                                   # already a real opp (e.g. SwRI)
        seen.add(key)
        oid = pay_id(key)
        while oid in ids:                              # hash collision guard
            oid = f"PAY-{(int(oid.split('-')[1]) + 1)}"
        ids.add(oid)
        staged.append((oid, p))

    section = BEGIN + "\n\n## PAYLOAD BUYERS — auto-bridged from BLK3 pipeline\n" + \
        "".join(render_block(oid, p) for oid, p in staged) + "\n" + END + "\n"

    if args.dry_run:
        print(f"[dry-run] {len(staged)} payload buyers would be staged into MC Opportunities:")
        for oid, p in staged:
            print(f"  {oid}  {p['name'][:55]:55}  [{p['status'][:20]}]")
        print("\n--- managed section preview ---\n" + section[:1500])
        return

    cur = open(OPP_MD).read()
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)
    if pattern.search(cur):
        cur = pattern.sub("", cur)
    cur = cur.rstrip() + "\n\n" + section
    open(OPP_MD, "w").write(cur)
    print(f"Staged {len(staged)} payload buyers into {os.path.basename(OPP_MD)}: "
          + ", ".join(oid for oid, _ in staged))

    r = subprocess.run(["python3", GENERATOR], capture_output=True, text=True, timeout=120)
    print("Generator:", "OK" if r.returncode == 0 else f"FAIL\n{r.stderr[:400]}")
    # confirm they landed
    try:
        pay = [o for o in json.load(open(OPP_JSON)).get("opportunities", [])
               if str(o.get("id", "")).startswith("PAY-")]
        print(f"opportunities.json now carries {len(pay)} PAY- buyers for the processor to price.")
    except Exception as e:
        print("verify failed:", e)


if __name__ == "__main__":
    main()
