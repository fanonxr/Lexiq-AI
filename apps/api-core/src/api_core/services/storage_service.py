"""Storage service for Azure Blob Storage operations."""

import logging
from typing import List, Optional

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient

from api_core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    """Service for Azure Blob Storage operations."""

    def __init__(self):
        """Initialize storage service."""
        self.settings = get_settings()
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._async_blob_service_client: Optional[AsyncBlobServiceClient] = None

    def _get_blob_service_client(self) -> BlobServiceClient:
        """Get or create BlobServiceClient (synchronous)."""
        if self._blob_service_client is None:
            if self.settings.storage.use_managed_identity:
                # Use Managed Identity
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=credential
                )
            elif self.settings.storage.connection_string:
                # Use connection string
                self._blob_service_client = BlobServiceClient.from_connection_string(
                    self.settings.storage.connection_string
                )
            elif self.settings.storage.account_key:
                # Use account key
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.settings.storage.account_key,
                )
            else:
                raise ValueError(
                    "Storage credentials not configured. Set STORAGE_ACCOUNT_NAME and "
                    "either STORAGE_USE_MANAGED_IDENTITY=true or STORAGE_CONNECTION_STRING"
                )
        return self._blob_service_client

    def _get_async_blob_service_client(self) -> AsyncBlobServiceClient:
        """Get or create AsyncBlobServiceClient."""
        if self._async_blob_service_client is None:
            if self.settings.storage.use_managed_identity:
                # Use Managed Identity
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self._async_blob_service_client = AsyncBlobServiceClient(
                    account_url=account_url, credential=credential
                )
            elif self.settings.storage.connection_string:
                # Use connection string
                self._async_blob_service_client = AsyncBlobServiceClient.from_connection_string(
                    self.settings.storage.connection_string
                )
            elif self.settings.storage.account_key:
                # Use account key
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                self._async_blob_service_client = AsyncBlobServiceClient(
                    account_url=account_url,
                    credential=self.settings.storage.account_key,
                )
            else:
                raise ValueError(
                    "Storage credentials not configured. Set STORAGE_ACCOUNT_NAME and "
                    "either STORAGE_USE_MANAGED_IDENTITY=true or STORAGE_CONNECTION_STRING"
                )
        return self._async_blob_service_client

    async def ensure_container_exists(self, container_name: str) -> None:
        """Ensure a container exists, create if it doesn't.

        Args:
            container_name: Name of the container

        Raises:
            AzureError: If container creation fails
        """
        try:
            client = self._get_async_blob_service_client()
            container_client = client.get_container_client(container_name)

            # Check if container exists
            exists = await container_client.exists()
            if not exists:
                # Create container
                await container_client.create_container()
                logger.info(f"Created storage container: {container_name}")
            else:
                logger.debug(f"Container already exists: {container_name}")
        except AzureError as e:
            logger.error(f"Failed to ensure container exists: {container_name}: {e}")
            raise

    async def upload_file(
        self,
        container_name: str,
        blob_name: str,
        file_data: bytes,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to Blob Storage.

        Args:
            container_name: Name of the container (e.g., firm-{firm_id}-documents)
            blob_name: Name of the blob (file path within container)
            file_data: File data as bytes
            content_type: Optional content type (MIME type)

        Returns:
            Blob URL

        Raises:
            AzureError: If upload fails
        """
        try:
            # Ensure container exists
            await self.ensure_container_exists(container_name)

            # Upload file
            client = self._get_async_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_name)

            await blob_client.upload_blob(
                data=file_data,
                content_type=content_type,
                overwrite=True,  # Allow overwriting existing files
            )

            blob_url = blob_client.url
            logger.info(f"Uploaded file to blob storage: {blob_url}")
            return blob_url

        except AzureError as e:
            logger.error(f"Failed to upload file to blob storage: {e}")
            raise

    async def delete_file(self, container_name: str, blob_name: str) -> None:
        """Delete a file from Blob Storage.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob

        Raises:
            AzureError: If deletion fails
        """
        try:
            client = self._get_async_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_name)

            await blob_client.delete_blob()
            logger.info(f"Deleted file from blob storage: {container_name}/{blob_name}")

        except AzureError as e:
            logger.error(f"Failed to delete file from blob storage: {e}")
            raise

    async def file_exists(self, container_name: str, blob_name: str) -> bool:
        """Check if a file exists in Blob Storage.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob

        Returns:
            True if file exists, False otherwise
        """
        try:
            client = self._get_async_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_name)
            return await blob_client.exists()
        except AzureError as e:
            logger.error(f"Failed to check if file exists: {e}")
            return False

    def get_container_name(self, firm_id: str) -> str:
        """Get container name for a firm.

        Args:
            firm_id: Firm ID

        Returns:
            Container name: firm-{firm_id}-documents
        """
        return f"firm-{firm_id}-documents"

    async def close(self) -> None:
        """Close storage clients."""
        if self._async_blob_service_client:
            await self._async_blob_service_client.close()


# Global service instance
_storage_service: Optional["StorageService"] = None


def get_storage_service() -> StorageService:
    """Get the global Storage service instance.

    Returns:
        StorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service

