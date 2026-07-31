import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

host = "127.0.0.1"
port = 1025
user = "jquinnexo@pm.me"
password = "SPqYBivj98-jyF3RujLKxA"

from_addr = "jquinn@exosaero.com"
to_addr = "ACSAbuDhabi@state.gov"
subject = "Follow-Up: US Citizen Fraud Case — Exos Aerospace vs. The Infinity Group FZCO — Dubai (April 6 Email)"

body = """Dear American Citizen Services Team,

I am writing to follow up on an email I sent to this office on April 6, 2026, which has not yet received a response. I am John Quinn, CEO of Exos Aerospace (Greenville, TX), and the matter involves a significant ongoing fraud case in which our company was defrauded of $613,097.63 by a UAE-based organized fraud ring operating under the names The Infinity Group FZCO and formerly Aras Consultancy FZCO, based in Dubai Marina. The Dubai Supreme Court ruled in our favor in August 2023 (Case #207/2023/5263, judgment of 3,420,830 AED), yet enforcement has been actively obstructed for over two years. A formal Dubai Police complaint was filed November 23, 2025 (Reference #225004184901). The principal perpetrators are Ralf Jung (alias Frank Kahn, German passport C4KN7VH02, with prior German fraud convictions), Ferhat Dogan (passport U235923290), and Ashraf Mahmoud.

I am reaching out again with some urgency because coordination with the Irish Embassy Abu Dhabi is now actively underway. David Moore at the Irish Embassy (David.Moore@dfa.ie) has been engaged on behalf of Irish victims in this same fraud ring and specifically recommended that US victims contact the US Embassy to establish parallel diplomatic coordination. This is a multinational case with an estimated 100 victims across the United States, Ireland, the United Kingdom, Germany, and Switzerland, with total losses exceeding 20 million euros. The Irish Embassy's active involvement creates a real opportunity for coordinated diplomatic pressure, but that window is time-sensitive.

In my April 6 email, I made three specific requests: (1) assignment of a Consular Officer who could coordinate directly with the Irish Embassy on this matter; (2) an introduction to the FBI Legal Attaché (Legat) stationed in Abu Dhabi; and (3) guidance on any available diplomatic escalation channels given the prolonged obstruction of a final court judgment. I would respectfully ask that these requests be reviewed and that someone from your office contact me at the information below at the earliest opportunity.

Thank you for your attention to this matter. I recognize your office handles a high volume of cases, and I appreciate your time. Given the scale of the fraud, the number of American and allied-nation victims, and the active engagement of a partner embassy, I believe this case merits prompt attention. I am happy to provide the full case documentation, court filings, and supporting materials upon request.

Sincerely,

John Quinn
Chief Executive Officer, Exos Aerospace
299 FM 1903, Greenville, TX 75402
jquinn@exosaero.com
+1-972-740-8355"""

msg = MIMEMultipart("alternative")
msg["From"] = f"John Quinn <{user}>"
msg["Reply-To"] = f"John Quinn <{from_addr}>"
msg["To"] = to_addr
msg["Subject"] = subject
msg.attach(MIMEText(body, "plain"))

try:
    with smtplib.SMTP(host, port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.sendmail(user, [to_addr], msg.as_string())
    print("SUCCESS: Email sent successfully.")
except Exception as e:
    print(f"FAILURE: {type(e).__name__}: {e}")
