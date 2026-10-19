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

# Remove Exos-only secrets/runtime files from the image
RUN rm -f mission-control/users.json \
           mission-control/crm-data.json \
           mission-control/uploads/_meta.json || true

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
