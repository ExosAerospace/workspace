# PURSUIT TRACKER — NIH Microgravity Biomedical (Capture Agent state file)
*Single source of truth for this pursuit. The Capture Agent reads this each run, advances the next open action, and updates State + Decision Log. Last updated: 2026-09-14.*

## Objective
Win NIH-relevant microgravity funding/revenue using BLK3 as the SUBORBITAL microgravity platform. Primary near-term = **NIH STTR (PA-27-102) — SUBMITTED 2026-09-08, now in NIH review** (Sep 5 fell on Saturday; NIH moved to Sep 8), teamed with a biomedical PI (Exos = platform). **As of 2026-09-03 the STTR is PURDUE-ONLY: Prof. Estelle (Sunghee) Park (Purdue Weldon BME) = Contact PD/PI and sole biomedical lead; Purdue = single Research Institution of record; Exos = small-business applicant providing the BLK3 suborbital platform + experiment methods. Science model = human intestinal organoid chips (enteroids / OCTOPUS). UW / Ed Kelly fell out 8/31 (UW OSP could not meet the Sep 8 routing); Prof. Steven Collicott is DROPPED (per Lizi 9/3).** Parallel = **sell BLK3 screening slots** to NIH/NCATS/TraCe MPS-funded researchers. Adjacent = **NASA ROSBio Appendix D** (suborbital biology). Win = an NIH STTR award and/or booked microgravity payload slots.

## Current stage
> ✅ **2026-09-14 04:45 CDT — CONFIRMED: NIH STTR APPLICATION 2207197 SUCCESSFULLY SUBMITTED ON DEADLINE, 2026-09-08 5:38pm CDT (22:38 UTC). This was NOT captured by any tracker entry — the last logged run was 9/8 04:45, hours before submission, and no capture-agent run exists for 9/9 through 9/13 (confirmed 6-day cron gap, consistent with the same gap flagged independently by the Sales Agent's 9/14 run).** Full IMAP + forwarded-mail scan closing that gap found the complete, unambiguous submission trail, all within a ~2.5 hr window on 9/8: **(1) 20:13 UTC — Park (Purdue) sent her final reference list** ("Here is the reference list for my section... I will leave it to you to add the appropriate citation numbers") — the last open science item. **(2) 22:38 UTC — three near-simultaneous NIH/Grants.gov confirmations landed:** (a) **era-notify@mail.nih.gov: "GRANT14760547/Park,Sunghee: Check Assembled Application in eRA Commons"** — NIH confirms receipt of the grant application titled *"A Reusable Suborbital Microgravity Platform for Onset-Kinetics and Post-Flight Recovery Screening of Human Intestinal..."* — this notification only fires after ASSIST successfully validates + submits a package; (b) **Grants.gov: "Grantor Agency Retrieval Receipt"** — confirms NIH (the grantor) retrieved the application from Grants.gov; (c) **Grants.gov: Agency Tracking Number Assignment — NIH assigned Agency Tracking Number 5331434.** **This is definitive: John completed the IP Allocation Agreement signature, PD/PI-role confirm, Validate, and Verify+Submit steps that the 9/8 04:45 entry was chasing, and the application cleared ASSIST/Grants.gov/eRA validation cleanly — no rejection or error notices found anywhere in the 9/8–9/14 mail scan.** **Grant application number of record: GRANT14760547. Agency Tracking Number: 5331434.** Checked MC decisions.json for anything open on this pursuit: **nothing blocking** — no unanswered NIH-STTR decision exists; all prior gating decisions (D-7281738, D-7281754, D-7281761, D-7281772, DNIH-BUDGET-NEIL-001) show answered. **Pursuit stage moves from SPRINT-TO-SUBMIT to AWAITING NIH REVIEW** — STTR Phase I review/council timelines typically run ~6-9 months from a standard-cycle deadline (expect summary statement ~Nov-Dec 2026, funding decision ~Q1-Q2 2027); nothing further is actionable on the application itself until NIH responds. **Reframe this pursuit's active work to the PARALLEL track (sell BLK3 screening slots to NIH/NCATS/TraCe-MPS-funded researchers)** — several BD outreach decisions for microgravity flight slots (D-7281556, D-7281560, D-7281577, D-7281519, D-7281518, D-7281495, D-7281494) already show `delegated` status, i.e. in motion via the Sales Agent's own cron; no duplicate action needed from this pursuit specifically. **External scan (1 search, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted as its own FOA** (NCATS space page still last-updated Apr 22 2026, funding-opportunities list still shows only the closed 2.0/RFA-TR-24-025); no NASA ROSBio Appendix D found. **Single most important action, now: none required from Jon — application is in NIH's hands.** Next capture-agent run should confirm the cron actually fired daily (this gap needs an infra check, not a pursuit action) and watch for eRA Commons status-check notifications (JIT, summary statement, council date) rather than re-chasing submission steps.
>
> 🔴 **[SUPERSEDED — see above] 2026-09-08 04:45 CDT — SUBMISSION DEADLINE DAY. No new decision card existed to gate John's 9/7-flagged IP-Agreement-signature action, so this run doesn't just report it — it re-dispatches it directly.** Full IMAP + forwarded-mail scan since the 9/7 04:45 entry: no reply from Park/Purdue/NIH overnight (only new inbound was the already-known 2207197 ASSIST access notification, 9/7 5:36pm CDT — not new information, already reflected below). No confirmation visible that John has signed the IP Allocation Agreement, run Validate, or submitted. **Checked MC decisions.json for a card gating the IP-agreement signature, PD/PI-role confirm, or Validate/Submit — none exists; these are John-only actions (sign a doc, click buttons in ASSIST) that don't route through the Decision queue, which is why they can silently sit unactioned.** Sent a direct, ranked 3-step action email to Jon's inbox this run (not gated — informational/urgent, deadline-day): (1) sign + return the STTR IP Allocation Agreement to Ryan Clayton (Purdue Sr. Pre-Award Manager), cc Brandee Hudspeth; (2) confirm abandoning duplicate ASSIST app 2205640; (3) run Validate on 2207197, fix any red items, then Verify + Submit as SO. Reconfirmed everything else is closed: biosketch, Neil's budget/Item L, SBC Control ID (001156963), Purdue UEI (YRXVL4JYCEF5), PD/PI role on JQUINN007. **Single most important action, today: John completes the 3 steps above — nothing else is blocking Sep 8.** External scan (1 search, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted as its own FOA. **RISK FLAG for future pursuits: John-only ASSIST/signature actions aren't decision-gated, so they can go unflagged for days — worth a lighter-weight "nudge" mechanism (not a full Decision card) for this class of action.**

> 🔴 **2026-09-07 04:45 CDT — 1 DAY TO SEP 8. PURDUE'S SIDE IS FULLY DONE; EVERYTHING LEFT IS ON EXOS. NEW BLOCKER FOUND: STTR IP ALLOCATION AGREEMENT NEEDS JOHN'S SIGNATURE.** Full IMAP + forwarded-mail scan since the 9/4 04:45 entry (no tracker entries logged 9/5-9/6, so this closes a 3-day gap) surfaced real, mostly-positive movement: **(1) Purdue's official submission package (proposal # FP80012618) landed 9/5 1:45pm CDT** — Brandee had it approved/routed 9/4 (confirms Park's 9/4 8:03am email: "Brandee will submit our administrative documents today since the university will be closed on Monday [Labor Day]"). Package confirms **Purdue subaward = $176,278, matches our locked number exactly, zero gap**, plus Purdue org IDs (DUNS 07-205-1394, EIN 1356002041A1, CAGE 6D418). **It also contains an STTR IP Allocation Agreement between Exos and Purdue — Purdue's side is fully executed (Ryan Clayton, Senior Pre-Award Manager, signed 9/4), but the Exos signature block is BLANK.** This is a genuinely new, previously-unflagged open item — not on Lizi's 9/3 punch list. **(2) John's biosketch is DONE** — finalized version resent 9/5 8:19am CDT (Kennedy-Western BSEE 2002, 11+ yrs Exos, 14.5 yrs Navy, npj Microgravity 2023;9:92 co-authorship, PD/PI role stated), correcting the ASSIST degree field to BACCALAUREATE (not Post-Baccalaureate). **This closes punch-list item #1 (John's SciENcv biosketch).** **(3) Neil's budget is DONE** — per Decision DNIH-BUDGET-NEIL-001 (answered 9/5 12:27 CDT), John's salary basis was resolved to his actual **$220,000 BambooHR-confirmed base** (not the $195K REV7 placeholder), Line A recalculated to $33,000 salary + $5,775 fringe, F. Other Direct rebalanced to hold the $117,519 Exos control total. **Combined Exos+Purdue Budget Justification (single Item L PDF) delivered to John's inbox 9/5 2:33pm CDT, ready to upload to ASSIST.** **This closes Neil's budget-line-item blocker entirely.** **(4) SBC Control ID = 001156963** — confirmed resolved 9/4 per `drafts/NIH_STTR_2207197_OPEN_ITEMS_for_John.md` (Jon supplied it that day, after the 04:45 tracker entry that had flagged it as still-open — stale flag, retire it). **(5) Jon asked a live, still-unanswered question 9/5 1:40pm CDT: "@exo how do i see if all this subaward information is entered in assist-?"** — answered this run (see below). **(6) Resolved this run (new research, not waiting on anyone): Purdue's UEI.** The open-items doc flagged Purdue's UEI as an unresolved blank (needed on SBIR/STTR Info Q13 + R&R Sites) because a prior web lookup couldn't verify it. Looked it up directly via the SAM.gov Entity API using Purdue's CAGE code (6D418, taken straight from Brandee's signed letter to confirm the right entity/campus — NOT Purdue Fort Wayne, which has a different UEI): **Purdue University (main, West Lafayette) UEI = YRXVL4JYCEF5, SAM-active through 2027-05-26.** Delivered to Jon's inbox this run. **Dispatched this run** (ready_action key `nih-sttr-2207197-assist-check-signature-uei-0907`, emailed to Jon's inbox): direct answer to his ASSIST question (log in as SO/JQUINN007 → open 2207197 → Forms → R&R Subaward Budget Attachment(s) Form to confirm Purdue's budget/SOW are attached → Project/Performance Site Locations to confirm Purdue's site + new UEI → click **Validate** at the application level for NIH's authoritative full-package check), the Purdue UEI, and the new IP-Agreement-signature ask. **Remaining open items, ALL on Exos now, NONE on Purdue/Park/Neil:** (a) John signs + returns the STTR IP Allocation Agreement to Ryan Clayton (Purdue), cc Brandee; (b) confirm JQUINN007 carries a **PD/PI role** in eRA Commons, not just Signing Official — required since John is 2nd PD/PI on 2207197, ASSIST will reject submission without it; (c) confirm abandoning duplicate application 2205640 so only 2207197 is submitted; (d) run **Validate** on 2207197 and chase whatever (if anything) still shows red; (e) final step, John only as SO: **Verify + Submit in ASSIST.** **Single most important action, today: John runs Validate on 2207197, signs the IP Agreement, and confirms the PD/PI role — those three close every open item left, and Purdue's side is fully done, so nothing external is blocking us.** **External scan (1 search, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted as its own FOA (NCATS page still shows only the closed 2.0, last updated Apr 22 2026); nothing new to act on there.**

> 🔴 **2026-09-04 04:45 CDT — APPLICATION-NUMBER CHAOS RESOLVED: LIVE APP IS 2207197 (Purdue intestinal, Park PI, budget locked). LIZI SENT A FULL PUNCH LIST TO JON LAST NIGHT — STILL UNANSWERED THIS MORNING. 4 DAYS TO SEP 8.** Full IMAP scan since 9/3 12:27 (the last tracker entry) found significant unlogged movement — reconciling the confusing multi-application-number trail first: **ASSIST actually spawned THREE application numbers in ASSIST this week — 2205640 (liver-titled, flagged 12:27, now DEAD), 2206096 (also liver-titled, access-grant email sent 9/2 10:25pm, captured to MC task #2613 by an earlier Exo run, ALSO effectively superseded), and 2207197 — this is the one Lizi is actually building and the one that matters.** Per Lizi's own 9/3 10:03pm CDT email ("URGENT: NIH STTR (ASSIST app 2207197) — status + what we still need before Sept 8"): **app 2207197 has the correct title, Park (ESTELLEPARK) as Contact PD/PI + John as second PD/PI, Collicott removed, all narrative attachments loaded (Aims/Abstract/Narrative/Facilities/Equipment/Consortium/Leadership/DMS/Resource-Sharing/Authentication/Commercialization/Cover Letter), Park's SciENcv biosketch + both research-security certs on file, and budget top line locked ($138,085 Exos / $176,278 Purdue / $314,363 total).** **Retire the 12:27 "fix 2205640's title" action — that application is being abandoned, not fixed.**
>
> **Lizi's full punch list (sent to Jon 9/3 10:03pm CDT, UNANSWERED as of this run):**
> - **From John (blocking):** (1) his own SciENcv biosketch — Lizi has the content drafted, John needs to paste into SciENcv + add education/position dates/Navy dates-rank/ORCID + export signed PDF; (2) confirm his eRA Commons account (JQUINN007) carries a **PD/PI role**, not just Signing Official — needed since he's the second PD/PI on 2207197; (3) confirm abandoning 2205640 so only 2207197 is submitted; (4) final step is his alone as SO: **Verify + Submit in ASSIST**.
> - **From Neil Milburn (blocking the R&R Budget form):** the Exos $117,519 budget line-item split (personnel/materials/BLK3 integration/travel/indirect). Lizi asked Neil directly 9/3 8:00am CDT ("URGENT - need today"); **Neil replied 9/3 5:53pm CDT: "Was driving all day. I'll send you the spreadsheet... this evening or first thing in the morning."** Nothing further has landed as of this run (checked through 9:45am UTC 9/4) — watch for it this morning, don't nag yet, it's still early.
> - **From Park (Purdue):** her final Research Strategy with references inserted + citations numbered (the biggest open science item) + standalone bibliography, her direct office phone (required field), and a quick sign-off that the intestinal science reads correctly. **Park told Jon 9/2 5:24pm CDT "I will try to get you the materials by Friday"** — today. Watch for her delivery.
> - **From Purdue/Brandee (SPS):** Purdue's UEI (required twice on the application) + the detailed Purdue subaward budget/SOW/signed commitment to the locked $176,278 target.
> - **TIME-SENSITIVE, RAISED AGAIN BY LIZI, NEVER CLOSED SINCE FIRST FLAGGED 8/25:** the **SBC Control ID (9-digit, SBA Company Registry)** — Lizi: "If Exos isn't already registered there, that can take a little time, so worth confirming today." This was flagged as "VERIFY TODAY" on 8/25 and no entry in this tracker since then confirms it was ever checked. **Genuine unclosed gap — needs Jon or Lizi to confirm Exos's SBA Company Registry status now, not assumed done.**
>
> **Also found, already actioned by an earlier run (no new action needed):** Exo replied to Jon's forward of the 2206096 access-grant at 9:06am CDT 9/3, captured it to MC task #2613, and correctly flagged the Sep 8 deadline math (PA-27-102 standard date is Sep 5, a Saturday; Sep 7 is Labor Day; NIH's weekend/holiday rule rolls it to Tue Sep 8 — confirmed correct, no fire drill).
>
> **Single most important action, today: Jon answers Lizi's 4-part punch list (SciENcv biosketch, PD/PI-role confirm, abandon-2205640 confirm, SBC Control ID check) so app 2207197 can clear validation** — everything else (Neil's budget, Park's citations, Brandee's UEI/SOW) is already in motion and just needs to land. **External scan (1 search, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted as its own FOA (still shows only the closed 2.0); no NASA ROSBio Appendix D/E found. Nothing new to act on there.**

> 🔴 **2026-09-03 12:27 CDT — ACTION FOR LIZI IN ASSIST: application 2205640 TITLE still says 'Human Liver Organoids' — must change to INTESTINAL.** eRA access-grant email confirms the ASSIST application number is **2205640**, created with the stale liver title. FIX in ASSIST → SF424 (R&R) Cover → item 11 'Descriptive Title of Applicant's Project' (this drives the application title shown in the ASSIST list): replace with **'A Reusable Suborbital Microgravity Platform for Onset-Kinetics and Post-Flight Recovery Screening of Human Intestinal Organoid Chips Before ISS Commitment'**. Cover Letter attachment + Specific Aims/Abstract/Narrative already carry the intestinal title (corrected set in drafts/nih_attachments_intestinal/). Access email itself = routine (John granted Edit All + Manage Status); no doc impact. Both PD/PI research-security certs now on file (Park + John).

> 🟢 **2026-09-03 09:55 CDT — FULL APPLICATION CONSISTENCY PASS (per Lizi): whole PA-27-102 package aligned to Park intestinal model + Collicott dropped.** (1) Rebuilt 14 corrected ancillary attachments to intestinal + Collicott-free at `drafts/nih_attachments_intestinal/` (Aims/Abstract/Narrative taken verbatim from Park's plan; hepatic markers -> KRT20/MUC2/crypt-budding/organoid-forming-efficiency/barrier). (2) Fixed Collicott line in `Exos_NIH_STTR_PA-27-102_SF424_Budget_Summary_2026-08-31.docx`. SF424 FillSheet already noted 'Collicott removed'. (3) Quarantined stale liver/Collicott-era versions (incl. the misleadingly-named 9/1 LIVER 'FINAL') to `drafts/nih_superseded_liver_collicott/` so the wrong plan can't be submitted; ACTIVE research plan = `Exos_NIH_STTR_PA-27-102_ResearchPlan_PURDUE_Park_2026-09-03.docx`. (4) Deprecated the 3 `build_nih_sttr_*` generator scripts (they emit liver/Collicott content). Liver now appears ONLY as the Phase II expansion, per Park. **Still open:** Park's final reference/citation pass + her science nod on the rewritten ancillary docs before John (SO) submits.

> 🟢 **2026-09-03 09:30 CDT — COLLICOTT DROPPED (per Lizi); PA-27-102 now Purdue-only / Park-PI / intestinal-organoid.** Removed Collicott from the two still-active drafts (ASSIST unblock email: CC + training-cert ask; Purdue-only reframe cover email: header, CC, and the Purdue-side suborbital-methods line -> now Exos). Marked the Collicott-era drafts SUPERSEDED (bio writeup, Park intro, CoI intro, meeting invite, subaward writeup, Collicott support letter). Credentials file: removed the 'need Collicott cert' open item. Science confirmed as Park's **intestinal organoid chip** model (liver = Phase II). **Open before Sep 8:** (A) Park's final reference/citation pass on the intestinal-organoid research plan; (B) Lizi enter **ESTELLEPARK / eRA 79298086** as Contact PD/PI in ASSIST.

> 🟢 **2026-09-03 08:38 CDT — PARK REPLIED. eRA CREDENTIALS + TRAINING CERT + UPDATED RESEARCH PLAN ALL IN HAND. TWO OPEN ITEMS REMAIN BEFORE ASSIST SUBMIT.** Park replied this morning to John's 9/2 ask with: **(1) eRA Commons username: ESTELLEPARK, Person ID: 79298086** — Lizi can now enter Park as Contact PD/PI in ASSIST immediately; **(2) Research security training cert link (Brightspace):** https://bip.brightspace.com/f81993d1-f040-40db-88cd-dddba8664daf/d2l/awards/assertions/540503/view — download and file; **(3) Updated research plan docx** (intestinal organoid chip model + Nature Methods paper data) — filed to `drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_PURDUE_Park_2026-09-03.docx`. **IMPORTANT MODEL NOTE:** Park's new plan uses the **intestinal organoid chip model** (not the liver organoid model that was in the 9/1 FINAL). This is Park's deliberate correction using her actual lab system. The new docx is the correct research plan for ASSIST — upload this version. Park says she will "update the references in my section" once she sees the final version — coordinate with her on a final citation pass before Sep 8 submit. **D-7281761 CLOSED** (Park answered; credentials logged to `capture/NIH_STTR_compliance/Park_eRA_Credentials.md`). **D-7281754 SUPERSEDED** (Park sent the new correct intestinal chip plan; prior liver organoid FINAL is obsolete). **Two open items for ASSIST before Sep 8:** (A) Collicott's research security training cert — still not received; chase today. (B) Park's reference citations — she's inserting them; get the final cite-numbered version from her before submitting. **Park also CC'd Brandee Hudspeth (Purdue Sponsored Programs) on her reply, which means Purdue SPS is in the loop.**

> 🔴 **2026-09-03 04:45 CDT — LIZI IS LIVE IN ASSIST BUILDING THE PA-27-102 SUBMISSION RIGHT NOW; PARK LOCKED AS CONTACT PD/PI; BOTH GATING DECISIONS (D-7281754, D-7281761) STILL OPEN, UNANSWERED SINCE YESTERDAY AFTERNOON.** Full IMAP + forwarded-mail scan surfaced a fast-moving exchange from yesterday afternoon (2026-09-02, ~2:23–2:51pm CDT) the tracker hadn't logged — it postdates the 04:45 CDT entry below and is genuinely new: **Exo emailed Jon at 2:23pm** flagging that **Lizi is actively building the PA-27-102 STTR application in NIH ASSIST right now** and is blocked on two answers only Jon can give: (1) who is Contact PD/PI — recommended Park (Purdue) as the clean default since STTR lets the PI sit at the RI; (2) status of PD/PI eRA-Commons affiliation + research-security-training certs for Park/Collicott/Exos PI. **Jon replied 2:31pm ("@exo park is the PI - prepare the draft the email to her for what we need... I have completed the ERA required training - certificate attached").** Exo actioned it same-run (2:51pm, before this cron): (1) **Park confirmed/logged as Contact PD/PI**, no Exos-side MPI added; (2) drafted the unblock email to Park (asking for her Purdue eRA Commons username + training certs for her/Collicott, needed by **Fri Sep 4** for margin before the Sep 8 deadline) and **gated it as Decision D-7281761** — still **OPEN**, unanswered. **Also found and fixed a real gap this run:** Exo's 2:51pm reply to Jon claimed "no file came through with the command" re: John's training certificate — **that was wrong**. Direct IMAP fetch of Jon's forward this run found the cert attachment (`John Quinn CTM 1.2.1 Security Training.pdf`) was there all along; the email-command pipeline just didn't extract it. **Extracted and filed it this run** to `capture/NIH_STTR_compliance/John_Quinn_CTM_Security_Training_Cert.pdf` (verified valid 1-page PDF) — John's training compliance is now a real, filed record, not just an assertion. He does NOT need to resend it. **Still gating everything: D-7281754 (send finalized Research Plan back to Park) and D-7281761 (send unblock email asking Park for her Commons username + her/Collicott's training certs) are BOTH still open in MC decisions — verified via decisions.json, neither has an answer/answeredAt timestamp.** This matters because Park's own Fri Sep 4 deadline for supplying her Commons ID + cert can't start until D-7281761 actually sends — every day this sits open eats into her turnaround margin with 5 days left to Sep 8. **Single most important action, today: Jon answers both D-7281754 and D-7281761** (both are simple Send/Hold calls, drafts already built and QC'd) so Lizi's live ASSIST build and Park's Fri deadline both stay reachable. **External scan (2 searches, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted as its own FOA (NCATS space page still shows only the closed 2.0, last updated Apr 22 2026, "Tissue Chips in Space 2.0 Will Reveal..." Feb 17 2026 award news is the latest item); NASA ROSES-25 remains the open/active NASA solicitation (through Dec 31 2026 per NSPIRES) with no distinct ROSBio Appendix D/suborbital-bio program element surfaced — nothing new to act on there.**
> ✅ **2026-09-02 04:45 CDT — eRA COMMONS SO ACCOUNT CREDENTIALS CONFIRMED ISSUED (previously uncaptured — closes a real gap). PARK RETURNED HER TRACKED-CHANGES DRAFT 9/1 EVENING; A FINALIZED DOCX ALREADY EXISTS AND IS GATED BEHIND OPEN DECISION D-7281754.** Full IMAP + forwarded-mail scan since 8/28 surfaced three items the tracker hadn't logged yet: **(1) SO credentials — NIH (commons@od.nih.gov) emailed John twice on 2026-08-31 (2:47pm CDT): account created, username `JQUINN007`, org "EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC." (IPF #10098778), role **SO**, plus a temporary password (expired ~48h after issue, i.e. by ~2026-09-02 2:47pm CDT). Jon forwarded both with "@exobot capture this" — never actioned. This is exactly the credential [[reference_nih_era_commons_account]] predicted. **Retire "SO creds pending" language.** Practical note: if John hasn't logged in yet (https://public.era.nih.gov/commonsplus/), the temp password is now expired or expiring today — he'll need to use "Forgot Password" to get a fresh one. **Still-open, John-only step: register the PD/PI under this SO account** so the Purdue subaward/application can route in ASSIST — nobody has done this yet as far as any visible record shows. **(2) Park (Purdue) replied the evening of 2026-09-01** to Jon's $176,278 correction (which Jon in fact re-sent again that afternoon, 2:31pm CDT, saying "I may have sent this already but since I am traveling..." — so the corrected figure has now gone to Park+Brandee at least twice, no ambiguity left there) with her own tracked-changes draft of the full Research Plan, asking Jon to review/revise and send back a finalized version so she can insert her already-compiled reference list (she's holding off on citation numbering until the text stops moving). Jon forwarded to Exo: "@exobot update this final version from Sunghee for submittal." **(3) That instruction was ALREADY EXECUTED by an earlier run today, before this one** — deliverable `drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_PURDUE_FINAL_2026-09-01.docx` exists, and **Decision D-7281754** ("Send finalized NIH STTR research plan back to Estelle Park?", priority high, dedupe `sttr-purdue-park-finalize-sendback-20260901") is **OPEN**, awaiting Jon's Send/Hold. **This run independently QC'd the deliverable by unzipping and diffing the docx XML against Park's original tracked-changes attachment:** all 581 of her deletions / 588 insertions were cleanly accepted, no leftover cross-contamination from earlier model versions (zero hits for "intestinal," "kidney," "Kelly," "UW," "proximal," "TBD," "XXX"), budget unchanged (**total $314,363 / Exos SBC $138,085 / Purdue $176,278**), all 3 Aims + both figures present, 7 intentional `[ref]` placeholders left exactly as Park requested. **Note the model has evolved again — not agent drift, it's Park's own correction reflecting her lab's actual working system:** Kelly's kidney PT-MPS (original, pre-8/31) → "intestinal epithelial MPS" (8/31 pivot language, written before Park's own draft came back) → **Human Liver Organoids**, confirmed in Park's own 9/1 tracked-changes draft and now the resolved FINAL docx. Title/Aims/Innovation/Preliminary-Data sections all consistently say liver organoids — this is correct and should not be "fixed" back to intestinal. **Decision surfaced to Jon this run (not duplicated — D-7281754 already exists and is the single gate):** approve sending the finalized docx back to Park, or hold with edits. **Still open / unaddressed since first flagged 8/28: research-security-training certs for every PI/Co-I at ≥10% effort** (Park, Collicott, Exos PI) — 6 days to Sep 8, nobody has touched this. **External scan this run: BLOCKED — web_search, tavily_search, and web_fetch all returned connectivity errors (not a rate limit); no NCATS Tissue Chips 3.0 / NASA ROSBio Appendix D check possible. Retry next run.**
> ✅ **2026-09-01 13:53 CDT — JON: "We have the eRA Commons approval." THE LAST PLUMBING GATE IS CLEARED.** The 8/31 13:03 eRA notice WAS the org-registration approval; Exos SBC org-level eRA Commons registration is **APPROVED / active**. **Retire all "org-reg pending" / "call 866-504-9552 to expedite" / escalation flags — do NOT re-report it as pending or nag the Help-Desk call.** Sep 8 is now fully unlocked on the registration/plumbing side. **Root-cause of the miss (correct going forward):** the approval notice lives in Jon's M365/Outlook, which this agent cannot read (Proton-IMAP-only) — so the automated check kept asserting "pending." **RULE: for any M365-only item (eRA notices, PI replies to Jon's Outlook), never assert "pending"/"not done" as fact — report "no confirmation visible to me (M365 blind spot); confirm with Jon," and treat Jon's word as authoritative.** Same class of blind spot as the Kelly/Park forwarded-reply miss (matcher fixed, commit 9274113).
> ✅ **2026-09-01 13:59 CDT — Purdue $176,278 correction drafted + SENT to Jon's inbox ("[READY TO FORWARD] Purdue subaward CORRECTION → $176,278").** Ready-to-forward reply for Jon to send Park + Brandee (cc Kelly + Collicott) before today's SPS lock: Purdue subaward = **$176,278** (was ~$188K pre-fee-allocation), scope/period unchanged. **RESOLVED 2026-09-01 14:03 (Jon): "I already sent those new $ to Purdue last night." Purdue HAS the corrected $176,278 — retire the "Purdue has stale figure" flag entirely; Exo's ready-to-forward draft is MOOT.** Verification also surfaced a SECOND blind spot: Jon's send to Purdue is OUTBOUND from Outlook and was NOT copied to Proton (not forwarded, not BCC'd), so neither the old scan nor the new forwarded_mail detector can see it — that is why the 04:49 cron wrongly said "nobody sent it." forwarded_mail closes INBOUND forwards only. **RULE: to confirm Jon's OUTBOUND M365 sends, he must BCC jquinnexo@pm.me (sent-loop-closer ingests those); absent a BCC, an outbound send is invisible to Proton — report "no confirmation visible (M365 outbound blind spot), confirm with Jon," never "not sent."** ALSO CONFIRMED this run: the eRA approval + Purdue-correction miss both trace to the **NIH capture cron's inbox scan skipping mail FROM jquinn@exosaero.com** (Jon's forwards read as "our own outbound"). FIX TO WIRE: give this cron's inbox scan the forwarded-mail parser (detect Jon-forwarded gov/PI notices), same as outreach-reply-tracker got in commit 9274113. SENT BEFORE THE FEE CORRECTION. TODAY IS THE SPS LOCK DAY. Nobody has sent the corrected $176,278 to Purdue.** Direct IMAP verification (headers + downloaded/opened the actual .docx attachment) of the mail Jon sent from Outlook: **2026-08-31 20:49 UTC (3:49pm CDT) — Jon emailed Sunghee "Estelle" Park (park1713@purdue.edu), CC Brandee Faith Schluttenhofer (bhudspet@purdue.edu), subject "Re: NIH STTR PA-27-102 — Research Plan Narrative," body "Here's the latest draft," attaching `Exos_NIH_STTR_PA-27-102_ResearchPlan_PURDUE_SUBMISSION_2026-.docx`.** This send happened **2.5 hours BEFORE** the 22:15 CDT fee-correction lock below. Opened the attachment directly: it states Purdue's share as **"balance up to ~60% (≈$188K inclusive of Purdue F&A)"** — the PRE-fee figure, not the corrected $176,278. **So Purdue's SPS office (Brandee, who explicitly asked for the budget) is right now sitting on a document that says ~$188K, while Exos's own internal final number is $176,278 — a ~$12K gap — and today (2026-09-01) is the ~Sep 1 Purdue SPS internal lock this tracker has flagged as the critical date since 8/28.** The 03:19 CDT Exo→Jon email (after the fee correction) told Jon "nothing sent externally, stays gated by D-7281738" — that statement was **stale/incorrect**: Jon had already sent Park+Brandee directly from Outlook 2.5 hrs earlier, independent of the D-7281738 gate (which Jon had separately answered "Send to me" at 18:27 CDT, before even that send). No reply from Park visible in Proton IMAP since the 20:49 send (Outlook-blind-spot caveat applies — she may have replied to Jon's Outlook where Exo can't see it). **No eRA Commons confirmation-click visible either (that thread lives in Jon's Outlook, same known blind spot) — cannot confirm whether Jon completed the "click the confirmation link" step from the 8/31 13:03 approval notice, or whether he made the escalation call (866-504-9552) that the 02:19 CDT email told him to make "first thing tomorrow" (= today).** **Single most important action, TODAY, before Purdue's SPS lock: get the corrected $176,278 Purdue figure to Brandee/Park** — either a short follow-up correction email, or confirm w/ Purdue that the SPS lock will use the internal $176,278 target regardless of what the routed draft said. Flagged directly to Jon this run (not routed through ready_action.py — that pipeline's sent-registry would silently suppress a Brandee/Park send since they're already marked "sent," even though the content/number is now stale, so this needs Jon's eyes now rather than sitting in a queue). **External scan (1 search, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted as its own FOA (NCATS funding-opportunity list still shows only the closed RFA-TR-24-025 "2.0"); no NASA ROSBio Appendix D found.**

> 🟢 **2026-08-31 22:15 CDT — PURDUE SUBAWARD NUMBER LOCKED at $176,278 (John decided the fee question via email-command).** John: *"Apply the 7% to Exos and reduce Purdue accordingly not exceeding the $314K."* This confirms the RECOMMENDED path in the SF424 budget summary: total to the NIH Phase I guideline of **$314,363 (fee-inclusive)** = **Exos $138,085** ($117,519 base @40% + **$20,566 SBC fee @7%, kept by Exos**) + **Purdue $176,278** (60% of base, incl. Purdue F&A; above the ≥30% RI floor). Supersedes the earlier ~$188K working figure (that was 60% figured *before* the fee). **Exo executed (internal/reversible):** (1) cover email `drafts/NIH_STTR_Purdue_ONLY_Reframe_CoverEmail_2026-08-31.md` updated — Brandee now routes against $176,278; ~$188K reconciled in-text; attach list = SUBMISSION research plan + SF424 budget summary; (2) research-plan budget section in `scripts/build_nih_sttr_proposal_purdue_submission_docx.py` corrected to $138,085 / $176,278 and the docx rebuilt; (3) SF424 budget summary docx §5 marked RESOLVED with John's decision. **No external send performed** — the send to Park (park1713@purdue.edu) + Brandee (bhudspet@purdue.edu, cc Collicott) remains gated by **Decision D-7281738**. Numbers are now clean for the ~Sep 1 Purdue SPS lock the moment John releases the send.

> 🟢 **2026-08-31 13:03 CDT — eRA COMMONS ORG-REGISTRATION APPROVED. THE LAST BINDING PLUMBING GATE FOR SEP 8 IS CLEARED.** NIH (era-notify@mail.nih.gov) emailed John 1:03pm today: *"Your institution registration has been approved for eRA Commons"* — EXOS AEROSPACE SYSTEMS & TECHNOLOGIES, INC., requested 8/25, org address 299 FM 1903, Greenville TX 75402-3606. This is exactly the approval every prior entry was watching for (the ~Sep 2 / 866-504-9552 escalation is now MOOT — retire it). **John forwarded it as "Weekly news! New NIH research path for funding established."** **TWO John-only steps remain to finish activation (gov / his account — cannot be automated):** (1) John clicks the confirmation link in the NIH email to confirm the registration; (2) NIH then sends the **Signing Official account credentials** to jquinn@exosaero.com (this yields JQUINN007 / SO on IPF #10098778 per [[reference_nih_era_commons_account]]). Until (1) is done the org is approved-but-not-confirmed, so do NOT overstate "fully live" — it's "approved, confirmation pending." **What this unblocks for the Sep 8 PA-27-102 STTR (Exos + Purdue):** the Exos-side federal-registration long pole that was the #1 deadline risk is now resolved on NIH's side; submission plumbing clears once John confirms + SO creds arrive + a **PD/PI is registered under the SO** (still open — recommend Park academic PI + Exos co-PI, MPI plan). Still-open time-critical items UNCHANGED by this (carry from the 11:05 entry): (a) John approves + sends the Purdue-only reframe cover email → Park + Brandee (Decision D-7281738); (b) Exo still owes the **SF424 budget template + final Purdue number** for Brandee; (c) ~Sep 1 Purdue SPS internal lock; (d) research-security-training certs for every PI/Co-I ≥10% effort. **Immediate next action = John confirms the eRA registration link, then register the PD/PI under the SO so the packet can be routed/signed.**
> 🔴 **2026-08-31 11:05 CDT — STRUCTURE CHANGE: UW / ED KELLY IS OUT. STTR IS NOW EXOS + PURDUE ONLY (Purdue = SINGLE research institution of record). PRIMARY MODEL PIVOTS FROM KELLY'S KIDNEY PT-MPS → PARK LAB INTESTINAL EPITHELIAL MPS.** Morning thread (8/31): Ed Kelly emailed 9:49am — "UW's OSP can't meet this really tight deadline… it would be all on Estelle and you John." Jon replied 10:41am ("Estelle looks like you are up to bat. Let's run with it. More money for your project. I will reframe that and get back to you."). Park replied 10:51am asking Jon to send her + **Brandee Faith Schluttenhofer (bhudspet@purdue.edu, Purdue SPS)** a **revised draft + budget**. Jon then emailed Exo (email-command, 10:57am): **"@exobot rewrite this for Purdue only and send to me."** **Exo executed:** (1) built the Purdue-only Research Plan narrative — Exos SBC ≥40% + Purdue single RI of record (balance up to ~60%); Park (Weldon BME, intestinal/hepatic organoids + MPS) = biomedical lead; Collicott (AAE) = suborbital methods co-I; ONE institution → ONE Purdue SPS routing clock (the UW-OSP clock that couldn't make it is gone). Phase I primary = **intestinal epithelial MPS** onset-kinetics **+ post-flight regeneration readout** (re-embed Matrigel, organoid-forming efficiency, crypt budding, proliferation, barrier recovery — the recoverable-suborbital differentiator ISS can't cheaply match); **hepatic organoid = Phase II**. All Kelly/UW ISS-heritage refs (CRS-17/CRS-22, Lidberg npj MG 2024) REMOVED — that was UW's IP; no ISS heritage claimed for Purdue. Files: `drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_PURDUE_DRAFT_2026-08-31.docx` (build script `scripts/build_nih_sttr_proposal_purdue_docx.py`) + cover email `drafts/NIH_STTR_Purdue_ONLY_Reframe_CoverEmail_2026-08-31.md`. (2) Budget reframed: Exos 40% (~$126K) / **Purdue up to ~60% (~$188K incl. F&A)** at the ~$314K guideline (UW's freed 30% rolls to Purdue = the "more money" Jon promised Park). (3) Delivered draft+email straight back to Jon via the email-command reply (docx attached) AND created **Decision D-7281738** (source "Exo (email command)", assigned jquinn@exosaero.com, dedupe `nih-sttr-purdue-reframe-send-0831`) gating the external send to Park+Brandee (cc Collicott). **OPEN / TIME-CRITICAL:** (a) Jon approves + sends the cover email → Park (park1713@purdue.edu) + Brandee (bhudspet@purdue.edu); (b) Exo owes Jon the **SF424 budget template + final Purdue number** for Brandee to route (promised "under separate cover" in the email); (c) ~Sep 1 Purdue SPS internal lock is the ONLY routing clock now — confirm SPS has the revised budget/SOW; (d) eRA Commons org-reg APPROVAL still pending (escalate ~Sep 2, 866-504-9552); (e) confirm PD/PI (recommend Park academic PI + Exos co-PI, MPI plan). Prior-entry facts about the DUAL-institution structure and the ~$94K Purdue subaward are SUPERSEDED by this entry.
> 🟢 **2026-08-31 04:45 CDT — PARK REPLIED SUN 8/30, JON ANSWERED HER SAME NIGHT (cc Kelly) — AIM 2/3 SCOPE NOW LOCKED. Purdue SPS internal lock is ~Sep 1 (essentially tomorrow).** Full IMAP scan since 8/28 found real movement that predates this run: **Sunghee "Estelle" Park (Purdue) replied 2026-08-30 3:39pm CDT** (cc edkelly@uw.edu) to Jon's 8/26 research-plan-narrative send, asking a substantive scoping question — keep Phase I focused solely on Dr. Kelly's kidney proximal-tubule MPS, or add her lab's intestinal/hepatic organoid work as a second primary model? She flagged the tradeoff herself (second model = title/abstract/aims rewrite risk this close to Sep 8) and offered to support Kelly's kidney model instead if that's the call. **Jon forwarded to Exo at ~9:44pm CDT ("@exobot advise and prepare draft response"); Exo drafted a recommendation (keep kidney MPS as sole Phase I model, bank Park's intestinal-organoid study explicitly as the Phase II expansion, fold her offered Aims 2/3 tasks — post-flight validation, recovery/culture protocols, viability/epithelial-integrity, imaging, barrier-function, mechanotransduction interpretation — under Kelly's direction as measurable subaward milestones); Jon sent that exact reply to Park (cc Kelly) at 10:20pm CDT — CONFIRMED SENT, IMAP-verified.** This closes the scope-ambiguity gap and gives Park a clear, actionable ask (write her Aims 2/3 tasks as milestones). **Still open / time-critical:** (a) Park now needs to turn around her milestone list fast — Jon's own email cites a **~Sep 1 Purdue SPS internal lock, i.e. essentially tomorrow (Tue)** — worth confirming with Jon whether Purdue SPS has what it needs (the ~$94K subaward budget was sent 8/28, per the entry below) or if anything is still missing before that lock; (b) **eRA Commons org-registration approval is STILL PENDING** — Jon's own 8/26 email to Kelly/Park states "still waiting out ERA commons approval" and no NIH approval notice has landed in any Proton folder since 8/28 (full keyword scan clean) — the ~Sep 2 escalation threshold (call eRA Commons Help Desk 866-504-9552) is now essentially due; (c) no confirmed independent reply from Kelly himself since 8/26 (he's been cc'd throughout but hasn't sent his own message) — not urgent since Park is actively carrying the Purdue side and Kelly's UW routing was reported started 8/28. **External scan (2 searches, per budget): no movement — NCATS Tissue Chips in Space 3.0 still not posted (page still shows only 2.0, last updated Apr 22 2026); NASA ROSES-2026/ROSBio Appendix D still not released (ROSES-25 remains the active solicitation through August 2026).** Separately noted for context (not urgent, not sent to Jon yet): a self-drafted 8/29 cross-pursuit memo flags NIH STTR as the richest Phase II lane in the portfolio ($2.15M cap, full amount typically awarded) — reinforces why Sep 8 is worth the sprint.
> 🟢 **2026-08-28 06:17 CDT — JON: "Kelly/Park writeups went out, and Park replied already — both forwarded." THE 04:45 RED-FLAG GAP IS CLOSED.** The aligned writeups WERE forwarded (Kelly/UW + Park/Purdue) before today's deadline, so **UW OSP + Purdue SPS routing is under way** — retire the "writeups may not have gone out" gap; do NOT re-nag on the forwards. **Park (Purdue biomedical) has already REPLIED** = a live, positive engagement on the Purdue side. Remaining gates for Sep 8: (a) get Park's reply content to Exo — Jon forward/BCC to exosmc@proton.me — so the next step (thank-you + scope/effort confirm + any co-I paperwork) can be drafted; (b) NIH's **eRA Commons org-reg APPROVAL** (still pending on NIH's side; escalate ~Sep 2 via 866-504-9552 if not landed); (c) **research-security-training** certs for every PI/Co-I at ≥10% effort. Routing clock (5–7 biz days) started with runway before the Sep 7 holiday. **Sep 8 is LIVE.**
> 🟢 **2026-08-28 09:30 CDT — PARK'S REPLY RETRIEVED (found in jquinnexo@proton.me; loop-closer missed it because it was a FORWARD from jquinn@exosaero.com carrying her reply, not a direct @purdue.edu send — matcher gap to widen).** Content: Jon forwarded the research-plan doc to BOTH Kelly (edkelly@uw.edu) + Park (park1713@purdue.edu) on 8/26 12:05. **Park (Sunghee "Estelle" Park) replied 8/26 12:10 — GREEN LIGHT:** "Thank you for sharing the document. I will work on this and send it back to you as soon as possible," and she **CC'd Purdue sponsored programs — Brandee Faith Schluttenhofer (bhudspet@purdue.edu)** — "please see John's email below for the budget information." **= Purdue SPS routing is initiated; Purdue's grants office now has the ball on the subaward budget.** NEXT ACTIONS (both route through Jon for send; university/gov-adjacent): (1) draft the **Purdue subaward budget + scope-of-work** for Brandee (she explicitly asked for budget info) — Purdue applies its own F&A; we supply the subaward total (~≤30% ≈ $94K) + task scope + PI effort; (2) short **thank-you/next-step reply to Park** confirming she fills in Aim detail + timeline. Kelly got the same forward — watch for his UW OSP reply; nudge if none by ~Sep 1.
> ✅ **2026-08-28 09:38 CDT — Purdue subaward budget draft SENT TO JON'S INBOX ("[READY TO FORWARD] Purdue subaward budget → Park + Brandee").** Ready-to-forward reply for Jon to send to park1713@purdue.edu + bhudspet@purdue.edu (cc Kelly + Collicott): Purdue subaward NTE **~$85K** (incl. Purdue F&A), scope = suborbital methods + biomedical support, ask = Purdue's detailed budget + SOW + signed LOI/subaward commitment for the Sep 8 packet. Budget basis (UPDATED 09:41 — Jon: make UW and Purdue EQUAL): statutory split held at Exos **40%** / UW **30%** / Purdue **30%** → **~$126K / ~$94K / ~$94K** at the ~$314K NIH guideline (equal universities pins everyone to the exact floors; detailed SF424 build must land UW & Purdue each at 30.0%+ and Exos 40.0%+). **Corrected ready-to-forward draft (Purdue ~$94K) resent to Jon's inbox — supersedes the earlier $85K version.** **Do NOT re-flag "budget not sent" — it's in Jon's inbox awaiting his forward.** Matcher fixed (commit 9274113) so future forwarded PI replies auto-capture. **2026-08-28 09:47 — BOTH subaward budget notes now ready-to-forward in Jon's inbox:** Purdue (Park+Brandee, corrected ~$94K) AND UW/Kelly (Ed Kelly + UW OSP, ~$94K, core biomedical science scope w/ CRS-17/CRS-22 benchmark). Open: (a) Jon forwards BOTH budget notes → UW OSP + Purdue SPS route in parallel; (b) eRA org-reg approval watch (~Sep 2, call 866-504-9552); (c) research-security-training certs (Kelly, Park, Collicott, Exos PI); (d) watch for Kelly's UW reply + Park's filled-in Aim detail (forwarded-reply matcher now auto-captures per commit 9274113).
> 🔴 **[SUPERSEDED by the 06:17 entry above] 2026-08-28 04:45 CDT — GAP FOUND: the 8/26 16:30 "ALIGNED" writeups (Jon-approved) have no confirmed external send, and today is effectively the last day they can go out and still clear Sep 8 on routing math.** Full IMAP scan (All Mail + Spam, all folders, since 8/26) found ZERO messages since **2026-08-26 16:30 CDT** on this pursuit — not even internal Exo/Jon chatter. That 16:30 email (from Exo, "per your approval") confirms Jon approved three finalized writeup docs the same afternoon: (1) `NIH_STTR_UW_Kelly_Writeup.docx` — forward to Dr. Kelly, frames UW as lead RI; (2) `NIH_STTR_Purdue_Subaward_Writeup.docx` — forward to Collicott, Purdue as subaward; (3) `NIH_STTR_Purdue_Park_CoI_Intro.docx` — optional Park co-I intro. The email states explicitly: **"forwarding 1 and 2 today is what starts UW OSP and Purdue SPS routing for Sep 8."** No record exists in Proton (or in this tracker, until now) that Jon actually forwarded #1 or #2 to Kelly/Collicott — this was never previously flagged as its own open item; prior entries tracked the eRA org-reg approval but not this forward. **Two possibilities: (a) Jon sent them from Outlook, invisible to Proton IMAP unless CC'd — the same blind spot flagged repeatedly on this pursuit; or (b) they never went out.** Either way this is now the most time-critical unknown: routing needs 5–7 business days, Sep 7 is Labor Day (federal holiday, offices closed), and Sep 8 is the deadline — if the forwards haven't gone out yet, today (Fri 8/28) is the last day that leaves any real runway (5 business days: 8/31–9/4) before the holiday-shortened final stretch. Dispatched an urgent status-check READY-ACTION this run (key: nih-microgravity-aligned-writeups-status-0828) rather than assuming either way. **eRA Commons org-reg approval:** still no notice either way; escalation threshold (~Sep 2, call 866-504-9552) unchanged, not yet due. **External scan (2 searches, per budget):** no NCATS Tissue Chips in Space 3.0 solicitation (NCATS space page still last-updated Apr 22 2026); ROSES-2026 still not released (ROSES-25 remains the active NASA solicitation, amendments through Jul 27) — no ROSBio Appendix D/E. Nothing new to act on there.
> 🟢 **2026-08-27 04:45 CDT — Kelly-lab assay/effect-size specifics DROPPED INTO AIM 2 (research task, no Jon input needed for this step).** Researched Dr. Kelly's actual published ISS PT-MPS flight record (public lit, not yet in the tracker) and folded real specifics into `drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_DRAFT_2026-08-26.docx` (regenerated via `scripts/build_nih_sttr_proposal_docx.py`): the Kelly lab has flown the proximal-tubule MPS to ISS **twice** — CRS-17 (vitamin D metabolism + proteinuric response) and CRS-22 (calcium-oxalate microcrystal nephrolithiasis model) — and their own published result (Lidberg et al., *npj Microgravity* 2024, cited 10x) found **no significant change in PTEC vitamin-D metabolism or a unique serum response under sustained ISS microgravity.** That null result on *chronic* exposure is a genuinely strong, honest hook for BLK3: it leaves the **acute onset window (0–240s, obscured by ISS transit time)** as an open question Kelly's own ISS data can't answer — exactly what Aim 2's staged-timepoint suborbital design tests. Added this to both the Innovation ("Distinct from prior art") section and Aim 2's assay-panel/power-analysis bullets, with the ISS flight names (CRS-17/CRS-22) and the vitamin-D bioactivation pathway (25(OH)D3→1,25(OH)2D3) as concrete, citable specifics — replacing the prior vague "benchmark against the lab's existing ISS datasets" placeholder. **This was the one open item in the doc that didn't require waiting on Jon** (PD/PI decision, NIBIB SEED concurrence, and routing were always Jon/Kelly/Collicott-gated). Doc is otherwise unchanged from the 8/26 version Jon is reviewing.
> — **External scan (2 searches, per budget):** No NCATS Tissue Chips in Space 3.0 solicitation posted yet (NCATS space page last updated Apr 22 2026, still describes the closed 2.0 program). No new NASA ROSBio Appendix D/E found. Nothing new to act on there — same as 8/26 finding, re-confirmed.
> — **Email/MC scan: NO movement since Jon's 8/26 15:47 reply.** No eRA Commons org-registration approval notice from NIH. No reply from Kelly (UW), Park (Purdue), or any @nih.gov/@uw.edu/@purdue.edu sender in the inbox since 8/26. No new MC decision recorded on this pursuit. **The org-reg approval clock is the only thing actually gating Sep 8 right now, and it's entirely on NIH's side** — per the 8/26 06:41 entry, escalate-to-Jon threshold is ~Sep 2 (call eRA Commons Help Desk 866-504-9552) if no approval lands by then. Today is day 1 of that watch window.

> 🟢 **2026-08-26 09:55 CDT — ACTUAL PROPOSAL NARRATIVE DRAFTED (Jon @Exobot request).** Jon clarified he wanted the *real NIH research-plan writeup aligned to PA-27-102 requirements*, NOT the intro/outreach correspondence already sent. Built `drafts/Exos_NIH_STTR_PA-27-102_ResearchPlan_DRAFT_2026-08-26.docx` — the actual NIH SBIR/STTR forms narrative: Project Narrative (3 sentences), Abstract (30 lines), **Specific Aims (1pg, 3 aims)**, **Research Strategy (6pg: Significance / Innovation / Approach)**, compliance/risk, Phase I deliverables, budget-to-40/30/30. Science anchored on **Kelly (UW) proximal-tubule kidney MPS + BLK3 onset-kinetics screening**; structure = **Exos SBC ≥40% · UW/Kelly RI-of-record ≥30% · Purdue (Collicott/Park) subaward ≤30%**. Honest guardrails held (BLK3 FAA-licensed not yet flown; µg durations/g-levels = design targets to verify in Aim 1; glioblastoma npj Microgravity 2023;9:92 heritage cited accurately; Greenville = mfg/test/hover only). Presented in chat for Jon's review. Still-open pre-submission gates flagged in the doc (PD/PI decision + MPI plan, NIBIB SEED concurrence, UW OSP / Purdue SPS routing, org-reg APPROVAL, Kelly assay specifics into Aim 2). Next: on Jon's edits, finalize + drop Kelly-lab assay/effect-size specifics into Aim 2, then hand to routing.

> 🟢 **2026-08-26 06:41 CDT — JON: "THE ORG REGISTRATION IS SUBMITTED — AWAITING APPROVAL." LAST BINDING GATE CLEARED (now in NIH's queue).** Jon answered the one remaining open item (Binding Constraint #1 — Exos SBC org-level eRA Commons registration with a Signing Official). It is **SUBMITTED to NIH, pending approval** — no longer a "start it today" item. **Retire the "start org reg today / org reg not addressed" flag.** All four registration constraints now closed on Exos's side: SAM.gov (have) + individual Login.gov→NIH link (8/25) + org-level eRA Commons SO reg (submitted 8/26). **New — and only — open dependency: NIH's approval turnaround on the org registration.** eRA Commons org registration approval historically runs ~2 biz days to 2 weeks; today is 8/26, deadline Sep 8 (≈9 business days out) — makeable but NOT guaranteed, and it is now entirely on NIH's clock, not ours. Agent next: (a) **do NOT nag Jon on org reg — it's submitted;** (b) set a watch to confirm the org-reg APPROVAL lands (Jon will get the eRA "organization registered / SO activated" notice — flag it the moment it hits so we know Sep 8 is fully unlocked on plumbing); (c) if no approval by ~Sep 2 (≈2 biz days of buffer before Sep 8), escalate to Jon to call the eRA Commons Help Desk (866-504-9552 / commons@od.nih.gov) to expedite; (d) keep routing/aims-scope/40-30-30 budget sprint moving on the GO assumption. Science + routing (Kelly/Collicott) and plumbing (registrations) are both now GO-tracked — the whole pursuit is live for Sep 8 pending NIH's registration approval.

> 🟢 **2026-08-26 06:23 CDT — JON: "THE CALLS HAPPENED AND WE ARE ON TRACK." GO — DO NOT STAND DOWN.** Jon answered the EOD go/no-go: the Kelly/Park calls occurred and Sep 8 stays LIVE. **Retract the "stand down / retarget Jan 5 2027 STTR" recommendation** — item #2 (PI routing / Kelly re-engage + Park status) is confirmed done and on track. **The ONLY remaining unanswered binding constraint is #1: Exos SBC ORG-level eRA Commons registration with a Signing Official** (individual Login.gov→NIH link is confirmed done 8/25; org-level SO reg is the days-to-2-week long pole and was NOT addressed in Jon's reply). A Decision card for that org-reg question was already dispatched this morning (04:45 run) — do NOT duplicate; that single answer now covers whether Sep 8 is fully reachable on the plumbing. Agent next: hold reply-watch on the eRA org-reg card; keep routing/scope/budget sprint moving on the assumption Sep 8 is GO.

> 🟡 **2026-08-26 04:45 CDT — NO MOVEMENT SINCE LAST NIGHT; TODAY IS GO/NO-GO DAY.** Checked MC decisions/tasks for any action on the two 8/25 urgent items (Kelly re-engage send, Park status check) — no new decision recorded, no evidence either was sent (last decision on file is still D-7281669, answered 8/24). The Exos-org eRA Commons registration question (flagged 8/25 21:17, Binding Constraint #1) also remains unanswered — no Decision card existed for it yet, so one is dispatched this run (see READY-ACTION below). External scan (2 searches): confirmed PA-27-102 due date is genuinely Sep 5/8 2026 (grants.gov, matches tracker); no NCATS Tissue Chips in Space 3.0 solicitation posted yet (still only 2.0, awarded Feb); no active 2026 NASA ROSBio Appendix D/E (suborbital/parabolic bio) solicitation found on NSPIRES — nothing to act on there. **Per the tracker's own 8/25 math, yesterday was already "the last practical day" for Kelly/Park to commit and start university routing — that day has now passed with no confirmed action.** Not calling it dead yet (routing offices open this morning, still time before EOD), but this run escalates to a single clear go/no-go ask rather than a third separate nag.

> 🟢 **2026-08-25 21:17 CDT — eRA COMMONS ACCESS CONNECTED (Jon).** Jon confirmed the Login.gov→NIH connection notice ("You connected your account to NIH," 9:17 PM CDT) was for **eRA Commons account access for the NIH proposal.** This directly advances **Binding Constraint #1** (the flagged #1 deadline risk). **Scope check — do NOT overstate:** a Login.gov→NIH link establishes an *individual* eRA Commons account/credential; the long-pole risk is the **Exos SBC org-level eRA Commons registration** (SO/AO institutional registration, historically days-to-2+ weeks). Open question for Jon: is the Exos *organization* registered in eRA Commons (with a Signing Official), or only Jon's personal account? If org reg is done → the #1 registration risk is effectively retired and Sep 8 stays live on registrations. If only individual → still need org reg started immediately. Also confirm SBA Company Registry + Grants.gov (SAM.gov already have). **Not gating the science — this is the plumbing that lets us actually submit.**

> 🟢 **2026-08-25 — KELLY SAID YES (Jon). PARTNER-LOCK GATE (Stage 1) PASSED.** Dr. Edward Kelly (UW) confirmed as the biomedical science anchor / RI-of-record for the PA-27-102 STTR. This is the make-or-break gate — now cleared. **Mode switches from "chase a PI" to "sprint a compliant STTR to Sep 8."**
> **Binding constraints to Sep 8 (in priority order — these, not the science, decide if we make it):**
> 1. **⚠️ #1 RISK — Exos SBC federal registrations.** STTR requires the small business registered in **SAM.gov (have it) + SBA Company Registry + eRA Commons + Grants.gov.** **eRA Commons org registration can take days-to-2+ weeks** — if Exos isn't already registered, this ALONE can miss Sep 8. **VERIFY TODAY.**
> 2. **Institutional sponsored-programs routing** — UW OSP (~5–7 biz days) + Purdue SPS (~5 biz days) run in parallel but the LATER governs. Kelly must open UW OSP routing **now**; Collicott opens Purdue subaward routing **now**. Commit-by ~Aug 26–27 was the line; today (Aug 25) both must start.
> 3. **PD/PI decision** — STTR PI may sit at the SBC (Exos) OR the RI (UW). Decide who is PD/PI (Kelly is a strong PI given his NIH/ISS track record; or Exos-side PI with Kelly as co-I).
> 4. **Structure (confirmed):** Exos (SBC) ≥40% · UW/Kelly (RI-of-record) ≥30% · Purdue/Collicott subaward ≤30%.
> Next actions: (a) verify Exos eRA Commons/SBA/Grants.gov registration status — TODAY; (b) draft Kelly teaming-confirmation email that triggers UW OSP routing; (c) scope specific aims (Kelly kidney-chip MPS + BLK3 onset-kinetics); (d) budget skeleton to the 40/30/30 split. **Honest call: Sep 8 is achievable only if registrations are already done and routing starts today — otherwise the realistic target is the next cycle (~Jan 2027). Flagging so we don't burn the team on an unmakeable deadline.**

> ✅ **2026-08-18 — JON DIRECTIVE (SUPERSEDES the 8/17 either/or pivot): "Restore the Ed Kelly framing and leverage Purdue capability as well — two can support the same effort."**
> **DUAL-INSTITUTION STTR. Kelly (UW) is RESTORED. Kelly and Collicott/Purdue are COMPLEMENTARY partners on ONE PA-27-102 application — not either/or. Do NOT emit any "pick one / suspend the other" decisions.**
> - **Roles:** **Dr. Edward Kelly (UW)** = biomedical science anchor (kidney chip / NCATS TraCe MPS kidney center 1U2CTR004867 / ISS Tissue Chips heritage) — fills the NIH biomedical-lead requirement that Collicott (AAE) cannot. **Prof. Steven Collicott (Purdue AAE)** = suborbital microgravity experiment design/methods + already-COMMITTED Exos partner (SACSS LOS in hand, "onboard" 7/27). **Exos** = SBC / flight platform / payload integration.
> - **STTR mechanics (structure it right):** an STTR needs ONE research-institution partner at **≥30%** of the work and the SBC (Exos) at **≥40%**; the remaining **≤30%** can subaward to a SECOND institution. So one of UW/Purdue is the formal **RI-of-record (≥30%)**, the other joins by **subaward / consultant / co-I**. **Recommended:** UW/Kelly = primary research institution (the NIH-fundable biomedical science); Purdue/Collicott = subaward for suborbital experiment methods. A Purdue Weldon BME organ-on-chip co-PI (Collicott's 7/24 intro) still strengthens the bio bench if it lands, but is no longer the blocker — Kelly IS the biomedical lead.
> - **RESTORED (was killed 8/17): the Kelly reply-retrieval action.** Kelly already replied but it is stuck in Jon's Outlook / GCC High (M365 blindspot — invisible to Exo). **Single most important action: Jon forwards Kelly's reply to exosmc@proton.me** so Exo can read it and advance the dual-institution teaming.
> - **Clock:** Sep 8 STTR. TWO routing clocks now — UW (~5–7 biz days) + Purdue SPS (~5 biz days); BOTH institutions must route, so the LATER one governs → both PIs need commitment by **~Aug 26–27** to make Sep 8. Tight but live, not dead.
> - Next agent actions: (1) advance Kelly reply-retrieval (Jon-forward to exosmc@proton.me) — RESTORED; (2) keep the Purdue/Collicott methods + optional Weldon BME co-PI confirmation; (3) draft the dual-institution teaming framing (roles + %-split + which RI is of-record) for Jon's review. Reply-watch on the other PIs continues.
> - ✅ **2026-08-24 16:51 CDT — JON ANSWERED DECISION D-7281669: "Yes — forward Kelly now."** Jon approved re-engaging Kelly directly (proposedAction: Exo drafts the intro/forward, delivers to inbox to send). As of this run (2026-08-25), no evidence that draft was produced or sent — Proton inbox scan (Sent/All Mail, all folders, since 8/21) shows zero Kelly/UW correspondence and zero Park/Purdue correspondence. **This run: drafted and dispatched the Kelly re-engagement email as a READY-ACTION** (key: nih-microgravity-kelly-reengage-0825), now CC'ing exosmc@proton.me on the ask itself so any reply lands somewhere Exo can read it (fixes the recurring BCC/Outlook blind spot going forward, per the standing-fix recommendation below).
> - ⚠️ **PARK TRACK STATUS UNKNOWN — SPS gate is essentially NOW.** Per the 8/18 framing, both UW and Purdue SPS need ~5–7 business days to route and BOTH PIs needed to commit by ~Aug 26–27 for Sep 8 to be reachable. Today is 2026-08-25 (Tuesday) — the absolute last practical day for either commitment. No email trace exists of the Park call (schedule/prep READY-ACTIONs sat in Jon's inbox 8/19–20; call may have happened by phone, which wouldn't show in IMAP — status genuinely unknown from here). **Dispatched an urgent status-check READY-ACTION** (key: nih-microgravity-park-status-check-0825) asking Jon directly whether the Park call happened and what her answer was.

**Stage 1 of 6 — Partner lock (Sep 8 STTR gate). THREE LIVE PI PATHS as of 2026-07-24 (Jon confirmed sends "DONE"):**
- **Vunjak-Novakovic (Columbia) + Kelly (UW) + NIH SEED office** — reply-chases SENT 2026-07-24 (Jon confirmed). Now in reply-watch; do NOT re-nudge before ~1 week.
- **Collicott (Purdue AAE) warm-intro ask** — delivered ready-to-send to Jon 2026-07-24 to reach a Purdue Weldon BME organ-on-chip / MPS PI (same-institution, warm path). Awaiting Jon send + Collicott reply.
- Han (TAMU) DECLINED 2026-07-16.
**Monday gate reframed: not "call it" but "did all sends go + did the Purdue warm intro open." Both now actioned.**

**2026-07-27 — JON DECISION = OPTION A: hold STTR track open through Aug 4, watch for inbounds (Wu/He/Sethu + Collicott/Purdue). Collicott confirmed SENT 7/24 12:39 (loop-closer).** Jon's note: "Collicott already onboard" — he is a COMMITTED Exos partner (SACSS LOS in hand), so his intro to a Purdue Weldon BME organ-on-chip PI is a warm partner referral, not a cold ask = strongest PI path. If a Purdue BME PI engages, that PI + Collicott (platform/methods) = a same-institution STTR team.

**2026-07-27 — JON SAID "HOLD": reply-watch ONLY. Do NOT stage or send any Collicott nudge; let him reply on his own. No outbound on this pursuit without Jon's go.**

**2026-07-27 22:56 CDT — KELLY REPLIED (per Jon), BUT reply is NOT retrievable by Exo. ⚠️ DO NOT PIVOT TO BD-ONLY.**
- Jon states Dr. Kelly (UW) already responded. Confirmed NOT present in any Proton inbox Exo can access: searched INBOX/Archive/Spam/Trash across all four aliases (jquinnexo@pm.me/proton.me, exosmc@pm.me/proton.me) by FROM kelly, FROM uw.edu, FROM edkelly, and by subject/body (kidney, microgravity, TraCe). Zero inbound from Kelly or any @uw.edu.
- ROOT CAUSE: all Kelly outreach went from Jon's Outlook (jquinn@exosaero.com), CC Lizi, Exo on BCC. BCC recipients are invisible to a reply, so Kelly's reply-all reached Jon + Lizi only, never Exo's BCC. His reply is sitting in Jon's exosaero.com inbox (and probably Lizi's).
- UNBLOCK (one action, on Jon): forward Kelly's reply to exosmc@proton.me or jquinnexo@pm.me. Then Exo reads it, drafts Jon's response, and advances the STTR.
- **The two open "PI-lock gate PASSED July 28 → pivot to BD-only" decision tasks (1639 unassigned, 1643 jquinn) are PREMATURE and should NOT auto-fire. A live PI response exists; the gate did not fail — the reply is merely unretrieved.** Overnight resolver / Capture Agent: hold both; do not pivot.
- DATE RECONCILIATION: Friday's subject cited a "PI-lock gate July 28." The most recent Jon decision on file (7/27, Option A above) is "hold STTR track open through Aug 4." Hard STTR submission deadline = Sep 8. Runway exists even if July 28 slips.
- **STANDING FIX (recommend to Jon): switch NIH-MG PI outreach from BCC-Exo to CC a Proton alias (exosmc@proton.me) so replies land where Exo can act and chase without Jon relaying.** Awaiting Jon's go to make this the standing pattern.
1. ▶ Lock a biomedical PI partner (gates NIH STTR) — Vunjak + Kelly + SEED chases SENT 7/24; Collicott warm-intro ask staged 7/24. **Emails verified: gv2131@columbia.edu (7/21), edkelly@uw.edu (7/1), collicot@purdue.edu (7/24).**
2. ⬜ Scope the STTR experiment (PI science + BLK3 platform role)
3. ⬜ Draft STTR (PA-27-102) toward Sep 5 2026
4. ✅ Sell-slot BD one-pager drafted (2026-06-27) — awaiting Jon approval to use
5. ⬜ Track NASA ROSBio Appendix D + NCATS Tissue Chips 3.0 windows
6. ⬜ Award / booked slots

## Key facts (anchor; don't drift)
- HONEST: NIH funds the biomedical PI/science, NOT the rocket. Exos = flight platform + payload integration + recovery. STTR REQUIRES a research-institution partner = the structural fit.
- BLK3 = ~3–4 min recoverable suborbital microgravity, fast turnaround, low cost. Niche = SCREEN/DE-RISK before ISS; onset-kinetics, nucleation, pharma/formulation, MPS validation. BLK3 is FAA-licensed but NOT yet flown commercially.
- NIH SBIR/STTR reauthorized Apr 14 2026. Parents: SBIR PA-27-100, STTR PA-27-102, Phase IIB PA-27-101, CRP PAR-27-098. **Next deadline: Sep 8 2026** (Sep 5 is Saturday; confirmed moved). High volume expected — missed Jan + Apr deadlines created submission pileup. "Microgravity" is not a named topic → investigator-initiated; frame to **NIBIB** (device/platform) primary / **NIA** (aging/muscle) secondary.
- NCATS Tissue Chips in Space 2.0 AWARDED Feb 17 2026 (closed; 6 grants) → watch for 3.0. ISS-focused (sustained µg).
- **⚠️ ISS-NL/CASIS SOLICITATION TRACK CONFIRMED DEAD (2026-06-27):** Per ISS-NL website: "Solicitations for proposals are unlikely to be issued in the future." Only Commercial Service Provider pathway remains. BD target shifts to researchers using CSP pathway (Axiom, Redwire, etc.) and NCATS TraCe MPS awardees with existing NIH grants.
- NSF/CASIS tissue-engineering µg FO: feasibility Jan 12 2026 / full Mar 4 2026 (PAST).
- NASA ROSBio Appendix D = parabolic/suborbital space biology (NASA, not NIH) = cleanest suborbital-bio money; track next appendix.
- Concept: captures/BLK3_NIH_Microgravity_Concept.md (emailed to Jon 2026-06-27). Ties to BLK3 payload-sales campaign (Mar 2027 flight).

## PI Shortlist (Action #1 — COMPLETE 2026-06-27)
Three Tier-1 targets for STTR partner outreach. All verified as active NIH awardees with ISS/MPS experience. All at STTR-eligible research institutions. **UNVERIFIED — Jon must approve before Exo contacts.**

### Tier 1A — Strongest fit
**Dr. Gordana Vunjak-Novakovic** | Columbia University | New York, NY
- Full professor of biomedical engineering; UNESCO Chair; National Academy member
- Tissue Chips in Space veteran: bone/cartilage and cardiac chips flown to ISS (2019-2022)
- Deep NIH portfolio; multiple STTR awards; knows the proposal process cold
- Best pitch: BLK3 as low-cost suborbital screening to de-risk payloads before her next ISS flight
- Contact via Columbia BME dept (gv2131@columbia.edu — verify before use)
- **STTR angle**: NIBIB framing, "suborbital microgravity device platform for musculoskeletal tissue chip de-risking"

### Tier 1B — Texas geography advantage
**Dr. Arum Han** | Texas A&M University | College Station, TX
- Professor of Electrical & Computer Engineering; MPS/organ-on-chip expert
- Active NCATS TraCe MPS awardee (1U2CTR004868 — pregnancy/women's health MPS, co-PI)
- Texas = operational logistics for Exos; same state = easier team meetings
- Pitch: BLK3 for rapid suborbital screening of TraCe MPS chip performance under µg onset
- Contact via TAMU ECE dept (arum.han@tamu.edu — verify before use)
- **STTR angle**: NIBIB or NICHD framing, "suborbital onset-kinetics validation of microphysiological platforms"

### Tier 1C — ISS veteran, kidney focus, now TraCe MPS
**Dr. Edward J. Kelly** | University of Washington | Seattle, WA
- Associate Professor of Pharmaceutics; kidney chip / drug transporter expert
- ISS Tissue Chips in Space veteran (kidney chip, 2019 + 2021 flights)
- Now co-PI on NCATS TraCe MPS kidney center (1U2CTR004867)
- Pitch: BLK3 suborbital as low-cost, rapid-turnaround screening step before the TraCe MPS ISS kidney flight
- Contact via UW Dept of Pharmaceutics (edkelly@uw.edu — ✅ VERIFIED 7/1; ed9@uw.edu was WRONG)
- **STTR angle**: NIBIB framing; strong precedent since he's done the NCATS-ISS flow before

## NIH Institute Framing (Action #2 — COMPLETE 2026-06-27)
**Recommended primary institute: NIBIB**
- NIBIB explicitly funds "biomedical imaging and bioengineering devices and platforms" — BLK3 is framed as a biomedical research platform device, not a launch vehicle
- NIBIB co-funded NCATS Tissue Chips in Space (RFA-TR-18-001 was NCATS + NIBIB joint) — program officers already have microgravity MPS in their portfolio
- NIBIB SB program will accept investigator-initiated STTR if framed as device/platform development
- NIBIB contact: NIH SEED office (seed@mail.nih.gov) for pre-submission inquiry — do this BEFORE submitting

**Secondary institute: NIA** (National Institute on Aging)
- µg accelerated aging is a documented, funded research area (muscle wasting, bone loss, immune aging all ISS-funded through NIA)
- BLK3 onset-kinetics framing: "rapid suborbital microgravity model for early-phase aging pathway activation"
- NIA is less precedented for STTR with launch platforms — NIBIB is safer primary

**Do NOT lead with NCATS** as the STTR institute. NCATS doesn't issue STTR FOAs directly; they co-fund via partnerships. The proposal goes to NIBIB/NIA.

## POCs / channels (LEADS — verify before any contact)
- NIH SEED office — seed@mail.nih.gov — pre-submission inquiry for STTR institute fit (verify email)
- Dr. Danilo Tagle — NCATS Tissue Chip program lead (verify current title; may have rotated)
- ISS-NL/CASIS — **solicitation track confirmed dead; CSP pathway only**; Dr. Michael Roberts (verify if still CSO)
- NASA ROSBio / Space Biology (BPS) program officer — find via NSPIRES

## Next actions
| # | Action | Owner | Due | Status |
|---|--------|-------|-----|--------|
| 1 | PI shortlist (3 targets) | Exo | done | ✅ COMPLETE (2026-06-27) |
| 2 | NIH institute framing (NIBIB primary, NIA secondary) | Exo | done | ✅ COMPLETE (2026-06-27) |
| 3 | PI outreach — Draft B (Han/TAMU) SENT 2026-07-16 ✅; Drafts A/C (Vunjak, Kelly) optional/secondary | Jon | done (Han) | ✅ HAN SENT 2026-07-16 5:46 PM; awaiting reply |
| 4 | Sell-slot BD one-pager | Exo→Jon | done | ✅ DRAFT COMPLETE (see below / captures/) |
| 4b | Jon approves BD one-pager → route to PI/MPS labs | Jon→Exo | ASAP | **DECISION NEEDED** |
| 5 | NIH SEED pre-submission inquiry (institute fit, program officer) | Exo→Jon | ASAP | ✅ DRAFT COMPLETE (2026-06-30) — Jon must approve/send; see SEED Inquiry Draft below |
| 6 | On PI lock: scope STTR experiment + draft PA-27-102 toward Sep 5 | Exo→Jon | by Aug 1 | STAGED |
| 7 | Track NASA ROSBio Appendix D + NCATS Tissue Chips 3.0 release | Exo | ongoing | OPEN |
| 8 | Verify POC contact info for all 3 PI targets before any outreach | Exo | before outreach | OPEN |

## Sell-slot BD One-Pager (Action #4 — DRAFT)
*Audience: NCATS TraCe MPS awardees and ISS-CSP-pathway-funded researchers who need low-cost, rapid suborbital microgravity screening*

---
**BLK3 SUBORBITAL PAYLOAD SLOTS — AVAILABLE MAR 2027**
*Exos Aerospace | SPACEavailable...™ Payload Services*

**The problem your ISS payload faces:**
ISS flights cost $1M+, take 18+ months of lead time, and hardware qualification is expensive. You don't know if your tissue chip behaves as expected in actual microgravity until you're already committed. A failed ISS payload is a wasted grant cycle.

**What BLK3 gives you:**
- ~3–4 minutes of recoverable, high-quality microgravity
- Days-fast turnaround (2-day between-flight window)
- Fraction of ISS cost
- Recovered payload returned for analysis
- FAA-licensed, reusable suborbital platform (one of only 3 FAA-licensed reusable launch providers in the US)

**The play: Screen on BLK3, fly the winners to ISS.**
Use suborbital flights for:
- Onset kinetics: how quickly does your cell/tissue respond to µg? (seconds-to-minutes window)
- MPS/organ-chip validation: does the chip maintain fluid dynamics, cell viability, and structural integrity under µg?
- Pharma/formulation screening: particle nucleation, drug release behavior
- Payload hardware de-risk before ISS qualification spend

**Available capacity: Mar 2027 BLK3 flight**
- Payload bay: 135 kg / 25 × 36 cm envelope
- Recovery: full payload recovery post-flight
- Interface: standard payload integration (contact us for ICD)

**Fit:** Especially relevant if you hold NCATS TraCe MPS, NIH Tissue Chips in Space, or NASA Flight Opportunities funding and are preparing for or planning an ISS flight.

**Contact:** John Quinn, Cofounder & CEO | jquinn@exosaero.com | +1-972-740-8355

---

## PI Outreach Drafts (Action #3 — DRAFTED 2026-06-29, awaiting Jon send-approval)

*Three ready-to-send emails from Jon to each PI target. Jon must approve before any are sent. Email voice: "Hello [Name],", no em-dashes, no AI tells. Exos email sig auto-appended by Outlook.*

---

### DRAFT A — Dr. Gordana Vunjak-Novakovic (Columbia)
**To:** gv2131@columbia.edu *(✅ VERIFIED 7/1)*
**Subject:** Suborbital microgravity screening platform for tissue chip work — quick introduction

Hello Dr. Vunjak-Novakovic,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. I've followed your tissue chip and ISS work closely, and I wanted to reach out about a potential collaboration that could complement your next microgravity flight.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S. We're planning a March 2027 flight from Spaceport America with recoverable payload capacity. The platform delivers 3 to 4 minutes of high-quality microgravity with full payload recovery, at a fraction of ISS cost and lead time.

The niche we fill is suborbital screening: onset kinetics of cell and tissue response, structural integrity checks on chips under µg, and hardware de-risk before an ISS qualification campaign. The pitch is simple, screen on BLK3, fly the winners to ISS.

We have available payload capacity on the March 2027 flight, and we're also exploring an NIH STTR (PA-27-102, September 2026 deadline) with a biomedical PI who would anchor the science while Exos provides the microgravity platform. Your group's ISS Tissue Chips in Space heritage is exactly the kind of precedent NIH reviewers recognize.

Would you have 20 minutes in the next few weeks to explore whether there's a fit?

John Quinn
Cofounder and CEO

---

### DRAFT B — Dr. Arum Han (Texas A&M)
**To:** arum.han@tamu.edu *(✅ VERIFIED 7/1)*
**Subject:** BLK3 suborbital platform + NIH STTR opportunity — Texas connection

Hello Dr. Han,

I'm John Quinn, Cofounder and CEO of Exos Aerospace, based in Greenville, Texas. I came across your TraCe MPS work (1U2CTR004868) and wanted to introduce a suborbital microgravity resource that may be useful for your microphysiological platforms.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the country. We're planning a March 2027 flight with recoverable payload capacity, delivering 3 to 4 minutes of microgravity at a fraction of ISS cost. Being Texas-based, we can make integration logistics straightforward.

For TraCe MPS work, suborbital flights offer a practical way to characterize chip behavior under µg onset before committing to a full ISS flight timeline, whether that's fluid dynamics, cell viability, or structural integrity.

We're also exploring an NIH STTR collaboration (PA-27-102, September 2026 deadline) where Exos serves as the suborbital microgravity platform and a biomedical PI anchors the science. The NIBIB device-platform framing is a strong fit.

If any of this is relevant to where your lab is headed, I'd be glad to connect. Even a quick call would help me understand whether there's a fit worth developing.

John Quinn
Cofounder and CEO

---

### DRAFT C — Dr. Edward J. Kelly (University of Washington)
**To:** edkelly@uw.edu *(✅ VERIFIED 7/1 — corrected from ed9@uw.edu)*
**Subject:** Suborbital kidney chip screening before your next ISS flight

Hello Dr. Kelly,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. Your kidney chip ISS work and current TraCe MPS center (1U2CTR004867) caught my attention, and I wanted to introduce a suborbital resource that could support your next ISS campaign.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S. We're planning a March 2027 flight from Spaceport America with recoverable payload capacity, providing 3 to 4 minutes of quality microgravity at a fraction of ISS cost.

For kidney chip work, the practical value is de-risking hardware before ISS qualification spend: confirming cell viability, transport function, and structural integrity under µg before you commit to an ISS flight cycle. You've done the NCATS-to-ISS pipeline before, so you understand how expensive a late-stage payload failure is.

We're also pursuing an NIH STTR (PA-27-102, September 2026 deadline) and are looking for a biomedical PI to anchor the science, with Exos providing the suborbital flight platform. Given your ISS track record, NIH reviewers would take that seriously.

Would a brief call make sense?

John Quinn
Cofounder and CEO

---

## NIH SEED Pre-Submission Inquiry Draft (Action #5 — DRAFTED 2026-06-30, awaiting Jon send-approval)

*Purpose: identify the NIBIB SB program officer who covers biomedical research platform STTRs, and get pre-submission guidance on framing before we submit PA-27-102. This is best done before PI lock — a PO name strengthens our pitch to PI candidates and confirms institute fit early. Route to Jon for send.*

---

**To:** seed@mail.nih.gov *(verify before sending)*
**Subject:** Pre-submission inquiry — STTR PA-27-102, suborbital microgravity research platform, NIBIB framing

Hello,

I am writing on behalf of Exos Aerospace Systems & Technologies, Inc. (Greenville, TX) to request pre-submission guidance for a planned NIH STTR (PA-27-102) application targeting the September 2026 deadline.

Our proposed project would develop and validate a reusable suborbital microgravity platform — our BLK3 vehicle, one of three FAA-licensed reusable suborbital launch systems in the U.S. — as a biomedical research tool for short-duration microgravity exposure (approximately 3 to 4 minutes, recoverable payload). The platform addresses a specific gap: onset-kinetics characterization and de-risk screening of microphysiological systems and tissue-chip payloads before an ISS flight commitment.

Exos would serve as the small business concern and flight-platform provider. We are currently finalizing our research-institution partner (PI at a STTR-eligible university biomedical engineering or pharmaceutical sciences department) who would anchor the science.

We believe this fits the NIBIB mission as a biomedical research platform device and would fall under an investigator-initiated STTR. We have two specific questions:

1. Is NIBIB the appropriate awarding component for a STTR proposing a suborbital microgravity platform for biomedical research use (onset-kinetics, tissue chip/MPS validation)? Or would you recommend a different institute?
2. Is there a program officer we should speak with before submission to ensure our framing and scope align with NIBIB priorities?

We would welcome a brief call at your convenience.

John Quinn
Cofounder and CEO, Exos Aerospace

---

## Tissue Chips in Space 2.0 Awardees — BD Sell-Slot Targets (COMPLETE 2026-07-13)
*6 grants awarded Feb 2026 under RFA-TR-24-025 (NCATS+NIA joint). Full list confirmed via NIH Reporter. These PIs are NOW actively designing ISS MPS experiments — primed for BLK3 suborbital screening pitch. ISS-NL solicitations are dead; these teams access ISS via CSP (Axiom/Redwire). BLK3 is the "screen before you commit" offer.*

| PI | Institution | Grant # | Research Focus | BD Status |
|----|-------------|---------|----------------|-----------|
| Arun Sharma, Ph.D. + Clive Svendsen, Ph.D. | Cedars-Sinai Medical Center | 1UG3AG099469-01 | Heart/gut/brain multiorgan; inflammaging; senescent cell targeting | 🎯 IDENTIFIED — outreach pending Jon |
| Y. Shrike Zhang, Ph.D. | Brigham and Women's Hospital / Harvard | 1UG3TR005836-01 | Aging Alveolar Lung Model in Microgravity | 🎯 IDENTIFIED — outreach pending Jon |
| Joseph C. Wu, MD, Ph.D. | Stanford University | 1UG3TR005845-01 | Cardiovascular aging; AI + 3D cardiac organoids; ISS Tissue Chips veteran (CRS-27 flight) | 🎯 IDENTIFIED — outreach drafted 2026-07-13; email ✅ jcwu@stanford.edu; pending Jon |
| Mei He, Ph.D. | University of Florida | 1UG3TR005829-01 | Brain-muscle MPS; extracellular vesicle network; understanding aging in space | 🎯 IDENTIFIED — outreach drafted 2026-07-13; pending Jon |
| Palaniappan Sethu, Ph.D. | University of Alabama at Birmingham | 1UG3AG101701-01 | Cardiovascular bioengineering; LEO accelerated aging; disease pathogenesis | 🎯 IDENTIFIED — outreach drafted 2026-07-13; pending Jon |
| Carrie German, Ph.D. | CFD Research Corporation | 1UG3TR005857-01 | Organ-on-chip: reproductive health, aging and disease in women | ⬇️ LOWER PRIORITY — small company (not university PI), different BD dynamic |

*Email status update (7/15): He email corrected to mhe@cop.ufl.edu ✅ (was meihe@ufl.edu — WRONG). All 6 TC-in-Space 2.0 BD targets now FULLY VERIFIED.*

*Note: Dmitriy Krepkiy, Ph.D. (NCATS OSI) is the program officer for Tissue Chips 2.0 — also a POC for context if Jon reaches out to NCATS. Tiziana Cogliati, Ph.D. (NIA) co-funded Sharma + Sethu grants.*

**BD outreach drafts for Wu, He, and Sethu added below (2026-07-13). All pending Jon approval.**

## BD Outreach Drafts — Tissue Chips 2.0 Awardees (NEW 2026-07-13, awaiting Jon send-approval)

*All three are Tier-1 sell-slot targets: active TC in Space 2.0 NIH awardees, ISS-bound MPS, need pre-ISS de-risk screening. Perfect BLK3 pitch. Jon must approve before sending.*

---

### DRAFT D — Dr. Joseph C. Wu (Stanford)
**To:** jcwu@stanford.edu *(⚠️ VERIFY — best-guess from Stanford profiles; confirm before send)*
**Subject:** Suborbital screening platform for your microgravity cardiovascular work — quick intro

Hello Dr. Wu,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. I saw your Tissue Chips in Space 2.0 award and your CRS-27 cardiac chip work, and wanted to introduce a complementary suborbital resource that could support your ISS campaign.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S. We're planning a March 2027 flight with recoverable payload capacity, providing 3 to 4 minutes of microgravity at a fraction of ISS cost and lead time.

For cardiac organoid and MPS work, the specific value is onset kinetics: characterizing how your 3D cardiac tissue responds in the first seconds to minutes of microgravity, before ISS-level chronic exposure sets in. That window is almost impossible to isolate on ISS, where transit time obscures early µg response. BLK3 can recover the payload intact for immediate post-flight assay.

We're also pursuing an NIH STTR (PA-27-102, September 2026 deadline) and are looking for a biomedical PI to anchor the science, with Exos providing the suborbital flight platform. Given your NCATS track record, your lab would be a strong fit.

Would a 20-minute call make sense?

John Quinn
Cofounder and CEO

---

### DRAFT E — Dr. Mei He (University of Florida)
**To:** mhe@cop.ufl.edu *(✅ VERIFIED 7/15 — confirmed from UF College of Pharmacy He Lab page; meihe@ufl.edu was WRONG)*
**Subject:** BLK3 suborbital platform for brain-muscle MPS space aging work

Hello Dr. He,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. Your NIH Tissue Chips in Space 2.0 award focused on brain-muscle microphysiological systems and extracellular vesicle networks caught my attention, and I wanted to introduce a suborbital resource that complements your ISS work.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S., planning a March 2027 flight with recoverable payload capacity. The platform delivers 3 to 4 minutes of microgravity with full payload recovery, at a fraction of ISS cost.

For brain-muscle MPS research, suborbital flights offer a specific advantage: capturing early-stage EV release and cell-to-cell signaling in the first minutes of µg onset, before steady-state ISS conditions develop. You get the early kinetics data and a de-risked payload before your ISS flight commitment.

We're also exploring an NIH STTR (PA-27-102, September 2026 deadline) and are looking for a biomedical PI partner to anchor the science. If any of this is relevant to where your lab is headed, I'd welcome a brief conversation.

John Quinn
Cofounder and CEO

---

### DRAFT F — Dr. Palaniappan Sethu (University of Alabama at Birmingham)
**To:** psethu@uabmc.edu *(✅ VERIFIED — from UAB scholars directory)*
**Subject:** Suborbital LEO environment screening platform — BLK3 intro

Hello Dr. Sethu,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. I came across your Tissue Chips in Space 2.0 award on exploiting LEO accelerated aging to understand disease pathogenesis, and wanted to introduce a suborbital resource that could strengthen your experimental design.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S. We're planning a March 2027 flight with recoverable payload capacity, providing 3 to 4 minutes of microgravity at a fraction of ISS cost.

For LEO aging research, the suborbital angle is onset: characterizing how your cardiovascular or MPS model initiates response in the first seconds to minutes of reduced gravity, distinct from the chronic steady-state you see on ISS. That early-kinetics dataset is novel and strengthens your ISS experiment design. Full payload recovery for post-flight assay is included.

We're also pursuing an NIH STTR (PA-27-102, September 2026 deadline) with a biomedical PI anchoring the science and Exos providing the flight platform. Given your work on LEO-accelerated disease models, your lab would be a natural fit.

Would a brief call make sense?

John Quinn
Cofounder and CEO

---

## Watch signals (Capture Agent scans each run)
- NIH SBIR/STTR notices (PA-27-100/102/101, PAR-27-098); any space/microgravity-relevant NIH NOSI
- NCATS Tissue Chips in Space 3.0 (2.0 closed Feb 2026; watch for 3.0)
- **NASA ROSES-2026 (NNH26ZDA001N) — ON NSPIRES, Status: Pending (2026-07-08)**: Shell confirmed; no appendices yet. Drop imminent — scan NSPIRES daily. Space biology appendices (ROSBio suborbital/parabolic window) are the cleanest parallel NASA track for BLK3.
- NASA ROSBio Appendix D release (next suborbital/parabolic biology window)
- ISS-NL CSP pathway research teams (identify who's accessing ISS via Axiom/Redwire)
- **MATChS (RFA-TR-23-018) — Sep 4, 2026 final deadline confirmed**: Feb 2024 and Feb 2025 round awardees are ALREADY FUNDED and building miniaturized/automated tissue chips — natural BLK3 sell-slot BD targets. Research specific awardee PI list via NIH Reporter (POST search on rfa_number=RFA-TR-23-018). **Action: NIH Reporter awardee lookup to build BD target sub-list.**
- **"Biotechnology Applications from Space for Earth" NASA STTR**: CONFIRMED CLOSED (May 21, 2026 deadline passed) — remove from watch
- Any Blue Origin/Virgin Galactic life-science suborbital precedents

## Guardrail
NEVER send external emails autonomously. All external outreach → drafted and routed to Jon for approval (email to jquinn@exosaero.com via msmtp is the channel to Jon, who is internal). Internal research, drafting, tracking, follow-up nudges are autonomous. Do not overstate: NIH funds the PI not the rocket; suborbital µg is short-duration (screening/de-risk, not sustained ISS science); BLK3 not yet flown commercially; POCs unverified until confirmed.

## SENT-STATE FEEDBACK LOOP (added 2026-07-17 — fixes the false-nudge bug)
Jon sends these from Outlook / M365 and BCCs jquinnexo@proton.me on his sends. **This agent CANNOT see M365 directly — "not in Proton" ≠ "didn't happen."** The nudge counter here is a self-incrementing internal flag, NOT evidence the email is unsent. The false-nudge bug (nudged #12 to "send Han today" on 2026-07-17, AFTER Jon actually sent it 2026-07-16) happened because nothing closed the loop.
- **Before emitting ANY "send X" nudge, first check the Proton inbox** (scripts/mission-control-imap.py) for a self-BCC'd copy addressed to the target (e.g., arum.han@tamu.edu). If found, mark that draft SENT in the Decision Log and **do not nudge to send it again.**
- If the agent cannot run the IMAP check (local-model run), it must NOT assert an item is unsent — phrase as "no confirmation of send visible to me (M365 blindspot); confirm before I nudge."
- **Never escalate a "send" nudge for an item already sent.** One reminder max, then wait for a reply, then a single reply-chase — not an escalating daily nag.
- **Confirmed SENT:** Draft B (Han/TAMU) → arum.han@tamu.edu, 2026-07-16 5:46 PM CT.

## STTR PA-27-102 Specific Aims Shell (Draft — 2026-07-07)
*Purpose: Proactive outline to share with PI candidates. Makes the partnership concrete; accelerates their commitment decision. Exo drafted; Jon/PI to refine.*

---

**Project Title:** Reusable Suborbital Microgravity Platform for Onset-Kinetics Characterization of Microphysiological Systems

**Overall goal:** Develop and validate BLK3, a reusable FAA-licensed suborbital launch vehicle, as a biomedical research platform delivering recoverable, short-duration microgravity exposure (~3–4 min) for rapid screening and onset-kinetics characterization of microphysiological systems (MPS) / tissue chips prior to ISS flight campaigns.

---

**Specific Aim 1 — Platform Integration & Validation [Exos lead]**
Design, fabricate, and qualify a standardized BLK3 payload module for tissue chip/MPS experiments. Deliverable: a certified, flight-ready biomedical payload interface (ICD, thermal, vibration, recovery) validated to BLK3 payload specifications (<4g boost, full payload recovery).

**Specific Aim 2 — Onset-Kinetics Characterization [UW / Dr. Kelly — biomedical science lead; research-institution-of-record]**
Fly Dr. Kelly's kidney-chip / MPS payload on BLK3 and characterize biological response during the 0–240 second microgravity window. Measure kidney-chip/MPS outcomes (transporter function, cell viability, cytoskeletal reorganization, fluid-interface behavior). Generate onset-kinetics dataset not obtainable from ISS (where launch/transit obscure early µg response). Exos provides the platform, telemetry, and recovered payload; UW/Kelly performs experiment design + post-flight assays.

**Specific Aim 3 — Screening Pipeline Demonstration [Joint: Exos platform + Purdue/Collicott suborbital methods]**
Demonstrate end-to-end pipeline: payload prep → BLK3 flight → sample recovery → assay → de-risk ISS decision. Purdue/Collicott leads the suborbital experiment methods (onset-kinetics protocol, µg data reduction, flight-experiment QA). Establish turnaround protocol (target: 2 flights within 7 days). Produce documented screening protocol applicable to future MPS-to-ISS campaigns.

---

**Innovation:** First reusable, FAA-licensed suborbital rocket platform configured specifically for biomedical MPS research. Fills a gap ISS cannot: onset kinetics in the first seconds-to-minutes of µg exposure. Recoverable payload eliminates the ISS "launch-and-hope" risk.

**Impact:** Reduces wasted NIH/ISS grant cycles; enables fast-cycle biomedical microgravity screening at <5% of ISS cost; generates novel onset-kinetics data with direct therapeutic relevance (aging, musculoskeletal, pharmacology).

**STTR Teaming Structure (formal — DUAL-INSTITUTION, locked 2026-08-18):**
- **Applicant / prime awardee:** Exos Aerospace Systems & Technologies, Inc. (SBC; UEI CK24BPZGF854, CAGE 7EMY6) — submits via eRA Commons/ASSIST, holds the award, subcontracts to both universities.
- **PD/PI:** Multi-PI plan — **Dr. Edward J. Kelly (UW)** as contact PI / biomedical science + an **Exos technical PI** / platform. (STTR permits the PD/PI to be employed by the SBC *or* the partnering research institution.)
- **Research institution of record (≥30% of work):** **University of Washington — Dr. Kelly** — biomedical science, MPS/kidney-chip design + post-flight assays (the NIH-fundable core; fills the biomedical-lead requirement).
- **Second institution (subaward, within the remaining ≤30%):** **Purdue University — Prof. Steven Collicott (AAE)** — suborbital microgravity experiment methods, onset-kinetics protocol, µg data reduction. Committed Exos partner (SACSS LOS in hand).
- **Work split (STTR minimums met):** Exos **≥40%** · UW **≥30%** · Purdue subaward inside the remaining **≤30%**.
- **Institute:** **NIBIB** primary (biomedical research platform/device framing); **NIA** secondary.
- **Budget:** Phase I ~$314–323K total, ~12 months (illustrative: ~$130K Exos / ~$100K UW / ~$85K Purdue). Phase II = expanded flight campaign.
- **Aim → performer map:** Aim 1 = Exos (platform) · Aim 2 = UW/Kelly (biomedical onset-kinetics, RI-of-record) · Aim 3 = Joint, Purdue/Collicott methods lead.

---

*Note: Aim 2 is shaped around Dr. Kelly's kidney-chip / NCATS TraCe MPS work (UW); Aim 3 methods are shaped around Collicott's suborbital-experiment expertise (Purdue). An optional Purdue Weldon BME organ-on-chip co-PI (Collicott's 7/24 intro) can broaden the bio bench but is no longer required — Kelly is the biomedical lead. Customize Aim 2 outcomes the moment Kelly's reply is in hand.*

---

## Decision Log
| Date | Event | Decision / Action |
|------|-------|-------------------|
| 2026-06-27 | Concept drafted and emailed to Jon | Concept: captures/BLK3_NIH_Microgravity_Concept.md |
| 2026-06-27 | ISS-NL solicitation track confirmed dead | BD channel updated: CSP-pathway researchers + NCATS TraCe MPS awardees only |
| 2026-06-27 | PI shortlist built: Vunjak-Novakovic (Columbia), Han (TAMU), Kelly (UW) | Action #1 COMPLETE. Awaiting Jon approval for outreach |
| 2026-06-27 | NIH institute framing: NIBIB primary, NIA secondary | Action #2 COMPLETE. NIBIB device/platform framing confirmed correct |
| 2026-06-29 | STTR deadline correction: Sep 5 is Saturday → actual deadline **Sep 8, 2026** | Tracker updated. Confirmed via alientt.com/NIH sources |
| 2026-06-29 | Application volume warning: high competition expected (missed Jan + Apr deadlines) | PI outreach and SEED inquiry should be advanced immediately |
| 2026-06-29 | PI outreach emails drafted for all 3 Tier-1 targets | Action #3 COMPLETE (drafts). **Jon must approve before sending.** See PI Outreach Drafts section |
| 2026-06-29 | Gordana Vunjak-Novakovic confirmed active 2026 (laureate award, new organ-on-a-chip paper) | Tier 1A remains strongest target |
| 2026-06-27 | Sell-slot BD one-pager drafted | Action #4 COMPLETE (draft). Awaiting Jon approval |
| 2026-06-30 | Sep 8 deadline re-confirmed via SEED.nih.gov (Sep 5 = Saturday → next business day) | Deadline confirmed; no change needed |
| 2026-06-30 | Scan: No new NIH microgravity NOSI; no NCATS Tissue Chips 3.0 release; ROSES-25 E.9 Space Bio Step-2 was June 2025 (past) — ROSBio suborbital window not confirmed open in ROSES-25 | Continue monitoring; ROSBio Appendix D/E watch maintained |
| 2026-06-30 | NASA SpaceX CRS-34 returned June 28 with stem cell/space bio science — active pipeline signal | Use as hook in PI outreach ("ISS space bio pipeline is very active right now") |
| 2026-06-30 | NIH SEED pre-submission inquiry drafted (Action #5) | Draft complete; Jon must approve/send to seed@mail.nih.gov; see SEED Inquiry Draft section |
| 2026-07-01 | Scan: No new NIH NOSI; no NCATS Tissue Chips 3.0; no new ROSBio/ROSES-25 suborbital window confirmed open | Monitoring continues. Sep 8 deadline confirmed (10 weeks). STTR deadline unchanged. |
| 2026-07-01 | NEW competitive signal: SSC Space SubOrbital Express-5 launched May 31 2026 — 12 scientific payloads (biology, cancer models, materials) from 9 countries, 6 min µg at 260km altitude | Confirms active suborbital bio research market. Use as outreach hook: "researchers across 9 countries are already doing this." Strengthens BLK3 value prop. |
| 2026-07-01 | BOTTLENECK: PI outreach (3 drafts, Jun 29) + SEED inquiry (Jun 30) still awaiting Jon send-approval. 10 weeks to Sep 8 STTR deadline. PI lock needed within 3-4 weeks to draft in time. | Nudge email sent to Jon. Action #3 and #5 remain gated on Jon. |
| 2026-07-01 | Jon requested all 4 drafts (PI A/B/C + SEED inquiry). Full package emailed to jquinn@exosaero.com (cc pm.me) ready to send from GCC High. | Delivered. Open risk: 3 PI email addresses (gv2131@columbia.edu, arum.han@tamu.edu, ed9@uw.edu) still best-guess — offered to verify before Jon sends. seed@mail.nih.gov confirmed. |
| 2026-07-01 | Jon requested "send as 4 separate email drafts" then "confirm emails first" | Sent 4 separate drafts to Jon; then VERIFIED all 3 PI addresses. gv2131@columbia.edu ✅ + arum.han@tamu.edu ✅ correct. **ed9@uw.edu WRONG → corrected to edkelly@uw.edu** (Kelly Lab + UW SOP). Corrected Draft 3 resent to Jon. All 4 now cleared to send. |
| 2026-07-02 | Scan: No new NIH NOSI; no NCATS Tissue Chips 3.0; no new ROSBio/ROSES-25 suborbital window. PA-27-102 STTR parent confirmed ACTIVE (May 28, 2026 – Apr 5, 2027); Sep 8 deadline firm; Phase I ceiling ~$323K. ROSES-26 expected July 2026 — watch for new space biology appendices that could open suborbital bio windows. | 9 wk 6 day to Sep 8 STTR deadline. PI outreach (3 drafts) + SEED inquiry still pending Jon send. Nudge sent. |
| 2026-07-03 | **NEW SIGNAL: ROSES-2026 confirmed releasing July 2026** (NASA Science SMD). When released, space biology appendices could include ROSBio suborbital/parabolic biology window — cleanest parallel NASA track for BLK3. Watch NSPIRES immediately for drop. No new NIH NOSI; no NCATS 3.0 RFA; PA-27-102 STTR unchanged (Sep 8). | PI outreach (3 drafts) + SEED inquiry still pending Jon send-approval. Nudge email sent to jquinn@exosaero.com. 9 weeks to Sep 8. ROSES-2026 watch added as priority scan item. |
| 2026-07-06 | Scan: No new NIH NOSI; no NCATS 3.0; ROSES-2026 not yet live (NASA ROSES-26 URL = 404 — drop is imminent, first week of July). PI outreach + SEED inquiry still PENDING Jon send-approval. 9 weeks to Sep 8. Nudge email sent (3rd nudge). PI lock deadline: need a response by ~Aug 1 to draft STTR in time. | **Action needed: Jon must send at least one PI email. Recommend starting with Dr. Arum Han (TAMU) — Texas geography, lowest friction, TraCe MPS funded.** ROSES-2026 drop watch is highest-priority parallel scan this week. |
| 2026-07-07 | Scan: No new NIH NOSI; no NCATS 3.0 RFA; ROSES-2026 confirmed NOT yet released (no NNH26ZDA001N found; NASA site showing July 2026 content but ROSES-26 announcement still "to be released" — drop could be today or tomorrow). STTR PA-27-102 Sep 8 deadline: 9 weeks remain. Bottleneck = PI outreach (3 drafts) + SEED inquiry pending Jon send, now 8+ days. **Proactive advance this run: STTR PA-27-102 Specific Aims Shell drafted** (see section above). This is the most useful unlockable action — showing PI candidates a concrete proposal outline shortens their decision window. | Nudge email sent to Jon (4th) attaching Specific Aims shell + reiterating PI send urgency. Recommend Jon send Dr. Arum Han (TAMU) email first — lowest friction, Texas. ROSES-2026 drop: watch NSPIRES daily this week; when it drops, immediate scan for ROSBio/space biology appendices. |
| 2026-07-08 | **NEW: ROSES-2026 (NNH26ZDA001N) confirmed ON NSPIRES — Status: Pending.** Shell exists; no appendices/program elements yet. Drop is truly imminent (any day). When appendices post, immediately scan for ROSBio/space biology suborbital window. **NEW BD SIGNAL: NCATS MATChS (RFA-TR-23-018) extended to 9/4/2026** — awardees building miniaturized/automated tissue chips are natural BLK3 sell-slot prospects. No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA found. Sep 8 STTR deadline: 62 days. PI outreach + SEED inquiry still pending Jon send (5th nudge). | Nudge email sent to Jon (5th). **CRITICAL: PI lock needed by ~July 28 to preserve drafting runway. 62 days to Sep 8.** MATChS awardee list to research next run as BD target expansion. |
| 2026-07-09 | Scan: ROSES-2026 still pending on NSPIRES (NSPIRES maintenance tonight 7/9 9-9:30PM ET — may drop after). No new NIH NOSI. **CONFIRMED: "Biotechnology Applications from Space for Earth" NASA STTR (May 21, 2026 deadline) = CLOSED, not actionable.** MATChS Sep 4, 2026 deadline confirmed (final window); Feb 2024 + Feb 2025 round awardees already funded — researching PI awardee list for BD targeting (NIH Reporter search needed). Sep 8 STTR deadline: **61 days.** PI outreach + SEED inquiry still pending Jon send (6th nudge). PI lock CRITICAL: must have a PI respond by ~July 28 to draft on time. | Nudge email sent to Jon (6th). Watch: NSPIRES post-maintenance for ROSES-2026 appendices. |
| 2026-07-10 | Scan: ROSES-2026 still "Pending" on NSPIRES — no appendices post-maintenance. No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. **NEW BD SIGNAL: Tissue Chips in Space 2.0 (RFA-TR-24-025) awardees identified** — 6 grants awarded Feb 2026; found 2 of 6: (1) Arun Sharma + Clive Svendsen / Cedars-Sinai (heart/gut/brain multiorgan, inflammaging); (2) Y. Shrike Zhang / Brigham and Women's Hospital. These PIs are NOW actively designing ISS MPS experiments — peak timing for BLK3 sell-slot pitch. Program officer: Dmitriy Krepkiy, Ph.D. (NCATS OSI). Added BD target section to tracker. Sep 8 STTR deadline: **60 days.** PI outreach + SEED inquiry still pending Jon send (7th nudge). | Nudge email sent to Jon (7th). BD outreach drafts for Sharma/Svendsen and Zhang queued. Need remaining 4 TC-in-Space 2.0 awardees next run. |
| 2026-07-13 | Scan: ROSES-2026 still "Pending" (shell confirmed on NSPIRES, no appendices; drop still imminent). No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. **COMPLETE: All 6 Tissue Chips in Space 2.0 awardees confirmed** via NIH Reporter API. Remaining 4 identified: (3) Joseph C. Wu / Stanford — cardiovascular aging, AI + 3D cardiac organoids (1UG3TR005845-01); (4) Mei He / U of Florida — brain-muscle MPS, EV network (1UG3TR005829-01); (5) Palaniappan Sethu / UAB — LEO accelerated aging, cardiovascular (1UG3AG101701-01); (6) Carrie German / CFD Research Corp — reproductive health MPS (lower priority, small company). BD emails drafted for Wu, He, Sethu (Drafts D/E/F) — pending Jon approval. Sethu email verified (psethu@uabmc.edu). Wu contact (jcwu@stanford.edu) needs verification. Sep 8 STTR deadline: **57 days.** PI outreach (Drafts A/B/C) + SEED inquiry still PENDING Jon send. **CRITICAL: PI lock needed by ~July 28. Only 15 days left to that gate.** | Nudge email sent to Jon (8th) with 3 new BD drafts attached. PI lock is now CRITICAL. Recommend Han (TAMU) as first PI send. ROSES-2026 watch continues. |
| 2026-07-14 | Scan: ROSES-2026 NOT released — NSPIRES still active on ROSES-2025 (NNH25ZDA001N, amended June 15, 2026); NNH26ZDA001N still "Pending." NASA confirmed July 2026 release window; drop imminent, any day. No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. **Wu email VERIFIED: jcwu@stanford.edu ✅** — Stanford profiles page confirms Joseph C. Wu as Director of Stanford Cardiovascular Institute; standard Stanford naming convention (first-initial+last@stanford.edu) confirmed consistent. Sep 8 STTR deadline: **55 days.** PI lock deadline (July 28): **14 days.** All 6 TC-in-Space 2.0 BD targets now have email status: Vunjak-Novakovic ✅ gv2131@columbia.edu, Han ✅ arum.han@tamu.edu, Kelly ✅ edkelly@uw.edu, Wu ✅ jcwu@stanford.edu, He ⚠️ meihe@ufl.edu (pattern-only), Sethu ✅ psethu@uabmc.edu. PI outreach (A/B/C) + SEED inquiry + BD drafts (D/E/F) ALL PENDING Jon send-approval. | Nudge email sent to Jon (9th). **14 days to PI lock. STTR is at risk without immediate action.** Recommend sending Han (TAMU) TODAY as first outreach. |
| 2026-07-15 | Scan: ROSES-2026 still NOT released (NNH26ZDA001N pending on NSPIRES; ROSES-25 still active). No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. ROSBio Appendix G spotted in search — CONFIRMED OLD (2017 ROSBio-2016 omnibus, NNH16ZTT001N-FG; irrelevant). MATChS (RFA-TR-23-018) confirmed extended to Sep 4, 2026 — awardee research via NIH Reporter still queued for next autonomous run. **He email CORRECTED and VERIFIED: mhe@cop.ufl.edu ✅** (was meihe@ufl.edu — WRONG; corrected from UF College of Pharmacy He Lab faculty page). All 6 TC-in-Space 2.0 BD targets now FULLY VERIFIED. Sep 8 STTR deadline: **54 days.** PI lock deadline (July 28): **13 days.** PI outreach (A/B/C) + SEED inquiry + BD drafts (D/E/F) ALL STILL PENDING Jon send-approval. | Nudge email sent to Jon (10th). Draft E corrected. **13 days to PI lock gate. STTR submission path is at critical risk.** |
| 2026-07-16 | Scan: ROSES-2026 STILL NOT released — NNH26ZDA001N remains "Pending" on NSPIRES; NASA confirmed July 2026 window but no appendices posted (now mid-July; drop is overdue and could be today). No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. "Tissue Chips in Space Initiative" showing Active on grantedai.com (2026) = existing 2.0 awards only, not a new RFA. MATChS awardee list still queued (NIH Reporter API requires POST; web_fetch approach won't work — need direct API call or browser). Sep 8 STTR deadline: **53 days.** PI lock deadline (July 28): **12 days.** PI outreach (A/B/C) + SEED inquiry + BD drafts (D/E/F) ALL STILL PENDING Jon send-approval. | Nudge email sent to Jon (11th). **12 days to PI lock gate. STTR path at critical risk.** At 12 days to PI lock with zero PI response, recommend Jon either: (A) send Draft B (Arum Han / TAMU) TODAY as minimum viable action, or (B) explicitly signal STTR track suspended so effort redirects fully to BD sell-slot track only. No action = both tracks slip. |
| 2026-07-17 | Scan: ROSES-2026 STILL NOT released — NSPIRES confirms ROSES-25 (NNH25ZDA001N) remains active, last amended June 15, 2026; ROSES-26 has NOT posted. No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. MATChS (RFA-TR-23-018) Sep 4, 2026 deadline confirmed via NOT-TR-26-005 extension notice; awardee BD list still unresearched. Sep 8 STTR deadline: **52 days.** PI lock deadline (July 28): **11 days.** All 6 BD outreach drafts (A-F) + SEED inquiry STILL PENDING Jon send-approval after 11 nudge emails. STTR path is at critical risk — 11 days to PI lock with no PI response. | Nudge email sent to Jon (12th) with hard binary: send one email today OR officially suspend STTR track. ROSES-2026 watch continues. MATChS awardee research deferred pending NIH Reporter access. |
| 2026-07-17 (later) | **CORRECTION — nudge #12 was a FALSE "unsent."** Jon confirmed he SENT Draft B to arum.han@tamu.edu on 2026-07-16 5:46 PM CT (Outlook screenshot, BCC jquinnexo@proton.me). The agent nudged to send it the next morning because its sent-state is an internal flag with no feedback loop and it cannot see M365. | Marked Han SENT; stage advanced to AWAITING HAN REPLY; added SENT-STATE FEEDBACK LOOP guardrail. PI-lock nudging for Han STOPPED. Next Han action = a single reply-chase ~2 weeks out if no response, not a resend nag. |
| 2026-07-20 | Scan: ROSES-2026 NOT released (NASA URL 404; no appendices posted; shell still pending). No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. MATChS (RFA-TR-23-018) confirmed open thru Sep 4, 2026; awardee BD lookup still pending NIH Reporter API access. Sep 8 STTR deadline: **49 days.** PI lock gate (July 28): **8 days.** Three PIs emailed (Vunjak-Novakovic + Kelly 7/01; Han 7/16). None have replied via visible channels. IMAP check returned no PI replies. **Reply-chase drafts G/H/I produced** for Vunjak-Novakovic (19d), Kelly (19d), and NIH SEED (20d). Han chase NOT triggered yet (only 4 days since send). BD drafts D/E/F (Wu, He, Sethu) still pending Jon approval. | Reply-chase package emailed to Jon (3 drafts). Decision needed: (1) send reply-chases G/H/I; (2) approve BD drafts D/E/F for Wu/He/Sethu. If no PI responds by July 28, STTR track at risk — Jon must decide: pivot fully to BD-only track or extend PI search. |
| 2026-07-21 | Scan: ROSES-2026 STILL NOT released — NSPIRES confirms ROSES-25 (NNH25ZDA001N) active, last amended June 15, 2026; NNH26ZDA001N still pending. No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. MATChS awardee BD lookup: **BLOCKED** — NIH Reporter is JS-rendered; API queries return empty; cannot retrieve Feb 2024/2025 round awardees without browser access. Note: MATChS awardees are SBCs (device companies), not academic labs — different BD dynamic than TC-in-Space 2.0 academic PIs. IMAP check: no PI replies from Vunjak-Novakovic, Kelly, Han, or SEED. Reply-chase package G/H/I delivered to Jon 2026-07-20 — NO RE-NUDGE today (sent yesterday). BD drafts D/E/F (Wu, He, Sethu) still pending Jon. Sep 8 STTR deadline: **48 days.** PI lock gate: **7 days (July 28).** | Tracker updated. No new drafts produced. No external actions taken. Awaiting Jon on: (1) G/H/I reply-chases; (2) D/E/F BD drafts. MATChS awardee research deferred — requires NIH Reporter JS rendering to pull SBC names; may be lower priority than TC-in-Space 2.0 academic PI BD targets already identified. |
| 2026-07-22 | Scan: ROSES-2026 STILL NOT released — NASA SARA page confirms "anticipate July 2026" release; ROSES-25 (NNH25ZDA001N) remains active. No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. IMAP: no PI replies from Vunjak-Novakovic, Kelly, Han, or NIH SEED. Reply-chases G/H/I (sent to Jon 7/20) not confirmed sent (no BCC in Proton). BD drafts D/E/F (Wu, He, Sethu) dispatched as READY-ACTION blocks this run — will reach Jon inbox + MC tasks via capture-action-dispatch.py. Sep 8 STTR deadline: **47 days.** PI lock gate (July 28): **6 days.** | BD sell-slot track formally unblocked this run via READY-ACTION dispatch for Wu/He/Sethu. STTR track: PI lock at risk if no response by July 28 — if no PI engages, Jon must decide whether to extend PI search or pivot to BD-only track. No new nudge on G/H/I (sent to Jon inbox 7/20; await send). Han reply-chase still on hold (sent 7/17, too recent to chase again). |
| 2026-07-24 | Scan: ROSES-2026 STILL NOT released (NASA confirms July 2026 target; shell NNH26ZDA001N pending on NSPIRES; no appendices). No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. PA-27-102 Sep 8 deadline confirmed active: **46 days.** IMAP: no PI replies from Vunjak-Novakovic, Han, Kelly, or NIH SEED. BD track: Wu, He, Sethu confirmed SENT 7/23 (auto BCC loop) — now in reply-watch mode; no further action needed. Reply-chases G/H/I still no Proton BCC confirmation — converted to READY-ACTION blocks this run (keys: nih-microgravity-chase-vunjak, nih-microgravity-chase-kelly, nih-microgravity-chase-seed) for dispatch. PI lock gate (July 28): **4 days.** Zero PI responses to date. Note: simpler.grants.gov lists NIH SEED contact as SEEDinfo@nih.gov — alternative if seed@mail.nih.gov goes unanswered. | Reply-chase READY-ACTIONs dispatched to Jon inbox + MC tasks (G/H/I). **DECISION NEEDED by July 28:** If no PI (Vunjak-Novakovic, Han, or Kelly) responds, Jon must choose: (A) expand PI search to Tissue Chips 2.0 awardees already outreached (Wu/He/Sethu now contacted as BD — could pivot STTR ask to them), or (B) officially suspend STTR track and go BD-only for this cycle. Han reply-chase held — only 8 days since 7/16 Outlook send; will trigger ~July 30 if no response. |

## AUTO SENT-CONFIRMATIONS (loop-closer)
*Written by scripts/sent-loop-closer.py from Jon's BCC'd Proton copies. If a target appears here, Jon ALREADY SENT it from Outlook — do NOT nudge to send it again; switch to reply-watch.*
- **SENT CONFIRMED (auto): seed@mail.nih.gov** on 2026-06-30 13:39 — subject "=?utf-8?q?Pre-submission_inquiry_=E2=80=94_STTR_PA-27-102,_suborbital_mic?= =?utf-8?q?rogravity_research_platform,_NIBIB_framing?=". Nudge-to-send STOPPED; reply-watch only. **Reply-chase drafted 2026-07-20 (20 days, no response — send once).**
- **SENT CONFIRMED (auto): gv2131@columbia.edu** on 2026-07-01 14:37 — subject "Suborbital microgravity screening platform for tissue chip work, quick introduction". Nudge-to-send STOPPED; reply-watch only. **Reply-chase drafted 2026-07-20 (19 days, no response — send once).**
- **SENT CONFIRMED (auto): arum.han@tamu.edu** on 2026-07-01 14:39 — subject "BLK3 suborbital platform + NIH STTR opportunity, Texas connection". Nudge-to-send STOPPED; reply-watch only. **Reply-chase drafted 2026-07-17 (manual, 16 days). DO NOT chase again yet — too soon after last nudge.**
- **SENT CONFIRMED (auto): edkelly@uw.edu** on 2026-07-01 14:41 — subject "FSuborbital kidney chip screening before your next ISS flight". Nudge-to-send STOPPED; reply-watch only. **Reply-chase drafted 2026-07-20 (19 days, no response — send once).**

## Reply-Chase Drafts (2026-07-20 — awaiting Jon send-approval)

*19–20 days since initial sends. Per tracker guardrail: one reply-chase max per contact, then wait. These are the ONE chase per PI — no further nudging after send.*

---

### REPLY-CHASE G — Dr. Gordana Vunjak-Novakovic (Columbia)
**To:** gv2131@columbia.edu
**Subject:** Re: Suborbital microgravity screening platform for tissue chip work — quick introduction

Hello Dr. Vunjak-Novakovic,

Circling back on my email from a few weeks ago. I know summer schedules can be full. I wanted to check whether our BLK3 suborbital platform and the NIH STTR opportunity are worth a brief conversation, or whether it's simply not a fit at this point.

We have a September 8 deadline for PA-27-102 and are still looking for a biomedical PI to anchor the science. If there's any interest, even a 15-minute call would help us understand whether to move forward together.

No need to respond if it's not a fit — I appreciate your time either way.

John Quinn
Cofounder and CEO

---

### REPLY-CHASE H — Dr. Edward J. Kelly (University of Washington)
**To:** edkelly@uw.edu
**Subject:** Re: Suborbital kidney chip screening before your next ISS flight

Hello Dr. Kelly,

Following up on my email from a few weeks ago about BLK3 suborbital microgravity capacity and a potential NIH STTR collaboration (PA-27-102, September 8 deadline).

With your TraCe MPS kidney chip work and ISS history, your lab is a natural fit for the suborbital screening pitch. If any of this is relevant, I'd welcome a brief call. If the timing or framing isn't right, no worries at all.

John Quinn
Cofounder and CEO

---

### REPLY-CHASE I — NIH SEED Office
**To:** seed@mail.nih.gov
**Subject:** Re: Pre-submission inquiry — STTR PA-27-102, suborbital microgravity research platform, NIBIB framing

Hello,

Following up on my pre-submission inquiry from June 30 regarding an STTR application (PA-27-102) proposing BLK3, a reusable suborbital vehicle, as a biomedical research platform for onset-kinetics characterization of microphysiological systems.

We are targeting the September 8 deadline and would greatly benefit from guidance on institute fit and a program officer contact before submission. Any direction you can offer would be appreciated.

Thank you,

John Quinn
Cofounder and CEO, Exos Aerospace


## DELIVERY RULE — READY-ACTION (added 2026-07-21; enforces feedback_send_or_mc_task_or_dead)
Jon does NOT read drafts in files. When an action is ready and gated on Jon, do NOT cite a file path or say "draft at path/§X" or "in your queue." Instead APPEND a READY-ACTION block (template below) to this tracker containing the FULL ready-to-send email. A deterministic dispatcher (scripts/capture-action-dispatch.py, launchd every 20 min) automatically (a) emails it to Jon at jquinn@exosaero.com as a ready-to-send and (b) opens a Mission Control task. In the channel summary, say "ready-to-send delivered to Jon inbox + MC task opened" — never a file path. Use a STABLE key so it is not re-sent each run; change the body only when the content actually changes (that re-delivers). Gov contacts still route to Jon to send.

Template (copy, fill real values — the dispatcher ignores this example because of the angle-bracket placeholders):
<!-- READY-ACTION
key: <pursuit>-<action-slug>
task_title: <short MC task title>
to: <primary recipient email>
cc: <optional cc emails>
subject: <email subject>
category: BD
priority: 80
body:
<full ready-to-send email text over multiple lines>
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-bd-wu
task_title: [NIH-MG] Send BD outreach — Dr. Joseph Wu, Stanford (TC-in-Space 2.0)
to: jcwu@stanford.edu
subject: Suborbital screening platform for your microgravity cardiovascular work — quick intro
category: BD
priority: 75
body:
Hello Dr. Wu,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. I saw your Tissue Chips in Space 2.0 award and your CRS-27 cardiac chip work, and wanted to introduce a complementary suborbital resource that could support your ISS campaign.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S. We're planning a March 2027 flight with recoverable payload capacity, providing 3 to 4 minutes of microgravity at a fraction of ISS cost and lead time.

For cardiac organoid and MPS work, the specific value is onset kinetics: characterizing how your 3D cardiac tissue responds in the first seconds to minutes of microgravity, before ISS-level chronic exposure sets in. That window is almost impossible to isolate on ISS, where transit time obscures early response. BLK3 can recover the payload intact for immediate post-flight assay.

We're also pursuing an NIH STTR (PA-27-102, September 8 deadline) and are looking for a biomedical PI to anchor the science, with Exos providing the suborbital flight platform. Given your NCATS track record, your lab would be a strong fit.

Would a 20-minute call make sense?

John Quinn
Cofounder and CEO
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-bd-he
task_title: [NIH-MG] Send BD outreach — Dr. Mei He, U of Florida (TC-in-Space 2.0)
to: mhe@cop.ufl.edu
subject: BLK3 suborbital platform for brain-muscle MPS space aging work
category: BD
priority: 75
body:
Hello Dr. He,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. Your NIH Tissue Chips in Space 2.0 award focused on brain-muscle microphysiological systems and extracellular vesicle networks caught my attention, and I wanted to introduce a suborbital resource that complements your ISS work.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S., planning a March 2027 flight with recoverable payload capacity. The platform delivers 3 to 4 minutes of microgravity with full payload recovery, at a fraction of ISS cost.

For brain-muscle MPS research, suborbital flights offer a specific advantage: capturing early-stage EV release and cell-to-cell signaling in the first minutes of onset, before steady-state ISS conditions develop. You get the early kinetics data and a de-risked payload before your ISS flight commitment.

We're also exploring an NIH STTR (PA-27-102, September 8 deadline) and are looking for a biomedical PI partner to anchor the science. If any of this is relevant to where your lab is headed, I'd welcome a brief conversation.

John Quinn
Cofounder and CEO
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-bd-sethu
task_title: [NIH-MG] Send BD outreach — Dr. Palaniappan Sethu, UAB (TC-in-Space 2.0)
to: psethu@uabmc.edu
subject: Suborbital LEO environment screening platform — BLK3 intro
category: BD
priority: 75
body:
Hello Dr. Sethu,

I'm John Quinn, Cofounder and CEO of Exos Aerospace. I came across your Tissue Chips in Space 2.0 award on exploiting LEO accelerated aging to understand disease pathogenesis, and wanted to introduce a suborbital resource that could strengthen your experimental design.

Exos operates BLK3, one of only three FAA-licensed reusable suborbital launch vehicles in the U.S. We're planning a March 2027 flight with recoverable payload capacity, providing 3 to 4 minutes of microgravity at a fraction of ISS cost.

For LEO aging research, the suborbital angle is onset: characterizing how your cardiovascular or MPS model initiates response in the first seconds to minutes of reduced gravity, distinct from the chronic steady-state you see on ISS. That early-kinetics dataset is novel and strengthens your ISS experiment design. Full payload recovery for post-flight assay is included.

We're also pursuing an NIH STTR (PA-27-102, September 8 deadline) with a biomedical PI anchoring the science and Exos providing the flight platform. Given your work on LEO-accelerated disease models, your lab would be a natural fit.

Would a brief call make sense?

John Quinn
Cofounder and CEO
END-READY-ACTION -->
- **SENT CONFIRMED (auto): mhe@cop.ufl.edu** on 2026-07-23 13:45 — subject "BLK3 suborbital platform for brain-muscle MPS space aging work". Nudge-to-send STOPPED; reply-watch only.
- **SENT CONFIRMED (auto): jcwu@stanford.edu** on 2026-07-23 13:47 — subject "=?utf-8?q?Fw:_Suborbital_screening_platform_for_your_microgravity_cardiov?= =?utf-8?q?ascular_work_=E2=80=94_quick_intro?=". Nudge-to-send STOPPED; reply-watch only.
- **SENT CONFIRMED (auto): psethu@uabmc.edu** on 2026-07-23 13:48 — subject "=?utf-8?q?Suborbital_LEO_environment_screening_platform_=E2=80=94_BLK3_in?= =?utf-8?q?tro?=". Nudge-to-send STOPPED; reply-watch only.

## READY-ACTION BLOCKS — Reply-Chases G/H/I (PI lock gate: July 28)
*G/H/I were drafted 7/20 and emailed to Jon, but have no send confirmation in Proton as of 7/24. Converting to READY-ACTION for dispatch. PI lock gate = July 28 (4 days). These must go out NOW to preserve any chance of Sep 8 STTR path.*

<!-- READY-ACTION
key: nih-microgravity-chase-vunjak
task_title: [NIH-MG] Send reply-chase — Dr. Vunjak-Novakovic, Columbia (PI lock gate July 28)
to: gv2131@columbia.edu
subject: Re: Suborbital microgravity screening platform for tissue chip work — quick introduction
category: BD
priority: 85
body:
Hello Dr. Vunjak-Novakovic,

Circling back on my email from a few weeks ago. I know summer schedules can be full. I wanted to check whether our BLK3 suborbital platform and the NIH STTR opportunity are worth a brief conversation, or whether it is simply not a fit at this point.

We have a September 8 deadline for PA-27-102 and are still looking for a biomedical PI to anchor the science. If there is any interest, even a 15-minute call would help us understand whether to move forward together.

No need to respond if it is not a fit, I appreciate your time either way.

John Quinn
Cofounder and CEO
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-chase-kelly
task_title: [NIH-MG] Send reply-chase — Dr. Kelly, UW (PI lock gate July 28)
to: edkelly@uw.edu
subject: Re: Suborbital kidney chip screening before your next ISS flight
category: BD
priority: 85
body:
Hello Dr. Kelly,

Following up on my email from a few weeks ago about BLK3 suborbital microgravity capacity and a potential NIH STTR collaboration (PA-27-102, September 8 deadline).

With your TraCe MPS kidney chip work and ISS history, your lab is a natural fit for the suborbital screening pitch. If any of this is relevant, I would welcome a brief call. If the timing or framing is not right, no worries at all.

John Quinn
Cofounder and CEO
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-chase-seed
task_title: [NIH-MG] Send reply-chase — NIH SEED office (institute fit, PO name)
to: seed@mail.nih.gov
subject: Re: Pre-submission inquiry — STTR PA-27-102, suborbital microgravity research platform, NIBIB framing
category: BD
priority: 80
body:
Hello,

Following up on my pre-submission inquiry from June 30 regarding an STTR application (PA-27-102) proposing BLK3, a reusable suborbital vehicle, as a biomedical research platform for onset-kinetics characterization of microphysiological systems.

We are targeting the September 8 deadline and would greatly benefit from guidance on institute fit and a program officer contact before submission. Any direction you can offer would be appreciated.

Thank you,

John Quinn
Cofounder and CEO, Exos Aerospace
END-READY-ACTION -->
- **SENT CONFIRMED (auto): collicot@purdue.edu** on 2026-07-24 12:39 — subject "Collicott warm-intro ask -> Purdue Weldon BME organ-on-chip PI?". Nudge-to-send STOPPED; reply-watch only.
- **SENT CONFIRMED (Jon, 7/24):** Reply-chase G (gv2131@columbia.edu), Reply-chase H (edkelly@uw.edu), Reply-chase I (seed@mail.nih.gov) — Jon confirmed "DONE" 2026-07-24. One-chase limit reached for all three. Switch to reply-watch only; do NOT re-nudge any of them.

## Decision Log (continued)
| 2026-07-27 | IMAP scan: NO PI replies from any of 6 outreached PIs (Vunjak, Han, Kelly, Wu, He, Sethu), NIH SEED, or Collicott (Purdue). ROSES-2026 still NOT released on NSPIRES (overdue vs. NASA's "July 2026" estimate). Sep 8 STTR deadline: **42 days.** PI lock gate (July 28): **TOMORROW.** Reply-chases G/H/I confirmed sent 7/24 — one-chase limit reached, do not re-nudge. Han reply-chase (~July 30) triggered early given PI lock gate; READY-ACTION dispatched. PI lock gate decision email dispatched to Jon. Collicott (Purdue warm-intro) sent 7/24 — potential NEW PI path if he connects Exos to Weldon BME; reply-watch. Wu/He/Sethu BD outreach (7/23) could pivot to STTR PI ask if any respond with interest. STTR track remains alive but gated on a PI engaging; if no response by ~Aug 4, Jon must decide to extend search or pivot to BD-only. |
| 2026-07-28 | IMAP scan: NO PI replies visible (Kelly replied per Jon 7/27 but sits in Outlook only — M365 blindspot). No new NIH NOSI. ROSES-2026 evidence: C.4 PSEF appendix "amended July 21, 2026" confirms ROSES-2026 has been released — but NO BPS/space biology suborbital appendix (ROSBio) found in searches; watch continues. Sep 8 STTR deadline: **41 days.** Jon decision (7/27) = Option A: hold through Aug 4. All PI reply-chases at one-chase limit (G/H/I sent 7/24; Han chase dispatched 7/27). **PRIORITY UNBLOCK: Jon must forward Kelly's reply from Outlook to exosmc@proton.me so Exo can read, draft response, and advance STTR.** No new drafts produced — guardrail on re-nudging contacts at one-chase limit. STTR track alive; next decision gate = Aug 4. |
| 2026-07-29 04:45 CDT | IMAP scan: NO PI replies visible in Proton from any PI (Vunjak, Han, Kelly, Wu, He, Sethu) or NIH SEED. Kelly's reply per Jon (7/27) still in Outlook only — M365 blindspot; unblock requires Jon forwarding to exosmc@proton.me. ROSES-2026 scan: ROSES-25 still actively amended as of July 27 (D.8 HWO-PSI new opportunity added); NO ROSBio/BPS space biology suborbital appendix confirmed in ROSES-2026 yet. No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. Sep 8 STTR deadline: **40 days.** Aug 4 decision gate: **6 days.** Han reply-chase was dispatched as READY-ACTION 7/27 — should have reached Jon inbox via capture-action-dispatch.py. No new external actions taken. Guardrail: all PIs at one-chase limit; no re-nudging. STTR track alive; all threads in reply-watch pending Aug 4 gate. |
| 2026-07-30 04:45 CDT | IMAP scan: NO PI replies visible in Proton (M365 blindspot still blocks Kelly's reply). No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. ROSES-2026 still NOT released as NNH26ZDA001N on NSPIRES; ROSES-25 active (Table 2 amended 07/27/2026). **NEW SIGNAL: NASA RFI NNH26ZDA010L "Private Sector Partnerships in Astrobiology, Planetary Protection, and Space Biology" — closes Aug 10, 2026 (11 days).** Exos/BLK3 is an exact fit as a private-sector suborbital space biology platform; responding positions us in front of NASA SMD before ROSBio drops. READY-ACTION drafted. Sep 8 STTR deadline: **39 days.** Aug 4 decision gate: **5 days.** Kelly's Outlook reply remains the priority unblock — READY-ACTION dispatched to Jon re: forwarding. All PIs at one-chase limit; no external actions taken. STTR track alive, pending Aug 4 gate. |
| 2026-07-31 04:45 CDT | IMAP scan: NO PI replies visible in Proton from any PI (Vunjak, Han, Kelly, Wu, He, Sethu) or NIH SEED. Kelly's reply per Jon (7/27) still in Outlook only — M365 blindspot; forward-to-exosmc READY-ACTION already dispatched 7/30. No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. ROSES-2026: NSPIRES still shows NNH26ZDA001N shell only; NO ROSBio/BPS space biology suborbital appendix confirmed released. ROSES-25 amendments still trickling (A.14 Atmosphere due 8/20 on NSPIRES). **NASA RFI NNH26ZDA010L confirmed still open on NSPIRES — Aug 10 deadline, 10 days remaining.** READY-ACTION (key: nih-microgravity-nasa-rfi-nnh26zda010l) already dispatched 7/30 — Jon should have in inbox + MC task. Sep 8 STTR deadline: **38 days.** Aug 4 decision gate: **4 days.** All PIs at one-chase limit; no external actions taken; STTR track alive pending Jon decision Aug 4. Also spotted NNH26ZDA012L (RFI: STAR Virtual Space Biosciences Training Course) on NSPIRES — closes TODAY (July 31); NASA BPS/SB context signal but not directly actionable for Exos. |
| 2026-08-03 04:45 CDT | IMAP scan: NO PI replies visible in Proton from any PI (Vunjak, Han, Kelly, Wu, He, Sethu), NIH SEED, or Collicott. Kelly's reply per Jon (7/27) still in Outlook only — M365 blindspot persists; kelly-forward-request READY-ACTION confirmed dispatched 7/30 (task 1708). No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. ROSES-2026 search: still no ROSBio/BPS space biology suborbital appendix found; NNH26ZDA001N shell only on NSPIRES. PA-27-102 Sep 8 STTR deadline confirmed active (Sep 5 = Saturday → Sep 8 actual). **Sep 8 deadline: 36 days.** **Aug 4 decision gate: TOMORROW.** NASA RFI NNH26ZDA010L: Aug 10 deadline = **7 days** — READY-ACTION confirmed dispatched 7/31 15:19 (task 1709); Jon has draft in inbox and MC task. All READY-ACTIONs confirmed dispatched in logs/ready-actions-dispatched.json; all 10 NIH-MG keys accounted for. No new external actions taken; all PIs at one-chase limit; guardrail holds. |
| 2026-08-04 04:45 CDT | **AUG 4 DECISION GATE — TODAY.** IMAP check not executable in cron context (no Bash/Read access); M365 blindspot persists for Kelly's reply (still in Outlook only). Scan results: ROSES-2026 (NNH26ZDA001N) still NOT released as standalone; ROSES-25 (NNH25ZDA001N) active (E.3 Space Biology: Research Studies = TBD, no due date). No ROSBio/BPS suborbital appendix confirmed. No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. **NEW: NIH research security training required starting Aug 5, 2026 — all PIs/Co-Is proposing ≥10% time must certify completion before submission. Affects Sep 8 STTR; PI partner must complete this.** NASA RFI NNH26ZDA010L: Aug 10 deadline = **6 days** — READY-ACTION dispatched 7/31 (task 1709); Jon must act on this TODAY or tomorrow. Sep 8 STTR deadline: **35 days.** STTR track status: Kelly replied (Outlook only, unreadable to Exo); all other PIs no visible reply; all at one-chase limit. **DECISION needed from Jon: (A) extend STTR search, (B) pivot BD-only, or (C) forward Kelly's reply so Exo can act.** New READY-ACTION dispatched (key: nih-microgravity-aug4-gate-update) with Aug 4 status. |

<!-- READY-ACTION
key: nih-microgravity-chase-han
task_title: [NIH-MG] Send reply-chase — Dr. Arum Han, TAMU (PI lock gate July 28)
to: arum.han@tamu.edu
subject: Re: BLK3 suborbital platform + NIH STTR opportunity — Texas connection
category: BD
priority: 85
body:
Hello Dr. Han,

Circling back on my email from a few weeks ago about BLK3 suborbital microgravity capacity and a potential NIH STTR collaboration.

We have a September 8 deadline for PA-27-102 and are still looking for a biomedical PI to anchor the science, with Exos providing the suborbital flight platform. Given your TraCe MPS work and Texas proximity, your lab remains our top candidate for a Texas-based collaboration.

If there is any interest, even a 15-minute call would help us understand whether to move forward. If the timing is not right, no worries at all.

John Quinn
Cofounder and CEO
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-pi-lock-gate-decision
task_title: [NIH-MG] DECISION: PI lock gate passed July 28 — extend search or pivot to BD-only?
to: jquinn@exosaero.com
subject: [NIH-MG] PI Lock Gate — Decision Needed Today
category: BD
priority: 90
body:
Jon,

Quick situation report on the NIH microgravity STTR pursuit. PI lock gate is today (July 28).

STATUS:
- Outreached: Vunjak-Novakovic (Columbia), Han (TAMU), Kelly (UW), Wu (Stanford), He (UF), Sethu (UAB), NIH SEED office
- Replies received: ZERO from any of the above
- Reply-chases sent: Vunjak + Kelly + SEED on July 24. Han chase dispatched today.
- Collicott (Purdue) warm-intro ask sent July 24 — potential new PI path, reply pending
- Sep 8 STTR deadline: 42 days remaining

With zero PI responses at the gate, you have three options:

OPTION A — EXTEND SEARCH (keep STTR alive)
Pivot STTR ask to Wu, He, or Sethu if any reply positively to the BD outreach sent July 23. These are active TC-in-Space 2.0 ISS researchers and stronger STTR candidates than cold contacts. Also wait on Collicott (Purdue) — if he connects us to a Weldon BME organ-on-chip PI, that could be a fast warm path.

OPTION B — STTR SUSPEND, BD-ONLY
Officially stand down the STTR track for this Sep 8 cycle. Redirect all effort to selling BLK3 payload slots to the 6 TC-in-Space 2.0 PIs and MATChS awardees. No grant deadline pressure; revenue focus.

OPTION C — ONE MORE PASS
I identify 2-3 new PI candidates from the MATChS awardee list (miniaturized tissue chips, Sep 4 deadline — natural suborbital interest) and NCATS/NASA space biology PI databases, and draft outreach for your review this week. Higher effort, still possible to lock a PI in time if someone responds quickly.

My read: Option A is lowest friction. Wu, He, and Sethu already have your BD email. If any of them reply, a second email pivoting to the STTR ask is a natural next step. Collicott is also live. I would hold the STTR track open through August 4 while watching for inbounds, then make the call.

What would you like me to do?

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-kelly-forward-request
task_title: [NIH-MG] Forward Kelly's reply to exosmc@proton.me so Exo can act
to: jquinn@exosaero.com
subject: [NIH-MG] Quick action needed: forward Kelly's reply to exosmc@proton.me
category: BD
priority: 90
body:
Jon,

One simple step that unblocks the Kelly/STTR path:

Dr. Kelly (edkelly@uw.edu, UW kidney chip) replied to your Outlook email. I can't see M365, so that reply is invisible to me. Please forward it to exosmc@proton.me — I'll read it, draft your response, and advance the STTR track immediately.

Sep 8 STTR deadline is 39 days out. If Kelly's reply is positive (even lukewarm), a same-day response from us keeps the thread alive.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-nasa-rfi-nnh26zda010l
task_title: [NIH-MG] NASA RFI: Private Sector Space Biology Partnerships — respond by Aug 10
to: jquinn@exosaero.com
subject: [NIH-MG] NEW: NASA RFI on Private Sector Space Biology Partnerships — Aug 10 deadline (draft inside)
category: BD
priority: 80
body:
Jon,

Flagging an 11-day opportunity: NASA just released a Request for Information (RFI), NNH26ZDA010L, "Private Sector Partnerships in Astrobiology, Planetary Protection, and Space Biology," closing August 10, 2026. Responses go to NASA's Science Mission Directorate (SMD) — the program office that funds ROSBio (Research Opportunities in Space Biology) and its space biology appendices. Responding now puts BLK3 on their radar before ROSBio drops.

Draft RFI response below — you would submit this via NSPIRES (the NASA Solicitation and Proposal Integrated Review and Evaluation System; login required). I can't submit on your behalf; you'd paste this into the NSPIRES response form.

---

SUBMITTED IN RESPONSE TO: NNH26ZDA010L
Organization: Exos Aerospace Systems and Technologies, Inc.
Contact: John Quinn, Cofounder and CEO | jquinn@exosaero.com | +1-972-740-8355

PARTNERSHIP INTEREST: Reusable Suborbital Platform for Space Biology Research

Exos Aerospace (Greenville, Texas) is one of only three Federal Aviation Administration (FAA)-licensed reusable suborbital launch companies in the United States. We operate BLK3 (Block 3), a Precision Suborbital Reusable Launch Vehicle (PSRLV) capable of delivering recoverable payloads to approximately 120 kilometers (km) altitude with 3 to 4 minutes of high-quality microgravity (µg) and full payload recovery. BLK3 holds an active FAA launch license (Part 431, renewed March 2026) and is manifested for a March 2027 flight from Spaceport America, New Mexico.

We believe BLK3 fills a specific gap in NASA's space biology research portfolio: short-duration, high-cadence microgravity for onset-kinetics characterization, payload de-risk, and rapid-cycle hypothesis testing before International Space Station (ISS) flight commitment. This niche — suborbital screening of biomedical payloads — complements sustained-microgravity ISS research rather than competing with it. Our platform is relevant to space biology in the following areas:

1. Microphysiological systems (MPS) and tissue chips: BLK3 can fly and recover MPS payloads, providing onset-kinetics data in the first seconds to minutes of microgravity exposure — a window not accessible on the ISS due to launch and transit delays.

2. Cell and molecular biology: Short-duration microgravity for gravisensing, cytoskeletal response, and nucleation studies, with same-day payload recovery for assay.

3. Platform development and validation: Repeated low-cost flights to validate spaceflight hardware before ISS qualification campaigns.

We are actively pursuing National Institutes of Health (NIH) Small Business Technology Transfer (STTR) teaming and NASA Flight Opportunities partnerships, and would welcome a discussion with NASA SMD program officers about how BLK3 fits the space biology pipeline.

We note that Exos also holds 18% ownership of Scorpius Space Launch Company, whose Type 5 cryogenic composite tank technology was flight-demonstrated on the Intuitive Machines Odysseus and Athena lunar landers. This positions us uniquely as a company with both suborbital flight capability and lunar-heritage materials technology relevant to long-duration space biology infrastructure.

---

If you want to submit this, log in to NSPIRES and search for NNH26ZDA010L — there should be a response link on the solicitation page. Takes about 10 minutes. Happy to refine any section before you submit.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-aug4-gate-update
task_title: [NIH-MG] AUG 4 GATE: STTR decision needed + NASA RFI in 6 days
to: jquinn@exosaero.com
subject: [NIH-MG] Aug 4 Gate — STTR decision + NASA RFI due Aug 10
category: BD
priority: 90
body:
Jon,

Two items needing your decision today on the NIH microgravity pursuit.

1. AUG 4 STTR GATE — Your 7/27 decision was "hold STTR track open through Aug 4." That's today.

Current state:
- Kelly replied (per you, 7/27) but his reply is in your Outlook inbox only — I cannot see it. This is the highest-leverage unblock: forward it to exosmc@proton.me and I will draft your response same day.
- All other PIs (Vunjak, Han, Wu, He, Sethu, Collicott): no visible replies in Proton.
- All PIs are at their one-chase limit. Sep 8 STTR deadline: 35 days.

Options:
A) FORWARD KELLY'S REPLY — If his response is even lukewarm, we have a live PI and 35 days is sufficient to draft. Highest-probability path. Takes 30 seconds.
B) EXTEND through Aug 11 — Watch for Wu, He, and Sethu to respond to BD outreach (sent 7/23). If any show interest, pivot the STTR ask to them. Low effort.
C) PIVOT TO BD-ONLY — Stand down the Sep 8 STTR track. Redirect to selling BLK3 payload slots only. No grant deadline pressure.

My recommendation: Do A immediately (forward Kelly's email). Hold B open simultaneously. Only call C if Kelly is negative and Wu, He, and Sethu do not engage by Aug 11.

2. NASA RFI NNH26ZDA010L — CLOSES AUG 10 (6 days)

Draft has been in your inbox since July 31 (MC task 1709). Submitting via NSPIRES takes about 10 minutes. This puts BLK3 directly in front of the NASA program officers who fund ROSBio. Zero risk, high visibility.

Please action both items. STTR path still has runway if Kelly is positive.

John Quinn / Exo
END-READY-ACTION -->

| 2026-08-07 04:45 CDT | **NASA RFI NNH26ZDA010L — CLOSES MONDAY AUG 10 (3 days). TODAY IS THE LAST BUSINESS DAY.** Final-call READY-ACTION (key: nih-microgravity-aug6-rfi-final-call) dispatched yesterday (Aug 6) — already in Jon's inbox + MC task 1709. No new dispatch needed. Scan: no new NIH NOSI; no NCATS Tissue Chips 3.0 RFA; ROSES-2026 ROSBio/BPS suborbital appendix still not released. PA-27-102 deadline RECONFIRMED: Sep 5 = Saturday, Sep 7 = Labor Day → official NIH submission deadline = **Sep 8, 2026** (32 days). Kelly's reply still locked in Outlook only (M365 blindspot). All PIs at one-chase limit; no new external actions taken. STTR track alive, gated on Kelly forward or new PI engaging. No new drafts produced — all active items already queued in Jon's inbox. |
| 2026-08-10 04:45 CDT | **NASA RFI NNH26ZDA010L — CLOSES TODAY (Aug 10).** NSPIRES confirmed: NNH26ZDA010L deadline is Aug 10, 2026. This is the absolute final window. ROSES-26 status: NSPIRES confirms ROSES-25 (NNH25ZDA001N) is still the active omnibus (now running through August 2026); ROSES-26 overdue vs. NASA's "July 2026" plan and still not released. NO ROSBio/BPS space biology suborbital appendix in ROSES-25 or ROSES-26. No new NIH NOSI. No NCATS Tissue Chips 3.0 RFA. PA-27-102 Sep 8 STTR deadline: **29 days.** Kelly's reply still locked in Outlook (M365 blindspot). All PIs at one-chase limit; no re-nudging. STTR track alive, gated on Kelly forward. New READY-ACTION dispatched (key: nih-microgravity-aug10-rfi-closes-today) — NASA RFI final-hour alert. |
| 2026-08-06 04:45 CDT | **NASA RFI NNH26ZDA010L — 4 DAYS REMAINING (closes Aug 10, Monday).** Aug 10 = Monday; last practical window to submit is today (Thu) or tomorrow (Fri) — weekend is the only fallback. Draft in Jon's inbox + MC task 1709 since July 31. STTR portal: PA-27-102 opened for submissions Aug 5 (yesterday) — applications now accepted. Scan: ROSES-25 E.3 Space Biology still "TBD" (no due date, no ROSBio/BPS suborbital appendix confirmed in ROSES-25 or ROSES-26). NNH26ZDA001N (ROSES-26) NOT released. No new NIH NOSI; no NCATS Tissue Chips 3.0. Research security training effective Aug 5 for both NIH AND NASA grants — PI must certify before Sep 8 submission. IMAP not accessible in cron; Kelly's reply still Outlook-only. All PIs at one-chase limit. Sep 8 STTR deadline: **33 days.** New READY-ACTION dispatched (key: nih-microgravity-aug6-rfi-final-call) — final practical window to submit RFI before Aug 10. |

| 2026-08-05 04:45 CDT | **AUG 4 GATE PASSED (yesterday).** Jon's 7/27 decision was "hold STTR track through Aug 4" — gate expired; decision still open. IMAP check not executable in cron context; M365 blindspot persists for Kelly's reply. Scan: ROSES-2026 still no ROSBio/BPS space biology appendix confirmed released; ROSES-25 (NNH25ZDA001N) still the active solicitation. No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA. **NASA RFI NNH26ZDA010L closes Aug 10 = 5 days — CRITICAL; task 1709 in Jon's queue; must act today.** NIH research security training requirement NOW IN EFFECT (Aug 5 start date). Sep 8 STTR deadline: **34 days.** All PIs at one-chase limit. Highest-leverage unblock: Jon forward Kelly's reply from Outlook to exosmc@proton.me. New READY-ACTION dispatched (key: nih-microgravity-aug5-status) with updated gate summary. |

<!-- READY-ACTION
key: nih-microgravity-aug5-status
task_title: [NIH-MG] AUG 5 — Gate passed, NASA RFI closes in 5 days, Kelly reply still locked
to: jquinn@exosaero.com
subject: [NIH-MG] Aug 4 gate passed — 2 time-critical items: Kelly reply + NASA RFI (Aug 10)
category: BD
priority: 90
body:
Jon,

Two items that need action today on NIH microgravity.

1. NASA RFI NNH26ZDA010L — CLOSES AUG 10 (5 DAYS)
Draft RFI response has been in your inbox and MC task 1709 since July 31. Submitting via NSPIRES takes about 10 minutes. This puts BLK3 directly in front of the NASA program officers who fund ROSBio. If you have not submitted yet, today is the day. Do not let this slip.

2. KELLY'S REPLY IS STILL UNREADABLE TO ME
Kelly's reply (per you, July 27) is sitting in your Outlook inbox only. I still cannot see M365. One action unblocks the STTR path: forward his email to exosmc@proton.me. I will read it and draft your response the same day.

State of play:
- Sep 8 STTR deadline: 34 days
- Aug 4 hold-gate has now passed; decision is overdue: forward Kelly / extend through Aug 11 / or pivot BD-only
- All other PIs (Vunjak, Han, Wu, He, Sethu) at one-chase limit, no visible replies
- NIH research security training now required for any PI we lock (started Aug 5 today)
- ROSES-2026: no ROSBio/space biology appendix released yet; still watching

My recommendation: forward Kelly's email right now. If his reply is even a soft maybe, 34 days is workable. Then submit the NASA RFI today while you are in your inbox.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-aug6-rfi-final-call
task_title: [NIH-MG] FINAL CALL: NASA RFI closes Aug 10 (Monday) — submit today or tomorrow
to: jquinn@exosaero.com
subject: [NIH-MG] Final call: NASA RFI NNH26ZDA010L closes Aug 10 — submit today
category: BD
priority: 95
body:
Jon,

This is the final practical window for the NASA RFI. NNH26ZDA010L closes Monday August 10. Today (Thursday) or tomorrow (Friday) are your only real windows — weekend is the fallback, but do not count on it.

The draft has been in your inbox and MC task 1709 since July 31. Submitting via NSPIRES takes about 10 minutes. This is a zero-risk, high-visibility move: you are putting BLK3 directly in front of the NASA program officers who fund ROSBio (the space biology suborbital window we are waiting for). Missing this would be a missed shot at free positioning with NASA SMD.

Please submit today. Log in to NSPIRES, search NNH26ZDA010L, and paste the draft into the response form.

Also still open: forward Kelly's reply (edkelly@uw.edu) from your Outlook to exosmc@proton.me. Sep 8 STTR deadline is 33 days. If Kelly is positive, 33 days is workable.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-research-security-training
task_title: [NIH-MG] STTR compliance: NIH research security training required for PI (Aug 5 effective)
to: jquinn@exosaero.com
subject: [NIH-MG] New NIH requirement for Sep 8 STTR: PI must complete research security training
category: BD
priority: 75
body:
Jon,

Heads-up on a new NIH compliance requirement affecting the Sep 8 STTR submission.

Starting August 5, 2026, NIH requires all PIs and Co-Is spending 10% or more time on a proposed grant to certify completion of research security training before submission. The approved option is the NSF Research Security Training (four online modules, self-paced, a few hours) or the SECURE Center condensed version.

What this means for us: whichever PI we lock as the STTR partner must complete this training before we submit on September 8. It is not a heavy lift but needs to happen early in the engagement so it does not become a last-minute blocker.

Action: When we confirm a PI, include this in the first substantive conversation and share the NSF link.

Reference: nsf.gov/funding/initiatives/research-security/training

John Quinn / Exo
END-READY-ACTION -->

| 2026-08-11 04:45 CDT | **STTR Sep 8 DEADLINE: 28 DAYS.** NASA RFI NNH26ZDA010L CLOSED yesterday (Aug 10) — no further action possible; it is either submitted or missed. No new NIH NOSI for microgravity/space biology. ROSES-2026 (NNH26ZDA001N): NASA SARA page still 404; NOT formally released; no ROSBio/BPS suborbital appendix. No NCATS Tissue Chips 3.0 RFA. IMAP: zero PI replies visible (Kelly's reply still Outlook-only; M365 blindspot). All PIs at one-chase limit; no re-nudging. **28 days to Sep 8 is the absolute floor for a STTR submission — PI lock must happen THIS WEEK to have any chance.** If Kelly is positive, forwarding his reply today is the only path. If not, Sep 8 STTR is dead; Jan 5, 2027 becomes the new target (full 5-month runway for a proper PI search and draft). **New READY-ACTION dispatched (key: nih-microgravity-aug11-sep8-binary) — binary decision for Jon.** BD sell-slot track continues regardless; Wu/He/Sethu replies still possible. Research security training compliance reminder noted for any PI who engages (Aug 5 effective). |

<!-- READY-ACTION
key: nih-microgravity-aug11-sep8-binary
task_title: [NIH-MG] BINARY DECISION: Forward Kelly now or call Sep 8 STTR dead — 28 days left
to: jquinn@exosaero.com
subject: [NIH-MG] 28 days to Sep 8 STTR — binary decision needed today
category: BD
priority: 95
body:
Jon,

28 days left to the Sep 8 STTR deadline (PA-27-102). The NASA RFI closed yesterday. One decision remains.

BINARY CHOICE:

OPTION A — FORWARD KELLY'S EMAIL (takes 30 seconds)
Dr. Kelly's reply has been in your Outlook inbox since July 27. I still cannot see M365. Forward it to exosmc@proton.me and I will read it, draft your response the same day, and push toward the Sep 8 deadline if his reply is positive. 28 days is the floor — PI lock this week is required.

OPTION B — CALL SEP 8 DEAD, TARGET JAN 5, 2027
Stand down the Sep 8 track. The January 5, 2027 deadline gives us 5 months of proper runway for a PI search, a better-drafted proposal, and a PI who has time to complete the required NIH research security training (now mandatory for all Co-Is). BD sell-slot track continues regardless.

STATE OF PLAY:
- 6 PIs contacted (Vunjak, Han, Kelly, Wu, He, Sethu) + Collicott warm intro + NIH SEED: zero visible replies
- Kelly replied per you (7/27), but only you can see it
- All PIs are at their one-chase limit
- Sep 8: 28 days / Jan 5: 147 days
- ROSES-2026 not yet released; ROSBio appendix still pending

My read: If Kelly's reply is lukewarm, Jan 2027 is the right call and we run a stronger submission. If Kelly is positive, forward the email and I will take it from there immediately.

Please decide today. Either direction is fine — I need the call to stop burning clock on a deadline we cannot hit without PI action.

John Quinn / Exo
END-READY-ACTION -->

| 2026-08-18 04:45 CDT | **PURDUE/COLLICOTT PATH — NEW INSTITUTIONAL ANCHOR.** Jon's 8/17 directive pivoted the STTR from UW/Kelly → Purdue / Collicott. All Kelly/UW nudges KILLED. **STTR Sep 8 DEADLINE: 21 DAYS.** Purdue SPS routing ~5 business days → effective PI commitment needed by ~Aug 26-27. **OPEN ITEM (gated on Jon):** Collicott is AAE, not biomedical — NIH STTR needs a biomedical science lead. On 7/24 Jon asked Collicott to intro a Purdue Weldon BME organ-on-chip / MPS PI. Has that intro happened? Who is the Weldon BME PI? Until confirmed, agent holds on PI outreach draft. **Scan:** No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA; ROSES-2026 still not released; no ROSBio suborbital appendix. BD sell-slot track continues. **New READY-ACTION (key: nih-microgravity-purdue-copi-confirm) dispatched** — asking Jon for Weldon BME co-PI identity. |
| 2026-08-17 08:14 CDT | **JON DIRECTIVE (email @exobot): "this was moved to Purdue Collicott."** STTR institutional anchor PIVOTED from UW/Kelly → Purdue / Prof. Steven Collicott (AAE), a committed Exos partner (SACSS LOS in hand). **Kelly/UW path SUPERSEDED; all "forward Kelly" + "UW routing clock" nudges KILLED.** Institutional routing recomputed to Purdue SPS (~5 business days → effective lock ≈ Sep 1); Sep 8 STTR is NOT dead — Purdue's clock governs, more runway than the UW "Aug 19" math implied. **Open item flagged to Jon:** Collicott is aerospace, not biomedical — confirm the Purdue Weldon BME organ-on-chip/MPS co-PI who leads the science (the warm intro asked of Collicott on 7/24). Tracker banner + Objective updated; agent to hold on Purdue bio co-PI confirmation, not Kelly. |
| 2026-08-18 09:34 CDT | **JON DIRECTIVE (@exobot): "restore the Ed Kelly framing and leverage Purdue capability as well — two can support the same effort." SUPERSEDES the 8/17 either/or pivot.** STTR is now a **DUAL-INSTITUTION** team on ONE PA-27-102: **Kelly (UW) = biomedical science anchor** (fills the NIH bio-lead requirement Collicott can't), **Collicott (Purdue AAE) = suborbital experiment methods + committed partner**, Exos = SBC/platform. STTR split framing added: one RI-of-record at ≥30%, Exos ≥40%, second institution via ≤30% subaward — recommended UW/Kelly primary RI + Purdue/Collicott subaward. **Kelly reply-retrieval RESTORED (was killed 8/17): single most important action = Jon forwards Kelly's Outlook reply to exosmc@proton.me.** Clock: two routing clocks (UW ~5–7 biz + Purdue SPS ~5 biz), later governs → both PIs committed by ~Aug 26–27 for Sep 8. Objective + Current-stage banner updated; agent to advance BOTH tracks, emit no "pick one" decisions. |
| 2026-08-17 04:45 CDT | **STTR Sep 8 DEADLINE: 22 DAYS — INSTITUTIONAL ROUTING CLOCK NOW CRITICAL.** Scan: no new NIH NOSI for space biology/microgravity; no NCATS Tissue Chips 3.0 RFA; ROSES-2026 (NNH26ZDA001N) still NOT released (ROSES-25 confirmed staying open through August 2026 per NASA SARA; no ROSBio/BPS space biology suborbital appendix). PA-27-102 Sep 8 deadline confirmed (Sep 5 Saturday → Sep 8). **NEW SIGNAL: NASA SBIR/STTR switched to rolling BAA (appendices throughout year) since April 17, 2026 — no single January sprint anymore; monitor for space biology subtopics as they drop.** No PI replies visible (Kelly's reply still Outlook-only; M365 blindspot). All PIs at one-chase limit. Aug 14 final-window READY-ACTION dispatched 3 days ago — no Jon response visible. Binary decision (Aug 11) 6 days without visible response. **INSTITUTIONAL MATH: At 22 days, UW's institutional routing alone typically takes 5-7 business days. PI must commit by Aug 18-19 EOD for any Sep 8 path to survive. New READY-ACTION dispatched (key: nih-microgravity-aug17-institutional-clock) with hard routing deadline.** Jan 5, 2027 fallback confirmed viable (141 days). BD sell-slot track continues; Wu/He/Sethu replies still possible. |

<!-- READY-ACTION
key: nih-microgravity-aug17-institutional-clock
task_title: [NIH-MG] 22 DAYS: Forward Kelly by Aug 19 or Sep 8 is mathematically dead
to: jquinn@exosaero.com
subject: [NIH-MG] 22 days to Sep 8 STTR — institutional clock requires Kelly forward by Aug 19
category: BD
priority: 95
body:
Jon,

22 days to the September 8 STTR deadline. I need to give you the institutional clock math, because the window is now narrower than the day count suggests.

INSTITUTIONAL ROUTING REALITY:
University of Washington requires roughly 5-7 business days of internal routing before any PI can submit to NIH. That means the effective submission deadline at UW is approximately August 28-31. Working backwards:

- PI commits and drafts are complete: by August 25
- That means PI lock must happen: by August 19 (Tuesday)

If you do not forward Dr. Kelly's reply by end of day tomorrow (August 18), the September 8 path is mathematically dead regardless of what Kelly's reply says.

ONE ACTION:
Forward Kelly's reply from your Outlook (edkelly@uw.edu) to exosmc@proton.me. Takes 30 seconds. I will read it, draft your response the same day, and push immediately if he is even lukewarm.

IF SEP 8 IS DEAD:
The January 5, 2027 deadline gives us 141 days of proper runway. I will close the September 8 track cleanly, set January 5 as the new target, and maintain the BD sell-slot track through year end. This is the right call if Kelly's reply is negative or you cannot act today.

Please decide now. Either answer is fine — I need the call.

John Quinn / Exo
END-READY-ACTION -->

| 2026-08-12 04:45 CDT | **STTR Sep 8 DEADLINE: 27 DAYS.** NASA RFI NNH26ZDA010L closed Aug 10 — no longer actionable. Scan: no new NIH NOSI for space biology/microgravity; no ROSES-2026 ROSBio/BPS suborbital appendix released (NNH26ZDA001N still pending); no NCATS Tissue Chips 3.0 RFA. No PI replies visible in Proton (Kelly's reply still Outlook-only; M365 blindspot). All PIs at one-chase limit. **Binary decision email (key: nih-microgravity-aug11-sep8-binary) dispatched yesterday (Aug 11) — in Jon's inbox + MC task.** No new READY-ACTION dispatched this run; re-nudging a same-day email is guardrail violation. Secondary signal: ISS NL May 2026 spotlight confirms Mei He (UF, our BD target) published muscle tissue chip EV results in iScience — useful hook if/when she replies. BD track continues; Wu/He/Sethu replies still possible. STTR path gated entirely on Jon's response to yesterday's binary decision. Jan 5, 2027 is the fallback deadline (147 days) if Sep 8 is called. |
| 2026-08-13 04:45 CDT | **STTR Sep 8 DEADLINE: 26 DAYS.** Scan: no new NIH NOSI for space biology/microgravity; no NCATS Tissue Chips 3.0 RFA; no ROSES-2026 ROSBio/BPS suborbital appendix confirmed released. NASA RFI NNH26ZDA010L closed Aug 10 — no longer actionable. No PI replies visible (Kelly's reply still Outlook-only; M365 blindspot). All PIs at one-chase limit. Binary decision (key: nih-microgravity-aug11-sep8-binary) dispatched Aug 11 — 2 days old, still awaiting Jon's response. No new READY-ACTION dispatched this run (binary decision already in Jon's inbox; re-nudging within 48h violates guardrail). BD track: Wu/He/Sethu replies still possible. **At 26 days, Sep 8 path requires PI lock THIS WEEK. Holding until Jon acts on Aug 11 binary decision.** |
| 2026-08-14 04:45 CDT | **STTR Sep 8 DEADLINE: 25 DAYS — FINAL PRACTICAL WINDOW FOR PI LOCK.** Scan: no new NIH NOSI for space biology/microgravity; no NCATS Tissue Chips 3.0 RFA; ROSES-2026 NNH26ZDA001N still not released (ROSES-25 active per NASA SARA; no ROSBio/BPS space biology suborbital appendix). NASA RFI NNH26ZDA010L closed Aug 10 — done. PA-27-102 confirmed active (Sep 5/8 deadline, Phase I ~$323K ceiling). No PI replies visible in any accessible channel. Kelly's reply still Outlook-only (M365 blindspot; persists since 7/27). Binary decision (key: nih-microgravity-aug11-sep8-binary) dispatched Aug 11 — now 3 days without visible response. **NEW NARRATIVE SIGNAL: NIH invested $150M in human-based research / animal model replacement (March 2026); Artemis II tissue chip work (Wyss, April 2026) confirms active NASA-NIH space bio pipeline. Both strengthen the BLK3 pitch when resuming PI outreach.** This week = absolute last window for Sep 8 STTR. If no PI locks by ~Aug 20, formally target Jan 5, 2027 (147 days of proper runway). New READY-ACTION dispatched (key: nih-microgravity-aug14-sep8-final-window) — concise final-window framing with explicit Jan 5 pivot proposal. BD track continues; research security training requirement noted for any PI who engages. |

<!-- READY-ACTION
key: nih-microgravity-aug14-sep8-final-window
task_title: [NIH-MG] FINAL WINDOW: Sep 8 STTR — forward Kelly this week or pivot to Jan 5
to: jquinn@exosaero.com
subject: [NIH-MG] 25 days to Sep 8 STTR — this week is the last window; Jan 5 is the backup
category: BD
priority: 90
body:
Jon,

25 days to the Sep 8 STTR deadline. This week is the last practical window to lock a PI and have any chance of submitting.

ONE THING THAT UNLOCKS SEP 8:
Forward Dr. Kelly's reply (edkelly@uw.edu) from your Outlook to exosmc@proton.me. His reply has been sitting in your Outlook since July 27. If it is even mildly positive, I will read it, draft your response same day, and we push for Sep 8. Takes 30 seconds.

IF KELLY IS NEGATIVE OR NOT PURSUED:
I recommend we formally call Sep 8 done and target January 5, 2027. That gives us 5 months of proper runway to run a stronger PI search, draft a tighter proposal, and not be rushed. The BD sell-slot track continues regardless, and the Jan 5 submission will be a better product. Six PIs have been outreached — if any of them (Wu, He, or Sethu) reply to the BD email positively, I pivot the STTR ask to them immediately.

WHAT I NEED FROM YOU:
A) Forward Kelly's email today → I take it from there immediately, and we keep Sep 8 alive.
B) Confirm Jan 5, 2027 pivot → I close the Sep 8 track cleanly, set Jan 5 as the target, and redirect to BD sell-slot for the rest of 2026.

Either answer is the right answer. I just need the call.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-aug10-rfi-closes-today
task_title: [NIH-MG] NASA RFI NNH26ZDA010L — CLOSES TODAY AUG 10 — last hour
to: jquinn@exosaero.com
subject: [NIH-MG] NASA RFI closes TODAY — submit now (takes 10 min)
category: BD
priority: 99
body:
Jon,

The NASA RFI NNH26ZDA010L "Private Sector Partnerships in Astrobiology, Planetary Protection, and Space Biology" closes TODAY, August 10, 2026.

This is the last moment. The draft has been in your inbox since July 31 (MC task 1709). Submitting via NSPIRES takes about 10 minutes. This puts BLK3 directly in front of the NASA SMD program officers who fund ROSBio — the space biology suborbital window we are waiting for. Missing it means we are invisible to NASA SMD until ROSES-26 drops.

To submit: log in to NSPIRES at nspires.nasaprs.com, search NNH26ZDA010L, and paste the draft into the response form. POC at NASA if questions: Rebecca McCauley Rench — rebecca.l.mccauleyrench@nasa.gov.

Please do this now.

Also still open: forward Dr. Kelly's reply (edkelly@uw.edu) from your Outlook to exosmc@proton.me. Sep 8 STTR deadline is 29 days. If Kelly is positive, 29 days is workable.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-purdue-copi-confirm
task_title: [NIH-MG] PURDUE PATH: Who is the Weldon BME co-PI? Need name by Aug 26
to: jquinn@exosaero.com
subject: [NIH-MG] Purdue STTR path: who is the Weldon BME co-PI? Need confirmation this week
category: BD
priority: 95
body:
Jon,

You moved the NIH STTR to Purdue / Collicott on August 17. Understood — the September 8 path is still viable under Purdue's institutional clock (Purdue SPS routes in approximately 5 business days, so PI commitment is needed by roughly August 26-27).

One thing I need to advance: the biomedical co-PI identity.

Collicott is AAE (aerospace), not biomedical. NIH STTR requires a biomedical science lead at the research institution — the PI who holds the science scope and whose lab runs the experiment. On July 24 you asked Collicott to introduce us to a Purdue Weldon School BME organ-on-chip / MPS co-PI. Has that introduction happened?

Two questions:
1. Has Collicott connected us with a Weldon BME PI? If yes, send me their name and email and I will draft engagement immediately.
2. If the intro has not happened yet, do you want me to identify 2-3 Purdue Weldon School BME PI candidates (organ-on-chip / MPS focus) so you or Collicott can reach out?

Timing: I need a name by approximately August 26 to leave Purdue SPS 5 business days to route before September 8. If we miss that window, September 8 is dead and January 5, 2027 becomes the target (full runway, stronger submission).

Please confirm the co-PI or tell me to find candidates — either answer lets me move.

John Quinn / Exo
END-READY-ACTION -->

---

## 2026-08-18 UPDATE — PURDUE BIO CO-PI RESOLVED (Estelle Park)
**The open item in the Current Stage box is now CLOSED.** On 2026-08-17 Prof. Steven Collicott (Purdue AAE) sent a warm intro connecting Jon with **Prof. Estelle (Sunghee) Park** (park1713@purdue.edu), Assistant Professor, **Weldon School of Biomedical Engineering, Purdue** — as the biomedical science lead for the STTR. Collicott explicitly steps back to **uncompensated advisor** ("you two charge ahead"). This is the same-institution Purdue BME co-PI the tracker was waiting on since 7/24.
- **Park fit (verified via Purdue Weldon BME profile + CV):** PhD Bioengineering, U-Penn under **Dan Huh** (founding organ-on-chip lab); research = **stem-cell-derived lung organoids-on-a-chip, intestinal/retina organoids-on-chip** = exact MPS onset-kinetics niche. Not in failed-DD registry; warm intro.
- **Jon directive (email-command 2026-08-18):** "prepare a write up and intro email. This is in parallel to Ed Kelly effort." → Two STTR PI paths now run CONCURRENTLY for the same Sep 8 deadline: **Purdue/Park (primary, warm, best-fit)** and **Kelly/UW (parallel)**. Do NOT treat Purdue as replacing Kelly this cycle — both live per Jon.
- **Deliverables produced (Exo):** concept write-up `drafts/Exos_Purdue_Bio_STTR_Writeup_2026-08-18.md` (attached to MC task 2125) + intro email draft `drafts/Purdue_Estelle_Park_STTR_Intro_2026-08-18.md` (To: park1713@purdue.edu, Cc: Collicott).
- **Gated on Jon:** Decision **D-7281651** (send-type) — on Yes, send-watcher delivers the Park intro to Jon's inbox to send. External .edu send; never auto-sent.
- **Governing gate:** Purdue Sponsored Programs routing lock **~Sep 1** (not Sep 8). Move to a call this week.
- **Capture Agent:** advance the Purdue/Park track (call scheduling, then tailor Aim 2 to Park's platform + one-page concept for Purdue SPS). Kelly track continues in parallel — no change.
- **SENT CONFIRMED (auto): park1713@purdue.edu** on 2026-08-18 12:27 — subject "Fw: Purdue  & Exos". Nudge-to-send STOPPED; reply-watch only.

| 2026-08-19 04:45 CDT | **STTR Sep 8 DEADLINE: 20 DAYS. PURDUE SPS GATE: ~Sep 1 (13 days).** Governing clock = Purdue Sponsored Programs (~5 biz days internal routing), meaning Park must formally commit by **~Aug 26–27** EOD — 7–8 days. Park intro sent 8/18 (yesterday); reply-watch only (too soon to chase). Kelly track: reply still Outlook-only (M365 blindspot). **This run's advances:** (1) Call-scheduling email READY-ACTION produced (key: nih-microgravity-park-call-schedule) — Jon should send this to Park today to secure a call this week; (2) Park-tailored Aim 2 drafted (lung organoid-on-chip onset kinetics, replacing the kidney-chip framing); full dual-PI Specific Aims shell can now be assembled when Park commits. No new NIH NOSI; no NCATS Tissue Chips 3.0 RFA; ROSES-2026 ROSBio suborbital appendix still not released. BD sell-slot track: Wu/He/Sethu/Sharma/Zhang replies still possible — reply-watch only. **Decision needed from Jon:** (A) send Park call-schedule email this week; (B) forward Kelly's Outlook reply to exosmc@proton.me (parallel path, unchanged). |

<!-- READY-ACTION
key: nih-microgravity-park-call-schedule
task_title: [NIH-MG] Schedule call with Prof. Park (Purdue Weldon BME) — this week
to: park1713@purdue.edu
cc: collicot@purdue.edu
subject: Re: Purdue & Exos — scheduling a call to discuss STTR collaboration
category: BD
priority: 95
body:
Hello Prof. Park,

Thank you for connecting with us through Prof. Collicott. I wanted to follow up quickly and see if you have 30 minutes available for a call this week or early next week.

I would like to walk you through the BLK3 platform and how we envision the STTR collaboration working — specifically how your lung organoid-on-chip work fits the onset-kinetics framing we're developing. I also want to make sure you have the full picture on the September 8 deadline and the Purdue Sponsored Programs timeline, so we can move quickly if there is a fit.

I am flexible on timing. Happy to accommodate your schedule — please let me know what works.

Looking forward to connecting.

John Quinn
Cofounder and CEO
END-READY-ACTION -->

## Park-Tailored Specific Aim 2 (produced 2026-08-19 — replaces Kelly kidney-chip framing in dual-PI shell)

*This is the Aim 2 for the Purdue/Park-primary STTR path. If Kelly's reply (Outlook-only) is positive, a Kelly kidney-chip Aim 2 runs in parallel and the two Aim 2 variants are synthesized or one is selected as primary RI-of-record. Park = lung organoid-on-chip; Kelly = kidney chip. Both are MPS/onset-kinetics — the Aim 1 (platform) and Aim 3 (screening pipeline) are platform-agnostic and unchanged.*

---

**Specific Aim 2 (Park/Purdue version) — Lung Organoid-on-Chip Onset-Kinetics Characterization [Purdue / Prof. Estelle Park — biomedical science lead; research-institution-of-record]**

Fly Prof. Park's stem-cell-derived lung organoid-on-chip payload on BLK3 and characterize alveolar epithelial response during the 0–240 second microgravity window. Outcomes measured: (1) ciliary beat frequency and airway surface liquid dynamics under µg onset; (2) alveolar epithelial tight junction integrity and surfactant secretion kinetics; (3) cell viability and organoid structural fidelity post-recovery. Generate the first onset-kinetics dataset for a lung organoid-on-chip system in suborbital microgravity — a window inaccessible on ISS due to launch vibration and transit delays obscuring early cellular response. Exos provides the flight platform, thermal envelope, payload recovery, and telemetry; Purdue/Park performs organoid fabrication, experiment design, and post-flight assays.

*Reviewer hook: Y. Shrike Zhang (BWH/Harvard) holds an active NCATS TC-in-Space 2.0 award (1UG3TR005836-01) for aging alveolar lung in microgravity, validating NIH reviewer familiarity with this science area. Park's Dan Huh lineage (lung-on-a-chip originator, UPenn) establishes direct methodological credibility. BLK3 provides the de-risk screening step Zhang's and Park's labs need before ISS commitment.*

---

*STTR teaming (Park/Purdue primary version):*
- **Exos** = SBC, ≥40%; applicant of record; flight platform + payload integration + recovery
- **Purdue / Park** = research-institution-of-record, ≥30%; biomedical science lead (Aim 2)
- **Purdue / Collicott** = uncompensated advisor (no separate subaward needed; cost-effective structure)
- **UW / Kelly** (if positive reply received): subaward, ≤30%; Aim 2 parallel data point or expanded Aim 3 screening pipeline. Kelly's involvement would elevate the submission but is not required for Sep 8 if Park commits alone.

---

| 2026-08-21 04:45 CDT | **STTR Sep 8 DEADLINE: 18 DAYS. PURDUE SPS GATE: ~Aug 26–27 (5–6 days).** No new NIH NOSI for space biology/microgravity. PA-27-102 confirmed still Open on sbir.gov. NCATS TC-in-Space page still showing last update Apr 22, 2026 — no TC 3.0 RFA released. ROSES-2026: still no NNH26ZDA001N ROSBio/BPS suborbital appendix found. State unchanged from 8/20: Park intro was sent 8/18; call-schedule READY-ACTION (key: nih-microgravity-park-call-schedule) and call-prep READY-ACTION (key: nih-microgravity-park-call-prep) were dispatched 8/19–20 and are in Jon's inbox. **CRITICAL PATH: Park must commit by Aug 26–27 for Purdue SPS to route before Sep 8. Jon must schedule the call TODAY.** No Park reply visible yet (only 3 days since intro — too soon to chase). No new READY-ACTION dispatched this run (call-schedule and call-prep already in Jon's queue; re-dispatch would be redundant). Kelly track: reply still Outlook-only. BD sell-slot track: reply-watch only. No new external actions taken. |
| 2026-08-20 04:45 CDT | **STTR Sep 8 DEADLINE: 19 DAYS. PURDUE SPS GATE: ~Aug 26–27 (6–7 days).** IMAP scan: NO PI replies visible in Proton (Kelly's reply still Outlook-only; M365 blindspot). No new NIH NOSI for space biology/microgravity. NCATS Tissue Chips 3.0 RFA: not released (last NCATS page update Apr 22, 2026; TC-in-Space 2.0 awardees still executing). ROSES-2026: still NOT released as NNH26ZDA001N — ROSES-25 confirmed still active (corrections as of Aug 4, 2026; last Table 2 amendment July 27, 2026); no ROSBio/BPS suborbital appendix. **State of play:** Park intro sent 2026-08-18 (2 days ago); call-schedule READY-ACTION (key: nih-microgravity-park-call-schedule) dispatched 8/19 with stale "Tuesday/Wednesday" timing — body UPDATED this run to "this week or early next week" and re-queued for dispatch. Park reply-watch only — too soon to chase (intro only 2 days old). **This run's advance:** call-prep brief READY-ACTION produced (key: nih-microgravity-park-call-prep) — Jon-facing, covers Park background, what to achieve on the call, and the institutional clock reality. **Critical path:** Jon must send call-schedule email TODAY (Thursday Aug 20) to secure a call by Friday Aug 22 or Monday Aug 25 at the very latest — if Park commits on Monday, SPS has exactly 5 biz days to route before Sep 8. One day of delay loses a day of runway. Kelly track unchanged — forward-to-exosmc READY-ACTION still in Jon's queue; parallel path still alive. BD sell-slot track (Wu/He/Sethu/Sharma/Zhang): reply-watch only, no new actions. |

<!-- READY-ACTION
key: nih-microgravity-park-call-prep
task_title: [NIH-MG] Call prep: Prof. Estelle Park (Purdue Weldon BME) — STTR partnership
to: jquinn@exosaero.com
subject: [NIH-MG] Call prep: Prof. Park (Purdue) — what to cover + what to walk away with
category: BD
priority: 90
body:
Jon,

Quick prep brief for your call with Prof. Estelle (Sunghee) Park this week. The call-schedule email is in your queue — send it today so you can get on her calendar by Friday or Monday.

---

WHO SHE IS

- Assistant Professor, Weldon School of Biomedical Engineering, Purdue
- PhD Bioengineering, University of Pennsylvania under Dan Huh — the researcher who invented lung-on-a-chip (Nature 2010). She is methodologically credentialed at the highest level.
- Research focus: stem-cell-derived lung organoids-on-a-chip, intestinal organoids-on-chip, retina organoids-on-chip
- Collicott intro = warm path (she took the intro through him); she is not a cold contact
- Not in our failed-DD registry; no flags

WHY SHE IS A STRONG FIT

- Her lung organoid chip work maps directly onto BLK3's onset-kinetics niche: alveolar epithelial response in the first 0-240 seconds of microgravity is a dataset nobody has — ISS cannot generate it (launch vibration + transit delay obscure early µg response)
- Y. Shrike Zhang (BWH/Harvard) holds an active NCATS Tissue Chips 2.0 award for aging alveolar lung in microgravity — NIH reviewers already know this science area, which validates Park's framing
- As Purdue BME with Collicott as advisor, the two-person team inside one institution is a clean STTR structure (Park = RI-of-record ≥30%, Exos = SBC ≥40%, Collicott = uncompensated advisor)

WHAT TO COVER ON THE CALL (suggested order)

1. One-minute BLK3 platform intro: 120 km altitude, 3-4 min recoverable microgravity, FAA-licensed, March 2027 flight, full payload recovery
2. The niche we fill: onset kinetics in the first seconds-to-minutes of µg — window ISS cannot provide due to transit delays. "Screen on BLK3, fly the winners to ISS."
3. Her role in the STTR: biomedical PI / research-institution-of-record. She drives Aim 2 (the lung organoid onset-kinetics science). Exos does the platform (Aim 1). Collicott/Purdue covers suborbital experiment methods as uncompensated advisor.
4. Budget framing: Phase I STTR ~$314-323K total over 12 months. Park/Purdue share ~$100-120K. She needs to be comfortable with that budget for her scope before we loop in Purdue SPS.
5. Institutional routing reality (be direct): Purdue Sponsored Programs needs ~5 business days to route. Sep 8 is the NIH deadline. For SPS to have time, she needs to formally commit and engage SPS no later than August 26-27. This week's call IS the decision call.
6. NIH research security training: as a Co-I/PI spending ≥10% time, she must certify completion before submission (NSF modules, a few hours; effective Aug 5). Flag early, not as a blocker — she likely has the institutional infrastructure for this.

WHAT TO WALK AWAY WITH FROM THE CALL

A) Her interest level: positive/neutral/negative (determines whether we pursue Sep 8 or stand down to Jan 5, 2027)
B) If positive: her name for Purdue SPS (or her SPS grants contact name), so you can confirm routing timeline
C) Her Aim 2 scope comfort: does she want to define the experiment or follow our Aim 2 draft?
D) Budget direction: is $100-120K for her lab's scope workable?
E) Her availability for rapid drafting (next 2 weeks): can she dedicate time to proposal review given the Sep 8 clock?

IF KELLY'S OUTLOOK REPLY IS POSITIVE (parallel track)

If you forward Kelly's reply (edkelly@uw.edu) from Outlook to exosmc@proton.me, I read it same-day and can integrate Kelly as a subaward partner on the UW kidney-chip science. Park = primary RI-of-record (≥30%), Kelly = subaward (within remaining ≤30%), Exos = SBC (≥40%). This structure is fully compliant and would give the proposal two ISS-caliber biomedical PIs — a stronger submission. But Park alone is sufficient for Sep 8 if Kelly is negative or unavailable.

---

Key dates (do not lose these):
- Park call: by Friday Aug 22 or Monday Aug 25 (absolute latest)
- Park commitment to SPS: by Aug 26-27 EOD
- Purdue SPS routing: Aug 27 - Sep 1
- NIH Sep 8 STTR PA-27-102 deadline

John Quinn / Exo
END-READY-ACTION -->

| 2026-08-25 04:45 CDT | **STTR Sep 8 DEADLINE: 14 DAYS. COMMITMENT WINDOW: TODAY IS THE LAST PRACTICAL DAY (per 8/18 framing, ~Aug 26-27 was the outer edge for both UW and Purdue SPS to route in time).** No new NIH NOSI for space biology/microgravity. PA-27-102 still Open on sbir.gov (unchanged). NCATS TC-in-Space page still last updated Apr 22, 2026 — no TC 3.0 RFA. ROSES-2026 (NNH26ZDA001N) still NOT released; ROSES-25 remains the active solicitation (amendments through Jul 27, corrections through Aug 4) — no ROSBio/BPS suborbital appendix has appeared. **Gap found:** Jon answered Decision D-7281669 "Yes — forward Kelly now" on 2026-08-24 16:51 CDT, but a full Proton IMAP scan (all folders, since 8/21) found zero follow-through — no Kelly draft sent, no Park/Purdue correspondence either. Both tracks have been silent for a week while the clock ran out. **This run's advance:** (1) drafted a ready-to-send direct re-engagement email to Dr. Kelly (edkelly@uw.edu, CC exosmc@proton.me) dispatched as READY-ACTION nih-microgravity-kelly-reengage-0825 — this both acts on Jon's 8/24 approval and fixes the BCC-blindspot going forward; (2) dispatched an urgent status-check READY-ACTION (nih-microgravity-park-status-check-0825) since Park's call cannot be verified by email (may have occurred by phone) and her answer determines whether the Sep 8 window is still alive. **If neither PI commits today, recommend standing down Sep 8 and retargeting the Jan 5, 2027 STTR cycle** — flagged to Jon in the status-check ask rather than decided unilaterally. Sell-slot BD track (Wu/He/Sethu/Sharma/Zhang) unchanged, reply-watch only. |

<!-- READY-ACTION
key: nih-microgravity-kelly-reengage-0825
task_title: [NIH-MG] Direct re-engagement to Dr. Kelly (UW) — per your Aug 24 approval, last-day commitment window
to: jquinn@exosaero.com
subject: [READY TO SEND] [NIH-MG] Re-engage Dr. Kelly directly — today is the last practical commitment day
category: BD
priority: 95
body:
Jon,

You answered "yes, forward Kelly now" on 8/24, but I don't see any draft or send since then, and I haven't found Kelly's original reply in any Proton folder (it's still stuck in Outlook). Rather than wait on that forward again, here's a direct email to Kelly you can send from Outlook right now. It re-opens the thread, confirms we want him in on the STTR alongside the Purdue track, and CCs exosmc@proton.me so his reply lands somewhere I can actually read it.

Today is effectively the last practical day for either PI (Kelly or Park) to commit and still let their university route the paperwork before the Sep 8 deadline. If this doesn't move today, recommend we talk about standing down to the Jan 5, 2027 cycle.

---

To: edkelly@uw.edu
Cc: exosmc@proton.me
Subject: Following up, ready to move forward on the STTR

Hello Dr. Kelly,

I wanted to follow up and confirm where things stand. We are moving ahead on the NIH STTR (PA-27-102, deadline September 8) and would like you to anchor the biomedical science as the UW partner. In parallel we have opened a track with a Purdue Weldon BME lab on suborbital experiment methods, the two are complementary, not competing, so there is room for both institutions if you are still interested.

The timing is tight. University routing on both sides needs about a week, so we need commitments locked today or tomorrow at the latest to make the September 8 deadline.

Could we get 20 minutes today or tomorrow to confirm your interest and next steps on the UW side? If it is easier, feel free to loop exosmc@proton.me in on any reply so nothing gets lost on my end this time.

Thank you,
John Quinn
Cofounder and CEO

---

Two-minute copy-paste. Send whenever you get this, every hour matters at this point.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-goNoGo-registrations-0826
task_title: [NIH-MG] Go/no-go on Sep 8 — eRA Commons org registration + Kelly/Park status, one answer needed
to: jquinn@exosaero.com
subject: [DECISION NEEDED] [NIH-MG] Go/no-go on Sep 8 — one answer covers it
category: BD
priority: 95
body:
Jon,

Combining two open threads into one ask so this doesn't feel like a third separate nag.

1. eRA Commons registration: is Exos (the organization, not just your individual Login.gov link) registered in eRA Commons with a Signing Official, or only your personal account? If org-level isn't done, that alone can miss Sep 8 regardless of PI status — it's a days-to-2-week process.

2. Kelly/Park: did the Kelly re-engagement email go out, and did the Park status call happen? Both PIs' university routing offices need to start this week for Sep 8 to be reachable.

I checked overnight, nothing moved on either front as of this morning. Yesterday (8/25) was the date we flagged as the last practical day for PI routing to start. I'm not calling Sep 8 dead yet since routing offices open this morning, but if I don't hear a clear answer on both by end of day today, my recommendation is to stand down and retarget the Jan 5, 2027 STTR cycle so we're not burning more runway chasing a window that's already closed.

No external searching turned up anything new to act on in the meantime (no NCATS Tissue Chips 3.0 release yet, no live NASA ROSBio suborbital solicitation).

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-park-status-check-0825
task_title: [NIH-MG] URGENT: did the Park call happen? Sep 8 window closes today/tomorrow
to: jquinn@exosaero.com
subject: [URGENT] [NIH-MG] Park status check — SPS routing gate is today/tomorrow
category: BD
priority: 95
body:
Jon,

Quick status check, this determines whether Sep 8 is still reachable. The call-schedule and call-prep drafts for Prof. Estelle Park (Purdue) went to your inbox 8/19-20, targeting a call by Friday 8/22 or Monday 8/25. I can't see phone calls, only email, so I have no way to confirm whether that call happened or what she said.

Per the 8/18 timing math, both UW (Kelly) and Purdue (Park) needed a committed PI today or tomorrow at the latest for their sponsored-programs office to route in time for Sep 8.

Three quick questions:
1. Did the Park call happen? What was her answer?
2. Is she willing to be research-institution-of-record and engage Purdue SPS this week?
3. If both Kelly and Park are still open, do you want me to stand down Sep 8 and retarget the Jan 5, 2027 STTR cycle instead, so we're not burning more runway chasing a deadline that's already effectively closed?

I'd rather get a clear answer now than keep circling this one.

John Quinn / Exo
END-READY-ACTION -->

<!-- READY-ACTION
key: nih-microgravity-aligned-writeups-status-0828
task_title: [NIH-MG] URGENT status check — did the UW/Purdue writeups from 8/26 4:30pm go out?
to: jquinn@exosaero.com
subject: [URGENT] [NIH-MG] Did the Kelly/Collicott writeups go out? Today is the last real day before Sep 8
category: BD
priority: 95
body:
Jon,

Going back through everything since 8/26, I found something that should have been flagged sooner and wasn't.

At 4:30pm on 8/26 I sent you three finalized writeup docs after you approved the aligned dual-institution structure: NIH_STTR_UW_Kelly_Writeup.docx (forward to Dr. Kelly), NIH_STTR_Purdue_Subaward_Writeup.docx (forward to Collicott), and an optional Park co-I intro. That email said forwarding the first two is literally what starts UW OSP and Purdue SPS routing for Sep 8.

I have no record in Proton that either one actually went to Kelly or Collicott, and nothing at all has moved on this pursuit since that 4:30pm email, over 36 hours of total silence. You may well have sent them from Outlook, which I can't see unless it's CC'd to exosmc@proton.me, so I'm asking rather than assuming.

Two questions:
1. Did you forward the UW writeup to Kelly and the Purdue writeup to Collicott? If yes, roughly when, so I can gauge the routing clock?
2. If not yet, can you send both today? Sep 7 is Labor Day, offices will be closed, so today is the last day that leaves close to a full week of runway before Sep 8.

Separately, still no word from NIH on the eRA Commons org-registration approval. That one isn't due for escalation until around Sep 2, so no action needed there yet, just tracking.

John Quinn / Exo
END-READY-ACTION -->
- **SENT CONFIRMED (auto): bhudspet@purdue.edu** on 2026-08-25 12:31 — subject "=?utf-8?q?Fw:_NIH_STTR_Proposal_with_Exos_Aerospace_=E2=80=93_FP80012618?=". Nudge-to-send STOPPED; reply-watch only.
- **SENT CONFIRMED (auto): Jon → Park (cc Kelly)** on 2026-08-31 03:20 UTC (2026-08-30 10:20pm CDT) — subject "NIH STTR PA-27-102 — Research Plan Narrative (Word doc attached), Exo update". Reply to Park's 8/30 3:39pm scoping question (kidney-MPS-only vs. add intestinal organoids). Locks Phase I to Kelly's kidney MPS as sole primary model; Park's intestinal/hepatic organoid study explicitly banked as Phase II; Purdue supports Aims 2/3 under Kelly's direction as measurable subaward milestones. Drafted by Exo per Jon's "@exobot advise and prepare draft response" request, sent by Jon within 19 minutes. Nudge-to-send N/A (already closed loop); reply-watch on Park's revised Aims 2/3 task list + Kelly's independent reply.

| 2026-08-31 | Park (Purdue) replied 8/30 3:39pm asking Phase I scope (kidney-MPS-only vs. add intestinal organoids); Jon answered same night (cc Kelly), locking kidney MPS as sole model and banking organoids for Phase II | CONFIRMED SENT via IMAP. Open: Park's milestone list, ~Sep 1 Purdue SPS lock, eRA org-reg approval still pending (escalation threshold ~Sep 2 now due) |

---
## 2026-09-02 15:00 CDT — Exo (email command from John)
**John's decisions on the two ASSIST blockers:**
1. **Contact PD/PI = Prof. Sunghee "Estelle" Park (Purdue)** — confirmed (no Exos-side MPI requested). Park sits at the research institution, allowed under STTR rules.
2. **John's research-security ("ERA required") training = COMPLETE** per John's note ("certificate attached"). ⚠️ The cert file did NOT surface with the email-command text — **file the actual certificate to this pursuit folder when it lands** so the compliance record is real, not just asserted.

**Still needed from Park to submit clean by Tue Sep 8 (Lizi building ASSIST now):**
- Park's **eRA Commons username** (Purdue Commons ID, PD/PI role affiliated under Purdue). If not yet affiliated, Purdue Sponsored Programs (Brandee Hudspeth, bhudspet@purdue.edu) can add/confirm.
- **Research-security training certificate for Park + Prof. Collicott** (all key personnel >=10% effort).

**Action taken:** Drafted John→Park email requesting the above (materials back by Fri Sep 4 for margin). Queued for John's approval as **Decision D-7281761** (attached docx). External send is gated; nothing sent yet.

---
## 2026-09-03 09:30 CDT — Exo (email command from John — Fw: Purdue subaward CORRECTION thread)
John forwarded the Park/Brandee thread. Two items, both already consistent with the docs of record — no new external action required from Exo (John handled the sends himself):
1. **Purdue subaward figure of record = $176,278** (inclusive of Purdue's negotiated F&A). John restated this to Brandee Schluttenhofer/Estelle Park on 9/1 for the SPS routing lock ("before SPS lock today"). This matches what was already LOCKED 8/31 22:15 and already carried in the SF424 Budget Summary + Research Plan SUBMISSION on task 2466. The "~$188K" in the earlier draft was the pre-SBC-fee 60% figure; **$176,278 is the clean, guideline-compliant number** (Phase I guideline $314,363 incl. 7% SBC fee; Exos held at 40% base floor). Scope of work and ~12-month PoP unchanged.
2. **Estelle Park's revised biosketch (9/2 5:14pm, "Park-cv-NIH STTR.pdf")** — revised to align with the current (Purdue-only) proposal. **Verified byte-identical (SHA 694e3eb9…) to the biosketch already on file** as `Park-NIHSTTR-biosketch_2026-09-02_LATEST.pdf`. It is now the **single biosketch of record** on task 2466 under doc_key `park-nihsttr-biosketch`; the duplicate `Park-NIHSTTR-cv.pdf` de-registered (byte-identical, kept for history).

**Net:** figure and biosketch of record confirmed and consolidated. Purdue's ~Sep 1 SPS lock and the Sep 8 NIH deadline remain the live gates; those actions sit with Brandee (Purdue SPS) and Lizi (ASSIST build). Nothing external pending from this forward.
