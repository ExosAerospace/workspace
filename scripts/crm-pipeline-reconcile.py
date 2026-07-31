#!/usr/bin/env python3
"""Reconcile the fundraising/BD pipeline (opportunities.json) against the Supabase CRM
(crm-data.json). Emits data/pipeline-crm-links.json (links + live CRM stage) and a
conflict report (pipeline active but CRM closed/failed/archived, or no CRM record).
Non-destructive: writes only the link/reconciliation file."""
import json, re, os, collections
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MC=os.path.join(HERE,'mission-control')
opps=json.load(open(os.path.join(MC,'data/opportunities.json')))['opportunities']
crm=json.load(open(os.path.join(MC,'crm-data.json')))

STOP={'capital','ventures','venture','group','partners','partner','llc','inc','management',
 'holdings','fund','funds','the','co','company','family','office','offices','advisors','asset','llp','lp','vc'}
def toks(s):
    return [t for t in re.findall(r'[a-z0-9]+', (s or '').lower())]
def core(s):
    return set(t for t in toks(s) if t not in STOP and len(t)>2)

# index CRM by tokens
crm_recs=[]
for r in crm:
    comp=r.get('company') or ''
    cont=r.get('contact') or ''
    crm_recs.append((core(comp)|core(cont), r, comp, cont))

def match(name):
    q=core(name)
    if not q: return None,0
    best=None; bestsc=0; bestlen=0
    for ctoks,r,comp,cont in crm_recs:
        ccomp=core(comp)
        if not ccomp: continue
        shared=q & ccomp
        if not shared: continue
        # link if one company name is a token-subset of the other (either direction)
        if shared==q or shared==ccomp:
            sc=1.0 if q==ccomp else 0.9
            # prefer the match that shares the most tokens (more specific)
            if (sc,len(shared))>(bestsc,bestlen):
                bestsc=sc; bestlen=len(shared); best=(r,comp,cont)
    return best,bestsc

DEAD_STAGE=re.compile(r'clos|fail|dead|pass|archiv|declin|inactive',re.I)
PIPE_DEAD=re.compile(r'clos|blackball|dead|declin|pass|❌|🚫',re.I)

links={}; conflicts=[]; nocrm=[]
for o in opps:
    if o.get('category') not in ('Fundraising','Business Development'): continue
    oid=o['id']; title=o.get('title','')
    name=re.split(r'\s[-—/|]\s', title)[0]
    m,sc=match(name)
    pstat=(o.get('status') or '')
    pipe_dead=bool(PIPE_DEAD.search(pstat))
    if m and sc>=0.9:
        r,comp,cont=m
        cstage=r.get('stage') or ''; cstatus=r.get('status') or ''
        crm_dead=bool(DEAD_STAGE.search(cstage+' '+cstatus))
        links[oid]={'crm_id':r.get('id'),'crm_company':comp,'crm_contact':cont,
                    'crm_stage':cstage,'crm_status':cstatus,'confidence':round(sc,2)}
        # conflict: pipeline active but CRM dead, or pipeline dead but CRM active
        why=None
        if crm_dead and not pipe_dead:
            why=f"CRM={cstage or cstatus} but pipeline active"
        elif pipe_dead and not crm_dead and cstage:
            why=f"pipeline dead but CRM={cstage or cstatus}"
        if why:
            links[oid]['conflict']=why
            conflicts.append((oid,title[:45],why))
    else:
        nocrm.append((oid,name[:40]))

out={'generated':'2026-07-02','links':links,
     'summary':{'linked':len(links),'conflicts':len(conflicts),'no_crm_record':len(nocrm)}}
json.dump(out,open(os.path.join(MC,'data/pipeline-crm-links.json'),'w'),indent=1)
print(f"LINKED {len(links)} pipeline entries to CRM | CONFLICTS {len(conflicts)} | NO CRM RECORD {len(nocrm)}")
print("\n=== CONFLICTS (stage mismatch) ===")
for oid,t,why in conflicts: print(f"  {oid}  {t}  ->  {why}")
print("\n=== IN PIPELINE, NOT IN CRM (should be added to CRM) ===")
for oid,n in nocrm[:25]: print(f"  {oid}  {n}")
