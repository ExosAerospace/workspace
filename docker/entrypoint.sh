#!/bin/bash
# MC container entrypoint: initialise /data volume on first run, then exec the server.
set -e

DATA_DIR="${DATA_DIR:-/data}"
ERP_DB_PATH="${ERP_DB_PATH:-$DATA_DIR/mc.db}"
ENTITY="${ENTITY:-exos}"

echo "[MC entrypoint] ENTITY=$ENTITY PORT=${PORT:-8080} DATA_DIR=$DATA_DIR"

# Ensure data directories exist
mkdir -p "$DATA_DIR/uploads/esign-executed"

# Seed an empty users.json if none exists
if [ ! -f "$DATA_DIR/users.json" ]; then
  echo "[]" > "$DATA_DIR/users.json"
  echo "[MC entrypoint] Created empty $DATA_DIR/users.json"
fi

# Seed an empty crm-data.json if none exists
if [ ! -f "$DATA_DIR/crm-data.json" ]; then
  echo '{"companies":[],"contacts":[],"opportunities":[]}' > "$DATA_DIR/crm-data.json"
  echo "[MC entrypoint] Created empty $DATA_DIR/crm-data.json"
fi

# Seed uploads/_meta.json if none exists (server expects an array)
if [ ! -f "$DATA_DIR/uploads/_meta.json" ] || [ "$(cat "$DATA_DIR/uploads/_meta.json")" = "{}" ]; then
  echo '[]' > "$DATA_DIR/uploads/_meta.json"
fi

# Entity task board: sample tasks only (never the Exos snapshot)
if [ -f "/app/docker-seed/$ENTITY/tasks.json" ]; then
  cp "/app/docker-seed/$ENTITY/tasks.json" /app/mission-control/data/tasks.json
else
  echo '{"tasks":[]}' > /app/mission-control/data/tasks.json
fi

# Initialise the ERP database from schema.sql if not present
if [ ! -f "$ERP_DB_PATH" ]; then
  echo "[MC entrypoint] Creating ERP database at $ERP_DB_PATH from schema.sql"
  node -e "
    const fs = require('fs');
    const path = require('path');
    const { DatabaseSync } = require('node:sqlite');
    const schema = fs.readFileSync('/app/erp-foundation/schema.sql', 'utf8');
    const db = new DatabaseSync('$ERP_DB_PATH');
    db.exec(schema);
    db.close();
    console.log('[MC entrypoint] ERP database initialised');
  "
fi

exec "$@"
