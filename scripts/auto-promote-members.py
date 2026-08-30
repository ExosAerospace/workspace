#!/usr/bin/env python3
"""Auto-promote member employees to manager after 30 days (Jon 2026-08-30).

Every Exos employee advances to manager — they all manage exobots, directly or indirectly.
Scope guards: only role=='member' AND an @exosaero.com email (employees), and NOT on the
exclude list. Early adopters (students/external, @utdallas.edu etc.) are never promoted.
Runs daily via launchd. Pass --dry-run to preview without changing anything.
"""
import json, sys, os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
WS = "/Users/exomac/.openclaw/workspace"
USERS = os.path.join(WS, "mission-control/users.json")
EXCLUDE_FILE = os.path.join(WS, "mission-control/data/auto-promote-exclude.json")
DAYS = 30
JON = "1501632195163590739"


def load_exclude():
    try:
        return set(e.lower() for e in json.load(open(EXCLUDE_FILE)))
    except Exception:
        return set()


def main():
    dry = "--dry-run" in sys.argv
    u = json.load(open(USERS))
    users = u if isinstance(u, list) else u.get("users", [])
    exclude = load_exclude()
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    promoted = []
    for x in users:
        if x.get("role") != "member":
            continue
        em = (x.get("email") or "").lower()
        if not em.endswith("@exosaero.com"):   # employees only
            continue
        if em in exclude:
            continue
        ca = x.get("created_at")
        created = None
        if ca:
            try:
                created = datetime.fromisoformat(str(ca).replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            except Exception:
                created = None
        # promote if no created_at (legacy) or 30+ days old
        if created is None or created <= cutoff:
            promoted.append((x.get("name") or em, em, ca))
            if not dry:
                x["role"] = "manager"

    if promoted and not dry:
        tmp = USERS + ".tmp"
        json.dump(u, open(tmp, "w"), indent=2)
        os.replace(tmp, USERS)

    if promoted:
        names = ", ".join(n for n, e, c in promoted)
        tag = "🔎 [dry-run] WOULD auto-promote to manager" if dry else "⬆️ Auto-promoted member(s) to manager"
        msg = f"{tag} (member employee 30+ days): {names}"
        print(msg)
        for n, e, c in promoted:
            print(f"   {n} <{e}>  created={c}")
        if not dry:
            try:
                from deliver import deliver
                deliver(msg + "\n(All Exos employees advance to manager — they manage exobots.)",
                        target=f"user:{JON}", source="auto-promote-members")
            except Exception as ex:
                print("notify failed:", ex)
    else:
        print("no member employees due for promotion")


if __name__ == "__main__":
    main()
