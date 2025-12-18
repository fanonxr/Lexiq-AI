"""Embedding models for document ingestion."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChunkEmbedding(BaseModel):
    """Embedding vector for a specific text chunk."""

    chunk_index: int = Field(..., description="0-based chunk index")
    chunk_id: Optional[str] = Field(default=None, description="Optional stable chunk id")
    vector: List[float] = Field(..., description="Embedding vector")
    model: str = Field(..., description="Embedding model/deployment used")
    provider: str = Field(..., description="Embedding provider (openai|azure)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata copied from the chunk")

"""Embedding models for document ingestion."""

from typing import List, Optional

from pydantic import BaseModel, Field


class EmbeddingVector(BaseModel):
    """Embedding vector for a specific text chunk."""

    chunk_index: int = Field(..., description="0-based chunk index")
    chunk_id: Optional[str] = Field(default=None, description="Optional chunk identifier")
    vector: List[float] = Field(..., description="Embedding vector")


