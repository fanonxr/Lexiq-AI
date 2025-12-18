"""Knowledge base service for file management operations."""

import logging
import uuid
from datetime import datetime
import json
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from api_core.database.models import KnowledgeBaseFile
from api_core.exceptions import NotFoundError, ValidationError
from api_core.repositories.knowledge_repository import KnowledgeRepository
from api_core.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for knowledge base file management."""

    def __init__(self, session: AsyncSession):
        """Initialize knowledge service."""
        self.repository = KnowledgeRepository(session)
        self.storage_service = get_storage_service()

    async def upload_file(
        self,
        user_id: str,
        firm_id: Optional[str],
        filename: str,
        file_data: bytes,
        file_type: str,
    ) -> KnowledgeBaseFile:
        """Upload a file to knowledge base.

        Args:
            user_id: User ID
            firm_id: Optional firm ID
            filename: Original filename
            file_data: File data as bytes
            file_type: File type (pdf, docx, txt, etc.)

        Returns:
            KnowledgeBaseFile instance

        Raises:
            ValidationError: If file validation fails
        """
        # Validate file size
        max_size_bytes = self.storage_service.settings.storage.max_file_size_mb * 1024 * 1024
        if len(file_data) > max_size_bytes:
            raise ValidationError(
                f"File size exceeds maximum allowed size of {self.storage_service.settings.storage.max_file_size_mb}MB"
            )

        # Validate file type
        allowed_types = self.storage_service.settings.storage.allowed_file_types
        if file_type.lower() not in [t.lower() for t in allowed_types]:
            raise ValidationError(
                f"File type '{file_type}' is not allowed. Allowed types: {', '.join(allowed_types)}"
            )

        # Generate unique blob name
        file_id = str(uuid.uuid4())
        blob_name = f"{user_id}/{file_id}/{filename}"

        # Get container name
        if firm_id:
            container_name = self.storage_service.get_container_name(firm_id)
        else:
            # Fallback to user-specific container if no firm_id
            container_name = f"user-{user_id}-documents"

        # Upload to blob storage
        try:
            blob_url = await self.storage_service.upload_file(
                container_name=container_name,
                blob_name=blob_name,
                file_data=file_data,
            )
        except Exception as e:
            logger.error(f"Failed to upload file to blob storage: {e}")
            raise ValidationError(f"Failed to upload file: {str(e)}") from e

        # Create database record
        kb_file = KnowledgeBaseFile(
            user_id=user_id,
            firm_id=firm_id,
            filename=filename,
            file_type=file_type.lower(),
            file_size=len(file_data),
            storage_path=f"{container_name}/{blob_name}",
            status="pending",  # Will be processed by ingestion service
        )

        try:
            await self.repository.create(kb_file)
            logger.info(f"Created knowledge base file record: {kb_file.id}")
            return kb_file
        except Exception as e:
            # If database save fails, try to delete the blob
            try:
                await self.storage_service.delete_file(container_name, blob_name)
            except Exception:
                pass  # Log but don't fail
            logger.error(f"Failed to create knowledge base file record: {e}")
            raise ValidationError(f"Failed to save file record: {str(e)}") from e

    async def get_file_by_id(self, file_id: str, user_id: str) -> KnowledgeBaseFile:
        """Get a knowledge base file by ID.

        Args:
            file_id: File ID
            user_id: User ID (for authorization check)

        Returns:
            KnowledgeBaseFile instance

        Raises:
            NotFoundError: If file not found or user doesn't have access
        """
        kb_file = await self.repository.get_by_id(file_id)
        if not kb_file:
            raise NotFoundError(f"Knowledge base file not found: {file_id}")

        # Check authorization
        if kb_file.user_id != user_id:
            raise NotFoundError(f"Knowledge base file not found: {file_id}")

        return kb_file

    async def list_files(
        self, user_id: str, firm_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[KnowledgeBaseFile]:
        """List knowledge base files for a user.

        Args:
            user_id: User ID
            firm_id: Optional firm ID to filter by
            status: Optional status to filter by

        Returns:
            List of KnowledgeBaseFile instances
        """
        if status:
            files = await self.repository.get_by_status(status, firm_id=firm_id)
        else:
            files = await self.repository.get_by_user_id(user_id, firm_id=firm_id)

        # Filter by user_id (additional security check)
        return [f for f in files if f.user_id == user_id]

    async def delete_file(self, file_id: str, user_id: str) -> None:
        """Delete a knowledge base file.

        Args:
            file_id: File ID
            user_id: User ID (for authorization check)

        Raises:
            NotFoundError: If file not found or user doesn't have access
        """
        # Get file
        kb_file = await self.get_file_by_id(file_id, user_id)

        # Delete from blob storage
        try:
            container_name, blob_name = kb_file.storage_path.split("/", 1)
            await self.storage_service.delete_file(container_name, blob_name)
        except Exception as e:
            logger.warning(f"Failed to delete file from blob storage: {e}")
            # Continue with database deletion even if blob deletion fails

        # Delete from database
        await self.repository.delete(file_id)
        logger.info(f"Deleted knowledge base file: {file_id}")

    async def update_file_status(
        self, file_id: str, status: str, error_message: Optional[str] = None
    ) -> KnowledgeBaseFile:
        """Update file processing status.

        Args:
            file_id: File ID
            status: New status (pending, processing, indexed, failed)
            error_message: Optional error message

        Returns:
            Updated KnowledgeBaseFile instance

        Raises:
            NotFoundError: If file not found
        """
        kb_file = await self.repository.get_by_id(file_id)
        if not kb_file:
            raise NotFoundError(f"Knowledge base file not found: {file_id}")

        kb_file.status = status
        kb_file.error_message = error_message
        if status == "indexed":
            kb_file.indexed_at = datetime.utcnow()

        await self.repository.update(kb_file)
        return kb_file

    async def update_qdrant_info(
        self, file_id: str, collection_name: str, point_ids: List[str]
    ) -> KnowledgeBaseFile:
        """Update Qdrant collection and point IDs for a file.

        Args:
            file_id: File ID
            collection_name: Qdrant collection name
            point_ids: List of Qdrant point IDs

        Returns:
            Updated KnowledgeBaseFile instance

        Raises:
            NotFoundError: If file not found
        """
        kb_file = await self.repository.get_by_id(file_id)
        if not kb_file:
            raise NotFoundError(f"Knowledge base file not found: {file_id}")

        kb_file.qdrant_collection = collection_name
        kb_file.qdrant_point_ids = json.dumps(point_ids)  # Store as JSON string

        await self.repository.update(kb_file)
        return kb_file


def get_knowledge_service(session: AsyncSession) -> KnowledgeService:
    """Get knowledge service instance.

    Args:
        session: Database session

    Returns:
        KnowledgeService instance
    """
    return KnowledgeService(session)

