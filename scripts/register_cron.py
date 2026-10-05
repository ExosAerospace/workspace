#!/usr/bin/env python3
"""register_cron.py — one-command exo3 registration for an OpenClaw cron (Jon 2026-10-05).

Sessions create crons with `automations add`, which the commit-time exo3 gate never sees, so new crons
kept tripping "registry drift" (decisions feed 10/4, FNEX loop 10/5). This derives a complete registry
entry from the live cron itself (schedule, prompt, tools, delivery target), so registering is one step:

  python3 scripts/register_cron.py <cron-id-or-prefix> [--purpose "..."] [--risk LOW|MEDIUM|HIGH]
                                    [--owner "John Quinn"] [--layer DECIDE] [--dry-run]

Derived fields: permission_envelope from toolsAllow + delivery target + prompt cues (external email,
external assignee, exec); risk_tier HIGH if the prompt can reach someone outside @exosaero.com or it has
exec, else MEDIUM if it writes MC data, else LOW. eval_suite = agent_eval cron hygiene (last-run status +
staleness vs its own cadence). Idempotent: an existing entry for the cron_id is updated in place.
"""
import json, os, re, sys, subprocess, argparse
from datetime import date

WS = "/Users/exomac/.openclaw/workspace"
REG = os.path.join(WS, "mission-control", "data", "agent-registry.json")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:60].rstrip("-")


def sched(s):
    s = s or {}
    if s.get("kind") == "every":
        return f"every {int(s.get('everyMs', 0) / 1000)}s"
    if s.get("kind") == "cron":
        return f"cron '{s.get('expr')}' {s.get('tz') or 'gateway-local'}"
    if s.get("kind") == "at":
        return f"once at {s.get('at')}"
    return json.dumps(s)


def derive(j, a):
    p = j.get("payload") or {}
    msg = p.get("message") or p.get("text") or p.get("script") or ""
    tools = p.get("toolsAllow") or []
    dl = j.get("delivery") or {}
    ext_email = bool(re.search(r"[\w.+-]+@(?!exosaero\.com)[\w-]+\.[\w.]+", msg))
    has_exec = "exec" in tools or not tools
    writes_mc = bool(re.search(r"decisions/ingest|supabase|mc-attach|PATCH|tasks", msg, re.I))
    risk = a.risk or ("HIGH" if (ext_email or has_exec) else "MEDIUM" if writes_mc else "LOW")
    cues = []
    if ext_email: cues.append("prompt references an external (non-@exosaero.com) address")
    if writes_mc: cues.append("writes Mission Control data (decisions/tasks/attachments)")
    if has_exec: cues.append("exec/shell available")
    tgt = dl.get("to") or "none"
    envelope = (f"toolsAllow {len(tools) or 'ALL (default)'} tools; delivery {dl.get('mode', 'none')} → {dl.get('channel', '')}:{tgt}; "
                + ("; ".join(cues) or "read/announce only"))
    self_remove = bool(re.search(r"remove this automation|automations action remove|deleteAfterRun", msg, re.I)) or j.get("deleteAfterRun")
    return {
        "label": "cron:" + slug(j.get("name")), "cron_id": j["id"], "kind": "openclaw-cron",
        "script": f"openclaw cron {j['id']} ({p.get('kind', '?')})", "schedule": sched(j.get("schedule")),
        "purpose": a.purpose or (j.get("name") or "") + " — " + re.sub(r"\s+", " ", msg)[:220],
        "stack_layer": a.layer or ("DECIDE" if re.search(r"decision", msg, re.I) else "ORCHESTRATE"),
        "autonomy_tier": "Execute-within-bounds", "human_owner": a.owner,
        "permission_envelope": envelope,
        "memory_boundary": f"session target {j.get('sessionTarget') or 'isolated'}; agent {j.get('agentId') or 'main'}",
        "escalation": "agent_eval cron hygiene → Jon on FAIL; Decisions board for any Jon call",
        "eval_suite": ("agent_eval cron hygiene (lastRunStatus ok + not stale vs its own cadence; consecutiveErrors → FAIL)"
                       + ("; OUTPUT: agent_eval check_duplicate_sends on its deliveries" if dl.get("mode") in ("announce", "webhook") or "message" in tools else "")),
        "eval_type": "output" if (dl.get("mode") in ("announce", "webhook") or "message" in tools or writes_mc) else "liveness",
        "telemetry": f"openclaw cron runs --id {j['id']}", "reusability_scope": "single-purpose",
        "risk_tier": risk, "lifecycle": "self-removing (prompt has an end condition)" if self_remove else "standing",
        "registered": date.today().isoformat(), "envelope_source": "register_cron.py derivation from the live cron",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cron"); ap.add_argument("--purpose"); ap.add_argument("--risk")
    ap.add_argument("--owner", default="John Quinn"); ap.add_argument("--layer"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    r = subprocess.run([OPENCLAW, "cron", "list", "--json"], capture_output=True, text=True, timeout=60)
    jobs = json.loads(r.stdout)
    jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else jobs
    hit = [j for j in jobs if j["id"].startswith(a.cron)]
    if len(hit) != 1:
        sys.exit(f"cron '{a.cron}': {len(hit)} matches")
    e = derive(hit[0], a)
    if a.dry_run:
        print(json.dumps(e, indent=1, ensure_ascii=False)); return
    d = json.load(open(REG))
    cur = next((x for x in d["agents"] if x.get("cron_id") == e["cron_id"]), None)
    if cur:
        cur.update(e); cur["updated"] = e.pop("registered")
    else:
        d["agents"].append(e)
    open(REG, "w").write(json.dumps(d, indent=1, ensure_ascii=False))
    print(f"registered {e['label']} ({e['cron_id'][:8]}) risk={e['risk_tier']} lifecycle={e['lifecycle']}")


if __name__ == "__main__":
    main()
