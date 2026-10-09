#!/usr/bin/env python3
"""Lizi's PIEE 30-day keep-alive (Lizi 10/9). PIEE locks accounts after ~30-34 days idle.
Daily 09:00 CT:
  - Open task tagged piee-keepalive-lizi: email Lizi 2 days before due, on the due date, then an
    URGENT email EVERY day it's overdue (escalating subject; lock warning from day 3 overdue).
  - When she marks it Done, create the next instance due 30 days after the COMPLETION date
    (completion-based, so an early login never lets the account lapse).
Emails carry X-Exo-No-Task so the email tracker never turns them into tasks."""
import os, json, subprocess, urllib.request
from datetime import date, datetime, timedelta
from email.message import EmailMessage
TAG = "piee-keepalive-lizi"
TO = "lquinn@exosaero.com"
STATE = os.path.expanduser("~/.openclaw/workspace/logs/lizi-piee-keepalive.state.json")
k = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
S = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
H = {"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json"}

def get(path):
    return json.load(urllib.request.urlopen(urllib.request.Request(S + path, headers=H), timeout=60))

def post(path, d):
    urllib.request.urlopen(urllib.request.Request(S + path, data=json.dumps(d).encode(),
                           headers={**H, "Prefer": "return=minimal"}, method="POST"), timeout=60)

def pdate(s):
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date() if s else None

def mail(subject, body):
    m = EmailMessage(); m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = TO; m["Subject"] = subject
    m["X-Exo-No-Task"] = "1"; m.set_content(body)
    subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", TO], input=m.as_bytes(), check=True, timeout=60)

def new_instance(due):
    post("tasks", {"title": "Log into PIEE (30-day keep-alive) — Lizi", "state": "To Do", "priority": 80,
                   "category": "Compliance", "owner": "Exo", "assigned_to": "Lizi Quinn", "assigned_email": TO,
                   "due_date": due.isoformat() + "T23:59:59+00:00", "source": "lizi-piee-keepalive", "tags": [TAG, "PIEE"],
                   "description": ("Log into https://piee.eb.mil (any login counts), then mark this task Done. "
                                   "PIEE locks accounts after ~30 days of inactivity. When you mark it Done, the next "
                                   "one is created automatically 30 days from that day. Daily URGENT emails start the day after it's due.")})

today = date.today()
rows = get(f"tasks?tags=cs.%7B{TAG}%7D&select=id,state,due_date,completed_at,updated_at&order=id.desc")
open_rows = [r for r in rows if str(r.get("state", "")).lower() not in ("done", "complete", "completed", "cancelled", "canceled")]
if not open_rows:
    if rows:
        last = rows[0]
        done_on = pdate(last.get("completed_at")) or pdate(last.get("updated_at")) or today
        new_instance(done_on + timedelta(days=30)); print("created next instance", done_on + timedelta(days=30))
    raise SystemExit
t = open_rows[0]; due = pdate(t["due_date"]); tid = t["id"]
st = json.load(open(STATE)) if os.path.exists(STATE) else {}
key = f"{tid}:{today.isoformat()}"
if st.get("last") == key:
    raise SystemExit
over = (today - due).days
link = "https://piee.eb.mil"
if over == -2:
    mail("PIEE login due in 2 days", f"Hi Lizi,\n\nHeads-up: your PIEE keep-alive login is due {due:%a %m/%d}. Log into {link}, then mark task #{tid} Done in Mission Control.\n\n- Exo")
elif over == 0:
    mail("⚠️ PIEE login due TODAY", f"Hi Lizi,\n\nToday's the day: log into {link} (any login counts) and mark task #{tid} Done. PIEE locks accounts after ~30 days idle.\n\n- Exo")
elif over > 0:
    lock = "  🔒 YOUR ACCOUNT MAY LOCK ANY DAY NOW" if over >= 3 else ""
    mail(f"🚨 URGENT: PIEE login OVERDUE {over} day{'s' if over > 1 else ''}{lock}",
         f"Hi Lizi,\n\nYour PIEE login is {over} day{'s' if over > 1 else ''} overdue (was due {due:%m/%d}).\n\n"
         f"1) Log into {link} right now.\n2) Mark task #{tid} Done in Mission Control.\n\n"
         "If it's already locked, call the PIEE help desk at 866-618-5988 (Vendor > Account Activations) "
         "or ask John/Neil to reactivate you.\n\nI'll keep emailing every day until it's marked Done.\n\n- Exo")
else:
    raise SystemExit
st["last"] = key; json.dump(st, open(STATE, "w"))
