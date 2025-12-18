"""Pydantic models for knowledge base API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class KnowledgeBaseFileResponse(BaseModel):
    """Response model for knowledge base file."""

    id: str = Field(..., description="File ID")
    userId: str = Field(..., alias="user_id", description="User ID")
    firmId: Optional[str] = Field(None, alias="firm_id", description="Firm ID")
    filename: str = Field(..., description="Original filename")
    fileType: str = Field(..., alias="file_type", description="File type (pdf, docx, txt, etc.)")
    fileSize: int = Field(..., alias="file_size", description="File size in bytes")
    storagePath: str = Field(..., alias="storage_path", description="Storage path in Blob Storage")
    status: str = Field(..., description="Processing status (pending, processing, indexed, failed)")
    errorMessage: Optional[str] = Field(None, alias="error_message", description="Error message if failed")
    qdrantCollection: Optional[str] = Field(
        None, alias="qdrant_collection", description="Qdrant collection name"
    )
    qdrantPointIds: Optional[str] = Field(
        None, alias="qdrant_point_ids", description="Qdrant point IDs (JSON array)"
    )
    indexedAt: Optional[datetime] = Field(None, alias="indexed_at", description="Indexing timestamp")
    createdAt: datetime = Field(..., alias="created_at", description="Creation timestamp")
    updatedAt: datetime = Field(..., alias="updated_at", description="Last update timestamp")

    model_config = {"populate_by_name": True}


class FileStatusUpdateRequest(BaseModel):
    """Request model to update file processing status (internal service use)."""

    status: str = Field(..., description="New status (pending, processing, indexed, failed)")
    error_message: Optional[str] = Field(
        default=None, description="Optional error message if failed"
    )


class QdrantInfoUpdateRequest(BaseModel):
    """Request model to update Qdrant indexing metadata (internal service use)."""

    collection_name: str = Field(..., description="Qdrant collection name")
    point_ids: List[str] = Field(..., description="List of Qdrant point IDs")


class KnowledgeBaseFileListResponse(BaseModel):
    """Response model for list of knowledge base files."""

    files: List[KnowledgeBaseFileResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    file: KnowledgeBaseFileResponse = Field(..., description="Uploaded file information")
    message: str = Field(default="File uploaded successfully", description="Success message")


class FileStatusResponse(BaseModel):
    """Response model for file status."""

    id: str = Field(..., description="File ID")
    status: str = Field(..., description="Processing status")
    errorMessage: Optional[str] = Field(None, alias="error_message", description="Error message if failed")
    indexedAt: Optional[datetime] = Field(None, alias="indexed_at", description="Indexing timestamp")

    model_config = {"populate_by_name": True}

