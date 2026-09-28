#!/usr/bin/env python3
"""
Explode the 7 tiered BLK3 Flight 2 outreach cards (#1301-1306) into ONE custom-email
task per target, assigned to Lizi, sequenced by booking probability at 2 sends/business day.
Keeps master #1300. Marks #1301-1306 superseded.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, urllib.request, datetime

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
import os  # supabase secret key loader (exo3 audit fix #1)
K  = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
HDR = {"apikey": K, "Authorization": "Bearer " + K, "Content-Type": "application/json"}

def req(method, path, body=None, prefer=None):
    h = dict(HDR)
    if prefer: h["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(SB + "/" + path, data=data, headers=h, method=method)
    with urllib.request.urlopen(r) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None

# ---- shared email scaffold -------------------------------------------------
IDENTITY = ("Exos Aerospace is one of only three FAA-licensed reusable rocket launch "
            "providers in the US, and we have been flying reusable suborbital vehicles since 2018. "
            "Our next mission, BLK3 Flight 2, launches in late Q1 / early Q2 2027 from Spaceport "
            "America with 135 kg of payload capacity open now, including small rideshare slots.")

CLOSE = ("I can send our Payload User Guide and hold a tentative slot while you evaluate fit. "
         "Would you have 15 minutes in the next week or two to talk?\n\nBest regards,\nLizi Quinn")

ASK = {
 "univ":    "A 1U to 3U slot on Flight 2 would give your team real microgravity plus recovery of the hardware after flight, at a fraction of an orbital campaign.",
 "channel": "One agreement could place several of your PIs' payloads on a single Flight 2 manifest, and lock capacity before the bay fills.",
 "derisk":  "Flight 2 is a fast, low-cost way to qualify your hardware in real flight before you commit it to orbit.",
 "biotech": "Flight 2 offers a rapid microgravity screening run for your program, with samples returned to you within days of landing.",
 "displace":"With New Shepard paused and ZERO-G grounded, Flight 2 is a near-term home for funded payloads that have lost their ride.",
 "gov":     "We would value Exos being considered as a flight provider for your suborbital payload and flight-test needs on this timeline.",
 "anchor":  "I would like to confirm your Flight 2 slot and get the reservation deposit scheduled so your payload is locked to the manifest.",
}

def email(first, hook, seg, subject):
    return (f"SUBJECT: {subject}\n\n"
            f"Hello {first},\n\n{hook}\n\n{IDENTITY}\n\n{ASK[seg]}\n\n{CLOSE}")

# ---- prioritized target list (send order = booking probability) ------------
# (first, contact_display, address_or_None, gate['' | 'verify' | 'intl' | 'gov'], seg, hook, subject)
T = [
 ("Scott","entX — Scott Edwards","", "", "anchor",
  "Thank you again for signing on to BLK3 Flight 2 with your radioisotope-heater-unit payload. With the manifest now filling for the early-2027 flight, I want to make sure your slot stays first in line.",
  "Confirming your BLK3 Flight 2 slot"),
 ("Markus","University of North Dakota — Markus Allgaier & Tim Young",None,"verify","univ",
  "Following up on your team's strong interest in flying on BLK3. Your early-2027 window lines up exactly with our next flight, and I would like to lock in your timing before the bay fills.",
  "BLK3 Flight 2 — securing UND's early-2027 slot"),
 ("Jim","CU Boulder — James 'Jim' Nabity",None,"verify","univ",
  "I know you have a BLK3 payload proposal in progress. With Flight 2 now manifesting for early 2027, I would like to help you secure a slot on this specific flight.",
  "BLK3 Flight 2 — your CU Boulder payload"),
 ("Stefanie","BioServe Space Technologies — Stefanie Countryman","countrym@colorado.edu","","channel",
  "With New Shepard paused for over two years, many of your ISS PIs need a near-term microgravity flight. BLK3 Flight 2 in early 2027 can carry a batch of BioServe payloads on a single manifest.",
  "BLK3 Flight 2 — a near-term flight for your PIs"),
 ("Katie","BioOrbit — Dr. Katie King","business@bioorbit.space","","biotech",
  "Your microgravity crystallization work is an ideal fit for a fast suborbital screening run. BLK3 Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a screening flight for BioOrbit"),
 ("Catriona","Sanford / ISSCOR (UC San Diego) — Dr. Catriona Jamieson","cjamieson@ucsd.edu","","biotech",
  "Your stem-cell and cancer microgravity research is exactly the kind of program Flight 2 can serve, with samples back in your hands within days of landing.",
  "BLK3 Flight 2 — a microgravity run for ISSCOR"),
 ("Prakash","Notre Dame — Prakash Nallathamby",None,"verify","univ",
  "Following up on the materials I sent. Given your interest in funded payloads and wet-lease options, I want to walk you through the Flight 2 manifest opening for early 2027.",
  "BLK3 Flight 2 — Notre Dame payload follow-up"),
 ("Thomas","Notre Dame — Thomas Juliano",None,"verify","univ",
  "I owe you a follow-up. Your hypersonic and fluids work would fly well on BLK3, and Flight 2 is manifesting now for early 2027.",
  "BLK3 Flight 2 — reconnecting on your payload"),
 ("Max","Vast Space — Max Haot","max@vastspace.com","verify","channel",
  "You hold MOUs with several groups that are a perfect fit for suborbital screening. One agreement could place LambdaVision, BioOrbit, Sanford ISSCOR, and Auxilium payloads on Flight 2 together.",
  "BLK3 Flight 2 — placing your MOU partners on one manifest"),
 ("Twyman","Space Tango — Twyman Clements","tclements@spacetango.com","verify","channel",
  "Your PI book needs near-term flights while ISS access tightens. A single agreement could fill a meaningful share of the Flight 2 bay with Space Tango payloads.",
  "BLK3 Flight 2 — capacity for your PI book"),
 ("Michael","ISS National Lab — Dr. Michael Roberts","michael.roberts@issnationallab.org","verify","channel",
  "You manage hundreds of PIs a year, many of whom would benefit from a low-cost suborbital pre-qualification before an ISS run. Flight 2 can serve as that on-ramp in early 2027.",
  "BLK3 Flight 2 — a suborbital on-ramp for your PIs"),
 ("Amela","Voyager / Nanoracks — Amela Wilson","awilson@nanoracks.com","verify","channel",
  "Your large ISS customer base needs flight options during the New Shepard pause. Flight 2 in early 2027 can absorb a batch of those payloads on one manifest.",
  "BLK3 Flight 2 — flight options for your customers"),
 ("Jessica","ASU / Space Edge — Jessica Rousset",None,"verify","univ",
  "Good to reconnect after our meeting. With Flight 2 manifesting for early 2027, I would like to move Space Edge from interest to a reserved slot.",
  "BLK3 Flight 2 — Space Edge next steps"),
 ("Jeff","Capitol Technology University (RockSat) — Jeff Volosin","jfvolosin@captechu.edu","","univ",
  "Your RockSat student teams would get a real reusable-rocket flight and hardware recovery on BLK3. Flight 2 launches early 2027 with 1U-class slots open.",
  "BLK3 Flight 2 — a flight for your RockSat teams"),
 ("Pedro","Embry-Riddle — Pedro Llanos",None,"verify","univ",
  "Following up on your interest in a 1U payload. Flight 2 is manifesting for early 2027 and a slot would fit your program timeline well.",
  "BLK3 Flight 2 — your 1U payload"),
 ("Francisco","USC — Francisco Valero-Cuevas",None,"verify","univ",
  "I would like to close out our earlier conversation with a concrete Flight 2 slot. Your neuromuscular research would fly well on a suborbital microgravity run in early 2027.",
  "BLK3 Flight 2 — USC payload slot"),
 ("Roberto","Brown University — Roberto Zenit",None,"verify","univ",
  "Your fluids and soft-matter work is a strong fit for suborbital microgravity. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a fluids flight for your lab"),
 ("David","RS&H — David Schleeper",None,"verify","derisk",
  "Thank you for the referral conversation. The nuclear payload you mentioned is well suited to a controlled suborbital flight test, and Flight 2 is manifesting for early 2027.",
  "BLK3 Flight 2 — your nuclear payload test"),
 ("Jose","Puerto Rico Space Foundation — Jose Molina",None,"verify","univ",
  "Your early-2027 timing lines up perfectly with Flight 2. I would like to help the Foundation place a payload and, ideally, a recurring student pipeline.",
  "BLK3 Flight 2 — a slot for the PR Space Foundation"),
 ("Nicole","LambdaVision — Nicole Wagner","nwagner@lambdavision.com","","biotech",
  "Your protein-based retinal work has strong ISS heritage. Flight 2 offers a fast, lower-cost microgravity run in early 2027 to keep your production research moving during the ISS transition.",
  "BLK3 Flight 2 — a microgravity run for LambdaVision"),
 ("Will","Varda Space — Will Bruey","will@varda.com","verify","derisk",
  "Your pharmaceutical crystallization program could use a fast suborbital screening flight to iterate between orbital runs. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a screening flight between orbital runs"),
 ("John","Redwire / SpaceMD — John Vellinger","jvellinger@redwirespace.com","verify","derisk",
  "Your drug-discovery and manufacturing payloads would benefit from a low-cost suborbital qualification step. Flight 2 in early 2027 can serve as that fast iteration flight.",
  "BLK3 Flight 2 — a qualification flight for SpaceMD"),
 ("Janet","Sierra Space — Dr. Janet Kavandi","jkavandi@sierraspace.com","verify","derisk",
  "Suborbital flight is a fast, low-cost way to qualify hardware before an orbital commitment. Flight 2 launches early 2027 and could de-risk a Sierra Space component set.",
  "BLK3 Flight 2 — qualifying hardware before orbit"),
 ("Lucie","Axiom Space — Dr. Lucie Low","lucie.low@axiomspace.com","verify","derisk",
  "As you build your research manifest, a suborbital screening flight can pre-qualify experiments before they reach your platform. Flight 2 in early 2027 is available for that role.",
  "BLK3 Flight 2 — pre-qualifying your research manifest"),
 ("Samuel","Keros Therapeutics — Dr. Samuel Cadena",None,"verify","biotech",
  "Your bone and muscle therapeutic work maps directly to microgravity physiology studies. Flight 2 offers a rapid, sample-return screening run in early 2027.",
  "BLK3 Flight 2 — a microgravity study for Keros"),
 ("Jason","Firefly Aerospace — Jason Kim","jkim@fireflyspace.com","verify","derisk",
  "A suborbital flight test can retire risk on subsystems before an orbital or lunar mission. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a flight-test option for Firefly"),
 ("Team","Merck — Space/microgravity research lead",None,"verify","biotech",
  "Your Keytruda crystallization work has flown on ISS. Flight 2 offers a faster, lower-cost microgravity screening run in early 2027 to keep that program iterating during the ISS transition.",
  "BLK3 Flight 2 — a screening flight for your crystallization work"),
 ("Team","Eli Lilly — Space/microgravity research lead",None,"verify","biotech",
  "Your Redwire drug-discovery collaboration shows the value of microgravity for your pipeline. Flight 2 provides a rapid suborbital screening option in early 2027.",
  "BLK3 Flight 2 — a microgravity screening option"),
 ("Team","Bristol Myers Squibb — Space/microgravity research lead",None,"verify","biotech",
  "Microgravity protein crystallization can sharpen structural work across your pipeline. Flight 2 offers a fast, sample-return screening run in early 2027.",
  "BLK3 Flight 2 — microgravity screening for your pipeline"),
 ("Team","Amgen — Space/microgravity research lead",None,"verify","biotech",
  "Your bone and muscle research is a natural fit for microgravity physiology studies. Flight 2 provides a rapid suborbital run with samples returned within days.",
  "BLK3 Flight 2 — a physiology run for Amgen"),
 ("Team","Flawless Photonics — Business development",None,"verify","derisk",
  "Your ZBLAN fiber work benefits from repeated microgravity draws. Flight 2 in early 2027 offers a low-cost suborbital pull between larger campaigns.",
  "BLK3 Flight 2 — a ZBLAN draw for Flawless"),
 ("Robbie","Planet Labs — Robbie Schingler",None,"verify","derisk",
  "A suborbital flight test can qualify new sensor or bus components before you fly them operationally. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — qualifying components before flight"),
 ("Gina","Spire Global — Gina Ruebensaal",None,"verify","derisk",
  "Suborbital flight is a fast way to de-risk payload electronics before an orbital deployment. Flight 2 in early 2027 could serve a Spire test article.",
  "BLK3 Flight 2 — de-risking payload electronics"),
 ("Christian","Capella Space — Christian Lenz",None,"verify","derisk",
  "A suborbital flight can validate RF and structural hardware in real launch and flight environments before orbit. Flight 2 is manifesting for early 2027.",
  "BLK3 Flight 2 — validating hardware before orbit"),
 ("Daniel","Observable Space — Daniel Roelker","droelker@observablespace.com","verify","derisk",
  "A low-cost suborbital flight is a strong way to prove your hardware before an orbital commitment. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — proving your hardware in flight"),
 ("David","CU Aerospace — David Carroll",None,"verify","derisk",
  "Your propulsion and payload work would benefit from a real flight environment before orbital use. Flight 2 in early 2027 offers that qualification step.",
  "BLK3 Flight 2 — a flight environment for your hardware"),
 ("Wesley","MIT Lincoln Laboratory — Wesley Esser",None,"verify","derisk",
  "A suborbital flight test can qualify sensor and materials articles in a real launch environment. Flight 2 is manifesting for early 2027.",
  "BLK3 Flight 2 — a flight-test slot"),
 ("Greg","GHGSat — Greg Frey",None,"verify","derisk",
  "Suborbital flight can validate optical and sensor payloads before orbital deployment. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — validating your sensor payload"),
 ("Emiliano","Satellogic — Emiliano Kargieman",None,"verify","derisk",
  "A fast suborbital qualification flight can retire risk on imaging or bus hardware before orbit. Flight 2 is manifesting for early 2027.",
  "BLK3 Flight 2 — a qualification flight for Satellogic"),
 ("Team","Space Pharma — Business development",None,"intl","biotech",
  "Your microgravity lab-in-a-box is ideal for a suborbital screening run. Flight 2 in early 2027 offers a fast, sample-return option.",
  "BLK3 Flight 2 — a screening run for Space Pharma"),
 ("Team","Exobiosphere — Business development",None,"intl","biotech",
  "Your microgravity drug-discovery platform is a strong fit for suborbital screening. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a microgravity screening flight"),
 ("Team","Space Cargo Unlimited — Business development",None,"intl","biotech",
  "Your applied microgravity research would benefit from a fast, lower-cost suborbital run between larger missions. Flight 2 is manifesting for early 2027.",
  "BLK3 Flight 2 — a suborbital run for your research"),
 ("Team","Boryung — Space healthcare / Axiom JV team",None,"intl","biotech",
  "Your Axiom investment shows a clear microgravity healthcare strategy. Flight 2 offers a fast suborbital screening option to complement your orbital plans in early 2027.",
  "BLK3 Flight 2 — a screening option for your program"),
 ("Ellen","ASGSR — Ellen Gertsen",None,"verify","channel",
  "Your members are exactly the PIs who need affordable microgravity access. Flight 2 in early 2027 could host a set of ASGSR payloads and student experiments.",
  "BLK3 Flight 2 — access for your members"),
 ("Kei","Narravity — Kei Shimada",None,"verify","derisk",
  "I would like to understand your payload interests and see whether Flight 2 in early 2027 is a fit. We have capacity open now.",
  "BLK3 Flight 2 — exploring fit for Narravity"),
 ("Giuseppe","Tyvak International — Giuseppe Santangelo",None,"intl","derisk",
  "A suborbital flight test can qualify smallsat components before orbit. Flight 2 is manifesting for early 2027. (International payload, subject to export screening.)",
  "BLK3 Flight 2 — qualifying smallsat components"),
 ("Andrew","NanoAvionics — Andrew Swain",None,"intl","derisk",
  "Suborbital flight is a fast way to prove bus and payload hardware before orbital deployment. Flight 2 launches early 2027. (International payload, subject to export screening.)",
  "BLK3 Flight 2 — proving hardware before orbit"),
 ("Raycho","EnduroSat — Raycho Raychev",None,"intl","derisk",
  "A low-cost suborbital flight can validate module hardware before an orbital run. Flight 2 is manifesting for early 2027. (International payload, subject to export screening.)",
  "BLK3 Flight 2 — validating your modules"),
 ("Janine","Dragonfly Aerospace — Janine Nicolson",None,"intl","derisk",
  "Suborbital flight can qualify imaging payloads in a real launch environment before orbit. Flight 2 launches early 2027. (International payload, subject to export screening.)",
  "BLK3 Flight 2 — a flight test for your imagers"),
 ("Hendrik","CubeSpace — Hendrik Burger",None,"intl","derisk",
  "A suborbital flight can validate ADCS hardware in flight before orbital use. Flight 2 is manifesting for early 2027. (International payload, subject to export screening.)",
  "BLK3 Flight 2 — validating your ADCS hardware"),
 ("Team","World View — Research payload team",None,"verify","displace",
  "Your balloon research customers who need true microgravity plus recovery are an ideal fit for a suborbital rocket flight. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — microgravity plus recovery for your customers"),
 ("Team","Aerostar / Tillamook — Balloon research team",None,"verify","displace",
  "Your NASA, NOAA, DoD, and university balloon customers are a natural ladder to a suborbital rocket flight. Flight 2 in early 2027 can carry the ones who need higher altitude and microgravity.",
  "BLK3 Flight 2 — the next rung for your balloon customers"),
 ("Team","Aurelia Institute — Flight campaign team",None,"verify","displace",
  "You aggregate education and research payloads for zero-g campaigns. Flight 2 in early 2027 could host a manifest of your community's experiments on a real rocket flight.",
  "BLK3 Flight 2 — a manifest for your campaign"),
 ("Allison","ZERO-G Corporation — Allison Odyssey","allison@gozero-g.com","verify","displace",
  "With parabolic flights grounded, your customers need another path to microgravity. Flight 2 in early 2027 can rehome those funded experiments.",
  "BLK3 Flight 2 — a home for your grounded payloads"),
 ("Team","Mayo Clinic — prior suborbital payload PI",None,"verify","biotech",
  "You have flown a payload with us before, and I would like to bring you back for Flight 2. It launches early 2027 with samples returned within days of landing.",
  "BLK3 Flight 2 — flying with you again"),
 ("Roberta","Politecnico di Torino — Roberta Fusaro",None,"intl","univ",
  "Your student team's experiment would fly well on BLK3, and Flight 2 is manifesting for early 2027. (International payload, subject to export screening.)",
  "BLK3 Flight 2 — a slot for your student team"),
 ("Team","HOSPO / Hokkaido Spaceport — Payload & wet-lease team",None,"intl","displace",
  "Beyond the wet-lease discussion, Flight 2 in early 2027 has open capacity for Japanese payloads that want near-term microgravity access. (International, subject to export screening.)",
  "BLK3 Flight 2 — payload capacity for your users"),
 ("Team","DLR — Suborbital payload integration team",None,"intl","displace",
  "Your groups that integrate ISS and suborbital payloads would find Flight 2 a useful near-term option in early 2027. (International, subject to export screening.)",
  "BLK3 Flight 2 — a near-term suborbital option"),
 ("Team","Italian Air Force / PoliTo network — prior suborbital flyers",None,"intl","displace",
  "Your prior suborbital flyers now need a flying platform. Flight 2 in early 2027 has open capacity. (International, subject to export screening.)",
  "BLK3 Flight 2 — a platform for your flyers"),
 # ---- government (route through Jon) ----
 ("David","NASA Flight Opportunities — David L. Pierce","david.l.pierce@nasa.gov","gov","gov",
  "As Exos advances toward contracted-provider status, we would value discussing how BLK3 Flight 2 (early 2027) can host TechFlights and other funded suborbital payloads.",
  "BLK3 Flight 2 — capacity for Flight Opportunities payloads"),
 ("Team","AFRL / AEDC — Hypersonic materials test POC",None,"gov","gov",
  "BLK3 offers a reusable, recoverable suborbital platform for hypersonic materials and component testing. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a test platform for AFRL/AEDC"),
 ("Team","Los Alamos National Laboratory — Suborbital payload POC",None,"gov","gov",
  "As a former UP Aerospace customer, LANL now needs a reliable commercial suborbital option. BLK3 Flight 2 in early 2027 can serve that role.",
  "BLK3 Flight 2 — a suborbital option for LANL"),
 ("Team","Sandia National Laboratories — Sounding-rocket payload POC",None,"gov","gov",
  "Given Sandia's sounding-rocket heritage, a reusable commercial suborbital platform offers a cost-effective complement. Flight 2 launches early 2027 with capacity open now.",
  "BLK3 Flight 2 — a commercial suborbital complement"),
]

# ---- schedule: 2 per business day starting 2026-07-22 ----------------------
def business_days(start, n):
    days, d = [], start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += datetime.timedelta(days=1)
    return days

n_days = (len(T) + 1) // 2
sched = business_days(datetime.date(2026, 7, 22), n_days)

rows = []
tid = 1307
for i, (first, disp, addr, gate, seg, hook, subj) in enumerate(T):
    day = sched[i // 2]
    slot = "AM" if i % 2 == 0 else "PM"
    seqn = i + 1

    # address / gate handling per standing rules
    if gate == "gov":
        to_line = (addr + " (GOV — ROUTE THROUGH JON, do not send directly)") if addr else "[POC — ROUTE THROUGH JON]"
        flag = "GOV — coordinate with Jon before any send."
    elif addr and gate == "":
        to_line = addr + " (confirmed)"
        flag = ""
    elif addr and gate == "verify":
        to_line = addr + " (VERIFY before send)"
        flag = "Verify the address before sending."
    elif gate == "intl":
        to_line = (addr + " (VERIFY)") if addr else "[find/verify contact]"
        flag = "INTERNATIONAL — run ITAR/EAR export screen BEFORE any send."
    else:  # verify, no address
        to_line = "[find/verify contact address]"
        flag = "Find and verify the contact address before sending."

    body = email(first, hook, seg, subj)
    desc = (f"CUSTOM OUTREACH EMAIL — send #{seqn} of {len(T)} | scheduled {day.isoformat()} {slot}\n"
            f"Target: {disp}\nTo: {to_line}\n"
            + (f"NOTE: {flag}\n" if flag else "")
            + "Pricing: do NOT quote $/kg until Jon approves external payload pricing. Offer the Payload User Guide and a tentative slot.\n"
            f"Cadence: 2 sends/business day. If you can do more, tell Jon/Exo and we raise the cap.\n\n"
            "----- READY-TO-SEND DRAFT (from lquinn@exosaero.com) -----\n" + body)

    rows.append({
        "title": f"[Send {seqn:02d}] BLK3 F2 outreach: {disp.split(' — ')[0]}",
        "owner": "Lizi Quinn",
        "assigned_to": "Lizi Quinn",
        "assigned_email": "lquinn@exosaero.com",
        "assigned_at": "2026-07-21T21:00:00+00:00",
        "state": "To Do" if i < 2 else "Queued",
        "priority": 95 - i,          # descending = booking-priority order
        "due_date": day.isoformat() + "T00:00:00+00:00",
        "category": "Payload Sales",
        "source": "Napier Park bridge — BLK3 Flight 2 payload campaign",
        "tags": ["blk3", "payload", "napier-park", "flight2", "outreach", f"seq-{seqn:02d}"],
        "description": desc,
    })
    tid += 1

created = req("POST", "tasks", rows, prefer="return=representation")
print(f"created {len(created)} individual outreach tasks: #{created[0]['id']}-#{created[-1]['id']}")
print(f"schedule: 2/business day, {sched[0].isoformat()} -> {sched[-1].isoformat()}")

# ---- supersede the 6 tiered cards, keep master #1300 -----------------------
for old in range(1301, 1307):
    cur = req("GET", f"tasks?id=eq.{old}&select=description")[0]["description"]
    req("PATCH", f"tasks?id=eq.{old}",
        {"state": "Done",
         "description": f"[SUPERSEDED 2026-07-21 — exploded into individual per-target custom-email tasks #1307-#{created[-1]['id']}, 2 sends/business day, booking-priority order.]\n\n" + cur})
print("superseded #1301-#1306 (kept master #1300)")

# ---- update master #1300 with the new model --------------------------------
m = req("GET", "tasks?id=eq.1300&select=description")[0]["description"]
req("PATCH", "tasks?id=eq.1300",
    {"description": m + ("\n\n--- UPDATE 2026-07-21 ---\nOutreach is now one CUSTOM EMAIL PER TARGET "
     f"(#1307-#{created[-1]['id']}), assigned to Lizi, sequenced by booking probability, 2 sends/business day "
     "starting 2026-07-22. Cap rises if Lizi confirms she can do more. Rideshare model: ~25 customers "
     "averaging ~5.4 kg fill the 135 kg bay over 6 months; deposits repay the $750K Napier Park bridge.")})
print("updated master #1300")
