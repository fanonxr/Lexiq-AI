# Storage Account Module

This module creates an Azure Storage Account for Blob Storage, used for storing knowledge base documents for RAG (Retrieval-Augmented Generation).

## Features

- Azure Storage Account (General Purpose V2)
- Blob Storage for document files
- Soft delete protection
- Versioning support (optional)
- Change feed (optional, for audit)
- Network access control

## Architecture

**One Storage Account** for the entire application with **multiple containers** (one per firm):
- Container naming: `firm-{firm_id}-documents`
- Containers are created dynamically in code when firms are created
- Access controlled via Managed Identity with container-level RBAC

## Usage

```hcl
module "storage" {
  source = "./modules/storage"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.azure_location
  resource_group_name = azurerm_resource_group.main.name

  account_tier             = "Standard"
  account_replication_type = "LRS"  # LRS for dev, GRS/ZRS for prod

  # Enable features for production
  versioning_enabled                = var.environment == "prod"
  blob_soft_delete_retention_days   = var.environment == "prod" ? 30 : 7
  change_feed_enabled              = var.environment == "prod"

  common_tags = var.common_tags
}
```

## Container Creation

Containers are **NOT** created in Terraform. They are created dynamically in code:

```python
# When firm is created (in Core API or Orchestrator)
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(
    account_url=f"https://{storage_account_name}.blob.core.windows.net",
    credential=credential
)

container_name = f"firm-{firm_id}-documents"
container_client = blob_service_client.get_container_client(container_name)
container_client.create_container()
```

## Access Control

### Recommended: Managed Identity

1. **Assign Managed Identity** to services (Container Apps, etc.)
2. **Grant RBAC role** at container level:
   - `Storage Blob Data Contributor` - Full access
   - `Storage Blob Data Reader` - Read-only access

```hcl
# Example: Grant access to Managed Identity
resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.managed_identity_principal_id
}
```

### Alternative: Access Keys

Access keys are available in outputs but should be avoided in favor of Managed Identity for security.

## Outputs

- `storage_account_name`: Name of the storage account
- `primary_blob_endpoint`: Blob endpoint URL
- `primary_access_key`: Access key (sensitive, use Managed Identity instead)

## Local Development

For local development, use **Azurite** (Blob Storage emulator) in Docker Compose:

```yaml
azurite:
  image: mcr.microsoft.com/azure-storage/azurite
  ports:
    - "10000:10000"  # Blob service
  volumes:
    - azurite_data:/data
```

Connection string for local:
```
DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;
```

## Cost Considerations

- **LRS (Locally Redundant)**: Cheapest, good for dev (~$0.005/GB/month)
- **GRS (Geo-Redundant)**: More expensive, better for prod (~$0.01/GB/month)
- **ZRS (Zone-Redundant)**: Higher availability, higher cost

## Security Best Practices

1. **Use Managed Identity** instead of access keys
2. **Enable HTTPS only** (default)
3. **Restrict network access** with private endpoints (for production)
4. **Enable soft delete** for recovery
5. **Enable versioning** for production
6. **Use container-level RBAC** for multi-tenant isolation

## References

- [Azure Storage Documentation](https://learn.microsoft.com/en-us/azure/storage/)
- [Blob Storage Best Practices](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-best-practices)
- [Azurite Emulator](https://github.com/Azure/Azurite)

