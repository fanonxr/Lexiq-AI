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

### Deployment (Dev)

- **`deploy-dev.sh`** - Backend: build Docker images, push to Azure Container Registry, update Azure Container Apps
- **`deploy-frontend-dev.sh`** - Frontend: build Next.js (static export), deploy to Azure Static Web App

Run from project root via Make:

```bash
# Backend (Container Apps)
make deploy-build      # Build all backend images
make deploy-push       # Push to ACR
make deploy-update     # Update Container Apps
make deploy-all        # Build, push, and update

# Frontend (Static Web App)
make deploy-frontend-build   # Build Next.js to apps/web-frontend/out
make deploy-frontend-deploy  # Deploy to Azure Static Web App
make deploy-frontend         # Build and deploy
```

Prerequisites: Azure CLI logged in (`az login`), ACR access for backend, Static Web App resource for frontend.

## Usage

Scripts are designed to be run from the project root:

```bash
./tools/scripts/docker-setup.sh
```

