"""Post-Call Worker for Memory Generation.

This module handles asynchronous post-call processing, including:
- Transcript summarization using LLMs
- Embedding generation for semantic search
- Memory storage in PostgreSQL (metadata) and Qdrant (vectors)

The worker is designed to be called after a conversation ends to generate
and store a summary for future client recognition.
"""

import json
from typing import List, Optional

from litellm import acompletion, aembedding
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from cognitive_orch.config import get_settings
from cognitive_orch.services.memory_service import MemoryService
from cognitive_orch.utils.errors import LLMError
from cognitive_orch.utils.logging import get_logger

logger = get_logger("post_call_worker")
settings = get_settings()


class PostCallWorker:
    """Worker service for post-call memory generation.
    
    This service processes call transcripts after a conversation ends,
    generating concise summaries and storing them in PostgreSQL with
    embeddings in Qdrant for semantic search.
    """

    def __init__(
        self,
        memory_service: Optional[MemoryService] = None,
        qdrant_client: Optional[QdrantClient] = None,
    ):
        """
        Initialize the post-call worker.
        
        Args:
            memory_service: Optional MemoryService instance. If not provided,
                          a new instance will be created.
            qdrant_client: Optional QdrantClient instance. If not provided,
                          a new instance will be created from settings.
        """
        self.memory_service = memory_service or MemoryService()
        self.qdrant_client = qdrant_client or self._create_qdrant_client()
        self.settings = get_settings()

    def _create_qdrant_client(self) -> QdrantClient:
        """Create Qdrant client from settings."""
        if self.settings.qdrant.is_cloud:
            return QdrantClient(
                url=self.settings.qdrant.url,
                api_key=self.settings.qdrant.api_key,
                timeout=self.settings.qdrant.timeout,
            )
        else:
            return QdrantClient(
                url=self.settings.qdrant.url,
                timeout=self.settings.qdrant.timeout,
                prefer_grpc=self.settings.qdrant.prefer_grpc,
            )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_memory(
        self,
        call_transcript: str,
        client_id: str,
        firm_id: str,
        include_embedding: bool = True,
    ) -> str:
        """
        Generate and store a memory from a call transcript.
        
        This method:
        1. Uses GPT-4o-mini to generate a concise summary
        2. Generates an embedding for the summary
        3. Stores metadata in PostgreSQL (ClientMemory)
        4. Stores vector in Qdrant for semantic search
        
        Args:
            call_transcript: The full conversation transcript
            client_id: The client's UUID
            firm_id: The firm's UUID (for Qdrant collection scoping)
            include_embedding: Whether to generate and store embeddings (default: True)
        
        Returns:
            str: The generated summary text
        
        Raises:
            LLMError: If LLM summarization fails after retries
            Exception: If memory storage fails
        """
        logger.info(f"Generating memory for client {client_id}")

        try:
            # Generate summary
            summary = await self._generate_summary(call_transcript)
            logger.info(f"Generated summary for client {client_id}: {summary[:100]}...")

            # Generate embedding and store in Qdrant if requested
            qdrant_point_id = None
            if include_embedding:
                embedding = await self._generate_embedding(summary)
                logger.info(f"Generated embedding for client {client_id} (dim: {len(embedding)})")
                
                # Store in Qdrant
                qdrant_point_id = await self._store_in_qdrant(
                    firm_id=firm_id,
                    client_id=client_id,
                    summary=summary,
                    embedding=embedding,
                )
                logger.info(f"Stored embedding in Qdrant: {qdrant_point_id}")

            # Store metadata in PostgreSQL
            await self.memory_service.store_memory(
                client_id=client_id,
                summary_text=summary,
                qdrant_point_id=qdrant_point_id,
            )

            logger.info(f"Successfully stored memory for client {client_id}")
            return summary

        except Exception as e:
            logger.error(
                f"Error generating memory for client {client_id}: {e}",
                exc_info=True,
            )
            raise

    async def _store_in_qdrant(
        self,
        firm_id: str,
        client_id: str,
        summary: str,
        embedding: List[float],
    ) -> str:
        """
        Store embedding in Qdrant.
        
        Args:
            firm_id: Firm UUID (for collection scoping)
            client_id: Client UUID
            summary: Summary text
            embedding: Embedding vector
        
        Returns:
            str: Qdrant point ID
        """
        import uuid
        from datetime import datetime

        collection_name = f"memories_{firm_id}"
        
        # Ensure collection exists
        try:
            self.qdrant_client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist, create it
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

        # Generate point ID
        point_id = str(uuid.uuid4())

        # Store point
        self.qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "client_id": client_id,
                        "summary": summary,
                        "created_at": datetime.utcnow().isoformat(),
                    },
                )
            ],
        )

        return point_id

    async def _generate_summary(self, transcript: str) -> str:
        """
        Generate a concise summary of the call transcript.
        
        Uses GPT-4o-mini with a specialized prompt to extract key facts
        that would be useful for a receptionist in future calls.
        
        Args:
            transcript: The full conversation transcript
        
        Returns:
            str: Concise 1-2 sentence summary
        
        Raises:
            LLMError: If summarization fails
        """
        # Build the summarization prompt
        system_prompt = self._build_summarization_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ]

        try:
            # Use GPT-4o-mini for cost-effective summarization
            response = await acompletion(
                model="azure/gpt-4o-mini",  # Adjust based on your deployment
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent summaries
                max_tokens=150,  # Keep summaries concise
            )

            summary = response.choices[0].message.content.strip()

            if not summary:
                raise LLMError("LLM returned empty summary")

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            raise LLMError(f"Failed to generate summary: {e}") from e

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the summary text.
        
        Uses Azure OpenAI text-embedding-ada-002 model (1536 dimensions).
        
        Args:
            text: The text to embed (typically the summary)
        
        Returns:
            List[float]: Embedding vector (1536 dimensions)
        
        Raises:
            LLMError: If embedding generation fails
        """
        try:
            # Generate embedding using LiteLLM
            response = await aembedding(
                model="azure/text-embedding-ada-002",  # Adjust based on your deployment
                input=[text],
            )

            # Extract embedding from response
            embedding = response.data[0]["embedding"]

            if not embedding or len(embedding) != 1536:
                raise LLMError(f"Invalid embedding dimension: {len(embedding) if embedding else 0}")

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            raise LLMError(f"Failed to generate embedding: {e}") from e

    @staticmethod
    def _build_summarization_prompt() -> str:
        """
        Build the system prompt for call summarization.
        
        Returns:
            str: System prompt instructing the LLM how to summarize
        """
        return """You are a legal receptionist assistant analyzing phone call transcripts.

Your task is to summarize this call in 1-2 sentences, focusing on key facts that would be useful for a receptionist in future calls.

Include:
- Names mentioned (caller, attorneys, other parties)
- Dates or deadlines discussed
- Type of legal matter or case
- Actions taken (scheduled appointment, requested callback, transferred call, etc.)
- Important context (urgency, emotional state if relevant)

Keep it concise, factual, and actionable. Write in past tense.

Example good summary:
"Client John Smith called about a divorce case. He scheduled a consultation for Tuesday at 2pm and mentioned needing help with child custody arrangements."

Example good summary:
"Caller inquired about estate planning services. Provided fee estimate of $2,500-$3,500 and sent intake form by email."

Now summarize the following call:"""


# Convenience function for direct usage
async def generate_memory(
    call_transcript: str,
    client_id: str,
    firm_id: str,
    include_embedding: bool = True,
) -> str:
    """
    Generate and store a memory from a call transcript.
    
    This is a convenience function that creates a PostCallWorker instance
    and calls generate_memory. Useful for simple invocations.
    
    Args:
        call_transcript: The full conversation transcript
        client_id: The client's UUID
        firm_id: The firm's UUID (for Qdrant collection scoping)
        include_embedding: Whether to generate and store embeddings (default: True)
    
    Returns:
        str: The generated summary text
    
    Raises:
        LLMError: If LLM summarization fails after retries
        Exception: If memory storage fails
    """
    worker = PostCallWorker()
    return await worker.generate_memory(call_transcript, client_id, firm_id, include_embedding)

