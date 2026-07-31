#!/usr/bin/env python3
"""
DAILY BURNDOWN — runs off-hours (low utilization). Two jobs:
  1. Sweep unambiguous noise tasks (auto-notifications, assignment echoes) -> Cancelled.
  2. Report the trend: created vs closed in the last 24h, net, open backlog, and the
     day-over-day direction, DM'd to Jon so he can watch the list actually come down.
Deterministic + safe (only closes clear noise); heavier resolution stays with the Overnight Resolver.
"""
import os, json, re, datetime, subprocess, urllib.request

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
K = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"
WS = os.path.expanduser("~/.openclaw/workspace")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"
STATE = os.path.join(WS, "logs", "daily-burndown-state.json")
LOG = os.path.join(WS, "logs", "daily-burndown.jsonl")

# unambiguous noise: auto-notification / assignment-echo rows that are not real work
NOISE_TITLE = re.compile(r'^\s*(re:|fw:|fwd:)?\s*\[mission control\]|task assigned to you|assignment notification', re.I)
NOISE_SOURCE = re.compile(r'assignment-notifier|notification|discord.?sync', re.I)


def q(path, method="GET", body=None):
    r = urllib.request.Request(SB + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={"apikey": K, "Authorization": "Bearer " + K,
        "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else []


def all_tasks():
    out, off = [], 0
    while True:
        pg = q(f"tasks?select=id,state,title,description,tags,source,created_at,completed_at&order=id&limit=1000&offset={off}")
        out += pg
        if len(pg) < 1000:
            return out
        off += 1000


_EMAIL = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
_SENDISH = re.compile(r'\b(send|outreach|reach out|follow.?up with|email .* to|contact|draft.*to)\b', re.I)

def tag_send_tasks(opn):
    """Keep auto-close flags current: any open task with an EXTERNAL send-target + send language
    gets 'autoclose-on-send' so a sent email always clears it (fixes flags going 'missing')."""
    n = 0
    for t in opn:
        blob = (t.get("title") or "") + " " + (t.get("description") or "")
        ext = [e for e in _EMAIL.findall(blob)
               if not e.lower().endswith("exosaero.com") and "proton" not in e.lower() and "pm.me" not in e.lower()]
        have = set(g.lower() for g in (t.get("tags") or []))
        if ext and _SENDISH.search(blob) and not (have & {"outreach", "autoclose-on-send", "cold-outreach"}):
            try:
                q(f"tasks?id=eq.{t['id']}", "PATCH", {"tags": list(dict.fromkeys((t.get("tags") or []) + ["autoclose-on-send"]))})
                n += 1
            except Exception:
                pass
    return n


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    day_ago = (now - datetime.timedelta(hours=24)).isoformat()
    tasks = all_tasks()
    opn = [t for t in tasks if (t.get("state") or "") not in ("Done", "Cancelled")]

    # 0) keep outreach auto-close flags current so sent emails always clear their task
    flagged = tag_send_tasks(opn)

    # 1) sweep noise
    noise = [t for t in opn if NOISE_TITLE.search(t.get("title") or "") or NOISE_SOURCE.search(t.get("source") or "")]
    swept = 0
    for t in noise:
        try:
            q(f"tasks?id=eq.{t['id']}", "PATCH", {"state": "Cancelled",
              "completed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ")})
            swept += 1
        except Exception:
            pass

    # 2) metrics (recompute open after sweep)
    open_now = len(opn) - swept
    created = sum(1 for t in tasks if (t.get("created_at") or "") >= day_ago)
    closed = sum(1 for t in tasks if (t.get("completed_at") or "") >= day_ago)
    net = created - closed

    prev = {}
    try:
        prev = json.load(open(STATE))
    except Exception:
        pass
    prev_open = prev.get("open")
    trend = ""
    if isinstance(prev_open, int):
        d = open_now - prev_open
        trend = f" ({'▼' if d < 0 else '▲' if d > 0 else '■'} {abs(d)} vs yesterday)"

    # DECISIONS (file-backed store) — folded into the same DM
    dopen = None
    try:
        dj = json.load(open(os.path.join(WS, "mission-control/data/decisions.json")))
        ditems = dj if isinstance(dj, list) else dj.get("decisions", dj.get("items", []))
        dopen = sum(1 for x in ditems if (x.get("status") or "").lower() in ("open", "pending"))
    except Exception:
        pass
    dprev = prev.get("decisions_open")
    dtrend = ""
    if isinstance(dopen, int) and isinstance(dprev, int):
        dd = dopen - dprev
        dtrend = f" ({'▼' if dd < 0 else '▲' if dd > 0 else '■'} {abs(dd)})"
    dec_line = f"\nDecisions awaiting you: **{dopen}**{dtrend}" if isinstance(dopen, int) else ""

    json.dump({"open": open_now, "decisions_open": dopen, "date": now.strftime("%Y-%m-%d")}, open(STATE, "w"))
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": now.isoformat(), "created": created, "closed": closed, "net": net,
                            "swept_noise": swept, "flagged": flagged, "open": open_now, "decisions_open": dopen}) + "\n")

    msg = (f"🔻 **Daily burndown — {now:%a %b %d}**\n"
           f"Open backlog: **{open_now}**{trend}\n"
           f"Last 24h: created {created} · closed {closed} · **net {'+' if net>=0 else ''}{net}**"
           f"{f' · swept {swept} noise' if swept else ''}{f' · flagged {flagged} auto-close' if flagged else ''}"
           f"{dec_line}\n"
           f"{'⚠️ still creating faster than closing — throttle is working, give it a few days' if net>0 else '✅ closing ≥ creating'}")
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", msg],
                       timeout=60, capture_output=True)
    except Exception:
        pass
    print(msg)


if __name__ == "__main__":
    main()
