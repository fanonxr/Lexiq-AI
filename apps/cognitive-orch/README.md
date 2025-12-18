# Cognitive Orchestrator Service

**Python FastAPI service - The Brain of LexiqAI**

## Overview

The Cognitive Orchestrator service handles:
- Conversation state management in Redis
- RAG (Retrieval-Augmented Generation) - Vector search in Qdrant
- LLM routing via LiteLLM (Azure OpenAI, Anthropic, AWS Bedrock, Groq)
- Context persistence and management
- Tool execution and function calling (calendar booking, CRM operations)
- System prompt injection with firm-specific personas

## Technology Stack

- **Framework:** FastAPI 0.110+
- **Language:** Python 3.11+
- **LLM Router:** LiteLLM 1.34+
- **Vector Store:** Qdrant (via qdrant-client)
- **Cache:** Redis 5.0+ (async) for conversation state
- **Communication:** gRPC (from Voice Gateway) + HTTP REST (for testing/frontend)
- **Validation:** Pydantic v2
- **Retry Logic:** Tenacity 8.2+
- **Testing:** pytest, pytest-asyncio, httpx

## Project Structure

```
apps/cognitive-orch/
├── .env.example              # Environment variables template
├── .gitignore               # Python-specific gitignore
├── pyproject.toml           # Python project configuration (Poetry)
├── requirements.txt         # Production dependencies (pip alternative)
├── requirements-dev.txt     # Development dependencies
├── README.md                # This file
├── src/
│   └── cognitive_orch/
│       ├── __init__.py
│       ├── main.py          # FastAPI application entry point
│       ├── config.py         # Configuration management
│       ├── dependencies.py   # FastAPI dependencies
│       ├── api/              # HTTP REST endpoints
│       │   ├── __init__.py
│       │   ├── v1/
│       │   │   ├── __init__.py
│       │   │   ├── router.py # Main router
│       │   │   ├── health.py # Health checks
│       │   │   └── test.py   # Test endpoints
│       │   └── middleware.py
│       ├── grpc/             # gRPC service (from Voice Gateway)
│       │   ├── __init__.py
│       │   ├── server.py     # gRPC server setup
│       │   ├── handlers.py   # gRPC request handlers
│       │   └── proto/        # Generated proto files (from libs/proto)
│       ├── services/         # Business logic layer
│       │   ├── __init__.py
│       │   ├── llm_service.py      # LiteLLM wrapper
│       │   ├── state_service.py    # Redis conversation state
│       │   ├── rag_service.py      # Qdrant vector search
│       │   ├── tool_service.py     # Tool execution
│       │   └── prompt_service.py  # System prompt injection
│       ├── repositories/     # Data access layer (if needed)
│       │   ├── __init__.py
│       │   └── conversation_repo.py
│       ├── models/           # Pydantic models (request/response)
│       │   ├── __init__.py
│       │   ├── conversation.py
│       │   ├── request.py
│       │   ├── response.py
│       │   └── tools.py
│       └── utils/            # Utility functions
│           ├── __init__.py
│           ├── logging.py
│           ├── retry.py      # Tenacity retry logic
│           └── errors.py
└── tests/                    # Test files
    ├── __init__.py
    ├── conftest.py
    ├── test_llm_service.py
    ├── test_state_service.py
    ├── test_rag_service.py
    ├── test_tool_service.py
    └── integration/
        └── test_grpc_flow.py
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- Docker and Docker Compose (for local dependencies: Redis, Qdrant)

### Option 1: Using Poetry (Recommended)

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   cd apps/cognitive-orch
   poetry install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Activate virtual environment**:
   ```bash
   poetry shell
   ```

5. **Run the development server**:
   ```bash
   uvicorn cognitive_orch.main:app --reload --host 0.0.0.0 --port 8001
   ```

### Option 2: Using pip (with Virtual Environment)

1. **Create virtual environment**:
   ```bash
   cd apps/cognitive-orch
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the development server**:
   ```bash
   uvicorn cognitive_orch.main:app --reload --host 0.0.0.0 --port 8001
   ```

### Using Docker Compose

The service is included in the root `docker-compose.yml`. To start all services:

```bash
# From project root
make docker-up

# Or directly
docker compose up -d
```

The Cognitive Orchestrator service will be available at:
- **HTTP REST API:** `http://localhost:8001`
- **gRPC:** `localhost:50051`

## Development Commands

### Code Formatting

```bash
# Using black
black src/ tests/

# Using ruff
ruff check --fix src/ tests/
```

### Type Checking

```bash
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cognitive_orch --cov-report=html

# Run specific test file
pytest tests/test_llm_service.py
```

## API Documentation

Once the server is running, API documentation is available at:

- **Swagger UI:** http://localhost:8001/docs
- **ReDoc:** http://localhost:8001/redoc

## Health Checks

- **Health:** `GET /health`
- **Readiness:** `GET /ready`

## Status

🚧 **In Development** - Currently implementing Phase 1: Foundation & Configuration

## Documentation

- [Implementation Plan](/docs/orchestrator/orch-impl-plan.md) - Detailed step-by-step implementation plan
- [System Design](/docs/design/system-design.md) - Architecture details
- [Feature Plan](/docs/orchestrator/feature-plan.md) - Feature requirements

## Configuration

The application uses `pydantic-settings` for configuration management. All settings are loaded from environment variables with validation.

### Environment Variables

See `.env.example` for all available environment variables. Key variables:

**Application:**
- `APP_NAME` - Application name (default: `cognitive-orch`)
- `ENVIRONMENT` - Environment: `development`, `staging`, or `production` (default: `development`)
- `DEBUG` - Enable debug mode (default: `false`)
- `LOG_LEVEL` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default: `INFO`)

**Server:**
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - HTTP server port (default: `8001`)
- `GRPC_PORT` - gRPC server port (default: `50051`)

**LLM Configuration:**
- `DEFAULT_MODEL_NAME` - Default LLM model (e.g., `azure/gpt-4o`)
- `FALLBACK_MODEL_NAME` - Fallback LLM model (e.g., `anthropic/claude-3-haiku`)
- `ENABLE_FALLBACKS` - Enable fallback logic (default: `true`)

**Model Provider Credentials:**
- `AZURE_API_KEY` - Azure OpenAI API key
- `AZURE_API_BASE` - Azure OpenAI endpoint
- `AZURE_API_VERSION` - Azure OpenAI API version
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GROQ_API_KEY` - Groq API key (optional)
- `AWS_ACCESS_KEY_ID` - AWS access key for Bedrock (optional)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key for Bedrock (optional)
- `AWS_REGION` - AWS region for Bedrock (optional)

**Redis:**
- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379/0`)
- `REDIS_PASSWORD` - Redis password (optional)
- `CONVERSATION_TTL` - Conversation state TTL in seconds (default: `3600`)

**Qdrant:**
- `QDRANT_URL` - Qdrant connection URL (default: `http://localhost:6333`)
- `QDRANT_API_KEY` - Qdrant API key (optional, for Qdrant Cloud)

**Integration:**
- `CORE_API_URL` - Core API service URL (default: `http://localhost:8000`)
- `INTEGRATION_WORKER_URL` - Integration Worker service URL (default: `http://localhost:8002`)

**Context Window:**
- `MAX_CONTEXT_WINDOW` - Maximum context window size in tokens (default: `8000`)
- `MAX_HISTORY_MESSAGES` - Maximum number of messages to keep in history (default: `50`)

## Contributing

See [CONTRIBUTING.md](/CONTRIBUTING.md) for development workflow and contribution guidelines.

