# CelesteOS Cloud_PMS Dockerfile
# Runs microaction extraction service with document processing

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY api/requirements.txt /app/api/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy application code
COPY api/ /app/api/

# Set working directory to api
WORKDIR /app/api

# Expose port (Render will set $PORT)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start uvicorn server
CMD uvicorn microaction_service:app --host 0.0.0.0 --port ${PORT:-8000}
