# Load environment variables from .env if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

# Voice Gateway Commands

voice-gateway-build: ## Build voice-gateway binary
	@echo "Building Voice Gateway..."
	cd apps/voice-gateway && go build -o bin/voice-gateway ./cmd/server

voice-gateway-run: voice-gateway-build ## Run voice-gateway service
	@echo "Running Voice Gateway..."
	cd apps/voice-gateway && ./bin/voice-gateway

voice-gateway-lint: ## Lint voice-gateway code
	@echo "Linting Voice Gateway code..."
	cd apps/voice-gateway && golangci-lint run || echo "⚠️  golangci-lint not installed, skipping"

voice-gateway-fmt: ## Format voice-gateway code
	@echo "Formatting Voice Gateway code..."
	cd apps/voice-gateway && go fmt ./...

voice-gateway-vendor: ## Vendor voice-gateway dependencies
	@echo "Vendoring Voice Gateway dependencies..."
	cd apps/voice-gateway && go mod vendor

.PHONY: help docker-up docker-down docker-logs docker-clean docker-build docker-build-api-core docker-build-cognitive-orch docker-build-document-ingestion docker-build-voice-gateway docker-build-no-cache install test   api-core-test api-core-test-cov cognitive-orch-test document-ingestion-test integration-worker-test voice-gateway-test voice-gateway-test-cov format lint terraform-init terraform-plan terraform-apply terraform-destroy terraform-validate terraform-fmt terraform-import-discover terraform-import-discover-staging terraform-import-discover-prod terraform-import terraform-import-staging terraform-import-prod terraform-sync frontend-dev frontend-build frontend-start frontend-install migrate-init migrate-create migrate-up migrate-up-local migrate-up-azure migrate-down migrate-current migrate-history migrate-stamp db-reset db-reset-local orch-venv-setup orch-venv-install orch-dev orch-test orch-format orch-lint orch-type-check ingestion-venv-setup ingestion-venv-install ingestion-dev ingestion-test ingestion-format ingestion-lint ingestion-type-check voice-deps voice-build voice-run voice-test voice-test-cov voice-fmt voice-vet voice-lint voice-check voice-clean voice-health proto-compile proto-compile-go proto-clean-go generate-api-key generate-api-key-long generate-api-key-env generate-api-key-docker

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

docker-build-voice-gateway: ## Build voice-gateway Docker image
	$(DOCKER_COMPOSE) build voice-gateway

docker-build-voice-gateway-no-cache: ## Build voice-gateway Docker image without using cache
	$(DOCKER_COMPOSE) build --no-cache voice-gateway

docker-rebuild: ## Rebuild and restart all services
	$(DOCKER_COMPOSE) up -d --build

docker-rebuild-api-core: ## Rebuild and restart api-core service
	$(DOCKER_COMPOSE) up -d --build api-core

docker-rebuild-api-core-no-cache: ## Rebuild and restart api-core service without using cache
	$(DOCKER_COMPOSE) build --no-cache api-core

docker-rebuild-cognitive-orch: ## Rebuild and restart cognitive-orch service
	$(DOCKER_COMPOSE) up -d --build cognitive-orch

docker-rebuild-document-ingestion: ## Rebuild and restart document-ingestion service
	$(DOCKER_COMPOSE) up -d --build document-ingestion

docker-rebuild-voice-gateway: ## Rebuild and restart voice-gateway service
	$(DOCKER_COMPOSE) up -d --build voice-gateway

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

# Testing - Individual App Tests
api-core-test: ## Run api-core unit tests
	@echo "Running API Core tests..."
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Using Poetry..."; \
		(cd apps/api-core && poetry install --no-interaction --no-root >/dev/null 2>&1 || true && \
		 poetry install --no-interaction >/dev/null 2>&1 || true && \
		 PYTHONPATH=src:../../libs/py-common/src poetry run pytest tests/ -v --cov=api_core --cov-report=term-missing); \
	elif [ -d "apps/api-core/.venv" ]; then \
		echo "Using virtual environment..."; \
		(cd apps/api-core && .venv/bin/pip install -q -r requirements-dev.txt >/dev/null 2>&1 || true && \
		 PYTHONPATH=src:../../libs/py-common/src .venv/bin/pytest tests/ -v --cov=api_core --cov-report=term-missing); \
	else \
		echo "⚠️  Poetry not found and no venv. Installing dependencies with pip..."; \
		(cd apps/api-core && pip install -q -r requirements-dev.txt >/dev/null 2>&1 || true && \
		 PYTHONPATH=src:../../libs/py-common/src pytest tests/ -v --cov=api_core --cov-report=term-missing); \
	fi

api-core-test-cov: ## Run api-core tests with coverage report
	@echo "Running API Core tests with coverage..."
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Using Poetry..."; \
		(cd apps/api-core && poetry install --no-interaction --no-root >/dev/null 2>&1 || true && \
		 poetry install --no-interaction >/dev/null 2>&1 || true && \
		 PYTHONPATH=src:../../libs/py-common/src poetry run pytest tests/ -v --cov=api_core --cov-report=html --cov-report=term-missing); \
	elif [ -d "apps/api-core/.venv" ]; then \
		echo "Using virtual environment..."; \
		(cd apps/api-core && .venv/bin/pip install -q -r requirements-dev.txt >/dev/null 2>&1 || true && \
		 PYTHONPATH=src:../../libs/py-common/src .venv/bin/pytest tests/ -v --cov=api_core --cov-report=html --cov-report=term-missing); \
	else \
		echo "⚠️  Poetry not found and no venv. Installing dependencies with pip..."; \
		(cd apps/api-core && pip install -q -r requirements-dev.txt >/dev/null 2>&1 || true && \
		 PYTHONPATH=src:../../libs/py-common/src pytest tests/ -v --cov=api_core --cov-report=html --cov-report=term-missing); \
	fi
	@echo "Coverage report: apps/api-core/htmlcov/index.html"

cognitive-orch-test: ## Run cognitive-orch unit tests
	@echo "Running Cognitive Orchestrator tests..."
	@if [ ! -f "$(ORCH_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make orch-venv-setup && make orch-venv-install' first"; \
		exit 1; \
	fi
	@(cd apps/cognitive-orch && PYTHONPATH=src:../../libs/py-common/src .venv/bin/pytest tests/ -v --cov=cognitive_orch --cov-report=term-missing)

document-ingestion-test: ## Run document-ingestion unit tests
	@echo "Running Document Ingestion tests..."
	@if [ ! -f "$(INGESTION_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make ingestion-venv-setup && make ingestion-venv-install' first"; \
		exit 1; \
	fi
	@(cd apps/document-ingestion && PYTHONPATH=src:../../libs/py-common/src .venv/bin/pytest tests/ -v --cov=document_ingestion --cov-report=term-missing)

integration-worker-test: ## Run integration-worker unit tests
	@echo "Running Integration Worker tests..."
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@(cd apps/integration-worker && PYTHONPATH=src:../api-core/src:../../libs/py-common/src .venv/bin/pytest tests/ -v --cov=integration_worker --cov-report=term-missing)

voice-gateway-test: ## Run voice-gateway unit tests
	@echo "Running Voice Gateway tests..."
	@(cd apps/voice-gateway && go test ./... -v -race)

voice-gateway-test-cov: ## Run voice-gateway tests with coverage
	@echo "Running Voice Gateway tests with coverage..."
	@(cd apps/voice-gateway && go test ./... -v -race -coverprofile=coverage.out -covermode=atomic && \
	  go tool cover -html=coverage.out -o coverage.html)
	@echo "Coverage report generated: apps/voice-gateway/coverage.html"

# Testing - Run All Tests
test-all: ## Run all unit tests for all applications
	@echo "========================================="
	@echo "Running all unit tests..."
	@echo "========================================="
	@echo ""
	@echo "1. Testing API Core..."
	@$(MAKE) api-core-test || (echo "❌ API Core tests failed" && exit 1)
	@echo ""
	@echo "2. Testing Cognitive Orchestrator..."
	@$(MAKE) cognitive-orch-test || (echo "❌ Cognitive Orchestrator tests failed" && exit 1)
	@echo ""
	@echo "3. Testing Document Ingestion..."
	@$(MAKE) document-ingestion-test || (echo "❌ Document Ingestion tests failed" && exit 1)
	@echo ""
	@echo "4. Testing Integration Worker..."
	@$(MAKE) integration-worker-test || (echo "❌ Integration Worker tests failed" && exit 1)
	@echo ""
	@echo "5. Testing Voice Gateway..."
	@$(MAKE) voice-gateway-test || (echo "❌ Voice Gateway tests failed" && exit 1)
	@echo ""
	@echo "========================================="
	@echo "✅ All tests passed!"
	@echo "========================================="

test: test-all ## Alias for test-all

# Code quality
format: ## Format code
	@echo "Formatting code..."
	# Add formatting commands here (prettier, black, gofmt, etc.)

lint: ## Lint code
	@echo "Linting code..."
	cd apps/web-frontend && npm run lint
	# Add other lint commands here

# Terraform commands
# All commands source .env for TF_VAR_* environment variables and use dev.tfvars
terraform-init: ## Initialize Terraform
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform init'

terraform-plan: ## Run Terraform plan (dev environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform plan -var-file=dev.tfvars'

terraform-apply: ## Apply Terraform changes (dev environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform apply -var-file=dev.tfvars'

terraform-destroy: ## Destroy Terraform resources (dev environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform destroy -var-file=dev.tfvars'

terraform-validate: ## Validate Terraform configuration syntax and structure
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform init -backend=false && terraform validate'

terraform-import-github-oidc: ## Import existing GitHub OIDC application into Terraform state
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-github-oidc.sh'

terraform-fmt: ## Format Terraform files
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform fmt -recursive'

terraform-refresh: ## Refresh Terraform state to match what actually exists in Azure (requires active subscription)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform refresh -var-file=dev.tfvars'

terraform-check-subscription: ## Check Azure subscription status and service accessibility (useful for troubleshooting)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/check-subscription-status.sh'

terraform-register-providers: ## Register required Azure resource providers (Container Apps, etc.)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/register-container-apps-provider.sh'

terraform-import-cae: ## Import existing Container Apps Environment into Terraform state
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-container-apps-env.sh'

terraform-import-container-apps: ## Import existing Container Apps into Terraform state
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-container-apps.sh'

terraform-check-app-status: ## Check status of integration-worker-beat Container App (for diagnosing 412 errors)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/check-container-app-status.sh'

terraform-delete-failed-app: ## Delete a failed Container App (usage: make terraform-delete-failed-app APP=api-core)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/delete-failed-container-app.sh $(APP)'

terraform-import-discover: ## Discover existing Azure resources and generate import commands (dev environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-resources.sh dev'

terraform-import-discover-staging: ## Discover existing Azure resources and generate import commands (staging environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-resources.sh staging'

terraform-import-discover-prod: ## Discover existing Azure resources and generate import commands (prod environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-resources.sh prod'

terraform-import: ## Run generated import commands (dev environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && if [ -f import-commands-dev.sh ]; then bash import-commands-dev.sh; else echo "Error: import-commands-dev.sh not found. Run 'make terraform-import-discover' first."; exit 1; fi'

terraform-import-staging: ## Run generated import commands (staging environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && if [ -f import-commands-staging.sh ]; then bash import-commands-staging.sh; else echo "Error: import-commands-staging.sh not found. Run 'make terraform-import-discover-staging' first."; exit 1; fi'

terraform-import-prod: ## Run generated import commands (prod environment)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && if [ -f import-commands-prod.sh ]; then bash import-commands-prod.sh; else echo "Error: import-commands-prod.sh not found. Run 'make terraform-import-discover-prod' first."; exit 1; fi'

terraform-sync: ## Sync existing Azure resources with Terraform state (discover + import) (dev environment)
	@echo "Step 1: Discovering existing resources..."
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/import-resources.sh dev'
	@echo ""
	@echo "Step 2: Review the generated import commands in infra/terraform/import-commands-dev.sh"
	@echo "Step 3: Run 'make terraform-import' to execute the imports"

terraform-state-cleanup: ## Remove old resources (OpenAI, Redis Cache) from Terraform state (works even if subscription is disabled)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/remove-old-resources.sh'

terraform-destroy-no-refresh: ## Destroy Terraform resources without refreshing state (useful when subscription is disabled)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && terraform destroy -refresh=false -var-file=dev.tfvars'

# Shared Resources Commands
# These commands target the shared resources in infra/terraform/shared/
terraform-shared-init: ## Initialize Terraform for shared resources
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform init'

terraform-shared-plan: ## Run Terraform plan for shared resources
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform plan -var-file=shared.tfvars'

terraform-shared-apply: ## Apply Terraform changes for shared resources
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform apply -var-file=shared.tfvars'

terraform-shared-destroy: ## Destroy shared resources (use with caution!)
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform destroy -var-file=shared.tfvars'

terraform-shared-validate: ## Validate Terraform configuration for shared resources
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform init -backend=false && terraform validate'

terraform-shared-output: ## Show outputs from shared resources
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform output'

terraform-shared-fmt: ## Format Terraform files for shared resources
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform/shared && terraform fmt -recursive'

# Terraform State Storage Management (DEV ONLY - CI/CD handles prod/staging)
terraform-disable-backend: ## [DEV ONLY] Disable backend configs for shared + dev (signifies local state management)
	@echo "⚠️  DEV ONLY: This command is for local dev environment only"
	@echo "   Production and staging are managed by CI/CD pipeline"
	@echo ""
	@echo "🔧 Disabling backend configurations..."
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; \
		cd infra/terraform/shared && \
		if [ -f backend-shared.tf ]; then \
			mv backend-shared.tf backend-shared.tf.disabled && \
			echo "✓ Shared backend disabled"; \
		else \
			echo "⚠️  Shared backend already disabled"; \
		fi'
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; \
		cd infra/terraform && \
		if [ -f backend.tf ]; then \
			mv backend.tf backend.tf.disabled && \
			echo "✓ Dev environment backend disabled"; \
		else \
			echo "⚠️  Dev backend already disabled"; \
		fi'
	@echo ""
	@echo "✅ Backend configurations disabled - Terraform will use local state"
	@echo "   Run 'make terraform-shared-init' and 'make terraform-init' to reinitialize"

terraform-restore-backend: ## [DEV ONLY] Restore backend configs for shared + dev and migrate states to remote storage
	@echo "⚠️  DEV ONLY: This command is for local dev environment only"
	@echo "   Production and staging are managed by CI/CD pipeline"
	@echo ""
	@echo "🔄 Restoring backend configurations and migrating states..."
	@echo ""
	@echo "📦 Step 1: Restoring shared resources backend..."
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; \
		cd infra/terraform/shared && \
		if [ ! -f backend-shared.tf.disabled ]; then \
			echo "⚠️  Shared backend is not disabled (already using remote state)"; \
		else \
			mv backend-shared.tf.disabled backend-shared.tf && \
			echo "✓ Shared backend restored" && \
			if [ -f terraform.tfstate ]; then \
				cp terraform.tfstate terraform.tfstate.local-backup-$$(date +%Y%m%d-%H%M%S) && \
				echo "✓ Shared local state backed up"; \
			fi && \
			echo "📦 Migrating shared state to remote..." && \
			terraform init -migrate-state && \
			echo "✅ Shared state migrated to remote storage"; \
		fi'
	@echo ""
	@echo "📦 Step 2: Restoring dev environment backend..."
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; \
		cd infra/terraform && \
		if [ ! -f backend.tf.disabled ]; then \
			echo "⚠️  Dev backend is not disabled (already using remote state)"; \
		else \
			mv backend.tf.disabled backend.tf && \
			echo "✓ Dev backend restored" && \
			if [ -f terraform.tfstate ]; then \
				cp terraform.tfstate terraform.tfstate.backup-$$(date +%Y%m%d-%H%M%S) && \
				echo "✓ Dev local state backed up"; \
			fi && \
			echo "📦 Migrating dev state to remote..." && \
			terraform init -migrate-state && \
			echo "✅ Dev state migrated to remote storage"; \
		fi'
	@echo ""
	@echo "✅ All backend configurations restored and states migrated!"
	@echo "   Verify with: make terraform-state-sync"

terraform-state-sync: ## [DEV ONLY] Verify and sync all Terraform states (shared + dev) are in remote storage
	@echo "⚠️  DEV ONLY: This command is for local dev environment only"
	@echo "   Production and staging are managed by CI/CD pipeline"
	@echo ""
	@echo "📋 Verifying Terraform state storage..."
	@echo ""
	@echo "1️⃣  Checking shared resources state..."
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; \
		cd infra/terraform/shared && \
		if [ -f backend-shared.tf.disabled ]; then \
			echo "   ⚠️  Backend disabled - using local state"; \
		else \
			if terraform state list > /dev/null 2>&1; then \
				echo "   ✅ Shared state: Remote (accessible)"; \
				terraform state list | head -5; \
				echo "   ... (showing first 5 resources)"; \
			else \
				echo "   ❌ Shared state: Not accessible"; \
			fi; \
		fi'
	@echo ""
	@echo "2️⃣  Checking dev environment state..."
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; \
		cd infra/terraform && \
		if [ -f backend.tf.disabled ]; then \
			echo "   ⚠️  Backend disabled - using local state"; \
		else \
			if terraform state list > /dev/null 2>&1; then \
				echo "   ✅ Dev state: Remote (accessible)"; \
				terraform state list | head -5; \
				echo "   ... (showing first 5 resources)"; \
			else \
				echo "   ❌ Dev state: Not accessible"; \
			fi; \
		fi'
	@echo ""
	@echo "3️⃣  Verifying state files in Azure Storage..."
	@bash -c 'az storage blob list \
		--container-name terraform-state \
		--account-name lexiqaitfstate \
		--auth-mode login \
		--query "[].{Name:name, Size:properties.contentLength, LastModified:properties.lastModified}" \
		-o table 2>/dev/null || echo "   ⚠️  Could not verify in Azure Storage (may need permissions - run: make terraform-shared-apply to grant access)"'
	@echo ""
	@echo "✅ State verification complete!"

# Phase 4: Migration Scripts
migrate-acr-images: ## Migrate container images from environment-specific ACR to shared ACR (usage: make migrate-acr-images ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make migrate-acr-images ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make migrate-acr-images ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/migrate-acr-images.sh
	@infra/terraform/scripts/migrate-acr-images.sh $(ENV) $(SHARED_ACR)

export-dns-records: ## Export DNS records from environment-specific DNS zone (usage: make export-dns-records ENV=dev [DNS_ZONE=lexiqai.com] [OUTPUT=dns-records-dev.json])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make export-dns-records ENV=<environment> [DNS_ZONE=<zone-name>] [OUTPUT=<output-file>]"; \
		echo "Example: make export-dns-records ENV=dev DNS_ZONE=lexiqai.com OUTPUT=dns-records-dev.json"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/export-dns-records.sh
	@infra/terraform/scripts/export-dns-records.sh $(ENV) $(DNS_ZONE) $(OUTPUT)

# Phase 7: Cleanup Scripts
verify-shared-resources: ## Verify Container Apps are using shared resources before cleanup (usage: make verify-shared-resources ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make verify-shared-resources ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make verify-shared-resources ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/verify-shared-resources.sh
	@infra/terraform/scripts/verify-shared-resources.sh $(ENV) $(SHARED_ACR)

cleanup-old-acr: ## Remove old environment-specific ACR from Terraform state (usage: make cleanup-old-acr ENV=dev [DELETE_FROM_AZURE=true])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make cleanup-old-acr ENV=<environment> [DELETE_FROM_AZURE=true]"; \
		echo "Example: make cleanup-old-acr ENV=dev"; \
		echo "Example: make cleanup-old-acr ENV=dev DELETE_FROM_AZURE=true"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/cleanup-old-acr.sh
	@if [ "$(DELETE_FROM_AZURE)" == "true" ]; then \
		infra/terraform/scripts/cleanup-old-acr.sh $(ENV) --delete-from-azure; \
	else \
		infra/terraform/scripts/cleanup-old-acr.sh $(ENV); \
	fi

cleanup-old-github-oidc: ## Remove old environment-specific GitHub OIDC app from Terraform state (usage: make cleanup-old-github-oidc ENV=dev [DELETE_FROM_AZURE=true])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make cleanup-old-github-oidc ENV=<environment> [DELETE_FROM_AZURE=true]"; \
		echo "Example: make cleanup-old-github-oidc ENV=dev"; \
		echo "Example: make cleanup-old-github-oidc ENV=dev DELETE_FROM_AZURE=true"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/cleanup-old-github-oidc.sh
	@if [ "$(DELETE_FROM_AZURE)" == "true" ]; then \
		infra/terraform/scripts/cleanup-old-github-oidc.sh $(ENV) --delete-from-azure; \
	else \
		infra/terraform/scripts/cleanup-old-github-oidc.sh $(ENV); \
	fi

cleanup-old-dns-zone: ## Remove old environment-specific DNS zone from Terraform state (usage: make cleanup-old-dns-zone ENV=dev [DNS_ZONE=lexiqai.com] [DELETE_FROM_AZURE=true])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make cleanup-old-dns-zone ENV=<environment> [DNS_ZONE=<zone-name>] [DELETE_FROM_AZURE=true]"; \
		echo "Example: make cleanup-old-dns-zone ENV=dev DNS_ZONE=lexiqai.com"; \
		echo "Example: make cleanup-old-dns-zone ENV=dev DNS_ZONE=lexiqai.com DELETE_FROM_AZURE=true"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/cleanup-old-dns-zone.sh
	@if [ "$(DELETE_FROM_AZURE)" == "true" ]; then \
		infra/terraform/scripts/cleanup-old-dns-zone.sh $(ENV) $(DNS_ZONE) --delete-from-azure; \
	else \
		infra/terraform/scripts/cleanup-old-dns-zone.sh $(ENV) $(DNS_ZONE); \
	fi

update-container-apps-shared-acr: ## Update Container Apps to use shared ACR images (usage: make update-container-apps-shared-acr ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make update-container-apps-shared-acr ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make update-container-apps-shared-acr ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/update-container-apps-to-shared-acr.sh
	@infra/terraform/scripts/update-container-apps-to-shared-acr.sh $(ENV) $(SHARED_ACR)

import-public-images-acr: ## Import public Docker images (Redis, RabbitMQ, Qdrant) into shared ACR (usage: make import-public-images-acr ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make import-public-images-acr ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make import-public-images-acr ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/import-public-images-to-acr.sh
	@infra/terraform/scripts/import-public-images-to-acr.sh $(ENV) $(SHARED_ACR)

update-container-apps-shared-acr: ## Update Container Apps to use shared ACR images (usage: make update-container-apps-shared-acr ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make update-container-apps-shared-acr ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make update-container-apps-shared-acr ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/update-container-apps-to-shared-acr.sh
	@infra/terraform/scripts/update-container-apps-to-shared-acr.sh $(ENV) $(SHARED_ACR)

import-public-images-acr: ## Import public Docker images (Redis, RabbitMQ, Qdrant) into shared ACR (usage: make import-public-images-acr ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make import-public-images-acr ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make import-public-images-acr ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/import-public-images-to-acr.sh
	@infra/terraform/scripts/import-public-images-to-acr.sh $(ENV) $(SHARED_ACR)

build-push-infrastructure-images: ## Build and push infrastructure images (Redis, RabbitMQ, Qdrant) to shared ACR (usage: make build-push-infrastructure-images ENV=dev [SHARED_ACR=lexiqaiacrshared])
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make build-push-infrastructure-images ENV=<environment> [SHARED_ACR=<acr-name>]"; \
		echo "Example: make build-push-infrastructure-images ENV=dev SHARED_ACR=lexiqaiacrshared"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/build-and-push-infrastructure-images.sh
	@infra/terraform/scripts/build-and-push-infrastructure-images.sh $(ENV) $(SHARED_ACR)

setup-static-web-app: ## Configure Static Web App app settings and get deployment token (usage: make setup-static-web-app ENV=dev)
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV is required"; \
		echo "Usage: make setup-static-web-app ENV=<environment>"; \
		echo "Example: make setup-static-web-app ENV=dev"; \
		exit 1; \
	fi
	@chmod +x infra/terraform/scripts/setup-static-web-app.sh
	@bash -c 'if [ -f .env ]; then set -a; source .env; set +a; fi; cd infra/terraform && bash scripts/setup-static-web-app.sh $(ENV)'

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
	@echo "Setting up Python virtual environment for API Core..."
	@echo "Checking for Python 3.11+ (required for api-core)..."
	@PYTHON_CMD=$$(command -v python3.12 || command -v python3.11 || command -v python3 || echo ""); \
	if [ -z "$$PYTHON_CMD" ]; then \
		echo "❌ Error: Python 3.11+ is required but not found."; \
		echo "Please install Python 3.11 or 3.12 and ensure it's in your PATH."; \
		echo "You can check available Python versions with: python3 --version"; \
		exit 1; \
	fi; \
	PYTHON_VERSION=$$($$PYTHON_CMD --version 2>&1 | awk '{print $$2}' | cut -d. -f1,2); \
	PYTHON_MAJOR=$$(echo $$PYTHON_VERSION | cut -d. -f1); \
	PYTHON_MINOR=$$(echo $$PYTHON_VERSION | cut -d. -f2); \
	if [ $$PYTHON_MAJOR -lt 3 ] || ([ $$PYTHON_MAJOR -eq 3 ] && [ $$PYTHON_MINOR -lt 11 ]); then \
		echo "❌ Error: Python 3.11+ is required, but found Python $$PYTHON_VERSION"; \
		echo "Please install Python 3.11 or 3.12 and ensure it's in your PATH."; \
		echo "You can check available Python versions with: python3.11 --version or python3.12 --version"; \
		exit 1; \
	fi; \
	echo "✓ Found Python $$PYTHON_VERSION at $$PYTHON_CMD"; \
	cd apps/api-core && $$PYTHON_CMD -m venv .venv
	@echo "✓ Virtual environment created at apps/api-core/.venv"
	@echo "Activate it with: source apps/api-core/.venv/bin/activate"
	@echo "Or install dependencies with: make api-venv-install"

api-venv-install: ## Install dependencies in virtual environment
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "Virtual environment not found. Creating it..."; \
		$(MAKE) venv-setup; \
	fi
	@echo "Installing dependencies..."
	cd apps/api-core && .venv/bin/python -m pip install --upgrade pip
	cd apps/api-core && .venv/bin/python -m pip install -r requirements-dev.txt
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

migrate-up-docker: ## Apply migratiorns from inside Docker container
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

migrate-stamp-local: ## Mark local database as being at a specific revision (usage: make migrate-stamp-local REVISION=abc123)
	@if [ -z "$(REVISION)" ]; then \
		echo "Error: REVISION is required. Usage: make migrate-stamp-local REVISION=abc123"; \
		exit 1; \
	fi
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make venv-setup && make venv-install' first"; \
		exit 1; \
	fi
	@echo "Stamping local database to revision $(REVISION)..."
	cd apps/api-core && DATABASE_URL="postgresql://admin:password@localhost:5432/lexiqai_local" $(ALEMBIC_CMD) stamp $(REVISION)

db-reset: ## Reset database by deleting all rows (keeps schema intact)
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make api-venv-setup && make api-venv-install' first"; \
		exit 1; \
	fi
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "⚠️  DATABASE_URL not set. Using local Docker default..."; \
		cd apps/api-core && DATABASE_URL="postgresql://admin:password@localhost:5432/lexiqai_local" .venv/bin/python ../../tools/scripts/reset_database.py; \
	else \
		cd apps/api-core && .venv/bin/python ../../tools/scripts/reset_database.py; \
	fi

db-reset-local: ## Reset local Docker database (deletes all rows, keeps schema)
	@if [ ! -f "$(VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make api-venv-setup && make api-venv-install' first"; \
		exit 1; \
	fi
	@echo "Resetting local Docker database..."
	cd apps/api-core && DATABASE_URL="postgresql://admin:password@localhost:5432/lexiqai_local" .venv/bin/python ../../tools/scripts/reset_database.py

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

orch-test: cognitive-orch-test ## Alias for cognitive-orch-test

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
	cd apps/document-ingestion && .venv/bin/python -m pip install -r requirements.txt
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

ingestion-test: document-ingestion-test ## Alias for document-ingestion-test

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

# Integration Worker Service commands
# Virtual environment paths
WORKER_VENV_PATH := apps/integration-worker/.venv
WORKER_VENV_ACTIVATE := $(WORKER_VENV_PATH)/bin/activate
WORKER_VENV_PYTHON := $(WORKER_VENV_PATH)/bin/python

# Use venv if it exists, otherwise use system commands
ifeq ($(wildcard $(WORKER_VENV_ACTIVATE)),)
	WORKER_CELERY_CMD := celery
	WORKER_PYTEST_CMD := pytest
	WORKER_BLACK_CMD := black
	WORKER_RUFF_CMD := ruff
else
	WORKER_CELERY_CMD := .venv/bin/celery
	WORKER_PYTEST_CMD := .venv/bin/pytest
	WORKER_BLACK_CMD := .venv/bin/black
	WORKER_RUFF_CMD := .venv/bin/ruff
endif

worker-venv-setup: ## Set up Python virtual environment for integration-worker
	@echo "Setting up Python virtual environment for Integration Worker..."
	@echo "Checking for Python 3.11+ (required for api-core and integration-worker)..."
	@PYTHON_CMD=$$(command -v python3.12 || command -v python3.11 || command -v python3 || echo ""); \
	if [ -z "$$PYTHON_CMD" ]; then \
		echo "❌ Error: Python 3.11+ is required but not found."; \
		echo "Please install Python 3.11 or 3.12 and ensure it's in your PATH."; \
		echo "You can check available Python versions with: python3 --version"; \
		exit 1; \
	fi; \
	PYTHON_VERSION=$$($$PYTHON_CMD --version 2>&1 | awk '{print $$2}' | cut -d. -f1,2); \
	PYTHON_MAJOR=$$(echo $$PYTHON_VERSION | cut -d. -f1); \
	PYTHON_MINOR=$$(echo $$PYTHON_VERSION | cut -d. -f2); \
	if [ $$PYTHON_MAJOR -lt 3 ] || ([ $$PYTHON_MAJOR -eq 3 ] && [ $$PYTHON_MINOR -lt 11 ]); then \
		echo "❌ Error: Python 3.11+ is required, but found Python $$PYTHON_VERSION"; \
		echo "Please install Python 3.11 or 3.12 and ensure it's in your PATH."; \
		echo "You can check available Python versions with: python3.11 --version or python3.12 --version"; \
		exit 1; \
	fi; \
	echo "✓ Found Python $$PYTHON_VERSION at $$PYTHON_CMD"; \
	if [ -d "apps/integration-worker/.venv" ]; then \
		EXISTING_PYTHON_VERSION=$$(apps/integration-worker/.venv/bin/python --version 2>&1 | awk '{print $$2}' | cut -d. -f1,2 2>/dev/null || echo ""); \
		if [ -n "$$EXISTING_PYTHON_VERSION" ]; then \
			EXISTING_MAJOR=$$(echo $$EXISTING_PYTHON_VERSION | cut -d. -f1); \
			EXISTING_MINOR=$$(echo $$EXISTING_PYTHON_VERSION | cut -d. -f2); \
			if [ $$EXISTING_MAJOR -lt 3 ] || ([ $$EXISTING_MAJOR -eq 3 ] && [ $$EXISTING_MINOR -lt 11 ]); then \
				echo "⚠️  Existing venv uses Python $$EXISTING_PYTHON_VERSION (< 3.11). Removing it..."; \
				rm -rf apps/integration-worker/.venv; \
			fi; \
		fi; \
	fi; \
	cd apps/integration-worker && $$PYTHON_CMD -m venv .venv
	@echo "✓ Virtual environment created at apps/integration-worker/.venv"
	@echo "Activate it with: source apps/integration-worker/.venv/bin/activate"
	@echo "Or install dependencies with: make worker-venv-install"

worker-venv-install: ## Install dependencies in integration-worker virtual environment
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "Virtual environment not found. Creating it..."; \
		$(MAKE) worker-venv-setup; \
	fi
	@echo "Installing dependencies for Integration Worker..."
	cd apps/integration-worker && .venv/bin/python -m pip install --upgrade pip
	cd apps/integration-worker && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
	@echo "✓ Dependencies installed (including api-core)"

worker-start: ## Start Celery worker
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Starting Integration Worker (Celery worker)..."
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src $(WORKER_CELERY_CMD) -A integration_worker.celery_app worker --loglevel=info --concurrency=4

worker-beat: ## Start Celery beat scheduler
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Starting Integration Worker Beat (Celery scheduler)..."
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src $(WORKER_CELERY_CMD) -A integration_worker.celery_app beat --loglevel=info

worker-flower: ## Start Celery Flower (web monitoring UI)
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Starting Celery Flower monitoring UI..."
	@echo "Flower will be available at http://localhost:5555"
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src $(WORKER_CELERY_CMD) -A integration_worker.celery_app flower

worker-status: ## Check Celery worker status
	@echo "Checking Integration Worker status..."
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src $(WORKER_CELERY_CMD) -A integration_worker.celery_app inspect active || echo "Worker not running or not accessible"

worker-purge: ## Purge all pending tasks from Celery queue
	@echo "⚠️  This will delete ALL pending tasks from the queue!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd apps/integration-worker && PYTHONPATH=src:../api-core/src $(WORKER_CELERY_CMD) -A integration_worker.celery_app purge -f; \
	fi

worker-test: integration-worker-test ## Alias for integration-worker-test

worker-test-cov: ## Run integration-worker tests with coverage
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Running Integration Worker tests with coverage..."
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src $(WORKER_PYTEST_CMD) tests/ --cov=integration_worker --cov-report=html --cov-report=term-missing

worker-format: ## Format integration-worker code with black
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Formatting Integration Worker code..."
	cd apps/integration-worker && $(WORKER_BLACK_CMD) src/ tests/

worker-lint: ## Lint integration-worker code with ruff
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Linting Integration Worker code..."
	cd apps/integration-worker && $(WORKER_RUFF_CMD) check --fix src/ tests/

worker-check: ## Run all code quality checks for integration-worker
	@echo "Running all code quality checks for Integration Worker..."
	$(MAKE) worker-format
	$(MAKE) worker-lint

worker-verify: ## Run integration-worker setup verification
	@echo "Verifying Integration Worker setup..."
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src python verify_setup.py

docker-build-worker: ## Build integration-worker Docker image
	$(DOCKER_COMPOSE) build integration-worker integration-worker-beat

docker-rebuild-worker: ## Rebuild and restart integration-worker services
	$(DOCKER_COMPOSE) up -d --build integration-worker integration-worker-beat

docker-logs-worker: ## View integration-worker logs
	$(DOCKER_COMPOSE) logs -f integration-worker

docker-logs-worker-beat: ## View integration-worker-beat logs
	$(DOCKER_COMPOSE) logs -f integration-worker-beat

docker-build-worker-webhooks: ## Build integration-worker-webhooks Docker image
	$(DOCKER_COMPOSE) build integration-worker-webhooks

docker-rebuild-worker-webhooks: ## Rebuild and restart integration-worker-webhooks service
	$(DOCKER_COMPOSE) up -d --build integration-worker-webhooks

docker-logs-worker-webhooks: ## View integration-worker-webhooks logs
	$(DOCKER_COMPOSE) logs -f integration-worker-webhooks

worker-webhooks-start: ## Start webhook server locally
	@if [ ! -f "$(WORKER_VENV_ACTIVATE)" ]; then \
		echo "⚠️  Virtual environment not found. Run 'make worker-venv-setup && make worker-venv-install' first"; \
		exit 1; \
	fi
	@echo "Starting Integration Worker Webhook Server..."
	@echo "Server will be available at http://localhost:8002"
	@echo "API docs will be available at http://localhost:8002/docs"
	cd apps/integration-worker && PYTHONPATH=src:../api-core/src .venv/bin/uvicorn integration_worker.main:app --reload --host 0.0.0.0 --port 8002

# Voice Gateway Service commands (Go)
voice-deps: ## Download and tidy Go dependencies for voice-gateway
	@echo "Downloading Go dependencies for Voice Gateway..."
	cd apps/voice-gateway && go mod download
	cd apps/voice-gateway && go mod tidy
	@echo "✓ Dependencies downloaded and tidied"

voice-build: ## Build voice-gateway binary
	@echo "Building Voice Gateway binary..."
	cd apps/voice-gateway && go build -o bin/voice-gateway ./cmd/server
	@echo "✓ Binary built at apps/voice-gateway/bin/voice-gateway"

voice-build-linux: ## Build voice-gateway binary for Linux (for Docker)
	@echo "Building Voice Gateway binary for Linux..."
	cd apps/voice-gateway && GOOS=linux GOARCH=amd64 go build -o bin/voice-gateway-linux ./cmd/server
	@echo "✓ Linux binary built at apps/voice-gateway/bin/voice-gateway-linux"

voice-run: ## Run voice-gateway development server
	@echo "Starting Voice Gateway development server..."
	@echo "Server will be available at http://localhost:8080"
	@echo "Twilio WebSocket endpoint: ws://localhost:8080/streams/twilio"
	@echo "Health check: http://localhost:8080/health"
	cd apps/voice-gateway && go run ./cmd/server

voice-test: voice-gateway-test ## Alias for voice-gateway-test

voice-test-cov: ## Run voice-gateway tests with coverage
	@echo "Running Voice Gateway tests with coverage..."
	cd apps/voice-gateway && go test ./... -coverprofile=coverage.out -covermode=atomic
	cd apps/voice-gateway && go tool cover -html=coverage.out -o coverage.html
	@echo "✓ Coverage report generated at apps/voice-gateway/coverage.html"

voice-fmt: ## Format voice-gateway code with gofmt
	@echo "Formatting Voice Gateway code..."
	cd apps/voice-gateway && go fmt ./...
	@echo "✓ Code formatted"

voice-vet: ## Run go vet on voice-gateway code
	@echo "Running go vet on Voice Gateway code..."
	cd apps/voice-gateway && go vet ./...
	@echo "✓ go vet completed"

voice-lint: ## Lint voice-gateway code with golangci-lint (if available)
	@echo "Linting Voice Gateway code..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		cd apps/voice-gateway && golangci-lint run ./...; \
		echo "✓ golangci-lint completed"; \
	else \
		echo "⚠️  golangci-lint not found. Install with: go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"; \
		echo "Running go vet instead..."; \
		$(MAKE) voice-vet; \
	fi

voice-check: ## Run all code quality checks (fmt, vet, lint)
	@echo "Running all code quality checks for Voice Gateway..."
	$(MAKE) voice-fmt
	$(MAKE) voice-vet
	$(MAKE) voice-lint

voice-clean: ## Clean voice-gateway build artifacts
	@echo "Cleaning Voice Gateway build artifacts..."
	cd apps/voice-gateway && rm -rf bin/ coverage.out coverage.html
	@echo "✓ Build artifacts cleaned"

voice-health: ## Check voice-gateway service health
	@echo "Checking Voice Gateway service health..."
	@curl -s http://localhost:8080/health | python3 -m json.tool || echo "Service not running or not accessible"

# Protocol Buffer compilation
proto-compile: ## Compile Protocol Buffer definitions to Python stubs (compatible with protobuf 5.x)
	@echo "Compiling Protocol Buffers with protobuf 5.x compatibility..."
	@chmod +x tools/scripts/compile_protos_compatible.sh
	@tools/scripts/compile_protos_compatible.sh

proto-compile-go: ## Compile Protocol Buffer definitions to Go stubs for voice-gateway
	@echo "Compiling Protocol Buffers for Go..."
	@mkdir -p apps/voice-gateway/internal/orchestrator/proto
	@PATH=$$PATH:$$HOME/go/bin:$$GOPATH/bin protoc \
		--proto_path=libs/proto \
		--go_out=apps/voice-gateway/internal/orchestrator/proto \
		--go_opt=paths=source_relative \
		--go-grpc_out=apps/voice-gateway/internal/orchestrator/proto \
		--go-grpc_opt=paths=source_relative \
		libs/proto/cognitive_orch.proto
	@echo "✓ Proto files compiled successfully"

proto-clean-go: ## Clean generated Go proto files
	@echo "Cleaning generated Go proto files..."
	@rm -rf apps/voice-gateway/internal/orchestrator/proto
	@echo "✓ Go proto files cleaned"

# Internal API Key Management
generate-api-key: ## Generate a secure internal API key (default: 32 bytes)
	@echo "Generating secure internal API key..."
	@python3 tools/scripts/generate_internal_api_key.py

generate-api-key-long: ## Generate a longer internal API key (64 bytes)
	@echo "Generating secure internal API key (64 bytes)..."
	@python3 tools/scripts/generate_internal_api_key.py --length 64

generate-api-key-env: ## Generate internal API key in .env format
	@echo "Generating internal API key in .env format..."
	@python3 tools/scripts/generate_internal_api_key.py --format env

generate-api-key-docker: ## Generate internal API key in docker-compose format
	@echo "Generating internal API key in docker-compose format..."
	@python3 tools/scripts/generate_internal_api_key.py --format docker


stripe-listen-webhook:
	@echo "Listening for Stripe webhook..."
	@stripe listen --forward-to localhost:8000/api/v1/billing/webhook/stripe

# Development utilities
clean: ## Clean build artifacts and temporary files
	find . -type d -name node_modules -prune -o -type d -name .next -prune -o -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

postgres-start:
	@echo "Starting PostgreSQL..."
	/opt/homebrew/opt/postgresql@14/bin/postgres -D /opt/homebrew/var/postgresql@14
