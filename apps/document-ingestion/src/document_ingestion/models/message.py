"""Message models for queue communication."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IngestionMessage(BaseModel):
    """
    Message model for document ingestion jobs.

    This model represents a job to process a document file:
    - Download from Azure Blob Storage
    - Parse the document
    - Chunk the text
    - Generate embeddings
    - Store in Qdrant
    """

    file_id: str = Field(..., description="Unique identifier for the file")
    user_id: str = Field(..., description="User who uploaded the file")
    firm_id: Optional[str] = Field(None, description="Firm ID (for multi-tenancy)")
    blob_path: str = Field(
        ...,
        description="Blob storage path (container/blob_name). Format: firm-{firm_id}-documents/{user_id}/{file_id}/{filename}",
    )
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type/extension (pdf, docx, txt, md)")
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow, description="Message creation timestamp"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class IngestionStatus(str, Enum):
    """Status values for document ingestion."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class StatusUpdateRequest(BaseModel):
    """Request model for updating file status via API Core."""

    status: IngestionStatus = Field(..., description="New status")
    error_message: Optional[str] = Field(None, description="Error message if status is failed")
    qdrant_point_ids: Optional[list[str]] = Field(
        None, description="List of Qdrant point IDs for successful indexing"
    )

