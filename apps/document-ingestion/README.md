# Document Ingestion Service

**Version:** 0.1.0  
**Service:** Document Ingestion (`apps/document-ingestion`)  
**Status:** Phase 1 - Foundation & Configuration Complete

## Overview

The Document Ingestion Service is a dedicated microservice responsible for processing uploaded knowledge base files. It downloads files from Azure Blob Storage, parses documents, chunks text, generates embeddings, and stores vectors in Qdrant for RAG (Retrieval-Augmented Generation).

### Key Features

- **Queue-Based Processing**: Async processing via RabbitMQ message queue
- **Document Parsing**: Supports PDF, DOCX, TXT, and MD files
- **Intelligent Chunking**: Token-based chunking with sentence awareness and overlap
- **Embedding Generation**: Uses Azure OpenAI for generating embeddings
- **Vector Storage**: Stores embeddings in Qdrant with firm-specific collections
- **Status Updates**: Updates file processing status via API Core
- **Fault Tolerance**: Robust retry logic and error handling

## Architecture

```
User Uploads File
    ↓
API Core (stores in Blob Storage, creates DB record)
    ↓
Publishes to RabbitMQ Queue
    ↓
Document Ingestion Service (consumes message)
    ↓
1. Download from Blob Storage
2. Parse Document (PDF/DOCX/TXT/MD)
3. Chunk Text
4. Generate Embeddings
5. Store in Qdrant
6. Update Status via API Core
```

## Directory Structure

```
apps/document-ingestion/
├── README.md
├── pyproject.toml              # Poetry dependencies
├── requirements.txt            # Alternative to Poetry
├── requirements-dev.txt        # Development dependencies
├── .env.example                # Environment variables template
├── src/
│   └── document_ingestion/
│       ├── __init__.py
│       ├── main.py             # FastAPI app entry point
│       ├── config.py            # Pydantic settings
│       ├── api/
│       │   └── v1/
│       │       ├── health.py    # Health check endpoints
│       │       └── router.py   # API router
│       ├── services/           # Business logic (to be implemented)
│       ├── workers/            # Queue workers (to be implemented)
│       ├── models/             # Pydantic models (to be implemented)
│       ├── utils/
│       │   ├── logging.py      # Logging configuration
│       │   └── errors.py       # Custom exceptions
│       └── clients/            # External service clients (to be implemented)
└── tests/                      # Tests (to be implemented)
```

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- Docker and Docker Compose (for local development)
- RabbitMQ (included in docker-compose.yml)
- Azure Blob Storage (or Azurite for local development)
- Azure OpenAI (for embeddings)
- Qdrant (included in docker-compose.yml)

### Local Development Setup

1. **Copy environment variables:**
   ```bash
   cp apps/document-ingestion/.env.example apps/document-ingestion/.env
   ```

2. **Update `.env` with your configuration:**
   - Set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`
   - Configure RabbitMQ connection (default works with docker-compose)
   - Configure storage connection (Azurite for local dev)

3. **Install dependencies:**
   ```bash
   cd apps/document-ingestion
   poetry install
   ```

4. **Run with Docker Compose:**
   ```bash
   # From project root
   docker-compose up document-ingestion
   ```

5. **Or run locally:**
   ```bash
   cd apps/document-ingestion
   poetry run uvicorn document_ingestion.main:app --reload --port 8003
   ```

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

- **RabbitMQ**: `RABBITMQ_URL`, `RABBITMQ_QUEUE_NAME`, etc.
- **Storage**: `STORAGE_ACCOUNT_NAME`, `STORAGE_USE_MANAGED_IDENTITY`
- **Embeddings**: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`
- **Qdrant**: `QDRANT_URL`, `QDRANT_API_KEY`
- **API Core**: `CORE_API_URL`, `CORE_API_API_KEY` (internal API key for service-to-service auth)

**Internal API Key (Service-to-Service Auth):**
- `CORE_API_API_KEY` - Internal API key for calling API Core internal endpoints (sent as `X-Internal-API-Key` header). This should match the `INTERNAL_API_KEY` value in the API Core service.

**Note:** See [Internal API Key Documentation](/docs/internal-api-key/internal-api-impl-plan.md) for details on service-to-service authentication.

## API Endpoints

### Health Checks

- `GET /health` - Basic health check
- `GET /ready` - Readiness check (verifies external dependencies)
- `GET /api/v1/health` - Health check via API v1
- `GET /api/v1/ready` - Readiness check via API v1

### API Information

- `GET /api/v1/` - API version and status information

## Implementation Status

### ✅ Phase 1: Foundation & Configuration (Complete)

- [x] Service directory structure
- [x] Configuration management (`config.py`)
- [x] FastAPI application setup (`main.py`)
- [x] Health check endpoints
- [x] Logging and error handling
- [x] Docker setup
- [x] Docker Compose integration

### 🚧 Phase 2: Message Queue Integration (Next)

- [ ] RabbitMQ queue setup
- [ ] Worker implementation
- [ ] Message models
- [ ] Queue consumer
- [ ] API Core integration

### 📋 Phase 3-7: (Planned)

See `docs/orchestrator/DOCUMENT_INGESTION_ARCHITECTURE.md` for full implementation plan.

## Development

### Running Tests

```bash
cd apps/document-ingestion
poetry run pytest
```

### Code Quality

```bash
# Format code
poetry run black src tests

# Lint code
poetry run ruff check src tests

# Type checking
poetry run mypy src
```

## Dependencies

### Core Dependencies

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `aio-pika` - Async RabbitMQ client
- `azure-storage-blob` - Azure Blob Storage client
- `openai` - Azure OpenAI client
- `qdrant-client` - Qdrant vector database client
- `pydantic` & `pydantic-settings` - Configuration and validation
- `httpx` - HTTP client for API Core

### Document Processing

- `pypdf2` - PDF parsing
- `python-docx` - DOCX parsing
- `tiktoken` - Token counting

## Integration Points

1. **API Core**: Status updates via HTTP
2. **Azure Blob Storage**: File downloads
3. **Azure OpenAI**: Embedding generation
4. **Qdrant**: Vector storage
5. **RabbitMQ**: Message queue

## Monitoring

- Health checks: `/health` and `/ready`
- Structured logging (JSON in production)
- Error tracking via custom exceptions

## Next Steps

1. Implement Phase 2: Message Queue Integration
2. Set up RabbitMQ queues and exchanges
3. Create worker for processing messages
4. Integrate with API Core for status updates

## Documentation

- Full implementation plan: `docs/orchestrator/DOCUMENT_INGESTION_ARCHITECTURE.md`
- File storage architecture: `docs/orchestrator/FILE_STORAGE_ARCHITECTURE.md`

