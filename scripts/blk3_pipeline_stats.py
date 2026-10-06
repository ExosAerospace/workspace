"""BLK3 Deal Flow KPIs in Python — mirrors mission-control/blk3-deal-flow.html (stage buckets, rate-card estimates, entX overlay). Import R or run for JSON."""
import json,re
o=json.load(open("/Users/exomac/.openclaw/workspace/mission-control/data/opportunities.json"))
opps=o.get("opportunities") or [v for v in o.values() if isinstance(v,list)][0]
po=json.load(open("/Users/exomac/.openclaw/workspace/mission-control/data/payload-orders.json")); orders=po["orders"] if isinstance(po,dict) else po
def bucket(s):
    s=(s or "").upper()
    if re.search(r"ACTIVE|MEETING|CALL|LOI|QUOTE|NEGOTIAT|DEPOSIT",s): return "active"
    if re.search(r"OUTREACH SENT|SENT|REPLIED|FOLLOW",s): return "outreach"
    if re.search(r"READY|DRAFT",s): return "ready"
    return "early"
def field(d,k):
    m=re.search(r"\*\*"+k+r":\*\*\s*([^\n]+)",d or ""); return m.group(1).strip() if m else ""
TIERS=[(r"tribal|education|k-12|school|student","1U",7500),(r"gov|defense|dod|nasa|navy|army|air force|afrl|missile|hypersonic|clps|lunar|pharma|station|otv|broker|aggregat|\bcro\b|integrator|prime","Quarter bay",255000),(r"photonics|sensor|commercial|manufactur|startup|biotech","6U",45000)]
def est(x):
    v=str(x.get("value") or "")
    if not re.search("full-bay list",v,re.I):
        n=re.sub(r"[^0-9.]","",v)
        try:
            n=float(n)
            if n>0: return n,"Quoted"
        except: pass
    s=f'{x["seg"]} {x["title"]}'
    for r,t,u in TIERS:
        if re.search(r,s,re.I): return u,t
    return 22500,"3U"
W={"active":.5,"outreach":.2,"ready":.1,"early":.05}
P=[]
for x in opps:
    if str(x.get("id","")).startswith("PAY-"):
        x=dict(x); x["b"]=bucket(x.get("status")); x["seg"]=field(x.get("description"),"Segment"); x["usd"],x["tier"]=est(x); P.append(x)
f2=[x for x in orders if not re.search("cancel",x.get("status") or "",re.I)]
booked=820000+sum(x.get("contract_value") or 0 for x in f2)
kg=sum(float(x.get("mass_kg") or 0) for x in f2)
pipe=sum(x["usd"] for x in P)+booked; wt=sum(x["usd"]*W[x["b"]] for x in P)+booked
from collections import Counter
R=dict(pipe=pipe,unbooked=pipe-booked,booked=booked,weighted=wt,kg=kg,n=len(P),stages=Counter(x["b"] for x in P),
 by_tier={t:(sum(1 for x in P if x["tier"]==t),sum(x["usd"] for x in P if x["tier"]==t)) for t in set(x["tier"] for x in P)},
 by_stage_usd={b:sum(x["usd"] for x in P if x["b"]==b) for b in W},
 orders=[(x["customer"],x["payload_name"],x["mass_kg"],x["contract_value"]) for x in f2])
top=sorted([x for x in P if x["b"] in("active","outreach")],key=lambda x:(-W[x["b"]],-x["usd"],-(x.get("priority") or 0)))
R["top"]=[(x["id"],x["title"][:90],x["b"],x["seg"][:70],x["usd"],x["tier"]) for x in top]
if __name__=="__main__": print(json.dumps(R,indent=1,default=str))
