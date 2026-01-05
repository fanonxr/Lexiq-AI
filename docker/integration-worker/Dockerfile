# Integration Worker Dockerfile
# Python background worker for calendar sync and CRM integration

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy api-core first (dependency for shared models)
COPY apps/api-core/pyproject.toml /app/api-core/pyproject.toml
COPY apps/api-core/requirements.txt /app/api-core/requirements.txt
COPY apps/api-core/src /app/api-core/src
COPY apps/api-core/README.md /app/api-core/README.md

# Install api-core in editable mode
RUN pip install --no-cache-dir -e /app/api-core

# Copy integration-worker requirements
COPY apps/integration-worker/requirements.txt /app/requirements.txt

# Install integration-worker dependencies (excluding api-core which is already installed)
# Filter out the "-e ../api-core" line since we already installed it above
RUN grep -v "^-e ../api-core" /app/requirements.txt > /app/requirements-docker.txt && \
    pip install --no-cache-dir -r /app/requirements-docker.txt

# Copy integration-worker source code
COPY apps/integration-worker/src /app/src

# Set Python path to include both src directories
ENV PYTHONPATH=/app/src:/app/api-core/src

# Create non-root user for security
RUN useradd -m -u 1000 celeryuser && \
    chown -R celeryuser:celeryuser /app

USER celeryuser

# Health check for Celery worker
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD celery -A integration_worker.celery_app inspect ping -d celery@$HOSTNAME || exit 1

# Default command: Celery worker
# Can be overridden in docker-compose.yml for beat scheduler
CMD ["celery", "-A", "integration_worker.celery_app", "worker", "--loglevel=info", "--concurrency=4"]

