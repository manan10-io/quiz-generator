# ─── Root Dockerfile ────────────────────────────────────────────────────────────
#
# This repository is a two-service application (Next.js frontend + FastAPI
# backend), each with its own purpose-built Dockerfile:
#   - backend/Dockerfile   — Python 3.11 + Tesseract OCR + all backend deps
#   - frontend/Dockerfile  — Next.js standalone build
#
# docker-compose.yml (the primary way to run this project locally or via
# Docker) references those two files directly via `build.context` and never
# reads this one. If you're using `docker compose up`, this file is not
# involved at all.
#
# This root-level Dockerfile exists ONLY for PaaS platforms (some configs of
# Railway, Fly.io, generic "Dockerfile at repo root" detectors) that require
# a single Dockerfile at the repository root and don't support pointing at a
# subdirectory. It builds the BACKEND service, since that's the more complex
# of the two and the one most such platforms are used to host.
#
# For the frontend, deploy to Vercel instead (see DEPLOYMENT.md) — Vercel's
# zero-config Next.js hosting is strictly better than containerizing it for
# production. If you must containerize the frontend too, build
# frontend/Dockerfile directly: `docker build -t quizgen-frontend ./frontend`
#
# To build the backend from this file: `docker build -t quizgen-backend .`
# (equivalent to `docker build -t quizgen-backend ./backend`)

FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-guj \
    libgl1 \
    libglib2.0-0 \
    fonts-dejavu-core \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /tmp/quizgen_uploads /tmp/quizgen_exports \
    && chown -R appuser:appuser /app /tmp/quizgen_uploads /tmp/quizgen_exports

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
