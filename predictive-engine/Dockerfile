# ========================================
# CelesteOS Predictive Maintenance Engine
# Docker Image
# ========================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 celeste && \
    chown -R celeste:celeste /app

USER celeste

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command: run web server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Alternative commands:
# Worker mode: docker run <image> python worker.py run-all
# Specific yacht: docker run <image> python worker.py run-yacht <yacht-id>
