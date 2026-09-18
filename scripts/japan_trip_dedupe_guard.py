#!/usr/bin/env python3
"""Japan-trip dedupe guard — auto-collapse NEW Japan trip/meeting-arrangement tasks into the
single canonical trip hub (#2684 "Japan trip (Oct 10–18) — MASTER PLAN").

Why: John's Oct Japan trip kept spawning duplicate trip/meeting tasks (flights, hotels, "arrange
the meeting during John san's visit", investor 1:1 pre-booking, HOSPO agenda) across Lizi/Toshi/
John, blowing up the board. On 2026-09-18 those were consolidated into #2684 by hand; this guard
keeps it clean going forward.

SCOPE — deliberately narrow. A task collapses ONLY if ALL hold:
  * it is active (not Done/Cancelled/…)
  * it is NOT the hub itself, the Innovation Dojo canonical (#2928), or a protected id
  * it does NOT carry the 'keep-separate' or 'consolidated' escape tag
  * title/description mentions a JAPAN token (japan/tokyo/hokkaido/hospo/obihiro/"john san")
  * title/description mentions a TRIP/MEETING-ARRANGEMENT token (trip, itinerary, flight, hotel,
    "tokyo schedule", 1:1, "pre-book", "arrange the meeting", "meeting with investor",
    "during john san", "visiting to/in japan", "meeting agenda … visit")
  * title does NOT mention a DISTINCT-THREAD token (dojo/idj/structure/funding/seed/itz/trade
    zone/tank/loi/payload/part 450/rfi/proposal/capstone/narrative/playbook/formation/
    ip license/bailment/outreach/"send NN"/market outreach) — those are real separate deliverables,
    never trip logistics.

Anything substantive that legitimately should stay separate: add the tag 'keep-separate'.

Collapse = set the dup to Cancelled with a pointer note + post a task_note activity on both the dup
and the hub (so it's visible on the board). Fully reversible (reopen the cancelled task). Snapshotted
to mission-control/data/. Dry-run by default; pass --apply to write.
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
WS = "/Users/exomac/.openclaw/workspace"
LOG = os.path.join(WS, "logs", "japan-trip-dedupe.log")

HUB = 2684                      # canonical Japan trip MASTER PLAN
PROTECTED = {2684, 2928}        # never collapse the hub or the Innovation Dojo canonical
DONE = {"Done", "Completed", "Closed", "Archived", "Cancelled"}
APPLY = "--apply" in sys.argv

JAPAN = re.compile(r"\b(japan|tokyo|hokkaido|hospo|obihiro|john[\s-]san)\b", re.I)
TRIP = re.compile(
    r"\b(trip|itinerary|flight|hotel|1:1|pre-?book|booking)\b"
    r"|tokyo schedule|arrange the meeting|meeting with investor|during john[\s-]san"
    r"|visiting (?:to|in) japan|visit(?:ing)? .* japan|meeting agenda.*visit", re.I)
# distinct, substantive Japan threads that must NEVER be swept into the trip hub
EXCLUDE = re.compile(
    r"\b(dojo|idj|structure|funding|seed|itz|trade zone|tank|loi|payload|part 450|rfi|proposal"
    r"|capstone|narrative|playbook|formation|ip license|bailment|outreach|market outreach"
    r"|send \d+|program structure|spaceplane)\b", re.I)


def log(m):
    try:
        with open(LOG, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {m}\n")
    except Exception:
        pass


def qall():
    out, off = [], 0
    while True:
        req = urllib.request.Request(
            f"{SB}/tasks?select=id,title,state,owner,description,tags,created_at&order=id&offset={off}&limit=1000",
            headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
        r = json.load(urllib.request.urlopen(req, timeout=60)); out += r
        if len(r) < 1000:
            return out
        off += 1000


def patch(tid, fields):
    req = urllib.request.Request(f"{SB}/tasks?id=eq.{tid}", data=json.dumps(fields).encode(),
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "Prefer": "return=minimal"}, method="PATCH")
    urllib.request.urlopen(req, timeout=30).read()


def note(tid, body):
    req = urllib.request.Request(f"{SB}/activities", method="POST",
        data=json.dumps({"type": "task_note", "subject": f"task:{tid}", "body": body,
                         "owner": "Exo", "status": "completed"}).encode(),
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
                 "Prefer": "return=minimal"})
    urllib.request.urlopen(req, timeout=30).read()


def matches(t):
    if t["id"] in PROTECTED:
        return False
    if (t.get("state") or "") in DONE:
        return False
    tags = [str(x).lower() for x in (t.get("tags") or [])]
    if "keep-separate" in tags or "consolidated" in tags:
        return False
    title = t.get("title") or ""
    if EXCLUDE.search(title):
        return False
    # Anchor BOTH signals to the TITLE. Descriptions mention Japan/Tokyo/"trip" tangentially
    # (e.g. an ERAU task noting Japan prospects, or a NY Up/Link hotel task noting John departs
    # for Tokyo), which caused false positives. Real trip tasks always carry both in the title.
    return bool(JAPAN.search(title) and TRIP.search(title))


def main():
    tasks = qall()
    hub = next((x for x in tasks if x["id"] == HUB), None)
    if not hub or (hub.get("state") or "") in DONE:
        log(f"hub #{HUB} missing or closed — standing down (no collapse without a live hub)")
        print(f"Hub #{HUB} missing or closed; nothing done.")
        return
    hits = [t for t in tasks if matches(t)]
    print(f"Japan trip/meeting dups to collapse into #{HUB}: {len(hits)}")
    for t in hits:
        print(f"  cancel #{t['id']} [{t['state']}] {(t.get('title') or '')[:60]!r} (own {t.get('owner')})")
    if not hits:
        return
    if not APPLY:
        print("\nDRY RUN — add --apply to collapse.")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    now = datetime.now(timezone.utc).isoformat()
    snap = [{"id": t["id"], "prev_state": t["state"], "title": t.get("title"),
             "owner": t.get("owner"), "hub": HUB} for t in hits]
    json.dump(snap, open(os.path.join(WS, "mission-control/data",
              f"japan-trip-dedupe-snapshot-{stamp}.json"), "w"), indent=2)
    for t in hits:
        nd = (t.get("description") or "") + (
            f"\n\n[JAPAN-TRIP GUARD {now[:10]}] Auto-collapsed into #{HUB} "
            f"(Japan trip MASTER PLAN) as a duplicate trip/meeting task. Reversible — reopen if this "
            f"is genuinely separate, and add the tag 'keep-separate' so the guard leaves it alone.")
        patch(t["id"], {"state": "Cancelled", "description": nd, "updated_at": now})
        note(t["id"], f"🔀 Exo (auto): collapsed into #{HUB} (Japan trip MASTER PLAN). "
                      f"Tag 'keep-separate' to exempt.")
        note(HUB, f"↩️ Auto-folded duplicate trip task #{t['id']} — “{(t.get('title') or '')[:80]}”.")
        log(f"collapsed #{t['id']} -> #{HUB} ({(t.get('title') or '')[:60]})")
    print(f"Collapsed {len(hits)} into #{HUB}; snapshot japan-trip-dedupe-snapshot-{stamp}.json")


if __name__ == "__main__":
    main()
