"""Queue consumer for RabbitMQ message processing."""

from typing import Optional

import aio_pika
from aio_pika.abc import AbstractConnection, AbstractQueue

from document_ingestion.config import get_settings
from document_ingestion.utils.errors import IngestionException
from document_ingestion.utils.logging import get_logger
from document_ingestion.workers.ingestion_worker import IngestionWorker

logger = get_logger("queue_consumer")
settings = get_settings()


class QueueConsumer:
    """
    RabbitMQ queue consumer for document ingestion jobs.

    Handles:
    - Consuming messages from the queue
    - Processing messages via IngestionWorker
    - Message acknowledgment
    - Error handling and dead-letter queue routing
    """

    def __init__(self, connection: AbstractConnection):
        """
        Initialize queue consumer.

        Args:
            connection: RabbitMQ connection instance
        """
        self.connection = connection
        self.worker = IngestionWorker()
        self.channel: Optional[aio_pika.abc.AbstractChannel] = None
        self.queue: Optional[AbstractQueue] = None
        self._consumer_tag: Optional[str] = None
        self._running = False

    async def start(self) -> None:
        """Start consuming messages from the queue."""
        if self._running:
            logger.warning("Queue consumer is already running")
            return

        try:
            # Create channel
            self.channel = await self.connection.channel()
            logger.info("Created channel for queue consumer")

            # Set QoS (prefetch count)
            await self.channel.set_qos(prefetch_count=settings.rabbitmq.prefetch_count)
            logger.info(f"Set channel QoS prefetch_count={settings.rabbitmq.prefetch_count}")

            # Get exchange
            exchange = await self.channel.declare_exchange(
                name=settings.rabbitmq.exchange_name,
                type=aio_pika.ExchangeType.DIRECT,
                passive=True,  # Only check if exists, don't create
            )
            logger.info(f"Connected to exchange: {settings.rabbitmq.exchange_name}")

            # Get queue
            self.queue = await self.channel.declare_queue(
                name=settings.rabbitmq.queue_name,
                passive=True,  # Only check if exists, don't create
            )
            logger.info(f"Connected to queue: {settings.rabbitmq.queue_name}")

            # Start consuming
            self._running = True
            self._consumer_tag = await self.queue.consume(self._on_message)
            logger.info("Started consuming messages from queue")

        except Exception as e:
            logger.error(f"Failed to start queue consumer: {e}", exc_info=True)
            self._running = False
            raise

    async def stop(self) -> None:
        """Stop consuming messages."""
        if not self._running:
            return

        logger.info("Stopping queue consumer...")
        self._running = False

        if self.queue:
            try:
                if self._consumer_tag:
                    await self.queue.cancel(self._consumer_tag)
                    logger.info("Cancelled queue consumer")
                else:
                    logger.info("No consumer_tag found; skipping queue cancel")
            except Exception as e:
                logger.error(f"Error cancelling queue consumer: {e}", exc_info=True)
            finally:
                self._consumer_tag = None

        if self.channel and not self.channel.is_closed:
            try:
                await self.channel.close()
                logger.info("Closed consumer channel")
            except Exception as e:
                logger.error(f"Error closing consumer channel: {e}", exc_info=True)

    async def _on_message(self, message: aio_pika.abc.AbstractIncomingMessage) -> None:
        """
        Handle incoming message.

        Args:
            message: Incoming message from RabbitMQ
        """
        try:
            await self.worker.handle_message(message)
        except IngestionException as e:
            # Log error and let message go to DLQ
            logger.error(
                f"Failed to process message: {e.message} (status_code={e.status_code})"
            )
            # Message will be rejected and sent to DLQ
            await message.reject(requeue=False)
        except Exception as e:
            # Unexpected error - log and send to DLQ
            logger.error(f"Unexpected error processing message: {e}", exc_info=True)
            await message.reject(requeue=False)

    @property
    def is_running(self) -> bool:
        """Check if consumer is running."""
        return self._running

