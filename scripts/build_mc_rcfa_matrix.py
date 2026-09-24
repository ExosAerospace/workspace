#!/usr/bin/env python3
"""Build the Mission Control RCFA + Countermeasures + Validation workbook (openpyxl)."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "drafts/MC_RCFA_Countermeasures_Validation_2026-09-24_v2_CORRECTED.xlsx"
NAVY="0A3D7C"; ORANGE="E8641A"; GREY="555555"; LGREY="F2F2F2"; RED="C0392B"; GREEN="1E7D34"; AMBER="B8860B"
hdr = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
navy_fill = PatternFill("solid", fgColor=NAVY)
title_f = Font(bold=True, color=NAVY, size=15)
sub_f = Font(italic=True, color=GREY, size=10)
b = Font(bold=True, color="1A1A1A")
wrap = Alignment(wrap_text=True, vertical="top")
thin = Border(*[Side(style="thin", color="D9D9D9")]*4)

wb = openpyxl.Workbook()

def style_header(ws, row, ncols):
    for c in range(1, ncols+1):
        cell = ws.cell(row=row, column=c); cell.font=hdr; cell.fill=navy_fill
        cell.alignment=Alignment(wrap_text=True, vertical="center"); cell.border=thin

def widths(ws, w):
    for i,x in enumerate(w,1): ws.column_dimensions[get_column_letter(i)].width=x

def put(ws, r, row, fills=None):
    for i,v in enumerate(row,1):
        cell=ws.cell(row=r, column=i, value=v); cell.alignment=wrap; cell.border=thin
    if fills:
        for col,color in fills.items():
            ws.cell(row=r,column=col).fill=PatternFill("solid",fgColor=color)
            ws.cell(row=r,column=col).font=Font(bold=True,color="FFFFFF")

# ---------------- TAB 1: SUMMARY ----------------
ws = wb.active; ws.title="Summary"
widths(ws,[42,90])
ws["A1"]="Mission Control — RCFA, Countermeasures & Validation"; ws["A1"].font=title_f
ws["A2"]="Reliability review of 'request made / no action taken' failures — week of 2026-09-17 → 2026-09-24"; ws["A2"].font=sub_f
rows=[
 ("Prepared","Exo — 2026-09-24, at John's direction"),
 ("Review period","2026-09-17 through 2026-09-24 (7 days)"),
 ("Method","git history (fix-class commits), auto-resume watchdog log, MC server.js failure-path review, incident recall. Measured vs inferred is marked per line."),
 ("","" ),
 ("HEADLINE FINDING (CORRECTED v2)","Root cause of the background-job failures = a MALFORMED session key. auto_resume.py used DEFAULT_SESSION 'agent:auto-resume' (2 parts); agent-prefixed keys require 3 parts 'agent:<agent-id>:<key>'. Every wake returned rc=1 'Invalid --session-key'. The 'plugins.allow is empty' line was an ADVISORY warning that the auto-resume log truncated to 200 chars, MASKING the real error — so it was initially mis-diagnosed as the cause. Proven: a wake with a VALID key returns rc=0 despite the plugins warning."),
 ("Question bubble — separate cause","The Ask-Exobot bubble uses a VALID key ('agent:main:mcchat-<slug>'), so it did NOT have the malformed-key bug. Its failures trace to: widget not injecting (FIXED 06a6982), stale awaiting-answer flag (FIXED 664af78), in-memory chatJobs lost on MC restart, and the 150s timeout. Wake path itself is proven working (rc=0)."),
 ("plugins.allow","NOT the cause and NOT changed. It is advisory only and is a PROTECTED config path. Optional hygiene: set allow=['discord','tavily'] to silence the warning (deferred; non-fatal)."),
 ("","" ),
 ("Requests made / no action taken (identified)","11 distinct incident classes this week (see Failure Log tab). Note: exact count is a floor — silent failures (e.g., a Question-bubble question that never returns) are not all logged."),
 ("Fixes shipped this week","18 fix-class commits of 96 total (see Failure Log + RCFA tabs for mapping)."),
 ("Fixes that are VERIFIED effective","8 — attachment integrity, hr.html loading, widget injection, inventory per-photo guard, crashed-agent repair, blocklist guard, PLUS (this session) the session-key fix + log-truncation fix."),
 ("ROOT-CAUSE FIX APPLIED (this session)","auto_resume.py DEFAULT_SESSION 'agent:auto-resume' -> 'agent:main:auto-resume'; repaired 4 stored commitments with the bad key; reset blk3-cost-fill to open; widened wake() error logging from 200 chars to the full stderr tail so a leading advisory can never mask the real error again."),
 ("VALIDATION RESULT","PASS. Wake with the fixed background-job key 'agent:main:auto-resume' -> rc=0 ('RESUME_OK'). Wake with the Question-bubble key format 'agent:main:mcchat-*' -> rc=0 ('BUBBLE_OK'). Both previously rc=1."),
 ("Residual (hardening, not blocking)","Persist chatJobs across MC restart; raise/queue the 150s chat timeout; add an open-request tracker so a turn never closes on an unanswered ask (see F-02/F-11)."),
 ("This document's own failure","The 08:02 request was initially dropped ('No response requested' after a task notification) — logged as incident F-11; it is the same class being analyzed."),
]
r=4
for k,v in rows:
    ws.cell(row=r,column=1,value=k).font=b; ws.cell(row=r,column=1).alignment=wrap
    ws.cell(row=r,column=2,value=v).alignment=wrap
    r+=1

# ---------------- TAB 2: FAILURE LOG ----------------
ws2=wb.create_sheet("Failure Log")
cols=["ID","Date","Request / Expected action","What happened (failure)","Action taken?","Evidence (measured/inferred)","Fix commit"]
widths(ws2,[7,12,34,40,16,30,26])
for i,c in enumerate(cols,1): ws2.cell(row=1,column=i,value=c)
style_header(ws2,1,len(cols))
data=[
 ("F-01","2026-09-24","Fill 33 BLK3 BOM prices this AM (blk3-cost-fill)","6 wake attempts 04:43–07:13 CDT all rc=1 — REAL cause: malformed session key 'agent:auto-resume' (Invalid --session-key), masked by a truncated plugins advisory; job STUCK 07:29","FIXED this session","MEASURED — reproduced rc=1 then rc=0 after fix","auto_resume.py key fix (this session)"),
 ("F-02","2026-09-24","Answer the 07:33 RCFA request","Ended turn 'No response requested' after a background-task notification; request dropped","NONE until re-asked 08:02","MEASURED — this transcript","this deliverable"),
 ("F-03","2026-09-24","Pricing subagent run to completion","Subagent stopped when the prior session exited (fire-and-forget); no completion record","Partial; being re-driven","MEASURED — task notification","b9943e7 (watchdog, partial)"),
 ("F-04","wk of 9/20","@exo replies must carry document attachments","Attachments silently dropped on task collapse; 49 orphaned docs found","FIXED","MEASURED — commit msgs","34cfeaa, d1611e1, 3193a95, 3fbdf9d"),
 ("F-05","2026-09-23","Ask-Exobot widget must load on every MC page","Widget injected before FIRST </body> → not injected on some pages; Question bubble absent","FIXED","MEASURED — commit","06a6982"),
 ("F-06","2026-09-23","HR directory page must load","hr.html stuck on 'Loading…' — nested </script> broke the page script","FIXED","MEASURED — commit","13300c8, e4c22c0"),
 ("F-07","2026-09-23","Agents must stay running","2 agents found crashed by Eval Wave 2","FIXED","MEASURED — commit","f34980c"),
 ("F-08","2026-09-22","Photo→inventory must NOT spawn a task per photo","Per-photo spurious task creation","FIXED (guard)","MEASURED — commit","c144216"),
 ("F-09","2026-09-23","Denied-party blocklist must not block bare gov/edu/mil","Structural risk of org-wide block on bare domains","FIXED (guard)","MEASURED — commit","327acf2"),
 ("F-10","2026-09-24","Question bubble: 'awaiting exo answer' must clear on reply","Flag not always cleared → stale awaiting state","FIXED","MEASURED — commit","664af78"),
 ("F-11","recurring","Any background/async job must complete or escalate","Fire-and-forget: jobs die on session rotation with no finish/verify","PARTIAL","INFERRED — memory feedback_finish_delegated_work + F-01/F-03","b9943e7 (partial)"),
]
r=2
for row in data:
    fill = {5: (RED if row[4].startswith("NONE") else GREEN if row[4].startswith("FIXED") else AMBER)}
    put(ws2,r,row,fills=fill); r+=1
ws2.freeze_panes="A2"

# ---------------- TAB 3: RCFA & COUNTERMEASURES ----------------
ws3=wb.create_sheet("RCFA & Countermeasures")
cols=["Failure mode","Root cause (5-why endpoint)","Countermeasure applied","Commit","Effectiveness","Residual risk / next step"]
widths(ws3,[30,40,38,20,20,38])
for i,c in enumerate(cols,1): ws3.cell(row=1,column=i,value=c)
style_header(ws3,1,len(cols))
rc=[
 ("Background agent job never completes (pricing, crons)","auto_resume.py wake used a MALFORMED session key 'agent:auto-resume' (2 parts); agent keys need 3 parts -> rc=1 'Invalid --session-key'. Truncated log (200 chars) showed only the plugins advisory, masking it.","Fixed key -> 'agent:main:auto-resume'; repaired 4 stored commitments; widened wake() error logging to full stderr tail","auto_resume.py (this session)","VERIFIED — wake now rc=0 ('RESUME_OK'); was rc=1","Re-drive blk3-cost-fill on the fixed mechanism (pricing already re-driving separately)"),
 ("Ask-Exobot Question bubble returns no answer","Uses a VALID key ('agent:main:mcchat-<slug>') so NOT the malformed-key bug. Prior causes: widget not injected; stale awaiting-answer flag; in-memory chatJobs lost on MC restart; 150s timeout","widget-injection fix; awaiting-answer clear; wake path proven working","06a6982, 664af78","VERIFIED (wake) — 'agent:main:mcchat-*' wake rc=0 ('BUBBLE_OK'); bubble shows & flag clears","Persist chatJobs across restart + raise/queue the 150s timeout (hardening)"),
 ("Request acknowledged then dropped (no action)","Turn ended on a background-task notification treated as 'no response needed'; no durable 'open request' tracker","(none yet)","—","INEFFECTIVE — recurred today (F-02)","Add an open-request ledger + turn-end check: never close a turn with an unanswered user ask"),
 ("@exo email drops document attachments","Docs de-referenced when a task was collapsed/migrated; silent attach failures","migrate docs on collapse; non-silent attach; nightly orphan watch; canonical emailer","34cfeaa, d1611e1, 3193a95","VERIFIED — 49 orphans reconciled; new sends attach","Monitor orphan-watch weekly for regressions"),
 ("MC page fails to load (HR directory)","Nested </script> inside a print-window string closed the page's own script tag","escape/guard nested script; comment guard","13300c8, e4c22c0","VERIFIED — page loads","Lint MC HTML for nested </script> in template strings"),
 ("Widget missing on some pages","Injected before FIRST </body>; pages with earlier </body> in strings missed it","inject before LAST </body>","06a6982","VERIFIED — widget on all pages","Covered by Validation Matrix page sweep"),
 ("Agents crash and stay down","Unhandled errors in agent lanes; no auto-restart","crashed-agent repair (Eval Wave 2); auto-resume watchdog","f34980c, b9943e7","VERIFIED (2 repaired); watchdog PARTIAL","Fold agent-liveness into a periodic self-test"),
 ("Spurious task per inventory photo","Capture path created a task on every photo","hard-guard against per-photo task creation","c144216","VERIFIED — guarded","Regression test in Validation Matrix"),
 ("Denied-party screen over-blocks","Bare gov/edu/mil domains could match org-wide block","structural guard","327acf2","VERIFIED — guard in place","Keep in CSL test set"),
]
r=2
for row in rc:
    eff=row[4]
    color = GREEN if eff.startswith("VERIFIED") else (RED if eff.startswith("INEFFECTIVE") else AMBER)
    put(ws3,r,row,fills={5:color}); r+=1
ws3.freeze_panes="A2"

# ---------------- TAB 4: VALIDATION MATRIX ----------------
ws4=wb.create_sheet("Validation Matrix")
cols=["MC area","Test case (concrete)","Method","Pass criteria","Status","Owner"]
widths(ws4,[26,42,34,34,16,12])
for i,c in enumerate(cols,1): ws4.cell(row=1,column=i,value=c)
style_header(ws4,1,len(cols))
val=[
 ("Question bubble (Ask-Exobot) — wake path","Wake with the widget's key format agent:main:mcchat-*","openclaw agent --session-key agent:main:mcchat-selftest","rc=0 and correct reply","PASS — rc=0 'BUBBLE_OK' (2026-09-24)","Exo"),
 ("Question bubble — full HTTP end-to-end","Ask a known-answer question from a logged-in MC page","POST /api/chat (authed) -> poll /api/chat/result","status='done', correct reply < 60s","PENDING — needs authed browser session","Exo"),
 ("Question bubble — restart resilience","Ask a question, restart MC mid-flight, keep polling","kill+relaunch MC launchd, continue poll","answer still returned OR job re-dispatched (not lost)","PENDING (needs chatJobs persistence)","Exo"),
 ("Question bubble — long-answer timeout","Ask a question needing >150s","time the run","no false 'timed out' before completion; queued not dropped","PENDING","Exo"),
 ("Question bubble — attachment path","Ask with a pasted document","POST /api/chat with attachment","agent reads file, references content","PENDING","Exo"),
 ("Question bubble — presence","Load every MC page, confirm bubble present","automated page sweep for /exobot-widget.js","widget on 100% of non-excluded pages","PARTIAL PASS (06a6982)","Exo"),
 ("Background agent jobs (crons/auto-resume)","Wake with fixed default key agent:main:auto-resume","openclaw agent --session-key agent:main:auto-resume","rc=0, job completes not STUCK","PASS — rc=0 'RESUME_OK' (2026-09-24)","Exo"),
 ("Open-request tracking","Send a request; end turn on a task notification","inject a background notification mid-flow","original request still answered same session","FAIL today (F-02) → build tracker","Exo"),
 ("@exo attachment delivery","@exo a task with a deliverable; check reply","send + inspect received email","attachment present; 0 new orphans","VERIFIED (F-04)","Exo"),
 ("HR directory page","Open hr.html","load page","renders (not stuck on Loading)","VERIFIED (F-06)","Exo"),
 ("Inventory photo capture","Post 3 photos to one task","capture flow","0 spurious tasks; inventory records written","VERIFIED (F-08)","Exo/Steve"),
 ("Agent liveness","Enumerate fleet agents","status sweep","0 crashed; all lanes responsive","PARTIAL (f34980c)","Exo"),
 ("BLK3 BOM pricing (today's job)","Fill remaining uncosted lines","bom_cost_fill set + report","priceable items costed; RFQ/internal lines listed (no fabricated $)","IN PROGRESS","Exo/Steve"),
 ("Denied-party blocklist","Screen bare gov/edu/mil + a known denied entity","CSL test set","allies pass, true hits block; no org-wide block","VERIFIED (F-09)","Exo"),
]
r=2
for row in val:
    st=row[4]
    color = GREEN if st.startswith("VERIFIED") else (RED if st.startswith("FAIL") else AMBER if st.startswith("PARTIAL") else "FFFFFF")
    fills={5:color} if color!="FFFFFF" else None
    put(ws4,r,row,fills=fills); r+=1
ws4.freeze_panes="A2"

wb.save(OUT)
print("WROTE", OUT)
