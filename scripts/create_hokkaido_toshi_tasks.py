#!/usr/bin/env python3
"""Create Toshi's Hokkaido trip follow-up tasks in Mission Control (approved by John, D-7282121, 2026-10-15 18:27 CDT).
John 10/15 19:09: AstroX + Space One moved to Tier 1. Idempotent: skips any task whose source already exists.
MJOLNIR follow-up already exists as #3796 (not duplicated)."""
import json, urllib.request
K=json.load(open("/Users/exomac/.openclaw/secrets.json"))["supabase_service_role_key"]
SB="https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
H={"apikey":K,"Authorization":"Bearer "+K,"Content-Type":"application/json"}
def sb(m,p,b=None,prefer=None):
    h=dict(H); 
    if prefer: h["Prefer"]=prefer
    r=urllib.request.Request(SB+"/"+p,data=json.dumps(b).encode() if b is not None else None,headers=h,method=m)
    raw=urllib.request.urlopen(r,timeout=30).read().decode(); return json.loads(raw) if raw.strip() else None
RULES=("\n\nRules: capability-level only, no technical data or drawings to any foreign party without export review "
       "(Empowered Official John Quinn, reviewer Denise Shirey). No pricing until John approves. BLK3 timing = 'early 2027'. "
       "Briefing: Hokkaido_Trip_Briefing_Prioritized_Opportunities (Mission Control docs).")
T=[("NYK Line — Japanese thank-you, project-cargo contact, shipping estimate","2026-10-22",88,
    "Tier 1. Send a Japanese thank-you to Daisuke Suga, Satohiko Kodama and Masahiro Morimoto. Ask for NYK's project-cargo contact and a non-binding TX→Japan and TX→Sardinia shipping estimate (dimensions and weights only). Help schedule John's follow-up meeting (booking link sent 10/15). OPP-636."),
   ("Innovative Space Carrier (Hatada-san) — thank-you + recovery call with John","2026-10-22",87,
    "Tier 1. Japanese thank-you to Kojiro Hatada (President & CEO). Propose a call with John on Exos backup recovery for ASCA test flights. Capability deck only."),
   ("AstroX (Oda-san) — follow-up after 10/16 meeting + recovery capability call","2026-10-22",86,
    "Tier 1 (John 10/15). John and Toshi met Shobu Oda on 10/16. Send a Japanese thank-you summarizing what was agreed, and set up the recovery-capability call (gondola/platform and attitude-control device recovery, test-rocket recovery, BLK3 bridge flights). AstroX briefing: AstroX_Briefing_2026-10-15_r2.docx."),
   ("Space One (KAIROS) — open contact via BD group; recovery + avionics/FTS flight-test","2026-10-24",85,
    "Tier 1 (John 10/15). Space One is 0-for-3 on KAIROS (latest, Mar 2026, an apparent flight-termination-system fault). Entry point: Hidenori Yagi, Group Executive, Business Development Group (Space BD can also broker an intro). Offer: recover KAIROS test hardware by drogue/parafoil, and fly avionics/FTS boxes on a recoverable Exos test flight before their next launch. Ask for a call with John. Space One has government (MoD) contracts, so keep it strictly capability-level."),
   ("Government thank-yous — translate John's letters (Sasaki, Mitsuhashi, Kurokawa)","2026-10-24",80,
    "Translate John's thank-you letters to Hajime Sasaki, Vice Governor Tsuyoshi Mitsuhashi and Mayor Yutaka Kurokawa. Get Mitsuhashi/Kurokawa emails via Space Cotan. John sends; no commitments."),
   ("Space BD (Umeda-san) — intro to microgravity utilization team","2026-10-24",72,
    "Ask Umeda for an introduction to Space BD's microgravity utilization team (BLK3 as a pre-ISS screening flight)."),
   ("Mitsui Bussan Aerospace (Mishima-san) — distribution-channel interest","2026-10-29",68,
    "After John's follow-up email, explore Mitsui Bussan's interest as a Japan import/distribution channel (Scorpius tanks, BLK3 services)."),
   ("AMORCE Inc. — verify company registration before any engagement","2026-10-29",55,
    "DD caution: no public business record found. Verify registration and business (Ginza) before engaging Hideyuki Wada / Chihiro Nakamura."),
   ("Hibiki Seiki + Sogo Kanri — courtesy thank-yous; log as future contacts","2026-11-05",40,
    "Courtesy thank-yous. Log Hibiki Seiki (machining) and Sogo Kanri (building management) as future supplier/facilities contacts.")]
def exists(src): return sb("GET",f"tasks?select=id&source=eq.{src}")
psrc="exo-hokkaido-trip-2026-10-parent"
par=exists(psrc)
if par: pid=par[0]["id"]
else:
    pid=sb("POST","tasks",{"title":"Hokkaido trip follow-ups (Oct 2026) — Toshi's ranked list","state":"In Progress","owner":"Toshihisa Kumazawa",
        "assigned_to":"Toshihisa Kumazawa","assigned_email":"toshihisa@exosaero.com","category":"Business Development","priority":85,
        "source":psrc,"tags":["hokkaido-trip-2026-10","japan"],"due_date":"2026-11-05T23:59:59+00:00",
        "description":"Parent for Toshi's ranked follow-ups from John's Hokkaido trip (Oct 13-16, 2026). Approved by John (D-7282121). Tier 1 per John 10/15: NYK, ISC, AstroX, Space One. MJOLNIR follow-up is task #3796."+RULES},"return=representation")[0]["id"]
out=[("parent",pid)]
for i,(title,due,pri,desc) in enumerate(T,1):
    src=f"exo-hokkaido-trip-2026-10-{i:02d}"
    e=exists(src)
    if e: out.append((title,e[0]["id"])); continue
    r=sb("POST","tasks",{"title":f"{i}. {title}","state":"To Do","owner":"Toshihisa Kumazawa","assigned_to":"Toshihisa Kumazawa",
        "assigned_email":"toshihisa@exosaero.com","category":"Business Development","priority":pri,"source":src,
        "tags":["hokkaido-trip-2026-10","japan",f"parent-{pid}"],"due_date":f"{due}T23:59:59+00:00",
        "description":f"Part of #{pid} (Hokkaido trip follow-ups, rank {i}).\n\n{desc}{RULES}"},"return=representation")
    out.append((title,r[0]["id"]))
print(json.dumps(out,ensure_ascii=False,indent=0))
