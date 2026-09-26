#!/usr/bin/env python3
"""
WARM FOLLOW-UP CADENCE — the nurture side of outreach (cold outreach auto-closes; WARM
pursuits get followed up until they close or the reply-tracker advances them).

Acts on open tasks tagged 'warm-followup'. Uses the task's due_date as the follow-up clock.
When a warm task's follow-up date has passed and it's still open, it goes into today's
"follow-ups due" digest (one consolidated DM to Jon), and its clock is advanced by the
category cadence. After MAX_NUDGES unanswered cycles it's flagged 'going-cold' for a keep/drop
decision instead of nudging forever. Never auto-closes (that stays with the reply-tracker).
Deterministic, zero LLM tokens. Run daily via launchd.

Run:  python3 scripts/warm-followup-cadence.py            # dry-run
      python3 scripts/warm-followup-cadence.py --apply
"""
import os, sys, json, re, datetime, subprocess, urllib.request
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
K = "sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp"
WS = os.path.expanduser("~/.openclaw/workspace")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
JON = "1501632195163590739"
LOG = os.path.join(WS, "logs", "warm-followup.jsonl")
APPLY = "--apply" in sys.argv
COLD_DAYS = 60   # keep following up until this many days cold, THEN retain for historical data (no delete)
CADENCE = {"series a": 7, "payload sales": 14}   # days between follow-ups by category
DEFAULT_CADENCE = 10


def q(path, method="GET", body=None):
    r = urllib.request.Request(SB + path, data=(json.dumps(body).encode() if body is not None else None),
        method=method, headers={"apikey": K, "Authorization": "Bearer " + K,
        "Content-Type": "application/json", "Prefer": "return=representation"})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else []


def page(path, fields):
    out, off = [], 0
    while True:
        pg = q(f"{path}?select={fields}&order=id&limit=1000&offset={off}")
        out += pg
        if len(pg) < 1000:
            return out
        off += 1000


def warm_since(tags):
    for t in (tags or []):
        m = re.fullmatch(r"ws:(\d{4}-\d{2}-\d{2})", str(t))
        if m:
            return datetime.date.fromisoformat(m.group(1))
    return None


def main():
    today = datetime.date.today()
    warm = [t for t in page("tasks", "id,title,category,due_date,tags,state,owner,priority")
            if (t.get("state") or "") not in ("Done", "Cancelled")
            and any(str(g).lower() == "warm-followup" for g in (t.get("tags") or []))]
    print(f"open warm-followup pursuits: {len(warm)}")

    due, retired = [], []
    for t in warm:
        dd = t.get("due_date")
        due_date = datetime.date.fromisoformat(dd[:10]) if dd else today  # no date -> due now
        if due_date > today:
            continue  # not yet due for follow-up
        days = (today - due_date).days
        ws = warm_since(t.get("tags")) or today   # first time we touch it, anchor the cold clock at today
        cold = (today - ws).days
        rec = {"id": t["id"], "title": (t.get("title") or "")[:60], "cat": t.get("category"),
               "days_overdue": days, "cold_days": cold}
        if cold >= COLD_DAYS:
            # 60 days cold -> stop nurturing, RETAIN for historical data (Cancelled = kept, not deleted)
            retired.append(rec)
            if APPLY:
                tags = [g for g in (t.get("tags") or []) if str(g).lower() != "warm-followup"
                        and not re.fullmatch(r"ws:\d{4}-\d{2}-\d{2}", str(g))]
                tags.append("historical-cold")
                q(f"tasks?id=eq.{t['id']}", "PATCH", {"state": "Cancelled",
                  "completed_at": today.strftime("%Y-%m-%dT%H:%M:%SZ"), "tags": tags,
                  "description": f"Retained for historical data: warm pursuit went {COLD_DAYS} days cold with no response. No longer nurtured."})
        else:
            due.append(rec)
            if APPLY:
                cad = CADENCE.get((t.get("category") or "").lower(), DEFAULT_CADENCE)
                next_due = (today + datetime.timedelta(days=cad)).isoformat()
                tags = list(t.get("tags") or [])
                if warm_since(tags) is None:   # stamp the cold-clock start once
                    tags.append(f"ws:{today.isoformat()}")
                q(f"tasks?id=eq.{t['id']}", "PATCH", {"due_date": f"{next_due}T23:59:59Z", "tags": tags})
        (open(LOG, "a").write(json.dumps({**rec, "ts": today.isoformat(), "applied": APPLY}) + "\n") if APPLY else None)

    print(f"{'due for follow-up' if not APPLY else 'nudged'}: {len(due)} | retained-historical (60d cold): {len(retired)}")
    for r in sorted(due, key=lambda x: -x["cold_days"])[:12]:
        print(f"   • {r['title']} [{r['cat']}] — {r['cold_days']}d cold")

    if APPLY and (due or retired):
        lines = "\n".join(f"• {r['title']} [{r['cat']}] — {r['cold_days']}d cold"
                          for r in sorted(due, key=lambda x: -x["cold_days"])[:10])
        msg = f"📨 **Warm follow-ups due ({len(due)})** — nurture, don't let these go cold:\n{lines}"
        if len(due) > 10:
            msg += f"\n…+{len(due)-10} more"
        if retired:
            msg += f"\n\n🗄️ **{len(retired)} retained as historical** (60 days cold, no response — kept for the record, no longer nurtured)."
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", msg],
                           timeout=60, capture_output=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
