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
import dd_screen  # shared DD gate (CRM engine verdicts + do-not-engage blocklist)

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
    eligible = [c for c in contacts
                if (c.get("tier") or "") not in ("Not a Fit",)
                and "BOUNCED" not in [str(f).upper() for f in (c.get("flags") or [])]]

    # DD PRE-SCREEN (shared gate): delist any firm that FAILED DD — either the nightly
    # CRM DD engine marked it 'fail' OR it's on the hand-curated do-not-engage blocklist.
    # 'caution' firms are kept but flagged for human review before contact.
    crm_ok = bool(dd_screen.crm_verdicts())

    def dd_of(c):
        return dd_screen.verdict_for(firm=c.get("firm"))

    delisted = [c for c in eligible if dd_of(c) == "fail"]
    # Jon 2026-09-01 rule: a DD-CAUTION firm is only worked if it is a VALIDATED active
    # space/tech investor — an obvious, currently active fund WITH funding traction in the last
    # ~12 months. Caution firms not yet validated (the `fund_active_12mo` flag, set by the DD
    # sweep) are auto-dropped from the daily work list rather than surfaced for cold contact.
    # Validated either by a manual flag on the contact OR by the DD deep-dive (fund_active_12mo
    # written into the DD registry when it confirms an active space/tech fund with ~12-mo traction).
    def validated_fund(c):
        return bool(c.get("fund_active_12mo")) or dd_screen.fund_active_for(firm=c.get("firm"))
    dropped_caution = [c for c in eligible
                       if dd_of(c) == "caution" and not validated_fund(c)]
    _drop_ids = {id(c) for c in dropped_caution}
    live = [c for c in eligible
            if dd_of(c) != "fail" and id(c) not in _drop_ids]

    live.sort(key=lambda c: -(c.get("score") or 0))
    top = live[:TOPN]
    if not top:
        print("no live Series A targets"); return

    lines = []
    for i, c in enumerate(top, 1):
        d = days_since(c.get("last_touched"))
        touch = "never touched" if not c.get("last_touched") else (f"{d}d ago" if d is not None else "—")
        na = c.get("next_action") or "set next action"
        tag = " ⚠️ DD-CAUTION (verify before contact)" if dd_of(c) == "caution" else ""
        lines.append(f"{i}. **{c.get('firm')}** ({c.get('tier')}, {c.get('score')}){tag} — {na}  · last: {touch}")

    hp = sum(1 for c in live if c.get("is_high_priority"))
    overdue = sum(1 for c in live if (days_since(c.get('last_touched')) or 99) >= 14)
    header = (f"🎯 **Series A — Top {len(top)} to work today** "
              f"({len(live)} DD-clean firms · {hp} high-priority · {overdue} overdue for follow-up)")

    # Pre-screen transparency line — never silently drop firms.
    if delisted:
        names = ", ".join(c.get("firm") for c in delisted[:12])
        more = f" (+{len(delisted) - 12} more)" if len(delisted) > 12 else ""
        screen = f"🛡️ DD pre-screen: delisted {len(delisted)} failed-DD firm(s) — {names}{more}"
    else:
        screen = "🛡️ DD pre-screen: 0 failed-DD firms in pool ✅"
    if dropped_caution:
        cnames = ", ".join(c.get("firm") for c in dropped_caution[:12])
        cmore = f" (+{len(dropped_caution) - 12} more)" if len(dropped_caution) > 12 else ""
        screen += (f"\n🚦 Auto-dropped {len(dropped_caution)} DD-CAUTION firm(s) with no validated active "
                   f"space/tech fund + 12-mo traction — {cnames}{cmore}. "
                   f"(Validate a fund → set fund_active_12mo to re-include.)")
    if not crm_ok:
        screen += "\n⚠️ CRM DD engine registry unreadable — screened against do-not-engage blocklist only (partial)."

    body = header + "\n" + screen + "\n" + "\n".join(lines) + \
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
