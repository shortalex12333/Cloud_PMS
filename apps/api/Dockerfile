# =============================================================================
# CelesteOS Pipeline Core - Production Dockerfile
# =============================================================================
# Multi-stage build for minimal image size and security
# SOC-2 Guardrails: non-root user, no secrets in image, pinned base
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and compile wheels
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (for packages with C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (layer caching)
COPY requirements.txt .

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install deps with no cache to minimize image size
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Security: Create non-root user before copying files
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

WORKDIR /app

# Install runtime dependencies only (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (respects .dockerignore)
COPY --chown=appuser:appgroup . .

# Security: Switch to non-root user
USER 10001:10001

# Expose port (Render expects 8080, but configurable via PORT env)
EXPOSE 8080

# Environment defaults (secrets come from Render env vars, NOT here)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Healthcheck - critical for Render deployments
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT}/health || exit 1

# Run with uvicorn
CMD ["sh", "-c", "uvicorn pipeline_service:app --host 0.0.0.0 --port ${PORT}"]
