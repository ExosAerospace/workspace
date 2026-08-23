#!/usr/bin/env python3
"""
SERIES A DAILY WORKLIST — the "who to hit today" punch list for the raise.
Reads the scored Series A CRM (mission-control/data/crm.json, already ranked by priority score
with manual worklist edits applied), picks the top targets weighted toward Tier 1 + high-priority
+ anyone overdue for follow-up, and DMs Jon each morning. Deterministic, zero LLM tokens.

Run:  python3 scripts/series-a-daily-worklist.py            # print
      python3 scripts/series-a-daily-worklist.py --send     # DM Jon
"""
import os, sys, json, datetime, subprocess
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)

WS = os.path.expanduser("~/.openclaw/workspace")
CRM = os.path.join(WS, "mission-control", "data", "crm.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"
TOPN = 10
SEND = "--send" in sys.argv


def days_since(lt):
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(str(lt)[:10])).days
    except Exception:
        return None


def main():
    try:
        data = json.load(open(CRM))
    except Exception as e:
        print("crm.json unreadable:", e); sys.exit(1)
    contacts = data.get("contacts") or []
    # Exclude dead-ends (bounced / not a fit); rank by the score the generator already computed.
    live = [c for c in contacts
            if (c.get("tier") or "") not in ("Not a Fit",)
            and "BOUNCED" not in [str(f).upper() for f in (c.get("flags") or [])]]
    live.sort(key=lambda c: -(c.get("score") or 0))
    top = live[:TOPN]
    if not top:
        print("no live Series A targets"); return

    lines = []
    for i, c in enumerate(top, 1):
        d = days_since(c.get("last_touched"))
        touch = "never touched" if not c.get("last_touched") else (f"{d}d ago" if d is not None else "—")
        na = c.get("next_action") or "set next action"
        lines.append(f"{i}. **{c.get('firm')}** ({c.get('tier')}, {c.get('score')}) — {na}  · last: {touch}")

    hp = sum(1 for c in live if c.get("is_high_priority"))
    overdue = sum(1 for c in live if (days_since(c.get('last_touched')) or 99) >= 14)
    header = (f"🎯 **Series A — Top {len(top)} to work today** "
              f"({len(live)} live firms · {hp} high-priority · {overdue} overdue for follow-up)")
    body = header + "\n" + "\n".join(lines) + \
        "\n\nOpen the Series A CRM tab to work them: click a firm → set next action + mark touched."
    print(body)
    if SEND:
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", body],
                           timeout=60, capture_output=True)
        except Exception as e:
            print("send failed:", e)


if __name__ == "__main__":
    main()
