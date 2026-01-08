"""API Core client for status updates and file information."""

from typing import Optional

import httpx

from document_ingestion.config import get_settings
from document_ingestion.models.message import IngestionStatus
from document_ingestion.utils.errors import IngestionException
from document_ingestion.utils.logging import get_logger
from py_common.clients import InternalAPIClient

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
        self._client = InternalAPIClient(
            base_url=settings.api_core.url,
            api_key=settings.api_core.api_key,
            timeout=float(settings.api_core.timeout),
        )

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
            payload = {
                "status": status.value,
            }
            if error_message:
                payload["error_message"] = error_message

            await self._client.put(
                f"/api/v1/knowledge/files/{file_id}/status",
                json=payload,
            )

            logger.info(f"Updated file status: {file_id} -> {status.value}")
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                logger.warning(f"File not found in API Core: {file_id}")
                raise IngestionException(
                    f"File not found: {file_id}",
                    status_code=404,
                ) from e
            else:
                error_text = e.response.text
                logger.error(
                    f"Failed to update file status: {file_id}. "
                    f"Status: {status_code}, Response: {error_text}"
                )
                raise IngestionException(
                    f"Failed to update file status: {status_code}",
                    status_code=status_code,
                ) from e
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
            payload = {
                "collection_name": collection_name,
                "point_ids": point_ids,
            }

            await self._client.put(
                f"/api/v1/knowledge/files/{file_id}/qdrant-info",
                json=payload,
            )

            logger.info(
                f"Updated Qdrant info: {file_id} -> {collection_name} "
                f"({len(point_ids)} points)"
            )
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 404:
                logger.warning(f"File not found in API Core: {file_id}")
                raise IngestionException(
                    f"File not found: {file_id}",
                    status_code=404,
                ) from e
            else:
                error_text = e.response.text
                logger.error(
                    f"Failed to update Qdrant info: {file_id}. "
                    f"Status: {status_code}, Response: {error_text}"
                )
                raise IngestionException(
                    f"Failed to update Qdrant info: {status_code}",
                    status_code=status_code,
                ) from e
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

