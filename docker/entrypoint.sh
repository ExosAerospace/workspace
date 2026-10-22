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

# Persist app-side state (feature selections, layouts, guard state, logs) on the volume so a
# rebuilt image never loses settings. /app/mission-control/data -> $DATA_DIR/appdata.
mkdir -p "$DATA_DIR/appdata" "$DATA_DIR/logs"
if [ ! -L /app/mission-control/data ]; then
  cp -n /app/mission-control/data/* "$DATA_DIR/appdata/" 2>/dev/null || true
  rm -rf /app/mission-control/data && ln -s "$DATA_DIR/appdata" /app/mission-control/data
fi
if [ ! -L /app/logs ]; then rm -rf /app/logs && ln -s "$DATA_DIR/logs" /app/logs; fi

# Entity seeds (first run only; later edits in Settings persist on the volume)
SEED="/app/docker-seed/$ENTITY"
[ -f "$SEED/tasks.json" ] && cp -n "$SEED/tasks.json" "$DATA_DIR/appdata/tasks.json"
[ -f "$DATA_DIR/appdata/tasks.json" ] || echo '{"tasks":[]}' > "$DATA_DIR/appdata/tasks.json"
[ -f "$SEED/mc-feature-selections.json" ] && cp -n "$SEED/mc-feature-selections.json" "$DATA_DIR/appdata/mc-feature-selections.json"
# Feature catalog source; server.js writes an entity-safe copy into appdata at startup.
export FEATURE_CATALOG_SRC=/app/docker-seed/_common/mc-feature-catalog.json

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
