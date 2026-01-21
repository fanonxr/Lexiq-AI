# Container App Init Jobs

## Overview

Init Jobs are one-time execution containers used for initialization and setup tasks. They run in the same VNet as your services, making them ideal for:
- Database role grants
- Database migrations
- Multi-region setup
- One-time configuration tasks
- Data seeding
- Infrastructure validation

## Architecture

All Init Jobs:
- ✅ Run in the Container Apps Environment (same VNet as services)
- ✅ Use Managed Identity for secure access to Key Vault and Azure resources
- ✅ Are manually triggered (run once and complete)
- ✅ Are idempotent (safe to run multiple times)
- ✅ Cost-effective (only charged for execution time)

## Available Init Jobs

### 1. Database Role Grant Job

**Name**: `{project-name}-init-grant-db-roles-{environment}`

**Purpose**: Grants PostgreSQL database roles to the Managed Identity

**When to Run**:
- After initial Terraform apply
- After creating a new environment
- After rotating Managed Identity
- After database restore

**How to Run**:
```bash
# Using script
./scripts/trigger-db-role-grant-job.sh dev

# Using Azure CLI
az containerapp job start \
  --name "lexiqai-init-grant-db-roles-dev" \
  --resource-group "lexiqai-rg-dev"
```

**Prerequisites**:
- `postgres-admin-password` secret in Key Vault
- Azure AD administrator configured for PostgreSQL

## Creating Custom Init Jobs

### Pattern

All init jobs follow this pattern:

```hcl
resource "azurerm_container_app_job" "your_job_name" {
  name                         = "${var.project_name}-init-{purpose}-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name

  # Always assign Managed Identity
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Secrets from Key Vault (if needed)
  dynamic "secret" {
    for_each = var.key_vault_name != null ? {
      "secret-name" = "https://${var.key_vault_name}.vault.azure.net/secrets/secret-name"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  template {
    container {
      name  = "job-container"
      image = "your-image:tag"

      # Environment variables
      env {
        name  = "VAR_NAME"
        value = "value"
      }

      # Command to execute
      command = ["your", "command", "here"]

      # Resource limits
      cpu    = 0.25  # Start small, increase if needed
      memory = "0.5Gi"
    }

    manual_trigger_config {
      parallelism             = 1
      replica_completion_count = 1
    }
  }

  trigger_type = "Manual"

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-init-{purpose}-${var.environment}"
      Purpose     = "Init job: {description}"
      JobType     = "init"
      JobCategory = "{category}"  # database, infrastructure, data, etc.
    }
  )
}
```

### Common Use Cases

#### Database Migrations

```hcl
resource "azurerm_container_app_job" "database_migration" {
  # ... standard job config ...
  
  template {
    container {
      name  = "migrate"
      image = "${var.container_registry}/${var.project_name}/api-core:${var.image_tag}"

      env {
        name  = "DATABASE_URL"
        value = "postgresql://${var.managed_identity_name}@${var.postgres_fqdn}:5432/${var.postgres_database_name}?sslmode=require"
      }

      command = ["python", "-m", "alembic", "upgrade", "head"]

      cpu    = 0.5
      memory = "1Gi"
    }
    # ...
  }
}
```

#### Multi-Region Setup

```hcl
resource "azurerm_container_app_job" "multi_region_setup" {
  # ... standard job config ...
  
  template {
    container {
      name  = "setup"
      image = "mcr.microsoft.com/azure-cli:latest"

      env {
        name  = "TARGET_REGION"
        value = var.secondary_region
      }

      command = [
        "sh",
        "-c",
        <<-EOT
          az login --identity
          # Your setup script here
        EOT
      ]

      cpu    = 0.5
      memory = "1Gi"
    }
    # ...
  }
}
```

#### Data Seeding

```hcl
resource "azurerm_container_app_job" "seed_data" {
  # ... standard job config ...
  
  template {
    container {
      name  = "seed"
      image = "${var.container_registry}/${var.project_name}/api-core:${var.image_tag}"

      env {
        name  = "DATABASE_URL"
        value = "postgresql://${var.managed_identity_name}@${var.postgres_fqdn}:5432/${var.postgres_database_name}?sslmode=require"
      }

      command = ["python", "-m", "scripts.seed_data"]

      cpu    = 0.5
      memory = "1Gi"
    }
    # ...
  }
}
```

## Best Practices

### 1. Naming Convention

Use consistent naming:
- Format: `{project-name}-init-{purpose}-{environment}`
- Examples:
  - `lexiqai-init-grant-db-roles-dev`
  - `lexiqai-init-db-migration-prod`
  - `lexiqai-init-seed-data-staging`

### 2. Resource Limits

Start with minimal resources and increase if needed:
- **Small jobs** (SQL scripts): `cpu = 0.25, memory = "0.5Gi"`
- **Medium jobs** (migrations): `cpu = 0.5, memory = "1Gi"`
- **Large jobs** (data processing): `cpu = 1.0, memory = "2Gi"`

### 3. Idempotency

Always make jobs idempotent:
- Check if work is already done before doing it
- Use `IF NOT EXISTS` in SQL
- Check state before making changes

### 4. Error Handling

Include proper error handling:
- Use `set -e` in shell scripts
- Check prerequisites before execution
- Provide clear error messages

### 5. Logging

Log important steps:
```bash
echo "=== Starting Job: {purpose} ==="
echo "Step 1: Checking prerequisites..."
echo "Step 2: Executing task..."
echo "✓ Job completed successfully!"
```

### 6. Tags

Always tag jobs consistently:
- `JobType = "init"` (all init jobs)
- `JobCategory = "database" | "infrastructure" | "data" | etc.`
- `Purpose = "Init job: {description}"`

## Triggering Jobs

### Via Script

Create a script for each job:
```bash
#!/bin/bash
# scripts/trigger-{job-name}.sh

JOB_NAME="lexiqai-init-{purpose}-${ENVIRONMENT}"
RESOURCE_GROUP="lexiqai-rg-${ENVIRONMENT}"

az containerapp job start \
  --name "$JOB_NAME" \
  --resource-group "$RESOURCE_GROUP"
```

### Via Azure CLI

```bash
az containerapp job start \
  --name "lexiqai-init-{purpose}-dev" \
  --resource-group "lexiqai-rg-dev"
```

### Via Azure Portal

1. Navigate to Container Apps → Jobs
2. Find your job
3. Click "Start"

### Via CI/CD Pipeline

Add to your GitHub Actions workflow:
```yaml
- name: Run Database Migration Job
  run: |
    az containerapp job start \
      --name "lexiqai-init-db-migration-${{ env.ENVIRONMENT }}" \
      --resource-group "lexiqai-rg-${{ env.ENVIRONMENT }}"
```

## Monitoring

### View Job Status

```bash
az containerapp job execution list \
  --name "lexiqai-init-{purpose}-dev" \
  --resource-group "lexiqai-rg-dev" \
  --query "[0].{Status:properties.status,StartTime:properties.startTime,EndTime:properties.endTime}" \
  --output table
```

### View Logs

```bash
az containerapp job logs show \
  --name "lexiqai-init-{purpose}-dev" \
  --resource-group "lexiqai-rg-dev" \
  --follow
```

### View in Portal

1. Go to Container Apps → Jobs
2. Click on your job
3. View "Executions" tab for history
4. Click on execution to see logs

## Cost Optimization

- **Minimal resources**: Use smallest CPU/memory needed
- **Fast execution**: Optimize scripts to complete quickly
- **Manual trigger**: Only run when needed (not scheduled)
- **Idempotent**: Safe to re-run if needed (no wasted executions)

## Security

- ✅ **Managed Identity**: No hardcoded credentials
- ✅ **Key Vault**: Secrets stored securely
- ✅ **VNet isolation**: Runs in same VNet as services
- ✅ **Private endpoints**: Can access private resources
- ✅ **Least privilege**: Only grant necessary permissions

## Troubleshooting

### Job Fails to Start

**Check**:
- Job exists: `az containerapp job show --name ...`
- Resource group exists
- Container Apps Environment is healthy

### Job Times Out

**Solutions**:
- Increase resource limits (CPU/memory)
- Optimize script performance
- Check for network connectivity issues

### Job Can't Access Resources

**Check**:
- Managed Identity has correct role assignments
- Key Vault secrets exist and are accessible
- Network connectivity (VNet, private endpoints)

### Job Succeeds But Nothing Happens

**Check**:
- Script logic (may be idempotent and skipping work)
- Logs to see what actually executed
- Verify prerequisites are met

## Examples

See `init-jobs.tf` for:
- Database role grant job (active)
- Database migration job (commented template)
- Multi-region setup job (commented template)

Uncomment and customize templates as needed for your use cases.
