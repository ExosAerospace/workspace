#!/usr/bin/env python3
"""send_naftu_attestation_esign.py — MC e-sign envelope for the NASA NAFTU Cybersecurity Attestation (Jon email-cmd 2026-10-07).
Jon is the only signer. One signature slot only: the auto-detector also flags the Title line, which would put his
signature on "Title" — so the slot list is pinned to the "Signed:" line and labelled "John Quinn".
Completion follow-up (ready-to-send to Dennis Small) = scripts/naftu_attestation_ready_watch.py."""
import base64, glob, json, os, subprocess, sys, tempfile, urllib.request, http.cookiejar
WS = "/Users/exomac/.openclaw/workspace"; sys.path.insert(0, WS + "/scripts"); import esign_stamp
PDF = WS + "/drafts/naftu/Exos_NAFTU_NASA_Cybersecurity_Attestation_PREFILLED_unsigned_2026-10-05.pdf"
BASE = "http://127.0.0.1:8080"
slots = [s for s in esign_stamp.find_slots(PDF) if s["kind"] == "sig"][:1]
assert slots and slots[0]["page"] == 2 and "Title" in slots[0]["label"], slots
slots[0]["label"] = "John Quinn"
with tempfile.TemporaryDirectory() as t:
    subprocess.run(["/opt/homebrew/bin/pdftoppm", "-r", "110", "-jpeg", "-jpegopt", "quality=82", PDF, t + "/p"], check=True)
    imgs = sorted(glob.glob(t + "/p-*.jpg"))
    pages = "".join(f'<div class="pdf-page" style="margin:0 auto 16px;max-width:720px;"><img src="data:image/jpeg;base64,{base64.b64encode(open(f,"rb").read()).decode()}" alt="Page {i}" style="width:100%;height:auto;display:block;border:1px solid #ddd;border-radius:4px;"></div>' for i, f in enumerate(imgs, 1))
html = f'<div class="pdf-rendered" data-pdf="1" data-pages="{len(imgs)}">{pages}{esign_stamp.slots_html(slots)}</div>'
env = {"title": "NASA NAFTU Cybersecurity Attestation — Exos", "html": html,
       "subject": "Signature requested: NASA NAFTU Cybersecurity Attestation (for Dennis Small, GSFC)",
       "message": "NASA export-controlled software attestation for NAFTU (MC task #2970). Sign on the 'Signed:' line. Once signed, Exo emails you a ready-to-send to Dennis Small with both forms attached.",
       "signers": [{"name": "John Quinn", "email": "jquinn@exosaero.com", "role": "Exos — Cofounder & CEO"}]}
if "--send" not in sys.argv:
    print("dry run", len(imgs), "pages", slots); sys.exit()
sec = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.open(urllib.request.Request(BASE + "/api/docusign/login", data=json.dumps({"passcode": sec["mc_docusign_passcode"]}).encode(), headers={"Content-Type": "application/json"}), timeout=30)
r = op.open(urllib.request.Request(BASE + "/api/esign/create", data=json.dumps(env).encode(), headers={"Content-Type": "application/json"}), timeout=60)
out = json.loads(r.read()); print(json.dumps({"id": out.get("id"), "success": out.get("success")}))
open(WS + "/logs/naftu-attestation-envelope.id", "w").write(out["id"])
