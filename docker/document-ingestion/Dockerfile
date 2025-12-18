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
COPY apps/document-ingestion/pyproject.toml apps/document-ingestion/poetry.lock* ./

# Install dependencies (without the package itself first)
# Update lock file to include any new dependencies from pyproject.toml, then install
RUN poetry lock && \
    poetry install --only main --no-interaction --no-ansi --no-root

# Copy application code
COPY apps/document-ingestion/src/ ./src/

# Install the package in development mode so document_ingestion is importable
# Try to install with poetry, but if it fails, we'll rely on PYTHONPATH
RUN poetry install --no-dev --no-interaction --no-ansi 2>&1 || echo "Poetry install completed with warnings or skipped"

# Set PYTHONPATH to ensure document_ingestion can be imported
# This is the primary way Python will find the module
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run application
CMD ["uvicorn", "document_ingestion.main:app", "--host", "0.0.0.0", "--port", "8003"]

