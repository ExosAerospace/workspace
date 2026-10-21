#!/usr/bin/env python3
"""ExoSign MNDA to Space Grove Ventures, LLC (Dr. Melissa Patton, Founder & CEO). Jon 2026-10-21 00:22.
Purpose: Exos education/workforce work (Science Fair Payload Award) + a Mission Control trial hosted on Exos servers.
Standard Exos MNDA (send_mnda_docusign.mnda_html); U.S. private LLC: standard §7, no MNPI clause."""
import sys, json, re, datetime, urllib.request, http.cookiejar, importlib.util
WS="/Users/exomac/.openclaw/workspace"
spec=importlib.util.spec_from_file_location("m",f"{WS}/scripts/send_mnda_docusign.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CP="Space Grove Ventures, LLC"; ADDR="Space Coast, Florida"
PURPOSE=("(a) a potential collaboration on education and workforce programs, including a science fair payload award program "
         "flown on Exos suborbital flights, and (b) a trial of Exos's Mission Control operations platform, hosted on Exos servers, "
         "for use by Space Grove")
eff=datetime.date.today().strftime("%B %d, %Y")
html=m.mnda_html(CP,ADDR,"Space Grove",PURPOSE,eff)
html,_n=re.subn(r"with offices at\s*Space Coast, Florida","with offices on the Space Coast, Florida",html); assert _n==1
old="<b>SPACE GROVE VENTURES, LLC</b><br>By: ______  Name: ____________  Title: ____________"
assert old in html, "signature block placeholder not found"
html=html.replace(old,"<b>SPACE GROVE VENTURES, LLC</b><br>By: ______  Name: Dr. Melissa Patton  Title: Founder & CEO")
env={"title":"Mutual NDA — Exos & Space Grove Ventures","html":html,
     "subject":"Signature requested: Mutual NDA (Exos Aerospace & Space Grove Ventures)",
     "message":("Melissa, here is our mutual NDA covering the education program work and a Mission Control trial hosted on Exos servers. "
                "Once you sign, Exos will countersign and you'll receive the fully executed copy. Looking forward to working together. "
                "Best regards, John Quinn"),
     "signers":[{"name":"Dr. Melissa Patton","email":"melissa@thespacegrove.org","role":"Counterparty"},
                {"name":"John Quinn","email":"jquinn@exosaero.com","role":"Exos"}]}
if "--send" not in sys.argv:
    print(re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",html))); sys.exit()
pc=m.SEC["mc_docusign_passcode"]
cj=http.cookiejar.CookieJar(); op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
op.open(urllib.request.Request(m.BASE+"/api/docusign/login",data=json.dumps({"passcode":pc}).encode(),headers={"Content-Type":"application/json"}),timeout=30)
r=op.open(urllib.request.Request(m.BASE+"/api/esign/create",data=json.dumps(env).encode(),headers={"Content-Type":"application/json"}),timeout=60)
print("RESULT:",r.read().decode()[:600])
