# Generic Init Jobs for Container Apps
# These jobs can be used for various initialization tasks:
# - Database role grants
# - Database migrations
# - Multi-region setup
# - One-time configuration tasks

# ============================================================================
# Database Role Grant Job
# Grants PostgreSQL database roles to Managed Identity
# ============================================================================
resource "azurerm_container_app_job" "grant_database_roles" {
  name                         = "${var.project_name}-init-grant-db-roles-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  location                     = var.location

  # Assign Managed Identity to access Key Vault
  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  # Secrets from Key Vault
  dynamic "secret" {
    for_each = var.key_vault_name != null ? {
      "postgres-admin-password" = "https://${var.key_vault_name}.vault.azure.net/secrets/postgres-admin-password"
    } : {}
    content {
      name                = secret.key
      key_vault_secret_id = secret.value
      identity            = var.managed_identity_id
    }
  }

  # Replica timeout (required at resource level)
  replica_timeout_in_seconds = 300 # 5 minutes timeout

  # Job configuration
  template {
    container {
      name  = "grant-roles"
      image = "postgres:16-alpine"

      # Environment variables
      env {
        name  = "PGHOST"
        value = var.postgres_fqdn
      }

      env {
        name  = "PGPORT"
        value = "5432"
      }

      env {
        name  = "PGDATABASE"
        value = var.postgres_database_name
      }

      env {
        name  = "PGUSER"
        value = var.postgres_admin_username
      }

      env {
        name        = "PGPASSWORD"
        secret_name = "postgres-admin-password"
      }

      env {
        name  = "PGSSLMODE"
        value = "require"
      }

      env {
        name  = "IDENTITY_NAME"
        value = var.managed_identity_name
      }

      # Command to run the SQL script
      command = [
        "sh",
        "-c",
        <<-EOT
          echo "=== Database Role Grant Init Job ==="
          echo "Granting database roles to Managed Identity: $IDENTITY_NAME"
          echo "Server: $PGHOST"
          echo "Database: $PGDATABASE"
          
          psql <<SQL
          -- Create Azure AD user if it doesn't exist
          DO \$\$
          BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$IDENTITY_NAME') THEN
                  EXECUTE format('CREATE USER %I FROM EXTERNAL PROVIDER', '$IDENTITY_NAME');
                  RAISE NOTICE 'Created Azure AD user: $IDENTITY_NAME';
              ELSE
                  RAISE NOTICE 'Azure AD user already exists: $IDENTITY_NAME';
              END IF;
          END
          \$\$;
          
          -- Grant database roles
          ALTER ROLE "$IDENTITY_NAME" GRANT db_datareader;
          ALTER ROLE "$IDENTITY_NAME" GRANT db_datawriter;
          ALTER ROLE "$IDENTITY_NAME" GRANT db_ddladmin;
          
          -- Verify
          SELECT 
              rolname AS role_name,
              'Database roles granted successfully' AS status
          FROM pg_roles 
          WHERE rolname = '$IDENTITY_NAME';
          SQL
          
          echo "✓ Database roles granted successfully!"
        EOT
      ]

      # Resource limits
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  # Manual trigger configuration
  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-init-grant-db-roles-${var.environment}"
      Purpose     = "Init job: Grant database roles"
      JobType     = "init"
      JobCategory = "database"
    }
  )
}

# ============================================================================
# Generic Init Job Template
# This can be used for custom initialization tasks
# ============================================================================
# Example: Database Migration Job
# Uncomment and customize as needed
#
# resource "azurerm_container_app_job" "database_migration" {
#   name                         = "${var.project_name}-init-db-migration-${var.environment}"
#   container_app_environment_id = azurerm_container_app_environment.main.id
#   resource_group_name          = var.resource_group_name
#
#   identity {
#     type         = "UserAssigned"
#     identity_ids = [var.managed_identity_id]
#   }
#
#   template {
#     container {
#       name  = "migrate"
#       image = "${var.container_registry}/${var.project_name}/api-core:${var.image_tag}"
#
#       env {
#         name  = "DATABASE_URL"
#         value = "postgresql://${var.managed_identity_name}@${var.postgres_fqdn}:5432/${var.postgres_database_name}?sslmode=require"
#       }
#
#       command = ["python", "-m", "alembic", "upgrade", "head"]
#
#       cpu    = 0.5
#       memory = "1Gi"
#     }
#
#     manual_trigger_config {
#       parallelism             = 1
#       replica_completion_count = 1
#     }
#   }
#
#   trigger_type = "Manual"
#
#   tags = merge(
#     var.common_tags,
#     {
#       Name        = "${var.project_name}-init-db-migration-${var.environment}"
#       Purpose     = "Init job: Database migrations"
#       JobType     = "init"
#       JobCategory = "database"
#     }
#   )
# }

# ============================================================================
# Multi-Region Setup Job (Example)
# Can be used when scaling to new regions
# ============================================================================
# Uncomment and customize when needed
#
# resource "azurerm_container_app_job" "multi_region_setup" {
#   name                         = "${var.project_name}-init-multi-region-${var.environment}"
#   container_app_environment_id = azurerm_container_app_environment.main.id
#   resource_group_name          = var.resource_group_name
#
#   identity {
#     type         = "UserAssigned"
#     identity_ids = [var.managed_identity_id]
#   }
#
#   template {
#     container {
#       name  = "setup"
#       image = "mcr.microsoft.com/azure-cli:latest"
#
#       env {
#         name  = "TARGET_REGION"
#         value = var.secondary_region # Would need to add this variable
#       }
#
#       command = [
#         "sh",
#         "-c",
#         <<-EOT
#           echo "Setting up resources in region: $TARGET_REGION"
#           # Your multi-region setup script here
#           echo "✓ Multi-region setup complete!"
#         EOT
#       ]
#
#       cpu    = 0.5
#       memory = "1Gi"
#     }
#
#     manual_trigger_config {
#       parallelism             = 1
#       replica_completion_count = 1
#     }
#   }
#
#   trigger_type = "Manual"
#
#   tags = merge(
#     var.common_tags,
#     {
#       Name        = "${var.project_name}-init-multi-region-${var.environment}"
#       Purpose     = "Init job: Multi-region setup"
#       JobType     = "init"
#       JobCategory = "infrastructure"
#     }
#   )
# }
