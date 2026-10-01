#!/usr/bin/env python3
"""ERP Phase 2 (Timekeeping Bamboo/DCAA -> MC cost accounting): file Jon's approval Decisions.
Exo took Phase 2 ownership 2026-10-01 (Jon). Idempotent via dedupeKey. Facts are from the live
Bamboo pull of 2026-10-01 (Sept 1-30 timesheet entries)."""
import json, os, urllib.request
WS = os.path.expanduser("~/.openclaw/workspace")
TOK = open(os.path.join(WS, "mission-control/data/.decisions-token")).read().strip()
REL = "task:1870 / ERP P2"
BASE = ("PHASE 2 STATUS (live Bamboo pull 10/1, Sept 1-30): 201 entries, 1,216 hrs, 8 of 12 people clocking. "
        "Only 2 Bamboo projects exist (\"EXOS US\" generic, \"Project Hermes\"), with no cost-code tasks. ~86% of hours carry no project. "
        "Hermes has 8.4 hrs in 2 months even though HVRR is the standing weekly focus. Not clocking: Kyle, David, Toshi, Andrew; Russ stopped 8/11. "
        "0 of 30 edited entries carry a reason. 20% were entered after the work day. Median approval lag is 6.5 days (max 15.5). "
        "Every employee except you reports to you in Bamboo, so you approve all timesheets, including Lizi's. "
        "The DCAA config has sat with Kyle (#1870, due 9/12) since 9/7 with no change. The MC side is built: bamboo_time_sync.js maps project/task to contract/WBS automatically once the codes exist.")
DECISIONS = [
 {"dedupeKey": "erp-p2-fin002-policy-approval",
  "title": "Approve DCAA Timekeeping Policy EXOS-FIN-002-0?",
  "question": "The policy has been PENDING APPROVAL since 9/5. It sets the rules: total-time accounting for everyone, same-day entry, one project and cost code per hour, no self-approval, corrections need a reason and re-approval, approved time locked. Approve it as written plus one addition: supervisors approve the prior week's time by Tuesday noon?",
  "context": BASE + "\n\nFILE: process-library/12-finance-accounting/EXOS-FIN-002-0_DCAA-Compliant_Timekeeping_Policy.docx (owner Kyle; Exo administers). Sec. 5 says approval happens 'on the defined schedule' but never defines it. I'd add 'by Tuesday 12:00 CT for the prior week'.",
  "proposedAction": "On Approve: I add the Tuesday-noon approval line, stamp Rev 0 APPROVED in the CM register and Process Library, and add it to Required Reading (sign by 11/1, same as the handbook). On Discuss: nothing changes.",
  "type": "choice", "options": ["Approve + Tuesday-noon approval rule (recommended)", "Approve as written", "Discuss"], "priority": "high"},
 {"dedupeKey": "erp-p2-bamboo-config-path",
  "title": "Who finishes the Bamboo DCAA setup? It's been stalled with Kyle since 9/7",
  "question": "The Bamboo API can't create projects or cost codes; that's admin-console only. How do we get it done this week?",
  "context": BASE + "\n\nOPTIONS: (1) A 30-min session where you or Lizi log into Bamboo admin in the ExoMac browser and I drive the setup on screen. No standing AI credential to the HR/PII system, and it's done in one sitting. This was your 9/5 plan (#2656). (2) Give Exo its own Bamboo admin account. Fastest ongoing, but it's a standing AI login with full HR/PII access, which is bad for CMMC scope. (3) Keep it with Kyle with a hard date of Fri 10/9. Kyle has had it since 9/7 and the date has slipped 3 weeks.",
  "proposedAction": "On (1): I close #2656's old premise, put a 30-min hold on your calendar (or Lizi's) for this week, and have the click-by-click setup sheet ready. On (3): I re-date #1870 to 10/9 with Kyle and nudge him. I re-run the sync the same day either way to confirm mapping.",
  "type": "choice", "options": ["30-min session, I log in, Exo drives (recommended)", "Lizi logs in, Exo drives", "Give Exo its own admin login", "Keep with Kyle, due 10/9"], "priority": "high"},
 {"dedupeKey": "erp-p2-cost-code-structure",
  "title": "Approve the Bamboo cost-code structure + timesheet approvers",
  "question": "This is what gets built in Bamboo. Approve the structure and the approver map?",
  "context": BASE + "\n\nPROJECTS -> TASKS (cost codes):\n- FA9300-25-C-6022 (Hermes / HVRR-RDRE SBIR II) -> 1.0 Program Mgmt, 2.0 RDRE Development, 3.0 HVRR Integration, 4.0 Test & Flight Demo\n- Karmen D2P2 -> 1.0 Program Mgmt, 2.0 BLK3 Demo Prep, 3.0 Flight Ops (2 flights/48 hr)\n- Overhead (shop/facility/fleet, incl. BLK3 build not on a contract)\n- G&A (exec, finance, HR, admin)\n- B&P (proposals)\n- IR&D (company-funded R&D)\n- Leave -> PTO, Holiday, Sick, Unpaid, Jury/Bereavement\n- Retire generic 'EXOS US' (re-label it Overhead so history isn't lost).\nProject names match the contract number exactly, so MC maps them automatically.\n\nAPPROVERS (no self-approval; you stop approving everyone):\n- Victor, Mike, Steve -> Phil\n- Phil -> Neil\n- Neil, Kyle, Russ, Toshi, Andrew -> you\n- Lizi -> Kyle (so you're not approving your spouse's time)\n- You -> David Mitchell\n- David -> you\nOpen question for Kyle: is BLK3 build Overhead or IR&D? It drives indirect rates. Default is Overhead until Kyle says otherwise.",
  "proposedAction": "On Approve: this is exactly what I build in the Bamboo setup session, and I set the supervisors in Bamboo to match. On 'Approve with edits': put your changes in the note.",
  "type": "choice", "options": ["Approve (recommended)", "Approve with edits (see note)", "Discuss"], "priority": "high"},
 {"dedupeKey": "erp-p2-total-time-scope",
  "title": "Who must clock time in Bamboo? (total-time accounting scope)",
  "question": "Kyle, David, Toshi and Andrew don't clock time, and Russ stopped 8/11. DCAA expects everyone whose labor lands on a government contract or an indirect pool to record all hours, salaried execs included. Who's in?",
  "context": BASE + "\n\n(1) All 12, exempt included (recommended). Indirect rates are only defensible if all labor is captured. G&A is mostly exec time. (2) Only people who charge government contracts (shop, Phil, Neil, Russ, you). Exec time then gets allocated by estimate, which is weaker in an audit. (3) Status quo (hourly/shop only). Not DCAA-defensible.",
  "proposedAction": "On (1) or (2): I email the affected people a 1-page quick-start from Exo (cc you) with the start date of Mon 10/12, after the codes exist. MC's weekly scorecard then flags missing days, late entries, and edits without a reason.",
  "type": "choice", "options": ["All 12, exempt included (recommended)", "Only gov-contract chargers", "Status quo"], "priority": "med"},
]
for d in DECISIONS:
    d.update({"source": "Exo (ERP Phase 2 owner)", "relatedItem": REL, "assignedTo": "jquinn@exosaero.com",
              "approver": "jquinn@exosaero.com", "agentClass": "erp"})
    r = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(d).encode(),
                               headers={"Content-Type": "application/json", "X-Exo-Token": TOK})
    print(d["dedupeKey"], "->", urllib.request.urlopen(r).read().decode()[:160])
