# Load environment variables from .env.local if it exists
ifneq (,$(wildcard .env.local))
    include .env.local
    export
endif

.PHONY: help docker-up docker-down docker-logs docker-clean docker-build docker-build-api-core docker-build-no-cache install test format lint terraform-init terraform-plan terraform-apply terraform-destroy frontend-dev frontend-build frontend-start frontend-install migrate-init migrate-create migrate-up migrate-up-local migrate-up-azure migrate-down migrate-current migrate-history migrate-stamp

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Docker Compose commands
# Use docker compose (v2) if available, fallback to docker-compose (v1)
DOCKER_COMPOSE := $(shell which docker-compose 2>/dev/null || echo "docker compose")

docker-up: ## Start local development services (PostgreSQL, Redis, Qdrant)
	$(DOCKER_COMPOSE) up -d

docker-down: ## Stop local development services
	$(DOCKER_COMPOSE) down

docker-logs: ## View logs from local services
	$(DOCKER_COMPOSE) logs -f

docker-logs-service: ## View logs for a specific service (usage: make docker-logs-service SERVICE=postgres)
	$(DOCKER_COMPOSE) logs -f $(SERVICE)

docker-clean: ## Remove containers and volumes
	$(DOCKER_COMPOSE) down -v

docker-ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

docker-restart: ## Restart all services
	$(DOCKER_COMPOSE) restart

docker-setup: ## Initialize Docker environment and verify services
	@chmod +x tools/scripts/docker-setup.sh
	@tools/scripts/docker-setup.sh

docker-health: ## Check health status of all services
	$(DOCKER_COMPOSE) ps

docker-build: ## Build all Docker images
	$(DOCKER_COMPOSE) build

docker-build-api-core: ## Build api-core Docker image
	$(DOCKER_COMPOSE) build api-core

docker-build-no-cache: ## Build all Docker images without using cache
	$(DOCKER_COMPOSE) build --no-cache

docker-build-api-core-no-cache: ## Build api-core Docker image without using cache
	$(DOCKER_COMPOSE) build --no-cache api-core

docker-rebuild: ## Rebuild and restart all services
	$(DOCKER_COMPOSE) up -d --build

docker-rebuild-api-core: ## Rebuild and restart api-core service
	$(DOCKER_COMPOSE) up -d --build api-core

# Installation
install: ## Install dependencies for all services
	cd apps/web-frontend && npm install
	@echo "Install Python dependencies manually: pip install -r requirements.txt"

# Frontend commands
frontend-install: ## Install frontend dependencies
	cd apps/web-frontend && npm install

frontend-dev: ## Start frontend development server
	cd apps/web-frontend && npm run dev

frontend-build: ## Build frontend for production
	cd apps/web-frontend && npm run build

frontend-start: ## Start frontend production server
	cd apps/web-frontend && npm run start

# Testing
test: ## Run tests (placeholder)
	@echo "Running tests..."
	# Add test commands here

# Code quality
format: ## Format code
	@echo "Formatting code..."
	# Add formatting commands here (prettier, black, gofmt, etc.)

lint: ## Lint code
	@echo "Linting code..."
	cd apps/web-frontend && npm run lint
	# Add other lint commands here

# Terraform commands
# Source .env.local to load TF_VAR_* environment variables
terraform-init: ## Initialize Terraform
	@bash -c 'if [ -f .env.local ]; then set -a; source .env.local; set +a; fi; cd infra/terraform && terraform init'

terraform-plan: ## Run Terraform plan (dev environment)
	@bash -c 'if [ -f .env.local ]; then set -a; source .env.local; set +a; fi; cd infra/terraform && terraform plan -var-file=dev.tfvars'

terraform-apply: ## Apply Terraform changes (dev environment)
	@bash -c 'if [ -f .env.local ]; then set -a; source .env.local; set +a; fi; cd infra/terraform && terraform apply -var-file=dev.tfvars'

terraform-destroy: ## Destroy Terraform resources (dev environment)
	@bash -c 'if [ -f .env.local ]; then set -a; source .env.local; set +a; fi; cd infra/terraform && terraform destroy -var-file=dev.tfvars'

terraform-validate: ## Validate Terraform configuration
	cd infra/terraform && terraform validate

terraform-fmt: ## Format Terraform files
	cd infra/terraform && terraform fmt -recursive

# Database Migrations (Alembic)
# All migration commands run from apps/api-core directory
# Uses virtual environment if available, otherwise uses system Python
# DATABASE_URL must be set as environment variable

# Detect virtual environment
VENV_PATH := apps/api-core/.venv
VENV_ACTIVATE := $(VENV_PATH)/bin/activate
VENV_PYTHON := $(VENV_PATH)/bin/python
VENV_ALEMBIC := $(VENV_PATH)/bin/alembic

# Use venv if it exists, otherwise use system commands
# Note: When running commands, we cd into apps/api-core first, so paths are relative to that
ifeq ($(wildcard $(VENV_ACTIVATE)),)
	ALEMBIC_CMD := alembic
else
	ALEMBIC_CMD := .venv/bin/alembic
endif

venv-setup: ## Set up Python virtual environment for api-core
	@echo "Setting up Python virtual environment..."
	cd apps/api-core && python3 -m venv .venv
	@echo "✓ Virtual environment created at apps/api-core/.venv"
	@echo "Activate it with: source apps/api-core/.venv/bin/activate"
	@echo "Or install dependencies with: make venv-install"

venv-install: ## Install dependencies in virtual environment
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "Virtual environment not found. Creating it..."; \
		$(MAKE) venv-setup; \
	fi
	@echo "Installing dependencies..."
	cd apps/api-core && .venv/bin/python -m pip install --upgrade pip
	cd apps/api-core && .venv/bin/python -m pip install -r requirements.txt
	@echo "✓ Dependencies installed"

venv-activate: ## Show instructions to activate virtual environment
	cd apps/api-core && source .venv/bin/activate

migrate-init: ## Initialize Alembic migrations (first time setup)
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Creating it..."; \
		$(MAKE) venv-setup; \
		$(MAKE) venv-install; \
	fi
	@echo "Initializing Alembic migrations..."
	@if [ ! -d "apps/api-core/migrations" ]; then \
		cd apps/api-core && $(ALEMBIC_CMD) init migrations; \
		echo "Replacing default env.py with custom version..."; \
		if [ -f "apps/api-core/migrations/env.py.example" ]; then \
			cp apps/api-core/migrations/env.py.example apps/api-core/migrations/env.py; \
			echo "✓ env.py configured from example"; \
		fi; \
	else \
		echo "Migrations directory already exists."; \
		if [ ! -f "apps/api-core/migrations/script.py.mako" ]; then \
			echo "⚠️  script.py.mako missing. Reinitializing migrations directory..."; \
			cd apps/api-core && rm -rf migrations && $(ALEMBIC_CMD) init migrations; \
			if [ -f "apps/api-core/migrations/env.py.example" ]; then \
				cp apps/api-core/migrations/env.py.example apps/api-core/migrations/env.py; \
			fi; \
		fi; \
		if [ ! -f "apps/api-core/migrations/env.py" ] || ! grep -q "api_core.config" apps/api-core/migrations/env.py 2>/dev/null; then \
			if [ -f "apps/api-core/migrations/env.py.example" ]; then \
				echo "Updating env.py with custom configuration..."; \
				cp apps/api-core/migrations/env.py.example apps/api-core/migrations/env.py; \
				echo "✓ env.py updated"; \
			fi; \
		fi; \
	fi
	@echo "✓ Alembic initialized"

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="description")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Usage: make migrate-create MESSAGE='description'"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "⚠️  DATABASE_URL not set. Using local Docker default for autogenerate..."; \
		cd apps/api-core && DATABASE_URL="postgresql://admin:password@localhost:5432/lexiqai_local" $(ALEMBIC_CMD) revision --autogenerate -m "$(MESSAGE)"; \
	else \
		cd apps/api-core && $(ALEMBIC_CMD) revision --autogenerate -m "$(MESSAGE)"; \
	fi

migrate-up: ## Apply all pending migrations (uses DATABASE_URL from environment)
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Error: DATABASE_URL environment variable is not set"; \
		echo "For local: export DATABASE_URL='postgresql://admin:password@localhost:5432/lexiqai_local'"; \
		echo "For Azure: export DATABASE_URL='postgresql://user@server:pass@server.postgres.database.azure.com:5432/dbname?sslmode=require'"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	cd apps/api-core && $(ALEMBIC_CMD) upgrade head

migrate-up-local: ## Apply migrations to local Docker PostgreSQL
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	@echo "Applying migrations to local Docker PostgreSQL..."
	cd apps/api-core && DATABASE_URL="postgresql://admin:password@localhost:5432/lexiqai_local" $(ALEMBIC_CMD) upgrade head

migrate-up-docker: ## Apply migrations from inside Docker container
	@echo "Applying migrations from inside Docker container..."
	$(DOCKER_COMPOSE) exec api-core bash -c "cd /app && alembic upgrade head"

migrate-up-azure: ## Apply migrations to Azure PostgreSQL (requires DATABASE_URL set)
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Error: DATABASE_URL environment variable is not set"; \
		echo "Example: export DATABASE_URL='postgresql://user@server:pass@server.postgres.database.azure.com:5432/dbname?sslmode=require'"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	@echo "Applying migrations to Azure PostgreSQL..."
	@echo "⚠️  Make sure your IP is allowed in Azure PostgreSQL firewall rules"
	cd apps/api-core && $(ALEMBIC_CMD) upgrade head

migrate-down: ## Rollback last migration (usage: make migrate-down STEPS=1)
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Error: DATABASE_URL environment variable is not set"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	cd apps/api-core && $(ALEMBIC_CMD) downgrade -$(or $(STEPS),1)

migrate-current: ## Show current migration version
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Error: DATABASE_URL environment variable is not set"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	cd apps/api-core && $(ALEMBIC_CMD) current

migrate-history: ## Show migration history
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	cd apps/api-core && $(ALEMBIC_CMD) history

migrate-stamp: ## Mark database as being at a specific revision (usage: make migrate-stamp REVISION=abc123)
	@if [ -z "$(REVISION)" ]; then \
		echo "Error: REVISION is required. Usage: make migrate-stamp REVISION=abc123"; \
		exit 1; \
	fi
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "Error: DATABASE_URL environment variable is not set"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	cd apps/api-core && $(ALEMBIC_CMD) stamp $(REVISION)

# Development utilities
clean: ## Clean build artifacts and temporary files
	find . -type d -name node_modules -prune -o -type d -name .next -prune -o -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

