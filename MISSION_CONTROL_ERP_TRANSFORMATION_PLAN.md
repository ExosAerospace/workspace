# Mission Control → Work-Management ERP
## Phased Transformation Plan (incl. BambooHR absorption & cutover)

**Prepared for:** John Quinn, Cofounder & Chairman, Exos Aerospace
**Date:** 2026-06-06
**Owner:** Exo (build) · Jon (review / go-no-go gates)

---

## 1. Executive Summary

Mission Control already contains ~70% of an ERP's building blocks: role-based auth, CRM
(companies/deals/activities), tasks with task-lists/projects/milestones/templates, time-entries,
e-sign/DocuSign, a decisions inbox, notifications, inbound-email, and a Teamwork sync. The work
ahead is **less about new features and more about system-of-record rigor**: a real database,
contract/cost accounting, HR as a first-class domain, and the audit + access controls a defense
contractor must have.

This plan does three things:
1. Hardens the foundation so ERP modules can be added without the system collapsing.
2. Absorbs **BambooHR** (employee records, onboarding, benefits, PTO, time tracking) into Mission
   Control, run **in parallel** until everyone is migrated, then a clean **cutover** and Bamboo
   decommission.
3. Adds the Exos-specific ERP spine: contracts/CDRL tracking, DCAA-grade timekeeping, project cost
   accounting, procurement, asset tracking, and QuickBooks finance integration.

**Single most important point:** do the foundation (Phase 0) before anything else. Adding HR,
contracts, or finance on top of today's JSON flat-files would compound fragility and create exactly
the data-integrity problems an ERP exists to prevent.

---

## 2. Current-State Assessment

**Architecture today**
- Vanilla Node `http` server — `server.js`, ~2,128 lines, hand-rolled routing (single file).
- Persistence = JSON flat-files (`crm-data.json` ~1.1MB, `tasks.json`, `envelopes.json`,
  `opportunities.json`, `decisions.json`, `users.json`).
- Auth with admin/member roles; DocuSign/e-sign subsystem; decisions inbox; inbound-email; Teamwork sync.

**Strengths:** broad functional surface already live; clean module boundaries by *page*; working
auth and e-sign; real users.

**Risks / gaps for ERP use**
- **No transactional database** → concurrent-write corruption risk, no relational integrity, no
  referential constraints. This is the critical blocker.
- **Two CRMs** — this MC CRM and a Supabase CRM (localhost:8080). Divergent customer data is the
  classic ERP-killer; one must become the system of record.
- **No audit trail** (who changed what, when, before/after) — required for ITAR and DCAA.
- **No HR domain, no contracts/CDRL, no procurement, no asset register, no cost accounting.**
- **Monolithic server** makes safe extension hard.

---

## 3. Target Architecture

- **Database:** SQLite now (zero-ops, single file, transactional, drop-in), with Postgres/Supabase
  as the documented scale path. One schema with migrations.
- **Server:** `server.js` decomposed into route modules + a data-access layer; auth/audit as
  middleware applied uniformly.
- **Security:** hardened RBAC (role + clearance), an immutable audit log on every mutation,
  encryption at rest for HR PII, ITAR access gating on controlled documents.
- **Integrations:** QuickBooks (finance), BambooHR API (one-time + delta import during parallel run),
  existing email/DocuSign retained.
- **System of record:** Mission Control becomes the single source of truth for work, people,
  contracts, and assets; QuickBooks remains the financial book of record.

---

## 4. Guiding Principles

1. **Foundation before features.** No new ERP domain lands on flat-files.
2. **Parallel-run, never big-bang** for anything people depend on (especially HR/payroll-adjacent).
3. **Every mutation is audited.** Non-negotiable for federal compliance.
4. **Integrate finance, don't rebuild it.** QuickBooks stays the GL.
5. **Migrate data with validation gates.** Reconcile record counts and spot-check before trusting.
6. **One system of record per domain.** Kill duplicates as we go.

---

## 5. Phased Plan

### Phase 0 — Foundation *(prerequisite for all that follows)*
**Goal:** make Mission Control safe to build an ERP on.
- Migrate JSON flat-files → **SQLite** with a defined schema + migration scripts; preserve all
  existing data (CRM, tasks, opportunities, envelopes, users).
- Decompose `server.js` into route modules + data layer.
- Add **audit-log** table + middleware (actor, timestamp, entity, before/after).
- Harden **RBAC** (roles + clearance levels); add automated nightly **backups** of the DB.
- **Resolve the two-CRM problem** — choose MC or Supabase as the single CRM of record; reconcile.
**Exit criteria:** all current features run on SQLite; audit log capturing changes; backups verified;
one CRM of record.

### Phase 1 — HR Core + BambooHR Import *(begins the Bamboo absorption)*
**Goal:** stand up People as a first-class domain and import Bamboo data.
- **Employee master record:** identity, role/title, manager, department, employment status,
  start/term dates, comp band, emergency contact, documents.
- **Org structure / reporting lines** (drives approvals downstream).
- **Onboarding workflows:** checklist templates, task assignment, document collection, e-sign of
  new-hire packets (reuse the DocuSign subsystem).
- **Benefits tracking:** plan enrollment, effective dates, dependents, open-enrollment records.
- **PTO / leave:** policies, accrual rules, balances, request → approval flow.
- **BambooHR import:** pull via BambooHR REST API (CSV fallback) — employees, org, time-off balances
  & policies, benefits enrollments, documents, onboarding templates.
- **Encrypt HR PII at rest; restrict by role.**
**Runs in parallel with Bamboo** — Bamboo remains authoritative until Phase 3 cutover.
**Exit criteria:** every active employee present and reconciled against Bamboo; onboarding runs
end-to-end in MC; benefits + PTO balances match Bamboo.

### Phase 2 — Timekeeping (DCAA-grade) + Project Cost Accounting (labor)
**Goal:** replace Bamboo time tracking with audit-defensible timekeeping tied to work.
- Upgrade the existing `time-entries` to **DCAA-compliant** timekeeping: daily entry, supervisor
  approval, **immutable audit trail**, no silent retroactive edits, labor mapped to project/WBS.
- **PTO integration** so leave and worked hours live in one timesheet.
- **Direct vs. indirect** labor classification; **budget-vs-actual** burn per project.
- Timesheet → (later) QuickBooks/payroll hand-off.
**Exit criteria:** a full pay-period run in MC matches Bamboo time data; supervisors approving in MC;
audit trail verified.

### Phase 3 — BambooHR Cutover & Decommission *(REMOVED 2026-10-01)*

> **REMOVED (Jon 2026-10-01): Phase 3 is deleted from the rollout. BambooHR stays the HR + timekeeping system of record permanently due to compliance risk; MC interfaces to it, never replaces it. Kept below for history only.**
**Goal:** make Mission Control authoritative for HR and retire Bamboo.
- **Go/no-go checklist** (see §6). Confirm 100% of staff onboarded into MC, balances reconciled,
  timekeeping validated for a full cycle, payroll/benefits data flowing.
- **Freeze Bamboo writes**, final delta import, flip MC to authoritative.
- **Export & archive** full Bamboo dataset for records retention before closing the account.
- Decommission Bamboo subscription; redirect HR processes to MC.
**Exit criteria:** all HR transactions originate in MC; Bamboo archived and cancelled.

### Phase 4 — Contracts & CDRL + Cost-Accounting Rollup *(highest Exos leverage)*
**Goal:** connect federal awards to work, labor, and money.
- **Contracts module:** contract → WBS → tasks → **deliverables/CDRLs** → milestones → invoices.
- Track SBIR Phase II, TACFI, DARPA DSO/TTO, Phase III vehicles with due dates and funded value.
- **Complete project cost accounting** by joining Phase-2 labor + Phase-5 spend against contract WBS
  (budget vs. actual, EAC/ETC).
**Exit criteria:** every active award modeled; CDRL due-dates tracked; live burn per contract.

### Phase 5 — Procurement + Asset/Hardware Tracking
**Goal:** control spend and flight-hardware configuration.
- **Procurement:** vendors, purchase orders, receiving; PO spend tied to project/WBS; feeds QuickBooks.
- **Asset register:** serialized flight hardware (BLK3, Type-5 tanks, GFE RDRE) — location, config,
  flight history, calibration/maintenance.
**Exit criteria:** POs raised and received in MC; hardware register reflects current fleet/config.

### Phase 5B — Production Management (Manufacturing) *(closes the gov-readiness manufacturing gap)*
**Goal:** plan and run low-rate/prototype production in the system of record, so Exos can answer "Yes" to the federal *manufacturing management* question and host quality records for the QMS. This is the one production-control capability not covered elsewhere in the plan.
**Why now:** the DIB/government readiness assessment (see Mission Control → Government/DIB Readiness Register, `data/gov-readiness.json`) flags manufacturing management (MQ-1) as the only hard **Gap**. A lightweight increment closes it without turning MC into a full MES.
- **Bill of Materials (BOM):** per end item (BLK3, Type-5 tank, subassemblies); links to `po_line`/`vendor` for buy parts.
- **Work orders / routings:** planned vs. actual, operation steps, labor booked via existing `time_entry`, material issued from the asset/inventory register.
- **Production scheduling & WIP:** simple capacity/lead-time view; surfaces single-source and scale constraints (feeds SCRM scalability item SCRM-4).
- **Quality records (QMS home):** inspection results, nonconformance (NCR), and corrective/preventive action (CAPA) tied to the work order — the transactional layer under the QMS Charter (readiness item MQ-2). First-article inspection records for gov work.
- **Boundary (no overlap):** production *transactions* live here in the ERP; the **QMS status, Manufacturing Maturation Plan (MRL) milestones, and certification register stay in the MC readiness layer** and reference these records rather than duplicating them.
**Exit criteria:** a BLK3 (or subassembly) build runs on a work order with BOM, booked labor, issued material, and captured inspection/NCR records; MQ-1 moves from Gap to Yes.

### Phase 6 — Finance Integration + Document Control / ITAR
**Goal:** close the loop with finance and lock down controlled documents.
- **QuickBooks integration:** sync invoices, POs, expenses; pull budget-vs-actual back into MC
  dashboards. (Integrate — do not rebuild a GL.)
- **Document control:** versioning, controlled access by role/clearance, full access audit; ITAR
  gating on technical data.
**Exit criteria:** finance reconciles MC ↔ QuickBooks; controlled docs access-gated and audited.

---

## 5A. Phase 0 Detail — RBAC, Backups, Availability & CMMC/CUI Hosting

### RBAC
Two dimensions enforced at one chokepoint:
- **Role** (`admin`, `manager`, `member`, plus `hr` / `finance` / `contracts`) = what job you do.
- **Sensitivity clearance** (`hr-pii`, `itar-controlled`, `financial`) = what data you may see. Role does
  not auto-grant sensitive data; both are checked together.
- A single auth+authz middleware runs on **every** `/api/*` route (not per-page as today), checks
  `role × sensitivity` against a permissions matrix, and writes the **audit log** on every mutation.
- HR PII / controlled docs encrypted at rest; controlled-doc reads logged. Separation of duties
  (timesheet entry ≠ approval). These map directly to NIST 800-171 families (AC, AU, IA, MP, SC).

### Backups (3-2-1, restore-tested)
SQLite = one file + write-ahead log (WAL):
- **Continuous:** WAL makes the last committed transaction durable (a crash loses nothing committed).
- **Snapshots:** hourly online snapshot (retain 48h), nightly full (30d), weekly (1y).
- **3-2-1:** copy on ExoMac + the `exobot-backup` node + **encrypted offsite** in the Atomus-managed
  Azure Government boundary. Encrypted because they contain HR PII / CUI.
- **Verified:** automated **monthly restore drill** into a scratch instance with row-count checks.
- **RPO ≤ ~5 min.**

### Availability — when ExoMac is down
- **Planned maintenance / reboot:** Phase 0 makes MC a supervised **launchd `KeepAlive` service**
  (today it's a bare `node server.js`). Auto-relaunch in seconds; WAL replays cleanly. Brief blip.
- **Crash / power loss:** same auto-restart path (RTO ≤ ~15 min worst case); last committed
  transaction survives. No manual step for the common case.
- **Systemic failure (host dead):** today MC is a **single point of failure on one Mac.** Fix =
  encrypted offsite backup (data survives hardware) + a **warm standby** in Azure Government running
  the same Node+SQLite, fed the offsite backups; repoint Cloudflare/Tailscale to it. **RTO ≈ 1–2h,
  RPO ≤ 5 min.**

### CMMC 2.0 / CUI Hosting
**Confirmed:** Exos has **commercial M365 with GCC High** (Atomus-managed). **Azure Government compute
is not confirmed** and likely must be added.

Critical distinction:
- **GCC High** = compliant M365 **SaaS** (email/SharePoint/OneDrive/Teams). A compliant place to
  **store** encrypted backup **files** today — at no new cost.
- It is **not** a place to **run** the custom Node/SQLite ERP. A custom app that processes CUI needs
  **Azure Government** compute, which Atomus can add alongside the existing GCC High agreement
  (defense contractors routinely run both together).

**The real scoping question is the PRIMARY host, not the backup.** For CMMC L2, the system that
processes/stores CUI is in the assessment boundary. Today that's **ExoMac — a Mac outside the
boundary.** Two clean paths:
- **(A) Host the CUI-bearing ERP in Azure Government** and keep CUI off ExoMac. Cleaner; ExoMac drops
  out of CUI scope (becomes dev / non-CUI node). Requires Azure Gov.
- **(B) Bring ExoMac into scope** and harden it to 800-171 as a managed CUI asset under Atomus.
  Heavier; keeps a single Mac as a compliance liability.
Recommendation: **(A).**

**Phased so it doesn't block progress:**
- **Now (no new spend):** GCC High SharePoint/OneDrive = encrypted **backup-file** target; `KeepAlive`
  on ExoMac; build Phase 0 foundation with **non-CUI / test data** so ExoMac stays out of scope.
- **Before Phase 1 (HR PII goes live):** Atomus adds **Azure Government**; host the CUI ERP + warm
  standby + immutable Blob backups there; ExoMac exits CUI scope.
- **Keep ITAR technical data out of MC entirely** (MNDA already enforces) so in-scope CUI = PII +
  contract/financial.

**Questions for Atomus (to finalize hosting):**
1. Can **Azure Government** compute be added to the existing GCC High agreement, and at what cost? (A
   live warm-standby ERP needs it; GCC High SaaS can't host a custom app.)
2. For **now**, confirm encrypted ERP backups may be stored in **GCC High SharePoint/OneDrive** as the
   compliant offsite target.
3. Confirm target = **CMMC 2.0 Level 2** for the MC/ERP enclave; define the **enclave boundary**.
4. Which 800-171 controls does the GCC High / Azure Gov boundary **inherit** vs. what MC must implement?
5. **ExoMac scoping:** is keeping CUI off ExoMac (Option A) acceptable to stay out of assessment scope,
   or must ExoMac be hardened/managed (Option B)?
6. **HR PII** handling expectations and any **DFARS 252.204-7012** flow-down obligations.

---

## 6. BambooHR Cutover Plan (detail) *(REMOVED 2026-10-01)*

> **REMOVED (Jon 2026-10-01): Phase 3 is deleted from the rollout. BambooHR stays the HR + timekeeping system of record permanently due to compliance risk; MC interfaces to it, never replaces it. Kept below for history only.**

**Strategy:** parallel-run, reconcile, validate, then flip. Bamboo stays authoritative until the
go/no-go passes.

**Data to import (API-first, CSV fallback):**
- Employee records & PII, org/reporting structure, comp bands
- Time-off policies, accruals, current balances
- Benefits plans, enrollments, dependents
- Stored HR documents, onboarding checklist templates
- Historical time-tracking / timesheets (for continuity & audit)

**Parallel-run period:** new hires onboarded in MC from Phase 1 onward; existing staff migrated in
batches. Bamboo and MC kept in sync via delta imports until cutover.

**Go/no-go checklist (all must be green):**
- [ ] 100% of active employees present in MC and reconciled to Bamboo (record-count + spot-check)
- [ ] PTO balances match to the day
- [ ] Benefits enrollments match
- [ ] A full pay-period of timekeeping in MC matches Bamboo, with supervisor approvals working
- [ ] Payroll/benefits data export from MC validated by whoever runs payroll
- [ ] HR PII encrypted, access-restricted, audited
- [ ] Full Bamboo export archived for retention

**Cutover:** freeze Bamboo → final delta import → flip MC authoritative → archive Bamboo → cancel
subscription.

**Rollback:** until the archive+cancel step, Bamboo remains intact and can be reinstated; cutover is
reversible up to that final gate.

---

## 7. Data-Model Sketch (core entities)

- **People:** employee, org_unit, position, benefit_enrollment, pto_policy, pto_balance, pto_request,
  onboarding_template, onboarding_instance
- **Work:** project (↔ contract/WBS), task_list, task, milestone, time_entry (→ approval, WBS),
  template
- **Contracts:** contract, wbs_element, deliverable/CDRL, contract_milestone, invoice
- **CRM:** company, contact, deal, activity, comment  *(single system of record)*
- **Procurement/Assets:** vendor, purchase_order, po_line, receipt, asset, asset_event
- **Cross-cutting:** user, role, clearance, audit_log, document (version, access_control), notification

---

## 8. Risks & Mitigations

- **HR/payroll-adjacent migration risk** → strict parallel-run + go/no-go gates; reversible until final archive.
- **PII / ITAR exposure** → encryption at rest, RBAC + clearance, audit log, controlled-doc gating.
- **Data-integrity during JSON→SQLite migration** → migrate with validation/reconciliation; keep
  flat-file backups until verified.
- **Duplicate CRM drift** → resolve in Phase 0 before further build.
- **Scope creep** → ship by phase, each with hard exit criteria; no phase starts before prior exit.

---

## 9. Effort & Sequencing

Relative sizing (built by Exo + the coding agent; Jon owns review/validation gates):

- **Phase 0 — Foundation:** Large. The unlock; everything depends on it.
- **Phase 1 — HR Core + Bamboo import:** Large.
- **Phase 2 — Timekeeping/cost (labor):** Medium-Large.
- **Phase 3 — Bamboo cutover:** Medium (mostly validation + gates, low new-build).
- **Phase 4 — Contracts/CDRL:** Medium-Large.
- **Phase 5 — Procurement + Assets:** Medium.
- **Phase 6 — Finance/QuickBooks + Doc control/ITAR:** Medium-Large.

Phases 0→3 form the **HR/Bamboo-replacement track** and should run first as a block. Phases 4→6 are
the **defense-ERP spine** and can begin once the foundation (Phase 0) is done — Phase 4 in particular
is the highest business value once timekeeping (Phase 2) exists to feed it.

---

## 10. Recommended Next Steps

1. **Approve Phase 0** and let me lock the data model/schema (this plan's §7) before migrating.
2. **Decide the CRM system of record** (MC vs. Supabase).
3. **Provision BambooHR API access** (API key) so I can scope the exact import in Phase 1.
4. Confirm **who validates payroll/benefits** at cutover (the go/no-go owner).

I recommend locking the schema first, then I stand up Phase 0 (SQLite + modular server + audit +
backups) so you can see it running before we touch HR data.
