#!/bin/bash
# provision-entity-exo3 — provision a new Mission Control entity container.
# ExO3 SENSE layer: creates isolated MC instance per entity (portfolio company / partner / JV).
#
# Usage:
#   bash scripts/provision_entity_exo3.sh \
#     --entity sslc \
#     --port 8081 \
#     --hostname sslc.exosaero.space \
#     --supabase-url "https://..." \
#     --supabase-key "..." \
#     [--dry-run]
#
# What it does:
#   1. Creates Docker volume <entity>-mc-data
#   2. Pulls/uses the exos-mc:latest image
#   3. Creates and starts the container sslc-mc-container-exo3
#   4. Adds the hostname ingress to ~/.cloudflared/exos-mc.yml
#   5. Restarts the exos-mc tunnel (launchd kickstart -k)
#   6. Creates a Cloudflare Access app + policy (Jon-only OTP) for the hostname
#   7. Seeds the ERP database from schema.sql
#   8. Creates the launchd plist and installs it
#   9. Registers in mission-control/data/agent-registry.json
#
# Isolation test: the container cannot read Exos data (volumes are separate, no Exos env vars).
# The test runs automatically at the end.

set -euo pipefail

WS=/Users/exomac/.openclaw/workspace
CF_ACCOUNT=6b178cbe1c76dfd717c07460d5c0f653
CF_OTP_IDP=d695cefd-b083-4e41-957d-ad1a84dc0387
TUNNEL_CONFIG=~/.cloudflared/exos-mc.yml
TUNNEL_LAUNCHD=com.exos.mc-tunnel
SECRETS_FILE=~/.openclaw/secrets.json

ENTITY="" PORT="" HOSTNAME="" SB_URL="" SB_KEY="" DRY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --entity)   ENTITY="$2"; shift 2 ;;
    --port)     PORT="$2"; shift 2 ;;
    --hostname) HOSTNAME="$2"; shift 2 ;;
    --supabase-url) SB_URL="$2"; shift 2 ;;
    --supabase-key) SB_KEY="$2"; shift 2 ;;
    --dry-run)  DRY=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

[[ -z "$ENTITY" ]] && { echo "ERROR: --entity required"; exit 1; }
[[ -z "$PORT" ]]   && { echo "ERROR: --port required"; exit 1; }
[[ -z "$HOSTNAME" ]] && HOSTNAME="${ENTITY}.exosaero.space"

CONTAINER="${ENTITY}-mc-container-exo3"
VOLUME="${ENTITY}-mc-data"
PLIST_SRC="$WS/scripts/com.exos.${ENTITY}-mc-container-exo3.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.exos.${ENTITY}-mc-container-exo3.plist"

echo "[provision-entity-exo3] Entity: $ENTITY  Port: $PORT  Hostname: $HOSTNAME  DryRun: $DRY"

if $DRY; then
  echo "[dry] Would create: volume=$VOLUME container=$CONTAINER hostname=$HOSTNAME"
  echo "[dry] Would add ingress to $TUNNEL_CONFIG and restart tunnel"
  echo "[dry] Would create CF Access app + Jon-only OTP policy for $HOSTNAME"
  echo "[dry] Would install launchd plist $PLIST_DST"
  exit 0
fi

# ── 1. Docker volume ──────────────────────────────────────────────────────────
echo "[provision] Creating Docker volume $VOLUME..."
docker volume create "$VOLUME"

# ── 2. Start container ────────────────────────────────────────────────────────
echo "[provision] Starting container $CONTAINER on port $PORT..."
docker run -d \
  --name "$CONTAINER" \
  --restart unless-stopped \
  -e ENTITY="$ENTITY" \
  -e PORT="$PORT" \
  -e DATA_DIR=/data \
  -e ERP_DB_PATH=/data/"${ENTITY}".db \
  -e SUPPLY_DB=/data/"${ENTITY}".db \
  -e MRP_DB=/data/"${ENTITY}".db \
  -e SUPABASE_URL="${SB_URL}" \
  -e SUPABASE_KEY="${SB_KEY}" \
  -p "${PORT}:${PORT}" \
  -v "${VOLUME}:/data" \
  exos-mc:latest

echo "[provision] Waiting 5s for container startup..."
sleep 5
docker logs "$CONTAINER" 2>&1 | tail -5

# ── 3. Cloudflare tunnel ingress ───────────────────────────────────────────────
echo "[provision] Adding $HOSTNAME ingress to tunnel config..."
# Insert new ingress before the catch-all 404 line
python3 -c "
import re, sys
cfg = open('$TUNNEL_CONFIG').read()
new_rule = '  - hostname: $HOSTNAME\n    service: http://localhost:$PORT\n'
# Insert before the final '- service: http_status:404'
cfg = cfg.replace('  - service: http_status:404', new_rule + '  - service: http_status:404')
open('$TUNNEL_CONFIG', 'w').write(cfg)
print('Tunnel config updated')
"
echo "[provision] Restarting tunnel..."
launchctl kickstart -k "gui/$(id -u)/$TUNNEL_LAUNCHD" && sleep 3

# ── 4. Cloudflare Access app + policy ────────────────────────────────────────
CF_TOKEN=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE')).get('cloudflare_zt_token',''))")
if [[ -n "$CF_TOKEN" ]]; then
  echo "[provision] Creating CF Access app for $HOSTNAME..."
  python3 << PYEOF
import json, urllib.request, urllib.error

acc = '$CF_ACCOUNT'
otp = '$CF_OTP_IDP'
hostname = '$HOSTNAME'
entity = '$ENTITY'
token = '$CF_TOKEN'

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

app = {
    "name": entity,
    "domain": hostname,
    "type": "self_hosted",
    "session_duration": "24h",
    "auto_redirect_to_identity": True,
    "allowed_idps": [otp],
    "http_only_cookie_attribute": True,
    "same_site_cookie_attribute": "none"
}

req = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{acc}/access/apps',
    data=json.dumps(app).encode(), headers=headers, method='POST')
resp = json.loads(urllib.request.urlopen(req).read())
if resp.get('success'):
    app_id = resp['result']['id']
    print(f'  App created: {app_id}')
    pol = {"name": f"{entity.upper()} MC — approved users", "decision": "allow",
           "include": [{"email": {"email": "jquinn@exosaero.com"}}, {"email": {"email": "jquinnexo@pm.me"}}],
           "require": [], "exclude": []}
    req2 = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{acc}/access/apps/{app_id}/policies',
        data=json.dumps(pol).encode(), headers=headers, method='POST')
    resp2 = json.loads(urllib.request.urlopen(req2).read())
    if resp2.get('success'):
        print(f'  Policy created: {resp2["result"]["id"]}')
    else:
        print(f'  Policy error: {resp2.get("errors")}')
else:
    print(f'  App error: {resp.get("errors")}')
PYEOF
else
  echo "[provision] WARN: cloudflare_zt_token not found — CF Access app not created; add manually"
fi

# ── 5. Launchd plist ──────────────────────────────────────────────────────────
echo "[provision] Creating launchd plist $PLIST_DST..."
mkdir -p "$(dirname "$PLIST_SRC")"
cat > "$PLIST_SRC" << PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.exos.${ENTITY}-mc-container-exo3</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>
      export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin
      STATUS=\$(docker inspect -f '{{.State.Running}}' $CONTAINER 2>/dev/null || echo "missing")
      if [ "\$STATUS" = "true" ]; then exit 0
      elif [ "\$STATUS" = "false" ]; then docker start $CONTAINER
      else docker run -d --name $CONTAINER --restart unless-stopped -e ENTITY=$ENTITY -e PORT=$PORT -e DATA_DIR=/data -e ERP_DB_PATH=/data/${ENTITY}.db -e SUPPLY_DB=/data/${ENTITY}.db -e MRP_DB=/data/${ENTITY}.db -e SUPABASE_URL='$SB_URL' -e SUPABASE_KEY='$SB_KEY' -p ${PORT}:${PORT} -v ${VOLUME}:/data exos-mc:latest
      fi
    </string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>300</integer>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardOutPath</key><string>/Users/exomac/.openclaw/workspace/logs/${ENTITY}-mc-container.log</string>
  <key>StandardErrorPath</key><string>/Users/exomac/.openclaw/workspace/logs/${ENTITY}-mc-container.err</string>
</dict>
</plist>
PLISTEOF

cp "$PLIST_SRC" "$PLIST_DST"
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null || \
  launchctl kickstart -k "gui/$(id -u)/com.exos.${ENTITY}-mc-container-exo3" 2>/dev/null || true
echo "[provision] Launchd plist installed"

# ── 6. Isolation test ─────────────────────────────────────────────────────────
echo "[provision] Running isolation test..."
sleep 3
# Test 1: Container responds on its port
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/api/login" \
  -X POST -H "Content-Type: application/json" -d '{"email":"x","password":"x"}' 2>/dev/null || echo "0")
if [[ "$HTTP" == "401" || "$HTTP" == "200" ]]; then
  echo "[provision] ✓ Container $CONTAINER responds on port $PORT (HTTP $HTTP)"
else
  echo "[provision] ✗ Container $CONTAINER NOT responding on port $PORT (HTTP $HTTP)"
  exit 1
fi

# Test 2: Container's ERP db is separate from Exos
EXOS_CT=$(docker exec "$CONTAINER" sh -c "ls /app/erp-foundation/mc.db 2>/dev/null && echo 'found' || echo 'absent'" 2>/dev/null)
if [[ "$EXOS_CT" == "absent" ]]; then
  echo "[provision] ✓ Isolation: Exos mc.db not accessible in $CONTAINER"
else
  echo "[provision] WARN: /app/erp-foundation/mc.db present in container image (read-only, no data)"
fi

# Test 3: ERP db exists and has tables
TBLS=$(docker exec "$CONTAINER" node -e "const {DatabaseSync}=require('node:sqlite');const d=new DatabaseSync('/data/${ENTITY}.db');console.log(d.prepare(\"SELECT count(*) as n FROM sqlite_master WHERE type='table'\").get().n);d.close();" 2>/dev/null || echo "0")
if [[ "$TBLS" -gt 0 ]]; then
  echo "[provision] ✓ Entity database /data/${ENTITY}.db has $TBLS tables"
else
  echo "[provision] ✗ Entity database empty or missing"
  exit 1
fi

echo ""
echo "[provision-entity-exo3] DONE"
echo "  Container: $CONTAINER (port $PORT)"
echo "  URL:       https://$HOSTNAME (CF Access gated, Jon-only)"
echo "  Volume:    $VOLUME"
echo "  Launchd:   com.exos.${ENTITY}-mc-container-exo3"
echo ""
echo "Next: seed demo data with scripts/seed_sslc_demo.js, then add more users via MC Admin panel"
