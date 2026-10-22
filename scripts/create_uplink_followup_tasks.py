#!/usr/bin/env python3
"""Up/Link NYC (Oct 19-21, 2026) follow-ups -> Mission Control, ranked top to bottom (Jon 2026-10-21 20:11 CDT).
Payload customers and BLK3 vehicle needs get priority > 100 + pin:100. Other follow-ups stay below 100.
Idempotent: new tasks keyed by source; existing tasks (#3926/#3932/#3934/#3928) are re-prioritized and linked, not duplicated."""
import json, urllib.request
K=json.load(open("/Users/exomac/.openclaw/secrets.json"))["supabase_service_role_key"]
SB="https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
H={"apikey":K,"Authorization":"Bearer "+K,"Content-Type":"application/json"}
def sb(m,p,b=None,prefer=None):
    h=dict(H)
    if prefer: h["Prefer"]=prefer
    r=urllib.request.Request(SB+"/"+p,data=json.dumps(b).encode() if b is not None else None,headers=h,method=m)
    raw=urllib.request.urlopen(r,timeout=30).read().decode(); return json.loads(raw) if raw.strip() else None
JOHN=("John Quinn","jquinn@exosaero.com"); LIZI=("Lizi Quinn","lquinn@exosaero.com")
RULES=("\n\nRules: John met this contact, so the follow-up goes from John with his booking link, Cc Lizi. "
       "BLK3 timing = 'early 2027'. Never call BLK3 bare 'FAA-licensed' (Part 431 to 450). "
       "No technical data to a foreign party without export review. Pricing only from the public payload calculator.")
# (rank, existing_id or None, title, priority, owner, due, lane, desc)
T=[
 (1,3926,None,130,JOHN,"2026-10-28","BLK3 vehicle",None),
 (2,3932,None,125,LIZI,"2026-10-28","Payload",None),
 (3,None,"Zeno Power (Tyler Bernstein): BLK3 qualification flight with inert surrogate units",122,JOHN,"2026-10-30","Payload",
  "Met at Up/Link 10/20. CRM Tier 1. Offer a BLK3 qualification flight using inert surrogate units (no radioactive material). "
  "Nestor Levin (SpaceWERX) also raised space nuclear on 10/21, so Zeno ties into that thread.\n\nDone when: intro call booked."),
 (4,3934,None,120,JOHN,"2026-10-24","Payload",None),
 (5,None,"Anywaves Federal (Nicolas Hine, CEO): antenna/RF flight qualification on BLK3",118,JOHN,"2026-10-30","Payload",
  "Card from Up/Link Day 2. n.hine@anywaves-federal.com, Austin. CRM Tier 2 payload customer. Pitch: flight-qualify antennas/RF hardware on BLK3 in early 2027. "
  "Check foreign-ownership ties (Anywaves parent) before sharing any technical data.\n\nDone when: call booked or payload questionnaire returned."),
 (6,None,"Space Tango (Molly Sullivan, Dir. Corp Dev): broker a multi-PI BLK3 payload slot",116,JOHN,"2026-10-30","Payload",
  "Met in person at Up/Link 10/20 (CRM 0a8ed6ac, Engaged). She is the way in after Twyman went silent. Pitch: Space Tango as broker/aggregator filling a BLK3 slot with several PIs.\n\nDone when: meeting booked."),
 (7,None,"Space Angel (Ram Kuppusamy): Australia NCE, dedicated BLK3 at Eucla, book follow-up meeting",115,JOHN,"2026-10-28","BLK3 vehicle",
  "Ram was at Up/Link 10/20. Meeting-request draft (email + text) was sent to Jon's inbox 10/20. Ties to the Australia National Charter Enterprise pursuit (ram@spaceangel.io).\n\nDone when: meeting held and LOI markup requested."),
 (8,None,"Proteus Space (David Kervin, CEO): manage the BLK3 payload bay + classified-payload path",112,JOHN,"2026-11-04","Payload",
  "Met at Up/Link 10/20, CRM Tier 1. Jon: Proteus could manage our BLK3 payload bay. Per their pitch they hold a TS facility clearance, which opens a classified-payload integration path.\n\nDone when: intro call booked."),
 (9,None,"ISS National Lab (Michael Roberts, Chief Scientist): virtual meeting from his LinkedIn note",110,JOHN,"2026-10-28","Payload",
  "He messaged John 10/21 after the Up/Link pitch asking for a virtual meeting. CRM 7509cac8. Reply draft with booking link is in Jon's inbox. Angle: BLK3 as a screening flight before ISS.\n\nDone when: meeting booked."),
 (10,None,"Starport Space (Roberto Vela III / Thomas Yoo): payload-readiness broker + Korea-US channel",108,JOHN,"2026-11-04","Payload",
  "Houston. Met at Up/Link 10/20. They help payloads get flight-ready and bridge Korea and the US, so they can feed BLK3 payloads.\n\nDone when: intro call booked."),
 (11,None,"SpaceWERX (Nestor Levin): send follow-up; DoD payloads via STP Kirtland / SSC Front Door + TACFI PY26.2",107,JOHN,"2026-10-28","Payload",
  "Met 10/21. Notes on #3898. Follow-ups: Space Test Program at Kirtland via the SSC Front Door (DoD payload rides on BLK3), THE BR-DGE/DTI, SpaceWERX PY26.2 TACFI (rolling), on-orbit logistics follow-on, space nuclear (ties to Zeno). Follow-up draft is in Jon's inbox.\n\nDone when: email sent and STP Front Door request submitted."),
 (12,None,"Big Bang Boom Solutions (DRONA; Atul Gupta): offer a BLK3 test flight",105,JOHN,"2026-11-04","Payload",
  "Chennai, India company that pitched its DRONA space system at Up/Link 10/20. Jon: we can test for them. Atul Gupta (London) in CRM. "
  "Foreign party: run export review and denied-party screening before any technical exchange.\n\nDone when: payload questionnaire sent."),
 (13,3928,None,104,JOHN,"2026-11-04","BLK3 vehicle",None),
 (14,None,"Aurelia Institute (Ariel Ekblaw): follow up on BLK3 payload for MIT SEI",103,JOHN,"2026-11-04","Payload",
  "Jon emailed her 8/10 about BLK3 for MIT SEI. At Up/Link she was raising Aurelia Foundry II (Form D filed 10/09/2026). CRM updated.\n\nDone when: reply received or call booked."),
 (15,None,"Space Grove (Melissa Patton): send the two docs (external agenda + MC trial questions)",95,JOHN,"2026-10-23","Other",
  "Jon 10/21: 'send the two docs to Melissa Patton'. Draft to melissa@thespacegrove.org is in Jon's inbox; files in drafts/uplink/.\n\nDone when: sent."),
 (16,None,"DIA (Inocentes): send follow-up email",92,JOHN,"2026-10-28","Other",
  "Emails added to CRM 10/21; follow-up draft is in Jon's inbox. Government contact, so no CUI in email.\n\nDone when: sent."),
 (17,None,"Up/Link 1:1s with no notes yet: send Exo your takeaways (Woodhouse, Graham, Shen, Kall, KickStage, Reynolds)",90,JOHN,"2026-10-23","Other",
  "No notes captured from: Woody Woodhouse (Leonardo DRS), Jamie Graham (KippsDeSanto), Crystal Shen (NYSE), Adam Kall (KMI), KickStage, Elizabeth Reynolds (Space Age). "
  "Reply on this task with one line each and Exo will add any payload or BLK3 follow-ups to this list.\n\nDone when: notes posted."),
 (18,None,"Quilty Space (Chris Quilty / Justin Cadman): M&A banker conversation",88,JOHN,"2026-11-04","Other",
  "Cards from Up/Link 10/20, CRM Tier 1. Candidate M&A advisor for SSLC, CTD and the RTO roll-up. Justin Cadman leads M&A.\n\nDone when: intro call booked."),
 (19,None,"Investor follow-ups: Chenel Capital (Richard Chenel), S4E Capital (Jodi Bartin), Mars Fund (Alex Burg)",85,JOHN,"2026-11-04","Other",
  "All three met at Up/Link and are in CRM. Bartin follow-up draft is in Jon's inbox. Series A worklist is paused for the RTO, so keep these as relationship touches.\n\nDone when: each has a reply or a booked call."),
 (20,None,"Low-priority Up/Link contacts: Gatens, Allocation.Space, KeyCAD, Dyson Sphere Labs, Hekinian",55,JOHN,"2026-11-15","Other",
  "Robyn Gatens (ret. NASA ISS director): relationship touch. Allocation.Space: parametric insurance idea. KeyCAD: demo draft in Jon's inbox (no CAD uploads, ITAR). "
  "Dyson Sphere Labs: Tier 3 marketplace. Aram Hekinian: possible launch video vendor.\n\nDone when: touched or closed."),
]
psrc="exo-uplink-nyc-2026-10-parent"
par=sb("GET",f"tasks?select=id&source=eq.{psrc}")
if par: pid=par[0]["id"]
else:
    pid=sb("POST","tasks",{"title":"Up/Link NYC (Oct 19-21) follow-ups: ranked checklist","state":"In Progress","owner":JOHN[0],
        "assigned_to":JOHN[0],"assigned_email":JOHN[1],"category":"Business Development","priority":115,"source":psrc,
        "tags":["up-link-2026","pin:100"],"due_date":"2026-11-04T23:59:59+00:00",
        "description":"Jon 2026-10-21: every Up/Link follow-up, ranked top to bottom. Payload customers and BLK3 vehicle needs are above 100. "
        "Separate: MUFG/Intrepid #3927 stays at 120 (Jon 10/21). Checklist document is on the Documents tab."},"return=representation")[0]["id"]
out=[("parent",pid,115)]
for rank,eid,title,pri,(own,mail),due,lane,desc in T:
    tags_new=["up-link-2026",f"parent-{pid}",f"uplink-rank-{rank:02d}"]+(["pin:100"] if pri>100 else [])
    if eid:
        t=sb("GET",f"tasks?select=id,title,tags,description&id=eq.{eid}")[0]
        tags=[x for x in (t.get("tags") or []) if not str(x).startswith(("pin:","uplink-rank-"))]
        tags=list(dict.fromkeys(tags+tags_new))
        d=t.get("description") or ""
        note=f"Up/Link checklist #{pid}, rank {rank} ({lane}). Priority set to {pri} by Jon's 10/21 ask."
        if note not in d: d=note+"\n\n"+d
        sb("PATCH",f"tasks?id=eq.{eid}",{"priority":pri,"tags":tags,"due_date":f"{due}T23:59:59+00:00","description":d})
        out.append((t["title"][:70],eid,pri)); continue
    src=f"exo-uplink-nyc-2026-10-{rank:02d}"
    e=sb("GET",f"tasks?select=id&source=eq.{src}")
    if e: out.append((title,e[0]["id"],pri)); continue
    r=sb("POST","tasks",{"title":f"{rank}. {title}","state":"To Do","owner":own,"assigned_to":own,"assigned_email":mail,
        "category":"Payload Sales" if lane=="Payload" else "Business Development","priority":pri,"source":src,"tags":tags_new,
        "due_date":f"{due}T23:59:59+00:00",
        "description":f"Part of #{pid} (Up/Link follow-ups, rank {rank}, {lane}).\n\n{desc}{RULES if lane!='Other' else ''}"},"return=representation")
    out.append((title,r[0]["id"],pri))
print(json.dumps(out,ensure_ascii=False,indent=0))
