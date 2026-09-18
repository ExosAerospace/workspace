#!/bin/zsh
# nightly-security.sh
# Runs at 3:15 AM daily via OpenClaw cron
# Security hardening routine for ExoMac

LOG_DIR="/Users/exomac/.openclaw/workspace/logs"
LOG_FILE="$LOG_DIR/security-$(date +%Y-%m-%d).log"
ALERT=""

mkdir -p "$LOG_DIR"

# --- Decisions inbox routing -------------------------------------------------
# Any condition that genuinely requires Jon to act (reboot, enable firewall, etc.)
# is pushed to the Decisions inbox so it lands in front of him. dedupeKey keeps a
# still-pending item from re-posting every night until it's answered/resolved.
DECISIONS_API="http://localhost:8080/api/decisions/ingest"
EXO_TOKEN="$(cat /Users/exomac/.openclaw/workspace/mission-control/data/.decisions-token)"

# post_decision <dedupeKey> <priority> <title> <question> <proposedAction>
post_decision() {
    curl -s -X POST "$DECISIONS_API" \
        -H "X-Exo-Token: $EXO_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"source\":\"Nightly Security Scan\",\"relatedItem\":\"security-$(date +%Y-%m-%d)\",\"title\":\"$3\",\"question\":\"$4\",\"proposedAction\":\"$5\",\"type\":\"yesno\",\"options\":[\"Yes\",\"No\"],\"priority\":\"$2\",\"dedupeKey\":\"$1\"}" \
        >> "$LOG_FILE" 2>&1
    echo "" >> "$LOG_FILE"
    echo "[→] Decision routed to inbox: $3" >> "$LOG_FILE"
}
# ----------------------------------------------------------------------------

echo "=== Nightly Security Run: $(date) ===" >> "$LOG_FILE"

# 1. macOS Software Updates (security patches only, non-interactive)
echo "[1] Checking macOS security updates..." >> "$LOG_FILE"
UPDATE_CHECK=$(/usr/sbin/softwareupdate -l 2>&1)
echo "$UPDATE_CHECK" >> "$LOG_FILE"
if echo "$UPDATE_CHECK" | grep -qi "recommended\|security"; then
    echo "[!] Security updates available — downloading only (install requires your password)" >> "$LOG_FILE"
    # Download only — cannot install headless, requires interactive auth
    /usr/sbin/softwareupdate --download --recommended 2>&1 >> "$LOG_FILE"
    ALERT="${ALERT}📦 macOS security updates downloaded and ready to install. Reboot when convenient to apply.\n"
    post_decision "macos-security-update-reboot" "high" \
        "Reboot ExoMac to apply pending macOS security update" \
        "A recommended macOS security update is downloaded and staged. Installing requires your password and a reboot. Apply it now?" \
        "Reboot ExoMac at a convenient time to install the staged security update."
else
    echo "[✓] macOS up to date" >> "$LOG_FILE"
fi

# 2. Homebrew security updates
echo "[2] Updating Homebrew packages..." >> "$LOG_FILE"
/opt/homebrew/bin/brew update 2>&1 >> "$LOG_FILE"
BREW_OUTDATED=$(/opt/homebrew/bin/brew outdated 2>&1)
if [ -n "$BREW_OUTDATED" ]; then
    echo "Outdated packages: $BREW_OUTDATED" >> "$LOG_FILE"
    /opt/homebrew/bin/brew upgrade 2>&1 >> "$LOG_FILE"
    ALERT="${ALERT}⚠️ Homebrew packages upgraded: $(echo $BREW_OUTDATED | tr '\n' ', ')\n"
else
    echo "[✓] Homebrew packages current" >> "$LOG_FILE"
fi

# Resolve openclaw binary — resilient across OS updates and cold launchd PATH.
# Try each candidate and keep the first that is actually executable. Never let a
# failed lookup (e.g. zsh `which` printing "openclaw not found") pollute OC_BIN.
OC_BIN=""
for cand in \
    "$(command -v openclaw 2>/dev/null)" \
    /Users/exomac/.local/share/mise/shims/openclaw \
    /Users/exomac/.local/share/mise/installs/node/*/bin/openclaw; do
    if [ -n "$cand" ] && [ -x "$cand" ]; then OC_BIN="$cand"; break; fi
done

# 3. OpenClaw security audit
echo "[3] Running OpenClaw security audit..." >> "$LOG_FILE"
if [ -n "$OC_BIN" ]; then
    AUDIT=$($OC_BIN security audit 2>&1)
    echo "$AUDIT" >> "$LOG_FILE"
    if echo "$AUDIT" | grep -qi "warning\|critical\|fail"; then
        ALERT="${ALERT}⚠️ OpenClaw security audit flagged issues — check logs.\n"
    else
        echo "[✓] OpenClaw audit clean" >> "$LOG_FILE"
    fi
else
    echo "[!] openclaw binary not found — skipping audit" >> "$LOG_FILE"
    ALERT="${ALERT}⚠️ openclaw binary not found — may need PATH fix after OS update.\n"
fi

# 4. OpenClaw update check
echo "[4] Checking OpenClaw version..." >> "$LOG_FILE"
if [ -n "$OC_BIN" ]; then
    UPDATE_STATUS=$($OC_BIN update status 2>&1)
    echo "$UPDATE_STATUS" >> "$LOG_FILE"
    if echo "$UPDATE_STATUS" | grep -qi "update available\|new version"; then
        ALERT="${ALERT}📦 OpenClaw update available — run: openclaw update\n"
    else
        echo "[✓] OpenClaw up to date" >> "$LOG_FILE"
    fi
fi

# 5. Credential file permissions hardening
echo "[5] Hardening credential file permissions..." >> "$LOG_FILE"
# msmtp config must be 600
if [ -f /Users/exomac/.msmtprc ]; then
    chmod 600 /Users/exomac/.msmtprc
    echo "[✓] .msmtprc permissions: 600" >> "$LOG_FILE"
fi
# OpenClaw workspace — ensure no world-readable sensitive files
chmod -R o-rwx /Users/exomac/.openclaw/workspace/drafts 2>/dev/null
chmod -R o-rwx /Users/exomac/.openclaw/workspace/references 2>/dev/null
echo "[✓] Workspace sensitive folders locked to owner-only" >> "$LOG_FILE"

# 6. Clean old OpenClaw session files (Alex Finn's documented tip)
echo "[6] Cleaning old session files..." >> "$LOG_FILE"
SESSION_DIR="/Users/exomac/.openclaw/agents/main/sessions"
if [ -d "$SESSION_DIR" ]; then
    SESSION_COUNT=$(ls "$SESSION_DIR"/*.jsonl 2>/dev/null | wc -l | tr -d ' ')
    echo "Session files found: $SESSION_COUNT" >> "$LOG_FILE"
    if [ "$SESSION_COUNT" -gt 100 ]; then
        # Keep 20 most recent, delete the rest
        ls -t "$SESSION_DIR"/*.jsonl 2>/dev/null | tail -n +21 | xargs rm -f
        echo "[✓] Cleaned old session files (kept 20 most recent)" >> "$LOG_FILE"
        ALERT="${ALERT}🧹 Cleaned $((SESSION_COUNT - 20)) old session files.\n"
    else
        echo "[✓] Session files within normal range ($SESSION_COUNT)" >> "$LOG_FILE"
    fi
fi

# 7. Check macOS firewall status
echo "[7] Firewall status check..." >> "$LOG_FILE"
FIREWALL=$(/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>&1)
echo "$FIREWALL" >> "$LOG_FILE"
if echo "$FIREWALL" | grep -qi "disabled"; then
    ALERT="${ALERT}🚨 macOS firewall is DISABLED — recommend enabling.\n"
    post_decision "macos-firewall-disabled" "high" \
        "Re-enable the macOS firewall on ExoMac" \
        "The macOS application firewall is currently DISABLED, leaving the machine more exposed. Re-enable it?" \
        "Enable the macOS firewall via System Settings > Network > Firewall, or socketfilterfw --setglobalstate on."
else
    echo "[✓] Firewall active" >> "$LOG_FILE"
fi

# 8. Check for unexpected open ports
echo "[8] Checking open ports..." >> "$LOG_FILE"
PORTS=$(lsof -nP -iTCP -sTCP:LISTEN 2>&1 | grep -v "127.0.0.1\|::1")
if [ -n "$PORTS" ]; then
    echo "External-facing ports detected:" >> "$LOG_FILE"
    echo "$PORTS" >> "$LOG_FILE"
    ALERT="${ALERT}🔍 External-facing open ports detected — review logs.\n"
else
    echo "[✓] No unexpected external ports" >> "$LOG_FILE"
fi

# 9. Log rotation — keep only 30 days of logs
find "$LOG_DIR" -name "security-*.log" -mtime +30 -delete 2>/dev/null
echo "[✓] Old logs cleaned (>30 days)" >> "$LOG_FILE"

echo "=== Run complete: $(date) ===" >> "$LOG_FILE"

# Send alert email if anything needs attention
if [ -n "$ALERT" ]; then
    echo -e "From: jquinnexo@pm.me\nTo: jquinnexo@pm.me\nSubject: 🔒 Nightly Security Alert — ExoMac $(date +%Y-%m-%d)\n\nThe following items require attention:\n\n${ALERT}\nFull log: $LOG_FILE" | /opt/homebrew/bin/msmtp jquinnexo@pm.me
fi

exit 0
