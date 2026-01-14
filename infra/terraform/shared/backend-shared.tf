# Terraform Backend Configuration for Shared Resources
# This file configures where Terraform stores its state for shared resources
#
# Currently using local state. To use remote state in Azure Storage:
# 1. Create a storage account for Terraform state (see backend-shared.tf.example)
# 2. Uncomment the backend block below and update with your storage account details
# 3. Run: terraform init -migrate-state

# terraform {
#   backend "azurerm" {
#     # Storage Account for Terraform state (shared resources)
#     # Use the same storage account as your environment-specific state, or create a separate one
#     resource_group_name  = "lexiqai-tfstate-rg"  # Update with your Terraform state resource group
#     storage_account_name = "lexiqaitfstatedev"    # Update with your Terraform state storage account (must be globally unique)
#     container_name       = "terraform-state"      # Same container as environment-specific state, or use "tfstate-shared"
#     key                  = "shared/terraform.tfstate"  # Separate key for shared resources
#
#     # Optional: Enable state locking
#     # State locking is automatically enabled with Azure Storage backend
#   }
# }

# Using local state for now (state will be stored in terraform.tfstate file)
# This is fine for development. Migrate to remote state before production.
