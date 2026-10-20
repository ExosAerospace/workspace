#!/bin/zsh
# Push the Exos DD-blocked-senders list to the GCC High tenant as a transport rule
# (action = Quarantine) and put Phil in the Strict preset (spam/bulk -> quarantine).
# Approved: D-SPAMBLOCK-M365-PHIL (9/02) + Phil email 2026-10-20. Task #2583.
# Usage: scripts/deploy_tenant_blocklist.sh   -> prints log path; device code appears in the log.
# A GCC High Exchange/Global admin enters the code at https://login.microsoftonline.us/device (15-min expiry).
WS=/Users/exomac/.openclaw/workspace
LOG=$WS/logs/tenant-blocklist-deploy-$(date +%Y%m%dT%H%M%S).log
cd $WS/email-blocklist
nohup ~/.local/pwsh/pwsh -NoProfile -NonInteractive -Command \
  "& ./Deploy-Exos-Blocked-Senders-Tenant.ps1 -Device -Action Quarantine -StrictUsers peaton@exosaero.com" \
  > $LOG 2>&1 &
echo $LOG
