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
                self._client = BlobServiceClient.from_connection_string(
                    settings.storage.connection_string
                )
                logger.info("Created BlobServiceClient with connection string")
            else:
                raise StorageError("Storage not configured. Set STORAGE_ACCOUNT_NAME and either STORAGE_USE_MANAGED_IDENTITY or STORAGE_CONNECTION_STRING")

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

