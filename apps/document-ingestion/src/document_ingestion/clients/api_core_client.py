"""API Core client for status updates and file information."""

from typing import Optional

import httpx

from document_ingestion.config import get_settings
from document_ingestion.models.message import IngestionStatus
from document_ingestion.utils.errors import IngestionException
from document_ingestion.utils.logging import get_logger

logger = get_logger("api_core_client")
settings = get_settings()


class APICoreClient:
    """
    HTTP client for communicating with API Core service.

    Handles:
    - Updating file processing status
    - Updating Qdrant information
    - Retrieving file information
    """

    def __init__(self):
        """Initialize API Core client."""
        self.base_url = settings.api_core.url.rstrip("/")
        self.timeout = settings.api_core.timeout
        self._headers = {}
        if getattr(settings.api_core, "api_key", None):
            self._headers["X-Internal-API-Key"] = settings.api_core.api_key

    async def update_file_status(
        self,
        file_id: str,
        status: IngestionStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Update file processing status via API Core.

        Args:
            file_id: File ID to update
            status: New status (pending, processing, indexed, failed)
            error_message: Optional error message if status is failed

        Raises:
            IngestionException: If status update fails
        """
        try:
            url = f"{self.base_url}/api/v1/knowledge/files/{file_id}/status"
            payload = {
                "status": status.value,
            }
            if error_message:
                payload["error_message"] = error_message

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(url, json=payload, headers=self._headers)

                if response.status_code == 200:
                    logger.info(f"Updated file status: {file_id} -> {status.value}")
                elif response.status_code == 404:
                    logger.warning(f"File not found in API Core: {file_id}")
                    raise IngestionException(
                        f"File not found: {file_id}",
                        status_code=404,
                    )
                else:
                    error_text = response.text
                    logger.error(
                        f"Failed to update file status: {file_id}. "
                        f"Status: {response.status_code}, Response: {error_text}"
                    )
                    raise IngestionException(
                        f"Failed to update file status: {response.status_code}",
                        status_code=response.status_code,
                    )
        except httpx.TimeoutException as e:
            logger.error(f"Timeout updating file status: {file_id} - {e}")
            raise IngestionException(
                f"Timeout updating file status: {file_id}",
                status_code=504,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Request error updating file status: {file_id} - {e}")
            raise IngestionException(
                f"Request error updating file status: {file_id}",
                status_code=500,
            ) from e
        except IngestionException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating file status: {file_id} - {e}", exc_info=True)
            raise IngestionException(
                f"Unexpected error updating file status: {file_id}",
                status_code=500,
            ) from e

    async def update_qdrant_info(
        self,
        file_id: str,
        collection_name: str,
        point_ids: list[str],
    ) -> None:
        """
        Update Qdrant information for a file via API Core.

        Args:
            file_id: File ID to update
            collection_name: Qdrant collection name (e.g., firm_{firm_id})
            point_ids: List of Qdrant point IDs

        Raises:
            IngestionException: If update fails
        """
        try:
            url = f"{self.base_url}/api/v1/knowledge/files/{file_id}/qdrant-info"
            payload = {
                "collection_name": collection_name,
                "point_ids": point_ids,
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(url, json=payload, headers=self._headers)

                if response.status_code == 200:
                    logger.info(
                        f"Updated Qdrant info: {file_id} -> {collection_name} "
                        f"({len(point_ids)} points)"
                    )
                elif response.status_code == 404:
                    logger.warning(f"File not found in API Core: {file_id}")
                    raise IngestionException(
                        f"File not found: {file_id}",
                        status_code=404,
                    )
                else:
                    error_text = response.text
                    logger.error(
                        f"Failed to update Qdrant info: {file_id}. "
                        f"Status: {response.status_code}, Response: {error_text}"
                    )
                    raise IngestionException(
                        f"Failed to update Qdrant info: {response.status_code}",
                        status_code=response.status_code,
                    )
        except httpx.TimeoutException as e:
            logger.error(f"Timeout updating Qdrant info: {file_id} - {e}")
            raise IngestionException(
                f"Timeout updating Qdrant info: {file_id}",
                status_code=504,
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Request error updating Qdrant info: {file_id} - {e}")
            raise IngestionException(
                f"Request error updating Qdrant info: {file_id}",
                status_code=500,
            ) from e
        except IngestionException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating Qdrant info: {file_id} - {e}", exc_info=True)
            raise IngestionException(
                f"Unexpected error updating Qdrant info: {file_id}",
                status_code=500,
            ) from e

