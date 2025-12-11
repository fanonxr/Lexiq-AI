# Firewall Rule: Allow Azure Services
# Note: With private endpoints, firewall rules are less critical but kept for flexibility
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  count            = var.allow_azure_services ? 1 : 0
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Firewall Rule: Allow access from compute subnet (if needed for troubleshooting)
# Note: With private endpoints, this may not be necessary, but kept as optional
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_compute_subnet" {
  count            = var.allow_compute_subnet_access ? 1 : 0
  name             = "AllowComputeSubnet"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = var.compute_subnet_start_ip
  end_ip_address   = var.compute_subnet_end_ip
}


