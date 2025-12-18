"""Chunk models for document ingestion."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TextChunk(BaseModel):
    """A chunk of text produced by the chunking service."""

    chunk_index: int = Field(..., description="0-based index of this chunk within the document")
    text: str = Field(..., description="Chunk text content")
    token_count: int = Field(..., ge=0, description="Token count of the chunk text")
    # Optional stable identifier; can be used for Qdrant point IDs later
    chunk_id: Optional[str] = Field(
        default=None, description="Optional stable identifier (e.g., '{file_id}:{chunk_index}')"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary metadata to carry forward (file_id, page, etc.)"
    )


