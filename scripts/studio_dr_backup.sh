#!/bin/bash
# studio_dr_backup.sh — daily DR backup of the primary (Studio) -> offsite Mini.
#
# Copies the operational stack (workspace/git working tree, ~/.openclaw config,
# secrets, MC data), computes a manifest checksum, and on success writes the
# backup-health sentinel (backup_health_gate.py). The watchdog reads that sentinel.
#
# Pre-migration SELF-TEST mode: config/dr-backup.json has dest_is_remote=false and a
# LOCAL dest dir, so we prove rsync+manifest+sentinel end-to-end on the mini without
# needing the Studio. At migration: set dest to the Mini over the Cloudflare SSH tunnel
# (exomac@ssh.exosaero.space:/Users/exomac/dr-mirror/) and dest_is_remote=true.
#
# Usage: bash scripts/studio_dr_backup.sh
set -uo pipefail

WS=/Users/exomac/.openclaw/workspace
CFG="$WS/config/dr-backup.json"
LOG="$WS/logs/dr-backup.log"
mkdir -p "$WS/logs"

j() { python3 -c "import json,sys; print(json.load(open('$CFG')).get('$1',''))"; }

DEST=$(j dest)
DEST_REMOTE=$(j dest_is_remote)
WS_SRC=$(j workspace_src)
CFG_SRC=$(j openclaw_config_src)
GIT_PUSH=$(j git_push)

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(ts) $*" | tee -a "$LOG"; }

# single-flight: the hourly/02:00 job and the Sunday drill must never overlap
LOCKDIR="$HOME/.openclaw/state/dr-backup.lock"
mkdir -p "$HOME/.openclaw/state"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  if [ -n "$(find "$LOCKDIR" -maxdepth 0 -mmin +240 2>/dev/null)" ]; then
    rmdir "$LOCKDIR" 2>/dev/null; mkdir "$LOCKDIR" 2>/dev/null || { log "another DR backup holds the lock; exit"; exit 0; }
    log "WARN stale DR-backup lock (>4h) broken"
  else
    log "another DR backup is running (lock $LOCKDIR); exit"; exit 0
  fi
fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT

log "=== DR backup start (dest=$DEST remote=$DEST_REMOTE) ==="

CUI_EXCLUDE="$WS/scripts/cui-exclude-list.txt"
COMMON_EXCLUDES=(
  --exclude='.git/' --exclude='node_modules/' --exclude='logs/'
  --exclude='*.log' --exclude='.DS_Store' --exclude='cui-quarantine/'
  --exclude='.venv/' --exclude='__pycache__/'
  --exclude='*.backup-before-*' --exclude='*.orig' --exclude='*.tmp'
)
[ -f "$CUI_EXCLUDE" ] && COMMON_EXCLUDES+=(--exclude-from="$CUI_EXCLUDE")

RSYNC_RC=0
run_rsync() {  # $1=src  $2=subdir-under-dest
  local src="$1" sub="$2"
  if [ "$DEST_REMOTE" = "True" ] || [ "$DEST_REMOTE" = "true" ]; then
    local host="${DEST%%:*}" base="${DEST#*:}"
    ssh "$host" "mkdir -p '${base}${sub}'" 2>>"$LOG" || true
    rsync -az --delete "${COMMON_EXCLUDES[@]}" -e ssh "$src" "${DEST}${sub}" 2>>"$LOG" || RSYNC_RC=$?
  else
    mkdir -p "${DEST}${sub}"
    rsync -a --delete "${COMMON_EXCLUDES[@]}" "$src" "${DEST}${sub}" 2>>"$LOG" || RSYNC_RC=$?
  fi
}

# 1) workspace working tree
run_rsync "$WS_SRC" "workspace/"
# 2) openclaw config (INCLUDES secrets.json) — no --exclude of secrets; DR must be complete.
#    Exclude the big regenerable model cache; models are backed up separately (2 copies/2 sites).
run_rsync "$CFG_SRC" "openclaw-config/"

# 2a) Vaultwarden nightly backup tarballs (encrypted vaults) -> offsite. Uses the consistent
#     nightly snapshots (com.exos.vaultwarden-backup), not the live sqlite that may be mid-write.
VW_SRC=$(j vaultwarden_backup_src)
if [ -n "$VW_SRC" ] && [ -d "$VW_SRC" ]; then
  run_rsync "$VW_SRC" "vaultwarden/"
fi

# 2b) home-level credentials that live OUTSIDE ~/.openclaw (Bridge cert, msmtp config).
#     Needed for failover email; the failover drill flagged these were being missed.
for f in "$HOME/.protonmail-bridge.crt" "$HOME/.msmtprc"; do
  [ -f "$f" ] || continue
  bn=$(basename "$f")
  if [ "$DEST_REMOTE" = "True" ] || [ "$DEST_REMOTE" = "true" ]; then
    rsync -a -e ssh "$f" "${DEST}openclaw-config/$bn" 2>>"$LOG" || RSYNC_RC=$?
  else
    cp -p "$f" "${DEST}openclaw-config/$bn" 2>>"$LOG" || RSYNC_RC=$?
  fi
done

# 2c) Cloudflare tunnel credentials (exos-mc creds/config + lan-tunnel token). Both tunnels
#     must move on failover (9/30 lesson: the LAN tunnel was missed at cutover -> laptops lost MC).
[ -d "$HOME/.cloudflared" ] && run_rsync "$HOME/.cloudflared/" "cloudflared/"
# 2d) file-based secrets outside ~/.openclaw (Bridge SMTP pw, bot tokens, vault env) + the Studio's
#     CURRENT com.exos launchd set — failover_monitor's promote loads the server jobs from here
#     (the Mini's parked disabled-standby copies are from before the 9/28 cutover).
[ -d "$HOME/.config/exos" ] && run_rsync "$HOME/.config/exos/" "config-exos/"
if [ "$DEST_REMOTE" = "True" ] || [ "$DEST_REMOTE" = "true" ]; then
  ssh "${DEST%%:*}" "mkdir -p '${DEST#*:}launchagents'" 2>>"$LOG" || true
  rsync -a --delete --include='com.exos.*.plist' --include='ai.openclaw.gateway.plist' --exclude='*' \
    -e ssh "$HOME/Library/LaunchAgents/" "${DEST}launchagents/" 2>>"$LOG" || RSYNC_RC=$?
else
  mkdir -p "${DEST}launchagents"
  rsync -a --delete --include='com.exos.*.plist' --include='ai.openclaw.gateway.plist' --exclude='*' \
    "$HOME/Library/LaunchAgents/" "${DEST}launchagents/" 2>>"$LOG" || RSYNC_RC=$?
fi

# 3) optional git push (off in self-test)
if [ "$GIT_PUSH" = "True" ] || [ "$GIT_PUSH" = "true" ]; then
  ( cd "$WS" && git push 2>>"$LOG" ) && log "git push OK" || log "WARN git push failed"
fi

# 4) manifest checksum over the workspace working tree (integrity signal for the watchdog)
MANIFEST_SHA=$(cd "$WS_SRC" && find . -type f \
    -not -path './.git/*' -not -path './node_modules/*' -not -path './logs/*' \
    -not -name '*.log' 2>/dev/null | sort | \
    xargs -I{} stat -f '%N %z %m' {} 2>/dev/null | shasum -a 256 | awk '{print $1}')
log "manifest sha256=$MANIFEST_SHA rsync_rc=$RSYNC_RC"

# rsync exit codes: 0=perfect; 23=partial (some files unreadable, e.g. a stray perms-denied
# junk file); 24=some source files vanished mid-run. 23/24 are benign for DR — the important
# data still copied — so we accept them as success-with-warning. Any OTHER non-zero (12 proto,
# 30 timeout, 255 ssh, etc.) is a REAL failure -> no sentinel, watchdog alerts + pauses.
if [ "$RSYNC_RC" -eq 0 ] || [ "$RSYNC_RC" -eq 23 ] || [ "$RSYNC_RC" -eq 24 ]; then
  [ "$RSYNC_RC" -ne 0 ] && log "WARN rsync rc=$RSYNC_RC (partial — a few unreadable/vanished files skipped; treated as OK)"
  # 5) content-hash verify of the critical files on the mirror (secrets, gateway config, MC server,
  #    tunnel creds). A mismatch = checksum FAIL -> no sentinel; the watchdog alerts Jon.
  if ! python3 "$WS/scripts/dr_verify.py" --verify >>"$LOG" 2>&1; then
    log "=== DR backup FAILED (checksum verify mismatch) — sentinel NOT updated; watchdog will alert ==="
    exit 1
  fi
  log "checksum verify OK"
  python3 "$WS/scripts/backup_health_gate.py" --write "$MANIFEST_SHA" >>"$LOG" 2>&1
  log "=== DR backup SUCCESS — sentinel written ==="
  exit 0
else
  log "=== DR backup FAILED (rsync_rc=$RSYNC_RC) — sentinel NOT updated; watchdog will alert+pause ==="
  exit 1
fi
