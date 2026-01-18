# Data sources to reference shared resources
# These resources are created in the shared resource group and used across all environments

# Data source to reference shared Container Registry
data "azurerm_container_registry" "shared" {
  name                = "${replace(var.project_name, "-", "")}acrshared" # Name of shared ACR
  resource_group_name = "${var.project_name}-rg-shared"
}

# Data source to reference shared DNS Zone (if using Azure DNS)
# Only look up if DNS zone name is configured
data "azurerm_dns_zone" "shared" {
  count = var.dns_zone_name != "" ? 1 : 0

  name                = var.dns_zone_name
  resource_group_name = "${var.project_name}-rg-shared"
}
