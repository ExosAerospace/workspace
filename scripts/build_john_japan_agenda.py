#!/usr/bin/env python3
"""John Quinn Japan trip (Oct 10-18, 2026): hour-by-hour agenda, US Central + JST, with quick-reference meeting briefs.
Source data consolidated 10/6 from MC #2684, Toshi itinerary rev01, United/JAL confirmations, JETRO confirmation, 10/6 weekly meeting."""
import docx
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
OUT="/Users/exomac/.openclaw/workspace/drafts/japan_trip/John_Japan_Trip_Agenda_Oct10-18_2026.docx"
ORANGE=RGBColor(0xF2,0x6A,0x21); GREY=RGBColor(0x55,0x55,0x55)
d=docx.Document()
for s in d.sections: s.left_margin=s.right_margin=Inches(0.8); s.top_margin=s.bottom_margin=Inches(0.7)
st=d.styles["Normal"]; st.font.name="Calibri"; st.font.size=Pt(10.5)
def H(t,l=1):
    h=d.add_heading(t,level=l)
    for r in h.runs: r.font.color.rgb=RGBColor(0,0,0)
    return h
def P(t="",b=False,i=False,c=None,sz=None):
    p=d.add_paragraph(); r=p.add_run(t); r.bold=b; r.italic=i
    if c: r.font.color.rgb=c
    if sz: r.font.size=Pt(sz)
    p.paragraph_format.space_after=Pt(2); return p
def B(t,lvl=0):
    p=d.add_paragraph(style="List Bullet" if lvl==0 else "List Bullet 2"); p.add_run(t); p.paragraph_format.space_after=Pt(1); return p
def EV(cdt,jst,title,where=None,who=None,notes=None,tbd=False):
    p=d.add_paragraph(); p.paragraph_format.space_before=Pt(5); p.paragraph_format.space_after=Pt(1)
    r=p.add_run(f"{cdt}  "); r.bold=True; r.font.color.rgb=ORANGE
    r=p.add_run(f"({jst} JST)  "); r.font.color.rgb=GREY; r.font.size=Pt(9.5)
    r=p.add_run(title); r.bold=True
    if tbd: r=p.add_run("  [TO CONFIRM]"); r.bold=True; r.font.color.rgb=RGBColor(0xC0,0,0)
    for lab,val in (("Where",where),("With",who),("Notes",notes)):
        if val:
            q=d.add_paragraph(); q.paragraph_format.left_indent=Inches(0.3); q.paragraph_format.space_after=Pt(0)
            rr=q.add_run(lab+": "); rr.bold=True; rr.font.size=Pt(9.5); rr2=q.add_run(val); rr2.font.size=Pt(9.5)

t=d.add_paragraph(); r=t.add_run("John Quinn — Japan Trip Agenda"); r.bold=True; r.font.size=Pt(20)
P("Saturday Oct 10 – Sunday Oct 18, 2026  ·  Tokyo · Obihiro / Taiki (Hokkaido) · onward to New York",b=True)
P("All times shown US CENTRAL (CDT) first, Japan time (JST) in grey. Japan is 14 hours AHEAD of Central: a 9:00 AM meeting in Tokyo is 7:00 PM the previous evening in Texas.",c=GREY)
P("Internal working document, prepared by Exo for Lizi, 10/6/2026. Items marked [TO CONFIRM] are not locked. Confirm with Toshi before the calendar entry is final.",i=True,c=GREY,sz=9)

H("Key contacts on the ground",2)
for x in ["Toshi Kumazawa (Exos Japan BD, escort): Japan mobile +81 90 9958 1863 / +81 50 3698 1962 · US mobile +1 430 242 0885 · satellite phone +44 7457 400236 · toshihisa@exosaero.com",
          "Rob Stynes (SPACE COTAN / Hokkaido Spaceport, Business Development Dept. Leader): stynes-robert1@spacecotan.com · +81 80-775-2311 (CRM also lists 080-9795-2311; confirm)",
          "Keith O. Sanders (JETRO, Asst. Director of Business Development, booked the VC meeting room): Keith_Sanders@jetro.go.jp · +1 713-654-5258",
          "Joshua Flannery (Innovation Dojo, Founder & CEO): joshua@innovationdojo.com.au · +81 80-3790-1978 · Kanako Murase (PM): kanako.murase@innovationdojo.com.au",
          "Kei Izawa (Japan government/industry navigation, ex-Opel Japan GM): k.izawa@gmail.com",
          "Bookings: United J7BF0L (outbound) · JAL FIXYT2 (Hokkaido legs, ticket 1312264387311, paid) · United J7KEK0 (return to New York)"]: B(x)

H("Before departure",1)
EV("Wed 10/7, 10:00 PM","Thu 10/8, 12:00 PM","Innovation Dojo (IDJ) investor pitch: 3-minute pitch + 2-minute Q&A",
   where="IDJ follow-up event, Tokyo. John + Toshi present.",who="Room of investors + corporate representatives (Innovation Dojo / Black Belt Venture Studio)",
   notes="Answers to Toshi's 3 questions (use of funds, EAI structure, 3-5 yr model) are drafted in drafts/IDJ_Toshi_Answers_2026-10-07.docx. They need John's review, and all securities language needs Counsel before it is shown to investors.")

H("Saturday, October 10 — Travel to Tokyo",1)
EV("5:30 AM","—","Leave for DFW Airport (suggested: ~90 min before a domestic connection to an international flight)",tbd=True)
EV("7:00 AM – 10:53 AM","—","Flight UA 790, Dallas/Fort Worth (DFW) → San Francisco (SFO)",notes="United First, seat 1E. Conf J7BF0L. Lands 8:53 AM Pacific. 1 h 42 m connection.")
EV("12:35 PM","Sun 10/11, 2:35 AM","Flight UA 875, San Francisco (SFO) → Tokyo Haneda (HND)",notes="United Polaris business, seat 3A. Departs 10:35 AM Pacific. Conf J7BF0L. Crosses the date line: lands Sunday afternoon Tokyo time.")

H("Sunday, October 11 — Arrive Tokyo",1)
EV("Sat 10/10, 11:55 PM","1:55 PM","Arrive Tokyo Haneda (HND), immigration + customs")
EV("Sun 12:45 AM (approx.)","2:45 PM (approx.)","Transfer Haneda → Hilton Tokyo by Airport Limousine Bus",notes="After customs, buy a ticket at the Limousine Bus counter in the arrivals hall for the bus to Hilton Tokyo (Shinjuku). Per Toshi.")
EV("Sun 1:00 AM","3:00 PM (check-in from)","Check in: Hilton Tokyo",where="6-6-2 Nishi-Shinjuku, Shinjuku-ku, Tokyo 160-0023 · hotel phone +81 3-3344-5111",notes="Confirmation 3533448509 (Hilton Honors #815117232). 2 nights, Oct 11-13. Twin Premium room, breakfast included. Rate ¥72,800/night; total ¥181,381 incl. tax + service. Free cancellation until 11:59 PM Oct 10; after that the first night + tax is charged.")

H("Monday, October 12 — Japanese national holiday (Sports Day)",1)
EV("Sun 10/11, 7:00 PM →","Mon 9:00 AM →","No formal meetings: rest / prep day",notes="Suggested prep: (1) Honda consulting scope + TAA reply; (2) investor deck / one-pager for the Fri JETRO meeting; (3) HOSPO agenda.")

H("Tuesday, October 13 — Honda, then fly to Hokkaido",1)
EV("Mon 10/12, 6:30 PM","8:30 AM","Check out of Hilton Tokyo (conf 3533448509; checkout deadline 11:00 AM) with luggage for Hokkaido")
EV("Mon 10/12, 7:00 PM","9:00 AM","Toshi picks John up at Hilton Tokyo lobby → travel to Honda",where="Hilton Tokyo, 6-6-2 Nishi-Shinjuku")
EV("Mon 10/12, 9:00 PM – 10:00 PM","11:00 AM – 12:00 PM","MEETING: Honda (Sato-san)",where="Honda R&D Co., Ltd., 1-4-1 Chuo, Wako City, Saitama Prefecture",who="Sato-san, Honda R&D. Exos: John + Toshi together (direct meeting at Honda's facility)",
   notes="See quick-reference brief: HONDA. Honda asked (call 10/5) for a consulting arrangement on reusable technologies + testing; John's answer is: send scope, we propose hours, TAA first.")
EV("Mon 10/12, 10:00 PM","12:00 PM","Leave Honda → Tokyo Haneda Airport (lunch en route)")
EV("Tue 10/13, 3:35 AM – 5:10 AM","5:35 PM – 7:10 PM","Flight JL 579, Tokyo Haneda (HND) → Obihiro (OBO), Hokkaido",notes="JAL Class J, seat 6C. Conf FIXYT2. Tokachi-Obihiro Airport is the gateway to Hokkaido Spaceport (Taiki).")
EV("Tue 10/13, ~5:30 AM","~7:30 PM","Taxi Obihiro Airport → hotel (arranged by SPACE COTAN), check in: Richmond Hotel Obihiro Ekimae",where="Nishi 2-jo Minami 11-chome 17, Obihiro, Hokkaido (in front of JR Obihiro Station)",notes="Booked by Toshi, pay at hotel. Nights of Oct 13 and Oct 14.")

H("Wednesday, October 14 — Hokkaido Spaceport (HOSPO), Taiki",1)
EV("Tue 10/13, 5:45 PM","7:45 AM","Meet Toshi at the Richmond Hotel front desk")
EV("Tue 10/13, 6:00 PM","8:00 AM","SPACE COTAN shuttle bus: hotel → HOSPO, Taiki Town",who="Rob Stynes (SPACE COTAN) picks up John + Toshi",notes="Shuttle provided by SPACE COTAN.")
EV("Tue 10/13, 7:00 PM","Wed 10/14, 9:00 AM","HOSPO facility tour",where="Hokkaido Spaceport, Taiki-cho, Hiroo-gun, Hokkaido",who="SPACE COTAN team (Rob Stynes, BD; CEO Yoshinori Odagiri, attendance TBD)",notes="See quick-reference brief: HOSPO / SPACE COTAN.")
EV("Wed 10/14, 4:00 AM","6:00 PM","Dinner reception hosted by HOSPO / SPACE COTAN",where="Obihiro City (restaurant TBD)",notes="Hosted dinner: a relationship moment. Bring a small gift (omiyage) for the hosts.")
EV("—","—","Overnight: Richmond Hotel Obihiro Ekimae")

H("Thursday, October 15 — HOSPO working meeting, return to Tokyo",1)
EV("Wed 10/14, 11:00 – 11:45 PM","Thu 10/15, 1:00 – 1:45 PM","MEETING: HOSPO team: International Trade Zone (ITZ) working session (45 min)",where="Hokkaido Hotel, Obihiro City: conference room inside the venue of a HOSPO-hosted event that day (street address to confirm). After the meeting, John + Toshi go straight to Obihiro Airport (Toshi: plenty of time).",who="SPACE COTAN / HOSPO team; possibly a Hokkaido/Tokachi investment-attraction officer via Kei Izawa (unconfirmed)",
   notes="Only 45 minutes, so lead with the asks: feasibility-study MOU + next steps. Agenda: ITZ / Container-as-Zone, vehicle wet-lease model, Spaceport America bridge service, payload demand, Scorpius Type-5 tanks, Exos Japan K.K., feasibility-study MOU. Commercial/concept level only.")
EV("Thu 10/15, ~11:50 PM Wed","~1:50 PM","Straight from the meeting to Obihiro Airport with Toshi (taxi arranged by SPACE COTAN)")
EV("Thu 10/15, 2:10 AM – 4:00 AM","4:10 PM – 6:00 PM","Flight JL 574, Obihiro (OBO) → Tokyo Haneda (HND)",notes="JAL Class J, seat 3C. Conf FIXYT2.")
EV("Thu 10/15, ~5:00 AM","~7:00 PM","Transfer Haneda → Hilton Tokyo, check in",where="6-6-2 Nishi-Shinjuku, Shinjuku-ku, Tokyo",notes="Nights of Oct 15, 16, 17. Second Hilton booking confirmed (Lizi has it on John's calendar); separate from conf 3533448509 (Oct 11-13).")

H("Friday, October 16 — AstroX + two investor meetings",1)
EV("Thu 10/15, 7:30 PM","9:30 AM","Toshi picks John up at Hilton Tokyo lobby → AstroX")
EV("Thu 10/15, 9:00 PM","11:00 AM","MEETING: AstroX",where="AstroX Ueno Office, 4-6-7 Higashi-Ueno, Taito Ward, Tokyo",who="AstroX team (Founder & CEO Shobu Oda, attendance TBD)",notes="See quick-reference brief: ASTROX.")
EV("Fri 10/16, 12:00 AM – 1:00 AM","2:00 PM – 3:00 PM","MEETING: Investor meeting, SBI Investment",where="SBI Investment, Izumi Garden Tower 19F, 1-6-1 Roppongi, Minato-ku, Tokyo",
   who="Ms. Yang and her team, SBI Investment (arranged by Toshi, confirmed 10/9)",
   notes="See quick-reference brief: SBI INVESTMENT. After: short taxi/walk to JETRO at Ark Mori Building (Akasaka 1-chome, next to Roppongi 1-chome) for the 4:00 PM meeting.")
EV("Fri 10/16, 2:00 AM – 3:00 AM","4:00 PM – 5:00 PM","MEETING: Investor meeting, 650 Fund (Dominik Steiner)",where="JETRO Tokyo, meeting room \"Botan\", Ark Mori Building, 1-12-32 Akasaka, Minato-ku, Tokyo. CHECK IN ON THE 7TH FLOOR.",
   who="Dominik Steiner, Founding Partner, 650 Fund. Room booked by Keith Sanders, JETRO (room held 3–5 PM).",
   notes="PRIMARY PURPOSE OF THE TRIP. See quick-reference brief: INVESTOR MEETING. JETRO IBSC page: https://www.jetro.go.jp/en/invest/jetros_support/ibsc/ibsc_tokyo.html")
EV("TBD","TBD (Oct 16–17)","Possible government intros via Kei Izawa: METI space office / Cabinet Office space policy secretariat / JETRO Invest Japan",tbd=True)

H("Saturday, October 17 — Open / backup",1)
EV("Fri 10/16, 7:00 PM →","Sat 9:00 AM →","Open day (no meetings booked; the second investor meeting is now Friday with SBI)",tbd=False)

H("Sunday, October 18 — Fly to New York",1)
EV("Sun 12:00 AM","2:00 PM","Check out Hilton Tokyo → Haneda (suggested: arrive ~2.5–3 h before international departure)",tbd=True)
EV("Sun 10/18, 3:15 AM","5:15 PM","Flight UA 882, Tokyo Haneda (HND) → Chicago O'Hare (ORD), lands 3:05 PM CDT same day",notes="United Polaris business, seat 6A. Conf J7KEK0. 1 h 55 m connection at O'Hare.")
EV("Sun 10/18, 5:00 PM – 7:25 PM","—","Flight UA 456, Chicago O'Hare (ORD) → New York LaGuardia (LGA), lands 8:25 PM Eastern",notes="United First, seat 2A. Conf J7KEK0.")
EV("Mon 10/19 – Wed 10/21","—","New York: Up/Link VIP reception Mon 10/19, 5:00–8:00 PM ET (4:00–7:00 PM CT), 30 Rockefeller Plaza + Up/Link Global Forum 10/20–21 (AWS Executive Briefing Center, 12 W 39th St)",notes="John is attending. 1:1 meeting requests sent to 13 targets; Lizi checks acceptances 10/11 and adds them to the calendar. NYC hotel full-refund deadline 10/12.")

H("Not yet on the schedule",2)
B("PD AeroSpace: NO MEETING this trip (Toshi 10/7: schedules could not be coordinated). Pursue the tank LOI remotely (MC #1538).")
B("Pantherion (the 'AI scheduler' / 'Prometheus' John mentioned 10/6): NO MEETING. They scheduled a meeting with John at Up/Link NY (post-Japan), then cancelled; they declined to meet (John, 10/7).")
B("Innovation Dojo: in-person meeting during the visit? Confirm with Toshi.")
B("Toyota: NO MEETING. No Toyota contact was received from Microcosm; the Marubeni contract has expired (John, 10/7, D-7281995).")

d.add_page_break()
H("Quick-reference meeting briefs (paste into each calendar event's notes)",1)
def BRIEF(title,lines):
    H(title,2)
    for l in lines: B(l)
BRIEF("HONDA (Sato-san) · Tue 10/13 11:00 JST / Mon 10/12 9:00 PM CDT",[
 "Who: Sato-san, Honda. Honda R&D (Honda's R&D subsidiary) is developing its own reusable rocket.",
 "Context: Honda R&D flew an experimental reusable rocket (6.3 m long, 85 cm diameter) to ~300 m and landed it on June 17, 2025, at Honda's test site in Taiki Town, Hokkaido, next to HOSPO. Source: https://global.honda/en/topics/2025/c_2025-06-17ceng.html",
 "Where it stands: on the 10/5 call Honda asked for a consulting arrangement on reusable technologies and testing (limited budget). John's position: send us the scope, we propose an hours estimate, and executing a TAA (export license agreement) is the first step.",
 "Goal for the meeting: agree on scope areas + next step (scope letter → hours proposal → TAA).",
 "Guardrail: no technical data or ITAR/EAR-controlled detail until a TAA is in place. Keep it to capabilities, heritage and business terms."])
BRIEF("HOSPO / SPACE COTAN · Wed 10/14 tour + dinner, Thu 10/15 ITZ meeting",[
 "Who: SPACE COTAN Co., Ltd. operates Hokkaido Spaceport (HOSPO) in Taiki Town: vertical + horizontal launch, launch pads, command center, runway, engine test stands. Sources: https://aerospacebiz.jaxa.jp/japanese-space-industry/detail/space-cotan-co-ltd , https://hokkaidospaceport.com/en",
 "People: Rob Stynes (Business Development Dept. Leader, our main contact); CEO Yoshinori Odagiri (per SPACE COTAN listing, https://tcru.jp/spacecotan); ono-takayuki@spacecotan.com also in CRM.",
 "Context: Firefly Aerospace signed a preliminary agreement with SPACE COTAN to study launching Alpha from HOSPO (Reuters). HOSPO is courting U.S. launch partners.",
 "Agenda (Thu): ITZ / Container-as-Zone, vehicle wet-lease model, Spaceport America bridge service, payload demand, Scorpius Type-5 tanks, Exos Japan K.K., feasibility-study MOU.",
 "Goal: a feasibility-study MOU and agreement on next steps for the trade-zone concept. Possible Hokkaido investment-attraction officer in the room (via Kei Izawa, unconfirmed).",
 "Guardrail: commercial/concept level only; no controlled technical data."])
BRIEF("ASTROX · Fri 10/16 11:00 JST / Thu 10/15 9:00 PM CDT",[
 "Who: AstroX, Inc., founded 2022, HQ Minamisoma, Fukushima. Founder & CEO Shobu Oda. Building small launch vehicles launched from stratospheric balloons ('rockoon'). Source: JAXA press release 5/28/2026, https://global.jaxa.jp/press/2026/05/20260528-1_e.html",
 "Context: AstroX + JAXA are jointly demonstrating a suspended attitude-control device for stratospheric balloons (same JAXA release). Funding ~US$17.7M across 4 rounds, Series A Feb 2026 (Tracxn, third-party data).",
 "Goal: explore collaboration (test/flight services, components, Japan ecosystem partner). Confirm their attendees before the meeting.",
 "Guardrail: commercial level; export review before any technical exchange."])
BRIEF("INVESTOR MEETING: SBI INVESTMENT · Fri 10/16 14:00–15:00 JST / 12:00–1:00 AM CDT",[
 "Who: SBI Investment Co., Ltd., the venture capital arm of the SBI Group. HQ: Izumi Garden Tower 19F, Roppongi (matches the meeting address; CB Insights investor profile). Meeting with Ms. Yang and her team, arranged by Toshi (10/9). Her title: confirm with Toshi.",
 "Same raise and structure as the 650 Fund meeting below: ¥790M (≈US$5.0M) Japan round, units in Exos Aerospace Investments, LLC under a separate offshore Regulation S offering.",
 "Bring: Japan investor pitch Rev2 / IDJ deck, investor one-pager, IDJ Q&A answers, all Counsel-reviewed first.",
 "Guardrail: all securities language (units, Reg S, returns, exit) must be Counsel-approved before it is shown to an investor."])
BRIEF("INVESTOR MEETING: 650 FUND @ JETRO · Fri 10/16 16:00–17:00 JST / 2:00–3:00 AM CDT",[
 "Who: Dominik Steiner, Founding Partner, 650 Fund (Palo Alto, Japan, Switzerland). 20+ year entrepreneur/investor; invests pre-seed to Series A across AI, robotics, AEROSPACE, mobility; helps foreign founders enter Japan. Sources: https://jp.linkedin.com/in/dosteiner , https://650.fund/fundii",
 "650 Fund II: $100M-target Japan-focused fund ($30M+ committed), pre-seed/seed with follow-ons, 3 pillars: AI Native, Deep Tech, Robotics; every deal needs a Japan thesis. Founding Partners Grace Stanat + Dominik Steiner (650.fund).",
 "Fit check: they are early-stage and our Japan round is about US$5M, so expect a smaller check or a co-investor/intro role. Lead with the Japan thesis: Exos Japan K.K., HOSPO trade zone, Japanese payload demand.",
 "Why it matters: investor meetings are the PRIMARY purpose of the trip (John, 9/7).",
 "The raise: ¥790M (≈US$5.0M). Japan investors buy units in Exos Aerospace Investments, LLC (EAI) in a separate offshore Regulation S offering. EAI units mirror Exos U.S. shares; Exos Aerospace Japan K.K. is wholly owned by Exos U.S. Exit is through an Exos U.S. listing or acquisition.",
 "Bring: Japan investor pitch Rev2 / IDJ deck, investor one-pager, IDJ Q&A answers (use of funds / structure / model), all Counsel-reviewed first.",
 "Guardrail: all securities language (units, Reg S, returns, exit) must be Counsel-approved before it is put in front of an investor. Projections are internal estimates."])
BRIEF("PD AEROSPACE (NO meeting this trip, follow up remotely)",[
 "Who: Shuji Ogawa, Founder, CEO & CTO, PD AeroSpace, LTD. Building a fully reusable suborbital spaceplane (horizontal takeoff/landing) powered by a mode-switching rotating detonation engine. Ogawa has served on the Cabinet Office Space Policy Committee's space transport subcommittee since 2013. Source: https://www.linkedin.com/in/shuji-ogawa-90b16b22",
 "Context: Exos has a draft Letter of Intent for a Type-V composite LOX + GHe tank pair for PD AeroSpace's spaceplane (MC #1538; terms from SMAD/Scorpius quote). Open: unit masses/prices, PDA contact, price-validity window.",
 "Goal (Neil, 10/6): come home with at least a signed LOI on the tanks.",
 "Guardrail: Japan sale → ITAR/EAR export contingency is written into the LOI."])
BRIEF("INNOVATION DOJO / JAPAN TECH (support network)",[
 "Joshua Flannery (Founder & CEO, Innovation Dojo) and Kanako Murase (PM) run the IDJ investor event on 10/8 and are the main route to Japanese investors.",
 "Itaru Ueda (Japan Tech, VC/CVC partner): warm bridge to Japanese corporate-venture investors."])
BRIEF("KEI IZAWA (government navigation)",[
 "Based in Boulder, CO. 10 years in Japanese government trade + 14 years as a GM executive (Rep. General Director, Opel Japan 1991–96). DD passed 10/1.",
 "Asks for this trip: 1–2 warm government intros 10/16–17 (METI space office, Cabinet Office National Space Policy Secretariat, JETRO Invest Japan) and a Hokkaido investment-attraction officer at the 10/15 HOSPO meeting. None confirmed yet.",
 "Not a capital intermediary: no retainer, no success fee."])
d.save(OUT); print(OUT)
