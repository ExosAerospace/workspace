# New Employee Onboarding — Company & Mission Control SOP

**Owner:** Lizi Quinn
**Purpose:** A repeatable checklist to bring a new hire into Exos and into Mission Control so they are productive, connected to Exo (our AI COO), and contributing to the mission from week one.
**Run this once per new hire.** Copy the checklist at the bottom into their onboarding task.

---

## Why this matters (the model we're building)
Exos runs on the ExO 3.0 operating model (Salim Ismail). Mission Control is where work is prioritized, assigned, and driven to completion — with Exo scoring what matters most and routing work to the right person. A new hire isn't fully onboarded until Exo knows what they're good at (their Capability Profile) and they know how to drive their own priorities in Mission Control. This SOP gets both done.

---

## Phase 1 — Before Day 1 (accounts & access)
1. **Company email** — confirm their `@exosaero.com` address is created (IT/M365).
2. **Proton intake email** — have them create `firstnamelastname@pm.me` (or note they'll CC the shared intake). This lets them task Exo and log work by email. Team intake address: **exosmc@proton.me**.
3. **Cloudflare WARP access** — Mission Control is only reachable through Cloudflare Zero Trust (CMMC requirement; ExoMac is not on the public Exos site). Add them to the Atomus **exosaero** Cloudflare team so they can install WARP. If we're at the 8-seat limit, request an additional seat from Atomus before their start date.
4. **Export-control note** — Exos is an aerospace company. Brief them: **no ITAR/EAR/CUI material goes into Mission Control or the email intake** — that content lives only in the designated SharePoint folder. Exo has a backup screen that will hold anything flagged, but their judgment is the primary control.

## Phase 2 — Day 1 (Mission Control account)
5. **Create their MC user** — Admin → Users → Add. Set role:
   - **Manager** = full team member (sees all tasks, can assign/edit). Default for staff.
   - **Member** = standard access. Use for contractors or limited scope.
   - Set a temp password and have them reset it on first login (Admin has a **Reset PW** button if they get locked out).
6. **Send them the access + Getting Started email** (Exo has the template — ask Exo to send the standard "Welcome to Mission Control" email, personalized). It includes the URL, how to favorite it, how to log in, and how the whole system works at a "for dummies" level.
7. **Walk them to the Help / Getting Started page** in Mission Control on their first login.

## Phase 3 — First Week (make them productive & known)
8. **Assign their Capability Survey** — ask Exo to create their Capability Survey task (or copy the standard one) assigned to them. This is how Exo learns their strengths and starts routing the right work to them. **This is required onboarding, not optional.**
9. **Show them how to drive their own priorities:**
   - **My Tasks** filter = their work. **Group** = shared team work.
   - They can add tasks, move them (Blocked → In Progress → Done), and — importantly — **flag what THEY think is a priority.** Exo's Mission Score is a recommendation; their on-the-ground judgment matters and feeds back into it.
   - **@Exobot by email** — they can email exosmc@proton.me to create/advance tasks; approvals route to their own Decisions matrix, not Jon's.
10. **Seed 2-3 real starter tasks** so they're contributing immediately, ideally in their strength area.
11. **Point them at Decisions** — anything needing a yes/no from them shows up in their Decisions inbox.

## Phase 4 — Close the loop
12. **Confirm the survey is done** — once submitted, Exo builds their Capability Profile into the auto-assignment matrix. Tell Exo "capability profile complete for <name>" so it activates fit-based routing for them.
13. **Two-week check-in** — confirm they're logging in, using My Tasks, and not blocked on access. Report any friction to Jon/Exo so we improve this SOP (recursive improvement).

## Offboarding (when someone leaves)
- Deactivate their Mission Control user (Admin → Users).
- Remove them from the Cloudflare **exosaero** team (revokes WARP access).
- Reassign their open tasks (ask Exo to surface them by owner).

---

## One-page checklist (copy into each hire's onboarding task)
- [ ] `@exosaero.com` email confirmed
- [ ] Proton intake email created / intake address shared
- [ ] Added to Cloudflare **exosaero** team (WARP installed & tested)
- [ ] Export-control briefing given (no ITAR/EAR/CUI in MC)
- [ ] Mission Control user created (role set, temp password)
- [ ] Welcome / Getting Started email sent (via Exo)
- [ ] Getting Started page walked through
- [ ] Capability Survey task assigned
- [ ] Shown My Tasks / Group / add & move tasks / flag priorities
- [ ] Shown @Exobot email + Decisions inbox
- [ ] 2-3 starter tasks assigned
- [ ] Capability Survey submitted → Exo notified to build profile
- [ ] Two-week check-in completed

_Maintained with Exo. Suggest improvements any time — this SOP is versioned and updated as the process gets better._
