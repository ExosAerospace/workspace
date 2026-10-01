#!/usr/bin/env python3
"""ERP-exo3 process register: route the 3 Lizi-drafted governance docs (SCRM Policy, QMS Charter,
Manufacturing Maturation Plan) to Jon for review as Decisions (Jon 2026-10-01). Idempotent via
dedupeKey. Attaches each Word draft to its card (uploads/_meta.json decision_id) so it opens inline."""
import json, os, shutil, time, uuid, urllib.request
WS = os.path.expanduser("~/.openclaw/workspace")
MC = os.path.join(WS, "mission-control")
TOK = open(os.path.join(MC, "data/.decisions-token")).read().strip()
REL = "ERP-exo3 process register (Phase 5/5B)"
COMMON = ("Drafted 7/29 (Rev A) and delivered by Lizi; it has sat 'in progress' on the ERP process register since. "
          "No approval/signature block yet. Click 📄 Review below to read it (about 1 page).")
AZ = ("It says CMMC is implemented 'on a GCC High / Azure Government boundary'. Azure Gov hosting is deferred and your "
      "CMMC strategy is to minimize scope, so I'd say 'Atomus-managed GCC High' only.")
DECISIONS = [
 {"file": "Exos_Supplier_SCRM_Policy.docx", "dedupeKey": "erp-reg-review-scrm-policy",
  "title": "Review: Supplier Management & SCRM Policy (Rev A)",
  "question": "Approve the Supplier Management & Supply-Chain Risk Policy for adoption?",
  "context": COMMON + "\n\nWHAT IT DOES: Approved Supplier List for flight-critical items; supplier qualification (quality, financial, export, cyber, past performance); scorecards (on-time, PPM, SCAR response); risk ratings (financial / single-source / geographic / cyber); second-source planning; FAR/DFARS flow-downs (252.246-7007 counterfeit parts, 252.204-7012 cyber, CMMC level checked before award); NIST SP 800-161.\n\nISSUES I'D FIX BEFORE ADOPTING:\n1. Sec. 8 says the supplier master, POs and receipts 'are maintained in the Exos ERP'. They aren't yet: the vendor/PO/receiving module is still 'todo' in ERP Phase 5. Reword to 'are being moved into the Exos ERP (Mission Control)' so it's true on audit.\n2. Sec. 3 relies on an Approved Supplier List 'maintained by Quality'. No ASL exists on file. Either we build it from the supplier DD registry (I can) or the policy says it is being established.\n3. Sec. 7: " + AZ + "\n4. Owner reads 'CEO / Quality'. Name a person for Quality (Mike Talley owns quality records today).",
  "options": ["Approve with Exo's fixes (recommended)", "Approve as written", "Changes needed (see note)"]},
 {"file": "Exos_QMS_Charter.docx", "dedupeKey": "erp-reg-review-qms-charter",
  "title": "Review: Quality Management System Charter (Rev A, AS9100D-aligned)",
  "question": "Approve the QMS Charter as the Exos quality framework (AS9100D certification shown as a target, not a claim)?",
  "context": COMMON + "\n\nWHAT IT DOES: Quality policy; process map (core + supporting); document/record control; nonconformance + CAPA; internal audit; management review; supplier quality (points to the SCRM Policy); 3-phase path to AS9100D certification (gap assessment → evidence → registrar audit).\n\nISSUES I'D FIX BEFORE ADOPTING:\n1. Sec. 10: " + AZ + "\n2. Internal audit and management review are 'on a defined schedule' but no schedule is defined. Suggest: management review quarterly, internal audit annually per process area.\n3. Owner 'CEO / Quality': name the Quality lead. Mike Talley owns NCR/CAPA/first-article in MC (due 12/15).\n4. Certification wording is correctly 'target/in progress'. Good, no overclaim.",
  "options": ["Approve with Exo's fixes (recommended)", "Approve as written", "Changes needed (see note)"]},
 {"file": "Exos_Manufacturing_Maturation_Plan.docx", "dedupeKey": "erp-reg-review-mrl-plan",
  "title": "Review: Manufacturing Maturation Plan (MRL) — has a BLK3 overclaim",
  "question": "Approve the BLK3 Manufacturing Maturation Plan, with the BLK3 overclaim corrected?",
  "context": COMMON + "\n\nWHAT IT DOES: DoD MRL framework; honest self-assessment of BLK3 at roughly MRL 5-7; target MRL 7-8; gaps (statistical process control, production tooling, second-source depth, rate capacity, AS9100D evidence); 4 milestones; risks incl. single-source composite supply from Scorpius.\n\nISSUES I'D FIX BEFORE ADOPTING:\n1. MUST FIX: Sec. 3 says 'BLK3 is a flight-proven reusable suborbital vehicle'. BLK3 hasn't flown yet. Flight heritage is SARGE. Reword: 'BLK3 is the enhanced successor to the flight-proven SARGE vehicle (commercial payloads since 2018); its first flight is planned.' This is the external-doc guardrail, and this plan is the kind of thing that ends up in proposals.\n2. The MRL 5-7 figure is our own estimate with no formal assessment behind it. Label it 'internal estimate', or Milestone 1 (baseline MRL assessment) has to come first.\n3. Sec. 7: " + AZ + "\n4. No dates on the milestones ('demand-driven'). Fine for now; MC tracks them.",
  "options": ["Approve with Exo's fixes (recommended)", "Changes needed (see note)", "Discuss"]},
]
PROP = ("On 'Approve with Exo's fixes': I make exactly the fixes listed, re-issue it as Rev B with an approval block (you as approver), "
        "file it in the Process Library (Quality / AS9100), and mark it done on the ERP process register. "
        "On 'Approve as written': I stamp Rev A approved and file it unchanged. On 'Changes needed': I apply your note and bring it back.")
meta_path = os.path.join(MC, "uploads/_meta.json")
for d in DECISIONS:
    f = d.pop("file")
    body = {**d, "proposedAction": PROP, "type": "choice", "priority": "med", "source": "Exo (ERP-exo3 process register)",
            "relatedItem": REL, "assignedTo": "jquinn@exosaero.com", "approver": "jquinn@exosaero.com", "agentClass": "erp"}
    r = urllib.request.Request("http://localhost:8080/api/decisions/ingest", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json", "X-Exo-Token": TOK})
    res = json.loads(urllib.request.urlopen(r).read().decode())
    did = res["id"]
    meta = json.load(open(meta_path))
    if not any(m.get("decision_id") == did and m.get("filename") == f for m in meta):
        stored = f"{int(time.time()*1000)}_{f}"
        shutil.copy2(os.path.join(WS, "drafts", f), os.path.join(MC, "uploads", stored))
        meta.append({"id": uuid.uuid4().hex[:16], "filename": f, "stored_name": stored,
                     "size": os.path.getsize(os.path.join(MC, "uploads", stored)), "extension": ".docx",
                     "task_id": None, "project_id": None, "decision_id": did, "doc_key": d["dedupeKey"],
                     "version": 1, "current": True, "uploaded_by": "Exo", "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        tmp = meta_path + ".tmp"; json.dump(meta, open(tmp, "w"), indent=2); os.replace(tmp, meta_path)
        time.sleep(0.01)
    print(did, d["dedupeKey"], "deduped" if res.get("deduped") else "")
