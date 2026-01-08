FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Configure Poetry: Don't create virtual environment, install dependencies globally
RUN poetry config virtualenvs.create false

# Copy dependency files
COPY apps/cognitive-orch/pyproject.toml apps/cognitive-orch/poetry.lock* apps/cognitive-orch/requirements.txt* ./

# Install dependencies
# Try Poetry first, fallback to pip if poetry.lock doesn't exist
RUN if [ -f poetry.lock ]; then \
        poetry install --no-dev --no-interaction --no-ansi --no-root; \
    else \
        echo "poetry.lock not found, installing from requirements.txt..."; \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy application code
COPY apps/cognitive-orch/src/ ./src/

# Copy shared libraries
COPY libs/py-common/src/ ./libs/py-common/src/

# Install the package in development mode so cognitive_orch is importable
# Try to install with poetry, but if it fails, we'll rely on PYTHONPATH
RUN poetry install --no-dev --no-interaction --no-ansi 2>&1 || echo "Poetry install completed with warnings or skipped"

# Set PYTHONPATH to ensure cognitive_orch and py_common can be imported
# This is the primary way Python will find the module
ENV PYTHONPATH=/app/src:/app/libs/py-common/src:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports (HTTP and gRPC)
EXPOSE 8001 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run application
CMD ["uvicorn", "cognitive_orch.main:app", "--host", "0.0.0.0", "--port", "8001"]

