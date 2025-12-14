terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
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

  depends_on = [
    module.network # Ensure network is fully created before database
  ]

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

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Redis Cache Module
# Explicitly depends on network module to ensure VNet and subnets are created first
module "cache" {
  source = "./modules/cache"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  vnet_id                    = module.network.vnet_id

  sku_name      = var.redis_sku_name
  family        = var.redis_family
  capacity      = var.redis_capacity
  redis_version = var.redis_version

  # Enable non-SSL port for local dev compatibility (dev only)
  enable_non_ssl_port = var.environment == "dev"

  # RDB backup disabled for dev, can be enabled for prod
  rdb_backup_enabled = var.environment == "prod"

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.network # Ensure network is fully created before Redis
  ]
}

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
  redis_cache_id     = module.cache.cache_id

  common_tags = merge(
    var.common_tags,
    {
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    module.database, # Need database server ID for role assignment
    module.cache     # Need cache ID for role assignment
  ]
}

