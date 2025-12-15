# API Core Service

**Python FastAPI service for authentication, user management, and billing**

## Overview

The API Core service handles:
- User authentication and authorization
- User profile management
- Billing and subscription logic
- Dashboard data APIs

## Technology Stack

- **Framework:** FastAPI 0.104+
- **Language:** Python 3.11+
- **Authentication:** Microsoft Entra External ID (Azure AD B2C)
- **Database:** PostgreSQL (via shared `libs/database`)
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic
- **Validation:** Pydantic v2
- **Testing:** pytest, pytest-asyncio, httpx
- **Code Quality:** black, ruff, mypy

## Project Structure

```
apps/api-core/
├── .env.example              # Environment variables template
├── .gitignore                # Python-specific gitignore
├── pyproject.toml           # Python project configuration (Poetry)
├── requirements.txt         # Production dependencies (pip alternative)
├── requirements-dev.txt     # Development dependencies
├── alembic.ini              # Alembic configuration
├── README.md                # This file
├── src/
│   └── api_core/
│       ├── __init__.py
│       ├── main.py          # FastAPI application entry point
│       ├── config.py         # Configuration management
│       ├── dependencies.py   # FastAPI dependencies
│       ├── middleware.py     # Custom middleware
│       ├── exceptions.py     # Custom exception handlers
│       ├── api/
│       │   ├── v1/
│       │   │   ├── router.py # API router aggregation
│       │   │   ├── auth.py   # Authentication endpoints
│       │   │   ├── users.py  # User management endpoints
│       │   │   ├── billing.py # Billing endpoints
│       │   │   └── dashboard.py # Dashboard endpoints
│       ├── models/          # Pydantic models (request/response)
│       ├── services/        # Business logic layer
│       ├── repositories/     # Data access layer
│       ├── auth/            # Authentication utilities
│       ├── database/        # Database connection and session management
│       └── utils/           # Utility functions
├── tests/                   # Test files
└── migrations/              # Alembic migrations
    └── versions/
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip
- Docker and Docker Compose (for local dependencies)

### Option 1: Using Poetry (Recommended)

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   cd apps/api-core
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
   uvicorn api_core.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Option 2: Using pip

1. **Create virtual environment**:
   ```bash
   cd apps/api-core
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
   uvicorn api_core.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Using Docker Compose

The service is included in the root `docker-compose.yml`. To start all services:

```bash
# From project root
make docker-up

# Or directly
docker compose up -d
```

The API Core service will be available at `http://localhost:8000`.

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
pytest --cov=api_core --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

### Database Migrations

**Using Make commands (recommended):**
```bash
# Apply migrations to local Docker PostgreSQL
make migrate-up-local

# Apply migrations from inside Docker container
make migrate-up-docker

# Apply migrations to Azure (set DATABASE_URL first)
export DATABASE_URL="postgresql://user@server:pass@server.postgres.database.azure.com:5432/dbname?sslmode=require"
make migrate-up-azure

# Create a new migration
make migrate-create MESSAGE="description of changes"

# Check current migration version
make migrate-current

# View migration history
make migrate-history

# Rollback last migration
make migrate-down STEPS=1
```

**Using Alembic directly:**
```bash
# Set DATABASE_URL first
export DATABASE_URL="postgresql://admin:password@localhost:5432/lexiqai_local"

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

See [MIGRATIONS.md](./MIGRATIONS.md) for detailed migration guide.

## API Documentation

Once the server is running, API documentation is available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Health Checks

- **Health:** `GET /health`
- **Readiness:** `GET /ready`

## Status

🚧 **In Development** - Currently implementing Phase 1: Project Foundation & Setup

## Documentation

- [Implementation Plan](/docs/backend/implementation-plan.md) - Detailed step-by-step implementation plan
- [System Design](/docs/design/system-design.md) - Architecture details (when available)

## Configuration

The application uses `pydantic-settings` for configuration management. All settings are loaded from environment variables with validation.

### Environment Variables

See `.env.example` for all available environment variables. Key variables:

**Application:**
- `APP_NAME` - Application name (default: `api-core`)
- `APP_ENV` - Environment: `development`, `staging`, or `production` (default: `development`)
- `DEBUG` - Enable debug mode (default: `false`)
- `LOG_LEVEL` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default: `INFO`)

**Server:**
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8000`)

**Database:**
- `DATABASE_URL` - PostgreSQL connection string (required)
- `DATABASE_POOL_SIZE` - Connection pool size (default: `10`)
- `DATABASE_MAX_OVERFLOW` - Maximum pool overflow (default: `20`)

**Redis:**
- `REDIS_URL` - Redis connection URL (default: `redis://localhost:6379/0`)
- `REDIS_PASSWORD` - Redis password (optional)

**Azure AD B2C:**
- `AZURE_AD_B2C_TENANT_ID` - Azure AD B2C tenant ID
- `AZURE_AD_B2C_CLIENT_ID` - Azure AD B2C client ID
- `AZURE_AD_B2C_CLIENT_SECRET` - Azure AD B2C client secret
- `AZURE_AD_B2C_POLICY_SIGNUP_SIGNIN` - Sign-up/sign-in policy name
- `AZURE_AD_B2C_INSTANCE` - Instance URL template (default: `https://{tenant}.b2clogin.com`)

**Azure Key Vault (Production):**
- `AZURE_KEY_VAULT_URL` - Azure Key Vault URL
- `AZURE_KEY_VAULT_ENABLED` - Enable Key Vault integration (default: `false`)

**JWT:**
- `JWT_SECRET_KEY` - JWT secret key (required in production)
- `JWT_ALGORITHM` - JWT algorithm (default: `HS256`)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: `30`)

**CORS:**
- `CORS_ORIGINS` - Comma-separated list of allowed origins (default: `http://localhost:3000`)

**API:**
- `API_V1_PREFIX` - API v1 prefix (default: `/api/v1`)

### Using Configuration in Code

```python
from api_core.config import get_settings, settings

# Use the global settings instance
settings = get_settings()

# Access configuration
db_url = settings.database.url
jwt_secret = settings.jwt.secret_key
cors_origins = settings.cors.origins

# Check environment
if settings.is_production:
    # Production-specific logic
    pass
```

### Azure Key Vault Integration

In production, secrets can be loaded from Azure Key Vault:

1. Set `AZURE_KEY_VAULT_URL` and `AZURE_KEY_VAULT_ENABLED=true`
2. The application will automatically load secrets from Key Vault
3. Secrets are loaded after initial settings creation
4. Supported secrets:
   - `database-url` - Database connection string
   - `jwt-secret-key` - JWT secret key
   - `azure-ad-b2c-client-secret` - Azure AD B2C client secret

### Production Validation

The configuration system validates production settings:
- JWT secret key must not be the default value
- Debug mode must be disabled
- Warnings for missing Azure Key Vault configuration

## Contributing

See [CONTRIBUTING.md](/CONTRIBUTING.md) for development workflow and contribution guidelines.

