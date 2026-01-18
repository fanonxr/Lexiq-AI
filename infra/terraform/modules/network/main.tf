# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  address_space       = var.vnet_address_space

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-vnet-${var.environment}"
    }
  )
}

# Compute Subnet (for Container Apps)
# Note: When using infrastructure_subnet_id in Container Apps Environment,
# the subnet should NOT be delegated. Container Apps will manage it automatically.
resource "azurerm_subnet" "compute" {
  name                 = "${var.project_name}-compute-subnet-${var.environment}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.compute_subnet_cidr]

  # Note: Delegation is NOT needed when using infrastructure_subnet_id
  # Container Apps Environment will automatically manage the subnet
  # Delegation is only needed if NOT using infrastructure_subnet_id
}

# Data Subnet (for databases)
resource "azurerm_subnet" "data" {
  name                 = "${var.project_name}-data-subnet-${var.environment}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.data_subnet_cidr]

  # Enable private endpoint network policies
  private_endpoint_network_policies = "Enabled"

  # Service delegation for PostgreSQL Flexible Server
  delegation {
    name = "Microsoft.DBforPostgreSQL/flexibleServers"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }

}

# Cache Subnet (for Redis Private Endpoints)
# Note: Azure Cache for Redis Basic/Standard SKUs use private endpoints, not VNet injection
# Premium SKU can use VNet injection (subnet_id), but we're using Basic/Standard
# So we use the private endpoint subnet for Redis private endpoints
# No delegation needed for private endpoints

# Private Endpoint Subnet
resource "azurerm_subnet" "private_endpoint" {
  name                 = "${var.project_name}-private-endpoint-subnet-${var.environment}"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.private_endpoint_subnet_cidr]

  # Enable private endpoint network policies
  private_endpoint_network_policies = "Enabled"
}

# Private DNS Zone for internal service discovery
resource "azurerm_private_dns_zone" "internal" {
  name                = "${var.project_name}.internal"
  resource_group_name = var.resource_group_name

  tags = var.common_tags
}

# Link Private DNS Zone to VNet
resource "azurerm_private_dns_zone_virtual_network_link" "internal" {
  name                  = "${var.project_name}-dns-link-${var.environment}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.internal.name
  virtual_network_id    = azurerm_virtual_network.main.id
  registration_enabled  = false # Manual registration only

  tags = var.common_tags
}

# Associate NSG with Compute Subnet
resource "azurerm_subnet_network_security_group_association" "compute" {
  subnet_id                 = azurerm_subnet.compute.id
  network_security_group_id = azurerm_network_security_group.compute.id
}

# Associate NSG with Data Subnet
resource "azurerm_subnet_network_security_group_association" "data" {
  subnet_id                 = azurerm_subnet.data.id
  network_security_group_id = azurerm_network_security_group.data.id
}

# Note: No cache subnet NSG association - Redis uses private endpoints

