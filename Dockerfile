# Startup Intelligence Platform — FastAPI serves static frontend + API (Vertex AI)
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
COPY --from=frontend /web/out ./static

# Seed database at build time
ENV LOCAL_FALLBACK=true
RUN python3 -c 'import sys; sys.path.insert(0, "."); from backend.seed import seed_database; seed_database()' || echo "seed done"

# Serve static files from FastAPI
RUN cat >> backend/main.py <<'PY'

# Serve the static frontend (Next.js export) from the same origin
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/", include_in_schema=False)
async def serve_spa():
    index = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return {"status": "api running", "docs": "/docs"}

_static = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static):
    app.mount("/", StaticFiles(directory=_static, html=True), name="spa")
PY

ENV PORT=8080
ENV USE_VERTEX=true
ENV GCP_PROJECT=personal-project-dg21
ENV GCP_REGION=us-central1

EXPOSE 8080
CMD exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8080
