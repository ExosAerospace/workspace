#!/usr/bin/env python3
"""
cron-registry audit worker, step 2: register every OpenClaw cron in
mission-control/data/agent-registry.json with a full exo3 spec (kind "openclaw-cron").

Input: logs/audit-workers/cron-registry.inventory.json (step 1). Idempotent: an existing
entry with the same cron_id is replaced in place; nothing else in the registry is touched.
Formatting preserved: json.dumps(indent=1, ensure_ascii=False), no trailing newline.
"""
import json, os, sys, datetime

WS = "/Users/exomac/.openclaw/workspace"
INV = os.path.join(WS, "logs", "audit-workers", "cron-registry.inventory.json")
REG = os.path.join(WS, "mission-control", "data", "agent-registry.json")

REMINDER_IDS = {"d244fa73", "f1464af0", "eb9006cf", "cc150b55", "2f914ea5", "2323192f", "3a9112dc",
                "6028e2b9", "4c3413e0", "3299389d"}
CAPTURE_IDS = {"fa596321", "f38b6aa2", "4dbd0e49", "8aef3ee2", "049e8c95", "018a38fe", "11feb1de", "804832dd"}
NOTIFY_ONLY = {"d244fa73", "2f914ea5", "3a9112dc", "6028e2b9", "2b6e4087"}

TOOLSETS = {
    32: "toolsAllow 32 tools (message, file_write, file_fetch, dir_list, browser, web_search/fetch, cron, gateway, sessions_send/spawn, subagents, nodes, node_inference; NO exec)",
    31: "toolsAllow 31 tools (message, file_write, file_fetch, dir_list, browser, web_search/fetch, cron, gateway, sessions_send/spawn, subagents, nodes; NO exec)",
    16: "toolsAllow 16 tools (message, file_write, web_search/fetch, tavily, memory_search, session_status; NO exec, NO cron/gateway)",
}


def tools_text(c):
    if c["payload_kind"] == "command":
        return "command payload (Gateway-executed argv, operator-admin authored; no model)"
    n = c.get("toolsAllow_count")
    if n is None:
        return "agent default tools (main agent tools.profile=full: exec/shell, file read/write, message, cron, gateway, browser, web)"
    return TOOLSETS.get(n, f"toolsAllow {n} tools: {', '.join(c['toolsAllow'])}")


def delivery_text(c):
    d = c.get("delivery") or {}
    if not d:
        return "no announce delivery (main-session system event; replies in the target session)"
    if d.get("mode") == "none":
        return "announce delivery off (mode none); any message is sent by the agent itself via the message tool"
    to = d.get("to", "")
    where = ("Jon DM" if "1501632195163590739" in to else f"Discord {to}") if d.get("channel") == "discord" else f"{d.get('channel')} {to}"
    return f"announces final output to {where}"


def memory_text(c):
    t = c["sessionTarget"]
    if t == "isolated":
        base = "fresh isolated session per run (no chat carry-over; OpenClaw memory_search available)"
    elif t == "main":
        base = "enqueued into the main agent session (shares Jon's main-session context)"
    else:
        base = f"persistent custom session {t.split(':', 1)[1]} (context carries across runs)"
    return f"{base}; data touched: {c['actions']}"


def autonomy(c):
    short = c["id"][:8]
    if short in NOTIFY_ONLY: return "Notify-only"
    if c["human_confirm_gap"]: return "Execute-within-bounds (acts WITHOUT human confirm; see human_confirm_gap)"
    if c["risk"] in ("HIGH", "MED") and c["stack_layer"] in ("ORCHESTRATE", "LEARN", "GOVERN", "DECIDE"):
        return "Execute-within-bounds"
    return "Recommends-with-Context"


def escalation(c):
    parts = []
    if c["human_confirm_gap"]:
        parts.append("NO human confirm before its closing/changing action (audit gap, reported to Jon 2026-09-29)")
    elif c["id"][:8] in ("51e09612", "148cdb94"):
        parts.append("human confirm gate: Jon approves in Discord before anything is committed/staged")
    elif c["risk"] == "HIGH":
        parts.append("external/investor/gov actions are drafted and routed to Jon; nothing sent outside Exos by the agent")
    parts.append(f"output: {delivery_text(c)}")
    parts.append("run failure -> OpenClaw consecutive_errors -> agent_eval FAIL alert (>=2 in a row) to the system channel")
    return "; ".join(parts)


def eval_text(c):
    if not c["enabled"]:
        return ("disabled: agent_eval registry drift only (an unregistered cron alerts); liveness and error checks "
                "resume automatically if re-enabled (config/agent-evals.json)")
    one_shot = c["schedule_raw"].get("kind") == "at"
    live = ("one-shot: WARN if still unrun 24h after its due time" if one_shot else
            "liveness: no finished run within 2.5x schedule interval -> WARN")
    q = (" Output quality scored nightly by cron:agent-meta-evaluator-nightly (advisory)."
         if c["payload_kind"] == "agentTurn" and c["id"][:8] != "1202feb8" else "")
    return (f"agent_eval hourly (config/agent-evals.json '{c['label']}'): registry drift; {live}; "
            f"consecutive_errors >= 2 -> FAIL + one deduped alert.{q}")


def reuse(c):
    s = c["id"][:8]
    if s in REMINDER_IDS: return "one-off/dated reminder; pattern only (fixed-text scheduled reminder)"
    if s in CAPTURE_IDS: return "reusable pursuit-capture pattern (tracker file as source of truth + draft-only outreach) for any new pursuit"
    if c["stack_layer"] == "SENSE": return "reusable watch/scan pattern (date-hygiene + search budget + silent-unless-hit) for any solicitation or signal source"
    if c["stack_layer"] == "INTERPRET": return "reusable digest/brief pattern for any audience channel"
    if c["stack_layer"] == "LEARN": return "fleet-wide learning loop (applies to any agent class)"
    if c["stack_layer"] == "GOVERN": return "fleet-wide governance/maintenance pattern"
    if c["stack_layer"] == "DECIDE":
        return ("decision-surfacing pattern reusable for any board" +
                ("; must gain a human-confirm step before reuse" if c["human_confirm_gap"] else " (propose-then-confirm)"))
    return "Exos-specific orchestration; pattern reusable for similar propose-then-confirm workflows"


def entry(c):
    e = {
        "label": c["label"],
        "script": f"openclaw cron {c['id']} ({c['payload_kind']})",
        "kind": "openclaw-cron",
        "schedule": c["schedule"],
        "purpose": c["purpose"],
        "stack_layer": c["stack_layer"],
        "autonomy_tier": autonomy(c),
        "human_owner": c["human_owner"],
        "permission_envelope": f"{tools_text(c)}; prompted actions: {c['actions']}; {delivery_text(c)}",
        "memory_boundary": memory_text(c),
        "escalation": escalation(c),
        "eval_suite": eval_text(c),
        "telemetry": ("scripts/cron_telemetry.py (com.exos.cron-telemetry, every 15 min) emits one fleet_log event per "
                      f"finished run to logs/fleet-events.jsonl (agent='{c['label']}'); raw history in "
                      "~/.openclaw/state/openclaw.sqlite cron_run_logs"),
        "reusability_scope": reuse(c),
        "risk_tier": c["risk"],
        "envelope_source": ("derived 2026-09-29 (cron-registry audit worker) from the cron's payload, toolsAllow and "
                            "delivery via `openclaw cron list --all --json`; prompt read by hand"),
        "enabled": c["enabled"],
        "cron_id": c["id"],
        "cron_name": c["name"],
        "model": c["model"],
        "ai_in_critical_path": c["ai_in_critical_path"],
    }
    if c["human_confirm_gap"]:
        e["human_confirm_gap"] = c["human_confirm_gap"]
    if c["prompt_embeds_credential"]:
        e["prompt_embeds_credential"] = True
    for k, v in e.items():
        if isinstance(v, str) and (not v.strip() or v.strip().upper() in ("TBD", "MISSING", "NONE")):
            sys.exit(f"blank field {k} on {c['label']}")
    return e


TELEMETRY_AGENT = {
    "label": "com.exos.cron-telemetry",
    "script": "cron_telemetry.py",
    "kind": "recurring",
    "schedule": "every 900s",
    "purpose": "cron_telemetry.py — mirrors OpenClaw cron run history into the fleet telemetry spine: one fleet_log event per NEW finished cron run (agent=cron:<name>, kind by stack layer, outcome ok/failed/skipped, level warn on error/timeout). High-water mark per job in state/cron-telemetry-state.json. Closes exo3 audit THEME 3 (crons emitted no telemetry).",
    "stack_layer": "GOVERN/ASSURE",
    "autonomy_tier": "Read-only exporter (no writes to source; local files only)",
    "human_owner": "Exo (infra) / John Quinn",
    "permission_envelope": "read-only: ~/.openclaw/state/openclaw.sqlite (opened mode=ro; tables cron_jobs, cron_run_logs) + agent-registry.json; writes logs/fleet-events.jsonl (append) + state/cron-telemetry-state.json; NO email, NO Discord, NO cron/gateway control, NO network",
    "memory_boundary": "reads OpenClaw cron job + run tables and agent-registry.json; writes state/cron-telemetry-state.json (per-job seq high-water mark) and appends logs/fleet-events.jsonl; run summaries truncated to 200 chars, error text to 300",
    "escalation": "none directly (exporter); agent_eval liveness on com.exos.cron-telemetry FAILs + alerts if it crashes or stops loading; cron failures it records surface via agent_eval cron checks",
    "eval_suite": "python3 scripts/cron_telemetry.py --selftest (fixture sqlite: first-run baseline, new-run emit, dedupe on re-run, error->warn, unknown-job label fallback, cron interval math) + agent_eval hourly liveness (config/agent-evals.json com.exos.cron-telemetry)",
    "telemetry": "logs/cron-telemetry.out.log / .err.log; logs/runs/*.jsonl via run_logged.py; its own fleet_log 'cron_telemetry' pass event per run",
    "reusability_scope": "pattern reusable for mirroring any external scheduler's run history (e.g. remote triggers) into fleet_log",
    "risk_tier": "LOW",
    "envelope_source": "hand-written with the script, 2026-09-29 (cron-registry audit worker)",
}


def main():
    inv = json.load(open(INV))
    raw = open(REG).read()
    reg = json.loads(raw)
    assert json.dumps(reg, indent=1, ensure_ascii=False) == raw, "registry not in indent=1 format; aborting"
    agents = reg["agents"]
    by_id = {a.get("cron_id"): i for i, a in enumerate(agents) if a.get("cron_id")}
    added = replaced = 0
    for c in inv["crons"]:
        e = entry(c)
        if c["id"] in by_id:
            agents[by_id[c["id"]]] = e; replaced += 1
        else:
            agents.append(e); added += 1
    ti = [i for i, a in enumerate(agents) if a.get("label") == TELEMETRY_AGENT["label"]]
    if ti: agents[ti[0]] = TELEMETRY_AGENT
    else: agents.append(TELEMETRY_AGENT)
    s = inv["summary"]
    reg["cron_backfill"] = {
        "date": datetime.date.today().isoformat(),
        "worker": "cron-registry (exo3 audit THEME 3 residual, Jon approved 2026-09-29 08:28)",
        "registered": len(inv["crons"]), "enabled": s["enabled"],
        "by_layer": s["by_layer"], "by_risk": s["by_risk"],
        "human_confirm_gaps": s["human_confirm_gaps"],
        "note": "kind openclaw-cron; label cron:<slug(name)>; drift matched on cron_id. Telemetry via scripts/cron_telemetry.py; evals via agent_eval.py cron checks.",
    }
    open(REG, "w").write(json.dumps(reg, indent=1, ensure_ascii=False))
    print(f"added {added}, replaced {replaced}, agents now {len(agents)}")


if __name__ == "__main__":
    main()
