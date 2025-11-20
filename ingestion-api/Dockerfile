# CelesteOS Ingestion API Dockerfile
# Multi-stage build for optimal size

FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 celesteos && \
    mkdir -p /var/celesteos/uploads && \
    chown -R celesteos:celesteos /var/celesteos

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/celesteos/.local

# Copy application code
COPY --chown=celesteos:celesteos . .

# Switch to non-root user
USER celesteos

# Add local bin to PATH
ENV PATH=/home/celesteos/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/v1/health')"

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
