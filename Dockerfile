# HealthSetu Backend Dockerfile
# Stage 1: Build & Runtime
FROM python:3.12-slim AS runtime

# Set environment variables for Python runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install minimal OS dependencies and security updates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security compliance in healthcare environments
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/false -m appuser

# Set working directory
WORKDIR /app

# Install Python dependencies first for caching efficiency
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create local storage directory with non-root ownership
RUN mkdir -p /app/data/documents /app/storage/documents && \
    chown -R appuser:appgroup /app/data /app/storage

# Copy application source code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose backend port
EXPOSE 8000

# Launch server via Uvicorn (binds dynamically to Railway/Cloud $PORT or defaults to 8000)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
