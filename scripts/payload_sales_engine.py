#!/usr/bin/env python3
"""
payload_sales_engine.py -- deterministic core of the BLK3 Payload Sales Engine.

WHY THIS EXISTS (ExO 3.0 / Quiet-Drift fix, 2026-07-27)
-------------------------------------------------------
The old engine was a single OpenClaw agentTurn where a weak local model did the
WHOLE job: read files, web-enrich, draft, AND write the pipeline. When the model
choked (it can't reliably read local files in the cron sandbox, and it over-
refused its own campaign doc as a "prompt injection") the run exited "ok" and
narrated the failure straight into #blk3-payload for three days. Green status,
garbage output -- textbook Quiet Drift.

The fix is to take the model OUT of the critical path. This script owns the
must-not-break flow deterministically:

    pipeline.md  ->  payload_pipeline_to_opps.py (bridge to priced opportunities)
                 ->  parsed status summary
                 ->  Discord #blk3-payload  (posted directly, no model)

The model is demoted to a separate BEST-EFFORT drafting layer (see the reworked
cron) that can never poison this run or spam the channel. If the model layer
fails, this summary still delivers.

Every run emits correlated start/end/error events via governance/govlog.py, and
the agent is registered as class `payload-sales` in governance/registry.json, so
run_evals.py (Trusted-Evals pillar) and the cron watchdog now cover it.

Usage:  payload_sales_engine.py [--dry-run]   # --dry-run: no bridge write, no post
"""
import os
import re
import sys
import shutil
import subprocess
import argparse

WORKSPACE = "/Users/exomac/.openclaw/workspace"
PIPELINE = os.path.join(WORKSPACE, "tasks/blk3-payload-sales-pipeline.md")
BRIDGE = os.path.join(WORKSPACE, "scripts/payload_pipeline_to_opps.py")
DRAFTS = os.path.join(WORKSPACE, "drafts/payload-outreach-drafts.md")
DISCORD_CHANNEL = "channel:1501636671492460554"  # #blk3-payload

# launchd has a minimal PATH; resolve the openclaw binary explicitly (same
# pattern as scripts/cron-failure-watchdog.py).
OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"

# Status vocabulary from the pipeline legend, ordered by funnel stage.
STAGES = ["NEW", "RESEARCHING", "READY", "OUTREACH SENT", "IN DISCUSSION",
          "SLOT RESERVED", "CLOSED", "LOST"]
DEAD = ("CLOSED", "LOST")

# --- governance: correlation-id logging (never let telemetry break the job) ---
sys.path.insert(0, os.path.join(WORKSPACE, "governance"))
try:
    import govlog
    _RUN = govlog.new_run("payload-sales")
except Exception:
    govlog = None
    _RUN = None


def glog(event, status="info", detail="", **fields):
    if govlog and _RUN:
        try:
            govlog.event(_RUN, event, status=status, detail=detail, **fields)
        except Exception:
            pass


def parse_pipeline():
    """Deterministically parse the pipeline into per-prospect records."""
    if not os.path.exists(PIPELINE):
        return []
    text = open(PIPELINE, encoding="utf-8", errors="replace").read()
    # Prospect blocks look like:  #### 3. SpaceTango (Lexington, KY) — Broker
    blocks = re.split(r"\n#### \d+\.\s*", text)
    records = []
    for b in blocks[1:]:
        name = b.splitlines()[0].strip()
        status = None
        m = re.search(r"\*\*Status:\*\*\s*([A-Z /]+)", b)
        if m:
            status = m.group(1).strip().rstrip("/").strip()
        pm = re.search(r"\*\*POC:\*\*\s*(.+)", b)
        poc_txt = pm.group(1).strip() if pm else ""
        has_poc = bool(poc_txt) and "TBD" not in poc_txt.upper()
        records.append({
            "name": name,
            "status": status or "NEW",
            "has_poc": has_poc,
        })
    return records


def norm_stage(s):
    s = (s or "NEW").upper()
    for stage in STAGES:
        if s.startswith(stage):
            return stage
    return "NEW"


def run_bridge(dry):
    """Run the deterministic pipeline->opportunities bridge (the critical flow)."""
    if dry:
        return "dry-run (bridge skipped)"
    try:
        r = subprocess.run([sys.executable, BRIDGE],
                           capture_output=True, text=True, timeout=300)
        out = (r.stdout or "").strip().splitlines()
        tail = out[-1] if out else "(no output)"
        if r.returncode != 0:
            glog("bridge", status="error", detail=(r.stderr or "")[:300])
            return f"bridge FAILED rc={r.returncode}: {(r.stderr or '')[:120]}"
        glog("bridge", status="info", detail=tail[:200])
        return tail
    except Exception as e:
        glog("bridge", status="error", detail=str(e)[:300])
        return f"bridge error: {e}"


def count_drafts():
    if not os.path.exists(DRAFTS):
        return 0
    txt = open(DRAFTS, encoding="utf-8", errors="replace").read()
    return len(re.findall(r"^## ", txt, flags=re.M))


def build_summary(records, bridge_line):
    counts = {}
    for r in records:
        st = norm_stage(r["status"])
        counts[st] = counts.get(st, 0) + 1
    total = len(records)
    live = sum(v for k, v in counts.items() if k not in DEAD)
    # Prospects that still need enrichment: NEW, or RESEARCHING without a POC.
    need = [r for r in records
            if norm_stage(r["status"]) == "NEW"
            or (norm_stage(r["status"]) == "RESEARCHING" and not r["has_poc"])]
    with_poc = sum(1 for r in records if r["has_poc"] and norm_stage(r["status"]) not in DEAD)

    funnel = "  ".join(f"{k} {counts[k]}" for k in STAGES if counts.get(k))
    lines = [
        "**BLK3 Payload Sales Engine — daily run**  ·  SPACEavailable™ (Flight 2, Mar 2027)",
        f"Pipeline: {total} prospects  ({live} live · {with_poc} with a named POC)",
        f"Funnel: {funnel}" if funnel else "Funnel: (empty)",
        f"Opportunities bridge: {bridge_line}",
        f"Outreach drafts in drafts file, staged for Jon's review: {count_drafts()}",
    ]
    if need:
        top = ", ".join(r["name"][:40] for r in need[:5])
        lines.append(f"Needs enrichment ({len(need)}): {top}")
    else:
        lines.append("Needs enrichment: none — every live prospect has a POC.")
    lines.append("_Deterministic core (model out of critical path). Drafting runs best-effort next; drafts land in drafts/payload-outreach-drafts.md for review — never auto-sent._")
    return "\n".join(lines)


def post_discord(text):
    try:
        subprocess.run(
            [OPENCLAW, "message", "send", "--channel", "discord",
             "--target", DISCORD_CHANNEL, "-m", text],
            capture_output=True, text=True, timeout=60)
        return True
    except Exception as e:
        glog("deliver", status="error", detail=str(e)[:200])
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    glog("start", status="info", detail="dry" if args.dry_run else "live")
    records = parse_pipeline()
    glog("parse", status="info", detail=f"{len(records)} prospects")
    bridge_line = run_bridge(args.dry_run)
    summary = build_summary(records, bridge_line)

    if args.dry_run:
        print(summary)
        glog("end", status="info", detail="dry-run, not posted")
        return 0

    ok = post_discord(summary)
    glog("end", status="info" if ok else "error",
         detail="posted" if ok else "post failed")
    print(summary)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
