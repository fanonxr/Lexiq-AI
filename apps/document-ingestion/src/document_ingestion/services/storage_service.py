"""Azure Blob Storage service for file operations."""

from typing import Optional

from azure.core.exceptions import AzureError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from document_ingestion.config import get_settings
from document_ingestion.utils.errors import IngestionException, StorageError
from document_ingestion.utils.logging import get_logger

logger = get_logger("storage_service")
settings = get_settings()


class StorageService:
    """
    Service for interacting with Azure Blob Storage.

    Handles:
    - Downloading files from blob storage
    - Container and blob path parsing
    """

    def __init__(self):
        """Initialize storage service."""
        self._client: Optional[BlobServiceClient] = None

    async def _get_client(self) -> BlobServiceClient:
        """
        Get or create BlobServiceClient.

        Returns:
            BlobServiceClient instance

        Raises:
            StorageError: If client creation fails
        """
        if self._client is not None:
            return self._client

        try:
            if settings.storage.use_managed_identity:
                # Use Managed Identity
                account_url = f"https://{settings.storage.account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self._client = BlobServiceClient(account_url=account_url, credential=credential)
                logger.info(f"Created BlobServiceClient with Managed Identity: {settings.storage.account_name}")
            elif settings.storage.connection_string:
                # Use connection string
                try:
                    # Clean connection string: remove trailing semicolons and whitespace
                    conn_str = settings.storage.connection_string.strip().rstrip(';')
                    
                    # Remove quotes if present (common issue with env vars)
                    if conn_str.startswith('"') and conn_str.endswith('"'):
                        conn_str = conn_str[1:-1]
                    if conn_str.startswith("'") and conn_str.endswith("'"):
                        conn_str = conn_str[1:-1]
                    
                    # Validate connection string format
                    if not conn_str or len(conn_str) < 50:
                        raise ValueError("Connection string appears to be too short or empty")
                    
                    # Validate required components
                    if "AccountName=" not in conn_str:
                        raise ValueError("Connection string missing AccountName component")
                    if "AccountKey=" not in conn_str and "SharedAccessSignature=" not in conn_str:
                        raise ValueError("Connection string missing AccountKey or SharedAccessSignature")
                    
                    self._client = BlobServiceClient.from_connection_string(conn_str)
                    logger.info("Created BlobServiceClient with connection string")
                except Exception as conn_error:
                    logger.error(f"Failed to create BlobServiceClient from connection string: {conn_error}")
                    # Fallback to account_key if available
                    if settings.storage.account_key and settings.storage.account_name:
                        logger.warning("Falling back to account_key method due to connection string parsing failure")
                        from azure.storage.blob.aio import BlobServiceClient
                        from azure.core.credentials import AzureNamedKeyCredential
                        account_url = f"https://{settings.storage.account_name}.blob.core.windows.net"
                        credential = AzureNamedKeyCredential(
                            name=settings.storage.account_name,
                            key=settings.storage.account_key
                        )
                        self._client = BlobServiceClient(account_url=account_url, credential=credential)
                        logger.info("Created BlobServiceClient using account_key fallback")
                    else:
                        raise StorageError(
                            f"Connection string parsing failed and no account_key available for fallback. "
                            f"Error: {conn_error}. "
                            f"Please check your connection string format or provide STORAGE_ACCOUNT_NAME and STORAGE_ACCOUNT_KEY instead."
                        ) from conn_error
            elif settings.storage.account_key and settings.storage.account_name:
                # Use account key directly
                from azure.core.credentials import AzureNamedKeyCredential
                account_url = f"https://{settings.storage.account_name}.blob.core.windows.net"
                credential = AzureNamedKeyCredential(
                    name=settings.storage.account_name,
                    key=settings.storage.account_key
                )
                self._client = BlobServiceClient(account_url=account_url, credential=credential)
                logger.info("Created BlobServiceClient with account key")
            else:
                raise StorageError("Storage not configured. Set STORAGE_ACCOUNT_NAME and either STORAGE_USE_MANAGED_IDENTITY, STORAGE_CONNECTION_STRING, or STORAGE_ACCOUNT_KEY")

            return self._client
        except Exception as e:
            logger.error(f"Failed to create BlobServiceClient: {e}", exc_info=True)
            raise StorageError(f"Failed to initialize storage client: {str(e)}") from e

    async def download_file(self, blob_path: str) -> bytes:
        """
        Download file from Azure Blob Storage.

        Args:
            blob_path: Blob path in format "container/blob_name" or full path

        Returns:
            File content as bytes

        Raises:
            StorageError: If download fails
        """
        try:
            # Parse blob path (format: container/blob_name or container/path/to/blob)
            if "/" not in blob_path:
                raise StorageError(f"Invalid blob path format: {blob_path}. Expected 'container/blob_name'")

            parts = blob_path.split("/", 1)
            container_name = parts[0]
            blob_name = parts[1]

            logger.info(f"Downloading file: container={container_name}, blob={blob_name}")

            client = await self._get_client()
            container_client = client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            # Download blob
            download_stream = await blob_client.download_blob()
            file_data = await download_stream.readall()

            logger.info(
                f"Successfully downloaded file: {blob_path}, "
                f"size={len(file_data)} bytes"
            )

            return file_data

        except AzureError as e:
            logger.error(f"Azure Storage error downloading file: {blob_path} - {e}", exc_info=True)
            raise StorageError(f"Failed to download file from storage: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {blob_path} - {e}", exc_info=True)
            raise StorageError(f"Failed to download file: {str(e)}") from e

    async def close(self) -> None:
        """Close storage client."""
        if self._client:
            try:
                await self._client.close()
                self._client = None
                logger.info("Storage client closed")
            except Exception as e:
                logger.error(f"Error closing storage client: {e}", exc_info=True)

