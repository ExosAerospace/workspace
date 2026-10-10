// Exos UHNW investor deck — DIB production-layer story. Dark theme, orange accent.
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
p.author = "Exos Aerospace"; p.company = "Exos Aerospace Systems & Technologies, Inc.";

const BG="0B0B0D", CARD="17171B", CARD2="202026", ORANGE="F26A21", WHITE="FFFFFF", GREY="C2C2C8", MUTED="8A8A92";
const HEAD="Arial", BODY="Calibri";
const W=13.3, H=7.5;
const LOGO="drafts/_exos_white_official.png";
const HERITAGE="media/inbound/openclaw-staged-68ea7fa7-a2be-4b50-832c-c73503dd44d9/image---110065bb-4b5e-4d43-a5f0-68b2f89d9aa2.png";

function bg(s,c){ s.background={color:c||BG}; }
function eyebrow(s,t){ s.addText(t.toUpperCase(),{x:0.7,y:0.5,w:11.9,h:0.32,isTextBox:true,margin:0,fontFace:HEAD,fontSize:12,bold:true,color:ORANGE,charSpacing:2}); }
function title(s,t,opt){ opt=opt||{}; s.addText(t,{x:0.7,y:opt.y||0.85,w:opt.w||11.9,h:opt.h||1.0,isTextBox:true,margin:0,fontFace:HEAD,fontSize:opt.fs||34,bold:true,color:WHITE,lineSpacing:opt.ls||38}); }
function foot(s,n){ s.addText([{text:"EXOS AEROSPACE",options:{bold:true,color:GREY}},{text:"   ·   Confidential — Proprietary/Unclassified   ·   Not an offer of securities",options:{color:MUTED}}],{x:0.7,y:7.05,w:10.6,h:0.3,isTextBox:true,margin:0,fontFace:BODY,fontSize:8.5}); s.addText(String(n),{x:12.4,y:7.05,w:0.5,h:0.3,isTextBox:true,margin:0,fontFace:BODY,fontSize:8.5,color:MUTED,align:"right"}); }
function card(s,x,y,w,h){ s.addShape(p.ShapeType.roundRect,{x,y,w,h,rectRadius:0.08,fill:{color:CARD},line:{color:CARD2,width:1},shadow:{type:"outer",color:"000000",opacity:0.45,blur:8,offset:3,angle:90}}); }
function stat(s,x,y,w,big,label){ card(s,x,y,w,1.85); s.addText(big,{x:x+0.15,y:y+0.22,w:w-0.3,h:0.85,isTextBox:true,margin:0,fontFace:HEAD,fontSize:34,bold:true,color:ORANGE,align:"center",valign:"middle"}); s.addText(label,{x:x+0.15,y:y+1.05,w:w-0.3,h:0.7,isTextBox:true,margin:0,fontFace:BODY,fontSize:12,color:GREY,align:"center",valign:"top",lineSpacing:14}); }
function bullets(s,x,y,w,items,fs){ s.addText(items.map((t,i)=>({text:t,options:{bullet:{code:"2022",indent:14},color:GREY,breakLine:true,paraSpaceAfter:9}})),{x,y,w,h:Math.max(1.0,6.85-y),isTextBox:true,margin:0,fontFace:BODY,fontSize:fs||14,color:GREY,lineSpacing:(fs||14)+5,valign:"top"}); }

// 1 — TITLE
let s=p.addSlide(); bg(s);
s.addImage({path:LOGO,x:0.7,y:0.65,w:3.3,h:3.3*926/2683});
s.addText("The Moon-Proven Standard for the Space Economy",{x:0.7,y:2.55,w:11.9,h:1.9,isTextBox:true,margin:0,fontFace:HEAD,fontSize:44,bold:true,color:WHITE,lineSpacing:48});
s.addText([{text:"The independent, TRL-9, moon-proven composite tank — ",options:{color:GREY}},{text:"the standard the space economy will be built on.",options:{color:ORANGE,bold:true}}],{x:0.7,y:4.55,w:11.6,h:0.8,isTextBox:true,margin:0,fontFace:BODY,fontSize:18,lineSpacing:24});
s.addText("Confidential Investor Presentation   ·   September 2026   ·   Proprietary — Unclassified   ·   Not an offer of securities",{x:0.7,y:6.7,w:11.9,h:0.4,isTextBox:true,margin:0,fontFace:BODY,fontSize:10.5,color:MUTED});

// 2 — WHITE SPACE
s=p.addSlide(); bg(s); eyebrow(s,"The opportunity");
title(s,"The space economy runs on tanks — and almost no one can build them.",{fs:30,ls:36,h:1.7,w:12.0});
s.addText("Every launch vehicle, lunar lander, orbital-transfer vehicle, and commercial station needs flight-grade cryogenic tanks and pressure structures. The industry delivers them in ~2 years, single-sourced. Exos builds moon-proven, TRL-9 tanks in ~90 days — and owns the capacity under the rest of the defense industrial base too: SRM cases, pressure structures, detonation engines.",{x:0.7,y:2.75,w:7.4,h:2.4,isTextBox:true,margin:0,fontFace:BODY,fontSize:15.5,color:GREY,lineSpacing:23,valign:"top"});
s.addText([{text:"We own the production layer.\n",options:{color:WHITE,bold:true,fontSize:20,breakLine:true}},{text:"One moon-proven tank, then the capacity beneath everything the space economy and the DIB can't make fast enough — cheaper, lighter, on U.S. soil.",options:{color:GREY,fontSize:15}}],{x:0.7,y:5.2,w:11.9,h:1.4,isTextBox:true,margin:0,fontFace:BODY,lineSpacing:24,valign:"top"});
card(s,8.5,2.7,4.1,2.0); s.addText("$1T",{x:8.5,y:2.95,w:4.1,h:0.9,isTextBox:true,margin:0,fontFace:HEAD,fontSize:52,bold:true,color:ORANGE,align:"center"}); s.addText("cryogenic-tank TAM by 2030 (from ~$640B) — plus the $20T physical economy beneath it",{x:8.7,y:3.9,w:3.7,h:0.85,isTextBox:true,margin:0,fontFace:BODY,fontSize:12.5,color:GREY,align:"center",lineSpacing:15});
foot(s,2);

// 3 — THE PROBLEM
s=p.addSlide(); bg(s); eyebrow(s,"The problem");
title(s,"America can't produce what it needs — fast enough, cheaply enough, or at home");
const probs=[["Solid-rocket-motor cases","Single-source, ~2-year lead times, aging capacity — the munitions build-rate the Navy/DIB needs is out of reach today."],["Cryogenic tanks & pressure structures","The moon economy and hypersonics demand flight-grade tanks in weeks, not years."],["Detonation engines (RDRE)","Next-gen propulsion the DoD wants flown — with no scaled domestic producer."]];
let py=2.6; probs.forEach((pr,i)=>{ s.addShape(p.ShapeType.ellipse,{x:0.75,y:py,w:0.5,h:0.5,fill:{color:ORANGE}}); s.addText(String(i+1),{x:0.75,y:py,w:0.5,h:0.5,isTextBox:true,margin:0,fontFace:HEAD,fontSize:18,bold:true,color:WHITE,align:"center",valign:"middle"}); s.addText(pr[0],{x:1.45,y:py-0.05,w:7.1,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:17,bold:true,color:WHITE}); s.addText(pr[1],{x:1.45,y:py+0.35,w:7.1,h:0.85,isTextBox:true,margin:0,fontFace:BODY,fontSize:13.5,color:GREY,lineSpacing:17,valign:"top"}); py+=1.45; });
card(s,9.0,2.6,3.6,4.05); s.addText("1,000",{x:9.0,y:3.1,w:3.6,h:0.9,isTextBox:true,margin:0,fontFace:HEAD,fontSize:50,bold:true,color:ORANGE,align:"center"}); s.addText("units / year",{x:9.0,y:4.0,w:3.6,h:0.4,isTextBox:true,margin:0,fontFace:BODY,fontSize:15,color:WHITE,align:"center",bold:true}); s.addText("the surge production the Navy / DIB has signaled it needs — versus the fragmented capacity that exists today.",{x:9.25,y:4.5,w:3.1,h:1.6,isTextBox:true,margin:0,fontFace:BODY,fontSize:13,color:GREY,align:"center",lineSpacing:17,valign:"top"});
foot(s,3);

// 4 — HERITAGE IMAGE
s=p.addSlide(); bg(s); eyebrow(s,"20+ years of doing what others only promise");
s.addText("A team that has flown, recovered, and re-flown — for two decades",{x:0.7,y:0.82,w:11.9,h:0.6,isTextBox:true,margin:0,fontFace:HEAD,fontSize:24,bold:true,color:WHITE});
const ha=1891/1071; let hw=10.9, hh=hw/ha; if(hh>5.0){hh=5.0;hw=hh*ha;} s.addImage({path:HERITAGE,x:(W-hw)/2,y:1.55,w:hw,h:hh});
s.addText("From Armadillo Aerospace (John Carmack) → Lunar Lander Challenge → SARGE reusable flights → USAF/DoD contracts → moon-flown tanks → RDRE → a clear path to public markets and exit.",{x:0.7,y:6.55,w:11.9,h:0.45,isTextBox:true,margin:0,fontFace:BODY,fontSize:11.5,color:MUTED,align:"center",italic:true});
foot(s,4);

// 5 — PROOF NOT PROMISE
s=p.addSlide(); bg(s); eyebrow(s,"Why Exos"); title(s,"Proof, not promise");
stat(s,0.75,2.5,2.85,"4 / 3","SARGE launches / recoveries (2018–19) — reflight demonstrated");
stat(s,3.78,2.5,2.85,"<20 · $5.7M","the team & spend that did it — peers spent hundreds of millions");
stat(s,6.81,2.5,2.85,"TRL-9","cryo tanks flown on Intuitive Machines' lunar landers");
stat(s,9.84,2.5,2.85,"$2.6B","prime on the AEDC Velocity Alliance test consortium");
s.addText([{text:"Half the cost. A fraction of the parts. ",options:{color:WHITE,bold:true}},{text:"BLK3 flies with <5,000 components vs. ~80,000 for peers; Scorpius gross margin lifted to ~55%; first moon-lander tank set delivered in 90 days vs. an industry two years.",options:{color:GREY}}],{x:0.75,y:4.75,w:11.9,h:1.6,isTextBox:true,margin:0,fontFace:BODY,fontSize:16,lineSpacing:23,valign:"top"});
foot(s,5);

// 6 — THE MOAT
s=p.addSlide(); bg(s); eyebrow(s,"The moat"); title(s,"Moon-proven IP, run by an AI-native operating system");
card(s,0.75,2.45,5.75,4.1); s.addText("Moon-proven, TRL-9 IP",{x:1.0,y:2.65,w:5.25,h:0.45,isTextBox:true,margin:0,fontFace:HEAD,fontSize:18,bold:true,color:ORANGE});
bullets(s,1.0,3.2,5.3,["Scorpius Type-5 linerless cryo tanks flew as fuel + LOX tanks on Intuitive Machines' Odysseus & Athena landers","Baseline tank set for IM's Nebula orbital-transfer vehicle — IM lander backlog ~$4.1B","We are aware of no competitor at this readiness and flight heritage","Exos owns 18% of Scorpius with a right of first refusal at a 2021 valuation basis"],13);
card(s,6.8,2.45,5.75,4.1); s.addText("The AI operating moat — Mission Control",{x:7.05,y:2.65,w:5.25,h:0.45,isTextBox:true,margin:0,fontFace:HEAD,fontSize:18,bold:true,color:ORANGE});
bullets(s,7.05,3.2,5.3,["Of record, the 4th of Exos's four core assets — the AI-deployed operating platform","~125 governed automated agents across BD, finance, compliance; ~7,000 CRM contacts","Runs a public-grade cadence of programs and lights-out production without a public-company G&A stack","Governed autonomy with a full audit trail — operating leverage, not a black box"],13);
foot(s,6);

// 7 — THE ENGINE
s=p.addSlide(); bg(s); eyebrow(s,"The engine"); title(s,"We don't build one product. We own the capacity under all of them.");
const steps=[["1","Deploy robots","into partners' idle, single-shift facilities"],["2","Run lights-out","on ~$30M of equipment they already own"],["3","Become the producer","then their acquirer — Exos secures the IP"],["4","Aggregate","toward ~75% of U.S. winding capacity"]];
let sx=0.75; steps.forEach(st=>{ card(s,sx,2.55,2.86,2.4); s.addShape(p.ShapeType.ellipse,{x:sx+1.13,y:2.8,w:0.6,h:0.6,fill:{color:ORANGE}}); s.addText(st[0],{x:sx+1.13,y:2.8,w:0.6,h:0.6,isTextBox:true,margin:0,fontFace:HEAD,fontSize:22,bold:true,color:WHITE,align:"center",valign:"middle"}); s.addText(st[1],{x:sx+0.15,y:3.55,w:2.56,h:0.5,isTextBox:true,margin:0,fontFace:HEAD,fontSize:15,bold:true,color:WHITE,align:"center"}); s.addText(st[2],{x:sx+0.2,y:4.05,w:2.46,h:0.8,isTextBox:true,margin:0,fontFace:BODY,fontSize:12,color:GREY,align:"center",lineSpacing:15,valign:"top"}); sx+=3.0; });
s.addText([{text:"A capability-gap ledger — acquire / build / license / partner. ",options:{color:WHITE,bold:true}},{text:"Manifest culled 137 companies → 7 finalists filling 9 mapped gaps, aggregating to the ~1,000-unit volume the DIB needs. Own the machines before the AI-materials breakthrough hits (casing 50→13 lb; materials $10→$0.10) and you own the base.",options:{color:GREY}}],{x:0.75,y:5.25,w:11.9,h:1.5,isTextBox:true,margin:0,fontFace:BODY,fontSize:14,lineSpacing:20,valign:"top"});
foot(s,7);

// 8 — MARKET
s=p.addSlide(); bg(s); eyebrow(s,"The market"); title(s,"A generational tailwind — and we sit under all of it");
stat(s,0.75,2.6,2.85,"$1.7T","proposed U.S. defense budget — re-industrialization is national priority");
stat(s,3.78,2.6,2.85,"$1T","cryogenic-tank TAM by 2030 (from ~$640B)");
stat(s,6.81,2.6,2.85,"~$100B","asymmetric / missile production white space");
stat(s,9.84,2.6,2.85,"$4.1B","Intuitive Machines lunar-lander backlog we supply into");
s.addText("Defense-tech capital is at record highs and family offices are writing $25M+ checks into dual-use hard-tech. The scarce trade isn't another software play — it's the physical infrastructure almost no one can build.",{x:0.75,y:4.85,w:11.9,h:1.4,isTextBox:true,margin:0,fontFace:BODY,fontSize:15,color:GREY,lineSpacing:22,valign:"top"});
foot(s,8);

// 9 — UNIT ECONOMICS
s=p.addSlide(); bg(s); eyebrow(s,"Business model"); title(s,"Profitable at the unit — and a roll-up that compounds it");
card(s,0.75,2.5,5.75,3.0); s.addText("Unit economics that carry the story",{x:1.0,y:2.7,w:5.3,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:16,bold:true,color:ORANGE});
bullets(s,1.0,3.2,5.3,["~½ the cost, lighter, fewer parts (integrated pressurized structures)","~$12.5K/kg vs. Rocket Lab ~$25K/kg","Scorpius gross margin lifted to ~55%; +35% across acquired contracts","Flight-test-as-a-service: orbital developers prove avionics/GNC/materials before risking a >$50M vehicle — recurring, high-margin","RDRE built ~$20K vs. a ~$300K market price"],11.5);
card(s,6.8,2.5,5.75,3.0); s.addText("The revenue bridge — stated honestly",{x:7.05,y:2.7,w:5.3,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:16,bold:true,color:ORANGE});
bullets(s,7.05,3.2,5.3,["Organic: ~$50M raise → ~$170M/yr; realistic 5-yr ceiling ~$300–350M","The consortium roll-up acquires revenue + capacity to reach ~$500M / $40–50M EBITDA","Pipeline grew $500K → $150M identified in 9 months — capital converts it","Margin-expansion play: we lift acquired companies' margins, not take them"],12.5);
s.addText("The roll-up is what turns a slow, DoD-paced organic ramp into an M&A-accelerated one — the only way the public-market math truly works.",{x:0.75,y:5.75,w:11.9,h:0.9,isTextBox:true,margin:0,fontFace:BODY,fontSize:14,italic:true,color:WHITE,lineSpacing:19,valign:"top"});
foot(s,9);

// 10 — PATH TO PUBLIC
s=p.addSlide(); bg(s); eyebrow(s,"The path"); title(s,"A public-market path already in motion — with control retained");
bullets(s,0.75,2.5,7.3,["Go public via reverse takeover into a clean, U.S. exchange-listed shell — with a verifiable track record and clean EDGAR provenance required before any mandate","Staged raise: ~$15M cash at close → +$25–50M on milestone news → $70–80M target","Founders retain voting control in writing; charter foreign-ownership cap ≤10% with a funded corrective buyback — no SSA/FOCI, CFIUS-clean, ITAR intact","Near-term, non-dilutive-leaning capital via an Office of Strategic Capital note (5–6%) + Title III"],14);
card(s,8.35,2.5,4.25,4.0); s.addText("A legal news flywheel",{x:8.6,y:2.7,w:3.75,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:15,bold:true,color:ORANGE});
bullets(s,8.6,3.2,3.75,["Locked capacity →","Enabled orders →","Marquee customers →","The Mar/Apr 2027 BLK3 flight ('half of NASA will be watching')"],12.5);
s.addText("Real, counsel-approved milestones on a monthly cadence — substance under the tape, not promotion.",{x:8.6,y:5.55,w:3.75,h:0.85,isTextBox:true,margin:0,fontFace:BODY,fontSize:11.5,italic:true,color:GREY,lineSpacing:15,valign:"top"});
foot(s,10);

// 11 — THE ASK
s=p.addSlide(); bg(s); eyebrow(s,"The ask"); title(s,"Capitalize the roll-up");
stat(s,0.75,2.5,3.9,"~$75M","pipe → RTO onto NASDAQ (~$15M pre-merger pipe + ~$60M on-market)");
stat(s,4.83,2.5,3.9,"$1M now","prefunds BLK3 flight 2 — flight 1 is fully customer-funded");
stat(s,8.91,2.5,3.7,"2021 basis","the Scorpius ROFR arbitrage you buy into");
s.addText("Use of proceeds",{x:0.75,y:4.7,w:11.9,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:16,bold:true,color:ORANGE});
bullets(s,0.75,5.15,11.9,["Acquire the balance of Scorpius (ROFR) + CTD + composite / advanced-tank targets","Deploy robots to lock idle national winding capacity; stand up surge production","Build the BD muscle to convert the $150M pipeline into booked revenue"],14);
foot(s,11);

// 12 — RETURN / EXIT
s=p.addSlide(); bg(s); eyebrow(s,"The return"); title(s,"Asymmetric upside, with a defined exit");
card(s,0.75,2.5,5.75,3.9); s.addText("Why the upside is asymmetric",{x:1.0,y:2.7,w:5.3,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:16,bold:true,color:ORANGE});
bullets(s,1.0,3.2,5.3,["TRL-9 lunar-heritage IP no competitor can match","Scorpius ROFR arbitrage — 2021 basis vs. current fair market value","The AI operating moat — public-grade output at private-company cost","A live public window on the space/defense wave"],13);
card(s,6.8,2.5,5.75,3.9); s.addText("The exit — 2029–30",{x:7.05,y:2.7,w:5.3,h:0.4,isTextBox:true,margin:0,fontFace:HEAD,fontSize:16,bold:true,color:ORANGE});
bullets(s,7.05,3.2,5.3,["Uplist → DoD-contract flywheel → positioned for merger / acquisition","Live comps: Quantum Space (~$1.2B de-SPAC), Rocket Lab, Firefly, Hadrian ($1.37B round)","Defense-tech M&A consolidating fast — a scaled domestic producer is the prize","Multiple exit paths: strategic acquisition, secondary, or continued public compounding"],13);
foot(s,12);

// 13 — TEAM
s=p.addSlide(); bg(s); eyebrow(s,"The team"); title(s,"Operators who have actually flown — and re-flown");
const team=[["John Quinn","Cofounder & CEO — capital, BD, strategy; drives the roll-up and the public path"],["Neil Milburn","Co-Founder & COO — 50-yr aerospace operator; launch ops & manufacturing"],["Phil Eaton","Technical principal — direct John Carmack / Armadillo rocket lineage"],["Scorpius (board control)","Exos took a board seat + financial control; lifted margins to ~55%"]];
let tx=0.75; team.forEach(t=>{ card(s,tx,2.6,2.86,3.4); s.addShape(p.ShapeType.ellipse,{x:tx+1.03,y:2.85,w:0.8,h:0.8,fill:{color:ORANGE}}); s.addText(t[0].split(" ").map(w=>w[0]).slice(0,2).join(""),{x:tx+1.03,y:2.85,w:0.8,h:0.8,isTextBox:true,margin:0,fontFace:HEAD,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle"}); s.addText(t[0],{x:tx+0.12,y:3.8,w:2.62,h:0.55,isTextBox:true,margin:0,fontFace:HEAD,fontSize:14.5,bold:true,color:WHITE,align:"center",lineSpacing:16}); s.addText(t[1],{x:tx+0.18,y:4.4,w:2.5,h:1.5,isTextBox:true,margin:0,fontFace:BODY,fontSize:11.5,color:GREY,align:"center",lineSpacing:15,valign:"top"}); tx+=3.0; });
foot(s,13);

// 14 — CLOSE
s=p.addSlide(); bg(s);
s.addImage({path:LOGO,x:0.7,y:0.7,w:2.7,h:2.7*926/2683});
s.addText("The moon-proven tank — and the production layer beneath the space economy.",{x:0.7,y:2.7,w:11.9,h:1.5,isTextBox:true,margin:0,fontFace:HEAD,fontSize:34,bold:true,color:WHITE,lineSpacing:40});
s.addText([{text:"TRL-9, moon-flown IP. An AI operating moat. A public path in motion. ",options:{color:GREY}},{text:"The scarce physical-AI trade — and a defined exit.",options:{color:ORANGE,bold:true}}],{x:0.7,y:4.25,w:11.6,h:0.9,isTextBox:true,margin:0,fontFace:BODY,fontSize:18,lineSpacing:24});
s.addText([{text:"John Quinn",options:{bold:true,color:WHITE}},{text:"   Cofounder & CEO   ·   jquinn@exosaero.com   ·   +1-972-740-8355",options:{color:GREY}}],{x:0.7,y:5.4,w:11.9,h:0.5,isTextBox:true,margin:0,fontFace:BODY,fontSize:15});
s.addText("Confidential — not an offer of securities. Any offering is made only through definitive documents, subject to due diligence and applicable securities, export-control, and CFIUS law.",{x:0.7,y:6.7,w:11.9,h:0.5,isTextBox:true,margin:0,fontFace:BODY,fontSize:9,color:MUTED});

p.writeFile({fileName:"drafts/Exos_Investor_Deck_2026-09-19.pptx"}).then(f=>console.log("wrote",f));
