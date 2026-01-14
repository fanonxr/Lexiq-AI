# Container Apps Environment
# This is the shared environment where all container apps will run
resource "azurerm_container_app_environment" "main" {
  name                       = "${var.project_name}-cae-${var.environment}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  infrastructure_subnet_id   = var.subnet_id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  # VNet integration - all apps will run in the VNet
  internal_load_balancer_enabled = var.environment == "prod"

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-cae-${var.environment}"
    }
  )
}

# Container Apps Environment Storage for Qdrant
# Registers the Azure File Share with the Container Apps Environment
resource "azurerm_container_app_environment_storage" "qdrant" {
  name                         = "qdrant-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = var.storage_account_name
  share_name                   = var.qdrant_file_share_name
  access_key                   = var.storage_account_access_key
  access_mode                  = "ReadWrite"
}

# Container Apps Environment Storage for RabbitMQ
# Registers the Azure File Share with the Container Apps Environment
resource "azurerm_container_app_environment_storage" "rabbitmq" {
  name                         = "rabbitmq-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = var.storage_account_name
  share_name                   = var.rabbitmq_file_share_name
  access_key                   = var.storage_account_access_key
  access_mode                  = "ReadWrite"
}
