# #rd-team — Task Queue
**Domain:** R&D, engineering, propulsion (RDRE), COPV, technical development
**Discord Channel ID:** 1501636614034821320
**Processor Schedule:** Every 6 hours

> **Context hygiene:** Do NOT inline decks, full proposals, or generated images into this thread — they overflow the context window. Build heavy artifacts as files (drafts/), post a summary + path only. Session auto-rotates on compaction; weekly floor-rotation via com.exos.channel-session-rotate.

---

### TASK-RD-001: NASA SBIR AERO.4.S26B — Appendix 26B (SBIR_26B_P1)
- **Status:** completed
- **Priority:** critical
- **Submitted:** 2026-05-20
- **Deadline:** 2026-05-21 5:00 PM ET
- **Submitted by:** Jon
- **Description:** NASA SBIR Phase I — AERO.4.S26B "Flight-Test Measurement Technologies for Propulsion and Structures." Proposal: Embedded Fiber Optic Bragg Grating SHM for Reusable Composite Launch Vehicle Structures. BAA 80NSSC26R0003, Appendix 26B. Award: up to $225K / 6 months. PI: Phil Eaton. LM ToI collaboration (Joseph Epstein, Craig Owens).
- **Deliverables:** Jon submit final package via ProSAMS by May 21 5 PM ET
- **Notes:** Full proposal + technical narrative in drafts/. Quad chart v2 sent. LM support letter in drafts/. Remaining: Jon ProSAMS submission | Collicott support letter signature | Verify CAGE/UEI in SAM.gov

### TASK-RD-002: NASA SBIR INSTALG.2.S26A — Appendix 26A (SBIR_26A_P1)
- **Status:** completed
- **Priority:** critical
- **Submitted:** 2026-05-20
- **Deadline:** 2026-05-21 5:00 PM ET
- **Submitted by:** Jon
- **Description:** NASA SBIR Phase I — INSTALG.2.S26A "Suborbital Instruments and Sensor Systems." Proposal v2: Suborbital Atmospheric Contaminant Sampling System (SACSS) — multi-altitude capture and return of reentry-derived particulate. BAA 80NSSC26R0003, Appendix 26A. Award: up to $225K / 6 months. PI: Phil Eaton.
- **Deliverables:** Jon submit final package via ProSAMS by May 21 5 PM ET
- **Notes:** V1 (RSSDP) and V2 (SACSS) drafts in drafts/. Jon to review and submit.

### TASK-RD-003: Mission Control Rollout to Early Adopters — Rules & Access
- **Status:** completed
- **Priority:** high
- **Submitted:** 2026-05-29
- **Completed:** 2026-05-29
- **Submitted by:** Jon
- **Description:** Prepare Mission Control for rollout to early adopters. Define access rules, usage guidelines, onboarding process, and permissions model. Determine who the early adopter group is, what they can see/do, and what guardrails are needed. Reference: mission-control/ directory for current state.
- **Deliverables:** Early adopter rollout plan with rules, access controls, and onboarding documentation
- **Notes:** Completed 2026-05-29. Implemented new `early_adopter` role in server.js with strict sandboxing: (1) API access limited to tasks and task updates only — CRM, deals, DocuSign, companies, templates, admin, dashboard all blocked; (2) Task deletion and capture endpoints blocked; (3) Page access restricted to index.html (task board) and /welcome onboarding page — attempts to access CRM, DocuSign, opportunities, admin redirect to /; (4) Task visibility scoped to assigned project via user.project field; (5) Welcome/onboarding page at /welcome with account info, capabilities, usage guidelines, and getting-started steps; (6) index.html updated with role-aware UI — hides Sync Teamwork, Opportunities, CRM, DocuSign nav links, hides delete button in task editor, shows "EARLY ADOPTER" badge and Welcome Guide link; (7) Admin panel updated with early_adopter role option, project assignment field, and updated permissions reference grid; (8) User creation/edit APIs accept project field for early_adopter role. Onboarding flow: admin creates early_adopter user with assigned project in admin.html, user logs in and is redirected to /welcome for guidelines, then proceeds to task board scoped to their project.

### TASK-RD-004: Mission Control — Document Upload for Work Management
- **Status:** completed
- **Priority:** high
- **Submitted:** 2026-05-29
- **Completed:** 2026-05-29
- **Submitted by:** Jon
- **Description:** Add document upload capability to Mission Control to support Work Management workflows. Users need to attach/upload documents (contracts, specs, reports, etc.) to work items, tasks, or projects within Mission Control. Reference: mission-control/ directory for current architecture.
- **Deliverables:** Document upload feature integrated into Mission Control work management interface
- **Notes:** Implemented 2026-05-29. Server: multipart upload parser, local filesystem storage (mission-control/uploads/), metadata JSON, download/delete endpoints with directory traversal protection. Frontend: Documents tab in task detail panel with drag-and-drop upload zone, file list with icons by type, open/download/delete actions, upload progress bar. Supported formats: PDF, DOCX, XLSX, PPTX, PNG, JPG, CSV, ZIP + more. 25 MB limit. Uploads auto-logged to task timeline. Early adopter role also has access.
