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
  }

  # Backend configuration is in backend-shared.tf
  # This allows the backend to be configured separately from the main configuration
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

provider "azuread" {
  # Tenant ID from environment variable or config
}

# Shared Resource Group
resource "azurerm_resource_group" "shared" {
  name     = "${var.project_name}-rg-shared"
  location = var.azure_location

  tags = merge(
    var.common_tags,
    {
      Environment = "shared"
      Purpose     = "Shared resources across all environments"
    }
  )
}

# Shared Azure Container Registry
resource "azurerm_container_registry" "shared" {
  name                = "${replace(var.project_name, "-", "")}acrshared" # ACR names must be globally unique, lowercase, alphanumeric
  resource_group_name = azurerm_resource_group.shared.name
  location            = azurerm_resource_group.shared.location
  sku                 = "Basic" # Premium for better performance and features
  admin_enabled       = false   # Use Managed Identity instead

  # Network access - can be configured per environment needs
  public_network_access_enabled = true # Can be restricted later with private endpoints

  # Retention policy to manage costs (Premium SKU only)
  retention_policy {
    days    = 30
    enabled = false
  }

  # Enable geo-replication for high availability (optional, Premium SKU feature)
  # Uncomment if you want geo-replication
  # geo_replications {
  #   location = "westus2"
  #   tags     = {}
  # }

  tags = merge(
    var.common_tags,
    {
      Environment = "shared"
      Purpose     = "Shared container registry for all environments"
    }
  )
}

# Data sources to look up environment resource groups
# These resource groups are created by environment-specific Terraform configs
# Only look up resource groups that are specified (may not all exist yet)
data "azurerm_resource_group" "environments" {
  for_each = var.environment_resource_group_names
  name     = each.value
}

# Shared GitHub OIDC Application
# This will be used by all environments (dev, staging, prod)
module "github_oidc" {
  source = "../modules/github-oidc"

  project_name = var.project_name
  environment  = "shared" # Shared across all environments

  # GitHub repository (same for all environments)
  github_repository = var.github_repository

  # Use GitHub environments (recommended) - matches GitHub Actions workflow
  github_environments = var.github_environments

  # Legacy branch support (for backward compatibility)
  github_branch = var.github_branch

  # Reference to shared container registry
  container_registry_id = azurerm_container_registry.shared.id
  resource_group_id     = azurerm_resource_group.shared.id
  key_vault_id          = null # Key Vaults remain environment-specific

  # Map of environment names to resource group IDs for role assignments
  # This allows GitHub Actions to deploy to all environments
  # Only includes resource groups specified in environment_resource_group_names
  environment_resource_group_ids = {
    for env, rg_name in var.environment_resource_group_names :
    env => data.azurerm_resource_group.environments[env].id
  }

  tags = merge(
    var.common_tags,
    {
      Environment = "shared"
      Purpose     = "GitHub Actions OIDC for all environments"
    }
  )

  # Ensure Container Registry and data sources are ready before GitHub OIDC module
  depends_on = [
    azurerm_container_registry.shared,
    azurerm_resource_group.shared,
    data.azurerm_resource_group.environments
  ]
}

# Shared Azure DNS Zone
# Only create if you're using Azure DNS (not external DNS provider)
resource "azurerm_dns_zone" "shared" {
  count = var.dns_zone_name != "" ? 1 : 0

  name                = var.dns_zone_name
  resource_group_name = azurerm_resource_group.shared.name

  tags = merge(
    var.common_tags,
    {
      Environment = "shared"
      Purpose     = "Shared DNS zone for all environments"
    }
  )
}

# Terraform State Storage Account
# Dedicated storage account for Terraform state files (dev, prod, shared)
# This is separate from application storage accounts used by microservices
resource "azurerm_resource_group" "tfstate" {
  name     = "${var.project_name}-tfstate-rg"
  location = var.azure_location

  tags = merge(
    var.common_tags,
    {
      Environment = "shared"
      Purpose     = "Terraform State Storage"
      ManagedBy   = "Terraform"
    }
  )
}

resource "azurerm_storage_account" "tfstate" {
  name                     = "${replace(var.project_name, "-", "")}tfstate"
  resource_group_name      = azurerm_resource_group.tfstate.name
  location                 = azurerm_resource_group.tfstate.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"

  # Security: Disable public access
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true # Can be restricted later with private endpoints

  # Enable HTTPS only
  https_traffic_only_enabled = true

  # Blob properties for state file recovery
  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }

    container_delete_retention_policy {
      days = 30
    }

    change_feed_enabled = true
  }

  tags = merge(
    var.common_tags,
    {
      Environment = "shared"
      Purpose     = "Terraform State Storage"
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    azurerm_resource_group.tfstate
  ]
}

# Container for Terraform state files
resource "azurerm_storage_container" "tfstate" {
  name                  = "terraform-state"
  storage_account_name  = azurerm_storage_account.tfstate.name
  container_access_type = "private"

  depends_on = [
    azurerm_storage_account.tfstate
  ]
}

# Data source for current Azure client config (for role assignments)
data "azurerm_client_config" "current" {}

# Grant GitHub Actions OIDC Service Principal access to Terraform state storage
# This allows GitHub Actions to read/write state files
resource "azurerm_role_assignment" "github_oidc_tfstate" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = module.github_oidc.service_principal_id

  depends_on = [
    azurerm_storage_account.tfstate,
    module.github_oidc
  ]
}

# Grant current user (running Terraform) access to Terraform state storage
# This allows you to read/write state files via Azure CLI and Terraform
resource "azurerm_role_assignment" "current_user_tfstate" {
  scope                = azurerm_storage_account.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id

  depends_on = [
    azurerm_storage_account.tfstate
  ]
}
