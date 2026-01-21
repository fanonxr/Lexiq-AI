terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.47"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }

  # Backend configuration will be set via backend.tf or backend config
  # For local development, backend can be omitted or use local backend
}

# Configure the Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }

  # Subscription and tenant can be set via environment variables or backend config
  # subscription_id = var.subscription_id
  # tenant_id       = var.tenant_id
}

# Configure the Azure AD Provider (for App Registrations)
provider "azuread" {
  # Tenant ID can be set via environment variable AZURE_TENANT_ID or here
  # tenant_id = var.tenant_id
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg-${var.environment}"
  location = var.azure_location

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Network Module
module "network" {
  source = "./modules/network"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  vnet_address_space           = var.vnet_address_space
  compute_subnet_cidr          = var.compute_subnet_cidr
  data_subnet_cidr             = var.data_subnet_cidr
  private_endpoint_subnet_cidr = var.private_endpoint_subnet_cidr

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Database Module
# Explicitly depends on network module to ensure VNet and subnets are created first
module "database" {
  source = "./modules/database"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  data_subnet_id             = module.network.data_subnet_id
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  vnet_id                    = module.network.vnet_id

  database_name         = "lexiqai"
  admin_username        = var.postgres_admin_username
  admin_password        = var.postgres_admin_password
  postgres_version      = var.postgres_version
  sku_name              = var.postgres_sku_name
  storage_mb            = var.postgres_storage_mb
  backup_retention_days = var.postgres_backup_retention_days
  # Note: Workload type is determined by SKU (B_Standard_* = DevTest, GP_Standard_* = GeneralPurpose)

  # Security: Disable direct access, use private endpoints only
  allow_azure_services        = false
  allow_compute_subnet_access = false

  # High availability only for production
  high_availability_enabled    = var.environment == "prod"
  geo_redundant_backup_enabled = var.environment == "prod"

  # Azure AD Authentication (enabled by default, can be disabled)
  azure_ad_auth_enabled = true

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.network # Ensure network is fully created before database
  ]
}

# Azure AD Administrator for PostgreSQL
# This must be created AFTER both the database and identity exist
# to avoid circular dependencies
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "main" {
  server_name         = module.database.server_name
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = var.tenant_id
  object_id           = module.identity.principal_id
  principal_name      = module.identity.name
  principal_type      = "ServicePrincipal"

  depends_on = [
    module.database,
    module.identity
  ]
}

# Grant Database Roles to Managed Identity
# This automates the SQL execution to grant database-level roles
# Note: This requires psql to be installed and database password to be available
# If psql is not available, you can run the script manually: infra/terraform/scripts/grant-postgres-database-roles.sh
resource "null_resource" "grant_database_roles" {
  count = var.grant_postgres_database_roles ? 1 : 0

  depends_on = [
    azurerm_postgresql_flexible_server_active_directory_administrator.main,
    module.database,
    module.identity
  ]

  triggers = {
    # Re-run if identity or database changes
    identity_principal_id = module.identity.principal_id
    identity_name         = module.identity.name
    server_id             = module.database.server_id
    database_name         = module.database.database_name
    server_fqdn           = module.database.server_fqdn
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Check if psql is available
      if ! command -v psql &> /dev/null; then
        echo "WARNING: psql not found. Skipping automatic database role grants."
        echo "The Azure AD administrator has been configured, but database roles need to be granted manually."
        echo ""
        echo "To grant database roles, run:"
        echo "  cd infra/terraform/scripts"
        echo "  ./grant-postgres-database-roles.sh ${var.environment}"
        echo ""
        echo "Or install PostgreSQL client tools:"
        echo "  macOS: brew install postgresql"
        echo "  Linux: sudo apt-get install postgresql-client"
        exit 0  # Don't fail terraform apply - this is optional
      fi
      
      set -e

      echo "Granting database roles to Managed Identity: ${module.identity.name}"
      echo "Server: ${module.database.server_fqdn}"
      echo "Database: ${module.database.database_name}"
      
      # Export password for psql
      export PGPASSWORD="${var.postgres_admin_password}"
      
      # Create SQL script for better error handling
      SQL_FILE=$(mktemp)
      cat > "$SQL_FILE" <<SQL
-- Grant Database Roles to Managed Identity

-- Create Azure AD user if it doesn't exist
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${module.identity.name}') THEN
        EXECUTE format('CREATE USER %I FROM EXTERNAL PROVIDER', '${module.identity.name}');
        RAISE NOTICE 'Created Azure AD user: ${module.identity.name}';
    ELSE
        RAISE NOTICE 'Azure AD user already exists: ${module.identity.name}';
    END IF;
END
\$\$;

-- Grant database roles (idempotent - safe to run multiple times)
ALTER ROLE "${module.identity.name}" GRANT db_datareader;
ALTER ROLE "${module.identity.name}" GRANT db_datawriter;
ALTER ROLE "${module.identity.name}" GRANT db_ddladmin;

-- Verify the user exists
SELECT 
    rolname AS role_name,
    'Database roles granted successfully' AS status
FROM pg_roles 
WHERE rolname = '${module.identity.name}';
SQL

      # Execute SQL script
      psql \
        "host=${module.database.server_fqdn} port=5432 dbname=${module.database.database_name} user=${var.postgres_admin_username} sslmode=require" \
        -f "$SQL_FILE"
      
      # Clean up
      rm -f "$SQL_FILE"
      
      echo "✓ Database roles granted successfully!"
    EOT

    environment = {
      PGPASSWORD = var.postgres_admin_password
    }
  }
}

# Redis Cache Module - MIGRATED TO CONTAINER APP
# Azure Cache for Redis has been replaced with containerized Redis in Container Apps
# This module is kept for reference but is no longer used
# 
# module "cache" {
#   source = "./modules/cache"
#
#   project_name        = var.project_name
#   environment         = var.environment
#   location            = var.azure_location
#   resource_group_name = azurerm_resource_group.main.name
#
#   private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
#   vnet_id                    = module.network.vnet_id
#
#   sku_name      = var.redis_sku_name
#   family        = var.redis_family
#   capacity      = var.redis_capacity
#   redis_version = var.redis_version
#
#   # Enable non-SSL port for local dev compatibility (dev only)
#   enable_non_ssl_port = var.environment == "dev"
#
#   # RDB backup disabled for dev, can be enabled for prod
#   rdb_backup_enabled = var.environment == "prod"
#
#   common_tags = merge(
#     var.common_tags,
#     {
#       Environment = var.environment
#       ManagedBy   = "Terraform"
#     }
#   )
#
#   depends_on = [
#     module.network # Ensure network is fully created before Redis
#   ]
# }

# Identity Module
# Creates user-assigned managed identity and role assignments
# Depends on database and cache modules to grant access
module "identity" {
  source = "./modules/identity"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name
  resource_group_id   = azurerm_resource_group.main.id

  # Pass resource IDs for role assignments
  postgres_server_id = module.database.server_id
  # redis_cache_id is no longer needed - Redis is now containerized
  # redis_cache_id     = module.cache.cache_id
  storage_account_id = module.storage.storage_account_id

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.database, # Need database server ID for role assignment
    module.storage   # Need storage account ID for role assignment
    # module.cache is no longer needed - Redis is now containerized
  ]
}

# Key Vault for Secrets Management
# Stores sensitive configuration like API keys, connection strings, etc.
# Always enabled for all environments
resource "azurerm_key_vault" "main" {
  count = 1

  name                = "${var.project_name}-kv-${var.environment}"
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  # Soft delete and purge protection
  soft_delete_retention_days = 7
  purge_protection_enabled   = var.environment == "prod"

  # Network access (can be restricted later)
  public_network_access_enabled = true

  # Access policies
  # Current user (for Terraform operations)
  access_policy {
    tenant_id = var.tenant_id
    object_id = data.azurerm_client_config.current[0].object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Recover",
      "Backup",
      "Restore",
      "Purge",
    ]
  }

  # Managed Identity (for Container Apps to read secrets)
  access_policy {
    tenant_id = var.tenant_id
    object_id = module.identity.principal_id

    secret_permissions = [
      "Get",
      "List",
    ]
  }

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.identity # Ensure Managed Identity exists before creating Key Vault access policy
  ]
}

# Grant Managed Identity access to Key Vault using Azure RBAC (preferred method)
# This is more modern than access policies and works better with Container Apps
resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = azurerm_key_vault.main[0].id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.identity.principal_id

  depends_on = [
    azurerm_key_vault.main,
    module.identity
  ]
}

# Data source for current Azure client config (for Key Vault access policy)
data "azurerm_client_config" "current" {
  count = 1
}

# Azure Container Registry - MIGRATED TO SHARED RESOURCES
# The Container Registry is now shared across all environments (see infra/terraform/shared/)
# This resource is kept for reference but is no longer used
# 
# To migrate:
# 1. Import existing images to shared ACR (see Phase 4)
# 2. Remove this resource from Terraform state: terraform state rm azurerm_container_registry.main
# 3. Remove this resource block from main.tf
#
# resource "azurerm_container_registry" "main" {
#   name                = "${replace(var.project_name, "-", "")}acr${var.environment}"
#   resource_group_name = azurerm_resource_group.main.name
#   location            = var.azure_location
#   sku                 = var.environment == "prod" ? "Premium" : "Basic"
#   admin_enabled       = false # Use Managed Identity instead
#   ...
# }

# Grant environment Managed Identity access to pull from shared ACR
# This allows Container Apps in this environment to pull images from the shared registry
resource "azurerm_role_assignment" "shared_acr_pull" {
  scope                = data.azurerm_container_registry.shared.id
  role_definition_name = "AcrPull"
  principal_id         = module.identity.principal_id

  depends_on = [
    module.identity,
    data.azurerm_container_registry.shared
  ]
}

# Note: Push access (AcrPush) is granted to GitHub Actions service principal in shared resources
# Environment Managed Identities only need AcrPull access

# Storage Account Module
# Creates Azure Blob Storage for knowledge base documents (RAG)
module "storage" {
  source = "./modules/storage"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  account_tier                  = var.storage_account_tier
  account_replication_type      = var.storage_account_replication_type
  public_network_access_enabled = var.storage_public_network_access_enabled

  # Enable features for production
  versioning_enabled                   = var.environment == "prod"
  blob_soft_delete_retention_days      = var.storage_blob_soft_delete_retention_days
  container_soft_delete_retention_days = var.storage_container_soft_delete_retention_days
  change_feed_enabled                  = var.environment == "prod"

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Log Analytics Workspace
# Required for Container Apps Environment and Application Insights
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs-${var.environment}"
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.environment == "prod" ? 90 : 30

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Application Insights
# Centralized observability for all application services
resource "azurerm_application_insights" "main" {
  name                = "${var.project_name}-appinsights-${var.environment}"
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.main.id

  # Enable sampling for cost optimization (optional)
  sampling_percentage = var.environment == "prod" ? 100 : 50

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Store Application Insights connection string in Key Vault
resource "azurerm_key_vault_secret" "appinsights_connection_string" {
  count        = length(azurerm_key_vault.main) > 0 ? 1 : 0
  name         = "appinsights-connection-string"
  value        = azurerm_application_insights.main.connection_string
  key_vault_id = azurerm_key_vault.main[0].id

  content_type = "application-insights-connection-string"

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    azurerm_application_insights.main,
    azurerm_key_vault.main
  ]
}

# Diagnostic Settings for PostgreSQL
resource "azurerm_monitor_diagnostic_setting" "postgres" {
  name                       = "postgres-diagnostics"
  target_resource_id         = module.database.server_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "PostgreSQLLogs"
    # Note: retention_policy is deprecated - retention is managed by Log Analytics Workspace
  }

  metric {
    category = "AllMetrics"
    enabled  = true
    # Note: retention_policy is deprecated - retention is managed by Log Analytics Workspace
  }
}

# Diagnostic Settings for Key Vault
resource "azurerm_monitor_diagnostic_setting" "key_vault" {
  count                      = length(azurerm_key_vault.main) > 0 ? 1 : 0
  name                       = "key-vault-diagnostics"
  target_resource_id         = azurerm_key_vault.main[0].id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category = "AuditEvent"
    # Note: retention_policy is deprecated - retention is managed by Log Analytics Workspace
  }

  metric {
    category = "AllMetrics"
    enabled  = true
    # Note: retention_policy is deprecated - retention is managed by Log Analytics Workspace
  }
}

# Diagnostic Settings for Storage Account
# Note: Storage Account log categories are not always available depending on storage account type
# Only metrics are enabled here as they are universally supported
resource "azurerm_monitor_diagnostic_setting" "storage" {
  name                       = "storage-diagnostics"
  target_resource_id         = module.storage.storage_account_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  # Note: StorageRead, StorageWrite, StorageDelete log categories are not supported
  # for all storage account types. If you need logs, enable them manually in Azure Portal
  # or use Azure Storage Analytics (classic) which is being phased out.

  metric {
    category = "Transaction"
    enabled  = true
    # Note: retention_policy is deprecated - retention is managed by Log Analytics Workspace
  }
}

# Container Apps Module
# Deploys containerized services including Redis (migrated from Azure Cache for Redis)
module "container_apps" {
  source = "./modules/container-apps"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  # Network
  subnet_id = module.network.compute_subnet_id

  # Identity
  managed_identity_id = module.identity.resource_id

  # Log Analytics (required for Container Apps Environment)
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  # Key Vault (for secrets)
  key_vault_id   = length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].id : null
  key_vault_name = length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].name : null

  # Application Insights
  application_insights_connection_string = azurerm_application_insights.main.connection_string

  # Dependencies
  postgres_fqdn              = module.database.server_fqdn
  postgres_database_name     = "lexiqai"
  postgres_admin_username    = var.postgres_admin_username
  managed_identity_name      = module.identity.name
  storage_account_name       = module.storage.storage_account_name
  storage_account_access_key = module.storage.primary_access_key

  # File Shares for persistent storage
  qdrant_file_share_name   = module.storage.qdrant_file_share_name
  rabbitmq_file_share_name = module.storage.rabbitmq_file_share_name

  # Custom Domains (optional - leave empty to use default Container Apps FQDN)
  api_core_custom_domain             = var.api_core_custom_domain
  voice_gateway_custom_domain        = var.voice_gateway_custom_domain
  integration_webhooks_custom_domain = var.integration_webhooks_custom_domain

  # Container Registry - Now using shared ACR
  container_registry = data.azurerm_container_registry.shared.login_server
  image_tag          = var.container_image_tag

  # Redis configuration
  redis_password_secret_name = "redis-password"

  # Scaling configuration (environment-specific)
  redis_min_replicas = var.environment == "prod" ? 1 : 0 # Scale to zero for dev
  redis_max_replicas = var.environment == "prod" ? 2 : 1
  redis_cpu          = var.environment == "prod" ? 1.0 : 0.5
  redis_memory       = var.environment == "prod" ? "2Gi" : "1Gi"

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.network,                                         # Need subnet for Container Apps Environment
    module.identity,                                        # Need Managed Identity
    azurerm_log_analytics_workspace.main,                   # Need Log Analytics Workspace
    azurerm_application_insights.main,                      # Need Application Insights
    azurerm_key_vault_secret.appinsights_connection_string, # Need Application Insights secret in Key Vault
    data.azurerm_container_registry.shared                  # Need shared Container Registry
  ]
}

# Azure AD App Registration Module
# Manages Entra ID App Registration with redirect URIs, API permissions, and exposed API
module "auth" {
  source = "./modules/auth"

  project_name = var.project_name
  environment  = var.environment

  # Sign-in audience (who can sign in)
  sign_in_audience = var.azure_ad_sign_in_audience

  # Redirect URIs
  # Web redirect URIs (for server-side OAuth flows)
  web_redirect_uris = var.azure_ad_web_redirect_uris

  # SPA redirect URIs (for frontend OAuth flows)
  spa_redirect_uris = var.azure_ad_spa_redirect_uris

  # API Configuration
  api_application_id_uri = var.azure_ad_api_application_id_uri

  # Exposed API scopes (for frontend to request tokens for backend)
  exposed_api_scopes = var.azure_ad_exposed_api_scopes

  # Microsoft Graph API Permissions
  microsoft_graph_permissions = var.azure_ad_microsoft_graph_permissions

  # Additional resource access (if needed)
  additional_resource_access = var.azure_ad_additional_resource_access

  # App roles (for RBAC)
  app_roles = var.azure_ad_app_roles

  # Client Secret
  create_client_secret     = var.azure_ad_create_client_secret
  client_secret_expiration = var.azure_ad_client_secret_expiration

  # Key Vault Integration
  key_vault_id = length(azurerm_key_vault.main) > 0 ? azurerm_key_vault.main[0].id : null

  # Service Principal
  app_role_assignment_required = var.azure_ad_app_role_assignment_required

  # Admin Consent (requires appropriate permissions)
  grant_admin_consent = var.azure_ad_grant_admin_consent

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Azure DNS Zone - MIGRATED TO SHARED RESOURCES
# The DNS Zone is now shared across all environments (see infra/terraform/shared/)
# This resource is kept for reference but is no longer used
# 
# To migrate:
# 1. Export DNS records from this zone (see Phase 4)
# 2. Remove this resource from Terraform state: terraform state rm azurerm_dns_zone.main[0]
# 3. Remove this resource block from main.tf
#
# resource "azurerm_dns_zone" "main" {
#   count = var.dns_zone_name != "" ? 1 : 0
#   name                = var.dns_zone_name
#   resource_group_name = azurerm_resource_group.main.name
#   ...
# }

# CNAME Records for Container Apps Custom Domains
# These are created only if custom domains are configured and DNS zone exists
# Note: These depend on Container Apps being created first to get the FQDN
resource "azurerm_dns_cname_record" "api_core" {
  count = var.api_core_custom_domain != "" && var.dns_zone_name != "" ? 1 : 0

  name                = replace(var.api_core_custom_domain, ".${var.dns_zone_name}", "")
  zone_name           = data.azurerm_dns_zone.shared[0].name
  resource_group_name = "${var.project_name}-rg-shared" # Shared resource group
  ttl                 = 300
  record              = module.container_apps.api_core_hostname

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.container_apps,
    data.azurerm_dns_zone.shared
  ]
}

resource "azurerm_dns_cname_record" "voice_gateway" {
  count = var.voice_gateway_custom_domain != "" && var.dns_zone_name != "" ? 1 : 0

  name                = replace(var.voice_gateway_custom_domain, ".${var.dns_zone_name}", "")
  zone_name           = data.azurerm_dns_zone.shared[0].name
  resource_group_name = "${var.project_name}-rg-shared" # Shared resource group
  ttl                 = 300
  record              = module.container_apps.voice_gateway_hostname

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.container_apps,
    data.azurerm_dns_zone.shared
  ]
}

# Note: integration_webhooks service was removed, so this DNS record is no longer needed
# resource "azurerm_dns_cname_record" "integration_webhooks" {
#   ...
# }

# Local values for Static Web App configuration
# Note: static_web_app_url will be computed after the resource is created

# Azure Static Web App
# Deploys the Next.js frontend application
resource "azurerm_static_web_app" "frontend" {
  name                = "${var.project_name}-web-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.static_web_app_location

  # SKU Configuration
  sku_tier = var.environment == "prod" ? "Standard" : "Free"
  sku_size = var.environment == "prod" ? "Standard" : "Free"

  # Tags
  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Note: App settings for Static Web Apps must be configured via Azure Portal or CLI
# after the resource is created. Terraform doesn't support app_settings directly.
# Use: az staticwebapp appsettings set --name <name> --resource-group <rg> --setting-names <key>=<value>

# Custom Domain for Static Web App (optional)
resource "azurerm_static_web_app_custom_domain" "frontend" {
  count = var.static_web_app_custom_domain != "" ? 1 : 0

  static_web_app_id = azurerm_static_web_app.frontend.id
  domain_name       = var.static_web_app_custom_domain
  validation_type   = "cname-delegation" # Static Web Apps uses CNAME validation
}

# DNS CNAME Record for Static Web App Custom Domain (if using Azure DNS)
resource "azurerm_dns_cname_record" "static_web_app" {
  count = var.static_web_app_custom_domain != "" && var.dns_zone_name != "" ? 1 : 0

  name                = replace(var.static_web_app_custom_domain, ".${var.dns_zone_name}", "")
  zone_name           = data.azurerm_dns_zone.shared[0].name
  resource_group_name = "${var.project_name}-rg-shared" # Shared resource group
  ttl                 = 300
  record              = azurerm_static_web_app.frontend.default_host_name

  tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    azurerm_static_web_app.frontend,
    data.azurerm_dns_zone.shared
  ]
}

# GitHub OIDC Federation - MIGRATED TO SHARED RESOURCES
# The GitHub OIDC application is now shared across all environments (see infra/terraform/shared/)
# This module is kept for reference but is no longer used
# 
# To migrate:
# 1. Update GitHub Actions secrets with shared application ID (see Phase 4)
# 2. Remove this module from Terraform state: terraform state rm 'module.github_oidc[0]'
# 3. Remove this module block from main.tf
#
# module "github_oidc" {
#   source = "./modules/github-oidc"
#   count  = var.github_repository != "" ? 1 : 0
#   ...
# }
