#!/usr/bin/env python3
"""send_eca_affiliation_esign.py — ExoSign envelope for the WidePoint ECA Proof of Organizational Affiliation (Lizi), MC task #2161.
Jon is the only signer (Jon @Exobot 2026-10-08: "send to me in exosign for signature and send")."""
import base64, glob, json, os, subprocess, sys, tempfile, urllib.request, http.cookiejar
WS = "/Users/exomac/.openclaw/workspace"; sys.path.insert(0, WS + "/scripts"); import esign_stamp
PDF = WS + "/drafts/ECA_ProofOfOrgAffiliation_ElizabethQuinn_ExoSign_2026-10-08.pdf"
BASE = "http://127.0.0.1:8080"
slots = [s for s in esign_stamp.find_slots(PDF) if s["kind"] == "sig"][:1]
assert slots and slots[0]["page"] == 2, slots
slots[0]["label"] = "John M. Quinn"
with tempfile.TemporaryDirectory() as t:
    subprocess.run(["/opt/homebrew/bin/pdftoppm", "-r", "110", "-jpeg", "-jpegopt", "quality=82", PDF, t + "/p"], check=True)
    imgs = sorted(glob.glob(t + "/p-*.jpg"))
    pages = "".join(f'<div class="pdf-page" style="margin:0 auto 16px;max-width:720px;"><img src="data:image/jpeg;base64,{base64.b64encode(open(f,"rb").read()).decode()}" alt="Page {i}" style="width:100%;height:auto;display:block;border:1px solid #ddd;border-radius:4px;"></div>' for i, f in enumerate(imgs, 1))
html = f'<div class="pdf-rendered" data-pdf="1" data-pages="{len(imgs)}">{pages}{esign_stamp.slots_html(slots)}</div>'
env = {"title": "ECA Proof of Organizational Affiliation — Elizabeth Quinn", "html": html,
       "subject": "Signature requested: ECA Proof of Organizational Affiliation (Lizi — WidePoint DoD PKI)",
       "message": "WidePoint ECA affiliation letter for Lizi's DoD PKI certificate request (MC task #2161). Sign on the line above your name. The executed PDF comes back to you by email so it can go to WidePoint with Lizi's request.",
       "signers": [{"name": "John M. Quinn", "email": "jquinn@exosaero.com", "role": "Exos — Cofounder & CEO"}]}
if "--send" not in sys.argv:
    print("dry run", len(imgs), "pages", slots); sys.exit()
sec = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.open(urllib.request.Request(BASE + "/api/docusign/login", data=json.dumps({"passcode": sec["mc_docusign_passcode"]}).encode(), headers={"Content-Type": "application/json"}), timeout=30)
r = op.open(urllib.request.Request(BASE + "/api/esign/create", data=json.dumps(env).encode(), headers={"Content-Type": "application/json"}), timeout=60)
out = json.loads(r.read()); print(json.dumps({"id": out.get("id"), "success": out.get("success")}))
open(WS + "/logs/eca-affiliation-envelope.id", "w").write(out["id"])
