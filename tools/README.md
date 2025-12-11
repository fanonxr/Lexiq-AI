# Development Tools

This directory contains scripts and utilities for local development and operations.

## Structure

- **`scripts/`** - Development and deployment scripts
  - Docker setup scripts
  - Database migration helpers
  - Local development utilities
  - Ngrok tunnel setup for Twilio webhooks

## Scripts

### Docker Setup

- `docker-setup.sh` - Initialize and start local Docker Compose environment
- `docker-health-check.sh` - Verify local services are running correctly

### Database

- `db-migrate.sh` - Run Alembic migrations
- `db-seed.sh` - Seed development database with test data

### Development

- `ngrok-setup.sh` - Set up Ngrok tunnel for local Twilio webhooks
- `env-template.sh` - Generate .env files from templates

## Usage

Scripts are designed to be run from the project root:

```bash
./tools/scripts/docker-setup.sh
```

