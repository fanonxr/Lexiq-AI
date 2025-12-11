# Load environment variables from .env.local if it exists
ifneq (,$(wildcard .env.local))
    include .env.local
    export
endif

.PHONY: help docker-up docker-down docker-logs docker-clean install test format lint terraform-init terraform-plan terraform-apply terraform-destroy

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

# Installation
install: ## Install dependencies for all services
	cd apps/web-frontend && npm install
	@echo "Install Python dependencies manually: pip install -r requirements.txt"

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

# Development utilities
clean: ## Clean build artifacts and temporary files
	find . -type d -name node_modules -prune -o -type d -name .next -prune -o -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

