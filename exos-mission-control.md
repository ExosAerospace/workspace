# Exos Aerospace — Mission Control
_Last updated: 2026-04-01_
_Owner: Exo | Review: Daily 4:30 AM + Monday 7 AM_

---

## HOW THIS WORKS

Each task has:
- **Owner:** `[EXO]` = Exo executes | `[JON]` = Jon executes | `[ASSIGN:name]` = delegated
- **Status:** 🔴 Blocked | 🟡 Ready | 🔵 In Progress | ✅ Done | ⏸ On Hold
- **Due date** and **trigger** (what unlocks the next step)

To add a task: tell Exo and it gets added immediately.
To execute a task: tell Exo "do [task name]" and it runs.

---

## 🔴 BLOCKED — Waiting on Input

### B-001 | Series A Direction
**Owner:** [JON]
**Due:** ASAP — unlocks B-002, B-003, B-004
**Blocked on:** Jon's direction (promised 2026-03-31 AM)
**Details:** $10M raise — acquire Scorpius ROFR, expand RDRE, build BLK3
**When unblocked:** Exo begins investor sourcing immediately

### B-002 | HVRR OTA Letter to Matt
**Owner:** [EXO] once unblocked
**Due:** TBD
**Blocked on:** (1) Matt's full name + contact, (2) Series A direction
**Details:** USAF FA930025C6022 — GFE RDRE delivery at risk. OTA path via SpEC/NSTXL. Neil Milburn coordinating with Matt.
**Draft ready:** `drafts/usaf-ota-solution-letter-v2.md` (needs correct addressee)

### B-003 | Teasley Outreach (NASA MSFC RDRE)
**Owner:** [EXO] once unblocked
**Due:** TBD
**Blocked on:** Funding (Series A or OTA must close first)
**Details:** DUA active, Teasley engaged. Cannot proceed without commercial build funding.
**Draft ready:** `drafts/teasley-nasa-outreach.md`

### B-004 | INRODES Flight Demo Outreach
**Owner:** [EXO] once unblocked
**Blocked on:** Same as B-003 — funding first
**Details:** Route via Teasley warm intro after B-003 is sent

### B-005 | Exobot Core Telegram Group
**Owner:** [JON]
**Blocked on:** Jon adds @Exosaerobot as member to Exobot Core group
**Action:** Open group → Add Members → search @Exosaerobot → Add

---

## 🟡 READY — Can Be Done Now

### R-001 | NASA FO Follow-Up Email
**Owner:** [EXO]
**Due:** 2026-04-08
**Details:** Follow up with Angela Stinchfield + Melissa Newell if no response to 2026-03-25 outreach
**Action:** Exo drafts and sends on April 8 if no response received

### R-002 | SAM.gov RDRE Capability Update
**Owner:** [JON]
**Due:** This week
**Details:** Log into SAM.gov, update Exos capability narrative with RDRE language
**Instructions:** `drafts/sam-gov-rdre-update.md`

### R-003 | Matt Contact Info
**Owner:** [JON]
**Due:** ASAP — unlocks B-002
**Action:** Send Exo Matt's full name and email/phone

### R-004 | Proton Bridge Auto-Start
**Owner:** [EXO]
**Due:** Today
**Details:** Configure Proton Mail Bridge to launch at login so email works after reboots

### R-005 | Qwen3 OpenClaw Integration
**Owner:** [EXO]
**Due:** Today
**Details:** Configure OpenClaw to route non-research cron jobs to local Qwen3-32B to reduce Anthropic costs

---

## 🔵 IN PROGRESS

### P-001 | ISC ARCA ETV Presentation
**Owner:** [JON]
**Status:** Jon editing final version with embedded video
**Details:** Branded FINAL2 + supermod_vtvl.mp4 delivered to ProtonMail. Jon inserting video manually in PowerPoint.

### P-002 | Basen Battery RS485 Connection
**Owner:** [JON + EXO]
**Status:** Wired correctly, JK BMS addon installed, protocol mismatch being resolved
**Next:** Try dbus-serialbattery addon OR firmware update on batteries
**Blocker:** JK BMS firmware V1.0.0 — may need RS485 address/baud confirmation

### P-003 | EG4 Inverter Modbus
**Owner:** [JON]
**Status:** Waiting on HDMI breakout board for RS485C port connection
**Next:** Order HDMI male breakout board (~$8 Amazon) → wire Pin 1 (A+) and Pin 4 (B-)

---

## ✅ COMPLETED

### C-001 | NASA FO Outreach Email — Sent 2026-03-25
Angela Stinchfield + Melissa Newell. CC: Lizi Quinn, Neil Milburn.
Solicitation 80AFRC23R0001 — evergreen, open now.
NOTE: Email incorrectly referenced SAA — clarify on call if raised.

### C-002 | ExoMac Security Setup
Nightly security script running 3:15 AM. Homebrew updates, OpenClaw audit, session cleanup, firewall check.

### C-003 | ProtonMail + msmtp Email Configured
jquinnexo@pm.me outbound working. Bridge on port 1025.

### C-004 | Qwen3-32B Local Model Installed
20GB model running via Ollama on ExoMac. Zero cost, fully local.

### C-005 | Home Assistant Solar Live
Enphase Envoy integrated. 30 microinverters reporting. Daily 7 AM solar report active.

### C-006 | HA Updated to 2026.3.4

### C-007 | ISC Branded Presentation Delivered
FINAL2 + video MP4 sent to ProtonMail for manual edit.

---

## 📋 CRON SCHEDULE

| Time | Task | Status |
|---|---|---|
| 3:15 AM | Nightly security | ✅ |
| 4:30 AM | File maintenance + lessons learned | ✅ |
| 6:30 AM | Aerospace opportunity scan | ✅ |
| 7:00 AM | Solar report | ✅ |
| 8:00 PM | End-of-day status | ✅ |
| Mon 7 AM | Mission Control weekly review | ✅ |
| Wed 8 AM | CRM dashboard refresh | ✅ |

---

## 📌 KEY CONTACTS

| Name | Role | Contact |
|---|---|---|
| Angela Stinchfield | NASA FO Contracting | angela.t.stinchfield@nasa.gov |
| Melissa Newell | NASA FO Contract Specialist | melissa.newell@nasa.gov |
| Thomas Teasley | NASA MSFC RDRE Lead | thomas.teasley@nasa.gov |
| Ramon Osorio | NASA MSFC Media/Comms | ramon.j.osorio@nasa.gov |
| Kiera Joyner | USAF AFTC CO (FA930025C6022) | kiera.joyner@us.af.mil |
| Cody Gallagher | USAF AFTC CS | cody.gallagher.1@us.af.mil |
| Neil Milburn | Exos (HVRR coordination) | — |
| Matt | USAF primary contact (HVRR) | TBD — Jon to provide |

---
_To add a task, tell Exo. To execute a task, say "Exo, do [task ID or name]."_
