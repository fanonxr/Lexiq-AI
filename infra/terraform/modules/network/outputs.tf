output "vnet_id" {
  description = "ID of the Virtual Network"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Name of the Virtual Network"
  value       = azurerm_virtual_network.main.name
}

output "vnet_address_space" {
  description = "Address space of the Virtual Network"
  value       = azurerm_virtual_network.main.address_space
}

output "compute_subnet_id" {
  description = "ID of the compute subnet"
  value       = azurerm_subnet.compute.id
}

output "compute_subnet_name" {
  description = "Name of the compute subnet"
  value       = azurerm_subnet.compute.name
}

output "data_subnet_id" {
  description = "ID of the data subnet"
  value       = azurerm_subnet.data.id
}

output "data_subnet_name" {
  description = "Name of the data subnet"
  value       = azurerm_subnet.data.name
}

output "private_endpoint_subnet_id" {
  description = "ID of the private endpoint subnet"
  value       = azurerm_subnet.private_endpoint.id
}

output "private_endpoint_subnet_name" {
  description = "Name of the private endpoint subnet"
  value       = azurerm_subnet.private_endpoint.name
}

output "compute_nsg_id" {
  description = "ID of the compute subnet NSG"
  value       = azurerm_network_security_group.compute.id
}

output "data_nsg_id" {
  description = "ID of the data subnet NSG"
  value       = azurerm_network_security_group.data.id
}

output "private_dns_zone_id" {
  description = "ID of the private DNS zone"
  value       = azurerm_private_dns_zone.internal.id
}

output "private_dns_zone_name" {
  description = "Name of the private DNS zone"
  value       = azurerm_private_dns_zone.internal.name
}

