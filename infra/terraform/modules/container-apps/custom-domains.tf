# Custom Domain Configuration for Container Apps
# Container Apps supports automatic SSL/TLS with Let's Encrypt for custom domains

# API Core Custom Domain
# Container Apps automatically uses managed certificates (Let's Encrypt) for custom domains
resource "azurerm_container_app_custom_domain" "api_core" {
  count = var.api_core_custom_domain != "" ? 1 : 0

  container_app_id = azurerm_container_app.api_core.id
  name             = var.api_core_custom_domain
}

# Voice Gateway Custom Domain
# Container Apps automatically uses managed certificates (Let's Encrypt) for custom domains
resource "azurerm_container_app_custom_domain" "voice_gateway" {
  count = var.voice_gateway_custom_domain != "" ? 1 : 0

  container_app_id = azurerm_container_app.voice_gateway.id
  name             = var.voice_gateway_custom_domain
}

# Integration Worker Webhooks Custom Domain
# Container Apps automatically uses managed certificates (Let's Encrypt) for custom domains
resource "azurerm_container_app_custom_domain" "integration_webhooks" {
  count = var.integration_webhooks_custom_domain != "" ? 1 : 0

  container_app_id = azurerm_container_app.integration_worker_webhooks.id
  name             = var.integration_webhooks_custom_domain
}
