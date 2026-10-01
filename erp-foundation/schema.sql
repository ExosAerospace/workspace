-- ============================================================================
-- Mission Control -> ERP : Phase 0 SQLite Schema
-- Implements the §7 data-model sketch from MISSION_CONTROL_ERP_TRANSFORMATION_PLAN.md
--
-- Conventions:
--   * All PKs are TEXT (existing data uses string ids like "EXOS-0001", "D-001",
--     "BD-022"); synthetic rows use uuid-ish text. INTEGER ids (users) are stored
--     as TEXT too for uniformity, original value preserved.
--   * Timestamps are ISO-8601 TEXT (matches the JSON sources).
--   * raw_json columns preserve the full source record so no field is ever lost
--     during the JSON->SQLite migration (lossless reconciliation guarantee).
--   * FKs are declared; enable enforcement at the connection with
--     `PRAGMA foreign_keys = ON;` (migrate.js does this).
-- ============================================================================

PRAGMA journal_mode = WAL;        -- write-ahead log: durable last-committed txn, concurrent reads
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;

-- ============================================================================
-- CROSS-CUTTING : user, role, clearance, audit_log, document, notification
--   (these come first because most other tables reference user)
-- ============================================================================

-- Roles = "what job you do" (admin, manager, member, hr, finance, contracts)
CREATE TABLE IF NOT EXISTS role (
  id          TEXT PRIMARY KEY,           -- e.g. 'admin'
  label       TEXT NOT NULL,
  description TEXT
);

-- Clearance / sensitivity = "what data you may see" (hr-pii, itar-controlled, financial)
CREATE TABLE IF NOT EXISTS clearance (
  id          TEXT PRIMARY KEY,           -- e.g. 'hr-pii'
  label       TEXT NOT NULL,
  description TEXT
);

CREATE TABLE IF NOT EXISTS user (
  id            TEXT PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  name          TEXT,
  role_id       TEXT REFERENCES role(id),
  password_hash TEXT,
  password_salt TEXT,
  active        INTEGER NOT NULL DEFAULT 1,   -- 0/1
  created_at    TEXT,
  raw_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);

-- Many-to-many: a user may hold several clearances (role x clearance matrix)
CREATE TABLE IF NOT EXISTS user_clearance (
  user_id      TEXT NOT NULL REFERENCES user(id) ON DELETE CASCADE,
  clearance_id TEXT NOT NULL REFERENCES clearance(id) ON DELETE CASCADE,
  granted_at   TEXT,
  granted_by   TEXT REFERENCES user(id),
  PRIMARY KEY (user_id, clearance_id)
);

-- Immutable audit trail. One row per mutation. before_json/after_json are the
-- full record snapshots. Append-only by convention (no UPDATE/DELETE in the DAL).
CREATE TABLE IF NOT EXISTS audit_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  actor       TEXT,                       -- user id or system actor (e.g. 'migrate.js')
  ts          TEXT NOT NULL,              -- ISO-8601
  entity      TEXT NOT NULL,              -- table name, e.g. 'deal'
  entity_id   TEXT,                       -- pk of affected row
  action      TEXT NOT NULL,              -- 'insert' | 'update' | 'delete'
  before_json TEXT,                       -- null on insert
  after_json  TEXT                        -- null on delete
);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);

-- Document control (Phase 6 detail, schema stub here). e-sign envelopes map here.
CREATE TABLE IF NOT EXISTS document (
  id              TEXT PRIMARY KEY,
  title           TEXT,
  doc_type        TEXT,                   -- 'envelope' | 'cdrl' | 'contract' | ...
  status          TEXT,
  version         INTEGER DEFAULT 1,
  clearance_id    TEXT REFERENCES clearance(id),  -- access-control gating
  body_html       TEXT,
  created_at      TEXT,
  created_by      TEXT REFERENCES user(id),
  raw_json        TEXT
);
CREATE INDEX IF NOT EXISTS idx_document_type ON document(doc_type);

-- e-sign signers (children of document where doc_type='envelope')
CREATE TABLE IF NOT EXISTS document_signer (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id    TEXT NOT NULL REFERENCES document(id) ON DELETE CASCADE,
  name           TEXT,
  email          TEXT,
  role           TEXT,
  token          TEXT,
  signed         INTEGER DEFAULT 0,
  signed_at      TEXT,
  ip             TEXT,
  signature_type TEXT,
  raw_json       TEXT
);
CREATE INDEX IF NOT EXISTS idx_signer_doc ON document_signer(document_id);

CREATE TABLE IF NOT EXISTS notification (
  id          TEXT PRIMARY KEY,
  user_id     TEXT REFERENCES user(id),
  kind        TEXT,
  title       TEXT,
  body        TEXT,
  read        INTEGER DEFAULT 0,
  created_at  TEXT,
  raw_json    TEXT
);

-- ============================================================================
-- CRM : company, contact, deal, activity, comment   (single system of record)
--   Source crm-data.json is a flat denormalized row (company+contact+deal
--   combined). Migration normalizes it: one company, one contact, one deal per
--   source row, keyed deterministically off the source id (EXOS-0001).
-- ============================================================================

CREATE TABLE IF NOT EXISTS company (
  id          TEXT PRIMARY KEY,           -- '<srcid>-co'
  name        TEXT,
  category    TEXT,                       -- Financial Investor / Strategic / ...
  fit_thesis  TEXT,
  tier        TEXT,                       -- Tier 1/2/3
  source      TEXT,
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_company_name ON company(name);

CREATE TABLE IF NOT EXISTS contact (
  id          TEXT PRIMARY KEY,           -- '<srcid>-ct'
  company_id  TEXT REFERENCES company(id) ON DELETE SET NULL,
  name        TEXT,
  title       TEXT,
  email       TEXT,
  emails_alt  TEXT,
  phone       TEXT,
  linkedin    TEXT,
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_contact_company ON contact(company_id);
CREATE INDEX IF NOT EXISTS idx_contact_email ON contact(email);

CREATE TABLE IF NOT EXISTS deal (
  id              TEXT PRIMARY KEY,       -- original crm-data id, e.g. 'EXOS-0001'
  company_id      TEXT REFERENCES company(id) ON DELETE SET NULL,
  contact_id      TEXT REFERENCES contact(id) ON DELETE SET NULL,
  owner           TEXT,
  stage           TEXT,
  status          TEXT,                   -- Active / Inactive / Archived
  meeting_status  TEXT,
  warm_intro      TEXT,
  offer           TEXT,
  priority_score  INTEGER,
  cadence         INTEGER,
  first_outreach  TEXT,
  last_touch      TEXT,
  next_touch      TEXT,
  due             TEXT,
  next_action     TEXT,
  notes           TEXT,
  source          TEXT,
  raw_json        TEXT
);
CREATE INDEX IF NOT EXISTS idx_deal_stage ON deal(stage);
CREATE INDEX IF NOT EXISTS idx_deal_owner ON deal(owner);
CREATE INDEX IF NOT EXISTS idx_deal_company ON deal(company_id);

-- Activities (calls/meetings/touches). No discrete source yet; stub for forward use.
CREATE TABLE IF NOT EXISTS activity (
  id          TEXT PRIMARY KEY,
  deal_id     TEXT REFERENCES deal(id) ON DELETE CASCADE,
  contact_id  TEXT REFERENCES contact(id) ON DELETE SET NULL,
  kind        TEXT,                       -- call/email/meeting/note
  occurred_at TEXT,
  summary     TEXT,
  created_by  TEXT REFERENCES user(id),
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_activity_deal ON activity(deal_id);

-- Generic threaded comments, attachable to any entity.
CREATE TABLE IF NOT EXISTS comment (
  id          TEXT PRIMARY KEY,
  entity      TEXT NOT NULL,              -- 'deal' | 'task' | ...
  entity_id   TEXT NOT NULL,
  author      TEXT REFERENCES user(id),
  body        TEXT,
  created_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_comment_entity ON comment(entity, entity_id);

-- ============================================================================
-- WORK : project (<->contract/WBS), task_list, task, milestone,
--        time_entry (->approval, WBS), template
-- ============================================================================

CREATE TABLE IF NOT EXISTS project (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  contract_id TEXT,                       -- FK added logically; references contract(id)
  status      TEXT,
  created_at  TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS task_list (
  id          TEXT PRIMARY KEY,
  project_id  TEXT REFERENCES project(id) ON DELETE CASCADE,
  name        TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS task (
  id            TEXT PRIMARY KEY,         -- original tasks.json id, e.g. 'BD-022'
  task_list_id  TEXT REFERENCES task_list(id) ON DELETE SET NULL,
  project_id    TEXT REFERENCES project(id) ON DELETE SET NULL,
  title         TEXT,
  state         TEXT,                     -- In Progress / Done / Blocked / Ready
  owner         TEXT,
  due_date      TEXT,
  priority      INTEGER,
  category      TEXT,
  description   TEXT,
  source        TEXT,
  raw_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_state ON task(state);
CREATE INDEX IF NOT EXISTS idx_task_owner ON task(owner);

CREATE TABLE IF NOT EXISTS milestone (
  id          TEXT PRIMARY KEY,
  project_id  TEXT REFERENCES project(id) ON DELETE CASCADE,
  name        TEXT,
  due_date    TEXT,
  status      TEXT,
  raw_json    TEXT
);

-- DCAA-grade timekeeping target (Phase 2). Approval + WBS mapping built in.
CREATE TABLE IF NOT EXISTS time_entry (
  id           TEXT PRIMARY KEY,
  user_id      TEXT REFERENCES user(id),
  task_id      TEXT REFERENCES task(id) ON DELETE SET NULL,
  project_id   TEXT REFERENCES project(id) ON DELETE SET NULL,
  wbs_id       TEXT,                      -- references wbs_element(id) logically
  work_date    TEXT,
  hours        REAL,
  labor_class  TEXT,                      -- direct/indirect
  notes        TEXT,
  approved_by  TEXT REFERENCES user(id),  -- separation of duties: entry != approval
  approved_at  TEXT,
  locked       INTEGER DEFAULT 0,         -- 1 = no silent retroactive edits
  raw_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_time_user_date ON time_entry(user_id, work_date);

-- Reusable templates (task-list / onboarding / etc.)
CREATE TABLE IF NOT EXISTS template (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  kind        TEXT,                       -- 'task_list' | 'onboarding' | ...
  body_json   TEXT,
  raw_json    TEXT
);

-- ============================================================================
-- OPPORTUNITIES (BD pipeline; opportunities.json). Not in the §7 sketch by name
-- but a live MC dataset that must round-trip. Kept distinct from CRM deals.
-- ============================================================================
CREATE TABLE IF NOT EXISTS opportunity (
  id          TEXT PRIMARY KEY,           -- e.g. 'OPP-001'
  title       TEXT,
  status      TEXT,
  type        TEXT,
  category    TEXT,
  value       TEXT,                       -- free-text in source, not numeric
  due         TEXT,
  next_action TEXT,
  priority    INTEGER,
  description TEXT,
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_opportunity_status ON opportunity(status);

-- ============================================================================
-- DECISIONS inbox (decisions.json). Live MC dataset; round-trips.
-- ============================================================================
CREATE TABLE IF NOT EXISTS decision (
  id             TEXT PRIMARY KEY,        -- e.g. 'D-001'
  source         TEXT,
  related_item   TEXT,
  title          TEXT,
  question       TEXT,
  context        TEXT,
  proposed_action TEXT,
  type           TEXT,                    -- yesno / ...
  options_json   TEXT,                    -- JSON array
  priority       TEXT,
  dedupe_key     TEXT,
  status         TEXT,                    -- open / answered
  answer         TEXT,
  note           TEXT,
  answered_at    TEXT,
  answered_by    TEXT,
  created        TEXT,
  updated        TEXT,
  raw_json       TEXT
);
CREATE INDEX IF NOT EXISTS idx_decision_status ON decision(status);

-- ============================================================================
-- PEOPLE (Phase 1 stub - schema only, NO data loaded in Phase 0)
-- ============================================================================
CREATE TABLE IF NOT EXISTS org_unit (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  parent_id   TEXT REFERENCES org_unit(id),
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS position (
  id          TEXT PRIMARY KEY,
  title       TEXT,
  org_unit_id TEXT REFERENCES org_unit(id),
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS employee (
  id               TEXT PRIMARY KEY,
  user_id          TEXT REFERENCES user(id),
  org_unit_id      TEXT REFERENCES org_unit(id),
  position_id      TEXT REFERENCES position(id),
  manager_id       TEXT REFERENCES employee(id),
  full_name        TEXT,
  employment_status TEXT,
  start_date       TEXT,
  term_date        TEXT,
  comp_band        TEXT,                  -- HR PII: encrypt at rest (Phase 1)
  emergency_contact TEXT,                 -- HR PII
  raw_json         TEXT
);

CREATE TABLE IF NOT EXISTS pto_policy (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  accrual_rule TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS pto_balance (
  id          TEXT PRIMARY KEY,
  employee_id TEXT REFERENCES employee(id) ON DELETE CASCADE,
  policy_id   TEXT REFERENCES pto_policy(id),
  balance_hours REAL,
  as_of       TEXT,
  raw_json    TEXT
);

-- ============================================================================
-- CONTRACTS (Phase 4 stub - schema only, NO data loaded in Phase 0)
-- ============================================================================
CREATE TABLE IF NOT EXISTS contract (
  id            TEXT PRIMARY KEY,
  number        TEXT,                     -- e.g. 'FA9300-25-C-6022'
  title         TEXT,
  customer      TEXT,                     -- AFRL / DARPA / NASA
  status        TEXT,
  funded_value  REAL,
  start_date    TEXT,
  end_date      TEXT,
  raw_json      TEXT
);

CREATE TABLE IF NOT EXISTS wbs_element (
  id          TEXT PRIMARY KEY,
  contract_id TEXT REFERENCES contract(id) ON DELETE CASCADE,
  parent_id   TEXT REFERENCES wbs_element(id),
  code        TEXT,
  name        TEXT,
  budget      REAL,
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_wbs_contract ON wbs_element(contract_id);

CREATE TABLE IF NOT EXISTS deliverable (    -- CDRL
  id            TEXT PRIMARY KEY,
  contract_id   TEXT REFERENCES contract(id) ON DELETE CASCADE,
  cdrl_number   TEXT,
  title         TEXT,
  due_date      TEXT,
  status        TEXT,
  document_id   TEXT REFERENCES document(id),
  raw_json      TEXT
);

CREATE TABLE IF NOT EXISTS contract_milestone (
  id          TEXT PRIMARY KEY,
  contract_id TEXT REFERENCES contract(id) ON DELETE CASCADE,
  name        TEXT,
  due_date    TEXT,
  amount      REAL,
  status      TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS invoice (
  id          TEXT PRIMARY KEY,
  contract_id TEXT REFERENCES contract(id) ON DELETE SET NULL,
  number      TEXT,
  amount      REAL,
  status      TEXT,
  issued_at   TEXT,
  raw_json    TEXT
);

-- ============================================================================
-- PROCUREMENT / ASSETS (Phase 5 stub - schema only, NO data loaded in Phase 0)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vendor (
  id          TEXT PRIMARY KEY,
  name        TEXT,
  raw_json    TEXT,
  -- Phase 5 supply chain (migrate_supply.js adds these to existing dbs)
  qb_id TEXT, asl_status TEXT, category TEXT, country TEXT, flight_critical INTEGER,
  dd_tier TEXT, review_due TEXT, active INTEGER, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS purchase_order (
  id          TEXT PRIMARY KEY,
  vendor_id   TEXT REFERENCES vendor(id),
  project_id  TEXT REFERENCES project(id),
  wbs_id      TEXT REFERENCES wbs_element(id),
  status      TEXT,
  total       REAL,
  issued_at   TEXT,
  raw_json    TEXT,
  -- Phase 5 supply chain (migrate_supply.js adds these to existing dbs)
  po_number TEXT, source TEXT, qb_id TEXT, requested_by TEXT, approved_by TEXT, approved_at TEXT,
  need_by TEXT, promised_date TEXT, contract_id TEXT, decision_id TEXT, flight_critical INTEGER, updated_at TEXT
);

CREATE TABLE IF NOT EXISTS po_line (
  id          TEXT PRIMARY KEY,
  po_id       TEXT REFERENCES purchase_order(id) ON DELETE CASCADE,
  description TEXT,
  qty         REAL,
  unit_price  REAL,
  raw_json    TEXT,
  -- Phase 5 supply chain (migrate_supply.js adds these to existing dbs)
  line_no INTEGER, part_number TEXT, account TEXT, amount REAL, qty_received REAL
);

CREATE TABLE IF NOT EXISTS receipt (
  id          TEXT PRIMARY KEY,
  po_id       TEXT REFERENCES purchase_order(id) ON DELETE CASCADE,
  received_at TEXT,
  raw_json    TEXT,
  -- Phase 5 supply chain (migrate_supply.js adds these to existing dbs)
  po_line_id TEXT, qty_received REAL, qty_accepted REAL, qty_rejected REAL, result TEXT,
  coc_received INTEGER, received_by TEXT, ncr_id TEXT
);

CREATE TABLE IF NOT EXISTS asset (
  id          TEXT PRIMARY KEY,
  serial      TEXT,                       -- serialized flight hardware
  name        TEXT,                       -- BLK3 / Type-5 tank / GFE RDRE
  config      TEXT,
  location    TEXT,
  raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS asset_event (
  id          TEXT PRIMARY KEY,
  asset_id    TEXT REFERENCES asset(id) ON DELETE CASCADE,
  kind        TEXT,                       -- flight/calibration/maintenance
  occurred_at TEXT,
  notes       TEXT,
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_asset_event_asset ON asset_event(asset_id);

-- ── P5B: Production management (closes gov-readiness gap MQ-1) — lightweight production control ──
CREATE TABLE IF NOT EXISTS work_order (
  id          TEXT PRIMARY KEY,
  wo_number   TEXT,                       -- WO-2026-001
  item        TEXT,                       -- assembly/part being built
  project_id  TEXT REFERENCES project(id),
  wbs_id      TEXT REFERENCES wbs_element(id),
  qty         REAL,
  status      TEXT,                       -- planned/released/in_progress/complete/hold
  due         TEXT,
  raw_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_work_order_status ON work_order(status);

CREATE TABLE IF NOT EXISTS work_order_op (
  id            TEXT PRIMARY KEY,
  work_order_id TEXT REFERENCES work_order(id) ON DELETE CASCADE,
  seq           INTEGER,                  -- routing step order
  operation     TEXT,                     -- layup/cure/machining/integration/test
  work_center   TEXT,
  status        TEXT,                     -- pending/in_progress/complete
  raw_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_wo_op_wo ON work_order_op(work_order_id);

CREATE TABLE IF NOT EXISTS ncr (
  id            TEXT PRIMARY KEY,
  ncr_number    TEXT,
  work_order_id TEXT REFERENCES work_order(id),
  kind          TEXT,                     -- NCR/CAPA/first-article
  description   TEXT,
  status        TEXT,                     -- open/in_review/closed
  disposition   TEXT,                     -- use-as-is/rework/scrap/return-to-vendor
  raw_json      TEXT
);
CREATE INDEX IF NOT EXISTS idx_ncr_wo ON ncr(work_order_id);

-- ===== Phase 5C — MRP (also applied additively by migrate_mrp.js) =====
CREATE TABLE IF NOT EXISTS part (
  id             TEXT PRIMARY KEY,          -- pt-<normalized part number>
  part_number    TEXT,
  description    TEXT,
  vendor         TEXT,                      -- normalized vendor name from the BOM
  vendor_id      TEXT REFERENCES vendor(id),
  unit           TEXT,
  unit_cost      REAL,
  cost_basis     TEXT,                      -- paid | found | bom-sheet | none
  lead_time_days INTEGER,
  make_buy       TEXT,                      -- make | buy
  active         INTEGER DEFAULT 1,
  raw_json       TEXT,
  updated_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_part_pn ON part(part_number);
CREATE TABLE IF NOT EXISTS bom_line (
  id          TEXT PRIMARY KEY,             -- <assembly>:<section>#<item>
  assembly    TEXT,                         -- BLK3
  section     TEXT,
  item_no     TEXT,
  part_id     TEXT REFERENCES part(id),
  qty_per     REAL,                         -- per vehicle; NULL = not quantified on the BOM
  raw_json    TEXT,
  updated_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_bom_assembly ON bom_line(assembly);
CREATE INDEX IF NOT EXISTS idx_bom_part ON bom_line(part_id);
CREATE TABLE IF NOT EXISTS inventory_txn (
  id          TEXT PRIMARY KEY,
  part_id     TEXT REFERENCES part(id),
  kind        TEXT,                         -- count (physical snapshot) | receipt (ERP receiving) | adjust
  qty         REAL,                         -- count: absolute on-hand; receipt/adjust: delta
  location    TEXT,
  source      TEXT,
  ref         TEXT,
  occurred_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_invtxn_part ON inventory_txn(part_id, occurred_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invtxn_ref ON inventory_txn(kind, ref) WHERE ref IS NOT NULL AND kind = 'receipt';
CREATE TABLE IF NOT EXISTS mission (
  id          TEXT PRIMARY KEY,             -- M5, M6
  label       TEXT,
  customer    TEXT,
  vehicle     TEXT,                         -- BLK3 (= BOM assembly)
  asset_id    TEXT REFERENCES asset(id),
  status      TEXT,
  need_date   TEXT,                         -- vehicle build-complete need date (drives MRP need-by)
  raw_json    TEXT,
  updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS mrp_run (
  id           TEXT PRIMARY KEY,
  run_at       TEXT,
  actor        TEXT,
  scope        TEXT,
  summary_json TEXT
);
CREATE TABLE IF NOT EXISTS mrp_line (
  id          TEXT PRIMARY KEY,
  run_id      TEXT REFERENCES mrp_run(id) ON DELETE CASCADE,
  part_id     TEXT REFERENCES part(id),
  assembly    TEXT,
  demand_ref  TEXT,                         -- asset serial + missions, e.g. "S0 (M5, M6)"
  gross       REAL,
  on_hand     REAL,
  on_order    REAL,
  net         REAL,
  unit_cost   REAL,
  ext_cost    REAL,
  vendor      TEXT,
  vendor_id   TEXT,
  make_buy    TEXT,
  need_by     TEXT,
  action      TEXT                          -- none | buy | make | quantify (BOM qty missing)
);
CREATE INDEX IF NOT EXISTS idx_mrp_line_run ON mrp_line(run_id);
CREATE TABLE IF NOT EXISTS purchase_request (
  id            TEXT PRIMARY KEY,           -- pr-<run>-<n>
  run_id        TEXT REFERENCES mrp_run(id),
  vendor        TEXT,
  vendor_id     TEXT,
  status        TEXT,                       -- open | converted | cancelled | superseded
  est_total     REAL,
  need_by       TEXT,
  routes_to_jon INTEGER,                    -- est_total >= supply-config approval threshold
  po_id         TEXT REFERENCES purchase_order(id),
  raw_json      TEXT,                       -- lines [{part_id, part_number, description, qty, unit_cost}]
  created_at    TEXT,
  updated_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_pr_status ON purchase_request(status);
