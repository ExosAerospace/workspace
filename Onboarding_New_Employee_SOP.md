# New-Employee Onboarding — Integrated SOP (Company/HR + Mission Control)

**Owner:** Lizi Quinn
**Purpose:** One repeatable flow that fuses the BambooHR/HR onboarding with the Mission Control & systems enablement, so a new hire is processed once — not through two parallel lists.
**Run once per hire.** Adding the hire to BambooHR is the trigger; the Bamboo new-hire watcher then auto-creates their MC onboarding task and notifies Lizi.

---

## Operating model
- **Phase A (HR / BambooHR)** runs in Lizi's Bamboo checklist as usual.
- **Handoff:** adding the person to BambooHR IS the trigger. The `bamboo_newhire_watcher` (daily) detects the new employee, auto-creates their MC onboarding task (Phases B–E), and emails Lizi. Fallback: tell Exo "new hire: <name>" to spin it up on the spot.
- **Phases B–E (systems & Mission Control)** are owned by Exo/Lizi off that auto-created task. A new hire isn't fully onboarded until Exo knows their strengths (Capability Profile) and they can drive their own priorities in MC.

---

## PHASE A — Offer accepted → HR setup (BambooHR)
**Employees**
1. Hiring officer emails the Hiring Manager with salary terms.
2. Hiring Manager adds the employee to BambooHR and sends the New Hire package: Employee Handbook, Personal Information Sheet, ACH authorization, W-4, I-9, EXOS Computer Policy.
3. Employee completes their BambooHR info and signs the documents.
4. Hiring Manager emails Tech@exosaero.com to create the @exosaero.com email.
5. Hiring Manager sends W-4, I-9, ACH to payroll (BBSNV — paula.lessnick@bbsnv.com) via encrypted Preveil, with salary terms.

**Contractors** (more fluid)
1. Hiring officer emails Hiring Manager with terms (often a PO).
2. Hiring Manager adds the contractor to BambooHR and sends: Consulting Agreement, ACH Authorization, I-9, W-9.
3. Contractor completes BambooHR info and signs.
4. If paid via BBSNV (preferred Vendor ACH): send W-9, I-9, ACH to paula.lessnick@bbsnv.com. If paid on a PO through Kyle: send terms/PO to Kyle with the ACH authorization.

> **▶ HANDOFF** — once the BambooHR record exists and the @exosaero.com email is requested, the watcher (or Lizi) starts Phase B.

## PHASE B — Before Day 1 (systems & access)
- @exosaero.com email confirmed live (IT/M365).
- Proton intake email created (firstnamelastname@pm.me) or shared intake noted — team intake exosmc@proton.me.
- Cloudflare One Client access — MC is only reachable through Cloudflare Zero Trust (CMMC). Add to Atomus **exosaero** team; request a seat if at the limit.
- Export-control briefing — no ITAR/EAR/CUI in MC or intake; that content lives only in SharePoint (GCC High). Exo has a backup screen; their judgment is the primary control.

## PHASE C — Day 1 (Mission Control account)
- Create MC user (Admin → Users → Add). Role: **Manager** = full team member (default staff); **Member** = standard/limited (contractors). Temp password, reset on first login.
- Send the "Welcome to Mission Control" Getting Started email (ask Exo for the standard, personalized template).
- Walk them to the Help / Getting Started page on first login.

## PHASE D — First week (make them productive & known)
- Assign their **Capability Survey** (ask Exo). Required — it's how Exo learns strengths and routes work.
- Show driving their own priorities: My Tasks = their work; Group = shared; add/move tasks (Blocked → In Progress → Done); flag priorities (feeds Exo's Mission Score).
- Show @Exobot by email (exosmc@proton.me — approvals route to their OWN Decisions matrix, not Jon's) + their Decisions inbox.
- Seed 2–3 starter tasks, ideally in their strength area.

## PHASE E — Close the loop
- Confirm the Capability Survey is submitted; tell Exo "capability profile complete for <name>" to activate fit-based routing.
- Two-week check-in — logging in, using My Tasks, not blocked on access. Report friction to improve this SOP.

## Offboarding (when someone leaves)
- HR: process departure in BambooHR; final pay / ACH close-out via BBSNV/Kyle as applicable.
- Systems: deactivate MC user (Admin → Users); remove from Cloudflare **exosaero** team (revokes access); ask Exo to surface and reassign open tasks.

---

## One-page checklist (auto-copied into each hire's onboarding task by the watcher)
**Phase A — HR / BambooHR**
- [ ] Salary terms / PO received from hiring officer
- [ ] Added to BambooHR + New Hire package sent (employee vs contractor)
- [ ] New hire completed BambooHR info + signed documents
- [ ] @exosaero.com email requested via Tech@exosaero.com
- [ ] Payroll/tax forms to BBSNV (Preveil) — or PO to Kyle (contractor)

**▶ Handoff — watcher opens the MC onboarding task + emails Lizi**

**Phases B–E — Systems & Mission Control**
- [ ] @exosaero.com email confirmed live
- [ ] Proton intake email created / intake address shared
- [ ] Added to Cloudflare **exosaero** team (Cloudflare One Client installed & tested)
- [ ] Export-control briefing given (no ITAR/EAR/CUI in MC)
- [ ] Mission Control user created (role set, temp password)
- [ ] Welcome / Getting Started email sent (via Exo)
- [ ] Getting Started page walked through
- [ ] Capability Survey task assigned
- [ ] Shown My Tasks / Group / add & move / flag priorities
- [ ] Shown @Exobot email + Decisions inbox
- [ ] 2–3 starter tasks assigned
- [ ] Capability Survey submitted → Exo notified to build profile
- [ ] Two-week check-in completed

_Automation: `scripts/bamboo_newhire_watcher.py` (launchd `com.exos.bamboo-newhire-watcher`, daily 08:30) detects new BambooHR employees, auto-creates the MC onboarding task, and emails Lizi. HR steps carried from the 2022 "Exos-US Onboarding Process" (status: pending review) — confirm BBSNV/Preveil and package contents are still current. Maintained with Exo; versioned._
