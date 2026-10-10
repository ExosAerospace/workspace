#!/usr/bin/env python3
"""Project GUNGNIR — TACFI meeting pack: (1) external one-pager, (2) internal game plan + question list."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle
from PIL import Image as PILImage

D = 'projects/USAF/Gungnir_BLK3-RDRE/03_TACFI_Meeting_2026-09/'
LOGO = 'assets/exos-letterhead-logo-tight.png'; FOOTER = 'assets/exos-letterhead-footer-tight.png'
NAVY = HexColor('#1B3A5C'); GRAY = HexColor('#404040'); DARK = HexColor('#222222'); LIGHT = HexColor('#E8EEF4')
PW, PH = letter; LM = 0.75*inch
LOGO_H = 0.6*inch; LOGO_W = LOGO_H*PILImage.open(LOGO).size[0]/PILImage.open(LOGO).size[1]
FOOT_H = 0.6*inch; FOOT_W = FOOT_H*PILImage.open(FOOTER).size[0]/PILImage.open(FOOTER).size[1]

def hf(c, d):
    c.saveState()
    c.drawImage(LOGO, LM, PH-LOGO_H-0.1*inch, width=LOGO_W, height=LOGO_H, mask='auto')
    c.drawImage(FOOTER, PW-LM-FOOT_W, 0, width=FOOT_W, height=FOOT_H, mask='auto')
    c.restoreState()

ss = getSampleStyleSheet()
body = ParagraphStyle('b', parent=ss['Normal'], fontName='Helvetica', fontSize=8.6, leading=11, textColor=DARK, spaceAfter=3)
bul = ParagraphStyle('bl', parent=body, leftIndent=10, bulletIndent=2)
h1 = ParagraphStyle('h1', parent=body, fontName='Helvetica-Bold', fontSize=10.5, textColor=NAVY, spaceBefore=6, spaceAfter=3)
title = ParagraphStyle('t', parent=body, fontName='Helvetica-Bold', fontSize=14, leading=17, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2)
sub = ParagraphStyle('s', parent=body, fontName='Helvetica-Bold', fontSize=10, textColor=GRAY, alignment=TA_CENTER, spaceAfter=5)
disc = ParagraphStyle('d', parent=body, fontName='Helvetica-Oblique', fontSize=7, textColor=GRAY, leading=8.5, spaceBefore=5)

def P(t, s=body): return Paragraph(t, s)
def L(items): return [Paragraph(i, bul, bulletText='•') for i in items]
def tbl(rows, widths):
    t = Table([[P(c) for c in r] for r in rows], colWidths=widths)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('GRID',(0,0),(-1,-1),0.4,GRAY),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2)]))
    return t

def build(path, flow):
    doc = BaseDocTemplate(path, pagesize=letter, leftMargin=LM, rightMargin=LM, topMargin=0.85*inch, bottomMargin=0.7*inch)
    doc.addPageTemplates([PageTemplate(frames=[Frame(LM, 0.7*inch, PW-2*LM, PH-1.55*inch, id='f')], onPage=hf)])
    doc.build(flow)

W = PW-2*LM
# ---------------- 1. EXTERNAL ONE-PAGER ----------------
f = [P('PROJECT GUNGNIR — Firing an RDRE in Space, on a Reusable Vehicle', title),
     P('USAF TACFI Request: $2M federal + $2M Texas Space Commission match = $4M program', sub),
     P('<b>Our purpose (MTP): Make Every Space Vehicle Reusable.</b> Exos Aerospace is building the enabling platform for reusable spaceflight — '
       'Integrated Pressurized Structures, zero-loss cryogenic propellant transfer, and FAA-licensed reusable launch vehicles that prove both in real flight. '
       'One of only three FAA-licensed vertical-takeoff reusable rocket providers with demonstrated recovery and reflight.'),
     P('The Ask', h1),
     P('A <b>TACFI</b> increase on SBIR Phase II <b>FA9300-25-C-6022</b> (AFRL/RJPE, Edwards AFB). If selected, TACFI would provide up to <b>$2M</b>, matched 1:1 by a '
       '<b>$2M Texas Space Commission (SEARF)</b> award — a <b>$4M, ~24-month</b> program to take the reusable VTVL flight-test vehicle from build to '
       'hover and flight test of a government-furnished RDRE — the ladder to <b>firing that RDRE in space</b>. The TSC board meets <b>11 December 2026</b> and can approve the match.'),
     P('The Key Point: Fire the RDRE in Space — Recover It — Fly It Again', h1)] + L([
     'The objective is to ignite and run a government-furnished RDRE <b>in the space environment</b> (above 100 km: vacuum, microgravity) on Exos\'s planned reusable suborbital vehicle, then recover the engine and its data and fly again.',
     'Ground stands cannot reproduce <b>vacuum ignition, in-space restart, and microgravity propellant feed</b>. That is the gap between a promising ground engine and a space-qualified one, and only flight in space closes it.',
     '<b>Why it matters for space sustainment:</b> RDRE\'s compact, higher-efficiency combustion targets in-space propulsion: orbital transfer vehicles, satellite servicing and repositioning, depots, and landers. Pair it with zero-loss cryo transfer (refuel) and Type V tanks (store), and you have <b>refuel + store + propel</b>, the core of sustained operations and Space Force mobility and logistics.',
     'Reusable means <b>repeated in-space firings per campaign</b>, not one expendable sounding-rocket shot.'])
f += [P('Why It Matters to the Air Force', h1)] + L([
     'RDRE has shown strong ground performance; the missing rungs are <b>recoverable, re-flyable flight test and firing in space</b>. Exos provides the reusable platform, integration, and recovery so each engine test flies, lands, and reflies — not a one-shot expendable.',
     'Dual-use: the same FAA-licensed reusable platform de-risks hypersonic, propulsion, and avionics hardware before it is committed to expensive orbital or weapon-class vehicles.',
     'Texas state capital matches federal dollars 1:1 — the Air Force gets a $4M program for $2M.'])
f += [P('Platform Synergies the Program Leverages', h1)] + L([
     '<b>Integrated Pressurized Structures (IPS):</b> moon-proven TRL 9 Type V composite cryogenic tanks (Scorpius, Exos-affiliated) — flew as fuel and LOX tanks on Intuitive Machines <i>Odysseus</i> and <i>Athena</i>; baseline tank set for IM\'s <i>Nebula</i> orbital transfer vehicle.',
     '<b>Zero-loss cryogenic propellant transfer</b> with Princeton Cryogenics: tank-to-tank transfer planned for flight demonstration on the reusable BLK3 suborbital platform (2027) — the path to in-space refueling, depots, and reusable OTVs (Space Force servicing, mobility and logistics).',
     '<b>Reusable launch with fewer than 5,000 parts</b>, minimal infrastructure (pad + power/comms), fast turnaround.'])
f += [P('Path to Transition — NASA Joins the Pull', h1),
     P('NASA Marshall is advancing RDRE toward flight demonstration and Exos is in active technical and business discussions with the program (meetings 30 Sep and 6 Oct 2026). '
       'Exos\'s Phase II supports a <b>sole-source SBIR Phase III</b> by any agency. With Air Force and NASA both pulling, Gungnir positions a follow-on '
       '<b>STRATFI</b> structured as <b>USAF : NASA : private/state capital</b>, in line with current STRATFI matching rules.'),
     tbl([['Step','Vehicle','Funding'],
          ['1  Now','TACFI on FA9300-25-C-6022','$2M USAF + $2M TSC = $4M'],
          ['2  Parallel','NASA SBIR Phase III (sole-source)','NASA mission funds'],
          ['3  Scale','STRATFI: in-space RDRE firing campaign','USAF + NASA + private/state match']], [0.9*inch, 2.6*inch, W-3.5*inch]),
     P('Team', h1),
     P('<b>Company POC:</b> John Quinn, Cofounder &amp; CEO — jquinn@exosaero.com — 972-740-8355. <b>Program Manager:</b> Neil Milburn, COO. '
       'Built and flown hundreds of rocket engines and dozens of flying vehicles; SBIR Phase II performer to AFRL/RJPE.'),
     P('Distribution: non-proprietary summary. TACFI funding is subject to selection; letters of support are endorsements, not funding commitments. '
       'RDRE hardware is government-furnished; engine sourcing for any follow-on is subject to a program trade study.', disc)]
build(D+'Gungnir_TACFI_OnePager_2026-09-28.pdf', f)

# ---------------- 2. INTERNAL GAME PLAN ----------------
g = [P('GUNGNIR — TACFI Meeting Game Plan (INTERNAL — do not hand out)', title),
     P('Goal: leave with a named government PM, a written commitment to file the next TACFI ingest, and a timeline that lands on the TSC 11 Dec board.', sub),
     P('The one constraint that drives everything', h1),
     P('TACFI match funds must be <b>available/received before the TACFI award</b> (AFWERX TACFI matching guidance; this does not apply to STRATFI). '
       'So the TSC grant must be the <b>§321.16 direct/advance</b> path, not a cost-reimbursement grant, and TSC and AFRL each want the other to go first. '
       'Fix: <b>cross-conditional commitments.</b> AFRL commits in writing to file at the next NOO, subject to the match. TSC approves on 11 Dec, subject to TACFI selection, with funds released before award.'),
     P('Recommended sequence', h1),
     tbl([['When','Action','Owner'],
          ['This week','TACFI meeting: get answers to the questions below, a named AFRL PM/champion, and a commitment-to-file email','John + Neil'],
          ['Same day','Call Norman Garza (TSC): confirm the Dec 11 board packet cutoff and what AFRL paper TSC needs','John'],
          ['30 Sep / 6 Oct','NASA Teasley technical + business meetings: ask for a NASA interest letter naming Gungnir as a transition path','Phil / John'],
          ['~Oct 30 (confirm)','Submit the SEARF match request with the AFRL commitment + NASA interest letter + refreshed 11-doc package','Neil'],
          ['11 Dec','TSC board approves the $2M match, subject to selection, pre-award disbursement','TSC'],
          ['Next NOO','Champion files ingest to afrl.rgv.stratfi-tacfi@us.af.mil; the package is already complete','AFRL champion'],
          ['2027','Open the STRATFI conversation (USAF + NASA + private/state)','John']],
         [1.0*inch, W-2.1*inch, 1.1*inch]),
     P('Questions for the TACFI meeting (get every one answered)', h1)] + L([
     '<b>Commitment:</b> Will AFRL/RJPE file our TACFI ingest at the next NOO? Can we get that in an email or memo we can give to TSC before 11 Dec?',
     '<b>PM:</b> Who is the named government PM/champion: Dr. Harvazinski or an alternate? Who is the backup if his schedule slips again?',
     '<b>Timing:</b> When does the next TACFI NOO open and close (PY27.1?), and when is the internal AFRL deadline for the champion package?',
     '<b>Money:</b> Is the $2M federal share still available at that cycle? Is there a program-office funding line behind it, or only AFWERX money?',
     '<b>Match rules:</b> Does a Texas SEARF §321.16 direct award count as the non-SBIR match? Does it have to be in our account before award, or is an obligated state grant enough? Will AFRL put that in writing for TSC?',
     '<b>Contract face:</b> Who is the AFRL/RJPE contracting officer for the delegation memo? Who signs the collaboration agreement as customer? Do we confirm the Scaled Hypersonics AF track?',
     '<b>Scope:</b> Is the GFE RDRE delivery date firm? It gates the hover test. Would AFRL accept a pressure-fed first flight and pump-fed later?',
     '<b>Transition customer:</b> Is AEDC or another warfighter org the named transition customer? Who signs the customer memorandum?',
     '<b>NASA:</b> Is AFRL open to NASA co-funding or a NASA Phase III off the same Phase II? Would AFRL support a later STRATFI with USAF, NASA, and private/state shares?',
     '<b>In-space firing:</b> Will AFRL state an in-space RDRE firing (vacuum ignition/restart) as the program end-objective? Which step funds it: TACFI, Phase III, or STRATFI? Is vacuum/restart data a stated RJPE need we can quote?',
     '<b>Package:</b> Is anything in our 11-document package out of date for the new cycle? Are there new templates or a new quad-chart format?'])
g += [P('Guardrails for the room', h1)] + L([
     'Lead with the in-space firing; it is the reason this matters beyond a ground test. Frame it as the objective and the planned ladder, not flown or funded. Do not claim a world or U.S. "first" (JAXA flew a detonation engine on a sounding rocket in 2021).',
     'Say "if selected". The LoS is an endorsement, not funding. Never say "awarded" or "committed $2M".',
     'Exos = reusable flight-test platform + integration for a <b>GFE</b> RDRE. We are <b>not</b> an RDRE developer or propulsion provider; the pump is planned, not built.',
     'Cryo transfer + IPS = platform synergy and Space Force SML relevance. Do not add it to the TACFI scope unless AFRL asks.',
     'Anything sent to AFRL, TSC, or NASA goes out under John\'s name. Exo drafts only.'])
build(D+'Gungnir_TACFI_Meeting_GamePlan_INTERNAL_2026-09-28.pdf', g)
print('ok')
