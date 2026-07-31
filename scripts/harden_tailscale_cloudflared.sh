#!/bin/bash
# harden_tailscale_cloudflared.sh
# Run AS master with sudo:   sudo bash scripts/harden_tailscale_cloudflared.sh
#
# Job 1: Fully remove Tailscale residue from the Mac (Atomus security decision).
# Job 2: Move the cloudflared tunnel token off the command line + lock plist perms.
# Safe + idempotent. Reads the existing token in place — does NOT hardcode any secret.
set -euo pipefail

echo "================ JOB 1: Remove Tailscale ================"
# Stop / move the GUI app and its system extension
if [ -d /Applications/Tailscale.app ]; then
  echo "Removing /Applications/Tailscale.app ..."
  rm -rf /Applications/Tailscale.app
fi
# CLI symlinks the GUI app left in /usr/local/bin
rm -f /usr/local/bin/tailscale /usr/local/bin/tailscaled 2>/dev/null || true
# Any leftover state
rm -rf /Library/Tailscale /Library/Application\ Support/Tailscale 2>/dev/null || true
echo "Tailscale files removed. NOTE: the running network system-extension"
echo "is torn down by macOS once the owning app is gone — REBOOT to finish."
echo "After reboot verify:  systemextensionsctl list | grep -i tailscale   (should be empty/terminated)"
echo

echo "================ JOB 2: Harden cloudflared token ================"
PLIST=/Library/LaunchDaemons/com.cloudflare.cloudflared.plist
PB=/usr/libexec/PlistBuddy

# Backup first
cp "$PLIST" "${PLIST}.bak"
echo "Backed up plist -> ${PLIST}.bak"

# Only migrate if the token is still inline as ProgramArguments index 4
if $PB -c "Print :ProgramArguments:4" "$PLIST" >/dev/null 2>&1; then
  TOKEN="$($PB -c "Print :ProgramArguments:4" "$PLIST")"
  # Drop the "--token" (idx 3) and the token value (idx 4) from the argv
  $PB -c "Delete :ProgramArguments:4" "$PLIST"
  $PB -c "Delete :ProgramArguments:3" "$PLIST"
  # Inject it as an environment variable instead (not visible in `ps`)
  $PB -c "Delete :EnvironmentVariables" "$PLIST" 2>/dev/null || true
  $PB -c "Add :EnvironmentVariables dict" "$PLIST"
  $PB -c "Add :EnvironmentVariables:TUNNEL_TOKEN string ${TOKEN}" "$PLIST"
  echo "Moved token from argv -> TUNNEL_TOKEN env var."
else
  echo "Token not inline in argv (already migrated?) — skipping rewrite."
fi

# Lock the plist so the token isn't world-readable (was -rw-r--r--)
chown root:wheel "$PLIST"
chmod 600 "$PLIST"
echo "Locked plist perms to 600 root:wheel."

# Reload the daemon so the change takes effect (KeepAlive reconnects the tunnel)
launchctl bootout system "$PLIST" 2>/dev/null || true
launchctl bootstrap system "$PLIST"
echo "Reloaded cloudflared daemon."
echo

echo "================ VERIFY ================"
sleep 3
echo "-- token should NO LONGER appear here --"
ps -ax -o args | grep -i "[c]loudflared" || echo "(cloudflared not visible / no token in argv — good)"
echo "-- tunnel should be reconnected (check log) --"
tail -n 5 /Library/Logs/com.cloudflare.cloudflared.out.log 2>/dev/null || true
echo "Done. If anything looks wrong, restore: cp ${PLIST}.bak ${PLIST} && launchctl bootstrap system ${PLIST}"
