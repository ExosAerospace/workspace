#!/usr/bin/env python
import imaplib
import smtplib
import ssl
import os
import re
from datetime import datetime
from email import message_from_bytes

# --- Configuration ---
IMAP_HOST = "127.0.0.1"
IMAP_PORT = 1143
EMAIL_USER = "jquinnexo@pm.me"
EMAIL_PASS = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
SMTP_HOST = "127.0.0.1"
SMTP_PORT = 1025
SMTP_SENDER = "jquinnexo@pm.me"
SMTP_PASSWORD = __import__('json').load(open(__import__('os').path.expanduser('~/.openclaw/secrets.json')))['protonmail_bridge_smtp_password']
TRACKER_PATH = "/Users/exomac/.openclaw/workspace/opportunities-tracker.md"
DRAFTS_DIR = "/Users/exomac/.openclaw/workspace/drafts"
HIGH_PRIORITY_EMAILS_TO_DRAFT = ["Government deadline", "direct customer inquiry", "Jon specifically flagged it"]

# --- Exos Capabilities ---
EXOS_CAPABILITIES = [
    "BLK3 PSRLV reusable suborbital launch",
    "Scorpius Type 5 TRL 9 cryogenic tanks (lunar heritage on IM Odysseus/Athena)",
    "RDRE development (NASA MSFC DUA)",
    "FAA-licensed reusable suborbital launch (licensed launch site: Spaceport America, NM); Greenville TX = manufacturing/test/hover facility only"
]

# --- Helper Functions ---

def is_scam_or_spam(subject, body):
    spam_keywords = ["security alert", "service notification", "receipt", "apple", "proton account", "fraud"]
    for keyword in spam_keywords:
        if keyword in subject.lower() or keyword in body.lower():
            return True
    return False

def is_out_of_scope(subject, body):
    return any(k in subject.lower() or k in body.lower() for k in ["service notification", "receipt", "apple", "proton account", "duplicate"])

def check_for_opportunity(subject, body, email_id):
    """Evaluates an email against business opportunity criteria."""
    if is_scam_or_spam(subject, body) or is_out_of_scope(subject, body):
        return None, "Filtered", "Out of Scope/Spam"

    # Basic scoring based on keywords
    score = 0
    found_keywords = []
    all_text = (subject + " " + body).lower()
    
    opportunity_triggers = [
        "rfi", "rfp", "solicitation", "capability request", "scoping", 
        "nasa", "nasa program", "dod", "air force", "navy", "army",
        "commercial launch", "partnership", "investor", "fundraising", 
        "international", "spaceport", "teaming", "contract"
    ]

    for trigger in opportunity_triggers:
        if trigger in all_text:
            score += 1
            found_keywords.append(trigger)

    # Check against core Exos value propositions
    for cap in EXOS_CAPABILITIES:
        if cap.lower() in all_text:
            score += 2
            found_keywords.append(f"Cap: {cap}")

    if score >= 2:
        # Create a placeholder opportunity structure
        return {
            "title": f"Potential Opportunity from: {subject}",
            "source": f"Email ID: {email_id}",
            "type": "Opportunity",
            "value_estimate": "TBD",
            "key_pitch": f"Scored highly based on keywords: {', '.join(set(found_keywords))}",
            "next_action": "Manual review required. Check context.",
            "status": "NEW",
            "priority": "Medium"
        }, "Found", "High Score"
    
    return None, "Not an Opportunity", "Low Score"

def update_tracker(opportunity_data, email_id, subject, body, today_date):
    """Appends a new opportunity entry and updates the log."""
    try:
        with open(TRACKER_PATH, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = "# Exos Aerospace Opportunity Tracker\n\nThis file was initialized by the email scanner.\n\n"
    
    # 1. Append New Opportunity (assuming we found one)
    new_entry = f"""
### OPP-AUTO-{datetime.now().strftime('%Y%m%d%H%M')[:8]} | {opportunity_data['title']}
**Source:** {opportunity_data['source']}
**Status:** {opportunity_data['status']}
**Due:** TBD
**Type:** {opportunity_data['type']}
**Value:** {opportunity_data['value_estimate']}
**Draft:** N/A
**Emailed to Jon:** N/A
**Key pitch:** {opportunity_data['key_pitch']}
**Next action:** {opportunity_data['next_action']}

---
"""
    # 2. Append to Daily Scan Log
    log_entry = f"""
| {today_date} | {email_id} | {opportunity_data['title']} | {opportunity_data['status']} |
"""

    # Simple regex/search to find and replace the log section - assumes the format provided in the prompt
    log_update_section = r"## DAILY EMAIL SCAN LOG\n\n\| Date \| Emails Scanned \| New Opps Found \| Notes \|\n\|------\|---------------|----------------|-------\|"
    
    if not re.search(log_update_section, content, re.DOTALL):
         # If log section doesn't exist, append it at the end
        content += f"\n\n## DAILY EMAIL SCAN LOG\n\n{log_update_section}\n"

    # Append the content update and log update
    new_content = content.replace(log_update_section, log_update_section + "\n") + new_entry + log_entry

    with open(TRACKER_PATH, 'w') as f:
        f.write(new_content)
    
    print(f"SUCCESS: Updated {TRACKER_PATH} with new opportunity and log entry.")
    return True

def draft_and_send_high_priority(opportunity, subject, body, email_id, today_date):
    """Drafts and emails a high-priority submittal."""
    print(f"!!! HIGH PRIORITY DETECTED: Drafting and sending for {opportunity['title']} !!!")
    
    # 1. Draft the document (using a predictable filename)
    draft_filename = f"high_priority_draft_{email_id}.md"
    draft_content = f"""# URGENT: High Priority Draft for {subject}
**Source Email:** {email_id}
**Context:** This material was triggered by an email scanned on {today_date}.
**Opportunity:** {opportunity['title']}
**Recommendation:** IMMEDIATE review and action required from Jon.
**Key Content Snippet:** {body[:1000]}...
"""
    if not os.path.exists(DRAFTS_DIR):
        os.makedirs(DRAFTS_DIR)
    
    draft_path = os.path.join(DRAFTS_DIR, draft_filename)
    with open(draft_path, 'w') as f:
        f.write(draft_content)
    print(f"DRAFT CREATED: Saved draft to {draft_path}")

    # 2. Compose Email
    recipient = "jquinn@exosaero.com"
    msg = f"Subject: URGENT: High Priority Opportunity Found - {subject[:50]}...\n\nTeam,\n\nFound a high-priority opportunity matching our criteria. The details have been logged in the primary tracker file. A draft submission file has been placed at {draft_path} for your immediate review. \n\nRegards,\nExo Scanner"
    
    # 3. Send Email (SMTP)
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context) # Secure connection
            server.login(SMTP_SENDER, SMTP_PASSWORD)
            server.sendmail(SMTP_SENDER, recipient, msg)
        print(f"SMTP SUCCESS: Draft successfully emailed to {recipient}.")
        return True
    except Exception as e:
        print(f"!!! CRITICAL ERROR: Failed to send high-priority email. Check local mail service. Error: {e} !!!")
        return False

# --- Mission Control wiring ---
import json as _json
import urllib.request as _urlreq

MC_BASE = "http://127.0.0.1:8080"
MC_TOKEN_PATH = "/Users/exomac/.openclaw/workspace/mission-control/data/.decisions-token"

def _mc_token():
    try:
        with open(MC_TOKEN_PATH) as f:
            return f.read().strip()
    except Exception:
        return ""

def _mc_post(path, payload):
    """POST JSON to a Mission Control ingest endpoint. Best-effort; never fatal."""
    try:
        req = _urlreq.Request(
            MC_BASE + path,
            data=_json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-exo-token": _mc_token()},
            method="POST",
        )
        with _urlreq.urlopen(req, timeout=8) as r:
            return 200 <= r.status < 300
    except Exception as e:
        print(f"  MC post failed ({path}): {e}")
        return False

def post_to_mission_control(opportunity, subject, body, email_id, today_date, is_high_priority):
    """Turn a scanned opportunity into Mission Control actions.

    - Always: append to the Research & Intel feed (Inbox Opportunity brief).
    - High priority: also raise a Decision (pursue? yes/no) in the Decisions inbox.
    """
    eid = str(email_id).strip("b'\" ")
    brief = {
        "id": f"inbox-{eid}",
        "title": opportunity["title"][:160],
        "date": today_date,
        "category": "Inbox Digest",
        "source": "Email Opportunity Scanner",
        "highlights": [
            f"**Next action:** {opportunity['next_action']}",
            f"**Signal:** {opportunity['key_pitch']}",
            f"**Status:** {opportunity['status']} | Priority: {opportunity['priority']}",
        ],
        "body": (subject + "\n\n" + body)[:3000],
    }
    _mc_post("/api/research/ingest", brief)

    if is_high_priority:
        _mc_post("/api/decisions/ingest", {
            "dedupeKey": f"inbox-opp-{eid}",
            "title": f"Pursue inbox opportunity: {subject[:90]}",
            "question": "Pursue this inbound opportunity?",
            "context": opportunity["key_pitch"],
            "proposedAction": opportunity["next_action"],
            "type": "yesno",
            "options": ["Pursue", "Pass"],
            "priority": "high",
            "relatedItem": opportunity["title"][:120],
            "source": "Email Opportunity Scanner",
        })
    print(f"  → Mission Control updated (decision={is_high_priority}) for {opportunity['title'][:50]}")


# --- Main Execution ---

def run_scanner():
    today_date = datetime.now().strftime("%Y-%m-%d")
    print(f"--- Starting Email Opportunity Scan for {today_date} ---")
    
    try:
        # 1. Connect to IMAP
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('inbox')
        
        # Fetch only unread emails
        status, messages = mail.search(None, 'UNSEEN')
        message_ids = messages[0].split()

        if not message_ids:
            print("No unread emails found. Scanner exiting.")
            return
        
        print(f"Found {len(message_ids)} unread emails. Processing...")

        processed_ids = []
        
        for msg_id in message_ids:
            # Fetch raw email data
            status, data = mail.fetch(msg_id, '(RFC822)')
            raw_email = data[0][1]
            
            # Parse email
            try:
                msg = message_from_bytes(raw_email)
                subject = msg['subject'] if msg['subject'] else "No Subject"
                body = ""
                body_parts = []
                for part in msg.walk():
                    ctype = part.get_content_type()
                    cdispo = part.get('Content-Disposition')

                    if ctype == 'text/plain' and not cdispo:
                        body_parts.append(part.get_payload(decode=True).decode(str(part.get_content_charset()) or 'utf-8', errors='ignore'))
                
                body = "\n\n".join(body_parts).strip()

                # 2. Evaluate opportunity
                opportunity, status_found, reason = check_for_opportunity(subject, body, msg_id)
                
                if opportunity:
                    print(f"[*] Opportunity found from Subject: {subject[:50]}...")
                    
                    # 3. Update Tracker
                    update_tracker(opportunity, msg_id, subject, body, today_date)
                    
                    # 4. Check for High Priority/Drafting
                    is_high_priority = any(trigger in subject or trigger in body for trigger in HIGH_PRIORITY_EMAILS_TO_DRAFT) or opportunity['priority'] in ["High"]

                    # 3b. Wire into Mission Control (research feed + decisions inbox)
                    post_to_mission_control(opportunity, subject, body, msg_id, today_date, is_high_priority)

                    if is_high_priority:
                        # This will also update the tracker (conceptually, by setting the draft status)
                        draft_and_send_high_priority(opportunity, subject, body, msg_id, today_date)
                        # Mark email as processed/read after high-priority action
                        mail.store(msg_id, '+FLAGS', '\\Seen') 
                        processed_ids.append(msg_id)
                    else:
                        # Mark email as read even if no action was taken, to prevent re-scanning unless needed
                        mail.store(msg_id, '+FLAGS', '\\Seen')
                        processed_ids.append(msg_id)
                else:
                    # Filtered out or not an opportunity, but we still mark it as seen to avoid looping
                    mail.store(msg_id, '+FLAGS', '\\Seen')
                    processed_ids.append(msg_id)

            except Exception as e:
                print(f"Error processing message {msg_id}: {e}")
                # Best effort to move the message if processing fails completely
                mail.store(msg_id, '+FLAGS', '\\Seen')
                processed_ids.append(msg_id)

        print("\n--- Scan Complete ---")
        print("All processed emails have been flagged as 'Seen' to prevent reprocessing.")

    except Exception as e:
        print(f"FATAL SCAN ERROR: Could not connect or execute IMAP scan. Reason: {e}")
        print("ACTION REQUIRED: Check network connection, credentials, and local services (IMAP/SMTP ports 1143/1025).")
    finally:
        if 'mail' in locals():
            mail.logout()

if __name__ == "__main__":
    run_scanner()