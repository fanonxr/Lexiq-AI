"""Storage service for Azure Blob Storage operations."""

import logging
from datetime import datetime, timedelta
import re
import time
from typing import List, Optional
from urllib.parse import unquote

from azure.core.exceptions import AzureError
from azure.core.credentials import AzureNamedKeyCredential
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.storage.blob.aio import BlobServiceClient as AsyncBlobServiceClient
from azure.storage.blob import BlobClient
import azure.storage.blob  # For version checking

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
            logger.debug(
                f"Initializing sync blob client - connection_string: {bool(self.settings.storage.connection_string)}, "
                f"account_key: {bool(self.settings.storage.account_key)}, "
                f"use_managed_identity: {self.settings.storage.use_managed_identity}"
            )
            if self.settings.storage.connection_string:
                # Use connection string
                logger.info(
                    f"Using connection string for Azure Blob Storage. "
                    f"Connection string length: {len(self.settings.storage.connection_string)}"
                )
                try:
                    # Clean connection string: remove trailing semicolons and whitespace
                    conn_str = self.settings.storage.connection_string.strip().rstrip(';')
                    
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
                    
                    self._blob_service_client = BlobServiceClient.from_connection_string(
                        conn_str
                    )
                    logger.info("Successfully created BlobServiceClient from connection string")
                except Exception as e:
                    logger.error(f"Failed to create BlobServiceClient from connection string: {e}")
                    # Fallback to account_key method if available
                    if self.settings.storage.account_key and self.settings.storage.account_name:
                        logger.warning("Falling back to account_key method due to connection string parsing failure")
                        try:
                            account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                            credential = AzureNamedKeyCredential(
                                name=self.settings.storage.account_name,
                                key=self.settings.storage.account_key
                            )
                            self._blob_service_client = BlobServiceClient(
                                account_url=account_url,
                                credential=credential,
                            )
                            logger.info("Successfully created BlobServiceClient using account_key fallback")
                        except Exception as fallback_error:
                            logger.error(f"Fallback to account_key also failed: {fallback_error}")
                            raise ValueError(
                                f"Both connection string and account_key methods failed. "
                                f"Connection string error: {e}. "
                                f"Account key error: {fallback_error}"
                            ) from e
                    else:
                        raise
            elif self.settings.storage.account_key:
                # Use account key
                logger.info("Using account key for Azure Blob Storage")
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
            # Priority: connection_string > account_key > managed_identity
            logger.debug(
                f"Initializing async blob client - connection_string: {bool(self.settings.storage.connection_string)}, "
                f"account_key: {bool(self.settings.storage.account_key)}, "
                f"use_managed_identity: {self.settings.storage.use_managed_identity}"
            )
            
            if self.settings.storage.connection_string:
                # Use connection string (for Azure Storage or other scenarios)
                # Log SDK version for debugging
                try:
                    import azure.storage.blob
                    sdk_version = azure.storage.blob.__version__
                except Exception:
                    sdk_version = "unknown"
                
                logger.info(
                    f"Using connection string for Azure Blob Storage. "
                    f"Connection string length: {len(self.settings.storage.connection_string)}, "
                    f"Azure Storage Blob SDK version: {sdk_version}"
                )
                try:
                    # Clean connection string: remove trailing semicolons and whitespace
                    conn_str = self.settings.storage.connection_string.strip().rstrip(';')
                    
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
                    
                    # Log connection string preview for debugging (first 80 chars, hide sensitive parts)
                    conn_preview = conn_str[:80] + "..." if len(conn_str) > 80 else conn_str
                    # Mask account key in preview
                    if "AccountKey=" in conn_preview:
                        parts = conn_preview.split("AccountKey=")
                        if len(parts) > 1:
                            key_part = parts[1].split(";")[0]
                            masked_key = key_part[:4] + "..." + key_part[-4:] if len(key_part) > 8 else "***"
                            conn_preview = parts[0] + "AccountKey=" + masked_key + (parts[1].split(";", 1)[1] if ";" in parts[1] else "")
                    logger.debug(f"Connection string preview: {conn_preview}")
                    
                    # Try to extract account_name and account_key from connection string
                    # This helps avoid connection string parsing issues in Azure SDK
                    account_name_from_conn = None
                    account_key_from_conn = None
                    try:
                        # Parse connection string more carefully
                        # Handle cases where values might contain special characters
                        # Match AccountName=value (value can contain anything until ; or end of string)
                        account_name_match = re.search(r'AccountName=([^;]+)', conn_str)
                        if account_name_match:
                            account_name_from_conn = account_name_match.group(1).strip()
                        
                        # Match AccountKey=value (value can contain anything until ; or end of string)
                        account_key_match = re.search(r'AccountKey=([^;]+)', conn_str)
                        if account_key_match:
                            account_key_from_conn = account_key_match.group(1).strip()
                            # URL-decode the account key in case it was URL-encoded
                            # This handles cases where keys contain special characters like +, /, =
                            account_key_from_conn = unquote(account_key_from_conn)
                        
                        # Log extracted values with masking for debugging
                        if account_key_from_conn:
                            key_preview = f"{account_key_from_conn[:4]}...{account_key_from_conn[-4:]}" if len(account_key_from_conn) > 8 else "***"
                            logger.info(
                                f"Extracted from connection string - "
                                f"AccountName: '{account_name_from_conn}', "
                                f"AccountKey length: {len(account_key_from_conn)}, "
                                f"AccountKey preview: {key_preview}"
                            )
                        else:
                            logger.warning(f"Failed to extract AccountKey from connection string")
                        
                        # If we successfully extracted both, use account_key method instead
                        # This is more reliable than connection string parsing
                        if account_name_from_conn and account_key_from_conn:
                            logger.info(f"Extracted account_name '{account_name_from_conn}' from connection string, using account_key method for better reliability")
                            
                            # Verify account key format (should be base64, typically 88 chars)
                            key_length = len(account_key_from_conn)
                            logger.debug(f"Account key length: {key_length}, starts with: {account_key_from_conn[:4]}..., ends with: ...{account_key_from_conn[-4:]}")
                            
                            # Check for common issues
                            if key_length < 80 or key_length > 100:
                                logger.warning(f"Account key length ({key_length}) seems unusual. Expected ~88 characters for base64-encoded key.")
                            
                            account_url = f"https://{account_name_from_conn}.blob.core.windows.net"
                            logger.debug(f"Using account URL: {account_url}")
                            
                            # Check system time sync (important for Azure Storage authentication)
                            current_time = datetime.utcnow()
                            logger.debug(f"Current UTC time: {current_time.isoformat()}")
                            
                            credential = AzureNamedKeyCredential(
                                name=account_name_from_conn,
                                key=account_key_from_conn
                            )
                            # Note: API version is handled automatically by the SDK
                            # If you see x-ms-version:2025-11-05 errors, try upgrading azure-storage-blob
                            self._async_blob_service_client = AsyncBlobServiceClient(
                                account_url=account_url,
                                credential=credential,
                            )
                            # Log SDK version for debugging
                            try:
                                import azure.storage.blob
                                sdk_version = azure.storage.blob.__version__
                                logger.info(f"Azure Storage Blob SDK version: {sdk_version}")
                            except Exception:
                                pass
                            logger.info(f"Successfully created AsyncBlobServiceClient using extracted account_name '{account_name_from_conn}' and account_key")
                        else:
                            # Fallback to connection string method
                            logger.warning("Could not extract account_name/key from connection string, using connection string method")
                            self._async_blob_service_client = AsyncBlobServiceClient.from_connection_string(
                                conn_str
                            )
                            logger.info("Successfully created AsyncBlobServiceClient from connection string")
                    except Exception as parse_error:
                        logger.warning(f"Error extracting account details from connection string: {parse_error}, trying connection string method")
                        self._async_blob_service_client = AsyncBlobServiceClient.from_connection_string(
                            conn_str
                        )
                        logger.info("Successfully created AsyncBlobServiceClient from connection string")
                except Exception as e:
                    logger.error(f"Failed to create AsyncBlobServiceClient from connection string: {e}")
                    logger.error(f"Connection string format check - contains 'AccountName': {'AccountName=' in conn_str if 'conn_str' in locals() else 'N/A'}")
                    logger.error(f"Connection string format check - contains 'AccountKey': {'AccountKey=' in conn_str if 'conn_str' in locals() else 'N/A'}")
                    
                    # Fallback to account_key method if available
                    if self.settings.storage.account_key and self.settings.storage.account_name:
                        logger.warning("Falling back to account_key method due to connection string parsing failure")
                        try:
                            account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                            credential = AzureNamedKeyCredential(
                                name=self.settings.storage.account_name,
                                key=self.settings.storage.account_key
                            )
                            self._async_blob_service_client = AsyncBlobServiceClient(
                                account_url=account_url,
                                credential=credential,
                            )
                            logger.info("Successfully created AsyncBlobServiceClient using account_key fallback")
                        except Exception as fallback_error:
                            logger.error(f"Fallback to account_key also failed: {fallback_error}")
                            raise ValueError(
                                f"Both connection string and account_key methods failed. "
                                f"Connection string error: {e}. "
                                f"Account key error: {fallback_error}"
                            ) from e
                    else:
                        raise ValueError(
                            f"Connection string parsing failed and no account_key available for fallback. "
                            f"Error: {e}. "
                            f"Please check your connection string format or provide STORAGE_ACCOUNT_NAME and STORAGE_ACCOUNT_KEY instead."
                        ) from e
            elif self.settings.storage.account_key:
                # Use account key for real Azure Storage
                logger.info(f"Using account key for Azure Blob Storage (account: {self.settings.storage.account_name})")
                
                # URL-decode the account key in case it was URL-encoded in environment variable
                # This handles cases where keys contain special characters like +, /, =
                # See: https://learn.microsoft.com/en-us/answers/questions/1636967/how-to-fix-mac-signature-found-in-the-http-request
                account_key = unquote(self.settings.storage.account_key)
                
                # Verify account key format (should be base64, typically 88 chars)
                key_length = len(account_key)
                logger.debug(f"Account key length: {key_length}, starts with: {account_key[:4]}..., ends with: ...{account_key[-4:]}")
                
                # Check for common issues
                if key_length < 80 or key_length > 100:
                    logger.warning(f"Account key length ({key_length}) seems unusual. Expected ~88 characters for base64-encoded key.")
                
                account_url = f"https://{self.settings.storage.account_name}.blob.core.windows.net"
                logger.debug(f"Using account URL: {account_url}")
                
                # Check system time sync (important for Azure Storage authentication)
                # Time skew can cause authentication failures - Azure requires time to be within 15 minutes
                current_time = datetime.utcnow()
                logger.debug(f"Current UTC time: {current_time.isoformat()}")
                
                # Log time sync warning (Azure Storage requires time to be within 15 minutes of server time)
                # Note: Docker containers inherit host time, but if host is out of sync, auth will fail
                logger.debug(
                    "Note: Azure Storage authentication requires system clock to be within 15 minutes of Azure server time. "
                    "If authentication fails, check Docker container clock sync."
                )
                
                credential = AzureNamedKeyCredential(
                    name=self.settings.storage.account_name,
                    key=account_key
                )
                # Create client - API version is set automatically by SDK
                # If you see x-ms-version:2025-11-05, it's a bug in the SDK version
                self._async_blob_service_client = AsyncBlobServiceClient(
                    account_url=account_url,
                    credential=credential,
                )
                # Log SDK version for debugging
                try:
                    import azure.storage.blob
                    sdk_version = azure.storage.blob.__version__
                    logger.info(f"Azure Storage Blob SDK version: {sdk_version}")
                except Exception:
                    pass
                logger.info(f"Successfully created AsyncBlobServiceClient for account '{self.settings.storage.account_name}'")
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
                    "either STORAGE_CONNECTION_STRING or STORAGE_USE_MANAGED_IDENTITY=true"
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
            
            # Log the account URL for debugging
            try:
                account_url = client.account_name
                logger.debug(f"Using storage account: {account_url}")
            except Exception:
                pass
            
            container_client = client.get_container_client(container_name)

            # Check if container exists
            exists = await container_client.exists()
            if not exists:
                # Create container
                await container_client.create_container()
                logger.info(f"Created storage container: {container_name}")
            else:
                logger.debug(f"Container already exists: {container_name}")
        except Exception as e:
            error_msg = str(e)
            # Check for the specific connection string parsing error
            if "defaultendpointsprotocol" in error_msg.lower() or "name or service not known" in error_msg.lower():
                logger.error(
                    f"Connection string parsing issue detected. "
                    f"Error: {error_msg}. "
                    f"This usually means the connection string format is incorrect or the Azure SDK is misparsing it. "
                    f"Try using STORAGE_ACCOUNT_NAME and STORAGE_ACCOUNT_KEY instead of STORAGE_CONNECTION_STRING."
                )
                # Try to recreate client using account_key if available
                if self.settings.storage.account_key and self.settings.storage.account_name:
                    logger.warning("Attempting to recreate client using account_key method")
                    # Reset the client to force recreation
                    self._async_blob_service_client = None
                    try:
                        client = self._get_async_blob_service_client()
                        container_client = client.get_container_client(container_name)
                        exists = await container_client.exists()
                        if not exists:
                            await container_client.create_container()
                            logger.info(f"Created storage container: {container_name} (using account_key method)")
                        else:
                            logger.debug(f"Container already exists: {container_name} (using account_key method)")
                        return
                    except Exception as retry_error:
                        logger.error(f"Retry with account_key method also failed: {retry_error}")
                        raise AzureError(f"Failed to ensure container exists: {container_name}. Original error: {error_msg}. Retry error: {retry_error}") from e
            logger.error(f"Failed to ensure container exists: {container_name}: {e}")
            raise AzureError(f"Failed to ensure container exists: {container_name}: {e}") from e

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
            
            # Log account info for debugging
            try:
                account_name = client.account_name
                logger.debug(f"Uploading to storage account: {account_name}")
            except Exception:
                pass
            
            # Azure SDK handles blob name encoding automatically, but we should ensure
            # the blob name doesn't have leading/trailing slashes or invalid characters
            # The SDK will properly encode special characters in the blob path
            blob_name_clean = blob_name.strip('/')  # Remove leading/trailing slashes
            
            logger.debug(f"Uploading blob: container={container_name}, blob={blob_name_clean}, size: {len(file_data)} bytes")
            
            blob_client = client.get_blob_client(container=container_name, blob=blob_name_clean)
            
            # Upload blob - Azure SDK handles API version and blob name encoding automatically
            # Note: If you see x-ms-version:2025-11-05 errors, the SDK might need upgrading
            await blob_client.upload_blob(
                data=file_data,
                content_type=content_type,
                overwrite=True,  # Allow overwriting existing files
            )

            blob_url = blob_client.url
            logger.info(f"✅ Successfully uploaded blob to: {blob_url}")
            return blob_url

        except AzureError as e:
            error_msg = str(e)
            # Check for authentication errors
            if "authentication" in error_msg.lower() or "authorization" in error_msg.lower():
                logger.error(
                    f"Authentication failed when uploading file. "
                    f"This usually means the account key is incorrect or the connection string was not parsed correctly. "
                    f"Error: {error_msg}. "
                    f"Please verify STORAGE_ACCOUNT_NAME and STORAGE_ACCOUNT_KEY are correct, "
                    f"or check that the connection string was parsed correctly."
                )
                # Log what we're actually using
                try:
                    client = self._get_async_blob_service_client()
                    logger.debug(f"Current storage account: {client.account_name if hasattr(client, 'account_name') else 'unknown'}")
                except Exception:
                    pass
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

