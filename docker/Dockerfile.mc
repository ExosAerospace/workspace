# Mission Control — multi-entity container image
# Build:  docker build -f docker/Dockerfile.mc -t exos-mc:latest .
# Run:    docker run -d \
#           -e ENTITY=sslc -e PORT=8081 \
#           -e SUPABASE_URL=... -e SUPABASE_KEY=... \
#           -v sslc-mc-data:/data \
#           -p 8081:8081 \
#           --name sslc-mc-container-exo3 \
#           exos-mc:latest

FROM node:24-alpine

# python3 for scripts (fx_rate, job_cost, etc.)
RUN apk add --no-cache python3 py3-pip curl bash

WORKDIR /app

# Copy package.json and install JS dependencies
COPY package.json package-lock.json* ./
RUN npm install --omit=dev 2>/dev/null || npm install

# Copy application source (no secrets, no runtime state, no uploads)
COPY mission-control/ ./mission-control/
COPY erp-foundation/ ./erp-foundation/
COPY scripts/ ./scripts/
COPY governance/ ./governance/

# Remove ALL Exos data/runtime state from the image (Jon 2026-10-22: no Exos data in a rollout site).
# The image ships code only; each entity's data lives in its /data volume or docker/seed/<entity>/.
RUN rm -rf mission-control/data mission-control/dataroom mission-control/uploads \
           mission-control/partner-docs mission-control/surveys logs \
    && rm -f mission-control/users.json* mission-control/crm-data.json* mission-control/sessions.json \
             mission-control/*.log mission-control/.ds-passcode mission-control/.public-url \
             mission-control/.env* mission-control/data/.guard-* \
    && find governance -type f ! -name 'govlog.*' ! -name '__init__.py' -delete \
    && find . -path ./node_modules -prune -o \( -name '*.bak*' -o -name '*.log' -o -name '*.jsonl' \) -type f -print -exec rm -f {} + \
    && rm -rf erp-foundation/sample-data erp-foundation/backups erp-foundation/agent-agreements \
              erp-foundation/*.db* erp-foundation/seed_*.js mission-control/brand-assets \
    && find scripts -type f ! \( -name 'fx_rate.py' -o -name 'job_cost.py' -o -name 'mc_guard.py' \
         -o -name 'mc_restore.py' -o -name 'fleet_log.py' -o -name 'itar_ear_screen.py' \) -delete \
    && find scripts -type d -empty -delete \
    && mkdir -p mission-control/data mission-control/uploads mission-control/brand-assets scripts
COPY docker/seed/ /app/docker-seed/

# Entrypoint: initialise /data volume on first run, then start the server
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# /data is the mutable volume — users.json, uploads/, erp db go here
VOLUME /data

# Defaults — override via -e or docker-compose env:
ENV ENTITY=exos \
    PORT=8080 \
    DATA_DIR=/data \
    ERP_DB_PATH=/data/mc.db \
    SUPABASE_URL="" \
    SUPABASE_KEY=""

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
CMD ["node", "mission-control/server.js"]
