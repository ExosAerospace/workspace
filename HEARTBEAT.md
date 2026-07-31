# HEARTBEAT — periodic check routine

When you receive a heartbeat, run the checks below, update `memory/heartbeat-state.json`,
and only message Jon if something genuinely needs attention. Otherwise reply exactly `HEARTBEAT_OK`.

## Quiet hours
- 23:00–08:00 America/Chicago: stay silent unless it is truly urgent. Reply `HEARTBEAT_OK`.

## If tools are unavailable this cycle — STAY QUIET (important)
If the ProtonMail Bridge / IMAP, web search, or other tools are unreachable this cycle
(transient network/provider blips happen), DO NOT post a "can't scan / everything failing"
report — that is noise, not signal. Just reply `HEARTBEAT_OK` and try again next cycle.
Only surface a tools-down message if it persists across multiple consecutive heartbeats.

## Checks (only act on real signal)
1. **Email** — scan the inbox via `python3 scripts/mission-control-imap.py` (Bridge IMAP on 127.0.0.1:1143).
   Flag only important/time-sensitive mail (investor, gov/.mil, customer, deadline). Skip routine.
2. **Calendar** — surface anything starting within the next 2 hours.
3. **Mentions** — note any direct Discord mentions/DMs needing a reply.
4. **Weather** — only if it affects a launch/travel/ops item; otherwise skip.

## State
Track last-check timestamps + last-seen message ids in `memory/heartbeat-state.json` so you
don't re-alert on the same item. Update it every run.

## Reach out only for
Important unread email, an event <2h out, a direct mention awaiting reply, or a genuinely
interesting/time-critical find. Batch into one concise message. Nothing pending → `HEARTBEAT_OK`.
