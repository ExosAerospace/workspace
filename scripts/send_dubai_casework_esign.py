#!/usr/bin/env python3
"""send_dubai_casework_esign.py — ExoSign envelope for the Dubai-fraud casework + referral pack (Jon @Exobot 2026-10-11:
"draft the congressional requests with the privacy release forms making sure they are exosigned").
Jon is the only signer. Cruz's official form is excluded (that office requires ink)."""
import base64, glob, json, os, subprocess, sys, tempfile, urllib.request, http.cookiejar
import pypdf
WS = "/Users/exomac/.openclaw/workspace"; sys.path.insert(0, WS + "/scripts"); import esign_stamp
D = WS + "/drafts/dubai_casework_2026-10-11/"
ORDER = ["Exos_Casework_Request_Sen_Cruz_2026-10-12.pdf", "Exos_Casework_Request_Rep_Self_2026-10-12.pdf",
         "Exos_Privacy_Release_Rep_Self_2026-10-12.pdf", "Exos_Casework_FollowUp_Sen_Cornyn_2026-10-12.pdf",
         "Exos_Privacy_Release_Sen_Cornyn_2026-10-12.pdf", "Exos_Referral_USSS_Dallas_2026-10-12.pdf",
         "Exos_Referral_HSI_Dallas_2026-10-12.pdf"]
PDF = D + "Exos_Dubai_Casework_Referrals_ExoSign_Pack_2026-10-12.pdf"
w = pypdf.PdfWriter()
for f in ORDER: w.append(D + f)
w.write(PDF)
slots = esign_stamp.find_slots(PDF)
assert sum(s["kind"] == "sig" for s in slots) == 7, slots
BASE = "http://127.0.0.1:8080"
with tempfile.TemporaryDirectory() as t:
    subprocess.run(["/opt/homebrew/bin/pdftoppm", "-r", "110", "-jpeg", "-jpegopt", "quality=82", PDF, t + "/p"], check=True)
    imgs = sorted(glob.glob(t + "/p-*.jpg"))
    pages = "".join(f'<div class="pdf-page" style="margin:0 auto 16px;max-width:720px;"><img src="data:image/jpeg;base64,{base64.b64encode(open(f,"rb").read()).decode()}" alt="Page {i}" style="width:100%;height:auto;display:block;border:1px solid #ddd;border-radius:4px;"></div>' for i, f in enumerate(imgs, 1))
html = f'<div class="pdf-rendered" data-pdf="1" data-pages="{len(imgs)}">{pages}{esign_stamp.slots_html(slots)}</div>'
env = {"title": "Dubai fraud: congressional casework requests, privacy releases, USSS + HSI referrals", "html": html,
       "subject": "Signature requested: Dubai fraud casework + referral pack (7 signatures)",
       "message": "Letters to Sen. Cruz, Rep. Keith Self and Sen. Cornyn, the Self and Cornyn privacy releases, and the Secret Service "
                  "and HSI Dallas referrals (MC task #53). Sign each line. The executed PDF comes back to you by email for sending. "
                  "Sen. Cruz's own privacy form needs an ink signature and is not in this envelope.",
       "signers": [{"name": "John Quinn", "email": "jquinn@exosaero.com", "role": "Exos — Cofounder & CEO"}]}
if "--send" not in sys.argv:
    print("dry run", len(imgs), "pages", [(s["page"], s["kind"]) for s in slots]); sys.exit()
sec = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.open(urllib.request.Request(BASE + "/api/docusign/login", data=json.dumps({"passcode": sec["mc_docusign_passcode"]}).encode(), headers={"Content-Type": "application/json"}), timeout=30)
r = op.open(urllib.request.Request(BASE + "/api/esign/create", data=json.dumps(env).encode(), headers={"Content-Type": "application/json"}), timeout=60)
out = json.loads(r.read()); print(json.dumps({"id": out.get("id"), "success": out.get("success")}))
open(WS + "/logs/dubai-casework-envelope.id", "w").write(out["id"])
