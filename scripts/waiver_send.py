#!/usr/bin/env python3
"""Send the customer's FAA cross-waiver of claims (14 CFR 440.17, Subpart A) together with the LSA.

The LSA is e-signed in ExoSign; the waiver must be WET-signed and the original mailed to Exos by L-90.
Lizi 2026-10-14: send both at the same time. Template = BLK3 / Spaceport America / Part 450
(templates/BLK3_CrossWaiver_Subpart_A_TEMPLATE.docx). Called by mission-control/lib/payload-orders.js
right after the send-lsa envelope is created (a human clicked Send).

Usage: waiver_send.py --order ID --customer "Org" --payload "desc" --email x@y --name "Signer" [--dry-run]
Prints JSON {pdf, sent}.
"""
import argparse, datetime, json, os, re, subprocess, sys, tempfile
from email.message import EmailMessage
from docx import Document

WS = "/Users/exomac/.openclaw/workspace"
TPL = os.path.join(WS, "templates", "BLK3_CrossWaiver_Subpart_A_TEMPLATE.docx")
OUT = os.path.join(WS, "mission-control", "uploads", "waivers")


def fill(customer, payload, signer):
    today = datetime.date.today()
    day = today.day
    suf = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    vals = {"{{DAY}}": f"{day}{suf}", "{{MONTH}}": today.strftime("%B"), "{{YEAR}}": str(today.year),
            "{{CUSTOMER}}": customer, "{{PAYLOAD}}": payload, "{{SIGNER}}": signer or "______________________________"}
    d = Document(TPL)
    for p in d.paragraphs:
        if "{{" in p.text:
            t = p.text
            for k, v in vals.items():
                t = t.replace(k, v)
            for r in p.runs[1:]:
                r._element.getparent().remove(r._element)
            p.runs[0].text = t
    os.makedirs(OUT, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", customer).strip("_")[:40]
    docx = os.path.join(OUT, f"CrossWaiver_{slug}_{today:%Y-%m-%d}.docx")
    d.save(docx)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", OUT, docx],
                   capture_output=True, timeout=120)
    pdf = docx[:-5] + ".pdf"
    if not os.path.exists(pdf):
        raise SystemExit("PDF conversion failed")
    return pdf


def main():
    ap = argparse.ArgumentParser()
    for a in ("--order", "--customer", "--payload", "--email", "--name"):
        ap.add_argument(a, default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    pdf = fill(a.customer, a.payload or "the Customer's payload", a.name)
    first = (a.name or "").split()[0] if a.name else ""
    body = (f"Hello{(' ' + first) if first else ''},\n\n"
            "Along with the Launch Services Agreement you'll receive by e-signature, attached is the FAA cross-waiver "
            "of claims for your payload. The FAA requires this one to be signed in ink, so please:\n\n"
            "1. Print the attached waiver.\n"
            "2. Sign and date it on the Customer signature lines.\n"
            "3. Mail the original to: Exos Aerospace Systems & Technologies, Inc., 299 FM 1903, Greenville, TX 75402.\n\n"
            "We need the signed original at Exos no later than 90 days before launch so we can submit it to the FAA "
            "with our payload approval, but sending it back with your signed agreement is easiest. "
            "Feel free to reply to this email with any questions.\n\n"
            "Best Regards,\nLizi Quinn\nExos Aerospace")
    m = EmailMessage()
    m["From"] = '"Exos Aerospace" <jquinnexo@pm.me>'
    m["To"] = a.email
    m["Cc"] = "lquinn@exosaero.com"
    m["Reply-To"] = "lquinn@exosaero.com"
    m["X-Exo-No-Task"] = "1"
    m["Subject"] = f"FAA cross-waiver of claims to print and sign: {a.customer}"
    m.set_content(body)
    m.add_attachment(open(pdf, "rb").read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf))
    sent = False
    if not a.dry_run and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", a.email or ""):
        p = subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", a.email, "lquinn@exosaero.com"],
                           input=m.as_bytes(), capture_output=True, timeout=60)
        sent = p.returncode == 0
    print(json.dumps({"pdf": os.path.relpath(pdf, os.path.join(WS, "mission-control")), "sent": sent}))


if __name__ == "__main__":
    main()
