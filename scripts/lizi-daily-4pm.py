#!/usr/bin/env python3
"""Lizi's 4 PM daily update (weekdays). Emails lquinn@ a ready-to-paste daily update for her open
weekly-target tasks (tag blk3-hvrr-weekly): today's notes on the target + referenced tasks, and her other
tasks touched today. Internal only. Lizi 10/12: "send my 4pm daily to my email"."""
import os, re, json, subprocess, urllib.request
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

K = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
H = {"apikey": K, "Authorization": "Bearer " + K}
TO = "lquinn@exosaero.com"


def get(q):
    return json.load(urllib.request.urlopen(urllib.request.Request(B + q, headers=H), timeout=30))


def main():
    now = datetime.now(timezone(timedelta(hours=-5)))  # CDT
    if now.weekday() >= 5:
        return
    day = now.strftime("%Y-%m-%d")
    start = (now.replace(hour=0, minute=0, second=0, microsecond=0)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    targets = [t for t in get("tasks?select=id,title,description,state,tags&assigned_email=eq.lquinn@exosaero.com"
                              "&tags=cs.%7Bblk3-hvrr-weekly%7D&state=neq.Done&state=neq.Cancelled")]
    out = [f"Hi Lizi,\n\nYour 4 PM update for {now.strftime('%a %b %-d')}. Paste the 'Update' lines into each target task "
           "(or reply in #lizi-channel-2 and Exo will post them).\n"]
    for t in targets:
        refs = sorted(set(re.findall(r"#(\d{3,5})", t.get("description") or "")) - {str(t["id"])})
        ids = [str(t["id"])] + refs
        notes = get("activities?select=subject,created_at,body&subject=in.(" +
                    ",".join(f"task:{i}" for i in ids) + f")&created_at=gte.{start}&order=created_at")
        notes = [n for n in notes if not (n.get("body") or "").startswith("[Update] State")]
        out.append(f"=== #{t['id']} {t['title']}")
        goals = [l.strip() for l in (t.get("description") or "").splitlines() if re.match(r"\s*\d+\.\s", l)]
        for g in goals:
            out.append("  Target: " + g[:220])
        if notes:
            out.append("  Today on " + ", ".join("#" + i for i in ids) + ":")
            for n in notes:
                out.append(f"   - {n['subject'].replace('task:', '#')}: " + (n.get("body") or "").splitlines()[0][:200])
            out.append(f"  Update ({day}): progress logged today on " +
                       ", ".join(sorted({n['subject'].replace('task:', '#') for n in notes})) + ". [edit/confirm]")
        else:
            out.append(f"  Update ({day}): no change today. [add a line if you worked on it]")
        out.append("")
    touched = get("tasks?select=id,title,state&assigned_email=eq.lquinn@exosaero.com"
                  f"&updated_at=gte.{start}&order=updated_at.desc&limit=25")
    if touched:
        out.append("Your other tasks updated today:")
        out += [f" - #{t['id']} [{t['state']}] {t['title'][:100]}" for t in touched]
        out.append("")
    if not targets:
        out.append("(No open weekly-target task found for you this week.)\n")
    if now.weekday() == 4:
        out.append("Friday: scorecard (committed vs done) is due at 3 PM. Exo drafts it Friday morning.\n")
    out.append("- Exo")
    m = EmailMessage()
    m["From"] = "Exo <jquinnexo@pm.me>"; m["To"] = TO
    m["Subject"] = f"Your 4 PM daily update ({now.strftime('%a %-m/%-d')})"
    m["X-Exo-No-Task"] = "1"
    m.set_content("\n".join(out))
    subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", TO], input=m.as_bytes(), check=True, timeout=60)
    print(day, "sent", len(targets), "targets")


if __name__ == "__main__":
    main()
