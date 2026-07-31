#!/usr/bin/env python3
"""
STRATFI Investor Commitment Email — Batch Sender
Sends personalized STRATFI co-investment opportunity emails to 195 investors.
Approved by Jon Quinn on 2026-05-15.
"""

import json
import subprocess
import time
import sys
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

MAILING_LIST = '/Users/exomac/.openclaw/workspace/stratfi-mailing-list.json'
LOG_FILE = '/Users/exomac/.openclaw/workspace/logs/stratfi-send-log.json'
FROM_EMAIL = 'jquinnexo@pm.me'
REPLY_TO = 'jquinn@exosaero.com'
CC_EMAIL = 'lquinn@exosaero.com'
SUBJECT = 'Exos Aerospace — STRATFI Co-Investment Opportunity | $15M+ DoD Match | Deadline May 29'
BOOKING_LINK = 'https://outlook.office365.us/bookwithme/user/3d1b68ea7e5643f9b2e76624f9dfd95f%40exosaero.com?anonymous&ismsaljsauthenabled'

DELAY_BETWEEN_EMAILS = 10  # seconds between sends — ProtonMail rate limits at ~25 with 3s delay

def get_email_body(first_name, company):
    """Generate personalized email body."""

    # Personalize the commitment request line based on whether we have company info
    if company and company != 'None':
        commitment_line = f"A non-binding letter of intent indicating {company}'s interest in co-investing alongside the DoD, contingent upon STRATFI selection."
    else:
        commitment_line = "A non-binding letter of intent indicating your interest in co-investing alongside the DoD, contingent upon STRATFI selection."

    body = f"""{first_name},

I am writing to share an exceptional near-term opportunity that could significantly accelerate Exos Aerospace's growth trajectory while providing substantial downside protection through direct U.S. Department of Defense co-investment.

THE OPPORTUNITY: SpaceWERX STRATFI (PY26.1)

The U.S. Space Force, through SpaceWERX, has issued a Strategic Funding Increase (STRATFI) Notice of Opportunity for PY26.1. STRATFI combines government funding with private capital, providing up to $15 million or more in combined DoD matching funds and private co-investment.

WHY EXOS QUALIFIES

Exos Aerospace holds an active U.S. Air Force SBIR Phase II contract (FA9300-25-C-6022) for our HVRR-RDRE technology. This active Phase II provides direct STRATFI eligibility under 15 U.S.C. Section 638 -- no new competition required. This is a sole-source pathway contingent on securing a USSF program office sponsor and demonstrating private co-investment commitment.

WHAT WE ARE REQUESTING

To submit a compelling STRATFI application, Exos needs letters of commitment from private investors. Specifically:

  - {commitment_line}
  - The approximate investment amount you would consider committing (the DoD match is typically 1:1 or greater against private capital).
  - Acknowledgment of the STRATFI structure, where DoD funds de-risk the private investment by directly funding technology maturation milestones.

WHY THIS MATTERS FOR INVESTORS

  - DoD matching funds effectively double capital deployed against Exos milestones without additional dilution.
  - Government co-investment validates the technology and provides a direct pathway to defense procurement.
  - STRATFI recipients receive dedicated program office sponsorship, accelerating DoD end-user contracts.
  - Exos's flight-proven Block 3 reusable vehicle and proprietary RDRE propulsion represent dual-use capabilities.

TIMELINE

  May 23, 2026 — Investor commitment letters needed
  May 29, 2026 — STRATFI Notice of Opportunity closes
  June 2026 — USSF program office sponsor engagement
  Q3-Q4 2026 — STRATFI award and program initiation

If this is of interest, I would welcome a brief call next week to discuss the opportunity and next steps.

Book a meeting: {BOOKING_LINK}

Given the May 29 deadline, I would appreciate your indication of interest by May 23.

Best regards,

John Quinn
CEO, Exos Aerospace
Greenville, Texas

CONFIDENTIAL -- This communication is intended solely for the named recipient and may contain information that is privileged, confidential, or exempt from disclosure. Any investment-related statements herein are forward-looking and subject to risk. No offer to sell securities is made hereby. Any such offer would be made only by means of a confidential private placement memorandum or similar offering document."""

    return body


def send_email(to_email, first_name, company):
    """Send a single personalized email via msmtp."""
    body = get_email_body(first_name, company)

    msg = MIMEMultipart('alternative')
    msg['From'] = f'John Quinn <{FROM_EMAIL}>'
    msg['To'] = to_email
    msg['Cc'] = CC_EMAIL
    msg['Reply-To'] = REPLY_TO
    msg['Subject'] = SUBJECT

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        proc = subprocess.run(
            ['msmtp', '-a', 'protonmail', '--', to_email, CC_EMAIL],
            input=msg.as_string().encode('utf-8'),
            capture_output=True,
            timeout=60
        )
        if proc.returncode == 0:
            return True, None
        else:
            err = proc.stderr.decode('utf-8', errors='ignore')
            # If rate limited, wait 60s and retry once
            if '554' in err or 'Too many' in err:
                time.sleep(60)
                proc2 = subprocess.run(
                    ['msmtp', '-a', 'protonmail', '--', to_email, CC_EMAIL],
                    input=msg.as_string().encode('utf-8'),
                    capture_output=True,
                    timeout=60
                )
                if proc2.returncode == 0:
                    return True, None
                return False, proc2.stderr.decode('utf-8', errors='ignore')
            return False, err
    except subprocess.TimeoutExpired:
        return False, 'timeout (60s)'
    except Exception as e:
        return False, str(e)


def main():
    with open(MAILING_LIST, 'r') as f:
        data = json.load(f)

    tier1 = data['tier1']
    tier2 = data['tier2']
    all_contacts = tier1 + tier2

    print(f"STRATFI Batch Sender")
    print(f"Total contacts: {len(all_contacts)} (Tier 1: {len(tier1)}, Tier 2: {len(tier2)})")
    print(f"Subject: {SUBJECT}")
    print(f"From: {FROM_EMAIL} | Reply-To: {REPLY_TO} | CC: {CC_EMAIL}")
    print(f"Delay: {DELAY_BETWEEN_EMAILS}s between emails")
    print(f"Starting at: {datetime.now().isoformat()}")
    print("=" * 60)

    # Load existing log if resuming
    log = []
    start_idx = 0
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            log = json.load(f)
        # Resume from where we left off
        sent_emails = {entry['email'] for entry in log if entry.get('status') == 'sent'}
        print(f"Resuming: {len(sent_emails)} already sent")
    else:
        sent_emails = set()

    sent = len(sent_emails)
    failed = 0

    for i, contact in enumerate(all_contacts):
        email = contact['email']
        if email in sent_emails:
            continue

        first_name = contact['first_name']
        company = contact['company']
        tier = contact['tier']

        print(f"[{sent+1}/{len(all_contacts)}] {tier} | {first_name} | {company} | {email}...", end=' ', flush=True)

        success, error = send_email(email, first_name, company)

        entry = {
            'email': email,
            'name': contact['name'],
            'first_name': first_name,
            'company': company,
            'tier': tier,
            'timestamp': datetime.now().isoformat(),
            'status': 'sent' if success else 'failed',
            'error': error
        }
        log.append(entry)

        if success:
            sent += 1
            print("✓")
        else:
            failed += 1
            print(f"✗ ({error})")

        # Save log after each send
        with open(LOG_FILE, 'w') as f:
            json.dump(log, f, indent=2)

        # Rate limit
        if i < len(all_contacts) - 1:
            time.sleep(DELAY_BETWEEN_EMAILS)

    print("=" * 60)
    print(f"Complete: {sent} sent, {failed} failed")
    print(f"Log saved to: {LOG_FILE}")


if __name__ == '__main__':
    main()
