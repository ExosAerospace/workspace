# -*- coding: utf-8 -*-
# Classify CRM contacts CONUS vs Non-CONUS (international) into a SIDE-FILE that survives
# crm-data.json regeneration. Heuristics: email ccTLD, phone country code, country keywords.
# Output: mission-control/data/crm-region.json = { id: {region, country, signal} }
import json, os, re

WS=os.path.expanduser("~/.openclaw/workspace")
CRM=os.path.join(WS,"mission-control","crm-data.json")
OUT=os.path.join(WS,"mission-control","data","crm-region.json")

# country ccTLD -> display country (non-US)
CCTLD={"jp":"Japan","au":"Australia","uk":"United Kingdom","gb":"United Kingdom","ca":"Canada",
 "de":"Germany","fr":"France","it":"Italy","es":"Spain","nl":"Netherlands","se":"Sweden","no":"Norway",
 "fi":"Finland","dk":"Denmark","ch":"Switzerland","at":"Austria","be":"Belgium","ie":"Ireland","in":"India",
 "sg":"Singapore","kr":"South Korea","cn":"China","hk":"Hong Kong","tw":"Taiwan","nz":"New Zealand",
 "br":"Brazil","mx":"Mexico","ae":"UAE","il":"Israel","za":"South Africa","pl":"Poland","cz":"Czechia",
 "pt":"Portugal","gr":"Greece","lu":"Luxembourg","eu":"Europe"}
# country keywords in company/notes/fit -> country
KW=[("japan","Japan"),("tokyo","Japan"),("hokkaido","Japan"),("hospo","Japan"),("space cotan","Japan"),
 ("kumazawa","Japan"),("australia","Australia"),("eucla","Australia"),("space angel","Australia"),
 ("perth","Australia"),("torino","Italy"),("torvergata","Italy"),("italia","Italy"),("italy","Italy"),
 ("i3p","Italy"),("euronext dublin","Ireland"),("dublin","Ireland"),("ireland","Ireland"),
 ("united kingdom","United Kingdom"),(" uk ","United Kingdom"),("london","United Kingdom"),("goodbody","Ireland"),
 ("canada","Canada"),("germany","Germany"),("munich","Germany"),("france","France"),("cailabs","France"),
 ("paris","France"),("india","India"),("singapore","Singapore"),("korea","South Korea"),("seoul","South Korea"),
 ("kolon","South Korea"),("taiwan","Taiwan"),("new zealand","New Zealand"),("netherlands","Netherlands"),
 ("switzerland","Switzerland"),("israel","Israel"),("uae","UAE"),("dubai","UAE"),("abu dhabi","UAE"),
 ("brazil","Brazil"),("mexico","Mexico"),("spain","Spain"),("sweden","Sweden"),("norway","Norway")]
US_STATES=set("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC".split())

def classify(c):
    email=(c.get("email") or "").lower().strip()
    blob=" ".join(str(c.get(k) or "") for k in ("company","contact","notes","fit_thesis","category","title","offer")).lower()
    phone=str(c.get("phone") or "")
    # 1) email ccTLD
    m=re.search(r"@[\w.-]+\.([a-z]{2})$", email)
    if m and m.group(1) in CCTLD:
        return "Non-CONUS", CCTLD[m.group(1)], f"email .{m.group(1)}"
    # 2) country keyword
    for kw,ct in KW:
        if kw in blob:
            return "Non-CONUS", ct, f"kw:{kw.strip()}"
    # 3) phone country code (non +1)
    pd=re.sub(r"[^\d+]","",phone)
    if pd.startswith("+") and not pd.startswith("+1") and len(pd)>=8:
        return "Non-CONUS", "Intl (phone)", f"phone {pd[:4]}"
    # 4) US signals -> CONUS
    if pd.startswith("+1") or re.match(r"^\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}", phone.strip()):
        return "CONUS", "United States", "US phone"
    if re.search(r"\b(TX|CA|FL|NM|CO|VA|MD|WA|AL|AZ|NY|MA|DC|OH|MI|GA)\b", c.get("notes") or ""):
        return "CONUS", "United States", "US state"
    if email.endswith(".gov") or email.endswith(".mil"):
        return "CONUS", "United States (gov)", "gov domain"
    return "Unknown", None, "no signal"

def main():
    rows=json.load(open(CRM)); rows=rows if isinstance(rows,list) else rows.get("contacts",[])
    reg={}
    from collections import Counter
    cnt=Counter()
    for c in rows:
        cid=str(c.get("id"))
        r,country,sig=classify(c)
        reg[cid]={"region":r,"country":country,"signal":sig}
        cnt[r]+=1
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    json.dump(reg,open(OUT,"w"),indent=0)
    print("classified",len(rows),"->",dict(cnt))
    # sample of Non-CONUS by country
    from collections import Counter as C2
    bycountry=C2(v["country"] for v in reg.values() if v["region"]=="Non-CONUS")
    print("Non-CONUS by country:",dict(bycountry.most_common(12)))

if __name__=="__main__": main()
