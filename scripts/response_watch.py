#!/usr/bin/env python3
"""
Response Watch — catches PICKUP MISSES (requests that sat unanswered) and measures real
first-response latency. Jon 2026-10-22: "How can we improve response times?" The ETA log showed
the work is fast (median 0.4x promised); the damage is requests nobody picked up (2-4.5h).

Every run (launchd com.exos.response-watch, every 120s, model-free):
  1. Reads recent messages in the EC guild text channels + Jon's DM via the Discord REST API.
  2. A "request" = a human message that is from Jon or @mentions the bot.
  3. First bot message after it in the same channel = the response; latency logged once to
     data/response-latency.jsonl (feeds weekly RSI §18).
  4. Unanswered > NUDGE_MIN: re-injects it into that channel's session via `openclaw agent`
     (non-blocking) so it gets picked up, and alerts #exomac-system. Once per request.

Run: python3 scripts/response_watch.py [--dry-run] [--selftest]
"""
import json, os, sys, subprocess, shutil, time, urllib.request
from datetime import datetime, timezone, timedelta

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
LAT_LOG = os.path.join(WS, "data", "response-latency.jsonl")
STATE = os.path.join(WS, "logs", "response-watch-state.json")
LOG = os.path.join(WS, "logs", "response-watch.log")
API = "https://discord.com/api/v10"
GUILD = "1501635980094996631"
JON = "1501632195163590739"
SYSTEM_CH = "1501636814849577050"  # #exomac-system
OPENCLAW = shutil.which("openclaw") or "/Users/exomac/.local/share/mise/shims/openclaw"

NUDGE_MIN = float(os.environ.get("RW_NUDGE_MIN", "10"))     # unanswered this long -> nudge
LOOKBACK_H = float(os.environ.get("RW_LOOKBACK_H", "6"))    # older requests are history, not nudged
TARGET_MIN = 5.0                                            # first-response target (RSI §18)


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def api(path, token, method="GET", body=None):
    req = urllib.request.Request(API + path, method=method,
                                 headers={"Authorization": "Bot " + token, "Content-Type": "application/json",
                                          "User-Agent": "ExosResponseWatch (exosaero.com, 1.0)"},
                                 data=json.dumps(body).encode() if body is not None else None)
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=20))
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < 2:
                time.sleep(float(json.loads(e.read() or b"{}").get("retry_after", 2)))
                continue
            raise


def ts(m):
    return datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))


def find_requests(msgs, bot_id, now):
    """msgs: Discord messages oldest->newest. Returns [(request_msg, first_reply_or_None)]."""
    out = []
    for i, m in enumerate(msgs):
        a = m.get("author", {})
        if a.get("bot"):
            continue
        mentioned = any(u.get("id") == bot_id for u in m.get("mentions", []))
        if not (a.get("id") == JON or mentioned):
            continue
        reply = next((r for r in msgs[i + 1:] if r.get("author", {}).get("id") == bot_id), None)
        out.append((m, reply))
    return out


def nudge(ch_id, m, dry):
    text = (m.get("content") or "(attachment)")[:600]
    body = (f"PICKUP MISS (response-watch): this request in this channel has had no reply for "
            f"{NUDGE_MIN:.0f}+ min — message {m['id']} at {m['timestamp'][:16]}Z from "
            f"{m['author'].get('username')}: \"{text}\". If it is still unanswered, acknowledge with an ETA "
            f"and answer it now via message(action=send) to channel:{ch_id}. If it was already handled or "
            f"needs no reply, do nothing.")
    if dry:
        log(f"DRY nudge {ch_id} {m['id']}")
        return
    subprocess.Popen([OPENCLAW, "agent", "--session-key", f"agent:main:discord:channel:{ch_id}",
                      "-m", body, "--timeout", "900"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def run(dry=False):
    token = json.load(open(SECRETS))["discord_token"]
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"logged": [], "nudged": []}
    logged, nudged = set(st.get("logged", [])), set(st.get("nudged", []))
    bot_id = api("/users/@me", token)["id"]
    chans = [(c["id"], c["name"]) for c in api(f"/guilds/{GUILD}/channels", token) if c.get("type") in (0, 5, 11)]
    try:
        chans.append((api("/users/@me/channels", token, "POST", {"recipient_id": JON})["id"], "jon-dm"))
    except Exception as e:
        log(f"dm lookup failed: {e}")
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=LOOKBACK_H)
    new_lat, misses = [], []
    for ch_id, name in chans:
        try:
            msgs = api(f"/channels/{ch_id}/messages?limit=50", token)
        except Exception as e:
            log(f"read {name} failed: {e}")
            continue
        msgs = sorted(msgs, key=ts)
        for m, reply in find_requests(msgs, bot_id, now):
            if ts(m) < cutoff:
                continue
            if reply is not None and m["id"] not in logged:
                lat = round((ts(reply) - ts(m)).total_seconds() / 60, 2)
                new_lat.append({"ts": m["timestamp"][:19], "channel": name, "msg": m["id"],
                                "latency_min": lat, "nudged": m["id"] in nudged})
                logged.add(m["id"])
            elif reply is None and (now - ts(m)).total_seconds() / 60 > NUDGE_MIN and m["id"] not in nudged:
                misses.append((ch_id, name, m))
        time.sleep(0.3)
    if not dry and new_lat:
        os.makedirs(os.path.dirname(LAT_LOG), exist_ok=True)
        with open(LAT_LOG, "a") as f:
            for r in new_lat:
                f.write(json.dumps(r) + "\n")
    for ch_id, name, m in misses:
        nudge(ch_id, m, dry)
        nudged.add(m["id"])
    if misses and not dry:
        lines = [f"⏱️ Pickup miss — {len(misses)} request(s) unanswered >{NUDGE_MIN:.0f} min, re-injected:"]
        lines += [f"- #{n}: {(m.get('content') or '(attachment)')[:80]}" for _, n, m in misses[:8]]
        try:
            api(f"/channels/{SYSTEM_CH}/messages", token, "POST", {"content": "\n".join(lines)[:1900]})
        except Exception as e:
            log(f"alert failed: {e}")
    if not dry:
        st = {"logged": sorted(logged)[-3000:], "nudged": sorted(nudged)[-3000:]}
        tmp = STATE + ".tmp"
        json.dump(st, open(tmp, "w"))
        os.replace(tmp, STATE)
    log(f"run: channels={len(chans)} logged+={len(new_lat)} misses={len(misses)}{' DRY' if dry else ''}")
    return new_lat, misses


def report_section(days=7):
    """Weekly RSI §18 — first-response latency vs target."""
    L = ["\n## 18. Response time (first reply to a request)"]
    if not os.path.exists(LAT_LOG):
        return L + ["- No latency data yet (response-watch started 2026-10-22)."]
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = [json.loads(l) for l in open(LAT_LOG) if l.strip()]
    rows = [r for r in rows if r["ts"] >= since]
    if not rows:
        return L + ["- No requests logged this week."]
    lat = sorted(r["latency_min"] for r in rows)
    p = lambda q: lat[min(len(lat) - 1, int(q * len(lat)))]
    within = sum(1 for x in lat if x <= TARGET_MIN)
    nudged = [r for r in rows if r.get("nudged")]
    pct = round(100 * within / len(lat))
    L.append(f"- {len(lat)} requests · median {p(0.5):.1f} min · p90 {p(0.9):.1f} min · "
             f"**{pct}% answered within {TARGET_MIN:.0f} min** (target ≥90%) · {len(nudged)} pickup misses (target 0)")
    if pct < 90 or nudged:
        worst = sorted(rows, key=lambda r: -r["latency_min"])[:5]
        L.append("- ⚠️ Below target. Slowest:")
        L += [f"  - {r['ts'][:16]} #{r['channel']} — {r['latency_min']:.0f} min{' (nudged)' if r.get('nudged') else ''}"
              for r in worst]
    return L


def selftest():
    bot, now = "B", datetime.now(timezone.utc)
    t = lambda mins: (now - timedelta(minutes=mins)).isoformat()
    msgs = [{"id": "1", "author": {"id": JON}, "timestamp": t(30), "mentions": []},
            {"id": "2", "author": {"id": bot, "bot": True}, "timestamp": t(28), "mentions": []},
            {"id": "3", "author": {"id": "X"}, "timestamp": t(20), "mentions": []},
            {"id": "4", "author": {"id": "X"}, "timestamp": t(15), "mentions": [{"id": bot}]}]
    r = find_requests(msgs, bot, now)
    assert [m["id"] for m, _ in r] == ["1", "4"], r
    assert r[0][1]["id"] == "2" and r[1][1] is None
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        lat, miss = run(dry="--dry-run" in sys.argv)
        print(f"logged {len(lat)} latencies, {len(miss)} pickup misses")
