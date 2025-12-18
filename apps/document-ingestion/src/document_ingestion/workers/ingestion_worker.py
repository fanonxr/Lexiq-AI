"""Ingestion worker for processing document ingestion jobs."""

import json

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from document_ingestion.clients.api_core_client import APICoreClient
from document_ingestion.config import get_settings
from document_ingestion.models.message import IngestionMessage, IngestionStatus
from document_ingestion.utils.errors import IngestionException
from document_ingestion.utils.logging import get_logger

logger = get_logger("ingestion_worker")
settings = get_settings()


class IngestionWorker:
    """
    Worker for processing document ingestion jobs from RabbitMQ.

    Processing pipeline:
    1. Download file from Blob Storage
    2. Parse document (Phase 3)
    3. Chunk text (Phase 4)
    4. Generate embeddings (Phase 5)
    5. Store in Qdrant (Phase 6)
    6. Update status via API Core
    """

    def __init__(self):
        """Initialize ingestion worker."""
        self.api_core_client = APICoreClient()
        # Initialize services
        from document_ingestion.services.chunking_service import ChunkingService
        from document_ingestion.services.embedding_service import EmbeddingService
        from document_ingestion.services.parser_service import ParserService
        from document_ingestion.services.qdrant_service import QdrantService
        from document_ingestion.services.storage_service import StorageService

        self.storage_service = StorageService()
        self.parser_service = ParserService()
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        # Services for later phases
        self.qdrant_service = QdrantService()

    async def process_message(self, message: IngestionMessage) -> None:
        """
        Process an ingestion job message.

        Args:
            message: Ingestion message containing file information

        Raises:
            IngestionException: If processing fails
        """
        file_id = message.file_id
        logger.info(
            f"Processing ingestion job: file_id={file_id}, "
            f"filename={message.filename}, type={message.file_type}"
        )

        try:
            # Update status to processing
            await self.api_core_client.update_file_status(
                file_id=file_id,
                status=IngestionStatus.PROCESSING,
            )

            # Phase 3: Download file from Blob Storage
            logger.info(f"Downloading file from storage: {message.blob_path}")
            file_data = await self.storage_service.download_file(message.blob_path)

            # Phase 3: Parse document
            logger.info(f"Parsing document: type={message.file_type}, filename={message.filename}")
            parsed_document = await self.parser_service.parse_document(
                file_data=file_data,
                file_type=message.file_type,
                filename=message.filename,
            )

            logger.info(
                f"Document parsed successfully: file_id={file_id}, "
                f"text_length={len(parsed_document.text)}, "
                f"word_count={parsed_document.metadata.word_count}"
            )

            # Phase 4: Chunk text
            base_metadata = {
                "file_id": file_id,
                "user_id": message.user_id,
                "firm_id": message.firm_id,
                "filename": message.filename,
                "file_type": message.file_type,
                **parsed_document.metadata.model_dump(exclude_none=True),
            }
            chunks = await self.chunking_service.chunk_text(
                text=parsed_document.text,
                chunk_size=settings.chunking.chunk_size,
                overlap=settings.chunking.chunk_overlap,
                method=settings.chunking.chunking_method,
                base_metadata=base_metadata,
                chunk_id_prefix=file_id,
            )
            total_tokens = sum(c.token_count for c in chunks)
            logger.info(
                f"Document chunked successfully: file_id={file_id}, "
                f"chunks={len(chunks)}, total_tokens={total_tokens}, "
                f"method={settings.chunking.chunking_method}"
            )

            # Phase 5: Generate embeddings
            embeddings = await self.embedding_service.generate_embeddings(chunks)
            embedding_dim = len(embeddings[0].vector) if embeddings else 0
            logger.info(
                f"Embeddings generated successfully: file_id={file_id}, "
                f"vectors={len(embeddings)}, dim={embedding_dim}, "
                f"provider={settings.embedding.provider.value}, model={settings.embedding.resolved_model_name}"
            )

            # Phase 6: Store in Qdrant
            collection_name = self.qdrant_service.get_collection_name(
                firm_id=message.firm_id,
                user_id=message.user_id,
            )
            point_ids = await self.qdrant_service.upsert_vectors(
                collection_name=collection_name,
                file_id=file_id,
                chunks=chunks,
                embeddings=embeddings,
            )

            # Phase 6: Update API Core with Qdrant info
            await self.api_core_client.update_qdrant_info(
                file_id=file_id,
                collection_name=collection_name,
                point_ids=point_ids,
            )

            # Parsing + chunking + embeddings + Qdrant indexing are complete (Phases 3-6).
            logger.info(
                f"Document indexed successfully (Phases 3-6 complete): file_id={file_id}, "
                f"text_length={len(parsed_document.text)}, chunks={len(chunks)}, dim={embedding_dim}, "
                f"collection={collection_name}, points={len(point_ids)}"
            )

            # Update status to indexed (only after Qdrant write + API Core update succeed)
            await self.api_core_client.update_file_status(
                file_id=file_id,
                status=IngestionStatus.INDEXED,
            )

            logger.info(f"Successfully processed ingestion job: file_id={file_id}")

        except IngestionException as e:
            # Ensure API Core reflects failure for any domain error (parsing/chunking/embedding/etc.)
            logger.error(
                f"Ingestion pipeline failed: file_id={file_id} - {e.message} ({e.code})",
                exc_info=True,
            )
            try:
                await self.api_core_client.update_file_status(
                    file_id=file_id,
                    status=IngestionStatus.FAILED,
                    error_message=e.message,
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update status to failed: file_id={file_id} - {update_error}",
                    exc_info=True,
                )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error processing ingestion job: file_id={file_id} - {e}",
                exc_info=True,
            )
            # Update status to failed
            try:
                await self.api_core_client.update_file_status(
                    file_id=file_id,
                    status=IngestionStatus.FAILED,
                    error_message=str(e),
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update status to failed: file_id={file_id} - {update_error}",
                    exc_info=True,
                )
            raise IngestionException(
                f"Failed to process ingestion job: {file_id}",
                status_code=500,
            ) from e

    async def handle_message(self, incoming_message: AbstractIncomingMessage) -> None:
        """
        Handle incoming message from RabbitMQ queue.

        Args:
            incoming_message: Raw message from RabbitMQ

        Raises:
            IngestionException: If message processing fails
        """
        async with incoming_message.process():
            try:
                # Parse message body
                try:
                    body = json.loads(incoming_message.body.decode("utf-8"))
                    message = IngestionMessage(**body)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse message: {e}")
                    raise IngestionException(
                        f"Invalid message format: {e}",
                        status_code=400,
                    ) from e

                # Process message
                await self.process_message(message)

                # Message will be acknowledged automatically by context manager
                logger.debug(f"Message processed and acknowledged: file_id={message.file_id}")

            except IngestionException:
                # Re-raise to let message go to DLQ
                raise
            except Exception as e:
                logger.error(f"Unexpected error handling message: {e}", exc_info=True)
                raise IngestionException(
                    f"Unexpected error handling message: {e}",
                    status_code=500,
                ) from e

