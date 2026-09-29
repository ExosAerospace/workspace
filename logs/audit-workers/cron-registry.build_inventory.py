#!/usr/bin/env python3
"""
cron-registry audit worker (2026-09-29): read-only inventory of every OpenClaw cron job.

Sources (read-only):
  - `openclaw cron list --all --json`  (job definitions + scheduler state, via the Gateway)
  - ~/.openclaw/state/openclaw.sqlite   table cron_run_logs, opened mode=ro (run history)

Writes logs/audit-workers/cron-registry.inventory.json. Prompt text is NOT copied into the
inventory (several prompts embed credentials); classification below is hand-written from a
read of each prompt on 2026-09-29.

Risk rubric (matches the 2026-09-26 envelope backfill):
  HIGH = can send email / act outside Exos, or change a system-of-record (Supabase tasks,
         MC decisions, MC data JSON, cron/agent config, MC or gateway restart)
  MED  = writes internal workspace state (trackers, drafts, reports, logs, outbox drops)
  LOW  = reads and reports only (Discord announce/DM to internal channels)
"""
import json, os, re, sqlite3, subprocess, datetime

WS = "/Users/exomac/.openclaw/workspace"
OUT = os.path.join(WS, "logs", "audit-workers", "cron-registry.inventory.json")
DB = os.path.expanduser("~/.openclaw/state/openclaw.sqlite")

J, LZ = "John Quinn", "Lizi Quinn"
# id prefix -> (layer, risk, owner, purpose, writes/actions, decides_without_confirm note or None)
C = {
 "51e09612": ("DECIDE", "LOW", J, "Daily task-backlog grind: proposes MERGE/CLOSE batches of duplicate and stale MC tasks to Jon; Jon replies 'commit batch' before anything changes.", "reads Supabase tasks (service key) + subject_dedup.py dry-run; posts one proposal to #exomac-system", None),
 "f2c9dda5": ("SENSE", "MED", J, "Watches for the SpaceWERX On-Orbit Logistics concept-paper open call; silent unless a future-dated deadline is confirmed.", "web search/fetch; on a hit writes reports/spacewerx-orbital-logistics-watch.md and DMs Jon", None),
 "29aab815": ("INTERPRET", "LOW", J, "Research Team weekly Investor & Capital Markets brief (rounds, family offices, M&A, SFO targets).", "web search; posts brief to #series-a", None),
 "bcff8330": ("INTERPRET", "LOW", LZ, "Trending Content Scanner: finds trending space conversations and writes ready-to-post social copy for Lizi to review and post.", "web search; posts drafts to the social channel (Lizi posts, never the agent)", None),
 "e6d339d7": ("INTERPRET", "LOW", LZ, "Industry Signal Posts: 1-2 brand-voice social drafts from recent news for Lizi to review and post.", "web search; posts drafts to the social channel", None),
 "d244fa73": ("ORCHESTRATE", "LOW", J, "Bi-weekly reminder to Jon of the Japan/ITZ working session with Toshi + HOSPO (through Oct 2026).", "no tools; announces fixed reminder to Jon DM", None),
 "4c974a8b": ("INTERPRET", "HIGH", J, "Daily Ainigma RTO due-diligence digest: summarises data-room activity and questions, prepares answers into drafts/, emails John only when there was activity.", "reads logs/dd-activity.log; writes drafts/; emails John via msmtp; data-room additions flagged for John, never made", None),
 "9e1b0cf7": ("INTERPRET", "HIGH", J, "Monthly investor/board activity report on the last day of the month.", "reads workspace trackers; writes reports/monthly-investor-report-YYYY-MM.md; emails jquinnexo@pm.me via local SMTP bridge (credential embedded in prompt)", None),
 "fa596321": ("ORCHESTRATE", "MED", J, "Capital Bridge ($1M) pursuit agent: advances the top open action, drafts investor/payload material for Jon+counsel, updates the pursuit tracker.", "reads/writes capture/Capital_Bridge_pursuit.md (stages, statuses, decision log); drafts only; DMs Jon; never sends externally", None),
 "f38b6aa2": ("ORCHESTRATE", "MED", J, "Payload BD sales agent: qualifies payload leads from the live CRM, maintains the ranked sales pipeline, drafts outreach for Jon.", "reads MC CRM API + opportunities.json; writes capture/Sales_Pipeline.md + drafts; DMs Jon; never sends externally", None),
 "4dbd0e49": ("ORCHESTRATE", "MED", J, "National Charter Enterprise agent: econ-dev/allied funding for the BLK3 build; maintains the NCE tracker and drafts partnership outreach for Jon.", "writes capture/NCE_BLK3_Build.md + drafts; DMs Jon; never sends externally", None),
 "8aef3ee2": ("ORCHESTRATE", "HIGH", J, "Capture agent for the NASA RDRE Phase III pursuit: scans for movement, advances the top action, maintains tracker and white paper.", "writes capture/NASA_RDRE_PhaseIII_pursuit.md, drafts, white-paper DOCX rebuild, outbox/drop report; prompt authorises msmtp email to Jon; never external", None),
 "049e8c95": ("ORCHESTRATE", "HIGH", J, "Capture agent for the NOAA ERB/AC4 SACSS pursuit: scans, advances the top action, maintains the tracker.", "writes capture/NOAA_ERB_AC4_SACSS_pursuit.md + drafts; prompt authorises msmtp email to Jon; never external", None),
 "018a38fe": ("ORCHESTRATE", "HIGH", J, "Capture agent for the NIH microgravity pursuit: scans NIH/NCATS/ISS-NL notices, advances the top action, maintains the tracker.", "writes capture/NIH_Microgravity_pursuit.md + drafts; prompt authorises msmtp email to Jon; never external", None),
 "d7ed7449": ("SENSE", "MED", J, "BD Daily Intel: surfaces genuinely new Exos-aligned opportunities not covered by the SAM feed.", "web search; appends reports/aligned-opportunities-YYYY-MM.md; posts brief to #rd-team", None),
 "77ee570f": ("DECIDE", "HIGH", J, "Decisions Matrix Daily Update (MC task R-017): surfaces new decisions from blocked/overdue tasks, auto-closes decisions it judges resolved, DMs Jon a digest.", "reads Supabase tasks (service key) + MC decisions API; POSTs up to 3 new decisions; POSTs 'Auto-closed' answers to /api/decisions/answer; mail_search evidence check; DMs Jon",
              "LLM closes open MC decisions (STEP 3b/STEP 4) on its own judgement of email evidence or task state, with no human confirm"),
 "b942779c": ("SENSE", "LOW", J, "Weekly SBIR/SpaceWERX/AFWERX topic-fit watch; DMs Jon only when a genuine future-dated fit exists.", "web search; DM to Jon on a hit", None),
 "148cdb94": ("ORCHESTRATE", "HIGH", J, "Payload Sales 3-a-day: presents 3 ready outreach drafts to Jon for yes/no, then stages approved ones as one email to Jon's inbox.", "main-session system event; reads capture drafts; Jon yes/no gate; stages email to jquinn@exosaero.com; logs to Sales_Pipeline.md", None),
 "f4ea413e": ("SENSE", "LOW", J, "Research Team weekly Grant & Contract Scanner (Phase III first, onshoring programs).", "web search; posts brief to #rd-team; no file writes", None),
 "c5b07fbf": ("INTERPRET", "LOW", J, "Daily read-only Discord actionable digest for Jon across the main channels.", "reads Discord channels via message tool; DMs Jon; no writes", None),
 "1cf93736": ("SENSE", "MED", J, "Research Team weekly Technology & IP Monitor (RDRE, cryo, reusability, patents).", "web search; posts brief to #rd-team; prompt contains a run-log append to opportunities-tracker.md (contradicted by its own no-file-access header)", None),
 "14b9917b": ("INTERPRET", "HIGH", J, "Weekly investor progress update draft for David Mitchell, emailed to Jon for review/forward.", "reads capture trackers; writes captures/EXOS_Investor_Update_Draft1.md; emails Jon via msmtp; DMs Jon", None),
 "5f3b0529": ("SENSE", "MED", J, "Research Team weekly Policy & Regulatory Watch incl. the FAA reusable-license roster.", "web search; posts brief to #rd-team; prompt contains a run-log append to opportunities-tracker.md (contradicted by its own no-file-access header)", None),
 "f1464af0": ("ORCHESTRATE", "LOW", J, "One-shot reminder (2026-10-03): follow up the AcqBot Awards data-gap ticket; draft a nudge for John if no reply.", "main-session system event; draft only", None),
 "1202feb8": ("LEARN", "MED", J, "Nightly meta-evaluator: scores yesterday's agent outputs and logs recommended fixes.", "reads logs + cron list; appends memory/agent-performance-log.md; DMs Jon; read-only on crons", None),
 "ed638bd8": ("LEARN", "HIGH", J, "Weekly self-improvement implementer: applies meta-eval recommendations to cron prompts, schedules and workspace files; escalates the rest to the Decisions inbox.", "cron tool get/update on other jobs' prompts and schedules; may retire duplicate jobs; edits workspace files; POSTs decisions (token embedded in prompt); DMs Jon",
              "LLM changes other agents' prompts/schedules and can retire a job ('IMPLEMENT NOW') with no human confirm and no eval"),
 "28a46633": ("SENSE", "HIGH", J, "Weekly APAC deal-flow scan: appends new candidates to the APAC opportunities data, restarts Mission Control, emails Toshi a digest.", "main-session system event; writes mission-control/data/apac-opportunities.json; launchctl kickstart of com.exos.missioncontrol; emails toshihisa@exosaero.com",
              "LLM appends records to MC APAC data and restarts production Mission Control with no human confirm (entries are Watch/$0, but the restart is unconditional)"),
 "bfe8d388": ("SENSE", "LOW", J, "Weekly NASA SBIR cryo Phase I appendix watch.", "web search; DMs Jon", None),
 "ad2b3471": ("SENSE", "LOW", J, "Weekly DIU open-solicitation / HyCAT watch (BD-032); silent unless something opens.", "browser + web search; DMs Jon on a hit", None),
 "60aed194": ("SENSE", "MED", J, "Research Team weekly Competitive Intelligence brief incl. the FAA RLV license check.", "web search; posts to #rd-team; prompt contains a run-log append to opportunities-tracker.md (contradicted by its own no-file-access header)", None),
 "2f914ea5": ("GOVERN", "LOW", J, "Every-85-days reminder to renew the SAM.gov API key.", "announces fixed reminder to Jon DM", None),
 "eb9006cf": ("ORCHESTRATE", "LOW", J, "One-shot reminder (2027-04-06): pre-position NASA M-STAR FY27 teaming with an MSI lead.", "main-session system event; reminder/drafts only", None),
 "cc150b55": ("GOVERN", "LOW", J, "One-shot reminder (2027-07-01): Descartes Visual Compliance renewal decision vs in-house CSL engine.", "main-session system event; recommends; Jon confirms", None),
 "11feb1de": ("ORCHESTRATE", "MED", J, "One-shot TEST of the Bucket D channel-partner sales program (disabled).", "reads CRM API; writes Sales_Pipeline.md + drafts; posts to #blk3-payload", None),
 "155b1806": ("INTERPRET", "LOW", J, "Nightly 10 PM briefing to Jon (disabled; superseded).", "reads workspace files; DMs Jon", None),
 "1f60acb4": ("DECIDE", "HIGH", J, "Overnight Resolver Opus escalation pass (disabled): resolves items the Sonnet pass escalated.", "writes drafts, MC cards, opus-escalation-queue.json; POSTs decisions (token embedded in prompt); DMs Jon",
              "LLM executes 'reversible' MC changes (status/owner/priority, dedupe/merge) and 'executes or stages' unblock actions with no human confirm (job disabled)"),
 "2323192f": ("ORCHESTRATE", "LOW", J, "One-shot follow-up reminder for the HELIOTECH speaker slot + Teasley letter (disabled, past).", "session reminder; drafts only", None),
 "2952a034": ("INTERPRET", "LOW", J, "End-of-day status update to Jon (disabled).", "reads workspace files; DMs Jon", None),
 "2b6e4087": ("GOVERN", "LOW", J, "One-shot command: verify the RDRE durable outbox drop (disabled, past).", "runs scripts/verify-rdre-drop.py", None),
 "3299389d": ("ORCHESTRATE", "HIGH", J, "One-shot VFW Tundra AMP PowerStep RFQ follow-up (disabled, past).", "scans Proton inbox; may resubmit the car-part.com RFQ externally; posts to #vfw-post2150", None),
 "3a9112dc": ("ORCHESTRATE", "LOW", J, "One-shot #exomac-system wake message (disabled, past).", "posts a fixed status line", None),
 "3c5f756b": ("INTERPRET", "LOW", LZ, "Weekly CRM follow-up report of overdue contacts (disabled).", "reads mission-control/data/crm-data.json; posts to #general", None),
 "4c3413e0": ("ORCHESTRATE", "MED", J, "One-shot Veteran Fund follow-up check (disabled, past).", "checks Proton inbox; drafts nudge for Jon; updates MC task FUND-VF + tracker", None),
 "6028e2b9": ("ORCHESTRATE", "LOW", J, "One-shot DIU HyCAT outreach send reminder (disabled, past).", "posts reminder to #blk3-payload", None),
 "60d808ad": ("SENSE", "LOW", J, "Daily DPA Title III reauthorization watch (disabled).", "web search; DMs Jon", None),
 "65eec208": ("GOVERN", "HIGH", J, "One-shot Jon-scheduled OpenClaw update to 2026.7.1-2 (disabled, done).", "gateway update.run / openclaw update; Discord confirmation", None),
 "6751f847": ("SENSE", "LOW", J, "Daily 7 PM home solar/battery report from Home Assistant (disabled).", "HTTP GET to Home Assistant (token embedded in prompt); posts to home channel", None),
 "764159d5": ("SENSE", "LOW", J, "One-shot KARMEN watch of DoW SBIR 26.BZ Release 5 topics (disabled, past).", "web search; posts to #rd-team", None),
 "804832dd": ("ORCHESTRATE", "MED", J, "BLK3 payload sales research engine on local model (disabled; superseded by the Sales Agent).", "web search; writes tasks/blk3-payload-sales-pipeline.md; posts to #blk3-payload", None),
 "8bc72d87": ("SENSE", "HIGH", J, "Daily email opportunity scanner over the Proton inbox (disabled; replaced by launchd jobs).", "IMAP read (credential embedded in prompt); writes opportunities-tracker.md + drafts; emails Jon via SMTP", None),
 "8e68de1a": ("SENSE", "MED", J, "Mission Control email tracker wrapper around mission-control-imap.py (disabled; replaced by launchd).", "runs scripts/mission-control-imap.py", None),
 "970ab1bc": ("LEARN", "LOW", J, "One-shot Overnight Resolver cost review (disabled, past).", "reads usage log + cron run history; web search; DMs Jon", None),
 "a56299c6": ("ORCHESTRATE", "MED", J, "Weekly CRM dashboard data refresh (disabled).", "runs scripts/dashboard-data-generator.py", None),
 "c38f1316": ("GOVERN", "MED", J, "Weekly workspace file maintenance + lessons-learned capture (disabled).", "reads logs; may append lessons to AGENTS.md; posts to #exomac-system", None),
 "f2ec7aca": ("DECIDE", "HIGH", J, "Overnight Resolver (disabled): works the top-15 open MC items, executes reversible board changes, escalates one-way doors to Decisions.", "Supabase PATCH on tasks (state/owner/priority); dedupe/merge; POST/PATCH decisions (token embedded in prompt); writes drafts + usage log; DMs Jon",
              "LLM changes task state/owner/priority and merges duplicates in Supabase with no human confirm (job disabled)"),
 "f4ccb9d6": ("INTERPRET", "LOW", J, "Weekly Mission Control review from the legacy MD mirror (disabled).", "reads exos-mission-control.md; DMs Jon", None),
 "f8e2535b": ("SENSE", "LOW", J, "Daily opportunity scan on local model (disabled; superseded by BD Daily Intel).", "web search; DMs Jon", None),
}

SECRET_PAT = re.compile(r"(pass(word)?:\s*\S{8,}|X-Exo-Token:\s*[0-9a-f]{20,}|Bearer\s+sb_|eyJhbGci[\w-]{20,}|Token:\s*eyJ)", re.I)


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60].rstrip("-")


def ms_iso(ms):
    if not ms: return None
    return datetime.datetime.fromtimestamp(ms / 1000).astimezone().isoformat(timespec="seconds")


def schedule_str(s):
    k = s.get("kind")
    if k == "cron": return f"cron '{s.get('expr')}' {s.get('tz') or ''}".strip()
    if k == "every": return f"every {int(s.get('everyMs', 0)) // 1000}s"
    if k == "at": return f"at {s.get('at')} (one-shot)"
    return json.dumps(s)


def main():
    raw = subprocess.run(["openclaw", "cron", "list", "--all", "--json"], capture_output=True, text=True, timeout=60, cwd="/tmp").stdout
    jobs = json.loads(raw)["jobs"]
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    runs = {}
    for jid, n, nerr, last_ts in con.execute(
            "select job_id, count(*), sum(status='error'), max(ts) from cron_run_logs group by job_id"):
        runs[jid] = {"runs_total": n, "errors_total": nerr or 0}
    for jid, ts, status, err, dur in con.execute(
            "select job_id, ts, status, error, duration_ms from cron_run_logs r where seq=(select max(seq) from cron_run_logs where job_id=r.job_id and store_key=r.store_key)"):
        runs.setdefault(jid, {}).update({"last_run_logged": ms_iso(ts), "last_run_logged_status": status,
                                         "last_error_excerpt": (err or "")[:160] or None, "last_duration_ms": dur})
    out, labels = [], set()
    for j in jobs:
        p, st, dl = j["payload"], j.get("state", {}), j.get("delivery") or {}
        cls = C.get(j["id"][:8])
        if not cls: raise SystemExit(f"unclassified cron {j['id']} {j['name']}")
        layer, risk, owner, purpose, actions, gap = cls
        label = "cron:" + slug(j["name"])
        if label in labels: label = "cron:" + j["id"]
        labels.add(label)
        ta = p.get("toolsAllow")
        msg = p.get("message") or p.get("text") or ""
        out.append({
            "label": label, "id": j["id"], "name": j["name"], "enabled": j["enabled"],
            "schedule": schedule_str(j["schedule"]), "schedule_raw": j["schedule"],
            "sessionTarget": j["sessionTarget"], "agentId": j.get("agentId"),
            "payload_kind": p["kind"], "model": p.get("model") or "agent default",
            "toolsAllow": ta if ta else "agent default (main agent tools.profile=full, includes exec)",
            "toolsAllow_count": len(ta) if ta else None,
            "delivery": {k: dl.get(k) for k in ("mode", "channel", "to") if dl.get(k)} or None,
            "last_run_at": ms_iso(st.get("lastRunAtMs")), "last_run_status": st.get("lastRunStatus"),
            "consecutive_errors": st.get("consecutiveErrors"), "next_run_at": ms_iso(st.get("nextRunAtMs")),
            "run_history": runs.get(j["id"], {"runs_total": 0}),
            "stack_layer": layer, "risk": risk, "human_owner": owner, "purpose": purpose,
            "actions": actions, "ai_in_critical_path": p["kind"] in ("agentTurn", "systemEvent"),
            "decides_without_human_confirm": bool(gap), "human_confirm_gap": gap,
            "prompt_embeds_credential": bool(SECRET_PAT.search(msg)),
        })
    from collections import Counter
    summary = {
        "total": len(out), "enabled": sum(o["enabled"] for o in out),
        "by_layer": dict(Counter(o["stack_layer"] for o in out)),
        "by_risk": dict(Counter(o["risk"] for o in out)),
        "by_payload_kind": dict(Counter(o["payload_kind"] for o in out)),
        "enabled_by_layer": dict(Counter(o["stack_layer"] for o in out if o["enabled"])),
        "enabled_by_risk": dict(Counter(o["risk"] for o in out if o["enabled"])),
        "human_confirm_gaps": [o["label"] for o in out if o["decides_without_human_confirm"]],
        "r017": [o["label"] for o in out if "R-017" in o["name"]],
        "prompts_embedding_credentials": [o["label"] for o in out if o["prompt_embeds_credential"]],
    }
    doc = {"generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "source": "openclaw cron list --all --json + ~/.openclaw/state/openclaw.sqlite cron_run_logs (read-only)",
           "risk_rubric": "HIGH = sends email / acts outside Exos / changes a system of record (Supabase, MC decisions, MC data, cron config, service restart); MED = writes internal workspace state; LOW = reads and reports only",
           "summary": summary, "crons": out}
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
