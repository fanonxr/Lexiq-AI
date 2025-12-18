"""RabbitMQ publisher for document ingestion jobs."""

import json
from typing import Any, Dict, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message

from api_core.config import get_settings
from api_core.utils.logging import get_logger

logger = get_logger("ingestion_queue")
settings = get_settings()


class IngestionQueuePublisher:
    """Publishes ingestion messages to RabbitMQ for the document-ingestion service."""

    def __init__(self) -> None:
        self._connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self) -> None:
        """Connect to RabbitMQ and declare the exchange."""
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(settings.rabbitmq.url)
        self._channel = await self._connection.channel()

        # Declare exchange (idempotent)
        self._exchange = await self._channel.declare_exchange(
            name=settings.rabbitmq.exchange_name,
            type=ExchangeType.DIRECT,
            durable=True,
        )
        logger.info(
            f"RabbitMQ publisher connected: exchange={settings.rabbitmq.exchange_name}, routing_key={settings.rabbitmq.routing_key}"
        )

    async def close(self) -> None:
        """Close channel/connection."""
        try:
            if self._channel and not self._channel.is_closed:
                await self._channel.close()
        finally:
            self._channel = None
            self._exchange = None
        try:
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
        finally:
            self._connection = None

    async def publish(self, payload: Dict[str, Any]) -> None:
        """Publish a message to the ingestion exchange."""
        if not self._exchange:
            await self.connect()
        assert self._exchange is not None

        body = json.dumps(payload).encode("utf-8")
        msg = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(msg, routing_key=settings.rabbitmq.routing_key)


# Simple app-wide singleton (initialized in lifespan, used by endpoints)
publisher = IngestionQueuePublisher()


