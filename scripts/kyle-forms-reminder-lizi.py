#!/usr/bin/env python3
"""One-shot reminder to Lizi (Thu 2026-09-03) to check on Kyle's 4 signed TDA forms
for the TX STEP grant. Emails Lizi via Proton Bridge, then unloads + removes its own
launchd job and plist so it never re-fires."""
import os
import smtplib
import subprocess
from email.mime.text import MIMEText

SMTP_HOST = '127.0.0.1'
SMTP_PORT = 1025
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
LIZI_EMAIL = 'Lquinn@exosaero.com'
LABEL = 'com.exos.kyle-forms-reminder-lizi'
PLIST = os.path.expanduser(f'~/Library/LaunchAgents/{LABEL}.plist')

BODY = """Hi Lizi,

Reminder you asked me for yesterday — check in on Kyle's four signed TDA forms for the
Texas STEP grant:

  1. W-9
  2. Texas Identification Number (TIN)
  3. Direct Deposit authorization
  4. SBA self-representation

Submit target is Sept 4 (hard deadline Sept 10), so there's still a little buffer. If they're
back, plug them in and submit. If not, nudge Kyle again — the drafted nudge is queued on your
Decisions matrix (D-7281760) ready to send.

John was already notified that the forms hadn't come back from Kyle.

- Exo
"""

def send():
    msg = MIMEText(BODY)
    msg['Subject'] = 'Reminder: check on Kyle’s TDA forms (STEP grant — submit target Sept 4)'
    msg['From'] = EMAIL_USER
    msg['To'] = LIZI_EMAIL
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(EMAIL_USER, EMAIL_PASS)
        s.sendmail(EMAIL_USER, [LIZI_EMAIL], msg.as_string())

def self_destruct():
    # Fire-once: tear down the launchd job and delete the plist so it can't re-fire.
    try:
        subprocess.run(['launchctl', 'unload', PLIST], check=False)
    except Exception:
        pass
    try:
        if os.path.exists(PLIST):
            os.remove(PLIST)
    except Exception:
        pass

if __name__ == '__main__':
    try:
        send()
    finally:
        self_destruct()
