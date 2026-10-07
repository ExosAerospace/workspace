#!/usr/bin/env python3
"""naftu_attestation_ready_watch.py — one-shot watcher (Jon email-cmd 2026-10-07).
When MC e-sign envelope (logs/naftu-attestation-envelope.id) completes, email Jon a READY-TO-SEND for Dennis Small
(NASA GSFC) with the executed attestation PDF + filled worksheet attached, file the executed PDF on MC task #2970,
then self-retire (marker + launchctl bootout). Gov recipient → Jon sends it himself; nothing goes to NASA from here."""
import json, os, smtplib, subprocess, sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
WS = "/Users/exomac/.openclaw/workspace"; MC = WS + "/mission-control"
LABEL = "com.exos.naftu-attestation-ready"; DONE = WS + "/logs/naftu-attestation-ready.done"
WORKSHEET = WS + "/drafts/naftu/Exos_NAFTU_Software_Requestor_Worksheet_v2.1_FILLED_2026-10-05.docx"
JON = "jquinn@exosaero.com"

def retire(why):
    print(why); open(DONE, "a").write(why + "\n")
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    sys.exit(0)

if os.path.exists(DONE): retire("already done")
eid = open(WS + "/logs/naftu-attestation-envelope.id").read().strip()
env = next((e for e in json.load(open(MC + "/data/envelopes.json")) if e["id"] == eid), None)
if not env: retire("envelope missing " + eid)
if env.get("status") != "completed":
    from datetime import datetime, timezone
    if datetime.now(timezone.utc).isoformat() > env.get("expiresAt", "9"): retire("envelope expired unsigned " + eid)
    print("waiting", eid); sys.exit(0)
pdf = os.path.join(MC, env.get("executedPdf") or "")
if not env.get("executedPdf") or not os.path.exists(pdf):
    print("completed but executed PDF not yet written"); sys.exit(0)
signed = os.path.join(WS, "drafts/naftu/Exos_NAFTU_NASA_Cybersecurity_Attestation_SIGNED_" + env["completedAt"][:10] + ".pdf")
subprocess.run(["cp", pdf, signed], check=True)
body = f"""READY TO SEND — your NASA NAFTU forms are signed (e-sign envelope {eid}, completed {env['completedAt'][:16]}Z).
Both files are attached. Forward this, or copy the draft below into a new email from jquinn@exosaero.com, attach both files, and send.

────────────────────────────────
To: Dennis Small <dennis.a.small@nasa.gov>
Subject: Exos Aerospace — NAFTU Software Requestor Worksheet and Signed Cybersecurity Attestation

Dennis,

Attached are the completed Software Requestor Information Worksheet and the signed Cybersecurity Attestation Form for NAFTU. Neil Milburn is our software custodian. Please let me know if you need anything else to prepare the license agreement.

Thank you,
John

John Quinn
Cofounder and CEO
Exos Aerospace Systems & Technologies, Inc.
Mob. +1-972-740-8355
────────────────────────────────

Attachments:
 1. {os.path.basename(WORKSHEET)}
 2. {os.path.basename(signed)}

Both are filed on Mission Control task #2970.
— Exo (automated)"""
m = MIMEMultipart(); m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = JON
m["Subject"] = "READY TO SEND: NAFTU forms to Dennis Small (NASA GSFC) — attestation signed"
m.attach(MIMEText(body, "plain"))
for f in (WORKSHEET, signed):
    a = MIMEApplication(open(f, "rb").read(), Name=os.path.basename(f)); a["Content-Disposition"] = f'attachment; filename="{os.path.basename(f)}"'; m.attach(a)
p = subprocess.run(["msmtp", "-a", "protonmail", JON], input=m.as_bytes(), capture_output=True, timeout=90)
if p.returncode != 0: print("send failed", p.stderr.decode()[-300:]); sys.exit(1)
subprocess.run(["/usr/bin/python3", WS + "/scripts/mc-attach.py", "--task", "2970", "--file", signed, "--by", "Exo", "--title", "NASA NAFTU Cybersecurity Attestation — SIGNED"], capture_output=True)
retire("ready-to-send emailed to Jon; executed PDF filed on #2970 " + signed)
