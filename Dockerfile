# ─────────────────────────────────────────────
# ACEest Fitness & Gym — Phase 2 Dockerfile
# Multi-stage build for leaner production image
# ─────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Production image ─────────────────
FROM python:3.12-slim

LABEL maintainer="ACEest DevOps Team"
LABEL description="ACEest Fitness & Gym — Flask Web Application"
LABEL version="2.0.0"

# Security: run as non-root user
RUN useradd -m -u 1000 aceest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=aceest:aceest . .

# Create data directory for SQLite DB persistence
RUN mkdir -p /data && chown aceest:aceest /data

# Initialise DB (creates tables + seeds admin user)
RUN python -c "from app import init_db; init_db()"

# Switch to non-root user
USER aceest

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/health')" || exit 1

CMD ["python", "app.py"]
