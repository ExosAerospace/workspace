#!/bin/zsh
# Deterministic morning Mission Control briefing.
# Reads the LIVE Supabase board via mc_briefing.py and emails Jon.
# Host-level (launchd) so it is never blinded by the agent sandbox — this is
# the fix for the crons that couldn't reach the board and web-dredged stale items.
set -e
WS="/Users/exomac/.openclaw/workspace"
LOG="/Users/exomac/.openclaw/logs/mc-briefing.log"
cd "$WS"

if [ -f /Users/exomac/.msmtprc ]; then chmod 600 /Users/exomac/.msmtprc; fi

BODY="$(/usr/bin/python3 "$WS/scripts/mc_briefing.py" 2>>"$LOG")"
if [ -z "$BODY" ]; then
  echo "$(date) briefing empty — Supabase unreachable, not sending" >> "$LOG"
  exit 0
fi

DATE="$(date +%Y-%m-%d)"
{
  echo "From: John Quinn <jquinnexo@pm.me>"
  echo "To: jquinn@exosaero.com"
  echo "Subject: Mission Control Briefing — $DATE (live board)"
  echo "Content-Type: text/plain; charset=UTF-8"
  echo ""
  echo "$BODY"
} | /opt/homebrew/bin/msmtp jquinn@exosaero.com

echo "$(date) briefing sent" >> "$LOG"
