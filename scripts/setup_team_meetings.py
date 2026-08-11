#!/usr/bin/env python3
"""
Generate the recurring team-meeting calendar invites (.ics) and email them to Jon to send from
Outlook. Weekly team sync every Tuesday 10:00 CT (Steve, Phil, John, Lizi); the Monthly Work
Management Meeting moves to the LAST Tuesday 10:00-11:00 CT and REPLACES the weekly that week
(the weekly carries EXDATEs for every last-Tuesday so there's no double-booking).
"""
import os, datetime, calendar, subprocess, smtplib
from email.message import EmailMessage

OUT = os.path.expanduser("~/.openclaw/workspace/meetings")
os.makedirs(OUT, exist_ok=True)
ATTENDEES = [("John Quinn", "jquinn@exosaero.com"), ("Steve Norsworthy", "snorsworthy@exosaero.com"),
             ("Phil Eaton", "peaton@exosaero.com"), ("Lizi Quinn", "lquinn@exosaero.com"),
             ("Mike Talley", "mtalley@exosaero.com"), ("Neil Milburn", "nmilburn@exosaero.com"),
             ("Victor Castilleja", "vcastilleja@exosaero.com"), ("Kyle Ballard", "kballard@exosaero.com")]
# Weekly is virtual (Teams); Monthly is on-site at Greenville.
LOC_WEEKLY = "Microsoft Teams (virtual)"
LOC_MONTHLY = "Exos Aerospace, 299 FM 1903, Greenville, TX 75402 (on-site)"
TODAY = datetime.date(2026, 7, 30)  # generation date (stamped, not runtime-derived)

VTIMEZONE = """BEGIN:VTIMEZONE
TZID:America/Chicago
BEGIN:DAYLIGHT
TZOFFSETFROM:-0600
TZOFFSETTO:-0500
TZNAME:CDT
DTSTART:19700308T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0500
TZOFFSETTO:-0600
TZNAME:CST
DTSTART:19701101T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE"""


def last_tuesday(y, m):
    cal = calendar.monthcalendar(y, m)
    for week in reversed(cal):
        if week[calendar.TUESDAY]:
            return datetime.date(y, m, week[calendar.TUESDAY])


def next_tuesday(d):
    return d + datetime.timedelta(days=(1 - d.weekday()) % 7 or 7) if d.weekday() != 1 else d


def last_tuesdays(start, months=18):
    out, y, m = [], start.year, start.month
    for _ in range(months):
        out.append(last_tuesday(y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def attendees_lines():
    lines = ["ORGANIZER;CN=John Quinn:mailto:jquinn@exosaero.com"]
    for cn, em in ATTENDEES:
        role = "CHAIR" if em == "jquinn@exosaero.com" else "REQ-PARTICIPANT"
        lines.append(f"ATTENDEE;CN={cn};ROLE={role};RSVP=TRUE:mailto:{em}")
    return "\n".join(lines)


def esc_text(s):
    # RFC 5545: escape backslash, semicolon, comma, and newlines in TEXT values.
    return (str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n"))


def fold_line(line):
    # RFC 5545 line folding: no content line may exceed 75 octets; continuation
    # lines begin with a single space. Strict parsers (new Outlook) reject long lines.
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    chunks, rest = [b[:75]], b[75:]
    while rest:
        chunks.append(b" " + rest[:74])
        rest = rest[74:]
    return b"\r\n".join(chunks).decode("utf-8")


def ics(uid, dtstart, dtend, rrule, summary, desc, exdates=None, location="Microsoft Teams"):
    stamp = TODAY.strftime("%Y%m%dT120000Z")
    ev = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Exos//Team Meetings//EN",
          "METHOD:REQUEST", "CALSCALE:GREGORIAN", VTIMEZONE, "BEGIN:VEVENT",
          f"UID:{uid}", f"DTSTAMP:{stamp}", attendees_lines(),
          f"DTSTART;TZID=America/Chicago:{dtstart}", f"DTEND;TZID=America/Chicago:{dtend}",
          f"RRULE:{rrule}"]
    if exdates:
        # one EXDATE line per date keeps Outlook happy
        for ex in exdates:
            ev.append(f"EXDATE;TZID=America/Chicago:{ex.strftime('%Y%m%d')}T100000")
    ev += [f"SUMMARY:{esc_text(summary)}", f"DESCRIPTION:{esc_text(desc)}", f"LOCATION:{esc_text(location)}",
           "STATUS:CONFIRMED", "SEQUENCE:0", "END:VEVENT", "END:VCALENDAR"]
    # flatten (attendees_lines() carries embedded newlines), fold every line, CRLF-join, trailing CRLF
    lines = []
    for part in ev:
        lines.extend(part.split("\n"))
    return "\r\n".join(fold_line(l) for l in lines) + "\r\n"


def main():
    first_tue = next_tuesday(TODAY)                    # 2026-08-04
    lasts = last_tuesdays(first_tue)                   # last-Tuesday of each month (monthly days)
    weekly = ics(
        f"exos-weekly-team-{first_tue:%Y%m%d}@exosaero.com",
        f"{first_tue:%Y%m%d}T100000", f"{first_tue:%Y%m%d}T104500",
        "FREQ=WEEKLY;BYDAY=TU",
        "Exos Weekly Team Meeting",
        "Weekly work-management sync (virtual / Teams). Skipped the week of the monthly Work Management Meeting (last Tuesday).",
        exdates=lasts, location=LOC_WEEKLY)
    first_monthly = lasts[0]                           # first last-Tuesday (2026-08-25)
    monthly = ics(
        f"exos-monthly-workmgmt-{first_monthly:%Y%m%d}@exosaero.com",
        f"{first_monthly:%Y%m%d}T100000", f"{first_monthly:%Y%m%d}T110000",
        "FREQ=MONTHLY;BYDAY=-1TU",
        "Exos Monthly Work Management Meeting",
        "Monthly Mission Control work-management review (ON-SITE at Greenville). Replaces the weekly sync this week. Agenda delivered the day before.",
        location=LOC_MONTHLY)
    wp = os.path.join(OUT, "Exos_Weekly_Team_Meeting.ics")
    mp = os.path.join(OUT, "Exos_Monthly_WorkMgmt_Meeting.ics")
    open(wp, "w").write(weekly)
    open(mp, "w").write(monthly)
    print(f"weekly:  {wp}  (first {first_tue:%a %b %d} 10:00 CT, exdates {len(lasts)})")
    print(f"monthly: {mp}  (first {first_monthly:%a %b %d} 10:00-11:00 CT, last Tuesday monthly)")

    # email both to Jon to open + send from Outlook
    m = EmailMessage()
    m["From"] = "Exo (Exos AI Assistant) <jquinnexo@pm.me>"
    m["To"] = "jquinn@exosaero.com"
    m["Subject"] = "Team meeting invites — Weekly (Tue 10am) + Monthly (last Tue) — open & send from Outlook"
    m.set_content(
        "Hello Jon,\n\n"
        "Two recurring calendar invites are attached, ready to open in Outlook and send to the team:\n\n"
        f"1) Weekly Team Meeting (VIRTUAL / Teams) — every Tuesday 10:00-10:45 CT, starting {first_tue:%A, %b %d}.\n"
        "   Attendees: John, Steve, Phil, Lizi, Mike Talley, Neil, Victor, Kyle. It automatically SKIPS the\n"
        "   last Tuesday of each month (that week is the monthly meeting instead).\n\n"
        f"2) Monthly Work Management Meeting (ON-SITE, Greenville) — LAST Tuesday, 10:00-11:00 CT, starting {first_monthly:%A, %b %d}.\n"
        "   Same attendees, in person. This replaces the weekly that week.\n\n"
        "To send: open each .ics in Outlook (double-click the attachment), confirm the attendees, and hit Send.\n"
        "If the inline preview says \"Couldn't import,\" SAVE the .ics to your desktop first, then double-click the\n"
        "saved file (or in Outlook use File > Open & Export > Open Calendar). These files are now RFC-corrected.\n\n"
        "If you'd rather just set them up by hand (60 seconds), the exact details are:\n"
        f"  - Weekly: New Teams Meeting, Tuesdays 10:00-10:45 AM CT, starts {first_tue:%b %d}, recurrence Weekly on Tuesday.\n"
        f"  - Monthly: New Meeting (on-site, 299 FM 1903 Greenville), 10:00-11:00 AM CT, starts {first_monthly:%b %d},\n"
        "    recurrence Monthly on the LAST Tuesday. Invite: John, Steve, Phil, Lizi, Mike, Neil, Victor, Kyle.\n\n"
        "— Exo")
    for p in (wp, mp):
        with open(p, "rb") as f:
            m.add_attachment(f.read(), maintype="text", subtype="calendar", filename=os.path.basename(p))
    try:
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", "jquinn@exosaero.com"],
                       input=m.as_bytes(), check=True, timeout=60)
        print("emailed both invites to jquinn@exosaero.com")
    except Exception as e:
        print("email failed:", e)


if __name__ == "__main__":
    main()
