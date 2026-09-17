# Startup Intelligence Platform — Next.js frontend + FastAPI backend (Vertex AI)
FROM node:20-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

FROM node:20-slim
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages
COPY backend/ ./backend/

# Copy Next.js standalone build
COPY --from=frontend /web/.next/standalone ./web/
COPY --from=frontend /web/.next/static ./web/.next/static
# public dir included in standalone build

# Seed database at build time
ENV LOCAL_FALLBACK=true
RUN python3 -c 'import sys; sys.path.insert(0, "."); from backend.seed import seed_database; seed_database()' || echo "seed done"

# Runtime
ENV PORT=8080
ENV USE_VERTEX=true
ENV GCP_PROJECT=personal-project-dg21
ENV GCP_REGION=us-central1

COPY start.sh /start.sh
RUN chmod +x /start.sh
EXPOSE 8080
ENTRYPOINT ["/start.sh"]
