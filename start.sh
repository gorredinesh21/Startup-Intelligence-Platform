#!/bin/sh
# FastAPI backend on port 8000 (internal)
cd /app && python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
# Next.js frontend on port 8080 (Cloud Run ingress)
cd /app/web && exec node server.js
