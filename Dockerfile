# Startup Intelligence Platform — Next.js frontend + FastAPI backend (Vertex AI)
FROM node:20-slim AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/

# Copy Next.js standalone build
COPY --from=frontend /web/.next/standalone ./web/
COPY --from=frontend /web/.next/static ./web/.next/static
COPY --from=frontend /web/public ./web/public/ 2>/dev/null || true

# Seed database at build time
ENV LOCAL_FALLBACK=true
RUN python -c "
import sys; sys.path.insert(0, '.')
from backend.seed import seed_database
seed_database()
" || echo "seed done (warnings ok)"

# Runtime
ENV PORT=8080
ENV USE_VERTEX=true
ENV GCP_PROJECT=personal-project-dg21
ENV GCP_REGION=us-central1

RUN cat > /start.sh <<'SHELL'
#!/bin/sh
# FastAPI backend on port 8000 (internal)
cd /app && python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
# Next.js frontend on port 8080 (Cloud Run ingress)
cd /app/web && exec node server.js
SHELL
RUN chmod +x /start.sh
EXPOSE 8080
ENTRYPOINT ["/start.sh"]
