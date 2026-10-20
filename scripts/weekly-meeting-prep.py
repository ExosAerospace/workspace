#!/usr/bin/env python3
"""
WEEKLY TEAM MEETING prep — builds the agenda for the Tuesday 10:00 weekly sync (Steve, Phil, John,
Lizi) and delivers it the day before (Monday). SKIPS the week of the monthly Work Management Meeting
(the last Tuesday) — that week the monthly runs instead. Deterministic; launchd Mondays 15:00.

Run:  python3 scripts/weekly-meeting-prep.py            # gated (only the day before a weekly Tue)
      python3 scripts/weekly-meeting-prep.py --force    # test now
"""
import os, sys, json, re, datetime, urllib.request, subprocess
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)

# Lizi 10/20: agendas in plain English — no Exobot jargon. Short lines, simple words, no symbol shorthand
# (no arrows, warning emoji or bullets standing in for words), acronyms spelled out.
PLAIN_ENGLISH_RULE = "Lizi 10/20: agendas in plain English — no Exobot jargon."

WS = os.path.expanduser("~/.openclaw/workspace")
K = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": K, "Authorization": "Bearer " + K}
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
JON = "1501632195163590739"
FORCE = "--force" in sys.argv
ATTENDEES = [("Steve Norsworthy", "snorsworthy@exosaero.com"), ("Phil Eaton", "peaton@exosaero.com"),
             ("John Quinn", "jquinn@exosaero.com"), ("Lizi Quinn", "lquinn@exosaero.com")]


def is_last_tuesday(d):
    return d.weekday() == 1 and (d + datetime.timedelta(days=7)).month != d.month


def is_weekly_prep_day(d):
    nxt = d + datetime.timedelta(days=1)
    return nxt.weekday() == 1 and not is_last_tuesday(nxt)   # Monday, and tomorrow's Tue isn't the monthly


def page(path):
    out, off = [], 0
    while True:
        r = urllib.request.Request(f"{SB}{path}&limit=1000&offset={off}", headers=H)
        pg = json.load(urllib.request.urlopen(r, timeout=30))
        out += pg
        if len(pg) < 1000:
            return out
        off += 1000


def build_agenda(meeting_day):
    # Only ACTIONABLE work counts toward a person's line. Done/Cancelled/Held/Queued are not
    # open action items — counting them made John's line read "597 open" when ~40 were dead states.
    DEAD = ("done", "cancelled", "canceled", "held", "queued")
    def _is_subtask(t):
        return any(str(x).lower().startswith("parent:") for x in (t.get("tags") or []))
    tasks = [t for t in page("tasks?select=id,title,due_date,state,owner,assigned_email,priority,category,tags&order=id")
             if (t.get("state") or "").lower() not in DEAD and t.get("source") != "mc-board-legacy"
             and not _is_subtask(t)]
    today = datetime.date.today()
    soon = today + datetime.timedelta(days=10)
    lines = [f"Exos Weekly Team Meeting: {meeting_day:%A, %B %-d}, 10:00 am Central",
             "Attendees: Steve, Phil, John, Lizi",
             "",
             "OPEN TASKS FOR EACH PERSON",
             "(Shows tasks that are due in the next 10 days or are high priority.)"]
    for name, email in ATTENDEES:
        mine = [t for t in tasks if (t.get("assigned_email") or "").lower() == email
                or (t.get("owner") or "").lower() in (name.lower(), name.split()[0].lower())]
        def due(t):
            try: return datetime.date.fromisoformat((t.get("due_date") or "")[:10])
            except Exception: return None
        hot = [t for t in mine if (due(t) and due(t) <= soon) or (t.get("priority") or 0) >= 80]
        hot.sort(key=lambda t: (due(t) or datetime.date(2099, 1, 1)))
        import re as _re
        ready = [t for t in mine if _re.search(r'\[READY|SUBMIT-READY|Ready to send|\bDRAFT\b|REVIEW V|for review', t.get("title") or "", _re.I)]
        rtag = f" {len(ready)} {'is' if len(ready) == 1 else 'are'} ready for you to review or send." if ready else ""
        lines.append(f"\n{name}: {len(mine)} open tasks. {len(hot)} due soon or high priority.{rtag}")
        for t in hot[:5]:
            d = due(t)
            flag = f" (LATE, was due {d:%b %-d})" if d and d < today else (f" (due {d:%b %-d})" if d else "")
            lines.append(f"    - #{t['id']} {(t.get('title') or '')[:60]}{flag}")
    def due2(t):
        try: return datetime.date.fromisoformat((t.get("due_date") or "")[:10])
        except Exception: return None

    # ---- Solicitations, pursuits & funding actions (trailing 7 days) ----
    # New solicitations submitted, opportunity pursuits, and major funding/contract actions.
    # Sourced from the opportunities board; "new this week" = most recent date stamped in the item.
    def clean(s, n=74):
        return re.sub(r"\s+", " ", (s or "")).strip()[:n]
    try:
        opps = json.load(open(os.path.join(WS, "mission-control", "data", "opportunities.json")))
        opps = opps if isinstance(opps, list) else opps.get("opportunities", [])
    except Exception:
        opps = []
    cutoff = meeting_day - datetime.timedelta(days=7)
    dre = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
    fund = re.compile(r"\b(WON|AWARD|AWARDED|CONTRACT|OBLIGAT|FUNDED|SUBMITTED|SELECTED)\b", re.I)
    recent = []
    for o in opps:
        blob = f"{o.get('status','')} {o.get('description','')} {o.get('next_action','')}"
        ds = []
        for y, m, d in dre.findall(blob):
            try: ds.append(datetime.date(int(y), int(m), int(d)))
            except Exception: pass
        last = max(ds) if ds else None
        if last and cutoff <= last <= meeting_day:
            recent.append((last, o, bool(fund.search(blob))))
    recent.sort(key=lambda x: x[0], reverse=True)
    lines.append("\nNEW FUNDING OPPORTUNITIES, BIDS AND AWARDS (last 7 days)")
    if recent:
        for dt, o, funding in recent[:10]:
            tag = "Funding or contract news: " if funding else ""
            lines.append(f"    - {tag}{clean(o.get('title'))} ({dt:%b %-d})")
    else:
        lines.append("    - Nothing new this week.")

    # ---- BLK3-to-Flight & HVRR build — per-employee task review ----
    # What each person owns to get BLK3 to flight and the HVRR build completed.
    # Detailed critical path lives in the ERP Schedule/Gantt; this is the owner roll-up.
    from collections import defaultdict
    def program_block(title, category):
        rows = [t for t in tasks if (t.get("category") or "") == category]
        lines.append(f"\n{title.upper()}: WHO OWNS WHAT ({len(rows)} open tasks)")
        if not rows:
            lines.append("    - No tasks are listed for this yet. Add owners and dates in the Mission Control schedule.")
            return
        g = defaultdict(list)
        for t in rows:
            g[(t.get("owner") or t.get("assigned_email") or "Unassigned")].append(t)
        for who in sorted(g, key=lambda k: -len(g[k])):
            lines.append(f"  {who} ({len(g[who])} open):")
            for t in sorted(g[who], key=lambda t: (due2(t) or datetime.date(2099, 1, 1)))[:6]:
                d = due2(t)
                flag = f" (LATE, was due {d:%b %-d})" if d and d < today else (f" (due {d:%b %-d})" if d else "")
                lines.append(f"    - #{t['id']} {(t.get('title') or '')[:56]}{flag}")
    program_block("BLK3 to first flight", "Blk3 Flight")
    program_block("HVRR build", "EXOS HVRR RDRE")
    try:
        dec = json.load(open(os.path.join(WS, "mission-control", "data", "decisions.json")))
        dec = dec if isinstance(dec, list) else dec.get("decisions", [])
        opend = [d for d in dec if (d.get("status") or "open") == "open"]
        lines.append(f"\nDecisions still waiting for an answer: {len(opend)}")
    except Exception:
        pass
    # scripted review items (standing, from agenda-review-items.json)
    try:
        ri = json.load(open(os.path.join(WS, "mission-control", "data", "agenda-review-items.json"))).get("review_items", [])
        if ri:
            lines.append("\nSTANDING ITEMS TO REVIEW")
            for it in ri:
                who = f" (owner: {it['owner']})" if it.get("owner") else ""
                lines.append(f"  - {it.get('title','')}{who}")
                for s in it.get("script", []):
                    lines.append(f"      - {s}")
    except Exception:
        pass
    return "\n".join(lines)


def main():
    today = datetime.date.today()
    if not (FORCE or is_weekly_prep_day(today)):
        print(f"{today} is not the day before a weekly Tuesday (or it's the monthly week) — skipping."); return
    meeting_day = today + datetime.timedelta(days=1)
    agenda = build_agenda(meeting_day)
    try:  # Lizi 10/20: every task ref on an agenda carries its live MC status
        sys.path.insert(0, os.path.join(WS, "scripts")); import agenda_task_status
        agenda = agenda_task_status.annotate_text(agenda)
    except Exception as e:
        print("agenda status stamp failed:", e)
    # email to Jon (organizer) the day before
    body = (f"Hello Jon,\n\nTomorrow ({meeting_day:%A, %B %-d}) is the weekly team meeting at 10:00 am Central. "
            f"Here is the draft agenda. The status in brackets after each task number comes from Mission Control.\n\n{agenda}\n\n"
            f"Reply with any changes and I will update it.\n\nExo")
    from email.message import EmailMessage
    m = EmailMessage(); m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = "jquinn@exosaero.com"
    m["Subject"] = f"Tomorrow: Weekly Team Meeting agenda ({meeting_day:%b %d})"; m.set_content(body)
    try:
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", "jquinn@exosaero.com"],
                       input=m.as_bytes(), check=True, timeout=60)
    except Exception as e:
        print("email failed:", e)
    # also email the agenda to Lizi (attendee) the day before — requested 2026-08-18
    lbody = (f"Hello Lizi,\n\nTomorrow ({meeting_day:%A, %B %-d}) is the weekly team meeting at 10:00 am Central. "
             f"Here is the agenda. The status in brackets after each task number comes from Mission Control.\n\n{agenda}\n\nExo")
    lm = EmailMessage(); lm["From"] = "Exo <jquinnexo@pm.me>"; lm["To"] = "lquinn@exosaero.com"
    lm["Subject"] = f"Tomorrow: Weekly Team Meeting agenda ({meeting_day:%b %d})"; lm.set_content(lbody)
    try:
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", "lquinn@exosaero.com"],
                       input=lm.as_bytes(), check=True, timeout=60)
    except Exception as e:
        print("lizi email failed:", e)
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m",
                        f"📅 **Weekly Team Meeting tomorrow ({meeting_day:%a %b %-d}), 10:00 am Central**\nThe agenda was emailed. Attendees: Steve, Phil, John, Lizi."],
                       timeout=60, capture_output=True)
    except Exception:
        pass
    print(f"weekly agenda prepped for {meeting_day}.")
    if FORCE:
        print("\n" + agenda)


if __name__ == "__main__":
    main()
