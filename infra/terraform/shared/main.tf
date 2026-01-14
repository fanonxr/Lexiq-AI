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
