"""Qdrant integration service for storing embeddings."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from document_ingestion.config import get_settings
from document_ingestion.models.chunk import TextChunk
from document_ingestion.models.embedding import ChunkEmbedding
from document_ingestion.utils.errors import QdrantError
from document_ingestion.utils.logging import get_logger

logger = get_logger("qdrant_service")
settings = get_settings()

# Deterministic namespace for generating stable point IDs from (file_id, chunk_index)
_POINT_ID_NAMESPACE = uuid.UUID("6b9c7d68-4b93-4c9c-9d83-0b6c68dbb4d9")


class QdrantService:
    """
    Store embeddings in Qdrant.

    Strategy:
    - Collection per firm: `firm_{firm_id}` (prefix configurable via `QDRANT_COLLECTION_PREFIX`)
    - If firm_id is missing, fall back to a per-user collection: `user_{user_id}`
    - Ensure collection exists with vector size matching the embedding dimension
    - Upsert points with metadata payload for RAG retrieval
    """

    def __init__(self) -> None:
        self._client: Optional[QdrantClient] = None

    def _get_client(self) -> QdrantClient:
        if self._client is not None:
            return self._client

        self._client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=settings.qdrant.timeout,
        )
        return self._client

    def get_collection_name(self, firm_id: Optional[str], user_id: str) -> str:
        """Resolve collection name for firm/user."""
        if firm_id:
            return f"{settings.qdrant.collection_prefix}{firm_id}"
        # fallback for personal uploads (no firm)
        return f"user_{user_id}"

    def _make_point_id(self, file_id: str, chunk_index: int) -> str:
        """Create a stable UUID point id for a chunk."""
        return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{file_id}:{chunk_index}"))

    async def ensure_collection(self, collection_name: str, vector_size: int) -> None:
        """Ensure the Qdrant collection exists with the right vector size."""

        def _ensure() -> None:
            client = self._get_client()
            try:
                info = client.get_collection(collection_name)
                # Qdrant can have named vectors; we only support default vector for now
                current_size = None
                try:
                    current_size = info.config.params.vectors.size  # type: ignore[attr-defined]
                except Exception:
                    # Newer configs may nest differently; fall back to None
                    current_size = None

                if current_size is not None and int(current_size) != int(vector_size):
                    raise QdrantError(
                        "Qdrant collection vector size mismatch",
                        details={
                            "collection": collection_name,
                            "expected": vector_size,
                            "actual": int(current_size),
                        },
                    )
                return
            except UnexpectedResponse as e:
                # If not found, Qdrant returns 404; create collection
                if getattr(e, "status_code", None) == 404:
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                    )
                    return
                raise
            except Exception as e:
                # Some client versions throw generic Exception on 404
                msg = str(e).lower()
                if "not found" in msg or "404" in msg:
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
                    )
                    return
                raise

        try:
            await asyncio.to_thread(_ensure)
            logger.info(
                f"Qdrant collection ensured: {collection_name} (vector_size={vector_size})"
            )
        except QdrantError:
            raise
        except Exception as e:
            raise QdrantError(
                "Failed to ensure Qdrant collection",
                details={"collection": collection_name, "error": str(e)},
            ) from e

    async def upsert_vectors(
        self,
        collection_name: str,
        file_id: str,
        chunks: List[TextChunk],
        embeddings: List[ChunkEmbedding],
    ) -> List[str]:
        """
        Upsert vectors into Qdrant and return point IDs.

        Assumes `embeddings` is aligned with `chunks` in order (same length).
        """
        if len(chunks) != len(embeddings):
            raise QdrantError(
                "Chunks and embeddings length mismatch",
                details={"chunks": len(chunks), "embeddings": len(embeddings)},
            )

        vector_size = len(embeddings[0].vector) if embeddings else 0
        if vector_size <= 0:
            raise QdrantError("Embedding vector size is invalid", details={"vector_size": vector_size})

        await self.ensure_collection(collection_name, vector_size)

        def _upsert() -> List[str]:
            client = self._get_client()
            points: List[PointStruct] = []
            point_ids: List[str] = []

            for chunk, emb in zip(chunks, embeddings):
                pid = self._make_point_id(file_id, chunk.chunk_index)
                payload: Dict[str, Any] = {
                    "file_id": file_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "embedding_model": emb.model,
                    "embedding_provider": emb.provider,
                    "metadata": chunk.metadata,
                }
                points.append(PointStruct(id=pid, vector=emb.vector, payload=payload))
                point_ids.append(pid)

            client.upsert(collection_name=collection_name, points=points, wait=True)
            return point_ids

        try:
            point_ids = await asyncio.to_thread(_upsert)
            logger.info(
                f"Qdrant upsert complete: collection={collection_name}, points={len(point_ids)}"
            )
            return point_ids
        except QdrantError:
            raise
        except Exception as e:
            raise QdrantError(
                "Failed to upsert vectors into Qdrant",
                details={"collection": collection_name, "error": str(e)},
            ) from e


