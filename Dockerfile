# Multi-stage Dockerfile that builds the Next.js frontend and packages
# the Python backend, runs both, and uses nginx as reverse proxy on port 80.

FROM node:20-bullseye AS frontend_build
WORKDIR /app/ui
COPY ui/package*.json ./
COPY ui/next.config.js ./
COPY ui/tsconfig.json ./
COPY ui/ .
RUN npm ci --silent && npm run build

FROM node:20-bookworm-slim AS final
RUN apt-get update && apt-get install -y --no-install-recommends \
  python3 python3-pip nginx ca-certificates curl build-essential \
  libsqlite3-0 libsqlite3-dev sqlite3 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy frontend build and all UI files so `next start` can run
COPY --from=frontend_build /app/ui /app/ui

# Copy the rest of the project (backend, src, requirements)
COPY . /app

# Install Python requirements
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Nginx site configuration
COPY docker/nginx.conf /etc/nginx/sites-available/default

# Entrypoint script that launches backend, frontend and nginx
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1/api/health || exit 1

CMD ["bash", "/start.sh"]
