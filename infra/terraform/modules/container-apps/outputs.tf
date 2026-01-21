# Container Apps Environment Outputs
output "container_app_environment_id" {
  description = "ID of the Container Apps Environment"
  value       = azurerm_container_app_environment.main.id
}

output "container_app_environment_name" {
  description = "Name of the Container Apps Environment"
  value       = azurerm_container_app_environment.main.name
}

# Init Jobs Outputs
output "init_job_grant_database_roles_id" {
  description = "ID of the database role grant init job"
  value       = azurerm_container_app_job.grant_database_roles.id
}

output "init_job_grant_database_roles_name" {
  description = "Name of the database role grant init job"
  value       = azurerm_container_app_job.grant_database_roles.name
}

# Redis Container App Outputs
output "redis_container_app_id" {
  description = "ID of the Redis container app"
  value       = azurerm_container_app.redis.id
}

output "redis_container_app_name" {
  description = "Name of the Redis container app"
  value       = azurerm_container_app.redis.name
}

output "redis_hostname" {
  description = "Hostname (FQDN) of the Redis container app for internal connections"
  value       = azurerm_container_app.redis.ingress[0].fqdn
  sensitive   = false # Internal FQDN is not sensitive
}

output "redis_port" {
  description = "Port number for Redis connections"
  value       = 6379
}

output "redis_url" {
  description = "Redis connection URL (without password - password should come from Key Vault)"
  value       = "redis://${azurerm_container_app.redis.ingress[0].fqdn}:6379"
  sensitive   = false # URL without password is not sensitive
}

# API Core Outputs
output "api_core_hostname" {
  description = "Hostname (FQDN) of the API Core container app (default Container Apps FQDN)"
  value       = azurerm_container_app.api_core.ingress[0].fqdn
}

output "api_core_custom_domain" {
  description = "Custom domain for API Core (if configured)"
  value       = var.api_core_custom_domain != "" ? var.api_core_custom_domain : null
}

output "api_core_url" {
  description = "URL of the API Core container app (uses custom domain if configured, otherwise default FQDN)"
  value       = var.api_core_custom_domain != "" ? "https://${var.api_core_custom_domain}" : "https://${azurerm_container_app.api_core.ingress[0].fqdn}"
}

# Cognitive Orchestrator Outputs
output "cognitive_orch_hostname" {
  description = "Hostname (FQDN) of the Cognitive Orchestrator container app"
  value       = azurerm_container_app.cognitive_orch.ingress[0].fqdn
}

output "cognitive_orch_url" {
  description = "URL of the Cognitive Orchestrator container app"
  value       = "http://${azurerm_container_app.cognitive_orch.ingress[0].fqdn}"
}

# Voice Gateway Outputs
output "voice_gateway_hostname" {
  description = "Hostname (FQDN) of the Voice Gateway container app (default Container Apps FQDN)"
  value       = azurerm_container_app.voice_gateway.ingress[0].fqdn
}

output "voice_gateway_custom_domain" {
  description = "Custom domain for Voice Gateway (if configured)"
  value       = var.voice_gateway_custom_domain != "" ? var.voice_gateway_custom_domain : null
}

output "voice_gateway_url" {
  description = "URL of the Voice Gateway container app (uses custom domain if configured, otherwise default FQDN)"
  value       = var.voice_gateway_custom_domain != "" ? "https://${var.voice_gateway_custom_domain}" : "https://${azurerm_container_app.voice_gateway.ingress[0].fqdn}"
}

# Qdrant Outputs
output "qdrant_hostname" {
  description = "Hostname (FQDN) of the Qdrant container app"
  value       = azurerm_container_app.qdrant.ingress[0].fqdn
}

output "qdrant_url" {
  description = "URL of the Qdrant container app"
  value       = "http://${azurerm_container_app.qdrant.ingress[0].fqdn}"
}

# RabbitMQ Outputs
output "rabbitmq_hostname" {
  description = "Hostname (FQDN) of the RabbitMQ container app"
  value       = azurerm_container_app.rabbitmq.ingress[0].fqdn
}

# Integration Worker Webhooks Outputs
output "integration_worker_webhooks_hostname" {
  description = "Hostname (FQDN) of the Integration Worker Webhooks container app (default Container Apps FQDN)"
  value       = azurerm_container_app.integration_worker_webhooks.ingress[0].fqdn
}

output "integration_worker_webhooks_custom_domain" {
  description = "Custom domain for Integration Worker Webhooks (if configured)"
  value       = var.integration_webhooks_custom_domain != "" ? var.integration_webhooks_custom_domain : null
}

output "integration_worker_webhooks_url" {
  description = "URL of the Integration Worker Webhooks container app (uses custom domain if configured, otherwise default FQDN)"
  value       = var.integration_webhooks_custom_domain != "" ? "https://${var.integration_webhooks_custom_domain}" : "https://${azurerm_container_app.integration_worker_webhooks.ingress[0].fqdn}"
}
