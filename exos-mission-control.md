# Exos Aerospace — Mission Control Task Tracker
_Last updated: 2026-04-01_

---

## 🚨 HIGH CONVICTION — PRIORITY 1
**Organization:** NASA Armstrong Flight Research Center — Flight Opportunities Program
**Type:** IDIQ Provider Contract (FO IDIQ 4 — 80AFRC23R0001)
**Value:** Up to $45M (multi-year IDIQ)
**Stakeholder:** Angela Stinchfield (angela.t.stinchfield@nasa.gov) / Melissa Newell (melissa.newell@nasa.gov) / Program Mgr: Greg Peters
**Urgency:** Follow-up due 2026-04-08 (2 weeks from send)
**Status:** 🟢 Email Sent 2026-03-25 — awaiting response

**CC'd:** nasa-flightopportunities@mail.nasa.gov, Lizi Quinn, Neil Milburn

**Next Actions:**
- [ ] **April 8** — Follow up if no response
- [ ] If response received: schedule call, prep BLK3 capability briefing
- [ ] NOTE: Sent email incorrectly referenced "Space Act Agreement" — it is a DUA. Clarify if raised on call.

**Source:** https://sam.gov/opp/a665d191eef14ab7966484b9d59584d6/view

---

## 🚨 HIGH CONVICTION — PRIORITY 2
**Organization:** NASA MSFC — Teasley RDRE / DUA Activation
**Type:** DUA → Funded Flight Demo Contract
**Value:** TBD
**Stakeholder:** Thomas Teasley — thomas.teasley@nasa.gov (MSFC-ER13)
**Urgency:** ON HOLD — blocked on funding (Series A or OTA must close first)
**Status:** 🔴 On hold — funding dependency

**Key Intel:**
- Exos holds a NASA Data Usage Agreement (DUA) — NOT a Space Act Agreement
- DUA covers: RDRE drawings, models, hot fire test data, design practices, lessons learned (ITAR/EAR controlled)
- Teasley is named NASA POC — he is engaged and aware of Exos
- Cannot proceed with commercial RDRE build without Series A or OTA funding

**Next Actions:**
- [ ] Series A close OR OTA funding → triggers Teasley engagement
- [ ] Draft outreach ready at `drafts/teasley-nasa-outreach.md`

---

## 🚨 HIGH CONVICTION — PRIORITY 2a
**Organization:** USAF AFTC — HVRR Contract FA930025C6022
**Type:** OTA Prototype — RDRE Alternative Development
**Value:** TBD
**Stakeholder:** Matt (primary USAF contact) + Neil Milburn (working with Matt)
**Urgency:** ON HOLD — waiting on Series A direction + Matt's contact details
**Status:** 🔴 On hold

**Key Intel:**
- Kiera Joyner (CO) is NOT the right contact — Matt is
- Neil Milburn is coordinating with Matt
- GFE RDRE delivery at risk — USAF disclosed delays
- OTA path: SpEC/NSTXL or AFWERX — Kiera's office to advise preferred vehicle
- Draft letter ready at `drafts/usaf-ota-solution-letter-v2.md` (needs update for Matt)

**Next Actions:**
- [ ] Jon to provide Matt's full name + contact
- [ ] Series A direction (this AM per Jon 2026-03-31) → unlocks OTA pursuit
- [ ] Neil Milburn to coordinate with Matt

---

## MEDIUM CONVICTION — PRIORITY 3
**Organization:** NASA MSFC — INRODES Program
**Type:** Flight Demonstration Partnership
**Value:** TBD
**Stakeholder:** Thomas Teasley / Ramon Osorio (ramon.j.osorio@nasa.gov)
**Urgency:** ON HOLD — same funding dependency as Priority 2
**Status:** 🔴 On hold

**Draft:** `drafts/msfc-inrodes-outreach.md` (route via Teasley warm intro)

---

## MEDIUM CONVICTION — PRIORITY 4
**Organization:** DoD — RDRE Capability Visibility
**Type:** SAM.gov registration + follow-on RFP watch
**Urgency:** Ongoing
**Status:** 🟡 Pending SAM.gov update

**Next Actions:**
- [ ] Update SAM.gov registration with RDRE capability language (`drafts/sam-gov-rdre-update.md`)
- [ ] Monitor for DoD RDRE follow-on RFP/BAA (prior RFI 2449PS50 closed)
- [ ] RDRE capability statement ready: `drafts/rdre-capability-statement.md`

---

## 🔑 CRITICAL PATH — SERIES A ($10M)

**Status:** 🔴 Direction pending — Jon to advise

**Use of proceeds:**
1. Acquire remaining 82% of Scorpius (exercise ROFR at 2021 basis)
2. Expand RDRE development
3. Build another BLK3 PSRLV

**Why this unlocks everything:**
- Teasley/RDRE engagement (Priority 2)
- HVRR OTA pursuit (Priority 2a)
- INRODES flight demo (Priority 3)
- Scorpius ROFR arbitrage (TRL 9 + lunar heritage at 2021 valuation)

**Investor profile:** Aerospace platform investors, dual-use tech, family office
**Next Actions:**
- [ ] Jon to provide Series A direction
- [ ] Exo to begin investor sourcing once direction confirmed

---

## 📋 ACTIVE CRON SCHEDULE

| Time | Task | Status |
|---|---|---|
| 3:15 AM daily | Nightly security hardening | ✅ Running |
| 4:30 AM daily | File maintenance & lessons learned | ✅ Running |
| 6:30 AM daily | Aerospace opportunity scan | ✅ Running |
| 7:00 AM daily | Solar report (HA/Enphase) | ✅ Running |
| 8:00 PM daily | End-of-day status update | ✅ Running |
| Monday 7 AM | Mission Control weekly review | ✅ Running |
| Wednesday 8 AM | CRM dashboard refresh | ✅ Running |

---

## 🏠 HOME AUTOMATION STATUS

**Enphase Solar:** ✅ Live — 30 microinverters reporting, daily report active
**EG4 Inverters:** ⚠️ RS485 connection not yet established — HDMI breakout board needed (~$8 Amazon)
**Basen Batteries (3x 15.4kWh):** ⚠️ RS485C wired, JK BMS addon installed, protocol mismatch — firmware V1.0.0 may need update or different integration
**Home Assistant:** ✅ 2026.3.4 running on HA Green (192.168.143.166)

---

## 🖥️ EXOMAC INFRASTRUCTURE

**Hardware:** M4 Pro Mac mini, 48GB RAM, macOS Tahoe 26.4
**OpenClaw:** 2026.3.28 — current
**Local LLM:** Qwen3-32B installed via Ollama (20GB, zero cost)
**Email:** ProtonMail Bridge + msmtp configured (jquinnexo@pm.me)
**Telegram:** @Exosaerobot — Exobot Core group setup pending bot member add

---

_Updated by Exo. Next review: Monday 7 AM (automated)._
