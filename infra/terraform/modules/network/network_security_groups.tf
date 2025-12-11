# Network Security Group for Compute Subnet
resource "azurerm_network_security_group" "compute" {
  name                = "${var.project_name}-compute-nsg-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-compute-nsg-${var.environment}"
      Subnet      = "compute"
      Description = "NSG for compute subnet (Container Apps)"
    }
  )
}

# Allow outbound to data subnet (PostgreSQL)
resource "azurerm_network_security_rule" "compute_to_postgres" {
  name                        = "AllowPostgreSQL"
  priority                    = 1000
  direction                   = "Outbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "5432"
  source_address_prefix      = var.compute_subnet_cidr
  destination_address_prefix = var.data_subnet_cidr
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.compute.name
}

# Note: Redis uses private endpoints (in private_endpoint_subnet)
# Private endpoints are handled by Azure, no explicit NSG rule needed
# Traffic to Redis goes through the private endpoint in the private_endpoint_subnet

# Allow outbound HTTPS for Azure services (Container Registry, Key Vault, etc.)
resource "azurerm_network_security_rule" "compute_to_https" {
  name                        = "AllowHTTPS"
  priority                    = 1020
  direction                   = "Outbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "443"
  source_address_prefix      = var.compute_subnet_cidr
  destination_address_prefix = "Internet"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.compute.name
}

# Allow outbound DNS
resource "azurerm_network_security_rule" "compute_to_dns" {
  name                        = "AllowDNS"
  priority                    = 1030
  direction                   = "Outbound"
  access                     = "Allow"
  protocol                   = "Udp"
  source_port_range          = "*"
  destination_port_range     = "53"
  source_address_prefix      = var.compute_subnet_cidr
  destination_address_prefix = "Internet"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.compute.name
}

# Network Security Group for Data Subnet
resource "azurerm_network_security_group" "data" {
  name                = "${var.project_name}-data-nsg-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = merge(
    var.common_tags,
    {
      Name        = "${var.project_name}-data-nsg-${var.environment}"
      Subnet      = "data"
      Description = "NSG for data subnet (Databases)"
    }
  )
}

# Allow inbound PostgreSQL from compute subnet only
resource "azurerm_network_security_rule" "data_from_compute_postgres" {
  name                        = "AllowPostgreSQLFromCompute"
  priority                    = 1000
  direction                   = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "5432"
  source_address_prefix       = var.compute_subnet_cidr
  destination_address_prefix  = var.data_subnet_cidr
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.data.name
}

# Note: Redis is now in a separate cache subnet, so Redis rules are in cache NSG

# Deny all other inbound traffic (default Azure behavior, but explicit for clarity)
resource "azurerm_network_security_rule" "data_deny_all_inbound" {
  name                        = "DenyAllInbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                     = "Deny"
  protocol                   = "*"
  source_port_range          = "*"
  destination_port_range     = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.data.name
}

# Allow outbound to Azure services (for backups, monitoring, etc.)
resource "azurerm_network_security_rule" "data_to_azure_services" {
  name                        = "AllowAzureServices"
  priority                    = 1000
  direction                   = "Outbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "443"
  source_address_prefix       = var.data_subnet_cidr
  destination_address_prefix  = "AzureCloud"
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.data.name
}

# Note: Redis uses private endpoints (in private_endpoint_subnet), not a dedicated cache subnet
# No cache NSG needed - private endpoints handle security
