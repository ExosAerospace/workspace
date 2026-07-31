#!/usr/bin/env python3
"""Build the 'Bamboo-Retained' ERP blueprint (Word + markdown).
Best-of-breed: Bamboo=HR/payroll SoR, QuickBooks=financial SoR, Mission Control=defense-ERP spine.
Drops original Phase 1 HR-core build + Phase 3 cutover; keeps timekeeping/contracts/cost/procurement/assets."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

NAVY=RGBColor(0x0F,0x2A,0x4A); GOLDT=RGBColor(0x9A,0x6B,0x10); GREYT=RGBColor(0x44,0x44,0x44)
doc=Document()
base=doc.styles['Normal']; base.font.name='Calibri'; base.font.size=Pt(10.5)

def shade(cell,hexc):
    tc=cell._tc.get_or_add_tcPr(); s=OxmlElement('w:shd'); s.set(qn('w:val'),'clear'); s.set(qn('w:fill'),hexc); tc.append(s)
def setcell(cell,text,bold=False,size=9.5,color=None):
    cell.text=''
    p=cell.paragraphs[0]; r=p.add_run(text); r.font.size=Pt(size); r.font.bold=bold
    if color: r.font.color.rgb=color
def H(txt,lvl):
    h=doc.add_heading(txt,level=lvl)
    for r in h.runs: r.font.color.rgb=NAVY
    return h
def P(txt,bold=False,italic=False,size=10.5):
    p=doc.add_paragraph(); r=p.add_run(txt); r.font.bold=bold; r.italic=italic; r.font.size=Pt(size); return p
def B(txt):
    p=doc.add_paragraph(style='List Bullet');
    # allow **bold** lead
    if txt.startswith('**') and '**' in txt[2:]:
        lead,rest=txt[2:].split('**',1); r=p.add_run(lead); r.font.bold=True; r.font.size=Pt(10.5); r2=p.add_run(rest); r2.font.size=Pt(10.5)
    else:
        r=p.add_run(txt); r.font.size=Pt(10.5)
    return p
def table(headers,rows,widths=None):
    t=doc.add_table(rows=1,cols=len(headers)); t.style='Light Grid Accent 1'
    for i,h in enumerate(headers):
        setcell(t.rows[0].cells[i],h,bold=True,size=9.5,color=RGBColor(0xFF,0xFF,0xFF)); shade(t.rows[0].cells[i],"1F3B66")
    for row in rows:
        c=t.add_row().cells
        for i,val in enumerate(row): setcell(c[i],val,size=9.5)
    if widths:
        for i,w in enumerate(widths):
            for r in t.rows: r.cells[i].width=Inches(w)
    return t

# ---------- Title ----------
tp=doc.add_paragraph(); tp.alignment=WD_ALIGN_PARAGRAPH.LEFT
r=tp.add_run("Mission Control -> Defense-ERP"); r.font.size=Pt(22); r.font.bold=True; r.font.color.rgb=NAVY
sp=doc.add_paragraph(); r=sp.add_run("The Bamboo-Retained Variant  ·  Working Build Blueprint"); r.font.size=Pt(13); r.font.color.rgb=GOLDT; r.font.bold=True
mp=doc.add_paragraph(); r=mp.add_run("Prepared for John Quinn, Cofounder & CEO  ·  Exos Aerospace  ·  2026-07-22  ·  Owner: Exo (build) / Jon (go-no-go gates)  ·  Proprietary"); r.font.size=Pt(9); r.font.color.rgb=GREYT

# ---------- 1 Executive decision ----------
H("1. The Decision, In One Line",1)
P("Do not turn Mission Control into an HRIS. Keep BambooHR as the system of record for people and payroll, "
  "integrate to it, and point the build at the defense-ERP spine (timekeeping, contracts, cost, procurement, assets). "
  "This is a best-of-breed architecture with three systems of record:")
B("**BambooHR** = people + payroll of record (PII, benefits, PTO/leave, onboarding, I-9/E-Verify, ACA, EEO, payroll -> QuickBooks).")
B("**QuickBooks** = financial book of record (GL, AP/AR, payroll posting).")
B("**Mission Control** = defense-ERP spine (DCAA timekeeping, contracts/CDRL, project cost, procurement, assets, document control). Reads people from Bamboo; never owns the sensitive HR data.")
P("Why this is the better call: you are a rocket company, not a payroll processor. Owning HR compliance is downside with no upside. "
  "Keeping PII and payroll in Bamboo's SOC-2 environment shrinks your CMMC/ITAR boundary and removes the two riskiest phases of the original plan.",italic=True)

# ---------- 2 System of record map ----------
H("2. System-of-Record Map",1)
table(["Domain","System of Record","Mission Control's Role"],
 [["Employee master / PII (SSN, DOB, bank, address)","BambooHR","No custody. Read-only mirror of non-sensitive fields only."],
  ["Benefits, PTO / leave balances","BambooHR","Read leave records for total-time accounting."],
  ["Onboarding, I-9/E-Verify, ACA, EEO","BambooHR","None."],
  ["Payroll processing","BambooHR -> QuickBooks","Feed approved hours in; no payroll calc."],
  ["Timekeeping (labor charging)","Mission Control","Owns. DCAA total-time accounting."],
  ["Contracts / CDRL / deliverables","Mission Control","Owns."],
  ["Project & indirect cost accounting","Mission Control","Owns."],
  ["Procurement / purchase orders","Mission Control","Owns."],
  ["Assets / hardware / calibration","Mission Control","Owns."],
  ["Financials (GL, AP, AR)","QuickBooks","Integrate (cost + invoice sync)."],
  ["Documents / e-sign / ITAR control","Mission Control","Owns."]],
 widths=[2.6,1.7,3.1])

# ---------- 3 Revised phase map ----------
H("3. Revised Phase Map (vs. the Absorb-and-Cutover Plan)",1)
table(["Phase","Scope","Change vs. original","Go/No-Go Gate"],
 [["0. Foundation","SQLite + audit log + RBAC/clearance","DONE (built, on branch erp-phase0)","Persistence cutover of live MC (pending)"],
  ["1'. Bamboo Integration","Thin read-only people-master sync via Bamboo API","REPLACES 'HR Core + Bamboo import'. ~1/4 the work.","Roster + leave sync reconciles to Bamboo"],
  ["2. DCAA Timekeeping + Labor Cost","Daily employee time, charge codes, approvals, project labor cost","KEPT - the core win Bamboo cannot do","DCAA-adequacy checklist passes"],
  ["(was 3.) Bamboo Cutover","-","REMOVED entirely. No migration, no decommission.","-"],
  ["4. Contracts / CDRL + Cost Rollup","Contract, CLIN, CDRL, indirect pools, cost rollup","KEPT - highest leverage","Contract cost ties to QuickBooks"],
  ["5. Procurement + Assets","POs, receiving, asset/calibration register","KEPT","-"],
  ["6. Finance + ITAR Doc Control","QuickBooks sync, document control, ITAR gating","KEPT","QB reconciliation + ITAR access review"]],
 widths=[1.3,2.7,2.5,2.0])
P("Net effect: the two HR-heavy, PII-heavy, highest-risk phases (original Phase 1 build and Phase 3 cutover) drop out. "
  "You reach the defense-ERP payoff faster and with a smaller compliance surface.",italic=True)

# ---------- 4 Bamboo API integration spec ----------
H("4. BambooHR Integration Spec",1)
P("One-way, read-only. Bamboo is authoritative; Mission Control mirrors only what it needs and never writes PII back.")
H("4.1 Connection",2)
B("REST API v1 at https://api.bamboohr.com/api/gateway.php/{subdomain}/v1/ ; Basic auth with an API key (key as username, 'x' as password).")
B("API key stored in the enclave secret store (not in code/repo); rotated; access audited. Least-privilege Bamboo user tied to the key.")
B("Direction: Bamboo -> MC only. MC has no write scope to Bamboo except the optional approved-hours import in 4.4.")
H("4.2 Objects synced",2)
table(["Bamboo object","Fields pulled into MC","Purpose"],
 [["Employee directory","bambooId, workEmail, displayName, status (active/term), hireDate, department, division, jobTitle, location, supervisor","People dimension for timekeeping, cost, RBAC mapping"],
  ["Employment fields","employmentStatus (exempt/non-exempt), employee type, labor category (custom field)","DCAA labor category + OT eligibility"],
  ["Time-off / leave","leave type, hours, date, status","Total-time accounting (see §5)"],
  ["Org / reporting","supervisor chain","Timesheet approval routing"]],
 widths=[1.9,3.3,2.2])
H("4.3 Explicitly NEVER synced (stay in Bamboo)",2)
B("SSN, date of birth, bank/direct-deposit, home address, dependents, individual compensation detail, benefits elections, documents. Field-level deny-list enforced in the sync, not just by omission.")
H("4.4 Cadence, storage, failure handling",2)
B("Nightly full delta + on-demand webhook on employee update -> MC 'person' table (keyed by bambooId) and 'person_leave' table.")
B("If a sync fails: MC keeps last-good roster, alerts, and writes an audit_log row. No partial overwrite.")
B("Rates: prefer labor-category standard/burdened rates held in an MC rate table (RBAC-restricted) over individual salaries, so individual comp never lands in MC. (Open decision - see §8.)")

# ---------- 5 Total time accounting ----------
H("5. Total-Time Accounting - The Key Seam",1)
P("DCAA requires every hour of every employee - worked, leave, and uncompensated - recorded daily in ONE timekeeping "
  "system, employee-entered, supervisor-approved, and immutably audited. Keeping Bamboo for PTO creates one seam to engineer correctly.")
H("5.1 Design",2)
B("**Mission Control is the timekeeping system of record.** All hours are entered daily in MC.")
B("**Worked hours** charge to a project / contract / CLIN / charge code.")
B("**Leave hours** are also entered in MC (against leave charge codes) so the daily record is complete; MC validates them against Bamboo PTO balances pulled via API. Bamboo stays the benefits/leave authority; MC stays the time authority.")
B("Daily entry, electronic signature, supervisor approval, timesheet lock. Corrections never delete - they create a versioned adjustment with reason + approver (the immutable audit_log from Phase 0 already supports this).")
B("Total-time reconciliation report: hours per employee per day = worked + leave + LWOP, flagged for gaps (DCAA floor-check equivalent).")
H("5.2 Payroll seam (preserves today's flow)",2)
P("Recommended: MC exports approved hours (regular / OT / leave by type) INTO Bamboo; Bamboo runs payroll and the existing "
  "Bamboo -> QuickBooks export continues unchanged. This keeps the one seam already flagged as critical intact and reproducible.")
B("Alternative: MC -> QuickBooks time directly (only if you ever move payroll off Bamboo). Not recommended now.")
H("5.3 Charge-code structure (DCAA)",2)
B("Direct: Contract -> CLIN -> WBS/task -> charge code. Indirect pools: Overhead, G&A, B&P, IR&D. Unallowable segregated per FAR 31.205.")

# ---------- 6 Compliance ----------
H("6. Compliance & Boundary (CMMC / ITAR)",1)
B("PII and payroll stay in Bamboo's SOC-2 cloud -> your CMMC/ITAR enclave scopes to CUI (contracts, technical data) and cost, not employee PII. Smaller assessment surface, less custody liability.")
B("Mission Control (Atomus GCC High enclave) holds timekeeping, charge codes, contract cost, and controlled documents; ITAR access-gating on technical data; audit log on every mutation.")
B("If burdened rates are held in MC for cost accounting, they sit in an RBAC + clearance-restricted, audited, encrypted table - or are avoided entirely by using labor-category standard rates.")

# ---------- 7 Delta ----------
H("7. What Changes vs. the Original Plan",1)
table(["Removed / shrunk","Added / kept"],
 [["Phase 1 HR-core build (benefits, PTO engine, onboarding) -> shrinks to a thin API sync","Bamboo read-only people + leave sync"],
  ["Phase 3 Bamboo cutover & decommission -> deleted","Total-time reconciliation against Bamboo"],
  ["HR PII custody, encryption-at-rest for PII, migration/parallel-run risk -> gone","Same DCAA timekeeping, contracts/CDRL, cost, procurement, assets, finance"]],
 widths=[4.7,4.7])

# ---------- 8 Sequence + open decisions ----------
H("8. Recommended Sequence, Gates & Open Decisions",1)
P("Sequence:",bold=True)
B("Now: Phase 1' Bamboo sync (small; unblocks the people dimension).")
B("Then: Phase 2 DCAA timekeeping (the core win) - gate on a DCAA-adequacy checklist.")
B("Then: Phase 4 contracts/CDRL -> Phase 5 procurement/assets -> Phase 6 finance/QuickBooks + ITAR doc control. Jon go/no-go at each gate.")
P("Open decisions for Jon:",bold=True)
B("1. Rates in MC: labor-category standard rates (recommended, minimal PII) vs. actual individual rates.")
B("2. Payroll seam: MC -> Bamboo -> QuickBooks (recommended, preserves current export) vs. MC -> QuickBooks direct.")
B("3. Persistence cutover of the live Mission Control app onto the Phase 0 SQLite database (still pending from Phase 0).")
B("4. Timekeeping rollout: which employees first, and parallel-run window against the current process.")

os.makedirs("drafts",exist_ok=True)
out="drafts/MC_Defense_ERP_Bamboo_Retained_Blueprint.docx"
doc.save(out)
print("BUILT",out)
