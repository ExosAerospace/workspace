# OLP -> Ovation/AEC point matcher (Dell plant, #power work stream)
# Maps OLP PtDesc -> AEC ObjectName tag via PDF-scoped + glossary-normalized fuzzy match.
# Prereq: pdftotext -layout of the Ovation Control Builder publish PDF to /tmp/pub.txt
#   pdftotext -layout media/inbound/Publish_*.pdf /tmp/pub.txt
# Tiers: AUTO(>=92 verified), REVIEW(>=75 + top-3 cands cols O/P/Q), MANUAL, ARTIFACT.
# Point name form: <tag>.U1@DELL1 . Glossary confirmed by Jon (BAL=Ball, CR=Cold Reheat, etc.).
import openpyxl, re
from rapidfuzz import process, fuzz
from openpyxl.styles import Font, PatternFill
AEC='/Users/exomac/.openclaw/media/inbound/AEC_Dell_Analog-Digital_Points---0ccd0349-6911-49da-a63b-13c178c03bdd.xlsx'
OLP='/Users/exomac/.openclaw/workspace/media/inbound/openclaw-staged-102b1633-2e34-409c-8ed9-7effcc76c2b7/OLP_Start_Template---8b7dfd04-ab41-4ab3-8367-525922dd4147.xlsx'
OUT='/Users/exomac/.openclaw/workspace/drafts/OLP_Populated_from_AEC_v8.xlsx'
SUFFIX='.U1@DELL1'
OVERRIDE={
 '01CEM->50%':[('1-JX-6629','GT LOAD TO CEMS'),('G1-L30OUT-ALM','GT OUT OF EMISS COMPL MODE'),('G1-AT-EMUNSTB','EMISSION UNSTABLE FLAG')],
 '02CEMS->50%':[('2-JX-6629','GT LOAD TO CEMS'),('G2-L30OUT-ALM','GT OUT OF EMISS COMPL MODE'),('G2-AT-EMUNSTB','EMISSION UNSTABLE FLAG')],
}
NOTE={'hdr.xlsx':'HEADER point - source description truncated (.xlsx paste artifact); full PtDesc needed'}

ABBR={
# equipment
'CT':'COMBUSTION TURBINE','CTG':'COMBUSTION TURBINE','GT':'COMBUSTION TURBINE','COMB':'COMBUSTION','TURB':'TURBINE',
'ST':'STEAM TURBINE','STG':'STEAM TURBINE','HRSG':'HEAT RECOVERY STEAM GENERATOR','HR':'HEAT RECOVERY STEAM GENERATOR',
'H':'HEAT RECOVERY STEAM GENERATOR','BFP':'BOILER FEED PUMP','GSU':'GENERATOR STEP UP','DB':'DUCT BURNER',
'BRN':'BURNER','BURNERS':'BURNER','STK':'STACK','DMPR':'DAMPER','SWGR':'SWITCHGEAR','HTR':'HEATER','GEN':'GENERATOR',
'FG':'FUEL GAS','FAN':'FAN',
# sections
'HP':'HIGH PRESSURE','IP':'INTERMEDIATE PRESSURE','LP':'LOW PRESSURE','CRH':'COLD REHEAT','HRH':'HOT REHEAT',
'RH':'REHEAT','CR':'COLD REHEAT','SH':'SUPERHEAT','SAT':'SATURATED','IPTEMP':'INTERMEDIATE PRESSURE TEMPERATURE',
# process/meas
'STM':'STEAM','FLW':'FLOW','PRS':'PRESSURE','PRESS':'PRESSURE','PRES':'PRESSURE','LVL':'LEVEL','LEV':'LEVEL',
'TEMP':'TEMPERATURE','ROC':'RATE OF CHANGE','MW':'MEGAWATT','MEGAWATTS':'MEGAWATT','MVAR':'MVAR','NOX':'NOX',
'CO':'CO','NH3':'AMMONIA','SP':'SETPOINT','PWR':'POWER','SYS':'SYSTEM','HIHI':'HIGH HIGH','HI':'HIGH','LO':'LOW',
# states/actions
'XFER':'TRANSFER','XFR':'TRANSFER','BYP':'BYPASS','ISO':'ISOLATION','ISOL':'ISOLATION','VLV':'VALVE','VLVS':'VALVE',
'V':'VALVE','CLSD':'CLOSED','CLOSD':'CLOSED','CLS':'CLOSED','OP':'OPEN','OPN':'OPEN','OPND':'OPENED','CMD':'COMMAND',
'TRP':'TRIP','TRIPPED':'TRIP','REMT':'REMOTE','REM':'REMOTE','MAN':'MANUAL','MSTR':'MASTER','SEL':'SELECT',
'BAL':'BALL','CAL':'CALIBRATION','CALC':'CALCULATED','COMP':'COMPLETE','XMITT':'TRANSMITTER','BLK':'BLOCK',
'WRM':'WARMUP','CNTL':'CONTROL','CTL':'CONTROL','CTRL':'CONTROL','MIN':'MINIMUM','BQ':'BAD QUALITY',
'USTR':'UNSATURATED','LMT':'LIMIT','TRGT':'TARGET','TC':'TEMPERATURE CONTROL','SD':'SHUTDOWN','SHUTDN':'SHUTDOWN',
'STRT':'START','SU':'STARTUP','STAT':'STATUS','POS':'POSITION','SPD':'SPEED','PERM':'PERMISSIVE','ALM':'ALARM',
'AUT':'AUTO','REQ':'REQUEST','DR':'DRAIN','DRN':'DRAIN','HDR':'HEADER','DISCH':'DISCHARGE','SUCT':'SUCTION',
'WTR':'WATER','PMP':'PUMP','BRKR':'BREAKER',
# controls/emissions
'CEMS':'CONTINUOUS EMISSIONS MONITORING','SCR':'SELECTIVE CATALYTIC REDUCTION','AVR':'AUTOMATIC VOLTAGE REGULATOR',
'BOP':'BALANCE OF PLANT','EMS':'ENERGY MANAGEMENT','AGC':'AUTOMATIC GENERATION CONTROL','ELEM':'ELEMENT',
# relays
'86G':'GENERATOR LOCKOUT','86T':'TRANSFORMER LOCKOUT','SGC':'STANDARD GAS COMBUSTION',
}
EQ=r'(CTG|CT|GT|STG|ST|HRSG|HR|BFP|DB|H|U|G)'
def preslash(s):
    s=s.upper()
    for a,b in [('B/P','BYPASS'),('S/U','STARTUP'),('U/STR','UNSATURATED'),('W/BYPASSES','WITH BYPASSES'),
                ('W/','WITH '),('TRIP/RESET','TRIP RESET'),('HP/IP/LP','HP IP LP'),('AND/OR','AND OR')]:
        s=s.replace(a,b)
    return s
def canon(s):
    if not s: return '',''
    s=preslash(str(s))
    s=re.sub(r'[^A-Z0-9 ]',' ',s)
    s=re.sub(r'\bH\d{2,}\b',' ',s)         # drop GE flow-config codes (H15) but keep H1/H2
    s=re.sub(EQ+r'(\d)',r'\1 \2',s)      # split glued unit digits: HRSG2->HRSG 2, H1->H 1
    s=re.sub(r'\s+',' ',s).strip()
    sig=s                                 # signature uses codes + split digits
    exp=' '.join(ABBR.get(t,t) for t in s.split())
    return sig, exp
def sigparts(sig):
    fam=set()
    for x in re.findall(r'\b(CTG|CT|GT|STG|ST|HRSG|HR|H|BFP|GSU|GEN|DB)\b',sig):
        fam.add({'CTG':'CT','GT':'CT','STG':'ST','HRSG':'HR','H':'HR'}.get(x,x))
    sec=set(re.findall(r'\b(HP|IP|LP|CRH|HRH)\b',sig))
    num=set(re.findall(r'(?<![0-9])([12])(?![0-9])',sig))
    return fam,sec,num
def tag_unit(tag):
    t=str(tag).upper()
    m=re.match(r'^([GSU])(\d)',t) or re.match(r'^(\d)[-A-Z]',t)
    if m:
        d=m.group(2) if m.lastindex==2 else m.group(1)
        return d if d in '12' else None
    return None
def conflict(sa,sb,tag=None):
    fa,se_a,na=sigparts(sa); fb,se_b,nb=sigparts(sb)
    if fa and fb and not (fa&fb): return True
    if se_a and se_b and not (se_a&se_b): return True
    if na and nb and not (na&nb): return True
    tu=tag_unit(tag) if tag else None
    if na and tu and tu not in na: return True
    an=' NOT ' in f' {sa} '; bn=' NOT ' in f' {sb} '
    if an!=bn: return True
    return False

txt=open('/tmp/pub.txt').read()
pdftoks=set(re.findall(r'[A-Za-z0-9][A-Za-z0-9_\-\.]{2,}', txt))
wb=openpyxl.load_workbook(AEC,read_only=True,data_only=True)
rows=[]
for sh in ['DigitalPoint','AnalogPoint']:
    ws=wb[sh]
    for r in ws.iter_rows(min_row=2,values_only=True):
        name=r[1]; desc=r[10]
        if not desc: continue
        if str(desc).strip().upper()=='@ OVATION CONTROL BUILDER @': continue
        if not (name and str(name).strip() in pdftoks): continue
        sig,exp=canon(desc)
        if exp: rows.append((exp,sig,name,str(desc).strip(),list(r[2:11])))
seen={}; ch=[]; idx=[]
for i,rec in enumerate(rows):
    if rec[0] not in seen:
        seen[rec[0]]=i; ch.append(rec[0]); idx.append(i)
print('scoped+glossary unique descs:',len(ch))

wbo=openpyxl.load_workbook(OLP); ws=wbo['Template1']
for col,t in [(13,'Status'),(14,'MatchScore'),(15,'Cand1 tag | desc'),(16,'Cand2 tag | desc'),(17,'Cand3 tag | desc')]:
    c=ws.cell(row=4,column=col,value=t); c.font=Font(bold=True)
green=PatternFill('solid',fgColor='C6EFCE'); yellow=PatternFill('solid',fgColor='FFEB9C'); red=PatternFill('solid',fgColor='FFC7CE')
nA=nR=nM=0
for row in range(5,293):
    raw=ws.cell(row=row,column=2).value
    if not raw or not str(raw).strip(): continue
    raws=str(raw).strip()
    if raws in NOTE:
        ws.cell(row=row,column=13,value='MANUAL'); ws.cell(row=row,column=1,value='manual entry req')
        for c in range(3,12): ws.cell(row=row,column=c,value='manual entry req')
        ws.cell(row=row,column=15,value=NOTE[raws])
        for c in range(1,18): ws.cell(row=row,column=c).fill=PatternFill('solid',fgColor='FFC7CE')
        nM+=1; continue
    if raws in OVERRIDE:
        ov=OVERRIDE[raws]
        ws.cell(row=row,column=1,value=ov[0][0]+SUFFIX)
        ws.cell(row=row,column=13,value='REVIEW'); ws.cell(row=row,column=14,value='manual bind')
        for k,(tg,ds) in enumerate(ov[:3]): ws.cell(row=row,column=15+k,value=f'{tg}{SUFFIX} | {ds}')
        for c in range(1,18): ws.cell(row=row,column=c).fill=PatternFill('solid',fgColor='FFEB9C')
        nR+=1; continue
    qsig,qexp=canon(raw)
    cands=process.extract(qexp,ch,scorer=fuzz.token_sort_ratio,limit=3)
    top=cands[0]; rec=rows[idx[top[2]]]; score=top[1]
    conf=conflict(qsig,rec[1],rec[2])
    for k,cd in enumerate(cands):
        rr=rows[idx[cd[2]]]
        ws.cell(row=row,column=15+k,value=f'{rr[2]}{SUFFIX} | {rr[3]} ({cd[1]:.0f})')
    ws.cell(row=row,column=14,value=round(score,1))
    if score>=92 and not conf:
        status='AUTO'; nA+=1; fill=green
        ws.cell(row=row,column=1,value=rec[2]+SUFFIX)
        for j,v in enumerate(rec[4]): ws.cell(row=row,column=3+j,value=v)
    elif score>=75:
        status='REVIEW'; nR+=1; fill=yellow
        ws.cell(row=row,column=1,value=rec[2]+SUFFIX)
        for j,v in enumerate(rec[4]): ws.cell(row=row,column=3+j,value=v)
    else:
        status='MANUAL'; nM+=1; fill=red
        ws.cell(row=row,column=1,value='manual entry req')
        for c in range(3,12): ws.cell(row=row,column=c,value='manual entry req')
    ws.cell(row=row,column=13,value=status)
    for c in range(1,18): ws.cell(row=row,column=c).fill=fill
wbo.save(OUT)
print('OUT',OUT)
print(f'AUTO:{nA}  REVIEW:{nR}  MANUAL:{nM}')
