#!/usr/bin/env python3
"""ExoSign MNDA to 650 Fund (Dominik Steiner, General Partner) for Japan-round data-room access. Jon 2026-10-16 20:20.
Standard Exos MNDA (send_mnda_docusign.mnda_html) with the party block and signature block filled in, and §7 adapted for a
non-U.S. counterparty (business/financial information only; no export-controlled technical data). Private fund: no MNPI clause."""
import sys, json, re, datetime, urllib.request, http.cookiejar, importlib.util
WS="/Users/exomac/.openclaw/workspace"
spec=importlib.util.spec_from_file_location("m",f"{WS}/scripts/send_mnda_docusign.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CP="650 Fund"; ADDR="Tokyo, Japan"
PURPOSE=("a potential investment by 650 Fund in the Japan round of Exos Aerospace (units of Exos Aerospace Investments, LLC), "
         "including review of Exos's investor data room")
eff=datetime.date.today().strftime("%B %d, %Y")
html=m.mnda_html(CP,ADDR,"650",PURPOSE,eff)
s7=("<p><b>7. Export Control.</b> Each Party shall comply with U.S. export laws, including ITAR (22 CFR 120-130) and EAR (15 CFR 730-774). "
    "650 is treated as a non-U.S. person for purposes of this Agreement. Information disclosed under this Agreement is limited to business and financial information; "
    "Exos will not disclose export-controlled technical data under this Agreement, and nothing in it authorizes any export.</p>")
html,n=re.subn(r"<p><b>7\. Export Control\.</b>.*?</p>",s7,html,flags=re.S); assert n==1
html=html.replace("<b>650 FUND</b><br>By: ______  Name: ____________  Title: ____________","<b>650 FUND</b><br>By: ______  Name: Dominik Steiner  Title: General Partner")
assert "Dominik Steiner" in html
env={"title":"Mutual NDA — Exos & 650 Fund","html":html,
     "subject":"Signature requested: Mutual NDA (Exos Aerospace & 650 Fund)",
     "message":("Dominik, thank you for meeting with us at JETRO today. Here is our mutual NDA for your review and signature. "
                "Once it's signed, Exos will countersign and I'll send you data-room access. Best regards, John Quinn"),
     "signers":[{"name":"Dominik Steiner","email":"dominik@650.fund","role":"Counterparty"},
                {"name":"John Quinn","email":"jquinn@exosaero.com","role":"Exos"}]}
if "--send" not in sys.argv:
    print(re.sub("<[^>]+>"," ",html)[:3500]); sys.exit()
pc=m.SEC["mc_docusign_passcode"]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request(m.BASE+"/api/docusign/login",data=json.dumps({"passcode":pc}).encode(),headers={"Content-Type":"application/json"}),timeout=30)
r=op.open(urllib.request.Request(m.BASE+"/api/esign/create",data=json.dumps(env).encode(),headers={"Content-Type":"application/json"}),timeout=60)
print("RESULT:",r.read().decode()[:600])
