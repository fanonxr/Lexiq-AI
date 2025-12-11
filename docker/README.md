# Docker Configuration

This directory contains Docker-related configurations for local development.

## Structure

- **`postgres/`** - PostgreSQL initialization scripts
  - `init.sql` - Database initialization script
- **`redis/`** - Redis configuration
  - `redis.conf` - Redis configuration file (optional)

## Local Development

For local development, use `docker-compose.yml` in the project root.

### Quick Start

```bash
# Start all services
make docker-up

# Or use the setup script
make docker-setup

# View logs
make docker-logs

# Stop services
make docker-down
```

### Services

- **PostgreSQL** (port 5432) - Relational database
- **Redis** (port 6379) - Cache and conversation state
- **Qdrant** (ports 6333/6334) - Vector database for RAG

### Customization

1. Copy `.env.example` to `.env.local` and customize
2. Copy `docker-compose.override.yml.example` to `docker-compose.override.yml` for service-specific overrides

## Production

Production images are built in CI/CD and pushed to Azure Container Registry (ACR).

