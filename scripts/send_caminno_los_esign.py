#!/usr/bin/env python3
"""send_caminno_los_esign.py — MC e-sign envelope for the CAMINNO (UHV3D) NASA SBIR Ignite Ph II letter of support
(Jon email-cmd 2026-10-07, MC task #3574). Jon is the only signer; signature on the line above his printed name."""
import base64, glob, json, os, subprocess, sys, tempfile, urllib.request, http.cookiejar
WS = "/Users/exomac/.openclaw/workspace"; sys.path.insert(0, WS + "/scripts"); import esign_stamp
PDF = WS + "/drafts/caminno/Exos_LoS_CAMINNO_NASA_SBIR_Ignite_PhII_SIGNATURE_2026-10-07.pdf"
BASE = "http://127.0.0.1:8080"
slots = [s for s in esign_stamp.find_slots(PDF) if s["kind"] == "sig"][:1]
assert slots and slots[0]["page"] == 1, slots
slots[0]["label"] = "John Quinn"
with tempfile.TemporaryDirectory() as t:
    subprocess.run(["/opt/homebrew/bin/pdftoppm", "-r", "110", "-jpeg", "-jpegopt", "quality=82", PDF, t + "/p"], check=True)
    imgs = sorted(glob.glob(t + "/p-*.jpg"))
    pages = "".join(f'<div class="pdf-page" style="margin:0 auto 16px;max-width:720px;"><img src="data:image/jpeg;base64,{base64.b64encode(open(f,"rb").read()).decode()}" alt="Page {i}" style="width:100%;height:auto;display:block;border:1px solid #ddd;border-radius:4px;"></div>' for i, f in enumerate(imgs, 1))
html = f'<div class="pdf-rendered" data-pdf="1" data-pages="{len(imgs)}">{pages}{esign_stamp.slots_html(slots)}</div>'
env = {"title": "Letter of Support — CAMINNO (UHV3D) NASA SBIR Ignite Phase II", "html": html,
       "subject": "Signature requested: CAMINNO NASA SBIR Ignite Phase II letter of support",
       "message": "Exos letter of support / conditional commercial commitment for CAMINNO's NASA SBIR Ignite Phase II (MC task #3574). 1 seat @ $75K/yr, first order Q1 2028, $25K services; non-binding. Sign on the line above your name.",
       "signers": [{"name": "John Quinn", "email": "jquinn@exosaero.com", "role": "Exos — Cofounder & CEO"}]}
if "--send" not in sys.argv:
    print("dry run", len(imgs), "pages", slots); sys.exit()
sec = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.open(urllib.request.Request(BASE + "/api/docusign/login", data=json.dumps({"passcode": sec["mc_docusign_passcode"]}).encode(), headers={"Content-Type": "application/json"}), timeout=30)
r = op.open(urllib.request.Request(BASE + "/api/esign/create", data=json.dumps(env).encode(), headers={"Content-Type": "application/json"}), timeout=60)
out = json.loads(r.read()); print(json.dumps({"id": out.get("id"), "success": out.get("success")}))
open(WS + "/logs/caminno-los-envelope.id", "w").write(out["id"])
