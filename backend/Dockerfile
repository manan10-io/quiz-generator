# ─── Backend Dockerfile ────────────────────────────────────────────────────────
# Multi-stage build: system deps (Tesseract, fonts, image libs) installed once,
# Python deps cached separately from application code for fast rebuilds.

FROM python:3.11-slim AS base

# ─── System dependencies ────────────────────────────────────────────────────────
# tesseract-ocr + language packs: OCR engine (Phase 4)
# libgl1, libglib2.0-0: required by opencv-python-headless at runtime
# fonts-dejavu-core: fallback font for weasyprint PDF export
# build-essential: compiles any C extensions in requirements.txt
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

# ─── Python dependencies (separate layer for build caching) ────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Application code ────────────────────────────────────────────────────────────
COPY . .

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /tmp/quizgen_uploads /tmp/quizgen_exports \
    && chown -R appuser:appuser /app /tmp/quizgen_uploads /tmp/quizgen_exports

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run migrations then start the server. Using a shell form so both commands
# execute in sequence — if migrations fail, the container fails fast rather
# than serving traffic against an out-of-date schema.
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
