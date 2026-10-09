#!/usr/bin/env python3
"""decisions-discord-feed.py — mirror Jon's MC Decisions into a dedicated Discord channel.

Jon 2026-10-03: "create a decisions channel for me in discord where I can see all my decisions as
they pop up in one place." Decisions stay the system of record (MC); this is a read-only feed.

Every run (launchd com.exos.decisions-discord-feed, every 2 min):
  - NEW open decision for Jon (assignedTo jquinn@ / empty, not a standing rule)  -> post 🔴❓ card
  - a previously posted decision that is no longer open (answered/delegated/cancelled) -> post 🟢✅ line
Target channel lives in config/decisions-feed.json {"target": "channel:<id>"}. With no target set it
records nothing and exits, so cards aren't marked as posted before the channel exists.
Delivery goes through deliver.py (durable spool + sweeper retry).
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deliver import deliver

WS = "/Users/exomac/.openclaw/workspace"
DECS = os.path.join(WS, "mission-control", "data", "decisions.json")
CFG = os.path.join(WS, "config", "decisions-feed.json")
STATE = os.path.join(WS, "logs", "decisions-discord-feed-state.json")
MC = "https://mc.exosaero.space/decisions.html"
JON = {"", "jquinn@exosaero.com", "jquinnexo@pm.me", "jon", "john quinn", "jquinn"}
DRY = "--dry-run" in sys.argv


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def for_jon(d):
    return str(d.get("assignedTo") or "").strip().lower() in JON and not d.get("standing")


def clip(s, n):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def is_high(p):
    # priority is either a label ("high") or a 0-100 score (80 = high) depending on the producer
    if isinstance(p, (int, float)) and not isinstance(p, bool):
        return p >= 80
    return str(p or "").strip().lower() in ("high", "urgent", "critical")


def opt_text(o):
    if isinstance(o, dict):
        return str(o.get("label") or o.get("text") or o.get("value") or o.get("title") or "")
    return str(o or "")


def card(d):
    flag = " · ⚠️ high priority" if is_high(d.get("priority")) else ""
    opts = " / ".join(t for t in map(opt_text, d.get("options") or []) if t)
    return (f"🔴 ❓ **{d['id']}** · {clip(d.get('title'), 180)}{flag}\n"
            f"{clip(d.get('question'), 400)}\n"
            + (f"Options: {clip(opts, 200)}\n" if opts else "")
            + f"Source: {d.get('source') or 'MC'} · Answer in MC: <{MC}>")


def selftest():
    # replays 2026-10-09 failures: int priority score, dict options, null created
    m = card({"id": "D1", "priority": 80, "options": [{"label": "Yes"}, "No"], "title": None, "question": 5})
    assert "high priority" in m and "Options: Yes / No" in m, m
    assert "high priority" not in card({"id": "D2", "priority": 55, "options": None})
    assert "high priority" in card({"id": "D3", "priority": "Urgent"})
    sorted([{"created": None}, {"created": "2026"}], key=lambda x: str(x.get("created") or ""))
    print("selftest ok")


def main():
    target = load(CFG, {}).get("target")
    if not target:
        print("no target configured (config/decisions-feed.json) — skipping")
        return
    decs = {d["id"]: d for d in load(DECS, []) if d.get("id")}
    st = load(STATE, {"posted": {}})
    posted = st["posted"]
    changed = False

    for d in sorted(decs.values(), key=lambda x: str(x.get("created") or "")):
        if d.get("status") == "open" and for_jon(d) and d["id"] not in posted:
            msg = card(d)
            if DRY:
                print("[dry] NEW", msg, "\n")
            else:
                deliver(msg, target=target, source="decisions-feed")
            posted[d["id"]] = "open"
            changed = True

    for did, s in list(posted.items()):
        if s != "open":
            continue
        d = decs.get(did)
        status = (d or {}).get("status", "removed")
        if status == "open":
            continue
        ans = clip((d or {}).get("answer") or status, 120)
        note = clip((d or {}).get("note"), 160)
        msg = (f"🟢 ✅ **{did}** resolved ({status}) · {clip((d or {}).get('title'), 120)}\n"
               f"Answer: {ans}" + (f" · Note: {note}" if note else ""))
        if DRY:
            print("[dry] DONE", msg, "\n")
        else:
            deliver(msg, target=target, source="decisions-feed")
        posted[did] = status
        changed = True

    if changed and not DRY:
        os.makedirs(os.path.dirname(STATE), exist_ok=True)
        json.dump(st, open(STATE, "w"), indent=1)


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
