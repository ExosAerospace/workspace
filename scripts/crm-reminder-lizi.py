#!/usr/bin/env python3
"""Biweekly reminder to Lizi to send updated CRM spreadsheet."""

# --- governance: correlation logging (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("crm")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gevent(_GRUN, "error", status="error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = '127.0.0.1'
SMTP_PORT = 1025
EMAIL_USER = 'jquinnexo@pm.me'
EMAIL_PASS = 'SPqYBivj98-jyF3RujLKxA'
LIZI_EMAIL = 'Lquinn@exosaero.com'

msg = MIMEMultipart('alternative')
msg['Subject'] = 'CRM Update Reminder \u2014 Send Latest Spreadsheet'
msg['From'] = EMAIL_USER
msg['To'] = LIZI_EMAIL

text = """Hi Lizi,

Quick reminder — when you get a chance, please email your latest CRM tracking spreadsheet to jquinnexo@pm.me so we can keep the system up to date.

Just reply to this email with the file attached, or send it over whenever it's ready. The system will automatically import any updates.

Thanks!
Jon
"""

html = """<html><body style="font-family:-apple-system,system-ui,sans-serif;color:#1a1a1a;line-height:1.6;">
<p>Hi Lizi,</p>
<p>Quick reminder &mdash; when you get a chance, please email your latest CRM tracking spreadsheet to <a href="mailto:jquinnexo@pm.me">jquinnexo@pm.me</a> so we can keep the system up to date.</p>
<p>Just reply to this email with the file attached, or send it over whenever it's ready. The system will automatically import any updates.</p>
<p>Thanks!<br>Jon</p>
</body></html>"""

msg.attach(MIMEText(text, 'plain'))
msg.attach(MIMEText(html, 'html'))

try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, LIZI_EMAIL, msg.as_string())
        print(f"Reminder sent to {LIZI_EMAIL}")
except Exception as e:
    print(f"Error sending reminder: {e}")
