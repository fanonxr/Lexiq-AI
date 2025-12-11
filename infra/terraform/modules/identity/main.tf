# User-assigned Managed Identity
# This identity will be used by all services (Container Apps, etc.) for passwordless authentication
resource "azurerm_user_assigned_identity" "main" {
  name                = "${var.project_name}-identity-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-identity-${var.environment}"
    }
  )
}

