# Load environment variables from .env.local if it exists
ifneq (,$(wildcard .env.local))
    include .env.local
    export
endif

.PHONY: help docker-up docker-down docker-logs docker-clean docker-build docker-build-api-core docker-build-cognitive-orch docker-build-document-ingestion docker-build-no-cache install test format lint terraform-init terraform-plan terraform-apply terraform-destroy frontend-dev frontend-build frontend-start frontend-install migrate-init migrate-create migrate-up migrate-up-local migrate-up-azure migrate-down migrate-current migrate-history migrate-stamp orch-venv-setup orch-venv-install orch-dev orch-test orch-format orch-lint orch-type-check ingestion-venv-setup ingestion-venv-install ingestion-dev ingestion-test ingestion-format ingestion-lint ingestion-type-check proto-compile

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

docker-build-cognitive-orch: ## Build cognitive-orch Docker image
	$(DOCKER_COMPOSE) build cognitive-orch

docker-build-cognitive-orch-no-cache: ## Build cognitive-orch Docker image without using cache
	$(DOCKER_COMPOSE) build --no-cache cognitive-orch

docker-build-document-ingestion: ## Build document-ingestion Docker image
	$(DOCKER_COMPOSE) build document-ingestion

docker-build-document-ingestion-no-cache: ## Build document-ingestion Docker image without using cache
	$(DOCKER_COMPOSE) build --no-cache document-ingestion

docker-rebuild: ## Rebuild and restart all services
	$(DOCKER_COMPOSE) up -d --build

docker-rebuild-api-core: ## Rebuild and restart api-core service
	$(DOCKER_COMPOSE) up -d --build api-core

docker-rebuild-cognitive-orch: ## Rebuild and restart cognitive-orch service
	$(DOCKER_COMPOSE) up -d --build cognitive-orch

docker-rebuild-document-ingestion: ## Rebuild and restart document-ingestion service
	$(DOCKER_COMPOSE) up -d --build document-ingestion

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

api-venv-setup: ## Set up Python virtual environment for api-core
	@echo "Setting up Python virtual environment..."
	cd apps/api-core && python3 -m venv .venv
	@echo "✓ Virtual environment created at apps/api-core/.venv"
	@echo "Activate it with: source apps/api-core/.venv/bin/activate"
	@echo "Or install dependencies with: make venv-install"

api-venv-install: ## Install dependencies in virtual environment
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "Virtual environment not found. Creating it..."; \
		$(MAKE) venv-setup; \
	fi
	@echo "Installing dependencies..."
	cd apps/api-core && .venv/bin/python -m pip install --upgrade pip
	cd apps/api-core && .venv/bin/python -m pip install -r requirements.txt
	@echo "✓ Dependencies installed"

api-venv-activate: ## Show instructions to activate virtual environment
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

# Cognitive Orchestrator commands
# Virtual environment paths
ORCH_VENV_PATH := apps/cognitive-orch/.venv
ORCH_VENV_ACTIVATE := $(ORCH_VENV_PATH)/bin/activate
ORCH_VENV_PYTHON := $(ORCH_VENV_PATH)/bin/python

# Use venv if it exists, otherwise use system commands
ifeq ($(wildcard $(ORCH_VENV_ACTIVATE)),)
	ORCH_UVICORN_CMD := uvicorn
	ORCH_PYTEST_CMD := pytest
	ORCH_BLACK_CMD := black
	ORCH_RUFF_CMD := ruff
	ORCH_MYPY_CMD := mypy
else
	ORCH_UVICORN_CMD := .venv/bin/uvicorn
	ORCH_PYTEST_CMD := .venv/bin/pytest
	ORCH_BLACK_CMD := .venv/bin/black
	ORCH_RUFF_CMD := .venv/bin/ruff
	ORCH_MYPY_CMD := .venv/bin/mypy
endif

orch-venv-setup: ## Set up Python virtual environment for cognitive-orch
	@echo "Setting up Python virtual environment for Cognitive Orchestrator..."
	cd apps/cognitive-orch && python3 -m venv .venv
	@echo "✓ Virtual environment created at apps/cognitive-orch/.venv"
	@echo "Activate it with: source apps/cognitive-orch/.venv/bin/activate"
	@echo "Or install dependencies with: make orch-venv-install"

orch-venv-install: ## Install dependencies in cognitive-orch virtual environment
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "Virtual environment not found. Creating it..."; \
		$(MAKE) orch-venv-setup; \
	fi
	@echo "Installing dependencies for Cognitive Orchestrator..."
	cd apps/cognitive-orch && .venv/bin/python -m pip install --upgrade pip
	cd apps/cognitive-orch && .venv/bin/python -m pip install -r requirements-dev.txt
	@echo "✓ Dependencies installed"

orch-dev: ## Run cognitive-orch development server
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Creating it..."; \
		$(MAKE) orch-venv-setup; \
		$(MAKE) orch-venv-install; \
	fi
	@echo "Starting Cognitive Orchestrator development server..."
	@echo "Server will be available at http://localhost:8001"
	@echo "API docs will be available at http://localhost:8001/docs"
	cd apps/cognitive-orch && PYTHONPATH=src .venv/bin/uvicorn cognitive_orch.main:app --reload --host 0.0.0.0 --port 8001

orch-test: ## Run cognitive-orch tests
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make orch-venv-setup && make orch-venv-install' first"; \
		exit 1; \
	fi
	@echo "Running Cognitive Orchestrator tests..."
	cd apps/cognitive-orch && PYTHONPATH=src .venv/bin/pytest tests/ -v

orch-test-cov: ## Run cognitive-orch tests with coverage
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make orch-venv-setup && make orch-venv-install' first"; \
		exit 1; \
	fi
	@echo "Running Cognitive Orchestrator tests with coverage..."
	cd apps/cognitive-orch && PYTHONPATH=src .venv/bin/pytest tests/ --cov=cognitive_orch --cov-report=html --cov-report=term-missing

orch-format: ## Format cognitive-orch code with black
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make orch-venv-setup && make orch-venv-install' first"; \
		exit 1; \
	fi
	@echo "Formatting Cognitive Orchestrator code..."
	cd apps/cognitive-orch && .venv/bin/black src/ tests/

orch-lint: ## Lint cognitive-orch code with ruff
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make orch-venv-setup && make orch-venv-install' first"; \
		exit 1; \
	fi
	@echo "Linting Cognitive Orchestrator code..."
	cd apps/cognitive-orch && .venv/bin/ruff check --fix src/ tests/

orch-type-check: ## Type check cognitive-orch code with mypy
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make orch-venv-setup && make orch-venv-install' first"; \
		exit 1; \
	fi
	@echo "Type checking Cognitive Orchestrator code..."
	cd apps/cognitive-orch && PYTHONPATH=src .venv/bin/mypy src/

orch-check: ## Run all code quality checks (format, lint, type-check)
	@echo "Running all code quality checks for Cognitive Orchestrator..."
	$(MAKE) orch-format
	$(MAKE) orch-lint
	$(MAKE) orch-type-check

orch-health: ## Check cognitive-orch service health
	@echo "Checking Cognitive Orchestrator health..."
	@curl -s http://localhost:8001/health | python3 -m json.tool || echo "Service not running or not accessible"

orch-ready: ## Check cognitive-orch service readiness
	@echo "Checking Cognitive Orchestrator readiness..."
	@curl -s http://localhost:8001/ready | python3 -m json.tool || echo "Service not running or not accessible"

# Document Ingestion Service commands
# Virtual environment paths
INGESTION_VENV_PATH := apps/document-ingestion/.venv
INGESTION_VENV_ACTIVATE := $(INGESTION_VENV_PATH)/bin/activate
INGESTION_VENV_PYTHON := $(INGESTION_VENV_PATH)/bin/python

# Use venv if it exists, otherwise use system commands
ifeq ($(wildcard $(INGESTION_VENV_ACTIVATE)),)
	INGESTION_UVICORN_CMD := uvicorn
	INGESTION_PYTEST_CMD := pytest
	INGESTION_BLACK_CMD := black
	INGESTION_RUFF_CMD := ruff
	INGESTION_MYPY_CMD := mypy
else
	INGESTION_UVICORN_CMD := .venv/bin/uvicorn
	INGESTION_PYTEST_CMD := .venv/bin/pytest
	INGESTION_BLACK_CMD := .venv/bin/black
	INGESTION_RUFF_CMD := .venv/bin/ruff
	INGESTION_MYPY_CMD := .venv/bin/mypy
endif

ingestion-venv-setup: ## Set up Python virtual environment for document-ingestion
	@echo "Setting up Python virtual environment for Document Ingestion Service..."
	cd apps/document-ingestion && python3 -m venv .venv
	@echo "✓ Virtual environment created at apps/document-ingestion/.venv"
	@echo "Activate it with: source apps/document-ingestion/.venv/bin/activate"
	@echo "Or install dependencies with: make ingestion-venv-install"

ingestion-venv-install: ## Install dependencies in document-ingestion virtual environment
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "Virtual environment not found. Creating it..."; \
		$(MAKE) ingestion-venv-setup; \
	fi
	@echo "Installing dependencies for Document Ingestion Service..."
	cd apps/document-ingestion && .venv/bin/python -m pip install --upgrade pip
	cd apps/document-ingestion && .venv/bin/python -m pip install -r requirements-dev.txt
	@echo "✓ Dependencies installed"

ingestion-dev: ## Run document-ingestion development server
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Creating it..."; \
		$(MAKE) ingestion-venv-setup; \
		$(MAKE) ingestion-venv-install; \
	fi
	@echo "Starting Document Ingestion Service development server..."
	@echo "Server will be available at http://localhost:8003"
	@echo "API docs will be available at http://localhost:8003/docs"
	cd apps/document-ingestion && PYTHONPATH=src .venv/bin/uvicorn document_ingestion.main:app --reload --host 0.0.0.0 --port 8003

ingestion-test: ## Run document-ingestion tests
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make ingestion-venv-setup && make ingestion-venv-install' first"; \
		exit 1; \
	fi
	@echo "Running Document Ingestion Service tests..."
	cd apps/document-ingestion && PYTHONPATH=src .venv/bin/pytest tests/ -v

ingestion-test-cov: ## Run document-ingestion tests with coverage
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make ingestion-venv-setup && make ingestion-venv-install' first"; \
		exit 1; \
	fi
	@echo "Running Document Ingestion Service tests with coverage..."
	cd apps/document-ingestion && PYTHONPATH=src .venv/bin/pytest tests/ --cov=document_ingestion --cov-report=html --cov-report=term-missing

ingestion-format: ## Format document-ingestion code with black
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make ingestion-venv-setup && make ingestion-venv-install' first"; \
		exit 1; \
	fi
	@echo "Formatting Document Ingestion Service code..."
	cd apps/document-ingestion && .venv/bin/black src/ tests/

ingestion-lint: ## Lint document-ingestion code with ruff
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make ingestion-venv-setup && make ingestion-venv-install' first"; \
		exit 1; \
	fi
	@echo "Linting Document Ingestion Service code..."
	cd apps/document-ingestion && .venv/bin/ruff check --fix src/ tests/

ingestion-type-check: ## Type check document-ingestion code with mypy
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make ingestion-venv-setup && make ingestion-venv-install' first"; \
		exit 1; \
	fi
	@echo "Type checking Document Ingestion Service code..."
	cd apps/document-ingestion && PYTHONPATH=src .venv/bin/mypy src/

ingestion-check: ## Run all code quality checks (format, lint, type-check)
	@echo "Running all code quality checks for Document Ingestion Service..."
	$(MAKE) ingestion-format
	$(MAKE) ingestion-lint
	$(MAKE) ingestion-type-check

ingestion-health: ## Check document-ingestion service health
	@echo "Checking Document Ingestion Service health..."
	@curl -s http://localhost:8003/health | python3 -m json.tool || echo "Service not running or not accessible"

ingestion-ready: ## Check document-ingestion service readiness
	@echo "Checking Document Ingestion Service readiness..."
	@curl -s http://localhost:8003/ready | python3 -m json.tool || echo "Service not running or not accessible"

# Protocol Buffer compilation
proto-compile: ## Compile Protocol Buffer definitions to Python stubs (compatible with protobuf 5.x)
	@echo "Compiling Protocol Buffers with protobuf 5.x compatibility..."
	@chmod +x scripts/compile_protos_compatible.sh
	@scripts/compile_protos_compatible.sh

# Development utilities
clean: ## Clean build artifacts and temporary files
	find . -type d -name node_modules -prune -o -type d -name .next -prune -o -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

