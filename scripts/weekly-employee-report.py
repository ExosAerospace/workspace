#!/usr/bin/env python3
"""
weekly-employee-report.py — a personal weekly Mission Control note to each employee.

Purpose: drive adoption. Each teammate gets a short, encouraging weekly email showing their
own open tasks and nudging them to LOG what they're doing in Mission Control (so their effort
is captured), including by sending Exo photos of what they're building or a problem to solve.

Run: python3 scripts/weekly-employee-report.py            → emails each employee their report
     python3 scripts/weekly-employee-report.py --preview  → emails ALL reports to Jon for review
Scheduled Mondays via launchd com.exos.weekly-employee-report.
"""

# --- supabase retry/backoff shim (auto-added) ---
import os as _sbu_os, sys as _sbu_sys; _sbu_sys.path.insert(0, _sbu_os.path.dirname(_sbu_os.path.abspath(__file__)))
import supabase_util as _sbu; _sbu.install()
# --- end shim ---
import json, os, sys, subprocess, urllib.request
from datetime import date
from email.message import EmailMessage

WS = "/Users/exomac/.openclaw/workspace"
USERS = os.path.join(WS, "mission-control", "users.json")
OPTOUT = os.path.join(WS, "mission-control", "data", "weekly-report-optout.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")


def optout_set():
    try:
        return {e.lower() for e in json.load(open(OPTOUT)).get("optout", [])}
    except Exception:
        return set()
NS = json.load(open(os.path.join(WS, "mission-control", "data", "north-stars.json")))
PREVIEW = "--preview" in sys.argv
JON = "jquinn@exosaero.com"
INTAKE = "exosmc@proton.me"

# Jon has several email identities but ONE Mission Control board (all tasks land on
# jquinn@exosaero.com). Any of these alias records must be treated as Jon so the
# adoption-nudge weekly is not mailed to a 0-task duplicate identity (which produced a
# false "Nothing is assigned to you" note to the CEO who actually has 250+ open items).
JON_ALIASES = {"jquinnexo@pm.me", "megawattcontrols@gmail.com"}
ALL_JON = {JON} | JON_ALIASES


def supa(path):
    k = json.load(open(SECRETS))["supabase_service_role_key"]
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/" + path,
        headers={"apikey": k, "Authorization": "Bearer " + k}), timeout=40).read())


def north_star(email):
    ns = NS.get("owner_map", {}).get(email.lower(), NS.get("default", "revenue"))
    return NS.get("north_stars", {}).get(ns, {}).get("label", "Revenue (near-term cash)")


def report_body(first, email, tasks):
    today = date.today()
    mine = [t for t in tasks if (t.get("assigned_email") or "").lower() == email.lower()
            and str(t.get("state", "")).lower() not in ("done", "complete", "completed")]
    def due(t):
        return str(t.get("due_date") or "9999")[:10]
    mine.sort(key=due)
    lines = [f"Hi {first},", "",
             "Here is your Mission Control weekly.", "",
             f"Your focus (North Star): {north_star(email)}.", ""]
    if mine:
        lines.append(f"Your open items ({len(mine)}):")
        for t in mine[:12]:
            d = str(t.get("due_date") or "")[:10]
            lines.append(f"  - {t.get('title','')[:70]}" + (f"  (due {d})" if d else ""))
        lines.append("")
    else:
        lines.append("Nothing is assigned to you in the system yet — so this is the perfect week to start capturing your work.")
        lines.append("")
    lines += [
        "Please use Mission Control to log what you are working on. It is how your effort gets seen, and how Exo can take load off you:",
        f"  - Add a task on your board, or email {INTAKE} with \"@Exobot\" and a plain-English request.",
        f"  - BCC {INTAKE} on your work emails and they file themselves into tasks and contacts automatically.",
        "  - Pictures are one of the best ways to communicate: send Exo a photo of what you are building, a part that will not seat, or a problem you are solving, and it will help you work through it. (Keep anything ITAR/EAR/CUI out — SharePoint only.)",
        "",
        "The more you put into the system, the more it works for you.",
        "",
        "Thank you,",
        "Jon (via Exo)",
    ]
    return "\n".join(lines)


def send(to, subject, body):
    m = EmailMessage()
    m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = to
    m["Subject"] = subject; m["Reply-To"] = JON
    m.set_content(body)
    p = subprocess.run(["msmtp", "-a", "protonmail", to], input=bytes(m), capture_output=True, timeout=60)
    return p.returncode == 0


def main():
    skip = optout_set()
    users = [u for u in json.load(open(USERS))
             if (u.get("email") or "").lower() not in ALL_JON
             and (u.get("email") or "").lower() not in skip]
    tasks = supa("tasks?select=id,title,state,due_date,assigned_email&limit=5000")
    sent = 0
    for u in users:
        email = u.get("email"); name = u.get("name") or email
        first = name.split()[0]
        body = report_body(first, email, tasks)
        if PREVIEW:
            ok = send(JON, f"[PREVIEW] Weekly MC report for {name}", body)
        else:
            ok = send(email, "Your Mission Control weekly", body)
        sent += ok
        print(("preview→Jon" if PREVIEW else "sent") + f": {name} ({'ok' if ok else 'FAIL'})")
    print(f"{sent}/{len(users)} reports {'previewed' if PREVIEW else 'sent'}")


if __name__ == "__main__":
    main()
