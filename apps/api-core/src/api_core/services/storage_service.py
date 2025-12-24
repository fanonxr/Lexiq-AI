"""Storage service for Azure Blob Storage operations."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from azure.core.exceptions import AzureError
from azure.core.credentials import AzureNamedKeyCredential
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
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
            # Priority: connection_string > account_key > managed_identity
            # For local development (Azurite), connection_string is preferred
            logger.debug(
                f"Initializing sync blob client - connection_string: {bool(self.settings.storage.connection_string)}, "
                f"account_key: {bool(self.settings.storage.account_key)}, "
                f"use_managed_identity: {self.settings.storage.use_managed_identity}"
            )
            if self.settings.storage.connection_string:
                # Use connection string (preferred for local dev with Azurite)
                logger.info(
                    f"Using connection string for Azure Blob Storage (Azurite/local). "
                    f"Connection string length: {len(self.settings.storage.connection_string)}"
                )
                try:
                    self._blob_service_client = BlobServiceClient.from_connection_string(
                        self.settings.storage.connection_string
                    )
                except Exception as e:
                    logger.error(f"Failed to create BlobServiceClient from connection string: {e}")
                    raise
            elif self.settings.storage.account_key:
                # Use account key
                logger.info("Using account key for Azure Blob Storage")
                # Check if this is Azurite
                is_azurite = (
                    self.settings.storage.connection_string and "azurite" in self.settings.storage.connection_string.lower()
                ) or (
                    self.settings.storage.account_name == "devstoreaccount1"
                )
                if is_azurite:
                    account_url = f"http://azurite:10000/{self.settings.storage.account_name}"
                else:
                    account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                credential = AzureNamedKeyCredential(
                    name=self.settings.storage.account_name,
                    key=self.settings.storage.account_key
                )
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential,
                )
            elif self.settings.storage.use_managed_identity:
                # Use Managed Identity (for production Azure deployments)
                logger.info("Using Managed Identity for Azure Blob Storage")
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self._blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=credential
                )
            else:
                raise ValueError(
                    "Storage credentials not configured. Set STORAGE_ACCOUNT_NAME and "
                    "either STORAGE_CONNECTION_STRING (for local/Azurite) or STORAGE_USE_MANAGED_IDENTITY=true (for Azure)"
                )
        return self._blob_service_client

    def _get_async_blob_service_client(self) -> AsyncBlobServiceClient:
        """Get or create AsyncBlobServiceClient."""
        if self._async_blob_service_client is None:
            # Priority: account_key (for Azurite) > connection_string > managed_identity
            # For Azurite, account_key with AzureNamedKeyCredential is more reliable
            logger.debug(
                f"Initializing async blob client - connection_string: {bool(self.settings.storage.connection_string)}, "
                f"account_key: {bool(self.settings.storage.account_key)}, "
                f"use_managed_identity: {self.settings.storage.use_managed_identity}"
            )
            
            # Check if this is Azurite (local dev)
            is_azurite = (
                self.settings.storage.connection_string and "azurite" in self.settings.storage.connection_string.lower()
            ) or (
                self.settings.storage.account_name == "devstoreaccount1"
            )
            
            # For Azurite, connection string is most reliable (handles endpoint correctly)
            if is_azurite and self.settings.storage.connection_string:
                logger.info("Using connection string for Azurite (most reliable method)")
                try:
                    # Remove any trailing semicolons that might cause issues
                    conn_str = self.settings.storage.connection_string.rstrip(';')
                    self._async_blob_service_client = AsyncBlobServiceClient.from_connection_string(
                        conn_str
                    )
                    logger.info(f"Successfully created AsyncBlobServiceClient for Azurite using connection string")
                except Exception as e:
                    logger.error(f"Failed to create AsyncBlobServiceClient from connection string: {e}")
                    # Fallback to account_key method
                    if self.settings.storage.account_key:
                        logger.info("Falling back to account_key method for Azurite")
                        account_url = f"http://azurite:10000/{self.settings.storage.account_name}"
                        credential = AzureNamedKeyCredential(
                            name=self.settings.storage.account_name,
                            key=self.settings.storage.account_key
                        )
                        self._async_blob_service_client = AsyncBlobServiceClient(
                            account_url=account_url,
                            credential=credential,
                        )
                    else:
                        raise
            elif self.settings.storage.connection_string:
                # Use connection string (fallback for local dev or other scenarios)
                logger.info(
                    f"Using connection string for Azure Blob Storage. "
                    f"Connection string length: {len(self.settings.storage.connection_string)}"
                )
                try:
                    self._async_blob_service_client = AsyncBlobServiceClient.from_connection_string(
                        self.settings.storage.connection_string
                    )
                except Exception as e:
                    logger.error(f"Failed to create AsyncBlobServiceClient from connection string: {e}")
                    raise
            elif self.settings.storage.account_key:
                # Use account key for real Azure Storage
                logger.info("Using account key for Azure Blob Storage")
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                credential = AzureNamedKeyCredential(
                    name=self.settings.storage.account_name,
                    key=self.settings.storage.account_key
                )
                self._async_blob_service_client = AsyncBlobServiceClient(
                    account_url=account_url,
                    credential=credential,
                )
            elif self.settings.storage.use_managed_identity:
                # Use Managed Identity (for production Azure deployments)
                logger.info("Using Managed Identity for Azure Blob Storage")
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self._async_blob_service_client = AsyncBlobServiceClient(
                    account_url=account_url, credential=credential
                )
            else:
                raise ValueError(
                    "Storage credentials not configured. Set STORAGE_ACCOUNT_NAME and "
                    "either STORAGE_CONNECTION_STRING (for local/Azurite) or STORAGE_USE_MANAGED_IDENTITY=true (for Azure)"
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

    async def generate_signed_url(
        self,
        container_name: str,
        blob_name: str,
        expiry_minutes: int = 60,
    ) -> str:
        """Generate a signed URL for a blob.

        Args:
            container_name: Name of the container
            blob_name: Name of the blob
            expiry_minutes: URL expiration time in minutes (default: 60)

        Returns:
            Signed URL with SAS token

        Raises:
            AzureError: If URL generation fails
            ValueError: If storage is not configured for SAS token generation
        """
        try:
            client = self._get_async_blob_service_client()
            blob_client = client.get_blob_client(container=container_name, blob=blob_name)

            # Check if blob exists
            if not await blob_client.exists():
                raise ValueError(f"Blob {container_name}/{blob_name} does not exist")

            # Generate SAS token
            # Note: SAS tokens require account_key or connection_string
            # If using managed identity only, we can't generate SAS tokens
            # In that case, we return the blob URL (which requires authentication)
            if not self.settings.storage.account_key and not self.settings.storage.connection_string:
                logger.warning(
                    "Cannot generate SAS token: account_key or connection_string not configured. "
                    "Returning blob URL (requires authentication)."
                )
                # Return the blob URL (will require authentication to access)
                sync_client = self._get_blob_service_client()
                sync_blob_client = sync_client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                return sync_blob_client.url

            # Generate SAS token with read permission
            # For connection string, extract account key
            account_key = self.settings.storage.account_key
            if not account_key and self.settings.storage.connection_string:
                # Extract account key from connection string
                # Format: DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=...
                from urllib.parse import parse_qs, urlparse
                parts = self.settings.storage.connection_string.split(";")
                for part in parts:
                    if part.startswith("AccountKey="):
                        account_key = part.split("=", 1)[1]
                        break

            if not account_key:
                raise ValueError(
                    "Cannot generate SAS token: account_key not available. "
                    "Configure STORAGE_ACCOUNT_KEY or use connection string."
                )

            sync_client = self._get_blob_service_client()
            sync_blob_client = sync_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.settings.storage.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes),
            )

            # Construct signed URL
            signed_url = f"{sync_blob_client.url}?{sas_token}"
            logger.info(
                f"Generated signed URL for {container_name}/{blob_name}, expires in {expiry_minutes} minutes"
            )
            return signed_url

        except AzureError as e:
            logger.error(f"Failed to generate signed URL for {container_name}/{blob_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating signed URL: {e}")
            raise AzureError(f"Failed to generate signed URL: {str(e)}") from e

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

