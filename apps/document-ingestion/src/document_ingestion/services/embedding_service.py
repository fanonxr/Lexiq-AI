"""Embedding generation service (provider-agnostic)."""

from __future__ import annotations

from typing import List

from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from document_ingestion.config import EmbeddingProvider, get_settings
from document_ingestion.models.chunk import TextChunk
from document_ingestion.models.embedding import ChunkEmbedding
from document_ingestion.utils.errors import EmbeddingError
from document_ingestion.utils.logging import get_logger

logger = get_logger("embedding_service")
settings = get_settings()


class EmbeddingService:
    """
    Generate embeddings for text chunks using a configurable provider.

    Providers:
    - openai: OpenAI direct API (recommended when Azure quota is unavailable)
    - azure: Azure OpenAI (requires deployment + quota)
    """

    def __init__(self) -> None:
        self._provider = settings.embedding.provider
        self._model_name = settings.embedding.resolved_model_name
        self._client = None  # lazy

    def _get_client(self):
        """Create the appropriate OpenAI client for the selected provider."""
        if self._client is not None:
            return self._client

        from openai import AsyncAzureOpenAI, AsyncOpenAI

        if self._provider == EmbeddingProvider.OPENAI:
            if not settings.embedding.openai_api_key:
                raise EmbeddingError(
                    "OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai",
                    model=self._model_name,
                )
            self._client = AsyncOpenAI(
                api_key=settings.embedding.openai_api_key,
                base_url=settings.embedding.openai_base_url,
                timeout=settings.embedding.timeout,
            )
            return self._client

        if self._provider == EmbeddingProvider.AZURE:
            if not (
                settings.embedding.azure_openai_endpoint
                and settings.embedding.azure_openai_api_key
                and settings.embedding.embedding_deployment_name
            ):
                raise EmbeddingError(
                    "Azure embeddings require AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and EMBEDDING_DEPLOYMENT_NAME",
                    model=self._model_name,
                )
            self._client = AsyncAzureOpenAI(
                api_key=settings.embedding.azure_openai_api_key,
                azure_endpoint=settings.embedding.azure_openai_endpoint,
                api_version=settings.embedding.azure_openai_api_version,
                timeout=settings.embedding.timeout,
            )
            return self._client

        raise EmbeddingError(f"Unsupported embedding provider: {self._provider}", model=self._model_name)

    async def _embed_batch(self, inputs: List[str]) -> List[List[float]]:
        """Embed one batch of texts."""
        client = self._get_client()
        try:
            resp = await client.embeddings.create(model=self._model_name, input=inputs)
            return [d.embedding for d in resp.data]
        except Exception as e:
            raise EmbeddingError(f"Embedding request failed: {e}", model=self._model_name) from e

    async def _embed_batch_with_retry(self, inputs: List[str]) -> List[List[float]]:
        """Embed a batch with retry logic (rate limits, transient failures)."""
        async for attempt in AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(settings.embedding.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            retry=retry_if_exception_type(EmbeddingError),
        ):
            with attempt:
                return await self._embed_batch(inputs)
        # unreachable due to reraise=True, but keeps type checkers happy
        raise EmbeddingError("Embedding retries exhausted", model=self._model_name)

    async def generate_embeddings(self, chunks: List[TextChunk]) -> List[ChunkEmbedding]:
        """
        Generate embeddings for a list of chunks.

        Args:
            chunks: Text chunks to embed

        Returns:
            List of ChunkEmbedding objects aligned with the input chunks order
        """
        if not chunks:
            return []

        if not settings.embedding.is_configured:
            raise EmbeddingError(
                "Embeddings are not configured. Set EMBEDDING_PROVIDER=openai and OPENAI_API_KEY (recommended) "
                "or EMBEDDING_PROVIDER=azure with AZURE_OPENAI_ENDPOINT/AZURE_OPENAI_API_KEY/EMBEDDING_DEPLOYMENT_NAME.",
                model=self._model_name,
            )

        provider_str = self._provider.value if hasattr(self._provider, "value") else str(self._provider)
        logger.info(
            f"Generating embeddings: provider={provider_str}, model={self._model_name}, "
            f"chunks={len(chunks)}, batch_size={settings.embedding.batch_size}"
        )

        inputs = [c.text for c in chunks]
        out: List[ChunkEmbedding] = []

        batch_size = max(1, settings.embedding.batch_size)
        for start in range(0, len(inputs), batch_size):
            batch_texts = inputs[start : start + batch_size]
            batch_chunks = chunks[start : start + batch_size]

            vectors = await self._embed_batch_with_retry(batch_texts)
            if len(vectors) != len(batch_chunks):
                raise EmbeddingError(
                    "Embedding response size mismatch",
                    model=self._model_name,
                    details={"expected": len(batch_chunks), "got": len(vectors)},
                )

            for chunk, vector in zip(batch_chunks, vectors):
                if (
                    settings.embedding.embedding_dimension is not None
                    and len(vector) != settings.embedding.embedding_dimension
                ):
                    raise EmbeddingError(
                        "Embedding dimension mismatch",
                        model=self._model_name,
                        details={
                            "expected_dimension": settings.embedding.embedding_dimension,
                            "actual_dimension": len(vector),
                        },
                    )

                out.append(
                    ChunkEmbedding(
                        chunk_index=chunk.chunk_index,
                        chunk_id=chunk.chunk_id,
                        vector=vector,
                        model=self._model_name,
                        provider=provider_str,
                        metadata=chunk.metadata,
                    )
                )

        if out:
            dim = len(out[0].vector)
            logger.info(f"Embeddings generated successfully: count={len(out)}, dimension={dim}")

        return out


