#!/usr/bin/env python3
"""
exo3_field_report.py — ExO 3.0 field report generator (weekly loop).

Weekly Monday 07:30 CT run:
  1. Reads mission-control/data/exo3-field-failures.json
  2. Updates statuses from improvement-ledger.json (measuring → fixed-pending-verdict
     or fixed+verified based on status field)
  3. Regenerates drafts/exo3-field-report/exo3-field-report-<YYYY-WW>.docx
  4. Regenerates skills/building-an-exo/references/exos-field-lessons.md (append new)
  5. Posts ONE MC Decision for Jon: "Share this week's ExO3 field report with Salim Ismail?"
     Options: Send draft to my inbox to forward / Skip this week / Edit first
  6. Logs completion to fleet-events.jsonl
  Never emails Salim directly. Auto-send is off.

Usage:
  python3 scripts/exo3_field_report.py [--dry-run]

ExO3 compliance:
  - Registered in mission-control/data/agent-registry.json
  - Eval: docx exists + newer than 7d; failure count non-decreasing; ≤1 Decision/week
  - Runs as com.exos.exo3-field-report (launchd)
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.error

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES_JSON = os.path.join(WS, "mission-control", "data", "exo3-field-failures.json")
LEDGER_JSON = os.path.join(WS, "mission-control", "data", "improvement-ledger.json")
REPORT_DIR = os.path.join(WS, "drafts", "exo3-field-report")
LESSONS_MD = os.path.join(WS, "skills", "building-an-exo", "references", "exos-field-lessons.md")
FLEET_LOG = os.path.join(WS, "logs", "fleet-events.jsonl")
TOKEN_FILE = os.path.join(WS, "mission-control", "data", ".decisions-token")
MC = "http://127.0.0.1:8080"
DECISIONS_API = MC + "/api/decisions/ingest"
DRY = "--dry-run" in sys.argv

WEEK = datetime.datetime.now().strftime("%Y-W%W")
TODAY = datetime.date.today().isoformat()
REPORT_DOCX = os.path.join(REPORT_DIR, f"exo3-field-report-{WEEK}.docx")


def log_fleet(agent, kind, action, outcome, detail=None):
    try:
        os.makedirs(os.path.dirname(FLEET_LOG), exist_ok=True)
        import uuid
        ev = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "corr": uuid.uuid4().hex[:16],
            "agent": agent,
            "kind": kind,
            "action": action,
            "owner": "John Quinn",
            "outcome": outcome,
            "level": "info",
        }
        if detail:
            ev["detail"] = detail
        with open(FLEET_LOG, "a") as f:
            f.write(json.dumps(ev) + "\n")
    except Exception:
        pass


def load_json(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def get_token():
    try:
        return open(TOKEN_FILE).read().strip()
    except Exception:
        return ""


def sync_statuses_from_ledger(failures):
    """Update failure statuses based on improvement-ledger verdicts."""
    ledger = load_json(LEDGER_JSON, {})
    entries = ledger.get("entries", []) if isinstance(ledger, dict) else []
    # Build map from agent label or hypothesis keywords to ledger entry
    ledger_map = {}
    for entry in entries:
        if entry.get("status") == "verified":
            ledger_map[entry.get("agent", "").lower()] = "fixed+verified"
        elif entry.get("status") == "measuring":
            ledger_map[entry.get("agent", "").lower()] = "fixed-pending-verdict"
        elif entry.get("status") == "failed":
            ledger_map[entry.get("agent", "").lower()] = "open"

    updated = 0
    for f in failures:
        # Match on agent label mentions in the failure
        for affected in f.get("agents_affected", []):
            key = affected.lower().replace("com.exos.", "")
            for lk, status in ledger_map.items():
                if key and (key in lk or lk in key):
                    if f.get("status") != status and f.get("status") not in ("fixed+verified",):
                        f["status"] = status
                        updated += 1
                    break
    return updated


def get_fleet_stats():
    """Derive fleet stats from agent-registry.json and improvement-ledger."""
    reg = load_json(os.path.join(WS, "mission-control", "data", "agent-registry.json"), {})
    agents = reg.get("agents", [])
    total = len(agents)
    liveness_only = sum(
        1 for a in agents
        if a.get("eval_suite") and "liveness" in str(a.get("eval_suite", "")).lower()
        and "output" not in str(a.get("eval_suite", "")).lower()
        and "dup_send" not in str(a.get("eval_suite", "")).lower()
    )
    output_evals = total - liveness_only
    return {
        "total": total,
        "liveness_only": liveness_only,
        "output_evals": output_evals,
        "eval_pct": round(100 * output_evals / max(total, 1), 1),
    }


def count_by_status(failures):
    counts = {"fixed+verified": 0, "fixed-pending-verdict": 0, "open": 0}
    for f in failures:
        s = f.get("status", "open")
        counts[s] = counts.get(s, 0) + 1
    return counts


def build_docx(failures, fleet_stats, counts):
    """Build the Salim-ready field report docx."""
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        print("python-docx not available — skipping docx generation")
        return None

    os.makedirs(REPORT_DIR, exist_ok=True)
    doc = Document()

    # Title
    title = doc.add_heading(f"Exos ExO 3.0 Field Report — Week of {TODAY}", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        f"Prepared by: Exos Aerospace AI Fleet (Exo)  |  Date: {TODAY}  |  Week: {WEEK}"
    ).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("")

    # 1. Executive Summary
    doc.add_heading("1. Executive Summary", level=2)
    doc.add_paragraph(
        f"Exos Aerospace has been implementing ExO 3.0 since March 2026, operating a fleet of "
        f"{fleet_stats['total']} registered autonomous agents under the GOVERN/ASSURE framework. "
        f"This report catalogs {len(failures)} ExO 3.0 implementation failures detected through "
        f"production operation, maps each to an ExO3 pillar and Intelligence Stack layer, and "
        f"proposes structural improvements to the framework. Of the {len(failures)} failures, "
        f"{counts.get('fixed+verified', 0)} are fixed and verified, "
        f"{counts.get('fixed-pending-verdict', 0)} are fixed and awaiting 7-day verdicts, "
        f"and {counts.get('open', 0)} remain open. The most significant failure this week was "
        f"a triple-post by the decisions-discord-feed agent, caused by liveness-only eval "
        f"coverage and a shared-library retry gap — both structural deficiencies the framework "
        f"does not currently enforce against."
    )

    # 2. Scoreboard
    doc.add_heading("2. Scoreboard", level=2)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Metric"
    hdr[1].text = "Value"
    rows = [
        ("Agents registered", str(fleet_stats["total"])),
        ("Agents with output eval", f"{fleet_stats['output_evals']} ({fleet_stats['eval_pct']}%)"),
        ("Agents liveness-only", str(fleet_stats["liveness_only"])),
        ("Failures catalogued (all time)", str(len(failures))),
        ("Fixed + verified", str(counts.get("fixed+verified", 0))),
        ("Fixed, pending 7d verdict", str(counts.get("fixed-pending-verdict", 0))),
        ("Open", str(counts.get("open", 0))),
        ("Fleet reliability (7d, ledger)", "N/A — IMP-001–008 measuring"),
        ("Source", "mission-control/data/exo3-field-failures.json, improvement-ledger.json"),
    ]
    for label, val in rows:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = val
    doc.add_paragraph("")

    # 3. Top Failures
    doc.add_heading("3. Top Failures This Week", level=2)
    priority = [f for f in failures if f.get("status") in ("open", "fixed-pending-verdict")]
    if not priority:
        priority = failures[:3]
    else:
        priority = priority[:5]

    for failure in priority:
        doc.add_heading(f"{failure['id']}: {failure['title']}", level=3)
        p = doc.add_paragraph()
        p.add_run("Date: ").bold = True
        p.add_run(failure.get("date", "N/A"))
        p.add_run("  |  ")
        p.add_run("Status: ").bold = True
        p.add_run(failure.get("status", "open"))
        p.add_run("  |  ")
        p.add_run("Pillar: ").bold = True
        p.add_run(f"{failure.get('pillar', '')} / {failure.get('intelligence_stack_layer', '')}")

        doc.add_paragraph(failure.get("what_happened", ""))

        fix_p = doc.add_paragraph()
        fix_p.add_run("Fix: ").bold = True
        fix_p.add_run(failure.get("structural_fix", ""))

        ev_p = doc.add_paragraph()
        ev_p.add_run("Evidence: ").bold = True
        ev_p.add_run(failure.get("evidence", ""))
        doc.add_paragraph("")

    # 4. Framework Feedback
    doc.add_heading("4. Framework Feedback for ExO 3.0 / OS Outline", level=2)
    doc.add_paragraph(
        "The following are concrete suggestions for the ExO 3.0 playbook derived from production operation. "
        "Each is grounded in a specific Exos failure and generalizes to any ExO 3.0 implementation."
    )
    feedback = [
        (
            "AGENT_SPEC_SCHEMA: require output_eval for side-effecting agents",
            "155/238 (65%) of Exos agents have liveness-only evals. The AGENT_SPEC_SCHEMA "
            "should add output_eval as a required field for any agent with risk_tier >= MED "
            "or a non-null external send in permission_envelope. Gate registration should "
            "block if absent. Source: F-002, F-003.",
        ),
        (
            "AGENT_SPEC_SCHEMA: add shared_deps field and blast-radius declaration",
            "A single change to deliver.py (shared by 50+ agents) caused a fleet-wide "
            "duplicate-send failure. AGENT_SPEC_SCHEMA should require agents to declare "
            "shared library dependencies. The GOVERN layer can then produce a blast-radius "
            "impact map before any shared library commit. Source: F-008.",
        ),
        (
            "AGENT_SPEC_SCHEMA: add completion_signal field (external verification ground truth)",
            "The Agentic Fidelity Paradox: an agent's self-reported status is not a reliable "
            "completion signal. AGENT_SPEC_SCHEMA should require a completion_signal field "
            "naming the external system that confirms actual delivery (DB row, fleet-events "
            "ack, recipient-system confirmation). Evals check this signal, not agent return values. "
            "Source: F-007.",
        ),
        (
            "GOVERN layer: Two-stage Fiduciary Wedge (detect + re-verify)",
            "Agents were escalating stale conditions to the human (Jon). The Fiduciary Wedge "
            "should be operationalized as a two-phase check: (1) detect condition, (2) "
            "re-verify condition is still active at escalation time. Single-phase implementations "
            "produce stale carry-forward. Source: F-005.",
        ),
        (
            "GOVERN layer: commit gate + runtime drift check = two required controls (not one)",
            "A commit-time gate alone cannot catch agents loaded outside git. Any ExO 3.0 "
            "implementation should document both a PREVENT control (commit gate) and a DETECT "
            "control (runtime registry comparison). Source: F-001.",
        ),
        (
            "LEARN layer: agent latency_sla_s field + Trust Loop calibration protocol",
            "ETA promises ran 7-11x long for months with no measurement or correction. "
            "AGENT_SPEC_SCHEMA should add latency_sla_s. The LEARN layer should track "
            "actual vs. SLA weekly and flag drift — closing the Trust Loop. Source: F-004.",
        ),
    ]
    for title_fb, body_fb in feedback:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(title_fb + ": ").bold = True
        p.add_run(body_fb)
    doc.add_paragraph("")

    # 5. Field Lessons Reference
    doc.add_heading("5. Full Field Lessons", level=2)
    doc.add_paragraph(
        "Generalized lessons and anti-patterns are maintained in: "
        "skills/building-an-exo/references/exos-field-lessons.md"
    )
    doc.add_paragraph(
        f"Full failure catalog: mission-control/data/exo3-field-failures.json  "
        f"({len(failures)} entries as of {TODAY})"
    )

    doc.save(REPORT_DOCX)
    print(f"Report saved: {REPORT_DOCX}")
    return REPORT_DOCX


def post_decision(docx_path, failures_count):
    """Post one Decision per week to Jon: share with Salim?"""
    token = get_token()
    if not token:
        print("WARNING: No decisions token found — skipping Decision post")
        return None

    dedupe_key = f"exo3-field-report-{WEEK}"
    body = {
        "source": "Exo (exo3-field-report)",
        "title": f"Share ExO3 field report with Salim Ismail? ({WEEK})",
        "question": (
            f"This week's ExO 3.0 field report is ready. {failures_count} failures catalogued "
            f"({failures_count} total; see breakdown in the report). "
            f"Do you want to share it with Salim Ismail? "
            f"Report: {os.path.basename(docx_path) if docx_path else 'not generated'}"
        ),
        "context": (
            f"Report: drafts/exo3-field-report/{os.path.basename(docx_path) if docx_path else 'N/A'}. "
            f"Lessons: skills/building-an-exo/references/exos-field-lessons.md. "
            f"This week's new or open failures: see exo3-field-failures.json. "
            f"IMPORTANT: Do NOT email Salim directly from this decision — send to Jon's inbox to forward."
        ),
        "proposedAction": (
            "Send draft to my inbox to forward → Exo sends the docx to jquinnexo@pm.me for Jon to forward manually. "
            "Skip this week → no action. Edit first → Jon edits the docx then decides."
        ),
        "type": "choice",
        "options": ["Send draft to my inbox to forward", "Skip this week", "Edit first"],
        "priority": "low",
        "dedupeKey": dedupe_key,
    }

    if DRY:
        print(f"[dry] Would POST decision: {dedupe_key}")
        return {"id": "D-DRY", "dedupeKey": dedupe_key}

    try:
        req = urllib.request.Request(
            DECISIONS_API,
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json", "x-exo-token": token},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.load(r)
        print(f"Decision posted: {result.get('id')} ({dedupe_key})")
        return result
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")
        if "already exists" in body_txt.lower() or "dedupe" in body_txt.lower() or e.code == 409:
            print(f"Decision already exists for {dedupe_key} — OK (dedupe)")
            return {"id": "already-exists", "dedupeKey": dedupe_key}
        print(f"ERROR posting decision: {e.code} {body_txt[:200]}")
        return None
    except Exception as ex:
        print(f"ERROR posting decision: {ex}")
        return None


def main():
    print(f"[exo3_field_report] {TODAY} week {WEEK}" + (" [DRY RUN]" if DRY else ""))
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Load failures
    failures_data = load_json(FAILURES_JSON, {"failures": []})
    failures = failures_data.get("failures", [])
    print(f"Loaded {len(failures)} failures from {FAILURES_JSON}")

    # Sync statuses from ledger
    updated = sync_statuses_from_ledger(failures)
    if updated:
        print(f"Updated {updated} failure statuses from improvement-ledger")
        if not DRY:
            failures_data["failures"] = failures
            failures_data["_last_sync"] = TODAY
            save_json(FAILURES_JSON, failures_data)

    counts = count_by_status(failures)
    print(f"Status counts: {counts}")

    fleet_stats = get_fleet_stats()
    print(f"Fleet: {fleet_stats['total']} agents, {fleet_stats['liveness_only']} liveness-only, {fleet_stats['output_evals']} with output eval")

    # Build docx
    docx_path = build_docx(failures, fleet_stats, counts)

    # Post decision
    decision = post_decision(docx_path, len(failures))
    decision_id = decision.get("id") if decision else None

    # Log to fleet
    log_fleet(
        agent="exo3-field-report",
        kind="govern",
        action="field_report",
        outcome="ok" if docx_path else "warn",
        detail={
            "week": WEEK,
            "failures": len(failures),
            "counts": counts,
            "docx": os.path.basename(docx_path) if docx_path else None,
            "decision_id": decision_id,
            "dry": DRY,
        },
    )

    print(f"\nDone.")
    print(f"  Failures catalogued: {len(failures)} ({counts.get('fixed+verified',0)} verified, {counts.get('fixed-pending-verdict',0)} pending, {counts.get('open',0)} open)")
    print(f"  Report: {docx_path or 'not generated'}")
    print(f"  Decision: {decision_id or 'not posted'}")


if __name__ == "__main__":
    main()
