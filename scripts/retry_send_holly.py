#!/usr/bin/env python3
"""One-shot resilient sender for the Holly Gilbert (NCAR/CMEx) draft to John's inbox.
Retries through the Proton Bridge outage (mail-api 500/503). Exits 0 on success,
1 if it gives up after the window. Safe to re-run."""
import smtplib, time, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

host, port = "127.0.0.1", 1025
user = "jquinnexo@pm.me"
password = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
from_addr = to_addr = "jquinn@exosaero.com"

proposed_subject = "135 kg SPACEavailable...(TM) on BLK3's next flight — chromospheric / heliophysics science-objective payloads"
email_body = """Hello Holly,

Our next BLK3 flight is targeted for late Q1 / early Q2 2027 with 135 kg of payload capacity still available, SPACEavailable...(TM), and after seeing the Chromospheric Magnetism Explorer at the 2026 HelioTech / Orbital Flight Symposium, I wanted to reach out to you directly about it.

I'm John Quinn, CEO of Exos Aerospace. We build and fly BLK3, a reusable, recoverable suborbital rocket, one of only three FAA-licensed reusable launch platforms in the U.S. We carry payloads above the atmosphere and return the hardware within a couple of days, which makes us a natural fit for science-objective payloads that today rely on sounding-rocket-class access: brief above-atmosphere observing windows, instrument technology maturation, and calibration flights, but with reusability and reflight economics behind them.

I would welcome a conversation about your science objectives and whether that open capacity could serve CMEx-class chromospheric and heliophysics payloads, whether to mature and de-risk instrument technology ahead of an orbital or Explorer mission, or as a lower-cost cadence for the observations themselves. If there is a fit, we can align the flight profile to your objectives and share our Payload User Guide.

Would you have 30 minutes in the next couple of weeks?

Best Regards,
John"""

body = f"""John — REVISED ready-to-send draft for your outreach to Dr. Holly Gilbert (PI, Chromospheric Magnetism Explorer / CMEx; NCAR High Altitude Observatory), captured at HelioTech 2026. Per your note: JUST TO HOLLY (no team CC), and leads with the flight opportunity. NCAR/UCAR is .edu nonprofit, not .gov, your direct send is fine; review/edit and send from your account.

TO:      hgilbert@ucar.edu
SUBJECT: {proposed_subject}

----- DRAFT BELOW -----

{email_body}

-----------------------
(Your Outlook signature will append title/company/address automatically. SPACEavailable...(TM) renders with the trademark symbol in your client.)
Also saved at drafts/Holly_Gilbert_NCAR_CMEx_ScienceObjective_Payloads_Outreach.md. Logged on the BLK3 payload pipeline as a high-value science-PI lead, Owner: John."""

def build():
    m = MIMEMultipart("alternative")
    m["From"] = f"John Quinn <{user}>"
    m["Reply-To"] = f"John Quinn <{from_addr}>"
    m["To"] = to_addr
    m["Subject"] = "[READY TO SEND] Holly Gilbert (NCAR / CMEx) — science-objective payloads on BLK3"
    m.attach(MIMEText(body, "plain"))
    return m

# retry for up to ~40 min: 40 attempts, 60s apart
for attempt in range(1, 41):
    try:
        s = smtplib.SMTP(host, port, timeout=30)
        s.starttls(); s.login(user, password)
        s.sendmail(user, [to_addr], build().as_string())
        s.quit()
        print(f"SENT ok on attempt {attempt}")
        sys.exit(0)
    except Exception as e:
        print(f"attempt {attempt} failed: {e}")
        time.sleep(60)
print("GAVE UP after 40 attempts")
sys.exit(1)
